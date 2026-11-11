from datetime import UTC, datetime, timedelta
from typing import Literal, cast
from uuid import UUID

from sqlalchemy import case, delete, func, or_, select
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
    OperatorSynonymCreate,
    OperatorSynonymUpdate,
)
from florabase.cuttings.model import PropagationAttempt, VegetativeLot
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing

UNIQUE_IDENTITY_CONSTRAINT = "uq_botanical_identities_name_cultivar_ci"


class BotanicalIdentityNotFoundError(Exception):
    pass


class SynonymNotFoundError(Exception):
    pass


class SynonymValidationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class ImmutableHistoricalNameError(Exception):
    def __init__(
        self,
        message: str = (
            "Original recorded names and historical accepted names are immutable "
            "provenance evidence and cannot be modified or removed."
        ),
    ) -> None:
        self.message = message
        super().__init__(message)


class BotanicalIdentityConflictError(Exception):
    def __init__(
        self, existing_id: UUID | None, message: str = "Botanical identity already exists"
    ) -> None:
        self.existing_id = existing_id
        self.message = message
        super().__init__(message)


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


def remove_matching_operator_synonyms(
    database: Session,
    identity_id: UUID,
    scientific_name: str,
    cultivar_name: str | None,
) -> None:
    """Remove any operator_synonym rows that match the newly accepted name."""
    cultivar_filter = (
        BotanicalIdentityName.cultivar_name.is_(None)
        if cultivar_name is None
        else func.lower(BotanicalIdentityName.cultivar_name) == cultivar_name.lower()
    )
    database.execute(
        delete(BotanicalIdentityName).where(
            BotanicalIdentityName.botanical_identity_id == identity_id,
            BotanicalIdentityName.status_kind == "operator_synonym",
            func.lower(BotanicalIdentityName.scientific_name) == scientific_name.lower(),
            cultivar_filter,
        )
    )


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
    name_changed = (
        botanical_identity.scientific_name != payload.scientific_name
        or botanical_identity.cultivar_name != payload.cultivar_name
    )
    if name_changed:
        from florabase.botanical_identities.reconciliation import record_superseded_identity_name

        record_superseded_identity_name(
            database,
            botanical_identity,
            now=datetime.now(UTC),
            source_provider="operator",
        )
    for field, value in payload.model_dump().items():
        setattr(botanical_identity, field, value)
    if name_changed:
        remove_matching_operator_synonyms(
            database,
            botanical_identity.id,
            payload.scientific_name,
            payload.cultivar_name,
        )
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


def list_identity_synonyms(
    database: Session,
    identity_id: UUID,
    status_kind: str | None = None,
) -> list[BotanicalIdentityName]:
    identity = database.get(BotanicalIdentity, identity_id)
    if identity is None:
        raise BotanicalIdentityNotFoundError
    statement = (
        select(BotanicalIdentityName)
        .where(BotanicalIdentityName.botanical_identity_id == identity_id)
        .order_by(
            BotanicalIdentityName.effective_from.asc(),
            BotanicalIdentityName.id.asc(),
        )
    )
    if status_kind is not None:
        statement = statement.where(BotanicalIdentityName.status_kind == status_kind)
    return list(database.scalars(statement))


def _get_active_identity(database: Session, identity_id: UUID) -> BotanicalIdentity:
    identity = database.get(BotanicalIdentity, identity_id)
    if identity is None:
        raise BotanicalIdentityNotFoundError
    if identity.merged_into_id is not None:
        raise BotanicalIdentityMergedError(identity.merged_into_id)
    return identity


def _get_modifiable_operator_synonym(
    database: Session, identity_id: UUID, name_id: UUID
) -> tuple[BotanicalIdentity, BotanicalIdentityName]:
    identity = _get_active_identity(database, identity_id)
    entry = database.get(BotanicalIdentityName, name_id)
    if entry is None or entry.botanical_identity_id != identity_id:
        raise SynonymNotFoundError
    if entry.status_kind != "operator_synonym":
        raise ImmutableHistoricalNameError
    return identity, entry


