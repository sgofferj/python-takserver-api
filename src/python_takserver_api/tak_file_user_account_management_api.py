#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# tak_file_user_account_management_api.py from https://github.com/sgofferj/takserver-api-python
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


"""file-user-account-management-api - https://docs.tak.gov/api/takserver#tag/file-user-account-management-api"""

from typing import Any


class UserAccountManagementApi:
    """User Account Management API wrapper"""

    def __init__(self, server: Any) -> None:
        self.server = server

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    async def create_or_update_file_user(
        self,
        username: str,
        password: str,
        group_list_both: list[str] | None = None,
        group_list_in: list[str] | None = None,
        group_list_out: list[str] | None = None,
    ) -> tuple[int, Any]:
        """Create or update a user on the server"""
        path = "/user-management/api/new-user"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        data: dict[str, Any] = {"username": username, "password": password}
        if group_list_in is not None:
            data.update({"groupListIN": group_list_in})
        if group_list_out is not None:
            data.update({"groupListOUT": group_list_out})
        if group_list_both is not None:
            data.update({"groupList": group_list_both})
        s, r = await self.server.connection.request("post", url, headers=headers, json=data)
        return s, r

    async def get_all_users(self) -> tuple[int, Any]:
        """Returns a list of all users on the server"""
        path = "/user-management/api/list-users"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, r

    async def get_all_group_names(self) -> tuple[int, Any]:
        """Returns a list of all groups on the server"""
        path = "/user-management/api/list-groupnames"
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
