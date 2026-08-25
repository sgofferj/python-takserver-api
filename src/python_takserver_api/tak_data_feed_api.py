#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# tak_data_feed_api.py from https://github.com/sgofferj/python-takserver-api
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


"""data-feed-api - predicate data feeds

Data feeds are server-side subscriptions that continuously pull CoT data
matching a predicate (e.g. a CoT type filter) from an external source.
This wrapper covers the `data-feed-api` tag: feed management (predicate
feeds), catalog/bounds queries, statistics and content access.

> **ACCESS TRAP (verified live):** when creating a predicate feed with
> `auth_type="X_509"` and an EMPTY `filter_groups` list, the server stores
> the feed in a state where NOBODY - not even the admin certificate -
> can read, update or delete it via the REST API (`403 Group access
> denied`). Always set `filter_groups` to at least one group your
> identity belongs to, e.g. `["__ANON__"]`. The `build_predicate_feed()`
> helper does this for you by default.

The server assigns its own UUID on creation; a `uuid` in the create body
is ignored.
"""

from typing import Any

from .class_helpers import unwrap_api_response


class DataFeedApi:
    """Data Feed API wrapper"""

    def __init__(self, server: Any) -> None:
        self.server = server

    @staticmethod
    def _unwrap(payload: Any) -> Any:
        return unwrap_api_response(payload)

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    @staticmethod
    def build_predicate_feed(
        name: str,
        predicate: str,
        predicate_lang: str = "JSON_PATH",
        source_endpoint: str | None = None,
        archive: bool = True,
        sync: bool = False,
        federated: bool = False,
        auth_type: str = "ANONYMOUS",
        filter_groups: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Builds a PredicateDataFeed body with sane defaults.

        The server rejects minimal bodies with HTTP 500; it wants a fairly
        complete object. This helper fills in the fields the server needs
        and defaults `filter_groups` to `["__ANON__"]` so the feed stays
        accessible after creation (see the access-trap note above).
        """
        return {
            "name": name,
            "predicate": predicate,
            "predicateLang": predicate_lang,
            "dataSourceEndpoint": source_endpoint or "",
            "archive": archive,
            "sync": sync,
            "federated": federated,
            "authType": auth_type,
            "filterGroups": filter_groups if filter_groups is not None else ["__ANON__"],
            "tags": tags or [],
        }

    async def get_data_feeds(self) -> tuple[int, Any]:
        """Returns all data feeds visible to the authenticated user"""
        path = "/Marti/api/datafeeds"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def get_data_feeds_in_bbox(self, bbox: str) -> tuple[int, Any]:
        """Returns feeds whose contents fall inside a bounding box.

        `bbox` format is "minLon,minLat,maxLon,maxLat" (e.g.
        "23.7,61.4,23.8,61.5").
        """
        path = f"/Marti/api/datafeeds/bounds/{bbox}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def get_data_feeds_in_polygon(self, points: list[str]) -> tuple[int, Any]:
        """Returns feeds inside a polygon given as a list of point strings.

        A GET-with-body endpoint: `points` is sent as a JSON array of
        strings (one "lat,lon" pair per element).
        """
        path = "/Marti/api/datafeeds/bounds/polygon"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers, json=points)
        return s, self._unwrap(r)

    async def create_predicate_data_feed(self, feed: dict[str, Any]) -> tuple[int, Any]:
        """Creates a predicate data feed.

        The server assigns its own UUID; any `uuid` in `feed` is ignored.
        Minimal bodies are rejected with HTTP 500 - use
        `build_predicate_feed()` to construct a complete body.

        **Access trap:** with `auth_type="X_509"` and empty
        `filter_groups`, the created feed cannot be read, updated or
        deleted by anyone afterwards.
        """
        path = "/Marti/api/datafeeds/predicate"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("post", url, headers=headers, json=feed)
        return s, self._unwrap(r)

    async def update_predicate_data_feed(self, feed: dict[str, Any], update_groups: bool = False) -> tuple[int, Any]:
        """Updates an existing predicate data feed.

        `feed` must contain the complete object including its `uuid`.
        """
        path = "/Marti/api/datafeeds/predicate?updateGroups="
        path += str(update_groups).lower()
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("put", url, headers=headers, json=feed)
        return s, self._unwrap(r)

    async def delete_predicate_data_feed(self, feed_guid: str) -> tuple[int, Any]:
        """Deletes a predicate data feed by its GUID/UUID"""
        path = f"/Marti/api/datafeeds/predicate/{feed_guid}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("delete", url, headers=headers)
        return s, self._unwrap(r)

    async def get_predicate_data_feed(self, feed_uuid: str) -> tuple[int, Any]:
        """Returns a single predicate data feed by its GUID/UUID"""
        path = f"/Marti/api/datafeeds/predicate/{feed_uuid}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def get_stats(self) -> tuple[int, Any]:
        """Returns message statistics for all data feeds"""
        path = "/Marti/api/datafeeds/stats"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def get_stats_for_feed(self, uuid: str) -> tuple[int, Any]:
        """Returns message statistics for a single data feed"""
        path = f"/Marti/api/datafeeds/stats/{uuid}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def get_existing_cot_types(self, uuid: str) -> tuple[int, Any]:
        """Returns the list of CoT types currently present in a data feed"""
        path = f"/Marti/api/datafeeds/{uuid}/cots_types"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def get_cots_by_cot_type(self, uuid: str, cot_type: str) -> tuple[int, Any]:
        """Returns the CoT messages of one type currently stored in a feed"""
        path = f"/Marti/api/datafeeds/{uuid}/cots/{cot_type}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)
