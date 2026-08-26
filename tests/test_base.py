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


@pytest.mark.asyncio
async def test_home_api_get_home() -> None:
    """HomeApi.get_home calls the home endpoint and returns status + data"""
    from python_takserver_api.tak_home_api import HomeApi

    class MockConnection:  # noqa: N801
        def __init__(self) -> None:
            self.requested_url: str | None = None

        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            assert method == "get"
            self.requested_url = url
            return 200, {"version": "5.7-RELEASE-43-HEAD"}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = HomeApi(MockServer())
    status, data = await api.get_home()
    assert status == 200
    assert data["version"] == "5.7-RELEASE-43-HEAD"
    assert api.server.connection.requested_url == "https://tak.example.com:8443/Marti/api/home"


@pytest.mark.asyncio
async def test_home_api_get_user_roles() -> None:
    """HomeApi.get_user_roles calls the roles endpoint and returns the role list"""
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
            assert method == "get"
            assert url == "https://tak.example.com:8443/Marti/api/util/user/roles"
            return 200, ["ROLE_ADMIN", "ROLE_WEBTAK"]

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = HomeApi(MockServer())
    status, data = await api.get_user_roles()
    assert status == 200
    assert data == ["ROLE_ADMIN", "ROLE_WEBTAK"]


@pytest.mark.asyncio
async def test_home_api_has_role_true() -> None:
    """HomeApi.has_role returns True when the certificate has the role"""
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
            return 200, ["ROLE_ADMIN", "ROLE_WEBTAK"]

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = HomeApi(MockServer())
    assert await api.has_role("ROLE_ADMIN") is True


@pytest.mark.asyncio
async def test_home_api_has_role_false() -> None:
    """HomeApi.has_role returns False when the certificate lacks the role"""
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
            return 200, ["ROLE_WEBTAK"]

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = HomeApi(MockServer())
    assert await api.has_role("ROLE_ADMIN") is False


@pytest.mark.asyncio
async def test_home_api_has_role_no_roles() -> None:
    """HomeApi.has_role returns False when the server returns no role list"""
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
            return 500, {"status": "error"}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = HomeApi(MockServer())
    assert await api.has_role("ROLE_ADMIN") is False


@pytest.mark.asyncio
async def test_home_api_server_version() -> None:
    """HomeApi.server_version returns the version string on HTTP 200"""
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
            assert method == "get"
            assert url == "https://tak.example.com:8443/Marti/api/version"
            return 200, "5.7-RELEASE-43-HEAD"

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = HomeApi(MockServer())
    assert await api.server_version() == "5.7-RELEASE-43-HEAD"


@pytest.mark.asyncio
async def test_home_api_server_version_error() -> None:
    """HomeApi.server_version returns None on a non-200 response"""
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
            return 500, {"status": "error"}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = HomeApi(MockServer())
    assert await api.server_version() is None


@pytest.mark.asyncio
async def test_home_api_is_ldap_admin_true() -> None:
    """HomeApi.is_ldap_admin returns True on HTTP 200 with truthy data"""
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
            assert url == "https://tak.example.com:8443/Marti/api/util/isLdapAdmin"
            return 200, {"ldap": True}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = HomeApi(MockServer())
    assert await api.is_ldap_admin() is True


@pytest.mark.asyncio
async def test_home_api_is_ldap_admin_falsy() -> None:
    """HomeApi.is_ldap_admin returns False on HTTP 200 with falsy data"""
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
    assert await api.is_ldap_admin() is False


@pytest.mark.asyncio
async def test_home_api_is_ldap_admin_missing_on_old_server() -> None:
    """HomeApi.is_ldap_admin returns False when TAK < 5.8 answers 404"""
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
            return 404, ""

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = HomeApi(MockServer())
    assert await api.is_ldap_admin() is False


@pytest.mark.asyncio
async def test_create_mission_url_encodes_parameters() -> None:
    """create_mission percent-encodes special characters in parameters"""
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
            assert "creatorUid=T+1" in url
            assert "group=a%26b%3Dc" in url
            assert "&classification=" not in url.split("group=")[1]
            return 200, {"name": "new"}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = MissionApi(MockServer())
    status, _ = await api.create_mission(name="new", creator_uid="T 1", group="a&b=c")
    assert status == 200


@pytest.mark.asyncio
async def test_add_mission_content_url_encodes_uid() -> None:
    """add_mission_content percent-encodes the creatorUid"""
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
            assert "creatorUid=TEST%2F001" in url
            return 200, {"data": []}

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = MissionApi(MockServer())
    status, _ = await api.add_mission_content(name="m", uids=["u"], my_uid="TEST/001", token="t")
    assert status == 200
