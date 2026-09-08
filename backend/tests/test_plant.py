from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock
from uuid import uuid7

import pytest
from fastapi import HTTPException, Response

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.events.model import Event
from florabase.events.schemas import EventResponse, PlantGroupEventTarget, ResultingPlantSummary
from florabase.geographic_places.model import GeographicPlace
from florabase.locations.model import Location
from florabase.plants import api, service
from florabase.plants.model import Plant, PlantGroup
from florabase.plants.schemas import (
    PlantCreate,
    PlantExtractionCreate,
    PlantGroupCreate,
    PlantGroupUpdate,
    PlantReintegrationCreate,
    PlantUpdate,
    ReintegrationEligibilityStatus,
)
from florabase.plants.service import (
    PlantDomainConflictError,
    PlantGroupProjection,
    PlantProjection,
    PlantReferenceNotFoundError,
)
from florabase.reversals.model import OperationKind, OperationReceipt
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing
from florabase.suppliers.model import Supplier


def models() -> tuple[
    Plant,
    PlantGroup,
    BotanicalIdentity,
    Sowing,
    SeedLot,
    BotanicalIdentity,
    Supplier,
    GeographicPlace,
    Location,
]:
    now = datetime.now(UTC)
    identity = BotanicalIdentity(
        id=uuid7(), scientific_name="Solanum quitoense", created_at=now, updated_at=now
    )
    upstream_identity = BotanicalIdentity(
        id=uuid7(), scientific_name="Solanum sp.", created_at=now, updated_at=now
    )
    lot = SeedLot(
        id=uuid7(),
        botanical_identity_id=upstream_identity.id,
        label="Packet",
        created_at=now,
        updated_at=now,
    )
    sowing = Sowing(
        id=uuid7(),
        seed_lot_id=lot.id,
        label="Tray",
        lifecycle="failed",
        created_at=now,
        updated_at=now,
    )
    supplier = Supplier(id=uuid7(), name="Nursery", created_at=now, updated_at=now)
    place = GeographicPlace(
        id=uuid7(),
        name="Ecuador",
        place_kind="custom",
        created_at=now,
        updated_at=now,
    )
    location = Location(id=uuid7(), name="Bench", created_at=now, updated_at=now)
    plant = Plant(
        id=uuid7(),
        botanical_identity_id=identity.id,
        originating_sowing_id=sowing.id,
        direct_origin_kind=None,
        label="Individual",
        collection_entry_date_precision="month",
        collection_entry_date_year=2026,
        collection_entry_date_month=8,
        location_id=location.id,
        lifecycle="dead",
        created_at=now,
        updated_at=now,
    )
    group = PlantGroup(
        id=uuid7(),
        botanical_identity_id=identity.id,
        direct_origin_kind="purchased",
        supplier_id=supplier.id,
        material_provenance_place_id=place.id,
        location_id=location.id,
        quantity_value=12,
        quantity_is_approximate=True,
        lifecycle="active",
        created_at=now,
        updated_at=now,
    )
    return plant, group, identity, sowing, lot, upstream_identity, supplier, place, location


def direct_payload(
    identity: BotanicalIdentity, supplier: Supplier, place: GeographicPlace, location: Location
) -> PlantCreate:
    return PlantCreate(
        botanical_identity_id=identity.id,
        direct_origin_kind="other",
        direct_origin_detail="exchange table",
        supplier_id=supplier.id,
        material_provenance_place_id=place.id,
        label="Individual",
        collection_entry_date={"precision": "day", "year": 2026, "month": 8, "day": 31},
        location_id=location.id,
        lifecycle="lost",
        notes="Retained.",
    )


def database_with_references(items: tuple[object, ...]) -> MagicMock:
    database = MagicMock()
    lookup = {(type(item), item.id): item for item in items if hasattr(item, "id")}
    database.get.side_effect = lambda model, item_id, **_kwargs: lookup.get((model, item_id))
    return database


