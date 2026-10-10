from uuid import uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from alembic import command

pytestmark = pytest.mark.integration


def test_empty_cycle_and_populated_downgrade_preserves_link(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    command.downgrade(config, "20261009_0039")
    command.upgrade(config, "head")
    ident, version = uuid7(), uuid7()
    try:
        with database_engine.begin() as db:
            db.execute(
                text(
                    "INSERT INTO botanical_identities(id,scientific_name,created_at,updated_at) "
                    "VALUES(:id,:name,now(),now())"
                ),
                {"id": ident, "name": f"Migration {ident}"},
            )
            db.execute(
                text(
                    "INSERT INTO wfo_links(identity_id,version,external_id,evidence,confirmed_at) "
                    "VALUES(:id,:v,'wfo-0000000001','{}',now())"
                ),
                {"id": ident, "v": version},
            )
        with pytest.raises(DBAPIError, match="Cannot downgrade with confirmed WFO links"):
            command.downgrade(config, "20261009_0039")
        with database_engine.begin() as db:
            assert db.scalar(text("SELECT version_num FROM alembic_version")) == "20261009_0041"
            assert (
                db.scalar(
                    text("SELECT version FROM wfo_links WHERE identity_id=:id"), {"id": ident}
                )
                == version
            )
            db.execute(text("DELETE FROM wfo_links WHERE identity_id=:id"), {"id": ident})
        command.downgrade(config, "20261009_0039")
        command.upgrade(config, "head")
    finally:
        command.upgrade(config, "head")
        with database_engine.begin() as db:
            db.execute(text("DELETE FROM botanical_identities WHERE id=:id"), {"id": ident})
