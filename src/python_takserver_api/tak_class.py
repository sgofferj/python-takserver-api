#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# tak_class.py from https://github.com/sgofferj/takserver-api-python
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

"""Main TAK Server API module"""

import aiohttp

from .class_helpers import ConnectionHelper
from .tak_home_api import HomeApi
from .tak_file_user_account_management_api import UserAccountManagementApi
from .tak_group_api import GroupApi
from .tak_mission_api import MissionApi


# pylint: disable=too-few-public-methods, too-many-instance-attributes
class Server:
    """Takserver API helper class"""

    def __init__(self, host: str, cert: str, key: str, username: str | None = None) -> None:
        """Initialize a server instance.

        `username` is optional and only needed by APIs that address the
        authenticated user by name (e.g. the group subscription helpers).
        For certificate auth it is the certificate's CN.
        """
        self.api_base_url = f"https://{host}:8443"
        self.username = username

        self.connection = ConnectionHelper(self, cert, key)
        tcpconn = self.connection.get_ssl_context()
        self.session = aiohttp.ClientSession(connector=tcpconn)

        self.home = HomeApi(self)
        self.user = UserAccountManagementApi(self)
        self.groups = GroupApi(self)
        self.mission = MissionApi(self)

    async def close(self) -> None:
        """Close the connection"""
        await self.session.close()
