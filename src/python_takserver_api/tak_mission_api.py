#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# tak_mission_api.py from https://github.com/sgofferj/takserver-api-python
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
#


"""home-api - https://docs.tak.gov/api/takserver#tag/mission-api"""

from typing import Any


class MissionApi:
    """Mission API wrapper"""

    def __init__(self, server: Any) -> None:
        self.server = server

    async def get_mission(self, name: str) -> tuple[int, Any]:
        """Returns a mission"""
        path = f"/Marti/api/missions/{name}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, r

    async def get_mission_role(self, name: str) -> tuple[int, Any]:
        """Returns role in the mission"""
        path = f"/Marti/api/missions/{name}/role"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, r

    async def get_mission_subscriptions(self, name: str) -> tuple[int, Any]:
        """Returns subscriptions to the mission"""
        path = f"/Marti/api/missions/{name}/subscriptions"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, r

    async def get_mission_subscription_roles(self, name: str) -> tuple[int, Any]:
        """Returns subscriptions to the mission"""
        path = f"/Marti/api/missions/{name}/subscriptions/roles"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, r

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    async def create_mission(
        self,
        name: str,
        creator_uid: str,
        group: str = "",
        default_role: str = "",
        classification: str = "",
    ) -> tuple[int, Any]:
        """Creates a mission"""
        path = f"/Marti/api/missions/{name}?creatorUid={creator_uid}"
        if group:
            path += f"&group={group}"
        if default_role:
            path += f"&defaultRole={default_role}"
        if classification:
            path += f"&classification={classification}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("put", url, headers=headers)
        return s, r

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    async def create_mission_subscription(
        self,
        name: str,
        uid: str,
        topic: str = "",
        password: str = "",
        secago: str = "",
        start: str = "",
        end: str = "",
    ) -> tuple[int, Any]:
        """Creates a mission subscription"""
        path = f"/Marti/api/missions/{name}/subscription?uid={uid}"
        if topic:
            path += f"&topic={topic}"
        if password:
            path += f"&password={password}"
        if secago:
            path += f"&secago={secago}"
        if start:
            path += f"&start={start}"
        if end:
            path += f"&end={end}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("put", url, headers=headers)
        return s, r

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    async def set_mission_role(
        self, name: str, client_uid: str, username: str, role: str, token: str
    ) -> tuple[int, Any]:
        """Sets the role for a subscriber"""
        path = f"/Marti/api/missions/{name}/role?clientUid={client_uid}&username={username}&role={role}"
        url = self.server.api_base_url + path
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        s, r = await self.server.connection.request("put", url, headers=headers)
        return s, r

    async def add_mission_content(self, name: str, uids: list[str], my_uid: str, token: str) -> tuple[int, Any]:
        """Adds content to a mission"""
        path = f"/Marti/api/missions/{name}/contents?creatorUid={my_uid}"
        url = self.server.api_base_url + path
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        data = {"uids": uids}
        s, r = await self.server.connection.request("put", url, headers=headers, json=data)
        return s, r

    async def remove_mission_content(self, name: str, uid: str, my_uid: str, token: str) -> tuple[int, Any]:
        """Removes content from a mission"""
        path = f"/Marti/api/missions/{name}/contents?creatorUid={my_uid}&uid={uid}"
        headers = {"Authorization": f"Bearer {token}"}
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("delete", url, headers=headers)
        return s, r
