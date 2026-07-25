#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# tak_mission_api.py from https://github.com/sgofferj/takserver-api-python
#
# Copyright Stefan Gofferje
#
# Licensed under the Gnu General Public License Version 3 or higher (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.gnu.org/licenses/gpl-3.0.en.html
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either expressed or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


"""Mission API - https://docs.tak.gov/api/takserver#tag/mission-api"""

import io
import json
import zipfile
import uuid
import time

from typing import Any


# pylint: disable=too-many-arguments, too-many-positional-arguments, too-many-locals
def build_mission_package(
    name: str,
    mission_name: str,
    mission_server: str,
    creator_uid: str,
    cot_files: dict[str, str | bytes],
    resource_files: dict[str, tuple[bytes, str, str, str]] | None = None,
    groups: list[str] | None = None,
) -> bytes:
    """Build a TAK mission package ZIP in memory.

    Parameters:
        name: Human-readable package name (e.g. "POI Export")
        mission_name: The TAK mission name
        mission_server: Server identifier (e.g. "tak.example.com:8443:ssl")
        creator_uid: UID of the creating client
        cot_files: Map of UID -> CoT XML string or bytes
        resource_files: Map of path -> (content, mimeType, name, resource_uid)
        groups: List of group names for access control

    Returns:
        bytes of the ZIP file ready for upload
    """
    package_uid = str(uuid.uuid4())

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        lines = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<MissionPackageManifest version="2">',
            "  <Configuration>",
            f'    <Parameter name="uid" value="{package_uid}"/>',
            f'    <Parameter name="name" value="{name}"/>',
            '    <Parameter name="mission_guid" value=""/>',
            f'    <Parameter name="creatorUid" value="{creator_uid}"/>',
            f'    <Parameter name="create_time" value="{int(time.time() * 1000)}"/>',
            '    <Parameter name="expiration" value="-1"/>',
            '    <Parameter name="tool" value="public"/>',
            '    <Parameter name="onReceiveImport" value="true"/>',
            '    <Parameter name="onReceiveDelete" value="false"/>',
            f'    <Parameter name="mission_name" value="{mission_name}"/>',
            '    <Parameter name="mission_uid" value=""/>',
            f'    <Parameter name="mission_server" value="{mission_server}"/>',
            "  </Configuration>",
            "  <Contents>",
        ]

        for uid, cot_content in cot_files.items():
            if isinstance(cot_content, str):
                cot_content = cot_content.encode("utf-8")
            zf.writestr(f"cot/{uid}.cot", cot_content)
            lines.append(
                f'    <Content zipEntry="cot/{uid}.cot" ignore="false">'
                f'      <Parameter name="uid" value="{uid}"/>'
                "    </Content>"
            )

        if resource_files:
            now = time.strftime("%Y-%m-%dT%H:%M:%S.", time.gmtime()) + "000Z"
            for path, (content, mime_type, res_name, res_uid) in resource_files.items():
                zf.writestr(f"contents/{path}", content)
                lines.append(
                    f'    <Content zipEntry="contents/{path}" ignore="false"'
                    f' mimeType="{mime_type}" name="{res_name}" uid="{res_uid}"'
                    f' creatorUid="{creator_uid}" size="{len(content)}"'
                    f' submissionTime="{now}"/>'
                )

        lines.append("  </Contents>")

        if groups:
            lines.append("  <Groups>")
            for g in groups:
                lines.append(f'    <Group name="{g}"/>')
            lines.append("  </Groups>")

        lines.append('  <Role name="MISSION_SUBSCRIBER">')
        lines.append('    <Permissions name="MISSION_WRITE"/>')
        lines.append('    <Permissions name="MISSION_READ"/>')
        lines.append("  </Role>")

        lines.append("</MissionPackageManifest>")

        zf.writestr("MANIFEST/manifest.xml", "\n".join(lines))

    return buf.getvalue()


class MissionApi:
    """Mission API wrapper"""

    def __init__(self, server: Any) -> None:
        self.server = server

    async def get_mission(self, name: str) -> tuple[int, Any]:
        """Returns a mission"""
        path = f"/Marti/api/missions/{name}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, r

    async def get_mission_role(self, name: str) -> tuple[int, Any]:
        """Returns role in the mission"""
        path = f"/Marti/api/missions/{name}/role"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, r

    async def get_mission_subscriptions(self, name: str) -> tuple[int, Any]:
        """Returns subscriptions to the mission"""
        path = f"/Marti/api/missions/{name}/subscriptions"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, r

    async def get_mission_subscription_roles(self, name: str) -> tuple[int, Any]:
        """Returns subscriptions to the mission"""
        path = f"/Marti/api/missions/{name}/subscriptions/roles"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, r

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    async def create_mission(
        self,
        name: str,
        creator_uid: str,
        group: str = "",
        default_role: str = "",
        classification: str = "",
    ) -> tuple[int, Any]:
        """Creates a mission"""
        path = f"/Marti/api/missions/{name}?creatorUid={creator_uid}"
        if group:
            path += f"&group={group}"
        if default_role:
            path += f"&defaultRole={default_role}"
        if classification:
            path += f"&classification={classification}"
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("put", url)
        return s, r

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    async def create_mission_subscription(
        self,
        name: str,
        uid: str,
        topic: str = "",
        password: str = "",
        secago: str = "",
        start: str = "",
        end: str = "",
    ) -> tuple[int, Any]:
        """Creates a mission subscription"""
        path = f"/Marti/api/missions/{name}/subscription?uid={uid}"
        if topic:
            path += f"&topic={topic}"
        if password:
            path += f"&password={password}"
        if secago:
            path += f"&secago={secago}"
        if start:
            path += f"&start={start}"
        if end:
            path += f"&end={end}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("put", url, headers=headers)
        return s, r

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    async def set_mission_role(
        self, name: str, client_uid: str, username: str, role: str, token: str
    ) -> tuple[int, Any]:
        """Sets the role for a subscriber"""
        path = f"/Marti/api/missions/{name}/role?clientUid={client_uid}&username={username}&role={role}"
        url = self.server.api_base_url + path
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        s, r = await self.server.connection.request("put", url, headers=headers)
        return s, r

    async def add_mission_content(self, name: str, uids: list[str], my_uid: str, token: str) -> tuple[int, Any]:
        """Adds content to a mission"""
        path = f"/Marti/api/missions/{name}/contents?creatorUid={my_uid}"
        url = self.server.api_base_url + path
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        data = {"uids": uids}
        s, r = await self.server.connection.request("put", url, headers=headers, json=data)
        return s, r

    async def remove_mission_content(self, name: str, uid: str, my_uid: str, token: str) -> tuple[int, Any]:
        """Removes content from a mission"""
        path = f"/Marti/api/missions/{name}/contents?creatorUid={my_uid}&uid={uid}"
        headers = {"Authorization": f"Bearer {token}"}
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("delete", url, headers=headers)
        return s, r

    async def add_mission_package(
        self,
        name: str,
        creator_uid: str,
        token: str,
        mission_package: bytes,
    ) -> tuple[int, Any]:
        """Upload a mission package to a mission.

        The mission_package bytes can be created with build_mission_package().
        """
        path = f"/Marti/api/missions/{name}/contents/missionpackage?creatorUid={creator_uid}"
        url = self.server.api_base_url + path
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream"}
        s, r = await self.server.connection.request("put", url, headers=headers, data=mission_package)
        return s, r
