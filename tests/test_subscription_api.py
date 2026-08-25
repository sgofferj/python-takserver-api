"""Tests for the Subscription API"""

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
    from python_takserver_api.tak_subscription_api import SubscriptionApi

    server = MockServer()
    server.connection = MockConnection(handler)
    return SubscriptionApi(server), server


SUB = {"clientUid": "UID-1", "callsign": "cs1", "incognito": False}


@pytest.mark.asyncio
async def test_get_all_subscriptions() -> None:
    """get_all_subscriptions unwraps the subscription list"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/subscriptions/all")
        return 200, envelope([SUB])

    api, _ = make_api(handler)
    status, subs = await api.get_all_subscriptions()
    assert status == 200
    assert subs == [SUB]


@pytest.mark.asyncio
async def test_get_subscription() -> None:
    """get_subscription builds the singular path"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/subscription/UID-1")
        return 200, envelope(SUB)

    api, _ = make_api(handler)
    status, sub = await api.get_subscription("UID-1")
    assert status == 200
    assert sub["clientUid"] == "UID-1"


@pytest.mark.asyncio
async def test_add_static_subscription() -> None:
    """add_static_subscription posts the tmpStaticSub body"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/subscriptions/add")
        assert json["uid"] == "static-1"
        assert json["subaddr"] == "127.0.0.1"
        return 200, envelope({})

    api, _ = make_api(handler)
    status, _ = await api.add_static_subscription({"uid": "static-1", "subaddr": "127.0.0.1", "subport": "8087"})
    assert status == 200


@pytest.mark.asyncio
async def test_delete_subscription() -> None:
    """delete_subscription uses DELETE with the uid path"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert method == "delete"
        assert url.endswith("/Marti/api/subscriptions/delete/static-1")
        return 200, envelope({})

    api, _ = make_api(handler)
    status, _ = await api.delete_subscription("static-1")
    assert status == 200


@pytest.mark.asyncio
async def test_toggle_incognito() -> None:
    """toggle_incognito POSTs to the incognito path"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert method == "post"
        assert url.endswith("/Marti/api/subscriptions/incognito/UID-1")
        return 200, envelope({})

    api, _ = make_api(handler)
    status, _ = await api.toggle_incognito("UID-1")
    assert status == 200


@pytest.mark.asyncio
async def test_set_filter_sends_xml_body() -> None:
    """set_filter PUTs raw XML with an XML content type"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert method == "put"
        assert url.endswith("/Marti/api/subscriptions/UID-1/filter")
        assert headers["Content-Type"] == "application/xml"
        assert data == "<filter/>"
        return 200, envelope({})

    api, _ = make_api(handler)
    status, _ = await api.set_filter("UID-1", "<filter/>")
    assert status == 200


@pytest.mark.asyncio
async def test_delete_filter() -> None:
    """delete_filter DELETEs the filter path"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert method == "delete"
        assert url.endswith("/Marti/api/subscriptions/UID-1/filter")
        return 200, envelope({})

    api, _ = make_api(handler)
    status, _ = await api.delete_filter("UID-1")
    assert status == 200


@pytest.mark.asyncio
async def test_bulk_groups_updated() -> None:
    """bulk_groups_updated POSTs the username list"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert method == "post"
        assert url.endswith("/Marti/api/groups/update")
        assert json == ["user-a", "user-b"]
        return 200, envelope(True)

    api, _ = make_api(handler)
    status, result = await api.bulk_groups_updated(["user-a", "user-b"])
    assert status == 200
    assert result is True
