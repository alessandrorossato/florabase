from decimal import Decimal

import pytest
from sqlalchemy import Connection, select
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.events.schemas import TransferCreate
from florabase.events.service import transfer_target
from florabase.plants.model import PlantGroup
from florabase.plants.schemas import PlantExtractionCreate
from florabase.plants.service import extract_plant
from florabase.propagation import service as propagation_service
from florabase.propagation.schemas import (
    PlantFromSowingCreate,
    PlantGroupFromSowingCreate,
    SeedLotSowingTransitionCreate,
)
from florabase.propagation.service import (
    create_plant_from_sowing,
    create_plant_group_from_sowing,
    create_sowing_from_seed_lot,
)
from florabase.reversals.model import OperationReceipt
from florabase.seed_lots.model import SeedLot

pytestmark = pytest.mark.integration


def _transition(
    quantity: dict[str, object] | None, adjustment: dict[str, object]
) -> SeedLotSowingTransitionCreate:
    return SeedLotSowingTransitionCreate.model_validate(
        {"sowing": {"quantity": quantity}, "source_adjustment": adjustment}
    )


def test_supported_operations_persist_typed_authoritative_receipts(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        identity = BotanicalIdentity(scientific_name="Receipt coverage")
        database.add(identity)
        database.flush()
        exact = SeedLot(
            botanical_identity_id=identity.id,
            quantity_kind="seed_count",
            quantity_value=Decimal(100),
            quantity_is_approximate=False,
        )
        approximate = SeedLot(
            botanical_identity_id=identity.id,
            quantity_kind="seed_count",
            quantity_value=Decimal(100),
            quantity_is_approximate=True,
        )
        unknown = SeedLot(botanical_identity_id=identity.id)
        weight = SeedLot(
            botanical_identity_id=identity.id,
            quantity_kind="weight",
            quantity_value=Decimal("2.5"),
            quantity_unit="g",
            quantity_is_approximate=False,
        )
        database.add_all([exact, approximate, unknown, weight])
        database.flush()

        sowing, _ = create_sowing_from_seed_lot(
            database,
            exact.id,
            _transition(
                {"kind": "seed_count", "value": 20, "is_approximate": False},
                {"mode": "partial"},
            ),
        )
        create_sowing_from_seed_lot(
            database,
            approximate.id,
            _transition(
                {"kind": "seed_count", "value": 20, "is_approximate": True},
                {
                    "mode": "partial",
                    "resulting_quantity": {
                        "kind": "seed_count",
                        "value": 73,
                        "is_approximate": True,
                    },
                },
            ),
        )
        create_sowing_from_seed_lot(database, unknown.id, _transition(None, {"mode": "partial"}))
        create_sowing_from_seed_lot(
            database,
            weight.id,
            _transition(
                {"kind": "weight", "value": "0.5", "unit": "g", "is_approximate": False},
                {"mode": "partial"},
            ),
        )
        plant, _ = create_plant_from_sowing(
            database,
            sowing.id,
            PlantFromSowingCreate(botanical_identity_id=identity.id),
            "completed",
        )
        group, _ = create_plant_group_from_sowing(
            database,
            sowing.id,
            PlantGroupFromSowingCreate(
                botanical_identity_id=identity.id,
                quantity={"value": 4, "is_approximate": False},
            ),
            "failed",
        )

        extraction_groups = [
            PlantGroup(
                botanical_identity_id=identity.id,
                direct_origin_kind="unknown",
                quantity_value=10,
                quantity_is_approximate=False,
            ),
            PlantGroup(
                botanical_identity_id=identity.id,
                direct_origin_kind="unknown",
                quantity_value=10,
                quantity_is_approximate=True,
            ),
            PlantGroup(botanical_identity_id=identity.id, direct_origin_kind="unknown"),
        ]
        database.add_all(extraction_groups)
        database.flush()
        for extraction_group in extraction_groups:
            extract_plant(database, extraction_group.id, PlantExtractionCreate())

        plant_event, _ = transfer_target(database, "plant", plant.id, TransferCreate())
        group_event, _ = transfer_target(database, "plant_group", group.id, TransferCreate())
        receipts = list(database.scalars(select(OperationReceipt).order_by(OperationReceipt.id)))

        assert len(receipts) == 11
        assert all(receipt.id.version == 7 for receipt in receipts)
        assert all(receipt.created_at.utcoffset() is not None for receipt in receipts)
        by_kind: dict[str, list[OperationReceipt]] = {}
        for receipt in receipts:
            by_kind.setdefault(receipt.kind, []).append(receipt)
        assert {kind: len(items) for kind, items in by_kind.items()} == {
            "seed_lot_to_sowing": 4,
            "sowing_to_plant": 1,
            "sowing_to_plant_group": 1,
            "plant_group_extraction": 3,
            "plant_transfer": 1,
            "plant_group_transfer": 1,
        }

        exact_receipt = next(
            item for item in by_kind["seed_lot_to_sowing"] if item.seed_lot_id == exact.id
        )
        assert (exact_receipt.before_quantity_value, exact_receipt.after_quantity_value) == (
            Decimal(100),
            Decimal(80),
        )
        approximate_receipt = next(
            item for item in by_kind["seed_lot_to_sowing"] if item.seed_lot_id == approximate.id
        )
        assert (
            approximate_receipt.before_quantity_value,
            approximate_receipt.after_quantity_value,
        ) == (
            Decimal(100),
            Decimal(73),
        )
        assert approximate_receipt.before_quantity_is_approximate is True
        assert approximate_receipt.after_quantity_is_approximate is True
        unknown_receipt = next(
            item for item in by_kind["seed_lot_to_sowing"] if item.seed_lot_id == unknown.id
        )
        assert unknown_receipt.before_quantity_kind is None
        assert unknown_receipt.after_quantity_kind is None
        weight_receipt = next(
            item for item in by_kind["seed_lot_to_sowing"] if item.seed_lot_id == weight.id
        )
        assert weight_receipt.before_quantity_unit == "g"
        assert weight_receipt.after_quantity_unit == "g"

        extraction_receipts = by_kind["plant_group_extraction"]
        exact_extraction = next(
            item for item in extraction_receipts if item.plant_group_id == extraction_groups[0].id
        )
        assert (exact_extraction.before_quantity_value, exact_extraction.after_quantity_value) == (
            Decimal(10),
            Decimal(9),
        )
        for item in extraction_receipts:
            assert item.event_id is not None
            assert item.plant_id is not None
        assert by_kind["plant_transfer"][0].event_id == plant_event.id
        assert by_kind["plant_transfer"][0].before_lifecycle == "active"
        assert by_kind["plant_transfer"][0].after_lifecycle == "transferred"
        assert by_kind["plant_group_transfer"][0].event_id == group_event.id
        assert by_kind["plant_group_transfer"][0].before_quantity_value == 4
        assert by_kind["plant_group_transfer"][0].after_quantity_value == 4

        exact.quantity_value = Decimal(76)
        database.flush()
        database.refresh(exact_receipt)
        assert exact_receipt.before_quantity_value == 100
        assert exact_receipt.after_quantity_value == 80


def test_receipt_failure_rolls_back_the_authoritative_operation(
    database_connection: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        identity = BotanicalIdentity(scientific_name="Receipt rollback")
        database.add(identity)
        database.flush()
        seed_lot = SeedLot(
            botanical_identity_id=identity.id,
            quantity_kind="seed_count",
            quantity_value=Decimal(10),
            quantity_is_approximate=False,
        )
        database.add(seed_lot)
        database.flush()
        nested = database.begin_nested()

        def fail_receipt(*args: object, **kwargs: object) -> None:
            raise RuntimeError("receipt persistence failed")

        monkeypatch.setattr(propagation_service, "add_receipt", fail_receipt)
        with pytest.raises(RuntimeError, match="receipt persistence failed"):
            propagation_service.create_sowing_from_seed_lot(
                database,
                seed_lot.id,
                _transition(
                    {"kind": "seed_count", "value": 8, "is_approximate": False},
                    {"mode": "partial"},
                ),
            )
        nested.rollback()
        database.expire_all()

        restored = database.get(SeedLot, seed_lot.id)
        assert restored is not None
        assert restored.quantity_value == 10
        assert list(database.scalars(select(OperationReceipt))) == []
