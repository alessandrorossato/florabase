from unittest.mock import MagicMock
from uuid import uuid7

import pytest

from florabase.lineage import service
from florabase.lineage.service import LineageCycleError
from florabase.plants import service as plant_service
from florabase.plants.model import Plant, PlantGroup
from florabase.plants.schemas import PlantGroupUpdate, PlantUpdate
from florabase.sowings import service as sowing_service
from florabase.sowings.model import Sowing
from florabase.sowings.schemas import SowingUpdate


def test_source_validation_rejects_self_and_long_cycles_but_respects_concrete_types() -> None:
    item_id, other_id = uuid7(), uuid7()
    database = MagicMock()
    database.execute.return_value.mappings.return_value = [
        {"kind": "plant", "id": other_id, "is_cycle": False},
        {"kind": "sowing", "id": item_id, "is_cycle": False},
    ]
    with pytest.raises(LineageCycleError):
        service.validate_source_assignment(database, ("sowing", item_id), ("plant", other_id))
    # UUID equality across concrete tables is not a self edge.
    service.validate_source_assignment(database, ("seed_lot", item_id), ("plant", other_id))
    with pytest.raises(LineageCycleError):
        service.validate_source_assignment(database, ("plant", other_id), ("plant", other_id))
    service.validate_source_assignment(database, ("plant", other_id), None)
    database.execute.return_value.mappings.return_value = [
        {"kind": "plant", "id": other_id, "is_cycle": True},
    ]
    with pytest.raises(LineageCycleError) as persisted:
        service.validate_source_assignment(database, ("seed_lot", item_id), ("plant", other_id))
    assert "Persisted" in persisted.value.message


@pytest.mark.parametrize("kind", ["plant", "plant_group", "sowing"])
def test_cycle_correction_returns_domain_conflict_before_writing(
    monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    item_id, source_id, identity_id = uuid7(), uuid7(), uuid7()
    database = MagicMock()

    def reject(*_args: object) -> None:
        raise LineageCycleError()

    if kind == "sowing":
        monkeypatch.setattr(sowing_service, "validate_source_assignment", reject)
        monkeypatch.setattr(
            sowing_service,
            "_require_references",
            lambda *_args, **_kwargs: (None, None),
        )
        item = Sowing(id=item_id, seed_lot_id=source_id, lifecycle="active")
        with pytest.raises(sowing_service.SowingDomainConflictError) as sowing_rejected:
            sowing_service.update_sowing(database, item, SowingUpdate(seed_lot_id=source_id))
        code = sowing_rejected.value.code
    else:
        monkeypatch.setattr(plant_service, "validate_source_assignment", reject)
        monkeypatch.setattr(plant_service, "_require_references", lambda *_args: None)
        payload = {"botanical_identity_id": identity_id, "originating_sowing_id": source_id}
        if kind == "plant":
            item_plant = Plant(id=item_id, originating_sowing_id=source_id, lifecycle="active")
            with pytest.raises(plant_service.PlantDomainConflictError) as plant_rejected:
                plant_service.update_plant(
                    database, item_plant, PlantUpdate.model_validate(payload)
                )
            code = plant_rejected.value.code
        else:
            item_group = PlantGroup(id=item_id, originating_sowing_id=source_id, lifecycle="active")
            with pytest.raises(plant_service.PlantDomainConflictError) as group_rejected:
                plant_service.update_plant_group(
                    database, item_group, PlantGroupUpdate.model_validate(payload)
                )
            code = group_rejected.value.code
    assert code == "lineage_cycle"
    database.flush.assert_not_called()


def test_lineage_projects_cuttings_and_preserves_the_existing_ancestry_types() -> None:
    from florabase.botanical_identities.model import BotanicalIdentity
    from florabase.cuttings import api as cutting_api
    from florabase.cuttings.model import PropagationAttempt, VegetativeLot, utc_now
    from florabase.seed_lots.model import SeedLot

    now = utc_now()
    identity = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Salvia rosmarinus",
        created_at=now,
        updated_at=now,
    )
    plant = Plant(id=uuid7(), label="Mother", lifecycle="active")
    group = PlantGroup(id=uuid7(), label="Original group", lifecycle="active")
    seed = SeedLot(id=uuid7(), label="Original seed", lifecycle="active", source_kind="unknown")
    sowing = Sowing(id=uuid7(), label="Original sowing", lifecycle="active")
    lot = VegetativeLot(id=uuid7(), label="Taken material", lifecycle="exhausted")
    attempt = PropagationAttempt(id=uuid7(), label="Clonal attempt", lifecycle="failed")
    path = [
        ("propagation_attempt", attempt.id),
        ("vegetative_lot", lot.id),
        ("plant", plant.id),
        ("plant_group", group.id),
        ("sowing", sowing.id),
        ("seed_lot", seed.id),
    ]
    walk = MagicMock()
    walk.mappings.return_value = [
        {"kind": kind, "id": key, "is_cycle": False} for kind, key in path
    ]
    database = MagicMock()
    database.get.return_value = attempt
    database.execute.side_effect = [
        walk,
        [(seed, identity)],
        [(plant, identity)],
        [(group, identity)],
        [(lot, identity)],
    ]
    database.scalars.side_effect = [[sowing], [attempt]]
    result = cutting_api.attempt_lineage(attempt.id, MagicMock(), database)
    assert result.subject.id == attempt.id
    assert [(entry.kind, entry.id) for entry in result.ancestors] == path[1:]
    assert [entry.label for entry in result.ancestors] == [
        "Taken material",
        "Mother",
        "Original group",
        "Original sowing",
        "Original seed",
    ]

    walk.mappings.return_value = [{"kind": "vegetative_lot", "id": lot.id, "is_cycle": False}]
    database.execute.side_effect = [walk, []]
    database.get.return_value = lot
    with pytest.raises(RuntimeError, match="missing concrete record"):
        cutting_api.lot_lineage(lot.id, MagicMock(), database)
