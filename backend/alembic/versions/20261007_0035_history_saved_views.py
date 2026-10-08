"""Allow History Saved Views without persisting projected history.

Revision ID: 20261007_0035
Revises: 20261006_0034
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261007_0035"
down_revision: str | None = "20261006_0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_SURFACES = (
    "'global_search', 'seed_lots', 'sowings', 'plants', 'harvests', 'stored_material', "
    "'events', 'media', 'botanical_identities', 'suppliers', 'locations', 'geography', "
    "'provenance_map'"
)


def upgrade() -> None:
    op.drop_constraint("ck_saved_views_surface", "saved_views", type_="check")
    op.create_check_constraint(
        "ck_saved_views_surface", "saved_views", f"surface IN ({OLD_SURFACES}, 'history')"
    )


def downgrade() -> None:
    op.execute("LOCK TABLE saved_views IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM saved_views WHERE surface='history')")
    ):
        raise RuntimeError("History Saved Views exist; delete them explicitly before downgrade.")
    op.drop_constraint("ck_saved_views_surface", "saved_views", type_="check")
    op.create_check_constraint(
        "ck_saved_views_surface", "saved_views", f"surface IN ({OLD_SURFACES})"
    )
