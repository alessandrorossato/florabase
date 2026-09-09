from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_profiles.model import (
    PROFILE_FIELDS,
    BotanicalProfile,
    BotanicalProfileNativeRange,
)
from florabase.botanical_profiles.schemas import (
    BotanicalNativeRangeResponse,
    BotanicalProfilePut,
)
from florabase.geographic_places.model import GeographicPlace
from florabase.geographic_places.service import display_path, list_geographic_places


class BotanicalIdentityNotFoundError(Exception):
    pass


class EmptyProfileError(Exception):
    pass


class GeographicPlaceNotFoundError(Exception):
    pass


class BotanicalNativeRangeConflictError(Exception):
    pass


class BotanicalNativeRangeNotFoundError(Exception):
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


def _profile_has_structured_data(database: Session, botanical_identity_id: UUID) -> bool:
    return (
        database.scalar(
            select(func.count())
            .select_from(BotanicalProfileNativeRange)
            .where(BotanicalProfileNativeRange.botanical_profile_id == botanical_identity_id)
        )
        or 0
    ) > 0


def put_botanical_profile(
    database: Session,
    botanical_identity_id: UUID,
    payload: BotanicalProfilePut,
) -> PutProfileResult:
    if payload.is_empty:
        identity = database.scalar(
            select(BotanicalIdentity)
            .where(BotanicalIdentity.id == botanical_identity_id)
            .with_for_update()
        )
        if identity is None:
            raise BotanicalIdentityNotFoundError
        existing = database.scalar(
            select(BotanicalProfile)
            .where(BotanicalProfile.botanical_identity_id == botanical_identity_id)
            .with_for_update()
        )
        if existing is None:
            raise EmptyProfileError
        if _profile_has_structured_data(database, botanical_identity_id):
            for field in PROFILE_FIELDS:
                setattr(existing, field, None)
            database.flush()
            return PutProfileResult(profile=existing, created=False)
        database.delete(existing)
        database.flush()
        return PutProfileResult(profile=None, created=False)

    if not botanical_identity_exists(database, botanical_identity_id):
        raise BotanicalIdentityNotFoundError
    existing = get_botanical_profile(database, botanical_identity_id)

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


def list_botanical_native_ranges(
    database: Session, botanical_identity_id: UUID
) -> list[BotanicalNativeRangeResponse]:
    if not botanical_identity_exists(database, botanical_identity_id):
        raise BotanicalIdentityNotFoundError
    places = list_geographic_places(database)
    by_id = {place.id: place for place in places}
    native_ranges = list(
        database.scalars(
            select(BotanicalProfileNativeRange).where(
                BotanicalProfileNativeRange.botanical_profile_id == botanical_identity_id
            )
        )
    )
    responses = [
        BotanicalNativeRangeResponse.from_models(
            native_range,
            by_id[native_range.geographic_place_id],
            geographic_place_path=display_path(by_id[native_range.geographic_place_id], places),
        )
        for native_range in native_ranges
    ]
    return sorted(
        responses,
        key=lambda item: (item.geographic_place_path.casefold(), item.geographic_place_id),
    )


def add_botanical_native_range(
    database: Session,
    botanical_identity_id: UUID,
    geographic_place_id: UUID,
) -> BotanicalNativeRangeResponse:
    place = database.scalar(
        select(GeographicPlace).where(GeographicPlace.id == geographic_place_id).with_for_update()
    )
    if place is None:
        raise GeographicPlaceNotFoundError
    identity = database.scalar(
        select(BotanicalIdentity)
        .where(BotanicalIdentity.id == botanical_identity_id)
        .with_for_update()
    )
    if identity is None:
        raise BotanicalIdentityNotFoundError
    profile = database.scalar(
        select(BotanicalProfile)
        .where(BotanicalProfile.botanical_identity_id == botanical_identity_id)
        .with_for_update()
    )
    if profile is None:
        profile = BotanicalProfile(botanical_identity_id=botanical_identity_id)
        database.add(profile)
        database.flush()
    existing = database.get(
        BotanicalProfileNativeRange, (botanical_identity_id, geographic_place_id)
    )
    if existing is not None:
        raise BotanicalNativeRangeConflictError
    native_range = BotanicalProfileNativeRange(
        botanical_profile_id=botanical_identity_id,
        geographic_place_id=geographic_place_id,
    )
    database.add(native_range)
    database.flush()
    places = list_geographic_places(database)
    return BotanicalNativeRangeResponse.from_models(
        native_range,
        place,
        geographic_place_path=display_path(place, places),
    )


def remove_botanical_native_range(
    database: Session,
    botanical_identity_id: UUID,
    geographic_place_id: UUID,
) -> None:
    database.scalar(
        select(GeographicPlace).where(GeographicPlace.id == geographic_place_id).with_for_update()
    )
    identity = database.scalar(
        select(BotanicalIdentity)
        .where(BotanicalIdentity.id == botanical_identity_id)
        .with_for_update()
    )
    if identity is None:
        raise BotanicalIdentityNotFoundError
    profile = database.scalar(
        select(BotanicalProfile)
        .where(BotanicalProfile.botanical_identity_id == botanical_identity_id)
        .with_for_update()
    )
    if profile is None:
        raise BotanicalNativeRangeNotFoundError
    native_range = database.get(
        BotanicalProfileNativeRange, (botanical_identity_id, geographic_place_id)
    )
    if native_range is None:
        raise BotanicalNativeRangeNotFoundError
    database.delete(native_range)
    database.flush()
    if not _profile_has_structured_data(database, botanical_identity_id) and all(
        getattr(profile, field) is None for field in PROFILE_FIELDS
    ):
        database.delete(profile)
        database.flush()
