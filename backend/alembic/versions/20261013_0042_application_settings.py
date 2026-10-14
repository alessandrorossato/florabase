"""Persist installation-wide QR destination and default print preset.

Revision ID: 20261013_0042
Revises: 20261009_0041
"""

import sqlalchemy as sa

from alembic import op

revision = "20261013_0042"
down_revision = "20261009_0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "application_settings",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("public_qr_base_url", sa.String(200), nullable=True),
        sa.Column("default_label_preset", sa.String(16), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_application_settings_singleton"),
        sa.CheckConstraint(
            "default_label_preset IN ('small', 'medium', 'large')",
            name="ck_application_settings_label_preset",
        ),
    )
    # Existing installations remain explicitly unconfigured; never infer a preview/login host.
    op.execute("INSERT INTO application_settings (id, default_label_preset) VALUES (1, 'medium')")


def downgrade() -> None:
    # Only application preferences are lost. No collection record is changed.
    op.drop_table("application_settings")
