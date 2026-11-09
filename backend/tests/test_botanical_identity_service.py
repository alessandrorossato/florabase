from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid7

import pytest
from sqlalchemy.exc import IntegrityError

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.reconciliation import (
    ReconciliationConflictError,
    ReconciliationNotFoundError,
    _split_gbif_scientific_name,
    correct_accepted_name,
    merge_duplicate_identity,
    record_superseded_identity_name,
)
from florabase.botanical_identities.schemas import (
    AcceptedNameCorrectionWrite,
    BotanicalIdentityCreate,
    BotanicalIdentityUpdate,
    DuplicateIdentityMergeWrite,
    IdentityCollectionCounts,
)
from florabase.botanical_identities.service import (
    BotanicalIdentityConflictError,
    BotanicalIdentityCoverReferencedError,
    BotanicalIdentityMergedError,
    BotanicalIdentityReferencedError,
    create_botanical_identity,
    delete_botanical_identity,
    list_botanical_identity_directory,
    update_botanical_identity,
)
from florabase.botanical_profiles.model import BotanicalProfile


def integrity_error(constraint_name: str) -> IntegrityError:
    original = MagicMock()
    original.diag.constraint_name = constraint_name
    return IntegrityError("insert", {}, original)


def test_unique_race_maps_only_the_botanical_identity_constraint() -> None:
    database = MagicMock()
    existing = BotanicalIdentity(id=uuid7(), scientific_name="Acer palmatum")
    payload = BotanicalIdentityCreate(scientific_name="acer palmatum")
    database.flush.side_effect = integrity_error("uq_botanical_identities_name_cultivar_ci")

    with (
        patch(
            "florabase.botanical_identities.service.find_duplicate",
            side_effect=[None, existing],
        ),
        pytest.raises(BotanicalIdentityConflictError) as caught,
    ):
        create_botanical_identity(database, payload)

    assert caught.value.existing_id == existing.id


def test_unrelated_integrity_error_is_not_misreported_as_a_duplicate() -> None:
    database = MagicMock()
    payload = BotanicalIdentityCreate(scientific_name="Acer palmatum")
    failure = integrity_error("some_other_constraint")
    database.flush.side_effect = failure

    with (
        patch("florabase.botanical_identities.service.find_duplicate", return_value=None),
        pytest.raises(IntegrityError) as caught,
    ):
        create_botanical_identity(database, payload)

    assert caught.value is failure


def test_update_corrects_the_same_identity_and_rejects_a_duplicate() -> None:
    database = MagicMock()
    database.scalar.return_value = None
    now = datetime.now(UTC)
    identity = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Acer palmatum",
        created_at=now,
        updated_at=now,
    )
    payload = BotanicalIdentityUpdate(
        scientific_name="Acer japonicum", common_name="Fullmoon maple"
    )
    with patch("florabase.botanical_identities.service.find_duplicate", return_value=None):
        assert update_botanical_identity(database, identity, payload) is identity
    assert identity.scientific_name == "Acer japonicum"
    assert identity.common_name == "Fullmoon maple"
    database.add.assert_called_once()

    duplicate = BotanicalIdentity(id=uuid7(), scientific_name="Acer japonicum")
    with (
        patch(
            "florabase.botanical_identities.service.find_duplicate",
            return_value=duplicate,
        ),
        pytest.raises(BotanicalIdentityConflictError),
    ):
        update_botanical_identity(database, identity, payload)

    merged = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Acer palmatum",
        merged_into_id=duplicate.id,
        merged_at=now,
        created_at=now,
        updated_at=now,
    )
    with pytest.raises(BotanicalIdentityMergedError):
        update_botanical_identity(database, merged, payload)


def test_delete_allows_unused_identity_and_rejects_collection_references() -> None:
    identity = BotanicalIdentity(id=uuid7(), scientific_name="Acer palmatum")
    database = MagicMock()
    database.scalar.side_effect = [identity.id, 0, None, 0, 0, 0, 0, 0, 0, 0]
    delete_botanical_identity(database, identity)
    database.delete.assert_called_once_with(identity)

    database = MagicMock()
    database.scalar.side_effect = [identity.id, 0, None, 0, 0, 0, 0, 1, 0, 0]
    with pytest.raises(BotanicalIdentityReferencedError):
        delete_botanical_identity(database, identity)
    database.delete.assert_not_called()

    database = MagicMock()
    database.scalar.return_value = 1
    with pytest.raises(BotanicalIdentityCoverReferencedError):
        delete_botanical_identity(database, identity)
    database.delete.assert_not_called()


def test_delete_rejects_retained_native_range_source_applications() -> None:
    identity = BotanicalIdentity(id=uuid7(), scientific_name="Acer palmatum")
    database = MagicMock()
    database.scalar.side_effect = [identity.id, 0, None, 1, 0, 0, 0, 0, 0, 0]
    with pytest.raises(BotanicalIdentityReferencedError):
        delete_botanical_identity(database, identity)
    database.delete.assert_not_called()


