"""Live tests for the Submission API - local machine only.

Run locally only:  poetry run pytest live_tests/ -m live
NEVER in CI.

Read-only coverage for the input/config/counter endpoints, plus a
state-restoring toggle check of the store-and-forward chat flag.

Creation of new inputs / named streaming data feeds is BROKEN on the
reference server (5.7-RELEASE-43-HEAD): the server throws an NPE inside
its own validation and answers HTTP 400 regardless of body. Those
operations are wrapped anyway; guard tests pin that behaviour so a
fixing upgrade gets noticed.
"""

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
async def test_guard_create_input_still_broken(server) -> None:
    """createInput still fails with 400 (server-side NPE)."""
    body = {
        "name": "live-test-inp-guard",
        "protocol": "tls",
        "port": 8091,
        "auth": "X_509",
        "archive": False,
        "coreVersion": 2,
    }
    status, _ = await server.submission.create_input(body)
    assert status == 400


@pytest.mark.asyncio
async def test_guard_data_feed_creation_still_broken(server) -> None:
    """createDataFeed still fails with 400/500 (same validation NPE)."""
    status, certs_body = await server.submission.get_input_metrics()
    template = dict(certs_body[0]["input"])
    template["name"] = "live-test-df-guard"
    template["port"] = 8091
    template["archive"] = False
    status, _ = await server.submission.create_data_feed(template)
    assert status in (400, 500)