def test_services_create_update_project_and_preserve_independent_lineage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plant, group, identity, sowing, lot, upstream, supplier, place, location = models()
    database = database_with_references(
        (identity, sowing, lot, upstream, supplier, place, location)
    )
    created = service.create_plant(database, direct_payload(identity, supplier, place, location))
    assert created.direct_origin_detail == "exchange table"
    assert created.collection_entry_date_day == 31
    sowing_payload = PlantUpdate(botanical_identity_id=identity.id, originating_sowing_id=sowing.id)
    service.update_plant(database, created, sowing_payload)
    assert created.originating_sowing_id == sowing.id
    assert created.direct_origin_kind is None
    assert created.updated_at.tzinfo is UTC

    group_payload = PlantGroupCreate(
        botanical_identity_id=identity.id,
        quantity={"value": 5, "is_approximate": False},
    )
    created_group = service.create_plant_group(database, group_payload)
    assert created_group.quantity_value == 5
    corrected = PlantGroupUpdate(
        botanical_identity_id=identity.id,
        quantity={"value": 0, "is_approximate": False},
        lifecycle="dead",
    )
    service.update_plant_group(database, created_group, corrected)
    assert created_group.lifecycle == "dead"
    assert created_group.quantity_value == 0

    plant_row = (plant, identity, sowing, lot, upstream, None, None, location, None, None)
    group_row = (group, identity, None, None, None, supplier, place, location)
    database.execute.return_value.one_or_none.side_effect = [plant_row, group_row]
    assert service.get_plant(database, plant.id) == PlantProjection(*plant_row)
    assert service.get_plant_group(database, group.id) == PlantGroupProjection(*group_row)
    database.execute.return_value.__iter__.side_effect = [iter([plant_row]), iter([group_row])]
    assert service.list_plants(database) == [PlantProjection(*plant_row)]
    assert service.list_plant_groups(database) == [PlantGroupProjection(*group_row)]

    monkeypatch.setattr(service, "list_locations", lambda _: [location])
    monkeypatch.setattr(service, "list_geographic_places", lambda _: [place])
    plant_response = service.plant_responses(database, [PlantProjection(*plant_row)])[0]
    assert plant_response.botanical_identity.display_label == "Solanum quitoense"
    assert plant_response.originating_sowing is not None
    assert plant_response.originating_sowing.botanical_identity_display_label == "Solanum sp."
    assert plant_response.location is not None
    assert plant_response.location.display_path == "Bench"
    group_response = service.plant_group_responses(database, [PlantGroupProjection(*group_row)])[0]
    assert group_response.quantity is not None
    assert group_response.quantity.value == 12
    assert group_response.supplier is not None
    assert group_response.material_provenance is not None
    assert group_response.material_provenance.display_path == "Ecuador"


@pytest.mark.parametrize(
    ("missing_type", "code"),
    [
        (BotanicalIdentity, "botanical_identity_not_found"),
        (Sowing, "sowing_not_found"),
        (Supplier, "supplier_not_found"),
        (GeographicPlace, "geographic_place_not_found"),
        (Location, "location_not_found"),
    ],
)
def test_service_friendly_missing_reference(missing_type: type[object], code: str) -> None:
    _, _, identity, sowing, _, _, supplier, place, location = models()
    payload = PlantCreate(
        botanical_identity_id=identity.id,
        originating_sowing_id=sowing.id,
        location_id=location.id,
    )
    if missing_type in (Supplier, GeographicPlace):
        payload = direct_payload(identity, supplier, place, location)
    database = database_with_references((identity, sowing, supplier, place, location))
    original = database.get.side_effect
    database.get.side_effect = lambda model, item_id, **_kwargs: (
        None if model is missing_type else original(model, item_id)
    )
    with pytest.raises(PlantReferenceNotFoundError) as error:
        service.create_plant(database, payload)
    assert error.value.code == code