def test_directory_uses_one_aggregate_query_and_maps_cover_and_collection_counts() -> None:
    identity = BotanicalIdentity(id=uuid7(), scientific_name="Acer palmatum")
    database = MagicMock()
    database.execute.return_value.all.return_value = [
        (identity, "external", "https://example.test/maple.jpg", 2, 3, 4, 5)
    ]

    result = list_botanical_identity_directory(database)

    assert result == [
        (
            identity,
            "external",
            "https://example.test/maple.jpg",
            IdentityCollectionCounts(seed_lots=2, sowings=3, plants=4, plant_groups=5),
        )
    ]
    database.execute.assert_called_once()
    sql = str(database.execute.call_args.args[0])
    assert "count(" in sql.lower()
    assert "sowings" in sql.lower()
    assert "plant_groups" in sql.lower()


def test_split_gbif_scientific_name_extracts_canonical_and_authorship() -> None:
    assert _split_gbif_scientific_name("   ") == ("", None)
    assert _split_gbif_scientific_name("Solanum") == ("Solanum", None)
    assert _split_gbif_scientific_name("Solanum lycopersicum L.") == (
        "Solanum lycopersicum",
        "L.",
    )
    assert _split_gbif_scientific_name("Acer palmatum") == ("Acer palmatum", None)
    assert _split_gbif_scientific_name("Mentha \u00d7 piperita L.") == (
        "Mentha \u00d7 piperita",
        "L.",
    )
    assert _split_gbif_scientific_name("Acer palmatum subsp. amoenum (Carri\u00e8re) H.Hara") == (
        "Acer palmatum subsp. amoenum",
        "(Carri\u00e8re) H.Hara",
    )


def test_record_superseded_identity_name_distinguishes_initial_and_subsequent_entries() -> None:
    now = datetime.now(UTC)
    identity = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Lycopersicon esculentum",
        created_at=now,
        updated_at=now,
    )
    database = MagicMock()
    database.scalar.return_value = None

    first = record_superseded_identity_name(
        database, identity, now=now, source_provider="wfo", source_version="2025-12"
    )
    assert first.status_kind == "initial_recorded"
    assert first.scientific_name == "Lycopersicon esculentum"

    database.scalar.return_value = first
    identity.scientific_name = "Solanum lycopersicum"
    second = record_superseded_identity_name(
        database, identity, now=now, source_provider="operator"
    )
    assert second.status_kind == "former_accepted"
    assert second.scientific_name == "Solanum lycopersicum"


def test_correct_accepted_name_validates_stale_noop_collision_and_conflict_acknowledgement() -> (
    None
):
    now = datetime.now(UTC)
    identity = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Lycopersicon esculentum",
        created_at=now,
        updated_at=now,
    )
    database = MagicMock()
    database.scalar.return_value = None
    with pytest.raises(ReconciliationNotFoundError):
        correct_accepted_name(
            database,
            identity.id,
            AcceptedNameCorrectionWrite(
                scientific_name="Solanum lycopersicum",
                identity_updated_at=now,
            ),
        )

    database.scalar.return_value = identity
    with pytest.raises(ReconciliationConflictError) as stale_err:
        correct_accepted_name(
            database,
            identity.id,
            AcceptedNameCorrectionWrite(
                scientific_name="Solanum lycopersicum",
                identity_updated_at=datetime(2020, 1, 1, tzinfo=UTC),
            ),
        )
    assert stale_err.value.code == "reconciliation_stale"

    with pytest.raises(ReconciliationConflictError) as noop_err:
        correct_accepted_name(
            database,
            identity.id,
            AcceptedNameCorrectionWrite(
                scientific_name="Lycopersicon esculentum",
                identity_updated_at=now,
            ),
        )
    assert noop_err.value.code == "reconciliation_noop"

    colliding = BotanicalIdentity(id=uuid7(), scientific_name="Solanum lycopersicum")
    with (
        patch(
            "florabase.botanical_identities.reconciliation.find_duplicate",
            return_value=colliding,
        ),
        pytest.raises(ReconciliationConflictError) as dup_err,
    ):
        correct_accepted_name(
            database,
            identity.id,
            AcceptedNameCorrectionWrite(
                scientific_name="Solanum lycopersicum",
                identity_updated_at=now,
            ),
        )
    assert dup_err.value.code == "duplicate_botanical_identity"
    assert dup_err.value.existing_id == colliding.id

    fake_inspection = MagicMock()
    fake_inspection.has_source_conflict = True
    with (
        patch("florabase.botanical_identities.reconciliation.find_duplicate", return_value=None),
        patch(
            "florabase.botanical_identities.reconciliation.inspect_reconciliation",
            return_value=fake_inspection,
        ),
        pytest.raises(ReconciliationConflictError) as unack_err,
    ):
        correct_accepted_name(
            database,
            identity.id,
            AcceptedNameCorrectionWrite(
                scientific_name="Solanum lycopersicum",
                identity_updated_at=now,
                acknowledge_conflict=False,
            ),
        )
    assert unack_err.value.code == "reconciliation_conflict_unacknowledged"


