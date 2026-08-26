"""Tests for ConnectionHelper, SSL context creation and Server lifecycle"""

import asyncio
import shutil
import ssl
import subprocess
from typing import Any

import aiohttp
import pytest

from python_takserver_api.class_helpers import ConnectionHelper, create_client_ssl_context
from python_takserver_api.tak_class import Server

OPENSSL = shutil.which("openssl")


def _generate_keypair(tmp_path: Any, cn: str = "localhost") -> tuple[str, str]:
    """Generates a throwaway self-signed keypair for SSL context tests"""
    assert OPENSSL is not None
    cert = tmp_path / "test.pem"
    key = tmp_path / "test.key"
    subprocess.run(
        [
            OPENSSL,
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-days",
            "1",
            "-nodes",
            "-subj",
            f"/CN={cn}",
        ],
        check=True,
        capture_output=True,
    )
    return str(cert), str(key)


def _generate_ca_signed_keypair(tmp_path: Any, cn: str = "takserver.local") -> tuple[str, str, str]:
    """Generates a throwaway CA plus a server keypair signed by it.

    Returns (ca_pem, server_cert, server_key) paths.
    """
    assert OPENSSL is not None
    ca_cert = tmp_path / "ca.pem"
    ca_key = tmp_path / "ca.key"
    subprocess.run(
        [
            OPENSSL,
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-keyout",
            str(ca_key),
            "-out",
            str(ca_cert),
            "-days",
            "1",
            "-nodes",
            "-subj",
            "/CN=test-ca",
            "-addext",
            "basicConstraints=critical,CA:TRUE",
            "-addext",
            "keyUsage=critical,keyCertSign,cRLSign",
        ],
        check=True,
        capture_output=True,
    )
    srv_key = tmp_path / "srv.key"
    srv_csr = tmp_path / "srv.csr"
    srv_cert = tmp_path / "srv.pem"
    subprocess.run(
        [
            OPENSSL,
            "req",
            "-new",
            "-newkey",
            "rsa:2048",
            "-keyout",
            str(srv_key),
            "-out",
            str(srv_csr),
            "-nodes",
            "-subj",
            f"/CN={cn}",
        ],
        check=True,
        capture_output=True,
    )
    ext = tmp_path / "ext.cnf"
    ext.write_text(
        "subjectAltName=DNS:takserver.local\n"
        "basicConstraints=CA:FALSE\n"
        "keyUsage=critical,digitalSignature,keyEncipherment\n"
        "extendedKeyUsage=serverAuth\n"
    )
    subprocess.run(
        [
            OPENSSL,
            "x509",
            "-req",
            "-in",
            str(srv_csr),
            "-CA",
            str(ca_cert),
            "-CAkey",
            str(ca_key),
            "-CAcreateserial",
            "-out",
            str(srv_cert),
            "-days",
            "1",
            "-extfile",
            str(ext),
        ],
        check=True,
        capture_output=True,
    )
    return str(ca_cert), str(srv_cert), str(srv_key)


def _make_helper() -> tuple[ConnectionHelper, Any]:
    class MockResponse:  # noqa: N801
        status = 200
        content_type = "application/json"

        async def json(self) -> Any:
            return {}

        async def text(self) -> str:
            return "{}"

    class MockSession:  # noqa: N801
        async def get(self, url: str, headers: Any = None, json: Any = None) -> MockResponse:
            return MockResponse()

    class MockServer:  # noqa: N801
        session: Any = MockSession()

    server = MockServer()
    return ConnectionHelper(server, "cert.pem", "key.pem"), server


@pytest.mark.asyncio
async def test_request_rejects_unknown_http_method() -> None:
    """request raises ValueError for unsupported methods instead of crashing"""
    helper, _ = _make_helper()
    with pytest.raises(ValueError, match="unsupported HTTP method"):
        await helper.request("patch", "https://tak.example.com:8443/x")


@pytest.mark.asyncio
async def test_request_returns_json_on_success() -> None:
    """request returns (status, parsed json) on a happy path"""
    helper, _ = _make_helper()
    status, payload = await helper.request("get", "https://tak.example.com:8443/x")
    assert status == 200
    assert payload == {}


@pytest.mark.skipif(OPENSSL is None, reason="openssl not available")
def test_create_client_ssl_context_loads_keypair(tmp_path: Any) -> None:
    """create_client_ssl_context loads the client cert and disables server verification"""
    cert, key = _generate_keypair(tmp_path)
    sslcontext = create_client_ssl_context(cert, key)
    assert isinstance(sslcontext, ssl.SSLContext)
    assert sslcontext.verify_mode == ssl.CERT_NONE  # deliberate: TAK servers are self-signed
    assert sslcontext.check_hostname is False


