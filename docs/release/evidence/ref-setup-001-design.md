# REF-SETUP-001 Design Note (Phase 1)

Branch: `feat/ref-setup-001` (from `origin/main` `b632c5c`, writer `neon-ref-setup-001`).
Target: Batch 14 (pre-`beta.10`), strictly isolated from `import_export/`, `import_wizard/`, and frontend import screens.

## 1. Open Checks

### 1.1 Live upstream behaviour (probed 2026-11-25) and download bounds

| Source | Pinned URL | Redirects | `Content-Type` | Exact size | Quirks observed today |
| --- | --- | --- | --- | --- | --- |
| WFO `2026-06` (Zenodo) | `https://zenodo.org/api/records/20782718/files/wfo_plantlist_2026-06.zip/content` | `0` (direct `200 OK`) | `application/octet-stream` **(sent twice)** | `132,643,291` B (126.5 MiB) | **1.** `Accept: application/zip` and `Accept: application/octet-stream` both return **`406 NOT ACCEPTABLE`**; must send `Accept: */*`. **2.** `GET` returns duplicate `content-type` headers (`['application/octet-stream', 'application/octet-stream']`), which `httpx` joins with `, `; must validate `headers.get_list("content-type")` entry-by-entry. |
| WCVP `v16` (Kew) | `https://sftp.kew.org/pub/data-repositories/WCVP/wcvp.zip` | `0` (direct `200 OK`) | `application/zip` (single) | `88,179,649` B (84.1 MiB) | Unversioned URL can rotate when v17 publishes; pinned SHA-256 fails closed before ZIP parsing. |

- **Redirects**: Both serve `200 OK` directly today; keep `follow_redirects=False` for both (fail closed if an upstream ever starts redirecting).
- **240 s cap on a slow line**: Does **not** hold reliably. At 240 s, WCVP needs ≥ 3.0 Mbps and WFO needs ≥ 4.5 Mbps sustained; on a 1–2 Mbps link or throttled mirror both time out.
- **Proposed bounds (both downloaders)**: `httpx.Timeout(read=60, connect=15, write=15, pool=15)` to fail fast on stalled sockets, plus an overall wall-clock cap `max_seconds=1800` (30 min, tolerates down to ~0.6 Mbps) since downloads run in the background and never block startup/health. Fast-fail if `Content-Length` mismatches exact WFO size (`132,643,291`) or exceeds WCVP `MAX_ARCHIVE_BYTES` (`100,000,000`), and enforce the byte bound while streaming.

### 1.2 Disk footprint (sequential build: WFO first, delete zip, then WCVP v16, delete zip)

| Index | Archive (deleted after publish) | Final SQLite + `.sha256` | Temp during build (staged in `state/reference/`) | Peak during build |
| --- | ---: | ---: | ---: | ---: |
| WFO `2026-06` | `126.5 MiB` (measured) | `393.9 MiB` (measured: `413,069,312` B) | `393.9 MiB` temp DB + `~150 MiB` SQLite index sort (est.) | `~670 MiB` |
| WCVP `v16` | `84.1 MiB` (measured) | `908.7 MiB` (measured: `952,799,232` B) | `908.7 MiB` temp DB + `~300 MiB` SQLite index sort (est.) | `~1.69 GiB` (incl. ready WFO) |
| **Combined steady state** | `0 MiB` | **`1.27 GiB`** (`1,365.9 MB`) | `0 MiB` | **`~1.69 GiB`** fresh (`~2.6 GiB` if replacing v16; recommend ≥ 3 GiB free) |

Setting `TMPDIR` and `SQLITE_TMPDIR` inside the staging subdir of `state/reference/` keeps `/tmp` usage at ~0 bytes (works with small `tmpfs` or `read_only: true`).

### 1.3 Build time and peak RSS (local measurement + DS224+ scaling)

