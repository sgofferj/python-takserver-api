"""Tests for the Group (channel subscription) API"""

import asyncio
from typing import Any

import pytest


def _group(name: str, direction: str, active: bool = False, bitpos: int = 0) -> dict[str, Any]:
    return {
        "name": name,
        "direction": direction,
        "created": "2026-08-23T00:00:00.000Z",
        "type": "SYSTEM",
        "bitpos": bitpos,
        "active": active,
    }


class MockConnection:
    """Mock connection recording requests and replaying canned responses."""

    def __init__(self, handler: Any) -> None:
        self.handler = handler

    async def request(  # noqa: N802
        self,
        method: str,
        url: str,
        headers: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: str | None = None,
    ) -> tuple[int, Any]:
        return await self.handler(method, url, headers, json, data)


class MockServer:  # noqa: N801
    api_base_url: str = "https://tak.example.com:8443"
    connection: Any = None
    username: str = "testadmin"


ENVELOPE = {
    "version": "3",
    "type": "com.bbn.marti.remote.groups.Group",
    "data": None,  # filled below
    "nodeId": "test-node",
}

ALL_GROUPS_RESPONSE = [
    _group("grp-alpha", "IN", active=True, bitpos=1),
    _group("grp-alpha", "OUT", bitpos=2),
    _group("grp-beta", "IN", active=True, bitpos=3),
    _group("grp-beta", "OUT", active=True, bitpos=4),
]

ENVELOPE["data"] = ALL_GROUPS_RESPONSE


def make_api(handler: Any) -> tuple[Any, MockServer]:
    from python_takserver_api.tak_group_api import GroupApi

    server = MockServer()
    server.connection = MockConnection(handler)
    return GroupApi(server), server


@pytest.mark.asyncio
async def test_get_all_groups() -> None:
    """get_all_groups requests useCache/sendLatestSA as lowercase query flags"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert method == "get"
        assert "/Marti/api/groups/all" in url
        assert "useCache=false" in url
        assert "sendLatestSA=true" in url
        return 200, ENVELOPE

    api, _ = make_api(handler)
    status, data = await api.get_all_groups(send_latest_sa=True)
    assert status == 200
    assert len(data) == 4


@pytest.mark.asyncio
async def test_get_groups_for_user() -> None:
    """get_groups_for_user passes the username query parameter"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert method == "get"
        assert "/Marti/api/groups/user?username=op1" in url
        return 200, {"version": "3", "type": "com.bbn.marti.remote.groups.Group", "data": [_group("grp-alpha", "OUT")]}

    api, _ = make_api(handler)
    status, data = await api.get_groups_for_user("op1")
    assert status == 200
    assert data[0]["name"] == "grp-alpha"


@pytest.mark.asyncio
async def test_get_group() -> None:
    """get_group builds the name/direction path"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert method == "get"
        assert url.endswith("/Marti/api/groups/grp-alpha/OUT")
        return 200, {"version": "3", "type": "com.bbn.marti.remote.groups.Group", "data": _group("grp-alpha", "OUT")}

    api, _ = make_api(handler)
    status, data = await api.get_group("grp-alpha", "out")
    assert status == 200
    assert data["direction"] == "OUT"


@pytest.mark.asyncio
async def test_set_active_groups_tuples() -> None:
    """set_active_groups serializes (name, direction) tuples"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert method == "put"
        assert "/Marti/api/groups/active" in url
        assert "clientUid" not in url
        assert json == [{"name": "grp-alpha", "direction": "IN"}]
        return 200, None

    api, _ = make_api(handler)
    status, _ = await api.set_active_groups([("grp-alpha", "in")])
    assert status == 200


@pytest.mark.asyncio
async def test_set_active_groups_dicts_with_client_uid() -> None:
    """set_active_groups passes dicts through and appends clientUid"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert "clientUid=uid-1" in url
        assert json == [{"name": "grp-beta", "direction": "IN"}]
        return 200, None

    api, _ = make_api(handler)
    status, _ = await api.set_active_groups([{"name": "grp-beta", "direction": "IN"}], client_uid="uid-1")
    assert status == 200


@pytest.mark.asyncio
async def test_set_active_groups_bits() -> None:
    """set_active_groups_bits sends the raw bitmask array"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert method == "put"
        assert "/Marti/api/groups/activebits" in url
        assert json == [1, 3]
        return 200, None

    api, _ = make_api(handler)
    status, _ = await api.set_active_groups_bits([1, 3])
    assert status == 200


@pytest.mark.asyncio
async def test_set_active_groups_force() -> None:
    """set_active_groups_force targets a username query param"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert method == "put"
        assert "/Marti/api/groups/activeForce?username=op2" in url
        assert json == [{"name": "grp-alpha", "direction": "IN"}]
        return 200, None

    api, _ = make_api(handler)
    status, _ = await api.set_active_groups_force("op2", [("grp-alpha", "IN")])
    assert status == 200


@pytest.mark.asyncio
async def test_wait_for_group_update() -> None:
    """wait_for_group_update long-polls the update endpoint"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert method == "get"
        assert url.endswith("/Marti/api/groups/update/op1")
        return 200, True

    api, _ = make_api(handler)
    status, data = await api.wait_for_group_update("op1")
    assert status == 200
    assert data is True