@pytest.mark.skipif(OPENSSL is None, reason="openssl not available")
@pytest.mark.asyncio
async def test_get_ssl_context_builds_connector_from_real_keypair(tmp_path: Any) -> None:
    """get_ssl_context wraps the client SSL context in a TCPConnector"""
    cert, key = _generate_keypair(tmp_path)
    helper = ConnectionHelper(object(), cert, key)  # noqa: B902
    connector = helper.get_ssl_context()
    try:
        assert isinstance(connector, aiohttp.TCPConnector)
    finally:
        await connector.close()


def _run_tls_handshake(srv_cert: str, srv_key: str, ca_file: str) -> None:
    """Runs a real TLS handshake against an in-loop TLS server.

    The server presents `(srv_cert, srv_key)`; the client side uses
    `create_client_ssl_context()` pinning `ca_file`. Raises `ssl.SSLError`
    when the server certificate does not verify against that CA.
    """
    server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_ctx.load_cert_chain(certfile=srv_cert, keyfile=srv_key)
    client_ctx = create_client_ssl_context(srv_cert, srv_key, ca_file=ca_file)

    async def run() -> None:
        server = await asyncio.start_server(lambda r, w: None, "127.0.0.1", 0, ssl=server_ctx)
        port = server.sockets[0].getsockname()[1]
        try:

            async def client() -> None:
                await asyncio.sleep(0.05)
                _, writer = await asyncio.open_connection(
                    "127.0.0.1", port, ssl=client_ctx, server_hostname="takserver.local"
                )
                writer.close()

            async with server:
                await asyncio.wait_for(client(), timeout=5)

        finally:
            server.close()

    asyncio.run(run())


@pytest.mark.skipif(OPENSSL is None, reason="openssl not available")
def test_create_client_ssl_context_with_ca_verifies_server(tmp_path: Any) -> None:
    """With a CA file the context enforces server certificate verification"""
    ca, srv_cert, srv_key = _generate_ca_signed_keypair(tmp_path)
    sslcontext = create_client_ssl_context(srv_cert, srv_key, ca_file=ca)
    assert sslcontext.verify_mode == ssl.CERT_REQUIRED
    assert sslcontext.check_hostname is True


@pytest.mark.skipif(OPENSSL is None, reason="openssl not available")
def test_handshake_succeeds_with_pinned_ca(tmp_path: Any) -> None:
    """The handshake succeeds when the server CA is pinned"""
    ca, srv_cert, srv_key = _generate_ca_signed_keypair(tmp_path)
    _run_tls_handshake(srv_cert, srv_key, ca)


@pytest.mark.skipif(OPENSSL is None, reason="openssl not available")
def test_handshake_fails_with_foreign_ca(tmp_path: Any) -> None:
    """The handshake fails when a foreign self-signed cert is pinned as CA"""
    ca, srv_cert, srv_key = _generate_ca_signed_keypair(tmp_path)
    foreign_dir = tmp_path / "foreign"
    foreign_dir.mkdir()
    foreign_cert, _foreign_key = _generate_keypair(foreign_dir)
    with pytest.raises(ssl.SSLError):
        _run_tls_handshake(srv_cert, srv_key, foreign_cert)


@pytest.mark.asyncio
async def test_server_close_closes_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """Server.close closes the underlying aiohttp session"""

    closed: list[bool] = []

    class FakeSession:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def close(self) -> None:
            closed.append(True)

    class FakeTCPConnector:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    monkeypatch.setattr(aiohttp, "ClientSession", FakeSession)
    monkeypatch.setattr(aiohttp, "TCPConnector", FakeTCPConnector)
    monkeypatch.setattr(ConnectionHelper, "get_ssl_context", lambda self: FakeTCPConnector())

    server = Server("tak.example.com", "cert.pem", "key.pem")
    assert closed == []
    await server.close()
    assert closed == [True]


@pytest.mark.asyncio
async def test_server_passes_ca_cert_to_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Server(..., ca_cert=...) forwards the CA to the connection helper"""

    class FakeSession:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    class FakeTCPConnector:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    monkeypatch.setattr(aiohttp, "ClientSession", FakeSession)
    monkeypatch.setattr(aiohttp, "TCPConnector", FakeTCPConnector)
    monkeypatch.setattr(ConnectionHelper, "get_ssl_context", lambda self: FakeTCPConnector())

    server = Server("tak.example.com", "cert.pem", "key.pem", ca_cert="ca.pem")
    assert server.connection.ca_cert == "ca.pem"
    server_default = Server("tak.example.com", "cert.pem", "key.pem")
    assert server_default.connection.ca_cert is None
