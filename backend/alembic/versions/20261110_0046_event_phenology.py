"""Add controlled phenological stages to observation, flowering and fruiting Events.

Revision ID: 20261110_0046
Revises: 20261109_0045
"""

import sqlalchemy as sa

from alembic import op

revision = "20261110_0046"
down_revision = "20261109_0045"
branch_labels = None
depends_on = None

# Frozen copy of florabase.events.model.PHENOLOGY_CHECK at this revision.
PHENOLOGY = (
    "((phenophase IS NULL AND phenophase_date_is_approximate IS NULL) OR "
    "(phenophase_date_is_approximate IS NOT NULL AND "
    "(phenophase_date_is_approximate IS FALSE OR occurred_on_precision IS NOT NULL) AND ("
    "(kind = 'observation' AND phenophase IN ('bud_break', 'leaf_color_change', 'leaf_fall', "
    "'dormancy_entry', 'dormancy_exit')) OR "
    "(kind = 'flowering' AND phenophase IN ('flowering_onset', 'flowering_ongoing', "
    "'flowering_end')) OR "
    "(kind = 'fruiting' AND phenophase IN ('fruit_set', 'fruit_ripening', 'fruit_ripe'))"
    "))) IS TRUE"
)


def upgrade() -> None:
    op.add_column("events", sa.Column("phenophase", sa.String(24), nullable=True))
    op.add_column(
        "events", sa.Column("phenophase_date_is_approximate", sa.Boolean(), nullable=True)
    )
    op.create_check_constraint("ck_events_phenology", "events", PHENOLOGY)


def downgrade() -> None:
    op.execute("LOCK TABLE events IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM events WHERE phenophase IS NOT NULL)")
    ):
        raise RuntimeError(
            "Phenology observations exist; clear their stages explicitly before downgrade."
        )
    op.drop_constraint("ck_events_phenology", "events", type_="check")
    op.drop_column("events", "phenophase_date_is_approximate")
    op.drop_column("events", "phenophase")
