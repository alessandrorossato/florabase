import json
import sqlite3
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from typing import cast
from uuid import uuid7

import pytest
from sqlalchemy import Connection, Engine, select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.service import (
    BotanicalIdentityReferencedError,
    delete_botanical_identity,
)
from florabase.botanical_profiles.model import BotanicalProfile, BotanicalProfileNativeRange
from florabase.botanical_profiles.service import (
    add_botanical_native_range,
    remove_botanical_native_range,
)
from florabase.geographic_places.model import GeographicPlace
from florabase.native_range_enrichment.model import (
    NativeRangeApplication,
    NativeRangeProposal,
    WcvpLink,
)
from florabase.native_range_enrichment.schemas import (
    ApplyWrite,
    ProposalResponse,
    RangeChoice,
    SourceAssertion,
)
from florabase.native_range_enrichment.service import (
    EnrichmentConflictError,
    WithdrawnRangeMappingError,
    apply,
    confirm_link,
    current_ids,
    inspect_proposal,
    propose,
    range_version,
)
from florabase.native_range_enrichment.snapshot import (
    DISTRIBUTION_FIELDS,
    NAMES_FIELDS,
    build_index,
)
from florabase.native_range_enrichment.source import (
    ARCHIVE_SHA256,
    DEFAULT_VERSION,
    RELEASES,
    SourceMetadata,
    SourceUnavailableError,
    WcvpSource,
    WcvpVersion,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def source(tmp_path: Path, request: pytest.FixtureRequest) -> WcvpSource:
    path = tmp_path / "wcvp.sqlite"
    names = [
        dict.fromkeys(NAMES_FIELDS, "")
        | {
            "plant_name_id": "100",
            "taxon_name": "Fixture species",
            "taxon_authors": "A.Author",
            "taxon_rank": "Species",
            "taxon_status": "Accepted",
            "accepted_plant_name_id": "100",
        }
    ]
    rows = [
        dict.fromkeys(DISTRIBUTION_FIELDS, "")
        | {
            "plant_locality_id": str(i),
            "plant_name_id": "100",
            "area_code_l3": code,
            "introduced": introduced,
            "extinct": extinct,
            "location_doubtful": doubtful,
        }
        for i, (code, introduced, extinct, doubtful) in enumerate(
            [
                ("BOL", "0", "0", "0"),
                ("PER", "0", "0", "0"),
                ("ITA", "0", "0", "0"),
                ("CZE", "0", "0", "0"),
                ("BUL", "1", "0", "0"),
                ("HUN", "0", "1", "0"),
                ("THA", "0", "0", "1"),
                ("UNKNOWN", "0", "0", "0"),
            ]
        )
    ]
    version = cast(WcvpVersion, getattr(request, "param", DEFAULT_VERSION))
    build_index(path, names, rows, SourceMetadata.for_release(version, "2026-10-09T00:00:00Z"))
    return WcvpSource(path, version)


@pytest.fixture
def database(database_connection: Connection) -> Iterator[Session]:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as session:
        yield session


@pytest.fixture
def identity(database: Session) -> BotanicalIdentity:
    identity = BotanicalIdentity(scientific_name="Synthetic enrichment test")
    database.add(identity)
    database.flush()
    return identity


def place(database: Session, code: str) -> GeographicPlace:
    return database.scalars(
        select(GeographicPlace).where(GeographicPlace.source_code == code)
    ).one()


def linked(database: Session, identity: BotanicalIdentity, source: WcvpSource) -> None:
    confirm_link(database, identity.id, "100", source.metadata().checksum, source)


@pytest.mark.parametrize("source", ["15", "16"], indirect=True)
@pytest.mark.parametrize("already_recorded", [False, True])
def test_v1_cos_evidence_is_frozen_but_only_safe_choices_can_apply(
    database: Session, identity: BotanicalIdentity, source: WcvpSource, already_recorded: bool
) -> None:
    costa_rica = place(database, "CR")
    bolivia = place(database, "BO")
    albania = place(database, "AL")
    if already_recorded:
        add_botanical_native_range(database, identity.id, costa_rica.id)
    linked(database, identity, source)
    assert source.path is not None
    row = source.distribution("100")[0]
    with sqlite3.connect(source.path) as index:
        for code in ("COS", "ALB", "BLT", "FIN"):
            payload = row | {
                "area_code_l3": code,
                "plant_locality_id": code,
            }
            index.execute(
                "INSERT INTO distributions VALUES (?, ?, ?)", (code, "100", json.dumps(payload))
            )
    fresh = propose(database, identity.id, source)
    assert fresh.crosswalk_version == f"wcvp{source.release.version}-wgsrpd2-cldr48.2.1-v2"
    link = database.get(WcvpLink, identity.id)
    assert link is not None
    assert fresh.link_version == link.version
    mappings = {a.original["area_code_l3"]: a.mapping for a in fresh.assertions}
    assert (mappings["COS"], mappings["FIN"], mappings["BLT"]) == (
        "partial",
        "unsupported_split",
        "unsupported_split",
    )
    assert next(c for c in fresh.choices if c.code == "AL").change == "ADD"
    assert [c.change for c in fresh.choices if c.code == "CR"] == (
        ["CURRENT-ONLY"] if already_recorded else []
    )

    # Reproduce the old stored shape without calling the current classifier for v1.
    evidence = fresh.model_copy(deep=True)
    evidence.crosswalk_version = f"wcvp{source.release.version}-wgsrpd2-cldr48.2.1-v1"
    cos = next(a for a in evidence.assertions if a.assertion_id == "COS")
    evidence.assertions = [
        SourceAssertion(
            assertion_id="COS",
            original=cos.original,
            status="native",
            mapping="equivalent",
            note="Reviewed level-3 / ISO equivalence.",
            place_ids=[costa_rica.id],
        ),
        *[
            a
            for a in evidence.assertions
            if a.original["area_code_l3"] not in {"COS", "ALB", "FIN", "BLT"}
        ],
    ]
    evidence.choices = [
        c for c in evidence.choices if c.place_id not in {costa_rica.id, albania.id}
    ] + [
        RangeChoice(
            place_id=costa_rica.id,
            name=costa_rica.name,
            path=costa_rica.name,
            code="CR",
            change="KEEP" if already_recorded else "ADD",
            assertions=["COS"],
        )
    ]
    frozen = evidence.model_dump(
        mode="json", exclude={"id", "created_at", "applied_at", "application"}
    )
    legacy = NativeRangeProposal(identity_id=identity.id, evidence=frozen)
    database.add(legacy)
    database.flush()
    if already_recorded:
        previous = NativeRangeProposal(
            identity_id=identity.id,
            evidence=frozen
            | {
                "current_ids": [],
                "destination_version": fresh.destination_version - 1,
                "choices": [
                    c | {"change": "ADD"} if c["code"] == "CR" else c for c in frozen["choices"]
                ],
            },
        )
        database.add(previous)
        database.flush()
        previous_proposal = inspect_proposal(database, identity.id, previous.id)
        receipt = {
            "format_version": 1,
            "proposal": previous_proposal.model_dump(mode="json"),
            "selected_place_ids": [str(costa_rica.id)],
            "added": [str(costa_rica.id)],
            "kept": [],
            "removed": [],
            "destination_version_after": fresh.destination_version,
        }
        database.add(
            NativeRangeApplication(
                proposal_id=previous.id, identity_id=identity.id, evidence=receipt
            )
        )
        database.flush()

    source.path.unlink()
    assert (
        inspect_proposal(database, identity.id, legacy.id).assertions[0].note
        == "Reviewed level-3 / ISO equivalence."
    )
    current = current_ids(database, identity.id)
    for selection in ([costa_rica.id], [costa_rica.id, bolivia.id]):
        with pytest.raises(WithdrawnRangeMappingError, match="Deselect Costa Rica"):
            apply(database, identity.id, legacy.id, ApplyWrite(selected_place_ids=selection))
        assert current_ids(database, identity.id) == current
        assert range_version(database, identity.id) == fresh.destination_version
        assert database.get(NativeRangeApplication, legacy.id) is None

    result = apply(database, identity.id, legacy.id, ApplyWrite(selected_place_ids=[bolivia.id]))
    assert result.added == [bolivia.id]
    assert result.kept == current
    database.refresh(legacy)
    assert legacy.evidence == frozen
    if already_recorded:
        historical = database.get(NativeRangeApplication, previous.id, populate_existing=True)
        assert historical is not None
        assert historical.evidence == receipt
        assert inspect_proposal(database, identity.id, previous.id).applied_at is not None


def test_compare_selective_apply_preserves_manual_and_qualifiers_and_receipt(
    database: Session, identity: BotanicalIdentity, source: WcvpSource
) -> None:
    manual = place(database, "IT")
    bolivia = place(database, "BO")
    add_botanical_native_range(database, identity.id, manual.id)
    add_botanical_native_range(database, identity.id, bolivia.id)
    linked(database, identity, source)
    proposal = propose(database, identity.id, source)
    assert {p.code: p.change for p in proposal.choices} == {
        "IT": "CURRENT-ONLY",
        "BO": "KEEP",
        "PE": "ADD",
    }
    assert len(proposal.assertions) == 8
    assert [a.mapping for a in proposal.assertions[2:4]] == ["partial", "unsupported_split"]
    assert [a.status for a in proposal.assertions[4:7]] == ["introduced", "qualified", "qualified"]
    assert all(not a.place_ids for a in proposal.assertions[2:])
    result = apply(
        database,
        identity.id,
        proposal.id,
        ApplyWrite(selected_place_ids=[place(database, "PE").id]),
    )
    assert result.added == [place(database, "PE").id]
    assert set(result.kept) == {manual.id, bolivia.id}
    receipt = database.get(NativeRangeApplication, proposal.id)
    assert receipt is not None
    retained = ProposalResponse.model_validate(receipt.evidence["proposal"])
    assert retained.source.version == DEFAULT_VERSION
    assert retained.source.checksum == RELEASES[DEFAULT_VERSION].checksum
    assert retained.assertions[0].original["area_code_l3"] == "BOL"
    assert receipt.evidence["removed"] == []
    assert inspect_proposal(database, identity.id, proposal.id).applied_at is not None
    with pytest.raises(EnrichmentConflictError):
        apply(database, identity.id, proposal.id, ApplyWrite(selected_place_ids=[bolivia.id]))
    assert (
        len(
            list(
                database.scalars(
                    select(BotanicalProfileNativeRange).where(
                        BotanicalProfileNativeRange.botanical_profile_id == identity.id
                    )
                )
            )
        )
        == 3
    )


@pytest.mark.parametrize(
    "change",
    ["range", "roundtrip", "identity", "link", "source", "crosswalk", "wrong-release", "forged"],
)
@pytest.mark.parametrize("source", ["15", "16"], indirect=True)
def test_stale_apply_is_atomic(
    database: Session, identity: BotanicalIdentity, source: WcvpSource, change: str
) -> None:
    linked(database, identity, source)
    proposal = propose(database, identity.id, source)
    if change in {"range", "roundtrip"}:
        manual = place(database, "IT")
        add_botanical_native_range(database, identity.id, manual.id)
        if change == "roundtrip":
            remove_botanical_native_range(database, identity.id, manual.id)
    elif change == "identity":
        identity.scientific_name = "Changed identity"
        database.flush()
    elif change == "link":
        linked(database, identity, source)
    else:
        # To model an older frozen source/crosswalk, insert another immutable proposal.
        evidence = proposal.model_dump(
            mode="json", exclude={"id", "created_at", "applied_at", "application"}
        )
        if change == "source":
            evidence["source"]["version"] = "16" if source.release.version == "15" else "15"
        elif change == "wrong-release":
            other = "16" if source.release.version == "15" else "15"
            evidence["crosswalk_version"] = f"wcvp{other}-wgsrpd2-cldr48.2.1-v1"
        elif change == "forged":
            evidence["crosswalk_version"] = f"wcvp{source.release.version}-wgsrpd2-cldr48.2.1-v1"
            evidence["assertions"][0]["original"]["area_code_l3"] = "ALB"
        else:
            evidence["crosswalk_version"] = "another-crosswalk"
        old = NativeRangeProposal(identity_id=identity.id, evidence=evidence)
        database.add(old)
        database.flush()
        proposal = inspect_proposal(database, identity.id, old.id)
    before = range_version(database, identity.id)
    with pytest.raises(EnrichmentConflictError):
        apply(
            database,
            identity.id,
            proposal.id,
            ApplyWrite(selected_place_ids=[place(database, "BO").id, place(database, "PE").id]),
        )
    assert range_version(database, identity.id) == before
    assert database.get(NativeRangeApplication, proposal.id) is None
    assert (
        database.get(BotanicalProfileNativeRange, (identity.id, place(database, "BO").id)) is None
    )


def test_frozen_proposal_works_without_cache_and_retrieval_failure_preserves_data(
    database: Session, identity: BotanicalIdentity, source: WcvpSource
) -> None:
    linked(database, identity, source)
    proposal = propose(database, identity.id, source)
    assert database.get(BotanicalProfile, identity.id) is None
    assert source.path is not None
    source.path.unlink()
    with pytest.raises(SourceUnavailableError):
        propose(database, identity.id, source)
    result = apply(
        database,
        identity.id,
        proposal.id,
        ApplyWrite(selected_place_ids=[place(database, "BO").id]),
    )
    assert len(result.added) == 1
    assert database.get(BotanicalProfile, identity.id) is not None
    with pytest.raises(BotanicalIdentityReferencedError):
        delete_botanical_identity(database, identity)


def test_unmapped_and_introduced_cannot_apply(
    database: Session, identity: BotanicalIdentity, source: WcvpSource
) -> None:
    linked(database, identity, source)
    proposal = propose(database, identity.id, source)
    with pytest.raises(EnrichmentConflictError):
        apply(
            database,
            identity.id,
            proposal.id,
            ApplyWrite(selected_place_ids=[place(database, "BG").id]),
        )
    assert database.get(BotanicalProfile, identity.id) is None


@pytest.mark.parametrize("source", ["15", "16"], indirect=True)
def test_proposal_and_application_evidence_are_immutable(
    database: Session, identity: BotanicalIdentity, source: WcvpSource
) -> None:
    linked(database, identity, source)
    proposal = propose(database, identity.id, source)
    apply(
        database,
        identity.id,
        proposal.id,
        ApplyWrite(selected_place_ids=[place(database, "BO").id]),
    )
    for sql in [
        "UPDATE native_range_proposals SET evidence='{}' WHERE id=:id",
        "UPDATE native_range_applications SET evidence='{}' WHERE proposal_id=:id",
        "DELETE FROM native_range_applications WHERE proposal_id=:id",
    ]:
        with pytest.raises(ProgrammingError), database.begin_nested():
            database.execute(text(sql), {"id": proposal.id})
    with pytest.raises(IntegrityError), database.begin_nested():
        database.execute(
            text("DELETE FROM native_range_proposals WHERE id=:id"), {"id": proposal.id}
        )


@pytest.mark.parametrize("source", ["15", "16"], indirect=True)
def test_concurrent_apply_commits_one_application(
    database_engine: Engine, source: WcvpSource
) -> None:
    identity_id = uuid7()
    with Session(database_engine) as database:
        identity = BotanicalIdentity(
            id=identity_id, scientific_name=f"Concurrent enrichment {identity_id}"
        )
        database.add(identity)
        database.flush()
        linked(database, identity, source)
        proposal = propose(database, identity_id, source)
        selected = [place(database, "BO").id, place(database, "PE").id]
        database.commit()
    barrier = Barrier(2)

    def worker() -> str:
        with Session(database_engine) as database:
            barrier.wait()
            try:
                apply(database, identity_id, proposal.id, ApplyWrite(selected_place_ids=selected))
                database.commit()
                return "applied"
            except EnrichmentConflictError:
                database.rollback()
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(lambda _: worker(), range(2))) == ["applied", "conflict"]
    with Session(database_engine) as database:
        assert (
            len(
                list(
                    database.scalars(
                        select(NativeRangeApplication).where(
                            NativeRangeApplication.identity_id == identity_id
                        )
                    )
                )
            )
            == 1
        )
        assert (
            len(
                list(
                    database.scalars(
                        select(BotanicalProfileNativeRange).where(
                            BotanicalProfileNativeRange.botanical_profile_id == identity_id
                        )
                    )
                )
            )
            == 2
        )
    # Discard only this proven fixture receipt in the disposable integration database.
    # TRUNCATE bypasses row-delete guards; it is never an application/runtime cleanup path.
    with database_engine.begin() as connection:
        assert list(
            connection.execute(text("SELECT identity_id FROM native_range_applications"))
        ) == [(identity_id,)]
        connection.execute(text("TRUNCATE native_range_applications"))
        connection.execute(
            text("DELETE FROM botanical_identities WHERE id=:id"), {"id": identity_id}
        )


