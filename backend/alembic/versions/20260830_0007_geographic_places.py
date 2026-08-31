"""Add canonical and operator-defined GeographicPlace hierarchy.

Revision ID: 20260830_0007
Revises: 20260830_0006
"""

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision: str = "20260830_0007"
down_revision: str | None = "20260830_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SNAPSHOT = Path(__file__).parents[1] / "data" / "geographic_places_cldr_48_2_1.json"


def _canonical_records() -> list[dict[str, Any]]:
    document = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    if (
        document.get("source") != "unicode_cldr"
        or document.get("version") != "48.2.1"
        or document.get("license") != "Unicode-3.0"
    ):
        raise RuntimeError("Unexpected GeographicPlace canonical snapshot metadata")
    records = document.get("records")
    if not isinstance(records, list):
        raise RuntimeError("GeographicPlace canonical snapshot has no records")
    return records


def upgrade() -> None:
    op.create_table(
        "geographic_places",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("place_kind", sa.String(length=16), nullable=False),
        sa.Column("source_name", sa.String(length=64), nullable=True),
        sa.Column("source_version", sa.String(length=32), nullable=True),
        sa.Column("source_code_type", sa.String(length=32), nullable=True),
        sa.Column("source_code", sa.String(length=16), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "char_length(name) BETWEEN 1 AND 255", name="ck_geographic_places_name_length"
        ),
        sa.CheckConstraint(
            "name = regexp_replace(btrim(name), '[[:space:]]+', ' ', 'g')",
            name="ck_geographic_places_name_normalized",
        ),
        sa.CheckConstraint("name !~ '[[:cntrl:]]'", name="ck_geographic_places_name_no_control"),
        sa.CheckConstraint(
            "parent_id IS NULL OR parent_id <> id",
            name="ck_geographic_places_not_self_parent",
        ),
        sa.CheckConstraint(
            "place_kind IN ('canonical', 'custom')", name="ck_geographic_places_kind"
        ),
        sa.CheckConstraint(
            "(place_kind = 'canonical' AND source_name IS NOT NULL "
            "AND source_version IS NOT NULL AND source_code_type IS NOT NULL "
            "AND source_code IS NOT NULL AND retired_at IS NULL) OR "
            "(place_kind = 'custom' AND source_name IS NULL AND source_version IS NULL "
            "AND source_code_type IS NULL AND source_code IS NULL)",
            name="ck_geographic_places_source_metadata",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["geographic_places.id"],
            name=op.f("fk_geographic_places_parent_id_geographic_places"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_geographic_places")),
        sa.UniqueConstraint(
            "source_name",
            "source_code_type",
            "source_code",
            name="uq_geographic_places_source_identifier",
        ),
    )
    op.create_index(
        op.f("ix_geographic_places_parent_id"),
        "geographic_places",
        ["parent_id"],
        unique=False,
    )
    op.create_index(
        "uq_geographic_places_one_root",
        "geographic_places",
        [sa.literal_column("(parent_id IS NULL)")],
        unique=True,
        postgresql_where=sa.text("parent_id IS NULL"),
    )

    table = sa.table(
        "geographic_places",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("parent_id", sa.Uuid()),
        sa.column("place_kind", sa.String()),
        sa.column("source_name", sa.String()),
        sa.column("source_version", sa.String()),
        sa.column("source_code_type", sa.String()),
        sa.column("source_code", sa.String()),
        sa.column("retired_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    records = _canonical_records()
    id_by_code = {record["source_code"]: UUID(record["id"]) for record in records}
    remaining = list(records)
    inserted: set[str] = set()
    timestamp = datetime(2026, 7, 8, tzinfo=UTC)
    while remaining:
        ready = [
            record
            for record in remaining
            if record["parent_source_code"] is None or record["parent_source_code"] in inserted
        ]
        if not ready:
            raise RuntimeError("Canonical GeographicPlace snapshot contains a cycle")
        op.bulk_insert(
            table,
            [
                {
                    "id": UUID(record["id"]),
                    "name": record["name"],
                    "parent_id": (
                        id_by_code[record["parent_source_code"]]
                        if record["parent_source_code"] is not None
                        else None
                    ),
                    "place_kind": "canonical",
                    "source_name": "unicode_cldr",
                    "source_version": "48.2.1",
                    "source_code_type": record["source_code_type"],
                    "source_code": record["source_code"],
                    "retired_at": None,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
                for record in ready
            ],
        )
        inserted.update(record["source_code"] for record in ready)
        remaining = [record for record in remaining if record not in ready]


def downgrade() -> None:
    op.drop_index("uq_geographic_places_one_root", table_name="geographic_places")
    op.drop_index(op.f("ix_geographic_places_parent_id"), table_name="geographic_places")
    op.drop_table("geographic_places")
