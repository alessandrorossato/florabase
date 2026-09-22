from typing import Literal, cast
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import (
    BotanicalIdentityCreate,
    BotanicalIdentityUpdate,
    IdentityCollectionCounts,
)
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing

UNIQUE_IDENTITY_CONSTRAINT = "uq_botanical_identities_name_cultivar_ci"


class BotanicalIdentityConflictError(Exception):
    def __init__(self, existing_id: UUID | None) -> None:
        self.existing_id = existing_id
        super().__init__("Botanical identity already exists")


class BotanicalIdentityReferencedError(Exception):
    pass


class BotanicalIdentityCoverReferencedError(Exception):
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
    from florabase.collection_photos.model import BotanicalIdentityCoverImage

    cover_count = database.scalar(
        select(func.count())
        .select_from(BotanicalIdentityCoverImage)
        .where(BotanicalIdentityCoverImage.botanical_identity_id == identity_id)
    )
    if cover_count:
        raise BotanicalIdentityCoverReferencedError
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


def list_botanical_identity_directory(
    database: Session,
) -> list[
    tuple[
        BotanicalIdentity,
        Literal["local", "external"] | None,
        str | None,
        IdentityCollectionCounts,
    ]
]:
    from florabase.attachments.model import Attachment, AttachmentState
    from florabase.collection_photos.model import BotanicalIdentityCoverImage

    compact_cover_kind = case(
        (BotanicalIdentityCoverImage.source_mode == "external", "external"),
        (
            (BotanicalIdentityCoverImage.source_mode == "local")
            & (Attachment.state == AttachmentState.ACTIVE),
            "local",
        ),
        else_=None,
    )
    # Aggregate before joining: one directory query with no row multiplication or N+1 loads.
    counts = [
        select(model.botanical_identity_id.label("identity_id"), func.count().label("total"))
        .where(model.lifecycle == "active")
        .group_by(model.botanical_identity_id)
        .subquery()
        for model in (SeedLot, Plant, PlantGroup)
    ]
    sowings = (
        select(SeedLot.botanical_identity_id.label("identity_id"), func.count().label("total"))
        .select_from(Sowing)
        .join(SeedLot, Sowing.seed_lot_id == SeedLot.id)
        .where(Sowing.lifecycle == "active")
        .group_by(SeedLot.botanical_identity_id)
        .subquery()
    )
    counts.insert(1, sowings)
    statement = (
        select(
            BotanicalIdentity,
            compact_cover_kind,
            BotanicalIdentityCoverImage.image_url,
            *[func.coalesce(c.c.total, 0) for c in counts],
        )
        .outerjoin(
            BotanicalIdentityCoverImage,
            BotanicalIdentityCoverImage.botanical_identity_id == BotanicalIdentity.id,
        )
        .outerjoin(Attachment, Attachment.id == BotanicalIdentityCoverImage.attachment_id)
        .order_by(
            func.lower(BotanicalIdentity.scientific_name),
            func.lower(BotanicalIdentity.cultivar_name).nulls_first(),
            BotanicalIdentity.id,
        )
    )
    for count in counts:
        statement = statement.outerjoin(count, count.c.identity_id == BotanicalIdentity.id)
    rows = database.execute(statement).all()
    return [
        (
            identity,
            cast(Literal["local", "external"] | None, cover_kind),
            external_cover_url,
            IdentityCollectionCounts(
                seed_lots=seeds, sowings=sown, plants=plants, plant_groups=groups
            ),
        )
        for identity, cover_kind, external_cover_url, seeds, sown, plants, groups in rows
    ]