@pytest.mark.parametrize("case", ["empty", "introduced_only", "exact", "source_subset"])
def test_empty_context_only_and_keep_only_proposals(
    database: Session, identity: BotanicalIdentity, source: WcvpSource, case: str
) -> None:
    assert source.path is not None
    with sqlite3.connect(source.path) as connection:
        if case == "empty":
            connection.execute("DELETE FROM distributions")
        elif case == "introduced_only":
            connection.execute("DELETE FROM distributions WHERE locality_id <> '4'")
        else:
            connection.execute("DELETE FROM distributions WHERE locality_id NOT IN ('0','1')")
    if case in {"exact", "source_subset"}:
        for code in ["BO", "PE"] if case == "exact" else ["BO", "PE", "IT"]:
            add_botanical_native_range(database, identity.id, place(database, code).id)
    linked(database, identity, source)
    proposal = propose(database, identity.id, source)
    if case in {"empty", "introduced_only"}:
        assert proposal.choices == []
        assert database.get(BotanicalProfile, identity.id) is None
        assert len(proposal.assertions) == (0 if case == "empty" else 1)
        if case == "introduced_only":
            assert proposal.assertions[0].status == "introduced"
    else:
        assert {c.change for c in proposal.choices} == (
            {"KEEP"} if case == "exact" else {"KEEP", "CURRENT-ONLY"}
        )
        revision = range_version(database, identity.id)
        result = apply(
            database,
            identity.id,
            proposal.id,
            ApplyWrite(selected_place_ids=[place(database, "BO").id]),
        )
        assert result.added == []
        assert len(result.kept) == (2 if case == "exact" else 3)
        assert result.destination_version == revision
        assert inspect_proposal(database, identity.id, proposal.id).application == result


