"""Add installation-wide media defaults to application_settings (MEDIA-SETTINGS-001).

Revision ID: 20261125_0050
Revises: 20261125_0049
"""

import sqlalchemy as sa

from alembic import op

revision = "20261125_0050"
down_revision = "20261125_0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The local-copy default only pre-checks a form choice; it never triggers a fetch by itself.
    op.add_column(
        "application_settings",
        sa.Column(
            "media_save_local_copy_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "application_settings",
        sa.Column("media_default_attribution", sa.String(2000), nullable=True),
    )
    op.add_column(
        "application_settings",
        sa.Column("media_default_licence_label", sa.String(2000), nullable=True),
    )
    op.add_column(
        "application_settings",
        sa.Column("media_default_licence_url", sa.String(2048), nullable=True),
    )


def downgrade() -> None:
    # Only these preferences are lost; no media asset or collection record is changed.
    op.drop_column("application_settings", "media_default_licence_url")
    op.drop_column("application_settings", "media_default_licence_label")
    op.drop_column("application_settings", "media_default_attribution")
    op.drop_column("application_settings", "media_save_local_copy_default")