- **WCVP v16 (measured locally**, `docs/review/wcvp-version-001/provisioning-v16.json`, Python 3.14.7): `208.5 s` wall (`173.7 s` user, `15.7 s` sys), peak RSS **`43.8 MiB`** (`44,872 KiB`).
- **WFO 2026-06 (estimated**; Phase 2 will measure a real-archive run): `~60–120 s` wall on this dev host (Ryzen AI 9 HX 370); peak RSS **`~120–180 MiB`** because `taxonomy/snapshot.py` loads `parents = dict(SELECT id, parent FROM concepts)` (454,688 ID pairs) + `done` set in memory for cycle validation.
- **Estimated low-end NAS (Synology DS224+, Celeron J4125, 2 GiB RAM, HDD)**: ~3–5× slower single-thread + HDD I/O → WFO `~3–8 min`, WCVP `~10–18 min`, combined download + build **`~15–30 min`** on first start. Peak RSS `~180 MiB` fits a 2 GiB NAS safely because builds run sequentially in short-lived subprocesses whose memory returns to the kernel immediately on exit.

### 1.4 Production Compose egress (ADR 0009 / ADR 0010)

- **Default `compose.yaml` (ADR 0010)**: No custom `networks:` block; all services share Docker's default bridge with outbound NAT (`backend` reaches the internet; `db` publishes no host port; `frontend` binds `127.0.0.1:8080`). **No compose network change needed.**
- **Optional hardened override (`docs/security.md`)**: `db` is exclusively on `internal: true` (zero egress); `backend` joins `[internal, app]` where `app` has outbound NAT. Both egress and `read_only: true` work unchanged because staging lives under writable `/var/lib/florabase/data/state/reference/`.

### 1.5 Process model: supervised subprocess + lightweight lifespan coordinator

- `florabase-start` runs `wait-db` → `deploy` → scrubs `FLORABASE_OWNER_*` → `exec`s `release_schema serve` → `os.execvp("uvicorn", ...)` as PID 1.
- **Design**: FastAPI `lifespan()` launches one `asyncio.Task` coordinator only when `FLORABASE_REFERENCES_SETUP=auto`. It inspects managed indexes; if all managed indexes are already valid/ready (or overridden by manual paths), the task exits immediately (**zero idle threads, timers, or processes** — honors `RUNTIME-IDLE-001`).
- For each missing/invalid managed index (sequentially: `wfo`, then `wcvp_v16`), the coordinator spawns a dedicated child subprocess (`python -m florabase.reference_setup.worker`) with `os.nice(10)` and `TMPDIR`/`SQLITE_TMPDIR` set to the staging directory inside `state/reference/`.
  - **Why subprocess over thread**: zero GIL contention on `uvicorn`, `os.nice(10)` does not throttle API serving, 100% OS memory reclamation of WFO's ~180 MiB build dict on exit, and clean `TMPDIR`/`SQLITE_TMPDIR` isolation without mutating server `os.environ`.
  - **Clean `SIGTERM`**: `uvicorn` (PID 1) runs FastAPI lifespan teardown → cancels retry sleep, sends `SIGTERM` to active worker, awaits up to 5 s, falls back to `SIGKILL` + `wait()` (no zombies). Because work stages in `.staging-*` and publishes via atomic `rename`/`os.replace` under an exclusive `fcntl.flock`, interruption never leaves a partial index; stale `.staging-*` dirs are cleaned under the lock on next run.
  - **Retry backoff**: On failure, log one sanitized line (no URLs/stack spam), keep state `failed: <short reason>`, retry with exponential backoff capped at 6 h (`15 min`, `1 h`, `6 h`, then at most every `6 h` while running; immediate retry on next container start).

### 1.6 `state/` interactions and backup/upgrade isolation

- **`postgres/florabase-postgres-entrypoint.sh`**: Validates `state/` (`10001:10001`, `0755`, non-recursive). Scans `state/*` **only** when `state/installation.env` is absent (first boot). Because provisioning runs only in `serve` (after `deploy` writes `installation.env`), `state/reference/` never exists before `installation.env`. On all subsequent starts `db` reads only `state/installation.env`. `state/reference/` is created `0700` owned by `10001:10001` (inaccessible to `db` uid `70`).
- **`backend/src/florabase/db/release_schema.py`**: Reads only `state/installation.env`, `state/installation.pending`, and `state/upgrade-failed.env`; only checks emptiness on `media/`, never `state/`. Pre-upgrade dump runs `pg_dump` only.
- **Paired backup (`docs/installation.md`, `scripts/backup.sh`, `backend/scripts/attachment_artifacts.py`)**: Archives `pg_dump` + `media/objects/` only; never reads `state/`. App exports read PostgreSQL only.

