"""Tests for base classes (HomeApi, MissionApi basic methods)"""

from typing import Any

import pytest


@pytest.mark.asyncio
async def test_home_api_is_admin_true() -> None:
    """HomeApi.is_admin returns True when server returns truthy data"""
    from python_takserver_api.tak_home_api import HomeApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            return 200, {"authenticated": True}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = HomeApi(MockServer())
    result = await api.is_admin()
    assert result is True


@pytest.mark.asyncio
async def test_home_api_is_admin_false() -> None:
    """HomeApi.is_admin returns False when server returns falsy data"""
    from python_takserver_api.tak_home_api import HomeApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            return 200, {}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = HomeApi(MockServer())
    result = await api.is_admin()
    assert result is False


@pytest.mark.asyncio
async def test_get_mission() -> None:
    """get_mission returns mission data"""
    from python_takserver_api.tak_mission_api import MissionApi

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
            assert "/Marti/api/missions/test-mission" in url
            return 200, {"name": "test-mission", "guid": "abc-123"}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = MissionApi(MockServer())
    status, data = await api.get_mission("test-mission")
    assert status == 200
    assert data["name"] == "test-mission"


@pytest.mark.asyncio
async def test_get_mission_role() -> None:
    """get_mission_role returns role data"""
    from python_takserver_api.tak_mission_api import MissionApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert "/missions/test-mission/role" in url
            return 200, {"role": "MISSION_OWNER"}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = MissionApi(MockServer())
    status, data = await api.get_mission_role("test-mission")
    assert status == 200
    assert data["role"] == "MISSION_OWNER"


@pytest.mark.asyncio
async def test_add_mission_content() -> None:
    """add_mission_content sends UIDs and returns content data"""
    from python_takserver_api.tak_mission_api import MissionApi

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
            assert json == {"uids": ["cot-001"]}
            return 200, {"data": [{"type": "ADD_CONTENT"}]}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = MissionApi(MockServer())
    status, data = await api.add_mission_content(
        name="test-mission",
        uids=["cot-001"],
        my_uid="TEST-001",
        token="t",
    )
    assert status == 200


@pytest.mark.asyncio
async def test_remove_mission_content() -> None:
    """remove_mission_content calls DELETE"""
    from python_takserver_api.tak_mission_api import MissionApi

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
            return 200, {"status": "removed"}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = MissionApi(MockServer())
    status, data = await api.remove_mission_content(
        name="test-mission",
        uid="cot-001",
        my_uid="TEST-001",
        token="t",
    )
    assert status == 200


@pytest.mark.asyncio
async def test_create_mission_with_opts() -> None:
    """create_mission with all optional parameters"""
    from python_takserver_api.tak_mission_api import MissionApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert "group=alpha" in url
            assert "defaultRole=OWNER" in url
            assert "classification=U" in url
            return 200, {"name": "new", "token": "t"}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = MissionApi(MockServer())
    status, data = await api.create_mission(
        name="new",
        creator_uid="T-001",
        group="alpha",
        default_role="OWNER",
        classification="U",
    )
    assert status == 200
    assert data["token"] == "t"


@pytest.mark.asyncio
async def test_create_mission_minimal() -> None:
    """create_mission without optional parameters"""
    from python_takserver_api.tak_mission_api import MissionApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert "group" not in url
            assert "defaultRole" not in url
            assert "classification" not in url
            return 200, {"name": "minimal"}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = MissionApi(MockServer())
    status, data = await api.create_mission(
        name="minimal",
        creator_uid="T-001",
    )
    assert status == 200


@pytest.mark.asyncio
async def test_get_mission_subscriptions() -> None:
    """get_mission_subscriptions returns subscription list"""
    from python_takserver_api.tak_mission_api import MissionApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert "/missions/test/subscriptions" in url
            return 200, [{"uid": "sub-1"}]

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = MissionApi(MockServer())
    status, data = await api.get_mission_subscriptions("test")
    assert status == 200


@pytest.mark.asyncio
async def test_get_mission_subscription_roles() -> None:
    """get_mission_subscription_roles returns role data"""
    from python_takserver_api.tak_mission_api import MissionApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert "/subscriptions/roles" in url
            return 200, [{"role": "MISSION_SUBSCRIBER"}]

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = MissionApi(MockServer())
    status, data = await api.get_mission_subscription_roles("test")
    assert status == 200


@pytest.mark.asyncio
async def test_set_mission_role() -> None:
    """set_mission_role sets role and returns result"""
    from python_takserver_api.tak_mission_api import MissionApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert "clientUid=client-1" in url
            assert "role=MISSION_OWNER" in url
            return 200, {"success": True}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = MissionApi(MockServer())
    status, data = await api.set_mission_role(
        name="test",
        client_uid="client-1",
        username="op",
        role="MISSION_OWNER",
        token="tok",
    )
    assert status == 200


@pytest.mark.asyncio
async def test_create_mission_subscription() -> None:
    """create_mission_subscription with optional params"""
    from python_takserver_api.tak_mission_api import MissionApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert "secago=3600" in url
            assert "topic=events" in url
            return 200, {"token": "sub-token"}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = MissionApi(MockServer())
    status, data = await api.create_mission_subscription(
        name="test",
        uid="u-1",
        topic="events",
        secago="3600",
    )
    assert status == 200


@pytest.mark.asyncio
async def test_create_mission_subscription_full() -> None:
    """create_mission_subscription with all remaining optional params"""
    from python_takserver_api.tak_mission_api import MissionApi

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert "password=x" in url
            assert "start=2025-01-01" in url
            assert "end=2025-12-31" in url
            return 200, {"token": "t"}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = MissionApi(MockServer())
    status, data = await api.create_mission_subscription(
        name="test",
        uid="u-1",
        password="x",
        start="2025-01-01",
        end="2025-12-31",
    )
    assert status == 200