def test_extraction_service_locks_inherits_decrements_and_preserves_put_origin() -> None:
    plant, group, identity, _, _, _, _, _, location = models()
    group.botanical_identity_id = identity.id
    group.location_id = location.id
    group.quantity_value = 1
    group.quantity_is_approximate = False
    group.lifecycle = "active"
    database = database_with_references((identity, location))
    database.scalar.return_value = group
    extracted, updated_group, extraction_event = service.extract_plant(
        database, group.id, PlantExtractionCreate(label="Chosen")
    )
    assert extracted.originating_plant_group_id == group.id
    assert extracted.botanical_identity_id == identity.id
    assert extracted.location_id == location.id
    assert extracted.direct_origin_kind is None
    assert updated_group.quantity_value == 0
    assert updated_group.lifecycle == "completed"
    assert extraction_event.kind == "extraction"
    assert extraction_event.plant_group_id == group.id
    assert extraction_event.resulting_plant_id == extracted.id
    assert database.add.call_args_list[:2] == [((extracted,),), ((extraction_event,),)]
    receipt = database.add.call_args_list[2].args[0]
    assert isinstance(receipt, OperationReceipt)
    assert receipt.kind == "plant_group_extraction"
    assert receipt.before_lifecycle == "active"
    assert receipt.after_lifecycle == "completed"
    assert receipt.before_quantity_value == 1
    assert receipt.after_quantity_value == 0
    assert database.flush.call_count == 3

    extracted.id = plant.id
    allowed = PlantUpdate(
        botanical_identity_id=identity.id,
        label="Corrected",
        location_id=location.id,
        lifecycle="dead",
    )
    service.update_plant(database, extracted, allowed)
    assert extracted.originating_plant_group_id == group.id
    assert extracted.label == "Corrected"
    with pytest.raises(PlantDomainConflictError):
        service.update_plant(
            database,
            extracted,
            PlantUpdate(botanical_identity_id=identity.id, direct_origin_kind="unknown"),
        )


def test_extraction_service_rejects_missing_historical_and_exhausted_groups() -> None:
    database = MagicMock()
    database.scalar.return_value = None
    with pytest.raises(PlantReferenceNotFoundError):
        service.extract_plant(database, uuid7(), PlantExtractionCreate())

    group = PlantGroup(
        id=uuid7(),
        botanical_identity_id=uuid7(),
        direct_origin_kind="unknown",
        lifecycle="dead",
    )
    database.scalar.return_value = group
    with pytest.raises(PlantDomainConflictError) as historical:
        service.extract_plant(database, group.id, PlantExtractionCreate())
    assert historical.value.code == "plant_group_not_active"

    group.lifecycle = "active"
    group.quantity_value = 0
    group.quantity_is_approximate = False
    database.get.return_value = object()
    with pytest.raises(PlantDomainConflictError) as exhausted:
        service.extract_plant(database, group.id, PlantExtractionCreate())
    assert exhausted.value.code == "plant_group_quantity_exhausted"


