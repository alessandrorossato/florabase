# Dependency-maintenance baseline — 2026-10-11

This closes the maintenance sweep before DASHBOARD-001. The sweep started from
`bc84fa403d09d2ac1f0012ecc43b8ddb0f32d7e7` after PR #86; this final isolated
pip-tools increment starts from `d31d6681bc7bf2f050608786ed6d75f6d22e9e52`
(PR #98). CI-003 / PR #85 is present. No product work or new schema migration is
included, and DASHBOARD-001 remains planned.

## Delivered groups before closure

Each group used a new branch from the preceding merged main, canonical FULL
verification, an exact-tree receipt, protected quality/integration/build checks,
repository delivery and repository feature-finish. Their GitHub merge identities
and successful protected checks were refreshed during closure; their maintenance
changes were not repeated.

| Group | Versions before → after | PR | Reviewed commit | Merge commit |
| --- | --- | --- | --- | --- |
| Frontend lint/format | ESLint 10.9.1 → 10.12.0; typescript-eslint 8.68.0 → 8.71.1; refresh plugin 0.5.5 → 0.5.7; Prettier 3.9.6 → 3.9.9 | [#88](https://github.com/alessandrorossato/florabase/pull/88) | `5a37084664d7b69952db4f4372cde7213a7449ac` | `1299d0cd973839c156e348c7b3bf14d264c85c79` |
| Vite toolchain | Vite 8.2.2 → 8.3.4; plugin-react 6.1.0 → 6.1.2 | [#90](https://github.com/alessandrorossato/florabase/pull/90) | `2abd7ca942583953e1f1ecddc9695b5fbfa86576` | `9594b7157cd0f93a46d9249693d9d76f94cea77a` |
| Backend tooling | mypy 2.3.1 → 2.4.0; Ruff 0.16.5 → 0.17.0 | [#92](https://github.com/alessandrorossato/florabase/pull/92) | `5dc0976f4cf7be9bc026b53698b3ddeed7ce02c8` | `a16172c88855fdac60ac006c1bd7861b4853b210` |
| PostgreSQL driver | psycopg/binary 3.3.4 → 3.3.6 | [#94](https://github.com/alessandrorossato/florabase/pull/94) | `eddffd0ee78445ba52afeb996547198584f1ab2b` | `106d2a622e77885eb71afcd1fc04e8b4c9841d9a` |
| Framework/server | FastAPI 0.141.1 → 0.143.0; Uvicorn 0.52.4 → 0.54.0 | [#96](https://github.com/alessandrorossato/florabase/pull/96) | `a2a2535feb522fd0be8ce0c54c270194ec11d3d2` | `48e9c4d4f5b3ba6aa6c21a51e8ee188460e098e8` |
| ORM/migrations | SQLAlchemy 2.0.52 → 2.0.54; Alembic 1.19.1 → 1.20.0 | [#98](https://github.com/alessandrorossato/florabase/pull/98) | `10a074ad50b450859d31f99c24a1d653bda5f122` | `d31d6681bc7bf2f050608786ed6d75f6d22e9e52` |

The recorded canonical suites were 910 backend, 557 frontend (57 files), and 711
PostgreSQL tests for #88–#96; #98 included 713 PostgreSQL tests after adding two
named-CHECK autogenerate regressions. All groups included workflow/static checks,
API drift, production backend/frontend builds, forced complete migration-cycle
verification and scoped disposable cleanup. Migration head stays `20261009_0041`.
No DEV migration upgrade is required.

## Final isolated pip-tools increment

Only `pip-tools==7.6.1 → 7.6.2` changes in the backend development dependencies.
The release was uploaded 2026-10-07, exceeding the 24-hour age policy. Upstream
supports Python 3.14; the actual Quality container runs Python 3.14.7,
pip-tools 7.6.2 and Click 8.5.0, with `pip check` clean.

[pip-tools 7.6.2 release notes](https://pip-tools.readthedocs.io/en/stable/changelog/)
identify Click 8.5 compatibility and incorrectly recorded `--no-index` command
headers as patch fixes relevant to this repository.

Both backend locks were regenerated through the existing Quality Compose
`pip-compile --strip-extras` workflow, using a writable temporary compiler cache
and an explicit backend workspace mount. Regeneration was repeated with the new
compiler and both SHA-256 checks matched byte-for-byte. Production lock pins are
identical to the base; the development lock changes only pip-tools. Both generated
command headers now correctly omit `--no-index`, which was never passed. No
transitive package, runtime dependency, application source or lint policy changed.

CI-003 automatically selects **FULL** for `backend/pyproject.toml`,
`backend/requirements.lock` and `backend/requirements-dev.lock`; migration mode is
`full-cycle`, both production builds and all backend/frontend/PostgreSQL/workflow
suites are selected. This baseline is accepted for delivery only after canonical
`make feature-verify` produces its exact-tree receipt and repository delivery
passes protected quality/integration/build checks. The Git commit and PR carrying
this record provide the final closure delivery identity.

## Deferred decisions

### SQLAlchemy 2.1

**SQLALCHEMY_2_1_DEFERRED.** The 2.1.4 trial produced 51 production typing
errors across 12 files (56 including new test diagnostics). Variadic Select/Row
and query-result typing require broader migration than this maintenance scope.
SQLAlchemy 2.0.54 was independently delivered instead. Reconsider 2.1 in a
separate typed-query and unconditional-autoflush/transaction review with complete
PostgreSQL concurrency verification; do not weaken mypy to force adoption.
See the [SQLAlchemy migration guide](https://docs.sqlalchemy.org/en/21/changelog/migration_21.html).

Alembic 1.20.0 was accepted with an equivalent online/offline registration of
`alembic.ext.checkconstraint_byname`, preserving the named-CHECK detection policy
from 1.19.1. Two disposable PostgreSQL tests detect adding/removing a named CHECK;
both fail without that plugin and pass with it. No autogenerate migration was
applied. Existing model/migration metadata differences and legacy configuration
warnings still require manual migration review; they are not hidden by this update.
See the [Alembic changelog](https://alembic.sqlalchemy.org/en/latest/changelog.html).

### jsdom

**JSDOM_DEFERRED_NODE_CONTRACT.** Latest reviewed 30.1.2 requires
`^22.22.2 || ^24.15.0 || >=26.0.0`, which excludes part of the declared
`>=24 <25` support range. Keep 30.0.1; do not silently narrow Node support.
The existing 30.0.1 engine has the same floor, while the actual 24.19.0 image
satisfies it. Reconsider when a supported release fully covers the declared
contract or a separate explicit platform decision resolves that existing mismatch.
Registry metadata was refreshed during closure.

### React 19.3

**REACT_19_3_DEFERRED_BROWSER_VERIFICATION.** Keep React/DOM 19.2.8,
@types/react 19.2.18 and @types/react-dom 19.2.5. The uncommitted 19.3.0 candidate
was reviewed and only its two dependency files restored to the current main;
no candidate remains.

Candidate focused evidence included frozen install, format/lint/strict TypeScript,
96 tests in App, lazy/transition, provenance-map screen and Schedule suites, and
frontend compilation. The profile clear test correctly activates Uses & warnings
before clearing the field and required no repair. This was insufficient browser
runtime evidence: map screen tests mock the map implementation. Existing
`scripts/perf/browser.mjs` and `verify-chunk-recovery.mjs` are benchmark/navigation
and chunk-recovery automation targeting the separate benchmark fixture; they do
not prove representative create/edit, profile clear/focus and Schedule flows.
Existing UAT automation proves boot/authentication/persistence, not those browser
interactions. No heavy browser framework was introduced and no protected benchmark
environment was repurposed. Reconsider when a repository-owned reproducible
acceptance path proves those flows, a real Leaflet interaction and no runtime
exceptions, followed by canonical FULL verification and protected CI.

### Node declarations

Node 26 types remain inappropriate for the Node 24 runtime contract.
@types/node stays 24.13.3. Reconsider only with an explicit runtime/platform upgrade.

## Bot proposals

Original #46 and #68 were already closed and remain closed. Re-read #24 before
closing its Node 26 proposal; re-read #91 before closing its React/types/jsdom
proposal with the explicit deferrals above. Re-read #99 before closing its grouped
SQLAlchemy 2.1.4/pip-tools proposal: SQLAlchemy remains deliberately deferred and
pip-tools is reproduced independently here. None of these branches was merged,
rebased or rewritten, and no bot PR comments were added. Newly generated routine
proposals should be classified as future maintenance rather than reopening this
completed scope unless necessary to preserve this baseline.

## Final dependency/runtime contract

| Component | Pin or contract |
| --- | --- |
| Node image / frontend engine | 24.19.0 / `>=24 <25` |
| pnpm / TypeScript | 11.19.0 / 5.9.3 |
| React / React DOM | 19.2.8 / 19.2.8 |
| React / DOM declarations | 19.2.18 / 19.2.5 |
| Vite / plugin-react | 8.3.4 / 6.1.2 |
| ESLint / typescript-eslint | 10.12.0 / 8.71.1 |
| react-refresh / Prettier | 0.5.7 / 3.9.9 |
| jsdom / Node declarations | 30.0.1 / 24.13.3 |
| Leaflet declarations / user-event | 1.9.22 / 14.6.7 (PR #86) |
| Python image / supported Python | 3.14.7 / `>=3.12,<3.15` |
| FastAPI / Uvicorn | 0.143.0 / 0.54.0 |
| SQLAlchemy / Alembic | 2.0.54 / 1.20.0 |
| psycopg / binary | 3.3.6 / 3.3.6 |
| PostgreSQL | 18.6-alpine |
| mypy / Ruff / pip-tools | 2.4.0 / 0.17.0 / 7.6.2 |

Framework-required OpenTelemetry API is not an adopted telemetry feature: no SDK
or exporter extras were installed and automatic instrumentation stays disabled.
Production Uvicorn still uses `--no-server-header --no-proxy-headers`.

## Lifecycle and next work

All cleanup uses CI-003 positive ownership. Protected DEV, Review, persistent UAT,
Stable Preview, production and unrelated workloads are preserved; historical unknown
resources and shared builder cache are retained. Host restarts during earlier
interruptions prevent a claim that pre-restart container start timestamps remained
unchanged; closure compares protected identities/mounts against its own fresh
snapshot. Primary main is updated only by authorized `make feature-finish` after
`DELIVERY_COMPLETE`, then checked clean and equal to origin/main. No new worktree
or manual primary fast-forward is used.

The next product increment is **DASHBOARD-001**. It has not been started here.
