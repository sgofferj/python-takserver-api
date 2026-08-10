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
        """Create or update a user on the server

        The three group lists are always sent - the server replies with
        HTTP 500 when they are omitted.
        """
        path = "/user-management/api/new-user"
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

    async def get_users_in_group(self, group: str) -> tuple[int, Any]:
        """Returns the users in a group (SimpleGroupWithUsersModel)"""
        path = f"/user-management/api/users-in-group/{group}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, r

    async def get_groups_for_user(self, username: str) -> tuple[int, Any]:
        """Returns the groups a user belongs to (SimpleUserGroupModel)"""
        path = f"/user-management/api/get-groups-for-user/{username}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, r

    async def change_user_password(self, username: str, password: str) -> tuple[int, Any]:
        """Change a user's password"""
        path = "/user-management/api/change-user-password"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        data: dict[str, Any] = {"username": username, "password": password}
        s, r = await self.server.connection.request("put", url, headers=headers, json=data)
        return s, r

    async def delete_user(self, username: str) -> tuple[int, Any]:
        """Delete a user from the server"""
        path = f"/user-management/api/delete-user/{username}"
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
        rejects requests without ``group_list`` (HTTP 400).
        Returns a list of UserPasswordModel with the generated passwords.
        """
        path = "/user-management/api/new-users"
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
        HTTP 500 when any of them is omitted.
        """
        path = "/user-management/api/update-group-users"
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
        HTTP 500 when any of them is omitted.
        """
        path = "/user-management/api/update-groups"
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