def test_api_routes_success_not_found_reference_and_owner_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plant, group, identity, sowing, lot, upstream, supplier, place, location = models()
    plant_projection = PlantProjection(
        plant, identity, sowing, lot, upstream, None, None, location, None, None
    )
    group_projection = PlantGroupProjection(
        group, identity, None, None, None, supplier, place, location
    )
    database = MagicMock()
    monkeypatch.setattr(service, "list_locations", lambda _: [location])
    monkeypatch.setattr(service, "list_geographic_places", lambda _: [place])
    plant_response = service.plant_responses(database, [plant_projection])[0]
    group_response = service.plant_group_responses(database, [group_projection])[0]
    monkeypatch.setattr(api, "list_plants", lambda _: [plant_projection])
    monkeypatch.setattr(api, "list_plant_groups", lambda _: [group_projection])
    monkeypatch.setattr(api, "plant_responses", lambda _db, _items: [plant_response])
    monkeypatch.setattr(api, "plant_group_responses", lambda _db, _items: [group_response])
    monkeypatch.setattr(api, "get_plant", lambda _db, _id: plant_projection)
    monkeypatch.setattr(api, "get_plant_group", lambda _db, _id: group_projection)
    monkeypatch.setattr(api, "create_plant", lambda _db, _payload: plant)
    monkeypatch.setattr(api, "create_plant_group", lambda _db, _payload: group)
    monkeypatch.setattr(api, "update_plant", lambda _db, item, _payload: item)
    monkeypatch.setattr(api, "update_plant_group", lambda _db, item, _payload: item)
    actor = cast(Any, SimpleNamespace(owner=True))
    plant_write = PlantCreate(botanical_identity_id=identity.id, originating_sowing_id=sowing.id)
    group_write = PlantGroupCreate(botanical_identity_id=identity.id)

    assert api.list_all_plants(actor, database)[0].id == plant.id
    assert api.list_all_plant_groups(actor, database)[0].id == group.id
    response = Response()
    assert api.create_one_plant(plant_write, response, actor, database).id == plant.id
    assert response.headers["location"].endswith(str(plant.id))
    assert api.read_plant(plant.id, actor, database).id == plant.id
    assert (
        api.update_one_plant(
            plant.id, PlantUpdate.model_validate(plant_write.model_dump()), actor, database
        ).id
        == plant.id
    )
    assert api.create_one_plant_group(group_write, Response(), actor, database).id == group.id
    assert api.read_plant_group(group.id, actor, database).id == group.id
    assert (
        api.update_one_plant_group(
            group.id, PlantGroupUpdate.model_validate(group_write.model_dump()), actor, database
        ).id
        == group.id
    )
    _, _, extraction_event, receipt = reintegration_models()
    evaluation = service.ReintegrationEvaluation(
        ReintegrationEligibilityStatus.SAFE,
        receipt,
        plant,
        group,
        (),
        (),
    )
    monkeypatch.setattr(api, "evaluate_reintegration", lambda _db, _id: evaluation)
    eligibility = api.read_plant_reintegration_eligibility(plant.id, actor, database)
    assert eligibility.status == ReintegrationEligibilityStatus.SAFE
    assert eligibility.operation_receipt_id == receipt.id
    extraction_event.kind = "observation"
    evaluation = service.ReintegrationEvaluation(
        ReintegrationEligibilityStatus.CONFIRMATION_REQUIRED,
        receipt,
        plant,
        group,
        (),
        (extraction_event,),
    )
    monkeypatch.setattr(api, "evaluate_reintegration", lambda _db, _id: evaluation)
    eligibility = api.read_plant_reintegration_eligibility(plant.id, actor, database)
    assert len(eligibility.retained_observations) == 1

    reintegration_event = Event(id=uuid7(), plant_group_id=group.id, kind="reintegration")
    reintegration_event_response = EventResponse(
        id=reintegration_event.id,
        target=PlantGroupEventTarget(
            id=group.id,
            label=group.label,
            lifecycle=group_response.lifecycle,
            botanical_identity=group_response.botanical_identity,
        ),
        kind="reintegration",
        occurred_on=None,
        notes=None,
        destination_location_id=None,
        destination_location=None,
        recipient=None,
        resulting_plant_id=plant.id,
        resulting_plant=ResultingPlantSummary(
            id=plant.id,
            label=plant.label,
            botanical_identity=plant_response.botanical_identity,
        ),
        operation_kind="plant_group_extraction",
        operation_status="reversed",
        created_at=identity.created_at,
        updated_at=identity.updated_at,
    )
    with monkeypatch.context() as reintegration_patch:
        reintegration_patch.setattr(
            api,
            "reintegrate_plant",
            lambda *_args, **_kwargs: (plant, group, reintegration_event, receipt),
        )
        reintegration_patch.setattr(api, "_plant_response", lambda _db, _id: plant_response)
        reintegration_patch.setattr(api, "_plant_group_response", lambda _db, _id: group_response)
        reintegration_patch.setattr(
            api, "_event_response", lambda _db, _id: reintegration_event_response
        )
        response = Response()
        reintegrated = api.reintegrate_one_plant(
            plant.id, PlantReintegrationCreate(), response, actor, database
        )
        assert reintegrated.plant.id == plant.id
        assert reintegrated.plant_group.id == group.id
        assert reintegrated.event.id == reintegration_event.id
        assert response.headers["location"].endswith(str(reintegration_event.id))

    monkeypatch.setattr(api, "get_plant", lambda _db, _id: None)
    with pytest.raises(HTTPException) as missing:
        api.read_plant(uuid7(), actor, database)
    assert missing.value.status_code == 404
    monkeypatch.setattr(api, "get_plant_group", lambda _db, _id: None)
    with pytest.raises(HTTPException) as missing_group:
        api.read_plant_group(uuid7(), actor, database)
    assert missing_group.value.status_code == 404

    error = PlantReferenceNotFoundError("location_not_found", "Location not found")
    monkeypatch.setattr(api, "create_plant", lambda _db, _payload: (_ for _ in ()).throw(error))
    with pytest.raises(HTTPException) as invalid:
        api.create_one_plant(plant_write, Response(), actor, database)
    assert invalid.value.status_code == 404
    with pytest.raises(HTTPException) as forbidden:
        api.create_one_plant(
            plant_write, Response(), cast(Any, SimpleNamespace(owner=False)), database
        )
    assert forbidden.value.status_code == 403


