"""Live tests against a real TAK server - local machine only.

Run locally only:  poetry run pytest live_tests/ -m live
NEVER in CI. Never modify or delete pre-existing server data - only touch
data that these tests create themselves.
"""

import uuid

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


@pytest.mark.asyncio
async def test_user_api_get_users_in_group(server) -> None:
    """get_users_in_group returns the group with its members for an existing group."""
    status, data = await server.user.get_users_in_group("__ANONYMOUS__")
    assert status == 200
    assert data["groupname"] == "__ANONYMOUS__"
    assert isinstance(data["usersInGroupList"], list)


@pytest.mark.asyncio
async def test_user_api_get_groups_for_user(server) -> None:
    """get_groups_for_user returns the group model for the admin user."""
    status, data = await server.user.get_groups_for_user("sgofferj")
    assert status == 200
    assert data["username"] == "sgofferj"
    assert isinstance(data["groupList"], list)


@pytest.mark.asyncio
async def test_user_api_full_lifecycle(server) -> None:
    """Create, read, update and delete a dedicated live-test user.

    Never touches pre-existing server data: the user is created with a
    unique name, exercised, and deleted again in the same test.
    """
    username = f"live-test-{uuid.uuid4()}"
    password = "Live-Test-Pw-9!"  # pragma: allowlist secret
    try:
        # create (group lists are always sent - omitting them is a server 500)
        status, _ = await server.user.create_or_update_file_user(username=username, password=password)
        assert status == 200 or status == 201
        assert await server.user.user_exists(username) is True

        # change password
        status, _ = await server.user.change_user_password(username, "Live-Test-Pw-8!")  # pragma: allowlist secret
        assert status == 200

        # bulk-created users (dedicated names) can be listed; the bulk
        # endpoint requires a non-empty group list (400 otherwise)
        status, _ = await server.user.create_file_users_in_bulk(
            username_expression=f"{username}-bulk-[N]",
            start_n=1,
            end_n=2,
            group_list=["__ANONYMOUS__"],
        )
        assert status == 200
        for n in (1, 2):
            assert await server.user.user_exists(f"{username}-bulk-{n}") is True

        # groups membership roundtrip on our own user
        status, _ = await server.user.update_groups_for_user(username, group_list=[])
        assert status == 200
        status, data = await server.user.get_groups_for_user(username)
        assert status == 200
        assert data["username"] == username
    finally:
        for n in (1, 2):
            bulk_name = f"{username}-bulk-{n}"
            if await server.user.user_exists(bulk_name):
                status, _ = await server.user.delete_user(bulk_name)
                assert status == 200
        if await server.user.user_exists(username):
            status, _ = await server.user.delete_user(username)
            assert status == 200
            assert await server.user.user_exists(username) is False
