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
import zipfile
import uuid
import time

from typing import Any
from urllib.parse import urlencode


# pylint: disable=too-many-arguments, too-many-positional-arguments, too-many-locals
# pylint: disable=too-many-public-methods  # API wrapper: one method per endpoint
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


def _unwrap_mission(response: Any) -> Any:
    """Unwrap a TAK Mission response envelope to the mission object.

    TAK 5.x wraps mission payloads as ``{"version": 3, "type": "Mission",
    "data": [mission_object], "nodeId": ...}``. This returns the inner
    mission object when the envelope is present, otherwise the response
    unchanged.
    """
    if isinstance(response, dict):
        data = response.get("data")
        if isinstance(data, list) and data:
            return data[0]
    return response


def _content_keywords(
    mission: Any,
    *,
    content_hash: str | None = None,
    content_uid: str | None = None,
) -> list[str] | None:
    """Return the keyword list of a mission content item, or None if absent.

    Exactly one of content_hash/content_uid must identify the item. Items
    without a keywords field are treated as having an empty list.
    """
    mission_obj = _unwrap_mission(mission)
    contents = mission_obj.get("contents") if isinstance(mission_obj, dict) else None
    if not isinstance(contents, list):
        return None
    for item in contents:
        if not isinstance(item, dict):
            continue
        if content_hash is not None and item.get("hash") == content_hash:
            return _keyword_list(item)
        if content_uid is not None and item.get("uid") == content_uid:
            return _keyword_list(item)
    return None


def _keyword_list(item: dict[str, Any]) -> list[str]:
    """Return the keywords field of a content item as a list of strings."""
    keywords = item.get("keywords", [])
    if isinstance(keywords, list):
        return [k for k in keywords if isinstance(k, str)]
    return []


def _query(**params: Any) -> str:
    """Build a URL query string from non-None params.

    Booleans are rendered as ``true``/``false`` (TAK API convention), lists
    become repeated parameters, and everything is URL-encoded.
    """
    parts: dict[str, Any] = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            value = "true" if value else "false"
        parts[key] = value
    if not parts:
        return ""
    return "?" + urlencode(parts, doseq=True)