@pytest.mark.asyncio
async def test_get_group_cache_enabled() -> None:
    """get_group_cache_enabled returns the cache flag payload"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert "/Marti/api/groups/groupCacheEnabled" in url
        return 200, {"version": "3", "type": "java.lang.Boolean", "data": False}

    api, _ = make_api(handler)
    status, data = await api.get_group_cache_enabled()
    assert status == 200
    assert data is False


@pytest.mark.asyncio
async def test_get_ldap_groups() -> None:
    """get_ldap_groups passes the required filter parameter"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert "/Marti/api/groups?groupNameFilter=ldap-filter" in url
        return 200, {"version": "3", "type": "...", "data": []}

    api, _ = make_api(handler)
    status, data = await api.get_ldap_groups("ldap-filter")
    assert status == 200
    assert data == []


@pytest.mark.asyncio
async def test_get_ldap_group_members() -> None:
    """get_ldap_group_members repeats groupNameFilter for every group"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert url.count("groupNameFilter=") == 2
        assert "groupNameFilter=A" in url
        assert "groupNameFilter=B" in url
        return 200, {"version": "3", "type": "...", "data": [{"groupname": "A", "members": []}]}

    api, _ = make_api(handler)
    status, data = await api.get_ldap_group_members(["A", "B"])
    assert status == 200
    assert data[0]["groupname"] == "A"


@pytest.mark.asyncio
async def test_get_active_groups_reads_subscriptions() -> None:
    """get_active_groups reads the SUBSCRIPTION view (/groups/user)"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert "/groups/user?username=testadmin" in url
        return 200, {
            "version": "3",
            "type": "com.bbn.marti.remote.groups.Group",
            "data": [
                _group("chan-a", "OUT", active=True),
                _group("chan-a", "OUT", active=True),  # stale duplicate
                _group("chan-b", "IN"),
            ],
        }

    api, _ = make_api(handler)
    active = await api.get_active_groups()
    assert active == [{"name": "chan-a", "direction": "OUT"}]


@pytest.mark.asyncio
async def test_get_active_groups_requires_username() -> None:
    """get_active_groups raises when no username is available"""
    from python_takserver_api.tak_group_api import GroupApi

    server = MockServer()
    server.username = None
    api = GroupApi(server)
    with pytest.raises(ValueError):
        await api.get_active_groups()


@pytest.mark.asyncio
async def test_subscribe_uses_subscription_readback() -> None:
    """subscribe does RMW: subscriptions read, availability check, one write"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        if "/groups/all" in url:
            return 200, ENVELOPE  # available channels (grp-alpha OUT only)
        if "/groups/user" in url:
            return 200, {"version": "3", "type": "...", "data": []}  # nothing subscribed yet
        assert method == "put" and "/groups/active" in url
        assert json == [
            {"name": "grp-alpha", "direction": "IN"},
            {"name": "grp-alpha", "direction": "OUT"},
        ]
        return 200, None

    api, _ = make_api(handler)
    status, _ = await api.subscribe("grp-alpha")
    assert status == 200


@pytest.mark.asyncio
async def test_subscribe_preserves_existing_subscriptions() -> None:
    """subscribe keeps already-subscribed channels untouched"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        if "/groups/all" in url:
            return 200, ENVELOPE
        if "/groups/user" in url:
            return 200, {
                "version": "3",
                "type": "...",
                "data": [_group("grp-alpha", "IN", active=True)],
            }
        assert json == [
            {"name": "grp-alpha", "direction": "IN"},
            {"name": "grp-alpha", "direction": "OUT"},
            {"name": "grp-beta", "direction": "IN"},
            {"name": "grp-beta", "direction": "OUT"},
        ]
        return 200, None

    api, _ = make_api(handler)
    status, _ = await api.subscribe_many(["grp-alpha", "grp-beta"])
    assert status == 200


@pytest.mark.asyncio
async def test_subscribe_unknown_group_raises_without_write() -> None:
    """subscribe raises ValueError for an unknown group without writing"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        if "/groups/all" in url:
            return 200, ENVELOPE
        if "/groups/user" in url:
            return 200, {"version": "3", "type": "...", "data": []}
        raise AssertionError("no write must happen for an unknown group")

    api, _ = make_api(handler)
    with pytest.raises(ValueError):
        await api.subscribe("GHOST")


@pytest.mark.asyncio
async def test_unsubscribe_removes_only_requested_directions() -> None:
    """unsubscribe deactivates the requested directions of one channel"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        if "/groups/all" in url:
            return 200, ENVELOPE
        if "/groups/user" in url:
            return 200, {
                "version": "3",
                "type": "...",
                "data": [
                    _group("grp-alpha", "IN", active=True),
                    _group("grp-alpha", "OUT", active=True),
                    _group("grp-beta", "OUT", active=True),
                ],
            }
        assert json == [{"name": "grp-alpha", "direction": "IN"}, {"name": "grp-beta", "direction": "OUT"}]
        return 200, None

    api, _ = make_api(handler)
    status, _ = await api.unsubscribe("grp-alpha", directions=["out"])
    assert status == 200


