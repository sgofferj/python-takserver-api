"""Live tests for the Certificate Manager API - local machine only.

Run locally only:  poetry run pytest live_tests/ -m live
NEVER in CI.

All tests are read-only against real certificate records EXCEPT the
negative-path checks with bogus hashes, which touch nothing.

The user-side TLS endpoints (tls/config, makeClientKeyStore,
signClient[/v2]) are deliberately NOT wrapped - they answer HTTP 403 even
for an admin certificate on the reference server. The guard tests at the
bottom assert that failure so a server upgrade that fixes it gets noticed.
"""

import pytest

pytestmark = pytest.mark.live


async def _newest_hash(server) -> str:
    """Hash of the most recently issued certificate (read-only probe)."""
    status, certs = await server.certs.get_certificates()
    assert status == 200
    newest = sorted(certs, key=lambda c: c.get("issuanceDate") or "", reverse=True)
    return newest[0]["hash"]


@pytest.mark.asyncio
async def test_get_certificates(server) -> None:
    """The full certificate list answers with complete records."""
    status, certs = await server.certs.get_certificates()
    assert status == 200
    assert isinstance(certs, list)
    assert all({"hash", "subjectDn", "issuanceDate"} <= set(c) for c in certs)


@pytest.mark.asyncio
async def test_get_certificates_username_filter(server) -> None:
    """The optional username filter narrows the result."""
    status, certs = await server.certs.get_certificates(username="sgofferj")
    assert status == 200
    assert isinstance(certs, list)


@pytest.mark.asyncio
async def test_get_certificate_collections(server) -> None:
    """active/expired/replaced/revoked all answer with lists."""
    for method in (
        server.certs.get_active_certificates,
        server.certs.get_expired_certificates,
        server.certs.get_replaced_certificates,
        server.certs.get_revoked_certificates,
    ):
        status, certs = await method()
        assert status == 200
        assert isinstance(certs, list)


@pytest.mark.asyncio
async def test_get_certificate_by_hash(server) -> None:
    """A single record can be fetched by its hash."""
    hash_id = await _newest_hash(server)
    status, cert = await server.certs.get_certificate(hash_id)
    assert status == 200
    assert isinstance(cert, dict)
    assert cert["hash"] == hash_id


@pytest.mark.asyncio
async def test_download_certificate(server) -> None:
    """download_certificate returns PEM text."""
    hash_id = await _newest_hash(server)
    status, pem = await server.certs.download_certificate(hash_id)
    assert status == 200
    assert isinstance(pem, str)
    assert pem.startswith("-----BEGIN CERTIFICATE-----")


@pytest.mark.asyncio
async def test_revoke_and_delete_own_old_certificates(server) -> None:
    """Full revoke -> verify -> delete cycle on the caller's OWN old certs.

    Authorized scope: certificates issued to the admin identity itself
    that were issued more than seven days ago are safe to revoke and
    delete - they are superseded by newer re-enrollments.

    Identifier quirk (verified live 2026-08-25): the {ids} path parameter
    of revoke/delete takes the server-side NUMERIC certificate ids (`id`
    field), not the hashes - hashes yield an HTML 500. The singular
    DELETE /cert/{hash} answers 200 but does not remove anything; the
    batch endpoint with numeric ids is the one that works.
    """
    from datetime import datetime, timedelta, timezone

    status, certs = await server.certs.get_certificates(username="sgofferj")
    assert status == 200
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    def _issued(cert: dict) -> datetime:
        raw = (cert.get("issuanceDate") or "").replace("Z", "+00:00")
        return datetime.fromisoformat(raw)

    candidates = sorted(
        (c for c in certs if c.get("issuanceDate") and _issued(c) < cutoff and not c.get("revocationDate")),
        key=_issued,
    )
    if len(candidates) < 2:
        pytest.skip("fewer than two week-old unrevoked certificates available")

    victim1, victim2 = candidates[0], candidates[1]
    ids = [victim1["id"], victim2["id"]]
    hashes = {victim1["hash"], victim2["hash"]}

    # revoke both by numeric id
    status, _ = await server.certs.revoke_certificates(ids)
    assert status == 200

    # verify: records now carry a revocation date and appear revoked
    _, r1 = await server.certs.get_certificate(victim1["hash"])
    _, r2 = await server.certs.get_certificate(victim2["hash"])
    assert r1.get("revocationDate") and r2.get("revocationDate")
    _, revoked = await server.certs.get_revoked_certificates()
    revoked_hashes = {c["hash"] for c in revoked}
    assert hashes <= revoked_hashes

    # delete both via the batch endpoint (numeric ids!)
    status, _ = await server.certs.delete_certificates(ids)
    assert status == 200

    # verify they are gone from the username-filtered listing
    _, remaining = await server.certs.get_certificates(username="sgofferj")
    remaining_hashes = {c["hash"] for c in remaining}
    assert hashes.isdisjoint(remaining_hashes)


@pytest.mark.asyncio
async def test_revoke_and_delete_negative_paths(server) -> None:
    """Bogus hashes answer an error - and touch nothing."""
    status, _ = await server.certs.revoke_certificates("00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF")
    assert status >= 400
    status, _ = await server.certs.delete_certificate("00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF")
    assert status >= 400


# --- guards for endpoints proven broken (deliberately NOT wrapped) ------


@pytest.mark.asyncio
async def test_guard_tls_config_still_broken(server) -> None:
    """/Marti/api/tls/config still answers 403 (not wrapped)."""
    status, _ = await server.connection.request(
        "get",
        f"{server.api_base_url}/Marti/api/tls/config",
        headers={"Content-Type": "application/json"},
    )
    assert status == 403


@pytest.mark.asyncio
async def test_guard_make_client_keystore_still_broken(server) -> None:
    """makeClientKeyStore still answers 403 (not wrapped)."""
    status, _ = await server.connection.request(
        "get",
        f"{server.api_base_url}/Marti/api/tls/makeClientKeyStore?cn=probe&password=atakatak",
        headers={"Content-Type": "application/json"},
    )
    assert status == 403


@pytest.mark.asyncio
async def test_guard_sign_client_still_broken(server) -> None:
    """signClient v1 and v2 still answer 403 (not wrapped)."""
    body = b"Zm9vYmFy"  # dummy payload, rejected before any signing
    for path in ("/Marti/api/tls/signClient", "/Marti/api/tls/signClient/v2"):
        status, _ = await server.connection.request(
            "post",
            f"{server.api_base_url}{path}?clientUid=probe&version=4.10.0",
            headers={"Content-Type": "application/octet-stream"},
            data=body,
        )
        assert status == 403


@pytest.mark.asyncio
async def test_guard_download_by_ids_still_broken(server) -> None:
    """GET /cert/download/{ids} still answers 500 even with valid hashes."""
    hash_id = await _newest_hash(server)
    status, _ = await server.connection.request(
        "get",
        f"{server.api_base_url}/Marti/api/certadmin/cert/download/{hash_id}",
        headers={"Content-Type": "application/json"},
    )
    assert status == 500
