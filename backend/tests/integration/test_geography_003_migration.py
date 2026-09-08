from datetime import UTC, datetime
from uuid import uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Connection, Engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from alembic import command

pytestmark = pytest.mark.integration


def test_geography_003_preserves_existing_places_and_cycles(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    place_id = uuid7()
    identity_id = uuid7()
    seed_lot_id = uuid7()
    now = datetime.now(UTC)
    try:
        command.downgrade(config, "20260907_0019")
        with database_engine.begin() as connection:
            world = connection.execute(
                text("SELECT id FROM geographic_places WHERE parent_id IS NULL")
            ).scalar_one()
            connection.execute(
                text(
                    "INSERT INTO geographic_places "
                    "(id, name, parent_id, place_kind, created_at, updated_at) "
                    "VALUES (:id, 'Existing local place', :parent, 'custom', :now, :now)"
                ),
                {"id": place_id, "parent": world, "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO botanical_identities "
                    "(id, scientific_name, created_at, updated_at) "
                    "VALUES (:id, 'Testa migratoria', :now, :now)"
                ),
                {"id": identity_id, "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO seed_lots "
                    "(id, botanical_identity_id, material_provenance_place_id, "
                    "created_at, updated_at) "
                    "VALUES (:id, :identity_id, :place_id, :now, :now)"
                ),
                {
                    "id": seed_lot_id,
                    "identity_id": identity_id,
                    "place_id": place_id,
                    "now": now,
                },
            )
        command.upgrade(config, "20260908_0020")
        with database_engine.begin() as connection:
            row = connection.execute(
                text("SELECT parent_id, place_type FROM geographic_places WHERE id=:id"),
                {"id": place_id},
            ).one()
            assert row[0] == world
            assert row[1] == "other_named_area"
            retained_place = connection.execute(
                text("SELECT material_provenance_place_id FROM seed_lots WHERE id=:id"),
                {"id": seed_lot_id},
            ).scalar_one()
            assert retained_place == place_id
            connection.execute(text("DELETE FROM seed_lots WHERE id=:id"), {"id": seed_lot_id})
            connection.execute(text("DELETE FROM geographic_places WHERE id=:id"), {"id": place_id})
            connection.execute(
                text("DELETE FROM botanical_identities WHERE id=:id"), {"id": identity_id}
            )
        command.downgrade(config, "20260907_0019")
        assert not inspect(database_engine).has_table("provenance_sites")
        command.upgrade(config, "20260908_0020")
        assert inspect(database_engine).has_table("provenance_sites")
    finally:
        command.upgrade(config, "head")


@pytest.mark.parametrize(
    ("latitude", "longitude", "accuracy"),
    [("1", None, None), ("91", "0", None), (None, None, "1")],
)
def test_provenance_site_database_coordinate_constraints(
    database_connection: Connection,
    latitude: str | None,
    longitude: str | None,
    accuracy: str | None,
) -> None:
    now = datetime.now(UTC)
    with pytest.raises(IntegrityError), database_connection.begin_nested():
        database_connection.execute(
            text(
                "INSERT INTO provenance_sites "
                "(id, name, latitude, longitude, coordinate_accuracy_m, created_at, updated_at) "
                "VALUES (:id, 'Invalid site', :latitude, :longitude, :accuracy, :now, :now)"
            ),
            {
                "id": uuid7(),
                "latitude": latitude,
                "longitude": longitude,
                "accuracy": accuracy,
                "now": now,
            },
        )


def test_geography_003_downgrade_refuses_to_discard_provenance_sites(
    database_engine: Engine,
) -> None:
    config = Config("alembic.ini")
    site_id = uuid7()
    now = datetime.now(UTC)
    try:
        with database_engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO provenance_sites (id, name, created_at, updated_at) "
                    "VALUES (:id, 'Retained origin', :now, :now)"
                ),
                {"id": site_id, "now": now},
            )
        with pytest.raises(DBAPIError, match="cannot downgrade while ProvenanceSite data"):
            command.downgrade(config, "20260907_0019")
        with database_engine.begin() as connection:
            connection.execute(text("DELETE FROM provenance_sites WHERE id=:id"), {"id": site_id})
        command.downgrade(config, "20260907_0019")
        command.upgrade(config, "20260908_0020")
    finally:
        command.upgrade(config, "head")
