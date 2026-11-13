import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast
from uuid import uuid7

import pytest
from sqlalchemy import Connection, event, select, text
from sqlalchemy.orm import Session
from test_native_range_enrichment import distribution
from test_native_range_enrichment import name as wcvp_name
from test_taxonomy import FAMILY, GENUS
from test_taxonomy import META as WFO_META

import florabase.native_range_enrichment.snapshot as wcvp_snapshot
import florabase.taxonomy.snapshot as wfo_snapshot
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_matching import MatchBatchReport, match_collection_identities
from florabase.botanical_profiles.model import BotanicalProfile
from florabase.core.config import Settings
from florabase.external_botany.model import ExternalTaxonLink
from florabase.main import app as _app  # noqa: F401 - register full ORM metadata for FKs
from florabase.native_range_enrichment.model import WcvpLink
from florabase.native_range_enrichment.source import (
    RELEASES,
    WcvpSource,
)
from florabase.native_range_enrichment.source import (
    SourceMetadata as WcvpSourceMetadata,
)
from florabase.seed_lots.model import SeedLot
from florabase.taxonomy.model import WfoLink
from florabase.taxonomy.schemas import TaxonomyEvidence
from florabase.taxonomy.source import CHECKSUM as WFO_CHECKSUM
from florabase.taxonomy.source import CODE, ROOT, WfoMetadata, WfoSource, WfoTaxon


class _RunQualificationFn(Protocol):
    def __call__(
        self,
        *,
        wfo_source: WfoSource | None = None,
        wcvp_v16_source: WcvpSource | None = None,
        wcvp_v15_source: WcvpSource | None = None,
        database_url: str | None = None,
    ) -> MatchBatchReport: ...


