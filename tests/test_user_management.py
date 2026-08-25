"""Tests for the User Account Management API"""

from typing import Any

import pytest


@pytest.mark.asyncio
async def test_create_or_update_file_user() -> None:
    """create_or_update_file_user sends username + password"""
    from python_takserver_api.tak_file_user_account_management_api import UserAccountManagementApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert method == "post"
            assert "/user-management/api/new-user" in url
            assert json is not None
            assert json["username"] == "op1"
            assert json["password"] == "hunter2"  # pragma: allowlist secret
            assert json["groupList"] == []
            assert json["groupListIN"] == []
            assert json["groupListOUT"] == []
            return 201, {"username": "op1"}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        user_management_base: str = "/user-management/api"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    status, data = await api.create_or_update_file_user(
        username="op1",
        password="hunter2",  # pragma: allowlist secret
    )
    assert status == 201


@pytest.mark.asyncio
async def test_create_or_update_user_with_groups() -> None:
    """create_or_update_file_user with all group params"""
    from python_takserver_api.tak_file_user_account_management_api import UserAccountManagementApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert json is not None
            assert json["groupListIN"] == ["writers"]
            assert json["groupListOUT"] == ["readers"]
            assert json["groupList"] == ["both"]
            return 201, {"username": "op2"}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        user_management_base: str = "/user-management/api"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    status, data = await api.create_or_update_file_user(
        username="op2",
        password="hunter2",  # pragma: allowlist secret
        group_list_in=["writers"],
        group_list_out=["readers"],
        group_list_both=["both"],
    )
    assert status == 201


@pytest.mark.asyncio
async def test_get_all_users() -> None:
    """get_all_users returns user list"""
    from python_takserver_api.tak_file_user_account_management_api import UserAccountManagementApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert "/list-users" in url
            return 200, [{"username": "op1"}, {"username": "op2"}]

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        user_management_base: str = "/user-management/api"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    status, data = await api.get_all_users()
    assert status == 200
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_all_group_names() -> None:
    """get_all_group_names returns group list"""
    from python_takserver_api.tak_file_user_account_management_api import UserAccountManagementApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert "/list-groupnames" in url
            return 200, [{"groupname": "admins"}, {"groupname": "users"}]

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        user_management_base: str = "/user-management/api"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    status, data = await api.get_all_group_names()
    assert status == 200
    assert len(data) == 2


@pytest.mark.asyncio
async def test_user_exists_true() -> None:
    """user_exists returns True when user is found"""
    from python_takserver_api.tak_file_user_account_management_api import UserAccountManagementApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            return 200, [{"username": "op1"}, {"username": "op2"}]

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        user_management_base: str = "/user-management/api"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    assert await api.user_exists("op1") is True
    assert await api.user_exists("op2") is True


@pytest.mark.asyncio
async def test_user_exists_false() -> None:
    """user_exists returns False when user is not found"""
    from python_takserver_api.tak_file_user_account_management_api import UserAccountManagementApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            return 200, [{"username": "op1"}]

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        user_management_base: str = "/user-management/api"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    assert await api.user_exists("nonexistent") is False


@pytest.mark.asyncio
async def test_group_exists_true() -> None:
    """group_exists returns True when group is found"""
    from python_takserver_api.tak_file_user_account_management_api import UserAccountManagementApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            return 200, [{"groupname": "admins"}, {"groupname": "users"}]

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        user_management_base: str = "/user-management/api"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    assert await api.group_exists("admins") is True


@pytest.mark.asyncio
async def test_group_exists_false() -> None:
    """group_exists returns False when group is not found"""
    from python_takserver_api.tak_file_user_account_management_api import UserAccountManagementApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            return 200, [{"groupname": "admins"}]

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        user_management_base: str = "/user-management/api"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    assert await api.group_exists("ghost") is False


@pytest.mark.asyncio
async def test_get_users_in_group() -> None:
    """get_users_in_group hits users-in-group with the group name"""
    from python_takserver_api.tak_file_user_account_management_api import UserAccountManagementApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert method == "get"
            assert url.endswith("/user-management/api/users-in-group/ops")
            return 200, {"groupname": "ops", "usersInGroupList": ["op1"]}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        user_management_base: str = "/user-management/api"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    status, data = await api.get_users_in_group("ops")
    assert status == 200
    assert data["groupname"] == "ops"


