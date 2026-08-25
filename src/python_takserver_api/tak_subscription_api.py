#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# tak_subscription_api.py from https://github.com/sgofferj/python-takserver-api
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


"""subscription-api - client subscription registry and per-client filters

The `subscription-api` tag covers the server's view of connected clients:
their subscription records (callsign, groups, client metadata), static
outbound subscriptions, the per-client incognito flag, per-client CoT
filters, and the group-change notification long-poll.

> **Handle with care:** every mutation here targets a *connected client's*
> state. Toggling `incognito` or installing a `filter` on someone else's
> client changes what the server delivers to them - only do that for UIDs
> you control.

The group-subscription toggles (`PUT /Marti/api/groups/active*`) are part
of this tag in the OpenAPI spec but live in
`python_takserver_api.tak_group_api.GroupApi`.
"""

from typing import Any

from .class_helpers import unwrap_api_response


class SubscriptionApi:
    """Subscription API wrapper"""

    def __init__(self, server: Any) -> None:
        self.server = server

    @staticmethod
    def _unwrap(payload: Any) -> Any:
        return unwrap_api_response(payload)

    async def get_all_subscriptions(self) -> tuple[int, Any]:
        """Returns all current client subscriptions.

        Each entry carries `clientUid`, `callsign`, `username`, `groups`,
        `incognito`, client metadata (`takClient`, `takVersion`,
        `protocol`, `port`, ...) and traffic counters.
        """
        path = "/Marti/api/subscriptions/all"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def get_subscription(self, uid: str) -> tuple[int, Any]:
        """Returns a single client subscription by its UID"""
        path = f"/Marti/api/subscription/{uid}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def add_static_subscription(self, sub: dict[str, Any]) -> tuple[int, Any]:
        """Adds a static subscription (tmpStaticSub).

        A static subscription makes the server treat a remote endpoint as
        a permanent subscriber: `uid`, `to` (destination address),
        `subaddr`/`subport`, `protocol`, optional `filterGroups` and
        `xpath`. Note that the server will attempt outbound connections
        to the given target.
        """
        path = "/Marti/api/subscriptions/add"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("post", url, headers=headers, json=sub)
        return s, self._unwrap(r)

    async def delete_subscription(self, uid: str) -> tuple[int, Any]:
        """Deletes a (static) subscription by UID"""
        path = f"/Marti/api/subscriptions/delete/{uid}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("delete", url, headers=headers)
        return s, self._unwrap(r)

    async def toggle_incognito(self, uid: str) -> tuple[int, Any]:
        """Toggles the incognito flag of a client subscription.

        An incognito client's markers are not broadcast to other clients.

        > **SERVER QUIRK (verified live 2026-08-25):** on the reference
        > server this call answers HTTP 200 but does NOT change the
        > `incognito` state of the subscription.
        """
        path = f"/Marti/api/subscriptions/incognito/{uid}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("post", url, headers=headers)
        return s, self._unwrap(r)

    async def set_filter(self, client_uid: str, filter_xml: str) -> tuple[int, Any]:
        """Installs a CoT filter for one client.

        `filter_xml` is the serialized `<filter>` document (application/xml,
        namespace `http://bbn.com/marti/xml/config`). The server requires a
        non-null `<geospatialFilter>` element inside it - e.g.

            <filter xmlns="http://bbn.com/marti/xml/config">
              <geospatialFilter filterTAKClients="true">
                <boundingBox minLongitude="0.0" minLatitude="0.0"
                  maxLongitude="10.0" maxLatitude="10.0"/>
              </geospatialFilter>
            </filter>

        The filter controls which CoT messages the server delivers to this
        client - a bad or too-restrictive filter can silence a client
        entirely.
        """
        path = f"/Marti/api/subscriptions/{client_uid}/filter"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/xml"}
        s, r = await self.server.connection.request("put", url, headers=headers, data=filter_xml)
        return s, self._unwrap(r)

    async def delete_filter(self, client_uid: str) -> tuple[int, Any]:
        """Removes a client's CoT filter"""
        path = f"/Marti/api/subscriptions/{client_uid}/filter"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/xml"}
        s, r = await self.server.connection.request("delete", url, headers=headers)
        return s, self._unwrap(r)

    async def bulk_groups_updated(self, usernames: list[str]) -> tuple[int, Any]:
        """Notifies the given users' clients about group changes.

        Bulk variant of the group-update long-poll trigger: pushes a group
        change notification to all listed usernames' connected clients so
        they re-fetch their channel list.
        """
        path = "/Marti/api/groups/update"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("post", url, headers=headers, json=usernames)
        return s, self._unwrap(r)
