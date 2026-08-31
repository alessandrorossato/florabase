from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_profiles.model import BotanicalProfile
from florabase.botanical_profiles.schemas import BotanicalProfilePut


class BotanicalIdentityNotFoundError(Exception):
    pass


class EmptyProfileError(Exception):
    pass


@dataclass(frozen=True)
class PutProfileResult:
    profile: BotanicalProfile | None
    created: bool


def get_botanical_profile(
    database: Session, botanical_identity_id: UUID
) -> BotanicalProfile | None:
    return database.get(BotanicalProfile, botanical_identity_id)


def botanical_identity_exists(database: Session, botanical_identity_id: UUID) -> bool:
    return database.get(BotanicalIdentity, botanical_identity_id) is not None


def put_botanical_profile(
    database: Session,
    botanical_identity_id: UUID,
    payload: BotanicalProfilePut,
) -> PutProfileResult:
    if not botanical_identity_exists(database, botanical_identity_id):
        raise BotanicalIdentityNotFoundError

    existing = get_botanical_profile(database, botanical_identity_id)
    if payload.is_empty:
        if existing is None:
            raise EmptyProfileError
        database.delete(existing)
        database.flush()
        return PutProfileResult(profile=None, created=False)

    values = payload.model_dump()
    # SQLAlchemy's PostgreSQL Insert typing does not retain the ORM entity type through
    # ``excluded``; the statement remains runtime-checked and exercised against PostgreSQL.
    insert_statement = cast(Any, insert(BotanicalProfile))
    statement = (
        insert_statement.values(botanical_identity_id=botanical_identity_id, **values)
        .on_conflict_do_update(
            index_elements=[BotanicalProfile.botanical_identity_id],
            set_={
                "description": insert_statement.excluded.description,
                "origin_distribution": insert_statement.excluded.origin_distribution,
                "cultivation": insert_statement.excluded.cultivation,
                "uses": insert_statement.excluded.uses,
                "warnings": insert_statement.excluded.warnings,
            },
        )
        .returning(BotanicalProfile)
    )
    profile = database.scalars(statement.execution_options(populate_existing=True)).one()
    return PutProfileResult(profile=profile, created=existing is None)
