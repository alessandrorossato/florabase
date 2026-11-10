from datetime import UTC, datetime
from typing import Literal, cast
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import (
    BotanicalIdentity,
    BotanicalIdentityName,
    BotanicalIdentityReconciliation,
)
from florabase.botanical_identities.schemas import (
    BotanicalIdentityCreate,
    BotanicalIdentityUpdate,
    IdentityCollectionCounts,
)
from florabase.cuttings.model import PropagationAttempt, VegetativeLot
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing

UNIQUE_IDENTITY_CONSTRAINT = "uq_botanical_identities_name_cultivar_ci"


class BotanicalIdentityConflictError(Exception):
    def __init__(self, existing_id: UUID | None) -> None:
        self.existing_id = existing_id
        super().__init__("Botanical identity already exists")


class BotanicalIdentityMergedError(Exception):
    def __init__(self, merged_into_id: UUID) -> None:
        self.merged_into_id = merged_into_id
        super().__init__("Botanical identity has been merged into another identity")


class BotanicalIdentityReferencedError(Exception):
    pass


class BotanicalIdentityCoverReferencedError(Exception):
    pass


def find_duplicate(
    database: Session, scientific_name: str, cultivar_name: str | None
) -> BotanicalIdentity | None:
    statement = select(BotanicalIdentity).where(
        BotanicalIdentity.merged_into_id.is_(None),
        func.lower(BotanicalIdentity.scientific_name) == scientific_name.lower(),
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
    if botanical_identity.merged_into_id is not None:
        raise BotanicalIdentityMergedError(botanical_identity.merged_into_id)
    existing = find_duplicate(database, payload.scientific_name, payload.cultivar_name)
    if existing is not None and existing.id != botanical_identity.id:
        raise BotanicalIdentityConflictError(existing.id)
    if (
        botanical_identity.scientific_name != payload.scientific_name
        or botanical_identity.cultivar_name != payload.cultivar_name
    ):
        from florabase.botanical_identities.reconciliation import record_superseded_identity_name

        record_superseded_identity_name(
            database,
            botanical_identity,
            now=datetime.now(UTC),
            source_provider="operator",
        )
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
    from florabase.native_range_enrichment.model import NativeRangeApplication

    # Serialize deletion with proposal Apply before checking retained references.
    if (
        database.scalar(
            select(BotanicalIdentity.id)
            .where(BotanicalIdentity.id == identity_id)
            .with_for_update()
        )
        is None
    ):
        return
    if botanical_identity.merged_into_id is not None:
        raise BotanicalIdentityReferencedError
    cover_count = database.scalar(
        select(func.count())
        .select_from(BotanicalIdentityCoverImage)
        .where(BotanicalIdentityCoverImage.botanical_identity_id == identity_id)
    )
    if cover_count:
        raise BotanicalIdentityCoverReferencedError
    from florabase.schedule.service import retained_reference

    if retained_reference(database, "botanical_identity", identity_id):
        raise BotanicalIdentityReferencedError
    references = (
        database.scalar(
            select(func.count())
            .select_from(NativeRangeApplication)
            .where(NativeRangeApplication.identity_id == identity_id)
        ),
        database.scalar(
            select(func.count())
            .select_from(BotanicalIdentityReconciliation)
            .where(
                or_(
                    BotanicalIdentityReconciliation.identity_id == identity_id,
                    BotanicalIdentityReconciliation.duplicate_identity_id == identity_id,
                )
            )
        ),
        database.scalar(
            select(func.count())
            .select_from(BotanicalIdentityName)
            .where(BotanicalIdentityName.origin_identity_id == identity_id)
        ),
        database.scalar(
            select(func.count())
            .select_from(BotanicalIdentity)
            .where(BotanicalIdentity.merged_into_id == identity_id)
        ),
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
    if any(references) or database.scalar(
        select(VegetativeLot.id).where(VegetativeLot.botanical_identity_id == identity_id).limit(1)
    ):
        raise BotanicalIdentityReferencedError
    database.delete(botanical_identity)
    database.flush()


def get_botanical_identity(
    database: Session, botanical_identity_id: UUID
) -> BotanicalIdentity | None:
    return database.get(BotanicalIdentity, botanical_identity_id)


def list_botanical_identities(database: Session) -> list[BotanicalIdentity]:
    statement = (
        select(BotanicalIdentity)
        .where(BotanicalIdentity.merged_into_id.is_(None))
        .order_by(
            func.lower(BotanicalIdentity.scientific_name),
            func.lower(BotanicalIdentity.cultivar_name).nulls_first(),
            BotanicalIdentity.id,
        )
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
    from florabase.collection_photos.model import BotanicalIdentityCoverImage, MediaAsset

    compact_cover_kind = case(
        (
            (MediaAsset.attachment_id.is_not(None))
            & (MediaAsset.state == "active")
            & (Attachment.state == AttachmentState.ACTIVE),
            "local",
        ),
        (BotanicalIdentityCoverImage.source_mode == "external", "external"),
        else_=None,
    )
    # Aggregate before joining: one directory query with no row multiplication or N+1 loads.
    counts = [
        select(model.botanical_identity_id.label("identity_id"), func.count().label("total"))
        .where(model.lifecycle == "active")
        .group_by(model.botanical_identity_id)
        .subquery()
        for model in (SeedLot, Plant, PlantGroup, VegetativeLot)
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
    counts.append(
        select(
            VegetativeLot.botanical_identity_id.label("identity_id"), func.count().label("total")
        )
        .select_from(PropagationAttempt)
        .join(VegetativeLot, PropagationAttempt.vegetative_lot_id == VegetativeLot.id)
        .where(PropagationAttempt.lifecycle == "active")
        .group_by(VegetativeLot.botanical_identity_id)
        .subquery()
    )
    statement = (
        select(
            BotanicalIdentity,
            compact_cover_kind,
            case(
                (
                    (MediaAsset.kind == "external") & (Attachment.state == AttachmentState.ACTIVE),
                    func.concat(
                        "/api/v1/media-assets/", MediaAsset.id, "/thumbnail?v=", Attachment.sha256
                    ),
                ),
                else_=MediaAsset.image_url,
            ),
            *[func.coalesce(c.c.total, 0) for c in counts],
        )
        .where(BotanicalIdentity.merged_into_id.is_(None))
        .outerjoin(
            BotanicalIdentityCoverImage,
            BotanicalIdentityCoverImage.botanical_identity_id == BotanicalIdentity.id,
        )
        .outerjoin(MediaAsset, MediaAsset.id == BotanicalIdentityCoverImage.media_asset_id)
        .outerjoin(Attachment, Attachment.id == MediaAsset.attachment_id)
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
            cover_url,
            IdentityCollectionCounts(
                seed_lots=seeds,
                sowings=sown,
                plants=plants,
                plant_groups=groups,
                vegetative_lots=lots,
                propagation_attempts=attempts,
            ),
        )
        for identity, cover_kind, cover_url, seeds, sown, plants, groups, lots, attempts in rows
    ]
