from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import Connection, insert, inspect, text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import DBAPIError

from florabase.botanical_identities.model import BotanicalIdentity

pytestmark = pytest.mark.integration


def insert_identity(connection: Connection, **overrides: object) -> RowMapping:
    values: dict[str, object] = {
        "scientific_name": "Acer palmatum",
        "cultivar_name": None,
        "common_name": None,
    }
    values.update(overrides)
    result = connection.execute(
        insert(BotanicalIdentity)
        .values(**values)
        .returning(
            BotanicalIdentity.id,
            BotanicalIdentity.scientific_name,
            BotanicalIdentity.cultivar_name,
            BotanicalIdentity.common_name,
            BotanicalIdentity.created_at,
            BotanicalIdentity.updated_at,
        )
    )
    return result.mappings().one()


def assert_insert_rejected(connection: Connection, **values: object) -> None:
    with pytest.raises(DBAPIError), connection.begin_nested():
        insert_identity(connection, **values)


def test_schema_uses_native_types_named_constraints_and_only_one_botanical_table(
    database_connection: Connection,
) -> None:
    columns = {
        row.name: row
        for row in database_connection.execute(
            text(
                """
                SELECT column_name AS name, data_type, udt_name, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'botanical_identities'
                """
            )
        ).mappings()
    }
    tables = set(inspect(database_connection).get_table_names(schema="public"))
    constraints = {
        row.name
        for row in database_connection.execute(
            text(
                """
                SELECT conname AS name
                FROM pg_constraint
                WHERE conrelid = 'botanical_identities'::regclass
                """
            )
        ).mappings()
    }
    index_definition = database_connection.execute(
        text(
            """
            SELECT indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND indexname = 'uq_botanical_identities_name_cultivar_ci'
            """
        )
    ).scalar_one()

    assert list(columns) == [
        "id",
        "scientific_name",
        "cultivar_name",
        "common_name",
        "created_at",
        "updated_at",
    ]
    assert columns["id"].udt_name == "uuid"
    assert columns["created_at"].data_type == "timestamp with time zone"
    assert columns["updated_at"].data_type == "timestamp with time zone"
    assert columns["cultivar_name"].is_nullable == "YES"
    assert columns["common_name"].is_nullable == "YES"
    assert "pk_botanical_identities" in constraints
    assert "ck_botanical_identities_scientific_name_normalized" in constraints
    assert "ck_botanical_identities_cultivar_name_unquoted" in constraints
    assert "NULLS NOT DISTINCT" in index_definition
    assert "lower((scientific_name)::text)" in index_definition
    assert "lower((cultivar_name)::text)" in index_definition
    assert tables == {
        "alembic_version",
        "app_metadata",
        "auth_sessions",
        "botanical_identities",
        "botanical_profiles",
        "events",
        "geographic_places",
        "locations",
        "login_throttles",
        "operation_receipts",
        "plant_groups",
        "plants",
        "seed_lots",
        "sowings",
        "suppliers",
        "users",
    }


def test_valid_row_uses_application_uuid7_and_utc_timestamps(
    database_connection: Connection,
) -> None:
    row = insert_identity(
        database_connection,
        scientific_name="Solanum quitoense",
        common_name="Naranjilla",
    )

    assert isinstance(row["id"], UUID)
    assert row["id"].version == 7
    assert row["scientific_name"] == "Solanum quitoense"
    assert row["cultivar_name"] is None
    assert row["common_name"] == "Naranjilla"
    assert row["created_at"].tzinfo is not None
    assert row["created_at"].utcoffset() == UTC.utcoffset(datetime.now(UTC))
    assert row["updated_at"].tzinfo is not None
    assert row["updated_at"].utcoffset() == UTC.utcoffset(datetime.now(UTC))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("scientific_name", None),
        ("scientific_name", ""),
        ("scientific_name", " "),
        ("scientific_name", " Acer palmatum"),
        ("scientific_name", "Acer  palmatum"),
        ("scientific_name", "Acer\npalmatum"),
        ("scientific_name", "A" * 256),
        ("cultivar_name", ""),
        ("cultivar_name", "Blood  good"),
        ("cultivar_name", "Blood\tgood"),
        ("cultivar_name", "'Bloodgood'"),
        ("cultivar_name", "\u2018Bloodgood\u2019"),
        ("cultivar_name", "B" * 121),
        ("common_name", ""),
        ("common_name", "Japanese  maple"),
        ("common_name", "Japanese\nmaple"),
        ("common_name", "C" * 161),
    ],
)
def test_database_rejects_invalid_persisted_text(
    database_connection: Connection, field: str, value: object
) -> None:
    assert_insert_rejected(database_connection, **{field: value})


def test_case_insensitive_unqualified_duplicate_is_rejected(
    database_connection: Connection,
) -> None:
    insert_identity(database_connection, scientific_name="Solanum quitoense")

    assert_insert_rejected(database_connection, scientific_name="solanum quitoense")


def test_case_insensitive_cultivar_duplicate_is_rejected(
    database_connection: Connection,
) -> None:
    insert_identity(
        database_connection,
        scientific_name="Acer palmatum",
        cultivar_name="Bloodgood",
    )

    assert_insert_rejected(
        database_connection,
        scientific_name="acer palmatum",
        cultivar_name="bloodGOOD",
    )


def test_unqualified_and_cultivar_qualified_identities_can_coexist(
    database_connection: Connection,
) -> None:
    unqualified = insert_identity(database_connection)
    qualified = insert_identity(database_connection, cultivar_name="Bloodgood")

    assert unqualified["id"] != qualified["id"]
    assert unqualified["cultivar_name"] is None
    assert qualified["cultivar_name"] == "Bloodgood"


def test_optional_names_persist_as_null_or_normalized_values(
    database_connection: Connection,
) -> None:
    absent = insert_identity(database_connection, scientific_name="Acer rubrum")
    present = insert_identity(
        database_connection,
        scientific_name="Acer saccharum",
        cultivar_name="Legacy",
        common_name="Sugar maple",
    )

    assert absent["cultivar_name"] is None
    assert absent["common_name"] is None
    assert present["cultivar_name"] == "Legacy"
    assert present["common_name"] == "Sugar maple"