def _load_run_qualification() -> _RunQualificationFn:
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "botanical_match_qualify.py"
    spec = importlib.util.spec_from_file_location("botanical_match_qualify", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(_RunQualificationFn, module.run_qualification)


pytestmark = pytest.mark.integration


def _local_sources(tmp_path: Path) -> tuple[WfoSource, WcvpSource]:
    wfo_names = [
        {"ID": ROOT, "scientificName": "Plantae", "authorship": "", "rank": "kingdom"},
        {"ID": FAMILY, "scientificName": "Lamiaceae", "authorship": "", "rank": "family"},
        {"ID": GENUS, "scientificName": "Lavandula", "authorship": "L.", "rank": "genus"},
        {
            "ID": "wfo-0000000010",
            "scientificName": "Lavandula angustifolia",
            "authorship": "Mill.",
            "rank": "species",
        },
        {
            "ID": "wfo-0000000011",
            "scientificName": "Salvia officinalis",
            "authorship": "L.",
            "rank": "species",
        },
    ]
    wfo_concepts = [
        {"ID": ROOT, "nameID": ROOT, "parentID": CODE},
        {"ID": FAMILY, "nameID": FAMILY, "parentID": ROOT},
        {"ID": GENUS, "nameID": GENUS, "parentID": FAMILY},
        {"ID": "wfo-0000000010", "nameID": "wfo-0000000010", "parentID": GENUS},
        {"ID": "wfo-0000000011", "nameID": "wfo-0000000011", "parentID": GENUS},
    ]
    wfo_path = tmp_path / "wfo.sqlite"
    wfo_snapshot.build_index(wfo_path, wfo_names, wfo_concepts, [], WFO_META)

    v16_path = tmp_path / "wcvp-16.sqlite"
    wcvp_snapshot.build_index(
        v16_path,
        [
            wcvp_name("10", "Accepted", "10") | {"taxon_name": "Lavandula angustifolia"},
            wcvp_name("11", "Accepted", "11") | {"taxon_name": "Salvia officinalis"},
        ],
        [distribution() | {"plant_name_id": "10"}],
        WcvpSourceMetadata.for_release("16", "2026-10-28T00:00:00Z"),
    )
    return WfoSource(wfo_path), WcvpSource(v16_path, "16")


def test_collection_matching_uses_bounded_queries_and_never_mutates(
    database_connection: Connection, tmp_path: Path
) -> None:
    wfo, v16 = _local_sources(tmp_path)
    now = datetime.now(UTC)

    rep_identity = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Lavandula angustifolia",
        common_name="English lavender",
        created_at=now,
        updated_at=now,
    )
    synthetic_identity = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Salvia officinalis",
        created_at=now,
        updated_at=now,
    )
    merged_identity = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Lavandula spica",
        merged_into_id=rep_identity.id,
        merged_at=now,
        created_at=now,
        updated_at=now,
    )
    extra_identities = [
        BotanicalIdentity(
            id=uuid7(),
            scientific_name=f"Plantus batchus_{idx:02d}",
            created_at=now,
            updated_at=now,
        )
        for idx in range(25)
    ]

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as session:
        session.add_all([rep_identity, synthetic_identity, *extra_identities])
        session.flush()
        session.add(merged_identity)
        session.add(
            SeedLot(
                id=uuid7(),
                botanical_identity_id=rep_identity.id,
                label="SL-1",
                lifecycle="active",
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            BotanicalProfile(
                botanical_identity_id=rep_identity.id,
                description="Hardy perennial subshrub",
            )
        )
        # Official WcvpLink preserved + Synthetic Golden WfoLink flagged
        session.add(
            WcvpLink(
                identity_id=rep_identity.id,
                version=uuid7(),
                external_id="10",
                taxon={
                    "external_id": "10",
                    "name": "Lavandula angustifolia",
                    "authorship": "A.Author",
                    "rank": "Species",
                    "status": "Accepted",
                    "accepted_id": "10",
                    "accepted_name": "Lavandula angustifolia",
                    "powo_id": "",
                    "reviewed": "",
                },
                source=WcvpSourceMetadata.for_release("16", "2026-10-28T00:00:00Z").model_dump(
                    mode="json"
                ),
                identity_snapshot={
                    "scientific_name": "Lavandula angustifolia",
                    "cultivar_name": None,
                    "common_name": "English lavender",
                    "updated_at": now.isoformat(),
                },
                confirmed_at=now,
            )
        )
        synthetic_evidence = TaxonomyEvidence(
            source=WfoMetadata(retrieved_at=now.isoformat()),
            taxon=WfoTaxon(
                source_taxon_id="wfo-0000000102",
                parent_source_taxon_id="wfo-4000000012",
                scientific_name="Salvia officinalis",
                authorship="Golden",
                rank="species",
                taxonomic_status="accepted",
                accepted_source_taxon_id=None,
            ),
            classification=[],
            identity_updated_at=now,
        ).model_dump(mode="json")
        session.add(
            WfoLink(
                identity_id=synthetic_identity.id,
                version=uuid7(),
                external_id="wfo-0000000102",
                evidence=synthetic_evidence,
                confirmed_at=now,
            )
        )
        session.add(
            ExternalTaxonLink(
                id=uuid7(),
                botanical_identity_id=rep_identity.id,
                provider="gbif",
                external_id="2927305",
                scientific_name="Lavandula angustifolia",
                canonical_name="Lavandula angustifolia",
                taxonomic_status="ACCEPTED",
                linked_at=now,
                last_refreshed_at=now,
                last_refresh_attempt_at=now,
            )
        )
        session.flush()

        executed_sql: list[str] = []

        def record_sql(_conn: object, _cursor: object, statement: str, *_args: object) -> None:
            executed_sql.append(statement.strip())

        event.listen(database_connection.engine, "before_cursor_execute", record_sql)
        try:
            report = match_collection_identities(
                session,
                wfo_source=wfo,
                wcvp_v16_source=v16,
            )
        finally:
            event.remove(database_connection.engine, "before_cursor_execute", record_sql)

        # Bounded O(1) SQL queries regardless of 27 identities, strictly read-only SELECTs.
        assert 1 <= len(executed_sql) <= 4
        assert all(sql.upper().startswith("SELECT") for sql in executed_sql)

        # Merged tombstone excluded; represented vs reference-only accurately reported.
        assert report.total_identities == 27
        assert report.represented_identities == 1
        assert report.reference_only_identities == 26
        by_name = {res.identity.scientific_name: res for res in report.results}
        assert "Lavandula spica" not in by_name

        rep_res = by_name["Lavandula angustifolia"]
        assert rep_res.identity.represented is True
        assert rep_res.wfo.outcome == "auto_eligible"
        assert rep_res.wcvp_v16.outcome == "already_linked"
        assert rep_res.wcvp_v16.existing_link_posture == "existing_verified_or_manual_current"
        assert rep_res.wcvp_v16.source_checksum == RELEASES["16"].checksum
        assert rep_res.wfo.source_checksum == WFO_CHECKSUM

        synth_res = by_name["Salvia officinalis"]
        assert synth_res.wfo.existing_link_posture == "synthetic_golden"
        assert "synthetic_evidence_present" in synth_res.wfo.reason_codes

        # Verify canonical identity and profile rows remained untouched.
        refetched = session.get(BotanicalIdentity, rep_identity.id)
        assert refetched is not None
        assert refetched.scientific_name == "Lavandula angustifolia"
        profile = session.scalar(
            select(BotanicalProfile).where(
                BotanicalProfile.botanical_identity_id == rep_identity.id
            )
        )
        assert profile is not None
        assert profile.description == "Hardy perennial subshrub"


def test_qualification_cli_database_url_runs_postgresql_read_only_transaction(
    integration_settings: Settings, tmp_path: Path
) -> None:
    wfo, v16 = _local_sources(tmp_path)
    database_url = integration_settings.database_url
    # Disposable DB is empty or pre-migrated; SET TRANSACTION READ ONLY executes cleanly.
    run_qualification = _load_run_qualification()
    report = run_qualification(
        wfo_source=wfo,
        wcvp_v16_source=v16,
        database_url=database_url,
    )
    assert report.total_identities == 0
    assert text("SELECT 1") is not None
