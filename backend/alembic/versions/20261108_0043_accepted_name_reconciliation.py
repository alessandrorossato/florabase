"""Add accepted-name reconciliation, historical name ledger, and duplicate survivor tombstones.

Revision ID: 20261108_0043
Revises: 20261013_0042
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261108_0043"
down_revision: str | None = "20261013_0042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("botanical_identities", sa.Column("merged_into_id", sa.Uuid(), nullable=True))
    op.add_column(
        "botanical_identities",
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_botanical_identities_merged_into_id_botanical_identities"),
        "botanical_identities",
        "botanical_identities",
        ["merged_into_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_botanical_identities_merged_into_id"),
        "botanical_identities",
        ["merged_into_id"],
    )
    op.create_check_constraint(
        "ck_botanical_identities_merge_state",
        "botanical_identities",
        "(merged_into_id IS NULL AND merged_at IS NULL) OR "
        "(merged_into_id IS NOT NULL AND merged_at IS NOT NULL AND merged_into_id <> id)",
    )
    op.drop_index("uq_botanical_identities_name_cultivar_ci", table_name="botanical_identities")
    op.create_index(
        "uq_botanical_identities_name_cultivar_ci",
        "botanical_identities",
        [sa.text("lower(scientific_name)"), sa.text("lower(cultivar_name)")],
        unique=True,
        postgresql_nulls_not_distinct=True,
        postgresql_where=sa.text("merged_into_id IS NULL"),
    )

    op.create_table(
        "botanical_identity_names",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("botanical_identity_id", sa.Uuid(), nullable=False),
        sa.Column("scientific_name", sa.String(length=255), nullable=False),
        sa.Column("cultivar_name", sa.String(length=120), nullable=True),
        sa.Column("common_name", sa.String(length=160), nullable=True),
        sa.Column("authorship", sa.String(length=255), nullable=True),
        sa.Column("status_kind", sa.String(length=32), nullable=False),
        sa.Column("source_provider", sa.String(length=32), nullable=False),
        sa.Column("source_version", sa.String(length=64), nullable=True),
        sa.Column("source_taxon_id", sa.String(length=255), nullable=True),
        sa.Column("accepted_source_taxon_id", sa.String(length=255), nullable=True),
        sa.Column("origin_identity_id", sa.Uuid(), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "char_length(scientific_name) BETWEEN 1 AND 255 "
            "AND scientific_name = "
            "regexp_replace(btrim(scientific_name), '[[:space:]]+', ' ', 'g') "
            "AND scientific_name !~ '[[:cntrl:]]'",
            name="ck_botanical_identity_names_scientific_name",
        ),
        sa.CheckConstraint(
            "cultivar_name IS NULL OR (char_length(cultivar_name) BETWEEN 1 AND 120 "
            "AND cultivar_name = regexp_replace(btrim(cultivar_name), '[[:space:]]+', ' ', 'g') "
            "AND cultivar_name !~ '[[:cntrl:]]')",
            name="ck_botanical_identity_names_cultivar_name",
        ),
        sa.CheckConstraint(
            "common_name IS NULL OR (char_length(common_name) BETWEEN 1 AND 160 "
            "AND common_name = regexp_replace(btrim(common_name), '[[:space:]]+', ' ', 'g') "
            "AND common_name !~ '[[:cntrl:]]')",
            name="ck_botanical_identity_names_common_name",
        ),
        sa.CheckConstraint(
            "status_kind IN ('initial_recorded', 'former_accepted', 'merged_duplicate', "
            "'source_synonym', 'operator_synonym')",
            name="ck_botanical_identity_names_status_kind",
        ),
        sa.CheckConstraint(
            "source_provider IN ('operator', 'wfo', 'wcvp', 'gbif')",
            name="ck_botanical_identity_names_source_provider",
        ),
        sa.CheckConstraint(
            "(status_kind = 'merged_duplicate' AND origin_identity_id IS NOT NULL) OR "
            "(status_kind <> 'merged_duplicate' AND origin_identity_id IS NULL)",
            name="ck_botanical_identity_names_origin_identity",
        ),
        sa.ForeignKeyConstraint(
            ["botanical_identity_id"],
            ["botanical_identities.id"],
            name=op.f("fk_botanical_identity_names_botanical_identity_id_botanical_identities"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["origin_identity_id"],
            ["botanical_identities.id"],
            name=op.f("fk_botanical_identity_names_origin_identity_id_botanical_identities"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_botanical_identity_names")),
    )
    op.create_index(
        op.f("ix_botanical_identity_names_botanical_identity_id"),
        "botanical_identity_names",
        ["botanical_identity_id"],
    )
    op.create_index(
        op.f("ix_botanical_identity_names_origin_identity_id"),
        "botanical_identity_names",
        ["origin_identity_id"],
    )

    op.create_table(
        "botanical_identity_reconciliations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identity_id", sa.Uuid(), nullable=False),
        sa.Column("duplicate_identity_id", sa.Uuid(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("previous_scientific_name", sa.String(length=255), nullable=False),
        sa.Column("previous_cultivar_name", sa.String(length=120), nullable=True),
        sa.Column("previous_common_name", sa.String(length=160), nullable=True),
        sa.Column("applied_scientific_name", sa.String(length=255), nullable=False),
        sa.Column("applied_cultivar_name", sa.String(length=120), nullable=True),
        sa.Column("applied_common_name", sa.String(length=160), nullable=True),
        sa.Column("source_provider", sa.String(length=32), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "((kind = 'accepted_name_correction' AND duplicate_identity_id IS NULL) OR "
            "(kind = 'duplicate_identity_merge' AND duplicate_identity_id IS NOT NULL "
            "AND duplicate_identity_id <> identity_id)) IS TRUE",
            name="ck_botanical_identity_reconciliations_kind",
        ),
        sa.CheckConstraint(
            "source_provider IN ('operator', 'wfo', 'wcvp', 'gbif')",
            name="ck_botanical_identity_reconciliations_source_provider",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(evidence) = 'object'",
            name="ck_botanical_identity_reconciliations_evidence",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_botanical_identity_reconciliations_actor_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["duplicate_identity_id"],
            ["botanical_identities.id"],
            name=op.f(
                "fk_botanical_identity_reconciliations_duplicate_identity_id_botanical_identities"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["identity_id"],
            ["botanical_identities.id"],
            name=op.f("fk_botanical_identity_reconciliations_identity_id_botanical_identities"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_botanical_identity_reconciliations")),
    )
    op.create_index(
        op.f("ix_botanical_identity_reconciliations_identity_id"),
        "botanical_identity_reconciliations",
        ["identity_id"],
    )
    op.create_index(
        op.f("ix_botanical_identity_reconciliations_duplicate_identity_id"),
        "botanical_identity_reconciliations",
        ["duplicate_identity_id"],
    )
    op.create_index(
        op.f("ix_botanical_identity_reconciliations_actor_user_id"),
        "botanical_identity_reconciliations",
        ["actor_user_id"],
    )
    op.execute(
        """
        CREATE FUNCTION guard_botanical_identity_reconciliation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'Botanical identity reconciliation evidence is immutable';
        END $$;
        CREATE TRIGGER immutable_botanical_identity_reconciliation
        BEFORE UPDATE OR DELETE ON botanical_identity_reconciliations
        FOR EACH ROW EXECUTE FUNCTION guard_botanical_identity_reconciliation();
        """
    )


def downgrade() -> None:
    op.execute(
        "LOCK TABLE botanical_identities, botanical_identity_names, "
        "botanical_identity_reconciliations IN ACCESS EXCLUSIVE MODE"
    )
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM botanical_identity_reconciliations) "
            "OR EXISTS(SELECT 1 FROM botanical_identity_names) "
            "OR EXISTS(SELECT 1 FROM botanical_identities WHERE merged_into_id IS NOT NULL)"
        )
    ):
        raise RuntimeError(
            "Accepted-name reconciliations or merged identities exist; "
            "downgrade would destroy reviewed botanical history."
        )
    op.execute(
        "DROP TRIGGER immutable_botanical_identity_reconciliation "
        "ON botanical_identity_reconciliations"
    )
    op.execute("DROP FUNCTION guard_botanical_identity_reconciliation()")
    op.drop_index(
        op.f("ix_botanical_identity_reconciliations_actor_user_id"),
        table_name="botanical_identity_reconciliations",
    )
    op.drop_index(
        op.f("ix_botanical_identity_reconciliations_duplicate_identity_id"),
        table_name="botanical_identity_reconciliations",
    )
    op.drop_index(
        op.f("ix_botanical_identity_reconciliations_identity_id"),
        table_name="botanical_identity_reconciliations",
    )
    op.drop_table("botanical_identity_reconciliations")

    op.drop_index(
        op.f("ix_botanical_identity_names_origin_identity_id"),
        table_name="botanical_identity_names",
    )
    op.drop_index(
        op.f("ix_botanical_identity_names_botanical_identity_id"),
        table_name="botanical_identity_names",
    )
    op.drop_table("botanical_identity_names")

    op.drop_index("uq_botanical_identities_name_cultivar_ci", table_name="botanical_identities")
    op.create_index(
        "uq_botanical_identities_name_cultivar_ci",
        "botanical_identities",
        [sa.text("lower(scientific_name)"), sa.text("lower(cultivar_name)")],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )
    op.drop_constraint("ck_botanical_identities_merge_state", "botanical_identities", type_="check")
    op.drop_index(op.f("ix_botanical_identities_merged_into_id"), table_name="botanical_identities")
    op.drop_constraint(
        op.f("fk_botanical_identities_merged_into_id_botanical_identities"),
        "botanical_identities",
        type_="foreignkey",
    )
    op.drop_column("botanical_identities", "merged_at")
    op.drop_column("botanical_identities", "merged_into_id")
