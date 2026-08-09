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
