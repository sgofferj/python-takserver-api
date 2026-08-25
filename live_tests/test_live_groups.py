"""Live tests for the Group (channel subscription) API - local machine only.

Run locally only:  poetry run pytest live_tests/ -m live
NEVER in CI.

Strategy (FAT-WARNING compliant): every test operates exclusively on data it
created itself. Each test run

1. creates a throwaway file user `live-test-<tag>` via the User API,
2. assigns a dedicated group `live-test-grp-<tag>` to it (groups are
   implicit - assigning creates the group),
3. mints a client certificate for that user via `makeCert.sh` on the server
   host (SSH + docker exec; see CERT_SSH_HOST below) so that the test can
   connect AS THE THROWAWAY USER instead of touching any real account's
   channel state, and
4. wipes everything afterwards: connection closed, TAK user deleted (which
   also removes its implicit group), server-side cert files removed.

Why not enroll via password (`signClient`)? This server authenticates basic
auth against LDAP first and does NOT fall back to file-based users
(verified live 2026-08-25: LdapAuthenticator error 49, no FileAuthenticator
attempt). makeCert.sh signed by the server CA works regardless.
"""

import asyncio
import subprocess
import tempfile
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
import pytest_asyncio

from python_takserver_api import Server

pytestmark = pytest.mark.live

CERT_SSH_HOST = "amp1.zt.gofferje.net"
CERT_DOCKER_CONTAINER = "takserver-server-1"
CERT_PASSWORD = "atakatak"  # pragma: allowlist secret  # noqa: S105


def _ssh(*args: str, binary: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", CERT_SSH_HOST, *args],
        capture_output=True,
        text=not binary,
        timeout=60,
    )


