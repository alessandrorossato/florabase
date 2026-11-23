# LABEL-001 implementation review

Reviewed and verified on `feat/label-001` from `d19829e`, without changing branches. LABEL-001 is
`verified`; all changes remain unstaged and uncommitted. No commit, push, delivery, merge, or branch
finish was performed. The physical printer and system print-dialog checks remain with the operator.

## Implementation and changed files

- `frontend/src/labels/LabelsScreen.tsx`: temporary composer, existing ReferencePicker, loading and
  retry states, unsupported/unavailable-target errors, empty state, copy validation, 36-label cap,
  add/remove, focus restoration, responsive preview, and browser Print sheet action.
- `frontend/src/labels/labelData.ts`: fixed target union, existing protected list API reads, compact
  name/context projection, supported UUID validation, configured-origin record URLs, and composition.
- `frontend/src/labels/LabelSheet.tsx`, `qrCode.ts`, and `labels.css`: bounded human-readable labels,
  local React SVGs, four-module quiet zones, medium error correction, fixed 22 mm QR, and the named
  A4 print page. Each cell is a 50 × 30 mm border-box; 4 × 9 cells occupy 200 × 270 mm with zero gap.
  Margins are 5 mm horizontally and 13.5 mm vertically. Print styling hides the app root and prints
  only a body-level sheet portal; named-page rules do not change other application printing.
- `frontend/src/App.tsx`: authenticated Labels route and Tools/More navigation.
- `frontend/src/seed-lots/SeedLotScreen.tsx`, `frontend/src/plants/PlantScreen.tsx`: secondary Print
  label actions in existing SeedLot, Plant, and PlantGroup detail headers, including historical records.
- `frontend/package.json`, `frontend/pnpm-lock.yaml`: pinned `qrcode-generator` 2.0.4, no runtime
  dependencies. `frontend/public/qrcode-generator-LICENSE.txt` distributes its MIT copyright/license
  with production assets; this is compatible with the application's AGPL-3.0-or-later license.
- `frontend/src/labels/LabelsScreen.test.tsx`: focused cases covering exact URLs, configured
  development/production origins, no query or
  credential copying, target/reference rejection, protected API reads, identity/context semantics,
  mixed copies and capacity, safe text, QR finder/quiet-zone behavior, print geometry, keyboard
  operation, validation, removal focus, StrictMode initial addition, retry/empty/unsupported states,
  unauthenticated record/composer links, and authenticated composer routing.
- `frontend/src/seed-lots/SeedLotScreen.test.tsx`, `frontend/src/plants/PlantScreen.test.tsx`: three
  authenticated direct-detail/action cases using existing screen fixtures.
- `backend/src/florabase/auth/api.py`, `backend/openapi.json`, and `frontend/src/api/schema.d.ts`:
  existing authenticated session response now includes the configured canonical origin; generated
  API contract and types are synchronized.
- `backend/src/florabase/core/config.py`, `backend/tests/test_config.py`, and
  `backend/tests/test_auth_api.py`: reject credential-bearing canonical origins and prove the
  session receives the configured value.
- `backend/tests/integration/test_seed_lot_api.py`: three parameterized existing-target lookup cases
  proving exact authenticated records, unauthenticated/invalid-session rejection, missing UUID 404,
  and malformed UUID 422. The independent final review subsequently added the session-origin
  response field described below; it adds no endpoint or persistence.
- `docs/labels.md`, `docs/architecture.md`, `docs/domain-model.md`, `docs/product-roadmap.md`,
  `docs/features.json`, and `docs/progress.md`: narrow workflow, security, physical format, dependency,
  implemented status, and verification evidence updates.

## Independent final review

The review found that QR construction used `window.location.origin`. That is not durable across
proxy aliases or a browser opened through a non-canonical host. It now uses `canonical_origin` from
the authenticated `/api/v1/auth/session` response, sourced directly from existing
`FLORABASE_CANONICAL_ORIGIN` settings. No Host/forwarded header or user-editable origin participates.
Development configured as `http://localhost:5173` produces that origin; production configured as
`https://flora.example.com` produces the production origin. The existing protected hash routes and
UUID validation are unchanged. Canonical origins containing credentials are rejected by backend
configuration; missing or malformed frontend values stop label creation. Focused regressions cover
both origins, independence from the browser origin, credential-free exact routes, and invalid
origins. This is an additive field on an existing authenticated session API response, with generated
OpenAPI and TypeScript updated; no migration or new endpoint was added.

Independent browser access reached the Florabase sign-in screen. No credentials were available in
the task, so authenticated composer screens and print media were not visually re-inspected in the
live browser. The implementation-side visual and PDF evidence above is not counted as independent
visual verification. The operator has manually confirmed functional behavior. Physical printer and
system print-dialog validation remain outstanding.

Labels contain BotanicalIdentity display text, Seed lot/Plant/Plant group, an optional existing
record label, Florabase, and QR. No photo, invented number, quantity, dates, provenance, or other
record-summary fields appear. Four lines bound the botanical text and two bound optional context;
the QR remains fixed. Required identity semantics are preserved, including cultivar and `sp.` text.

QR URLs are built from the authenticated session's canonical origin, `/`, the existing hash route,
and a validated UUID. Current URL queries/hash, auth state, cookies, tokens, signed credentials,
and request Host/forwarded headers do not enter the payload. Normal login and existing protected
APIs remain authoritative. There is no new public access model, migration, database print entity,
worker, browser storage, external QR service, photo request, or server PDF generation.

