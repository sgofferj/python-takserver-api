"""Tests for the Data Feed API"""

from typing import Any

import pytest


class MockConnection:
    """Mock connection recording requests and replaying canned responses."""

    def __init__(self, handler: Any) -> None:
        self.handler = handler

    async def request(  # noqa: N802
        self,
        method: str,
        url: str,
        headers: dict[str, Any] | None = None,
        json: dict[str, Any] | list[Any] | None = None,
        data: str | None = None,
    ) -> tuple[int, Any]:
        return await self.handler(method, url, headers, json, data)


class MockServer:  # noqa: N801
    api_base_url: str = "https://tak.example.com:8443"
    connection: Any = None


def envelope(data: Any) -> dict[str, Any]:
    return {"version": "3", "type": "tak.server.feeds.DataFeed", "data": data}


def make_api(handler: Any) -> tuple[Any, MockServer]:
    from python_takserver_api.tak_data_feed_api import DataFeedApi

    server = MockServer()
    server.connection = MockConnection(handler)
    return DataFeedApi(server), server


FEED_BODY = {
    "name": "feed-a",
    "predicate": "type == 'a-u'",
    "predicateLang": "JSON_PATH",
}


@pytest.mark.asyncio
async def test_get_data_feeds() -> None:
    """get_data_feeds unwraps the feed list"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert method == "get"
        assert url.endswith("/Marti/api/datafeeds")
        return 200, envelope([{"name": "feed-a"}])

    api, _ = make_api(handler)
    status, feeds = await api.get_data_feeds()
    assert status == 200
    assert feeds == [{"name": "feed-a"}]


@pytest.mark.asyncio
async def test_get_data_feeds_in_bbox() -> None:
    """get_data_feeds_in_bbox passes the bbox path segment"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/datafeeds/bounds/23.7,61.4,23.8,61.5")
        return 200, envelope([])

    api, _ = make_api(handler)
    status, feeds = await api.get_data_feeds_in_bbox("23.7,61.4,23.8,61.5")
    assert status == 200
    assert feeds == []


@pytest.mark.asyncio
async def test_get_data_feeds_in_polygon_sends_json_body() -> None:
    """get_data_feeds_in_polygon is a GET with a JSON array body"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert method == "get"
        assert url.endswith("/Marti/api/datafeeds/bounds/polygon")
        assert json == ["61.4,23.7", "61.5,23.7", "61.5,23.8"]
        return 200, envelope(["feed-a"])

    api, _ = make_api(handler)
    status, feeds = await api.get_data_feeds_in_polygon(["61.4,23.7", "61.5,23.7", "61.5,23.8"])
    assert status == 200
    assert feeds == ["feed-a"]


@pytest.mark.asyncio
async def test_create_predicate_data_feed() -> None:
    """create posts the feed body and unwraps the created object"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert method == "post"
        assert url.endswith("/Marti/api/datafeeds/predicate")
        assert json["name"] == "feed-a"
        return 200, envelope({"uuid": "uuid-1", "name": "feed-a"})

    api, _ = make_api(handler)
    status, feed = await api.create_predicate_data_feed(FEED_BODY)
    assert status == 200
    assert feed["uuid"] == "uuid-1"


@pytest.mark.asyncio
async def test_update_predicate_data_feed() -> None:
    """update sends the body via PUT with updateGroups flag"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert method == "put"
        assert url.endswith("/Marti/api/datafeeds/predicate?updateGroups=false")
        assert json["name"] == "feed-a"
        return 200, envelope({"uuid": "uuid-1", "name": "feed-a"})

    api, _ = make_api(handler)
    status, _ = await api.update_predicate_data_feed(FEED_BODY | {"uuid": "uuid-1"})
    assert status == 200


@pytest.mark.asyncio
async def test_update_predicate_data_feed_update_groups() -> None:
    """update_groups=True lands in the query string"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/datafeeds/predicate?updateGroups=true")
        return 200, envelope({})

    api, _ = make_api(handler)
    status, _ = await api.update_predicate_data_feed(FEED_BODY | {"uuid": "u"}, update_groups=True)
    assert status == 200


@pytest.mark.asyncio
async def test_get_predicate_data_feed() -> None:
    """get_predicate_data_feed builds the uuid path"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/datafeeds/predicate/uuid-9")
        return 200, envelope({"uuid": "uuid-9"})

    api, _ = make_api(handler)
    status, feed = await api.get_predicate_data_feed("uuid-9")
    assert status == 200
    assert feed["uuid"] == "uuid-9"


@pytest.mark.asyncio
async def test_delete_predicate_data_feed() -> None:
    """delete uses the predicate/{guid} path"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert method == "delete"
        assert url.endswith("/Marti/api/datafeeds/predicate/uuid-9")
        return 200, envelope({})

    api, _ = make_api(handler)
    status, _ = await api.delete_predicate_data_feed("uuid-9")
    assert status == 200


@pytest.mark.asyncio
async def test_get_stats() -> None:
    """get_stats returns the list of per-feed statistics"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/datafeeds/stats")
        return 200, envelope([{"dataFeedNumMessages": 5}])

    api, _ = make_api(handler)
    status, stats = await api.get_stats()
    assert status == 200
    assert stats[0]["dataFeedNumMessages"] == 5


@pytest.mark.asyncio
async def test_get_stats_for_feed() -> None:
    """get_stats_for_feed addresses one feed by uuid"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/datafeeds/stats/uuid-9")
        return 200, {"version": "3", "type": "...DataFeedStats...", "data": None}

    api, _ = make_api(handler)
    status, stats = await api.get_stats_for_feed("uuid-9")
    assert status == 200
    assert stats is None  # envelope without payload passes through as None


@pytest.mark.asyncio
async def test_get_existing_cot_types() -> None:
    """get_existing_cot_types hits the cots_types path"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/datafeeds/uuid-9/cots_types")
        return 200, envelope(["a-u-A", "a-u-G"])

    api, _ = make_api(handler)
    status, types = await api.get_existing_cot_types("uuid-9")
    assert status == 200
    assert types == ["a-u-A", "a-u-G"]


@pytest.mark.asyncio
async def test_get_cots_by_cot_type() -> None:
    """get_cots_by_cot_type builds the cots/{type} path"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/datafeeds/uuid-9/cots/a-u-A")
        return 200, envelope(["<event .../>"])

    api, _ = make_api(handler)
    status, cots = await api.get_cots_by_cot_type("uuid-9", "a-u-A")
    assert status == 200
    assert cots == ["<event .../>"]


@pytest.mark.asyncio
async def test_build_predicate_feed_defaults() -> None:
    """build_predicate_feed fills required fields and safe filter groups"""
    from python_takserver_api.tak_data_feed_api import DataFeedApi

    feed = DataFeedApi.build_predicate_feed("my-feed", "type == 'a-u'")
    assert feed["name"] == "my-feed"
    assert feed["predicate"] == "type == 'a-u'"
    assert feed["predicateLang"] == "JSON_PATH"
    assert feed["filterGroups"] == ["__ANON__"]  # avoids the access lockout
    assert feed["authType"] == "ANONYMOUS"
    assert feed["archive"] is False  # safe default: archiving bloats Postgres
    assert feed["sync"] is False

    feed_archived = DataFeedApi.build_predicate_feed("x", "p", archive=True)
    assert feed_archived["archive"] is True

    feed2 = DataFeedApi.build_predicate_feed("x", "p", auth_type="X_509", filter_groups=["MY_GROUP"])
    assert feed2["filterGroups"] == ["MY_GROUP"]
