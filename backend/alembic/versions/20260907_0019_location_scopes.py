"""Add explicit Location usage scopes.

Revision ID: 20260907_0019
Revises: 20260907_0018
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260907_0019"
down_revision: str | None = "20260907_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing Locations are enabled for every current consumer. This preserves all assignments
    # without guessing intent from incomplete or historical data.
    for column in ("supports_plants", "supports_sowings", "supports_seed_lots"):
        op.add_column(
            "locations",
            sa.Column(column, sa.Boolean(), nullable=False, server_default=sa.true()),
        )
    op.create_check_constraint(
        "ck_locations_at_least_one_scope",
        "locations",
        "supports_plants OR supports_sowings OR supports_seed_lots",
    )


def downgrade() -> None:
    op.drop_constraint("ck_locations_at_least_one_scope", "locations", type_="check")
    for column in ("supports_seed_lots", "supports_sowings", "supports_plants"):
        op.drop_column("locations", column)
