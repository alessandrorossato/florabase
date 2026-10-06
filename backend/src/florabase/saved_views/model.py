from datetime import datetime
from uuid import UUID, uuid7

from pydantic import JsonValue
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from florabase.botanical_identities.model import utc_now
from florabase.db.base import Base
from florabase.saved_views.state import SavedViewSurface


class SavedView(Base):
    __tablename__ = "saved_views"
    __table_args__ = (
        CheckConstraint("char_length(name) BETWEEN 1 AND 120", name="ck_saved_views_name_length"),
        CheckConstraint("name = btrim(name) AND name !~ '[[:cntrl:]]'", name="ck_saved_views_name"),
        CheckConstraint(
            "surface IN (" + ", ".join(f"'{surface.value}'" for surface in SavedViewSurface) + ")",
            name="ck_saved_views_surface",
        ),
        CheckConstraint("state_version >= 1", name="ck_saved_views_version"),
        CheckConstraint(
            "jsonb_typeof(state) = 'object' AND octet_length(state::text) <= 8192",
            name="ck_saved_views_state",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    surface: Mapped[str] = mapped_column(String(32))
    state_version: Mapped[int] = mapped_column(Integer())
    state: Mapped[dict[str, JsonValue]] = mapped_column(JSONB())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


# Its owner/surface prefix serves both list paths; no JSON query index is needed.
Index(
    "uq_saved_views_owner_surface_name_ci",
    SavedView.owner_id,
    SavedView.surface,
    func.lower(SavedView.name),
    unique=True,
)
