"""Add structured botanical native ranges.

Revision ID: 20260909_0022
Revises: 20260909_0021
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260909_0022"
down_revision: str | None = "20260909_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_botanical_profiles_at_least_one_section",
        "botanical_profiles",
        type_="check",
    )
    op.create_table(
        "botanical_profile_native_ranges",
        sa.Column("botanical_profile_id", sa.Uuid(), nullable=False),
        sa.Column("geographic_place_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["botanical_profile_id"],
            ["botanical_profiles.botanical_identity_id"],
            name="fk_botanical_profile_native_ranges_profile",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["geographic_place_id"],
            ["geographic_places.id"],
            name="fk_botanical_profile_native_ranges_place",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "botanical_profile_id",
            "geographic_place_id",
            name=op.f("pk_botanical_profile_native_ranges"),
        ),
    )
    op.create_index(
        op.f("ix_botanical_profile_native_ranges_geographic_place_id"),
        "botanical_profile_native_ranges",
        ["geographic_place_id"],
    )
    op.execute(
        """
        CREATE FUNCTION botanical_profile_require_meaningful_data()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            profile_id uuid;
        BEGIN
            IF TG_TABLE_NAME = 'botanical_profiles' THEN
                profile_id := NEW.botanical_identity_id;
            ELSE
                profile_id := OLD.botanical_profile_id;
            END IF;
            IF EXISTS (
                SELECT 1 FROM botanical_profiles profile
                WHERE profile.botanical_identity_id = profile_id
                  AND profile.description IS NULL
                  AND profile.origin_distribution IS NULL
                  AND profile.cultivation IS NULL
                  AND profile.uses IS NULL
                  AND profile.warnings IS NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM botanical_profile_native_ranges native_range
                      WHERE native_range.botanical_profile_id = profile_id
                  )
            ) THEN
                RAISE EXCEPTION 'BotanicalProfile requires meaningful profile-owned data';
            END IF;
            RETURN NULL;
        END
        $$
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER botanical_profiles_meaningful_data
        AFTER INSERT OR UPDATE ON botanical_profiles
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION botanical_profile_require_meaningful_data()
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER botanical_native_ranges_meaningful_data
        AFTER DELETE OR UPDATE ON botanical_profile_native_ranges
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION botanical_profile_require_meaningful_data()
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM botanical_profile_native_ranges) THEN
                RAISE EXCEPTION 'cannot downgrade while botanical native-range data exists';
            END IF;
        END
        $$
        """
    )
    op.execute(
        "DROP TRIGGER botanical_native_ranges_meaningful_data ON botanical_profile_native_ranges"
    )
    op.execute("DROP TRIGGER botanical_profiles_meaningful_data ON botanical_profiles")
    op.execute("DROP FUNCTION botanical_profile_require_meaningful_data()")
    op.drop_index(
        op.f("ix_botanical_profile_native_ranges_geographic_place_id"),
        table_name="botanical_profile_native_ranges",
    )
    op.drop_table("botanical_profile_native_ranges")
    op.create_check_constraint(
        "ck_botanical_profiles_at_least_one_section",
        "botanical_profiles",
        "description IS NOT NULL OR origin_distribution IS NOT NULL OR "
        "cultivation IS NOT NULL OR uses IS NOT NULL OR warnings IS NOT NULL",
    )
