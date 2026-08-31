"""Create botanical profiles.

Revision ID: 20260829_0004
Revises: 20260828_0003
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260829_0004"
down_revision: str | None = "20260828_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FIELDS = ("description", "origin_distribution", "cultivation", "uses", "warnings")
MAX_SECTION_LENGTH = 20_000


def upgrade() -> None:
    constraints: list[sa.CheckConstraint] = []
    for field in FIELDS:
        constraints.extend(
            [
                sa.CheckConstraint(
                    f"{field} IS NULL OR char_length({field}) BETWEEN 1 AND {MAX_SECTION_LENGTH}",
                    name=f"ck_botanical_profiles_{field}_length",
                ),
                sa.CheckConstraint(
                    f"{field} IS NULL OR {field} !~ '^[[:space:]]|[[:space:]]$'",
                    name=f"ck_botanical_profiles_{field}_trimmed",
                ),
                sa.CheckConstraint(
                    f"{field} IS NULL OR "
                    f"regexp_replace({field}, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]'",
                    name=f"ck_botanical_profiles_{field}_no_control",
                ),
            ]
        )

    op.create_table(
        "botanical_profiles",
        sa.Column("botanical_identity_id", sa.Uuid(), nullable=False),
        *(sa.Column(field, sa.Text(), nullable=True) for field in FIELDS),
        *constraints,
        sa.CheckConstraint(
            " OR ".join(f"{field} IS NOT NULL" for field in FIELDS),
            name="ck_botanical_profiles_at_least_one_section",
        ),
        sa.ForeignKeyConstraint(
            ["botanical_identity_id"],
            ["botanical_identities.id"],
            name="fk_botanical_profiles_identity",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("botanical_identity_id", name=op.f("pk_botanical_profiles")),
    )


def downgrade() -> None:
    op.drop_table("botanical_profiles")
