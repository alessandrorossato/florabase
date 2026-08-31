from datetime import UTC

from sqlalchemy import DateTime, Uuid

from florabase.botanical_identities.model import BotanicalIdentity, utc_now
from florabase.db.base import Base


def test_mapping_has_only_the_verified_contract() -> None:
    assert BotanicalIdentity.metadata is Base.metadata
    assert list(BotanicalIdentity.__table__.columns.keys()) == [
        "id",
        "scientific_name",
        "cultivar_name",
        "common_name",
        "created_at",
        "updated_at",
    ]
    assert isinstance(BotanicalIdentity.__table__.c.id.type, Uuid)
    assert isinstance(BotanicalIdentity.__table__.c.created_at.type, DateTime)
    assert isinstance(BotanicalIdentity.__table__.c.updated_at.type, DateTime)
    assert BotanicalIdentity.__table__.c.created_at.type.timezone is True
    assert BotanicalIdentity.__table__.c.updated_at.type.timezone is True


def test_application_defaults_are_uuid7_and_utc() -> None:
    id_default = BotanicalIdentity.__table__.c.id.default
    created_default = BotanicalIdentity.__table__.c.created_at.default

    assert id_default is not None
    assert created_default is not None
    assert id_default.arg({}).version == 7
    assert created_default.arg({}).tzinfo is UTC
    assert utc_now().tzinfo is UTC
