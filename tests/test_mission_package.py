"""Tests for mission package functions and MissionApi request construction"""

import io
import zipfile
import xml.etree.ElementTree as ET
from typing import Any, NamedTuple

import pytest

from python_takserver_api.tak_mission_api import MissionApi, _query, build_mission_package


class MockConnection:  # noqa: N801
    """Recording connection mock.

    Every request() call is appended to ``calls`` as a
    (method, url, headers, json, data) tuple and a canned 200 response is
    returned, so tests can assert the exact request the API issued.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any] | None, Any, Any]] = []

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, Any] | None = None,
        json: dict[str, Any] | list[Any] | None = None,
        data: str | None = None,
    ) -> tuple[int, Any]:
        self.calls.append((method, url, headers, json, data))
        return 200, {"ok": True}


class MockServer:  # noqa: N801
    """Minimal server stub carrying a base URL and a recording connection."""

    def __init__(self) -> None:
        self.api_base_url: str = "https://tak.example.com:8443"
        self.connection: MockConnection = MockConnection()
        self.session: Any = None


class RequestCase(NamedTuple):
    """Expected request issued by one MissionApi method call"""

    api_method: str
    kwargs: dict[str, Any]
    http_method: str
    url: str
    json_body: Any
    data_body: Any
    headers: dict[str, Any] | None


MISSION_REQUEST_CASES: list[RequestCase] = [
    RequestCase(
        "get_mission_count",
        {"password_protected": True, "tool": "public"},
        "get",
        "https://tak.example.com:8443/Marti/api/missioncount?passwordProtected=true&tool=public",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_mission_names",
        {"password_protected": False, "default_role": "MISSION_READ"},
        "get",
        "https://tak.example.com:8443/Marti/api/missions?passwordProtected=false&defaultRole=MISSION_READ",
        None,
        None,
        None,
    ),
    RequestCase(
        "delete_mission_by_guid",
        {"guid": "guid-123", "creator_uid": "user-1"},
        "delete",
        "https://tak.example.com:8443/Marti/api/missions?guid=guid-123&creatorUid=user-1&deepDelete=false",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_all_invitations",
        {"client_uid": "uid-001"},
        "get",
        "https://tak.example.com:8443/Marti/api/missions/all/invitations?clientUid=uid-001",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_all_logs",
        {},
        "get",
        "https://tak.example.com:8443/Marti/api/missions/all/logs",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_all_subscriptions",
        {},
        "get",
        "https://tak.example.com:8443/Marti/api/missions/all/subscriptions",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_all_subscriptions_by_guid",
        {},
        "get",
        "https://tak.example.com:8443/Marti/api/missions/all/subscriptions/guid",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_invitations",
        {"client_uid": "uid-001"},
        "get",
        "https://tak.example.com:8443/Marti/api/missions/invitations?clientUid=uid-001",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_paged_missions",
        {"page": 2, "pagesize": 25, "ascending": True},
        "get",
        "https://tak.example.com:8443/Marti/api/pagedmissions?page=2&pagesize=25&ascending=true",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_log_entry",
        {"log_id": "log-42"},
        "get",
        "https://tak.example.com:8443/Marti/api/missions/logs/entries/log-42",
        None,
        None,
        None,
    ),
    RequestCase(
        "delete_log_entry",
        {"log_id": "log-42"},
        "delete",
        "https://tak.example.com:8443/Marti/api/missions/logs/entries/log-42",
        None,
        None,
        None,
    ),
    RequestCase(
        "create_log_entry",
        {"log_entry": {"content": "hello", "severity": "Info"}},
        "post",
        "https://tak.example.com:8443/Marti/api/missions/logs/entries",
        {"content": "hello", "severity": "Info"},
        None,
        {"Content-Type": "application/json"},
    ),
    RequestCase(
        "update_log_entry",
        {"log_entry": {"content": "updated", "severity": "Warning"}},
        "put",
        "https://tak.example.com:8443/Marti/api/missions/logs/entries",
        {"content": "updated", "severity": "Warning"},
        None,
        {"Content-Type": "application/json"},
    ),
    RequestCase(
        "delete_mission",
        {"name": "alpha", "creator_uid": "user-1", "deep_delete": True},
        "delete",
        "https://tak.example.com:8443/Marti/api/missions/alpha?creatorUid=user-1&deepDelete=true",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_mission_archive",
        {"name": "alpha"},
        "get",
        "https://tak.example.com:8443/Marti/api/missions/alpha/archive",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_mission_changes",
        {"name": "alpha", "secago": 3600, "squashed": True},
        "get",
        "https://tak.example.com:8443/Marti/api/missions/alpha/changes?secago=3600&squashed=true",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_mission_children",
        {"name": "alpha"},
        "get",
        "https://tak.example.com:8443/Marti/api/missions/alpha/children",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_mission_contacts",
        {"name": "alpha"},
        "get",
        "https://tak.example.com:8443/Marti/api/missions/alpha/contacts",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_mission_cot",
        {"name": "alpha", "path": "a-b"},
        "get",
        "https://tak.example.com:8443/Marti/api/missions/alpha/cot?path=a-b",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_mission_cot",
        {"name": "alpha"},
        "get",
        "https://tak.example.com:8443/Marti/api/missions/alpha/cot",
        None,
        None,
        None,
    ),
    RequestCase(
        "set_mission_expiration",
        {"name": "alpha", "expiration": 1234567890},
        "put",
        "https://tak.example.com:8443/Marti/api/missions/alpha/expiration?expiration=1234567890",
        None,
        None,
        None,
    ),
    RequestCase(
        "set_mission_expiration",
        {"name": "alpha"},
        "put",
        "https://tak.example.com:8443/Marti/api/missions/alpha/expiration",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_mission_kml",
        {"name": "alpha", "download": True},
        "get",
        "https://tak.example.com:8443/Marti/api/missions/alpha/kml?download=true",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_mission_parent",
        {"name": "alpha"},
        "get",
        "https://tak.example.com:8443/Marti/api/missions/alpha/parent",
        None,
        None,
        None,
    ),
    RequestCase(
        "send_mission",
        {"name": "alpha"},
        "post",
        "https://tak.example.com:8443/Marti/api/missions/alpha/send",
        None,
        None,
        None,
    ),
    RequestCase(
        "set_content_keywords",
        {"name": "alpha", "content_hash": "hash-456", "keywords": ["kw1", "kw2"], "creator_uid": "user-1"},
        "put",
        "https://tak.example.com:8443/Marti/api/missions/alpha/content/hash-456/keywords?creatorUid=user-1",
        ["kw1", "kw2"],
        None,
        {"Content-Type": "application/json"},
    ),
    RequestCase(
        "delete_content_keywords",
        {"name": "alpha", "content_hash": "hash-456"},
        "delete",
        "https://tak.example.com:8443/Marti/api/missions/alpha/content/hash-456/keywords",
        None,
        None,
        None,
    ),
    RequestCase(
        "remove_mission_content_by_hash",
        {"name": "alpha", "content_hash": "hash-456", "creator_uid": "user-1"},
        "delete",
        "https://tak.example.com:8443/Marti/api/missions/alpha/contents?hash=hash-456&creatorUid=user-1",
        None,
        None,
        None,
    ),
    RequestCase(
        "create_external_data",
        {"name": "alpha", "creator_uid": "user-1", "external_data": {"uid": "ext-1", "dataType": "x"}},
        "post",
        "https://tak.example.com:8443/Marti/api/missions/alpha/externaldata?creatorUid=user-1",
        {"uid": "ext-1", "dataType": "x"},
        None,
        {"Content-Type": "application/json"},
    ),
    RequestCase(
        "delete_external_data",
        {"name": "alpha", "data_id": "data-789", "notes": "cleanup", "creator_uid": "user-1"},
        "delete",
        "https://tak.example.com:8443/Marti/api/missions/alpha/externaldata/data-789?notes=cleanup&creatorUid=user-1",
        None,
        None,
        None,
    ),
    RequestCase(
        "change_external_data",
        {"name": "alpha", "data_id": "data-789", "creator_uid": "user-1", "notes": "updated", "data": "<xml/>"},
        "post",
        "https://tak.example.com:8443/Marti/api/missions/alpha/externaldata/data-789/change?creatorUid=user-1&notes=updated",
        None,
        "<xml/>",
        {"Content-Type": "application/json"},
    ),
    RequestCase(
        "invite_to_mission",
        {"name": "alpha"},
        "post",
        "https://tak.example.com:8443/Marti/api/missions/alpha/invite",
        None,
        None,
        None,
    ),
    RequestCase(
        "set_mission_invite",
        {"name": "alpha", "invite_type": "user", "invitee": "bob", "creator_uid": "user-1", "role": "MISSION_READ"},
        "put",
        "https://tak.example.com:8443/Marti/api/missions/alpha/invite/user/bob?creatorUid=user-1&role=MISSION_READ",
        None,
        None,
        None,
    ),
    RequestCase(
        "delete_mission_invite",
        {"name": "alpha", "invite_type": "group", "invitee": "alpha-team", "creator_uid": "user-1"},
        "delete",
        "https://tak.example.com:8443/Marti/api/missions/alpha/invite/group/alpha-team?creatorUid=user-1",
        None,
        None,
        None,
    ),
    RequestCase(
        "set_mission_keywords",
        {"name": "alpha", "keywords": ["kw1", "kw2"], "creator_uid": "user-1"},
        "put",
        "https://tak.example.com:8443/Marti/api/missions/alpha/keywords?creatorUid=user-1",
        ["kw1", "kw2"],
        None,
        {"Content-Type": "application/json"},
    ),
    RequestCase(
        "delete_mission_keywords",
        {"name": "alpha", "creator_uid": "user-1"},
        "delete",
        "https://tak.example.com:8443/Marti/api/missions/alpha/keywords?creatorUid=user-1",
        None,
        None,
        None,
    ),
    RequestCase(
        "delete_mission_keyword",
        {"name": "alpha", "keyword": "kw", "creator_uid": "user-1"},
        "delete",
        "https://tak.example.com:8443/Marti/api/missions/alpha/keywords/kw?creatorUid=user-1",
        None,
        None,
        None,
    ),
    RequestCase(
        "set_mission_password",
        {"name": "alpha", "password": "secret", "creator_uid": "user-1"},  # pragma: allowlist secret
        "put",
        "https://tak.example.com:8443/Marti/api/missions/alpha/password?password=secret&creatorUid=user-1",
        None,
        None,
        None,
    ),
    RequestCase(
        "clear_mission_password",
        {"name": "alpha", "creator_uid": "user-1"},
        "delete",
        "https://tak.example.com:8443/Marti/api/missions/alpha/password?creatorUid=user-1",
        None,
        None,
        None,
    ),
    RequestCase(
        "set_uid_keywords",
        {"name": "alpha", "uid": "uid-001", "keywords": ["kw1"], "creator_uid": "user-1"},
        "put",
        "https://tak.example.com:8443/Marti/api/missions/alpha/uid/uid-001/keywords?creatorUid=user-1",
        ["kw1"],
        None,
        {"Content-Type": "application/json"},
    ),
    RequestCase(
        "delete_uid_keywords",
        {"name": "alpha", "uid": "uid-001"},
        "delete",
        "https://tak.example.com:8443/Marti/api/missions/alpha/uid/uid-001/keywords",
        None,
        None,
        None,
    ),
    RequestCase(
        "copy_mission",
        {
            "name": "alpha",
            "creator_uid": "user-1",
            "copy_name": "beta",
            "copy_path": "/beta",
            "default_role": "MISSION_READ",
        },
        "put",
        "https://tak.example.com:8443/Marti/api/missions/alpha/copy?creatorUid=user-1&copyName=beta&copyPath=%2Fbeta&defaultRole=MISSION_READ",
        None,
        None,
        None,
    ),
    RequestCase(
        "create_mission_feed",
        {"name": "alpha", "creator_uid": "user-1", "data_feed_uid": "feed-1", "filter_callsign": "alpha-1"},
        "post",
        "https://tak.example.com:8443/Marti/api/missions/alpha/feed?creatorUid=user-1&dataFeedUid=feed-1&filterCallsign=alpha-1",
        None,
        None,
        None,
    ),
    RequestCase(
        "delete_mission_feed",
        {"name": "alpha", "uid": "feed-1", "creator_uid": "user-1"},
        "delete",
        "https://tak.example.com:8443/Marti/api/missions/alpha/feed/feed-1?creatorUid=user-1",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_mission_invitations",
        {"name": "alpha"},
        "get",
        "https://tak.example.com:8443/Marti/api/missions/alpha/invitations",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_mission_layers",
        {"name": "alpha"},
        "get",
        "https://tak.example.com:8443/Marti/api/missions/alpha/layers",
        None,
        None,
        None,
    ),
    RequestCase(
        "delete_mission_layer",
        {"name": "alpha", "uid": "layer-1", "creator_uid": "user-1"},
        "delete",
        "https://tak.example.com:8443/Marti/api/missions/alpha/layers?uid=layer-1&creatorUid=user-1",
        None,
        None,
        None,
    ),
    RequestCase(
        "create_mission_layer",
        {
            "name": "alpha",
            "layer_name": "LayerA",
            "layer_type": "Cot",
            "uid": "layer-1",
            "parent_uid": "p-1",
            "creator_uid": "user-1",
        },
        "put",
        "https://tak.example.com:8443/Marti/api/missions/alpha/layers?name=LayerA&type=Cot&uid=layer-1&parentUid=p-1&creatorUid=user-1",
        None,
        None,
        None,
    ),
    RequestCase(
        "set_mission_layer_parent",
        {"name": "alpha", "layer_uid": "layer-1", "parent_uid": "p-1", "creator_uid": "user-1"},
        "put",
        "https://tak.example.com:8443/Marti/api/missions/alpha/layers/parent?layerUid=layer-1&parentUid=p-1&creatorUid=user-1",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_mission_layer",
        {"name": "alpha", "layer_uid": "layer-1"},
        "get",
        "https://tak.example.com:8443/Marti/api/missions/alpha/layers/layer-1",
        None,
        None,
        None,
    ),
    RequestCase(
        "rename_mission_layer",
        {"name": "alpha", "layer_uid": "layer-1", "new_name": "NewName", "creator_uid": "user-1"},
        "put",
        "https://tak.example.com:8443/Marti/api/missions/alpha/layers/layer-1/name?name=NewName&creatorUid=user-1",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_mission_log",
        {"name": "alpha", "secago": 60, "start": "2024-01-01T000000Z"},
        "get",
        "https://tak.example.com:8443/Marti/api/missions/alpha/log?secago=60&start=2024-01-01T000000Z",
        None,
        None,
        None,
    ),
    RequestCase(
        "add_mission_maplayer",
        {"name": "alpha", "creator_uid": "user-1", "map_layer": {"name": "MapA", "type": "Imagery"}},
        "post",
        "https://tak.example.com:8443/Marti/api/missions/alpha/maplayers?creatorUid=user-1",
        {"name": "MapA", "type": "Imagery"},
        None,
        {"Content-Type": "application/json"},
    ),
    RequestCase(
        "update_mission_maplayer",
        {"name": "alpha", "creator_uid": "user-1", "map_layer": {"name": "MapA", "uid": "ml-1"}},
        "put",
        "https://tak.example.com:8443/Marti/api/missions/alpha/maplayers?creatorUid=user-1",
        {"name": "MapA", "uid": "ml-1"},
        None,
        {"Content-Type": "application/json"},
    ),
    RequestCase(
        "delete_mission_maplayer",
        {"name": "alpha", "uid": "ml-1", "creator_uid": "user-1"},
        "delete",
        "https://tak.example.com:8443/Marti/api/missions/alpha/maplayers/ml-1?creatorUid=user-1",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_mission_token",
        {"name": "alpha", "password": "secret"},  # pragma: allowlist secret
        "get",
        "https://tak.example.com:8443/Marti/api/missions/alpha/token?password=secret",
        None,
        None,
        None,
    ),
    RequestCase(
        "get_mission_subscription",
        {"name": "alpha", "uid": "uid-001"},
        "get",
        "https://tak.example.com:8443/Marti/api/missions/alpha/subscription?uid=uid-001",
        None,
        None,
        None,
    ),
    RequestCase(
        "delete_mission_subscription",
        {"name": "alpha", "uid": "uid-001", "topic": "topic-1", "disconnect_only": True},
        "delete",
        "https://tak.example.com:8443/Marti/api/missions/alpha/subscription?uid=uid-001&topic=topic-1&disconnectOnly=true",
        None,
        None,
        None,
    ),
    RequestCase(
        "create_mission_subscriptions",
        {"name": "alpha", "creator_uid": "user-1", "uids": ["uid-001", "uid-002"]},
        "post",
        "https://tak.example.com:8443/Marti/api/missions/alpha/subscription?creatorUid=user-1",
        ["uid-001", "uid-002"],
        None,
        {"Content-Type": "application/json"},
    ),
]


def test_build_package_minimal() -> None:
    """Minimal mission package with just CoTs"""
    package = build_mission_package(
        name="Test Package",
        mission_name="test-mission",
        mission_server="tak.example.com:8443:ssl",
        creator_uid="TEST-001",
        cot_files={"cot-abc": "<event></event>"},
    )

    assert isinstance(package, bytes)
    assert len(package) > 0

    zf = zipfile.ZipFile(io.BytesIO(package))
    names = zf.namelist()
    assert "MANIFEST/manifest.xml" in names
    assert "cot/cot-abc.cot" in names

    manifest = ET.fromstring(zf.read("MANIFEST/manifest.xml"))
    assert manifest.tag == "MissionPackageManifest"
    assert manifest.attrib["version"] == "2"

    cfg = manifest.find("Configuration")
    assert cfg is not None
    params = {p.attrib["name"]: p.attrib["value"] for p in cfg.findall("Parameter")}
    assert params["name"] == "Test Package"
    assert params["mission_name"] == "test-mission"
    assert params["tool"] == "public"


def test_build_package_with_resources() -> None:
    """Mission package with both CoTs and resource files"""
    package = build_mission_package(
        name="Full Package",
        mission_name="test-mission",
        mission_server="tak.example.com:8443:ssl",
        creator_uid="TEST-002",
        cot_files={"cot-001": "<event uid='cot-001'/>"},
        resource_files={
            "screenshot.png": (b"PNG...", "image/png", "screenshot.png", "res-001"),
            "report.pdf": (b"PDF...", "application/pdf", "report.pdf", "res-002"),
        },
    )

    zf = zipfile.ZipFile(io.BytesIO(package))
    assert "MANIFEST/manifest.xml" in zf.namelist()
    assert "cot/cot-001.cot" in zf.namelist()
    assert "contents/screenshot.png" in zf.namelist()
    assert "contents/report.pdf" in zf.namelist()

    assert zf.read("cot/cot-001.cot") == b"<event uid='cot-001'/>"
    assert zf.read("contents/screenshot.png") == b"PNG..."
    assert zf.read("contents/report.pdf") == b"PDF..."

    manifest = ET.fromstring(zf.read("MANIFEST/manifest.xml"))
    contents = manifest.find("Contents")
    assert contents is not None
    content_entries = contents.findall("Content")
    assert len(content_entries) == 3


def test_build_package_with_groups() -> None:
    """Mission package with group access control"""
    package = build_mission_package(
        name="Group Package",
        mission_name="group-mission",
        mission_server="tak.example.com:8443:ssl",
        creator_uid="TEST-003",
        cot_files={"cot-xyz": "<event/>"},
        groups=["Alpha", "Bravo"],
    )

    zf = zipfile.ZipFile(io.BytesIO(package))
    manifest = ET.fromstring(zf.read("MANIFEST/manifest.xml"))
    groups_elem = manifest.find("Groups")
    assert groups_elem is not None
    group_names = [g.attrib["name"] for g in groups_elem.findall("Group")]
    assert group_names == ["Alpha", "Bravo"]


def test_build_package_role() -> None:
    """Mission package includes default subscriber role"""
    package = build_mission_package(
        name="Role Test",
        mission_name="test",
        mission_server="tak.example.com:8443:ssl",
        creator_uid="TEST-004",
        cot_files={},
    )

    zf = zipfile.ZipFile(io.BytesIO(package))
    manifest = ET.fromstring(zf.read("MANIFEST/manifest.xml"))
    role = manifest.find("Role")
    assert role is not None
    assert role.attrib["name"] == "MISSION_SUBSCRIBER"
    perms = [p.attrib["name"] for p in role.findall("Permissions")]
    assert "MISSION_WRITE" in perms
    assert "MISSION_READ" in perms


def test_build_package_uid_generation() -> None:
    """Each call generates a new package UID"""
    pkg_a = build_mission_package(
        name="Same",
        mission_name="test",
        mission_server="t.example.com:8443:ssl",
        creator_uid="T",
        cot_files={},
    )
    pkg_b = build_mission_package(
        name="Same",
        mission_name="test",
        mission_server="t.example.com:8443:ssl",
        creator_uid="T",
        cot_files={},
    )

    zf_a = zipfile.ZipFile(io.BytesIO(pkg_a))
    zf_b = zipfile.ZipFile(io.BytesIO(pkg_b))

    cfg_a = ET.fromstring(zf_a.read("MANIFEST/manifest.xml")).find("Configuration")
    cfg_b = ET.fromstring(zf_b.read("MANIFEST/manifest.xml")).find("Configuration")

    assert cfg_a is not None and cfg_b is not None
    uid_a = {p.attrib["name"]: p.attrib["value"] for p in cfg_a.findall("Parameter")}["uid"]
    uid_b = {p.attrib["name"]: p.attrib["value"] for p in cfg_b.findall("Parameter")}["uid"]
    assert uid_a != uid_b


def test_build_package_cot_bytes() -> None:
    """CoT content can be passed as bytes"""
    package = build_mission_package(
        name="Bytes Test",
        mission_name="test",
        mission_server="t.example.com:8443:ssl",
        creator_uid="T",
        cot_files={"cot-bytes": b"<event/>"},
    )

    zf = zipfile.ZipFile(io.BytesIO(package))
    assert zf.read("cot/cot-bytes.cot") == b"<event/>"


def test_build_package_empty_cot_files() -> None:
    """build_mission_package handles empty cot_files"""
    package = build_mission_package(
        name="Empty",
        mission_name="test",
        mission_server="t.example.com:8443:ssl",
        creator_uid="T",
        cot_files={},
    )
    zf = zipfile.ZipFile(io.BytesIO(package))
    manifest = ET.fromstring(zf.read("MANIFEST/manifest.xml"))
    contents = manifest.find("Contents")
    assert contents is not None
    assert len(contents.findall("Content")) == 0


def test_build_package_none_groups() -> None:
    """build_mission_package handles groups=None"""
    package = build_mission_package(
        name="NoGroups",
        mission_name="test",
        mission_server="t.example.com:8443:ssl",
        creator_uid="T",
        cot_files={"c": "<e/>"},
        groups=None,
    )
    zf = zipfile.ZipFile(io.BytesIO(package))
    manifest = ET.fromstring(zf.read("MANIFEST/manifest.xml"))
    assert manifest.find("Groups") is None


@pytest.mark.asyncio
async def test_mission_api_class() -> None:
    """MissionApi instantiates and carries server reference"""
    from python_takserver_api.tak_mission_api import MissionApi

    class MockServer:
        api_base_url: str = "https://tak.example.com:8443"
        connection: None = None
        session: None = None

    api = MissionApi(MockServer())
    assert api.server is not None
    assert api.server.api_base_url == "https://tak.example.com:8443"


@pytest.mark.asyncio
async def test_add_mission_package_http_error() -> None:
    """add_mission_package returns error tuple when server returns >=400"""
    from python_takserver_api.tak_mission_api import MissionApi

    class MockResponse:  # noqa: N801
        status: int = 401
        content_type: str = "text/plain"

        async def text(self) -> str:
            return "Unauthorized"

        async def json(self) -> dict[str, Any]:
            return {"error": "unauthorized"}

    class MockSession:  # noqa: N801
        async def put(self, url: str, **kwargs: Any) -> MockResponse:  # noqa: A003
            assert kwargs.get("data") == b"test zip data"
            return MockResponse()

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            session = MockSession()
            if data is not None:
                resp = await session.put(url, headers=headers, data=data)
            else:
                resp = await session.put(url, headers=headers, json=json)
            if resp.status >= 400:
                return resp.status, await resp.text()
            return resp.status, await resp.json()

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = MissionApi(MockServer())
    status, data = await api.add_mission_package(
        name="test-mission",
        creator_uid="TEST-001",
        token="test-token",
        mission_package=b"test zip data",
    )
    assert status == 401
    assert data == "Unauthorized"


@pytest.mark.asyncio
async def test_add_mission_package_success() -> None:
    """add_mission_package returns 200 with mission change data"""
    from python_takserver_api.tak_mission_api import MissionApi

    class MockResponse:  # noqa: N801
        status: int = 200
        content_type: str = "application/json"

        async def json(self) -> dict[str, Any]:
            return {
                "version": "3",
                "type": "MissionChange",
                "data": [{"type": "ADD_CONTENT", "contentUid": "res-001"}],
                "nodeId": "test-node",
            }

    class MockConnection:  # noqa: N801
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            data: str | None = None,
        ) -> tuple[int, Any]:
            return 200, MockResponse()

    class MockServer:  # noqa: N801
        api_base_url: str = "https://tak.example.com:8443"
        connection: Any = MockConnection()

    api = MissionApi(MockServer())
    status, response = await api.add_mission_package(
        name="test-mission",
        creator_uid="TEST-001",
        token="test-token",
        mission_package=b"real zip data",
    )
    assert status == 200
    assert isinstance(response, MockResponse)


@pytest.mark.asyncio
async def test_connection_helper_request_get() -> None:
    """ConnectionHelper.request handles GET with JSON response"""
    from python_takserver_api.class_helpers import ConnectionHelper

    class MockResponse:  # noqa: N801
        status: int = 200
        content_type: str = "application/json"

        async def json(self) -> dict[str, str]:
            return {"key": "value"}

    class MockSession:  # noqa: N801
        async def get(self, url: str, **kwargs: Any) -> MockResponse:  # noqa: A003
            return MockResponse()

    class MockServer:  # noqa: N801
        session: Any = MockSession()

    helper = ConnectionHelper(MockServer(), "/fake/cert", "/fake/key")
    status, data = await helper.request("get", "http://example.com/api")
    assert status == 200
    assert data == {"key": "value"}


@pytest.mark.asyncio
async def test_connection_helper_request_put_json() -> None:
    """ConnectionHelper.request handles PUT with JSON body"""
    from python_takserver_api.class_helpers import ConnectionHelper

    class MockResponse:  # noqa: N801
        status: int = 200
        content_type: str = "application/json"

        async def json(self) -> dict[str, str]:
            return {"status": "ok"}

    class MockSession:  # noqa: N801
        async def put(self, url: str, **kwargs: Any) -> MockResponse:  # noqa: A003
            assert kwargs.get("json") == {"hello": "world"}
            return MockResponse()

    class MockServer:  # noqa: N801
        session: Any = MockSession()

    helper = ConnectionHelper(MockServer(), "/fake/cert", "/fake/key")
    status, data = await helper.request("put", "http://example.com/api", json={"hello": "world"})
    assert status == 200
    assert data == {"status": "ok"}


@pytest.mark.asyncio
async def test_connection_helper_request_put_data() -> None:
    """ConnectionHelper.request handles PUT with raw data body"""
    from python_takserver_api.class_helpers import ConnectionHelper

    class MockResponse:  # noqa: N801
        status: int = 200
        content_type: str = "text/plain"

        async def text(self) -> str:
            return "OK"

    class MockSession:  # noqa: N801
        async def put(self, url: str, **kwargs: Any) -> MockResponse:  # noqa: A003
            assert kwargs.get("data") == "raw body"
            return MockResponse()

    class MockServer:  # noqa: N801
        session: Any = MockSession()

    helper = ConnectionHelper(MockServer(), "/fake/cert", "/fake/key")
    status, data = await helper.request("put", "http://example.com/api", data="raw body")
    assert status == 200
    assert data == "OK"


@pytest.mark.asyncio
async def test_connection_helper_request_error() -> None:
    """ConnectionHelper.request returns error tuple on >=400"""
    from python_takserver_api.class_helpers import ConnectionHelper

    class MockResponse:  # noqa: N801
        status: int = 404
        content_type: str = "text/plain"

        async def text(self) -> str:
            return "Not Found"

    class MockSession:  # noqa: N801
        async def get(self, url: str, **kwargs: Any) -> MockResponse:  # noqa: A003
            return MockResponse()

    class MockServer:  # noqa: N801
        session: Any = MockSession()

    helper = ConnectionHelper(MockServer(), "/fake/cert", "/fake/key")
    status, data = await helper.request("get", "http://example.com/api")
    assert status == 404
    assert data == "Not Found"


@pytest.mark.asyncio
async def test_connection_helper_request_post() -> None:
    """ConnectionHelper.request handles POST with JSON"""
    from python_takserver_api.class_helpers import ConnectionHelper

    class MockResponse:  # noqa: N801
        status: int = 201
        content_type: str = "application/json"

        async def json(self) -> dict[str, int]:
            return {"id": 1}

    class MockSession:  # noqa: N801
        async def post(self, url: str, **kwargs: Any) -> MockResponse:  # noqa: A003
            return MockResponse()

    class MockServer:  # noqa: N801
        session: Any = MockSession()

    helper = ConnectionHelper(MockServer(), "/fake/cert", "/fake/key")
    status, data = await helper.request("post", "http://example.com/api", json={"a": 1})
    assert status == 201
    assert data == {"id": 1}


@pytest.mark.asyncio
async def test_connection_helper_request_delete() -> None:
    """ConnectionHelper.request handles DELETE"""
    from python_takserver_api.class_helpers import ConnectionHelper

    class MockResponse:  # noqa: N801
        status: int = 204
        content_type: str = "application/json"

        async def json(self) -> dict[str, int]:
            return {}

    class MockSession:  # noqa: N801
        async def delete(self, url: str, **kwargs: Any) -> MockResponse:  # noqa: A003
            return MockResponse()

    class MockServer:  # noqa: N801
        session: Any = MockSession()

    helper = ConnectionHelper(MockServer(), "/fake/cert", "/fake/key")
    status, data = await helper.request("delete", "http://example.com/api")
    assert status == 204


@pytest.mark.asyncio
@pytest.mark.parametrize("case", MISSION_REQUEST_CASES, ids=[case.api_method for case in MISSION_REQUEST_CASES])
async def test_new_mission_methods_issue_exact_request(case: RequestCase) -> None:
    """New MissionApi methods issue the exact method, URL, headers, and body"""
    from python_takserver_api.tak_mission_api import MissionApi

    server = MockServer()
    api = MissionApi(server)
    status, data = await getattr(api, case.api_method)(**case.kwargs)
    assert status == 200
    assert data == {"ok": True}
    assert len(server.connection.calls) == 1
    recorded_method, recorded_url, recorded_headers, recorded_json, recorded_data = server.connection.calls[0]
    assert recorded_method == case.http_method
    assert recorded_url == case.url
    assert recorded_json == case.json_body
    assert recorded_data == case.data_body
    assert recorded_headers == case.headers


@pytest.mark.asyncio
async def test_get_mission_optional_params() -> None:
    """get_mission renders optional params in order and omits None"""
    from python_takserver_api.tak_mission_api import MissionApi

    server = MockServer()
    api = MissionApi(server)
    status, data = await api.get_mission(
        name="alpha",
        password="secret",  # pragma: allowlist secret
        changes=True,
        logs=False,
        secago=3600,
        start="2024-01-01T00:00:00Z",
    )
    assert status == 200
    assert data == {"ok": True}
    recorded_method, recorded_url, recorded_headers, recorded_json, recorded_data = server.connection.calls[0]
    assert recorded_method == "get"
    assert recorded_url == (
        "https://tak.example.com:8443/Marti/api/missions/alpha"
        "?password=secret&changes=true&logs=false&secago=3600&start=2024-01-01T00%3A00%3A00Z"
    )
    assert recorded_headers == {"Content-Type": "application/json"}
    assert recorded_json is None
    assert recorded_data is None


def test_query_skips_none() -> None:
    """_query drops None params"""
    assert _query(a=1, b=None, c="x") == "?a=1&c=x"


def test_query_renders_bools_lowercase() -> None:
    """_query renders booleans as lowercase true/false"""
    assert _query(flag=True, other=False) == "?flag=true&other=false"


def test_query_empty_when_all_none() -> None:
    """_query returns an empty string when every param is None"""
    assert _query(a=None, b=None) == ""


def test_query_repeats_lists_with_doseq() -> None:
    """_query repeats list values as separate query parameters"""
    assert _query(tags=["a", "b"]) == "?tags=a&tags=b"


def test_query_url_encodes_special_chars() -> None:
    """_query URL-encodes spaces and special characters"""
    assert _query(name="a b&c", path="x/y") == "?name=a+b%26c&path=x%2Fy"


@pytest.mark.asyncio
async def test_connection_helper_request_post_data() -> None:
    """ConnectionHelper.request handles POST with raw data body"""
    from python_takserver_api.class_helpers import ConnectionHelper

    class MockResponse:  # noqa: N801
        status: int = 201
        content_type: str = "text/plain"

        async def text(self) -> str:
            return "Created"

    class MockSession:  # noqa: N801
        async def post(self, url: str, **kwargs: Any) -> MockResponse:  # noqa: A003
            assert kwargs.get("data") == "raw body"
            assert "json" not in kwargs
            return MockResponse()

    class MockServer:  # noqa: N801
        session: Any = MockSession()

    helper = ConnectionHelper(MockServer(), "/fake/cert", "/fake/key")
    status, data = await helper.request("post", "http://example.com/api", data="raw body")
    assert status == 201
    assert data == "Created"


def _mission_envelope(contents: list[dict[str, Any]]) -> dict[str, Any]:
    """TAK 5.x Mission envelope wrapping a single mission object."""
    return {
        "version": 3,
        "type": "Mission",
        "data": [{"name": "alpha", "contents": contents}],
        "nodeId": "node-1",
    }


class ScriptedMockConnection:  # noqa: N801
    """Recording connection mock returning canned responses in order."""

    def __init__(self, responses: list[tuple[int, Any]]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, dict[str, Any] | None, Any, Any]] = []

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, Any] | None = None,
        json: dict[str, Any] | list[Any] | None = None,
        data: str | None = None,
    ) -> tuple[int, Any]:
        self.calls.append((method, url, headers, json, data))
        return self.responses.pop(0)


def _make_scripted_api(responses: list[tuple[int, Any]]) -> tuple[MissionApi, ScriptedMockConnection]:
    server = MockServer()
    conn = ScriptedMockConnection(responses)
    server.connection = conn
    return MissionApi(server), conn


@pytest.mark.asyncio
async def test_delete_content_keyword_by_hash_removes_keyword() -> None:
    """delete_content_keyword_by_hash reads the list and writes it back reduced"""
    envelope = _mission_envelope([{"hash": "h1", "uid": "u1", "keywords": ["a", "b"], "name": "doc.txt"}])
    api, conn = _make_scripted_api([(200, envelope), (200, {"ok": True})])

    status, data = await api.delete_content_keyword_by_hash("alpha", "h1", "a")

    assert status == 200
    assert data == {"ok": True}
    assert len(conn.calls) == 2
    method, url, headers, json_body, _ = conn.calls[0]
    assert (method, url) == (
        "get",
        "https://tak.example.com:8443/Marti/api/missions/alpha?changes=false&logs=false",
    )
    method, url, headers, json_body, _ = conn.calls[1]
    assert method == "put"
    assert url == "https://tak.example.com:8443/Marti/api/missions/alpha/content/h1/keywords"
    assert headers == {"Content-Type": "application/json"}
    assert json_body == ["b"]


@pytest.mark.asyncio
async def test_delete_content_keyword_by_uid_removes_keyword() -> None:
    """delete_content_keyword_by_uid writes back through the uid endpoint"""
    envelope = _mission_envelope([{"hash": "h1", "uid": "u1", "keywords": ["a", "b", "c"]}])
    api, conn = _make_scripted_api([(200, envelope), (200, {"ok": True})])

    status, data = await api.delete_content_keyword_by_uid("alpha", "u1", "b")

    assert status == 200
    method, url, headers, json_body, _ = conn.calls[1]
    assert url == "https://tak.example.com:8443/Marti/api/missions/alpha/uid/u1/keywords"
    assert json_body == ["a", "c"]


@pytest.mark.asyncio
async def test_delete_content_keyword_absent_is_noop() -> None:
    """Deleting a keyword that is not present returns the list, no write"""
    envelope = _mission_envelope([{"hash": "h1", "uid": "u1", "keywords": ["a", "b"]}])
    api, conn = _make_scripted_api([(200, envelope)])

    status, data = await api.delete_content_keyword_by_hash("alpha", "h1", "zzz")

    assert status == 200
    assert data == ["a", "b"]
    assert len(conn.calls) == 1


@pytest.mark.asyncio
async def test_delete_content_keyword_content_missing_returns_404() -> None:
    """A content hash that is not in the mission yields a 404 and no write"""
    envelope = _mission_envelope([{"hash": "h1", "uid": "u1", "keywords": ["a"]}])
    api, conn = _make_scripted_api([(200, envelope)])

    status, data = await api.delete_content_keyword_by_uid("alpha", "nope", "a")

    assert status == 404
    assert "not found" in str(data)
    assert len(conn.calls) == 1


@pytest.mark.asyncio
async def test_delete_content_keyword_mission_error_passthrough() -> None:
    """A failing mission fetch is returned unchanged, no write attempted"""
    api, conn = _make_scripted_api([(500, "boom")])

    status, data = await api.delete_content_keyword_by_hash("alpha", "h1", "a")

    assert (status, data) == (500, "boom")
    assert len(conn.calls) == 1


@pytest.mark.asyncio
async def test_delete_content_keyword_works_with_unwrapped_mission() -> None:
    """A bare mission object (no envelope) is handled the same way"""
    bare_mission = {"name": "alpha", "contents": [{"hash": "h1", "keywords": ["x", "y"]}]}
    api, conn = _make_scripted_api([(200, bare_mission), (200, {"ok": True})])

    status, data = await api.delete_content_keyword_by_hash("alpha", "h1", "x")

    assert status == 200
    assert conn.calls[1][3] == ["y"]
