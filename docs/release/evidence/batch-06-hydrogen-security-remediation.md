# Batch 06 — Hydrogen security remediation evidence (BETA-SECURITY-001 / G-SEC)

Branch `fix/batch-06-security-remediation`, writer `hydrogen-batch06-security-remediation` (claim `ceef322df8ea`), pinned base `main` `c555baabe916e3fea1ef2c8f834c747ced5aa926`.
Implementation source commit: `347bc9b8c4d6f5cba4d0b7f78c7daba38d97d807` (tree `4339452ee59f80f8fd60700caef4b5008bdce59c`).

## Scope and baseline defect

In the Batch 06 baseline on clean `main` (`c555baabe916e3fea1ef2c8f834c747ced5aa926`), Sol built the production runtime images and observed that unauthenticated backend-direct `GET` and `HEAD` requests to FastAPI's four generated documentation and schema routes returned HTTP `200`:

- `GET` / `HEAD` `/docs` (Swagger UI)
- `GET` / `HEAD` `/redoc` (ReDoc)
- `GET` / `HEAD` `/docs/oauth2-redirect` (Swagger OAuth redirect)
- `GET` / `HEAD` `/openapi.json` (OpenAPI JSON)

Under the G-SEC route allowlist ([`docs/release/scope-v1.md`](../scope-v1.md)), only sign-in (`POST /api/v1/auth/login`), health (`GET /api/v1/health`), and readiness (`GET /api/v1/ready`) may be callable without authentication. While production nginx served the SPA shell on those four paths, the backend service itself exposed them inside the internal network.

Sol additionally identified mutable GitHub Actions major-tag references (`actions/checkout@v6` and `actions/upload-artifact@v7`) in [`.github/workflows/ci.yml`](../../../.github/workflows/ci.yml), whose `push` to `main` jobs authorize protected publication via `scripts/beta-release-checks.py`.

## Implemented remediation (`347bc9b8c4d6f5cba4d0b7f78c7daba38d97d807`)

Four authorized files were modified in the implementation commit:

