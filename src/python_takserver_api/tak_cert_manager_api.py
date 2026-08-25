#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# tak_cert_manager_api.py from https://github.com/sgofferj/python-takserver-api
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


"""cert-manager-admin-api - server certificate administration

Admin-side certificate management: list issued certificates (all, active,
expired, replaced, revoked), inspect single certificates, download PEM
copies and revoke/delete certificates.

Requires an administrator certificate.

> **Deliberately NOT wrapped (verified broken on 5.7-RELEASE-43-HEAD,
> 2026-08-25):** the whole user-side `cert-manager-api` surface -
> `GET /Marti/api/tls/config`, `GET .../makeClientKeyStore`,
> `POST .../signClient[/v2]` - answers HTTP 403 even for an admin
> certificate, and `GET .../cert/download/{ids}` answers HTTP 500 even
> with valid hashes. See the Cert-Manager-API wiki page. Live tests
> assert these failures so a server upgrade that fixes them gets noticed.
"""

from typing import Any

from .class_helpers import unwrap_api_response


class CertManagerApi:
    """Certificate Manager (admin) API wrapper"""

    def __init__(self, server: Any) -> None:
        self.server = server

    @staticmethod
    def _unwrap(payload: Any) -> Any:
        return unwrap_api_response(payload)

    @staticmethod
    def _join_ids(ids: str | list[Any]) -> str:
        """Joins one or more certificate ids into a path segment"""
        if isinstance(ids, str):
            return ids
        return ",".join(str(i) for i in ids)

    async def get_certificates(self, username: str | None = None) -> tuple[int, Any]:
        """Returns all certificates known to the server.

        Each entry carries `hash` (the primary identifier used by the
        other operations), `subjectDn`, `userDn`, `clientUid`,
        `serialNumber`, `issuanceDate`, `expirationDate`,
        `revocationDate`, `certificate` and more.
        """
        path = "/Marti/api/certadmin/cert"
        if username is not None:
            path += f"?username={username}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def get_active_certificates(self) -> tuple[int, Any]:
        """Returns all currently active (valid, non-revoked) certificates"""
        path = "/Marti/api/certadmin/cert/active"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def get_expired_certificates(self) -> tuple[int, Any]:
        """Returns all expired certificates"""
        path = "/Marti/api/certadmin/cert/expired"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def get_replaced_certificates(self) -> tuple[int, Any]:
        """Returns all certificates that have been replaced by newer ones"""
        path = "/Marti/api/certadmin/cert/replaced"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def get_revoked_certificates(self) -> tuple[int, Any]:
        """Returns all revoked certificates"""
        path = "/Marti/api/certadmin/cert/revoked"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def get_certificate(self, hash_id: str) -> tuple[int, Any]:
        """Returns a single certificate record by its hash id"""
        path = f"/Marti/api/certadmin/cert/{hash_id}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, self._unwrap(r)

    async def download_certificate(self, hash_id: str) -> tuple[int, Any]:
        """Downloads a single certificate as PEM text.

        Note this differs from `GET .../cert/download/{ids}` (plural),
        which is broken on the reference server and therefore not wrapped.
        """
        path = f"/Marti/api/certadmin/cert/{hash_id}/download"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("get", url, headers=headers)
        return s, unwrap_api_response(r) if isinstance(r, dict) else r

    async def delete_certificate(self, hash_id: str) -> tuple[int, Any]:
        """Deletes a single certificate record by its hash id.

        > **SERVER BUG (verified live 2026-08-25):** this call answers
        > HTTP 200 but does NOT actually remove the record. Use
        > `delete_certificates([cert_id])` instead - the batch endpoint
        > with the NUMERIC certificate id works.
        """
        path = f"/Marti/api/certadmin/cert/{hash_id}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("delete", url, headers=headers)
        return s, self._unwrap(r)

    async def delete_certificates(self, ids: str | list[str]) -> tuple[int, Any]:
        """Deletes several certificate records.

        `ids` are the server-side NUMERIC certificate ids (`id` field of
        `get_certificates()` entries) - NOT the hashes. Verified live:
        batch deletion by numeric id removes the records, while the
        singular `delete_certificate(hash)` silently does nothing.
        """
        path = f"/Marti/api/certadmin/cert/delete/{self._join_ids(ids)}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("delete", url, headers=headers)
        return s, self._unwrap(r)

    async def revoke_certificates(self, ids: str | list[str]) -> tuple[int, Any]:
        """Revokes certificates.

        `ids` are the server-side NUMERIC certificate ids (`id` field of
        `get_certificates()` entries) - NOT the hashes. Passing hashes
        results in an HTML error page with HTTP 500. After revocation,
        the affected records carry a `revocationDate`.
        """
        path = f"/Marti/api/certadmin/cert/revoke/{self._join_ids(ids)}"
        url = self.server.api_base_url + path
        headers = {"Content-Type": "application/json"}
        s, r = await self.server.connection.request("delete", url, headers=headers)
        return s, self._unwrap(r)
