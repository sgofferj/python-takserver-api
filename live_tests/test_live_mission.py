"""Live tests for the Mission API - local machine only.

Run locally only:  poetry run pytest live_tests/ -m live
NEVER in CI. Never modify or delete pre-existing server data - only touch
data that these tests create themselves (missions named live-test-<uuid>).
"""

import uuid

import pytest

pytestmark = pytest.mark.live


@pytest.mark.asyncio
async def test_mission_crud(server) -> None:
    """Create, inspect, modify and delete a throwaway mission.

    The mission and its content are removed in a finally block so a failing
    assertion can never leave test data behind on the server.
    """
    name = f"live-test-{uuid.uuid4()}"
    creator_uid = f"live-test-uid-{uuid.uuid4()}"
    try:
        status, data = await server.mission.create_mission(name=name, creator_uid=creator_uid)
        assert status in (200, 201), data

        status, data = await server.mission.get_mission(name)
        assert status == 200, data
        assert name in str(data)

        status, data = await server.mission.get_mission_names()
        assert status == 200, data
        assert name in str(data)

        status, data = await server.mission.get_mission_count()
        assert status == 200, data

        status, data = await server.mission.create_mission_subscription(name=name, uid=creator_uid)
        assert status in (200, 201), data

        status, data = await server.mission.get_mission_subscriptions(name)
        assert status == 200, data
        assert creator_uid in str(data)

        status, data = await server.mission.set_mission_keywords(name, ["live-test"])
        assert status in (200, 201), data

        status, data = await server.mission.get_mission_changes(name)
        assert status == 200, data
    finally:
        status, data = await server.mission.delete_mission(name, creator_uid=creator_uid, deep_delete=True)
        assert status in (200, 404), (status, data)
