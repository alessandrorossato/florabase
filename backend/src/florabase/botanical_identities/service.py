from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityCreate, BotanicalIdentityUpdate
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot

UNIQUE_IDENTITY_CONSTRAINT = "uq_botanical_identities_name_cultivar_ci"


class BotanicalIdentityConflictError(Exception):
    def __init__(self, existing_id: UUID | None) -> None:
        self.existing_id = existing_id
        super().__init__("Botanical identity already exists")


class BotanicalIdentityReferencedError(Exception):
    pass


def find_duplicate(
    database: Session, scientific_name: str, cultivar_name: str | None
) -> BotanicalIdentity | None:
    statement = select(BotanicalIdentity).where(
        func.lower(BotanicalIdentity.scientific_name) == scientific_name.lower()
    )
    if cultivar_name is None:
        statement = statement.where(BotanicalIdentity.cultivar_name.is_(None))
    else:
        statement = statement.where(
            func.lower(BotanicalIdentity.cultivar_name) == cultivar_name.lower()
        )
    return database.scalars(statement).one_or_none()


def _constraint_name(error: IntegrityError) -> str | None:
    diagnostic = getattr(error.orig, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)
    return constraint_name if isinstance(constraint_name, str) else None


def create_botanical_identity(
    database: Session, payload: BotanicalIdentityCreate
) -> BotanicalIdentity:
    existing = find_duplicate(database, payload.scientific_name, payload.cultivar_name)
    if existing is not None:
        raise BotanicalIdentityConflictError(existing.id)

    botanical_identity = BotanicalIdentity(**payload.model_dump())
    try:
        with database.begin_nested():
            database.add(botanical_identity)
            database.flush()
    except IntegrityError as error:
        if _constraint_name(error) != UNIQUE_IDENTITY_CONSTRAINT:
            raise
        existing = find_duplicate(database, payload.scientific_name, payload.cultivar_name)
        raise BotanicalIdentityConflictError(
            existing.id if existing is not None else None
        ) from error
    return botanical_identity


def update_botanical_identity(
    database: Session,
    botanical_identity: BotanicalIdentity,
    payload: BotanicalIdentityUpdate,
) -> BotanicalIdentity:
    existing = find_duplicate(database, payload.scientific_name, payload.cultivar_name)
    if existing is not None and existing.id != botanical_identity.id:
        raise BotanicalIdentityConflictError(existing.id)
    for field, value in payload.model_dump().items():
        setattr(botanical_identity, field, value)
    try:
        with database.begin_nested():
            database.flush()
    except IntegrityError as error:
        if _constraint_name(error) != UNIQUE_IDENTITY_CONSTRAINT:
            raise
        existing = find_duplicate(database, payload.scientific_name, payload.cultivar_name)
        raise BotanicalIdentityConflictError(
            existing.id if existing is not None else None
        ) from error
    return botanical_identity


def delete_botanical_identity(database: Session, botanical_identity: BotanicalIdentity) -> None:
    identity_id = botanical_identity.id
    references = (
        database.scalar(
            select(func.count())
            .select_from(SeedLot)
            .where(SeedLot.botanical_identity_id == identity_id)
        ),
        database.scalar(
            select(func.count())
            .select_from(Plant)
            .where(Plant.botanical_identity_id == identity_id)
        ),
        database.scalar(
            select(func.count())
            .select_from(PlantGroup)
            .where(PlantGroup.botanical_identity_id == identity_id)
        ),
    )
    if any(references):
        raise BotanicalIdentityReferencedError
    database.delete(botanical_identity)
    database.flush()


def get_botanical_identity(
    database: Session, botanical_identity_id: UUID
) -> BotanicalIdentity | None:
    return database.get(BotanicalIdentity, botanical_identity_id)


def list_botanical_identities(database: Session) -> list[BotanicalIdentity]:
    statement = select(BotanicalIdentity).order_by(
        func.lower(BotanicalIdentity.scientific_name),
        func.lower(BotanicalIdentity.cultivar_name).nulls_first(),
        BotanicalIdentity.id,
    )
    return list(database.scalars(statement))
