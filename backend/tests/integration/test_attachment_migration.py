import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import ProgrammingError

from alembic import command

pytestmark = pytest.mark.integration


def test_attachment_migration_upgrade_constraints_downgrade_and_reupgrade(
    database_engine: Engine,
) -> None:
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "20260909_0022")
        assert not inspect(database_engine).has_table("attachments")

        command.upgrade(config, "head")
        inspector = inspect(database_engine)
        assert inspector.has_table("attachments")
        assert [column["name"] for column in inspector.get_columns("attachments")] == [
            "id",
            "storage_key",
            "original_filename",
            "media_type",
            "byte_size",
            "sha256",
            "state",
            "created_at",
        ]
        with database_engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO attachments "
                    "(id, storage_key, original_filename, media_type, byte_size, sha256, "
                    "state, created_at) VALUES (gen_random_uuid(), :key, 'leaf.png', "
                    "'image/png', 1, :digest, 'active', now())"
                ),
                {"key": "objects/aa/" + "a" * 32, "digest": "a" * 64},
            )
        with pytest.raises(ProgrammingError, match="cannot downgrade"):
            command.downgrade(config, "20260909_0022")

        with database_engine.begin() as connection:
            connection.execute(text("DELETE FROM attachments"))
        command.downgrade(config, "20260909_0022")
        assert not inspect(database_engine).has_table("attachments")
    finally:
        command.upgrade(config, "head")

    assert inspect(database_engine).has_table("attachments")
