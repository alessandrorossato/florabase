from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid7

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.collection_views import api, service
from florabase.collection_views.schemas import DashboardCounts, DashboardResponse


def test_dashboard_uses_database_counts_and_a_bounded_recent_event_query() -> None:
    database = MagicMock()
    database.scalar.side_effect = [2, 3, 4, 5, 6, 7]
    with (
        patch(
            "florabase.collection_views.service.list_all_events", return_value=["event"]
        ) as events,
        patch(
            "florabase.collection_views.service.event_responses",
            return_value=[],
        ) as responses,
    ):
        result = service.dashboard(database)
    assert result.counts == DashboardCounts(
        active_plants=2,
        active_plant_groups=3,
        active_seed_lots=4,
        active_sowings=5,
        botanical_identities=6,
        events=7,
    )
    events.assert_called_once_with(database, limit=6)
    responses.assert_called_once_with(database, ["event"])


def test_identity_collection_is_scoped_to_stored_identity_relationships() -> None:
    database = MagicMock()
    identity_id = uuid7()
    now = datetime.now(UTC)
    identity = BotanicalIdentity(
        id=identity_id,
        scientific_name="Solanum betaceum",
        created_at=now,
        updated_at=now,
    )
    with (
        patch(
            "florabase.collection_views.service.get_botanical_identity",
            return_value=identity,
        ),
        patch("florabase.collection_views.service.list_seed_lots", return_value=[]) as seeds,
        patch("florabase.collection_views.service.list_sowings", return_value=[]) as sowings,
        patch("florabase.collection_views.service.list_plants", return_value=[]) as plants,
        patch("florabase.collection_views.service.list_plant_groups", return_value=[]) as groups,
        patch("florabase.collection_views.service.list_all_events", return_value=[]) as events,
    ):
        result = service.botanical_identity_collection(database, identity_id)
    assert result is not None
    assert result.identity.display_label == "Solanum betaceum"
    for scoped in (seeds, sowings, plants, groups):
        scoped.assert_called_once_with(database, identity_id)
    events.assert_called_once_with(database, botanical_identity_id=identity_id)


def test_identity_collection_missing_and_dashboard_api_are_thin() -> None:
    database = MagicMock()
    with patch(
        "florabase.collection_views.service.get_botanical_identity",
        return_value=None,
    ):
        assert service.botanical_identity_collection(database, uuid7()) is None

    response = DashboardResponse(
        counts=DashboardCounts(
            active_plants=0,
            active_plant_groups=0,
            active_seed_lots=0,
            active_sowings=0,
            botanical_identities=0,
            events=0,
        ),
        recent_events=[],
    )
    with patch("florabase.collection_views.api.dashboard", return_value=response):
        assert api.read_dashboard(MagicMock(), database) is response