def test_merge_duplicate_identity_refuses_self_merge_and_unresolved_profile_conflict() -> None:
    now = datetime.now(UTC)
    duplicate = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Lycopersicon esculentum",
        created_at=now,
        updated_at=now,
    )
    survivor = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Solanum lycopersicum",
        created_at=now,
        updated_at=now,
    )
    database = MagicMock()

    with pytest.raises(ReconciliationConflictError) as self_err:
        merge_duplicate_identity(
            database,
            duplicate.id,
            DuplicateIdentityMergeWrite(
                survivor_identity_id=duplicate.id,
                duplicate_updated_at=now,
                survivor_updated_at=now,
            ),
        )
    assert self_err.value.code == "reconciliation_invalid"

    dup_profile = BotanicalProfile(
        botanical_identity_id=duplicate.id,
        description="Duplicate description",
    )
    surv_profile = BotanicalProfile(
        botanical_identity_id=survivor.id,
        description="Survivor description",
    )

    def get_side_effect(model: object, key: object) -> object:
        if model is BotanicalIdentity:
            return duplicate if key == duplicate.id else survivor
        if model is BotanicalProfile:
            return dup_profile if key == duplicate.id else surv_profile
        return None

    database.get.side_effect = get_side_effect

    with pytest.raises(ReconciliationConflictError) as prof_err:
        merge_duplicate_identity(
            database,
            duplicate.id,
            DuplicateIdentityMergeWrite(
                survivor_identity_id=survivor.id,
                duplicate_updated_at=now,
                survivor_updated_at=now,
                profile_resolution="fail_on_conflict",
            ),
        )
    assert prof_err.value.code == "botanical_profile_conflict"
    assert prof_err.value.conflicting_fields == ["description"]