@pytest.mark.asyncio
async def test_get_groups_for_user() -> None:
    """get_groups_for_user hits get-groups-for-user with the username"""
    from python_takserver_api.tak_file_user_account_management_api import UserAccountManagementApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert method == "get"
            assert url.endswith("/user-management/api/get-groups-for-user/op1")
            return 200, {"username": "op1", "groupList": ["admins"]}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        user_management_base: str = "/user-management/api"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    status, data = await api.get_groups_for_user("op1")
    assert status == 200
    assert data["groupList"] == ["admins"]


@pytest.mark.asyncio
async def test_change_user_password() -> None:
    """change_user_password sends username + password to change-user-password"""
    from python_takserver_api.tak_file_user_account_management_api import UserAccountManagementApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert method == "put"
            assert url.endswith("/user-management/api/change-user-password")
            assert json == {
                "username": "op1",
                "password": "newpass",  # pragma: allowlist secret
            }
            return 200, None

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        user_management_base: str = "/user-management/api"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    status, _ = await api.change_user_password("op1", "newpass")  # pragma: allowlist secret
    assert status == 200


@pytest.mark.asyncio
async def test_delete_user() -> None:
    """delete_user hits delete-user with the username"""
    from python_takserver_api.tak_file_user_account_management_api import UserAccountManagementApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert method == "delete"
            assert url.endswith("/user-management/api/delete-user/op1")
            return 200, None

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        user_management_base: str = "/user-management/api"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    status, _ = await api.delete_user("op1")
    assert status == 200


@pytest.mark.asyncio
async def test_create_file_users_in_bulk() -> None:
    """create_file_users_in_bulk sends the bulk model to new-users"""
    from python_takserver_api.tak_file_user_account_management_api import UserAccountManagementApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert method == "post"
            assert url.endswith("/user-management/api/new-users")
            assert json == {
                "usernameExpression": "bulk-%n",
                "startN": 1,
                "endN": 3,
                "groupList": ["both"],
                "groupListIN": ["writers"],
                "groupListOUT": ["readers"],
            }
            return 200, [{"username": "bulk-1", "password": "pw1"}]  # pragma: allowlist secret

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        user_management_base: str = "/user-management/api"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    status, data = await api.create_file_users_in_bulk(
        username_expression="bulk-%n",
        start_n=1,
        end_n=3,
        group_list=["both"],
        group_list_in=["writers"],
        group_list_out=["readers"],
    )
    assert status == 200
    assert data[0]["username"] == "bulk-1"


@pytest.mark.asyncio
async def test_create_file_users_in_bulk_minimal() -> None:
    """create_file_users_in_bulk without groups sends only the core fields"""
    from python_takserver_api.tak_file_user_account_management_api import UserAccountManagementApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert json == {
                "usernameExpression": "bulk-%n",
                "startN": 4,
                "endN": 5,
                "groupList": [],
                "groupListIN": [],
                "groupListOUT": [],
            }
            return 200, []

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        user_management_base: str = "/user-management/api"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    status, data = await api.create_file_users_in_bulk("bulk-%n", 4, 5)
    assert status == 200
    assert data == []


@pytest.mark.asyncio
async def test_update_users_for_group() -> None:
    """update_users_for_group sends the group model to update-group-users"""
    from python_takserver_api.tak_file_user_account_management_api import UserAccountManagementApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert method == "put"
            assert url.endswith("/user-management/api/update-group-users")
            assert json == {
                "groupname": "admins",
                "usersInGroupList": ["op1", "op2"],
                "usersInGroupListIN": ["op3"],
                "usersInGroupListOUT": ["op4"],
            }
            return 200, None

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        user_management_base: str = "/user-management/api"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    status, _ = await api.update_users_for_group(
        groupname="admins",
        users_in_group_list=["op1", "op2"],
        users_in_group_list_in=["op3"],
        users_in_group_list_out=["op4"],
    )
    assert status == 200


@pytest.mark.asyncio
async def test_update_users_for_group_minimal() -> None:
    """update_users_for_group with no lists sends empty lists (server 500s otherwise)"""
    from python_takserver_api.tak_file_user_account_management_api import UserAccountManagementApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert json == {
                "groupname": "admins",
                "usersInGroupList": [],
                "usersInGroupListIN": [],
                "usersInGroupListOUT": [],
            }
            return 200, None

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        user_management_base: str = "/user-management/api"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    status, _ = await api.update_users_for_group("admins")
    assert status == 200


@pytest.mark.asyncio
async def test_update_groups_for_user() -> None:
    """update_groups_for_user sends the user model to update-groups"""
    from python_takserver_api.tak_file_user_account_management_api import UserAccountManagementApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert method == "put"
            assert url.endswith("/user-management/api/update-groups")
            assert json == {
                "username": "op1",
                "groupList": ["both"],
                "groupListIN": ["writers"],
                "groupListOUT": ["readers"],
            }
            return 200, None

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        user_management_base: str = "/user-management/api"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    status, _ = await api.update_groups_for_user(
        username="op1",
        group_list=["both"],
        group_list_in=["writers"],
        group_list_out=["readers"],
    )
    assert status == 200