class MissionApi:
    """Mission API wrapper"""

    def __init__(self, server: Any) -> None:
        self.server = server

    async def get_mission(
        self,
        name: str,
        password: str | None = None,
        changes: bool = False,
        logs: bool = False,
        secago: int | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> tuple[int, Any]:
        """Returns a mission"""
        path = f"/Marti/api/missions/{name}" + _query(
            password=password, changes=changes, logs=logs, secago=secago, start=start, end=end
        )
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

    async def get_mission_count(
        self,
        password_protected: bool | None = None,
        default_role: str | None = None,
        tool: str | None = None,
    ) -> tuple[int, Any]:
        """Returns the number of missions on the server."""
        path = "/Marti/api/missioncount" + _query(
            passwordProtected=password_protected, defaultRole=default_role, tool=tool
        )
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def get_mission_names(
        self,
        password_protected: bool | None = None,
        default_role: str | None = None,
        tool: str | None = None,
    ) -> tuple[int, Any]:
        """Returns the names of all missions on the server."""
        path = "/Marti/api/missions" + _query(passwordProtected=password_protected, defaultRole=default_role, tool=tool)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def delete_mission_by_guid(
        self, guid: str, creator_uid: str | None = None, deep_delete: bool = False
    ) -> tuple[int, Any]:
        """Deletes a mission identified by GUID."""
        path = "/Marti/api/missions" + _query(guid=guid, creatorUid=creator_uid, deepDelete=deep_delete)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("delete", url)
        return s, r

    async def get_all_invitations(self, client_uid: str | None = None) -> tuple[int, Any]:
        """Returns all mission invitations across all missions."""
        path = "/Marti/api/missions/all/invitations" + _query(clientUid=client_uid)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def get_all_logs(self) -> tuple[int, Any]:
        """Returns the mission logs of all missions."""
        path = "/Marti/api/missions/all/logs"
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def get_all_subscriptions(self) -> tuple[int, Any]:
        """Returns the subscriptions of all missions."""
        path = "/Marti/api/missions/all/subscriptions"
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def get_all_subscriptions_by_guid(self) -> tuple[int, Any]:
        """Returns the subscriptions of all missions, keyed by mission GUID."""
        path = "/Marti/api/missions/all/subscriptions/guid"
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def get_invitations(self, client_uid: str) -> tuple[int, Any]:
        """Returns mission invitations for a specific client UID."""
        path = "/Marti/api/missions/invitations" + _query(clientUid=client_uid)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def get_paged_missions(
        self,
        page: int | None = None,
        pagesize: int | None = None,
        sort: str | None = None,
        name_filter: str | None = None,
        uid_filter: str | None = None,
        ascending: bool | None = None,
        password_protected: bool | None = None,
        default_role: str | None = None,
        tool: str | None = None,
    ) -> tuple[int, Any]:
        """Returns a page of missions with filtering and sorting."""
        path = "/Marti/api/pagedmissions" + _query(
            page=page,
            pagesize=pagesize,
            sort=sort,
            nameFilter=name_filter,
            uidFilter=uid_filter,
            ascending=ascending,
            passwordProtected=password_protected,
            defaultRole=default_role,
            tool=tool,
        )
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def get_log_entry(self, log_id: str) -> tuple[int, Any]:
        """Returns a single mission log entry."""
        path = f"/Marti/api/missions/logs/entries/{log_id}"
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def delete_log_entry(self, log_id: str) -> tuple[int, Any]:
        """Deletes a mission log entry."""
        path = f"/Marti/api/missions/logs/entries/{log_id}"
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("delete", url)
        return s, r

    async def create_log_entry(self, log_entry: dict[str, Any]) -> tuple[int, Any]:
        """Creates a mission log entry (see the LogEntry schema in the API spec)."""
        path = "/Marti/api/missions/logs/entries"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("post", url, headers=headers, json=log_entry)
        return s, r

    async def update_log_entry(self, log_entry: dict[str, Any]) -> tuple[int, Any]:
        """Updates a mission log entry (see the LogEntry schema in the API spec)."""
        path = "/Marti/api/missions/logs/entries"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("put", url, headers=headers, json=log_entry)
        return s, r

    async def delete_mission(
        self, name: str, creator_uid: str | None = None, deep_delete: bool = False
    ) -> tuple[int, Any]:
        """Deletes a mission. deep_delete also removes the mission content."""
        path = f"/Marti/api/missions/{name}" + _query(creatorUid=creator_uid, deepDelete=deep_delete)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("delete", url)
        return s, r

    async def get_mission_archive(self, name: str) -> tuple[int, Any]:
        """Returns a ZIP archive of the mission's content."""
        path = f"/Marti/api/missions/{name}/archive"
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def get_mission_changes(
        self,
        name: str,
        secago: int | None = None,
        start: str | None = None,
        end: str | None = None,
        squashed: bool = False,
    ) -> tuple[int, Any]:
        """Returns the change history of a mission."""
        path = f"/Marti/api/missions/{name}/changes" + _query(secago=secago, start=start, end=end, squashed=squashed)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def get_mission_children(self, name: str) -> tuple[int, Any]:
        """Returns the child missions of a mission."""
        path = f"/Marti/api/missions/{name}/children"
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def get_mission_contacts(self, name: str) -> tuple[int, Any]:
        """Returns the contacts subscribed to a mission."""
        path = f"/Marti/api/missions/{name}/contacts"
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def get_mission_cot(self, name: str, path: str | None = None) -> tuple[int, Any]:
        """Returns CoT events of a mission, optionally filtered by CoT path."""
        url_path = f"/Marti/api/missions/{name}/cot" + _query(path=path)
        url = self.server.api_base_url + url_path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def set_mission_expiration(self, name: str, expiration: int | None = None) -> tuple[int, Any]:
        """Sets the expiration time (epoch millis) of a mission."""
        path = f"/Marti/api/missions/{name}/expiration" + _query(expiration=expiration)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("put", url)
        return s, r

    async def get_mission_kml(self, name: str, download: bool = False) -> tuple[int, Any]:
        """Returns a KML representation of a mission's content."""
        path = f"/Marti/api/missions/{name}/kml" + _query(download=download)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def get_mission_parent(self, name: str) -> tuple[int, Any]:
        """Returns the parent mission of a mission."""
        path = f"/Marti/api/missions/{name}/parent"
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def send_mission(self, name: str) -> tuple[int, Any]:
        """Sends a mission to all subscribed users."""
        path = f"/Marti/api/missions/{name}/send"
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("post", url)
        return s, r

    async def set_content_keywords(
        self, name: str, content_hash: str, keywords: list[str], creator_uid: str | None = None
    ) -> tuple[int, Any]:
        """Sets the keywords of a mission content item (identified by its hash)."""
        path = f"/Marti/api/missions/{name}/content/{content_hash}/keywords" + _query(creatorUid=creator_uid)
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("put", url, headers=headers, json=keywords)
        return s, r

    async def delete_content_keywords(
        self, name: str, content_hash: str, creator_uid: str | None = None
    ) -> tuple[int, Any]:
        """Removes the keywords of a mission content item (identified by its hash)."""
        path = f"/Marti/api/missions/{name}/content/{content_hash}/keywords" + _query(creatorUid=creator_uid)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("delete", url)
        return s, r

    async def remove_mission_content_by_hash(
        self, name: str, content_hash: str, creator_uid: str | None = None
    ) -> tuple[int, Any]:
        """Removes a mission content item identified by its hash."""
        path = f"/Marti/api/missions/{name}/contents" + _query(hash=content_hash, creatorUid=creator_uid)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("delete", url)
        return s, r

    async def create_external_data(self, name: str, creator_uid: str, external_data: dict[str, Any]) -> tuple[int, Any]:
        """Creates an external data entry in a mission (see ExternalMissionData in the API spec)."""
        path = f"/Marti/api/missions/{name}/externaldata" + _query(creatorUid=creator_uid)
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("post", url, headers=headers, json=external_data)
        return s, r

    async def delete_external_data(self, name: str, data_id: str, notes: str, creator_uid: str) -> tuple[int, Any]:
        """Deletes an external data entry from a mission."""
        path = f"/Marti/api/missions/{name}/externaldata/{data_id}" + _query(notes=notes, creatorUid=creator_uid)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("delete", url)
        return s, r

    async def change_external_data(
        self,
        name: str,
        data_id: str,
        creator_uid: str,
        notes: str,
        data: str | None = None,
    ) -> tuple[int, Any]:
        """Changes an external data entry in a mission."""
        path = f"/Marti/api/missions/{name}/externaldata/{data_id}/change" + _query(creatorUid=creator_uid, notes=notes)
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("post", url, headers=headers, data=data)
        return s, r

    async def invite_to_mission(self, name: str, creator_uid: str | None = None) -> tuple[int, Any]:
        """Invites the current user to a mission."""
        path = f"/Marti/api/missions/{name}/invite" + _query(creatorUid=creator_uid)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("post", url)
        return s, r

    async def set_mission_invite(
        self,
        name: str,
        invite_type: str,
        invitee: str,
        creator_uid: str,
        role: str | None = None,
    ) -> tuple[int, Any]:
        """Sets the invitation state of a user or group for a mission.

        invite_type is either "user" or "group".
        """
        path = f"/Marti/api/missions/{name}/invite/{invite_type}/{invitee}" + _query(creatorUid=creator_uid, role=role)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("put", url)
        return s, r

    async def delete_mission_invite(
        self, name: str, invite_type: str, invitee: str, creator_uid: str
    ) -> tuple[int, Any]:
        """Removes the invitation of a user or group for a mission.

        invite_type is either "user" or "group".
        """
        path = f"/Marti/api/missions/{name}/invite/{invite_type}/{invitee}" + _query(creatorUid=creator_uid)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("delete", url)
        return s, r

    async def set_mission_keywords(
        self, name: str, keywords: list[str], creator_uid: str | None = None
    ) -> tuple[int, Any]:
        """Sets the keywords of a mission."""
        path = f"/Marti/api/missions/{name}/keywords" + _query(creatorUid=creator_uid)
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("put", url, headers=headers, json=keywords)
        return s, r

    async def delete_mission_keywords(self, name: str, creator_uid: str | None = None) -> tuple[int, Any]:
        """Removes all keywords of a mission."""
        path = f"/Marti/api/missions/{name}/keywords" + _query(creatorUid=creator_uid)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("delete", url)
        return s, r

    async def delete_mission_keyword(self, name: str, keyword: str, creator_uid: str | None = None) -> tuple[int, Any]:
        """Removes a single keyword from a mission."""
        path = f"/Marti/api/missions/{name}/keywords/{keyword}" + _query(creatorUid=creator_uid)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("delete", url)
        return s, r

    async def set_mission_password(self, name: str, password: str, creator_uid: str | None = None) -> tuple[int, Any]:
        """Sets (or changes) the password of a mission."""
        path = f"/Marti/api/missions/{name}/password" + _query(password=password, creatorUid=creator_uid)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("put", url)
        return s, r

    async def clear_mission_password(self, name: str, creator_uid: str | None = None) -> tuple[int, Any]:
        """Removes the password from a mission."""
        path = f"/Marti/api/missions/{name}/password" + _query(creatorUid=creator_uid)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("delete", url)
        return s, r

    async def set_uid_keywords(
        self, name: str, uid: str, keywords: list[str], creator_uid: str | None = None
    ) -> tuple[int, Any]:
        """Sets the keywords of a mission content item (identified by its UID)."""
        path = f"/Marti/api/missions/{name}/uid/{uid}/keywords" + _query(creatorUid=creator_uid)
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("put", url, headers=headers, json=keywords)
        return s, r

    async def delete_uid_keywords(self, name: str, uid: str, creator_uid: str | None = None) -> tuple[int, Any]:
        """Removes the keywords of a mission content item (identified by its UID)."""
        path = f"/Marti/api/missions/{name}/uid/{uid}/keywords" + _query(creatorUid=creator_uid)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("delete", url)
        return s, r

    async def delete_content_keyword_by_hash(
        self,
        name: str,
        content_hash: str,
        keyword: str,
        creator_uid: str | None = None,
    ) -> tuple[int, Any]:
        """Removes a single keyword from a mission content item (by hash).

        The TAK API only supports replacing the whole keyword list or
        removing all keywords of a content item, so this convenience helper
        reads the current list from the mission, removes the keyword and
        writes the reduced list back.

        Returns (404, message) if the content item does not exist in the
        mission. Deleting a keyword that is not present is a no-op that
        returns (200, current_keywords) without touching the server.
        """
        status, mission = await self.get_mission(name)
        if status != 200:
            return status, mission
        keywords = _content_keywords(mission, content_hash=content_hash)
        if keywords is None:
            return 404, f"content {content_hash!r} not found in mission {name!r}"
        if keyword not in keywords:
            return 200, keywords
        remaining = [k for k in keywords if k != keyword]
        return await self.set_content_keywords(name, content_hash, remaining, creator_uid)

    async def delete_content_keyword_by_uid(
        self,
        name: str,
        uid: str,
        keyword: str,
        creator_uid: str | None = None,
    ) -> tuple[int, Any]:
        """Removes a single keyword from a mission content item (by UID).

        Same semantics as delete_content_keyword_by_hash(), identifying the
        content item by its UID instead of its hash.
        """
        status, mission = await self.get_mission(name)
        if status != 200:
            return status, mission
        keywords = _content_keywords(mission, content_uid=uid)
        if keywords is None:
            return 404, f"content {uid!r} not found in mission {name!r}"
        if keyword not in keywords:
            return 200, keywords
        remaining = [k for k in keywords if k != keyword]
        return await self.set_uid_keywords(name, uid, remaining, creator_uid)

    async def copy_mission(
        self,
        name: str,
        creator_uid: str,
        copy_name: str,
        copy_path: str | None = None,
        default_role: str | None = None,
        password: str | None = None,
    ) -> tuple[int, Any]:
        """Copies a mission to a new mission with the given name."""
        path = f"/Marti/api/missions/{name}/copy" + _query(
            creatorUid=creator_uid,
            copyName=copy_name,
            copyPath=copy_path,
            defaultRole=default_role,
            password=password,
        )
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("put", url)
        return s, r

    async def create_mission_feed(
        self,
        name: str,
        creator_uid: str,
        data_feed_uid: str,
        filter_polygon: str | None = None,
        filter_cot_types: str | None = None,
        filter_callsign: str | None = None,
    ) -> tuple[int, Any]:
        """Adds a data feed to a mission."""
        path = f"/Marti/api/missions/{name}/feed" + _query(
            creatorUid=creator_uid,
            dataFeedUid=data_feed_uid,
            filterPolygon=filter_polygon,
            filterCotTypes=filter_cot_types,
            filterCallsign=filter_callsign,
        )
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("post", url)
        return s, r

    async def delete_mission_feed(self, name: str, uid: str, creator_uid: str) -> tuple[int, Any]:
        """Removes a data feed from a mission."""
        path = f"/Marti/api/missions/{name}/feed/{uid}" + _query(creatorUid=creator_uid)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("delete", url)
        return s, r

    async def get_mission_invitations(self, name: str) -> tuple[int, Any]:
        """Returns the invitations of a mission."""
        path = f"/Marti/api/missions/{name}/invitations"
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def get_mission_layers(self, name: str) -> tuple[int, Any]:
        """Returns the layers of a mission."""
        path = f"/Marti/api/missions/{name}/layers"
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def delete_mission_layer(self, name: str, uid: str, creator_uid: str) -> tuple[int, Any]:
        """Deletes a layer from a mission."""
        path = f"/Marti/api/missions/{name}/layers" + _query(uid=uid, creatorUid=creator_uid)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("delete", url)
        return s, r

    async def create_mission_layer(
        self,
        name: str,
        layer_name: str,
        layer_type: str,
        uid: str | None = None,
        parent_uid: str | None = None,
        after_uid: str | None = None,
        creator_uid: str | None = None,
    ) -> tuple[int, Any]:
        """Creates a layer in a mission.

        layer_type is one of "Cot", "Imagery", "Video", "DataPackage".
        """
        path = f"/Marti/api/missions/{name}/layers" + _query(
            name=layer_name,
            type=layer_type,
            uid=uid,
            parentUid=parent_uid,
            afterUid=after_uid,
            creatorUid=creator_uid,
        )
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("put", url)
        return s, r

    async def set_mission_layer_parent(
        self,
        name: str,
        layer_uid: str,
        parent_uid: str | None = None,
        after_uid: str | None = None,
        creator_uid: str | None = None,
    ) -> tuple[int, Any]:
        """Moves a layer under a parent layer in a mission."""
        path = f"/Marti/api/missions/{name}/layers/parent" + _query(
            layerUid=layer_uid, parentUid=parent_uid, afterUid=after_uid, creatorUid=creator_uid
        )
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("put", url)
        return s, r

    async def get_mission_layer(self, name: str, layer_uid: str) -> tuple[int, Any]:
        """Returns a single layer of a mission."""
        path = f"/Marti/api/missions/{name}/layers/{layer_uid}"
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def rename_mission_layer(self, name: str, layer_uid: str, new_name: str, creator_uid: str) -> tuple[int, Any]:
        """Renames a layer of a mission."""
        path = f"/Marti/api/missions/{name}/layers/{layer_uid}/name" + _query(name=new_name, creatorUid=creator_uid)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("put", url)
        return s, r

    async def get_mission_log(
        self,
        name: str,
        secago: int | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> tuple[int, Any]:
        """Returns the mission log of a mission."""
        path = f"/Marti/api/missions/{name}/log" + _query(secago=secago, start=start, end=end)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def add_mission_maplayer(self, name: str, creator_uid: str, map_layer: dict[str, Any]) -> tuple[int, Any]:
        """Adds a map layer to a mission (see the MapLayer schema in the API spec)."""
        path = f"/Marti/api/missions/{name}/maplayers" + _query(creatorUid=creator_uid)
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("post", url, headers=headers, json=map_layer)
        return s, r

    async def update_mission_maplayer(self, name: str, creator_uid: str, map_layer: dict[str, Any]) -> tuple[int, Any]:
        """Updates a map layer of a mission (see the MapLayer schema in the API spec)."""
        path = f"/Marti/api/missions/{name}/maplayers" + _query(creatorUid=creator_uid)
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("put", url, headers=headers, json=map_layer)
        return s, r

    async def delete_mission_maplayer(self, name: str, uid: str, creator_uid: str) -> tuple[int, Any]:
        """Deletes a map layer from a mission."""
        path = f"/Marti/api/missions/{name}/maplayers/{uid}" + _query(creatorUid=creator_uid)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("delete", url)
        return s, r

    async def get_mission_token(self, name: str, password: str | None = None) -> tuple[int, Any]:
        """Returns a bearer token for a mission."""
        path = f"/Marti/api/missions/{name}/token" + _query(password=password)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def get_mission_subscription(self, name: str, uid: str | None = None) -> tuple[int, Any]:
        """Returns the subscription of a single UID to a mission."""
        path = f"/Marti/api/missions/{name}/subscription" + _query(uid=uid)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("get", url)
        return s, r

    async def delete_mission_subscription(
        self,
        name: str,
        uid: str | None = None,
        topic: str | None = None,
        disconnect_only: bool = False,
    ) -> tuple[int, Any]:
        """Unsubscribes a UID from a mission, or disconnects only its topics."""
        path = f"/Marti/api/missions/{name}/subscription" + _query(uid=uid, topic=topic, disconnectOnly=disconnect_only)
        url = self.server.api_base_url + path
        s, r = await self.server.connection.request("delete", url)
        return s, r

    async def create_mission_subscriptions(self, name: str, creator_uid: str, uids: list[str]) -> tuple[int, Any]:
        """Subscribes multiple UIDs to a mission in one call."""
        path = f"/Marti/api/missions/{name}/subscription" + _query(creatorUid=creator_uid)
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("post", url, headers=headers, json=uids)
        return s, r

    async def get_resource(self, hash_id: str) -> tuple[int, Any]:
        """Returns the resource records stored under a content hash."""
        path = f"/Marti/api/resources/{hash_id}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, r

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    async def search_sync(
        self,
        box: str | None = None,
        circle: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        min_altitude: float | None = None,
        max_altitude: float | None = None,
        filename: str | None = None,
        keyword: list[str] | None = None,
        mimetype: str | None = None,
        name: str | None = None,
        uid: str | None = None,
        hash: str | None = None,  # pylint: disable=redefined-builtin
        mission: str | None = None,
        tool: str | None = None,
    ) -> tuple[int, Any]:
        """Searches mission data sync contents.

        All parameters are optional filters; `box` is a bounding box
        ("minLon,minLat,maxLon,maxLat"), `circle` a
        "lat,lon,radius(meters)" query. `keyword` may be repeated.
        """
        path = "/Marti/api/sync/search" + _query(
            box=box,
            circle=circle,
            startTime=start_time,
            endTime=end_time,
            minAltitude=min_altitude,
            maxAltitude=max_altitude,
            filename=filename,
            keyword=keyword,
            mimetype=mimetype,
            name=name,
            uid=uid,
            hash=hash,
            mission=mission,
            tool=tool,
        )
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, r