def test_inspect_reconciliation_evaluates_wfo_wcvp_gbif_and_conflicts(tmp_path: object) -> None:
    from pathlib import Path

    from florabase.botanical_identities.model import (
        BotanicalIdentityName,
        BotanicalIdentityReconciliation,
    )
    from florabase.botanical_identities.reconciliation import inspect_reconciliation
    from florabase.external_botany.model import ExternalTaxonLink
    from florabase.native_range_enrichment.model import WcvpLink
    from florabase.native_range_enrichment.snapshot import (
        DISTRIBUTION_FIELDS,
        NAMES_FIELDS,
    )
    from florabase.native_range_enrichment.snapshot import (
        build_index as build_wcvp_index,
    )
    from florabase.native_range_enrichment.source import (
        SourceMetadata as WcvpSourceMetadata,
    )
    from florabase.native_range_enrichment.source import (
        WcvpSource,
    )
    from florabase.taxonomy.model import WfoLink
    from florabase.taxonomy.snapshot import build_index as build_wfo_index
    from florabase.taxonomy.source import CODE, ROOT, WfoMetadata, WfoSource

    base_dir = Path(str(tmp_path))
    now = datetime.now(UTC)
    identity = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Lycopersicon esculentum",
        cultivar_name="San Marzano",
        common_name="Plum tomato",
        created_at=now,
        updated_at=now,
    )
    colliding = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Solanum lycopersicum",
        cultivar_name="San Marzano",
        common_name="Tomato",
        created_at=now,
        updated_at=now,
    )

    # WFO snapshot
    wfo_path = base_dir / "wfo.sqlite"
    wfo_meta = WfoMetadata(retrieved_at="2026-10-09T14:48:29Z")
    build_wfo_index(
        wfo_path,
        [
            {"ID": ROOT, "scientificName": "Plantae", "authorship": "", "rank": "kingdom"},
            {
                "ID": "wfo-4000000002",
                "scientificName": "Solanum",
                "authorship": "L.",
                "rank": "genus",
            },
            {
                "ID": "wfo-0001020304",
                "scientificName": "Solanum lycopersicum",
                "authorship": "L.",
                "rank": "species",
            },
            {
                "ID": "wfo-0009999999",
                "scientificName": "Lycopersicon esculentum",
                "authorship": "Mill.",
                "rank": "species",
            },
        ],
        [
            {"ID": ROOT, "nameID": ROOT, "parentID": CODE},
            {"ID": "wfo-4000000002", "nameID": "wfo-4000000002", "parentID": ROOT},
            {"ID": "wfo-0001020304", "nameID": "wfo-0001020304", "parentID": "wfo-4000000002"},
        ],
        [
            {
                "ID": "wfo-0009999999-2026-06",
                "nameID": "wfo-0009999999",
                "taxonID": "wfo-0001020304",
            }
        ],
        wfo_meta,
    )
    wfo_source = WfoSource(wfo_path)

    # WCVP v15 & v16 snapshots
    wcvp_v15_path = base_dir / "wcvp_v15.sqlite"
    build_wcvp_index(
        wcvp_v15_path,
        [
            dict.fromkeys(NAMES_FIELDS, "")
            | {
                "plant_name_id": "10",
                "taxon_name": "Lycopersicon esculentum",
                "taxon_authors": "Mill.",
                "taxon_rank": "Species",
                "taxon_status": "Synonym",
                "accepted_plant_name_id": "20",
            },
            dict.fromkeys(NAMES_FIELDS, "")
            | {
                "plant_name_id": "20",
                "taxon_name": "Solanum lycopersicum",
                "taxon_authors": "L.",
                "taxon_rank": "Species",
                "taxon_status": "Accepted",
                "accepted_plant_name_id": "20",
            },
        ],
        [
            dict.fromkeys(DISTRIBUTION_FIELDS, "")
            | {
                "plant_locality_id": "1",
                "plant_name_id": "20",
                "area_code_l3": "PER",
                "introduced": "0",
                "extinct": "0",
                "location_doubtful": "0",
            }
        ],
        WcvpSourceMetadata.for_release("15", "2026-10-09T00:00:00Z"),
    )
    wcvp_v15 = WcvpSource(wcvp_v15_path, "15")

    wcvp_v16_path = base_dir / "wcvp_v16.sqlite"
    build_wcvp_index(
        wcvp_v16_path,
        [
            dict.fromkeys(NAMES_FIELDS, "")
            | {
                "plant_name_id": "10",
                "taxon_name": "Lycopersicon esculentum",
                "taxon_authors": "Mill.",
                "taxon_rank": "Species",
                "taxon_status": "Synonym",
                "accepted_plant_name_id": "30",
            },
            dict.fromkeys(NAMES_FIELDS, "")
            | {
                "plant_name_id": "30",
                "taxon_name": "Solanum pimpinellifolium",
                "taxon_authors": "L.",
                "taxon_rank": "Species",
                "taxon_status": "Accepted",
                "accepted_plant_name_id": "30",
            },
        ],
        [
            dict.fromkeys(DISTRIBUTION_FIELDS, "")
            | {
                "plant_locality_id": "1",
                "plant_name_id": "30",
                "area_code_l3": "PER",
                "introduced": "0",
                "extinct": "0",
                "location_doubtful": "0",
            }
        ],
        WcvpSourceMetadata.for_release("16", "2026-10-09T00:00:00Z"),
    )
    wcvp_v16 = WcvpSource(wcvp_v16_path, "16")

    former = BotanicalIdentityName(
        id=uuid7(),
        botanical_identity_id=identity.id,
        scientific_name="Solanum esculentum",
        cultivar_name="San Marzano",
        common_name="Plum tomato",
        authorship="Dunal",
        status_kind="initial_recorded",
        source_provider="operator",
        effective_from=now,
        superseded_at=now,
        created_at=now,
    )
    event = BotanicalIdentityReconciliation(
        id=uuid7(),
        identity_id=identity.id,
        kind="accepted_name_correction",
        previous_scientific_name="Solanum esculentum",
        applied_scientific_name="Lycopersicon esculentum",
        source_provider="operator",
        evidence={"format_version": "1"},
        created_at=now,
    )
    gbif_link = ExternalTaxonLink(
        id=uuid7(),
        botanical_identity_id=identity.id,
        provider="gbif",
        external_id="2930137",
        scientific_name="Lycopersicon esculentum Mill.",
        canonical_name="Lycopersicon esculentum",
        authorship="Mill.",
        rank="SPECIES",
        taxonomic_status="SYNONYM",
        accepted_external_id="2930136",
        accepted_name="Solanum lycopersicum L.",
        linked_at=now,
        last_refreshed_at=now,
        last_refresh_attempt_at=now,
    )

    database = MagicMock()

    def get_side_effect(model: object, key: object) -> object:
        if model is BotanicalIdentity and key == identity.id:
            return identity
        if model is WfoLink:
            return None
        if model is WcvpLink:
            return None
        if model is BotanicalProfile:
            return None
        return None

    database.get.side_effect = get_side_effect
    database.scalars.side_effect = [[former], [event]]
    database.scalar.side_effect = lambda stmt: (
        gbif_link if "external_taxon_links" in str(stmt) else 1
    )

    with patch(
        "florabase.botanical_identities.reconciliation.find_duplicate",
        return_value=colliding,
    ):
        result = inspect_reconciliation(
            database,
            identity.id,
            wfo_source=wfo_source,
            wcvp_v15_source=wcvp_v15,
            wcvp_v16_source=wcvp_v16,
        )

    assert result.original_scientific_name == "Solanum esculentum"
    assert len(result.former_names) == 1
    assert len(result.reconciliations) == 1
    assert result.has_source_conflict is True
    assert {c.kind for c in result.conflicts} == {
        "wcvp_version_conflict",
        "cross_source_conflict",
        "duplicate_identity_collision",
    }
    assert {s.source_provider for s in result.suggestions} == {"wfo", "wcvp", "gbif"}

    # Also test linked WFO and fallback stored WCVP link when snapshot files are absent
    wfo_link = WfoLink(
        identity_id=identity.id,
        version=uuid7(),
        external_id="wfo-0009999999",
        evidence={
            "source": {
                "provider": "wfo",
                "version": wfo_meta.version,
                "checksum": wfo_meta.checksum,
                "retrieved_at": wfo_meta.retrieved_at,
            },
            "taxon": {
                "source_taxon_id": "wfo-0009999999",
                "scientific_name": "Lycopersicon esculentum",
                "authorship": "Mill.",
                "rank": "species",
                "taxonomic_status": "synonym",
                "accepted_source_taxon_id": "wfo-0001020304",
                "parent_source_taxon_id": None,
            },
            "classification": [
                {
                    "source_taxon_id": "wfo-0001020304",
                    "scientific_name": "Solanum lycopersicum",
                    "authorship": "L.",
                    "rank": "species",
                    "taxonomic_status": "accepted",
                    "accepted_source_taxon_id": None,
                    "parent_source_taxon_id": "wfo-4000000002",
                }
            ],
            "identity_updated_at": now,
        },
        confirmed_at=now,
    )
    wcvp_link = WcvpLink(
        identity_id=identity.id,
        version=uuid7(),
        external_id="10",
        taxon={
            "external_id": "10",
            "name": "Lycopersicon esculentum",
            "authorship": "Mill.",
            "rank": "Species",
            "status": "Synonym",
            "accepted_id": "20",
            "accepted_name": "Solanum lycopersicum",
            "powo_id": "urn:lsid:ipni.org:names:10",
            "reviewed": "Y",
        },
        source=wcvp_v15.metadata().model_dump(mode="json"),
        identity_snapshot={"scientific_name": "Lycopersicon esculentum"},
    )

    def get_linked_side_effect(model: object, key: object) -> object:
        if model is BotanicalIdentity and key == identity.id:
            return identity
        if model is WfoLink:
            return wfo_link
        if model is WcvpLink:
            return wcvp_link
        return None

    database.get.side_effect = get_linked_side_effect
    database.scalars.side_effect = [[], []]
    database.scalar.side_effect = lambda stmt: None if "external_taxon_links" in str(stmt) else 0

    with patch(
        "florabase.botanical_identities.reconciliation.find_duplicate",
        return_value=None,
    ):
        linked_result = inspect_reconciliation(
            database,
            identity.id,
            wfo_source=wfo_source,
            wcvp_v15_source=None,
            wcvp_v16_source=None,
        )
    assert len(linked_result.suggestions) == 2
    assert {s.source_provider for s in linked_result.suggestions} == {"wfo", "wcvp"}

    database.scalars.side_effect = [[], []]
    with patch(
        "florabase.botanical_identities.reconciliation.find_duplicate",
        return_value=None,
    ):
        linked_with_live_wcvp = inspect_reconciliation(
            database,
            identity.id,
            wfo_source=wfo_source,
            wcvp_v15_source=wcvp_v15,
            wcvp_v16_source=wcvp_v16,
        )
    assert len(linked_with_live_wcvp.suggestions) == 3


