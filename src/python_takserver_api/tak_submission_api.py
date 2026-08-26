#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# tak_submission_api.py from https://github.com/sgofferj/python-takserver-api
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


"""submission-api - CoT input management and messaging configuration

Covers the `submission-api` tag: read access to the server's CoT input
streams and their metrics, streaming data-feed registry (`/datafeeds`
by name), database counters, the store-and-forward chat feature flag
and the global messaging configuration.

> **NAMING RULE:** input and feed names must match `[A-Za-z0-9_]` plus
> whitespace, max 30 characters - hyphens are rejected with
> "Invalid input name".
>
> **SERVER QUIRKS (verified live on 5.7-RELEASE-43-HEAD, 2026-08-25):**
> - `modify_input()` is rejected (HTTP 400) by the messaging layer for
>   freshly created inputs.
> - `create_data_feed()` / `modify_data_feed()` fail with an empty HTTP
>   500 regardless of body.
> Live tests pin the broken behaviour so a fixing upgrade gets noticed.
"""

from typing import Any

from .class_helpers import unwrap_api_response


class SubmissionApi:
    """Submission API wrapper (CoT inputs, messaging config)"""

    def __init__(self, server: Any) -> None:
        self.server = server

    @staticmethod
    def _unwrap(payload: Any) -> Any:
        return unwrap_api_response(payload)

    # ------------------------------------------------------------------
    # Inputs
    # ------------------------------------------------------------------

    async def get_input_metrics(self, exclude_data_feeds: bool = False) -> tuple[int, Any]:
        """Returns metrics for all configured CoT input streams"""
        path = "/Marti/api/inputs"
        if exclude_data_feeds:
            path += "?excludeDataFeeds=true"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def get_input_metric(self, name: str) -> tuple[int, Any]:
        """Returns metrics for a single input stream by name

        On the reference server this answers HTTP 400 for unknown names.
        """
        path = f"/Marti/api/inputs/{name}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def create_input(self, feed: dict[str, Any]) -> tuple[int, Any]:
        """Creates a CoT input stream.

        > **Broken on the reference server:** always HTTP 400 (server-side
        > NPE during validation), independent of the body.
        """
        path = "/Marti/api/inputs"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("post", url, headers=headers, json=feed)
        return s, self._unwrap(r)

    async def modify_input(self, input_id: str, feed: dict[str, Any]) -> tuple[int, Any]:
        """Modifies a CoT input stream identified by its id"""
        path = f"/Marti/api/inputs/{input_id}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("put", url, headers=headers, json=feed)
        return s, self._unwrap(r)

    async def delete_input(self, name: str) -> tuple[int, Any]:
        """Deletes a CoT input stream by name

        Handle with care - deleting one of the server's primary inputs
        (e.g. its TLS listener) disconnects every client on it.
        """
        path = f"/Marti/api/inputs/{name}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("delete", url, headers=headers)
        return s, self._unwrap(r)

    # ------------------------------------------------------------------
    # Streaming data feeds (/Marti/api/datafeeds by name)
    # ------------------------------------------------------------------

    async def create_data_feed(self, feed: dict[str, Any]) -> tuple[int, Any]:
        """Creates a named streaming data feed.

        > **Broken on the reference server:** answers an empty HTTP 500
        > regardless of body (verified live 2026-08-25).
        """
        path = "/Marti/api/datafeeds"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("post", url, headers=headers, json=feed)
        return s, self._unwrap(r)

    async def get_data_feed(self, name: str) -> tuple[int, Any]:
        """Returns a named streaming data feed (HTTP 400 when unknown)"""
        path = f"/Marti/api/datafeeds/{name}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def modify_data_feed(self, name: str, feed: dict[str, Any]) -> tuple[int, Any]:
        """Modifies a named streaming data feed"""
        path = f"/Marti/api/datafeeds/{name}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("put", url, headers=headers, json=feed)
        return s, self._unwrap(r)

    async def delete_data_feed(self, name: str) -> tuple[int, Any]:
        """Deletes a named streaming data feed"""
        path = f"/Marti/api/datafeeds/{name}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("delete", url, headers=headers)
        return s, self._unwrap(r)

    # ------------------------------------------------------------------
    # Messaging configuration & features
    # ------------------------------------------------------------------

    async def get_config_info(self) -> tuple[int, Any]:
        """Returns the messaging configuration (database pool, SSL, SA settings).

        Passwords are masked by the server.
        """
        path = "/Marti/api/inputs/config"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def modify_config_info(self, config: dict[str, Any]) -> tuple[int, Any]:
        """Replaces the messaging configuration.

        **Global impact:** this touches database connection pooling and
        SSL settings of a running server. There is no dry-run.
        """
        path = "/Marti/api/inputs/config"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("put", url, headers=headers, json=config)
        return s, self._unwrap(r)

    async def is_store_forward_chat_enabled(self) -> tuple[int, Any]:
        """Returns whether store-and-forward for chat messages is enabled"""
        path = "/Marti/api/inputs/storeForwardChat/enabled"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def enable_store_forward_chat(self) -> tuple[int, Any]:
        """Enables store-and-forward for chat messages"""
        return await self._sf_toggle("enable")

    async def disable_store_forward_chat(self) -> tuple[int, Any]:
        """Disables store-and-forward for chat messages"""
        return await self._sf_toggle("disable")

    async def _sf_toggle(self, action: str) -> tuple[int, Any]:
        path = f"/Marti/api/inputs/storeForwardChat/{action}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("put", url, headers=headers)
        return s, self._unwrap(r)

    # ------------------------------------------------------------------
    # Database counters
    # ------------------------------------------------------------------

    async def get_database_cot_counts(self) -> tuple[int, Any]:
        """Returns CoT event/image counts stored in the database"""
        path = "/Marti/api/database/cotCount"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)
