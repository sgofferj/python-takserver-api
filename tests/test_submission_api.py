"""Tests for the Submission API (CoT inputs, messaging config)"""

from typing import Any

import pytest


class MockConnection:
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
    return {"version": "3", "type": "...", "data": data}


def make_api(handler: Any) -> tuple[Any, MockServer]:
    from python_takserver_api.tak_submission_api import SubmissionApi

    server = MockServer()
    server.connection = MockConnection(handler)
    return SubmissionApi(server), server


INPUT_BODY = {"name": "in-a", "protocol": "tls", "port": 8089}


@pytest.mark.asyncio
async def test_get_input_metrics() -> None:
    """get_input_metrics unwraps the metrics list"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/inputs")
        return 200, envelope([{"id": "1"}])

    api, _ = make_api(handler)
    status, metrics = await api.get_input_metrics()
    assert status == 200
    assert metrics == [{"id": "1"}]


@pytest.mark.asyncio
async def test_get_input_metrics_exclude_data_feeds() -> None:
    """exclude_data_feeds lands in the query string"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/inputs?excludeDataFeeds=true")
        return 200, envelope([])

    api, _ = make_api(handler)
    status, _ = await api.get_input_metrics(exclude_data_feeds=True)
    assert status == 200


@pytest.mark.asyncio
async def test_get_input_metric() -> None:
    """get_input_metric addresses one input by name"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/inputs/stdssl")
        return 200, envelope({"id": "1"})

    api, _ = make_api(handler)
    status, metric = await api.get_input_metric("stdssl")
    assert status == 200
    assert metric["id"] == "1"


@pytest.mark.asyncio
async def test_create_and_modify_and_delete_input() -> None:
    """create uses POST, modify PUT by id, delete DELETE by name"""
    calls: list[tuple[str, str]] = []

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        calls.append((method, url))
        if method == "post":
            assert json == INPUT_BODY
            return 200, envelope(INPUT_BODY)
        if method == "put":
            assert "/Marti/api/inputs/id-9" in url and json["name"] == "in-a"
            return 200, envelope({})
        assert method == "delete"
        assert url.endswith("/Marti/api/inputs/in-a")
        return 200, envelope({})

    api, _ = make_api(handler)
    await api.create_input(INPUT_BODY)
    await api.modify_input("id-9", INPUT_BODY)
    status, _ = await api.delete_input("in-a")
    assert status == 200
    assert ("post", "https://tak.example.com:8443/Marti/api/inputs") in calls


@pytest.mark.asyncio
async def test_data_feed_by_name_crud() -> None:
    """create/get/modify/delete for the named streaming feed registry"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        if method == "post":
            assert url.endswith("/Marti/api/datafeeds")
            return 200, envelope({"name": "df"})
        if method == "get":
            assert url.endswith("/Marti/api/datafeeds/df")
            return 200, envelope({"name": "df"})
        if method == "put":
            assert url.endswith("/Marti/api/datafeeds/df")
            return 200, envelope({})
        assert method == "delete"
        return 200, envelope({})

    api, _ = make_api(handler)
    assert (await api.create_data_feed({"name": "df"}))[0] == 200
    assert (await api.get_data_feed("df"))[0] == 200
    assert (await api.modify_data_feed("df", {"name": "df"}))[0] == 200
    assert (await api.delete_data_feed("df"))[0] == 200


@pytest.mark.asyncio
async def test_config_info_roundtrip() -> None:
    """get_config_info reads; modify_config_info PUTs the full object"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/inputs/config")
        if method == "get":
            return 200, envelope({"numDbConnections": 16})
        assert method == "put"
        assert json == {"numDbConnections": 32}
        return 200, envelope({})

    api, _ = make_api(handler)
    status, cfg = await api.get_config_info()
    assert status == 200
    assert cfg["numDbConnections"] == 16
    status, _ = await api.modify_config_info({"numDbConnections": 32})
    assert status == 200


@pytest.mark.asyncio
async def test_store_forward_chat_toggle() -> None:
    """enable/disable hit the dedicated toggle endpoints"""
    seen: list[str] = []

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        if url.endswith("/storeForwardChat/enabled"):
            return 200, envelope(True)
        assert method == "put"
        seen.append(url.rsplit("/", 1)[-1])
        return 200, envelope({})

    api, _ = make_api(handler)
    status, enabled = await api.is_store_forward_chat_enabled()
    assert status == 200 and enabled is True
    await api.disable_store_forward_chat()
    await api.enable_store_forward_chat()
    assert seen == ["disable", "enable"]


@pytest.mark.asyncio
async def test_get_database_cot_counts() -> None:
    """get_database_cot_counts returns the counter payload"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/database/cotCount")
        return 200, envelope({"cotEvents": 5, "cotImages": 0})

    api, _ = make_api(handler)
    status, counts = await api.get_database_cot_counts()
    assert status == 200
    assert counts["cotEvents"] == 5