def reintegration_models() -> tuple[Plant, PlantGroup, Event, OperationReceipt]:
    now = datetime.now(UTC)
    group = PlantGroup(
        id=uuid7(),
        botanical_identity_id=uuid7(),
        direct_origin_kind="unknown",
        quantity_value=9,
        quantity_is_approximate=False,
        lifecycle="active",
        created_at=now - timedelta(days=1),
        updated_at=now - timedelta(seconds=1),
    )
    plant = Plant(
        id=uuid7(),
        botanical_identity_id=group.botanical_identity_id,
        originating_plant_group_id=group.id,
        lifecycle="active",
        created_at=now - timedelta(seconds=1),
        updated_at=now - timedelta(seconds=1),
    )
    event = Event(
        id=uuid7(),
        plant_group_id=group.id,
        kind="extraction",
        resulting_plant_id=plant.id,
        created_at=now - timedelta(seconds=1),
        updated_at=now - timedelta(seconds=1),
    )
    receipt = OperationReceipt(
        id=uuid7(),
        kind="plant_group_extraction",
        status="applied",
        plant_id=plant.id,
        plant_group_id=group.id,
        event_id=event.id,
        before_lifecycle="active",
        after_lifecycle="active",
        before_quantity_kind="count",
        before_quantity_value=10,
        before_quantity_is_approximate=False,
        after_quantity_kind="count",
        after_quantity_value=9,
        after_quantity_is_approximate=False,
        created_at=now,
    )
    return plant, group, event, receipt


def reintegration_database(
    plant: Plant,
    group: PlantGroup,
    event: Event,
    receipt: OperationReceipt,
    *,
    seed_lot_count: int = 0,
    cutoff: datetime | None = None,
    later_plant_receipts: list[OperationReceipt] | None = None,
    later_group_receipts: list[OperationReceipt] | None = None,
    later_events: list[Event] | None = None,
) -> MagicMock:
    database = MagicMock()
    database.scalar.side_effect = [receipt, group, plant, seed_lot_count, cutoff]
    database.get.return_value = event
    database.scalars.side_effect = [
        later_plant_receipts or [],
        later_group_receipts or [],
        later_events or [],
    ]
    return database


def test_reintegration_evaluation_safe_confirmation_and_missing_receipt() -> None:
    plant, group, event, receipt = reintegration_models()
    safe = service.evaluate_reintegration(
        reintegration_database(plant, group, event, receipt), plant.id
    )
    assert safe.status == ReintegrationEligibilityStatus.SAFE
    assert safe.reasons == ()

    observation = Event(
        id=uuid7(),
        plant_id=plant.id,
        kind="observation",
        created_at=receipt.created_at + timedelta(seconds=1),
    )
    confirmation = service.evaluate_reintegration(
        reintegration_database(plant, group, event, receipt, later_events=[observation]),
        plant.id,
    )
    assert confirmation.status == ReintegrationEligibilityStatus.CONFIRMATION_REQUIRED
    assert confirmation.retained_observations == (observation,)

    database = MagicMock()
    database.scalar.side_effect = [None, plant]
    unavailable = service.evaluate_reintegration(database, plant.id)
    assert unavailable.status == ReintegrationEligibilityStatus.BLOCKED
    assert unavailable.reasons[0].code == "extraction_receipt_not_found"
    database.scalar.side_effect = [None, None]
    with pytest.raises(PlantReferenceNotFoundError):
        service.evaluate_reintegration(database, uuid7())


