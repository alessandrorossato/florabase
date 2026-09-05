from datetime import UTC
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid7

from florabase.plants.model import PlantGroup
from florabase.reversals.model import OperationKind, OperationReceipt
from florabase.reversals.service import add_receipt, group_quantity, seed_quantity
from florabase.seed_lots.model import SeedLot


def test_quantity_snapshots_preserve_exact_approximate_unknown_and_units() -> None:
    exact_weight = SeedLot(
        quantity_kind="weight",
        quantity_value=Decimal("2.50"),
        quantity_unit="g",
        quantity_is_approximate=False,
    )
    approximate_group = PlantGroup(quantity_value=12, quantity_is_approximate=True)
    unknown = SeedLot()

    assert seed_quantity(exact_weight).columns("before") == {
        "before_quantity_kind": "weight",
        "before_quantity_value": Decimal("2.50"),
        "before_quantity_unit": "g",
        "before_quantity_is_approximate": False,
    }
    assert group_quantity(approximate_group).columns("after") == {
        "after_quantity_kind": "count",
        "after_quantity_value": Decimal(12),
        "after_quantity_unit": None,
        "after_quantity_is_approximate": True,
    }
    assert seed_quantity(unknown).columns("before") == {
        "before_quantity_kind": None,
        "before_quantity_value": None,
        "before_quantity_unit": None,
        "before_quantity_is_approximate": None,
    }


def test_add_receipt_is_internal_typed_and_uses_uuid7_utc_defaults() -> None:
    database = MagicMock()
    seed_lot_id, sowing_id = uuid7(), uuid7()
    receipt = add_receipt(
        database,
        kind=OperationKind.SEED_LOT_TO_SOWING,
        seed_lot_id=seed_lot_id,
        sowing_id=sowing_id,
        adjustment_mode="none",
        before_lifecycle="active",
        after_lifecycle="active",
    )

    assert isinstance(receipt, OperationReceipt)
    assert receipt.kind == "seed_lot_to_sowing"
    assert receipt.seed_lot_id == seed_lot_id
    assert receipt.sowing_id == sowing_id
    database.add.assert_called_once_with(receipt)
    database.flush.assert_called_once_with()

    generated_id = OperationReceipt.__table__.c.id.default.arg(None)
    generated_at = OperationReceipt.__table__.c.created_at.default.arg(None)
    assert generated_id.version == 7
    assert generated_at.tzinfo is UTC
