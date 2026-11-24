# Engineering progress

## 2026-11-24 — IMPORT-002 single-sheet CSV/XLSX import wizard (backend pass)

- On `feat/import-002-sheet-wizard` from `origin/main` `ddf5a14` (writer `neon`); backend-only pass
  while waiting for `ci/batch-12` and `feat/mobile-002-device-auth` to land on `main` before the
  frontend wizard pass (which will reuse batch 12's `WfoNameInput`).
- Narrow refactor of `backend/src/florabase/import_export/service.py`: extracted
  `build_rows(kind, sources, refs)` from `preview(...)` and added optional `PendingReference`
  support (`pending=None` default) on `References` so preview can validate collection rows against
  not-yet-created identities, suppliers, and locations while keeping IMPORT-001 byte-identical.
- Added `backend/src/florabase/import_wizard/` (`sheet.py`, `mapping.py`, `schemas.py`,
  `service.py`, `api.py`), mounted from `import_export/api.py` under `/api/v1/sheet-imports/*`
  (`inspect`, `preview`, `apply`; `operation_id`s `inspectSheetImport`, `previewSheetImport`,
  `applySheetImport`) to avoid route collision with `/api/v1/imports/{kind}/*`.
  - Pinned `openpyxl==3.1.5` (MIT, pulls `et-xmlfile==2.0.0`, MIT) in `backend/pyproject.toml` and
    regenerated `backend/requirements.lock` and `backend/requirements-dev.lock`.
  - Enforced 2 MiB upload, 2,000 nonblank rows, 60 columns, one sheet, header row 1–10, 30 MiB
    uncompressed zip budget, 100:1 compression ratio, bounded `<!DOCTYPE`/`<!ENTITY` rejection,
    `read_only=True`/`data_only=True` cached-value-only parsing, and a bounded `data_only=False`
    second pass to flag uncached formulas as invalid if mapped and ignore them if unmapped.
  - Added EN/IT header auto-suggestions (`quantity_value` omitted for Plants), optional
    `append_unmapped_to_notes`, grouped identity/location/supplier review with near-match
    suggestions and explicit `skip` visibility ("will be left empty"), 15-minute session-bound
    HMAC-SHA256 confirmation, and single-transaction apply that creates identities → suppliers →
    locations, rebuilds `References` from the DB to re-run `build_rows`, and rolls back with `409`
    on any conflict or row-outcome drift.
- Copied synthetic fixtures from `import-samples.zip` as-is into `backend/tests/fixtures/sheet/`,
  added unit (`backend/tests/test_import_wizard.py`) and PostgreSQL integration tests
  (`backend/tests/integration/test_import_wizard_api.py`), regenerated `backend/openapi.json` and
  `frontend/src/api/schema.d.ts`, mapped `import_wizard/` and `fixtures/sheet/` in
  `scripts/verification-impact.json`, extended `docs/import-export.md`, and registered `IMPORT-002`
  (`in_progress` in `docs/features.json`, `best-effort` in `docs/release/scope-v1.json`, both right
  after `IMPORT-001`).
- Backend review fixes (`M1`, `M2`):
  - **M1 (confirmed preview state digest)**: added `preview_state_digest(plan)` over per-group
    `(key, action, matched_id)` for identities, locations, and suppliers plus `row_count` and
    per-row outcomes; bound it inside the HMAC confirmation token (`issued.preview_digest.sig`)
    and verified it inside `apply_sheet` before creating any entity (returning `409` `"validate
    again"` with zero writes when e.g. a Location with the same path is created between preview
    and apply).
  - **M2 (formatted blank XLSX rows)**: raised `MAX_SCANNED_ROWS` to `200_000`, enforced
    `MAX_ROWS` strictly on nonblank rows, stopped storing trailing/empty rows during CSV/XLSX
    scanning, and bounded the `data_only=False` formula pass by `last_nonblank_row` (verified on
    a 2-data-row XLSX with a formatted empty cell at `A50000`).
- Checks passed: `make check` (`doc-links` 364 docs, `format-check` 447 backend + Prettier, `lint`
  Ruff + ESLint, `typecheck` strict mypy 392 files + tsc, `api-check` zero drift, `test-backend`
  1356 passed / 3 skipped / 90.55% coverage, `test-frontend` 133 files / 1437 passed),
  re-verified after M1/M2 fixes with `ruff format --check`, `ruff check`, strict `mypy` (392
  files), `make api-check`, focused unit suite (`test_import_export.py`, `test_import_export_api.py`,
  `test_import_wizard.py`: 51 passed), and `./scripts/test-integration.sh` on
  `test_import_export_api.py` + `test_import_wizard_api.py` (20 passed), plus earlier
  `scripts/test_check_api_routes.py` (27 passed), `make license-check` (PyPI + 290 npm packages,
  0 forbidden), `scripts/check-features.py` (181 valid), and `scripts/test-verification-impact.py`
  (46 OK). Not yet run: frontend wizard UI (pending batch 12 + `MOBILE-002` merge into this branch)
  and final canonical FULL `make feature-verify`.

## 2026-11-23 — MOBILE-001 Capacitor Android shell spike (PWA preserved)

- On `feat/mobile-001-capacitor-spike` from `origin/main` `68e9449` (writer `neon-mobile-001`).
- Added Capacitor 8 Android shell under `mobile/` (`@capacitor/{core,android,cli}@8.6.2`,
  `@capacitor/preferences@8.0.1`, `@capacitor/app@8.1.2`, `pnpm@11.19.0`, Node `24.x`, Android
  platform only, `com.google.gms:google-services` removed for F-Droid cleanliness) consuming
  `../frontend/dist` with zero backend, auth, CORS, CSP, or PWA changes.
- Added runtime native detection (`frontend/src/mobile/runtime.ts`, reading Capacitor's injected
  `window.Capacitor.isNativePlatform()` with zero `@capacitor/*` imports in `frontend/package.json`
  or the web bundle) and gated `frontend/src/main.tsx` so native builds skip
  `registerServiceWorker()` and `<UpdateNotice />` and lazy-load `NativeServerOnboarding`
  (web entry delta: `+584 B` raw / `+194 B` gzip; `index-*.css` `+0 B`; `/sw.js` preserved).
- Added native Server URL onboarding (`frontend/src/mobile/`): `https://` required in release,
  `http://10.0.2.2` and private LAN allowed only in debug builds, `GET /api/v1/health` + optional
  `/release.json` probe via native `CapacitorHttp`, URL persistence via Capacitor Preferences,
  distinct error states (invalid URL, unreachable, TLS CA, cleartext, non-Florabase), and the
  `MOBILE-002` sign-in placeholder.
- Added `mobile/android/app/src/main/res/xml/network_security_config.xml` (release: no cleartext,
  trusts `system` + `user` CAs) and `src/debug/res/xml/network_security_config.xml` (debug local
  HTTP overlay), root and Android `.gitignore` rules for APKs/keystores/Gradle/`local.properties`,
  and `make mobile-sync` / `make mobile-android-debug` targets in `Makefile`.
- Classified `mobile/` and `frontend/src/mobile/` under non-FULL, non-golden `mobile` scope in
  `scripts/verification-impact.json` with regressions in `scripts/test-verification-impact.py`,
  permitted the standard `10.0.2.2` emulator loopback alias in `scripts/test-beta-runtime.py`,
  documented setup and architecture in [docs/mobile.md](mobile.md) and
  [docs/mobile-001-adr.md](mobile-001-adr.md), and registered `MOBILE-001` (`implemented`,
  proposed release class `post-1.0`) in `docs/features.json` and `docs/release/scope-v1.json`.
- Verified `make mobile-android-debug` (`app-debug.apk`, 6.5 MB) and live Android 16 AOSP emulator
  (`florabase_api36`): zero service-worker registrations, distinct invalid/unreachable/non-Florabase
  errors, `http://10.0.2.2:5173` `/api/v1/health` OK, Preferences persistence across force-stop
  restart, and observed WebView `fetch` / `Origin` / `SameSite=Strict` / CORS login blockers.
  Canonical `make feature-verify AGENT_ID=neon-mobile-001` runs on the frozen committed tree.

## 2026-11-23 — Lower idle container CPU, probe log filter, startup banner, and settings error diagnostics (`RUNTIME-IDLE-001`)

- On `feat/runtime-idle-001` (rebased onto `1d4e0ba`, writer `antigravity`).
- Replaced the Python `/api/v1/ready` backend image `HEALTHCHECK` with busybox `wget` against
  `/api/v1/health` (`--interval=30s --timeout=5s --start-period=60s --start-interval=2s --retries=3`),
  moved `postgres/Dockerfile` (`18.6-alpine-florabase.5`, reproducible index
  `sha256:8397c577...`, platform `sha256:8b9e1108...`) and `frontend/Dockerfile` to 30 s intervals
  with `--start-interval`, keeping `compose.yaml` and `compose.dev.yaml` untouched (ADR 0009) and
  `/api/v1/ready` unchanged. Verified `moby/moby` `v24.0.2` ignores unknown `StartInterval` in OCI
  image configs (`image.NewFromJSON` uses `encoding/json.Unmarshal`).
- Added `HealthProbeAccessFilter` on `uvicorn.access` (drops loopback 2xx `GET /api/v1/health` and
  `/api/v1/ready` only), plain-ASCII ≤ 72-column startup banner as the first stdout output of
  `release_schema wait-db` (`FLORABASE_REVISION` exposed from `ARG REVISION`), and
  `pydantic.ValidationError` field-name reporting across all `release_schema` actions without
  leaking input values, context, URLs, or secrets.
- Measured on disposable `compose.yaml` stack (120 s idle cgroup CPU delta, before vs after):
  `backend` 3,970.01 ms (3.31%) → 398.88 ms (0.33%, −90.0%), `db` 1,172.29 ms (0.98%) → 341.43 ms
  (0.28%, −70.9%), `frontend` 425.58 ms (0.35%) → 138.13 ms (0.12%, −67.5%); backend idle access
  logs 12 → 0; single backend probe wall time (10 runs) 340.70 ms → 63.11 ms median (−81.5%).
- Checks: `beta_release.py postgres-identity --check` (`POSTGRES_IDENTITY_REPRODUCED`),
  `make smoke-beta-images` (`LOCAL_BETA_CANDIDATE_PASSED`), `scripts/smoke-portable-compose.py`
  passed, `make feature-verify AGENT_ID=antigravity` (FULL). Unresolved: none.

## 2026-11-23 — WF-CLEANUP-001 finish auto-retirement, Golden closure and review residue

- On `ci/wf-cleanup-001` from `origin/main` `c4ffd63` (writer `neon`).
- **Auto-retirement on finish & batch finish:** Factored `retire_path()`, `is_managed_worktree()`,
  `retire_finished_worktree()` and `retire-finished --path <abs>` out of `retire()` in
  `scripts/feature_worktree.py` so `scripts/feature-finish.sh` (from the primary checkout via final
  `exec`) and `scripts/feature_batch.py finish()` reuse every retirement guard (operator identity,
  managed marker directly under `florabase-worktrees/`, locks, finish proof, clean/ignored checks,
  Docker resource and running-mount guards, mountinfo/symlink/permission preflight, non-forced
  `git worktree remove`). Managed worktrees auto-retire best-effort (`WORKTREE: RETIRED <path>` /
  `FINISHED <branch> at <tip>; RETIRED <path>`); any refusal or `KEEP_WORKTREE=1` retains the
  worktree with exit code 0, exact reason and follow-up command (`WORKTREE: RETAINED <path>
  (<reason>)`). Provider-managed worktrees are never touched. Updated `Makefile` (`KEEP_WORKTREE`
  export + help), `AGENTS.md`, `docs/development-workflow.md`, `scripts/test-agent-workflow.py`,
  and `scripts/test-workflow-helpers.sh`.
- **Agent post-delivery guidance:** Documented the 3-step post-delivery worktree removal rule for
  provider-managed worktrees in `AGENTS.md`, `docs/development-workflow.md`, and
  [agent-prompt-template.md](agent-prompt-template.md).
- **Verification impact & Golden closure:** Added `backend/alembic.ini`, `backend/scripts/` and
  `postgres/` to `golden_prefixes` and classified `backend/scripts/check_api_routes.py` and
  `backend/scripts/test_check_api_routes.py` under `product_backend_prefixes` (product tier backend
  ALL + `golden-dataset`, no FULL escalation) in `scripts/verification-impact.json`, with focused
  regressions in `scripts/test-verification-impact.py`.
- **No `assert` in container smoke snippets:** Replaced `assert` checks inside container Python
  snippets in `scripts/smoke-beta-images.py` (dev-tool check, now naming offending packages via
  `sys.exit`) and `scripts/smoke-uat-preview.py` (relationship/photo checks via `RuntimeError`) and
  in the `scripts/test-beta-images.py` fake-checker fixture, with an offline `python -O` regression
  in `scripts/test-beta-images.py`.
- **Batch 11 P3 notes, L5 closure & operator dispositions (2026-11-22):**
  - Promoted `INSTALL-003` to `verified` in `docs/features.json` (normalized multi-line
    `dependencies`, citing [wf-04-batch-11.md](release/evidence/wf-04-batch-11.md)) and updated the
    stale UI-REVIEW-001 gate-rerun pointer below.
  - Closed L5 review residue: verified `scripts/beta_release.py` `compose_template()` binds the
    tracked `compose.yaml` by SHA-256 in the `compose_template` field of the attested
    `release-manifest.json` (`release/manifest.schema.json`, `.github/workflows/beta-images.yml`),
    and appended the resolution note to the historical INSTALL-001 residual below.
  - Applied operator dispositions (option (a), 2026-11-22): `BETA-RUNTIME-001` moved to
    `implemented` / `record` (`docs/features.json`, `docs/release/scope-v1.json`,
    `docs/release/feature-reconciliation-v1.md`) with its real-host persistence, paired
    backup/restore, HTTPS/origin/CSRF and failure-recovery gates folded into `BETA-ACCEPTANCE-001`
    (retaining `BETA-RUNTIME-001` in `dependencies`); `ENG-03` confirmed `best-effort` across
    `docs/release/feature-reconciliation-v1.md`, `docs/release/scope-v1.md` and
    `docs/release/scope-v1-handoff.md`.
  - Registered `WF-CLEANUP-001` (`implemented`, proposed release class `tooling`) in
    `docs/features.json` and `docs/release/scope-v1.json`.
- Focused checks before canonical FULL: `test-agent-workflow.py` (80 OK, 3 skipped),
  `test-workflow-helpers.sh` (pass), `test-feature-workflow.py` (55 OK),
  `test-verification-impact.py` (45 OK), `test-stage-evidence.py` (22 OK),
  `test-check-features.py` (26 OK), `workflow-check` (82 `test-beta-images` + 4 lock + 16
  `test-beta-runtime` + Dependabot policy + Ruff + strict mypy across 49 scripts),
  `check-features.py` (177 valid; `--release-candidate` blockers unchanged: `RELEASE-001`,
  `BETA-IMAGE-001`, `beta-postgres-repro-001`, `BETA-SECURITY-001`, `BETA-DATA-001`,
  `BETA-ACCEPTANCE-001`), `check-doc-links.py` (357 docs), and `test-doc-links.py` (4 OK).
  Canonical FULL (`make feature-verify AGENT_ID=neon`) runs on this frozen committed head before
  operator delivery; no push, PR or merge.

## 2026-11-23 — DOCS-002 root community docs, licensing notices and docs/ tidy-up

- Implemented on `docs/docs-001` from `origin/main` `c4ffd63` (`v0.1.0-beta.8`, writer
  `neon-docs-001`). Note: `DOCS-001` already existed as a verified baseline entry in
  `docs/features.json`, so this increment uses the next free identifier `DOCS-002` (proposed
  release class `best-effort` in `docs/release/scope-v1.json`).
- **Part A (root community & licensing docs)**: rewrote `README.md` "What works today" around the
  UI navigation names from `frontend/src/shell/navigation.ts`, folded the Docker Compose merge
  rules link into Requirements, shortened self-hosting to point to `docs/installation.md`, updated
  visibility wording to "public pre-release (beta) series" (verified public repo and public GHCR
  manifests), and added copyright (`Alessandro Rossato`), `THIRD-PARTY-NOTICES.md` and
  `docs/README.md` links. Updated `CONTRIBUTING.md` with an external-contributor section
  (issue-first, focused PRs, AGPL-3.0-or-later inbound=outbound, DCO `git commit -s`, respectful
  conduct without a separate CoC, `SECURITY.md`) above the preserved maintainer/agent workflow,
  added a DCO checkbox to `.github/pull_request_template.md`, updated `SECURITY.md` supported
  versions for the latest published beta while retaining the 1.x row and GitHub private reporting,
  added `Alessandro Rossato` author metadata to `backend/pyproject.toml` and
  `frontend/package.json` without editing `LICENSE` or beta.8 version surfaces, and added root
  `THIRD-PARTY-NOTICES.md` from committed notices and `DataSourcesScreen.tsx`.
- **Part B (`docs/` structure & links)**: added [`docs/README.md`](README.md) indexing living
  guides and marking `docs/review/` and `docs/release/evidence/` as historical evidence; moved 72
  finished (`implemented`/`verified`) increment artefacts via `git mv` into
  `docs/archive/<FEATURE-ID>/` (preserving all living guides, `in_progress`/`planned` feature docs,
  and all script/code-referenced paths); updated 367 relative Markdown links plus
  `docs/features.json`; split `docs/progress.md` verbatim at `v0.1.0-beta.7` into
  [`docs/archive/progress-until-beta-7.md`](archive/progress-until-beta-7.md) (redacting one
  pre-existing personal home path flagged by `test-beta-runtime.py`); documented ongoing placement
  and no-committed-review-screenshot conventions in `AGENTS.md` and `docs/development-workflow.md`;
  wired `doc-links` (`scripts/check-doc-links.py`) into `make check`.
- **Part C (cheap doc-only verification & licence audit)**: moved `LICENSE` from `full_prefixes` to
  `documentation_paths` alongside `SECURITY.md`, `CHANGELOG.md`, and `THIRD-PARTY-NOTICES.md` in
  `scripts/verification-impact.json`, updated `scripts/test-verification-impact.py`, and added
  local `make license-check` (`scripts/license_check.py`, `scripts/license_check_npm.mjs`; no CI
  job). Full move inventory and operator TODOs are in
  [`docs/archive/DOCS-002/docs-002-handoff.md`](archive/DOCS-002/docs-002-handoff.md).
- Checks: `python3 scripts/check-doc-links.py` (360 documents), `python3 scripts/test-doc-links.py`
  (4 OK), `python3 scripts/check-features.py` (177 valid), `python3 scripts/test-check-features.py`
  (26 OK), `python3 scripts/test-verification-impact.py` (43 OK), `make test-agent-workflow` (76 OK,
  3 skipped), `make license-check` (PyPI 53 packages, npm 290 packages, 0 forbidden), followed by
  canonical `make feature-verify AGENT_ID=neon-docs-001` (FULL).

## 2026-11-22 — v0.1.0-beta.8 release preparation

- Version surfaces move to `0.1.0-beta.8` (`release/inputs.json`, backend package and module,
  frontend package, both Dockerfiles, OpenAPI `info.version`). The Unreleased CHANGELOG section
  becomes the `v0.1.0-beta.8` entry: minimal `:latest` three-service `compose.yaml` (#214, #216),
  `LINEAGE-004` and `UI-REVIEW-001`, and a note that a Compose-manager update pulls the current
  `:latest` images including rebuilt `florabase-postgres` images within PostgreSQL 18.
  PostgreSQL moves to `18.6-alpine-florabase.4`, published for the first time by this release.
  `docs/beta-data-001.md` names beta.8 and the backend deploy step instead of the removed
  `migrate` service.
- No feature status changes. Tag, protected publication and publication evidence remain operator
  actions.

## 2026-11-22 — WF-04 Batch 11 integration (`INSTALL-003` + `UI-REVIEW-001` / `LINEAGE-004`)

- Prepared `ci/batch-11` on top of pinned `origin/main` (`ef5451f`, includes #215) with writer
  `neon` via `make feature-batch-plan` and `make feature-batch-prepare`.
- Merged `INSTALL-003` (`feat/install-003-latest-compose` at `ac93677`, merge `fae46af`) and
  `UI-REVIEW-001` with `LINEAGE-004` (`fix/ui-ux-review` at `27ece94`, merge `76b0479`) without
  rewriting source branches. `README.md`, `docs/features.json` and `docs/release/scope-v1.json`
  merged cleanly keeping all 176 features; `docs/progress.md` resolved additively and was
  reconciled newest-first (`INSTALL-003`, `UI-REVIEW-001`, `LINEAGE-004` above `VERIFY-SPEED-001`,
  retaining `1e985f1`'s tail UAT smoke milestone).
- Recorded [Batch 11 provenance](release/evidence/wf-04-batch-11.md) and
  [batch-11.json](release/evidence/batches/batch-11.json). Proposed release classes in
  `docs/release/scope-v1.json`: `INSTALL-003` (`release-work`), `UI-REVIEW-001` (`best-effort`),
  `LINEAGE-004` (`best-effort`).
- Exact-head independent batch QA (`make feature-batch-review`) and one fresh canonical FULL gate
  (`env -u REUSE FRESH=1 make feature-verify AGENT_ID=neon`) run on this frozen committed head
  before operator delivery.

## 2026-11-22 — INSTALL-003 directly usable `:latest` `compose.yaml` (ADR 0010)

- On `feat/install-003-latest-compose` from `16ccf4b` (writer `antigravity-install-003`).
- Adopted [ADR 0010](decisions/0010-deployable-latest-compose.md) amending
  [ADR 0009](decisions/0009-minimal-production-compose.md): `compose.yaml` on `main` is now a
  directly usable 40-line file referencing `:latest` images
  (`ghcr.io/alessandrorossato/florabase-{postgres,backend,frontend}:latest`), plain short bind
  mounts with Synology-style absolute host path examples, plain environment literals (no `.env` or
  Compose interpolation), header folder-setup instructions, and no custom networks (`internal: true`
  and `app` moved to the optional hardened override in [docs/security.md](security.md)).
- Added `change-me` placeholder password refusal in both
  `postgres/florabase-postgres-entrypoint.sh` (reproduced `18.6-alpine-florabase.4` at
  `index_digest` `sha256:2d843bd2ac7e9cebc4b4aaed2d24bb6f7717261fa27e798fe1f28583e853d625`,
  `platform_digest` `sha256:c677e9e20e56d6c32c2d359f66b44b66e2ead27d51fcaa64528f78a88299589d`) and
  `backend/src/florabase/db/release_schema.py`.
- Removed `FLORABASE_DATA_DIR` / `FLORABASE_BACKUP_DIR` env vars from `compose.yaml`; added
  `/proc/self/mountinfo` identical/nested bind-mount detection in `release_schema.py` (including
  btrfs subvolumes, warning and continuing on indeterminate mountinfo and refusing on positive
  detection).
- Updated `scripts/beta_release.py`, `scripts/publish-beta-images.py` and
  `.github/workflows/beta-images.yml`: dropped `render_compose()` and the rendered `compose.yaml`
  release asset/attestation (keeping OCI image + `release-manifest.json` attestations), and added
  `:latest` promotion alongside versioned tags with a code-enforced PostgreSQL 18 major guard.
- Updated `docs/installation.md`, `docs/security.md`, `README.md`, `CHANGELOG.md`,
  `docs/security/beta-distribution-001/postgresql-image.md`, `docs/features.json` (`INSTALL-003`
  `implemented`) and `docs/release/scope-v1.json` (`INSTALL-003` proposed class `release-work`).
- Checks passed: `make format-check lint typecheck test-backend` (1300 passed, 90.18% coverage),
  `make workflow-check` (81+4 release tests, 16 beta-runtime tests, ruff/format/strict mypy),
  `python3 scripts/test-environment-workflow.py` (44 OK), `python3 scripts/check-features.py`,
  `python3 scripts/beta_release.py check --publication`,
  `python3 scripts/beta_release.py postgres-identity --check` (`POSTGRES_IDENTITY_REPRODUCED`), and
  live disposable `scripts/smoke-portable-compose.py` against `compose.yaml`. Not run: full
  `make feature-verify` (not yet committed/pushed per operator Phase 2 instructions).

## 2026-11-22 — UI-REVIEW-001 operator UI/UX review (with LINEAGE-004 merged)

- On `fix/ui-ux-review` from `1e985f1` (writer `claude-ui-review`); LINEAGE-004 (`77b8b54`) merged in
  at the operator's request so one FULL and one delivery cover both. Bugs and visual alignment only.
- Harvests/Stored material use the Cuttings record-type switch (`.directory-surfaces`) under the
  search in both views. One List/Gallery toggle and one Agenda/Calendar toggle name the view they open.
- Workbench: Saved views are sub-items of their owning section (five, then "Show all"), with a
  hover/focus remove control confirmed in a dialog (`DELETE /api/v1/saved-views/{id}`); the separate
  panel group and the Today "all views" list are gone. `sectionOfHash` is shared with `workspaceOfHash`.
- Journal/History/Schedule headers follow the directory grammar; Schedule month is one compact row of
  controls with viewport-sized cells and 24px pointer targets (44px kept for touch).
- Taxonomy: absolutely positioned sr-only text escaped the review list and grew the document by
  ~2,500px; the list now contains it. Gallery plates no longer centre inside stretched card buttons.
- Maps: Collection origins and Species distribution use the Native ranges metric cards; Online basemap
  is shown only when `mapOnlineEnabled` is set (Species distribution previously ignored the flag).
- Themes: the Field Ledger system (fonts, radii, controls) applies to every palette; Field Ledger is
  labelled Botanical, the old Botanical palette is retired (stored choice falls back), Herbarium and
  Mineral gain rail and lineage colours (contrast-tested). Settings and identity lineage gain breadcrumbs.
- Later rounds: Cuttings rows use the shared Details/Edit actions (`?action=edit` opens the edit
  dialog); Explore titles equal their menu entries (Taxonomy, Collection origins, Species
  distribution, Native ranges, Places); Taxonomy uses one List/Tree toggle with icons and an inline
  stage; Lineage home shows metric cards and an identity gallery on a dotted stage; record lineage
  cards share one grammar; Settings adds **Help** (built from the navigation) and a static **Data
  sources** page (current references, access rules, planned integration standard).
- README: `docs/assets/readme-showcase.png` mosaic (desktop and phone) from the Feature Review dataset with demo names and WFO links applied only to that disposable Review database.
- Record ancestry (`#/lineage/<kind>/<id>`) now belongs to Explore → Lineage with breadcrumbs; record pages keep their Lineage tab and link there. The record-type switch is a `DirectoryTools` `surfaces` slot directly under the toolbar.
- Checks: frontend typecheck, ESLint, Prettier and the full Vitest suite (128 files, 1419 tests) in the
  Review container; browser review on Feature Review at 1440×900, 768 and 375, light and dark.
  Canonical gate: `make feature-verify` (tier full, after merging `origin/main` at `16ccf4b`) passed
  all stages, including quality, production builds, migration cycle and integration (1324.6s).
  Two earlier attempts failed for environmental reasons: WCVP/WFO indexes copied into this
  worktree's ignored `backend/src/.source-cache/` for the Review screenshots made
  `test_missing_v16_keeps_v15_link_current_without_silent_fallback` see a real v16 index (cache
  removed), and `PlantScreen.test.tsx` "detail loading, detail failure, authorization, and session
  expiry" failed once under full-suite load but passes in isolation and on rerun (possible flake).
- Independent QA (read-only, detached `3c55bdc`): no P0/P1. Fixed every P2: focus returns to the
  owning section link after a saved-view removal and an expired session shows an error; Cuttings
  `?action=edit` no longer opens editing for reversed attempts and is cleared on close; the Taxonomy
  tree scroller also contains sr-only text; the Lineage gallery shows counts with " · " (no implied
  ancestry), uses `display_label` for cultivars and handles 401; Data sources describes all GBIF
  online requests and WCVP CC BY 3.0. P3: remove-button hover specificity, one `aria-current` per
  view, compact "+N more" in the Schedule month, occurrence tile guard and basemap copy, palette test
  names plus an explicit retired-Botanical fallback test, docs (lineage routes, page inventory nav),
  refreshed README showcase. Canonical gate rerun after these fixes was the Batch 11 FULL recorded
  in the Batch 11 milestone above and [wf-04-batch-11.md](release/evidence/wf-04-batch-11.md).
  UI-REVIEW-001 and LINEAGE-004 are marked verified. Release class proposed for the operator for
  UI-REVIEW-001: `best-effort`.

## 2026-11-22 — LINEAGE-004 identity lineage in Explore

- On `feat/lineage-004` from `1e985f1` (writer `claude-lineage004`). Reuses the LINEAGE-003 explorer.
- Backend: `GET /api/v1/lineage/identities/{identity_id}/graph` (`getIdentityLineageGraph`) returns
  one BotanicalIdentity's records (Sowings and rooting attempts through their own source lot) with
  only explicit edges from the explorer's source columns; linked records of other identities are
  flagged `in_identity=false`; bounded at 500 with `truncated`, never presenting a left-out member as
  foreign; 404 `botanical_identity_not_found`. No schema change.
- Frontend: Explore → **Lineage** (`#/lineage`) searches identities, Seed lots, Sowings, Plants and
  Plant groups via `/api/v1/search`; `#/lineage/identity/<id>` draws one stem per recorded line,
  with outside-identity cards, references for multi-parent records and a separate list of records
  without recorded relationships. The identity overview links to it. New `lineage` icon and section.
- Checks (cloud session, outside Docker: the quality images cannot fetch dependencies through the
  session proxy): ruff check/format and strict mypy clean; backend unit suite 1281 passed with
  coverage 90.15% (3 failures are root/host-path environment tests, unrelated); PostgreSQL 16
  integration `test_lineage_api.py` 14 passed; frontend tsc, ESLint and Prettier clean; lineage and
  navigation tests pass; the remaining 46 frontend failures are identical on `origin/main` under the
  session's Node 22 (the project pins Node 24). OpenAPI regenerated with the locked dependencies.
  Visual check of both pages at desktop and phone width, no horizontal overflow.
- Not run: FULL `make feature-verify`, `make api-check` (both need the Docker quality stack).
  Release class proposed for the operator: `best-effort`.

## 2026-11-22 — VERIFY-SPEED-001 canonical FULL wall-time optimization

- On `ci/verify-speed-001` from `origin/main` `16ccf4b` (writer `neon`).
- Split `backend/tests/integration/test_golden_dataset.py` out of the default integration run using
  the same explicit-selection fixture as `test_golden_comprehensive.py` (`SEARCH_PATH =
  "test_golden_dataset"`), preserving `test_the_full_suite_skips_the_comprehensive_module` and
  adding `test_the_full_suite_skips_the_golden_dataset_module` and updating the stale default-CI
  comment in `test_comprehensive_does_not_touch_the_smoke_plan`. Added validated `golden_prefixes`
  to `scripts/verification-impact.json` covering the full Golden import and runtime closure
  (`backend/src/florabase/`, `backend/alembic/`, `backend/pyproject.toml`, `backend/requirements`,
  `backend/uv.lock`, `backend/Dockerfile`, `compose.dev.yaml`, `Makefile`,
  `scripts/test-integration.sh`, Golden/fixture scripts, and integration test fixtures),
  `golden_dataset` selection (closure-triggered or fail-closed on unclassified paths) in
  `scripts/verification_impact.py`, the non-reusable `golden-dataset` stage
  (`make golden-dataset-check`) in `scripts/verification_gate.py`, and exhaustive `main` push CI
  coverage in `scripts/ci-verify.py`.
- Enabled Vitest file parallelism in `frontend/vite.config.ts` (`fileParallelism: true`,
  `pool: "forks"`, `maxWorkers` defaulting to `3` via `VITEST_MAX_WORKERS`, keeping `testTimeout:
  15_000`) and lifted the pinned `VITEST_MAX_WORKERS: "1"` in `scripts/compose_stacks.py` to
  `"${VITEST_MAX_WORKERS:-3}"`. Five consecutive `make test-frontend` runs passed (127 files,
  1,414 tests each, zero retries): `96.84 s`, `98.33 s`, `96.01 s`, `96.12 s`, `96.43 s` (down
  from `~258 s` serial locally).
- Consolidated `workflow-check` in `Makefile` from 7 separate backend container runs into one
  container invocation with shared file-list Make variables, run-all failure reporting, and a
  worktree-owned disposable mypy cache under `<git-dir>/florabase-mypy-workflow-cache` (verified
  host-UID owned, zero root-owned files; `33.06 s` before -> `27.16 s` cold / `23.73 s` warm).
- Hygiene: removed retired `deploy/` from `full_prefixes`, added manual `make smoke-beta-lifecycle`
  and documented `scripts/test-beta-lifecycle.py` in `docs/beta-image-001-final-reliability.md`,
  profiled all 22 tests in `scripts/test-stage-evidence.py` (`110.26 s` total; fixtures retained
  unchanged to preserve subprocess/Git coverage), and recorded the two-lane gate design note in
  [VERIFY-SPEED-001](archive/VERIFY-SPEED-001/verify-speed-001.md) without implementing parallel lanes.
- Registered `VERIFY-SPEED-001` (`implemented`, proposed release class `tooling`) in
  `docs/features.json` and `docs/release/scope-v1.json`.
- Focused checks before canonical FULL: `test-verification-impact.py` (43 OK),
  `test-stage-evidence.py` (22 OK, 110.26 s), `test-check-features.py` (26 OK),
  `test-feature-workflow.py` (55 OK), `test-environment-workflow.py` (44 OK),
  `make golden-dataset-check` (35 passed in 349.73 s), `make test-frontend` ×5 (5/5 passed),
  `make workflow-check` (cold + warm pass), `check-features.py`, `check-doc-links.py`, and
  `test-doc-links.py`. Canonical FULL (`env -u REUSE FRESH=1 make feature-verify AGENT_ID=neon`)
  runs on this frozen committed tree; no push, PR or merge.

## 2026-11-22 — WF-04 Batch 10 integration (`WF-SCOPE-001` + `INSTALL-002`)

- Prepared `ci/batch-10` on top of pinned `origin/main` (`1e985f1`) with writer `neon` via
  `make feature-batch-plan` and `make feature-batch-prepare`.
- Linear bootstrap commit `b51e2b3` updated `additive_progress` in `scripts/feature_batch.py` (with
  regression coverage in `scripts/test-agent-workflow.py`) so pure top-of-file progress prepends
  preserve non-conflicting tail edits on `main` (such as PR #213's `1e985f1` entry) while staying
  fail-closed on edits inside existing progress content.
- Merged `INSTALL-002` (`feat/install-002-minimal-compose` at `a012f43`, including `internal: true`
  and `app` network isolation in `compose.yaml`, `scripts/test-beta-runtime.py`,
  `scripts/test-beta-images.py`, `scripts/smoke-portable-compose.py`, ADR 0009 and
  `docs/security.md`, merge `b150388`) and `WF-SCOPE-001` (`feat/wf-scope-001-scoped-verification`
  at `1b78a04`, merge `b34ab43`) without rewriting source branches. `docs/features.json` and
  `docs/release/scope-v1.json` merged cleanly; `docs/progress.md` resolved additively keeping all
  entries newest-first alongside `1e985f1`'s tail milestone.
- Recorded [Batch 10 provenance](release/evidence/wf-04-batch-10.md) and
  [batch-10.json](release/evidence/batches/batch-10.json). Proposed release classes in
  `docs/release/scope-v1.json`: `WF-SCOPE-001` (`tooling`), `INSTALL-002` (`release-work`).
- Exact-head independent review (`make feature-batch-review`) and one fresh canonical FULL gate
  (`env -u REUSE FRESH=1 make feature-verify AGENT_ID=neon`) run on this frozen committed head
  before operator delivery.

## 2026-11-22 — INSTALL-002 minimal three-service production `compose.yaml` (ADR 0009)

- On `feat/install-002-minimal-compose` from `c5f9cdf` (writer `neon`).
- Adopted [ADR 0009](decisions/0009-minimal-production-compose.md) amending
  [ADR 0008](decisions/0008-self-initializing-single-compose.md), shrinking production
  `compose.yaml` from 188 lines to 49 lines with three non-root services (`db`, `backend`,
  `frontend`), fixed `container_name` (`florabase-db`, `florabase-backend`, `florabase-frontend`),
  `internal: true` (`db`/`backend`) and `app` (`backend`/`frontend`) network isolation, no YAML
  anchors, no inline shell scripts, no root containers, `create_host_path: false` on every bind
  mount, literal `127.0.0.1` frontend-only publication, single `FLORABASE_DB_PASSWORD`, and
  `TZ=${TZ:-Europe/Rome}` (logs only).
- Built and verified reproducible `florabase-postgres:18.6-alpine-florabase.4`
  (`index_digest` `sha256:93797c3941d06b3a8d591851df04605b5287ace2a11bb32421589ddff1a1782c`,
  `platform_digest` `sha256:7213d5bb35a00e1f80ca60193ad81a07c946e328ad4128a57e53e50fb47bb8b9`),
  adding `PGDATA`, `POSTGRES_DB`, `POSTGRES_USER`, image `HEALTHCHECK`, `-c timezone=UTC`,
  `FLORABASE_DB_PASSWORD` mapping, and pre-start ownership/mode/empty-folder/marker/`pg_controldata`
  guards with 70-owned `postgres/installation.pending` while preserving `gosu` removal, `USER 70:70`
  and exit 64 root refusal.
- Moved backend constant production `ENV` values into `backend/Dockerfile` (`runtime`), added
  `florabase-backend-entrypoint` (`PGPASSWORD` derivation) and `florabase-start` (`wait-db` →
  `release_schema deploy` → owner-env scrub → `exec release_schema serve`), pinned SQLAlchemy,
  Alembic and password-reset sessions to `-c timezone=UTC`, added host-path/non-nesting/same-folder
  and private `backup/pre-upgrade` permission guards, and added atomic `state/upgrade-failed.env`
  latching so restart loops never write repeated dumps.
- Registered `INSTALL-002` (`implemented`, `release-work`) in `docs/features.json` and
  `docs/release/scope-v1.json`; updated `scripts/beta_release.py` (`COMPOSE_SLOTS`),
  `scripts/test-beta-runtime.py`, `scripts/test-beta-images.py`, `scripts/smoke-beta-images.py`,
  `scripts/smoke-portable-compose.py` (ownership refusals, failed-upgrade single-dump latch, UTC
  check with `TZ=Europe/Rome`, beta.7 `0701`-folder upgrade, isolated restore via untracked
  `container_name` override), `docs/installation.md`, `docs/deployment.md`, `docs/security.md`
  (accepted trade-offs + optional hardened override), `docs/security/beta-distribution-001/postgresql-image.md`,
  `README.md`, `CHANGELOG.md`, and `AGENTS.md`.
- Checks: `beta_release.py postgres-identity --check` (`POSTGRES_IDENTITY_REPRODUCED`),
  `make test-beta-runtime` (17 OK), `make test-beta-images` (80 + 4 OK), `make smoke-beta-images`
  (`LOCAL_BETA_CANDIDATE_PASSED`), live `smoke-portable-compose.py` (all 3 stacks green with zero
  residual resources), `make workflow-check`, `pytest tests/test_release_schema.py
  tests/test_infrastructure.py` (68 OK), `check-features.py` (171 valid), `check-doc-links.py`
  (352 docs), independent infrastructure QA (all P0–P3 findings resolved), and canonical FULL
  `make feature-verify AGENT_ID=neon` plus `make release-preflight-local`.

## 2026-11-22 — WF-SCOPE-001 scoped verification by changed files

- On `feat/wf-scope-001-scoped-verification` from `c5f9cdf` (writer `neon-wf-scope-001`).
- Added the `product-frontend` tier (`TIER_ORDER`: `docs < affected < product-frontend < product <
  full`), bumped `scripts/verification-impact.json` to schema v2 (`product_backend_prefixes`,
  `product_frontend_prefixes`, `product_backend_tests`, `product_frontend_tests`), and moved
  `LICENSE` from `documentation_paths` into `full_prefixes` because all three Dockerfiles copy it.
- Scoped PR CI (`scripts/ci-verify.py`): `affected` and `product-frontend` plans run selected
  static/unit suites, selected integration files (or docs checks when empty) and selected builds,
  while `product`, `full`, pushes to `main` and fallbacks remain exhaustive and `ci/batch-*` keeps
  platform-tree validation plus `make_plan(base)`.
- Added `python3 scripts/ci-verify.py rehearse-scope` and PR-only `concurrency` to
  `.github/workflows/beta-release-rehearsal.yml` so docs-only PRs exit `rehearse` early with green
  status while non-docs PRs, pushes to `main`, `workflow_dispatch` and any planning or import error
  fail closed into the full rehearsal.
- Registered `WF-SCOPE-001` (`implemented`) in `docs/features.json` and proposed class `tooling` in
  `docs/release/scope-v1.json`; updated `docs/development-workflow.md`.
- Checks before final canonical gate: `test-verification-impact.py` (42 OK), `workflow-check`
  (Dependabot policy, 79 `test-beta-images`, 4 `test-release-tools-lock`, 18 `test-beta-runtime`,
  Ruff check/format, `mypy --strict` across 49 scripts), `test-feature-workflow` (55 OK),
  `test-agent-workflow` (75 OK, 3 skipped), `check-features.py`, `check-doc-links.py`,
  `test-doc-links.py`. Canonical `make verify-full` runs on this frozen tree before commit/delivery.
- Unresolved: none locally; PR description will link a real docs-only commit run showing `rehearse`
  exiting early after operator approves push/PR.

## 2026-11-22 — ENG-05 closed on branch (a)

- Documentation only, on `claude/project-thread-7djkvu` from `1126c03`. The operator chose
  branch (a) of the ENG-05 criterion: the two-session PostgreSQL regression delivered in #185.
- `./scripts/test-integration.sh backend/tests/integration/test_taxonomy_concurrency.py` passed
  13 tests on PostgreSQL 18.6 with clean disposable cleanup; recorded in
  [ENG-05 evidence](release/evidence/eng-05.md).
- Updated the TAXONOMY-001 lines of `feature-reconciliation-v1.md` and answered question 3 of
  `scope-v1-handoff.md`. The CERT-02 note of 2026-11-16 that calls both findings open predates
  this record and is superseded by it. TAXONOMY-001 status is unchanged.

## 2026-11-22 — UAT Preview smoke repaired on main

- On `fix/uat-fixture-activity-targets`, rebased on `e2db9f4` (writer `claude-uat-fixture`).
- `smoke-uat-preview` failed on `main` since PR #167: `test-uat-fixture.py` requires a Schedule
  activity for every `TARGETS` kind, but the fixture created no vegetative lot or propagation
  attempt. Added the additive `cutting_schedule_extension` (one basil stem-cutting lot and rooting
  attempt via `cuttings.fast_create`, plus two planned activities at today+5/+9) to both seed paths
  and `validate_manifest`; existing manifests gain it once and operator edits are never rescheduled.
- A second defect hidden behind the first: `UATPreview.marker_state` ran `docker run` on the
  retained backend container's image ID, which the containerd image store (Docker 29) drops after a
  rebuild (`No such image`). It now uses the project's own `-backend-development` tag, as
  `uat_instance.py` already does; regression test added to `test-uat-preview.py`.
- Checks: `make smoke-uat-preview` passed (fixture pytest 52 passed, 1 skipped; exact cleanup);
  `python3 scripts/test-uat-preview.py` 20 OK; ruff check/format and strict mypy on the touched
  scripts clean. Not run: FULL `make feature-verify`.

## 2026-11-21 — Batch 09: WF-09 two Compose files, rehearse in delivery, RC-SEQ-01 records

- WF-09 (ADR 0008): the repository tracks exactly `compose.yaml` and a standalone
  `compose.dev.yaml` (the former `compose.runtime.yaml` base merged with the development
  override). `scripts/compose_stacks.py` holds the workflow overrides (production, review, UAT,
  UAT instance, sourcing, quality, quality-network, preview, performance and the standalone
  integration stack) and writes them content-addressed under the checkout's untracked Git
  directory (`florabase-compose/<digest>/compose.<name>.yaml`). The eleven tracked overlays and the
  two historical `docs/review` stacks are removed. A revision from before WF-09 keeps its tracked
  overlays and the helpers still load them (DEV on an older primary, Stable Preview of an older
  ref). `docker compose config` of every stack (DEV, prod, review, sourcing, UAT, UAT instance,
  quality, quality-network, preview, perf, integration) was identical before and after, apart from
  top-level `x-` anchors that Compose ignores. Release artifact copies, lint/type lists and tests
  carry the new module.
- `feature-deliver` now also waits for the hosted `rehearse` job and fails loudly when it fails,
  after #207 merged with a failing rehearsal. On 2026-11-21 the operator also added `rehearse` to
  the `Protect main` ruleset, which now requires quality, integration, build and rehearse.
- RC-SEQ-01 operator decisions are recorded: CUTTING-001 and UI-SYSTEM-001 are `implemented`
  (verified only after RC-image G-CORE/G-UX and operator acceptance), U02 accepted for the
  non-Preview clauses, UI-FLICKER-001 option (a). The Codex CUTTING-001 claim was taken over on
  the operator's instruction; its uncommitted files are untouched.
- Batch 08 follow-ups: mypy includes `backend/scripts/check_api_routes.py`, and the production
  route inventory test no longer passes ambient `FLORABASE_*` variables. The impact classification
  of that script and the smoke `assert` statements remain open.
- The beta.7 publication record is part of this batch. Trivy keeps the floating vulnerability
  database (operator decision 2026-11-21): pinning would make scans reproducible but hide newly
  published CVEs. Instead every scan set records the database that judged it: `scan_images`
  (used by `publish-beta-images` and `rehearse`) writes `scanner-version.json` (`trivy version`
  with the DB `Version`, `UpdatedAt`, `NextUpdate`, `DownloadedAt`) next to the reports and blocks
  the security gate when that record is missing.
- Smoke fixtures follow WF-09: `smoke-dev-recovery` and `smoke-dev-upgrade` copy
  `scripts/compose_stacks.py` (without it the fixture read as a pre-WF-09 tree lacking a base
  `compose.yaml`), and the recovery smoke's modelled old source drops it again. `smoke-dev-golden`
  already copied `scripts/`. `smoke-migration-cycle` commits its baseline with `--allow-empty`,
  since a clean HEAD plus identical copied files left nothing to commit.
- The recovery smoke rendered its modelled pre-WF-09 baseline under the generator's
  `florabase-prod` name, which pinned `florabase-prod_*` network and volume names into the fixture;
  the baseline now drops those names so only the fixture project owns them.
- Checks: `make workflow-check` passed. Real smokes: `smoke-workflow-resources` (502 s) and
  `smoke-uat-instance` (203 s) passed on `73e5510`; after the fixes `smoke-environment-workflow`
  (114 s, Review and Stable Preview), `smoke-dev-recovery`, `smoke-dev-upgrade` (40 s) and
  `smoke-migration-cycle` (76 s) passed. `trivy version --format json` with a populated cache was
  run against the pinned 0.69.3 image and returns the DB `Version`/`UpdatedAt`; the full
  `scan_images` path runs first in hosted `rehearse`.
- Unresolved: `smoke-uat-preview` fails in `test-uat-fixture.py` because the UAT fixture creates no
  scheduled activity for the `vegetative_lot` and `propagation_attempt` targets added by #167. This
  predates Batch 09 and is not in the FULL gate; it needs its own fixture fix. Resolved by the milestone below.

## 2026-11-21 — v0.1.0-beta.7 published

- `1126c03` was tagged `v0.1.0-beta.7` and published through the protected release workflow
  (run `44949666442`, attempt 2, after the operator updated `RELEASE_APPROVED_SHA` from the beta.6
  commit). The [publication record](release/evidence/beta-7-publication.md) lists the five Release
  assets with matching SHA-256 digests and GHCR tags resolving to the manifest digests;
  `gh attestation verify` succeeded for the three images, `compose.yaml` and the manifest, bound
  to the commit and run.
- `docs/release/scope-v1.md` names beta.7 as the current G-MIGRATE and G-UPGRADE baseline. No
  feature status changed.

## 2026-11-21 — Release rehearsal upgrade smoke under umask 077

- The hosted `rehearse` job failed from #207 onward: the release pipeline runs under umask 077, so
  the derived test-only upgrade image copied its migration and previous-release declaration as
  0600 and `migrate` (uid 10001) stopped with `PermissionError` instead of the expected
  `SQLSTATE 42P07`. The derived Dockerfile now copies both with `--chmod=0644`; the production
  backend image is unaffected. A mismatched refusal now prints the `up` output, service states
  and the service log tail. The local checks did not catch it because they ran under umask 022.
- Checks: hosted `rehearse` on this branch (workflow dispatch) and the canonical gate.

## 2026-11-21 — v0.1.0-beta.7 release preparation

- Version surfaces move to `0.1.0-beta.7` (`release/inputs.json`, backend package and module,
  frontend package, both Dockerfiles, regenerated OpenAPI). The Unreleased CHANGELOG section
  becomes the `v0.1.0-beta.7` entry, the first release with the self-initializing `compose.yaml`
  (#205, #207). The installation guides name beta.7 as the first release of the new layout.
  PostgreSQL stays `18.6-alpine-florabase.3`; the backend declares beta.6 as its previous release.
- No feature status changes. Tag, protected publication and publication evidence remain operator
  actions.

---

Earlier milestones (through `v0.1.0-beta.6` / `INSTALL-001`) are archived verbatim, newest-first, in [archive/progress-until-beta-7.md](archive/progress-until-beta-7.md).