@pytest.mark.asyncio
async def test_is_subscribed_checks_any_or_specific_direction() -> None:
    """is_subscribed defaults to ANY direction and can narrow to one"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert "/groups/user?username=testadmin" in url
        return 200, {
            "version": "3",
            "type": "...",
            "data": [_group("chan-a", "OUT", active=True)],
        }

    api, _ = make_api(handler)
    assert await api.is_subscribed("chan-a") is True
    assert await api.is_subscribed("chan-a", direction="OUT") is True
    assert await api.is_subscribed("chan-a", direction="IN") is False
    assert await api.is_subscribed("ghost") is False


@pytest.mark.asyncio
async def test_is_subscribed_explicit_username() -> None:
    """is_subscribed can query another user's subscriptions"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert "username=other-user" in url
        return 200, {"version": "3", "type": "...", "data": [_group("chan-a", "IN", active=True)]}

    api, _ = make_api(handler)
    assert await api.is_subscribed("chan-a", username="other-user") is True


@pytest.mark.asyncio
async def test_unsubscribe_many_removes_all_requested_directions() -> None:
    """unsubscribe_many strips the requested channels in one write"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        if url.endswith("/groups/user?username=testadmin"):
            return 200, {
                "version": "3",
                "type": "...",
                "data": [
                    _group("chan-a", "IN", active=True),
                    _group("chan-a", "OUT", active=True),
                    _group("chan-b", "IN", active=True),
                ],
            }
        assert method == "put"
        assert json == [{"name": "chan-b", "direction": "IN"}]
        return 200, None

    api, _ = make_api(handler)
    status, _ = await api.unsubscribe_many(["chan-a"])
    assert status == 200


@pytest.mark.asyncio
async def test_unsubscribe_many_keeps_other_channels() -> None:
    """unsubscribe_many ignores unknown names and keeps unrelated directions"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        if url.endswith("/groups/user?username=testadmin"):
            return 200, {
                "version": "3",
                "type": "...",
                "data": [_group("chan-a", "OUT", active=True), _group("chan-b", "IN", active=True)],
            }
        assert json == [{"name": "chan-a", "direction": "OUT"}]
        return 200, None

    api, _ = make_api(handler)
    await api.unsubscribe_many(["ghost", " chan-b "], directions=["IN"])


@pytest.mark.asyncio
async def test_wait_for_group_update_until_returns_on_change() -> None:
    """wait_for_group_update_until returns the payload when a change arrives"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert "/groups/update/testadmin" in url
        return 200, {"version": "3", "type": "...", "data": True}

    api, _ = make_api(handler)
    status, result = await api.wait_for_group_update_until("testadmin", timeout=5.0)
    assert status == 200
    assert result["data"] is True


@pytest.mark.asyncio
async def test_wait_for_group_update_until_times_out() -> None:
    """wait_for_group_update_until raises TimeoutError when nothing changes"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        await asyncio.sleep(5)
        raise AssertionError("should not complete")

    api, _ = make_api(handler)
    with pytest.raises(TimeoutError):
        await api.wait_for_group_update_until("testadmin", timeout=0.05)


@pytest.mark.asyncio
async def test_get_channels_collapses_duplicates() -> None:
    """get_channels returns one record per channel with direction flags"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        assert "/groups/all" in url
        return 200, {
            "version": "3",
            "type": "...",
            "data": [
                _group("chan-b", "IN", active=True),
                _group("chan-a", "IN", active=False),
                _group("chan-a", "OUT", active=True),
            ],
        }

    api, _ = make_api(handler)
    channels = await api.get_channels()
    assert [c["name"] for c in channels] == ["chan-a", "chan-b"]
    assert channels[0]["directions"] == {"IN": False, "OUT": True}
    assert channels[1]["directions"] == {"IN": True}


@pytest.mark.asyncio
async def test_channel_exists_true_and_false() -> None:
    """channel_exists matches padded spellings and rejects unknown names"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        return 200, {
            "version": "3",
            "type": "...",
            "data": [_group(" chan-a ", "IN"), _group("chan-b", "OUT")],
        }

    api, _ = make_api(handler)
    assert await api.channel_exists("chan-a") is True
    assert await api.channel_exists("chan-b") is True
    assert await api.channel_exists("ghost") is False


@pytest.mark.asyncio
async def test_get_active_groups_raises_clear_error_on_server_error() -> None:
    """get_active_groups raises ValueError instead of crashing on error text"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        return 500, "<html>Server Error</html>"

    api, _ = make_api(handler)
    with pytest.raises(ValueError, match="HTTP 500"):
        await api.get_active_groups()


@pytest.mark.asyncio
async def test_is_subscribed_raises_clear_error_on_server_error() -> None:
    """is_subscribed raises ValueError instead of crashing on error text"""

    async def handler(method: str, url: str, headers: Any, json: Any, data: Any) -> tuple[int, Any]:
        return 403, "Group access denied"

    api, _ = make_api(handler)
    with pytest.raises(ValueError, match="HTTP 403"):
        await api.is_subscribed("chan-a")
