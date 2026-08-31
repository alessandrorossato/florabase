"""Create botanical identities.

Revision ID: 20260828_0002
Revises: 20260827_0001
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260828_0002"
down_revision: str | None = "20260827_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "botanical_identities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scientific_name", sa.String(length=255), nullable=False),
        sa.Column("cultivar_name", sa.String(length=120), nullable=True),
        sa.Column("common_name", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "char_length(scientific_name) BETWEEN 1 AND 255",
            name="ck_botanical_identities_scientific_name_length",
        ),
        sa.CheckConstraint(
            "scientific_name = regexp_replace(btrim(scientific_name), '[[:space:]]+', ' ', 'g')",
            name="ck_botanical_identities_scientific_name_normalized",
        ),
        sa.CheckConstraint(
            "scientific_name !~ '[[:cntrl:]]'",
            name="ck_botanical_identities_scientific_name_no_control",
        ),
        sa.CheckConstraint(
            "cultivar_name IS NULL OR char_length(cultivar_name) BETWEEN 1 AND 120",
            name="ck_botanical_identities_cultivar_name_length",
        ),
        sa.CheckConstraint(
            "cultivar_name IS NULL OR cultivar_name = "
            "regexp_replace(btrim(cultivar_name), '[[:space:]]+', ' ', 'g')",
            name="ck_botanical_identities_cultivar_name_normalized",
        ),
        sa.CheckConstraint(
            "cultivar_name IS NULL OR cultivar_name !~ '[[:cntrl:]]'",
            name="ck_botanical_identities_cultivar_name_no_control",
        ),
        sa.CheckConstraint(
            "cultivar_name IS NULL OR NOT ("
            "(left(cultivar_name, 1) = chr(39) AND right(cultivar_name, 1) = chr(39)) OR "
            "(left(cultivar_name, 1) = chr(34) AND right(cultivar_name, 1) = chr(34)) OR "
            "(left(cultivar_name, 1) = chr(8216) AND right(cultivar_name, 1) = chr(8217)) OR "
            "(left(cultivar_name, 1) = chr(8220) AND right(cultivar_name, 1) = chr(8221)))",
            name="ck_botanical_identities_cultivar_name_unquoted",
        ),
        sa.CheckConstraint(
            "common_name IS NULL OR char_length(common_name) BETWEEN 1 AND 160",
            name="ck_botanical_identities_common_name_length",
        ),
        sa.CheckConstraint(
            "common_name IS NULL OR common_name = "
            "regexp_replace(btrim(common_name), '[[:space:]]+', ' ', 'g')",
            name="ck_botanical_identities_common_name_normalized",
        ),
        sa.CheckConstraint(
            "common_name IS NULL OR common_name !~ '[[:cntrl:]]'",
            name="ck_botanical_identities_common_name_no_control",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_botanical_identities")),
    )
    op.create_index(
        "uq_botanical_identities_name_cultivar_ci",
        "botanical_identities",
        [sa.text("lower(scientific_name)"), sa.text("lower(cultivar_name)")],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_botanical_identities_name_cultivar_ci",
        table_name="botanical_identities",
    )
    op.drop_table("botanical_identities")
