"""Review fixture acceptance runs only in the guarded disposable PostgreSQL workflow."""

import json
import socket
import sys
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from sqlalchemy import Connection, select
from sqlalchemy.orm import Session

from florabase.db.base import Base
from florabase.provenance_sites.service import collection_provenance_map
from florabase.seed_lots.schemas import SeedLotCreate
from florabase.seed_lots.service import SeedLotDomainConflictError

sys.path.insert(0, "/review")
v5 = pytest.importorskip("review_dataset_v5", reason="available in integration runner only")
pytestmark = pytest.mark.integration


def isolate_fixture_tables(connection: Connection) -> None:
    """Use empty synthetic state inside the disposable test transaction only."""
    table_names = {table.name for table in Base.metadata.tables.values()}
    # v4 preserves canonical geography installed by migrations; only remove app-owned custom rows.
    table_names.discard("geographic_places")
    quoted = ", ".join(f'"{name}"' for name in sorted(table_names))
    connection.exec_driver_sql(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE")
    while True:
        result = connection.exec_driver_sql(
            """
            DELETE FROM geographic_places AS place
            WHERE place.place_kind = 'custom'
              AND NOT EXISTS (
                SELECT 1 FROM geographic_places AS child
                WHERE child.parent_id = place.id
              )
            """
        )
        if result.rowcount == 0:
            break


def test_extended_dataset_preserves_baseline_and_operator_edits(
    database_connection: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FLORABASE_WORKFLOW_MODE", "review")
    isolate_fixture_tables(database_connection)

    # PostgreSQL uses its Unix/established connection. Any fixture network acquisition fails.
    def no_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("Fixture attempted unexpected network access")

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        owner = v5.v4.bootstrap_owner(database, "review-owner", "test-only-review-password-v5")
        password_hash = owner.password_hash
        monkeypatch.setattr(socket, "create_connection", no_network)
        monkeypatch.setattr(httpx.HTTPTransport, "handle_request", no_network)

        async def no_async_network(*args: object, **kwargs: object) -> None:
            raise AssertionError("Fixture attempted unexpected asynchronous network access")

        monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", no_async_network)
        baseline = v5.v4.seed(database, tmp_path)
        baseline_before = json.loads(json.dumps(baseline))
        extension = v5.seed(database, tmp_path, baseline)
        assert extension["state"] == "ready"
        assert baseline == baseline_before
        v5.v4.validate_manifest(database, tmp_path, baseline)
        assert owner.password_hash == password_hash
        first_counts = v5.counts(database)
        for key, minimum in {
            "identity": 30,
            "seed": 25,
            "plant": 15,
            "group": 5,
            "sowing": 10,
            "order": 10,
            "supplier": 8,
            "site": 12,
            "identities_with_ranges": 15,
            "local_media": 8,
            "external_media": 7,
        }.items():
            assert first_counts[key] >= minimum, (key, first_counts)
        seed = database.get(v5.v4.SeedLot, UUID(extension["records"]["seed:00"]))
        assert seed is not None
        refs = extension["records"]
        assert set(refs) == v5.expected_keys(v5.inputs()[0])
        assert UUID(refs["identity:00"]).version == 7
        assert seed.acquisition_date_year is None
        assert seed.quantity_value is None
        approximate = database.get(v5.v4.SeedLot, UUID(refs["seed:01"]))
        exact = database.get(v5.v4.SeedLot, UUID(refs["seed:02"]))
        assert approximate is not None
        assert exact is not None
        assert approximate.quantity_is_approximate
        assert approximate.acquisition_date_month is None
        assert not exact.quantity_is_approximate
        assert exact.acquisition_date_day is None
        exhausted = database.get(v5.v4.SeedLot, UUID(refs["seed:26"]))
        assert exhausted is not None
        assert exhausted.quantity_value == 0
        produced = database.get(v5.v4.SeedLot, UUID(refs["seed:produced"]))
        assert produced is not None
        assert produced.producer_plant_id == UUID(refs["plant:00"])
        group = database.get(v5.v4.PlantGroup, UUID(refs["group:0"]))
        assert group is not None
        assert group.quantity_value == 11
        mismatch = SeedLotCreate(
            botanical_identity_id=UUID(refs["identity:28"]),
            source_kind="purchased",
            supplier_id=UUID(refs["supplier:1"]),
            order_id=UUID(refs["order:00"]),
        )
        with pytest.raises(SeedLotDomainConflictError) as conflict:
            v5.v4.seeds.create_seed_lot(database, mismatch)
        assert conflict.value.code == "order_supplier_conflict"
        mapped = collection_provenance_map(database)
        assert mapped.total_provenance_sites == 14
        assert mapped.coordinate_less_sites == 2
        assert len(mapped.sites) == 12
        records = [record for site in mapped.sites for record in site.records]
        assert UUID(refs["plant:extracted"]) not in {record.id for record in records}
        assert UUID(refs["plant:derived"]) not in {record.id for record in records}
        shared = next(site for site in mapped.sites if str(site.id) == refs["site:00"])
        assert (
            len(shared.records)
            > len({record.botanical_identity.id for record in shared.records})
            > 1
        )
        assert {record.record_type for record in records} == {"seed_lot", "plant", "plant_group"}
        assert any(site.usage.total == 0 for site in mapped.sites)
        assert any(site.coordinate_accuracy_m is None for site in mapped.sites)
        selected = [UUID(refs[f"identity:{i:02d}"]) for i in range(5)]
        ranges = list(
            database.scalars(
                select(v5.BotanicalProfileNativeRange).where(
                    v5.BotanicalProfileNativeRange.botanical_profile_id.in_(selected)
                )
            )
        )
        places = {place.id: place for place in database.scalars(select(v5.v4.GeographicPlace))}
        for code, expected in {"BR": 5, "TH": 4, "IT": 3, "US": 2, "AU": 1}.items():
            assert (
                sum(places[row.geographic_place_id].source_code == code for row in ranges)
                == expected
            )
        _, photos, _ = v5.inputs()
        for index, photo in enumerate(photos.values()):
            local = database.get(v5.MediaAsset, UUID(refs[f"asset:local:{index}"]))
            assert local is not None
            assert local.attachment_id
            assert photo["creator"] in local.attribution
            assert local.licence_label == photo["licence"]
            assert local.licence_url == photo["licence_url"]
            if index < 7:
                external = database.get(v5.MediaAsset, UUID(refs[f"asset:external:{index}"]))
                assert external is not None
                assert external.attachment_id is None
                assert external.fetched_at is None
                assert external.source_url == photo["source_url"]
        supplier = database.get(v5.v4.Supplier, UUID(refs["supplier:0"]))
        profile = database.get(v5.BotanicalProfile, UUID(refs["profile:00"]))
        assert supplier is not None
        assert profile is not None
        supplier.notes = "Review v5 — operator Supplier notes retained"
        profile.description = "Review v5 — operator reference text retained"
        seed.label = "Review v5 — operator edited label retained"
        database.commit()
        second = v5.seed(database, tmp_path, baseline)
        assert second == extension
        assert v5.counts(database) == first_counts
        database.refresh(seed)
        assert seed.label == "Review v5 — operator edited label retained"
        assert owner.password_hash == password_hash
        database.refresh(supplier)
        database.refresh(profile)
        assert supplier.notes == "Review v5 — operator Supplier notes retained"
        assert profile.description == "Review v5 — operator reference text retained"


def test_wrong_environment_refused_before_database(monkeypatch: pytest.MonkeyPatch) -> None:
    for mode in ("", "dev", "uat", "sourcing", "production"):
        monkeypatch.setenv("FLORABASE_WORKFLOW_MODE", mode)
        with pytest.raises(v5.v4.FixtureError, match="Review-only"):
            v5.require_review(None)


def test_failure_rolls_back_and_never_claims_ready(
    database_connection: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FLORABASE_WORKFLOW_MODE", "review")
    isolate_fixture_tables(database_connection)
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        v5.v4.bootstrap_owner(database, "review-owner", "test-only-review-password-v5")
        baseline = v5.v4.seed(database, tmp_path)
        before = v5.counts(database)
        create = v5.create_graph

        def fail(*args: object) -> None:
            create(*args, fail_after=20)

        monkeypatch.setattr(v5, "create_graph", fail)
        with pytest.raises(v5.v4.FixtureError, match="Injected failure"):
            v5.seed(database, tmp_path, baseline)
        manifest = json.loads((tmp_path / v5.LEDGER).read_text())
        assert manifest["state"] == "failed"
        assert "Injected failure" in manifest["diagnostic"]
        assert v5.counts(database) == before
        with pytest.raises(v5.v4.FixtureError, match="incomplete/failed"):
            v5.seed(database, tmp_path, baseline)
        v5.v4.validate_manifest(database, tmp_path, baseline)
