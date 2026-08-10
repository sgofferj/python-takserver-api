"""Live tests against a real TAK server - local machine only.

Run locally only:  poetry run pytest live_tests/ -m live
NEVER in CI. Never modify or delete pre-existing server data - only touch
data that these tests create themselves.
"""

import pytest

pytestmark = pytest.mark.live


@pytest.mark.asyncio
async def test_is_admin(server) -> None:
    """The local admin certificate must be recognized as admin."""
    assert await server.home.is_admin() is True


@pytest.mark.asyncio
async def test_version(server) -> None:
    """The version endpoint answers with a TAK release string."""
    status, data = await server.connection.request(
        "get",
        f"{server.api_base_url}/Marti/api/version",
        headers={"Content-Type": "application/json"},
    )
    assert status == 200
    assert "RELEASE" in str(data)


@pytest.mark.asyncio
async def test_home_get_home(server) -> None:
    """GET /Marti/api/home answers with the home payload."""
    status, data = await server.home.get_home()
    assert status == 200


@pytest.mark.asyncio
async def test_home_get_user_roles(server) -> None:
    """The admin certificate sees its own roles, including ROLE_ADMIN."""
    status, data = await server.home.get_user_roles()
    assert status == 200
    assert isinstance(data, list)
    assert "ROLE_ADMIN" in data


@pytest.mark.asyncio
async def test_home_has_role(server) -> None:
    """has_role reports the admin role for the admin certificate."""
    assert await server.home.has_role("ROLE_ADMIN") is True
    assert await server.home.has_role("ROLE_NONEXISTENT") is False


@pytest.mark.asyncio
async def test_home_server_version(server) -> None:
    """server_version returns the TAK release string."""
    version = await server.home.server_version()
    assert version is not None
    assert "RELEASE" in version


@pytest.mark.asyncio
async def test_home_ver_endpoint_not_wrapped(server) -> None:
    """/Marti/api/ver is NOT wrapped because it returns HTTP 500 on the live server.

    See docs (Home-API wiki page). This test documents the server-side
    failure so it is noticed if a server upgrade ever fixes the endpoint.
    """
    status, _ = await server.connection.request(
        "get",
        f"{server.api_base_url}/Marti/api/ver",
        headers={"Content-Type": "application/json"},
    )
    assert status == 500
