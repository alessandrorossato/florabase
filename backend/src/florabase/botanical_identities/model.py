from datetime import UTC, datetime
from uuid import UUID, uuid7

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
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
        CheckConstraint(
            "(merged_into_id IS NULL AND merged_at IS NULL) OR "
            "(merged_into_id IS NOT NULL AND merged_at IS NOT NULL AND merged_into_id <> id)",
            name="ck_botanical_identities_merge_state",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    scientific_name: Mapped[str] = mapped_column(String(255))
    cultivar_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    common_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    merged_into_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("botanical_identities.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    postgresql_where=BotanicalIdentity.merged_into_id.is_(None),
)


class BotanicalIdentityName(Base):
    __tablename__ = "botanical_identity_names"
    __table_args__ = (
        CheckConstraint(
            "char_length(scientific_name) BETWEEN 1 AND 255 "
            "AND scientific_name = "
            "regexp_replace(btrim(scientific_name), '[[:space:]]+', ' ', 'g') "
            "AND scientific_name !~ '[[:cntrl:]]'",
            name="ck_botanical_identity_names_scientific_name",
        ),
        CheckConstraint(
            "cultivar_name IS NULL OR (char_length(cultivar_name) BETWEEN 1 AND 120 "
            "AND cultivar_name = regexp_replace(btrim(cultivar_name), '[[:space:]]+', ' ', 'g') "
            "AND cultivar_name !~ '[[:cntrl:]]')",
            name="ck_botanical_identity_names_cultivar_name",
        ),
        CheckConstraint(
            "common_name IS NULL OR (char_length(common_name) BETWEEN 1 AND 160 "
            "AND common_name = regexp_replace(btrim(common_name), '[[:space:]]+', ' ', 'g') "
            "AND common_name !~ '[[:cntrl:]]')",
            name="ck_botanical_identity_names_common_name",
        ),
        CheckConstraint(
            "status_kind IN ('initial_recorded', 'former_accepted', 'merged_duplicate', "
            "'source_synonym', 'operator_synonym')",
            name="ck_botanical_identity_names_status_kind",
        ),
        CheckConstraint(
            "source_provider IN ('operator', 'wfo', 'wcvp', 'gbif')",
            name="ck_botanical_identity_names_source_provider",
        ),
        CheckConstraint(
            "(status_kind = 'merged_duplicate' AND origin_identity_id IS NOT NULL) OR "
            "(status_kind <> 'merged_duplicate' AND origin_identity_id IS NULL)",
            name="ck_botanical_identity_names_origin_identity",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    botanical_identity_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("botanical_identities.id", ondelete="CASCADE"), index=True
    )
    scientific_name: Mapped[str] = mapped_column(String(255))
    cultivar_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    common_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    authorship: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status_kind: Mapped[str] = mapped_column(String(32))
    source_provider: Mapped[str] = mapped_column(String(32))
    source_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_taxon_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    accepted_source_taxon_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    origin_identity_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("botanical_identities.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    superseded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class BotanicalIdentityReconciliation(Base):
    __tablename__ = "botanical_identity_reconciliations"
    __table_args__ = (
        CheckConstraint(
            "((kind = 'accepted_name_correction' AND duplicate_identity_id IS NULL) OR "
            "(kind = 'duplicate_identity_merge' AND duplicate_identity_id IS NOT NULL "
            "AND duplicate_identity_id <> identity_id)) IS TRUE",
            name="ck_botanical_identity_reconciliations_kind",
        ),
        CheckConstraint(
            "source_provider IN ('operator', 'wfo', 'wcvp', 'gbif')",
            name="ck_botanical_identity_reconciliations_source_provider",
        ),
        CheckConstraint(
            "jsonb_typeof(evidence) = 'object'",
            name="ck_botanical_identity_reconciliations_evidence",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    identity_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("botanical_identities.id", ondelete="RESTRICT"), index=True
    )
    duplicate_identity_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("botanical_identities.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(32))
    previous_scientific_name: Mapped[str] = mapped_column(String(255))
    previous_cultivar_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    previous_common_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    applied_scientific_name: Mapped[str] = mapped_column(String(255))
    applied_cultivar_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    applied_common_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source_provider: Mapped[str] = mapped_column(String(32))
    evidence: Mapped[dict[str, object]] = mapped_column(JSONB())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
