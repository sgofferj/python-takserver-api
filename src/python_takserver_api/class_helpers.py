#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# class_helpers.py from https://github.com/sgofferj/takserver-api-python
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

"""Helper classes for TAK Server API"""

from typing import Any
import ssl
import aiohttp


class ConnectionHelper:
    """Helper class for managing connections"""

    def __init__(self, server: Any, cert: str, key: str) -> None:
        self.server = server
        self.cert = cert.strip()
        self.key = key.strip()

    def get_ssl_context(self) -> aiohttp.TCPConnector:
        """Returns an SSL context for the connection"""
        sslcontext = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
        sslcontext.check_hostname = False
        sslcontext.verify_mode = ssl.CERT_NONE
        sslcontext.load_cert_chain(certfile=self.cert, keyfile=self.key)
        tcpconn = aiohttp.TCPConnector(ssl_context=sslcontext)
        return tcpconn

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: str | None = None,
    ) -> tuple[int, Any]:
        """Performs an HTTP request"""
        try:
            r: Any = "Error"
            match method:
                case "get" | "GET":
                    r = await self.server.session.get(url, headers=headers)
                case "post" | "POST":
                    r = await self.server.session.post(url, headers=headers, json=json)
                case "put" | "PUT":
                    if data is not None:
                        r = await self.server.session.put(url, headers=headers, data=data)
                    else:
                        r = await self.server.session.put(url, headers=headers, json=json)
                case "delete" | "DELETE":
                    r = await self.server.session.delete(url, headers=headers)

            if r.status >= 400:
                return r.status, await r.text()
            if r.content_type == "application/json":
                return r.status, await r.json()
            return r.status, await r.text()
        except (
            aiohttp.ClientConnectorSSLError,
            aiohttp.ClientConnectorCertificateError,
        ) as e:
            r = str(e)
            return 999, r
