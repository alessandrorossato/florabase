# DASHBOARD-001 — implementation handoff

Base: `18941647fc8f0e322d13c8743d637139bc043fd6`.
Branch: `feat/dashboard-001-ui-foundation` in Codex worktree `51ba`.

## Independent verification — 2026-10-12

The initial canonical run stopped at strict mypy because the new empty-state integration assertion
chained equality between the distinct upcoming and history response-list types. The assertion was
split into two explicit empty-list checks; no test behavior or timeout was weakened. The final
`make feature-verify` FULL run passed and recorded the exact-tree verification receipt.

- Quality passed: backend unit tests **910 passed**, frontend Vitest **564 passed / 58 files**,
  backend Ruff, frontend ESLint/Prettier, Python mypy (339 source files), TypeScript, generated API
  drift, feature/workflow checks, and whitespace checks.
- PostgreSQL integration passed: **717 passed**. New Dashboard integration cases passed as part of
  that suite. Full production backend and frontend image builds passed.
- The required migration full-cycle passed from/to the existing head `20261009_0041`; this feature
  adds no schema migration. Disposable migration resources were verified clean after the cycle.
- The earlier isolated Quality Vitest wrapper had returned exit 143 after reporting success. This
  canonical run completed its Vitest stage with 564 passing tests and then passed the remaining
  integration, production-build, migration, and health stages; no exit 143 recurred. No assertions
  or timeout limits were changed to obtain the result.
- The read-only workflow resource inventory was reviewed after the earlier failed run. No runner
  container remained; unrelated/legacy Docker projects and the shared build cache were preserved.
- Product review found no material domain or UI-foundation defect. Existing desktop/tablet/mobile
  visual and keyboard review is recorded below; API counts and semantics are covered by the
  independent test suites.

Feature status is `verified`. Delivery and worktree finish follow the protected repository workflow.

## Foundation

[UI contract](ui-contract.md) is authoritative and linked from AGENTS.md. It records all final
palette values, type scale, spacing/radii, page archetypes, interaction surfaces, accessibility,
responsive rules and do/don't examples. The sole token source is `frontend/src/styles/tokens.css`;
legacy variable names are aliases, not a second palette. Base typography/focus, controls and the
subtle shell apply globally; unrelated page layouts are retained.

Source Sans 3 Variable for UI and Source Serif 4 Variable for botanical names: exactly pinned
Fontsource 5.3.0 packages, normal/italic WOFF2, font-display swap, same-origin Vite assets.
No runtime CDN. OFL licenses ship in `frontend/public/licenses`. July 19 releases meet the
unchanged 1,440-minute release-age policy; October 11 releases were deliberately not selected.
No other package versions changed. UI 15/22, headings 32/38, 22/28, 17/24, metrics 32/36;
4/8/12/16/24/32/48/64 spacing; 6/10/14 radii. No default card shadow.

Reuses PageHeader, existing shell, search/SavedViews, navigation and interaction components.
Adds Page, SectionHeader, Metric, StatusBadge and empty/loading/error states in WorkspaceUI.
Metric accessible descriptions preserve qualifiers. Schedule urgency and recent sources have text
labels. Dashboard reuses OverflowMenu for Quick add and TaskDialog for advanced filters and
compact SavedViews access. Document scrolling replaces the fixed-height workspace scroller only
on Dashboard. Desktop four metrics, tablet/mobile two; the operational row uses approximately
7:5 on desktop, equal columns on tablet, and stacks on mobile. Supporting facts use ruled sections,
not nested cards.

## Dashboard definitions

Every inclusion, exclusion and unknown rule is recorded in the [audit](dashboard-001-audit.md).
The four main values are active **records**, not quantities or viability claims. Identity coverage
reuses Explore current membership (including active stored material on historical source plants).
Unknown germination and recorded zero remain separate; neither implies failure. Optional sourcing
review counts active purchased seed lots without an Order link; Orders have no open lifecycle.
Profile content includes text or structured native ranges, excluding empty profile shells.
WFO coverage counts explicit retained confirmations, not inferred matches or correctness scores.

Schedule is planned intention: overdue < supplied local day, today equal, next seven tomorrow
through day seven inclusive. Earliest five planned rows ordered by due date/UUID, with target
and retained lifecycle. Recent six reuse History's deduplicated ordering: Event-source entries
are labelled Journal, other operational sources History. Partial dates, recorded fallback (UTC)
and reversal status stay visible. No ScheduledActivity is presented as historical occurrence.

## Implementation and performance

