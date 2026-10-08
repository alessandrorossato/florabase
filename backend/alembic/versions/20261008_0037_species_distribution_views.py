"""Allow private Species distribution Saved Views, without occurrence persistence.

Revision ID: 20261008_0037
Revises: 20261008_0036
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261008_0037"
down_revision: str | None = "20261008_0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_SURFACES = (
    "'global_search', 'seed_lots', 'sowings', 'plants', 'harvests', 'stored_material', 'events', "
    "'history', 'media', 'botanical_identities', 'suppliers', 'orders', 'locations', 'geography', "
    "'provenance_map'"
)


def upgrade() -> None:
    op.drop_constraint("ck_saved_views_surface", "saved_views", type_="check")
    op.create_check_constraint(
        "ck_saved_views_surface",
        "saved_views",
        f"surface IN ({OLD_SURFACES}, 'species_distribution')",
    )


def downgrade() -> None:
    op.execute("LOCK TABLE saved_views IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM saved_views WHERE surface='species_distribution')")
    ):
        raise RuntimeError(
            "Species distribution Saved Views exist; explicitly remove them before downgrade."
        )
    op.drop_constraint("ck_saved_views_surface", "saved_views", type_="check")
    op.create_check_constraint(
        "ck_saved_views_surface", "saved_views", f"surface IN ({OLD_SURFACES})"
    )
