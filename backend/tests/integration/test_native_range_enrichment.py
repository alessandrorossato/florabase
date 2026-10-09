import sqlite3
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
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
)
from florabase.native_range_enrichment.schemas import ApplyWrite, ProposalResponse
from florabase.native_range_enrichment.service import (
    EnrichmentConflictError,
    apply,
    confirm_link,
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
    SourceMetadata,
    SourceUnavailableError,
    WcvpSource,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def source(tmp_path: Path) -> WcvpSource:
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
    build_index(path, names, rows, SourceMetadata(retrieved_at="2026-10-09T00:00:00Z"))
    return WcvpSource(path)


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
    confirm_link(database, identity.id, "100", ARCHIVE_SHA256, source)


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
    assert retained.source.checksum == ARCHIVE_SHA256
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
    "change", ["range", "roundtrip", "identity", "link", "source", "crosswalk"]
)
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
            evidence["source"]["version"] = "16"
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