def _validate_operator_synonym_target(
    database: Session,
    identity: BotanicalIdentity,
    scientific_name: str,
    cultivar_name: str | None,
    *,
    exclude_name_id: UUID | None = None,
) -> None:
    if (
        scientific_name.casefold() == identity.scientific_name.casefold()
        and (cultivar_name or "").casefold() == (identity.cultivar_name or "").casefold()
    ):
        raise SynonymValidationError(
            code="synonym_equals_accepted_name",
            message=(
                "The proposed synonym is identical to the current accepted name "
                "of this botanical identity."
            ),
        )

    cultivar_filter = (
        BotanicalIdentityName.cultivar_name.is_(None)
        if cultivar_name is None
        else func.lower(BotanicalIdentityName.cultivar_name) == cultivar_name.lower()
    )
    filters = [
        BotanicalIdentityName.botanical_identity_id == identity.id,
        func.lower(BotanicalIdentityName.scientific_name) == scientific_name.lower(),
        cultivar_filter,
    ]
    if exclude_name_id is not None:
        filters.append(BotanicalIdentityName.id != exclude_name_id)
    if database.scalar(select(BotanicalIdentityName).where(*filters)) is not None:
        raise SynonymValidationError(
            code="duplicate_identity_name",
            message="This botanical identity already has this synonym or historical name recorded.",
        )

    colliding = find_duplicate(database, scientific_name, cultivar_name)
    if colliding is not None and colliding.id != identity.id:
        raise BotanicalIdentityConflictError(
            colliding.id,
            message=(
                "Another active botanical identity already uses this name as its accepted name. "
                "Use duplicate-identity reconciliation to merge duplicate identities "
                "instead of adding it as a synonym."
            ),
        )


def _flush_synonym_write(database: Session) -> None:
    try:
        with database.begin_nested():
            database.flush()
    except IntegrityError as error:
        raise SynonymValidationError(
            code="duplicate_identity_name",
            message="This botanical identity already has this synonym or historical name recorded.",
        ) from error


def add_operator_synonym(
    database: Session,
    identity_id: UUID,
    payload: OperatorSynonymCreate,
) -> BotanicalIdentityName:
    identity = _get_active_identity(database, identity_id)
    _validate_operator_synonym_target(
        database, identity, payload.scientific_name, payload.cultivar_name
    )

    now = datetime.now(UTC)
    entry = BotanicalIdentityName(
        botanical_identity_id=identity.id,
        scientific_name=payload.scientific_name,
        cultivar_name=payload.cultivar_name,
        common_name=payload.common_name,
        authorship=payload.authorship,
        status_kind="operator_synonym",
        source_provider="operator",
        source_version=payload.source_citation,
        source_taxon_id=None,
        accepted_source_taxon_id=None,
        origin_identity_id=None,
        effective_from=now,
        superseded_at=now,
        created_at=now,
    )
    database.add(entry)
    identity.updated_at = max(now, identity.updated_at + timedelta(microseconds=1))
    _flush_synonym_write(database)
    return entry


def update_operator_synonym(
    database: Session,
    identity_id: UUID,
    name_id: UUID,
    payload: OperatorSynonymUpdate,
) -> BotanicalIdentityName:
    identity, entry = _get_modifiable_operator_synonym(database, identity_id, name_id)
    _validate_operator_synonym_target(
        database,
        identity,
        payload.scientific_name,
        payload.cultivar_name,
        exclude_name_id=name_id,
    )

    now = datetime.now(UTC)
    entry.scientific_name = payload.scientific_name
    entry.cultivar_name = payload.cultivar_name
    entry.common_name = payload.common_name
    entry.authorship = payload.authorship
    entry.source_version = payload.source_citation
    identity.updated_at = max(now, identity.updated_at + timedelta(microseconds=1))
    _flush_synonym_write(database)
    return entry


def remove_operator_synonym(
    database: Session,
    identity_id: UUID,
    name_id: UUID,
) -> None:
    identity, entry = _get_modifiable_operator_synonym(database, identity_id, name_id)
    now = datetime.now(UTC)
    database.delete(entry)
    identity.updated_at = max(now, identity.updated_at + timedelta(microseconds=1))
    database.flush()