Authenticated GET `/api/v1/dashboard` gains optional strict date-only `today` (UTC default), and
required `overview` with bounded upcoming/recent arrays and semantic counts. Browser sends local
calendar day; a local timer detects midnight without polling the API while the day is unchanged.
No provider requests or caching. Existing counts/recent_events are retained for compatibility;
the browser renders the new operational projection. OpenAPI and TS declarations are generated.
Six original count requests are consolidated into one scalar-subquery SELECT. Coverage reuses a
single distinct membership CTE, profiles/ranges use existence checks; no row-multiplying joins.
Schedule targets resolve in bounded batches; History uses its existing one-query projection.
Existing lifecycle/FK/status-date indexes are retained. Aggregate counts necessarily inspect the
qualifying population; no speculative indexes or migration were added.

## UAT and fixtures

The user explicitly authorized retirement of old SCHEDULE-001 UAT. The owning `dcdf` helper
removed only validated `florabase-uat-preview` synthetic resources. Current review uses this
worktree at `http://localhost:15174`, UAT-only `preview / preview`. DEV, Stable Preview,
production and primary main remain untouched.
Existing canonical fixture already contains active/historical material, Orders, profile content,
stored material, Journal/Harvest facts and relative-day planned work (overdue/today/future).
The additive Dashboard extension adds one purchased basil packet without an Order and two active
sowings (unknown and recorded-zero germination). Its manifest marker prevents repeat creation or
operator-edit overwrite; repeated seeding retains 56 baseline records. A separate synthetic
collection-wide activity due 2026-10-12 was added through Schedule during browser review because
the original fixture was seeded the previous day. Relative-day fixtures naturally age; reseeding
never silently reschedules operator work. No real collection is modified.

Final UAT status: frontend/backend/database healthy, all running from worktree 51ba, database
current equals code head 20261009_0041. The initial restart returned nonzero during its status
probe; the subsequent guarded status command and browser/API use passed. WFO snapshot is optional
and absent here (honest zero coverage); nonzero WFO coverage is covered by PostgreSQL tests.

## Initial implementation verification evidence

Baseline: collection-view backend unit tests **3 passed**; existing App/DashboardSearch frontend
**82 passed / 2 files**.

- Final collection-view unit tests: **3 passed**; Ruff lint/format and strict mypy passed.
- PostgreSQL Dashboard, event API and primary-photo integration selection: **21 passed** during
  implementation, including lifecycle exclusions, strict dates/auth, current membership, profile
  content, deterministic History and bounded query count (at most 25 including retained legacy
  event enrichment). Disposable resources cleaned up by the integration helper.
- Final Quality runtime Vitest: **93 passed / 4 files** (App, UX001, DashboardSearch,
  DashboardScreen). Host runs under concurrent builds had five lazy-workspace loading timeouts;
  the unchanged tests pass in the canonical runtime. No test timeout or assertion was weakened.
- Frontend ESLint, TypeScript and production Vite build passed; generated API drift check passed.
  Vite emits self-hosted font assets; main JS is approximately 222 kB (69 kB gzip).
- Script lint uses the existing isolated E4/E7/E9/F/I/B/UP rules; passed. Backend-only broader
  Ruff rules initially reported pre-existing script conventions; no unrelated cleanup applied.
- Dashboard fixture test: **1 passed / 23 deselected**, with repeat seeding and operator-edit
  preservation; no reset of the prepared review collection.
- Changed-source formatting and `git diff --check` pass. No migration is needed. Canonical
  `make feature-verify` remains reserved for independent QA; status is implemented, not verified.

## Initial visual self-review — 2026-10-12 (superseded layouts)

Dashboard and representative existing Seeds, Botanical identities directory, and Schedule were
inspected at **1440×844, 1024×844 and 390×844**. No horizontal document overflow, clipped metric
values or unreachable actions observed. Mobile operational rows wrap with dates/status retained;
lower propagation, sourcing, coverage and quick actions remain usable above the fixed navigation.
Scientific names retain serif italics and cultivar text remains distinct. Existing page-specific
layouts and legacy editorial headings are deliberately retained.

Checked Dashboard → Schedule, due-today filtered navigation, search filter and SavedViews
disclosures, and a real synthetic Schedule create dialog (initial input focus and successful save).
Keyboard Tab from SavedViews reaches the first metric with a visible 3 px #3D6F8E focus outline.
Text/attention contrast was reviewed; warning-text and border-strong tokens are documented
accessibility adjustments. Loading/error/retry/empty/auth states are covered by frontend tests.
No new overlay interaction mechanism is introduced.

Screenshots are local review artifacts, outside Git:
`/home/alessandro/.codex/visualizations/2026/10/11/01a12c0d-1da7-79b2-8a75-a87e76cf63e1/`.
Files: `dashboard-{1440,1024,390}.jpg`, `dashboard-390-lower.jpg`,
`dashboard-keyboard-focus.jpg`, `seeds-{1440,1024,390}.jpg`,
`identities-{1440,1024,390}.jpg`, `schedule-{1440,1024,390}.jpg`.

Independent QA should run the reserved canonical gate and perform the final product visual review.
The candidate remains on the requested baseline branch with an empty Git index and no new commit.

## Visual-review refinements — 2026-10-12

