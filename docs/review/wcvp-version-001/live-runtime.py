"""Small additive synthetic fixtures, restricted to the WCVP-owned Review database."""

# ruff: noqa: T201 -- Review evidence only; credentials are read from stdin.
from __future__ import annotations

import fcntl
import json
import os
import sys
from uuid import UUID

import uat_fixture as guarded
from sqlalchemy import select
from sqlalchemy.orm import Session

from florabase.auth.model import User
from florabase.auth.service import bootstrap_owner
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_profiles.schemas import BotanicalProfilePut
from florabase.botanical_profiles.service import add_botanical_native_range, put_botanical_profile
from florabase.db.session import get_engine
from florabase.geographic_places.model import GeographicPlace
from florabase.native_range_enrichment.model import WcvpLink
from florabase.native_range_enrichment.schemas import ApplyWrite
from florabase.native_range_enrichment.service import apply, confirm_link, inspect_proposal, propose
from florabase.native_range_enrichment.source import WcvpSource

EXPECTED_SOURCE = "__SOURCE__"


def require_source() -> None:
    assert os.environ.get("FLORABASE_REVIEW_SOURCE") == EXPECTED_SOURCE, "Foreign source refused"


def check_refusals(settings: object, db: Session) -> None:
    from unittest.mock import patch

    for changes in (
        {"FLORABASE_WORKFLOW_MODE": "dev"},
        {"FLORABASE_REVIEW_PROJECT": "florabase-feature-review"},
        {"FLORABASE_REVIEW_PROJECT": "florabase-ui-audit-bc88"},
        {"FLORABASE_REVIEW_SOURCE": "/foreign"},
    ):
        with patch.dict(os.environ, changes):
            try:
                require_source()
                guarded.require_identity(settings, db, require_marker=False)
            except AssertionError, guarded.FixtureError:
                continue
            raise AssertionError(f"Foreign runtime accepted: {changes}")


def main() -> None:
    require_source()
    settings = guarded.get_settings()
    action = sys.argv[1]
    with Session(get_engine()) as db:
        root = guarded.require_identity(settings, db, require_marker=False)
        check_refusals(settings, db)
        with (root / ".wcvp-version-001.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            ledger_path = root / ".wcvp-version-001.json"
            if ledger_path.exists():
                ledger = json.loads(ledger_path.read_text())
                assert ledger["source"] == EXPECTED_SOURCE
                for entry in ledger["scenarios"]:
                    assert db.get(BotanicalIdentity, UUID(entry["identity_id"])) is not None
                print(json.dumps(ledger, indent=2))
                return
            assert action == "seed", "Review is not seeded"
            assert db.scalar(select(User.id).limit(1)) is None, "Existing owner; seed refused"
            assert db.scalar(select(BotanicalIdentity.id).limit(1)) is None, (
                "Existing data; seed refused"
            )
            credentials = json.load(sys.stdin)
            bootstrap_owner(
                db, credentials["login"], credentials["password"], "WCVP Review operator"
            )
            v15 = WcvpSource(settings.wcvp_snapshot_path)
            v16 = WcvpSource(settings.wcvp_v16_snapshot_path, "16")
            scenarios = []
            cases = [
                ("Frozen v15 Apply with both indices installed", "15", "2640812", False),
                ("Immutable v15 applied evidence", "15", "2640812", True),
                ("Explicit v16 proposal", "16", "2640812", False),
                ("Removed in v16; retain v15 link", "15", "184159", False),
                ("Accepted to synonym; retain v15 link", "15", "101680", False),
                ("Accepted-ID transition; explicit v16 choice", "16", "100008", False),
            ]
            italy = db.scalars(
                select(GeographicPlace).where(GeographicPlace.source_code == "IT")
            ).one()
            for number, (label, version, external_id, applied) in enumerate(cases, 1):
                source = v15 if version == "15" else v16
                taxon = source.taxon(external_id)
                assert taxon.eligible
                identity = BotanicalIdentity(
                    scientific_name=taxon.name, cultivar_name=f"Review {number}", common_name=label
                )
                db.add(identity)
                db.flush()
                put_botanical_profile(
                    db,
                    identity.id,
                    BotanicalProfilePut(
                        cultivation="Synthetic operator text: preserve through WCVP review."
                    ),
                )
                add_botanical_native_range(db, identity.id, italy.id)
                confirm_link(db, identity.id, external_id, source.metadata().checksum, source)
                proposal = propose(db, identity.id, source)
                if applied:
                    selected = [c.place_id for c in proposal.choices if c.change == "ADD"]
                    assert selected, "Fixture requires applicable native assertions"
                    apply(db, identity.id, proposal.id, ApplyWrite(selected_place_ids=selected))
                scenarios.append(
                    {
                        "label": label,
                        "identity_id": str(identity.id),
                        "proposal_id": str(proposal.id),
                        "source_version": version,
                        "external_id": external_id,
                    }
                )
                assert db.get(WcvpLink, identity.id).source["version"] == version
                assert inspect_proposal(db, identity.id, proposal.id).source.version == version
            db.commit()
            ledger = {"source": EXPECTED_SOURCE, "synthetic": True, "scenarios": scenarios}
            ledger_path.write_text(json.dumps(ledger))
            print(json.dumps(ledger, indent=2))


if __name__ == "__main__":
    main()
