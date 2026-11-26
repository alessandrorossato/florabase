# REF-SETUP-001 Evidence — Automatic Background Reference Provisioning

Branch: `feat/ref-setup-001` (from `origin/main` `b632c5c`, writer `neon-ref-setup-001`).
Design note: [ref-setup-001-design.md](ref-setup-001-design.md).

## Summary of Implemented Behaviour

- **Opt-in automatic setup (`FLORABASE_REFERENCES_SETUP=auto`):** Backend defaults to `off` when
  unset. The shipped [`compose.yaml`](../../../compose.yaml) enables
  `- FLORABASE_REFERENCES_SETUP=auto` explicitly (keeping the file at 50 lines, within ADR 0009's
  budget and `scripts/test-beta-runtime.py`'s 60-line check). Existing installs without the line
  remain `off` until the operator adds it (documented in
  [`docs/installation.md`](../../installation.md) and [`CHANGELOG.md`](../../../CHANGELOG.md)).
- **Non-blocking supervised worker:** FastAPI `lifespan()` launches one
  `ReferenceSetupCoordinator` task only when `auto` is enabled and at least one managed index is
  not yet ready. Each missing index (`wfo`, then `wcvp_v16`) builds sequentially in a dedicated
  `os.nice(10)` subprocess (`florabase.reference_setup.worker`) with `TMPDIR` and `SQLITE_TMPDIR`
  pointed at a staging directory inside `/var/lib/florabase/data/state/reference/` (`0700`,
  backend-owned). On `SIGTERM`, lifespan teardown terminates the child subprocess cleanly and
  leaves zero partial files. Once all managed indexes are ready, the coordinator exits with zero
  idle tasks or timers.
- **Shared pinned downloader and builders:** `core/reference_index.py::download_archive()`
  centralizes streaming HTTP validation (`follow_redirects=False`, configurable `max_seconds=1800`
  wall-clock cap, `connect=10 s`, `read=60 s`, `Content-Length` fast-fail, streaming byte cap,
  duplicate `content-type` header validation via `get_list("content-type")` for Zenodo, and
  `Accept: */*` for Zenodo WFO to avoid `406 NOT ACCEPTABLE`). Both `taxonomy/snapshot.py` and
  `native_range_enrichment/snapshot.py` reuse it; SHA-256 checksums are verified before ZIP
  parsing, downloaded archives are deleted after publish, and valid sealed indexes are never
  overwritten or deleted.
- **Locking, disk pre-check, retries, and `off` / `manual` semantics:**
  - Exclusive inter-process `fcntl.flock` lock (`state/reference/.reference-setup.lock`) held by the
    worker for the whole build; stale `.staging-*` directories are cleaned on start under the lock.
  - Free-space pre-check (`(archive + expected_index) * 1.2`) runs before each download; shortage
    fails closed with `failed: disk` without touching the network.
  - Failures log one sanitized line per index (`network`, `checksum`, `size`, `build`, or `disk`)
    with no URLs or stack spam, and retry on next start or at most once every 6 hours while running.
  - When `off`, zero outbound requests are made; pre-existing valid sealed managed indexes remain
    usable and report `ready (setup off)` while missing ones report `off`.
  - Manual paths configured via `FLORABASE_WFO_SNAPSHOT_PATH` / `FLORABASE_WCVP_V16_SNAPSHOT_PATH`
    are skipped by auto-setup, never written, and reported as `manual`. Managed WCVP v16 enforces
    `require_seal=True` unconditionally.
- **Read-only diagnostics & UI:** `GET /api/v1/system/info` stays unchanged and unauthenticated.
  New authenticated read-only `GET /api/v1/system/references` (`SystemReferencesResponse`,
  `ReferenceSetupIndexStatus`, `Cache-Control: no-store`) feeds a compact read-only **Reference
  index status** section in **Settings → Data sources** (no start-now button). Taxonomy and
  native-range screens indicate when reference data is being prepared in the background.
- **Backups & upgrades:** `state/reference/` lives outside `media/objects/` and PostgreSQL, is
  created only during `serve` (after `deploy` writes `state/installation.env`), and is verified
  ignored by `attachment_artifacts.py` and `release_schema.py`.

## Real-Archive End-to-End Run (2026-11-25)

Executed `python -m florabase.reference_setup.worker` against the live pinned official archives
(Zenodo WFO `2026-06` and Kew WCVP `v16`) into a disposable directory inside the Quality backend
container (Ryzen AI 9 HX 370 host, tmpfs `/tmp`, cleaned up automatically):

| Index | Archive bytes | Wall time (dl + build) | User / Sys CPU | Peak RSS | Final SQLite bytes | Probe (`Solanum lycopersicum`) |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| WFO `2026-06` | `132,643,291` (126.5 MiB) | `126.78 s` | `28.06 s / 1.57 s` | `170,436 KiB` (166.4 MiB) | `413,069,312` (393.9 MiB) | `wfo-0001029217` (sealed) |
| WCVP `v16` | `88,179,649` (84.1 MiB) | `87.90 s` | `34.98 s / 1.90 s` | `68,836 KiB` (67.2 MiB) | `952,799,232` (908.7 MiB) | `2932342` (sealed, `require_seal=True`) |

- Managed directory mode verified: `0o700`; leftover `.staging-*` directories: `[]`.
- Combined steady-state footprint: `1,365,868,544` B (`1.27 GiB`); recommended free space ≥ `3 GiB`.
- Estimated low-end NAS (Synology DS224+, Celeron J4125, 2 GiB RAM, HDD): `~15–30 min` total on
  first start; sequential subprocess exit reclaims the `166 MiB` WFO build heap immediately.

## Verification & Batch 14 Compatibility

- **Focused backend unit tests (`backend/tests/test_reference_setup.py`):** 17 tests covering
  settings/mode resolution, `off` + existing sealed indexes (`ready (setup off)`), managed WCVP
  v16 mandatory seal, Zenodo `Accept: */*` + duplicate `content-type` headers, redirect/size/
  content-type/timeout/checksum rejection, `0700` dir & symlink refusal, inter-process `fcntl`
  lock contention, stale `.staging-*` cleanup, free-space pre-check (`failed: disk`, zero network),
  atomic staging & non-overwrite of valid sealed indexes, real subprocess `SIGTERM` clean stop
  with zero partial publish, coordinator retry & single-line sanitized warning log, standalone
  module import-cycle checks, authenticated `GET /api/v1/system/references` vs unchanged
  `GET /api/v1/system/info`, and backup/deploy isolation of `state/reference/`.
- **PostgreSQL integration tests (`backend/tests/integration/test_reference_setup.py`):** 3 tests
  using a local `127.0.0.1` HTTP fixture server (zero external network): fresh `auto` end-to-end
  to `ready` with live WFO/WCVP API lookups, `off` mode with zero network + reuse of sealed
  managed indexes (`ready (setup off)`), and offline `failed: network` + healthy app + untouched
  read-only `0555` manual mount (`manual`).
- **Frontend tests:** `HelpAndSources.test.tsx`, `TaxonomyScreen.test.tsx`, and
  `NativeRangeEnrichmentPanel.test.tsx` (34 tests passed), verifying read-only **Reference index
  status** badges (no action buttons) and background-preparing messages.
- **Compose contract (`scripts/test-beta-runtime.py`):** 17/17 tests passed.
- **Batch 14 `git merge-tree` against `feat/import-002-sheet-wizard` (`7dcbfd8`):**
  - Clean auto-merge on all code, `backend/openapi.json`, `frontend/src/api/schema.d.ts`,
    `docs/features.json`, and `docs/release/scope-v1.json`.
  - Sole expected conflict: `docs/progress.md` (both branches insert a new top milestone below
    `# Engineering progress`, handled automatically by `feature_batch.py`'s `additive_progress()`
    from `WF-BATCH-PROGRESS-001`).
- **Canonical gate:** `make feature-verify AGENT_ID=neon-ref-setup-001` run on the frozen
  committed tree.
- **Visual diagnostics note:** Screenshot capture for Settings → Data sources is not committed per
  repository policy (`AGENTS.md`); attach to PR or review in Feature Review / UAT.