- Dashboard toolbar order is Search, Filters, Saved views, Quick add. Search expands with available
  width; mobile places it on its own line above the compact controls. Header spacing is tightened.
  The standalone Saved Views row and bottom “Record in your collection” strip are removed.
- Quick add reuses OverflowMenu and all nine existing creation routes, with arrow/Home/End keys,
  Escape/action dismissal and outside-click focus restoration. Focus-driven dismissal keeps the
  next intended control; clicking a blank surface restores the trigger after browser blur.
- Advanced filters reuse TaskDialog as a right-side drawer, with native focus containment and
  trigger return on Escape, Close, Done or safe backdrop dismissal. All filters and reference
  pickers are retained. Choices apply immediately to the existing canonical URL/history; resetting
  filters preserves the query. Record types and references use compact columns on desktop and a
  single readable column on mobile. Only the drawer scrolls while it is open; no inline panel
  expands the page, and background document scrolling is locked.
- SavedViews gains an optional compact dialog presentation used by Dashboard. Existing list,
  all-surface access, pagination, unsupported-state notices, routes and CRUD logic are shared.
  Save view moves inside that dialog when search/filter state is meaningful. Its normal inline
  presentation on other pages is retained.
- Width/scroll fixes are scoped through the Dashboard workspace: full available width, no 86rem
  cap, auto-height shell/content, document scrolling and sticky desktop navigation. Attention and
  Recent use approximately 7:5 desktop columns, equal tablet columns, then one column on mobile.
  Supporting sections retain restrained dividers and balanced desktop thirds.

Browser self-review covers Dashboard, toolbar, Quick add and filters at **1440×844, 1024×844,
390×844**. Verified no horizontal overflow; app-content and workspace use overflow visible, not
independent content scrolling. Mobile drawer bounds exactly match 390×844, all choices and footer
controls remain reachable, and Quick add fits without covering the bottom navigation. Reviewed
secondary sections on mobile and desktop. A synthetic “Preview — Dashboard active plants” Saved
View was created through the UI and reopened to restore `kind=plant&lifecycle=active`. No collection
records were edited. Quick add opened the existing seed-lot editor, which was cancelled unchanged.

Regression review: Seeds and Botanical identities retain their existing desktop pane scrolling and
mobile layout. Botanical identities still uses inline SavedViews. Changes to shared components are
optional SavedViews presentation, TaskDialog's optional ID for accessible control association, and
OverflowMenu pointer-dismissal focus restoration; no unrelated page styling was migrated.
Pre-existing page-specific spacing/editorial-heading differences remain for the later global review.

Refinement screenshots are under the same local artifact directory in **`refinement/`**:
`dashboard-{1440,1024,390}.jpg`, `dashboard-390-lower.jpg`, `dashboard-1440-lower.jpg`,
`quick-add-{1440,1024,390}.jpg`, `filters-{1440,1024,390}.jpg`, `filters-390-lower.jpg`,
`saved-views-{1440,390}.jpg`, `seeds-{1440,390}.jpg`, `identities-{1440,390}.jpg`.
The original screenshots above document the initial candidate; these refinement files are current.

Refinement validation: collection-view unit **3 passed**, Dashboard PostgreSQL **4 passed** with
owned disposable cleanup; frontend baseline Dashboard **4 passed**. Frontend TypeScript, ESLint,
changed-source Prettier and production Vite build passed; main JS remains approximately 222 kB
(69 kB gzip). `git diff --check` passes. The repository's `pnpm test` runner reports **105 passed /
5 files**: DashboardScreen, DashboardSearch, SavedViews, UX001 and App. Tests cover menu keyboard
navigation/dismissal/focus, drawer state/reset/history, shared SavedViews routing and existing
workspace behavior. Direct Vitest invocations had a cold first-workspace loading timeout; the
configured runner passes without assertion or timeout changes.
Quality Vitest completed its 105-test success report, but the Docker wrapper returned exit 143
afterward; `make quality-status` confirms zero retained test containers. A subsequent host runner
reported 102 passes and three existing App timing failures during a concurrent lint/build run:
session restoration and sidebar disclosure exceeded the unchanged 15-second timeout (121/166
seconds elapsed), and a Native ranges lazy workspace did not load within its query wait. All three
passed in Quality, and an isolated host rerun of exactly those failures passed **3 tests / 70
skipped** in 11.82 seconds with no concurrent lint/build. These host/runner limits are retained as
evidence for Luna; assertions and timeouts remain unchanged.
No backend/API contract or dependency manifest/lock change was made in this refinement; the prior
API drift result remains applicable at that handoff point. The independent FULL canonical gate and
exact-tree receipt are recorded in the verification section above.

## Deferred

Full cross-application migration, page-specific legacy colors/spacing/editorial typography,
unrelated interaction changes, new task-manager concepts, rates/spend/financial metrics,
external enrichment and dependency maintenance. No schema/migration or DEV upgrade.