### 1.7 `wcvp_v16_require_seal` default for managed directory

- **Yes, enforce `require_seal=True` for the managed directory.** Auto-setup always writes `index.sqlite` and `index.sha256` atomically together in staging before `rename` (like `dev_references.py:setup_wcvp`). Because `state/reference/` is backend-writable rather than a root-owned `:ro` mount, mandatory seal verification detects truncation or corruption fail-closed. Manual mounts (`FLORABASE_WCVP_V16_SNAPSHOT_PATH` set outside the managed dir) preserve `settings.wcvp_v16_require_seal` (default `False`) for backward compatibility.

## 2. Two Decisions to Confirm Before Phase 2

1. **Diagnostics API surface**: `RUNTIME-IDLE-001` added container-log startup/validation diagnostics (not an HTTP diagnostics endpoint), while `GET /api/v1/system/info` (`MOBILE-002`) is **unauthenticated** (pre-login mobile compatibility check). Proposal: keep `/api/v1/system/info` unchanged and unauthenticated, add an **authenticated** read-only `GET /api/v1/system/references` returning `{mode, wfo, wcvp_v16}` (states `off | preparing | ready | failed | manual` + bounded sanitized `reason`, no paths/URLs), display it in **Settings → Data sources**, and add `References: auto|off` to the startup banner. *(Alternative: add a coarse field to `/api/v1/system/info` if preferred.)*
2. **Behaviour of `off` when managed files already exist**: Proposal: when `FLORABASE_REFERENCES_SETUP=off` and no manual path env var is set, resolve path to `None` and report `off` (100% identical to today's behaviour, zero disk/network surprises; once `ready`, `auto` already performs zero outbound requests). *(Alternative: read existing sealed managed files even when `off`.)*

## 3. Planned Phase 2 File Touch List

- **New backend package**: `backend/src/florabase/reference_setup/{__init__.py,state.py,lock.py,runner.py,worker.py}`
- **Backend changes**: `backend/src/florabase/core/config.py`, `backend/src/florabase/core/banner.py`, `backend/src/florabase/taxonomy/{snapshot.py,source.py,api.py}`, `backend/src/florabase/native_range_enrichment/{snapshot.py,source.py}`, `backend/src/florabase/botanical_identities/api.py`, `backend/src/florabase/main.py`, `backend/src/florabase/api/system.py`, `backend/openapi.json`
- **Compose & runtime contract**: `compose.yaml` (replaces line 36 comment with active `FLORABASE_REFERENCES_SETUP=auto`, keeping file at 50 lines ≤ 60-line limit), `scripts/test-beta-runtime.py`
- **Frontend**: `frontend/src/api/schema.d.ts`, `frontend/src/settings/{api.ts,DataSourcesScreen.tsx,HelpAndSources.test.tsx}`, `frontend/src/taxonomy/{TaxonomyScreen.tsx,TaxonomyScreen.test.tsx,IdentityTaxonomyPanel.tsx}`, `frontend/src/botanical-profiles/NativeRangeEnrichmentPanel.tsx`
- **Tests**: `backend/tests/test_reference_setup.py`, `backend/tests/integration/test_reference_setup.py`, targeted updates in `backend/tests/{test_taxonomy.py,test_native_range_enrichment.py,test_release_schema.py,test_system_info.py}`
- **Docs & metadata**: `docs/installation.md`, `docs/dev-references.md`, `docs/security/beta-distribution-001/sqlite-reference-indexes.md`, `CHANGELOG.md`, `docs/features.json` (next to WFO/WCVP entries), `docs/release/scope-v1.json` (`"best-effort"`), `docs/progress.md`, `docs/release/evidence/ref-setup-001.md` *(no `docs/user-guide*` exists on `main` at `b632c5c`)*