@pytest.mark.parametrize("source", ["15", "16"], indirect=True)
def test_apply_and_identity_deletion_serialize_without_losing_evidence(
    database_engine: Engine, source: WcvpSource
) -> None:
    from florabase.native_range_enrichment.service import EnrichmentNotFoundError

    identity_id = uuid7()
    with Session(database_engine) as database:
        identity = BotanicalIdentity(id=identity_id, scientific_name=f"Deletion race {identity_id}")
        database.add(identity)
        database.flush()
        linked(database, identity, source)
        proposal = propose(database, identity_id, source)
        selected = [place(database, "BO").id]
        database.commit()
    barrier = Barrier(2)

    def worker(action: str) -> str:
        with Session(database_engine) as database:
            barrier.wait()
            try:
                if action == "apply":
                    apply(
                        database, identity_id, proposal.id, ApplyWrite(selected_place_ids=selected)
                    )
                    database.commit()
                    return "applied"
                identity = database.get(BotanicalIdentity, identity_id)
                if identity is not None:
                    delete_botanical_identity(database, identity)
                database.commit()
                return "deleted"
            except BotanicalIdentityReferencedError:
                database.rollback()
                return "referenced"
            except EnrichmentNotFoundError:
                database.rollback()
                return "missing"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = set(executor.map(worker, ["apply", "delete"]))
    assert outcomes in ({"applied", "referenced"}, {"missing", "deleted"})
    with Session(database_engine) as database:
        applications = list(database.scalars(select(NativeRangeApplication)))
        if "applied" in outcomes:
            assert len(applications) == 1
            assert applications[0].identity_id == identity_id
            assert database.get(BotanicalIdentity, identity_id) is not None
            # Only this committed disposable concurrency fixture exists here.
            database.execute(text("TRUNCATE native_range_applications"))
            database.execute(
                text("DELETE FROM botanical_identities WHERE id=:id"), {"id": identity_id}
            )
            database.commit()
        else:
            assert applications == []
            assert database.get(BotanicalIdentity, identity_id) is None


