#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# tak_file_user_account_management_api.py from https://github.com/sgofferj/python-takserver-api
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


"""file-user-account-management-api

Manages file-based user accounts and groups. All operations are
version-aware: on TAK Server 5.7 the endpoints live under
``/user-management/api``, on 5.8+ they moved to
``/Marti/api/user-management/api``. The base path is detected from the
server's version string on first use (and cached); it can also be forced
by setting ``user_management_base`` on the ``Server`` instance before
first use.
"""

import re
from typing import Any

PREFIX_LEGACY = "/user-management/api"
PREFIX_MARTI = "/Marti/api/user-management/api"


def um_prefix_for_version(version: str | None) -> str:
    """Returns the user-management base path for a TAK version string.

    TAK Server 5.8 relocated the user-management endpoints from
    ``/user-management/api`` to ``/Marti/api/user-management/api``.
    Anything undetectable falls back to the legacy prefix.
    """
    if not version:
        return PREFIX_LEGACY
    match = re.match(r"^v?(\d+)\.(\d+)", version.strip())
    if match:
        major, minor = int(match.group(1)), int(match.group(2))
        if major > 5 or (major == 5 and minor >= 8):
            return PREFIX_MARTI
    return PREFIX_LEGACY


class UserAccountManagementApi:
    """User Account Management API wrapper"""

    def __init__(self, server: Any) -> None:
        self.server = server
        # explicit override wins; otherwise detect once, lazily
        self._prefix: str | None = getattr(server, "user_management_base", None)

    async def _base(self) -> str:
        """Resolves (and caches) the user-management base path"""
        if self._prefix is None:
            s, r = await self.server.connection.request(
                "get",
                f"{self.server.api_base_url}/Marti/api/version",
                headers={"Content-Type": "application/json"},
            )
            self._prefix = um_prefix_for_version(str(r) if s == 200 else None)
        return self._prefix

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    async def create_or_update_file_user(
        self,
        username: str,
        password: str,
        group_list_both: list[str] | None = None,
        group_list_in: list[str] | None = None,
        group_list_out: list[str] | None = None,
    ) -> tuple[int, Any]:
        """Create or update a user on the server.

        The three group lists are always sent - the server replies with
        HTTP 500 when they are omitted.

        Note: on 5.7, creating a user with a group in `groupList` did not
        reliably persist the membership; assigning groups afterwards via
        `update_groups_for_user()` proved dependable.
        """
        path = f"{await self._base()}/new-user"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        data: dict[str, Any] = {
            "username": username,
            "password": password,
            "groupList": group_list_both if group_list_both is not None else [],
            "groupListIN": group_list_in if group_list_in is not None else [],
            "groupListOUT": group_list_out if group_list_out is not None else [],
        }
        s, r = await self.server.connection.request("post", url, headers=headers, json=data)
        return s, r

    async def get_all_users(self) -> tuple[int, Any]:
        """Returns a list of all users on the server"""
        path = f"{await self._base()}/list-users"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, r

    async def get_all_group_names(self) -> tuple[int, Any]:
        """Returns a list of all groups on the server"""
        path = f"{await self._base()}/list-groupnames"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, r

    async def user_exists(self, user: str) -> bool:
        """Check if a user exists on the server"""
        _, r = await self.get_all_users()
        g = next((item for item in r if item["username"] == user), None)
        return bool(g)

    async def group_exists(self, group: str) -> bool:
        """Check if a group exists on the server"""
        _, r = await self.get_all_group_names()
        g = next((item for item in r if item["groupname"] == group), None)
        return bool(g)

    async def get_users_in_group(self, group: str) -> tuple[int, Any]:
        """Returns a group record with its member list"""
        path = f"{await self._base()}/users-in-group/{group}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, r

    async def get_groups_for_user(self, username: str) -> tuple[int, Any]:
        """Returns the group entitlements of a user (UserManagement model).

        For channel subscriptions see
        `tak_group_api.GroupApi.get_groups_for_user()` instead.
        """
        path = f"{await self._base()}/get-groups-for-user/{username}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, r

    async def change_user_password(self, username: str, password: str) -> tuple[int, Any]:
        """Changes a user's password"""
        path = f"{await self._base()}/change-user-password"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        data = {"username": username, "password": password}
        s, r = await self.server.connection.request("put", url, headers=headers, json=data)
        return s, r

    async def delete_user(self, username: str) -> tuple[int, Any]:
        """Deletes a user account"""
        path = f"{await self._base()}/delete-user/{username}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("delete", url, headers=headers)
        return s, r

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    async def create_file_users_in_bulk(
        self,
        username_expression: str,
        start_n: int,
        end_n: int,
        group_list: list[str] | None = None,
        group_list_in: list[str] | None = None,
        group_list_out: list[str] | None = None,
    ) -> tuple[int, Any]:
        """Create multiple users in bulk (UserGenerationInBulkModel)

        ``username_expression`` must contain the ``[N]`` placeholder which is
        substituted with the running number from ``start_n`` to ``end_n``,
        e.g. ``"live-test-user-[N]"`` with ``start_n=1``, ``end_n=3``
        creates ``live-test-user-1`` .. ``live-test-user-3``. The server
        rejects requests without ``group_list`` (HTTP 400). Directions:
        `group_list_in` = send-into memberships, `group_list_out` =
        receive-from memberships.
        Returns a list of UserPasswordModel with the generated passwords.
        """
        path = f"{await self._base()}/new-users"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        data: dict[str, Any] = {
            "usernameExpression": username_expression,
            "startN": start_n,
            "endN": end_n,
            "groupList": group_list if group_list is not None else [],
            "groupListIN": group_list_in if group_list_in is not None else [],
            "groupListOUT": group_list_out if group_list_out is not None else [],
        }
        s, r = await self.server.connection.request("post", url, headers=headers, json=data)
        return s, r

    async def update_users_for_group(
        self,
        groupname: str,
        users_in_group_list: list[str] | None = None,
        users_in_group_list_in: list[str] | None = None,
        users_in_group_list_out: list[str] | None = None,
    ) -> tuple[int, Any]:
        """Replace the user membership of a group (SimpleGroupWithUsersModel)

        The three user lists are always sent - the server replies with
        HTTP 500 when any of them is omitted. Directions are from the
        group's point of view: `users_in_group_list_in` lists users who
        may send INTO the group, `users_in_group_list_out` users who
        receive its traffic, and `users_in_group_list` covers both.
        """
        path = f"{await self._base()}/update-group-users"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        data: dict[str, Any] = {
            "groupname": groupname,
            "usersInGroupList": users_in_group_list if users_in_group_list is not None else [],
            "usersInGroupListIN": users_in_group_list_in if users_in_group_list_in is not None else [],
            "usersInGroupListOUT": users_in_group_list_out if users_in_group_list_out is not None else [],
        }
        s, r = await self.server.connection.request("put", url, headers=headers, json=data)
        return s, r

    async def update_groups_for_user(
        self,
        username: str,
        group_list: list[str] | None = None,
        group_list_in: list[str] | None = None,
        group_list_out: list[str] | None = None,
    ) -> tuple[int, Any]:
        """Replace the group membership of a user (SimpleUserGroupModel)

        The three group lists are always sent - the server replies with
        HTTP 500 when any of them is omitted. Directions are from the
        group's point of view: `group_list_in` = groups the user may send
        into, `group_list_out` = groups whose traffic they receive,
        `group_list` = both directions.
        """
        path = f"{await self._base()}/update-groups"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        data: dict[str, Any] = {
            "username": username,
            "groupList": group_list if group_list is not None else [],
            "groupListIN": group_list_in if group_list_in is not None else [],
            "groupListOUT": group_list_out if group_list_out is not None else [],
        }
        s, r = await self.server.connection.request("put", url, headers=headers, json=data)
        return s, r
