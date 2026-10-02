"""Complete supported histories, concrete edges, and orthogonal reference boundaries."""

from decimal import Decimal
from uuid import UUID, uuid7

import pytest
from psycopg.errors import ForeignKeyViolation
from sqlalchemy import Connection, event, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_profiles.service import add_botanical_native_range
from florabase.events.model import Event
from florabase.events.schemas import EventCreate, EventUpdate, TransferCreate
from florabase.events.service import create_event, delete_event, transfer_target, update_event
from florabase.geographic_places.model import GeographicPlace
from florabase.geographic_places.schemas import GeographicPlaceCreate, GeographicPlaceUpdate
from florabase.geographic_places.service import create_geographic_place, update_geographic_place
from florabase.harvests.schemas import HarvestWrite
from florabase.harvests.service import delete_harvest, write_harvest
from florabase.lineage.service import LineageKey, lineage
from florabase.locations.schemas import LocationCreate, LocationUpdate
from florabase.locations.service import create_location, update_location
from florabase.media.schemas import ExternalAssetCreate, LinkWrite, MediaTarget
from florabase.media.service import create_external_asset, create_link, unlink
from florabase.plants.model import Plant
from florabase.plants.schemas import PlantExtractionCreate, PlantUpdate
from florabase.plants.service import (
    PlantDomainConflictError,
    evaluate_reintegration,
    extract_plant,
    reintegrate_plant,
    update_plant,
)
from florabase.propagation.reversal import evaluate, reverse
from florabase.propagation.schemas import (
    PlantFromSowingCreate,
    PlantGroupFromSowingCreate,
    SeedLotSowingTransitionCreate,
)
from florabase.propagation.service import (
    create_plant_from_sowing,
    create_plant_group_from_sowing,
    create_sowing_from_seed_lot,
    propagation_summary,
)
from florabase.provenance_sites.schemas import ProvenanceSiteCreate
from florabase.provenance_sites.service import create_provenance_site
from florabase.reversals.model import OperationReceipt
from florabase.seed_lots.model import SeedLot
from florabase.seed_lots.schemas import SeedLotCreate
from florabase.seed_lots.service import create_seed_lot
from florabase.sowings.model import Sowing

pytestmark = pytest.mark.integration


def root(database: Session) -> tuple[BotanicalIdentity, SeedLot, Sowing]:
    identity = BotanicalIdentity(scientific_name=f"Lineage audit {uuid7().hex}")
    database.add(identity)
    database.flush()
    lot = create_seed_lot(
        database,
        SeedLotCreate.model_validate(
            {
                "botanical_identity_id": identity.id,
                "quantity": {"kind": "seed_count", "value": 100, "is_approximate": False},
            }
        ),
    )
    sowing, _ = create_sowing_from_seed_lot(
        database,
        lot.id,
        SeedLotSowingTransitionCreate.model_validate(
            {
                "sowing": {
                    "quantity": {"kind": "seed_count", "value": 20, "is_approximate": False}
                },
                "source_adjustment": {"mode": "partial"},
            }
        ),
    )
    return identity, lot, sowing


def path(database: Session, subject: LineageKey) -> list[LineageKey]:
    return [(node.kind, node.id) for node in lineage(database, subject).ancestors]


