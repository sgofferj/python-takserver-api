"""Tests for the Certificate Manager (admin) API"""

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
    return {"version": "3", "type": "...Cert...", "data": data}


def make_api(handler: Any) -> tuple[Any, MockServer]:
    from python_takserver_api.tak_cert_manager_api import CertManagerApi

    server = MockServer()
    server.connection = MockConnection(handler)
    return CertManagerApi(server), server


def ok(data: Any):
    async def handler(method: str, url: str, headers: Any, json: Any, data_: Any) -> tuple[int, Any]:
        assert method == "get"
        return 200, envelope(data)

    return handler


CERT = {"hash": "AB:CD", "subjectDn": "CN=user1"}


@pytest.mark.asyncio
async def test_get_certificates() -> None:
    """get_certificates returns the unwrapped certificate list"""
    api, _ = make_api(ok([CERT]))
    status, certs = await api.get_certificates()
    assert status == 200
    assert certs == [CERT]


@pytest.mark.asyncio
async def test_get_certificates_username_filter() -> None:
    """get_certificates passes the optional username filter"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/certadmin/cert?username=op1")
        return 200, envelope([CERT])

    api, _ = make_api(handler)
    status, certs = await api.get_certificates(username="op1")
    assert status == 200
    assert len(certs) == 1


@pytest.mark.parametrize(
    "endpoint,method_suffix",
    [
        ("active", "/Marti/api/certadmin/cert/active"),
        ("expired", "/Marti/api/certadmin/cert/expired"),
        ("replaced", "/Marti/api/certadmin/cert/replaced"),
        ("revoked", "/Marti/api/certadmin/cert/revoked"),
    ],
)
@pytest.mark.asyncio
async def test_get_certificate_collections(endpoint: str, method_suffix: str) -> None:
    """active/expired/replaced/revoked hit their dedicated endpoints"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith(method_suffix)
        return 200, envelope([CERT])

    api, _ = make_api(handler)
    method = getattr(api, f"get_{endpoint}_certificates")
    status, certs = await method()
    assert status == 200
    assert certs == [CERT]


@pytest.mark.asyncio
async def test_get_certificate_by_hash() -> None:
    """get_certificate addresses one record by hash"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/certadmin/cert/AB:CD")
        return 200, envelope(CERT)

    api, _ = make_api(handler)
    status, cert = await api.get_certificate("AB:CD")
    assert status == 200
    assert cert["hash"] == "AB:CD"


@pytest.mark.asyncio
async def test_download_certificate_returns_pem_text() -> None:
    """download_certificate returns the raw PEM text (not an envelope)"""
    pem = "-----BEGIN CERTIFICATE-----\nabc\n-----END CERTIFICATE-----"

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/certadmin/cert/AB:CD/download")
        return 200, pem

    api, _ = make_api(handler)
    status, body = await api.download_certificate("AB:CD")
    assert status == 200
    assert body.startswith("-----BEGIN CERTIFICATE-----")


@pytest.mark.asyncio
async def test_delete_certificate() -> None:
    """delete_certificate uses DELETE on the hash path"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert method == "delete"
        assert url.endswith("/Marti/api/certadmin/cert/AB:CD")
        return 200, envelope({})

    api, _ = make_api(handler)
    status, _ = await api.delete_certificate("AB:CD")
    assert status == 200


@pytest.mark.asyncio
async def test_delete_certificates_joins_ids() -> None:
    """delete_certificates accepts a list and joins it with commas"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/certadmin/cert/delete/AA,BB,CC")
        return 200, envelope({})

    api, _ = make_api(handler)
    status, _ = await api.delete_certificates(["AA", "BB", "CC"])
    assert status == 200


@pytest.mark.asyncio
async def test_delete_certificates_accepts_single_string() -> None:
    """delete_certificates passes a single string through unchanged"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/certadmin/cert/delete/AA")
        return 200, envelope({})

    api, _ = make_api(handler)
    status, _ = await api.delete_certificates("AA")
    assert status == 200


@pytest.mark.asyncio
async def test_revoke_certificates() -> None:
    """revoke_certificates uses the revoke/{ids} path"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert method == "delete"
        assert url.endswith("/Marti/api/certadmin/cert/revoke/AA,BB")
        return 200, envelope({})

    api, _ = make_api(handler)
    status, _ = await api.revoke_certificates(["AA", "BB"])
    assert status == 200


@pytest.mark.asyncio
async def test_get_active_certificates() -> None:
    """get_active_certificates hits the /active endpoint and unwraps"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/certadmin/cert/active")
        return 200, envelope([CERT])

    api, _ = make_api(handler)
    status, certs = await api.get_active_certificates()
    assert status == 200
    assert certs[0]["hash"] == "AB:CD"


@pytest.mark.asyncio
async def test_get_expired_certificates() -> None:
    """get_expired_certificates hits the /expired endpoint"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/certadmin/cert/expired")
        return 200, envelope([])

    api, _ = make_api(handler)
    status, certs = await api.get_expired_certificates()
    assert status == 200
    assert certs == []


@pytest.mark.asyncio
async def test_get_replaced_certificates() -> None:
    """get_replaced_certificates hits the /replaced endpoint"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/certadmin/cert/replaced")
        return 200, envelope([])

    api, _ = make_api(handler)
    status, certs = await api.get_replaced_certificates()
    assert status == 200
    assert certs == []


@pytest.mark.asyncio
async def test_get_revoked_certificates() -> None:
    """get_revoked_certificates hits the /revoked endpoint"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.endswith("/Marti/api/certadmin/cert/revoked")
        return 200, envelope([{**CERT, "revocationDate": "2026-01-01"}])

    api, _ = make_api(handler)
    status, certs = await api.get_revoked_certificates()
    assert status == 200
    assert certs[0]["revocationDate"] == "2026-01-01"
