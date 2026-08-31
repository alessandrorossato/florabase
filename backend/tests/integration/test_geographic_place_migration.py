import pytest
from alembic.config import Config
from sqlalchemy import Connection, Engine, inspect, text

from alembic import command

pytestmark = pytest.mark.integration


def test_geographic_place_migration_upgrade_downgrade_reupgrade_and_paths(
    database_engine: Engine,
) -> None:
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "20260830_0006")
        assert not inspect(database_engine).has_table("geographic_places")
        command.upgrade(config, "head")
        assert inspect(database_engine).has_table("geographic_places")
        command.downgrade(config, "20260830_0006")
        assert not inspect(database_engine).has_table("geographic_places")
    finally:
        command.upgrade(config, "head")

    with database_engine.connect() as connection:
        assert (
            connection.execute(text("SELECT count(*) FROM geographic_places")).scalar_one() == 287
        )
        rows = connection.execute(
            text(
                "WITH RECURSIVE ancestry AS ("
                " SELECT id, name, parent_id, source_code, name::text AS path"
                " FROM geographic_places WHERE parent_id IS NULL"
                " UNION ALL"
                " SELECT child.id, child.name, child.parent_id, child.source_code,"
                " ancestry.path || ' → ' || child.name"
                " FROM geographic_places child JOIN ancestry ON child.parent_id = ancestry.id"
                ") SELECT source_code, path FROM ancestry"
                " WHERE source_code IN ('001', '005', 'BR', '035', 'TH')"
            )
        ).all()
        paths: dict[str, str] = {str(row[0]): str(row[1]) for row in rows}
        assert paths["001"] == "World"
        assert paths["005"] == "World → Americas → Latin America and the Caribbean → South America"
        assert paths["BR"] == paths["005"] + " → Brazil"
        assert paths["TH"] == "World → Asia → Southeast Asia → Thailand"
        brazil_id = connection.execute(
            text("SELECT id FROM geographic_places WHERE source_code = 'BR'")
        ).scalar_one()
        assert brazil_id.version == 7


def test_canonical_metadata_and_schema_are_reference_safe(
    database_connection: Connection,
) -> None:
    brazil = database_connection.execute(
        text(
            "SELECT place_kind, source_name, source_version, source_code_type, source_code, "
            "retired_at FROM geographic_places WHERE source_code = 'BR'"
        )
    ).one()
    assert tuple(brazil) == (
        "canonical",
        "unicode_cldr",
        "48.2.1",
        "iso_3166_1_alpha_2",
        "BR",
        None,
    )
    south_america = database_connection.execute(
        text("SELECT source_code_type FROM geographic_places WHERE source_code = '005'")
    ).scalar_one()
    assert south_america == "un_m49"
    foreign_keys = inspect(database_connection).get_foreign_keys("geographic_places")
    assert foreign_keys[0]["options"]["ondelete"] == "RESTRICT"
