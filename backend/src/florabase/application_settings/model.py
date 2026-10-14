from sqlalchemy import CheckConstraint, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from florabase.db.base import Base


class ApplicationSettings(Base):
    """One installation-wide configuration row, not a collection/domain record."""

    __tablename__ = "application_settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_application_settings_singleton"),
        CheckConstraint(
            "default_label_preset IN ('small', 'medium', 'large')",
            name="ck_application_settings_label_preset",
        ),
    )
    id: Mapped[int] = mapped_column(SmallInteger(), primary_key=True)
    public_qr_base_url: Mapped[str | None] = mapped_column(String(200))
    default_label_preset: Mapped[str] = mapped_column(String(16))
