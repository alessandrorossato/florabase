from datetime import UTC, datetime
from uuid import UUID, uuid7

from sqlalchemy import CheckConstraint, DateTime, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from florabase.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class BotanicalIdentity(Base):
    __tablename__ = "botanical_identities"
    __table_args__ = (
        CheckConstraint(
            "char_length(scientific_name) BETWEEN 1 AND 255",
            name="ck_botanical_identities_scientific_name_length",
        ),
        CheckConstraint(
            "scientific_name = regexp_replace(btrim(scientific_name), '[[:space:]]+', ' ', 'g')",
            name="ck_botanical_identities_scientific_name_normalized",
        ),
        CheckConstraint(
            "scientific_name !~ '[[:cntrl:]]'",
            name="ck_botanical_identities_scientific_name_no_control",
        ),
        CheckConstraint(
            "cultivar_name IS NULL OR char_length(cultivar_name) BETWEEN 1 AND 120",
            name="ck_botanical_identities_cultivar_name_length",
        ),
        CheckConstraint(
            "cultivar_name IS NULL OR cultivar_name = "
            "regexp_replace(btrim(cultivar_name), '[[:space:]]+', ' ', 'g')",
            name="ck_botanical_identities_cultivar_name_normalized",
        ),
        CheckConstraint(
            "cultivar_name IS NULL OR cultivar_name !~ '[[:cntrl:]]'",
            name="ck_botanical_identities_cultivar_name_no_control",
        ),
        CheckConstraint(
            "cultivar_name IS NULL OR NOT ("
            "(left(cultivar_name, 1) = chr(39) AND right(cultivar_name, 1) = chr(39)) OR "
            "(left(cultivar_name, 1) = chr(34) AND right(cultivar_name, 1) = chr(34)) OR "
            "(left(cultivar_name, 1) = chr(8216) AND right(cultivar_name, 1) = chr(8217)) OR "
            "(left(cultivar_name, 1) = chr(8220) AND right(cultivar_name, 1) = chr(8221)))",
            name="ck_botanical_identities_cultivar_name_unquoted",
        ),
        CheckConstraint(
            "common_name IS NULL OR char_length(common_name) BETWEEN 1 AND 160",
            name="ck_botanical_identities_common_name_length",
        ),
        CheckConstraint(
            "common_name IS NULL OR common_name = "
            "regexp_replace(btrim(common_name), '[[:space:]]+', ' ', 'g')",
            name="ck_botanical_identities_common_name_normalized",
        ),
        CheckConstraint(
            "common_name IS NULL OR common_name !~ '[[:cntrl:]]'",
            name="ck_botanical_identities_common_name_no_control",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    scientific_name: Mapped[str] = mapped_column(String(255))
    cultivar_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    common_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


Index(
    "uq_botanical_identities_name_cultivar_ci",
    func.lower(BotanicalIdentity.scientific_name),
    func.lower(BotanicalIdentity.cultivar_name),
    unique=True,
    postgresql_nulls_not_distinct=True,
)
