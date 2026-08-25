#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# tak_home_api.py from https://github.com/sgofferj/python-takserver-api
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


"""home-api - https://docs.tak.gov/api/takserver#tag/home-api"""

from typing import Any


class HomeApi:
    """Home API wrapper"""

    def __init__(self, server: Any) -> None:
        self.server = server

    async def is_admin(self) -> bool:
        """Check if the configured certificate has admin rights on the server"""
        path = "/Marti/api/util/isAdmin"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        _, r = await self.server.connection.request("get", url, headers=headers)
        return bool(r)

    async def is_ldap_admin(self) -> bool:
        """Check if the configured certificate has LDAP admin rights.

        New in TAK Server 5.8 - on 5.7 the endpoint does not exist
        (HTTP 404).
        """
        path = "/Marti/api/util/isLdapAdmin"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        if s == 200:
            return bool(r)
        return False

    async def get_home(self) -> tuple[int, Any]:
        """Returns the server's home payload"""
        path = "/Marti/api/home"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, r

    async def get_user_roles(self) -> tuple[int, Any]:
        """Returns the roles of the configured certificate"""
        path = "/Marti/api/util/user/roles"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, r

    async def has_role(self, role: str) -> bool:
        """Check if the configured certificate has a specific role"""
        _, r = await self.get_user_roles()
        return bool(r) and role in r

    async def server_version(self) -> str | None:
        """Return the TAK server version string, or ``None`` if it cannot be determined.

        The spec's home-api ``getVer`` endpoint (``/Marti/api/ver``) returns
        HTTP 500 on the reference server (5.7-RELEASE-43-HEAD) and is
        therefore not wrapped; this helper uses the working version-api
        endpoint ``/Marti/api/version`` instead.
        """
        path = "/Marti/api/version"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        if s == 200:
            return str(r)
        return None