@pytest.mark.parametrize("source", ["15"], indirect=True)
def test_dual_version_frozen_apply_and_explicit_reconfirmation(
    database: Session, identity: BotanicalIdentity, source: WcvpSource, tmp_path: Path
) -> None:
    from florabase.native_range_enrichment.source import RELEASES

    metadata16 = SourceMetadata.for_release("16", "2026-10-28T20:31:34Z")
    path16 = tmp_path / "v16.sqlite"
    rows = [
        dict.fromkeys(DISTRIBUTION_FIELDS, "")
        | {
            "plant_locality_id": "16-1",
            "plant_name_id": "100",
            "area_code_l3": "PER",
            "introduced": "0",
            "extinct": "0",
            "location_doubtful": "0",
        }
    ]
    names = [
        dict.fromkeys(NAMES_FIELDS, "")
        | {
            "plant_name_id": "100",
            "taxon_name": "Fixture species",
            "taxon_authors": "A.Author",
            "taxon_rank": "Species",
            "taxon_status": "Accepted",
            "accepted_plant_name_id": "100",
        }
    ]
    build_index(path16, names, rows, metadata16)
    v16 = WcvpSource(path16, "16")
    manual = place(database, "IT")
    add_botanical_native_range(database, identity.id, manual.id)
    linked(database, identity, source)
    old = propose(database, identity.id, source)
    assert source.path is not None
    source.path.unlink()  # Both a v16 index and missing optional v15 must not affect frozen Apply.
    bolivia = place(database, "BO")
    applied = apply(database, identity.id, old.id, ApplyWrite(selected_place_ids=[bolivia.id]))
    assert manual.id in applied.kept
    historical = database.get(NativeRangeApplication, old.id)
    assert historical is not None
    receipt = dict(historical.evidence)
    assert ProposalResponse.model_validate(receipt["proposal"]).source.version == "15"
    # A second retained proposal remains inspectable after deliberate reconfirmation.
    build_index(source.path, names, rows, SourceMetadata(retrieved_at="2026-10-09T00:00:00Z"))
    # Reconfirm v15 first because this independently rebuilt fixture has a different taxon payload.
    confirm_link(database, identity.id, "100", ARCHIVE_SHA256, source)
    pending = propose(database, identity.id, source)
    confirm_link(database, identity.id, "100", RELEASES["16"].checksum, v16)
    with pytest.raises(EnrichmentConflictError):
        apply(
            database,
            identity.id,
            pending.id,
            ApplyWrite(selected_place_ids=[place(database, "PE").id]),
        )
    fresh = propose(database, identity.id, v16)
    assert fresh.source.version == "16"
    assert fresh.crosswalk_version == "wcvp16-wgsrpd2-cldr48.2.1-v2"
    path16.unlink()
    result = apply(
        database, identity.id, fresh.id, ApplyWrite(selected_place_ids=[place(database, "PE").id])
    )
    assert set(result.kept) == {manual.id, bolivia.id}
    assert historical.evidence == receipt
    assert inspect_proposal(database, identity.id, old.id).source.version == "15"