def test_reintegration_evaluation_reports_specific_blockers() -> None:
    plant, group, _event, receipt = reintegration_models()
    receipt.status = "reversed"
    plant.originating_plant_group_id = uuid7()
    plant.lifecycle = "transferred"
    plant.updated_at = receipt.created_at + timedelta(seconds=2)
    group.lifecycle = "completed"
    group.quantity_value = 7
    group.updated_at = receipt.created_at + timedelta(seconds=2)
    transfer = OperationReceipt(
        id=uuid7(),
        kind=OperationKind.PLANT_TRANSFER.value,
        status="applied",
        plant_id=plant.id,
        before_lifecycle="active",
        after_lifecycle="transferred",
        created_at=receipt.created_at + timedelta(seconds=1),
    )
    later_extraction = OperationReceipt(
        id=uuid7(),
        kind=OperationKind.PLANT_GROUP_EXTRACTION.value,
        status="applied",
        plant_id=uuid7(),
        plant_group_id=group.id,
        event_id=uuid7(),
        before_lifecycle="active",
        after_lifecycle="active",
        created_at=receipt.created_at + timedelta(seconds=1),
    )
    group_transfer = OperationReceipt(
        id=uuid7(),
        kind=OperationKind.PLANT_GROUP_TRANSFER.value,
        status="applied",
        plant_group_id=group.id,
        event_id=uuid7(),
        before_lifecycle="active",
        after_lifecycle="transferred",
        created_at=receipt.created_at + timedelta(seconds=2),
    )
    later_event = Event(
        id=uuid7(),
        plant_id=plant.id,
        kind="pruning",
        created_at=receipt.created_at + timedelta(seconds=1),
    )
    evaluation = service.evaluate_reintegration(
        reintegration_database(
            plant,
            group,
            Event(id=uuid7(), kind="other"),
            receipt,
            seed_lot_count=1,
            later_plant_receipts=[transfer],
            later_group_receipts=[later_extraction, group_transfer],
            later_events=[later_event],
        ),
        plant.id,
    )
    assert evaluation.status == ReintegrationEligibilityStatus.BLOCKED
    assert {
        "receipt_already_reversed",
        "plant_state_changed",
        "transfer_exists",
        "produced_seed_lot_exists",
        "later_extraction_exists",
        "source_group_transferred",
        "source_group_changed",
        "downstream_dependency",
    } <= {reason.code for reason in evaluation.reasons}


def test_reintegration_mutation_restores_snapshot_and_requires_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plant, group, _event, receipt = reintegration_models()
    database = MagicMock()
    blocked = service.ReintegrationEvaluation(
        ReintegrationEligibilityStatus.BLOCKED,
        receipt,
        plant,
        group,
        (service._reason("source_group_changed", "Changed"),),
        (),
    )
    monkeypatch.setattr(service, "evaluate_reintegration", lambda *_args, **_kwargs: blocked)
    with pytest.raises(PlantDomainConflictError):
        service.reintegrate_plant(database, plant.id, confirm_retained_observations=False)

    observation = Event(id=uuid7(), plant_id=plant.id, kind="observation")
    confirmation = service.ReintegrationEvaluation(
        ReintegrationEligibilityStatus.CONFIRMATION_REQUIRED,
        receipt,
        plant,
        group,
        (),
        (observation,),
    )
    monkeypatch.setattr(service, "evaluate_reintegration", lambda *_args, **_kwargs: confirmation)
    with pytest.raises(PlantDomainConflictError) as required:
        service.reintegrate_plant(database, plant.id, confirm_retained_observations=False)
    assert required.value.code == "reintegration_confirmation_required"

    result = service.reintegrate_plant(database, plant.id, confirm_retained_observations=True)
    assert result[:2] == (plant, group)
    assert plant.lifecycle == "reintegrated"
    assert group.quantity_value == 10
    assert result[2].kind == "reintegration"
    assert result[2].reversed_operation_receipt_id == receipt.id
    assert receipt.status == "reversed"
    database.add.assert_called_once_with(result[2])
