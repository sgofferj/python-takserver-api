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
            assert "groupList" not in json
            return 201, {"username": "op1"}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
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
            assert json["groupListIN"] == ["readers"]
            assert json["groupListOUT"] == ["writers"]
            assert json["groupList"] == ["both"]
            return 201, {"username": "op2"}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    status, data = await api.create_or_update_file_user(
        username="op2",
        password="hunter2",  # pragma: allowlist secret
        group_list_in=["readers"],
        group_list_out=["writers"],
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
        connection: Any = MockConnection()

    api = UserAccountManagementApi(MockServer())
    assert await api.group_exists("ghost") is False
