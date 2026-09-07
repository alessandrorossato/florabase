"""Closed, typed propagation result snapshot contract (version 1)."""

from florabase.plants.model import Plant, PlantGroup
from florabase.reversals.service import QuantitySnapshot, group_quantity, seed_quantity
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing


def result_snapshot(result: Sowing | Plant | PlantGroup) -> dict[str, object]:
    quantity = (
        seed_quantity(result)
        if isinstance(result, Sowing)
        else group_quantity(result)
        if isinstance(result, PlantGroup)
        else QuantitySnapshot(None, None, None, None)
    )
    date_prefix = "sowing_date" if isinstance(result, Sowing) else "collection_entry_date"
    return {
        "result_snapshot_version": 1,
        "result_lifecycle": result.lifecycle,
        **quantity.columns("result"),
        "result_botanical_identity_id": (
            None if isinstance(result, Sowing) else result.botanical_identity_id
        ),
        "result_location_id": result.location_id,
        **{
            f"result_date_{part}": getattr(result, f"{date_prefix}_{part}")
            for part in ("precision", "year", "month", "day")
        },
    }


def propagation_snapshot(
    source: SeedLot | Sowing, result: Sowing | Plant | PlantGroup
) -> dict[str, object]:
    return {
        **result_snapshot(result),
        "source_location_id": source.location_id,
        "source_seed_lot_id": source.seed_lot_id if isinstance(source, Sowing) else None,
    }
