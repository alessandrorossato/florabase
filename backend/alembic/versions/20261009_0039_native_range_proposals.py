"""Reviewable WCVP native-range proposals and immutable application evidence.

Revision ID: 20261009_0039
Revises: 20261008_0038
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261009_0039"
down_revision: str | None = "20261008_0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wcvp_links",
        sa.Column(
            "identity_id",
            sa.Uuid(),
            sa.ForeignKey("botanical_identities.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("version", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("taxon", postgresql.JSONB(), nullable=False),
        sa.Column("source", postgresql.JSONB(), nullable=False),
        sa.Column("identity_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "char_length(external_id) BETWEEN 1 AND 255", name="ck_wcvp_link_external_id"
        ),
    )
    op.create_table(
        "native_range_revisions",
        sa.Column(
            "identity_id",
            sa.Uuid(),
            sa.ForeignKey("botanical_identities.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("version >= 0", name="ck_native_range_revision_nonnegative"),
    )
    op.create_table(
        "native_range_proposals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "identity_id",
            sa.Uuid(),
            sa.ForeignKey("botanical_identities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint(
            "jsonb_typeof(evidence) = 'object' AND "
            "evidence->>'format_version' IS NOT DISTINCT FROM '1'",
            name="ck_native_range_proposal_format",
        ),
    )
    op.create_index(
        "ix_native_range_proposals_identity_id", "native_range_proposals", ["identity_id"]
    )
    op.create_table(
        "native_range_applications",
        sa.Column(
            "proposal_id",
            sa.Uuid(),
            sa.ForeignKey("native_range_proposals.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "identity_id",
            sa.Uuid(),
            sa.ForeignKey("botanical_identities.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint(
            "jsonb_typeof(evidence) = 'object'", name="ck_native_range_application_evidence"
        ),
    )
    op.create_index(
        "ix_native_range_applications_identity_id", "native_range_applications", ["identity_id"]
    )
    op.execute("""
      CREATE FUNCTION advance_native_range_revision() RETURNS trigger LANGUAGE plpgsql AS $$
      DECLARE target uuid;
      BEGIN
        target := CASE WHEN TG_OP = 'DELETE' THEN OLD.botanical_profile_id
                  ELSE NEW.botanical_profile_id END;
        PERFORM 1 FROM botanical_identities WHERE id=target FOR UPDATE;
        IF FOUND THEN
          INSERT INTO native_range_revisions(identity_id, version) VALUES(target, 1)
          ON CONFLICT(identity_id) DO UPDATE SET version=native_range_revisions.version+1;
        END IF;
        IF TG_OP = 'UPDATE' AND OLD.botanical_profile_id <> NEW.botanical_profile_id THEN
          INSERT INTO native_range_revisions(identity_id, version)
          VALUES(OLD.botanical_profile_id, 1)
          ON CONFLICT(identity_id) DO UPDATE SET version=native_range_revisions.version+1;
        END IF;
        RETURN NULL;
      END $$;
      CREATE TRIGGER advance_native_range_revision AFTER INSERT OR UPDATE OR DELETE
      ON botanical_profile_native_ranges FOR EACH ROW
      EXECUTE FUNCTION advance_native_range_revision();
      CREATE FUNCTION guard_native_range_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
        RAISE EXCEPTION 'Native-range source evidence is immutable';
      END $$;
      CREATE TRIGGER immutable_native_range_proposal BEFORE UPDATE ON native_range_proposals
      FOR EACH ROW EXECUTE FUNCTION guard_native_range_evidence();
      CREATE TRIGGER immutable_native_range_application BEFORE UPDATE OR DELETE
      ON native_range_applications
      FOR EACH ROW EXECUTE FUNCTION guard_native_range_evidence();
    """)


def downgrade() -> None:
    op.execute(
        "LOCK TABLE wcvp_links, native_range_proposals, native_range_applications, "
        "botanical_profile_native_ranges IN ACCESS EXCLUSIVE MODE"
    )
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM native_range_proposals) "
            "OR EXISTS(SELECT 1 FROM native_range_applications) "
            "OR EXISTS(SELECT 1 FROM wcvp_links)"
        )
    ):
        raise RuntimeError(
            "WCVP links or source evidence exist; downgrade would destroy reviewed provenance."
        )
    op.execute("DROP TRIGGER advance_native_range_revision ON botanical_profile_native_ranges")
    op.execute("DROP FUNCTION advance_native_range_revision()")
    for table in (
        "native_range_applications",
        "native_range_proposals",
        "native_range_revisions",
        "wcvp_links",
    ):
        op.drop_table(table)
    op.execute("DROP FUNCTION guard_native_range_evidence()")
