"""Retained future collection intentions, separate from Events.

Revision ID: 20261009_0041
Revises: 20261009_0040
"""

import sqlalchemy as sa

from alembic import op

revision = "20261009_0041"
down_revision = "20261009_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduled_activities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("activity_kind", sa.String(24), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "botanical_identity_id",
            sa.Uuid(),
            sa.ForeignKey("botanical_identities.id", ondelete="RESTRICT"),
        ),
        sa.Column("seed_lot_id", sa.Uuid(), sa.ForeignKey("seed_lots.id", ondelete="RESTRICT")),
        sa.Column("sowing_id", sa.Uuid(), sa.ForeignKey("sowings.id", ondelete="RESTRICT")),
        sa.Column("plant_id", sa.Uuid(), sa.ForeignKey("plants.id", ondelete="RESTRICT")),
        sa.Column(
            "plant_group_id", sa.Uuid(), sa.ForeignKey("plant_groups.id", ondelete="RESTRICT")
        ),
        sa.Column("location_id", sa.Uuid(), sa.ForeignKey("locations.id", ondelete="RESTRICT")),
        sa.Column(
            "linked_event_id",
            sa.Uuid(),
            sa.ForeignKey("events.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column("completion_fingerprint", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            (
                "activity_kind IN ('repot', 'water', 'fertilize', 'move', "
                "'check_germination', 'inspect', 'harvest', 'follow_up')"
            ),
            name="ck_schedule_kind",
        ),
        sa.CheckConstraint(
            "status IN ('planned', 'completed', 'cancelled')", name="ck_schedule_status"
        ),
        sa.CheckConstraint("version >= 1", name="ck_schedule_version"),
        sa.CheckConstraint(
            "char_length(title) BETWEEN 1 AND 255 AND title = btrim(title) "
            "AND title !~ '[[:cntrl:]]'",
            name="ck_schedule_title",
        ),
        sa.CheckConstraint(
            "notes IS NULL OR char_length(notes) BETWEEN 1 AND 20000", name="ck_schedule_notes"
        ),
        sa.CheckConstraint(
            "due_on BETWEEN DATE '0001-01-01' AND DATE '9999-12-31'", name="ck_schedule_due"
        ),
        sa.CheckConstraint(
            (
                "num_nonnulls(botanical_identity_id, seed_lot_id, sowing_id, plant_id, "
                "plant_group_id, location_id) <= 1"
            ),
            name="ck_schedule_target",
        ),
        sa.CheckConstraint(
            (
                "(status = 'planned' AND completed_at IS NULL AND cancelled_at IS NULL AND "
                "completion_fingerprint IS NULL AND linked_event_id IS NULL) OR (status = "
                "'completed' AND completed_at IS NOT NULL AND cancelled_at IS NULL AND "
                "completion_fingerprint IS NOT NULL) OR (status = 'cancelled' AND "
                "cancelled_at IS NOT NULL AND completed_at IS NULL AND "
                "completion_fingerprint IS NULL AND linked_event_id IS NULL)"
            ),
            name="ck_schedule_transition",
        ),
        sa.CheckConstraint(
            "linked_event_id IS NULL OR num_nonnulls(plant_id, plant_group_id) = 1",
            name="ck_schedule_event_target",
        ),
    )
    for column in (
        "due_on",
        "status",
        "botanical_identity_id",
        "seed_lot_id",
        "sowing_id",
        "plant_id",
        "plant_group_id",
        "location_id",
    ):
        op.create_index(f"ix_scheduled_activities_{column}", "scheduled_activities", [column])


def downgrade() -> None:
    op.execute("LOCK TABLE scheduled_activities IN ACCESS EXCLUSIVE MODE")
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM scheduled_activities) THEN
            RAISE EXCEPTION 'Retained scheduled activities prevent downgrade';
        END IF;
    END $$""")
    op.drop_table("scheduled_activities")
