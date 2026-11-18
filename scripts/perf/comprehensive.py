"""Supported Golden COMPREHENSIVE provisioning, validation and report evaluation."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
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
EXCLUDED_COUNT_TABLES = frozenset({"auth_sessions", "login_throttles"})
NOT_DOMAIN_COUNT_TABLES = frozenset({"application_settings", "users", "external_provider_cache"})

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
    allow_baseline_drift: bool = False,
) -> dict[str, Any]:
    """Validate COMPREHENSIVE identity, schema pin, entity/media counts and digests."""
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
    elif baseline_state == "invariant-valid-baseline-modified" and allow_baseline_drift:
        pin_differences.extend(verify_baseline.get("baseline_differences") or [])
        if digest.get("canonical_sha256") != baseline_pin["canonical_sha256"]:
            pin_differences.append(
                f"canonical_sha256: {digest.get('canonical_sha256')} != "
                f"reviewed {baseline_pin['canonical_sha256']}"
            )
    else:
        differences.append(f"verify-baseline state is {baseline_state!r}")
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
    return {
        "valid": True,
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
        "baseline_pin_matches": baseline_state == "baseline-verified" and not pin_differences,
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


def evaluate_report(report: dict[str, Any]) -> dict[str, Any]:
    """Evaluate completeness and enforced repository invariants transparently."""
    required_sections = ("environment", "api", "transfer", "browser", "chunk_recovery", "cleanup")
    missing_sections = [key for key in required_sections if not report.get(key)]
    checks: list[dict[str, Any]] = []
    failures: list[str] = []

    def record_check(
        name: str, passed: bool, *, observed: Any, threshold: Any, detail: str = ""
    ) -> None:
        checks.append(
            {
                "id": name,
                "passed": passed,
                "observed": observed,
                "threshold": threshold,
                "detail": detail,
            }
        )
        if not passed:
            failures.append(f"{name}: {detail or f'observed {observed!r} vs {threshold!r}'}")

    record_check(
        "required_measurement_sections_present",
        not missing_sections,
        observed=sorted(k for k in required_sections if report.get(k)),
        threshold=list(required_sections),
        detail=f"missing sections: {missing_sections}" if missing_sections else "all present",
    )

    env = report.get("environment") or {}
    manifest = env.get("manifest") or {}
    record_check(
        "fixture_manifest_valid",
        bool(manifest.get("valid"))
        and manifest.get("baseline_state")
        in {"baseline-verified", "invariant-valid-baseline-modified"},
        observed={
            "valid": manifest.get("valid"),
            "baseline_state": manifest.get("baseline_state"),
            "schema_revision": manifest.get("schema_revision"),
        },
        threshold={
            "valid": True,
            "baseline_state": ["baseline-verified", "invariant-valid-baseline-modified"],
        },
        detail="Golden COMPREHENSIVE domain/schema/count/media manifest validation",
    )

    api = report.get("api") or {}
    reads = api.get("reads") or {}
    missing_reads = [
        path
        for path, entry in reads.items()
        if not isinstance(entry, dict) or entry.get("median_ms") is None or not entry.get("queries")
    ]
    record_check(
        "api_measurements_complete",
        bool(reads) and not missing_reads and api.get("create_edit_delete_ms") is not None,
        observed={"endpoint_count": len(reads), "incomplete": missing_reads},
        threshold="all endpoints with median_ms and SQL counts",
        detail=f"incomplete endpoints: {missing_reads}" if missing_reads else "complete",
    )

    transfer = report.get("transfer") or {}
    static_assets = transfer.get("static_assets") or {}
    record_check(
        "static_compression_and_api_integrity",
        bool(static_assets)
        and transfer.get("protected_api_compressed") is False
        and (transfer.get("runtime_configuration") or {}).get("compressed") is False
        and (transfer.get("health") or {}).get("compressed") is False,
        observed={
            "static_assets_checked": len(static_assets),
            "protected_api_compressed": transfer.get("protected_api_compressed"),
        },
        threshold="static gzip + Vary; runtime-config/health/authenticated API uncompressed",
    )

    browser = report.get("browser") or {}
    resources = browser.get("resources") or []
    js_chunks = [item for item in resources if str(item.get("path", "")).endswith(".js")]
    largest_chunk_bytes = max((int(item.get("bytes", 0)) for item in js_chunks), default=0)
    record_check(
        "frontend_largest_chunk_under_vite_advisory",
        bool(js_chunks) and largest_chunk_bytes <= VITE_CHUNK_ADVISORY_BYTES,
        observed=largest_chunk_bytes,
        threshold=VITE_CHUNK_ADVISORY_BYTES,
        detail=(
            f"largest raw JS chunk {largest_chunk_bytes} bytes (limit {VITE_CHUNK_ADVISORY_BYTES})"
        ),
    )

    browser_errors = browser.get("errors")
    record_check(
        "browser_zero_errors",
        isinstance(browser_errors, list) and len(browser_errors) == 0,
        observed=browser_errors,
        threshold=[],
        detail=f"browser errors: {browser_errors}" if browser_errors else "0 errors",
    )

    workload = browser.get("workload") or []
    unexpected_external = [
        item.get("name")
        for item in workload
        if item.get("name") != "occurrence" and int(item.get("external", 0)) > 0
    ]
    record_check(
        "browser_no_unrelated_external_requests",
        bool(workload) and not unexpected_external,
        observed=unexpected_external,
        threshold=[],
        detail=(
            f"external requests on {unexpected_external}"
            if unexpected_external
            else "0 external requests on unrelated routes"
        ),
    )

    cycles = browser.get("cycles") or []
    cycle_requests = browser.get("cycleRequests") or []
    expected_cycles = 6
    leaked_maps = [i for i, c in enumerate(cycles) if int(c.get("maps", -1)) != 0]
    interval_counts = [int((c.get("timers") or {}).get("intervals", -1)) for c in cycles]
    timer_growth = [
        i
        for i, c in enumerate(cycles)
        if int((c.get("timers") or {}).get("timeouts", -1)) != 0
        or not (0 <= int((c.get("timers") or {}).get("intervals", -1)) <= 2)
    ]
    timers_constant = bool(interval_counts) and len(set(interval_counts)) == 1
    steady_cycle_requests = cycle_requests[1:]
    requests_stable = (
        bool(steady_cycle_requests) and max(steady_cycle_requests) - min(steady_cycle_requests) <= 4
    )
    record_check(
        "browser_six_cycles_stability",
        len(cycle_requests) == expected_cycles
        and len(cycles) == expected_cycles + 1
        and not leaked_maps
        and not timer_growth
        and timers_constant
        and requests_stable,
        observed={
            "cycle_count": len(cycle_requests),
            "cycle_requests": cycle_requests,
            "interval_counts": interval_counts,
            "leaked_map_checkpoints": leaked_maps,
            "unexpected_timer_checkpoints": timer_growth,
        },
        threshold={
            "cycles": expected_cycles,
            "maps_on_today": 0,
            "intervals_on_today": "<= 2 and constant across cycles (Today day check + release watcher)",
            "timeouts_on_today": 0,
            "cycles_2_to_6_request_spread_max": 4,
        },
    )

    idle_seconds = browser.get("idleSeconds")
    idle_requests = browser.get("idleRequests")
    idle_samples = browser.get("idle") or []
    session_snapshots = {
        json.dumps(s.get("sessions"), sort_keys=True) for s in idle_samples if "sessions" in s
    }
    record_check(
        "browser_idle_120s_stability",
        isinstance(idle_seconds, int | float)
        and idle_seconds >= 120
        and isinstance(idle_requests, list)
        and len(idle_requests) == 0
        and len(idle_samples) >= 13
        and len(session_snapshots) == 1,
        observed={
            "idle_seconds": idle_seconds,
            "idle_requests_count": len(idle_requests) if isinstance(idle_requests, list) else None,
            "sample_count": len(idle_samples),
            "distinct_session_states": len(session_snapshots),
        },
        threshold={
            "idle_seconds": ">= 120",
            "idle_requests_count": 0,
            "sample_count": ">= 13",
            "distinct_session_states": 1,
        },
    )

    chunk_recovery = report.get("chunk_recovery") or {}
    fallback = chunk_recovery.get("nginx_fallback") or {}
    record_check(
        "lazy_chunk_recovery_verified",
        chunk_recovery.get("shell_retained") is True
        and chunk_recovery.get("automatic_reload") is False
        and chunk_recovery.get("page_errors") == []
        and fallback.get("status") == 200
        and str(fallback.get("contentType", "")).lower().startswith("text/html"),
        observed=chunk_recovery,
        threshold={
            "shell_retained": True,
            "automatic_reload": False,
            "page_errors": [],
            "fallback_status": 200,
        },
    )

    cleanup = report.get("cleanup") or {}
    record_check(
        "benchmark_resource_cleanup_verified",
        cleanup.get("containers_remaining") == 0 and cleanup.get("networks_remaining") == 0,
        observed={
            "containers_remaining": cleanup.get("containers_remaining"),
            "networks_remaining": cleanup.get("networks_remaining"),
        },
        threshold={"containers_remaining": 0, "networks_remaining": 0},
    )

    harness_status = "passed" if not missing_sections else "incomplete"
    invariant_status = "passed" if not failures else "failed"
    return {
        "execution_stage": "preliminary_source_rehearsal",
        "rc_g_perf_certification": False,
        "harness_status": harness_status,
        "invariant_status": invariant_status,
        "fixture_pin_status": manifest.get("baseline_state"),
        "fixture_differences_from_pin": manifest.get("differences_from_pin", []),
        "missing_sections": missing_sections,
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