## Verification

- Baseline frontend suite: 197 tests passed before implementation.
- Focused label suite: `cd frontend && pnpm test src/labels/LabelsScreen.test.tsx` — 20 passed.
  The combined Labels/SeedLot/Plant suites passed all 62 cases, including the three new detail links.
- `make check` — exit 0; Ruff formatting/lint, strict mypy (214 files), frontend Prettier/ESLint/
  TypeScript, 422 backend unit tests, 220 frontend tests across 23 files, and generated OpenAPI/
  TypeScript drift checks passed. The existing backend coverage display inconsistency remains:
  raw coverage is 89.75%, pytest-cov prints a `FAIL` summary while its zero-precision threshold check
  rounds to 90% and exits successfully. This matches the prior documented ATTACHMENT-004 result;
  no coverage configuration or policy changed.
- `make test-integration` — 354 PostgreSQL cases passed, including all three new lookup cases,
  in the repository's isolated tmpfs integration project; 118 existing warnings. No development
  or preview database was modified by these checks.
- `docker compose build frontend` — production build passed. The existing Vite large-chunk advisory
  remains. The final build includes the MIT notice. No backend production code changed.
- `python3 scripts/check-features.py` — 81 features valid; `git diff --check` passed.
- Same-origin development `/api/v1/health` and `/api/v1/ready` — both returned `status: ok`.

Initial development checks caught lint issues and a test fixture that reused a consumed Response in
StrictMode; these were corrected without weakening checks. Browser review corrected the heading to
the existing page-header pattern. The canonical final feature gate remains with independent review.

## Browser and print evidence

An isolated loopback Vite frontend at `http://localhost:15174` rendered the actual App and Labels
components in Chromium 151, with disposable intercepted API fixtures. No owner credentials or real
collection records were used. The fixture was presentation-only; PostgreSQL tests separately proved
live record authorization. Browser tooling and the independent decoder were temporary test tools,
not repository dependencies or screenshot-golden infrastructure.

Reviewed **1440 × 844, 1024 × 844, and 390 × 844**: empty composer, one label, mixed SeedLot/Plant/
PlantGroup, duplicates, short binomial, long infraspecific-style text, cultivar display, partial
`Solanum sp.`, absent optional record label, keyboard selection, copy editing, removal/focus, and
Print sheet invocation. Whole-document scroll width equaled viewport width at all three sizes.
No external request or browser page error occurred, including fixtures with external primary-photo
metadata. The label text and QR boxes stayed inside every physical label.

Print media rendered all **36** labels in the fixed 4 × 9 grid. Computed cell dimensions were
**188.96875 × 113.375 CSS px** (50 × 30 mm at 96 CSS px/in, subject only to browser subpixel rounding).
The QR measured **83.140625 × 83.140625 px** (22 mm). Every cell had `transform: none`, `zoom: 1`, and
`break-inside: avoid`; the app root had `display: none`. No CSS scaling was applied.

Chromium's ordinary print-to-PDF renderer, with CSS page size, scale 1, and browser headers/footers
disabled, produced **one A4 page**, approximately 209.889 × 297.011 mm due to browser page rounding.
SVGs rasterized at approximately 300 dpi decoded independently to four exact fixture record URLs.
The actual printed PDF was then rasterized at 300 dpi; first-cell and final-row crops independently
decoded all four distinct SeedLot/Plant/PlantGroup URLs again, confirming margin positions and
scanability after print rendering. No credential/query material appeared.

Local review artifacts are in `/tmp/label-001-review/`: `empty-*`, `one-*`, and `mixed-*` viewport
PNGs, `print-media.png`, `labels-a4.pdf`, `printed-a4.png`, `evidence.json`, and `pdf-decoded.json`.
The temporary browser fixture is `/tmp/label-001-browser.cjs`; its Playwright/Sharp imports use the
desktop's bundled runtime and its independent jsQR decoder lives under `/tmp/label-001-test-tools`.
These are disposable local evidence, not tracked application files.

## Operator review and limitations

Inspect the real system print dialog and physical printer separately: A4 portrait, 100% / Actual
size, no Fit to page, no headers/footers, and the stylesheet's margins. Measure the 50 × 30 mm cell
pitch, verify all four columns/nine rows align with the selected stock, and scan the three record
types from another device using the reachable canonical deployment address. Check long-name
readability and scanability at the actual installation hostname and printer resolution.

The operator confirmed the functional workflow. The live browser reached the sign-in screen, so
authenticated composer screens and print media were not independently viewed without credentials;
implementation-side screenshots above are not counted as independent visual proof. The system print
dialog and physical printer were not validated. The layout requires fresh stock matching its fixed
zero-gutter pitch and margins; no partial-sheet offsets are implemented. Exceptionally long text
truncates. Selected labels are temporary loaded snapshots and must be reopened after name corrections.
A refresh of a detail-action URL starts again with that one record, while other composition edits are
discarded.

Canonical `make feature-verify` passed on the final review tree with
`FEATURE_VERIFICATION_PASSED`: 423 backend unit tests, 228 frontend tests, 354 PostgreSQL integration
tests, API drift, feature graph, formatting, lint, mypy, TypeScript, both production builds, and the
migration cycle (no Alembic revisions). The backend coverage summary displayed 89.77% against the
nominal 90% threshold but returned success, matching the repository's existing rounding behavior;
coverage policy was not changed.
