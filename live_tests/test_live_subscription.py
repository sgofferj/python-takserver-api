"""Live tests for the Subscription API - local machine only.

Run locally only:  poetry run pytest live_tests/ -m live
NEVER in CI.

Read-only checks against the server's real connected clients, plus a
full mutation cycle on a SELF-CONNECTED throwaway client: a CoT socket
on port 8089 with a dedicated `live_test_sub_*` UID so that incognito
and filter operations only ever touch data these tests created.
"""

import asyncio
import datetime
import ssl
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
import pytest_asyncio

pytestmark = pytest.mark.live


def _cot_event(uid: str, callsign: str) -> str:
    """A contact-bearing placenta; without <contact>/<takv> metadata the
    server never lists the client in /subscriptions/all."""
    now = datetime.datetime.now(datetime.timezone.utc)
    t = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    stale = (now + datetime.timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return (
        f"<event version='2.0' uid='{uid}' type='a-f-G-U-C' how='m-g' "
        f"time='{t}' start='{t}' stale='{stale}' le='1000.0' ce='9999999.0' "
        f"lat='61.48' lon='23.73' hae='100.0'><detail>"
        f"<contact endpoint='*.*.*.*' phone='noreply' callsign='{callsign}'/>"
        f"<uid Droid='{callsign}'/>"
        f"<takv device='live-test' platform='live-test' os='1' version='1'/>"
        f"<__group name='Cyan' role='Team Member'/></detail></event>"
    )


@pytest_asyncio.fixture
async def own_subscription(server, live_host):
    """Throwaway user with an actual CoT connection -> own subscription."""
    from python_takserver_api import Server

    tag = uuid.uuid4().hex[:8]
    username = f"live_test_sub_{tag}"
    uid = f"live_test_uid_{tag}"

    status, _ = await server.user.create_or_update_file_user(
        username=username,
        password="Live-Test-Pw-9!",  # noqa: S106  # pragma: allowlist secret
    )
    assert status == 200

    # mint cert via makeCert.sh on the server host (same recipe as groups)
    import subprocess

    proc = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            "amp1.zt.gofferje.net",
            "sudo",
            "docker",
            "exec",
            "takserver-server-1",
            "sh",
            "-c",
            f"'cd /opt/tak/certs && ./makeCert.sh client {username}'",
        ],
        capture_output=True,
    )
    if proc.returncode != 0:
        await server.user.delete_user(username)
        pytest.skip(f"cannot mint test cert: {proc.stderr[:150]}")

    p12 = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "amp1.zt.gofferje.net",
            "sudo",
            "docker",
            "exec",
            "takserver-server-1",
            "cat",
            f"/opt/tak/certs/files/{username}.p12",
        ],
        capture_output=True,
    )
    tmpdir = Path("/tmp/opencode")
    tmpdir.mkdir(exist_ok=True)
    p12_file = tmpdir / f"{username}.p12"
    p12_file.write_bytes(p12.stdout)
    pem = tmpdir / f"{username}-combined.pem"
    pem.write_text("")
    for args in (["-clcerts", "-nokeys"], ["-nocerts"]):
        x = subprocess.run(
            ["openssl", "pkcs12", "-in", str(p12_file), "-nodes", "-legacy", "-passin", "pass:atakatak", *args],
            capture_output=True,
            text=True,
        )
        if x.returncode != 0:
            await server.user.delete_user(username)
            pytest.skip("openssl cannot process test cert")
        with open(pem, "a") as fh:
            fh.write(x.stdout)

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.load_cert_chain(str(pem), str(pem))
    reader, writer = await asyncio.open_connection(live_host, 8089, ssl=ctx)
    writer.write(_cot_event(uid, f"LTS_{tag}").encode())
    await writer.drain()

    async def _keepalive() -> None:
        """Periodic re-announce so the client stays in the registry."""
        try:
            while True:
                await asyncio.sleep(5)
                writer.write(_cot_event(uid, f"LTS_{tag}").encode())
                await writer.drain()
        except Exception:
            pass

    ka_task = asyncio.create_task(_keepalive())

    user_conn = Server(live_host, str(pem), str(pem), username=username)
    try:
        yield SimpleNamespace(admin=server, user=user_conn, uid=uid, username=username, writer=writer, ka_task=ka_task)
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        await user_conn.close()
        if await server.user.user_exists(username):
            await server.user.delete_user(username)
        subprocess.run(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "amp1.zt.gofferje.net",
                "sudo",
                "docker",
                "exec",
                "takserver-server-1",
                "sh",
                "-c",
                f"'rm -f /opt/tak/certs/files/{username}.*'",
            ],
            capture_output=True,
        )