def test_correct_accepted_name_and_merge_duplicate_identity_complete_flows() -> None:
    from florabase.botanical_identities.model import BotanicalIdentityName
    from florabase.botanical_identities.schemas import (
        AcceptedNameSuggestionResponse,
        BotanicalIdentityResponse,
        IdentityReconciliationResponse,
    )
    from florabase.collection_photos.model import BotanicalIdentityCoverImage
    from florabase.external_botany.model import ExternalTaxonLink

    now = datetime.now(UTC)
    identity = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Lycopersicon esculentum",
        cultivar_name="San Marzano",
        common_name="Plum tomato",
        created_at=now,
        updated_at=now,
    )
    suggestion = AcceptedNameSuggestionResponse(
        suggestion_id="wfo:2025-12:wfo-0009999999:wfo-0001020304",
        source_provider="wfo",
        source_label="World Flora Online (2025-12)",
        source_version="2025-12",
        source_checksum="checksum-123",
        link_version=uuid7(),
        matched_taxon_id="wfo-0009999999",
        matched_scientific_name="Lycopersicon esculentum",
        matched_authorship="Mill.",
        matched_status="synonym",
        accepted_taxon_id="wfo-0001020304",
        accepted_scientific_name="Solanum lycopersicum",
        accepted_authorship="L.",
        accepted_rank="species",
        stale=False,
    )
    inspection = IdentityReconciliationResponse(
        identity=BotanicalIdentityResponse.from_model(identity),
        original_scientific_name=identity.scientific_name,
        original_cultivar_name=identity.cultivar_name,
        original_common_name=identity.common_name,
        original_display_label="Lycopersicon esculentum \u2018San Marzano\u2019",
        former_names=[],
        suggestions=[suggestion],
        source_assessments=[],
        conflicts=[],
        has_source_conflict=False,
        reconciliations=[],
    )

    database = MagicMock()
    database.scalar.side_effect = [identity, None]

    with (
        patch("florabase.botanical_identities.reconciliation.find_duplicate", return_value=None),
        patch(
            "florabase.botanical_identities.reconciliation.inspect_reconciliation",
            return_value=inspection,
        ),
    ):
        res = correct_accepted_name(
            database,
            identity.id,
            AcceptedNameCorrectionWrite(
                scientific_name="Solanum lycopersicum",
                cultivar_name="San Marzano",
                common_name="Plum tomato",
                source_provider="wfo",
                source_version="2025-12",
                source_checksum="checksum-123",
                link_version=suggestion.link_version,
                matched_taxon_id="wfo-0009999999",
                accepted_taxon_id="wfo-0001020304",
                accepted_authorship="L.",
                acknowledge_conflict=False,
                notes="WFO accepted name",
                identity_updated_at=now,
            ),
            actor_user_id=uuid7(),
        )
    assert res is inspection
    assert identity.scientific_name == "Solanum lycopersicum"

    # Now test full merge_duplicate_identity execution
    duplicate = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Lycopersicon esculentum",
        created_at=now,
        updated_at=now,
    )
    survivor = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Solanum lycopersicum",
        created_at=now,
        updated_at=now,
    )
    dup_profile = BotanicalProfile(
        botanical_identity_id=duplicate.id,
        description="Adopted description",
    )
    place_1 = uuid7()
    place_2 = uuid7()
    lot_id = uuid7()
    plant_id = uuid7()
    group_id = uuid7()
    act_id = uuid7()
    dup_cover = BotanicalIdentityCoverImage(
        id=uuid7(),
        botanical_identity_id=duplicate.id,
        media_asset_id=uuid7(),
        source_mode="external",
    )
    ext_link = ExternalTaxonLink(
        id=uuid7(),
        botanical_identity_id=duplicate.id,
        provider="gbif",
        external_id="123",
        scientific_name="Lycopersicon esculentum",
        linked_at=now,
        last_refreshed_at=now,
        last_refresh_attempt_at=now,
    )
    dup_former = BotanicalIdentityName(
        id=uuid7(),
        botanical_identity_id=duplicate.id,
        scientific_name="Solanum esculentum",
        status_kind="initial_recorded",
        source_provider="operator",
        effective_from=now,
        superseded_at=now,
        created_at=now,
    )

    merge_db = MagicMock()

    def get_merge_side_effect(model: object, key: object) -> object:
        if model is BotanicalIdentity:
            return duplicate if key == duplicate.id else survivor
        if model is BotanicalProfile:
            return dup_profile if key == duplicate.id else None
        return None

    merge_db.get.side_effect = get_merge_side_effect
    merge_db.scalar.side_effect = [duplicate, survivor, None, dup_cover]
    merge_db.scalars.side_effect = [
        [place_1, place_2],  # dup_place_ids
        [place_1],  # surv_place_ids
        [lot_id],  # seed_lot_ids
        [plant_id],  # plant_ids
        [group_id],  # plant_group_ids
        [act_id],  # scheduled_activity_ids
        [],  # surv_ext_providers
        [ext_link],  # duplicate external links
        [dup_former],  # dup_former_names
    ]

    with patch(
        "florabase.botanical_identities.reconciliation.inspect_reconciliation",
        return_value=inspection,
    ):
        merge_res = merge_duplicate_identity(
            merge_db,
            duplicate.id,
            DuplicateIdentityMergeWrite(
                survivor_identity_id=survivor.id,
                duplicate_updated_at=now,
                survivor_updated_at=now,
                profile_resolution="keep_survivor",
                notes="Merged duplicate",
            ),
            actor_user_id=uuid7(),
        )
    assert merge_res is inspection
    assert duplicate.merged_into_id == survivor.id
    assert duplicate.merged_at is not None
    assert dup_cover.botanical_identity_id == survivor.id
    assert ext_link.botanical_identity_id == survivor.id


