"""Explicit purchase transactions and optional physical SeedLot grouping.

Revision ID: 20261008_0036
Revises: 20261007_0035
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261008_0036"
down_revision: str | None = "20261007_0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_SURFACES = (
    "'global_search', 'seed_lots', 'sowings', 'plants', 'harvests', 'stored_material', 'events', "
    "'history', 'media', 'botanical_identities', 'suppliers', 'locations', 'geography', "
    "'provenance_map'"
)


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("supplier_id", sa.Uuid(), sa.ForeignKey("suppliers.id", ondelete="RESTRICT")),
        sa.Column("ordered_on_precision", sa.String(8)),
        sa.Column("ordered_on_year", sa.SmallInteger()),
        sa.Column("ordered_on_month", sa.SmallInteger()),
        sa.Column("ordered_on_day", sa.SmallInteger()),
        sa.Column("order_reference", sa.String(255)),
        sa.Column("total_price", sa.Numeric()),
        sa.Column("currency", sa.String(3)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(ordered_on_precision IS NULL AND ordered_on_year IS NULL AND ordered_on_month IS "
            "NULL AND ordered_on_day IS NULL) OR "
            "(ordered_on_year BETWEEN 1 AND 9999 AND ("
            "(ordered_on_precision = 'year' AND ordered_on_month IS NULL AND ordered_on_day IS "
            "NULL) OR "
            "(ordered_on_precision = 'month' AND ordered_on_month BETWEEN 1 AND 12 AND "
            "ordered_on_day IS NULL) OR "
            "(ordered_on_precision = 'day' AND ordered_on_month BETWEEN 1 AND 12 AND "
            "ordered_on_day BETWEEN 1 AND 31 "
            "AND make_date(ordered_on_year, ordered_on_month, ordered_on_day) IS NOT NULL))) "
            "IS TRUE",
            name="ck_orders_ordered_on",
        ),
        sa.CheckConstraint(
            "order_reference IS NULL OR (char_length(order_reference) BETWEEN 1 AND 255 AND "
            "order_reference = btrim(order_reference) AND order_reference !~ '[[:cntrl:]]')",
            name="ck_orders_reference",
        ),
        sa.CheckConstraint(
            "(total_price IS NULL AND currency IS NULL) OR (total_price IS NOT NULL AND "
            "total_price >= 0 AND total_price < 'Infinity'::numeric AND currency IS NOT NULL "
            "AND currency ~ '^[A-Z]{3}$')",
            name="ck_orders_price_currency",
        ),
        sa.CheckConstraint(
            "notes IS NULL OR (char_length(notes) BETWEEN 1 AND 20000 AND notes = "
            "btrim(notes) AND regexp_replace(notes, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
            name="ck_orders_notes",
        ),
    )
    op.create_index("ix_orders_supplier_id", "orders", ["supplier_id"])
    op.create_index(
        "ix_orders_date", "orders", ["ordered_on_year", "ordered_on_month", "ordered_on_day", "id"]
    )
    op.add_column("seed_lots", sa.Column("order_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_seed_lots_order_id", "seed_lots", "orders", ["order_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_index("ix_seed_lots_order_id", "seed_lots", ["order_id"])
    op.create_check_constraint(
        "ck_seed_lots_order_source",
        "seed_lots",
        "order_id IS NULL OR source_kind IN ('purchased', 'purchased_fruit')",
    )
    op.drop_constraint("ck_saved_views_surface", "saved_views", type_="check")
    op.create_check_constraint(
        "ck_saved_views_surface", "saved_views", f"surface IN ({OLD_SURFACES}, 'orders')"
    )


def downgrade() -> None:
    # Prevent writers from racing the refusal checks. Never drop meaningful purchases.
    op.execute("LOCK TABLE orders, seed_lots, saved_views IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM orders) OR EXISTS (SELECT 1 FROM saved_views WHERE "
            "surface='orders')"
        )
    ):
        raise RuntimeError(
            "Orders or Order Saved Views exist; explicitly remove them before downgrade."
        )
    op.drop_constraint("ck_saved_views_surface", "saved_views", type_="check")
    op.create_check_constraint(
        "ck_saved_views_surface", "saved_views", f"surface IN ({OLD_SURFACES})"
    )
    op.drop_constraint("ck_seed_lots_order_source", "seed_lots", type_="check")
    op.drop_index("ix_seed_lots_order_id", "seed_lots")
    op.drop_constraint("fk_seed_lots_order_id", "seed_lots", type_="foreignkey")
    op.drop_column("seed_lots", "order_id")
    op.drop_table("orders")