@pytest.mark.asyncio
async def test_update_groups_for_user_minimal() -> None:
    """update_groups_for_user with no lists sends empty lists (server 500s otherwise)"""
    from python_takserver_api.tak_file_user_account_management_api import UserAccountManagementApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert json == {
                "username": "op1",
                "groupList": [],
                "groupListIN": [],
                "groupListOUT": [],
            }
            return 200, None

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        user_management_base: str = "/user-management/api"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    status, _ = await api.update_groups_for_user("op1")
    assert status == 200


def test_um_prefix_for_version() -> None:
    """5.8+ uses the Marti prefix, older/unknown versions the legacy one."""
    from python_takserver_api.tak_file_user_account_management_api import (
        PREFIX_LEGACY,
        PREFIX_MARTI,
        um_prefix_for_version,
    )

    assert um_prefix_for_version("5.7-RELEASE-43") == PREFIX_LEGACY
    assert um_prefix_for_version("5.6-RELEASE-1") == PREFIX_LEGACY
    assert um_prefix_for_version("5.8-RELEASE-66") == PREFIX_MARTI
    assert um_prefix_for_version("5.9-RELEASE-1") == PREFIX_MARTI
    assert um_prefix_for_version("6.0-RELEASE-1") == PREFIX_MARTI
    assert um_prefix_for_version(None) == PREFIX_LEGACY
    assert um_prefix_for_version("garbage") == PREFIX_LEGACY


@pytest.mark.asyncio
async def test_um_base_auto_detection_57() -> None:
    """On a 5.7 server the legacy prefix is detected and cached."""
    from python_takserver_api.tak_file_user_account_management_api import (
        PREFIX_LEGACY,
        UserAccountManagementApi,
    )

    class MockConnection:  # noqa: N801
        async def request(self, method, url, headers=None, json=None, data=None):
            if url.endswith("/Marti/api/version"):
                return 200, "5.7-RELEASE-43 HEAD ..."
            raise AssertionError(f"unexpected request {url}")

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    assert await api._base() == PREFIX_LEGACY  # noqa: SLF001
    assert await api._base() == PREFIX_LEGACY  # cached, no second probe


@pytest.mark.asyncio
async def test_um_base_auto_detection_58() -> None:
    """On a 5.8 server the Marti prefix is detected."""
    from python_takserver_api.tak_file_user_account_management_api import (
        PREFIX_MARTI,
        UserAccountManagementApi,
    )

    class MockConnection:  # noqa: N801
        async def request(self, method, url, headers=None, json=None, data=None):
            assert url.endswith("/Marti/api/version")
            return 200, "5.8-RELEASE-66 RELEASE"

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    status_url_used = []

    async def _spy_base():
        prefix = await api._base()
        status_url_used.append(prefix)
        return prefix

    assert await _spy_base() == PREFIX_MARTI

    # a full operation must use the detected prefix
    async def handler(method, url, headers=None, json=None, data=None):
        assert "/Marti/api/user-management/api/list-users" in url
        return 200, []

    api.server.connection = MockConnection()
    api.server.connection.request = handler  # type: ignore[method-assign]
    status, users = await api.get_all_users()
    assert status == 200


@pytest.mark.asyncio
async def test_um_base_detection_failure_falls_back_to_legacy() -> None:
    """If the version endpoint fails, the legacy prefix is used."""
    from python_takserver_api.tak_file_user_account_management_api import (
        PREFIX_LEGACY,
        UserAccountManagementApi,
    )

    class MockConnection:  # noqa: N801
        async def request(self, method, url, headers=None, json=None, data=None):
            if url.endswith("/Marti/api/version"):
                return 500, "boom"
            raise AssertionError(f"unexpected request {url}")

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    assert await api._base() == PREFIX_LEGACY


@pytest.mark.asyncio
async def test_um_base_explicit_override_wins() -> None:
    """A user_management_base attribute on the server overrides detection."""
    from python_takserver_api.tak_file_user_account_management_api import (
        UserAccountManagementApi,
    )

    class MockConnection:  # noqa: N801
        async def request(self, method, url, headers=None, json=None, data=None):
            raise AssertionError("no requests expected")

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        user_management_base: str = "/Marti/api/user-management/api"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    assert await api._base() == "/Marti/api/user-management/api"