def test_reconciliation_edge_cases_and_stale_guards() -> None:
    from florabase.botanical_identities.reconciliation import inspect_reconciliation
    from florabase.botanical_identities.schemas import (
        AcceptedNameSuggestionResponse,
        BotanicalIdentityResponse,
        IdentityReconciliationResponse,
    )
    from florabase.native_range_enrichment.model import WcvpLink
    from florabase.taxonomy.model import WfoLink

    now = datetime.now(UTC)
    identity = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Lycopersicon esculentum",
        created_at=now,
        updated_at=now,
    )

    # 1. inspect_reconciliation not found
    missing_db = MagicMock()
    missing_db.get.return_value = None
    with pytest.raises(ReconciliationNotFoundError):
        inspect_reconciliation(missing_db, identity.id)

    # 2. inspect_reconciliation with invalid WfoLink evidence and invalid WcvpLink taxon
    bad_wfo = WfoLink(
        identity_id=identity.id,
        version=uuid7(),
        external_id="wfo-0009999999",
        evidence={"invalid": True},
        confirmed_at=now,
    )
    bad_wcvp = WcvpLink(
        identity_id=identity.id,
        version=uuid7(),
        external_id="10",
        taxon={"invalid": True},
        source={"invalid": True},
        identity_snapshot={},
    )
    bad_db = MagicMock()
    bad_db.get.side_effect = lambda model, _key: (
        identity
        if model is BotanicalIdentity
        else bad_wfo
        if model is WfoLink
        else bad_wcvp
        if model is WcvpLink
        else None
    )
    bad_db.scalars.side_effect = [[], []]
    bad_db.scalar.side_effect = lambda stmt: None if "external_taxon_links" in str(stmt) else 0
    bad_res = inspect_reconciliation(bad_db, identity.id)
    assert len(bad_res.source_assessments) == 1
    assert bad_res.source_assessments[0].stale is True

    # 3. correct_accepted_name guards: merged, missing/stale suggestion, checksum, link_version
    merged_identity = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Lycopersicon esculentum",
        merged_into_id=uuid7(),
        merged_at=now,
        created_at=now,
        updated_at=now,
    )
    db = MagicMock()
    db.scalar.return_value = merged_identity
    with pytest.raises(ReconciliationConflictError) as merged_err:
        correct_accepted_name(
            db,
            merged_identity.id,
            AcceptedNameCorrectionWrite(
                scientific_name="Solanum lycopersicum",
                identity_updated_at=now,
            ),
        )
    assert merged_err.value.code == "botanical_identity_merged"

    db.scalar.return_value = identity
    base_suggestion = AcceptedNameSuggestionResponse(
        suggestion_id="wfo:2026-06:wfo-0009999999:wfo-0001020304",
        source_provider="wfo",
        source_label="WFO",
        source_version="2026-06",
        source_checksum="chk-1",
        link_version=uuid7(),
        matched_taxon_id="wfo-0009999999",
        matched_scientific_name="Lycopersicon esculentum",
        matched_status="synonym",
        accepted_taxon_id="wfo-0001020304",
        accepted_scientific_name="Solanum lycopersicum",
        stale=False,
    )
    empty_inspection = IdentityReconciliationResponse(
        identity=BotanicalIdentityResponse.from_model(identity),
        original_scientific_name=identity.scientific_name,
        original_cultivar_name=None,
        original_common_name=None,
        original_display_label=identity.scientific_name,
        former_names=[],
        suggestions=[],
        source_assessments=[],
        conflicts=[],
        has_source_conflict=False,
        reconciliations=[],
    )

    with (
        patch("florabase.botanical_identities.reconciliation.find_duplicate", return_value=None),
        patch(
            "florabase.botanical_identities.reconciliation.inspect_reconciliation",
            return_value=empty_inspection,
        ),
        pytest.raises(ReconciliationConflictError) as no_cand_err,
    ):
        correct_accepted_name(
            db,
            identity.id,
            AcceptedNameCorrectionWrite(
                scientific_name="Solanum lycopersicum",
                source_provider="wfo",
                identity_updated_at=now,
            ),
        )
    assert no_cand_err.value.code == "reconciliation_stale"

    stale_inspection = empty_inspection.model_copy(
        update={"suggestions": [base_suggestion.model_copy(update={"stale": True})]}
    )
    with (
        patch("florabase.botanical_identities.reconciliation.find_duplicate", return_value=None),
        patch(
            "florabase.botanical_identities.reconciliation.inspect_reconciliation",
            return_value=stale_inspection,
        ),
        pytest.raises(ReconciliationConflictError) as stale_sugg_err,
    ):
        correct_accepted_name(
            db,
            identity.id,
            AcceptedNameCorrectionWrite(
                scientific_name="Solanum lycopersicum",
                source_provider="wfo",
                identity_updated_at=now,
            ),
        )
    assert stale_sugg_err.value.code == "reconciliation_stale"

    valid_inspection = empty_inspection.model_copy(update={"suggestions": [base_suggestion]})
    with (
        patch("florabase.botanical_identities.reconciliation.find_duplicate", return_value=None),
        patch(
            "florabase.botanical_identities.reconciliation.inspect_reconciliation",
            return_value=valid_inspection,
        ),
        pytest.raises(ReconciliationConflictError) as chk_err,
    ):
        correct_accepted_name(
            db,
            identity.id,
            AcceptedNameCorrectionWrite(
                scientific_name="Solanum lycopersicum",
                source_provider="wfo",
                source_checksum="wrong-chk",
                link_version=base_suggestion.link_version,
                identity_updated_at=now,
            ),
        )
    assert chk_err.value.code == "reconciliation_stale"

    with (
        patch("florabase.botanical_identities.reconciliation.find_duplicate", return_value=None),
        patch(
            "florabase.botanical_identities.reconciliation.inspect_reconciliation",
            return_value=valid_inspection,
        ),
        pytest.raises(ReconciliationConflictError) as lv_err,
    ):
        correct_accepted_name(
            db,
            identity.id,
            AcceptedNameCorrectionWrite(
                scientific_name="Solanum lycopersicum",
                source_provider="wfo",
                source_checksum="chk-1",
                link_version=uuid7(),
                identity_updated_at=now,
            ),
        )
    assert lv_err.value.code == "reconciliation_stale"

    # IntegrityError unique race during correct_accepted_name
    race_db = MagicMock()
    race_db.scalar.side_effect = [identity, None]
    race_db.flush.side_effect = integrity_error("uq_botanical_identities_name_cultivar_ci")
    with (
        patch(
            "florabase.botanical_identities.reconciliation.find_duplicate",
            side_effect=[None, merged_identity],
        ),
        patch(
            "florabase.botanical_identities.reconciliation.inspect_reconciliation",
            return_value=empty_inspection,
        ),
        pytest.raises(ReconciliationConflictError) as race_err,
    ):
        correct_accepted_name(
            race_db,
            identity.id,
            AcceptedNameCorrectionWrite(
                scientific_name="Solanum lycopersicum",
                source_provider="operator",
                identity_updated_at=now,
            ),
        )
    assert race_err.value.code == "duplicate_botanical_identity"

    # 4. merge_duplicate_identity guards: missing, merged duplicate, merged survivor, stale
    m_db = MagicMock()
    m_db.get.return_value = None
    with pytest.raises(ReconciliationNotFoundError):
        merge_duplicate_identity(
            m_db,
            identity.id,
            DuplicateIdentityMergeWrite(
                survivor_identity_id=uuid7(),
                duplicate_updated_at=now,
                survivor_updated_at=now,
            ),
        )

    survivor = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Solanum lycopersicum",
        created_at=now,
        updated_at=now,
    )
    m_db.get.side_effect = lambda _m, key: (
        merged_identity if key == merged_identity.id else survivor
    )
    with pytest.raises(ReconciliationConflictError) as md_err:
        merge_duplicate_identity(
            m_db,
            merged_identity.id,
            DuplicateIdentityMergeWrite(
                survivor_identity_id=survivor.id,
                duplicate_updated_at=now,
                survivor_updated_at=now,
            ),
        )
    assert md_err.value.code == "botanical_identity_merged"

    m_db.get.side_effect = lambda _m, key: identity if key == identity.id else merged_identity
    with pytest.raises(ReconciliationConflictError) as ms_err:
        merge_duplicate_identity(
            m_db,
            identity.id,
            DuplicateIdentityMergeWrite(
                survivor_identity_id=merged_identity.id,
                duplicate_updated_at=now,
                survivor_updated_at=now,
            ),
        )
    assert ms_err.value.code == "botanical_identity_merged"

    m_db.get.side_effect = lambda _m, key: identity if key == identity.id else survivor
    with pytest.raises(ReconciliationConflictError) as m_stale_err:
        merge_duplicate_identity(
            m_db,
            identity.id,
            DuplicateIdentityMergeWrite(
                survivor_identity_id=survivor.id,
                duplicate_updated_at=datetime(2020, 1, 1, tzinfo=UTC),
                survivor_updated_at=now,
            ),
        )
    assert m_stale_err.value.code == "reconciliation_stale"

    # 5. service.py helper functions find_duplicate, get_botanical_identity, list_identities
    from florabase.botanical_identities.service import (
        find_duplicate,
        get_botanical_identity,
        list_botanical_identities,
    )

    s_db = MagicMock()
    s_db.scalars.return_value.one_or_none.return_value = identity
    assert find_duplicate(s_db, "Lycopersicon esculentum", None) is identity
    assert find_duplicate(s_db, "Lycopersicon esculentum", "San Marzano") is identity
    s_db.get.return_value = identity
    assert get_botanical_identity(s_db, identity.id) is identity
    s_db.scalars.return_value = [identity]
    assert list_botanical_identities(s_db) == [identity]