def _provision_client_cert(tag: str, tmpdir: str) -> Path:
    """Mint a client cert for the throwaway user on the server host.

    Returns a combined PEM (cert + key) usable with Server(). Skips the test
    when the cert host is unreachable - live tests must degrade to skips on
    foreign machines.
    """
    cn = f"live-test-{tag}"
    r = _ssh(
        "sudo",
        "docker",
        "exec",
        CERT_DOCKER_CONTAINER,
        "sh",
        "-c",
        f"'cd /opt/tak/certs && ./makeCert.sh client {cn} >/dev/null 2>&1'",
    )
    if r.returncode != 0:
        pytest.skip(f"cannot mint test cert on {CERT_SSH_HOST}: {r.stderr[:200]}")
    p12 = _ssh("sudo", "docker", "exec", CERT_DOCKER_CONTAINER, "cat", f"/opt/tak/certs/files/{cn}.p12", binary=True)
    if p12.returncode != 0 or not p12.stdout:
        pytest.skip(f"cannot fetch test cert from {CERT_SSH_HOST}")
    p12_file = Path(tmpdir) / f"{cn}.p12"
    p12_file.write_bytes(p12.stdout)
    pem = Path(tmpdir) / f"{cn}-combined.pem"
    for args in (["-clcerts", "-nokeys"], ["-nocerts"]):
        x = subprocess.run(
            ["openssl", "pkcs12", "-in", str(p12_file), "-nodes", "-legacy", "-passin", f"pass:{CERT_PASSWORD}", *args],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if x.returncode != 0:
            pytest.skip(f"openssl cannot process test cert: {x.stderr[:200]}")
        with open(pem, "a") as fh:
            fh.write(x.stdout)
    return pem


def _remove_server_cert(tag: str) -> None:
    """Best-effort removal of the issued cert files on the server host."""
    cn = f"live-test-{tag}"
    _ssh(
        "sudo",
        "docker",
        "exec",
        CERT_DOCKER_CONTAINER,
        "sh",
        "-c",
        f"'rm -f /opt/tak/certs/files/{cn}.*'",
    )


@pytest_asyncio.fixture
async def group_env(server: Server, live_host: str):
    """Throwaway user + client cert as that user.

    Entitlements: two STABLE pre-existing channels (WOLF_ADSB via
    groupListOUT, WOLF_Family via groupList) so subscription writes have
    well-known targets, plus one dedicated `live-test-grp-<tag>` group
    whose implicit lifecycle (created by assignment, gone after user
    deletion) gets its own test. Brand-new groups are deliberately NOT
    used for subscription writes - the server applies those erratically
    for fresh users (verified live 2026-08-25).
    """
    tag = uuid.uuid4().hex[:8]
    username = f"live-test-{tag}"
    group = f"live-test-grp-{tag}"

    status, _ = await server.user.create_or_update_file_user(
        username=username,
        password="Live-Test-Pw-9!",  # noqa: S106  # pragma: allowlist secret
        group_list_out=["WOLF_ADSB"],
        group_list_both=["WOLF_Family", group],
    )
    assert status == 200

    with tempfile.TemporaryDirectory() as tmpdir:
        certfile = _provision_client_cert(tag, tmpdir)
        user_conn = Server(live_host, str(certfile), str(certfile), username=username)
        try:
            yield SimpleNamespace(
                admin=server,
                user=user_conn,
                username=username,
                group=group,
                stable_channels=("WOLF_ADSB", "WOLF_Family"),
            )
        finally:
            await user_conn.close()
            if await server.user.user_exists(username):
                status, _ = await server.user.delete_user(username)
                assert status == 200
            _remove_server_cert(tag)


@pytest.mark.asyncio
async def test_get_all_groups_shape(server) -> None:
    """get_all_groups returns a list of group dicts for the admin cert."""
    status, groups = await server.groups.get_all_groups()
    assert status == 200
    assert isinstance(groups, list)
    assert all({"name", "direction", "active"} <= set(g) for g in groups)


@pytest.mark.asyncio
async def test_get_group_cache_enabled(server) -> None:
    """The cache-enabled endpoint answers with a boolean payload."""
    status, enabled = await server.groups.get_group_cache_enabled()
    assert status == 200
    assert isinstance(enabled, bool)


@pytest.mark.asyncio
async def test_get_ldap_groups_readonly(server) -> None:
    """The LDAP group search endpoint is readable (empty on this server)."""
    status, data = await server.groups.get_ldap_groups("nonexistent-filter-xyz")
    assert status == 200


@pytest.mark.asyncio
async def test_channel_subscription_lifecycle(group_env) -> None:
    """Subscribe -> verify -> unsubscribe -> verify -> restore.

    Subscription truth is read via the ADMIN connection
    (`get_groups_for_user(username)`). QUARK verified live 2026-08-25:
    querying `/groups/user` with username == own principal returns the
    CONNECTION-bound state - empty for REST-only clients without a
    messaging session - while querying another user returns the persisted
    state instantly.
    """
    env = group_env

    async def subs() -> set[str]:
        _, r = await env.admin.groups.get_groups_for_user(env.username)
        return {g["name"] for g in (r or []) if g.get("active")}

    async def subs_becomes(expected: set[str], timeout: float = 30.0) -> None:
        """Poll until the subscription view converges (cache propagation)."""
        try:
            async with asyncio.timeout(timeout):
                while True:
                    if await subs() == expected:
                        return
                    await asyncio.sleep(2)
        except TimeoutError:
            pytest.fail(f"subscriptions did not converge to {expected}, got {await subs()}")

    adsb, family = env.stable_channels

    # all three entitled channels are available to the user
    _, all_groups = await env.user.groups.get_all_groups()
    available = {g["name"] for g in all_groups}
    assert {adsb, family, env.group} <= available
    assert await env.user.groups.channel_exists(adsb) is True

    # a freshly created user has NO subscriptions yet
    assert await subs() == set()

    # NOTE: the RMW helpers (subscribe/unsubscribe) are designed for
    # clients whose own connection-bound subscription view works (i.e.
    # ATAK-style clients with a messaging session). A REST-only client's
    # self-view is empty, so this test drives ABSOLUTE writes directly,
    # computing each new set from the admin-side readback.

    # subscribe ADSB (non-empty absolute write)
    status, _ = await env.user.groups.set_active_groups([(adsb, "OUT")])
    assert status == 200
    await subs_becomes({adsb})

    # add Family
    status, _ = await env.user.groups.set_active_groups([(adsb, "OUT"), (family, "OUT")])
    assert status == 200
    await subs_becomes({adsb, family})

    # drop ADSB again - Family must stay subscribed
    status, _ = await env.user.groups.set_active_groups([(family, "OUT")])
    assert status == 200
    await subs_becomes({family})
    assert await subs() == {family}

    # restore the exact original (empty) set
    status, _ = await env.user.groups.set_active_groups([])
    assert status == 200
    await subs_becomes(set())


@pytest.mark.asyncio
async def test_get_channels_view(group_env) -> None:
    """get_channels lists all entitled channels with collapsed duplicates."""
    env = group_env
    channels = await env.user.groups.get_channels()
    names = {c["name"] for c in channels}
    assert {"WOLF_ADSB", "WOLF_Family", env.group} <= names
    assert await env.user.groups.channel_exists(env.group) is True


@pytest.mark.asyncio
async def test_rmw_helpers_via_admin_username(group_env) -> None:
    """subscribe/unsubscribe/is_subscribed/get_active_groups with username=.

    The RMW helpers need a readable subscription view for their target.
    Self-views of REST-only clients are empty (see scope notes), but
    views queried for ANOTHER user return persisted truth instantly -
    so the admin connection drives the helpers on behalf of the
    throwaway user.
    """
    env = group_env
    adsb, family = env.stable_channels

    # nothing subscribed yet
    assert await env.admin.groups.get_active_groups(env.username) == []
    assert await env.admin.groups.is_subscribed(adsb, username=env.username) is False

    status, _ = await env.user.groups.subscribe(adsb, directions=["OUT"], username=env.username)
    assert status == 200
    active = await env.admin.groups.get_active_groups(env.username)
    assert [g["name"] for g in active] == [adsb]
    assert await env.admin.groups.is_subscribed(adsb, direction="OUT", username=env.username) is True

    status, _ = await env.user.groups.unsubscribe(adsb, directions=["OUT"], username=env.username)
    assert status == 200
    assert await env.admin.groups.is_subscribed(adsb, username=env.username) is False


@pytest.mark.asyncio
async def test_get_ldap_group_members_readonly(server) -> None:
    """The member-count endpoint answers for an existing group."""
    status, count = await server.groups.get_ldap_group_members(["WOLF_ADSB"])
    assert status == 200


@pytest.mark.asyncio
async def test_wait_for_group_update_on_admin_change(group_env) -> None:
    """The long-poll fires when an admin force-changes the user's groups.

    Polled via the ADMIN connection: the limited user cert gets 403 on
    `/groups/update/{username}` (verified live 2026-08-25).
    """
    env = group_env

    async def trigger() -> None:
        await asyncio.sleep(1.5)
        # freshly created users are sometimes unknown to the messaging
        # layer for a short while (force then answers 403) - retry
        for _ in range(5):
            status, _ = await env.admin.groups.set_active_groups_force(env.username, [(env.group, "OUT")])
            if status == 200:
                return
            await asyncio.sleep(3)
        pytest.fail(f"set_active_groups_force kept failing with {status}")

    task = asyncio.create_task(trigger())
    try:
        status, _ = await env.admin.groups.wait_for_group_update_until(env.username, timeout=20)
        assert status == 200
    except TimeoutError:
        pytest.fail("wait_for_group_update did not fire within 20s")
    finally:
        task.cancel()


@pytest.mark.asyncio
async def test_group_disappears_with_user(group_env) -> None:
    """Deleting the throwaway user removes its implicit group completely."""
    env = group_env
    status, names = await env.admin.user.get_all_group_names()
    assert status == 200
    assert env.group in [n["groupname"] for n in names]

    status, _ = await env.admin.user.delete_user(env.username)
    assert status == 200

    status, names = await env.admin.user.get_all_group_names()
    assert env.group not in [n["groupname"] for n in names]
