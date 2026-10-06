from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import utc_now
from florabase.saved_views.model import SavedView
from florabase.saved_views.schemas import SavedViewCreate, SavedViewUpdate
from florabase.saved_views.state import SavedViewSurface, canonical_state


class SavedViewConflictError(ValueError):
    pass


def list_views(
    database: Session, owner_id: UUID, surface: SavedViewSurface | None, offset: int = 0
) -> list[SavedView]:
    statement = select(SavedView).where(SavedView.owner_id == owner_id)
    if surface is not None:
        statement = statement.where(SavedView.surface == surface)
    return list(
        database.scalars(
            statement.order_by(SavedView.surface, func.lower(SavedView.name), SavedView.id)
            .offset(offset)
            .limit(100)
        )
    )


def get_view(database: Session, owner_id: UUID, view_id: UUID) -> SavedView | None:
    return database.scalar(
        select(SavedView).where(SavedView.id == view_id, SavedView.owner_id == owner_id)
    )


def _flush(database: Session) -> None:
    try:
        database.flush()
    except IntegrityError as exc:
        if getattr(exc.orig, "sqlstate", None) == "23505":
            raise SavedViewConflictError(
                "A Saved View with this name already exists on this surface"
            ) from exc
        raise


def create_view(database: Session, owner_id: UUID, payload: SavedViewCreate) -> SavedView:
    record = SavedView(owner_id=owner_id, **payload.model_dump())
    database.add(record)
    _flush(database)
    return record


def update_view(database: Session, record: SavedView, payload: SavedViewUpdate) -> SavedView:
    if payload.state is not None and payload.state_version is not None:
        record.state = canonical_state(
            SavedViewSurface(record.surface), payload.state_version, payload.state
        )
        record.state_version = payload.state_version
    if payload.name is not None:
        record.name = payload.name
    record.updated_at = utc_now()
    _flush(database)
    return record