@pytest.mark.asyncio
async def test_get_all_subscriptions(server) -> None:
    """The registry lists connected clients with their metadata."""
    status, subs = await server.subscriptions.get_all_subscriptions()
    assert status == 200
    assert isinstance(subs, list)
    assert all("clientUid" in s and "groups" in s for s in subs)


@pytest.mark.asyncio
async def test_get_single_subscription(server) -> None:
    """A known UID resolves to its full subscription record."""
    status, subs = await server.subscriptions.get_all_subscriptions()
    assert status == 200 and subs
    # transient entries with an empty UID exist in the registry; pick a
    # resolvable one
    uid = next(s["clientUid"] for s in subs if s["clientUid"])
    status, sub = await server.subscriptions.get_subscription(uid)
    assert status == 200
    assert sub["clientUid"] == uid


@pytest.mark.asyncio
async def test_bulk_groups_updated(server) -> None:
    """The bulk group-change trigger answers 200."""
    status, _ = await server.subscriptions.bulk_groups_updated(["nonexistent-user-xyz"])
    assert status == 200


@pytest.mark.asyncio
async def test_own_subscription_lifecycle(own_subscription) -> None:
    """Own client appears in the registry; incognito + filter cycle works."""
    env = own_subscription

    async def in_registry() -> dict | None:
        _, subs = await env.admin.subscriptions.get_all_subscriptions()
        return next((s for s in subs if s["clientUid"] == env.uid), None)

    # wait for the CoT connection to register (poll up to ~15s)
    sub = None
    for _ in range(15):
        sub = await in_registry()
        if sub:
            break
        await asyncio.sleep(1)
    assert sub is not None, "own client never appeared in the registry"

    # stop announcing now - a fresh placenta would re-register the client
    # and reset any mutation we perform afterwards
    env.ka_task.cancel()

    status, single = await env.admin.subscriptions.get_subscription(env.uid)
    assert status == 200
    assert single["clientUid"] == env.uid

    # incognito toggle: answers 200 but does not change the flag on this
    # build (verified live 2026-08-25) - pin the endpoint's reachability
    _, before = await env.admin.subscriptions.get_subscription(env.uid)
    original = bool(before.get("incognito"))
    status, _ = await env.admin.subscriptions.toggle_incognito(env.uid)
    assert status == 200
    await asyncio.sleep(1)
    _, after = await env.admin.subscriptions.get_subscription(env.uid)
    assert bool(after.get("incognito")) is original  # quirk: unchanged

    # per-client filter: a Filter without a geospatialFilter element is
    # rejected with 400; use a minimal bounding-box filter
    geo_filter = (
        '<filter xmlns="http://bbn.com/marti/xml/config">'
        '<geospatialFilter filterTAKClients="true">'
        '<boundingBox minLongitude="0.0" minLatitude="0.0" '
        'maxLongitude="10.0" maxLatitude="10.0" '
        'minAltitude="0.0" maxAltitude="10000.0"/>'
        "</geospatialFilter></filter>"
    )
    status, _ = await env.admin.subscriptions.set_filter(env.uid, geo_filter)
    assert status == 200
    status, _ = await env.admin.subscriptions.delete_filter(env.uid)
    assert status == 200
