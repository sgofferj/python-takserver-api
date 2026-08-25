#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# tak_group_api.py from https://github.com/sgofferj/python-takserver-api
#
# Copyright Stefan Gofferje
#
# Licensed under the Gnu General Public License Version 3 or higher (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.gnu.org/licenses/gpl-3.0.en.html
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either expressed or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""groups-api - channel (group) subscriptions

In TAK Server 5.x, "channels" are the classic file/LDAP auth groups exposed
to end users as a selectable subscription mechanism. Subscribing to a channel
is purely a change of the connection's active-group set in the server's
routing layer - no new CoT semantics are involved.

IMPORTANT: `set_active_groups()` has ABSOLUTE semantics - the request body
must contain the complete desired active set. Anything omitted becomes
inactive. The convenience helpers (`get_active_groups()`, `subscribe()`,
`unsubscribe()`) take care of the read-modify-write cycle for you.
"""

import asyncio
from collections.abc import Sequence
from typing import Any


class GroupApi:
    """Group (channel subscription) API wrapper"""

    def __init__(self, server: Any) -> None:
        self.server = server

    @staticmethod
    def _serialize_groups(groups: Sequence[tuple[str, str] | dict[str, Any]]) -> list[dict[str, str]]:
        """Serialize (name, direction) pairs or dicts into the request body format"""
        return [g if isinstance(g, dict) else {"name": g[0], "direction": str(g[1]).upper()} for g in groups]

    @staticmethod
    def _unwrap(payload: Any) -> Any:
        """Extract the `data` field of an ApiResponse envelope, pass through anything else.

        The group endpoints answer with `{"version", "type", "data", "nodeId"}`;
        callers get the payload itself instead of the envelope. Some responses
        (e.g. a user without any groups) omit the `data` field entirely -
        in that case `None` is returned.
        """
        if isinstance(payload, dict) and "version" in payload and "type" in payload:
            return payload.get("data")
        return payload

    async def get_all_groups(self, use_cache: bool = False, send_latest_sa: bool = False) -> tuple[int, Any]:
        """Returns the channels available to the authenticated user.

        The ApiResponse envelope is unwrapped: the returned payload is the
        list of groups. SCOPE NOTE: this endpoint lists the channels the
        user is ENTITLED to - its `active` flag does NOT reliably reflect
        the current subscription state. Use `get_groups_for_user()` (or
        this wrapper's `get_active_groups()`) for that. The list may
        contain duplicate group names with different creation dates
        (stale + current entries).
        """
        path = f"/Marti/api/groups/all?useCache={str(use_cache).lower()}"
        path += f"&sendLatestSA={str(send_latest_sa).lower()}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def get_groups_for_user(self, username: str) -> tuple[int, Any]:
        """Returns a user's ACTIVE CHANNEL SUBSCRIPTIONS.

        This is the subscription readback of `set_active_groups()` - one
        entry per subscribed (group, direction) pair. It is NOT the same
        as the entitlements managed by the User Account Management API
        (`UserAccountManagementApi.get_groups_for_user()`): entitlements
        define what a user MAY subscribe to, this defines what they ARE
        subscribed to right now.
        """
        path = f"/Marti/api/groups/user?username={username}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    # pylint: disable=redefined-builtin
    async def get_group(self, name: str, direction: str) -> tuple[int, Any]:
        """Returns a single group by name and direction ("IN" or "OUT")"""
        path = f"/Marti/api/groups/{name}/{str(direction).upper()}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def set_active_groups(
        self,
        groups: Sequence[tuple[str, str] | dict[str, Any]],
        client_uid: str | None = None,
    ) -> tuple[int, Any]:
        """Sets the COMPLETE active group set of the authenticated user.

        Semantics are absolute, not incremental: anything omitted from
        `groups` becomes inactive. Takes effect immediately on the existing
        CoT connection. Accepts (name, direction) tuples or plain dicts
        (e.g. entries taken straight from `get_all_groups()`).
        """
        path = "/Marti/api/groups/active"
        if client_uid is not None:
            path += f"?clientUid={client_uid}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("put", url, headers=headers, json=self._serialize_groups(groups))
        return s, r

    async def set_active_groups_bits(self, bits: list[int], client_uid: str | None = None) -> tuple[int, Any]:
        """Sets the active group set as a list of bitmask positions.

        Bit positions correspond to each group's `bitpos` field. As with
        `set_active_groups()`, the set is absolute.
        """
        path = "/Marti/api/groups/activebits"
        if client_uid is not None:
            path += f"?clientUid={client_uid}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("put", url, headers=headers, json=bits)
        return s, r

    async def set_active_groups_force(
        self, username: str, groups: Sequence[tuple[str, str] | dict[str, Any]]
    ) -> tuple[int, Any]:
        """Admin-forced activation of groups for a user (bypasses opt-out).

        Requires admin rights. As with `set_active_groups()`, semantics are
        absolute for the target user's FORCED set.
        """
        path = f"/Marti/api/groups/activeForce?username={username}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("put", url, headers=headers, json=self._serialize_groups(groups))
        return s, r

    async def wait_for_group_update(self, username: str) -> tuple[int, Any]:
        """Long-poll: blocks until an admin alters group assignments server-side.

        This is how clients refresh their channel list without reconnecting.
        Note that this call can block for a long time when nothing changes;
        wrap it in an `asyncio.timeout()` if you need a bounded wait.
        """
        path = f"/Marti/api/groups/update/{username}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, r

    async def get_group_cache_enabled(self) -> tuple[int, Any]:
        """Returns whether the server-side group cache is enabled"""
        path = "/Marti/api/groups/groupCacheEnabled"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def get_ldap_groups(self, group_name_filter: str) -> tuple[int, Any]:
        """Returns LDAP groups matching a name filter (LDAP-backed servers only)"""
        path = f"/Marti/api/groups?groupNameFilter={group_name_filter}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def get_ldap_group_members(self, group_name_filter: list[str]) -> tuple[int, Any]:
        """Returns members of LDAP groups matching the given name filters"""
        path = "/Marti/api/groups/members"
        sep = "?"
        for name in group_name_filter:
            path += f"{sep}groupNameFilter={name}"
            sep = "&"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    def _resolve_username(self, username: str | None) -> str:
        """Returns the explicitly given username or the server's default.

        Raises `ValueError` when neither is available.
        """
        resolved = username or getattr(self.server, "username", None)
        if not resolved:
            raise ValueError("username required: pass it explicitly or construct Server(..., username=...)")
        return resolved

    async def get_active_groups(self, username: str | None = None) -> list[dict[str, Any]]:
        """Returns a user's ACTIVE CHANNEL SUBSCRIPTIONS as `{"name", "direction"}` dicts.

        Built on `get_groups_for_user()` - the subscription readback - NOT
        on `get_all_groups()`, whose `active` flag does not reflect
        subscriptions. The result is directly suitable for feeding back
        into `set_active_groups()` (read-modify-write).

        `username` defaults to the username the `Server` was constructed
        with (`Server(..., username="cn-of-your-cert")`).
        """
        user = self._resolve_username(username)
        _, r = await self.get_groups_for_user(user)
        seen: set[tuple[str, str]] = set()
        active: list[dict[str, Any]] = []
        for g in r or []:
            if not g.get("active"):
                continue
            key = (g["name"], g["direction"])
            if key not in seen:
                seen.add(key)
                active.append({"name": g["name"], "direction": g["direction"]})
        return active

    @staticmethod
    def _resolve_spelling(all_groups: list[dict[str, Any]], name: str) -> str | None:
        """Returns the server's exact spelling of a group name.

        The group list can contain stale duplicate entries, including
        variants padded with leading/trailing whitespace. The unpadded
        spelling is preferred.
        """
        matches = sorted(
            {g["name"] for g in all_groups if g["name"].strip() == name.strip()},
            key=lambda s: s != name.strip(),
        )
        return matches[0] if matches else None

    async def subscribe_many(
        self,
        names: Sequence[str],
        directions: Sequence[str] = ("IN", "OUT"),
        username: str | None = None,
    ) -> tuple[int, Any]:
        """Subscribes to several channels with one read-modify-write cycle.

        Activates the given directions (default both) of each channel while
        leaving all other active groups untouched. Raises `ValueError` for
        channels that do not exist or are not visible to this user; in that
        case nothing is written.
        """
        wanted = {d.upper() for d in directions}
        _, all_groups = await self.get_all_groups()
        updated = await self.get_active_groups(username)
        for name in names:
            exact = self._resolve_spelling(all_groups, name)
            if exact is None:
                raise ValueError(f"Group '{name}' does not exist or is not visible to this user")
            available = {g["direction"] for g in all_groups if g["name"] == exact}
            for direction in sorted(wanted & available):
                if not any(g["name"] == exact and g["direction"] == direction for g in updated):
                    updated.append({"name": exact, "direction": direction})
        return await self.set_active_groups(updated)

    async def unsubscribe_many(
        self,
        names: Sequence[str],
        directions: Sequence[str] = ("IN", "OUT"),
        username: str | None = None,
    ) -> tuple[int, Any]:
        """Unsubscribes from several channels with one read-modify-write cycle.

        Deactivates the given directions of each channel while leaving all
        other active groups untouched. Unknown channels are ignored. NOTE:
        the server ignores writes of an EMPTY active set - you cannot
        unsubscribe from your last remaining channel via this endpoint
        (verified live 2026-08-25).
        """
        wanted = {d.upper() for d in directions}
        stripped = {n.strip() for n in names}
        current = await self.get_active_groups(username)
        updated = [g for g in current if not (g["name"].strip() in stripped and g["direction"] in wanted)]
        return await self.set_active_groups(updated)

    async def subscribe(
        self,
        name: str,
        directions: Sequence[str] = ("IN", "OUT"),
        username: str | None = None,
    ) -> tuple[int, Any]:
        """Subscribes to a channel (activates the given directions, default both).

        Read-modify-write around `set_active_groups()` - all other active
        groups remain untouched.
        """
        return await self.subscribe_many([name], directions, username)

    async def unsubscribe(
        self,
        name: str,
        directions: Sequence[str] = ("IN", "OUT"),
        username: str | None = None,
    ) -> tuple[int, Any]:
        """Unsubscribes from a channel (deactivates the given directions).

        Read-modify-write around `set_active_groups()` - all other active
        groups remain untouched.
        """
        return await self.unsubscribe_many([name], directions, username)

    async def get_channels(self) -> list[dict[str, Any]]:
        """Returns the dev-friendly view of all channels available to this user.

        Collapses the server's duplicate/stale entries into one record per
        channel:

            {"name": "channel-a",
             "type": "SYSTEM",
             "bitpos": 3,
             "directions": {"IN": True, "OUT": False}}

        where each direction maps to its `active` flag (a direction missing
        from the server's list is absent from the dict). When duplicates
        disagree, the newest entry (`created` date) wins and the unpadded
        name spelling is preferred. SCOPE NOTE: availability, not
        subscription state - see `get_active_groups()`.
        """
        _, r = await self.get_all_groups()
        ordered = sorted(r or [], key=lambda g: g.get("created") or "", reverse=True)
        ordered.sort(key=lambda g: g["name"] != g["name"].strip())
        channels: dict[str, dict[str, Any]] = {}
        for g in ordered:
            key = g["name"].strip()
            record = channels.setdefault(key, {"name": key, "directions": {}})
            record.setdefault("type", g.get("type"))
            record.setdefault("bitpos", g.get("bitpos"))
            record["directions"].setdefault(g["direction"], bool(g.get("active")))
        return [channels[k] for k in sorted(channels)]

    async def channel_exists(self, name: str) -> bool:
        """Check if a channel (group) is visible/available to this user"""
        _, r = await self.get_all_groups()
        return self._resolve_spelling(r or [], name) is not None

    async def is_subscribed(
        self,
        name: str,
        direction: str | None = None,
        username: str | None = None,
    ) -> bool:
        """Check whether a channel is currently subscribed.

        Built on the subscription readback (`get_groups_for_user()`), so it
        reflects reality - unlike the `active` flag of `get_all_groups()`.
        `direction` optionally narrows the check to "IN" or "OUT";
        by default ANY subscribed direction counts as subscribed.
        """
        user = self._resolve_username(username)
        _, r = await self.get_groups_for_user(user)
        matches = [
            g
            for g in r or []
            if g["name"].strip() == name.strip() and (direction is None or g["direction"] == direction.upper())
        ]
        return any(g.get("active") for g in matches)

    async def wait_for_group_update_until(self, username: str, timeout: float) -> tuple[int, Any]:
        """Bounded variant of `wait_for_group_update()`.

        Blocks at most `timeout` seconds; raises `TimeoutError` when no
        change happens within the window.
        """
        async with asyncio.timeout(timeout):
            return await self.wait_for_group_update(username)