@pytest.mark.parametrize("source", ["15"], indirect=True)
@pytest.mark.parametrize("change", ["removed", "synonym", "accepted_id"])
def test_v16_transitions_do_not_automatically_migrate_v15_links(
    database: Session, identity: BotanicalIdentity, source: WcvpSource, tmp_path: Path, change: str
) -> None:
    from florabase.native_range_enrichment.model import WcvpLink
    from florabase.native_range_enrichment.source import RELEASES

    linked(database, identity, source)
    original = database.get(WcvpLink, identity.id)
    assert original is not None
    original_version = original.version
    path = tmp_path / "changed-v16.sqlite"
    names = (
        []
        if change == "removed"
        else [
            dict.fromkeys(NAMES_FIELDS, "")
            | {
                "plant_name_id": "100",
                "taxon_name": "Fixture species",
                "taxon_rank": "Species",
                "taxon_status": "Synonym" if change == "synonym" else "Accepted",
                "accepted_plant_name_id": "101" if change == "accepted_id" else "100",
            }
        ]
    )
    build_index(path, names, [], SourceMetadata.for_release("16", "2026-10-28T00:00:00Z"))
    v16 = WcvpSource(path, "16")
    with pytest.raises((EnrichmentConflictError, SourceUnavailableError)):
        confirm_link(database, identity.id, "100", RELEASES["16"].checksum, v16)
    assert original.version == original_version
    assert original.source["version"] == "15"
    assert propose(database, identity.id, source).source.version == "15"