1. **Production FastAPI documentation-route closure ([`backend/src/florabase/main.py`](../../../backend/src/florabase/main.py#L23-L33)):**
   `create_app()` derives `expose_docs = settings.environment is not Environment.PRODUCTION` and passes `openapi_url="/openapi.json" if expose_docs else None`, `docs_url="/docs" if expose_docs else None`, and `redoc_url="/redoc" if expose_docs else None` to `FastAPI(...)`. No new public endpoints were introduced, and `AuthSafetyMiddleware`, `CORSMiddleware`, and `api_router` remain unchanged.
2. **Backend infrastructure and G-SEC tests ([`backend/tests/test_infrastructure.py`](../../../backend/tests/test_infrastructure.py#L379-L530)):**
   Added five tests covering:
   - `test_production_disables_docs_and_schema_routes`: verifies with real `FLORABASE_ENVIRONMENT=production` env vars and `get_settings.cache_clear()` that all four routes are absent from `production_app.routes` and return `404` for both `GET` and `HEAD`.
   - `test_development_preserves_docs_and_schema_routes`: verifies with `FLORABASE_ENVIRONMENT=development` and `get_settings.cache_clear()` that all four routes remain `200` for both `GET` and `HEAD`, and `/openapi.json` returns valid OpenAPI JSON.
   - `test_offline_openapi_generation_works_in_production_and_matches_artifact`: verifies `production_app.openapi()` generates the identical schema to `app.openapi()` and matches `backend/openapi.json` (`backend/scripts/export_openapi.py` format).
   - `test_production_route_inventory_satisfies_gsec_allowlist`: enumerates all leaf routes via `iter_route_contexts(production_app.routes)`, confirms zero non-`APIRoute` routes exist, and verifies the unauthenticated operation set is exactly `{("GET", "/api/v1/health"), ("GET", "/api/v1/ready"), ("POST", "/api/v1/auth/login")}`.
   - `test_production_public_and_authenticated_api_routes_remain_intact`: verifies `GET /api/v1/health` (`200`), `GET /api/v1/ready` (`200`), unauthenticated `GET /api/v1/auth/session` (`401`), invalid `POST /api/v1/auth/login` (`401`), and authenticated `GET /api/v1/auth/session` (`200`).
3. **CI action commit SHA pinning ([`.github/workflows/ci.yml`](../../../.github/workflows/ci.yml#L29-L114)):**
   Replaced the four `actions/checkout@v6` references with `actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6` and the four `actions/upload-artifact@v7` references with `actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7`, preserving all jobs (`quality`, `integration`, `build`, `release-migration`), triggers, permissions, and artifact uploads without modifying release workflows.
4. **CI workflow pinning regression ([`scripts/test-beta-images.py`](../../../scripts/test-beta-images.py#L1412-L1431)):**
   Added `test_trusted_ci_workflow_pins_actions_to_full_commit_shas`, asserting all eight `uses:` entries in `.github/workflows/ci.yml` use 40-hex commit SHAs (`4` checkout, `4` upload-artifact) and preserving the four required job names.

## Production GET/HEAD probe results (before vs. after)

Rebuilt production `backend` and `frontend` runtime targets plus `postgres/` from `347bc9b8c4d6f5cba4d0b7f78c7daba38d97d807` in an isolated internal Docker network (zero host-published ports, `Environment.PRODUCTION`, secure cookies, HTTPS canonical origin, empty CORS list, `alembic upgrade head` at `20261110_0047`, bootstrapped synthetic owner):

| Request (unauthenticated unless noted) | Before (`c555baa`, backend-direct) | After (`347bc9b`, backend-direct) | After (`347bc9b`, production nginx ingress) |
| --- | --- | --- | --- |
| `GET /docs` | `200` (Swagger UI) | `404` (`application/json`, `22` bytes) | `200` (SPA index, matches `/` byte-for-byte) |
| `HEAD /docs` | `200` (`0` bytes) | `404` (`application/json`, `0` bytes) | `200` (`text/html`, `0` bytes) |
| `GET /redoc` | `200` (ReDoc) | `404` (`application/json`, `22` bytes) | `200` (SPA index, matches `/` byte-for-byte) |
| `HEAD /redoc` | `200` (`0` bytes) | `404` (`application/json`, `0` bytes) | `200` (`text/html`, `0` bytes) |
| `GET /docs/oauth2-redirect` | `200` (OAuth redirect) | `404` (`application/json`, `22` bytes) | `200` (SPA index, matches `/` byte-for-byte) |
| `HEAD /docs/oauth2-redirect` | `200` (`0` bytes) | `404` (`application/json`, `0` bytes) | `200` (`text/html`, `0` bytes) |
| `GET /openapi.json` | `200` (OpenAPI JSON) | `404` (`application/json`, `22` bytes) | `200` (SPA index, matches `/` byte-for-byte) |
| `HEAD /openapi.json` | `200` (`0` bytes) | `404` (`application/json`, `0` bytes) | `200` (`text/html`, `0` bytes) |
| `GET /healthz` | N/A | N/A | `200` (`ok`) |
| `GET /api/v1/health` | `200` | `200` (`15` bytes) | `200` (`15` bytes) |
| `GET /api/v1/ready` | `200` | `200` (`15` bytes) | `200` (`15` bytes) |
| `GET /api/v1/auth/session` | `401` | `401` (`36` bytes) | `401` (`36` bytes) |
| `GET /api/v1/plants` | — | `401` (`36` bytes) | `401` (`36` bytes) |
| `POST /api/v1/auth/login` (invalid credentials) | `401` | `401` | `401` |
| `POST /api/v1/auth/login` (valid owner) | — | `200` (`has_csrf: true`) | `200` (`has_csrf: true`) |
| `GET /api/v1/auth/session` (authenticated) | — | `200` (`owner: true`) | `200` (`owner: true`) |
| `GET /api/v1/plants` (authenticated) | — | `200` | `200` |

Inside the rebuilt production `backend` image under `FLORABASE_ENVIRONMENT=production`, offline `app.openapi()` returned `{"openapi": "3.1.0", "paths": 168, "routes": 1}`.

## Focused verification and artifact-smoke results (`347bc9b8c4d6f5cba4d0b7f78c7daba38d97d807`)

- `ruff check .` (backend): passed.
- `ruff format --check .` (backend): `435 files already formatted`.
- `mypy` (backend): `Success: no issues found in 382 source files`.
- `pytest -m "not integration"` (backend): `1231 passed, 3 skipped, 861 deselected`, `90.18%` coverage (including all 20 tests in `backend/tests/test_infrastructure.py`, `test_health.py`, `test_readiness.py`, `test_auth_api.py`, `test_auth_security.py`, `test_config.py`).
- `./scripts/check-api-generated.sh`: passed (`export_openapi.py --check` and `openapi-typescript --check` with zero drift).
- `FLORABASE_RELEASE_OFFLINE=1 python3 ./scripts/release-tools.py ./scripts/test-beta-images.py`: `Ran 61 tests in 11.065s` — `OK`.
- `make workflow-check AGENT_ID=hydrogen-batch06-security-remediation`: passed (`test-dependabot-policy`, `test-beta-images` 61 OK, `test-release-tools-lock` 4 OK, `test-beta-runtime` 63 tests on Python `3.14.4` and 51 tests on Python `3.8.20`, Ruff check/format and strict mypy over all workflow scripts).
- Production artifact build & official artifact-only smoke (`scripts/smoke-beta-images.py`): `BETA_IMAGE_SMOKE_PASSED distribution=local-candidate`.
- Disposable resource cleanup: `RESOURCE_CLEANUP_PASSED` across all temporary smoke and build projects (`0` residual containers, networks, volumes, or tagged smoke images).

## Independent source QA and retained artifacts

- Sol independently reviewed the implementation commit `347bc9b8c4d6f5cba4d0b7f78c7daba38d97d807` across all four authorized paths and returned `PASS`.
- Sol's baseline and scope authorization records live on branch `docs/batch-06-security-evidence` (`docs/release/evidence/batch-06-security-baseline.md` and `docs/release/evidence/batch-06-remediation-scope.md`).
- Hydrogen's runtime probe output and artifact-smoke logs for `347bc9b8c4d6f5cba4d0b7f78c7daba38d97d807` are retained outside Git in the Antigravity session scratch directory `batch06_verify/` (`prod-stack-evidence.json`, `artifact-smoke.log`, `remediation-handoff.json`, `candidate.json`).
- This additive documentation commit awaits independent review of the updated branch tip before WF-04 batch registration.

## Remaining security risks and deferred decisions

- **Non-gate second-scanner (`anchore/grype:v0.121.1`) findings (documented, deferred from this increment):**
  - `libcrypto3` and `libssl3` `3.5.9-r0` (4 HIGH: `CVE-2026-107496`, `CVE-2026-88823`, `CVE-2026-95691`, `CVE-2026-95692`; 1 MEDIUM: `CVE-2026-88822`) across backend, frontend, and PostgreSQL images: no Alpine 3.24 fix available; runtime paths (`CMS_encrypt`, AES-GCM-SIV, OpenSSL QUIC client) are unused.
  - `python 3.14.10` (`CVE-2026-119170`, HIGH, fixed in `3.14.11`): OpenSSL FIPS-mode `hashlib` regression; verified `FIPS_mode: 0` (`EVP_default_properties_is_fips_enabled(None) == 0`) in the base image.
  - `sqlite-libs 3.53.4-r0` (4 HIGH, 6 MEDIUM): no Alpine 3.24 fix; mitigated by [`open_reference_index`](../../../backend/src/florabase/core/reference_index.py) ([`sqlite-reference-indexes.md`](../../security/beta-distribution-001/sqlite-reference-indexes.md)).
  - `busybox` / `busybox-binsh` / `ssl_client` `1.37.0-r31` (`CVE-2025-60876`, MEDIUM): no Alpine 3.24 fix.
- **Deferred Python MEDIUM findings:** `Mako 1.4.1` (`CVE-2026-102991` → `1.4.2`) and `opentelemetry-api 1.45.1` (`CVE-2026-126360` → `1.45.2`) in `backend/requirements.lock`, below the `HIGH,CRITICAL` release gate and excluded from Batch 06 remediation scope.
- **PostgreSQL maintenance & release operations:** Switching installed systems from published `.1` (`v0.1.0-beta.5`) to pinned `.2` (`18.6-alpine-florabase.2`) requires separate operator-approved PostgreSQL maintenance with a paired backup/restore rehearsal ([`postgresql-image.md`](../../security/beta-distribution-001/postgresql-image.md)). GitHub Release immutability and any VEX or advisory disposition remain operator decisions.

## Pending acceptance statement

Final G-SEC acceptance (including final release-candidate digest scans, second-host port probe, ENG-01/ENG-02 verification, and protected GHCR attestations), canonical FULL verification, WF-04 integration, and release-candidate (`v0.1.0-beta.6` / RC) publication acceptance remain **pending**.
