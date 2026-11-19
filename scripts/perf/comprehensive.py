"""Supported Golden COMPREHENSIVE provisioning, validation and report evaluation."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import re
import statistics
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeGuard, cast
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from disposable_workflow import compose_invocation  # noqa: E402
from workflow_resources import Disposable, Owner  # noqa: E402

SCENARIOS_PATH = ROOT / "scripts/fixtures/golden/scenarios.json"
GOLDEN_COPY_NAME = "golden_perf"
GOLDEN_PROFILE = "comprehensive"
GOLDEN_OWNER_LOGIN = "golden-owner"
GOLDEN_OWNER_PASSWORD = "disposable-golden-owner-password"
POSTGRES_STAGE_USER = "florabase_integration"
GOLDEN_COPY_ROOT = Path("/tmp/florabase-golden")
# Matches Vite's unchanged 500 kB build chunk warning threshold (PERF-001.md).
VITE_CHUNK_ADVISORY_BYTES = 500_000
PIN_MODE_STRICT = "strict"
PIN_MODE_ALLOW_MODIFIED = "allow-modified-baseline"
VALID_PIN_MODES = frozenset({PIN_MODE_STRICT, PIN_MODE_ALLOW_MODIFIED})
EXCLUDED_COUNT_TABLES = frozenset({"auth_sessions", "login_throttles"})
NOT_DOMAIN_COUNT_TABLES = frozenset({"application_settings", "users", "external_provider_cache"})
# Append-only / operational audit or session tables that a supported mutation workflow may add to.
LEGITIMATE_POST_MUTATION_DELTA_TABLES = frozenset(
    {"auth_sessions", "login_throttles", "operation_receipts"}
)
REQUIRED_STARTUP_KEYS: tuple[str, ...] = (
    "provision_bundle_s",
    "database_health_s",
    "restore_db_s",
    "application_health_s",
    "restore_media_s",
)
REQUIRED_SERVICES: tuple[str, ...] = ("db", "backend", "frontend")

# Complete 48-endpoint normalized read inventory exercised against COMPREHENSIVE.
REQUIRED_API_ENDPOINTS: tuple[str, ...] = (
    "/dashboard",
    "/botanical-identities",
    "/seed-lots",
    "/sowings",
    "/plants",
    "/plant-groups",
    "/vegetative-lots",
    "/propagation-attempts",
    "/harvests",
    "/harvest-inventory",
    "/orders",
    "/suppliers",
    "/locations",
    "/geographic-places",
    "/provenance-sites",
    "/provenance-sites/map",
    "/events",
    "/history",
    "/schedule",
    "/media-assets",
    "/saved-views",
    "/explore/native-ranges/overview",
    "/explore/species-distribution/identities",
    "/explore/taxonomy/tree",
    "/search?q=Golden",
    "/botanical-identities/{id}",
    "/botanical-identities/{id}/collection",
    "/botanical-identities/{id}/profile",
    "/seed-lots/{id}",
    "/seed-lots/{id}/lineage",
    "/sowings/{id}",
    "/sowings/{id}/germination",
    "/plants/{id}",
    "/plants/{id}/lineage",
    "/plant-groups/{id}",
    "/vegetative-lots/{id}",
    "/propagation-attempts/{id}",
    "/harvests/{id}",
    "/harvest-inventory/{id}",
    "/orders/{id}",
    "/suppliers/{id}",
    "/locations/{id}",
    "/provenance-sites/{id}",
    "/collection-records/seed_lot/{id}/photos",
    "/media-assets/{id}",
    "/media-assets/{id}/thumbnail",
    "/collection-photos/local/{id}/thumbnail",
    "/attachments/{id}/content",
)

# Complete 39-route browser workload inventory exercised in browser.mjs.
REQUIRED_BROWSER_ROUTES: tuple[str, ...] = (
    "today",
    "identities",
    "identity",
    "identity_reference",
    "identity_maps",
    "seeds",
    "seed",
    "photos",
    "lineage",
    "sowings",
    "sowing",
    "germination",
    "cuttings",
    "cutting_lot",
    "plants",
    "plant",
    "group",
    "harvests",
    "harvest",
    "stored_material",
    "suppliers",
    "supplier",
    "orders",
    "order",
    "locations",
    "location",
    "geography",
    "site",
    "place",
    "native_ranges",
    "taxonomy",
    "media",
    "events",
    "history",
    "schedule",
    "provenance",
    "occurrence",
    "labels",
    "dashboard",
)

# Stable scenario keys in the canonical COMPREHENSIVE plan used across API & browser workloads.
MANIFEST_SCENARIO_KEYS: dict[str, str] = {
    "identity": "identity:base-reference/basil",
    "rich_identity": "identity:identity-reference/rich",
    "seed": "seed:media-references/with-media",
    "lineage_seed": "seed:seed-collection-produced/from-plant",
    "sowing": "sowing:sowing-germination-states/environment",
    "plant": "plant:current-collection-history/offspring",
    "group": "group:plant-lifecycle-states/exact",
    "cutting_lot": "cutting_lot:current-collection-history/mother",
    "cutting_attempt": "cutting_attempt:current-collection-history/rooted",
    "harvest": "harvest:harvest-stored-material/tracked",
    "inventory": "inventory:harvest-stored-material/active",
    "order": "order:sourcing-suppliers-orders/exact",
    "supplier": "supplier:base-reference/seller",
    "location": "location:base-reference/shelf",
    "site": "site:base-reference/mapped",
    "place": "place:base-reference/garden",
    "asset": "asset:media-references/shared",
    "photo_link": "link:media-references/seed",
}

GENERATOR_FILES: tuple[str, ...] = (
    "scripts/golden_dataset.py",
    "scripts/golden_plan.py",
    "scripts/fixtures/golden/scenarios.json",
    "scripts/perf/compose.sh",
    "scripts/perf/comprehensive.py",
    "scripts/perf/measure.py",
    "scripts/perf/browser.mjs",
    "scripts/perf/verify-chunk-recovery.mjs",
    "compose.yaml",
    "compose.perf.yaml",
)


class FixtureValidationError(RuntimeError):
    """Raised when the Golden COMPREHENSIVE fixture or manifest fails validation."""


@dataclass(frozen=True)
class ProvisionedBundle:
    """Artifacts and verified provenance captured from a disposable golden_<name> copy."""

    dump_bytes: bytes
    originals_tar_bytes: bytes
    ledger: dict[str, Any]
    verify_baseline: dict[str, Any]
    digest: dict[str, Any]
    validate: dict[str, Any]
    targets: dict[str, str]
    provisioning_project: str
    copy_name: str
    provisioned_at: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_scenarios_manifest(path: Path = SCENARIOS_PATH) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def expected_comprehensive_pin(path: Path = SCENARIOS_PATH) -> dict[str, Any]:
    manifest = load_scenarios_manifest(path)
    profile = manifest["profiles"][GOLDEN_PROFILE]
    expected = profile["expected"]
    return {
        "dataset": manifest["dataset"],
        "version": manifest["version"],
        "seed": manifest["seed"],
        "anchor_date": manifest["anchor_date"],
        "profile": GOLDEN_PROFILE,
        "volume": profile["volume"],
        "plan_sha256": expected["plan_sha256"],
        "nodes": expected["nodes"],
        "tables": expected["tables"],
        "projections": expected["projections"],
        "baseline": expected["baseline"],
    }


def code_alembic_head(root: Path = ROOT) -> str:
    versions_dir = root / "backend/alembic/versions"
    revisions: set[str] = set()
    referenced: set[str] = set()
    rev_pattern = re.compile(r"^revision(?:\s*:\s*[^=]+)?\s*=\s*['\"]([^'\"]+)['\"]", re.M)
    down_pattern = re.compile(r"^down_revision(?:\s*:\s*[^=]+)?\s*=\s*(.+)$", re.M)
    for path in sorted(versions_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        rev_match = rev_pattern.search(text)
        if not rev_match:
            continue
        revisions.add(rev_match.group(1))
        down_match = down_pattern.search(text)
        if down_match:
            rhs = down_match.group(1).strip()
            for token in re.findall(r"['\"]([^'\"]+)['\"]", rhs):
                referenced.add(token)
    heads = sorted(revisions - referenced)
    if len(heads) != 1:
        raise FixtureValidationError(f"Expected single Alembic head in source; found {heads}")
    return heads[0]


def resolve_targets(records: dict[str, Any], *, attachment_id: str | None = None) -> dict[str, str]:
    targets: dict[str, str] = {}
    missing: list[str] = []
    for target_name, scenario_key in MANIFEST_SCENARIO_KEYS.items():
        value = records.get(scenario_key)
        if not isinstance(value, str):
            missing.append(scenario_key)
            continue
        try:
            UUID(value)
        except ValueError as error:
            raise FixtureValidationError(
                f"Invalid UUID for scenario key {scenario_key}: {value!r}"
            ) from error
        targets[target_name] = value
    if missing:
        raise FixtureValidationError(
            "COMPREHENSIVE ledger is missing required scenario keys: " + ", ".join(missing)
        )
    if attachment_id is not None:
        try:
            UUID(attachment_id)
        except ValueError as error:
            raise FixtureValidationError(f"Invalid attachment UUID: {attachment_id!r}") from error
        targets["attachment"] = attachment_id
    return targets


def _run_checked(
    argv: list[str],
    *,
    env: dict[str, str] | None = None,
    text_mode: bool = True,
    allowed_exit_codes: tuple[int, ...] = (0,),
) -> bytes | str:
    result = subprocess.run(
        argv,
        env=env,
        check=False,
        capture_output=True,
        text=text_mode,
    )
    if result.returncode not in allowed_exit_codes:
        stderr = (
            result.stderr
            if isinstance(result.stderr, str)
            else result.stderr.decode("utf-8", "replace")
        )
        stdout = (
            result.stdout
            if isinstance(result.stdout, str)
            else result.stdout.decode("utf-8", "replace")
        )
        detail = stderr.strip() or stdout.strip() or f"exit code {result.returncode}"
        raise FixtureValidationError(f"Command failed ({' '.join(argv)}): {detail}")
    return cast(bytes | str, result.stdout)


def provision_comprehensive_bundle(
    root: Path = ROOT,
    *,
    copy_name: str = GOLDEN_COPY_NAME,
) -> ProvisionedBundle:
    """Generate and validate COMPREHENSIVE via the supported disposable TEST-copy route."""
    if not re.fullmatch(r"golden_[a-z0-9_]{1,40}", copy_name):
        raise FixtureValidationError(f"Disallowed golden copy name: {copy_name!r}")

    owner = Owner.disposable("integration", root)
    with tempfile.TemporaryDirectory(prefix="florabase-perf-provision-") as temporary:
        argv, env = compose_invocation("integration", root, owner, [], Path(temporary))
        with Disposable(owner) as lifecycle:
            lifecycle.run([*argv, "up", "-d", "--wait", "--wait-timeout", "120", "db"], env=env)
            lifecycle.run([*argv, "build", "tests"], env=env)
            lifecycle.run(
                [*argv, "run", "-d", "--no-deps", "tests", "sleep", "infinity"],
                env=env,
            )
            inventory = lifecycle.resources.inventory()
            lifecycle.resources.preflight(inventory)
            (runner,) = [
                item["Id"]
                for item in inventory["containers"]
                if item["Config"]["Labels"]["com.docker.compose.service"] == "tests"
            ]
            created_copy = False
            try:
                _run_checked(
                    [
                        "docker",
                        "exec",
                        runner,
                        "python",
                        "/review/golden_dataset.py",
                        "create-copy",
                        "--copy",
                        copy_name,
                        "--profile",
                        GOLDEN_PROFILE,
                    ]
                )
                created_copy = True
                _run_checked(
                    [
                        "docker",
                        "exec",
                        runner,
                        "python",
                        "/review/golden_dataset.py",
                        "generate",
                        "--copy",
                        copy_name,
                        "--profile",
                        GOLDEN_PROFILE,
                    ]
                )
                baseline_raw = cast(
                    str,
                    _run_checked(
                        [
                            "docker",
                            "exec",
                            runner,
                            "python",
                            "/review/golden_dataset.py",
                            "verify-baseline",
                            "--copy",
                            copy_name,
                            "--profile",
                            GOLDEN_PROFILE,
                        ],
                        allowed_exit_codes=(0, 3),
                    ),
                )
                verify_baseline = cast(dict[str, Any], json.loads(baseline_raw))
                digest_raw = cast(
                    str,
                    _run_checked(
                        [
                            "docker",
                            "exec",
                            runner,
                            "python",
                            "/review/golden_dataset.py",
                            "digest",
                            "--copy",
                            copy_name,
                        ]
                    ),
                )
                digest_report = cast(dict[str, Any], json.loads(digest_raw))
                validate_raw = cast(
                    str,
                    _run_checked(
                        [
                            "docker",
                            "exec",
                            runner,
                            "python",
                            "/review/golden_dataset.py",
                            "validate",
                            "--copy",
                            copy_name,
                            "--profile",
                            GOLDEN_PROFILE,
                        ]
                    ),
                )
                validate_report = cast(dict[str, Any], json.loads(validate_raw))
                ledger_raw = cast(
                    str,
                    _run_checked(
                        [
                            "docker",
                            "exec",
                            runner,
                            "cat",
                            f"{GOLDEN_COPY_ROOT / copy_name / '.golden-dataset.json'}",
                        ]
                    ),
                )
                ledger = cast(dict[str, Any], json.loads(ledger_raw))
                dump_bytes = cast(
                    bytes,
                    _run_checked(
                        [
                            *argv,
                            "exec",
                            "-T",
                            "db",
                            "pg_dump",
                            "-U",
                            POSTGRES_STAGE_USER,
                            "-d",
                            copy_name,
                            "-Fc",
                            "--no-owner",
                            "--no-privileges",
                        ],
                        env=env,
                        text_mode=False,
                    ),
                )
                originals_tar_bytes = cast(
                    bytes,
                    _run_checked(
                        [
                            "docker",
                            "exec",
                            "-e",
                            f"FLORABASE_ATTACHMENT_STORAGE_ROOT={GOLDEN_COPY_ROOT / copy_name}",
                            runner,
                            "python",
                            "/app/scripts/attachment_artifacts.py",
                            "archive",
                        ],
                        text_mode=False,
                    ),
                )
            finally:
                if created_copy:
                    subprocess.run(
                        [
                            "docker",
                            "exec",
                            runner,
                            "python",
                            "/review/golden_dataset.py",
                            "retire-copy",
                            "--copy",
                            copy_name,
                        ],
                        check=False,
                        capture_output=True,
                    )

    targets = resolve_targets(ledger.get("records", {}))
    return ProvisionedBundle(
        dump_bytes=dump_bytes,
        originals_tar_bytes=originals_tar_bytes,
        ledger=ledger,
        verify_baseline=verify_baseline,
        digest=digest_report,
        validate=validate_report,
        targets=targets,
        provisioning_project=owner.project,
        copy_name=copy_name,
        provisioned_at=datetime.now(UTC).isoformat(),
    )


def validate_fixture_manifest(
    *,
    ledger: dict[str, Any],
    verify_baseline: dict[str, Any],
    digest: dict[str, Any],
    validate_report: dict[str, Any],
    targets: dict[str, str],
    live_schema_revision: str,
    live_table_counts: dict[str, int],
    live_canonical_places_count: int,
    live_attachment_count: int,
    media_verify_output: str,
    expected_pin: dict[str, Any] | None = None,
    source_code_head: str | None = None,
    pin_mode: str = PIN_MODE_STRICT,
) -> dict[str, Any]:
    """Validate COMPREHENSIVE identity, schema pin, entity/media counts and digests."""
    if pin_mode not in VALID_PIN_MODES:
        raise FixtureValidationError(
            f"Unsupported fixture pin_mode {pin_mode!r}; expected one of {sorted(VALID_PIN_MODES)}"
        )
    pin = expected_pin if expected_pin is not None else expected_comprehensive_pin()
    code_head = source_code_head if source_code_head is not None else code_alembic_head()
    differences: list[str] = []
    pin_differences: list[str] = []

    if ledger.get("dataset") != pin["dataset"]:
        differences.append(f"dataset mismatch: {ledger.get('dataset')!r} != {pin['dataset']!r}")
    if ledger.get("version") != pin["version"]:
        differences.append(f"version mismatch: {ledger.get('version')!r} != {pin['version']!r}")
    if ledger.get("profile") != pin["profile"]:
        differences.append(f"profile mismatch: {ledger.get('profile')!r} != {pin['profile']!r}")
    if ledger.get("seed") != pin["seed"]:
        differences.append(f"seed mismatch: {ledger.get('seed')!r} != {pin['seed']!r}")
    if ledger.get("anchor_date") != pin["anchor_date"]:
        differences.append(
            f"anchor_date mismatch: {ledger.get('anchor_date')!r} != {pin['anchor_date']!r}"
        )
    if ledger.get("volume") != pin["volume"]:
        differences.append(f"volume mismatch: {ledger.get('volume')!r} != {pin['volume']!r}")
    if ledger.get("state") != "ready":
        differences.append(f"ledger state is not ready: {ledger.get('state')!r}")
    if ledger.get("plan_sha256") != pin["plan_sha256"]:
        differences.append(
            f"plan_sha256 mismatch: {ledger.get('plan_sha256')!r} != {pin['plan_sha256']!r}"
        )

    baseline_pin = pin["baseline"]
    pinned_revision = baseline_pin["schema_revision"]
    if code_head != pinned_revision:
        differences.append(
            f"source Alembic head {code_head!r} differs from COMPREHENSIVE pin {pinned_revision!r}"
        )
    if live_schema_revision != pinned_revision:
        differences.append(
            f"live DB Alembic revision {live_schema_revision!r} != pinned {pinned_revision!r}"
        )
    baseline_state = verify_baseline.get("state")
    if verify_baseline.get("domain_problems"):
        differences.append(f"domain problems: {verify_baseline.get('domain_problems')}")
    if validate_report.get("domain") != "valid":
        differences.append(f"validate domain state is {validate_report.get('domain')!r}")

    if baseline_state == "baseline-verified":
        if digest.get("canonical_sha256") != baseline_pin["canonical_sha256"]:
            differences.append(
                f"canonical_sha256 mismatch: {digest.get('canonical_sha256')!r} != "
                f"{baseline_pin['canonical_sha256']!r}"
            )
        if verify_baseline.get("baseline_differences"):
            differences.append(
                f"baseline differences: {verify_baseline.get('baseline_differences')}"
            )
    elif (
        baseline_state == "invariant-valid-baseline-modified"
        and pin_mode == PIN_MODE_ALLOW_MODIFIED
    ):
        pin_differences.extend(verify_baseline.get("baseline_differences") or [])
        if digest.get("canonical_sha256") != baseline_pin["canonical_sha256"]:
            pin_differences.append(
                f"canonical_sha256: {digest.get('canonical_sha256')} != "
                f"reviewed {baseline_pin['canonical_sha256']}"
            )
    else:
        differences.append(
            f"strict pin violation ({pin_mode}): verify-baseline state is {baseline_state!r}"
        )
        if verify_baseline.get("baseline_differences"):
            differences.append(
                f"baseline differences: {verify_baseline.get('baseline_differences')}"
            )
        if digest.get("canonical_sha256") != baseline_pin["canonical_sha256"]:
            differences.append(
                f"canonical_sha256 mismatch: {digest.get('canonical_sha256')!r} != "
                f"{baseline_pin['canonical_sha256']!r}"
            )

    expected_tables: dict[str, int] = pin["tables"]
    for table in sorted(expected_tables.keys() | live_table_counts.keys()):
        if table in EXCLUDED_COUNT_TABLES:
            continue
        actual_count = live_table_counts.get(table, 0)
        pinned_count = expected_tables.get(table, 0)
        if actual_count != pinned_count:
            differences.append(f"live table {table}: {actual_count} != pinned {pinned_count}")

    expected_attachments = expected_tables["attachments"]
    if live_attachment_count != expected_attachments:
        differences.append(
            f"live attachments {live_attachment_count} != pinned {expected_attachments}"
        )
    if f"Verified {expected_attachments} stored attachment file(s)" not in media_verify_output:
        differences.append(
            f"media verification output did not confirm {expected_attachments} files: "
            f"{media_verify_output.strip()!r}"
        )

    resolve_targets(ledger.get("records", {}), attachment_id=targets.get("attachment"))

    if differences:
        raise FixtureValidationError(
            "COMPREHENSIVE fixture manifest validation failed:\n- " + "\n- ".join(differences)
        )

    counted_rows = sum(live_table_counts.values())
    domain_records = sum(
        count for table, count in live_table_counts.items() if table not in NOT_DOMAIN_COUNT_TABLES
    )
    baseline_pin_matches = baseline_state == "baseline-verified" and not pin_differences
    blockers = ["Source build benchmark; formal RC-image G-PERF requires immutable RC images"]
    if not baseline_pin_matches:
        blockers.append(
            f"Modified fixture state ({baseline_state}) cannot produce formal certification evidence"
        )
    if pin_mode != PIN_MODE_STRICT:
        blockers.append(f"Non-strict pin mode ({pin_mode}) used for preliminary rehearsal")
    return {
        "valid": True,
        "pin_mode": pin_mode,
        "strict_pin_enforced": pin_mode == PIN_MODE_STRICT,
        "certification_eligible": False,
        "certification_blockers": blockers,
        "dataset": ledger["dataset"],
        "version": ledger["version"],
        "profile": ledger["profile"],
        "seed": ledger["seed"],
        "anchor_date": ledger["anchor_date"],
        "volume": ledger["volume"],
        "schema_revision": live_schema_revision,
        "pinned_schema_revision": pinned_revision,
        "plan_sha256": ledger["plan_sha256"],
        "canonical_sha256": digest["canonical_sha256"],
        "pinned_canonical_sha256": baseline_pin["canonical_sha256"],
        "media_sha256": digest["media_sha256"],
        "scenario_keys_sha256": digest["scenario_keys_sha256"],
        "baseline_state": baseline_state,
        "baseline_pin_matches": baseline_pin_matches,
        "ledger_records_count": len(ledger.get("records", {})),
        "plan_nodes": pin["nodes"],
        "counted_rows": counted_rows,
        "domain_records": domain_records,
        "canonical_geographic_places": live_canonical_places_count,
        "total_rows_with_canonical_places": counted_rows + live_canonical_places_count,
        "table_counts": dict(sorted(live_table_counts.items())),
        "media": {
            "attachments_stored": live_attachment_count,
            "media_assets": live_table_counts.get("media_assets", 0),
            "baseline_digest_media_files": digest.get("media_files"),
            "verification_summary": media_verify_output.strip(),
        },
        "targets": dict(sorted(targets.items())),
        "differences_from_pin": pin_differences,
    }


def generator_identity(root: Path = ROOT) -> dict[str, Any]:
    files: dict[str, str] = {}
    for rel in GENERATOR_FILES:
        candidate = root / rel
        if candidate.is_file():
            files[rel] = file_sha256(candidate)
    return {
        "source_alembic_head": code_alembic_head(root),
        "files_sha256": files,
    }


def collect_source_identity(root: Path = ROOT) -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

    head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    branch = git("branch", "--show-current") or "detached"
    dirty = bool(git("status", "--porcelain"))
    try:
        base = git("merge-base", "HEAD", "origin/main")
    except subprocess.CalledProcessError:
        base = ""
    return {
        "branch": branch,
        "head": head,
        "tree": tree,
        "base": base,
        "dirty": dirty,
    }


def collect_host_metadata(
    runner: Callable[[list[str]], str] | None = None,
) -> dict[str, Any]:
    def run(cmd: list[str]) -> str:
        if runner is not None:
            return runner(cmd).strip()
        return subprocess.check_output(cmd, text=True).strip()

    cpu_model = ""
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.lower().startswith("model name"):
                cpu_model = line.partition(":")[2].strip()
                break
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "host_python": platform.python_version(),
        "cpu_model": cpu_model or "unknown",
        "cpu_count_os": os.cpu_count(),
        "docker_info": run(
            ["docker", "info", "--format", "{{.NCPU}} CPUs; {{.MemTotal}} bytes RAM"]
        ),
        "docker_version": run(["docker", "version", "--format", "{{.Server.Version}}"]),
        "compose_version": run(["docker", "compose", "version", "--short"]),
    }


def _is_finite_number(value: Any) -> TypeGuard[int | float]:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def _is_nonneg_int(value: Any) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _as_dict(value: Any) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def evaluate_post_mutation_integrity(
    *,
    expected_counts: dict[str, int],
    post_counts: dict[str, int],
    expected_canonical_places: int,
    post_canonical_places: int,
    expected_schema_revision: str,
    post_schema_revision: str,
    created_identity_deleted: bool,
    residual_perf_records: int,
    media_verify_output: str,
    expected_attachments: int,
) -> dict[str, Any]:
    """Verify logical fixture integrity after create/edit/delete without naive byte-equality."""
    unexpected_deltas: dict[str, dict[str, int]] = {}
    audit_deltas: dict[str, int] = {}
    for table in sorted(expected_counts.keys() | post_counts.keys()):
        if table in EXCLUDED_COUNT_TABLES:
            continue
        before = expected_counts.get(table, 0)
        after = post_counts.get(table, 0)
        if table in LEGITIMATE_POST_MUTATION_DELTA_TABLES:
            if after < before:
                unexpected_deltas[table] = {"expected_min": before, "actual": after}
            elif after != before:
                audit_deltas[table] = after - before
            continue
        if after != before:
            unexpected_deltas[table] = {"expected": before, "actual": after}

    media_verified = (
        f"Verified {expected_attachments} stored attachment file(s)" in media_verify_output
    )
    return {
        "checked": True,
        "created_identity_deleted": created_identity_deleted,
        "residual_perf_records": residual_perf_records,
        "schema_revision": post_schema_revision,
        "expected_schema_revision": expected_schema_revision,
        "canonical_geographic_places": post_canonical_places,
        "expected_canonical_geographic_places": expected_canonical_places,
        "audit_deltas": audit_deltas,
        "unexpected_table_deltas": unexpected_deltas,
        "media_verified": media_verified,
        "media_verification_summary": media_verify_output.strip(),
    }


def _validate_api_entry(entry: Any) -> list[str]:
    problems: list[str] = []
    if not isinstance(entry, dict):
        return ["malformed entry (not an object)"]
    if not _is_finite_number(entry.get("first_ms")) or entry["first_ms"] < 0:
        problems.append("invalid first_ms")
    if not _is_finite_number(entry.get("median_ms")) or entry["median_ms"] < 0:
        problems.append("invalid median_ms")
    samples = entry.get("samples_ms")
    if (
        not isinstance(samples, list)
        or len(samples) != 7
        or not all(_is_finite_number(v) and v >= 0 for v in samples)
    ):
        problems.append("samples_ms must have 7 non-negative finite timings")
    else:
        expected_median = statistics.median(samples)
        if abs(float(entry["median_ms"]) - float(expected_median)) > 0.15:
            problems.append("median_ms inconsistent with samples_ms")
        range_ms = entry.get("range_ms")
        if (
            not isinstance(range_ms, list)
            or len(range_ms) != 2
            or not all(_is_finite_number(v) for v in range_ms)
            or abs(float(range_ms[0]) - float(min(samples))) > 0.15
            or abs(float(range_ms[1]) - float(max(samples))) > 0.15
        ):
            problems.append("range_ms inconsistent with samples_ms")
    byte_count = entry.get("bytes")
    if not _is_nonneg_int(byte_count) or byte_count <= 0:
        problems.append("bytes must be positive integer")
    queries = entry.get("queries")
    if not isinstance(queries, list) or not queries or not all(_is_nonneg_int(q) for q in queries):
        problems.append("queries must be non-empty list of non-negative integers")
    q_samples = entry.get("query_count_samples")
    if (
        not isinstance(q_samples, list)
        or len(q_samples) != 7
        or not all(_is_nonneg_int(q) for q in q_samples)
    ):
        problems.append("query_count_samples must have 7 non-negative integers")
    elif isinstance(queries, list) and sorted(set(q_samples)) != sorted(set(queries)):
        problems.append("queries inconsistent with query_count_samples")
    if not _is_nonneg_int(entry.get("sql_statements_count")):
        problems.append("missing sql_statements_count")
    return problems


def _valid_checkpoint(checkpoint: Any) -> bool:
    if not isinstance(checkpoint, dict):
        return False
    timers = _as_dict(checkpoint.get("timers"))
    if not timers:
        return False
    intervals = timers.get("intervals")
    timeouts = timers.get("timeouts")
    heap = checkpoint.get("JSHeapUsedSize")
    nodes = checkpoint.get("Nodes")
    listeners = checkpoint.get("JSEventListeners")
    return (
        checkpoint.get("maps") == 0
        and checkpoint.get("Documents") == 1
        and _is_finite_number(heap)
        and float(heap) > 0
        and _is_nonneg_int(nodes)
        and nodes > 0
        and _is_nonneg_int(listeners)
        and listeners > 0
        and _is_nonneg_int(timeouts)
        and timeouts == 0
        and _is_nonneg_int(intervals)
        and 0 <= intervals <= 2
    )


def evaluate_report(report: dict[str, Any], *, pin_mode: str | None = None) -> dict[str, Any]:
    """Evaluate harness completeness and application invariants transparently."""
    required_sections = ("environment", "api", "transfer", "browser", "chunk_recovery", "cleanup")
    missing_sections = [
        key
        for key in required_sections
        if not isinstance(report.get(key), dict) or not report.get(key)
    ]
    checks: list[dict[str, Any]] = []
    harness_failures: list[str] = []
    application_failures: list[str] = []

    def record_check(
        name: str,
        passed: bool,
        *,
        category: str,
        observed: Any,
        threshold: Any,
        detail: str = "",
    ) -> None:
        checks.append(
            {
                "id": name,
                "category": category,
                "passed": passed,
                "observed": observed,
                "threshold": threshold,
                "detail": detail,
            }
        )
        if not passed:
            message = f"{name}: {detail or f'observed {observed!r} vs {threshold!r}'}"
            if category == "harness":
                harness_failures.append(message)
            else:
                application_failures.append(message)

    errors = report.get("errors")
    warmup_s = report.get("warmup_s")
    record_check(
        "harness_execution_no_errors",
        isinstance(errors, list)
        and len(errors) == 0
        and _is_finite_number(warmup_s)
        and float(warmup_s) >= 0,
        category="harness",
        observed={"errors": errors, "warmup_s": warmup_s},
        threshold={"errors": [], "warmup_s": ">= 0"},
        detail=f"execution errors={errors!r}, warmup_s={warmup_s!r}",
    )

    env = _as_dict(report.get("environment"))
    startup = _as_dict(env.get("startup"))
    missing_startup = [
        k
        for k in REQUIRED_STARTUP_KEYS
        if not _is_finite_number(startup.get(k)) or float(cast(float, startup.get(k))) < 0
    ]
    runtime_cfg = _as_dict(env.get("runtime_config"))
    proc_counts = _as_dict(env.get("process_counts"))
    proc_ok = all(
        _is_nonneg_int(_as_dict(proc_counts.get(svc)).get("count"))
        and cast(int, _as_dict(proc_counts.get(svc)).get("count")) >= 1
        for svc in REQUIRED_SERVICES
    )
    images = _as_list(env.get("images"))
    source_meta = _as_dict(env.get("source"))
    images_ok = (
        isinstance(env.get("images"), list)
        and len(images) >= 3
        and all(isinstance(item, dict) and bool(item.get("id")) for item in images)
    )
    sections_ok = (
        not missing_sections
        and not missing_startup
        and runtime_cfg.get("storage_mode") == "tmpfs"
        and "tmpfs" in str(runtime_cfg.get("tmpfs_disclosure", "")).lower()
        and proc_ok
        and images_ok
        and bool(source_meta.get("head"))
    )
    record_check(
        "required_measurement_sections_present",
        sections_ok,
        category="harness",
        observed={
            "missing_sections": missing_sections,
            "missing_startup": missing_startup,
            "storage_mode": runtime_cfg.get("storage_mode"),
            "process_counts_present": proc_ok,
            "images_present": images_ok,
        },
        threshold={
            "sections": list(required_sections),
            "startup": list(REQUIRED_STARTUP_KEYS),
            "services_process_counts": list(REQUIRED_SERVICES),
        },
        detail=f"missing sections={missing_sections}, missing startup={missing_startup}",
    )

    manifest = _as_dict(env.get("manifest"))
    manifest_pin_mode = manifest.get("pin_mode")
    report_pin_mode = report.get("pin_mode")
    effective_pin_mode = pin_mode or report_pin_mode or manifest_pin_mode or PIN_MODE_STRICT
    pin_mode_consistent = (
        effective_pin_mode in VALID_PIN_MODES
        and (manifest_pin_mode is None or manifest_pin_mode == effective_pin_mode)
        and (report_pin_mode is None or report_pin_mode == effective_pin_mode)
    )
    baseline_state = manifest.get("baseline_state")
    allowed_states = (
        {"baseline-verified"}
        if effective_pin_mode == PIN_MODE_STRICT
        else {"baseline-verified", "invariant-valid-baseline-modified"}
    )
    pin_requirements_ok = (
        baseline_state == "baseline-verified"
        and manifest.get("baseline_pin_matches") is True
        and not manifest.get("differences_from_pin")
        if effective_pin_mode == PIN_MODE_STRICT
        else baseline_state in allowed_states
        and (baseline_state == "baseline-verified" or bool(manifest.get("differences_from_pin")))
    )
    api = _as_dict(report.get("api"))
    api_manifest = _as_dict(api.get("manifest"))
    manifests_match = bool(api_manifest) and all(
        api_manifest.get(field) == manifest.get(field)
        for field in (
            "plan_sha256",
            "canonical_sha256",
            "baseline_state",
            "schema_revision",
            "pin_mode",
        )
    )
    record_check(
        "fixture_manifest_valid",
        bool(manifest.get("valid"))
        and pin_mode_consistent
        and pin_requirements_ok
        and manifest.get("certification_eligible") is False
        and manifests_match,
        category="harness",
        observed={
            "valid": manifest.get("valid"),
            "pin_mode": effective_pin_mode,
            "pin_mode_consistent": pin_mode_consistent,
            "baseline_state": baseline_state,
            "baseline_pin_matches": manifest.get("baseline_pin_matches"),
            "schema_revision": manifest.get("schema_revision"),
            "api_manifest_matches_env": manifests_match,
        },
        threshold={
            "valid": True,
            "pin_mode": effective_pin_mode,
            "baseline_state": sorted(allowed_states),
            "certification_eligible": False,
        },
        detail="Golden COMPREHENSIVE domain/schema/count/media manifest and pin validation",
    )

    reads = _as_dict(api.get("reads"))
    expected_endpoints = set(REQUIRED_API_ENDPOINTS)
    actual_endpoints = set(reads.keys())
    missing_endpoints = sorted(expected_endpoints - actual_endpoints)
    unexpected_endpoints = sorted(actual_endpoints - expected_endpoints)
    malformed_reads = {
        path: _validate_api_entry(reads[path])
        for path in sorted(actual_endpoints & expected_endpoints)
        if _validate_api_entry(reads[path])
    }
    ced_ms = api.get("create_edit_delete_ms")
    api_complete = (
        not missing_endpoints
        and not unexpected_endpoints
        and not malformed_reads
        and _is_finite_number(ced_ms)
        and float(ced_ms) >= 0
    )
    record_check(
        "api_measurements_complete",
        api_complete,
        category="harness",
        observed={
            "endpoint_count": len(reads),
            "expected_count": len(REQUIRED_API_ENDPOINTS),
            "missing_endpoints": missing_endpoints,
            "unexpected_endpoints": unexpected_endpoints,
            "malformed": malformed_reads,
            "create_edit_delete_ms": ced_ms,
        },
        threshold={
            "endpoint_count": len(REQUIRED_API_ENDPOINTS),
            "samples_per_endpoint": 7,
            "create_edit_delete_ms": ">= 0",
        },
        detail="Complete 48-endpoint inventory with 7 samples, bytes, query counts and mutation trace",
    )

    sql_inst = _as_dict(api.get("sql_instrumentation"))
    sql_inst_active = (
        sql_inst.get("extension_installed") is True
        and "pg_stat_statements" in str(sql_inst.get("shared_preload_libraries", ""))
        and sql_inst.get("reset_executed_per_sample") is True
        and sql_inst.get("probe_query_captured") is True
        and sql_inst.get("sample_count_per_endpoint") == 7
    )
    unverified_zero_queries = [
        path
        for path, entry in reads.items()
        if isinstance(entry, dict)
        and isinstance(entry.get("queries"), list)
        and 0 in entry["queries"]
        and not (sql_inst_active and entry.get("sql_zero_queries_verified") is True)
    ]
    any_nonzero_queries = any(
        isinstance(entry, dict)
        and isinstance(entry.get("queries"), list)
        and any(_is_nonneg_int(q) and q > 0 for q in entry["queries"])
        for entry in reads.values()
    )
    record_check(
        "api_sql_instrumentation_complete",
        sql_inst_active and any_nonzero_queries and not unverified_zero_queries,
        category="harness",
        observed={
            "sql_instrumentation": sql_inst,
            "any_nonzero_queries": any_nonzero_queries,
            "unverified_zero_queries": unverified_zero_queries,
        },
        threshold={
            "extension_installed": True,
            "probe_query_captured": True,
            "zero_query_distinguished_from_uninstrumented": True,
        },
        detail="pg_stat_statements instrumentation verified active; zero-query routes require verified instrumentation",
    )

    integrity = _as_dict(api.get("fixture_integrity_after_mutation"))
    integrity_ok = (
        integrity.get("checked") is True
        and integrity.get("created_identity_deleted") is True
        and integrity.get("residual_perf_records") == 0
        and integrity.get("schema_revision") == manifest.get("schema_revision")
        and integrity.get("canonical_geographic_places")
        == manifest.get("canonical_geographic_places")
        and integrity.get("media_verified") is True
        and integrity.get("unexpected_table_deltas") == {}
    )
    record_check(
        "fixture_post_mutation_integrity_verified",
        integrity_ok,
        category="harness",
        observed=integrity,
        threshold={
            "created_identity_deleted": True,
            "residual_perf_records": 0,
            "unexpected_table_deltas": {},
            "media_verified": True,
        },
        detail="Logical fixture invariants preserved after POST/PUT/DELETE mutation trace",
    )

    transfer = _as_dict(report.get("transfer"))
    static_assets = _as_dict(transfer.get("static_assets"))
    static_ok = len(static_assets) >= 2 and all(
        isinstance(item, dict)
        and _is_nonneg_int(item.get("raw_bytes"))
        and cast(int, item.get("raw_bytes")) > 0
        and _is_nonneg_int(item.get("gzip_bytes"))
        and cast(int, item.get("gzip_bytes")) > 0
        and "accept-encoding" in str(item.get("vary", "")).lower()
        for item in static_assets.values()
    )
    record_check(
        "static_compression_and_api_integrity",
        static_ok
        and transfer.get("protected_api_compressed") is False
        and _as_dict(transfer.get("runtime_configuration")).get("compressed") is False
        and _as_dict(transfer.get("health")).get("compressed") is False,
        category="application",
        observed={
            "static_assets_checked": len(static_assets),
            "protected_api_compressed": transfer.get("protected_api_compressed"),
        },
        threshold="static gzip + Vary; runtime-config/health/authenticated API uncompressed",
    )

    browser = _as_dict(report.get("browser"))
    resources = _as_list(browser.get("resources"))
    js_chunks = [
        item
        for item in resources
        if isinstance(item, dict) and str(item.get("path", "")).endswith(".js")
    ]
    largest_chunk_bytes = max((int(item.get("bytes", 0)) for item in js_chunks), default=0)
    record_check(
        "frontend_largest_chunk_under_vite_advisory",
        bool(js_chunks) and largest_chunk_bytes <= VITE_CHUNK_ADVISORY_BYTES,
        category="application",
        observed=largest_chunk_bytes,
        threshold=VITE_CHUNK_ADVISORY_BYTES,
        detail=(
            f"largest raw JS chunk {largest_chunk_bytes} bytes (limit {VITE_CHUNK_ADVISORY_BYTES})"
        ),
    )

    workload = _as_list(browser.get("workload"))
    route_names = [item.get("name") for item in workload if isinstance(item, dict)]
    duplicate_routes = sorted(
        {name for name in route_names if isinstance(name, str) and route_names.count(name) > 1}
    )
    missing_routes = [name for name in REQUIRED_BROWSER_ROUTES if name not in route_names]
    unexpected_routes = sorted(
        {
            name
            for name in route_names
            if isinstance(name, str) and name not in REQUIRED_BROWSER_ROUTES
        }
    )
    route_by_name = {
        item["name"]: item
        for item in workload
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    malformed_routes = [
        item.get("name")
        for item in workload
        if not isinstance(item, dict)
        or not _is_finite_number(item.get("ms"))
        or float(cast(float, item.get("ms"))) < 0
        or not _is_nonneg_int(item.get("external"))
        or not _is_nonneg_int(item.get("maps"))
        or not (isinstance(item.get("requests"), list) or _is_nonneg_int(item.get("request_count")))
    ]
    initial = _as_dict(browser.get("initial"))
    initial_ms = initial.get("ms")
    maps_lifecycle_ok = (
        "provenance" in route_by_name
        and int(route_by_name["provenance"].get("maps", 0)) >= 1
        and "occurrence" in route_by_name
        and int(route_by_name["occurrence"].get("maps", 0)) >= 1
        and "dashboard" in route_by_name
        and int(route_by_name["dashboard"].get("maps", -1)) == 0
    )
    record_check(
        "browser_workload_complete",
        _is_finite_number(initial_ms)
        and float(initial_ms) >= 0
        and isinstance(initial.get("resources"), list)
        and bool(initial.get("resources"))
        and not missing_routes
        and not duplicate_routes
        and not unexpected_routes
        and not malformed_routes
        and maps_lifecycle_ok,
        category="harness",
        observed={
            "route_count": len(workload),
            "missing_routes": missing_routes,
            "duplicate_routes": duplicate_routes,
            "unexpected_routes": unexpected_routes,
            "malformed_routes": malformed_routes,
            "maps_lifecycle_ok": maps_lifecycle_ok,
        },
        threshold={
            "route_count": len(REQUIRED_BROWSER_ROUTES),
            "unique_routes": True,
            "maps_lifecycle": {"provenance": ">=1", "occurrence": ">=1", "dashboard": 0},
        },
    )

    browser_errors = browser.get("errors")
    record_check(
        "browser_zero_errors",
        isinstance(browser_errors, list) and len(browser_errors) == 0,
        category="application",
        observed=browser_errors,
        threshold=[],
        detail=f"browser errors: {browser_errors}" if browser_errors else "0 errors",
    )

    unexpected_external = [
        item.get("name")
        for item in workload
        if isinstance(item, dict)
        and item.get("name") != "occurrence"
        and int(item.get("external", 0)) > 0
    ]
    record_check(
        "browser_no_unrelated_external_requests",
        bool(workload) and not unexpected_external,
        category="application",
        observed=unexpected_external,
        threshold=[],
        detail=(
            f"external requests on {unexpected_external}"
            if unexpected_external
            else "0 external requests on unrelated routes"
        ),
    )

    cycles = _as_list(browser.get("cycles"))
    cycle_requests = _as_list(browser.get("cycleRequests"))
    expected_cycles = 6
    invalid_checkpoints = [i for i, c in enumerate(cycles) if not _valid_checkpoint(c)]
    final_checkpoint = browser.get("final")
    final_ok = _valid_checkpoint(final_checkpoint)
    interval_counts = [
        int((c.get("timers") or {}).get("intervals", -1)) for c in cycles if isinstance(c, dict)
    ]
    timers_constant = len(interval_counts) == expected_cycles + 1 and len(set(interval_counts)) == 1
    cycle_requests_valid = len(cycle_requests) == expected_cycles and all(
        _is_nonneg_int(r) and r > 0 for r in cycle_requests
    )
    steady_cycle_requests = cycle_requests[1:] if cycle_requests_valid else []
    requests_stable = (
        bool(steady_cycle_requests) and max(steady_cycle_requests) - min(steady_cycle_requests) <= 4
    )
    record_check(
        "browser_six_cycles_stability",
        cycle_requests_valid
        and len(cycles) == expected_cycles + 1
        and not invalid_checkpoints
        and final_ok
        and timers_constant
        and requests_stable,
        category="application",
        observed={
            "cycle_count": len(cycle_requests),
            "cycle_requests": cycle_requests,
            "interval_counts": interval_counts,
            "invalid_checkpoints": invalid_checkpoints,
            "final_checkpoint_valid": final_ok,
        },
        threshold={
            "cycles": expected_cycles,
            "maps_on_today": 0,
            "documents_on_today": 1,
            "intervals_on_today": "<= 2 and constant across cycles (Today day check + release watcher)",
            "timeouts_on_today": 0,
            "cycles_2_to_6_request_spread_max": 4,
        },
    )

    idle_seconds = browser.get("idleSeconds")
    idle_requests = browser.get("idleRequests")
    idle_samples = _as_list(browser.get("idle"))
    sample_times: list[float] = [
        float(s["at"])
        for s in idle_samples
        if isinstance(s, dict) and _is_finite_number(s.get("at"))
    ]
    times_valid = (
        len(sample_times) == len(idle_samples)
        and all(sample_times[i] <= sample_times[i + 1] for i in range(len(sample_times) - 1))
        and (len(sample_times) >= 2 and sample_times[-1] - sample_times[0] >= 115.0)
    )
    valid_idle_samples = [
        s
        for s in idle_samples
        if isinstance(s, dict)
        and isinstance(s.get("containers"), list)
        and len(s["containers"]) == 3
        and isinstance(s.get("connections"), dict)
        and _is_nonneg_int(s["connections"].get("total"))
        and _is_nonneg_int(s["connections"].get("idle"))
        and isinstance(s.get("sessions"), dict)
        and _is_nonneg_int(s["sessions"].get("count"))
        and int(s["sessions"]["count"]) >= 1
    ]
    session_snapshots = {json.dumps(s["sessions"], sort_keys=True) for s in valid_idle_samples}
    record_check(
        "browser_idle_120s_stability",
        _is_finite_number(idle_seconds)
        and float(idle_seconds) >= 120
        and isinstance(idle_requests, list)
        and len(idle_requests) == 0
        and len(idle_samples) >= 13
        and times_valid
        and len(valid_idle_samples) == len(idle_samples)
        and len(session_snapshots) == 1,
        category="application",
        observed={
            "idle_seconds": idle_seconds,
            "idle_requests_count": len(idle_requests) if isinstance(idle_requests, list) else None,
            "sample_count": len(idle_samples),
            "valid_samples": len(valid_idle_samples),
            "timestamps_valid": times_valid,
            "distinct_session_states": len(session_snapshots),
        },
        threshold={
            "idle_seconds": ">= 120",
            "idle_requests_count": 0,
            "sample_count": ">= 13",
            "idle_span_seconds": ">= 115",
            "distinct_session_states": 1,
        },
    )

    chunk_recovery = _as_dict(report.get("chunk_recovery"))
    fallback = _as_dict(chunk_recovery.get("nginx_fallback"))
    record_check(
        "lazy_chunk_recovery_verified",
        chunk_recovery.get("shell_retained") is True
        and chunk_recovery.get("automatic_reload") is False
        and chunk_recovery.get("page_errors") == []
        and fallback.get("status") == 200
        and str(fallback.get("contentType", "")).lower().startswith("text/html"),
        category="application",
        observed=chunk_recovery,
        threshold={
            "shell_retained": True,
            "automatic_reload": False,
            "page_errors": [],
            "fallback_status": 200,
        },
    )

    cleanup = _as_dict(report.get("cleanup"))
    cleanup_ok = (
        cleanup.get("containers_remaining") == 0
        and cleanup.get("networks_remaining") == 0
        and cleanup.get("volumes_remaining") == 0
        and (cleanup.get("images_remaining") in (None, 0))
        and cleanup.get("ownership_verified") is True
    )
    record_check(
        "benchmark_resource_cleanup_verified",
        cleanup_ok,
        category="harness",
        observed={
            "containers_remaining": cleanup.get("containers_remaining"),
            "networks_remaining": cleanup.get("networks_remaining"),
            "volumes_remaining": cleanup.get("volumes_remaining"),
            "images_remaining": cleanup.get("images_remaining"),
            "ownership_verified": cleanup.get("ownership_verified"),
        },
        threshold={
            "containers_remaining": 0,
            "networks_remaining": 0,
            "volumes_remaining": 0,
            "images_remaining": 0,
            "ownership_verified": True,
        },
    )

    failures = [*harness_failures, *application_failures]
    if missing_sections or (isinstance(errors, list) and errors):
        harness_status = "incomplete" if missing_sections else "failed"
    else:
        harness_status = "passed" if not harness_failures else "failed"
    application_status = "passed" if not application_failures else "failed"
    invariant_status = "passed" if not failures else "failed"
    if harness_failures and application_failures:
        failure_classification = "both"
    elif harness_failures:
        failure_classification = "harness_invalid"
    elif application_failures:
        failure_classification = "application_failure"
    else:
        failure_classification = "none"

    execution_stage = (
        "preliminary_modified_baseline_rehearsal"
        if baseline_state == "invariant-valid-baseline-modified"
        else "preliminary_source_rehearsal"
    )
    return {
        "pin_mode": effective_pin_mode,
        "execution_stage": execution_stage,
        "rc_g_perf_certification": False,
        "certification_eligible": False,
        "harness_status": harness_status,
        "application_status": application_status,
        "invariant_status": invariant_status,
        "failure_classification": failure_classification,
        "fixture_pin_status": baseline_state,
        "fixture_differences_from_pin": manifest.get("differences_from_pin", []),
        "missing_sections": missing_sections,
        "harness_failures": harness_failures,
        "application_failures": application_failures,
        "failures": failures,
        "enforced_invariants": checks,
        "operator_g_perf_thresholds": {
            "status": "unset_until_g_perf",
            "authority": "docs/release/scope-v1.md (G-PERF, decision 7)",
            "note": (
                "No runtime latency, CPU, RAM or supported collection-size pass/fail thresholds "
                "exist until the operator sets them from RC-image G-PERF measurements."
            ),
        },
    }


def summarize_report(
    report: dict[str, Any],
    *,
    full_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Produce a compact machine-readable summary with full external artifact provenance."""
    summary: dict[str, Any] = {
        "schema_version": report.get("schema_version", 2),
        "summary_format": "perf-001-comprehensive-summary-v1",
        "generated_at": report.get("generated_at"),
        "pin_mode": report.get("pin_mode"),
        "warmup_s": report.get("warmup_s"),
        "errors": list(report.get("errors") or []),
        "environment": report.get("environment"),
        "transfer": report.get("transfer"),
        "chunk_recovery": report.get("chunk_recovery"),
        "cleanup": report.get("cleanup"),
    }
    if "live_occurrence" in report:
        summary["live_occurrence"] = report["live_occurrence"]

    api = report.get("api")
    if isinstance(api, dict):
        summary["api"] = {
            "started_at": api.get("started_at"),
            "completed_at": api.get("completed_at"),
            "manifest": api.get("manifest"),
            "sql_instrumentation": api.get("sql_instrumentation"),
            "create_edit_delete_ms": api.get("create_edit_delete_ms"),
            "fixture_integrity_after_mutation": api.get("fixture_integrity_after_mutation"),
            "resources": api.get("resources"),
            "reads": api.get("reads"),
            "statements_externalized": True,
        }

    browser = report.get("browser")
    if isinstance(browser, dict):
        initial = browser.get("initial")
        compact_initial = initial
        if isinstance(initial, dict):
            compact_initial = {
                "ms": initial.get("ms"),
                "request_count": len(initial.get("requests") or []),
                "resources": initial.get("resources"),
            }
        workload_summary = [
            {
                "name": item.get("name"),
                "ms": item.get("ms"),
                "request_count": (
                    item.get("request_count")
                    if isinstance(item.get("request_count"), int)
                    else len(item.get("requests") or [])
                ),
                "external": item.get("external"),
                "maps": item.get("maps"),
            }
            for item in (browser.get("workload") or [])
            if isinstance(item, dict)
        ]
        summary["browser"] = {
            "chromium": browser.get("chromium"),
            "initial": compact_initial,
            "workload": workload_summary,
            "cycles": browser.get("cycles"),
            "cycleRequests": browser.get("cycleRequests"),
            "idleSeconds": browser.get("idleSeconds"),
            "idleRequests": browser.get("idleRequests"),
            "idle": browser.get("idle"),
            "final": browser.get("final"),
            "errors": browser.get("errors"),
            "resources": browser.get("resources"),
            "route_requests_externalized": True,
        }

    if report.get("profile_summary") is not None:
        lines = str(report["profile_summary"]).splitlines()
        summary["profile_excerpt"] = "\n".join(lines[:15])
    if isinstance(report.get("query_plans"), dict):
        summary["query_plans_summary"] = {
            key: len(value) if isinstance(value, list) else 0
            for key, value in report["query_plans"].items()
        }
    if full_artifact is not None:
        summary["full_artifact"] = full_artifact
    summary["limitations"] = [
        "Preliminary source-build rehearsal only; not formal immutable RC-image G-PERF certification.",
        "PostgreSQL data and attachment storage use tmpfs; disk durability and fsync latency are excluded.",
        "browser.mjs route ms includes a 500ms network-quiescence settle wait (time-to-quiet, not paint/render latency).",
        "browser.mjs stubs /occurrence-map/cache and tiles locally; external provider/tile latency is excluded from browser timings.",
        "Host load and concurrent agent worktrees are shared; timings are host-specific loopback HTTP numbers.",
    ]
    summary["evaluation"] = evaluate_report(summary, pin_mode=summary.get("pin_mode"))
    return summary
