# Frontend low-risk dependency maintenance handoff

Implementation-only batch on `fix/deps-frontend-low-risk`, based on authoritative main
`aebe4715a1c26c7ed3dca9b1e19d7420cc8ea4d4` (merged CI-003 repair, PR #85).
The attached `d9bd` worktree was clean; its pre-squash detached commit had the same tree.
Only this worktree was aligned to `origin/main`, then initialized with `make feature-init`.
The supported initializer requires a `feat/`, `fix/`, `docs/` or `ci/` prefix.

## Selected packages and compatibility

- `@types/leaflet`: **1.9.21 → 1.9.22**. Current stable registry version; no Node engine
  requirement. Comparing the published declarations shows only `DivIconOptions.html` widening
  from `HTMLElement` to `Element`. Runtime Leaflet remains **1.9.4**. Existing map consumers
  need no source changes, casts, ignored diagnostics or new API assumptions.
- `@testing-library/user-event`: **14.6.6 → 14.6.7**. Current stable registry version; Node
  `>=12`, npm `>=6`, peer `@testing-library/dom >=7.21.4`. The retained DOM package is
  **10.4.1**. Upstream changes add iframe keyboard handling and normalize DataTransfer aliases;
  React and the DOM/test runner stack remain unchanged.
- Registry metadata was refreshed for this batch, rather than copied from Dependabot. Both
  releases exceed the unchanged repository minimum-release-age policy.
- Sources: [Leaflet registry](https://registry.npmjs.org/@types%2fleaflet/1.9.22),
  [user-event registry](https://registry.npmjs.org/@testing-library%2fuser-event/14.6.7),
  [user-event patch comparison](https://github.com/testing-library/user-event/compare/v14.6.6...v14.6.7).

## Manifest and lock integrity

Used the repository Quality frontend workflow with pinned pnpm:
`pnpm add --save-dev --save-exact @types/leaflet@1.9.22 @testing-library/user-event@14.6.7 --lockfile-only`.
The generated diff changes only those two importer entries, package versions/integrity hashes,
and snapshot keys. There is **no transitive version churn**; GeoJSON types stay **7946.0.16**.
Frozen installation succeeds and an independent exact-diff assertion confirms manifest/lock agreement.

Unchanged: pnpm **11.19.0**, Node engine **>=24 <25**, Docker Node **24.19.0**, Node types
**24.13.3**, React/DOM **19.2.8**, React types **19.2.18/19.2.5**, Vite **8.2.2**, React plugin
**6.1.0**, jsdom **30.0.1**, ESLint **10.9.1**, typescript-eslint **8.68.0**, React refresh lint
plugin **0.5.5**, Prettier **3.9.6**, TypeScript **5.9.3**, Vitest **4.1.11**, and all backend files.

## Focused verification

All frontend checks ran in worktree-scoped Quality using actual Node **24.19.0** and pnpm **11.19.0**.

- Unchanged main: `pnpm test src/App.test.tsx` — **73 passed**. Two preceding exact filtered
  attempts stopped at the cold lazy identity screen (`+ New botanical identity` unavailable,
  `Loading workspace…`), before the clear/focus interaction. No test or timeout was changed.
- Updated dependencies: **104 passed across seven files** — `App.test.tsx`,
  `components/FormSections.test.tsx`, `provenance-map/ProvenanceMapScreen.test.tsx`,
  `provenance-sites/ProvenanceSiteManager.test.tsx`, `native-ranges/NativeRangesScreen.test.tsx`,
  `occurrence-map/OccurrenceMapPanel.test.tsx`, and `occurrence-map/OccurrenceDensityMap.test.tsx`.
- `pnpm typecheck`, frontend `pnpm lint`, and Prettier checking the two dependency files passed.
- Additional strict Leaflet declaration compilation passed with `tsc --noEmit --strict
  --target ES2023 --module ESNext --moduleResolution bundler --lib ES2023,DOM`, using
  `readlink -f node_modules/@types/leaflet/index.d.ts`. An initial probe through the public symlink
  could not resolve transitive GeoJSON types; correcting the probe path required no dependency or
  source changes. Application typing passed independently.
- `make verify-build SERVICES=frontend` — production frontend build passed; owned image retired.
- `git diff --check` passed. API artifacts/contracts are unchanged; API drift and exhaustive
  verification remain included in Luna's later FULL gate.

## Historical clear/focus workflow and bounded runtime smoke

Independent review reproduced the UI state behind the historical failure: after opening Edit
profile, the “Uses” field is hidden until “Uses & warnings” is activated. The production behavior is
correct because users cannot focus or clear a hidden field. The existing test previously tried to
clear “Uses” before activating its tab; jsdom allowed this despite the real browser interaction
being unavailable. The test now activates the tab before reading and clearing the field. Its saved
profile and final “profile cleared” assertions remain intact. This is a narrowly justified test-only
repair; no production behavior changed, and the test does not attribute the historical failure to
user-event 14.6.7.

A unique synthetic UAT fixture used existing `SmokeUAT` and `SmokeLifecycle` helpers, registering
cleanup before creation. Browser smoke verified real owner login, authenticated Dashboard boot,
normal identity creation, and a two-section profile save. Clearing Description preserved Uses;
revealing the Uses tab, focusing/clearing Uses, then saving produced “Botanical profile cleared”
and “No botanical profile yet.” Collection origins rendered real Leaflet basemap/marker controls,
popup and linked synthetic records. Browser console warning/error inspection was empty.

The updated test preserves all prior assertions while following the same visible tab workflow as
the browser. Broad visual review remains deferred.

## CI-003, cleanup and handoff boundary

`make verification-plan FORMAT=json` selects **FULL**, escalated by both dependency paths:
all backend/frontend/PostgreSQL tests, all eight workflow checks, global static/API checks,
both production builds and **full-cycle** migrations. No `CI003_GAP` was found. Sol had not run
the canonical gate at the implementation handoff; independent final verification is recorded below.

Production build `florabase-verification-build-758adb14406d` and browser fixture
`florabase-uat-preview-smoke-70ef204d4a30` reported zero residual containers/networks/volumes;
their owned images retired. `make quality-clean` retired only this worktree's newly created
`florabase-quality-ab1b459cfd98`; final Quality status is zero containers/images/networks/volumes.
Shared BuildKit cache was retained and no global prune ran. Protected DEV/Review/UAT/Stable
Preview/production resource identities, mounts, database digests and primary Git identity match
the before snapshot. The initial snapshot assertion compared in-memory tuples with serialized
lists; independent JSON-normalized comparison confirmed equality without changing any environment.

At the implementation handoff, the diff was the two dependency files plus this handoff and a concise
progress milestone. The independent QA test correction is limited to activating the Uses tab before
the existing clear assertion. Primary main was untouched during implementation. No bot PR or branch
was edited. Later groups start from main after this batch is delivered.

Deferred: Node types 26, React/DOM/types, Vite/plugin-react, lint/type/format tooling, jsdom,
all backend updates and DASHBOARD-001. No feature graph or roadmap status was changed.

## Independent Luna verification

Luna independently reviewed the complete diff and reproduced the hidden-field state in the browser.
The focused test-only correction activates “Uses & warnings” before interacting with Uses; all
existing partial-save and final-clear assertions remain unchanged. No production code changed.

The final `make verification-plan FORMAT=json` selected **FULL** because both frontend dependency
manifest and lockfile are escalation paths. Canonical `make feature-verify` passed: feature graph
valid, all eight workflow checks, static/format/lint/type/API checks, **910 backend tests** at
**90.32% coverage**, **557 frontend tests across 57 files**, **711 PostgreSQL integration tests**,
production backend and frontend builds, forced full migration cycle at `20261009_0041`, whitespace
checks, and exact-tree receipt.

An independent browser smoke against a unique synthetic UAT fixture verified owner login, Dashboard
boot, synthetic identity creation, profile save, partial clearing that preserves Uses, final clearing
to “No botanical profile yet,” and Leaflet marker popup with its linked record. The fixture was
retired with its exact workflow owner; both it and an interrupted earlier unique fixture have zero
remaining containers, images, networks, or volumes. `make quality-clean` removed this worktree's
Quality resources; shared cache remained. DEV, UAT Preview, Stable Preview and Production project
identities remained present and unchanged. No broad visual review or database upgrade was performed.
