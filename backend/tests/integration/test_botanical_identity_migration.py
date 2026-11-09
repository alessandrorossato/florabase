import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect

from alembic import command

pytestmark = pytest.mark.integration


def test_upgrade_downgrade_and_reupgrade(database_engine: Engine) -> None:
    config = Config("alembic.ini")

    try:
        command.downgrade(config, "20260827_0001")
        assert not inspect(database_engine).has_table("botanical_identities")

        command.upgrade(config, "head")
        assert inspect(database_engine).has_table("botanical_identities")

        command.downgrade(config, "20260827_0001")
        assert not inspect(database_engine).has_table("botanical_identities")
    finally:
        command.upgrade(config, "head")

    assert inspect(database_engine).has_table("botanical_identities")


def test_authentication_migration_cycle_preserves_botanical_schema(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    botanical_columns_before = [
        column["name"] for column in inspect(database_engine).get_columns("botanical_identities")
    ]

    try:
        command.downgrade(config, "20260828_0002")
        inspector = inspect(database_engine)
        assert inspector.has_table("botanical_identities")
        assert not inspector.has_table("users")
        assert not inspector.has_table("auth_sessions")
        assert not inspector.has_table("login_throttles")

        command.upgrade(config, "head")
        inspector = inspect(database_engine)
        assert inspector.has_table("users")
        assert inspector.has_table("auth_sessions")
        assert inspector.has_table("login_throttles")
    finally:
        command.upgrade(config, "head")

    assert [
        column["name"] for column in inspect(database_engine).get_columns("botanical_identities")
    ] == botanical_columns_before


def test_accepted_name_reconciliation_migration_cycle_and_immutability_guards(
    database_engine: Engine,
) -> None:
    from datetime import UTC, datetime
    from uuid import uuid7

    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    config = Config("alembic.ini")
    try:
        command.downgrade(config, "20261109_0044")
        inspector = inspect(database_engine)
        assert not inspector.has_table("botanical_identity_names")
        assert not inspector.has_table("botanical_identity_reconciliations")
        cols_0044 = {c["name"] for c in inspector.get_columns("botanical_identities")}
        assert "merged_into_id" not in cols_0044

        command.upgrade(config, "head")
        inspector = inspect(database_engine)
        assert inspector.has_table("botanical_identity_names")
        assert inspector.has_table("botanical_identity_reconciliations")
        cols_head = {c["name"] for c in inspector.get_columns("botanical_identities")}
        assert {"merged_into_id", "merged_at"} <= cols_head

        ident_id = uuid7()
        rec_id = uuid7()
        now = datetime.now(UTC)
        with database_engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO botanical_identities "
                    "(id, scientific_name, created_at, updated_at) "
                    "VALUES (:id, 'Echinopsis lageniformis', :now, :now)"
                ),
                {"id": ident_id, "now": now},
            )
            conn.execute(
                text(
                    "INSERT INTO botanical_identity_reconciliations "
                    "(id, identity_id, kind, previous_scientific_name, applied_scientific_name, "
                    "source_provider, evidence, created_at) "
                    "VALUES (:rid, :iid, 'accepted_name_correction', 'Echinopsis lageniformis', "
                    "'Trichocereus bridgesii', 'operator', "
                    '\'{"format_version": "1"}\'::jsonb, :now)'
                ),
                {"rid": rec_id, "iid": ident_id, "now": now},
            )

        with pytest.raises(DBAPIError, match="immutable"), database_engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE botanical_identity_reconciliations "
                    "SET applied_scientific_name = 'Tampered' WHERE id = :rid"
                ),
                {"rid": rec_id},
            )

        with pytest.raises(DBAPIError, match="immutable"), database_engine.begin() as conn:
            conn.execute(
                text("DELETE FROM botanical_identity_reconciliations WHERE id = :rid"),
                {"rid": rec_id},
            )

        with pytest.raises(RuntimeError, match="Accepted-name reconciliations"):
            command.downgrade(config, "20261109_0044")
    finally:
        with database_engine.begin() as conn:
            if inspect(database_engine).has_table("botanical_identity_reconciliations"):
                conn.execute(
                    text(
                        "ALTER TABLE botanical_identity_reconciliations "
                        "DISABLE TRIGGER immutable_botanical_identity_reconciliation"
                    )
                )
                conn.execute(text("DELETE FROM botanical_identity_reconciliations"))
                conn.execute(
                    text(
                        "ALTER TABLE botanical_identity_reconciliations "
                        "ENABLE TRIGGER immutable_botanical_identity_reconciliation"
                    )
                )
            if inspect(database_engine).has_table("botanical_identity_names"):
                conn.execute(text("DELETE FROM botanical_identity_names"))
            conn.execute(text("DELETE FROM botanical_identities"))
        command.upgrade(config, "head")
