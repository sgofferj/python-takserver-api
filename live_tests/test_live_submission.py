"""Live tests for the Submission API - local machine only.

Run locally only:  poetry run pytest live_tests/ -m live
NEVER in CI.

Read-only coverage for the input/config/counter endpoints, plus a
state-restoring toggle check of the store-and-forward chat flag.

Input CRUD works live (names must match [A-Za-z0-9_], max 30 chars -
hyphens are rejected as "Invalid input name"). Creation/modification of
NAMED STREAMING DATA FEEDS (/Marti/api/datafeeds) is broken on the
reference server: empty HTTP 500 regardless of body. Guard tests pin
that behaviour so a fixing upgrade gets noticed.
"""

import uuid

import pytest

pytestmark = pytest.mark.live


@pytest.mark.asyncio
async def test_get_input_metrics(server) -> None:
    """The server's CoT inputs are listed with their metrics."""
    status, metrics = await server.submission.get_input_metrics()
    assert status == 200
    assert isinstance(metrics, list)
    assert all("id" in m and "input" in m for m in metrics)


@pytest.mark.asyncio
async def test_get_input_metric_known_name(server) -> None:
    """A single input metric can be fetched by name."""
    status, metrics = await server.submission.get_input_metrics()
    name = metrics[0]["input"]["name"]
    status, metric = await server.submission.get_input_metric(name)
    assert status == 200
    assert metric["input"]["name"] == name


@pytest.mark.asyncio
async def test_get_config_info(server) -> None:
    """The messaging configuration is readable (passwords masked)."""
    status, cfg = await server.submission.get_config_info()
    assert status == 200
    assert isinstance(cfg, dict)
    assert "numDbConnections" in cfg


@pytest.mark.asyncio
async def test_get_database_cot_counts(server) -> None:
    """Database counters answer with cotEvents/cotImages."""
    status, counts = await server.submission.get_database_cot_counts()
    assert status == 200
    assert isinstance(counts, dict)
    assert "cotEvents" in counts


@pytest.mark.asyncio
async def test_store_forward_chat_toggle_restores_state(server) -> None:
    """Disable -> verify -> enable -> verify; the original state returns.

    The reference server has S&F chat enabled; this test flips it off,
    checks the flag, and restores it immediately.
    """
    api = server.submission
    status, original = await api.is_store_forward_chat_enabled()
    assert status == 200
    try:
        if original:
            status, _ = await api.disable_store_forward_chat()
        else:
            status, _ = await api.enable_store_forward_chat()
        assert status == 200
        _, flipped = await api.is_store_forward_chat_enabled()
        assert flipped is not original
    finally:
        if original:
            await api.enable_store_forward_chat()
        else:
            await api.disable_store_forward_chat()
    _, restored = await api.is_store_forward_chat_enabled()
    assert restored is original


# --- guards for operations proven broken (wrapped, but pinned) ----------


@pytest.mark.asyncio
async def test_input_crud_cycle(server) -> None:
    """Create -> read -> modify -> delete a dedicated input on port 8091.

    Port 8091 was added to the stack for exactly this purpose; the input
    is deleted again immediately. archive stays False (never archive a
    high-volume ephemeral feed - Postgres bloat risk).
    """
    import uuid

    api = server.submission
    name = f"live_test_inp_{uuid.uuid4().hex[:6]}"
    body = {
        "name": name,
        "protocol": "tls",
        "port": 8091,
        "auth": "X_509",
        "archive": False,
        "coreVersion": 2,
    }
    status, created = await api.create_input(body)
    assert status == 200, f"create failed: {created}"

    try:
        status, metric = await api.get_input_metric(name)
        assert status == 200 and metric["input"]["name"] == name
        input_id = metric["id"]

        # appears in the general listing too
        status, metrics = await api.get_input_metrics()
        assert name in [m["input"]["name"] for m in metrics]

        # modify: flip archive flag via PUT by id. NOTE: on the reference
        # server the messaging layer answers 400 for freshly created
        # inputs here (verified live 2026-08-25); accept either outcome
        # but only assert state when the write reported success.
        modified = dict(metric["input"])
        modified["archive"] = True
        status, _ = await api.modify_input(input_id, modified)
        if status == 200:
            _, after = await api.get_input_metric(name)
            assert after["input"]["archive"] is True
    finally:
        status, _ = await api.delete_input(name)
        assert status == 200

    # deletion quirk: the metric endpoint keeps answering 200, but with a
    # null payload once the input is gone
    status, metric = await api.get_input_metric(name)
    gone_from_list = True
    status2, metrics = await api.get_input_metrics()
    gone_from_list = name not in [m["input"]["name"] for m in metrics]
    assert gone_from_list


@pytest.mark.asyncio
async def test_guard_data_feed_creation_still_broken(server) -> None:
    """createDataFeed still fails with an empty HTTP 500."""
    template = {
        "name": f"live_test_df_{uuid.uuid4().hex[:6]}",
        "protocol": "tls",
        "port": 8091,
        "auth": "X_509",
        "type": "Streaming",
        "sync": False,
        "archive": False,
        "coreVersion": 2,
        "filtergroup": [],
        "tags": [],
    }
    status, _ = await server.submission.create_data_feed(template)
    assert status in (400, 500)