@pytest.mark.parametrize("source", ["15", "16"], indirect=True)
def test_apply_refreshes_geography_after_another_transaction_changes_it(
    database_engine: Engine,
    source: WcvpSource,
) -> None:
    identity_id = uuid7()
    with Session(database_engine, expire_on_commit=False) as db:
        record = BotanicalIdentity(
            id=identity_id, scientific_name=f"Geography concurrency {identity_id}"
        )
        db.add(record)
        db.flush()
        linked(db, record, source)
        proposal = propose(db, identity_id, source)
        bolivia = place(db, "BO")
        previous = bolivia.source_version
        db.commit()
        try:
            with Session(database_engine) as other:
                changed = other.get(GeographicPlace, bolivia.id)
                assert changed is not None
                changed.source_version = "concurrent-unreviewed"
                other.commit()
            with pytest.raises(EnrichmentConflictError, match="geography changed"):
                apply(db, identity_id, proposal.id, ApplyWrite(selected_place_ids=[bolivia.id]))
            db.rollback()
            assert db.get(NativeRangeApplication, proposal.id) is None
            assert db.get(BotanicalProfileNativeRange, (identity_id, bolivia.id)) is None
        finally:
            db.rollback()
            with Session(database_engine) as cleanup:
                changed = cleanup.get(GeographicPlace, bolivia.id)
                assert changed is not None
                assert changed.source_version == "concurrent-unreviewed"
                changed.source_version = previous
                cleanup.delete(cleanup.get(BotanicalIdentity, identity_id))
                cleanup.commit()