@pytest.mark.parametrize(
    "quantity", [{"value": 2, "is_approximate": False}, {"value": 8, "is_approximate": True}, None]
)
def test_extractions_reintegration_and_downstream_first_reversals_preserve_full_path(
    database_connection: Connection, quantity: dict[str, object] | None
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity, lot, sowing = root(db)
        group, _ = create_plant_group_from_sowing(
            db,
            sowing.id,
            PlantGroupFromSowingCreate.model_validate(
                {"botanical_identity_id": identity.id, "quantity": quantity}
            ),
            "completed",
        )
        first, _, first_event = extract_plant(db, group.id, PlantExtractionCreate())
        second, _, second_event = extract_plant(db, group.id, PlantExtractionCreate())
        expected = [("plant_group", group.id), ("sowing", sowing.id), ("seed_lot", lot.id)]
        for plant in (first, second):
            assert plant.originating_sowing_id is None
            assert path(db, ("plant", plant.id)) == expected
        if quantity and not quantity["is_approximate"]:
            assert (group.quantity_value, group.lifecycle) == (0, "completed")
        else:
            assert group.quantity_value == (quantity["value"] if quantity else None)
            assert group.lifecycle == "active"
        assert any(
            reason.code == "later_extraction_exists"
            for reason in evaluate_reintegration(db, first.id).reasons
        )
        assert evaluate(db, "plant_group", group.id).eligibility.status == "blocked"
        reintegrate_plant(db, second.id, confirm_retained_observations=False)
        reintegrate_plant(db, first.id, confirm_retained_observations=False)
        assert group.quantity_value == (quantity["value"] if quantity else None)
        assert group.quantity_is_approximate == (quantity["is_approximate"] if quantity else None)
        assert group.lifecycle == "active"
        assert first.lifecycle == second.lifecycle == "reintegrated"
        assert path(db, ("plant", first.id)) == expected
        assert db.get(Event, first_event.id) is not None
        assert db.get(Event, second_event.id) is not None
        with pytest.raises(PlantDomainConflictError, match="already"):
            reintegrate_plant(db, first.id, confirm_retained_observations=False)
        summary = propagation_summary(db, sowing.id)
        assert {p.originating_plant_group_id for p in summary.plants} == {group.id}
        assert summary.exact_descendant_count == (
            2 if quantity and not quantity["is_approximate"] else 0
        )
        reverse(db, "plant_group", group.id, confirm=False)
        reverse(db, "sowing", sowing.id, confirm=False)
        assert group.lifecycle == sowing.lifecycle == "reversed"
        assert path(db, ("plant", first.id)) == expected
        assert lot.quantity_value == Decimal(100)
        assert propagation_summary(db, sowing.id).exact_descendant_count == 0
        assert db.scalar(
            select(OperationReceipt.id).where(
                OperationReceipt.plant_id == first.id, OperationReceipt.status == "reversed"
            )
        )


def test_siblings_same_identity_are_independent_and_retained_after_transfer(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity, lot, sowing = root(db)
        other_lot = create_seed_lot(db, SeedLotCreate(botanical_identity_id=identity.id))
        other_sowing, _ = create_sowing_from_seed_lot(
            db,
            other_lot.id,
            SeedLotSowingTransitionCreate.model_validate(
                {"sowing": {}, "source_adjustment": {"mode": "none"}}
            ),
        )
        plant, _ = create_plant_from_sowing(
            db, sowing.id, PlantFromSowingCreate(botanical_identity_id=identity.id), "active"
        )
        sibling, _ = create_plant_from_sowing(
            db, sowing.id, PlantFromSowingCreate(botanical_identity_id=identity.id), "active"
        )
        group, _ = create_plant_group_from_sowing(
            db,
            sowing.id,
            PlantGroupFromSowingCreate.model_validate(
                {
                    "botanical_identity_id": identity.id,
                    "quantity": {"value": 5, "is_approximate": False},
                }
            ),
            "active",
        )
        other_group, _ = create_plant_group_from_sowing(
            db,
            other_sowing.id,
            PlantGroupFromSowingCreate(botanical_identity_id=identity.id),
            "active",
        )
        extracted, _, _ = extract_plant(db, group.id, PlantExtractionCreate())
        before = {p.id: path(db, ("plant", p.id)) for p in (plant, sibling, extracted)}
        transfer_target(db, "plant", plant.id, TransferCreate())
        transfer_target(db, "plant", extracted.id, TransferCreate())
        transfer_target(db, "plant_group", group.id, TransferCreate())
        for p in (plant, sibling, extracted):
            assert path(db, ("plant", p.id)) == before[p.id]
        assert group.quantity_value == 4
        assert path(db, ("plant_group", group.id)) == [("sowing", sowing.id), ("seed_lot", lot.id)]
        assert path(db, ("plant_group", other_group.id)) == [
            ("sowing", other_sowing.id),
            ("seed_lot", other_lot.id),
        ]
        summary = propagation_summary(db, sowing.id)
        assert {p.id for p in summary.plants} == {plant.id, sibling.id, extracted.id}
        # Transferred historical individuals remain tracked; this is not an active-holdings count.
        assert summary.exact_descendant_count == 7
        assert evaluate_reintegration(db, extracted.id).status == "blocked"
        assert evaluate(db, "plant_group", group.id).eligibility.status == "blocked"


def test_five_generations_use_concrete_edges_and_batched_lineage_queries(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity, lot, sowing = root(db)
        expected: list[LineageKey] = [("sowing", sowing.id), ("seed_lot", lot.id)]
        for _ in range(5):
            group, _ = create_plant_group_from_sowing(
                db,
                sowing.id,
                PlantGroupFromSowingCreate(botanical_identity_id=identity.id),
                "active",
            )
            plant, _, _ = extract_plant(db, group.id, PlantExtractionCreate())
            expected = [("plant_group", group.id), *expected]
            assert path(db, ("plant", plant.id)) == expected
            lot = create_seed_lot(
                db,
                SeedLotCreate.model_validate(
                    {
                        "botanical_identity_id": identity.id,
                        "source_kind": "collection_produced",
                        "producer_plant_id": plant.id,
                    }
                ),
            )
            assert evaluate_reintegration(db, plant.id).status == "blocked"
            sowing, _ = create_sowing_from_seed_lot(
                db,
                lot.id,
                SeedLotSowingTransitionCreate.model_validate(
                    {"sowing": {}, "source_adjustment": {"mode": "none"}}
                ),
            )
            expected = [("sowing", sowing.id), ("seed_lot", lot.id), ("plant", plant.id), *expected]
        final, _ = create_plant_from_sowing(
            db, sowing.id, PlantFromSowingCreate(botanical_identity_id=identity.id), "active"
        )
        queries: list[str] = []

        def record(
            _conn: object,
            _cursor: object,
            statement: str,
            _params: object,
            _context: object,
            _many: object,
        ) -> None:
            queries.append(statement)

        event.listen(database_connection, "before_cursor_execute", record)
        try:
            assert path(db, ("plant", final.id)) == expected
        finally:
            event.remove(database_connection, "before_cursor_execute", record)
        assert len(expected) == 22
        assert len(queries) == 5  # One recursive walk plus one summary batch per concrete type.


def test_event_location_identity_provenance_media_and_harvest_never_supply_lineage(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity, lot, sowing = root(db)
        plant, _ = create_plant_from_sowing(
            db, sowing.id, PlantFromSowingCreate(botanical_identity_id=identity.id), "active"
        )
        group, _ = create_plant_group_from_sowing(
            db, sowing.id, PlantGroupFromSowingCreate(botanical_identity_id=identity.id), "active"
        )
        independent = Plant(botanical_identity_id=identity.id, direct_origin_kind="unknown")
        db.add(independent)
        db.flush()
        subjects: list[LineageKey] = [
            ("plant", plant.id),
            ("plant_group", group.id),
            ("plant", independent.id),
            ("sowing", sowing.id),
        ]
        before = {key: path(db, key) for key in subjects}
        location_a = create_location(db, LocationCreate(name="Audit bench A"))
        location_b = create_location(db, LocationCreate(name="Audit bench B"))
        movement = create_event(
            db,
            "plant",
            plant.id,
            EventCreate(kind="movement", destination_location_id=location_a.id),
        )
        update_event(
            db, movement, EventUpdate(kind="movement", destination_location_id=location_b.id)
        )
        delete_event(db, movement)
        assert plant.location_id == location_a.id  # History correction/deletion never replays.
        update_location(
            db, location_a.id, LocationUpdate(name=location_a.name, parent_id=location_b.id)
        )
        world = db.scalar(select(GeographicPlace).where(GeographicPlace.parent_id.is_(None)))
        assert world is not None
        area = create_geographic_place(
            db, GeographicPlaceCreate(name="Audit area", parent_id=world.id)
        )
        place = create_geographic_place(
            db, GeographicPlaceCreate(name="Audit site area", parent_id=world.id)
        )
        site = create_provenance_site(
            db, ProvenanceSiteCreate(name="Shared origin", geographic_place_id=place.id)
        )
        add_botanical_native_range(db, identity.id, place.id)
        update_geographic_place(
            db, place.id, GeographicPlaceUpdate(name=place.name, parent_id=area.id)
        )
        independent.provenance_site_id = lot.provenance_site_id = site.id
        corrected_identity = BotanicalIdentity(scientific_name=f"Corrected audit {uuid7().hex}")
        db.add(corrected_identity)
        db.flush()
        update_plant(
            db,
            plant,
            PlantUpdate(
                botanical_identity_id=corrected_identity.id,
                originating_sowing_id=sowing.id,
                location_id=location_b.id,
            ),
        )
        identity.scientific_name = f"Renamed audit {uuid7().hex}"
        db.flush()
        asset = create_external_asset(
            db,
            ExternalAssetCreate(
                image_url="https://example.com/a.png",
                source_url="https://example.com/a",
                attribution="Audit",
            ),
            commit=False,
        )
        targets: list[tuple[MediaTarget, UUID]] = [
            ("sowing", sowing.id),
            ("plant", plant.id),
            ("plant", independent.id),
        ]
        links = [
            create_link(db, target, item_id, asset.id, LinkWrite(), commit=False)
            for target, item_id in targets
        ]
        for source_field, item_id in [("plant_id", plant.id), ("plant_group_id", group.id)]:
            harvest = write_harvest(
                db,
                HarvestWrite.model_validate(
                    {source_field: item_id, "items": [{"material_kind": "seed"}]}
                ),
            )
            create_link(db, "harvest", harvest.id, asset.id, LinkWrite(), commit=False)
            assert {key: path(db, key) for key in subjects} == before
            # Correct production context to an unrelated specimen; it never moves ancestry.
            write_harvest(
                db,
                HarvestWrite.model_validate(
                    {"plant_id": independent.id, "items": [{"material_kind": "whole_plant"}]}
                ),
                harvest.id,
            )
            delete_harvest(db, harvest.id)
        for link in links:
            unlink(db, link.id)
        assert {key: path(db, key) for key in subjects} == before
        assert before[("plant", independent.id)] == []
        assert lot.producer_plant_id is None  # Seed HarvestItem never becomes a producer edge.


@pytest.mark.parametrize(
    ("table", "field", "target"),
    [
        ("sowings", "seed_lot_id", "plant"),
        ("plants", "originating_sowing_id", "seed_lot"),
        ("plant_groups", "originating_sowing_id", "plant"),
    ],
)
def test_cross_type_references_and_required_ancestor_deletion_are_rejected(
    database_connection: Connection, table: str, field: str, target: str
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity, lot, sowing = root(db)
        group, _ = create_plant_group_from_sowing(
            db, sowing.id, PlantGroupFromSowingCreate(botanical_identity_id=identity.id), "active"
        )
        plant, _, _ = extract_plant(db, group.id, PlantExtractionCreate())
        propagated, _ = create_plant_from_sowing(
            db, sowing.id, PlantFromSowingCreate(botanical_identity_id=identity.id), "active"
        )
        item_id = {"sowings": sowing.id, "plants": propagated.id, "plant_groups": group.id}[table]
        wrong_id = {"plant": plant.id, "seed_lot": lot.id}[target]
        with pytest.raises(IntegrityError) as wrong_type, db.begin_nested():
            db.execute(
                text(f"UPDATE {table} SET {field}=:wrong WHERE id=:id"),
                {"wrong": wrong_id, "id": item_id},
            )
        assert isinstance(wrong_type.value.orig, ForeignKeyViolation)
        with pytest.raises(IntegrityError), db.begin_nested():
            db.execute(text("UPDATE sowings SET seed_lot_id=id WHERE id=:id"), {"id": sowing.id})
        for ancestor_table, ancestor_id in [
            ("seed_lots", lot.id),
            ("sowings", sowing.id),
            ("plant_groups", group.id),
            ("plants", plant.id),
        ]:
            with pytest.raises(IntegrityError), db.begin_nested():
                db.execute(text(f"DELETE FROM {ancestor_table} WHERE id=:id"), {"id": ancestor_id})


def test_allowed_source_correction_keeps_receipt_facts_and_blocks_unsafe_inverse(
    database_connection: Connection,
) -> None:
    from florabase.plants.schemas import PlantGroupUpdate
    from florabase.plants.service import update_plant_group
    from florabase.sowings.schemas import SowingUpdate
    from florabase.sowings.service import update_sowing

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity, lot, sowing = root(db)
        _, other_lot, other_sowing = root(db)
        group, _ = create_plant_group_from_sowing(
            db, sowing.id, PlantGroupFromSowingCreate(botanical_identity_id=identity.id), "active"
        )
        plant, _, _ = extract_plant(db, group.id, PlantExtractionCreate())
        receipt = db.scalar(
            select(OperationReceipt).where(
                OperationReceipt.kind == "sowing_to_plant_group",
                OperationReceipt.plant_group_id == group.id,
            )
        )
        assert receipt is not None
        original_facts = tuple(
            getattr(receipt, column.name) for column in OperationReceipt.__table__.columns
        )
        update_plant_group(
            db,
            group,
            PlantGroupUpdate(
                botanical_identity_id=identity.id, originating_sowing_id=other_sowing.id
            ),
        )
        assert path(db, ("plant", plant.id)) == [
            ("plant_group", group.id),
            ("sowing", other_sowing.id),
            ("seed_lot", other_lot.id),
        ]
        assert (
            tuple(getattr(receipt, column.name) for column in OperationReceipt.__table__.columns)
            == original_facts
        )
        assert any(
            reason.code == "receipt_relationship_mismatch"
            for reason in evaluate(db, "plant_group", group.id).eligibility.reasons
        )
        assert evaluate_reintegration(db, plant.id).status == "blocked"
        update_sowing(db, sowing, SowingUpdate(seed_lot_id=other_lot.id))
        assert sowing.seed_lot_id != lot.id
        assert any(
            reason.code == "receipt_relationship_mismatch"
            for reason in evaluate(db, "sowing", sowing.id).eligibility.reasons
        )
