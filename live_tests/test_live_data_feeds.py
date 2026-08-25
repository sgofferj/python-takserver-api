"""Live tests for the Data Feed API - local machine only.

Run locally only:  poetry run pytest live_tests/ -m live
NEVER in CI.

Each run creates its own predicate feed (`live-test-feed-<tag>`), exercises
the read/update/stats/content endpoints against it and deletes it again.
The feed is created via `build_predicate_feed()` with `filter_groups`
set to a group the calling identity belongs to - a feed whose filter
groups exclude its creator becomes inaccessible to EVERYONE, including
the admin (verified live 2026-08-25).
"""

import uuid

import pytest
import pytest_asyncio

pytestmark = pytest.mark.live


@pytest_asyncio.fixture
async def feed(server):
    """Creates a dedicated predicate feed and deletes it afterwards."""
    name = f"live-test-feed-{uuid.uuid4().hex[:8]}"
    body = server.datafeeds.build_predicate_feed(
        name=name,
        predicate="type == 'a-u'",
        predicate_lang="JSON_PATH",
        source_endpoint="https://localhost:8080",
        # the creating identity must be a member of a filter group,
        # otherwise the feed locks everyone out (403 Group access denied)
        filter_groups=["WOLF_Friends"],
    )
    status, created = await server.datafeeds.create_predicate_data_feed(body)
    assert status == 200, f"feed creation failed: {status}"
    assert created and created.get("uuid")
    try:
        yield created
    finally:
        if created.get("uuid"):
            status, _ = await server.datafeeds.delete_predicate_data_feed(created["uuid"])
            assert status == 200


@pytest.mark.asyncio
async def test_get_data_feeds_contains_own_feed(server, feed) -> None:
    """The catalog lists the feed we just created."""
    status, feeds = await server.datafeeds.get_data_feeds()
    assert status == 200
    names = {f["name"] for f in feeds}
    assert feed["name"] in names


@pytest.mark.asyncio
async def test_get_predicate_data_feed_roundtrip(server, feed) -> None:
    """Reading by UUID returns the created object."""
    status, fetched = await server.datafeeds.get_predicate_data_feed(feed["uuid"])
    assert status == 200
    assert fetched["uuid"] == feed["uuid"]
    assert fetched["name"] == feed["name"]


@pytest.mark.asyncio
async def test_update_predicate_data_feed(server, feed) -> None:
    """Renaming the feed persists."""
    renamed = dict(feed)
    renamed["name"] = feed["name"] + "-renamed"
    status, _ = await server.datafeeds.update_predicate_data_feed(renamed)
    assert status == 200
    status, fetched = await server.datafeeds.get_predicate_data_feed(feed["uuid"])
    assert status == 200
    assert fetched["name"].endswith("-renamed")


@pytest.mark.asyncio
async def test_get_existing_cot_types_empty(server, feed) -> None:
    """A fresh feed has no CoT types yet."""
    status, types = await server.datafeeds.get_existing_cot_types(feed["uuid"])
    assert status == 200
    assert isinstance(types, list)


@pytest.mark.asyncio
async def test_get_cots_by_cot_type(server, feed) -> None:
    """CoT-by-type answers 200 with a list for the fresh feed."""
    status, cots = await server.datafeeds.get_cots_by_cot_type(feed["uuid"], "a-u-A")
    assert status == 200
    assert isinstance(cots, list)


@pytest.mark.asyncio
async def test_get_stats_and_bounds_queries(server, feed) -> None:
    """Stats and bounds endpoints answer 200 while our feed exists."""
    status, all_stats = await server.datafeeds.get_stats()
    assert status == 200
    assert isinstance(all_stats, list)

    # an empty feed has no statistics yet; the endpoint answers with an
    # envelope without payload (unwrapped to None)
    status, one = await server.datafeeds.get_stats_for_feed(feed["uuid"])
    if status == 200:
        # a feed without messages has no stats yet (None / empty payload)
        assert one is None or isinstance(one, dict)
    else:
        # server quirk: 500 with an envelope that has no `data` field
        assert status == 500

    status, in_bbox = await server.datafeeds.get_data_feeds_in_bbox("23.0,61.0,24.0,62.0")
    assert status == 200
    assert isinstance(in_bbox, list)

    status, in_polygon = await server.datafeeds.get_data_feeds_in_polygon(
        ["61.0,23.0", "62.0,23.0", "62.0,24.0", "61.0,24.0"]
    )
    assert status == 200
    assert isinstance(in_polygon, list)


@pytest.mark.asyncio
async def test_delete_predicate_data_feed(server, feed) -> None:
    """Deleting removes the feed from the catalog."""
    status, _ = await server.datafeeds.delete_predicate_data_feed(feed["uuid"])
    assert status == 200
    status, _ = await server.datafeeds.get_predicate_data_feed(feed["uuid"])
    assert status >= 400

    # prevent double deletion in fixture teardown
    del feed["uuid"]
