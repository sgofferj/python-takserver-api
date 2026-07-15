"""Tests for mission package functions (build_mission_package, add_mission_package)"""

import io
import zipfile
import xml.etree.ElementTree as ET
from typing import Any

import pytest

from python_takserver_api.tak_mission_api import build_mission_package


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
    import json
    import base64

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
            parsed = json.loads(kwargs.get("data", ""))
            assert isinstance(parsed, str)
            base64.b64decode(parsed)
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
