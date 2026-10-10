# Engineering progress

## 2026-10-10 — frontend low-risk dependency batch (implementation handoff)

- From merged PR #85 main `aebe471`, updated only `@types/leaflet` **1.9.21 → 1.9.22** and
  `@testing-library/user-event` **14.6.6 → 14.6.7**, with pnpm-generated lockfile and no transitive
  churn. Node, React, Vite, jsdom, lint/format tools and backend dependencies are unchanged.
- Baseline App **73 passed**; updated focused App/form/map selection **104 passed / 7 files**,
  strict TypeScript/Leaflet declarations, frontend lint, dependency formatting and production
  frontend build passed. Bounded synthetic browser smoke covered auth, normal form creation,
  partial/final profile clearing and real Leaflet marker/popup behavior; exact owned cleanup passed.
- CI-003 selects **FULL** including migration cycle. Changes remain unstaged/uncommitted;
  canonical gate, independent review and delivery belong to Luna. See the
  [handoff](dependency-maintenance-frontend-low-risk-handoff.md), including cold-test readiness
  evidence. Independent review found the clear-flow test acted on a hidden Uses field; the test now
  activates its tab before clearing, without weakening assertions or changing production behavior.
  No roadmap status changed.

## 2026-10-10 — frontend low-risk dependency batch (Luna independent verification)

- Independent review accepted the two-package dependency scope and pnpm lockfile delta. The only
  test repair follows the real UI by activating “Uses & warnings” before accessing Uses; production
  behavior and all save/clear assertions remain unchanged.
- Canonical `make feature-verify` selected **FULL** and passed: **910 backend tests, 90.32% coverage;
  557 frontend tests across 57 files; 711 PostgreSQL integration tests; eight workflow checks;
  static/format/lint/type/API checks; backend/frontend production builds; full migration cycle at
  `20261009_0041`; exact-tree receipt. Node 24.19.0 and pnpm 11.19.0 were used by Quality.
- Independent synthetic browser smoke confirmed authenticated Dashboard boot, identity creation,
  profile save, partial/final clearing, and Leaflet marker popup. Exact fixture and Quality cleanup
  passed; protected project identities remained. No database migration or DEV upgrade is needed.

## 2026-10-10 — CI-003 independent verification and protected delivery preparation

- Independently reviewed the implementation, complete feature graph, CI ownership, resource
  registration/cleanup paths, failure/signal handling, verification selectors/receipts, delivery and
  finish guards, and real Compose evidence. No workflow defect or `NEEDS_SOL` blocker was found.
- `make smoke-workflow-resources` passed against isolated synthetic projects: exact target cleanup
  was idempotent, dirty-primary finish refusal preserved Quality, proven fixture finish retired only
  its own Quality resources, and DEV/Review/UAT/Stable Preview/production, another Quality owner,
  unrelated projects, and shared BuildKit cache remained unchanged.
- Explicit `make verify-full` passed. After final status and roadmap updates, `make feature-verify`
  independently selected **FULL** and passed with a final-tree receipt: feature graph **99 valid**;
  workflow/helper suites, repository format/lint/strict typing and API drift; backend **910 passed**
  at **90.32%** coverage; frontend **557 passed across 57 files**; PostgreSQL integration **711
  passed**; backend/frontend production builds; and migration **base → head → base → head** through
  `20261009_0041`. Every disposable run reported zero owned container/network/volume residuals.
- The first final-gate attempt had one transient frontend lazy-load timeout under exhausted host
  swap. The unchanged test passed three isolated repetitions and the complete frontend suite passed
  on the fresh full-gate retry; no test or timeout was altered. Final canonical rerun follows this
  progress-log update so the receipt matches the complete final tree.
- CI-003 is `verified`; no schema changes mean no DEV upgrade is needed. After protected delivery
  and `make feature-finish`, sweep open bot dependency-update PRs before DASHBOARD-001. No staging,
  commit, push, PR, delivery, or feature finish has yet occurred.

## 2026-10-10 — CI-003 scoped Docker retirement and impact-aware local verification implemented

- Audited the complete **99-feature** graph and existing workflow/build/environment ownership at
  SCHEDULE-001 merge `3592593`; extended existing **CI-003** rather than create a duplicate ID.
  Attached `c122` through `make feature-init`, branch `ci/workflow-resource-impact-verification`.
- Added a versioned explicit impact map over complete committed/index/dirty/untracked inventories,
  rename/deletion/mode/symlink changes and bounded transitive regression consumers. Unknown,
  foundational/security/dependency/migration/workflow paths escalate **FULL**. Canonical local gate
  derives affected/full automatically; explicit `verify-full` remains available. Docs-only skips all
  Docker/product/static runtime stages; ordinary product changes skip workflow suites. Remote
  protected quality/integration/build remain exhaustive and retain coverage policy.
- Version **2** receipts preserve exact tree/base/branch/HEAD integrity and additionally record map
  digest, scopes/reasons, selected suites, actual commands/results, migration/build outcomes and UTC
  completion. Write/read independently rederive selection; stale, unsupported, incomplete or
  differently mapped evidence refuses delivery. Focused iteration writes no feature receipt.
- Registered exact positive ownership retirement for integration, migration, selected production
  builds and existing unique smoke fixtures, including caught INT/TERM, partial creation and cleanup
  failure. Exact IDs/names, foreign-user preflight/recheck and residual verification replace silent
  migration cleanup. Quality status/cleanup is worktree-scoped; proven finish retires it only after
  all existing Git/PR/primary checks. DEV/Review/UAT/Stable/production persistence is preserved.
  Ambiguous images, legacy unknowns and shared default BuildKit cache are retained/reported;
  no global prune or retroactive other-worktree cleanup was introduced.
- Focused offline tests: selector/inventory/receipt **15**, resource/runner/signals **13**, feature/
  delivery **37**, environment **29**, Preview **19**, UAT **19**; shell/Git helper fixtures pass.
  Workflow Ruff format/lint (**19 files**) and strict mypy (**13 runtime files + 1 UAT fixture**) pass.
  Whole product format/lint/type/API drift checks pass, measured serially at **55.61 / 118.19 /
  91.24 / 22.54 s** including Quality startup. They remain global for product safety, with their
  material cost documented. Graph remains **99 valid**; shell syntax and whitespace pass.
- Real disposable Schedule PostgreSQL **12 passed** in **35.18 s**; forced migration cycle passes in
  **30.04 s** (this source has no new revision: base/feature head both **0041**). Each retires its
  project/image with **zero** owned containers/networks/volumes. Derived Taxonomy frontend selection
  **29 passed across 4 files** in **35.40 s** including startup. Separate backend/frontend production
  builds pass in **6.64 / 3.05 s**, each exclusively owned image retired without deployment.
- Real synthetic isolation smoke passes exact target cleanup, stale network/volume, idempotence,
  preservation of nine non-target projects including two independently derived Quality owners, and
  actual linked-fixture finish safety/retirement. All **11 containers / 12 networks / 12 volumes**
  retire; real DEV/Review/UAT/Stable/production identities and final reports match their snapshots.
  Initial smoke reproduced exhausted default IPv4 pools and still cleaned all partial fixtures;
  synthetic isolation uses explicit unique IPv6 subnets, without changing product networking.
- [Handoff](ci-003-resource-impact-handoff.md) and [machine evidence](ci-003-resource-impact-evidence.json)
  distinguish real substage timings from four deterministic before/after selection/resource plans.
  Focused docs-plan commands took **0.346 s**, creating no Docker resources; no old/new end-to-end
  canonical timing or percentage is invented. Current Quality intentionally stays reusable;
  legacy/other-worktree resources and shared cache stay intact. Existing full product smoke scripts
  were adapted/statically checked, not claimed executed. Luna owns independent review and the final
  **FULL** canonical gate. CI-003 remains `implemented`; next product increment is **DASHBOARD-001**.
  Primary source/main unchanged; no staging, commit, push, delivery, attached-feature finish, DEV
  upgrade, product visual UAT or canonical verification occurred. **READY_FOR_VISUAL_REVIEW**.

## 2026-10-10 — SCHEDULE-001 independent final verification

- Independently reviewed the Schedule domain boundary, authenticated API and generated contract,
  target lifecycle/deletion behavior, Event transaction/idempotency, bounded queries, migration 0041,
  and focused frontend/context integrations. No product-policy blocker or functional/accessibility/
  responsive defect remains. Broad cross-application visual redesign remains deferred.
- Reproduced and fixed four stale pre-existing integration expectations exposed by revision 0041:
  the exact schema table set now includes `scheduled_activities`, and populated older-migration refusal
  assertions retain the actual Alembic head `20261009_0041`. All four focused PostgreSQL regressions
  pass; the complete isolated PostgreSQL integration suite passes **711 tests**.
- Live Schedule Preview review at 1440×844, 1024×844 and 390×844 verified filters, explicit create,
  completion with and without an Event, cancellation with retained terminal evidence, browser Back,
  keyboard focus and no horizontal overflow. A synthetic review-only activity was created then
  cancelled; seeded examples were left intact. No DEV, Stable Preview or production resources changed.
- Canonical `make feature-verify` passed: feature graph/workflow checks, repository formatting/lint/
  strict typing, backend tests and coverage policy, frontend strict typecheck and **557 tests across 57
  files**, generated OpenAPI/TypeScript drift, isolated PostgreSQL integration, production backend/
  frontend builds, migration 0041 downgrade/re-upgrade verification, whitespace and a per-worktree
  receipt for this final reviewed tree.
- SCHEDULE-001 is `verified` in `docs/features.json`. Delivery, `make feature-finish` and
  `make dev-upgrade` remain the next authorized lifecycle steps; migration 0041 requires the DEV
  upgrade after successful delivery. See [handoff](schedule-001-handoff.md).

## 2026-10-10 — SCHEDULE-001 scheduled collection activities implemented

- Initialized attached `dcdf` through guarded `make feature-init`, branch
  `feat/schedule-001-collection-activities`, from `8eece520408679579114677b3e2537e23f357b4b`.
  The roadmap named SCHEDULE-001 but the base 98-entry feature graph omitted it; exactly one
  canonical entry reconciles the omission. No existing feature record/status changed.
- Added retained future intentions with complete date-only due days, eight narrow activity kinds,
  optional exact BotanicalIdentity/SeedLot/Sowing/Plant/PlantGroup/Location targets, explicit
  planned/completed/cancelled states and derived overdue. Timestamp/epoch coercion is rejected;
  browser grouping and displayed day share the returned device-day projection across midnight.
- Owner/Origin/CSRF-protected APIs use row locks and versions. Completion without Event creates no
  occurrence or History item. Explicit compatible Plant/PlantGroup Event recording invokes the normal
  service atomically, with independently entered occurrence day/notes, durable restrictive linkage
  and exact retry idempotence. Inactive references remain understandable; no lifecycle cascade or
  target inference. Migration `20261009_0041` adds only Schedule; populated downgrade refuses and
  empty downgrade/re-upgrade preserves unrelated records.
- Added Activity → Schedule with active date groups, canonical URL filters, bounded Dashboard
  counts/upcoming records and Plant/PlantGroup/SeedLot/Sowing detail context/preselection. Existing
  TaskDialog/ReferencePicker patterns retain accessible confirmations, focus, retry and stale-form
  recovery. Filters are initially collapsed for mobile access. Calendar, Schedule Saved Views,
  recurrence, notifications, attachments and generic task-management capabilities remain deferred.
- Focused checks: backend **93 passed**, `--no-cov`, Schedule/Event/Event schemas/History/Saved Views/
  Location/BotanicalIdentity service/API; real PostgreSQL **52 passed** (Schedule **12**, Event API,
  History and Saved Views), including actual two-session races, target lifecycle/deletion races,
  atomic rollback, API security/filters and migration preservation. Backend Ruff format/lint and strict
  mypy (**336 files**) pass; UAT fixture scoped Ruff and strict mypy (**1 file**) pass.
- Frontend **197 passed across 9 files** (Schedule/App/lazy App/Plant/Sowing/SeedLot/Journal/History/
  Saved Views), full strict TypeScript/ESLint, affected Prettier and asset build. Final inactive-label
  correction additionally passes **20 tests** (Schedule **16**, ReferencePicker **4**), strict
  typing, focused lint/format and asset build. The shared picker keeps its original default wording;
  Schedule preserves transferred/converted/exhausted labels. Fixed duplicate initial reads that
  could mask a load error; retry and session-expiry regressions pass. Existing navigation expectations
  include Schedule and await Journal readiness. No assertions/timeouts were weakened.
- Workflow regressions: `scripts/test-uat-preview.py` **19 passed** and
  `scripts/test-environment-workflow.py` **29 passed**. Guarded UAT up/seed/status and repeated seed
  succeed. `make api-generate` and `make api-check` pass; final backend OpenAPI export check confirms
  no drift after date validation. Structural API audit finds only six new paths/ten new schemas,
  with all existing contracts unchanged. Feature graph **99 valid**; final docs formatting and
  `git diff --check` pass. Final production backend/frontend image builds pass (`make build`), without deployment.
- Retired the prior `748b` Preview through its exact owning guarded remove command, as authorized;
  `dcdf` Preview remains healthy at <http://localhost:15174>, schema **0041**, with **53** manifest
  records and additive synthetic Schedule examples. Repeated seed preserves edits. Browser review
  covered 1440×844, 1024×844 and 390×844 without horizontal overflow, native keyboard date reschedule,
  create/context across all four detail types, no-Event completion, independent November due/October
  linked occurrence, cancellation, terminal evidence, Back, focus containment/Escape and mobile More.
  Synthetic operator review records remain explicit; no personal collection data was used.
- [Schedule contract](schedule.md) and [implementation handoff](schedule-001-handoff.md) record scope,
  date/target/completion policy, checks and UAT readiness. SCHEDULE-001 is **implemented**, pending
  Luna visual review/canonical verification. PHYLOGENY-001 remains planned/SOURCE_BLOCKED,
  TAXONOMY-003 verified, BOTANY-003/004 and ENRICHMENT-002 planned. Primary remains clean; no DEV,
  Stable Preview or production services/data were changed. No `make feature-verify`, staging,
  commit, push, delivery, finish or DEV upgrade occurred. **READY_FOR_VISUAL_REVIEW**.

## 2026-10-09 — PHYLOGENY-001 source audit blocked before implementation

- Initialized attached `4aaf` through `make feature-init`, branch
  `feat/phylogeny-001-collection-tree`, from clean current origin/main `33f5592`.
  Audited all 98 feature owners/dependencies; existing PHYLOGENY-001 remains planned.
- Securely inspected actual Open Tree archive/current API: **opentree16.1**, **OTT 3.7draft3**,
  December 2025 completion rather than the release page's inconsistent June text. Archive
  **41,608,973 bytes**, SHA-256
  `c447c83e49f0cf61fa96d9a02c6135b809abf315ad384fdb26b88359a28da12c`.
  Verified induced-subtree capability, actual public-name candidates, mixed/taxonomy support,
  conflicts and long unary/ancestral paths; no inferred WFO↔OTT mapping or branch dating.
- Exact data-rights gate **SOURCE_BLOCKED**: current conditional CC0 terms plus mixed/unlicensed
  source repository, nine pinned input snapshots (three CC0, one empty, five missing license fields)
  and no release-specific license did not establish current redistribution scope for the exact
  synthetic result with required annotations. The producer's positive **2017 synthetic/OTT CC0
  declaration** is explicitly retained, not ignored; no prohibition on synthetic reuse is claimed.
  Recorded a precise reopening criterion and minimal derived-content boundary in the
  [source decision](phylogeny-001-source.md), [planned contract](collection-phylogeny.md) and
  [blocked handoff](phylogeny-001-handoff.md). No product implementation follows a failed source GO.
- Focused existing offline baseline: **54 passed**, `--no-cov`, taxonomy source/service/API and
  Species distribution/Native ranges Explore. Reused installed UAT development image with current
  source read-only, network disabled and no application/database volumes; no new build under host
  disk/swap pressure. Feature graph **98 valid**. Pinned Prettier passes all seven changed documents;
  `git diff --check`, local documentation links and final scope audits pass.
- Canonical `make feature-verify` passed: repository lint/format/type checks, backend **895 passed**
  (90.03% coverage), frontend **541 passed**, PostgreSQL integration **699 passed**, generated API
  drift check, production backend/frontend builds, and migration cycle (**no Alembic revisions
  added**). It recorded the verified working-tree receipt. Verification reran after this progress
  correction; no migration or DEV upgrade is applicable.
- Read-only UAT status confirms actual `748b` owner, frontend/backend/db healthy and migration
  **0040**; source mismatch correctly refuses takeover from `4aaf`. Existing Taxonomy UAT preserved.
  No UI, API generation, migration, index, confirmed OTT fixture, PostgreSQL implementation suite,
  frontend phylogeny tests, performance/render benchmark or visual review claimed. Primary was clean
  at source-gate stop; no DEV/Stable Preview/production changes or migration step is applicable.
- TAXONOMY-003 stays verified. TAXONOMY-001/002, BOTANY-003/004 and ENRICHMENT-002 stay planned;
  SCHEDULE-001 and broad cross-application visual review remain deferred. **SOURCE_BLOCKED**,
  not READY_FOR_VISUAL_REVIEW. This is audit documentation only; no visual product review applies.

## 2026-10-09 — TAXONOMY-003 collection-aware classification implemented

- Initialized attached `748b` through `make feature-init`, branch
  `feat/taxonomy-003-collection-tree`, from verified cached origin/main `a8ae74a`.
  Securely audited the complete official WFO Plant List 2026-06 ColDP archive and publisher
  exporters before implementation. Classification-only CC0 source GO pins checksum, release,
  exact parent/synonym semantics and the biological Plantae boundary; no TLS bypass or HTML scraping.
- Added optional ignored 394 MiB local SQLite hierarchy index and one canonical operator-confirmed
  WFO relationship per BotanicalIdentity. Explicit local search → inspect → Confirm, stale/version
  revalidation and unlink preserve local names/profiles/other providers and material Lineage.
  Migration `20261009_0040` adds only links and refuses populated downgrade.
- Reused shared EXPLORE-001/002 representation/category projection for collection-pruned paths,
  distinct identity counts, literal local search, family/genus details, unresolved knowledge,
  full identity breadcrumbs and taxonomy-only Related in my collection. Responsive keyboard tree,
  stable URL filter/selected-node state; Saved Views deliberately deferred.
- Implementation-focused suites passed: **96 offline backend tests**, **58 PostgreSQL tests**
  (including concurrent confirmation, migration preservation and Explore/provider regressions),
  **19 UAT workflow tests**, and **104 distinct frontend tests**. Final independent gate results are
  recorded below and in the [handoff](taxonomy-003-handoff.md).
- Initial implementation measurements under concurrent image/build load included a 34.48 s first
  UAT projection and a 6.93 s checksum-only run. Independent post-restart review with no image/build
  process running rendered the six-identity UAT Taxonomy view in 8.84 s and an immediate page reload
  in 1.07 s. The host still had load 3.78, 1.9/2 GiB swap used, and 1.1 GB free disk. A separate
  same-UAT-database measurement returned 6 identities, 23 required nodes, one unresolved identity,
  13,226 UTF-8 serialized-model bytes, and constant 2 PostgreSQL SELECTs + 3 SQLite statements;
  first/warm same-process projections took 1.84 s / 22 ms with the index already OS-cached. The
  34.48 s many-tens-of-seconds delay did not recur, though this was not an unpressured host baseline.
  A 500-identity synthetic test returns five nodes in 299 ms.
- Retired old Preview only through actual owner `16cc` guarded remove; current `748b` UAT seeded
  with 44 manifest records, five exact real WFO links, same-genus/family coverage and unresolved
  lavender. Repeat seed preserves edits. Initial frontend health deadline during initialization
  recovered without timeout changes: status reports correct source, 0040, healthy app/db, proxy 200.
  Functional browser review covered 1440×844, 1024×844 and 390×844, keyboard focus/expansion,
  node detail, related peers, breadcrumb and advisory source-synonym inspection without overflow.
- TAXONOMY-003 is **verified**. TAXONOMY-001/002, PHYLOGENY-001, BOTANY-003/004 and ENRICHMENT-002
  remain planned; broad cross-application visual review stays deferred.

## 2026-10-09 — BOTANY-003 source re-audit; narrow description source approved

- Initialized the attached `857e` worktree through `make feature-init`, branch
  `feat/botany-003-profile-enrichment`, from clean current cached origin/main `345e9f2`.
  Audited the complete two-field approved contract and delivered ENRICHMENT-001 implementation.
  Fresh host curl, existing development/runtime HTTPX and newly built worktree HTTPX rejected the
  exact official Flora of China archive before HTTP bytes; verified OpenSSL still shows the missing
  issuing intermediate and fatal error 20. Official static WFO Plant List release 2026-06 is a
  taxonomy source candidate, not proof of a replacement descriptive-content artifact.
- Independently retrieved WCVP v15 securely: **89,508,082 bytes**, SHA-256
  `693e05b31ea6ce724c88ccf38bb964db2f22424b396f7ed1fd04fdb203af7e81`, actual retrieval
  **2026-10-09T12:32:17.250119Z**. Complete **1,441,152** names-row scan confirms distinct
  geographic_area prose; source-field GO remains separate from structured ranges. No invented
  description, range-derived prose, provider ID crosswalk, TLS exception or page scraping.
- Separate source discovery securely inspected three complete official SEPASAL CSVs: taxa,
  major-use references and note references. Dataset-specific CC BY 4.0, TaxKey, cultivation/use/
  toxicity categories and bibliographic joins make this a concrete future candidate for those fields;
  exact cultivation/use/warning field imports remain unapproved. A later bounded description review
  approved only three exact SEPASAL / Flora Zambesiaca records under the dataset's CC BY 4.0 license.
  This does not approve the remaining records or provide broad coverage.
- Preserved existing TAXONOMY-001 reconciliation and TAXONOMY-002 name-history owners. Added
  **planned TAXONOMY-003** collection taxonomy browsing, **planned PHYLOGENY-001** separate
  evolutionary-tree discovery and **planned BOTANY-004** other profile-field source review.
  Updated roadmap, approved/deferred domain requirements, source decisions and blocked handoff.
- Focused current baseline passed **72 backend unit tests**, `--no-cov`. Feature graph **98 valid**
  and `git diff --check` passed. Pinned Prettier 3.9.6 passed for all ten changed documents. No text implementation,
  migration, generated API, PostgreSQL text/concurrency checks, new frontend tests or visual QA is
  claimed; these remain pending at the source prerequisite. The quality baseline built its current
  development image. No canonical `make feature-verify`, staging, commit or delivery.
- Read-only UAT status confirmed healthy prior owner `16cc` and schema **0039**; source mismatch
  correctly refuses this worktree's takeover. Preserved that Preview and its review evidence because
  no BOTANY-003 UI exists. Primary source and DEV/Stable Preview/production state were not changed.
  BOTANY-003 remains **planned**. Its exact Flora of China source is **SOURCE_BLOCKED**; the three
  reviewed SEPASAL records are a narrow `DESCRIPTION_SOURCE_GO`, insufficient for general
  BOTANY-003 implementation. This is not READY_FOR_VISUAL_REVIEW.
  [Current sources](botanical-profile-enrichment-sources.md), [separate discovery](botanical-knowledge-source-audit.md),
  [future taxonomy](collection-taxonomy-plan.md), [blocked handoff](botany-003-handoff.md).

## 2026-10-09 — ENRICHMENT-001 independent verification

- Operator UAT and independent domain/UI review passed. The independent final gate initially found
  one stale integration assertion: a populated downgrade from the new `20261009_0039` head
  correctly rolls back transactionally at `0039`, but the prior test expected `0038`. Updated the
  expected current revision; the focused reproduction passed and the full canonical gate then
  passed on the final tree.
- `make feature-verify` passed: **95 feature records valid**, **856 backend unit tests** with
  **90.04% coverage**, **534 frontend tests**, **693 PostgreSQL integration tests**, strict mypy
  (**317 files**), Ruff/format, Prettier/ESLint, strict TypeScript, OpenAPI drift, production build,
  migration verification and whitespace checks. A tree-specific verification receipt was recorded.
- Integration first could not allocate a Docker bridge because 14 unattached
  `florabase-quality-*` networks had exhausted the default pools. After inspecting their exact
  Compose labels, IDs, subnets and zero endpoints, only those verified quality orphans were removed
  explicitly. DEV, UAT Preview, Feature Review, Stable Preview, production and all running-container
  network assignments were preserved. The fresh integration project allocated and cleaned up its
  network successfully; the full gate passed without a Docker-pool or memory-pressure failure.
- ENRICHMENT-001 is **verified** and ready for reviewed local commit and protected delivery. Delivery,
  conservative finish and the required DEV upgrade for migration `20261009_0039` remain pending.
  Broad cross-application visual/product review, ENRICHMENT-002 and SCHEDULE-001 remain future work.

## 2026-10-09 — ENRICHMENT-001 structured native-range implementation

- Source GO preceded implementation: exact official **Kew WCVP v15** plain archive, README,
  complete schemas/rows and release-specific CC BY 3.0/citation were inspected. Retained SHA-256
  `693e05b31ea6ce724c88ccf38bb964db2f22424b396f7ed1fd04fdb203af7e81` and actual UTC retrieval.
  Explicit optional provisioning built the complete local **1,441,152-taxon / 1,986,879-assertion**
  SQLite index. It is ignored/excluded from Git/images; ordinary startup/API/Apply use no provider
  network. Missing source data preserves canonical ranges, profile editing and durable evidence.
- Added explicit WCVP taxon review/confirmation, frozen current-versus-proposed range evidence,
  a versioned twelve-unit literal TDWG/canonical crosswalk, visible excluded partial/split/unresolved
  units and original Native/Introduced/extinction/doubtful flags. Only explicit selected unqualified
  Native Apply adds existing `BotanicalProfileNativeRange` links; every current range is kept and
  no profile text or material origin changes. Removal/replacement is unsupported.
- Migration **20261009_0039** adds separate source links, monotonic destination revisions, frozen
  proposals and immutable applications. Locked source/link/identity/geography/destination/crosswalk
  checks reject stale/repeated Apply atomically, including edit-and-restore. Frozen v15 proposals
  can apply without the source index. Applied provenance survives manual edits/link changes and
  blocks identity deletion; deletion serializes with Apply. Empty downgrade preserves canonical
  ranges/text; any source link/proposal/application refuses populated downgrade.
- Source review is inside the existing BotanicalIdentity Reference → Native range module, with
  literal prefix search, exact IDs/accepted context, selective checkboxes, Add/Keep confirmation,
  immutable history/outcomes, source attribution, explicit retry and focused feedback. Corrected
  schema-name collisions with Media during generated-type verification and made source reprovision
  stale state/deletion feedback explicit. Updated the exact database table inventory and mock
  reference counts for the four intentional new tables; existing assertions remain strict.
- Final focused checks passed: **75 backend unit**, **81 disposable PostgreSQL integration**,
  **38 distinct frontend**, **19 host UAT guards**; Ruff/format, strict mypy (**315 files**),
  Prettier/ESLint/strict TypeScript, OpenAPI generation/drift, Vite production bundle, both production
  Docker runtime builds, **95-feature graph**, whitespace. Real PostgreSQL covers migration cycle,
  populated refusal, immutable evidence, stale state, concurrent Apply and Apply/deletion races.
  Production startup/health also passed with no source index, network disabled and read-only root
  plus ephemeral attachment tmpfs. Existing six Alembic path-separator deprecation warnings remain.
  Initial disposable subnet overlap was resolved using a free scoped subnet, with no product change.
- Guardedly retired the previous UAT through its owner `258f`, then started and explicitly seeded
  this worktree's **http://localhost:15174**, **preview / preview**, schema **0039**, fixture
  **v4 / 42 baseline records**. Startup's first health window expired during frontend dependency
  installation; frontend subsequently became healthy. Exact Aloe smoke added Oman, kept manual
  Thailand/Italy, refreshed canonical ranges and retrieved a fresh KEEP proposal; its source link
  and immutable application are retained for operator review. DOM/accessibility checks at
  **390×844, 1024×844 and 1440×844** showed no horizontal overflow and focused success feedback.
  No operator acceptance is claimed. No personal collection data or DEV/Stable Preview/production
  state was changed; primary checkout remains clean.
- At implementation handoff ENRICHMENT-001 was **implemented**, pending operator product UAT and
  Luna independent review; the later verification milestone above records its completed status.
  BOTANY-003's blocked text contract is unchanged; ENRICHMENT-002 automation, SCHEDULE-001 and broad
  cross-application product/visual review remain future. Tree stays **unstaged/uncommitted**;
  no canonical feature gate/receipt, commit, push, delivery, merge or finish was performed.
  [Source audit](native-range-enrichment-source-v15.md), [contract](native-range-enrichment.md)
  and [handoff](enrichment-001-handoff.md) retain exact evidence and review scenarios.

## 2026-10-08 — EXPLORE-002 independent final verification

- Independent review found the implementation aligned with the accepted collection-aware Native
  ranges contract and operator UAT. No production behavior defect was found. Three integration tests
  had stale hard-coded expectations for migration `0037`; those test assertions now read Alembic's
  current head, and their focused rerun passed.
- Canonical `make feature-verify` passed on the reviewed tree: **804 backend unit tests** at **90.06%
  coverage**, **528 frontend tests**, **673 PostgreSQL integration tests**, feature graph (**95 valid**),
  Ruff/Prettier/ESLint, strict mypy (**303 files**), strict
  TypeScript, API drift, both production image builds, migration cycle `0037 → 0038 → 0037 → 0038`,
  whitespace checks and a working-tree verification receipt.
- Migration `0038` is additive and passed its populate/refuse-downgrade and empty-cycle checks.
  Existing Alembic path-separator deprecation warnings remain. The operator accepted functional UAT;
  the broad cross-application visual/product review remains deferred before release hardening.
- EXPLORE-002 is `verified` and ready for its reviewed local commit and protected delivery. Delivery
  and `feature-finish` are still pending. Because this feature adds migration `0038`, successful
  delivery must be followed by `make dev-upgrade` on DEV. No production or Stable Preview state was
  modified.

## 2026-10-08 — EXPLORE-002 bounded operator UAT refinement

- The operator has now **accepted the current functionality for delivery**; broad visual/product
  review remains explicitly deferred across the application. Added explicit
  checkbox selection up to **20** identities, Selected species (N), deselection/Remove/View only/Clear,
  exact one-species detail and multiple-species distinct territory coverage with contributor lists.
  Per-identity broad/precise overlap counts once. Missing/filter-excluded IDs remain explicit and
  contribute no coverage; no query-wide selection or arbitrary replacement.
- Added OR **Collection records** filters for Seeds/Sowings/Plants/Plant groups/Stored material.
  Status remains single-select; Current qualifies active selected-category records, Living qualifies
  selected Plant/PlantGroup records, Historical requires retained selected-category evidence and
  globally no Current representation. Directory/overview/selection share all eligibility filters.
  New bounded comparison endpoint uses **2 SELECTs**, including twenty-ID requests; existing 2/4/4
  directory/overview/exact-detail query bounds remain. No domain/provider writes.
- Canonical repeated-ID/category URL and Saved View v1 sets restore deterministically; singular v1
  UUID state remains readable. No additional migration beyond **0038**. Desktop Explore now places
  Botanical identities/Media/Geography before non-actionable **Maps** text and the three unchanged
  map destinations; mobile remains flat with every destination.
- Audited official Kew WCVP/POWO sources and the complete **95-feature** graph. Refined existing
  **planned ENRICHMENT-001** for a separately reviewed structured-native-range candidate immediately
  after EXPLORE-002 delivery, before SCHEDULE-001 unless reprioritised. Exact reviewed taxon matching,
  TDWG crosswalk, provenance and operator-reviewed replacement remain future decisions. BOTANY-003
  stays unchanged. Recorded the later broad cross-application review checkpoint before release hardening.
- Final focused checks: **97 backend unit**, **39 disposable PostgreSQL**, **152 distinct frontend**
  tests (151 main-run passes plus corrected route-order test rerun), **23 read-only UAT runtime/fixture**,
  **19 host guard**; Ruff/format, strict mypy on 6 changed source files, CLI import lint,
  frontend Prettier/ESLint/strict TypeScript, Vite production build, API generation/drift, feature graph
  and whitespace passed. Existing 18 Alembic warnings remain. No full canonical gate/receipt is claimed.
- Task-owned UAT stays healthy at **http://localhost:15174/#/native-ranges**, **preview / preview**,
  schema **0038**, fixture **v4 / 42**. The explicit additive stored-material extension and repeated
  seed preserve existing operator edits/inventory; no reset. DOM/accessibility checks at
  **1440×844, 1024×844, 390×844** confirmed comparison, filter exclusion, one-species links,
  refresh and mobile IA without horizontal overflow. No screenshots.
- At this handoff the feature tree remained **unstaged/uncommitted**. The operator has authorized
  independent review, canonical verification, commit and protected delivery; the final verification
  evidence is recorded above.
  See [updated handoff](explore-002-handoff.md) and [source audit](native-range-enrichment-audit.md).

## 2026-10-08 — EXPLORE-002 implementation and UAT handoff

- Added the separate Native ranges Explore workspace with Collection overview and Selected species.
  Reused GEOGRAPHY-002's exact profile-owned range relationships and EXPLORE-001's representation,
  lifecycle/inventory scopes and literal search. No occurrence, prose or material-provenance inference.
  Broad/precise overlaps count distinct identities once per map territory; exact relationship lists
  retain broad, disjoint, custom and unavailable places without rewriting stored knowledge.
- Reviewed and pinned Natural Earth 1:110m Admin 0 map units (dataset 5.1.1, repository v5.1.2,
  public domain). Bundled 179 SVG paths in a separate lazy geometry chunk, **150.83 kB / 60.46 kB
  gzip**, with exact ISO mapping and canonical M49 descendant drawing primitives. Missing/custom
  boundaries stay explicit. Raw JSON parse median/p95 **0.56/0.99 ms** in local Node; this does not
  measure device paint. No runtime geometry/provider fetch or GIS persistence/library was added.
- Added authenticated bounded directory/overview/selection endpoints with constant **2/4/4 SELECTs**,
  summary totals independent of pagination and HTML map/count/precision companions. Canonical URL
  and private v1 Native ranges Saved Views persist stable scope/search/mode/identity/filter only.
  Migration **0038** solely extends the surface constraint and locks/refuses incompatible downgrade.
- Focused checks passed: **93 backend unit**, **38 isolated PostgreSQL** and **147 frontend** tests;
  Ruff/backend formatting (**344 files**), strict mypy (**303 files**), CLI syntax/import checks,
  geometry reproducibility, frontend Prettier/ESLint/strict TypeScript, `make api-generate`,
  `make api-check`, feature graph (**95 valid**), both final production image builds and
  `git diff --check`. After lint corrections, the **60 affected frontend tests** and Vite build
  passed again; see [handoff](explore-002-handoff.md). Existing 18 Alembic
  path-separator warnings remain; exhausted default Docker address pools were handled with an
  isolated subnet in the disposable final PostgreSQL project, which cleaned its own resources.
- Retired previous `c6cd` UAT through its owning guarded command, started this worktree, corrected
  an initial malformed fixture call and recovered only the incomplete synthetic preview through
  guarded reset. UAT is healthy/current at **0038**, fixture **v4 / 41 records**; repeated seed and
  **21 read-only runtime/fixture checks** plus **19 host guard tests** passed. All 5 / Living 2 /
  Current 4 / Historical 1, broad+Brazil overlap, disjoint Italy/Thailand, custom and no-range examples
  are ready at **http://localhost:15174/#/native-ranges**, **preview / preview**.
- DOM/accessibility inspection covered overview/selection at **1440×844, 1024×844 and 390×844**,
  wrapping, mobile navigation, native manager link, Saved View dialog and clear-selection focus;
  no horizontal overflow or screenshot artifacts. Operator visual/product UAT remains pending.
  EXPLORE-002 is **implemented**, all changes unstaged/uncommitted. Canonical `make feature-verify`,
  independent review, commit and delivery remain Luna's responsibility. Primary, DEV, Stable Preview
  and production runtime state were not modified. SCHEDULE-001 remains future; biological daily-use
  candidates remain next choices and BOTANY-003 stays blocked/unchanged.

## 2026-10-08 — EXPLORE-001 independent verification

- Independent final review found no production behavior defect. Collection projections, exact provider
  link use, query/paging bounds, Saved View/URL restore behavior, migration downgrade protection and
  the no-inference/no-persistence boundaries matched the accepted contract and passed operator UAT.
- Canonical `make feature-verify` passed on the reviewed tree: **797 backend unit tests** at **90.06%
  coverage**, **508 frontend tests**, **662 isolated PostgreSQL integration tests**, feature graph
  (**94 valid**), workflow helpers and static policy, Ruff/Prettier/ESLint, strict mypy (**299 files**),
  strict TypeScript, API drift, both production image builds, migration cycle
  `0036 → 0037 → 0036 → 0037`, whitespace checks and a working-tree verification receipt.
- Disposable PostgreSQL integration and migration-cycle resources were cleaned by their workflows.
  Existing Alembic path-separator deprecation warnings remain. Operator UAT had already passed; no
  product code changed after acceptance.
- EXPLORE-001 is `verified`; this tree is ready for its reviewed local commit, protected delivery and
  `feature-finish`. Migration `0037` means successful delivery must be followed by `make dev-upgrade`.
  Next after delivery: separate **EXPLORE-002 — Native ranges**; SCHEDULE-001 remains future and
  BOTANY-003 remains blocked/unchanged.

## 2026-10-08 — EXPLORE-001 implementation and UAT handoff

- Added authenticated bounded collection-aware identity discovery and Species distribution under
  Explore. Exact SeedLot/Plant/PlantGroup, Sowing → SeedLot and managed inventory → Harvest → source
  relationships define All represented, Living, Current and Historical. Historical excludes identities
  with any current representation; terminal/reversed/reintegrated evidence is retained. Grouped SQL
  yields unique identities and two SELECTs for totals/page, with literal search and deterministic paging.
- Reused MAP-002 unchanged for deliberate one-identity occurrence loading, quality policy, density,
  attribution and privacy. Discovery/selection/Saved Views perform no provider requests. No occurrence
  persistence, scientific-name rematching, native-range inference or Collection origins change.
- Added canonical local URL/v1 Saved View state with explicit stale/missing selection and same-view
  page-one/unloaded-map reset. Migration `20261008_0037` extends only the surface constraint and
  safely refuses populated downgrade under a writer lock; compatible cycles preserve existing views.
- Initial focused verification: **115 backend unit**, **35 isolated PostgreSQL**, **130 frontend** tests and
  **20 guarded fixture** tests passed. Ruff/backend formatting (**339 files**), strict mypy (**299
  files**), focused workflow-script policy/typing, frontend Prettier/ESLint/strict TypeScript,
  `make api-generate`, `make api-check`, feature graph (**94 valid**), both production runtime image
  builds, frontend Vite build and `git diff --check` passed. Existing Alembic path-separator warnings
  remain. Canonical `make feature-verify` was deliberately not run.
- After explicit operator approval, retired the old owning UAT with its guarded command and started
  this worktree's preview. Healthy source/schema `0037`, fixture v3 (**38 records**), repeated seed
  idempotence and baseline guards verified. Living basil/aloe, Current non-living lavender, Historical
  long-cultivar radish and excluded reference-only Viola support UAT; basil has the reviewed real
  CoL XR `48GBK` link, seeded offline through existing confirmation with no fabricated occurrences.
- Operator UAT passed. Independent route inspection confirmed the four expected identities, one locally
  occurrence-ready link and reference-only exclusion. A narrow viewport inspection showed vertical flow
  and wrapping of the long cultivar; automated tests cover explicit map load and error/zero states. No
  screenshot files saved. Preview:
  **http://localhost:15174/#/species-distribution**, **preview / preview**.
- EXPLORE-001 was `implemented` pending the independent review recorded above. EXPLORE-002 Native ranges is the preferred next separate increment;
  SCHEDULE-001 remains future and BOTANY-003 blocked/unchanged. See [handoff](explore-001-handoff.md)
  and [contract/lifecycle matrix](species-distribution.md). Primary checkout is clean at the base SHA.

## 2026-10-08 — ORDER-001 independent final verification

- Independent review found no Order, acquisition reconciliation, migration, security, or navigation
  behavior defect. The full canonical `make feature-verify` passed on the reviewed tree: feature graph
  (93 valid), workflow guards, Ruff/Prettier/lint/strict typing, **787 backend unit tests** (90.01%
  coverage), **503 frontend tests**, generated API drift, **645 PostgreSQL integration tests**,
  production backend/frontend builds, migration cycle `0035 → 0036 → 0035 → 0036`, whitespace checks
  and a working-tree verification receipt.
- The first frontend run exposed an obsolete UX-001 test expectation for the navigation group formerly
  called “Reference.” Production navigation correctly uses the approved “Explore” and “Sourcing” groups;
  only the stale test assertion was updated. The full gate passed after that test-only correction.
- ORDER-001 is now `verified` after operator UAT and independent review. Changes remain unstaged and
  uncommitted; protected delivery and local finish are the next authorized steps.

## 2026-10-08 — ORDER-001 purchase-context UAT refinement

- Replaced isolated Order selection with one authoritative purchase-context preview/resolve service
  used by SeedLot → Order, Order → existing lot and Order → new lot. Selection is read-only;
  existing Apply atomically saves reviewed acquisition fields/link while preserving independent
  material fields and other form drafts. Both Order/SeedLot versions are checked under consistent
  locks; stale refusal applies nothing. Creation revalidates confirmed fields and Order version.
- Purchased kinds stay exact; Unknown proposes Purchased. Incompatible known sources require a valid
  explicit saved correction. Blank Supplier proposes fill; known mismatch requires confirmation,
  including conflicts hidden by an unsaved Supplier draft. Unknown Order Supplier preserves known
  lot Supplier. Order Supplier edit refuses linked-lot contradictions without automatic synchronization.
- Acquisition is vertical with exact read-only Order/transaction information and Supplier-aware bounded
  search plus explicit Show all. Origin stays separate; Order total is never a lot price. Optional
  Order-date copy is unchecked by default, preserves PartialDate precision and never overwrites a
  differing receipt date silently. Unlink retains confirmed Source/Supplier/date values.
- Final backend regressions: **52 passed**; whole Ruff/format and strict mypy (**292 files**) pass.
  Real disposable PostgreSQL: **645 passed**, including **27 new reconciliation tests**; its helper
  cleaned only its own resources. OpenAPI drift and both production runtime image builds pass.
  Frontend: **50 passed across 4 focused files**; whole ESLint, strict TypeScript, Prettier and
  generated API drift pass. Feature graph: **93 valid**; no additional migration.
- Guardedly resumed owned UAT without resetting data. Fixture v2's **34 baseline records** and operator
  edits remain intact; four labelled synthetic extra lots support blank/Unknown, matching Supplier,
  conflicting Supplier/differing year and confirmed month-only date-copy scenarios. Browser checks at
  **1440×844, 1024×844 and 390×844** verified proposals, Cancel/Escape, reverse Apply and refresh,
  transaction price distinction, new-lot precision, unlink retention and no horizontal overflow.
  No screenshots were taken and viewport was reset. Preview: **http://localhost:15174/#/orders**,
  credentials **preview / preview**; see [handoff](order-001-handoff.md) for exact examples/evidence.
- At this historical UAT handoff, ORDER-001 remained `implemented`; its independent review and
  canonical verification were still pending.

## 2026-10-08 — ORDER-001 implementation and visual handoff

- Implemented explicit purchase transactions with optional Supplier, precision-preserving Order
  date, normalized non-unique reference, exact non-negative decimal total/paired currency and notes.
  Purchased/purchased-fruit SeedLots may explicitly link/unlink/relink one Order; known Suppliers
  must agree on both edit paths. Order row locks serialize these checks. Referenced deletion is
  refused; no backfill, automatic lots, quantity/lifecycle/date/origin/Location or lineage effects.
- Added bounded authenticated REST/directory/detail and compact create/edit dialogs, authoritative
  counts, exact Supplier/SeedLot navigation and normal SeedLot creation with only purchase context
  prefilled. Orders Saved Views restore canonical filters at page one. Direct Order Global Search
  joins Suppliers under Sourcing without linked-botany matching or expanding History.
- Applied the approved IA: Collection includes Locations; Explore contains Botanical identities,
  Media, Geography and Collection origins; Sourcing contains Suppliers/Orders. Page eyebrows,
  keyboard disclosures, active-group expansion and mobile reachability follow that mapping.
  Collection origins retains `#/map` and internal `provenance_map`; its copy describes recorded
  collection material origins. EXPLORE-001 Species distribution and EXPLORE-002 Native ranges remain
  roadmap-only candidates; SCHEDULE-001 stays future Activity work and BOTANY-003 is unchanged.
- Migration `20261008_0036` adds Orders, restrictive nullable SeedLot links, money/date/source checks,
  justified indexes and the Saved View surface. It preserves old lots and refuses downgrade with
  Orders or Orders Saved Views. Real PostgreSQL: **618 passed**, including **21 Order integration
  tests**; standalone disposable migration cycle **0035 → 0036 → 0035 → 0036 passed**. Six old
  schema/head expectations were corrected after the initial integration run; the fresh full run passed.
- Focused backend regressions: **178 passed**. Whole backend Ruff/format and strict mypy (**288
  files**), generated OpenAPI/TypeScript drift, feature graph (**93 valid**) and production backend
  runtime build passed. Focused frontend regressions: **187 passed across 11 files** (182 in the ten
  unaffected final-run files, then all five in the corrected Supplier suite). Whole-frontend ESLint,
  strict TypeScript and Prettier plus targeted lint on final edits passed. SeedLot tests now preload
  their screen; Supplier photo actions await their own controls. Existing assertions/timeouts and
  dedicated lazy-loading tests remain intact. Frontend production build evidence is in the handoff.
  Changed UAT scripts pass canonical workflow Ruff/format and strict fixture mypy;
  `make test-uat-preview` and real read-only fixture/guard tests each passed **19 tests**. No policy or
  timeout was weakened.
- Guardedly retired the prior ed24-owned UAT through its supported remove command, then started,
  explicitly seeded twice and checked this worktree's UAT. Services are healthy at revision 0036;
  fixture v2 has **34 baseline synthetic records**, including two independent Basil packets in one
  EUR purchase and a month-only purchase with unknown Supplier/price. Operator edits and extras are
  retained on re-seed. DEV, Stable Preview, Feature Review and production were not operated.
- Browser interaction/DOM/layout checks at **1440×844, 1024×844 and 390×844** covered Orders, forms,
  exact money/date/unknown knowledge, long references, linked lots, Supplier/SeedLot context, Add seed
  lot prefill, Saved Views, Global Search, sidebar keyboard/active expansion, mobile More and Collection
  origins vocabulary. Inspected views had no horizontal overflow. A development reference-load
  interruption recovered through Retry. No screenshots were taken; temporary viewport was reset.
  UAT is ready at **http://localhost:15174/#/orders**, credentials **preview / preview**. Operator
  visual/product acceptance remains pending.
- ORDER-001 is `implemented`. All work remains unstaged/uncommitted; no canonical feature gate,
  push, delivery, merge or finish. Luna owns independent review, verification and reviewed commit
  after operator UAT. See [implementation handoff](order-001-handoff.md) and [Order contract](orders.md).

## 2026-10-08 — HISTORY-001 independently verified

- Operator UAT passed, including the accepted Activity/navigation refinement. The independent review
  found no product or workflow defect. It corrected three pre-existing SeedLot test selectors that
  became ambiguous with the new History destination, and updated two migration-test head assertions
  for revision `20261007_0035`; the affected focused suite and final complete suites passed.
- `make feature-verify` passed on this tree: feature graph (93 valid), workflow helper/static checks,
  formatting, lint and typing, backend tests (**749 passed**), frontend Vitest (**474 passed across
  48 files**), isolated PostgreSQL integration (**597 passed**), OpenAPI drift, production image
  builds, migration cycle through `20261007_0035`, whitespace, and a working-tree verification receipt.
- HISTORY-001 is now `verified` in `docs/features.json`. Collection productivity v2 is complete on
  protected delivery; Orders / Purchases follows. SCHEDULE-001 remains future work and BOTANY-003 is
  unchanged. Commit, delivery and finish remain the authorized next steps for this review.

## 2026-10-07 — HISTORY-001 operator-UAT Activity refinement

- Added accessible desktop disclosures for all six sidebar groups, expanded on first use, with
  browser-only collapsed-group persistence and active-route auto-expansion. Mobile retains its
  existing compact navigation/More pattern and every destination.
- Renamed the global Event destination/title and Saved View display label to **Journal**, retaining
  `#/events`, the `events` surface, Event model/API/kinds and all existing category membership.
  Permanent Journal/History purpose copy links the two roles; correction/history help stays secondary.
  Journal rows prioritize date, kind, Plant/Group target, bounded notes and secondary related links.
- Refined History into a compact chronological rail/list with explicit pressed **All activity** and
  multi-category chips, compact record/year controls and Clear year. PartialDate/Recorded labels,
  canonical URLs, page-one Saved Views, projection/dedup/date/query semantics and migration 0035
  remain unchanged. No scheduling or domain persistence is added; roadmap sequencing stays intact.
- Checks: **88 backend unit** tests and **123 isolated PostgreSQL** tests passed; **181 frontend**
  tests across 12 files passed (172 in ten files, final corrected two-file rerun: nine). Whole-frontend
  zero-warning ESLint, strict TypeScript and Prettier passed; final test edits also passed targeted
  lint/format and strict type checking. Both API drift checks, backend/frontend production image
  builds, feature graph (**93 valid**) and `git diff --check` passed. No policy or timeout was weakened.
- Browser: Journal/History reviewed at **1440×844 and 1024×844**; sidebar keyboard/focus,
  collapse/refresh persistence and active-group expansion, Saved Views and multi-category/year
  Apply/Clear URLs checked. At **390×844**, History orientation/filter wrapping, semantic states,
  timeline DOM and all More destinations had no horizontal overflow. Browser control then became
  unavailable (empty browser inventory); mobile Journal and scrolled timeline/long-label visual
  review remain operator items, and the temporary viewport could not be reset. See the handoff.
- Read-only UAT status confirms live ed24 source, healthy services, revision `20261007_0035`,
  fixture v1 / 31 baseline records and existing edits preserved. This pass did not reset/reseed UAT
  or mutate operator records. Everything remains unstaged/uncommitted; no push/delivery or canonical
  `make feature-verify`. Operator UAT has passed; HISTORY-001 remains `implemented` pending this
  independent canonical verification and delivery.

## 2026-10-07 — HISTORY-001 implementation and visual handoff

- Implemented the read-only Activity → History projection over existing Events, propagation receipts,
  germination observations, structured Harvests, material dispositions and seed conversions. Owned
  backing Events/receipts/dispositions collapse to one operation; corrections retain typed keys.
  PartialDate precision, explicit Recorded fallback, persisted reversal status/instants and current-state
  exclusions remain truthful. No History table, audit log, mutation or scheduling capability is added.
- Added globally ordered SQL pagination/filtered totals in one joined query, typed authoritative links,
  canonical URL filters and History Saved Views. Migration `20261007_0035` extends only the SavedView
  surface check and refuses downgrade while History views exist. History uses the established
  workspace/navigation vocabulary and exact retained inventory focus within Harvest detail.
- Focused backend unit regressions: **230 passed**; real PostgreSQL regressions: **123 passed**,
  including source/dedup/date/query bounds and downgrade/re-upgrade safety. Frontend regressions:
  **161 passed across 9 files** (160 in the main run plus the separate transition test), including
  complete App navigation. Ruff formatting/lint, strict mypy (**281 files**), whole-frontend
  zero-warning ESLint, strict TypeScript, Prettier, generated API drift, feature graph (**93 valid**),
  production backend/frontend image builds and whitespace passed.
- Browser review covers **1440×844, 1024×844 and 390×844**, keyboard filters, canonical URL,
  browser Back restoration, separate mobile Events/History navigation and Harvest deep links without
  horizontal overflow. Supported guarded UAT replacement, startup and fixture-v1 seed succeeded from
  ed24; DEV, Stable Preview, Feature Review, production and primary checkout were not modified.
- HISTORY-001 is `implemented`; operator visual UAT has passed and independent review/canonical gate
  remain for this delivery phase. Collection productivity v2 remains open; Orders/Purchases follows verified delivery.
  SCHEDULE-001 remains future work and BOTANY-003 is unchanged. No canonical gate, staging, commit,
  push, delivery, merge or finish was run. See [HISTORY-001 handoff](history-001-handoff.md).

## 2026-10-07 — BULK-001 independent final verification

- Operator UAT passed for the scoped multi-select and atomic Location moves. The reviewed scope
  includes five typed active collection kinds, transient selection, authoritative per-kind domain
  effects, current server preview, stale-state refusal, keyboard-accessible controls, responsive
  navigation and truthful directory counts. No schema migration is part of the increment.
- Independent review found no production or workflow defect across the full diff, domain effects,
  selection/Saved Views boundaries, API/auth/CSRF, concurrency and atomicity, query bounds,
  accessibility, navigation, result counts, generated contracts and documentation.
- `make feature-verify` passed: backend **735 passed** at **90.54%** coverage; frontend **462 passed
  across 46 files**; PostgreSQL integration **582 passed**; strict mypy (**274 files**), strict
  TypeScript, Ruff, Prettier, zero-warning ESLint, generated API drift, production builds, no-migration
  cycle, whitespace and working-tree receipt all passed. The feature graph validates **92 features**.
- The gate's initial run found a stale Sowing test stub returning `None` after the reference helper
  gained a tuple return for Location assignment. Only that test double was corrected; the focused
  lineage suite passed (**4 tests**) and the full gate then passed. BULK-001 is now `verified` in the
  graph. Documentation changes require a final receipt refresh before commit.

## 2026-10-07 — BULK-001 operator UAT refinements

- Moved Select into the Saved Views utility row and made active selection compact, with one primary
  Move action and lightweight Select visible / Clear selection / Done controls. Enlarged the typed
  Location chooser/dialog; safe opt-in backdrop/Escape dismissal restores Move focus, while pending
  Apply remains guarded. Target changes still invalidate preview and disable Apply.
- Added Botanical Identity Add plant shortcuts in Quick Preview and detail, reusing normal identity-
  prefilled Plant creation. Added shared quiet result metadata across Collection, Places and Reference
  lists using existing filtered responses and authoritative Media totals; no count queries/domain
  changes/migration. Existing map companion lists count matching sites; bare maps/details/forms do not.
- Focused frontend checks: **266 tests in 17 files passed**. Whole-frontend Prettier, zero-warning
  ESLint, strict TypeScript and production Vite build passed; `git diff --check` clean. Backend
  semantics are unchanged from the implementation evidence; no canonical gate was run.
- Browser review covered **1440×844, 1024×844 and 390×844**: utility/selection controls, searchable
  chooser, preview invalidation, backdrop/inside clicks, keyboard focus/trap/return, truthful list
  counts and Identity action/navigation/prefill. No horizontal overflow or new persistent UAT record
  edits. Supported UAT restart preserved fixture v1, 31 baseline records and prior operator edits.
- Operator visual acceptance passed; Luna is now performing independent final review and canonical
  verification. Everything remains unstaged and uncommitted until the verified-tree delivery phase.
  Details and count-source audit: [BULK-001 handoff](bulk-001-handoff.md).

## 2026-10-06 — BULK-001 implementation and UAT handoff

- Added bounded explicit typed selection and server Preview → Apply Location moves for active
  SeedLots, Sowings, Plants, PlantGroups and managed Stored material. Reuses owning assignment
  primitives and per-record Movement Events; revalidates all record/target versions under locks,
  including no-ops, and rolls back the entire batch on conflict. No migration, selection persistence,
  query expansion, generic bulk framework or additional bulk action.
- Selection clears on filter/search, directory/task navigation and identical Saved View reopening.
  Accessible toolbar/dialog supports keyboard focus, no-op/conflict feedback, directory refresh and
  filter retention. Historical Harvest remains excluded. Approved macroareas and page eyebrows
  preserve routes, titles, descriptions and mobile destination access.
- Focused checks: **172 backend unit/domain tests**, **195 real PostgreSQL integration tests**,
  **242 frontend tests in 10 files**. Ruff, strict mypy (**274 files**), Prettier, zero-warning ESLint,
  strict TypeScript, both generated API drift checks, frontend/backend production builds and the
  **92-feature graph** and `git diff --check` passed. PostgreSQL tests cover atomic rollback, stale record/target changes,
  all five kinds and 100-row query bounds. No verification threshold was weakened.
- UAT Preview ownership moved from c5e8 through the supported guarded retirement and b647 startup,
  seed/status workflow. Fixture v1/code and 31 baseline records are preserved. Normal synthetic UAT
  exercises added moves, one explicitly unknown-quantity tracked inventory and a filtered Saved View;
  DEV/Stable Preview/Feature Review/production are untouched. Services are healthy at
  `http://localhost:15174` with `preview / preview`.
- Browser review covered **1440×844, 1024×844 and 390×844**, supported selection/preview surfaces,
  keyboard focus/trap/Escape, no-op handling, wrapping/bounds, Saved View reset and Movement history.
  Two-tab stale testing encountered a CSRF refusal before mutation; domain stale/atomic safety is
  proven in PostgreSQL, while that browser scenario remains for operator review. Automatic approval
  review rejected an extra direct fixture mutation; it was not executed or bypassed.
- At the time of this implementation handoff, BULK-001 remained `implemented` pending operator UAT
  and independent review/canonical gate.
  Unified operational history remains next, Orders/Purchases later, BOTANY-003 unchanged and blocked;
  SCHEDULE-001 is only a later candidate. Source is unstaged/uncommitted; no `feature-verify`, delivery,
  merge, finish or DEV upgrade. See [the handoff](bulk-001-handoff.md).

## 2026-10-06 — VIEW-001 independent review and final verification

- Independent review covered owner isolation, typed/canonical state contracts, stale references and
  future-version management, Origin/CSRF/session boundaries, single-query bounded listings, migration
  safety, all thirteen frontend adapters, ordinary URL/history behavior and accessible directory chrome.
  No production behavior defect was found. Operator UAT had passed at 1440×844, 1024×844 and
  390×844, including keyboard order, visible focus, named controls/groups and overflow checks.
- The first canonical run exposed 89.88% backend coverage versus the existing 90% policy. Added
  focused Saved View service/API unit tests; the complete backend unit suite then passed **690 tests at
  90.36%**. Its PostgreSQL run passed **562 tests** and exposed one stale pre-VIEW-001 schema inventory
  assertion; updated that table inventory to include the new `saved_views` migration table.
- Complete frontend Vitest passed **436 tests in 43 files**; Prettier, zero-warning ESLint, strict
  TypeScript, Ruff and strict mypy passed. The final canonical gate is rerunning the corrected frozen
  tree, including full isolated PostgreSQL integration/migration, API drift and production builds.
- VIEW-001 is marked **verified** on the basis of accepted operator scenarios and independent review;
  the final tree-specific canonical receipt is produced by the in-progress gate. No implementation
  semantics or verification thresholds were weakened.

## 2026-10-06 — VIEW-001 final operator UAT directory chrome polish

- Visually hid redundant peer directory headings, search captions and operational lifecycle captions
  with the existing `sr-only` convention. Explicit search labels, named directory regions and native
  fieldset legends remain accessible. Meaningful section/filter headings and detail/form hierarchy
  are preserved; DirectorySearch opt-in leaves picker/linker/contextual searches unchanged.
- Kept heading/subtitle → Saved Views → search → filters → results. Plants' desktop lifecycle
  buttons align with Record type without stretching. This follow-up changes no routes, search/filter
  behavior, Saved View state, API or domain semantics.
- Fresh review covered twelve supported directories plus the Provenance sites variant at
  **1440×844, 1024×844 and 390×844**: **78 collapsed/expanded bounds checks** found no horizontal
  overflow; **39 keyboard checks** retained named search/first-filter order and visible focus.
  Search-to-Active and Save dialog focus/trap/Escape passed at each size; mobile management-dialog
  cancellation returned focus to each exact trigger. Accessibility snapshots preserve label/group names.
- Focused frontend regressions: **225 passed in 13 files** after an **11-test baseline**. Final
  whole-frontend Prettier, zero-warning ESLint, strict TypeScript and production Vite build passed.
  Evidence and retained headings are recorded in [the updated handoff](view-001-handoff.md).
- UAT services remain healthy with existing operator data preserved. The source is unstaged and
  uncommitted; VIEW-001 remains **implemented**, awaiting visual review and Luna's canonical gate.

## 2026-10-06 — VIEW-001 operator UAT placement correction

- Moved Saved Views out of the Plants search/filter grid into its own row below the directory
  heading and above search. Applied the same placement to SeedLots and Sowings; Stored material
  now places the row below its explanatory subtitle. Other supported directories already use this
  arrangement. Saved Views does not shrink as a child of bounded directory flex layouts.
- Cross-surface review also caught the Saved Stored material route using an incorrect tab value.
  Its adapter and history guard now use the existing `tab=stored-material`; normal UI Save/Open and
  refresh retained the exact query/state. Added an App-level regression against the actual peer view.
- Browser review covered all 13 supported surfaces at **1440×844, 1024×844 and 390×844**:
  39 document/panel bounds checks found no horizontal overflow, with directory controls separated
  from ordinary filters. Checked empty lists, expanded long names, wrapped actions, keyboard
  Save/Saved views/search order, modal focus trap, Escape return, and Rename/Update/Delete cancellation.
  Screenshots and measurements stay outside Git in `/tmp/florabase-view001-layout-review`.
- Focused post-layout directory/UI tests: **90 passed**. Saved View adapter/UI and Stored material
  tests after the route correction: **67 passed**. Targeted App open/refresh and keyboard peer-view
  checks: **3 passed** (the Saved Views UI cases overlap between focused runs).
- Final affected-file Prettier and zero-warning ESLint, strict TypeScript and production Vite build
  passed. UAT status reports this worktree, healthy frontend/backend/DB, revision 0034 and fixture v1
  with existing edits preserved. `git diff --check` passed; the index remains empty and primary clean.
- VIEW-001 remains **implemented**, with no staging, commit, canonical gate or delivery in this phase.

## 2026-10-06 — VIEW-001 Saved operator views implementation

- Implemented owner-private PostgreSQL SavedView persistence, revision `20261006_0034`, typed v1
  state for all thirteen audited existing search/directory surfaces, canonical ordinary URLs and
  compact Save/Open/Rename/Update-current/Delete controls with Dashboard access.
- State excludes pagination and transient interaction state. Exact stale UUIDs remain filters;
  incompatible stored versions remain manageable without silent interpretation. Existing search
  matching and default directory predicates are preserved. Lists use one bounded owner-scoped
  query per page, without executing views or materializing results.
- Focused backend/state/search checks: **84 passed**. Real isolated PostgreSQL checks: **61 passed**,
  covering JSONB/UUIDv7/UTC, naming, second-user isolation, mutation protections, bounded listing,
  stale/future state, populated downgrade refusal and empty downgrade/re-upgrade, plus SEARCH-002
  and current-head migration regressions. Ruff format/lint and strict mypy passed; production
  backend runtime build passed. Final frozen frontend suite: **435 passed in 43 files**;
  zero-warning ESLint, strict TypeScript, production frontend build and Prettier passed.
  Generated API drift, feature graph (91 features) and `git diff --check` passed. Complete browser evidence is in
  [the implementation handoff](view-001-handoff.md).
- Supported guarded retirement proved prior UAT owner `9f48` before retiring only its resources;
  this branch prepares fresh synthetic UAT through normal up/seed/status. Fixture v1 is unchanged.
- Initial browser flows passed at 1440×844 before the browser connection disappeared. The operator
  UAT correction above completes the reference and responsive visual/overflow review; UAT remains healthy.
- VIEW-001 is **implemented**, awaiting operator visual/product UAT and independent architecture/QA
  and canonical verification. No feature-verify, staging, commit or delivery in this phase.
  Collection productivity v2 remains open: bulk operations next, then justified unified history,
  then Orders/Purchases. BOTANY-003's existing blocker is unchanged.

## 2026-10-06 — PREVIEW-001 ownership retirement regression required by SEARCH-002 UAT

- Delivered UAT lacked retirement: stop kept ownership and reset recreated it under the old owner.
  Added guarded `make uat-preview-remove CONFIRM_REMOVE_UAT_PREVIEW=florabase-uat-preview`, isolated
  from SEARCH-002 application code. It requires the owning linked source, including a delivered
  detached owner, and performs only read-only Git validation. Missing/wrong token, non-owner,
  ambiguous container/volume/network identity and foreign volume writers/network endpoints refuse.
- Removal proves exact resource/source identity, stops UAT writers, rechecks identities, then removes
  only scoped UAT containers/internal network and the individually named postgres/media/dependency
  volumes. No generic `down -v`, rebuild, reseed, Git/source edit or other environment operation.
  Stop/reset semantics remain distinct; workflow and PREVIEW-001 handoff now document old-owner
  removal followed by next-feature up/seed/status, including invocation from a pre-command owner.
- Regression checks: **19 UAT helper tests**, **29 environment helper tests**, workflow Ruff
  format/lint and strict mypy passed. Real disposable Compose smoke
  `florabase-uat-preview-smoke-2e4782f118e6` passed **18 PostgreSQL fixture tests**, its established
  seed/auth/persistence/reset/ahead-refusal checks and old-owner remove → new linked fixture source
  up → empty auth → fresh seed/IDs/media/ownership → real login. Supported removal cleaned fixture
  resources; operator environment/data and primary snapshots remained unchanged.
- With explicit operator authorization, ran the corrected Makefile's removal target from owning
  `80b3`: four containers, one network and exactly the three allowed volumes were proved and retired.
  No manual Docker deletion or relabeling. Live missing-confirmation/non-owner checks refused.
  Standard `9f48` up, seed and status then passed. DEV/Stable Preview/Feature Review/production
  resource/data digests and old/primary Git identities matched before/after. Operator acceptance has
  passed; independent QA and the canonical gate are underway.

## 2026-10-06 — SEARCH-002 global Harvest and Media coverage

- Implemented only in attached `9f48` worktree on `feat/search-002-global-coverage`, PREVIEW-001
  base/unchanged HEAD `0c36a404eedb89531447581d3769867e44d35490`. Added typed Harvest/Media kinds,
  exact authenticated routes, generated contracts, Collection → Media → Botany → Reference groups,
  existing kind controls and Harvest occurrence-year filtering.
- Harvest uses its current authoritative title/source/identity, notes and material text; only exact
  source identity and true occurrence year apply. No Location/Supplier/provenance/lifecycle/Event-kind
  inference. Media shares Library title/original-filename/attribution matching and title fallback,
  with safe context and UUID/missing-target handling on the existing exact detail route. Search
  loads no images and contacts no external host. EXISTS/grouped materials and unique Attachment
  joins preserve one result per record and fixed query bounds: six SELECTs for mixed new-kind text
  search at three or 51 matches; 28 for all 13 kinds. Independent final review added saved external-
  copy filename coverage; the full supported integration wrapper then passed **550 tests**, including
  40 SEARCH-002 cases.
- Focused backend **100 passed**; the earlier focused disposable PostgreSQL matrix **69 passed**, including all
  eleven old kinds, partial dates, forbidden filters, deduplication, auth, paging and query bounds;
  frontend DashboardSearch/MediaScreen/HarvestScreen/lazy routing **36 passed**. Ruff/mypy (257 files),
  generated API preparation, zero-warning ESLint, strict TypeScript, 90-feature graph, production
  frontend Vite/backend runtime builds, changed-file Prettier checks and `make api-check` passed.
  Ordinary test fixtures/readiness/lint issues were corrected without weakening tests, rules or
  thresholds. Disposable integration resources were cleaned without operator deletion.
- SEARCH-002 operator acceptance and independent verification have passed. Canonical `make feature-verify`
  passed on this tree: graph (90 valid), UAT/environment/workflow helpers (19/29/37 passed), Ruff,
  Prettier, strict mypy (257 files), strict TypeScript and ESLint, backend unit tests (613 passed,
  90.13% coverage), frontend tests (382 passed across 41 files), API drift, PostgreSQL integration
  (550 passed, 160 warnings), production images, migration-cycle check (no new revisions), whitespace
  and tree receipt. The cold lazy Botanical Identity route test now waits 3 seconds for its unchanged
  result assertion; an isolated diagnostic showed the cold Vite import resolves in about 2 seconds,
  while all 11 UX-004 tests pass in the full suite. No UX-004 production behavior changed.
  SEARCH-002 is **verified**. Saved filters/views
  are next; bulk operations and justified history remain deferred. Orders and the BOTANY-003 WFO TLS
  blocker are unchanged. No migration/index/search infrastructure or later productivity work added.
- The PREVIEW-001 retirement correction above enabled supported `80b3` → `9f48` UAT. Up/seed/status
  passed; DB/backend/frontend are healthy at `localhost:15174`, code/DB head `20261005_0033`, fixture
  v1 initialized (31 baseline records), and real `preview / preview` browser login succeeded.
- Independent `make smoke-uat-preview` passed on unique disposable project
  `florabase-uat-preview-smoke-e92b8aceebfa`, including 18 fixture tests and old-owner retirement →
  new linked source up → fresh seed/login → guarded cleanup. The operator UAT remains healthy.
- Actual browser review at 1440×844, 1024×844 and 390×844 passed result/filter fit with no horizontal
  overflow, exact Harvest/Media navigation, Media refresh/back/forward/missing-target state, external
  opt-in remaining unloaded, source/filename/year searches, empty/clear and Escape focus restoration.
  Final diff review reproduced an uppercase UUID Media link stuck in Loading; case normalization,
  a dedicated regression and repeated real UAT/frontend checks resolved it. Search results contain
  no images. Review artifacts are outside Git. Implementation is
  operator acceptance passed; independent final review and canonical verification passed. See
  [handoff](search-002-handoff.md) for exact semantics, checks, regression isolation and searches.
  At independent-review handoff, primary was clean on `main` and the index was empty; the reviewed
  branch then proceeds through the repository's single-commit protected delivery and conservative
  finish workflow.

## 2026-10-05 — PREVIEW-001 persistent dirty-feature operator UAT

- Implemented only in the attached 80b3 Codex worktree, `feat/preview-001-uat`, at SUPPLIER-003
  base/HEAD `bd7904316445f41570aadb827d680c24ba082900` (#70). UAT reuses Feature Review's source,
  build, non-root initializer, migration and persistence helpers with independent `florabase-uat-preview`
  DB/media/dependency volumes and network. It uses current tracked/untracked dirty source at loopback
  15174; Stable Preview's ref/worktree commands, DEV/primary source and production remain distinct.
- Added five `uat-preview-*` operator commands. Up never seeds; explicit guarded seed creates the
  UAT-only public `preview / preview` owner through normal owner/Argon2 machinery and a bounded
  version-1 basil/lavender/aloe collection. Normal password validation, login, sessions, Origin and
  CSRF remain unchanged. The fixture CLI is mounted explicitly, absent from production images.
  Host project/source/network/actual mount/volume/container checks and runtime origin/cookie/resource
  marker/current-database/user checks fail closed before seed/reset can target another environment.
- A media-volume manifest records 31 service-created UUIDv7 identities without production domain
  fields. Repeated seed preserves ordinary operator edits and adds no duplicate owner/media/link.
  Interrupted, missing or incompatible baselines require guarded reset rather than guessed repair.
  The synthetic collection covers Supplier media/absence, Location hierarchy, geography/provenance,
  varied SeedLots, active/historical Sowings, direct/derived Plants/group, explicit lineage,
  observations, Harvest, generated local PNG and offline external metadata. Reset requires
  `CONFIRM_RESET_UAT_PREVIEW=florabase-uat-preview`, validates exact resources, deletes DB/media/
  dependencies individually (never `down -v`), then rebuilds health and explicitly seeds.
- Focused checks: Stable Preview **19**, environment **29**, feature workflow **37**, UAT helper **9**
  tests passed. Real disposable UAT pytest **18 passed** covers runtime/DB/environment guard refusal,
  unchanged normal bootstrap password validation, interrupted/version/missing records and media.
  `make workflow-check` passed Ruff, formatting and strict helper/fixture mypy; final harness/test
  formatting/lint and strict three-module harness typing passed after the diagnostic/CI portability
  corrections. `bash -n` for the changed
  verification script, feature graph (**89 valid**), Make help and `git diff --check` passed.
- Full real Compose smoke passed on UUID-scoped `florabase-uat-preview-smoke-d84c2ca17471`: empty
  startup/auth; untracked current-source migration; real Argon2/session login/private collection;
  fixture lineage/Harvest/shared-media/primary relationships; triple seed preserving operator text
  and an operator-only record; DB/owner/media/dependency stop/start persistence; DB-ahead refusal
  without downgrade; rejected reset confirmations; complete reset/removal of operator data and
  recreated owner/media; repeat seed after reset. Before/after primary Git, operator container/volume
  metadata and running DB data checksums matched for DEV, Feature Review, Stable Preview, production
  and operator UAT. Only proven disposable resources were cleaned. DEV has no `preview` account.
  One fresh attempt failed frontend startup health with host load 25.98 and full swap; the final
  serial rerun passed unchanged health deadlines. No tests or timeouts were weakened.
- PREVIEW-001 remains **implemented** pending its canonical verification receipt;
  next product milestone remains **Collection productivity v2**. BOTANY-003's blocker and historical
  RELEASE-001 planning remain unchanged. No schema/domain/API or graphical shell change was made.
  Primary is clean on main; this feature stays unstaged/uncommitted. `make feature-verify`, staging,
  commit, push, delivery, merge and finish were not run. See [handoff](preview-001-handoff.md).
- Operator UAT passed; the healthy environment remains running at `http://localhost:15174`, seeded explicitly with
  `preview / preview`; DB current/code head are `20261005_0033`. Browser login and seeded Seeds,
  Suppliers, Sowings and Plants were inspected at 1440×844, 1024×844 and 390×844 without horizontal
  overflow. Mobile Dashboard, Supplier Photos and keyboard activation of Supplier detail also passed
  spot checks. To free the existing Review port,
  Feature Review was stopped from its owning 73d8 source after the isolated smoke; all three Review
  volumes were retained. DEV, Stable Preview, production and primary remain unchanged.

## 2026-10-05 — PREVIEW-001 independent review

- Operator reported product UAT passed. Independently reviewed the complete tracked and untracked
  PREVIEW-001 diff, host/runtime guards, normal authentication boundaries, fixture service invariants,
  persistence/reset scope, migration refusal, CI wiring, feature graph and operator documentation.
  No production/workflow defect or out-of-scope domain change was found; no tests were added because
  the existing independent runtime tests and real disposable smoke cover the reviewed contracts.
- Independently reran `make smoke-uat-preview` on fresh disposable project
  `florabase-uat-preview-smoke-901ac5363b53`. Eighteen PostgreSQL fixture/guard tests passed; the
  smoke confirmed dirty/untracked source, normal Argon2/session login, runtime refusals, triple seed,
  edit preservation, stop/start DB/media/dependency persistence, ahead-of-code refusal, guarded reset
  and recreation, and unchanged DEV/Feature Review/Stable Preview/production/operator UAT snapshots.
  Exact disposable resources were cleaned; operator UAT remains running. `git diff --check`, feature
  graph (89 valid), and `make help` passed. Canonical verification is the next step.

## 2026-10-05 — SUPPLIER-003 shared Supplier imagery and Reference completion

- Implemented only in the current 73d8 Codex worktree, attached through `make feature-init` as
  `feat/supplier-003-media` at merged HARVEST-003 base `4dbf6cf` (#69). Supplier is an ordinary
  typed shared-media target with multiple reusable local/external assets and one optional explicit
  primary. Concrete restrictive FKs, exact-target/duplicate/primary constraints and the existing
  immutable-link guard protect membership. Revision `20261005_0033` follows `20261004_0032`,
  has no backfill or binary mutation, cycles empty state and refuses populated downgrade before DDL.
- Supplier directory, Quick Preview and detail reuse protected thumbnails/neutral placeholders;
  the new Photos tab reuses shared upload/reference/link/caption/order/primary/unlink controls.
  Fixed direct-detail editing to use its loaded Supplier. Media Library Target now offers All,
  Collection media, Suppliers and every existing collection target. EXISTS filtering composes with
  search/kind/association and deterministic pagination, returns unique assets and uses two SELECTs.
  Collection media is exactly an explicit SeedLot/Sowing/Plant/PlantGroup/Event/Harvest link;
  Supplier-only assets are excluded and Supplier + Plant assets appear in both. Supplier choices
  use two SELECTs; mixed directory primary summaries use at most four, exercised with 30 Suppliers.
- Shared assets and each exact primary remain independent. Unlink clears the exact primary and
  retains assets/other links/covers; zero record links plus zero identity covers still gates deletion.
  Acquisition/lineage never inherits imagery. External disclosure/copy safety and protected reads,
  owner mutations, CSRF and exact Origin remain shared. No logo role/category, second media system,
  Orders, global Search v2 or botanical work was added.
- QUALITY focused backend Supplier/media/primary/copy pytest `--no-cov`: **59 passed**. The final
  disposable tmpfs PostgreSQL matrix passed **42 tests** across Supplier media/migration, shared
  media/races/primary races, Supplier API, external copies and shared-media migration preservation.
  Eighteen existing Alembic path_separator deprecation warnings remain. Cleaned only task-owned
  project `florabase-supplier003-20261005` without volume deletion; retained Feature Review.
- Focused SupplierScreen/MediaScreen/PhotosSection Vitest: **27 passed across 3 files**; existing App
  Supplier/UX-005 regressions passed **8 tests** (59 unrelated cases skipped) after actual lazy-render readiness and
  representative-image accessible-name selector corrections. Ruff format,
  Ruff check, strict mypy (**256 files**), zero-warning ESLint, strict TypeScript, generated contracts
  from `make api-generate`, `make api-check`, **89-feature** graph and both production image builds
  passed. Final diff audit and `git diff --check` passed. The independent canonical gate is pending.
- Corrected ordinary new-test selectors/types/lint. Existing full-row migration preservation now
  includes the new null Supplier column; retention assertions use the truthful Record links wording.
  An initial frontend command accidentally launched the full suite, exhausted host RAM/swap and was
  interrupted by stopping only its own test container. It is not passing evidence. Focused reruns
  used direct Vitest path selection; no validation, thresholds, timeouts or assertions were weakened.
- With explicit operator authorization, removed the prior fbb6-owned Review only through its supported
  helper and created current Review. `make feature-review-up` and `make feature-review-status` show
  healthy isolated services, 73d8 live source binds and code/database revision 0033 at localhost:15174.
  Synthetic A–G Supplier/media examples and screenshots stay outside repository source. Actual browser
  checks cover Supplier directory/Quick Preview/Photos and primary replacement at 1440×844, detail at
  1024×844, and directory/detail/external dialog focus/escape at 390×844 with no horizontal overflow.
  Reference-only external primary stays unloaded. The browser later disconnected and reported no
  available browser despite healthy Review; this agent did not complete the full Media Library matrix
  or a successful external fetch from example.test.
- The operator subsequently reported manual product UAT passed on 2026-10-05. Independent review
  found no production defect; focused tests above independently cover the acceptance criteria.
  SUPPLIER-003 is P1 **verified**. The canonical frozen-tree gate supplies its final delivery receipt.
  The new operator-approved next step is **PREVIEW-001**, added as planned P1 infrastructure;
  Collection productivity v2 follows it. BOTANY-003's approved WFO TLS blocker and historical
  RELEASE-001 planning remain unchanged. See [full handoff](supplier-003-handoff.md) for the
  contract and evidence. Primary checkout is untouched.

## 2026-10-04 — HARVEST-003 explicit SeedLot conversion and guarded reversal

- Continued only in the existing fbb6 Codex worktree, attached through `make feature-init` as
  `feat/harvest-003-seedlot-conversion` at merged HARVEST-002 base `c351971` (#67). The original
  product gate was resolved by the operator's approved B guarded-reversal contract. Added narrow
  typed conversion persistence, explicit active tracked seed-only creation, atomic stock/disposition/
  SeedLot accounting, canonical exact producer lineage and on-demand cross-links. Source identity
  defaults independently correctable target identity; PartialDate occurrence and explicit target
  Location preserve known facts without acquisition/provenance/Event/media/Sowing inference.
- Undo retains the original immutable disposition, conversion and resulting SeedLot as `reversed`,
  restoring typed source before quantity/state only under captured after-state/correction-version
  compatibility and resolved dependency rules. Converted producer/source and Harvest source are
  protected; later standalone dispositions still have no generic reversal. Reversed lots remain in
  history/totals/Location evidence and cannot reactivate or supply new Sowings. Safe descriptive,
  identity and Location corrections remain possible. Revision `20261004_0032` installs restrictive
  FKs, unique result/disposition links, typed quantity/coherence/origin guards and guarded downgrade.
- Added HARVEST-003 and promoted it to `verified` after accepted UAT and independent review, without
  changing other feature contracts/statuses.
  Reconciled the roadmap's current direction and actual landed graph statuses, retaining historical
  0.1.0/RELEASE-001 planning. Recorded the approved forward sequence through 1.0.0 and BOTANY-003's
  parallel approved-WFO incomplete-TLS-chain blocker without workaround or reselection. See
  [contract](harvest-seed-conversion.md) and [full Sol handoff](harvest-003-handoff.md).
- Focused QUALITY backend pytest `--no-cov`: **129 passed** across Harvest, inventory, conversion,
  SeedLot model/schema, lineage and import/export service files; SeedLot service/API **6 passed**;
  ordinary Sowing service **4 passed**. Focused Vitest Conversion/SeedLotScreen/SowingScreen:
  **48 passed**; the added identity/target-Location choice brought Conversion to **8 passed**,
  and final eligibility-request failure coverage brought it to **9 passed**, for **50 unique focused
  cases**. Final audit fixed an eligibility error appearing behind Undo: the dialog now shows the
  failure and keeps confirmation disabled. Final focused Conversion rerun: **9 passed**.
- Task-owned disposable PostgreSQL tmpfs project `florabase-harvest003-20261004` ran the current
  backend through `compose.integration.yaml` plus an untracked `/tmp` source override. Fresh focused
  matrix: **160 passed** across CSV API, conversion/migration, inventory/migration, SeedLot API,
  lineage API/integrity and propagation reversal. Final conversion/migration rerun after boundary/
  correction tests and SQL readability cleanup: **42 passed**. Twelve deterministic transaction/
  observed-lock-wait race cases cover overuse, duplicate use-all, source correction/Harvest/real
  lineage mutation and Undo vs disposition/conversion/use/duplicate Undo/correction, without sleeps.
  Migration cycles preserve a pre-existing ordinary lot/inventory without conversion backfill and
  reject populated downgrade. Existing Alembic path_separator deprecation warnings remain unchanged.
- An early reused test DB retained pre-cleanup race reference fixtures and caused four existing
  empty-DB CSV assertions to fail. Added complete fixture-reference cleanup and reran on fresh tmpfs:
  all passed. New-test enum fixture/selector/type/lint failures were fixed without weakening existing
  assertions, validation, configuration or timeouts.
- Ruff, Python format check, strict mypy (**254 source files**), Prettier, zero-warning ESLint,
  strict TypeScript, `make api-check`, the **87-feature** graph, production backend/frontend image
  builds and `git diff --check` passed. Generated contracts came from `make api-generate`.
  After resumption, final production builds, mypy over **132 application source files**, Python
  formatting (**289 files**) and Prettier passed again on the current tree.
  The final modal error-state fix passed strict TypeScript, zero-warning ESLint, Prettier and
  both production image builds on October 5.
- Feature Review was initially blocked by 8dfa ownership. With explicit operator approval, removed
  only that prior Review through its owning `feature-review-remove`; current `feature-review-up`
  and `feature-review-status` report fbb6 live binds, isolated DB/media/dependencies, healthy services
  and revision 0032 at localhost:15174. Actual browser smoke completed exact Plant partial transfer,
  changed target Location, dates, cross-links and lineage at **1440×844**, then a second exact use-all
  packet, depleted source and retained two conversions at **1024×844**. Browser reconnection resolved
  the interrupted mobile smoke: **390×844** blocked older Undo with useful reasons and disabled
  confirmation, restored focus on Cancel, then safely reversed the newest packet and restored exactly
  20 items. The reversed lot retained Harvest links and Plant lineage with no Start sowing action.
  PlantGroup approximate stock produced an exact 35 g packet with explicitly confirmed approximate
  65 g remainder; unknown group stock produced a measured 20 g packet while remainder stayed unknown.
  Non-seed/depleted rows had no conversion action. Mobile dialogs had no horizontal overflow and
  native quantity controls passed keyboard selection. All representative A–L cases are covered
  across the three requested sizes. Operator acceptance is accepted. Review synthetic data,
  credentials and screenshots are outside the diff; viewport override reset; DEV was unused.
  On October 5 the retained Review frontend/backend were found stopped; `make feature-review-up`
  restarted the isolated services without state removal and confirmed all healthy at revision 0032.
  - All changes remain unstaged/uncommitted. No extra worktree, primary checkout source change,
    commit, push, PR, delivery, merge or feature-finish. Operator UAT/visual acceptance and Luna's
    independent review/matrix are complete. The first canonical attempt stopped after 588 passing unit
    tests because coverage was 88.78% against the unchanged 90% threshold. Added independent unit
    coverage for creation, exact use-all conflict and kg guard, reversal eligibility/restoration,
    conversion history projection and API paths. Final canonical `make feature-verify` passed on
    October 5: backend 595 passed at 90.00%, frontend 368 passed across 40 files, PostgreSQL
    integration 500 passed, API drift and workflow checks passed, and production images built. The
    disposable migration cycle passed from 20261003_0031 through 20261004_0032, back and forward again.
    The gate exposed a migration-cycle helper that missed normal unannotated Alembic assignments; it
    now supports both forms and all 37 workflow-helper tests pass. The per-worktree verified receipt
    matches this tree. The reviewed local commit remains pending.

## 2026-10-04 — HARVEST-002 independent QA and canonical verification

- Independently reviewed the complete feature diff, including migration/model constraints, service
  locking and inventory transitions, Harvest/Location retention integration, APIs, tests, generated
  OpenAPI/TypeScript declarations and documentation. No material contract gap, production defect or
  unresolved product decision was found. Inventory remains independent of collected quantity and
  biological lifecycle; immutable disposition history and tracked source context remain protected.
- Verified Sol's PlantScreen/App edits synchronize against the real lazy workspace import using
  `vi.dynamicImportSettled()` inside React `act`. Existing detail/form assertions and API fixtures are
  preserved, with no mocks, sleeps, retries or timeout increases. The original Plant and PlantGroup
  deep links, Events preservation, hash switching, Back/Forward and return to the directory passed;
  PlantGroup also passed alone as a cold first import. The two full affected suites passed **107 tests**.
- First canonical gate passed: feature graph, workflow checks, Ruff, mypy across **247** backend source
  files, strict TypeScript, zero-warning ESLint, Prettier, API drift, **578** backend unit tests at
  **90.14%** coverage, **359** frontend tests across **39** files, **458** PostgreSQL integration tests,
  production builds and migration upgrade/downgrade/re-upgrade cycle. Final gate is being repeated on
  this documentation-complete tree so its receipt matches the committed source digest.
- Browser smoke remained unavailable because the Review frontend/backend were stopped; no browser
  result is claimed. No production correction was needed.

## 2026-10-04 — Plant route test synchronization

- Investigated Luna's preserved Plant/PlantGroup deep-link blocker before changing any implementation.
  Reproduced `#/plants/01900000-0000-7000-8000-000000000701` and
  `#/plant-groups/01900000-0000-7000-8000-000000000702`. Temporary tracing showed correct route parsing
  (`plants`, requested record ID, `plant`/`group`) and correct PlantScreen props. The real cold lazy
  PlantScreen import resolved after **1,147 ms**, just after the original **1,000 ms** detail-query
  deadline; the requested detail and Print label link then appeared and the workspace placeholder
  disappeared. The next warm case passed. This clarifies the earlier blocker record: the observed
  failure was test synchronization, not an indefinitely suspended production workspace. All tracing
  was removed and the instrumented production files restored byte-for-byte.
- With explicit operator approval, wrapped mocked session restoration and the real dynamic-import
  completion in React `act` in the two existing Plant deep-link cases. Applied the same synchronization
  to App's parameterized direct-creation routes after its first cold identity case failed in the
  combined focused run but resolved correctly in isolation. Existing detail/form assertions, real
  lazy imports, API fixtures, query/test timeouts and error boundaries remain unchanged. No production
  file was changed for this handoff, and HARVEST-002 semantics and Luna's existing changes are retained.
- Added a real hash/history regression covering Plant → PlantGroup switching, `?tab=events`, native
  Back/Forward events and return to `#/plants`. The test awaits actual hash/history events inside
  `act`, without sleeps, retries, global test configuration or mocked workspaces.
- Focused container validation: **126 passed across six files** (`App`, `PlantScreen`,
  `Propagation002`, App lazy/transition and WorkspaceBoundary). After callback lint corrections,
  App/PlantScreen again passed **107 tests**; the final event-synchronization adjustment passed both
  original deep-link regressions plus the history case (**3 passed**), and PlantGroup passed as a
  separate cold first import (**1 passed**). `pnpm format:check`, strict `pnpm typecheck`,
  `pnpm lint` with zero warnings and `git diff --check` passed.
- Optional browser smoke was unavailable: localhost:15174 refused the connection; read-only
  `make feature-review-status` confirmed Review frontend/backend exited, with the database healthy
  at revision `20261003_0031`. No Review volumes or credentials changed. No backend suite, canonical
  `make feature-verify`, staging, commit, push, delivery, merge or primary checkout modification was
  performed in this handoff. Independent review and final verification remain with Luna.

## 2026-10-03 — HARVEST-002 independent final-review verification

- Completed an independent review of the current feature tree, including the inventory ownership,
  quantity/state rules, serialized writes, source-context restrictions, Harvest/Event separation,
  Location projections, authenticated API boundary, generated contracts and operator-reviewed UI.
  No HARVEST-002 defect or unresolved domain decision was found. Final verification is blocked by
  an unrelated existing Plant/PlantGroup deep-link test that leaves the workspace on its loading
  placeholder.
- Extended the disposable PostgreSQL concurrency matrix to cover simultaneous tracking of the same
  HarvestItem and competing use-all dispositions. Both serialize on the owner-first locks; duplicate
  tracking conflicts without a second inventory and the losing use-all conflicts after seeing the
  depleted balance. Updated existing full-schema integration expectations for the two new inventory
  tables and the Harvest inventory Location scope.
- Added unit coverage for inventory API filter forwarding, error translation/rollback and write-route
  commit/refresh behavior to keep the required backend coverage threshold. Updated older Location UI
  expectations for the additional storage scope and fifth usage-count row.
- `make test-integration`: **458 passed, 571 deselected** against a unique disposable PostgreSQL
  Compose project, including HARVEST inventory and migration tests. The initial run exposed only the
  stale schema expectations above; the corrected full rerun passed. `git diff --check` and Python
  compile checks passed. The full frontend suite passed **358 tests across 39 files** after updating
  the two stale Location assertions. `make feature-verify` passed workflow and quality checks,
  including backend unit coverage at 90.14%, then failed in the unrelated Plants deep-link frontend
  test. The test also fails in isolation against the `origin/main` App.tsx and its regression test is
  preserved. No HARVEST-002 implementation files changed during the final gate attempt. Verification
  remains incomplete; no commit, push, delivery, merge or primary checkout changes were made.

## 2026-10-03 — HARVEST-002 operator UAT filter and peer-view corrections

- Continued only in `feat/harvest-002-inventory` in the existing `8dfa` Codex worktree.
  Reused Geography's peer-view button styling with `aria-pressed` and native Tab/Enter/Space
  behavior; no DetailTabs or dangling tabpanel relationships. `#/harvests` and
  `#/harvests?tab=stored-material` retain selected view across Back/Forward and refresh.
- Added the shared searchable ReferencePicker to both directories, default All botanical
  identities, with an accessible clear action and restored input focus. Choices are exact,
  deduplicated source identity references. Harvests reuse the existing `botanical_identity_id`
  API query and preserve the unfiltered choices while narrowed; Stored material filters its
  existing source projection locally. Identity composes with text/material/source type for
  Harvests and text/state/material/Location for Stored material. Misleading titles cannot
  establish membership. Global-empty and filtered-empty messages remain distinct. This UAT
  correction changed no backend, schema, generated contract or domain relationship.
- Aligned labels and 44px controls in compact desktop grids, two-column tablet grids and
  mobile full-width search/identity plus paired small selectors. Browser review of both URLs
  at **1440×844**, **1024×844** and **390×844** confirmed selected state, keyboard selection and
  clearing, exact identity/material/source composition, filtered-empty results and no page-wide
  horizontal overflow. Review initially showed no Harvests; three explicitly labelled synthetic
  UAT Harvests and tracked lines across two identities were added through existing services,
  including Plant/PlantGroup sources and an intentionally misleading cross-identity title.
  No existing Review records or volumes were removed or credentials changed.
- `make feature-review-up` and `make feature-review-status` passed: frontend/backend/DB healthy,
  source is this worktree, unchanged HEAD `519b9f0887b445fee84b19ea3ff96023a8573fac`, migration
  head/current `20261003_0031`, same `florabase-feature-review` DB/media/dependency volume names.
- Focused baseline **26 passed**. Final frontend **32 passed**: Harvest 9, Stored material 14,
  API query serialization 1, ReferencePicker 4, native reference interactions 2, plus the two
  targeted App route/keyboard cases (65 unrelated App cases intentionally skipped). Strict
  TypeScript, zero-warning ESLint, Prettier and `git diff --check` passed. Initial lint/import
  cleanup findings were corrected and the affected checks rerun successfully. No backend checks
  or API generation were needed for this frontend-only correction. Updated only the current UI
  contract and this milestone; prior implementation evidence remains intact.
- Operator visual acceptance remains pending. Work remains unstaged and uncommitted; no push,
  delivery, `make feature-verify`, new feature/worktree or primary checkout changes occurred.
  Review remains available at `http://localhost:15174`; screenshots remain outside the repository.

## 2026-10-03 — HARVEST-002 implemented for visual review

- Worked only in `/home/alessandro/.codex/worktrees/8dfa/florabase` on
  `feat/harvest-002-inventory`, attached with `make feature-init` from clean detached
  `origin/main`/HEAD `519b9f0887b445fee84b19ea3ff96023a8573fac`. HEAD remains unchanged.
  Primary `main` remains clean. No additional worktree, staging, commit, push, delivery,
  merge, feature-finish or canonical `make feature-verify` occurred.
- Added explicit zero/one inventory per historical HarvestItem and owned disposition facts.
  Positive finite NUMERIC exact/approximate count or mg/g/kg weight and unknown quantity stay
  independent of collected quantity. Active/depleted, storage Location, current correction,
  controlled consumed/processed/discarded/gifted/used_for_propagation, partial/use-all and typed
  immutable before/after snapshots follow [the inventory contract](harvest-inventory.md).
  Exact partial arithmetic preserves precision beyond 28 digits; approximate remainder requires
  confirmation; unknown stays unknown; use-all preserves precision and depletes.
- Harvest → inventory → Location locks refresh current state and serialize competing requests.
  Restrictive source-context FKs, item-kind/source triggers, unique item ownership, quantity/date/
  transition/snapshot checks and immutable disposition updates supplement service guards. Harvest
  correction retains item IDs and stock/history; deletion or tracked-line removal/kind changes
  conflict. History prevents tracking removal. No biological lifecycle/quantity/Location mutation,
  source Event, SeedLot conversion, propagation receipt, lineage edge, new media target or global
  search expansion was added.
- Inventory reads batch source/identity/Harvest context and storage paths with a history-existence
  flag; history loads on demand. The existing single recursive Location aggregate includes the
  fifth canonical inventory assignment type, active excluding depleted and total retaining it.
  Query evidence covers twelve rows and a deep tree within ten combined statements; the existing
  Location directory still proves two domain queries. Existing Locations migrate with storage
  eligibility disabled; scope removal/deletion guards retain assigned depleted material.
- Revision `20261003_0031` follows `20261002_0030`: no inventory backfill, historical quantity and
  owned Event retained across upgrade, empty downgrade/re-upgrade passes, populated downgrade
  refuses before destructive operations. Harvest-only Location scope is also guarded on downgrade.
  Review database reports the same head. Generated OpenAPI and TypeScript declarations match source.
- Focused checks: initial Harvest/Location unit baseline **56 passed**; final focused backend
  **77 passed** (Harvest 44, inventory 21, Location 12); disposable PostgreSQL **47 passed**
  (inventory 18, migration 1, existing Harvest/Location coverage 28). Real transactions verify
  7-vs-7 consumption at balance 10, disposition-vs-correction, tracking-vs-Harvest deletion and
  tracking-vs-material-kind correction. Tests retain genuinely preloaded ORM state, observe a real
  PostgreSQL lock wait and verify a valid refreshed outcome without arbitrary sleeps. Source and
  collected-quantity correction preserve stock/history; direct SQL cannot edit disposition facts.
  Hostile Origin, missing CSRF and unauthenticated access are rejected. Six pre-existing Alembic
  configuration deprecation warnings remain; no tests/checks/timeouts were weakened.
- Frontend focused **22 passed** (Stored material 13, Harvest 7, native Reference interactions 2).
  Backend Ruff and formatting, strict mypy (247 source files), frontend Prettier, zero-warning ESLint,
  strict TypeScript, `make api-check`, feature graph (86 valid features), production backend runtime
  image and frontend production build passed. `git diff --check` passed. Focused integration fixtures
  use unique tmpfs PostgreSQL Compose projects and scoped container/network cleanup without volume
  deletion. Initial import/fixture-cleanup/test-selector/lint failures were corrected and rerun.
- Feature Review is healthy at `http://localhost:15174`, project `florabase-feature-review`, with live
  source from this worktree and isolated review DB/media/dependency volumes. Owner was created through
  the supported password-stdin bootstrap; credentials/fixture scripts/screenshots stayed outside the
  repository. Synthetic examples cover untracked Harvests, exact seeds, approximate weight, unknown
  quantity, retained/depleted material, mixed tracked/untracked lines, dead Plant and completed
  PlantGroup, long botanical/source names and a five-level storage path.
- Browser implementation review at **1440×844**, **1024×844** and **390×844** checked directory/detail,
  tracking below collected amount, Location keyboard selection, each of the five categories, exact
  partial consumed (8→5 while Collected stays 10), approximate processed (confirmed About 60 g),
  unknown gifted partial, propagation use-all, discarded use-all, depletion, independent correction
  after history, never-used removal and retained mobile history. Filter-empty and depleted directory
  states work. No page-wide horizontal overflow was observed. Named dialogs, labelled quantity
  controls, visible focus, focus trapping, Escape/launcher restoration and focused server conflicts
  worked. Active/depleted and quantity precision use text. Mobile dialogs scroll within the viewport.
- HARVEST-002 is `implemented`, not `verified`. No unresolved implementation defect or new product
  ambiguity was found. Operator visual acceptance and independent Luna review/final canonical gate
  remain outstanding by the requested phase boundary. Work is intentionally unstaged/uncommitted:
  `READY_FOR_VISUAL_REVIEW`.

## 2026-10-02 — BOTANY-003 TLS diagnosis: missing provider intermediate

- Preserved all approved source/replacement findings on the current branch at `cd29de9`. Inspected
  the pinned Python 3.14.7 slim-bookworm Dockerfile and the unchanged development/runtime images
  using isolated read-only, non-root, no-mount diagnostic containers. Both already contain Debian
  `ca-certificates` `20250419~deb12u1`, populated system stores (150 roots) and certifi 2026.07.22
  (121 roots). Python 3.14.7/OpenSSL 3.0.20 default paths resolve to the system bundle/directory;
  SSL_CERT_FILE/SSL_CERT_DIR and conventional proxy variables are unset. Host has a newer public
  system CA package. Full image identities, bundle inventory and trust paths are in audit section 33.
- Direct SNI/verified OpenSSL diagnostics on host/development/runtime all receive exactly one
  identical certificate from the exact approved archive host: leaf `*.worldfloraonline.org`, issued
  by `GeoTrust TLS RSA CA G1`, valid 2026-07-14 through 2027-01-28, SAN matching the archive host.
  All fail with error 20 at depth 0. DigiCert's official metadata identifies the issuing intermediate's
  root as DigiCert Global Root G2, already present and valid in all tested system/certifi bundles.
  The issuing intermediate is omitted from the served chain; no issuer certificate was fetched,
  installed, embedded or trusted as a workaround.
- Host Python/system curl and both images' Python system/certifi plus HTTPX default/system probes
  all reject the chain with verification/hostname checks enabled. Evidence supports case C (observed
  remote incomplete chain), not a missing CA package, wrong effective CA path or hostname mismatch.
  No proxy/interception evidence was observed; no independent off-site network audit is claimed.
- `SOURCE_TLS_PROVIDER_BLOCKED`: WFO must serve its issuing intermediate to restore normal public
  chain validation. Provider-specific trust augmentation is an option requiring separate explicit
  approval, not implemented. No standard Florabase trust fix was justified; no rebuild, unrelated
  dependency change, insecure fallback, alternate source or application implementation occurred.
  BOTANY-003 remains `planned`; its source/product decision remains APPROVED. GBIF/CoL TLS behavior,
  operator services/data, branch and source research remain intact.
- Updated audit, domain-model blocker note, roadmap blocker note and progress. Pinned Prettier,
  feature graph (85 valid features) and diff checks cover documentation only. No provider-dependent
  CI check, application/migration/browser checks, canonical gate, staging, commit, push or delivery.

## 2026-10-02 — BOTANY-003 source/replacement approval and implementation access blocker

- Preserved the existing worktree/branch at `cd29de9` and all source-capability research. Recorded
  the operator's APPROVED decision C: WFO / Flora of China description → `description`; Kew WCVP
  `geographic_area` → `origin_distribution`; replacement policy 3 requires explicit Apply/confirmed
  Replace, typed immutable history and field-specific current attribution. Manual edits clear only
  the edited field's association while retaining history; source confirmation and stale-review
  checks are mandatory. No additional source/capability or provider-selection reconsideration.
- Tested the exact reviewed WFO archive securely before adding application code. Isolated read-only,
  non-root, no-mount containers from the existing QUALITY development and production backend images
  both used HTTPX 0.28.1/certifi 2026.07.22 with default TLS validation, fixed URL, no redirects and
  bounded streamed range retrieval. Both exited 1 before an HTTP response with
  `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`. Host curl independently
  exited 60 for the same issuer-chain validation failure. Ephemeral probe containers were removed;
  operator environments/data and trust configuration were not changed.
- `SOURCE_IMPLEMENTATION_BLOCKED`: the operator required stopping if this exact approved access
  mechanism cannot be used safely. No TLS bypass, custom trust exception, alternate API/source,
  browser-download runtime mechanism or partial WCVP-only feature was substituted. Secure backend
  retrieval of this exact archive must succeed with a validated certificate chain before resuming.
  Root cause beyond the observed validation error has not been established; the earlier successful
  browser research and approved content/licensing findings remain intact.
- Updated audit, feature acceptance criteria, domain-model approved/deferred note, roadmap and
  progress. BOTANY-003 remains `planned`; no persistence model, route, parser, UI, migration or API
  artifact was implemented. Pinned Prettier, feature graph and diff checks cover documentation only.
  Implementation tests/build/browser checks did not run; the prior unrelated baseline failure was
  not investigated. No canonical gate, staging, commit, push, delivery, merge or finish.

## 2026-10-02 — BOTANY-003 bounded source-capability investigation

- Continued the existing `feat/botany-003-controlled-enrichment` worktree at `cd29de9`, under
  explicit research-only authorization. Extended `docs/botany-003-audit.md` with the full capability
  matrix, two actual taxa per source (Acer palmatum and Annona cherimola), access/license evidence,
  geography feasibility, provenance assessment and exact proposed responsibility boundaries.
- Retrieved WFO's publicly identified Flora of China Darwin Core Archive and verified exact WFO-ID
  description/reference joins, English general descriptions, CC BY 4.0/MBG effective metadata and
  original bibliography/URLs for both taxa. Classified this publication as public structured but
  weakly documented for consumers; no current supported live content API was established.
  Normal browser download succeeded; local curl reported issuer-chain validation failure. No TLS
  bypass or private harvester access occurred. Kept only minimal description excerpts in the report.
- Retrieved the officially supported Kew WCVP v16 download (extracted 2026-06-04), verified its
  README CC BY 3.0/citation, generalized distribution strings, native/introduced/extinct/doubtful
  flags and TDWG level-3 rows for both taxa. Inspected POWO's element-specific contributors/licenses;
  Annona UPFC uses carry CC BY-NC-SA 3.0, and poison-use/conservation categories are not warnings.
  The published historical pykew API hostname returned 403; no narrative API contract was inferred.
- Recommend source option C with non-overlapping fields: WFO's inspected licensed description
  subset → `description`; WCVP `geographic_area` → `origin_distribution`. Eligibility is conditional
  on explicit source choice, exact confirmed source IDs, approved snapshot access and durable
  per-value attribution. Existing GBIF/CoL remains taxonomy/match only. No third provider surveyed.
- Native ranges remain informational/unmapped: the official TDWG tables demonstrate KOR vs KP/KR,
  JAP vs political JP, and ECU vs GAL within EC. Florabase's CLDR places have no reviewed crosswalk;
  do not guess from labels or erase native/introduced distinctions. Cultivation, uses, warnings and
  uninspected contributors remain deferred. Mutable links/cache alone cannot retain applied-value
  license/reference/history; a small source-attribution extension is needed, not implemented.
- `SOURCE_CAPABILITY_DECISION_REQUIRED`. BOTANY-003 remains `planned`. Only the audit/progress
  documents changed. Pinned Prettier checks, `python3 scripts/check-features.py` (85 valid features)
  and `git diff --check` passed. No application tests or canonical gate were rerun, and the earlier
  unchanged frontend baseline failure was not investigated. No code/API/schema/UI/migration changes,
  staging, commit, push, delivery, merge or finish.

## 2026-10-02 — BOTANY-003 controlled enrichment audit

- Initialized the existing Codex worktree at `cd29de9` through `make feature-init` on
  `feat/botany-003-controlled-enrichment`. Audited the identity/profile, external adapter/cache,
  geographic hierarchy/native-range implementation, migrations, APIs, frontend modules, tests and
  current domain/architecture/roadmap contracts. The primary checkout and DEV were not modified.
- Recorded the full field matrix and requested handoff topics in `docs/botany-003-audit.md`.
  The implemented GBIF/CoL XR matcher supplies taxonomy and diagnostics, while BotanicalProfile
  owns five narrative sections and exact structured native ranges. There are no safe direct or
  deterministically normalized writable mappings. Taxonomy remains informational; narratives and
  native-status geography lack an eligible content contract. Official GBIF taxonomy documentation
  was checked; no new source capability was probed live.
- `NEEDS_PRODUCT_DECISION`: choose an approved profile-content source with an example linked taxon,
  retrieval/attribution/licensing contract and field mapping, or explicitly authorize bounded
  source-capability investigation. No placeholder proposal/apply API, synthetic taxonomy narrative,
  additional local fields, receipt or migration was added. BOTANY-003 remains `planned`.
- Baseline checks passed: 45 backend unit tests (`pytest --no-cov` over
  `test_external_botany_provider.py`, `test_external_botany_service.py`,
  `test_external_botany_api.py`, `test_botanical_profile_schemas.py`,
  `test_botanical_profile_service.py` and `test_botanical_native_range.py`); 15 PostgreSQL tests
  over external-botany API/migration and botanical-profile API/native-range migration suites;
  and 3 `ExternalBotanicalDataPanel.test.tsx` tests. PostgreSQL ran in isolated
  `florabase-integration-botany003-b4a3` with tmpfs storage, upgraded to actual code head
  `20261002_0030`, then its containers/network were removed without deleting volumes.
  Integration emitted 12 existing Alembic `path_separator` deprecation warnings.
- The additional unchanged `App.test.tsx --testNamePattern='profile|native.range'` baseline
  passed 10 cases and failed the directory/profile case at line 816 while locating the
  `Annona cherimola.*Cherimoya` button. The failure precedes profile interaction; it is not an
  enrichment regression. The exact case also failed in isolation. No test expectations, timeouts
  or unrelated UI were changed. Pinned Prettier checks over both changed documents,
  `python3 scripts/check-features.py` (85 valid features) and `git diff --check` passed.
- No application code or API artifacts changed, so application lint/typechecking/API drift and
  production builds were not run. No Feature Review launch, independent implementation review,
  operator acceptance, canonical `make feature-verify`, staging, commit, push, delivery, merge
  or finish was performed.

## 2026-10-02 — DEV upgrade initializer image portability fix

- Confirmed PR #64's upgrade path built only `backend`, then migrated before invoking
  `dev-state-init` from a potentially historical frontend development image. DEV upgrade now
  builds `backend` and `dev-state-init` together from the selected primary source and checks the
  initializer executable in the rendered image through a read-only, network-disabled Docker run
  without mounting DEV volumes, before starting the DB or applying migrations. Migration compatibility,
  revision confirmation and migration-before-initialization order retain their existing semantics.
- QUALITY frontend commands had the same initializer freshness assumption and now share this
  preparation helper. DEV up and Feature Review already build all services before initialization;
  Stable Preview/production/integration do not invoke this development initializer.
- Regressions failed against the old implementation and pass after the fix: stale/absent images,
  pending migration, already-at-head retry, build/executable failure before any DB operation,
  explicit current-source build ordering and QUALITY initialization. Focused checks passed
  29 environment tests, 37 feature-workflow tests, 19 Preview tests and shell helper fixtures;
  `make workflow-check` passed Ruff lint/format and strict mypy, plus `git diff --check`.
- `make smoke-dev-upgrade` passed on UUID project
  `florabase-dev-upgrade-smoke-51021aa5ae37`: the deliberately old image lacked the initializer;
  failed initializer build preserved revision 0029 and DB rows; rebuilding applied 0029 → 0030,
  initialized ownership, retried successfully at head and rebuilt again with the image absent.
  DB rows, media/dependency markers, all three volume identities and the DB container survived.
  Only fixture containers/network/volumes/image tags were removed. Before/after operator
  DEV/Review/Preview/production container+volume and primary Git snapshots match.
- Updated the canonical runtime freshness/retry invariant and added the repeatable isolated smoke
  target to script static checks. This worktree is attached through `make feature-init` to
  `fix/dev-upgrade-initializer-image` at main base `31209b2`. No primary checkout changes, operator
  DEV mutation, staging, commit, push, delivery, merge or finish. Ready for independent infrastructure
  review; the final canonical `make feature-verify` gate remains after that review. No graphical
  product review or feature-status promotion was performed.

## 2026-10-02 — CI-003 portable development and quality identity

- PR #64's GitHub `quality` failure reached frontend `pnpm format:check` but could not create
  `/app/_tmp_*`: Compose's 1000:1000 defaults did not match the invoking checkout owner. Both
  development application services shared this bind-mount assumption.
- DEV, Review and QUALITY now explicitly use the invoking POSIX UID/GID for both runtimes and
  project-local dependency/media initialization, overriding stale shell and `.env` defaults. Root
  invocation refuses; platforms without UID/GID APIs require an explicit numeric non-root identity
  in the process environment. Production and Stable Preview retain their image users and topology.
- Focused checks passed 26 environment tests and 37 feature-workflow tests, plus workflow Ruff
  lint/format and strict mypy. New linked-worktree cases cover UID 1000, UID 20023/GID 20024, stale
  settings, root refusal, missing/invalid host identity and production isolation.
- A separate synthetic `/tmp` checkout owned by 20023:20024 reproduced the exact frontend EACCES
  at UID 1000, then passed the same `pnpm format:check` with the corrected identity. Real non-root
  frontend/backend bind writes, backend media writes, fresh noninteractive dependency bootstrap,
  root-owned `.bin` repair, backend formatting/API drift and production configuration checks passed.
  Only the proven-new fixture resources were removed; the real checkout was never ownership-modified.
- Reviewed the correction and froze the tree before fresh `make feature-verify`; the canonical result
  and exact-worktree receipt are reported in the handoff. Correction remains uncommitted for operator
  review/redelivery on the existing branch and PR; no push, delivery, merge or finish was performed.

## 2026-10-02 — CI-003 safe foreign-source DEV recovery

- Fixed the independent review's recovery dead end: `dev-stop` no longer needs the primary or old
  Compose files to operate an existing DEV stack. Exact project/service/role (including recognized
  legacy metadata), source-mount and volume ownership checks identify DEV and fail closed on ambiguous
  resources. Stop retains its containers, network, DB/media/dependency volumes and all persistent data.
- Legacy media really uses Docker tmpfs, which disappears on stop. An initial isolated smoke caught
  Docker `cp`'s unsupported tmpfs view before any operator use. The final fixed helper reads the frozen
  backend's live filesystem through its PID namespace, exclusively copies missing regular files into
  the validated DEV attachment volume, verifies preservation and kills the frozen writer without a
  new-write window. Conflicts/copy errors leave the original backend alive; no media or volume is deleted.
- Primary startup accepts only a validated stopped stack, starts the retained DB without rebinding it,
  and refuses ahead/incompatible revisions before dependency initialization or application recreation.
  Explicit upgrade keeps the same revision guard; no automatic downgrade or implicit migration occurs.
  Stopped status reports retained source and exited state rather than cached healthy/running claims.
- Focused checks: 23 environment tests and 37 feature-workflow tests; workflow Ruff lint/format and
  strict mypy. Recovery coverage includes primary/foreign stop, old source absent, media conflicts,
  non-root ownership restoration, idempotence, ambiguous identity, destructive refusal, primary reuse
  and ahead-of-code state. Existing Review/Preview contracts and their isolation guards remain intact.
- `make smoke-dev-recovery` passed on a UUID-scoped real Compose fixture: vanished old source,
  tmpfs+durable media, DB rows and dependency state survive stop/recreation; services become healthy
  from primary; repeated stop is safe; ahead startup/upgrade refuse without downgrade. Operator DEV,
  Review, Preview, production and primary Git snapshots match before/after, including fixture cleanup.
- The prior receipt's digest `233acab3...` matched the dirty worktree. Its reported mismatch came from
  using the delivery check against uncommitted `HEAD`, not from stale source evidence. Added explicit
  `verify --worktree` for pre-commit review; default verification still requires both HEAD and working
  source for delivery. This fix changes the tree and requires fresh evidence. The final frozen-tree
  `make feature-verify` result and new exact-worktree receipt are reported in the handoff.
- Updated the canonical operator recovery flow and added the isolated smoke target. The live `8a70`
  DEV remains running and healthy; only read-only identity/status checks were performed on it. Primary
  is clean `main` at `4e90cce`; no real worktree creation, commit, push, delivery, merge or finish.

## 2026-10-02 — CI-003 environment/worktree workflow consolidation

- Discovered this Codex worktree clean/detached at `4e90cce`, identical to `origin/main` and primary
  `main`; attached `ci/development-environment-workflow` only here. No additional real worktree,
  commit, push, delivery, merge or finish was performed. Primary source/index remains untouched.
- Added idempotent existing-worktree initialization, isolated dirty-source Feature Review commands,
  primary-sourced DEV status/up/upgrade/stop, explicit production and worktree-quality projects,
  per-run disposable integration identity, automatic `.env` discovery and source/health/revision
  observability. DEV deliberately retains `florabase` to preserve existing operator volumes.
- Fresh named dependency/media volumes are initialized automatically; frontend stays non-root,
  bootstraps frozen dependencies without TTY and uses the pinned Corepack cache. DEV media is now
  persistent; legacy temporary media prevents unsafe recreation/stop. Revision compatibility guards
  distinguish code head from DB current and refuse ahead/incompatible state without downgrading.
- Stable Preview keeps clean `origin/main` source and immutable dependencies, uses its own stable
  overlay, rejects primary/other-branch paths and reports current/head. Its incomplete database-only
  import now refuses before mutation; coordinated DEV DB+media cloning is explicitly deferred.
- Delivery errors now print missing-CLI/auth/API/precondition evidence. Linked finish fast-forwards
  only clean primary `main`, retains the detached Codex checkout and atomically deletes only the
  proven merged branch. Receipt tests cover dirty/untracked migrations, symlinks, post-commit validity,
  later edits, per-worktree metadata, stale-evidence invalidation and edits during verification.
- Focused gates passed shell helper fixtures, 37 feature-workflow tests, 19 Preview tests, 13 environment
  tests, workflow Ruff lint/format and strict mypy for the new operational helpers, shell syntax,
  85-feature graph validation and whitespace checks. Early `make check` passed formatting/lint/types,
  550 backend unit tests, 339 frontend tests and API drift before final verification.
- Real `make smoke-environment-workflow` passed on this dirty linked source: untracked no-op migration
  applied only to Review, all three services healthy, frontend UID 1000, fresh noninteractive install,
  automated root-owned `.bin` repair, changed dependency/lockfile fixture, DB/media/dependency
  stop/restart persistence, Review-only destruction and independently healthy stable archive Preview.
  Production/integration configurations validate; smoke resource cleanup and DEV before/after
  container/mount/Git/revision snapshots match. No operator data was destroyed.
- Read-only `make dev-status` reveals the existing operator `florabase` project is still bound to the
  previous `8a70` worktree, with healthy services, temporary media root and DB revision 0030; selected
  primary code is also 0030. The command reports that source mismatch and refuses takeover. This
  legacy environment is deliberately left running and unchanged for operator reconciliation.
- [Canonical workflow](development-workflow.md), AGENTS, CONTRIBUTING, development/deployment guidance
  and the CI-003 graph entry are updated. CI-003 remains `implemented` pending independent infrastructure
  review. The frozen-tree canonical `make feature-verify` result and matching per-worktree receipt are
  reported in the handoff; no product graphical review is required. Public images/GHCR, release
  packaging, unrelated roadmap features and full DEV data cloning remain outside this increment.

## 2026-10-02 — lineage integrity audit for independent logical review

- Audited `320865b` / `fix/lineage-integrity-audit`, including HARVEST-001. Canonical ancestry uses
  explicit SeedLot/Sowing/Plant/PlantGroup foreign keys, including collection-produced SeedLot
  producers and immutable immediate extraction origins. Receipts, Events, Harvest, shared media,
  Location, geographic provenance/native ranges and botanical identity remain distinct. The
  [audit and invariant matrix](lineage-integrity.md) records corrections, historical retention,
  end-to-end representations, concurrency, query evidence and deferred capabilities.
- Reproduced three correction API cycles returning 200. All mutable source corrections now use
  the existing typed walker. Revision `20261002_0030` adds serialized acyclic graph writes and
  insertion-time source/result/Event correlation for all six receipt kinds. Existing cycles block
  upgrade without data repair; populated guard-only downgrade/reupgrade preserves all facts.
  READ COMMITTED graph-write isolation is enforced to avoid stale-snapshot lock races.
- Reproduced cached-ORM failures after competing commits in extraction, reintegration eligibility
  and SeedLot consumption. Locked reads now refresh current state before quantity/snapshot guards.
  Two further interleavings reproduced stale Plant/PlantGroup origin comparisons bypassing the
  reversed-Sowing guard; compare persisted origins before source-first row locking.
  Added complete exact/approximate/unknown extraction/reintegration/reversal histories, sibling and
  transfer isolation, five production generations, reference/Harvest/media separation, direct SQL
  corruption guards, stale-receipt correction, migration preservation and real lock contention.
- Semantic UI changes display ancestor lifecycle, prevent stale cross-record paths, and separate
  extracted Plants from direct Sowing results using an additive exact source-group API field.
  Both generated API artifacts are updated. No graphical polish, new lineage capability, feature ID
  or feature-status change is introduced; stale Event/reintegration documentation is corrected.
- Focused checks passed Ruff, strict mypy (240 source/test files), 83 backend unit tests, 72
  PostgreSQL tests, frontend lint/types and 68 affected frontend tests. The long-chain read returns
  22 ancestors in five statements. The main baseline test stages passed 546 backend / 336 frontend;
  its API-drift stage overlapped the contract edit and is superseded by final verification.
- The first full gate passed 550 backend unit and 339 frontend tests, then reached 434 successful
  PostgreSQL tests and failed the old expected migration-head assertion. Updated that assertion
  for revision 0030; the final gate is rerun after the confirmed origin-race fix.
- The next gate passed 550 backend unit tests (91.25% coverage), 339 frontend tests and 437
  PostgreSQL tests, production builds and the migration cycle, then failed receipt storage because
  `.git` is a file in this linked worktree. The helper now resolves its actual per-worktree Git
  metadata directory for write/read. A real linked-worktree regression and all 35 feature-workflow
  helper tests pass. Rerun the unchanged complete canonical gate on the final tree.
- Final full suites, API drift, feature graph/workflow helpers, production builds, migration cycle,
  whitespace and verification receipt run through `make feature-verify`; its exact completed result
  is reported in the handoff. No thresholds or runner settings are relaxed. The operator database
  is not upgraded; all work remains unstaged and uncommitted, with no push, delivery, merge or finish.

## 2026-10-01 — HARVEST-001 structured Harvest review handoff

- Continued `feat/structured-harvests` at `6a44a18`. Harvest records one Plant XOR PlantGroup,
  existing partial date, optional label/notes and 1–100 ordered material lines. Controlled material
  kinds, exact/approximate count or weight and unknown quantities retain explicit precision.
  Identity is derived from the source; lifecycle, group quantity, Location and seed inventory stay
  unchanged, including root, whole-plant and seed collection.
- Atomic aggregate writes own one protected harvest Event. Corrections update source/date/notes
  coherently; deletion removes Harvest and owned Event while retaining shared assets. Existing
  free-form harvest Events are preserved. Retained historical sources are selectable; concrete
  restrictive foreign keys protect their history. No source hard-delete API is introduced.
- Revision `20261001_0029` follows 0028. Concrete media/primary relationships extend the shared
  library. Immediate constraints and deferred aggregate/Event checks enforce final validity;
  populated downgrade refuses history loss and empty downgrade/reupgrade is supported.
- Added Collection navigation, directory/filters, compact desktop preview, detail, accessible
  multi-line forms, contextual source actions, identity Harvest history, Dashboard Quick action
  and structured Event links/images. Central image fallback preserves external-image privacy.
  Directory projection batches source/identity/material/image reads; 16 mixed-source records stay
  within eight statements.
- Baseline `make check` passed (502 backend unit tests, 90.89% coverage; 327 frontend tests).
  Development checks passed Ruff, backend/frontend typing and focused suites; 16 PostgreSQL tests
  cover rollback, coherence, source retention, media/primary membership and migration preservation.
  The complete canonical `make feature-verify` result and receipt are reported in the handoff;
  no thresholds, timeouts or runner settings are weakened.
- Browser review uses isolated synthetic data at 1440 × 844, 1024 × 844 and 390 × 844, covering
  directory/preview, one/multiple-item creation, correction, detail/media, Plant/PlantGroup contextual
  creation, activity/journal links, long names and partial/unknown dates/quantities. Keyboard material
  add/remove focus and dialog focus restoration were checked; no horizontal overflow was found.
  The [Harvest handoff](harvests.md) records the contract, review matrix and exact changed files.
- HARVEST-001 remains `implemented` pending operator acceptance. The tree stays unstaged and
  uncommitted on the same branch. Harvested-material inventory/disposition and explicit SeedLot
  conversion remain separate pre-1.0 candidates; all established roadmap milestones are preserved.

## 2026-10-01 — ATTACHMENT-005 persistent external copies

- Continued the same unstaged `feat/shared-media-library` tree. External assets keep their kind,
  canonical URL, attribution, UUID, links, primary selections and covers while optionally referencing
  one protected Attachment snapshot with UTC fetched-at metadata. Explicit Save/Refresh/Remove copy
  routes reuse original storage and shared derivatives; reads prefer saved content across views.
- Bounded fetches validate every DNS result and redirect, pin public IP connections, verify TLS
  hostnames, reject unsafe destinations/credentials, cap timeout/bytes, and reuse strict still-image
  decoding and pixel-bomb checks. Failed refresh retains the valid copy. Asset-row locks and a
  durable pending-cleanup pointer serialize copy/deletion actions and support explicit retry.
- Revision 0028 follows 0027, initializes old external copies as absent, performs no network access,
  and guards downgrade while copies/cleanup remain. Both migration contracts and the full empty
  cycle are covered. Persistent snapshots are included in paired original/database backups.
- Focused checks passed: Ruff, strict backend typing (229 files), 85 backend security/storage/media
  unit tests, 42 frontend media/photo/activity tests, frontend lint/types, and 19 PostgreSQL lifecycle,
  rollback, migration and real lock-race tests. The final canonical gate covers the complete tree;
  its result is reported in the handoff. No runner settings or thresholds are relaxed.
- Browser review at 1440 × 844, 1024 × 844 and 390 × 844 exercised real Save/Refresh, concise Gallery
  states, saved metadata, protected record/Photos/activity imagery, and removal confirmation with
  Escape focus restoration. No horizontal overflow was found. The tree remains unstaged and
  uncommitted; operator visual acceptance remains pending.

## 2026-10-01 — ATTACHMENT-005 shared media review handoff

- Continued the clean `feat/shared-media-library` branch at `1c4fbf1`, implementing the approved
  unlinked-media policy. MediaAsset owns one local original or attributed external reference;
  exact RecordMediaLinks retain the five established targets and independent caption/order.
  Explicit SeedLot/Plant/PlantGroup primary designations remain per target. Identity covers remain
  separate active references. Unlink and cover replacement retain assets; deletion requires zero
  collection links and zero covers, with no automatic cleanup or destructive cascade.
- Revision `20261001_0027` preserves existing IDs, files, technical/source metadata, targets,
  captions, chronological order, primary and cover references. Representative pre-upgrade data
  and guarded populated downgrade are tested. Empty downgrade/reupgrade is supported; populated
  rollback requires the coordinated pre-upgrade database/content backup.
- Added the paginated Media directory, compact preview, dedicated detail, shared metadata editor,
  record picker and record Photos link-existing workflow. External references stay unloaded in
  Gallery/Quick Preview and require explicit detail/Photos opt-in. Original storage/security and
  central record-image fallback remain. One locked, cached 320px WebP derivative serves every link.
- Baseline `make check` passed (433 backend / 310 frontend). Final focused checks passed Ruff,
  backend typing, 45 media/cover/API unit tests, frontend format/lint/typing and 81 Media/Photos/App
  tests. PostgreSQL migration, reference constraints, bounded queries, duplicate-link and
  link/delete races, primary serialization and HTTP auth/CSRF checks passed. The canonical
  `make feature-verify` runs the complete final suites, API drift, builds and migration cycle;
  its completed outcome and tree receipt are reported in the handoff. No thresholds or runner
  settings were weakened.
- Rendered review used disposable synthetic fixtures at 1440 × 844, 1024 × 844 and 390 × 844:
  Gallery/pagination/filters, landscape/portrait/square previews, detail, record Photos and both
  pickers; primary set/clear, link reuse, last-unlink retention, cover-only deletion guard, external
  opt-in/failure, empty search and keyboard Escape/focus restoration. Reviewed views have no
  horizontal overflow. The [media handoff](media-library.md) records contracts, resource/query
  evidence, migration/compatibility notes, review matrix and exact changed files.
- ATTACHMENT-005 is `implemented`, awaiting operator visual acceptance. Architecture/domain/storage/
  backup/deployment docs were updated, and the requested eight pre-1.0 roadmap milestones remain
  future work. No stage, commit, push, delivery, merge, branch switch or feature-finish is performed.

## 2026-10-01 — LOCATION-003 hierarchical usage final review

- Continued `feat/location-descendant-aggregation` at `c1fc7c5`. LOCATION-003 adds derived
  direct and arbitrary-depth inclusive usage for SeedLot, Sowing, Plant and PlantGroup. Legacy
  `usage` remains direct (including combined Plants/groups); additive `direct_usage` and
  `usage_including_descendants` expose the four types separately. Total/all-lifecycle and
  active-only semantics, assignment eligibility and child/direct/history deletion guards remain.
- The directory uses one hierarchy read plus one batched recursive PostgreSQL aggregate;
  distinct containment pairs terminate even for malformed cycles. No N+1 record queries,
  persisted counters, new indexes or migration are introduced. A representative planner check
  on 206 Locations/4,015 assignments reported 6.107 ms execution with one scan/aggregate per
  record type. Reparent tests verify both roots change without any record Location update.
- Directory and desktop Quick Preview show inclusive content with an explicit direct count when
  different, equal leaf counts once, and one empty message. Detail compares both scopes with
  per-type total/active counts. Existing general collection links are preserved: Location has
  no associated-record list, so no listing scope/default was introduced. Deep rows retain parent
  context and full paths while indentation stops growing after three levels.
- Focused checks passed 12 backend unit tests, 16 PostgreSQL Location/migration tests and
  66 frontend App/Location tests. Added coverage includes twelve-level trees, siblings, roots,
  empty branches, every lifecycle/type, source non-inference, cycle termination, two-query batching,
  additive API semantics, keyboard selection and deep-tree collapse/path context. Final complete
  suites and quality/API/build checks run through the canonical local gate; the completed result
  and tree receipt are reported with the handoff. No test settings or thresholds were weakened.
- Rendered review in the in-app browser covered 1440 × 844, 1024 × 844 and 390 × 844,
  including parent-only descendant content, mixed and leaf counts, empty Quick Preview, long paths
  and the expanded twelve-level mobile tree. Review found and fixed indentation collapse from
  26 px to a readable 211 px row. Final reviewed frames have no horizontal overflow; compact
  counts are included in the accessible row names. The [audit](location-descendant-aggregation.md)
  records contracts, query-plan evidence, visual matrix, screenshots and changed files.
- Operator visual acceptance and independent final review are complete. The review confirmed the
  direct/inclusive contract, all four canonical assignment types, unchanged legacy usage, recursive
  cycle-safe aggregation, dynamic reparenting, lifecycle semantics, API drift, existing deletion
  guards, and UI scope labels. No implementation defect or product ambiguity was found. The prior
  canonical verification receipt matches this tree; `git diff --check` passes. LOCATION-003 remains
  `implemented` pending final commit and delivery. All edits remain unstaged and uncommitted; no
  commit, push, merge, delivery or feature-finish ran.

## 2026-09-30 — Final operator pass 33–47 ready for visual acceptance

- Continued `feat/ui-consistency-polish` at `cd5bf70`, preserving prior work. Guided
  Sowing and Plant/PlantGroup forms now reuse normal field groups/section navigation,
  retain source/lineage, atomic quantity/result semantics and receipts, and use the
  existing display-name resolver. Nested native/server validation reveals and focuses
  the owning section without discarding state.
- Added accessible desktop sidebar resizing (248px default, 220px minimum, up to
  400px/35% of viewport), live route-preserving width and 32px collapsed inset. World
  initially expands to continents; user interaction remains. Shared More menus use
  anchored viewport-bounded portals with outside/Escape/focus behavior. Geography
  Sites/Map creation uses the existing page-header action pattern.
- BotanicalIdentity Edit groups existing Identity/Reference/Native range/Media owners;
  normal desktop sections fit, with independent detail navigation retained. Provenance
  Sites accept validated decimal or DMS inputs through unchanged decimal payloads.
  Labels adopts controls/preview composition and compact expandable print guidance,
  preserving dimensions, 4 × 9 print sheet and configured-origin QR semantics.
- Rendered review succeeded in the Codex in-app browser at 1440 × 844, 1024 × 844 and
  390 × 844 for every requested surface. The [audit](ui-consistency-polish.md) records
  the exact matrix, item 33–47 statuses, 108 chronological review captures and exact
  final-pass/complete branch manifests. Final frames replace QA-found quantity overflow,
  DMS label collisions, Botany spacing and tall Labels guidance. Operator acceptance
  remains pending. The synthetic tmpfs project was removed and browser overrides reset;
  no normal operator data or volumes were deleted.
- Affected checks passed 174 tests/10 files, compatibility checks 58/5 and final
  Seed/Labels checks 51/2. The final full frontend suite passed **304 tests/33 files**
  (19:57:22, 124.57s); formatting, zero-warning lint, strict TypeScript/production build,
  exporter/generator API drift, feature graph (81), Markdown formatting and diff checks
  passed. Intermediate interrupted execution is excluded from verification evidence.
- No backend/API/generated-contract/migration change was added by this final pass;
  earlier branch changes remain preserved. Supplier imagery/logo is explicitly post-0.1.0;
  Location `Direct here` / `Including descendants` remains a functional follow-up.
  UX-006 stays `implemented`. No canonical gate, staging, commit, push, merge, delivery
  or feature-finish ran. All work remains unstaged/uncommitted for visual acceptance.

## 2026-09-30 — Sectioned forms and shared record presentation ready for visual review

- Continued `feat/ui-consistency-polish` with the requested A–T refinement. Shared
  left-aligned workspaces begin 24px from the desktop sidebar, with surplus width
  on the right. A small shared form-section primitive keeps one mounted form/state,
  direct keyboard-accessible tabs, Back/Next, final-only submission and invalid-field
  reveal/focus. SeedLot, Sowing, Plant/PlantGroup, BotanicalProfile and ProvenanceSite
  editors use it; compact identity names and independent reference actions remain
  reachable. Existing payloads, partial dates, quantities and lineage are preserved.
- Centralized record imagery resolves local designated primary, eligible botanical
  cover, then type placeholder, including exact Event targets. Display names resolve
  explicit label, common name, useful cultivar, scientific name, then generic fallback
  without stored-name changes or numbering. Bounded photo cards and contained Botany
  preview images preserve aspect ratio. Sowing preview groups primary, maintenance
  and descendant actions. Reference shares shell, search and inset focus geometry.
- Rendered review completed at 1440 × 844, 1024 × 844 and 390 × 844 across all
  eleven requested routes and every required editor/photo/preview surface. The
  [audit](ui-consistency-polish.md) records the exact matrix, 117 final captures,
  image-shape checks, retained values and hidden native/server validation focus.
  QA-found small Seed rows, Sowing action sizing, mobile focus and activity badges
  were corrected. No page-wide horizontal overflow was found. Existing tablet/mobile
  selection opens detail directly where Quick Preview is desktop-only. The earlier
  browser limitation is resolved; final operator acceptance remains pending.
- Affected frontend checks passed 108 tests across 10 files; the complete final
  suite passed 281 tests across 30 files. Formatting, lint, TypeScript, production
  build, API exporter/generator drift, feature graph (81 features) and diff checks
  passed. No canonical gate or unrelated backend suite ran during this refinement;
  initial-phase backend/generated changes remain preserved.
- Shared media (`MediaAsset` ↔ `RecordMediaLink` ↔ records) and Location counts
  (`Direct here: 2` / `Including sublocations: 7`) remain documented follow-ups.
  UX-006 remains `implemented`; HEAD remains `cd5bf70`, all changes unstaged and
  uncommitted. No push, delivery, merge or finish ran. The synthetic review project
  and browser tab were removed without deleting operator data or volumes.

## 2026-09-30 — Final operator UI pass, rendered confirmation pending

- Continued `feat/ui-consistency-polish` for items 16–32. Shared desktop inset,
  compact Seed/Plant edit disclosures, Sowing action groups/facts/path, compact
  creation dependency panels, Plant origin/operations, neutral local-only directory
  photo slots, viewport-sized map, and scoped Botany cover/actions/edit/search fixes
  are implemented. The [audit](ui-consistency-polish.md) records the exact final-pass
  and 31-file branch manifests, each requested status and remaining visual checks.
  Shared media and Location subtree aggregation are documented follow-ups only;
  current direct usage and descendant-aware Dashboard filtering are unchanged.
- Focused checks passed 114 tests across eight files; the final complete frontend
  suite passed 268 tests across 27 files. An added note-retention assertion was
  corrected to retain original text; an intervening host-memory timeout run recovered
  with unchanged tests after stopping only the disposable review web services.
  Formatting, lint, TypeScript, production build, exporter/generator API drift,
  feature graph validation (81 features), Markdown formatting and diff checks passed.
- Rendered desktop checks confirmed compact Seed/Plant/Botany editors, keyboard
  access to Botany fields/actions, two-observation Germination, landscape cover and
  map composition. Final overview refinements, directory thumbnails/focus, actual
  Botany overflow scroll and the full 1024 × 844 / 390 × 844 matrix remain
  VISUAL_CONFIRMATION_PENDING: the browser connection disappeared under exhausted
  host memory and did not recover after tests recovered. Saved `final-` desktop
  screenshots remain available. Earlier 1–15 behavior passes regression checks;
  final responsive visual reconfirmation is pending, not claimed.
- Frontend/tests/docs only in this pass; earlier backend/generated changes are
  preserved. UX-006 remains `implemented`; HEAD is `cd5bf70`, with all changes
  unstaged/uncommitted. No gate, commit, push, delivery, merge or finish ran.
  The disposable review project was removed without operator volume/data changes.

## 2026-09-30 — Fifteen-item UI corrective pass for visual review

- Continued on `feat/ui-consistency-polish` with the focused Dashboard, Seeds,
  Sowings, Plants, Events and Provenance map corrections. The updated
  [audit](ui-consistency-polish.md) records one PASS receipt for each requested item,
  the exact 16 corrective-pass files and the full 26-file branch manifest. UX-006
  remains `implemented`; no feature graph status changed.
- Shared labelled record relationships clarify headers. Seed Remaining aligns in
  directory rows; grouped Seed/Sowing/Plant editors use desktop width. Sowing preview
  actions are grouped, Germination uses paired metrics/history, and propagation paths
  respond to their own available width. Plant group origin/history share a desktop row.
  Dashboard filter scroll controls reserve an inner gutter. Global Events and record
  journals reuse local-only target thumbnails without external/absent/broken placeholders.
  Map reuses the page intro and keeps its layers below mobile navigation. Existing
  values, validation, disclosures, operation guards, privacy and payloads are preserved.
- Corrective affected tests passed 113 cases across nine files; final full frontend
  tests passed 265 cases across 27 files. Frontend formatting, lint, TypeScript and
  production build passed. Existing API exporter/generator drift checks passed in the
  disposable review environment, feature graph validation passed (81 features), and
  Markdown formatting plus `git diff --check` passed. No backend/schema/generated
  contract edits were made during this corrective pass; initial-phase changes remain.
- Browser access recovered. Representative rendered checks covered 1440 × 844,
  1024 × 844, 1024 × 600 and 390 × 844, with the exact surface matrix in the audit.
  Long-label Seed edit height decreased approximately 39%; expanded individual Plant
  edit decreased 30% during review. The PlantGroup essentials editor fit 844px height.
  Measured views had no page-wide horizontal overflow; inset selected keyboard focus
  remained visible. Screenshots are saved in this task's visualization folder.
  Expanded editors, populated galleries/long history and operation receipts retain
  natural scrolling; exhaustive content/viewport combinations and operator visual
  acceptance remain pending. The disposable project was removed without deleting
  operator data or volumes.
- All changes remain unstaged and uncommitted at `cd5bf70`. No feature gate, delivery,
  push, merge or finish was run. Suppliers and deeper Reference work remain deferred.

## 2026-09-30 — Scoped UI consistency polish for visual review

- Implemented the reported Dashboard, Seeds, Sowings and Plants polish on
  `feat/ui-consistency-polish`. The [implementation audit](ui-consistency-polish.md) records the
  shared header/form/highlight rules, root causes, exact changed files and visual-review limits.
  UX-006 remains `implemented`; the feature graph is unchanged.
- Reused `WorkspaceIntro`, `Breadcrumbs`, `DetailHeader` and `PrimaryPhotoVisual`. Record/task
  headers reduce repeated context, forms use aligned responsive grids, fact values align and detail
  sections use desktop width. Sowing preview gives Open details primary emphasis. Inset result
  focus/selection and symmetric scrolling clearance resolve the identified clipping cause.
- Dashboard Events expose only the explicit Plant/PlantGroup target's designated primary photo,
  through the existing batched summary helper and protected local thumbnails. External designations
  remain neutral. No inheritance rule, migration, attachment/privacy change or unresolved domain
  decision was introduced. Existing disclosure, validation and payload contracts remain intact.
- Final affected frontend checks passed 87 tests across five files; the complete suite passed
  264 tests across 27 files. Frontend lint, formatting, TypeScript and production build passed.
  Backend focused tests passed 42 cases; Ruff formatting/lint and Event mypy checks passed. The
  affected PostgreSQL suites passed 17 tests, including Dashboard photo designation/clearing and
  thumbnail authorization. The first full integration run passed 357 tests and failed one exact
  response expectation; adding the new nullable target field to that expectation resolved it.
  No test timeout, sleep, retry, skip or runner change was introduced.
- API drift (`make api-check`), feature graph validation (81 valid features), Markdown formatting
  and `git diff --check` passed. Interim rendered review at 1440 × 844 covered Dashboard imagery and
  filters plus Seeds directory/preview/overview/detail with long context; no horizontal overflow was
  visible there. Browser access then became unavailable during host memory pressure. Final desktop,
  tablet and mobile layouts, affected editors and selected/focused result geometry remain pending
  operator visual review; responsive rendering is not claimed as verified. The disposable
  `florabase-ui-review` project was removed without deleting operator data or volumes.
- Work remains unstaged and uncommitted. No canonical feature gate, delivery, merge or finish
  workflow was run. Suppliers and the deeper Reference redesign remain intentionally deferred.

## 2026-09-30 — Plants and Plant groups UX consistency for visual review

- Refined the Plants-specific UX-006 implementation on `feat/plants-plantgroups-ux`; the feature
  graph remains unchanged and UX-006 remains `implemented`. The
  [audit and review notes](plants-plantgroups-ux.md) record findings, decisions, domain boundaries,
  rendered coverage and scoped follow-ups.
- Directory rows now prioritize identity, lifecycle and tracking type, with group-only exact,
  approximate or unknown quantity and wrapping recorded context. Designated collection photos also
  appear in the established desktop Quick Preview. Open details leads inspection; Edit leads normal
  correction, while extraction and whole-record transfer are secondary collection operations.
- Detail separates record summary, managed group, origin/provenance, notes and explicit extracted-Plant
  history. History uses only stored group origin and retains Reintegrated Plants without inferring
  current membership. Historical location/quantity labels describe retained facts; historical records
  do not show empty current-operation sections. Existing Events, Photos, Lineage, receipt reintegration
  and creation-reversal contracts remain intact.
- Both entry types put identity, label, group-only quantity and location in Essentials. Additional
  details retains mounted values, editing starts expanded, validation exposes corrective fields and
  focuses visible feedback, and final submit/Cancel actions follow the fields. Creation and structural
  dialog focus return behavior is covered. No shared component, backend, API, migration, dependency
  or persistence contract changed; the added styles are scoped to Plants.
- Live production-runtime review used only a separate disposable `florabase-ux-review` Compose
  project. Inspected 1440 × 844, 1024 × 844, 390 × 844 and 1024 × 600: populated and single-record
  directories, no-match/empty states, long botanical names/location paths, sparse records, landscape
  and portrait primary photos, disclosure, detail and dialogs. No horizontal overflow was observed.
  Exercised Plant creation/edit/location correction, movement Event and protected Photos; group
  creation with unknown quantity, approximate/exact edits, extraction and receipt reintegration,
  retained relationship history and authoritative Events. The review project was removed without
  volume-deletion commands; operator projects and data were preserved.
- The affected suite (`pnpm exec vitest run --configLoader runner src/plants/PlantScreen.test.tsx`)
  passed 38 tests; `pnpm test` passed 260 tests across 26 files using the repository's existing runner
  configuration. Thirteen behavioral cases were added
  for disclosure/value retention, quantities, sparse identity, stored extraction links, primary-photo
  privacy, historical facts and focus/validation. An overlapping test/lint attempt failed under host
  memory pressure; final tests passed with checks separated. Timeouts, runner settings, retries and
  skip behavior were not changed.
- Frontend `pnpm lint`, `pnpm format:check`, `pnpm typecheck` and `pnpm build` passed, as did
  Prettier checks for both changed Markdown documents. API drift (`make api-check`),
  `python3 scripts/check-features.py` (81 valid features) and `git diff --check` passed. The
  implementation is unstaged and uncommitted for independent visual review; no `feature-deliver` or
  `feature-finish` workflow was run. Suppliers and Reference remain candidates for their separate
  consistency passes.

## 2026-09-29 — independent shell and propagation UX QA

- Independently swept Dashboard, Seeds, Sowings, Plants and Plant groups, Suppliers, Botanical
  identities, Locations, Geography and provenance sites, Provenance map, Events, Labels, and Import /
  Export. Rendered checks covered 1440 × 844, 1024 × 844, 390 × 844, and 1024 × 600. Sidebar hide
  and reopen preserved the mounted workspace; hidden navigation had no focusable descendants, and
  state reset on reload. No shared-shell overflow, clipping, or route-width regression was found.
- Review corrected exact-zero Sowing copy and guarded observed percentages and T50 against zero-count
  denominators even if a response supplies derived values. Added boundary coverage for exact positive,
  approximate, weight, unknown, absent and zero quantities in list/detail paths. Test helpers now wait
  for the route or collection state the test needs; the session-expiry Plant test keeps its login-path
  assertion without waiting for an authenticated page title.
- The full frontend suite passed (247 / 247 tests, 26 files). `make check` and `make feature-verify`
  returned successfully; the latter recorded the final tree, ran disposable integration tests and
  production builds, and confirmed no Alembic revisions were added. `git diff --check` passed.
  No files were staged or committed.
- Follow-up gate review found that pytest-cov's `--cov-fail-under=90` was active, while
  coverage.py's default zero-decimal precision rounded 89.82% to 90 for its exit-status comparison.
  The raw pytest process therefore returned status 0; Make, the feature gate, and CI did not swallow
  an upstream failure. Coverage reports now use two-decimal precision, and a policy regression test
  locks both the 90% threshold and precise comparison. Focused germination-service tests cover
  validation and mutation paths; the direct backend run now passes 431 tests at 90.52% with status 0.

This log preserves meaningful verified milestones and current repository state. Exact acceptance
criteria and current status live in [`features.json`](features.json); Git history retains line-level
implementation detail.

## 2026-09-29 — shell and Sowings pre-release polish for operator review

- The desktop sidebar now hides and reopens with labeled keyboard controls while keeping the same
  workspace mounted. At 1440 × 844 and 1024 × 844 in the disposable preview, all groups and the
  account footer fitted without sidebar scrolling; hiding reclaimed the full workspace width.
  Navigation is Overview, Collection, Reference and Tools, with Botanical identities under Reference.
  The shared shell no longer adds an outer page-like background, shadow or clipping edge; it keeps
  readable maximum width and responsive gutters. Mobile retains its existing navigation behavior.
- New Seed lot is a single task without a duplicate top action. Essentials and Inventory stay in the
  fast-entry flow; Acquisition, Storage, Provenance, Seed details and Notes use a labeled disclosure
  that retains entered values. Quantity, source and partial-date controls are grouped with their
  related fields; final Add to collection and Cancel actions follow the form. Existing exact,
  approximate, unknown, supplier, storage and geographic-origin meanings remain unchanged.
- Sowings now uses a compact scrolling directory and persistent Quick Preview on desktop, with
  explicit identity, source, context, lifecycle and germination row information. Percentages use only
  a positive exact Sowing seed count as denominator; approximate, mass and unknown quantities keep
  text-only germination totals. Overview separates Source, Sowing, Germination, Results, Cultivation
  and Notes. Direct creation and editing use grouped fields and additional details; the Seed lot
  guided task remains distinct. Germination observations remain evidence, with derived values shown
  only when available. Descendant tasks distinguish the result and resulting Sowing state.
- The full frontend suite passed with one worker (247 tests across 26 files) before the final mobile
  row and descendant-copy corrections. After those edits, formatting, lint, TypeScript, production
  build, the exact affected descendant test and whitespace checks passed. API drift passed earlier;
  neither final edit touched the API. A broader
  focused rerun on the loaded host missed several lazy-screen waits; that run is not counted as a
  pass. `make check` passed formatting, lint, typing and all 425 backend unit tests, but its two
  Docker frontend runs exited with different slow-test failures (246/247 and 242/247). The
  originally timed-out Geography case then passed unchanged in the same Docker image; the two
  variable Plants/Seeds files passed unchanged with one worker (48/48). No test timeout, assertion
  or implementation was weakened for the loaded
  host. The disposable browser pass checked shell fit, hide/show, workspace width, Seeds creation,
  and Sowings directory, preview and detail at 1440 × 844 and 1024 × 844. A reopened 390 × 844
  preview exposed cramped Sowing row wrapping; a mobile-only grid correction was rebuilt and visually
  rechecked. Mobile Seed lot
  create, additional details, Sowing detail, New Sowing, Germination and Sowing-to-Plant forms used
  natural page scrolling without horizontal overflow. A 1440 × 844 route sweep covered Dashboard,
  Plants, Events, Botanical identities, Suppliers, Locations, Geography, Labels, Import / Export
  and the provenance map for headings and shell width. At 1024 × 600 the sidebar navigation scrolls
  while its account footer stays visible. The disposable stack was removed. No backend, API, schema,
  migration, dependency, eager route import or per-row request changed. All work remains unstaged
  and uncommitted; `make feature-verify` is reserved for the authorized later phase.

## 2026-09-28 — Seeds vertical UI polish for operator review

- Dashboard Quick actions now contains four collection and four reference creation links, each using
  the existing route and creation form. The Tools shortcuts were removed from that panel; both tools
  remain in the sidebar. Clicking an active sidebar destination returns to its canonical root and
  resets transient workspace state without a document reload. An edited form asks before discarding
  changes. Plants retains `+ New plant or group` because that button still opens a choice between
  individual Plant and PlantGroup creation.
- Seeds now gives its inventory more desktop width, compact two-line rows, a bounded list scroll
  area, and a persistent inspector. Rows, preview and detail distinguish active remaining quantity
  from a historical recorded quantity and preserve exact, approximate and unknown wording. The
  inspector shows the available Start sowing action and concise status, storage and Supplier facts.
  Overview uses separate Inventory, Source & origin, Dates & condition and Notes groups, with
  consistent internal links. The editor groups every existing field by task and keeps advanced
  fields visible during correction.
- Guided sowing shows the source lot and its state before entry, then requires an explicit choice to
  keep inventory unchanged, use part or use the whole lot. Exact compatible partial use previews
  its remainder; approximate partial use asks for a confirmed estimate without arithmetic; unknown
  stays unknown. The final step states the resulting operation and retains cancel, validation and
  conflict recovery. No backend, API, schema, migration, dependency or per-row data request changed.
- An authoritative original denominator is not stored for SeedLots. Receipts and current Sowings do
  not establish an all-time total after corrections and reversals, so a numeric utilization bar or
  used percentage would imply unsupported precision. This remains a domain decision for a separate
  increment; this pass shows the stored quantity and lifecycle truthfully.
- The disposable populated preview was reviewed at 1440 × 844, 1024 × 844 and 390 × 844 for Seeds
  directory, selection, filters, search, preview, detail tabs, editor, guided sowing, validation and
  active-sidebar reset. Disposable approximate, unknown and exhausted lots confirmed truthful row,
  preview and guided-use states alongside the exact fixture. Desktop list scroll and mobile natural
  document scroll were confirmed with
  no horizontal overflow. The final mobile pass restored bottom clearance below the fixed navigation
  so the guided form's Cancel link and editor actions remain reachable. The preview was removed after
  review. Focused tests passed, the full
  frontend suite passed (245 tests across 26 files), and `make check` passed formatting, lint,
  backend and frontend type checks, backend and frontend tests, and API drift. Production build and
  whitespace checks also passed. Changes remain unstaged and uncommitted; independent Seeds visual
  review precedes `make feature-verify`.

## 2026-09-28 — cross-application UI consistency for review

- Completed the existing Dashboard launcher with compact Create, Reference workspaces and Tools
  groups. New seed lot, sowing, plant and plant group links open their existing creation flows; the
  sowing link still requires an explicit SeedLot choice. Botanical identities, Suppliers, Locations
  and Geography link to their workspaces because they have no canonical direct-create route. Events
  remain contextual to a Plant or PlantGroup, so there is no global Event shortcut.
- Aligned major workspace eyebrow, title and one-sentence subtitle copy with the reviewed product
  terminology. Plants now says `+ New plant or group` because its button offers both creation paths;
  Seed lots and Sowings use explicit sentence-case actions. Mobile Seeds, Sowings and Plants titles
  now use the same compact 32 px scale as the other workspaces. Existing detail headers were
  inspected without changing their record structure or content.
- The route title flash came from bare loading/error `<h2>` elements on Seeds, Sowings and Plants
  inheriting the global large heading style before each compact ready header appeared. These states
  now share one `WorkspaceIntro` structure and copy. The lazy-route Suspense fallback is a restrained,
  title-free skeleton; route-level lazy imports and the separate chunk-failure recovery boundary remain.
  A deferred-module test covers the unresolved-chunk transition without introducing a duplicate title.
- Live disposable populated-preview navigation covered Dashboard → Seeds → Sowings → Plants → Events
  → Botanical identities → Suppliers → Geography → Labels → Dashboard at 1440 × 844 and 1024 × 844;
  mobile navigation and the same major routes were reviewed at 390 × 844. Loading and ready headers,
  the mobile More menu, four creation links, Quick actions, detail header structure, sidebar stability
  and horizontal overflow were inspected. No oversized title, competing header, white flash or
  horizontal overflow was observed. The preview was removed after review.
- Focused frontend tests passed (64 in the final focused rerun), followed by the full frontend suite
  (235 tests across 26 files); lint, formatting, TypeScript, production build and `git diff --check`
  passed. The build retains 39 lazy JavaScript chunks, 761,743 raw JS bytes total (1,396 above the
  preceding Dashboard pass), largest chunk 208,532 bytes (298 above), and 114,488 raw CSS bytes
  (891 above), without a Vite size advisory. No dependency, eager route/map loading, backend, API,
  schema or migration changed. This review boundary remains unstaged and uncommitted; the canonical
  `make feature-verify` gate is reserved for the later authorized phase.

## 2026-09-28 — Dashboard and sidebar-brand review pass

- On `fix/release-ui-polish`, gave the existing serif sidebar wordmark a dedicated block with aligned
  left padding, a restrained divider and normal letter spacing. Live inspection caught inherited
  negative heading letter spacing that had visually compressed the brand; the corrected wordmark is
  fully readable without widening the sidebar. The account footer and compact shell remain in place.
- Dashboard keeps its existing search, filters, four holding counts, Event data and four actions.
  Below the compact snapshot, Recent activity occupies the primary desktop column and Quick actions
  sits in a compact secondary panel. The activity list alone scrolls beneath its persistent heading
  and View all Events link. Compact Event rows align kind/date, record/badge and botanical context;
  internal links use the Florabase green for normal and visited states, with visible keyboard focus.
  Count links now announce their label and value clearly to assistive technology.
- The populated disposable preview was inspected at 1440 × 844, 1024 × 844 and 390 × 844. Both
  desktop widths had no document or horizontal overflow; activity scrolls within its column. At
  1024, search moves below the heading to preserve a usable width while the two columns remain.
  Mobile presents header, search, 2 × 2 snapshot, actions and activity in order, with natural page
  scrolling and no nested activity scroll pane. The preview was removed after review.
- Focused Dashboard/shell tests passed (58), full frontend tests passed (233), and frontend lint,
  formatting, TypeScript and final production build passed. The build retains 39 lazy JavaScript
  chunks, totaling 760,347 raw bytes (156 above the previous polish receipt); largest is 208,234
  bytes (26 above). CSS totals 113,597 raw bytes including the existing Labels stylesheet, with no
  Vite size advisory. No dependency, API, backend, schema or migration changed. The Dashboard visual
  direction awaits operator review; this pass remains unstaged and uncommitted.

## 2026-09-28 — final pre-release UI polish for visual review

- Kept the frozen 0.1.0 product scope and current `fix/release-ui-polish` branch. The full-height
  sidebar now carries brand, account and Sign out; the main masthead is gone. Shared compact headers
  and flex/grid workspace sizing replace viewport subtraction heights on desktop. Seeds, Sowings,
  Plants, Events, Botanical identities, Suppliers, Locations, Geography hierarchy and provenance
  sites use their result region as the principal scroll surface. Dashboard's activity list takes
  the remaining space. Mobile retains its navigation and natural document scrolling.
- Suppliers use compact list rows with direct-record context. Geography now exposes Places,
  Provenance sites and Map as peer views, retaining the stored-coordinate map and accessible
  companion list. Labels retain the approved A4 print geometry and temporary state while showing
  remaining sheet capacity and keeping the record picker visible during desktop composition.
- No domain, API, schema, migration, authentication, photo, map-provider or persistence contract
  changed. PERF-001 route and optional-map lazy loading remains in place. Browser review used the
  guarded disposable populated fixture at 1440 × 844, 1024 × 844 and 390 × 844; directory, timeline,
  hierarchy, selection, search and mobile scroll ownership were inspected without changing operator
  data. The fixture was removed after review. Empty and loading states, long botanical names, label
  copies and removal remain covered by focused component tests; physical label geometry was unchanged.
- Focused frontend checks passed: 81 App/Labels cases on the final code. `make check` passed backend and
  frontend formatting, lint and type checks, 425 backend unit tests, 232 frontend tests, and API
  drift. The existing pytest-cov 89.82% warning still prints against a whole-percent 90% setting,
  while pytest and the canonical `make check` exit successfully as explained in PERF-001.
  `pnpm build`, feature graph validation (81 features), and whitespace checks passed. The production build
  retains 39 JavaScript chunks: 760,191 raw bytes total versus PERF-001's 759,387; largest chunk
  208,208 versus 207,746 bytes, with no Vite size advisory. CSS grows to 110,231 raw bytes from the
  documented 100,981 because the shared viewport layouts are new. No dependency or eager route/map
  loading was added. Independent visual review remains before any release-hardening work.

## 2026-09-27 — PERF-001 implemented for independent review

- Preserved the untouched `d5a9da5` baseline, frozen protocol and comparison evidence in
  [PERF-001 report](performance/PERF-001.md), `baseline.json` and `after.json`. The guarded disposable
  `florabase-perf` project reuses production runtime images/topology with tmpfs PostgreSQL/media,
  loopback preview-style cookies and deterministic personal-collection data. Operator stacks/data
  were preserved; measurements ran separately from checks/builds. Maps use explicit deterministic
  browser responses; three separate live summary probes returned 200 with no eligible fixture data.
- Measured hotspots justified response-local geography maps, distinct-site serialization and reused
  loaded geography in SeedLot/Plant/PlantGroup responses, native lazy workspaces/wizards with loading
  and download-failure recovery, and public-static nginx gzip. API/schema/security/privacy/domain
  contracts and Vite advisory threshold remain unchanged; no index, migration, broad cache or pool
  tuning was justified. Alembic remains `20260925_0026`.
- Identical 28-read workloads retain seven repetitions, median/range, first-call timing, payload
  sizes and SQL counts; first comparison, warmed repeat and final repeat are all retained. Initial
  browser JS/CSS is 691,307→117,364 bytes (~83% less); initial requests 9→18; largest chunk 207,746
  bytes with no large-chunk advisory. Total all-workspace JS grows ~1.6% raw/~13% independently gzipped.
  Final SeedLot/Geography/Plant medians are 46.0/15.4/47.2ms versus 122.3/64.2/82.8ms baseline, but
  unchanged controls also become faster, so not all timing improvement is attributed to the fixes.
  SeedLot/Plant query counts drop 11→10; exact captured EXPLAIN plans did not justify new indexes.
- Final browser run has no errors, six cycles of 53 requests, stable DOM/listeners, no Dashboard maps
  or timers, and 122s idle with zero requests, unchanged session timestamps and five idle database
  connections. Runtime container memory settles around 298MiB with this tmpfs fixture; the report
  records health-check CPU, image/process/startup costs and no unsupported hardware guarantee.
  Thumbnail/original transfers, local Photos laziness and external opt-in remain intact. Larger full
  directories, provider/network latency and all-workspace chunk overhead remain documented costs.
- Regression coverage adds hierarchy reuse/integrity tests, three PostgreSQL query-count tests at
  1/20 records, workspace deferral/module reuse and failed-chunk recovery, and four benchmark safety
  guards. Focused runs: 36 backend, 54 frontend and 3 PostgreSQL cases passed. Existing UI assertions
  now await lazy-route readiness without weakening their assertions or timeouts.
- Final serial `make check` exits 0: formatting, Ruff, zero-warning ESLint, strict mypy (215 files),
  TypeScript, 425 backend unit tests, 230 frontend tests (25 files), and API drift check. **Coverage
  caveat:** pytest reports 89.82% against the configured 90% and prints a failure message while the
  command continues successfully. Independent review confirmed coverage.py defaults to 0-digit
  precision, so `round(89.82, 0)` meets the configured whole-percent 90% gate; pytest-cov separately
  prints a red unrounded warning without changing pytest's exit status. The message is misleading;
  threshold and precision remain unchanged.
  `make test-integration`: 357 passed/425 deselected/118 warnings in 132.97s. Production runtime build,
  actual static gzip/protected-response integrity, helper safety/lint/format/syntax checks and feature
  graph validation pass. Host Python 3.12 lacks existing `uuid7`; successful checks use Docker 3.14.7.
  An interrupted high-memory-pressure run was replaced with complete serial runs, not counted as proof.
- Independent final review found and corrected two narrow defects: a workspace error boundary that
  could mask unrelated lazy-module failures, and duplicate `/healthz` Content-Type headers. Recovery
  now recognizes only dynamic-import fetch/MIME `TypeError`s; a rebuilt Chromium run against the real
  hidden Seeds chunk showed the SPA fallback, recovery UI and retained authenticated shell without a
  document reload. Fresh production responses reproduced 10 SeedLot/Plant and 6 PlantGroup query
  counts; gzip/Vary, identity fallback, no-store runtime config, uncompressed protected API and the
  corrected plain-text health response all passed. The reviewed source/image identities and measured
  response details are in `after.json` and this report.
- Independent final `make feature-verify` passed all stages: quality, 425 backend unit tests, 232
  frontend tests, 357 PostgreSQL integration tests, generated API drift, production build, feature
  graph and migration checks. The 89.82% coverage line still prints pytest-cov's misleading warning,
  but the configured zero-precision 90% gate passes and the canonical command exits 0. PERF-001 is
  now `verified`; no staging, commit, push, delivery, merge, branch switch or finish was performed.
  RELEASE-001 should repeat the documented sanity workload on the exact candidate, real target
  hardware/persistent storage and HTTPS, alongside security/mobile/keyboard/installation/recovery.

## 2026-09-27 — LABEL-001 implemented for operator physical/visual review

- Added a temporary authenticated Labels workspace and secondary Print label detail actions for
  SeedLot, Plant, and PlantGroup. Reused the searchable ReferencePicker and existing protected record
  APIs; add/remove, copy counts, empty/retry/error states, keyboard operation, and responsive preview
  prepare one fresh A4 sheet of up to 36 labels. No persistence, migration, API change, numbering,
  photo loading, public record page, or server PDF service was introduced.
- Labels show the existing BotanicalIdentity display name, record type, optional existing record
  label, Florabase, and locally generated SVG QR. QR payloads contain only existing detail routes
  and validated UUIDs; login and authorization remain unchanged. Pinned the small
  dependency-free MIT `qrcode-generator` 2.0.4 and distributed its license notice with frontend assets.
- Fixed physical border-box cells are 50 × 30 mm, with a 22 mm QR and four-module quiet zone.
  Named A4 print CSS gives 4 × 9 cells, a 200 × 270 mm grid, 5 mm horizontal/13.5 mm vertical margins,
  no gutters, no scaling, no split labels, and only sheet output. Operator instructions require
  100% / Actual size and no Fit to page.
- Chromium fixture review covered empty/one/mixed/duplicate/long/cultivar/partial-name states at
  1440 × 844, 1024 × 844, and 390 × 844 with no page overflow or external requests. Print media
  measured all 36 cells at 188.96875 × 113.375 CSS px with no transform/zoom; ordinary print-to-PDF
  produced one A4 page. An independent decoder recovered all distinct exact record URLs from SVG
  rasterization and from 300 dpi crops of the actual printed PDF. Physical printer/system-dialog
  validation remains with the operator.

## 2026-09-27 — LABEL-001 independent final review

- Review found that the QR origin was browser-derived. QR generation now uses the existing
  `FLORABASE_CANONICAL_ORIGIN`, returned by the authenticated session API, so proxy/browser aliases
  cannot change a durable printed URL. Development produces the configured `http://localhost:5173`
  origin and production uses its configured HTTPS domain. Credential-bearing canonical origins are
  rejected. The additive authenticated-session response field is reflected in generated OpenAPI and
  frontend types; no endpoint, setting, migration, or public lookup behavior was added.
- Added regression coverage for canonical development and production URLs, browser-origin
  independence, invalid origins, and configured session output. The independent browser reached the
  sign-in screen; authenticated UI and print media were not visually re-reviewed without credentials.
  Operator reports functional UAT complete. Physical printer/system-dialog validation remains open.
- `make feature-verify` passed on the final LABEL-001 review tree: feature graph, formatting, lint,
  mypy, TypeScript, 423 backend unit tests, 228 frontend tests, API drift, 354 PostgreSQL integration
  tests, production builds, migration cycle (no new revision), whitespace check, and verification
  receipt. Backend coverage reported 89.77% against the nominal 90% threshold while the canonical
  gate succeeded, consistent with the existing rounding behavior. LABEL-001 is now `verified` in
  `features.json`; all changes remain unstaged and uncommitted. Physical printer/system-dialog checks
  remain open.
- Checks passed: 20 focused label cases; broad `make check` (422 backend unit and 220 frontend tests,
  Ruff, strict mypy, Prettier, ESLint, TypeScript, generated API drift); 354 isolated PostgreSQL tests
  including three new protected lookup/error cases; production frontend image; feature graph (81),
  diff whitespace, and same-origin health/readiness. The unchanged 89.75% coverage summary/rounded
  exit-status discrepancy documented for ATTACHMENT-004, Alembic warnings, and Vite chunk advisory
  remain. See [implementation review](label-001-review.md) and [operator guide](labels.md).
- LABEL-001 is `implemented`, not `verified`. All changes remain unstaged and uncommitted;
  independent `make feature-verify`, final commit, and delivery were intentionally reserved.

## 2026-09-26 — ATTACHMENT-004 implemented; operator visual review passed

- Added Alembic revision `20260925_0026` and a separate UUIDv7 `CollectionPrimaryPhoto` table with
  exactly one supported target/source and unique target/source constraints. No primary is inferred
  on migration, upload, or deletion. Selection locks the concrete target, existing photo, and local
  Attachment, validates exact ownership and active/presentable content, and changes designation only.
  Supported targets are SeedLot, Plant, and PlantGroup; Sowing and Event Photos and BotanicalIdentity
  reference covers remain separate.
- Added protected typed primary read/set/clear operations and a fixed authenticated local-photo
  WebP thumbnail using the existing safe decode/orientation mechanics, trusted storage resolver,
  320px maximum edge, no upscale, private digest/version ETag, and no persisted derivative. Directory
  response builders batch only compact primary summaries, without per-row metadata/gallery requests.
  External primaries render a neutral indicator and retain the gallery's explicit remote-load choice.
- Local deletion clears designation in the first pending-delete transaction, including failed-unlink
  retry behavior. External deletion clears it in the same metadata transaction; defensive source FK
  cascades guard final cleanup. Primary changes and metadata edits preserve gallery history/order.
  Photos actions update the mounted detail and directory state coherently.
- Browser review used an isolated disposable fixture for A–J: absent photos, one unselected photo,
  selected local primary, change, clear, selected-local deletion, Plant, PlantGroup, external primary,
  and excluded Sowing Photos. Reviewed representative directory/detail/gallery layouts at 1440px,
  1024px, and 390×844, including mobile action reachability and no page overflow. External views had
  no remote image element before explicit loading; a full Network-panel capture was not available.
  Selected-local browser deletion used the protected API followed by a browser refresh; focused UI
  tests cover authoritative designation refresh after photo removal. This is implementation fixture
  review, not operator UAT.
- Focused checks passed: 13 collection-photo backend unit tests; 19 PostgreSQL attachment/photo/API
  and migration integration tests, including upgrade/downgrade/re-upgrade preserving all existing
  Attachment, local/external photo, and BotanicalIdentity-cover metadata; 50 SeedLot/Plant unit and
  88 directory/detail API integration tests; 39 existing SeedLot/Plant screen tests and 11
  photo/primary frontend tests; Ruff formatting/lint and strict mypy; frontend
  Prettier/ESLint/TypeScript; backend production image and frontend production build; generated
  OpenAPI and frontend schema drift. Alembic emits its existing `path_separator` deprecation warning;
  Vite retains its existing large-chunk warning. Feature graph and final diff checks complete the
  handoff. See [implementation handoff](attachment-004-review.md) for exact commands and boundaries.
- ATTACHMENT-004 is `implemented`, not `verified`. Independent QA, `make feature-verify`, and the
  final local commit remain for Luna. No staging, commit, delivery, or production database migration
  was performed.

## 2026-09-27 — ATTACHMENT-004 independent QA

- Fixed the designation deletion/replacement race by locking the designation row during replacement;
  added a PostgreSQL concurrency regression test. Updated the integration assertions for migration
  head `20260925_0026` and the new table.
- Added focused unit coverage for selection and thumbnail route contracts. The canonical
  `make feature-verify` passed: 422 backend unit tests, 197 frontend tests, 351 PostgreSQL tests,
  production builds, generated API drift, and migration cycle `0025 → 0026 → 0025 → 0026`.
- The independent QA browser tool could not access the local review app. The operator subsequently
  completed the manual viewport and lifecycle review and reported a pass. Final review found the
  coverage display inconsistency documented in `attachment-004-review.md`; no coverage policy was
  changed.

## 2026-09-25 — GERMINATION-001 implemented for operator visual review

- Added Alembic revision `20260925_0025` for exact-day, non-negative incremental germination
  observations, with one row per Sowing/date and a restrictive Sowing foreign key. Observation
  mutations and Sowing edits lock the Sowing row before validating the independent cumulative total
  against an exact seed count. Exact date edits cannot move sowing after an observation. The existing
  operator-maintained `germinated_count` remains independent; corrections do not change lifecycle,
  Events, propagation, or descendants.
- Added protected typed germination detail and observation CRUD APIs. The backend derives chronological
  cumulative counts, first positive observation, elapsed days where the Sowing date is exact,
  exact-seed percentage, and decimal T50 from half the exact seeds sown using linear interpolation.
  Missing date/denominator/threshold inputs return absent values rather than fabricated metrics.
  Generated OpenAPI and frontend declarations are updated.
- Added a read-first Sowing Germination tab with concise separate totals, missing-data explanations,
  focused add/edit/delete dialogs, and a chronological table that stacks on mobile. A disposable
  browser fixture covered no observations, zero-only and populated history, full metrics,
  approximate quantity, partial date, threshold not reached, edit, delete, and mobile rows at
  1440px, 1024px, and 390×844. This was implementation-level fixture review, not operator UAT.
- Focused checks: 14 backend unit tests; 3 PostgreSQL migration, service and API integration tests;
  Python 3.14 Ruff and mypy; Sowing frontend component tests, Prettier, ESLint, TypeScript, and
  production build; generated OpenAPI drift, feature graph, and diff whitespace checks. The
  independent review, canonical `make feature-verify`, and commit remain for Luna.

## 2026-09-25 — GERMINATION-001 independent QA complete

- Added regression coverage for odd-count T50, baseline and multi-zero interpolation, exact inputs,
  endpoint authentication/CSRF/Origin, chronological insertion order, zero and exact-bound counts,
  CRUD corrections, and Sowing date/quantity edits. A two-session PostgreSQL test confirms one of
  two concurrent writes that exceed the exact seed total is rejected. Updated stale repository
  integration assertions for the new table and Alembic head.
- Independent checks passed: 11 germination unit cases, the Sowing frontend suite (15 tests), and
  the targeted PostgreSQL checks. The full frontend suite passed (190 tests across 21 files).
  Canonical `make feature-verify` passed with 414 backend unit tests and 348 PostgreSQL integration
  tests, including the migration upgrade/downgrade/re-upgrade cycle, generated API drift, frontend
  checks, production builds, and workflow helpers.
- GERMINATION-001 remains `implemented`; the exact verified tree is ready for the requested local
  commit. No production-code correction was required.

## 2026-09-25 — SEARCH-001 independent QA correction

- Corrected Event search context projection to select the BotanicalIdentity belonging to the
  Event's actual Plant or PlantGroup target. Regression coverage confirms both targets, readable
  context when optional labels are absent, unique Event hits, and existing result routes.
- Extended Dashboard QA for actual browser Back/Forward transitions, structured-filter restoration
  after remount, and out-of-order search responses. Search integration coverage also checks
  authentication, record domains, explicit relationships, combined filters, deterministic ordering,
  bounded pages, response privacy, and typed API validation.
- Focused checks passed: 5 PostgreSQL search integration tests, 403 backend unit tests at 90.60%
  coverage (including search API/service and Event tests), 189 frontend tests, 4 focused Dashboard
  search tests, backend Ruff/mypy, frontend Prettier/ESLint/strict TypeScript/build, API drift,
  feature graph, and `git diff --check`. Canonical verification follows on the final reviewed tree.

## 2026-09-25 — SEARCH-001 operator visual correction

- Styled the four existing Dashboard Quick-action links as compact secondary buttons. Their routes,
  normal-state placement, keyboard semantics, and search prominence remain unchanged.
- Tightened grouped search results into a consistent full-width row pattern. Type headings now keep
  counts beside their labels, bounded groups state the loaded and total counts, and repeated title
  context is suppressed. The total sits by the results heading; one lightweight Back to Dashboard
  control also serves the empty state. Collection, Botany, and Reference remain separate.
- Disposable browser fixture review covered normal Dashboard, one and many results, Event, Botany,
  Reference, and empty states at 1440px, 1024px, and 390×844. Quick actions wrapped on mobile; no
  whole-page horizontal overflow appeared. Event kind and target remain visible. Event dates are
  absent from the existing search-result payload and were left unchanged in this presentation-only
  pass.
- Focused frontend Prettier, ESLint, strict TypeScript, 21 component tests, production build, and
  `git diff --check` passed. No backend files changed; the canonical gate remains for later review.

## 2026-09-25 — SEARCH-001 implemented for operator visual review

- Made the authenticated Dashboard the global collection-search entry point without adding a
  navigation destination. Search-active state replaces the snapshot, Quick actions, and activity
  feed; clearing it restores them. Hash query parameters retain text and structured filters across
  refresh and browser history. Normal Dashboard Quick actions now open Add seed lot, Add plant, Add
  plant group, and Import / Export before recent activity. Sowing creation stays on its SeedLot's
  authoritative propagation workflow.
- Added a typed, server-side `/api/v1/search` contract for Collection records (SeedLot, Sowing,
  Plant, PlantGroup, Event), Botany (BotanicalIdentity and separate BotanicalProfile reference
  knowledge), and Reference (Supplier, Location, GeographicPlace, ProvenanceSite). Literal,
  case-insensitive text matching uses persisted labels, notes, identities, and explicit current
  relationships. Filters cover record kind, identity, applicable lifecycle or Event kind, current
  Location and descendants, direct Supplier/place/site, and type-specific recorded year. Results
  sort deterministically and page per kind with exact counts. No schema, index, or migration changed.
- Documented exact search semantics in `docs/search.md`; generated OpenAPI and frontend types; set
  SEARCH-001 to `implemented` pending operator visual review and independent final verification.
  Earlier disposable browser fixture review covered the Dashboard, filters, grouped results, and
  1440px, 1024px, and 390×844 layouts without whole-page horizontal overflow. The fixture was
  presentation-only; focused PostgreSQL tests exercised the live query behavior.
- Focused verification: 15 adjacent backend unit tests, 3 PostgreSQL search integration tests,
  21 Dashboard search and adjacent UX component tests, backend Ruff/mypy, frontend
  Prettier/ESLint/strict TypeScript, generated API drift, production builds, feature graph,
  documentation formatting, and `git diff --check` passed.
  `make feature-verify` remains reserved for the authorized later phase.

## 2026-09-24 — IMPORT-001 independent final review

- Independently reviewed the import contract, signed preview/apply flow, ordinary domain-service
  writes, CSV safety, frontend states, and feature graph. Added database-independent coverage for
  remaining format, reference-choice, export, and API token cases. No implementation defects were
  found; IMPORT-001 remains `implemented` pending delivery.
- `make feature-verify` passed: 393 backend unit tests at 90.41% coverage, all 337 PostgreSQL
  integration tests, 185 frontend tests, generated API drift, production builds, migration checks
  (no revision added), and the feature verification receipt. The final review reruns this gate on
  the complete tree before the local commit.

## 2026-09-24 — IMPORT-001 visual and information hierarchy correction

- Made Import the dominant desktop task with a compact secondary Export panel, a four-step
  Template → Upload → Preview → Import indicator, a grouped template/example/guide tool set, and
  clearer record-type, file, and validation controls. The recommended import order remains visible
  as supporting information. No CSV, API, domain, or preview/apply semantics changed.
- Moved the field guide below the top Import/Export row. A semantic, scroll-contained table keeps
  every field's meaning, requirement, accepted format, example, and notes scannable on wider
  screens; compact separator rows show the same information on mobile. Preview now uses quieter
  filters and row dividers, with Supplier changes compared in Field / Existing / CSV columns.
- Browser fixture review at 1440px, 1024px, and 390x844 covered the initial workspace, Supplier
  guide and update choice, long Seed lot guide, valid Seed lot preview, and invalid Supplier preview.
  No whole-page horizontal overflow appeared. The fixture mocked API responses; prior PostgreSQL
  integration checks covered actual backend behavior. Focused frontend component tests, Prettier,
  ESLint, strict TypeScript, production build, and `git diff --check` passed. No backend checks or
  `make feature-verify` ran in this presentation-only pass.

## 2026-09-24 — IMPORT-001 operator-UAT corrections

- Removed `record_ref` from all six normal import templates. Advanced CSVs may still supply an
  existing UUID explicitly, and exports retain UUID relationships. Preview now shows exact existing
  BotanicalIdentity, Supplier, and Location candidates with explicit Use existing, Update existing
  (current Supplier only), or Create separate choices where the domain permits them. Ambiguous
  relationship names and paths show actual candidate choices. A same-tuple BotanicalIdentity cannot
  be created separately; SeedLot, Plant, and PlantGroup imports remain create-only.
- Supplier Update existing shows a field-level diff and uses the ordinary update service. Blank CSV
  cells retain existing values. Preview stays read-only; signed choices bind to the reviewed bytes,
  session, candidate state, and confirmation time. Apply revalidates, locks Supplier updates, and
  rolls the entire file back on a later failure or stale choice.
- Added shared narrow enum/whitespace normalization with canonical values shown in Preview, clearer
  invalid-value messages, six downloadable valid examples, and a responsive in-app field guide.
  Template headers, examples, and field descriptions come from the same backend CSV contract.
  Updated `docs/import-export.md`; no schema or migration changed. The pre-0.1.0 roadmap selection
  remains unchanged.
- Browser review against a disposable fixture using realistic CSV files covered a new and existing
  identity, a new and existing Supplier, `Nursery` normalization, an invalid Supplier kind, a
  Location, and a Seed lot with readable relationships. At 1440px, 1024px, and 390x844 there was no
  whole-page horizontal overflow. The review corrected the cramped 1024px card layout and radio
  controls that stretched away from their labels. The guide and choice controls remained readable
  on mobile; the example link was visible for every selected type. The fixture mocked API responses;
  the separate PostgreSQL integration tests exercised actual backend Preview and Apply behavior.
- Focused checks: 17 backend unit tests, 13 PostgreSQL integration tests, 3 frontend component
  tests, Ruff formatting/lint, mypy, Prettier/ESLint/TypeScript, generated API drift, production
  frontend and backend image builds, feature graph, and `git diff --check` passed. The canonical
  `make feature-verify` gate remains with the independent final reviewer.

## 2026-09-24 — IMPORT-001 implemented for operator visual review

- Added separate bounded CSV imports for BotanicalIdentity, Supplier, Location, SeedLot, direct-origin
  Plant, and direct-origin PlantGroup. Exact headers, UTF-8/BOM handling, 2 MiB/2,000-row limits,
  schema and reference validation, row-level outcomes, and in-file Location parent keys are
  documented in `docs/import-export.md`. Preview only reads domain records. A 15-minute,
  session-bound confirmation token binds apply to the exact reviewed bytes; apply revalidates and
  commits one file atomically through existing create services. Existing collection records are not
  merged or silently skipped.
- Added authenticated, deterministic CSV export for these types with UUID relationships, readable
  companion labels/paths, partial dates, quantity certainty, lifecycle, and spreadsheet formula
  protection. Export is neither backup nor full-fidelity transfer. Sowing, sowing-origin descendants,
  Events, operation receipts, photos, and direct lineage import remain outside this contract; no
  historical operation receipts are fabricated. No schema or migration changed.
- Added one Import / Export workspace with type selection, template downloads, format help, file
  validation, filtered row-level preview, explicit confirmation, and result/retry states. A
  disposable browser fixture showed the preview and unresolved/invalid rows at 1440px, 1024px, and
  390×844 with no page horizontal overflow. This was UI layout review against a fixture; operator
  UAT on real collection data and the independent canonical gate remain outstanding.
- Recorded the operator's pre-0.1.0 selection of IMPORT-001, SEARCH-001, GERMINATION-001, LABEL-001,
  and planned ATTACHMENT-004. PWA-001, LINEAGE-003, ORDER-001, and DASHBOARD-001 remain post-0.1.0
  by default. IMPORT-001 is `implemented`, not `verified`; ATTACHMENT-004 is `planned` and not built.
- Focused checks passed: 10 backend unit tests, 7 PostgreSQL integration tests, 2 frontend Vitest
  flow, backend Ruff formatting/lint and mypy, frontend Prettier/lint/typecheck and production
  build, generated API drift, feature graph (81 valid features), documentation formatting, and
  `git diff --check`. The existing Vite chunk-size advisory remains. `make feature-verify` was
  intentionally reserved for independent final review after operator UAT.

## 2026-09-24 — approved 0.1.0 release boundary and resource phase recorded for review

- Added planned P0 `PERF-001` with dependencies on UX-006 and MAP-002. It requires a reproducible
  production-like resource baseline over idle and representative collection workflows, focused
  optimization of demonstrated backend, database, frontend, media, map, Docker, and long-running
  hotspots, then repeat measurement and documented modest self-hosting expectations. UX-006 supplies
  the redesigned collection and provenance-map path; MAP-002 directly supplies the occurrence-map
  path outside UX-006's dependency closure. No resource target is invented before measurement.
- Added planned P0 `RELEASE-001` with focused dependencies on UX-006, ATTACHMENT-002, CI-002, and
  PERF-001. Its acceptance contract covers production installation and upgrade, complete
  database-plus-media recovery, end-to-end collection UAT, security and failure review,
  responsive/accessibility review, final release-candidate resource sanity against PERF-001 results,
  accurate operator documentation, version policy, and first changelog entry. No optional product
  candidate became a dependency of either required increment; `BOTANY-003` remains planned and is
  explicitly post-0.1.0 under the current provider-content constraint.
- Replaced stale roadmap release sequencing with required, optional, and post-release boundaries.
  Corrected current-state UX review prose and the README/deployment claims that collection photos,
  contextual help, and attachment storage were absent or that a database-only backup was sufficient.
  No application behavior, schema, API, or release tooling changed. The operator still needs to
  select any optional pre-release work and, during `RELEASE-001`, settle supported upgrade/version
  expectations, licensing, and the first changelog entry.
- Focused checks: `python3 -m json.tool docs/features.json`, `python3 scripts/check-features.py`
  (80 valid features), priority/category and required-dependency assertions, changed-document
  internal-link checks, Prettier on changed Markdown/JSON, and `git diff --check` passed. The
  canonical application gate is reserved for independent review of this documentation-only graph
  change.

## 2026-09-24 — UX-006 independently reviewed and ready for delivery

- Audited the merged UX-004/UX-005 directory, preview, detail, task, help and responsive patterns against SeedLot, Sowing, Plant/PlantGroup, propagation, Events, Photos, Lineage and Dashboard. The operational directories mixed selection with nearly full detail, large editors competed with browsing, and repeated borders and permanent explanations obscured the record and next action.
- Seed lots, Sowings and Plants/Groups now share polished search, compact record-first rows, lifecycle/type filters, selected and focus states, a compact Quick Preview and dedicated read-first detail. Large create/edit forms open as explicit tasks with grouped core and optional fields; desktop and mobile use the same record routes, including Back/Forward and direct links. Existing quantity certainty, partial dates, source, provenance, lifecycle and explicit lineage rules remain intact.
- Dashboard now shows linked collection holdings, recent recorded Events and valid quick actions. Global Events uses a chronological activity view with compact category filters and contextual non-replay guidance. Propagation and Plant operation surfaces clarify next actions, source/result/quantity effects, receipt-dependent reversal and reintegration, while Photos and Lineage use the shared restrained presentation and retain their existing privacy and relationship boundaries.
- Browser inspection with existing representative records covered populated Dashboard, SeedLot/Sowing/Plant/Group browsing and detail, Events, Photos, Lineage, creation and extraction at 1440px, 1024px and 390×844. Review corrected extraction Cancel focus restoration, type-specific unlabelled-record fallbacks, a repeat-selection loading defect, narrow Plant-detail overflow, raw origin ID and compact desktop header wrap. No operator records were changed. The operator has accepted the general design direction; minor polish in historical and receipt-edge presentation is deferred to final cross-app UAT.
- Added UX-006 as `implemented` in the feature graph and aligned the roadmap. No backend, API, generated declaration, schema, migration, dependency or persistence change was made. Focused verification passed: 78 tests across six Vitest files, with all 23 Plant cases rerun after the final focus and label corrections; `pnpm format:check`, `pnpm lint`, `pnpm typecheck`, `pnpm build`, `python3 scripts/check-features.py` (78 valid features), and `git diff --check`. `make feature-verify` passed: 358 backend tests, 182 frontend tests, integration suite, generated API drift, type/lint/format checks, production builds, migration cycle, whitespace checks and verification receipt. Vite retained its chunk-size advisory. UX-006 remains `implemented` pending delivery workflow.

## 2026-09-23 — UX-005 independent review

- The operator accepted the general design direction and deferred minor visual refinements. Independent review confirmed the UX-005-only frontend/documentation scope, preserved explicit provenance and hierarchy semantics, lazy maps, and no backend, generated API, schema, migration, or dependency changes. UX-005 remains `implemented`; no UX-006 record was added.
- Corrected two data/error edge cases in the site and place inspectors: zero accuracy now displays, local places with a null type are not labeled canonical, and non-conflict delete failures no longer claim a relationship conflict. Pending site/place saves now disable their form controls. Shared dialog and menu focus-return regressions were strengthened.

## 2026-09-23 — UX-005 operator UAT corrections ready for visual review

- Fixed the shared dialog flash-close defect: React StrictMode effect replay closed the native dialog during cleanup, and its queued `close` event dismissed the newly reopened state. TaskDialog now handles intentional native cancellation without treating programmatic cleanup as user dismissal. The shared OverflowMenu now dismisses on outside pointer/focus, Escape, action selection and opening a peer, with listener cleanup and focus return. Focused StrictMode and menu regressions cover repeated open/close, focus trapping and outside interaction.
- Location filtering auto-reveals matching descendants and ancestors while preserving manual collapse/reopen for the current filter; a changed filter recomputes the initial expansion, and clearing it restores the unfiltered tree. Location, Supplier, Geographic Place and Provenance Site details now use compact read-first headers, structured relationships, usage figures and record lists; rare actions remain in More. A shared directory search and selected-row treatment bring Supplier, Location and Geography closer to BotanicalIdentity, whose selected card is now visibly distinct from focus and hover.
- Browser UAT with representative data inspected Supplier, Location, Geography, Provenance sites and BotanicalIdentity across 1440px, 1024px and 390×844: dialogs remained open until dismissed, menu outside-click worked, filtered branches stayed manually collapsed, linked material remained readable, mobile action rows aligned, and no horizontal overflow was found. The temporary browser fixture was removed. Focused verification: 63 tests across four Vitest files, followed by 53 App tests on the final handler edit; `pnpm lint`, `pnpm typecheck`, `pnpm format:check`, `pnpm build`, and `git diff --check` passed. Vite retained its chunk-size advisory. The operator has accepted the general design direction; minor visual refinements are deferred. The independent review and canonical verification follow this UAT milestone.

## 2026-09-23 — UX-005 implemented for operator visual review

- Audited UX-004's merged BotanicalIdentity patterns and the existing Supplier, Location, Geography, Provenance-site and collection-map workflows. The old surfaces mixed selection with full editing, showed permanent forms and repeated bordered panels, while the map competed with its list. Kept their recorded relationships, hierarchy, route meanings and loading/error behavior.
- Separated Supplier directory, compact list-backed Quick Preview and hash-routed detail. Detail reads contact, notes, recent acquisitions and directly linked material before editing; create and edit use a shared accessible dialog, and retirement stays in More.
- Recast Location as a hierarchy browser with search over names and paths, explicit usage-scope filtering, ancestor context, compact preview and dedicated read-first detail. Multiple roots, arbitrary depth, child creation, lifecycle and guarded edits/deletion keep the existing backend semantics.
- Organized Geography into Browse (Places and Provenance sites) and Map. The place browser distinguishes immutable canonical nodes from editable local nodes. Site browse keeps coordinate-less records visible; map mode lazily loads Leaflet for stored coordinate pairs only, with synchronized marker, list and site inspector. Place and site forms open on explicit create/edit intent.
- Made the separate collection provenance map the main surface with a companion site list and selected direct-record inspector. Its filters, direct-only record associations, markers, attribution and backend contract remain unchanged. Shared UX-004 PageHeader, QuickPreview, DetailHeader, StatStrip, Breadcrumbs and OverflowMenu vocabulary was reused; the small TaskDialog primitive supplies modal focus, Escape, Cancel and focus return.
- Reviewed representative data in the browser at 1440px, 1024px and 390×844 across directory, detail, hierarchy, browse/map, selected records and dialogs. Corrected row density, mobile tree alignment, page chrome and map layout; checked that no horizontal overflow remained. The temporary fixture was removed. The operator's final visual acceptance remains outstanding.
- Added UX-005 as `implemented` in `features.json`, updated the roadmap's scoped handoff, and corrected stale `docs/progress.md` current-state statuses against the feature registry. No backend, API, schema or migration change was made. Focused verification: `pnpm exec vitest run --configLoader runner src/App.test.tsx src/provenance-sites/ProvenanceSiteManager.test.tsx src/provenance-map/ProvenanceMapScreen.test.tsx` (60 passed); `pnpm lint`, `pnpm typecheck`, `pnpm format:check`, `pnpm build`, `git diff --check`, and feature-registry JSON validation passed. The production build retained Vite's chunk-size advisory; the map remains a separate lazy chunk. `make feature-verify` is reserved for independent final review after operator acceptance.

## 2026-09-22 — UX-004 operator-accepted reference ready for delivery

- Tightened the BotanicalIdentity directory into catalog rows with a polished search control and
  small collection context. The directory itself is the bounded scrolling region beside a compact,
  non-sticky Quick Preview; the page heading remains in a stable catalog frame. The navigation sits
  within a continuous full-height green column. Creation now uses a focused modal with trapped
  keyboard focus, Escape, validation retention and trigger restoration instead of expanding the page.
- Limited the rich cover-and-summary row to Overview and contained its representative image at the
  requested compact scale. Collection, Reference and Events use a shorter work header containing the
  identity context and the same Add/Edit/More hierarchy, so task content starts sooner at desktop,
  compact desktop and mobile widths.
- Simplified Overview to record dates and recent activity without repeating summary counts or names.
  Collection now distinguishes its segmented inner navigation from the main tabs and separates next
  actions from records, especially a source-seed-lot sowing launcher followed by a separate Recorded
  sowings section. Human-facing Seed lot, Sowing, Plant and Plant group wording replaces backend-style
  labels on the touched reference surfaces.
- Made Reference read-first and split it into Profile, Native range, Botanical source and Occurrences
  modules, with only the chosen module mounted. Profile fields render as a dossier until Add/Edit;
  Save and Cancel return to read mode. Native-range controls appear only after Manage, provider
  change/unlink actions live in anchored, Escape-closing More menus, and occurrence evidence remains
  an explicit load with its semantics and privacy detail behind accessible disclosures. Raw cover
  URLs and routine successful backend status no longer appear in the botanical UI. Trigger focus is
  restored across profile and native-range mode changes.
- Corrected the visible GBIF taxon action to `/taxon/{opaqueId}` without changing provider APIs,
  tightened cover credit to Photo / Source / Licence, and recorded possible occurrence caching plus
  post-0.1.0 operator-triggered botanical retrieval as contract-dependent future work only.
- Added the nullable stored external cover URL to the existing single-query directory projection.
  Configured external covers now render immediately in cards and Quick Preview without selection or
  per-record requests, using lazy loading, asynchronous decoding and no-referrer browser requests.
  Visible cards can contact their configured external hosts; Florabase still does not proxy, cache,
  discover or choose an external image. Local cards retain the authenticated thumbnail route and all
  broken or missing images retain the botanical fallback.
- Browser inspection used a temporary local representative-data fixture, removed afterward. It
  covered the 21-record bounded directory, creation dialog and focus restoration, local/external/
  no-cover states, long names, Quick Preview, Overview density, compact work headers, Collection
  subsections, all four Reference modules, native-range form, exact GBIF link and provider menu at
  1440px, 1024px and 390×844. The mobile image stays within 256px, fixed navigation leaves enough
  scroll clearance for provider actions, the continuous shell holds, and no horizontal overflow or
  browser console warning/error appeared.
- The independent review aligned the roadmap and reference guide with accepted operator behavior,
  narrowed mobile scroll spacing to BotanicalIdentity detail, and corrected the remaining user-facing
  Plant group and transfer terminology. No persistence, migration, dependency, unrelated screen redesign,
  occurrence cache, or botanical enrichment was added. UX-004 remains `implemented`; minor aesthetic
  refinements are deferred to later increments.
- Final `make feature-verify` passed on the reviewed tree: 358 backend unit tests at 90.18% coverage,
  171 frontend tests, 324 disposable PostgreSQL integration tests, workflow/feature helpers, format,
  lint, typing, generated API drift, production build, migration-cycle check (no Alembic revisions),
  whitespace validation and a recorded verification receipt. No unresolved technical or product
  contract issues remain; minor visual refinements stay deferred to later scoped increments.

## 2026-09-19 — UX-004 implemented; operator visual review required

- Audited global styling and the BotanicalIdentity directory/detail mixture. Added a restrained
  paper/green/sage vocabulary, spacing and radius tokens, editorial names, integrated image cards,
  a small shared PageHeader/QuickPreview/StatStrip/FormSection/FormActions set, and limited shell
  polish. Other entity screens and maps keep their structure; visible Transfer, GBIF taxon and
  Provenance site terminology is corrected without domain changes.
- Separated searchable directory, compact desktop preview and dedicated hash-routed detail. Preview
  uses only list metadata. Below 68rem cards open details directly; existing deep links select the
  new Overview / Collection / Reference / Events navigation and Seeds / Sowings / Plants subviews.
  Cover management is secondary within the hero. Existing profile/native-range/provider, cover,
  collection creation, history, guarded delete and contextual-help behaviors remain available.
- Added active record counts to the existing directory response through one grouped SQL query;
  independent aggregates prevent multiplication and per-record fetches. Generated OpenAPI and
  TypeScript declarations are updated. Directory/preview retain bounded local thumbnails and
  external-cover placeholders; Reference and occurrence-map lazy boundaries remain intact. No
  migration, domain model, framework, telemetry or remote visual dependency was added.
- Focused verification covers directory image privacy, selection versus keyboard focus, compact
  preview requests, detail routes and back/forward, legacy subsections, lazy Reference, mobile
  navigation, form grouping/help/validation, cover and guarded edit/delete behavior. Added a
  PostgreSQL regression for exact active counts, empty identities and a single directory query.
  Final canonical gate: `make feature-verify`; its working-tree receipt records successful checks.
- Browser layout checks used the actual application components with temporary mocked data at
  1440px, 1024px and 390×844, including mobile detail/Reference forms and a long unbroken scientific
  name. No horizontal overflow was observed. Temporary fixture files were removed; the real app
  remains behind owner login. These checks do not replace operator review of actual collection data.
- At that milestone, the next checkpoint was `OPERATOR_VISUAL_REVIEW` on desktop and mobile. The
  operator accepted the direction on 2026-09-22; remaining entity redesign and release hardening stay
  deferred to their own increments. UX-004 remains `implemented`.

## 2026-09-19 — UX-002 implemented

- Audited current create/edit forms and guided propagation, Event, transfer, extraction,
  reintegration, reversal, reference-selection, profile, provenance, and cover-image workflows after
  UX-003. Kept self-explanatory names, labels, contact fields, Notes, and ordinary actions free of
  extra help chrome while targeting domain boundaries that can change an operator's answer.
- Added one local layered-help system: concise inline text uses `aria-describedby`; expandable
  examples use named keyboard/touch buttons and semantic regions with Escape focus restoration; and
  focused modal help traps focus, closes with Escape, and returns focus for genuinely complex
  creation reversal semantics. The layout remains inline and full-width on narrow screens rather
  than using hover bubbles.
- Covered exact/approximate/unknown quantity, count-versus-weight, partial-date precision, current
  collection Location versus biological provenance, Supplier versus origin, shared botanical
  identity versus lineage, one-packet-per-SeedLot identity, Plant versus PlantGroup tracking, Event
  journal versus state-changing creation behavior, native range versus material provenance,
  external-image credit/licence metadata, and reversible-operation consequences.
- Added focused interaction and integration coverage for help/error description composition,
  keyboard activation, screen-reader names and regions, Escape/focus behavior, deliberate absence
  of help on Notes, existing form submission, and the affected SeedLot, Sowing, Plant/Event, and
  reversal workflows. Frontend type checking and linting pass; 60 focused tests pass. Canonical
  `make feature-verify` passes all 357 backend tests at 90.09% coverage, 159 frontend tests, and 323
  disposable PostgreSQL integration tests, plus feature/workflow checks, formatting, linting, strict
  typing, generated API drift, production builds, and whitespace checks. It detects no added Alembic
  revision. No API, generated contract, backend, persistence, or telemetry changed; UX-002 remains
  `implemented` pending independent review and release UAT.

## 2026-09-14 — UX-003 implemented

- Audited the complete collection workflow after maps, photos, transfer, propagation, and reversal
  work. Standardized desktop navigation in `Seeds → Sowings → Plants → Events` lifecycle order and
  kept the five-item mobile bar focused on Home, Seeds, Sowings, Plants, and an accessible More menu
  that leads with Events and preserves the secondary identity, map, and reference destinations.
- Made major collection lists lead with each record's own label and use BotanicalIdentity as
  supporting context. Detail headers now surface the natural next operation—add a SeedLot, start a
  Sowing, create a Plant/PlantGroup, extract, or transfer—before correction controls, while rare
  reversal and destructive actions remain separated. Stored BotanicalIdentity, source SeedLot or
  Sowing, original PlantGroup, Location, Supplier, provenance, and Event relationships gained direct
  navigation without inferring lineage from shared identity.
- Restructured BotanicalIdentity into Overview, Reference, Seeds, Sowings, Plants, and Events. Cover
  and collection summaries remain in Overview; profile, structured native range, and advisory
  external occurrence evidence share a distinct Reference surface. Hidden reference/collection
  panels no longer cause unnecessary eager requests, occurrence maps remain explicit-load, and
  external covers are not requested by compact directory views.
- Added a fixed-purpose authenticated local-cover thumbnail endpoint. It decodes the validated local
  cover under Pillow's bounds, applies orientation, preserves aspect ratio, never upscales, and emits
  WebP with a maximum 320-pixel edge. Private caching uses an ETag derived from attachment SHA-256
  and the transform version; conditional requests can return 304 before decoding. The endpoint does
  not expose storage paths, persist derivatives, proxy external images, or provide generic resize
  controls. Directory rows use this endpoint for local covers, a neutral external-cover indicator,
  and a clean no-cover fallback.
- Completed consistent tab-to-panel ARIA relationships, semantic panels, record-first headings,
  linked status/context fields, wrapping action groups, and deep-linkable Location selection.
  Collection-wide Events explicitly remain journal history whose ordinary edits/deletes do not
  recompute current state.
- Focused verification covers thumbnail dimensions, format, authentication, ownership behavior,
  private validators and 304 handling, external/missing cover behavior, absence of a generic resize
  route, navigation/action hierarchy, lifecycle cross-links, mobile structure, tab semantics, lazy
  reference loading, and existing Plant/Sowing flows. Canonical verification evidence is recorded by
  `make feature-verify`; UX-003 remains `implemented` pending independent review and final browser
  UAT.

## 2026-09-14 — ATTACHMENT-003 implemented

- Added revision `20260913_0024` with separate `LocalCollectionPhoto`, `ExternalImageReference`, and
  `BotanicalIdentityCoverImage` tables. Collection photos retain exactly one explicit target among
  SeedLot, Sowing, Plant, PlantGroup, and Event. The separate cover row has one unique
  BotanicalIdentity, exactly one local/external source mode, unique local Attachment ownership, and
  HTTPS/attribution constraints. A transaction-locked database guard prevents one Attachment from
  being a collection photo and identity cover simultaneously; populated photo or cover metadata
  blocks downgrade.
- Added authenticated target-scoped listing and owner/CSRF-protected upload, create, metadata-edit,
  and remove APIs. Local upload reuses ATTACHMENT-002 validation/storage and coordinates Attachment
  plus relationship persistence with cleanup on relation failure. Local removal preserves
  `active → pending_delete → unlink → relationship/Attachment deletion`, leaving failed or missing
  content as a hidden retry-only relationship. Direct Attachment deletion and Event hard deletion
  are blocked while a photo owns or references them; historical targets still accept photos.
- Added a reusable responsive Photos section to SeedLot, Sowing, Plant, and PlantGroup details and a
  focused Event-history dialog. Galleries distinguish uploaded content from external references,
  order by creation time then ID, cover empty/loading/broken/mutation states, and use caption-based
  or record-context alt text. External images show attribution and source host without loading,
  require an explicit privacy-disclosed browser action, send no referrer, and are never fetched by
  the backend.
- Added a conservative current cover to BotanicalIdentity details with local upload or attributed
  external HTTPS metadata, explicit external-host privacy acknowledgement, automatic no-referrer
  rendering after opt-in, and accessible replace/remove flows. Local replacement/removal composes
  with ATTACHMENT-002 pending-delete retries; external changes are metadata-only. Cover ownership
  blocks direct Attachment deletion, and an identity with a cover receives a meaningful deletion
  conflict. No automatic discovery, provider search, cover history, album or reordering, EXIF
  inspection, thumbnail, derivative, background media worker, list-card rendering, or
  BotanicalIdentity gallery was introduced; compact imagery remains for `UX-003` with a justified
  thumbnail strategy.
- Verification: focused affected backend tests (`35 passed`) and focused photo/cover component tests
  (`7 passed`); the backend suite (`354 passed`, 90.21% coverage), frontend suite (`150 passed`),
  and disposable PostgreSQL integration suite (`323 passed`) pass. The canonical
  `make feature-verify` gate covers those suites plus feature/workflow checks, API drift, production
  builds, the `0023 ↔ 0024` migration cycle with populated-data guard, whitespace, and the
  working-tree receipt.

## 2026-09-13 — ATTACHMENT-002 verified

- Added a narrow Attachment aggregate and Alembic revision `20260913_0023`: application-generated
  UUIDv7 metadata identifies active or retryable `pending_delete` still-image content while a
  separate opaque UUIDv7-derived key selects a backend-owned local path. No collection-record,
  Event, external-image, gallery, caption, attribution, or cover-image relationship was introduced.
- Added owner/CSRF-protected streaming upload and deletion plus owner-protected metadata/content
  retrieval. Uploads are limited to exactly 25 MiB and fully decode as one still JPEG, PNG, or WebP;
  normalized filenames remain display-only, SHA-256 and size are stored, permanent placement uses
  an atomic same-filesystem rename, storage keys resolve beneath one trusted root, and responses do
  not expose paths. Two-phase pending deletion makes unlink and metadata failures retryable.
- Added the backend-only `attachment_data` volume, non-root UID/GID 10001 ownership, 0700 directory
  permissions, isolated development/integration tmpfs roots, and a 32 MiB API proxy ceiling for
  multipart overhead. Backup and restore now quiesce writes, require a same-timestamp PostgreSQL
  dump/attachment tar pair, reject unsafe archive members, and verify stored sizes and SHA-256.
- Independent review confirmed the streaming size, full-decode, opaque-path, deletion-state, volume,
  migration, and archive boundaries. It tightened metadata/content retrieval to the owner session
  with `private, no-store` responses, rejects restore artifact filename/timestamp mismatches before
  Docker operations, adds exact-limit-minus-one and decompression-warning regression coverage, and
  removes redundant builder-stage filesystem setup.
- The final canonical `make feature-verify` covers the feature graph, workflow helpers, formatting,
  linting, strict typing, backend/frontend tests, API drift, disposable PostgreSQL integration,
  production image builds, the `0022 → 0023 → 0022 → 0023` migration cycle, whitespace, and a
  working-tree verification receipt. ATTACHMENT-002 is verified; ATTACHMENT-003 remains planned.

## 2026-09-12 — MAP-002 implemented

- Proved the current production GBIF path before implementation with documented Catalogue of Life
  XR fixture `Q2M4` and checklist `7ddf754f-d193-4cc9-b351-99906754a03b`. Exact occurrence search
  returned 437,168 PRESENT records and 431,970 coordinate-bearing PRESENT records without flagged
  geospatial issues; the same opaque ID, checklist, status, and quality filters returned a valid
  256-pixel PNG from the Maps v2 ad-hoc hex-density route. Runtime uses only the confirmed stored
  link ID and never performs scientific-name rematching or numeric-backbone translation.
- Added authenticated normalized occurrence-summary and fixed-purpose raster tile endpoints. The
  backend constructs only allowlisted GBIF requests with bounded time and response sizes, validates
  zoom/coordinates and PNG content, forwards no browser headers or collection metadata, and exposes
  no arbitrary proxy URL. Counts and tiles stay live; no occurrence, viewport, tile, native-range,
  GeographicPlace, BotanicalProfile, or collection persistence and no migration were introduced.
- Added an explicit-load BotanicalIdentity occurrence panel and lazy-loaded direct Leaflet layer.
  Zoom-appropriate hexagons show record density with a qualitative GBIF-style legend and an exact
  independently queried eligible total. The desktop/mobile textual companion covers taxon, source,
  checklist, retrieval time, quality policy, privacy, uncertainty, sampling bias, non-native and
  non-abundance semantics, dataset-specific licensing, attribution, empty and provider-error states.
  MAP-001 collection provenance and GEOGRAPHY-002 operator-managed native ranges remain separate.
- Canonical `make feature-verify` passed after independent review: the 75-entry feature graph and workflow
  helper suites passed; Ruff, Prettier, ESLint, strict mypy (169 source files), and strict TypeScript
  passed; 299 backend unit tests passed at 90.76% coverage, 143 frontend tests passed, and 305
  PostgreSQL integration tests passed; generated API declarations had no drift; backend and frontend
  production images built successfully (the lazy occurrence-map chunk is 0.90 kB / 0.54 kB gzip);
  the migration cycle correctly reported that no Alembic revision was added, and the final whitespace
  check passed.

## 2026-09-12 — PROPAGATION-002 frontend loading test stabilized

- Diagnosed the first guided-sowing component test's deterministic failure as an invalid test-timing
  assumption. Its in-memory session, CSRF, SeedLot, Location, and health mocks all resolved and the
  production workflow had no missing request or state race, but the test delegated the complete
  multi-effect React bootstrap to Testing Library's one-second polling deadline. On slower runs that
  deadline expired while the correct `Loading guided sowing…` state was still rendered.
- Kept the production UI and PROPAGATION-002 semantics unchanged. The affected test now explicitly
  flushes the immediate mocked request/update lifecycle inside an asynchronous React `act` boundary,
  then asserts the ready heading synchronously. No sleep, retry, timeout increase, weakened
  assertion, suite serialization, mock bypass, or global test-setting change was introduced.
- The exact affected test passed 10 consecutive fresh-process runs, and the complete 14-test
  PROPAGATION-002 file passed five consecutive runs (70 test executions) with normal timeouts. The
  complete 134-test frontend suite, Prettier, ESLint, strict TypeScript, the production Vite build,
  generated API drift, and diff whitespace checks pass.

## 2026-09-10 — contextual reference-picker race fixed

- Diagnosed the intermittent SeedLot contextual-creator failures as a stale delayed blur callback in
  the shared reference picker. Moving from the initially focused identity picker to the lot label
  scheduled a menu close; quickly returning to the picker reopened it, but the old callback could
  then close it again before the contextual-create action. CI's failed DOM captured that exact
  closed-combobox state.
- Replaced the input timer with focus-within handling at the picker boundary. The menu now closes
  synchronously only when focus leaves the complete picker, so pointer actions remain available and
  keyboard focus can move into its controls without an unowned timer. Added fake-timer regressions
  that deterministically reproduce blur and immediate refocus and protect internal focus movement.
- The stale-callback regression failed against the original implementation and all four focused
  picker regressions pass with the fix. A fresh container passed three consecutive complete SeedLot
  test-file runs (42 executions), including both affected contextual workflows on every run. The
  exact final code passes frontend Prettier, ESLint, strict TypeScript, the production Vite build,
  generated API drift, all 75 feature-graph entries, and diff whitespace checks.
- The unrelated `PROPAGATION-002` readiness-test timing assumption was subsequently corrected on
  `main` in `2caef9f`; it no longer blocks final verification of this focused picker change.

## 2026-09-10 — repository consistency and delivery reliability implemented

- Reconciled the public current-state summary and architecture overview with the verified Events,
  propagation lineage and reversal, geographic provenance, collection map, structured native-range,
  and external botanical-reference surfaces. Attachments/photos, richer germination and Event data,
  advanced search/analytics, import/export, contextual help, and PWA installability remain explicit
  deferrals; the V1 sequence and domain contracts are unchanged.
- Recorded the open-source-readiness follow-up already present on `main`: commit `a9c4391` adopted
  AGPL-3.0-or-later across the root license and package metadata, removed React Leaflet and its core
  package from the frontend manifest and lockfile, and retained Leaflet 1.9.4 directly for MAP-001.
  This pass reconfirmed those manifests, the lockfile, direct dependency tree, and direct Leaflet map
  implementation without adding dependency-audit infrastructure or changing runtime behavior.
- Corrected the delivery rerun gap after protected squash merge. Once `origin/main` advances, the
  reviewed feature SHA is no longer its ancestor; delivery now checks that SHA's associated
  same-repository PR before pushing and accepts the terminal state only when the exact branch/SHA was
  merged into `main`, every required current-SHA check passed, the reported merge SHA is on fetched
  `origin/main`, and the remote feature branch is deleted. Closed-unmerged, mismatched, ambiguous,
  missing-check, and unproven-divergence states remain blocked.
- Added deterministic no-network regression coverage for the merged-and-deleted rerun and retained
  exact-SHA failure cases. All 34 delivery/workflow helper tests pass. The complete SeedLot component
  file also passed nine consecutive focused runs (126 test executions); the reported contextual
  `Create identity` CI flake was not reproduced, its existing route/storage/dialog isolation remains
  sound, and no frontend code was changed.

## 2026-09-09 — GEOGRAPHY-002 implemented

- Added exact, many-valued BotanicalProfile native-range relationships to the shared
  GeographicPlace hierarchy. Broad and precise places can coexist without inferred ancestor or
  descendant links, and reparenting a custom place changes its derived display path without changing
  the stable relationship.
- Generalized the BotanicalProfile lifecycle: a profile exists while it owns any populated text
  section or structured native range. Adding the first range creates the profile atomically; clearing
  final text preserves range-only profiles; removing the final range deletes the profile only when
  no other meaningful profile-owned data remains. A deferred database constraint prevents persistent
  completely empty profiles.
- Added protected focused list/add/remove APIs, generated contracts, responsive identity-detail
  controls with path-disambiguated choices and accessible mutation feedback, and Geography usage
  visibility/deletion guards. Material provenance, ProvenanceSites, collection Locations, Suppliers,
  BotanicalIdentity fields, GBIF linking, and occurrence/distribution maps remain separate.
- Verification passed Ruff and Prettier formatting, Ruff and ESLint linting, strict mypy over 169
  source files, strict TypeScript, 286 backend unit tests at 90.78% coverage, 134 frontend tests, and
  304 disposable PostgreSQL integration tests. Revision `20260909_0022` was exercised through
  upgrade, populated-data downgrade refusal, cleanup, downgrade to `20260909_0021`, re-upgrade,
  deferred empty-profile rejection, and concurrent duplicate-add convergence. Generated API drift,
  both production image builds, all 75 feature-graph entries, and diff whitespace checks pass.
  `GEOGRAPHY-002` is implemented pending independent review.

## 2026-09-09 — BOTANY-002 verified

- Added the canonical BOTANY-002 external-data foundation and aligned separate planned
  GEOGRAPHY-002 native ranges, BOTANY-003 profile enrichment, MAP-002 botanical distribution,
  existing ATTACHMENT-002/003 photo work, later UX stabilization/help, and prose-only release
  hardening. V1 now denotes product scope while `0.1.0` is the intended first distributable release.
- Added a narrow backend-only GBIF adapter using the documented v2 matching service and Catalogue of
  Life eXtended Release checklist selection. Bounded requests normalize names, authorship, rank,
  status, accepted-name context, classification, match diagnostics, and alternatives while
  translating network, rate-limit, not-found, server, and malformed-response failures.
- Added one explicit current provider link per BotanicalIdentity/provider and a deterministic
  PostgreSQL JSONB response cache with a configurable one-day default freshness period. Link,
  replacement, stale-preserving refresh, and unlink operations never modify Florabase identity or
  profile facts; cache entries remain independent of links.
- Added protected focused APIs and a responsive BotanicalIdentity panel for editable search,
  ambiguous candidates, explicit confirmation, linked provenance, trusted GBIF navigation,
  refresh/failure freshness, replacement, and unlinking. The UI discloses that only botanical search
  terms leave Florabase and keeps enrichment, native ranges, occurrences, and MAP-001 out of scope.
- Independent verification passed 281 backend unit tests at 90.59% coverage, 132 frontend tests,
  298 disposable PostgreSQL integration tests, Ruff and Prettier formatting, Ruff and ESLint
  linting, strict mypy over 167 source files, strict TypeScript, and the migration cycle
  `20260908_0020 → 20260909_0021 → 20260908_0020 → 20260909_0021`, including populated-data
  downgrade refusal and concurrent link/cache convergence. Generated API drift, backend and
  frontend production image builds, validation of all 75 feature-graph entries, and final diff
  hygiene also pass. Canonical `make feature-verify` passed, including workflow helper coverage,
  production builds, the disposable migration cycle, and final whitespace and working-tree checks.

## 2026-09-09 — isolated stable-preview workflow implemented

- Added an operator-only stable-preview lifecycle around a detached adjacent Git worktree, with
  `origin/main` as the fetched default and an explicit-ref override. Existing clean previews move
  through safe detached switches; dirty previews and malformed worktree registrations fail closed,
  while targeted Git worktree repair covers a safely moved linked checkout without changing the
  primary branch, HEAD, index, or files; concurrent primary edits do not block preview preparation.
- Added a production-runtime Compose override and guarded orchestration for the explicit
  `florabase-preview` project. Rendered configuration validation pins build contexts to the preview
  worktree, publishes only `127.0.0.1:15173`, uses the matching loopback development origin/cookie
  policy, and requires isolated `florabase-preview_internal` and
  `florabase-preview_postgres_data` resources.
- Added explicit forward-only preview migration handling, interactive reuse of the existing owner
  bootstrap CLI, guarded development-to-preview custom-format dump/restore, bounded readiness,
  concise status, and stop/remove behavior that never deletes the preview volume. Development is
  hard-coded as import source and preflighted for migration compatibility before preview data is
  replaced; ordinary preview startup never imports data or runs a downgrade.
- Added 17 no-network workflow tests covering Git safety, fetched detached explicit-ref selection,
  invalid-ref and dirty-preview refusal, Compose paths/projects/resources/ports/configuration,
  persistent stop/remove semantics, preview-only migration/bootstrap targeting, guarded import
  direction and revision checks, readiness failures, status output, and unchanged disposable
  integration isolation. The new Python
  helpers pass Ruff formatting and lint; existing workflow and delivery helper suites, the 72-entry
  feature graph, Python compilation, and `git diff --check` pass.
- Real Docker verification created the clean sibling preview at
  `073ebf97c88e3a876280cfebfc23980b1048e4d2`, built from `origin/main`, migrated its new isolated
  volume to `20260908_0020`, reached both health endpoints through `http://localhost:15173`, and
  created an owner through the interactive preview bootstrap. Repeated startup was idempotent;
  stop and remove each preserved the volume; recreating the worktree retained both schema and owner;
  status accurately reported all three healthy services, exact SHA/ref, URL, volume, and revision.
  The exact temporary bootstrap test owner was removed afterward, leaving the running preview ready
  for the operator to create their own credentials.
  The persistent development stack was not running, so a real data import was deliberately not
  attempted. No product feature entry or Alembic revision was added for this developer workflow.

## 2026-09-09 — MAP-001 implemented

- Added the first-class authenticated collection provenance map using one Leaflet marker per
  coordinate-bearing ProvenanceSite. The initial viewport fits the available sites; accuracy is
  shown as an optional metre-radius circle, and explicit no-site, no-coordinate, and filter-empty
  states avoid inventing positions from broader geography or any other record.
- Added a deterministic bulk API projection for directly associated SeedLots, Plants, and
  PlantGroups with BotanicalIdentity and lifecycle context. Historical records remain visible,
  while Sowing-derived and PlantGroup-extracted descendants are deliberately excluded rather than
  inheriting an ancestor's provenance.
- Added record-type and BotanicalIdentity filtering with marker counts derived from the visible
  records, synchronized marker/list/detail selection, keyboard-operable companion navigation, and
  links to each collection record, BotanicalIdentity, and ProvenanceSite management route. The
  responsive layout preserves those non-map representations on narrow screens.
- Added pinned Leaflet 1.9.4, React Leaflet 5.0.0, and Leaflet type declarations. Operators can
  replace the OpenStreetMap-compatible tile URL and required attribution through an uncached runtime
  configuration asset; documentation calls out third-party tile-request privacy and self-hosting.
  The browser sends no Florabase record metadata, and no geocoding, geolocation, analytics,
  backend tile proxy, PostGIS, native-range data, or database migration was introduced.
- Implementation verification passed 265 backend unit tests at 90.45% coverage, 129 frontend tests,
  294 disposable PostgreSQL integration tests, Ruff and Prettier formatting, Ruff and ESLint
  linting, strict mypy over 156 source files, strict TypeScript, generated API drift, production
  backend and frontend image builds, validation of all 72 feature-graph entries, and
  `git diff --check`. The production frontend build retains Vite's non-failing warning for a
  roughly 601 kB main chunk. Canonical `make feature-verify` remains reserved for independent
  review.

## 2026-09-08 — SUPPLIER-002 verified

- Promoted Supplier from CRUD reference data to a focused detail hub while preserving its precise
  meaning: the direct acquisition source for a SeedLot, directly acquired Plant, or directly
  acquired PlantGroup. Sowing-derived and extracted descendants are not attributed to an ancestor's
  Supplier; GeographicPlace, ProvenanceSite, and physical collection Location remain independent.
- Added one-query Supplier-directory summaries and a focused detail projection with direct
  active/total counts, BotanicalIdentity-aware linked records, and deterministic recent acquisitions.
  SeedLots use their acquisition date, while directly acquired Plants and PlantGroups use their
  collection-entry date; unknown dates remain visible on linked records but are not presented as
  recent activity.
- Added responsive Overview and Linked material sections, useful empty states, direct navigation
  between Supplier and collection-record details, identity links, and historical lifecycle labels.
  Existing optional metadata and retirement/reactivation remain unchanged; retirement preserves all
  retained references, and no delete, order, purchase, price, or financial-analytics model was added.
- Focused implementation verification passed 263 backend unit tests at 90.41% coverage, 124 frontend
  tests, 293 disposable PostgreSQL integration tests, Ruff and Prettier formatting, Ruff and ESLint
  linting, strict mypy over 156 source files, strict TypeScript, generated API drift, production
  image builds, validation of all 71 feature-graph entries, and `git diff --check`. Alembic remains at
  `20260908_0020`; the feature required no schema change. Independent canonical verification is
  recorded with the reviewed feature branch.

## 2026-09-08 — GEOGRAPHY-003 implemented

- Superseded the stale evaluation-only planning contract and removed planned GEOGRAPHY-002 as a
  prerequisite. GEOGRAPHY-003 now depends on verified GEOGRAPHY-001 and UX-001; GEOGRAPHY-002
  remains planned for separate structured botanical native distribution.
- Preserved the immutable canonical World-rooted CLDR hierarchy and extended editable custom
  descendants with descriptive city/town, locality, and other named-area types. Added collapsed
  browsing, derived paths, bulk usage summaries, safe leaf deletion, and existing locked cycle-safe
  reparenting without inferred parents or a bundled city catalogue.
- Added relational ProvenanceSite records with optional GeographicPlace, coherent optional WGS84
  coordinates, optional non-negative metre accuracy, notes, timestamps, focused CRUD, usage-aware
  deletion, and reference support for SeedLots and directly entered Plants/PlantGroups. Location,
  Supplier, and planned botanical native distribution remain separate.
- Added an accessible responsive ProvenanceSite manager and path-aware selectors. The API exposes
  labels, coordinates, parent place paths, and supported collection usage for future MAP-001 without
  adding a map, geocoding, external requests, or botanical occurrence data.
- Focused verification passed 262 backend unit tests at 90.27% coverage, 123 frontend tests, 292
  disposable PostgreSQL integration tests, Ruff and Prettier formatting, Ruff and ESLint linting,
  strict mypy over 156 source files, strict TypeScript, generated API drift, feature-graph
  validation, and `git diff --check`. The disposable migration coverage exercises
  `20260907_0019 → 20260908_0020 → 20260907_0019 → 20260908_0020` and explicit downgrade refusal
  when ProvenanceSite data would be lost. Canonical `make feature-verify` remains reserved for
  independent review.

## 2026-09-07 — LOCATION-002 implemented

- Corrected the feature graph so global `UX-003` stabilization follows, rather than blocks, the
  remaining V1 feature surfaces. `LOCATION-002` now retains only its verified Location and UX
  foundations; the same stale prerequisite was removed from later `SUPPLIER-002`. `UX-003` remains
  planned and untouched.
- Added explicit Plants, Sowings, and Seed Lots scopes to the one shared hierarchical Location
  model, including safe migration defaults, API validation, backend-enforced assignments and moves,
  scope-aware selectors, and current-path preservation.
- Added an accessible collapsed-by-default Location tree with scope badges, usage summaries and
  directory links, child creation, reparenting, retirement/reactivation, and guarded leaf deletion.
  Active counts exclude historical records while totals retain them; used scopes cannot be removed,
  and referenced or parent Locations cannot be deleted.
- Implementation verification passed Ruff and formatting checks, ESLint, strict mypy over 148 source
  files, strict TypeScript, 251 backend unit tests at 90.13% coverage, 121 frontend tests, 282
  disposable PostgreSQL integration tests, generated API drift, feature-graph validation, and
  `git diff --check`. Canonical `make feature-verify` was intentionally not run; `LOCATION-002`
  remains implemented pending independent review.

## 2026-09-07 — PROPAGATION-003 verified

- Added receipt-proven reversal for SeedLot-to-Sowing, Sowing-to-Plant, and
  Sowing-to-PlantGroup. New forward operations atomically capture a versioned typed result
  expected-after snapshot with the receipt; historical receipts remain unchanged and report
  `legacy_receipt_missing_result_snapshot` instead of reconstructing past state from current data.
- Reversal restores the source's immutable BEFORE lifecycle and quantity representation without
  inverse arithmetic, marks the created result `reversed`, retains lineage and informational
  history, and marks only the receipt status reversed. Deterministic eligibility covers safe,
  retained-observation confirmation, structural correction, downstream-first ordering, transfer,
  extraction/reintegration, produced SeedLots, and other active-operation blockers.
- Added purpose-specific authenticated eligibility and CSRF-protected mutation APIs, plus responsive
  detail-page actions, typed blocker links, confirmation, authoritative refresh, historical badges,
  active-filter exclusions, and forward-workflow guards for reversed records.
- Independent review confirmed snapshot completeness and immutability, source restoration from the
  receipt BEFORE state, expected-result guards, downstream-first and cross-operation dependencies,
  global lock ordering, and the safe upgrade and guarded downgrade of Alembic revision
  `20260907_0018`. It corrected the historical-lifecycle validation message and made reversal
  eligibility refresh after Event creation, editing, or deletion so retained-history confirmation
  never presents stale same-screen state.
- Verification passed Ruff, strict mypy over 148 source files, 248 backend unit tests at 90.49%
  coverage, 278 disposable PostgreSQL integration tests, generated API drift, ESLint, strict
  TypeScript, all 119 frontend tests, and `git diff --check`. Manual QA in a disposable migrated
  stack covered safe, confirmation-required, and blocked reversal; retained observations; linked
  source, result, and dependent navigation; distinct repeated creation; active/history filters;
  accessible status and controls; and responsive behavior at desktop and 390×844.

## 2026-09-06 — PLANT-006 delivery CI follow-up

- Investigated a reported contextual SeedLot-creation test failure across isolated, in-file, and
  Plant-before-SeedLot runs. The route-hash changes did not leak state; the affected test had an
  ambiguous asynchronous modal lookup and did not reset browser storage during its own lifecycle.
  It now identifies each intended contextual dialog by accessible name and resets hash plus browser
  storage before and after every SeedLot screen test, while retaining the entered seed-lot details
  assertion after duplicate identity and failed supplier creation.

## 2026-09-06 — PLANT-006 verified

- Independent review confirmed the receipt-snapshot restoration, dependency guards, migration safety,
  and desktop/mobile reintegration workflow. It corrected two ordinary defects: operation-owned
  extraction and reintegration Events can no longer be edited through the ordinary Event API or UI,
  and successful extraction/reintegration now updates the Plant route hash to the authoritative
  target.
- Canonical `make feature-verify` passed: feature graph and workflow helpers; quality checks
  (including 209 backend tests at 90.05% coverage and 111 frontend tests); 247 disposable
  PostgreSQL integration tests; production builds; the `20260905_0016 → 0017 → 0016 → 0017`
  migration cycle; whitespace validation; and the local verification receipt.

## 2026-09-05 — PLANT-006 implemented

- Added receipt-proven reintegration of an extracted Plant into only its original PlantGroup. The
  locked atomic operation restores the immutable before-snapshot without inverse arithmetic, marks
  the Plant `reintegrated`, retains its lineage and Events, records one group-targeted reintegration
  Event, preserves the extraction Event, and changes only the receipt status to reversed.
- Added focused eligibility and mutation APIs with safe, confirmation-required retained-observation,
  and typed blocked outcomes. Guards cover receipt/result mismatch, lifecycle and structural Plant
  changes, transfer or other active receipts, produced SeedLots and downstream lineage, later group
  operations, group lifecycle/quantity correction, already-reversed receipts, and missing historical
  receipts. Concurrent mutation serializes on the receipt and affected rows.
- Added the responsive Plant and Event-journal experience: original-group context, retained-history
  confirmation, actionable blocker explanations, authoritative post-success refresh, Reintegrated
  historical state, lifecycle summaries, linked reintegration history, and operation-owned
  extraction actions that no longer resemble ordinary Event deletion.
- Added Alembic revision `20260905_0017`, generated API declarations, focused backend/frontend and
  PostgreSQL coverage including migration cycle, snapshot variants, history, blockers, rollback,
  repeat use, and concurrent requests. Implementation checks passed: Ruff and ESLint; strict mypy
  over 141 source files and strict TypeScript; 209 backend unit tests at 90.08% coverage; 111
  frontend tests; generated API drift; 247 disposable PostgreSQL integration tests; and
  `git diff --check`. Final canonical `make feature-verify` is intentionally left to the independent
  reviewer; `PROPAGATION-003` remains unimplemented.

## 2026-09-05 — CI-002 auto-merge delivery fix

- Corrected `make feature-deliver` to recognize GitHub REST's `closed` plus `merged: true` response
  after successful squash auto-merge, retain the resulting merge SHA, and continue blocking closed
  unmerged pull requests. Focused no-network coverage includes open polling, both closed outcomes,
  an auto-merge between polling reads, and resulting main-SHA reporting. Workflow tests, helper
  compilation, and `git diff --check` passed.

## 2026-09-05 — CI-002 verified

- Added `make feature-verify` as the final local feature gate. It validates the feature graph and
  repository workflow helpers, runs the quality, disposable PostgreSQL integration, and production
  build gates exactly once, checks both staged and unstaged whitespace errors, and stores an ignored
  local tree receipt rather than changing application files or requiring a clean working tree.
- Added conditional Alembic detection against the `origin/main` merge base. A branch with revision
  files receives `previous main head → feature head → previous main head → feature head` in a uniquely
  named Compose project backed by tmpfs PostgreSQL; non-migration branches skip that extra cycle.
- Added fail-closed `make feature-deliver`: it requires a clean reviewed commit and expected Florabase
  origin, refuses unsafe branch/history states, verifies the receipt, makes only a normal push, reuses
  one open PR or creates one deterministic PR, enables exact-SHA squash auto-merge, polls current-SHA
  `quality`, `integration`, and `build` checks with bounded startup/completion waits, and confirms the
  merge and remote-head deletion. Failed terminal checks leave the branch and PR untouched with
  `DELIVERY_BLOCKED`; a migration is reported only as a later `make dev-upgrade` reminder after
  `make feature-finish`.
- Focused no-network helper tests exercise verification success/failure and migration paths, clean
  delivery preconditions, normal non-force push, PR creation/reuse, exact SHA auto-merge/checks,
  action registration delay, failure/cancel/timeout handling, and remote-branch deletion. Canonical
  `make feature-verify`, `make check`, `make ci`, and `git diff --check` passed; delivery was not run
  against GitHub.
- The first real delivery created PR #19 but then rejected GitHub REST's lowercase `open` state.
  Delivery now normalizes REST state on parsing and validates the returned open PR's head branch,
  base branch, and exact delivery SHA for both reuse and creation. Regression fixtures cover lowercase
  and mixed-case state, historical closed/merged entries, mismatched branch/base data, and follow-up
  reuse without a duplicate PR.
- A second real delivery confirmed GitHub's normal post-push REST propagation window: PR #19 initially
  returned its prior head SHA before later reflecting the pushed SHA and registering new-SHA checks.
  Delivery now validates the open PR target immediately, then waits at a bounded two-second/sixty-second
  cadence only for a prior same-lineage head to advance to the delivery SHA. It rejects mismatched
  branch, base, state, or unrelated SHA without waiting, and begins the separate current-SHA check
  registration wait only after the PR head matches. No-network regression coverage includes delayed,
  immediate, timeout, wrong-target, no-duplicate, and check-sequencing paths.

## 2026-09-05 — REVERSAL-001 verified

- Added one closed relational `operation_receipts` representation for the six supported forward
  operation kinds. Explicit source/result/Event foreign keys and per-kind database checks replace a
  generic JSON payload; UUIDv7 identity, UTC creation time, applied/reversed status, adjustment mode,
  lifecycle, and exact/approximate/unknown quantity state are retained.
- Wired receipt creation into the existing locked SeedLot-to-Sowing, Sowing-to-Plant,
  Sowing-to-PlantGroup, PlantGroup extraction, Plant transfer, and PlantGroup transfer transactions.
  Exact and unit-bearing values are copied directly, estimates retain both recorded values, unknown
  remains all-null, group extraction records actual stored before/after state, and later aggregate
  correction does not rewrite the receipt.
- Added a unique operation-owned Event relationship for extraction and transfer. Ordinary Events
  retain non-replay edit/delete behavior; ordinary deletion of an operation-owned Event is rejected
  until a future purpose-specific undo exists. No historical receipts are fabricated, no receipt
  CRUD API is exposed, and no undo, reintegration, reverse mutation, or UI was added.
- Added migration `20260905_0016`, immutable-original-facts enforcement with a separately mutable
  future status, kind/payload constraints, focused unit/integration coverage, rollback injection,
  losing-concurrency receipt counts, and the disposable downgrade/re-upgrade cycle.
- Verification passed: canonical `make check` and `make ci`; workflow-helper checks; backend and
  frontend formatting, lint, strict typing, unit and frontend suites; API/generated-contract drift;
  all 238 disposable PostgreSQL integration tests including concurrency coverage; production backend
  and frontend builds; and `git diff --check`. The migration cycle passed after widening the stored
  transfer predecessor lifecycle constraint so the receipt schema never assumes that the captured
  prior lifecycle is always `active`.

## 2026-09-05 — reversible domain-operation planning refinement

- Audited the verified forward operations without changing application behavior. Exact SeedLot
  partial use and exact PlantGroup extraction have reversible numerical invariants (`100 → 80 → 100`
  and `10 → 9 → 10`); approximate values must restore their recorded estimate rather than use
  inverse arithmetic, unknown remains unknown, and quantity dimensions/units cannot be crossed.
- Recorded the current gap: forward transactions and extraction-result links exist, but no persisted
  operation identity, adjustment mode, before-state snapshot, complete created-record set, or prior
  transfer lifecycle exists. Current persistence is therefore insufficient for generally reliable
  undo despite the deliberate non-replay Event contract.
- Added planned `REVERSAL-001` for a narrow immutable authoritative-operation receipt,
  `PLANT-006` for recorded extracted-Plant reinsertion, and `PROPAGATION-003` for guarded
  propagation reversal. The plan keeps ordinary Event deletion separate from validated Undo action,
  records deterministic dependency blocks, and preserves history rather than assuming destructive
  cleanup. These increments are sequenced before later Location/geography selection, without adding
  artificial Location or geography feature dependencies.

## 2026-09-05 — PLANT-005 verified

- Added an explicit `transferred` lifecycle for Plant and PlantGroup plus owner-authorized,
  CSRF-protected transfer operations. Each operation locks the active target and atomically creates
  a transfer Event with an optional precision-preserved date, free-text recipient, and notes; the
  target remains editable as historical correction data, while later Event edits or deletion never
  replay lifecycle effects.
- Whole-group transfer preserves the stored group quantity and offers no partial quantity control.
  The existing extraction operation is now the required partial-transfer path: it atomically creates
  the resulting Plant, updates only an exact source count when applicable, and records a cultivation
  extraction Event on the source group with a navigable resulting-Plant relationship. Generic Event
  creation cannot manufacture extraction Events.
- Updated the responsive Plants experience with explicit bilingual transfer actions, accessible
  dialogs, active/history filtering, historical styling, transfer and extraction Event rendering,
  corrected routed-result navigation, and active-versus-transferred BotanicalIdentity summaries.
  Dashboard active totals continue to count only lifecycle `active` records.
- Added Alembic revision `20260904_0015`, regenerated OpenAPI and TypeScript declarations, and
  documented lifecycle, Event categories, quantity, correction, and relationship semantics.
- Independent release review added a database-enforced source-group/result-Plant relation and
  matching service validation, preventing an extraction Event from being reassigned to a Plant from
  a different PlantGroup. It also corrected the integration migration-head expectation.
- Canonical verification passed: `make check` (Ruff, Prettier, ESLint, strict mypy over 134 source
  files, strict TypeScript, API drift, 203 backend tests at 90.02% coverage, and 110 frontend
  tests) and `make ci` (workflow helpers, the same checks, 235 fresh PostgreSQL integration and
  migration tests, and production image builds). Authenticated browser QA covered desktop
  individual transfer and extraction journals plus the 390 × 844 responsive PlantGroup Events view
  and mobile navigation. `PLANT-005` is `verified`.

## 2026-09-04 — PROPAGATION-002 verified

- Added contextual BotanicalIdentity actions for preselected SeedLot creation, explicit source
  SeedLot selection before Sowing, and explicit Sowing-versus-direct paths for Plants and PlantGroups.
  Successful guided creation opens the new record while preserving visible links to its source and
  identity context.
- Added a two-stage SeedLot-to-Sowing workflow over the verified atomic API. It previews exact
  subtraction, requires confirmation before mutation, keeps approximate remainders visibly editable,
  preserves unknown quantities, suppresses incompatible arithmetic, offers no adjustment and valid
  use-all choices, prevents duplicate submission, and retains entered data on API failure.
- Added Sowing source and descendant summaries, explicit Plant/PlantGroup actions, operator-selected
  resulting Sowing lifecycle defaulting to active, deliberate completion summaries, and derived
  exact non-germinated counts only when the exact seed-count denominator permits them. Completed
  Sowings remain available under Completed and All; failed and abandoned records remain under All.
- Added a responsive, textual, clickable propagation-path component for stored lineage on Sowing and
  propagated Plant/PlantGroup overviews. Identity aggregation is still labeled as non-lineage;
  direct creation, retroactive entry, correction, and no-replay semantics remain unchanged. No
  backend, schema, migration, OpenAPI, or generated declaration change was needed.
- Focused verification: baseline 93 frontend tests passed before changes; Prettier and ESLint passed
  across the frontend; strict TypeScript passed; and 63 focused frontend tests passed across the new
  PROPAGATION-002 coverage and the affected identity, SeedLot, Sowing, and Plant screens. Generated
  API drift and `git diff --check` passed. An isolated migrated Compose stack verified contextual
  identity-to-SeedLot entry, exact SeedLot subtraction, atomic Sowing and Plant creation, returned
  record navigation, stored propagation links and summaries, and the compact responsive layout in a
  real browser. A one-shot full frontend run reached 96/98 before two existing SeedLot tests hit the
  15-second limit under host contention; the complete SeedLot file then passed 14/14 in isolation and
  again within the 63-test focused regression run.
- Independent verification passed `make check` and `make ci`: workflow-helper checks;
  backend/frontend formatting, lint, and strict type checks; 192 backend unit tests at 90.20%
  coverage; 108 frontend tests; API declaration drift; 229 disposable PostgreSQL integration tests;
  and production image builds. Browser QA at desktop and 390 × 844 verified the responsive,
  authenticated BotanicalIdentity → SeedLot → Sowing → Plant workflow, exact partial-use preview,
  explicit Sowing completion, source and descendant summaries, and clickable stored-lineage links.

## 2026-09-04 — PROPAGATION-001 verified

- Added explicit atomic SeedLot-to-Sowing and Sowing-to-Plant/PlantGroup backend operations while
  preserving every ordinary create and correction path. Exact compatible source quantities are
  locked and subtracted without allowing a negative remainder; approximate partial use requires an
  explicitly confirmed editable approximate remainder; unknown partial use remains unknown; and
  explicit use-all exhausts the source without manufacturing exact zero for approximate or unknown
  material.
- Added explicit post-transition Sowing lifecycle selection and a strongly typed propagation
  summary derived only from stored Sowing lineage. Each Plant contributes one exact tracked
  individual, exact PlantGroup counts contribute their quantities, and approximate or unknown
  groups remain separately visible without becoming exact counts. Germination observations are not
  rewritten, Sowing completion is never inferred, later edits do not replay transition effects, and
  no propagation log, redundant counter, automatic Event, frontend workflow, or migration was
  introduced.
- Independent review found the transition contract, explicit uncertainty handling, locking,
  correction boundaries, derived summary, and deferred Event/UI boundaries aligned with the
  acceptance criteria. Canonical `make ci` passed: workflow-helper tests; backend/frontend format,
  lint, and strict type checks; 192 backend unit tests at 90.20% coverage; 93 frontend tests; API
  generation drift check; 229 isolated PostgreSQL integration tests; and production image builds.
  The OpenAPI and TypeScript declarations are regenerated and current. No migration was needed.

## 2026-09-03 — post-UX-001 UAT roadmap refinement

- Recorded the intended collection lifecycle narrative from BotanicalIdentity through SeedLot,
  Sowing, Plant/PlantGroup, and Events or terminal state while preserving the distinction between
  identity aggregation, explicit lineage, quantities, and lifecycle state.
- Added planned `PROPAGATION-001` and `PROPAGATION-002` increments so quantity accounting,
  total/partial-use choices, source lifecycle decisions, contextual creation entry points, and
  cross-linking are decided and delivered in that order. `PROPAGATION-001` is the recommended next
  increment; no application behavior is included in this planning pass.
- Added later planned increments for transferred/ceded Plant lifecycle (`PLANT-005`), observed-use
  navigation refinement (`UX-003`), scope-aware hierarchical Location browsing (`LOCATION-002`),
  deliberately scoped finer-grained geography (`GEOGRAPHY-003`), and connected Supplier summaries
  (`SUPPLIER-002`). PlantGroup transfer remains an evaluation, global city reference data is not a
  first-release requirement, and Supplier financial totals remain gated by `ORDER-001`.
- Preserved every existing verified status and acceptance criterion. Validation parsed all 67
  feature records; checked required fields, allowed statuses and priorities, unique IDs, dependency
  references, self-dependencies, DAG cycles, and verified prerequisites; structurally compared all
  35 pre-existing verified records with `origin/main`; checked changed files with Prettier; and ran
  `git diff --check`.

## 2026-09-03 — UX-001

- Reframed Florabase around a collection Dashboard; persistent grouped desktop navigation; a fixed
  five-destination mobile bar with a secondary More tray; unified Plants browsing for distinct Plant
  and PlantGroup records; and a complete global Events journal. The focused Dashboard endpoint
  supplies authoritative collection counts and six recent Events, while the global endpoint keeps
  EVENT-001 ordering and EVENT-002's All, Observations, Cultivation, and Status vocabulary.
- Added shared breadcrumb, detail-header, accessible routed-tab, card, Event-feed, and explicit
  lineage primitives across Plant, PlantGroup, SeedLot, Sowing, and BotanicalIdentity details.
  BotanicalIdentity is now an identity-based collection hub with Overview, Seeds, Sowings, combined
  Plants and Plant groups, and Events tabs; textual record types, concrete cross-links, and explicit
  copy keep identity aggregation separate from recorded lineage.
- Completed the editability audit: Plant, PlantGroup, SeedLot, and Sowing retain their lifecycle-aware
  editors; Location, Supplier, and user-created GeographicPlace now share visible Edit and overflow
  action placement; canonical geography remains immutable. BotanicalIdentity gained focused update
  and guarded deletion: unused identities can be removed, while SeedLot, Plant, or PlantGroup
  references produce a clear conflict and never cascade. Contextual form guidance remains UX-002.
- Verification passed formatting, Ruff, ESLint, strict mypy, strict TypeScript, 176 backend unit
  tests, 93 frontend tests, all 224 disposable PostgreSQL integration tests, generated API drift,
  workflow-helper checks, production backend/frontend builds, and `git diff --check` through the
  canonical `make ci` path. Browser QA on an isolated tmpfs PostgreSQL stack covered every required
  detail, dashboard, global Events, menu, desktop sidebar, and 390×844 bottom-navigation flow with no
  console errors or horizontal page overflow. No migration was required and no operator database or
  persistent volume was modified. `UX-001` is verified.

## 2026-09-02 — EVENT-002

- Added one protected Event journal to both Plant and PlantGroup detail pages. The complete
  EVENT-001 vocabulary has human-readable labels; API order and unknown, year, month, or complete
  occurrence-date precision remain faithful. Desktop uses a vertical chronological timeline, while
  narrow screens use compact wrapping cards with touch-sized actions and no horizontal scrolling.
- Added predictable All, Observations, Cultivation, and Status filters plus useful loading, error,
  retry, empty, and mutation states. The accessible create flow conditionally requires a movement
  destination and explains movement or lifecycle side effects. Every Event can be edited or deleted;
  both flows explain that historical correction/deletion neither replays nor rolls back current
  Location or lifecycle. Successful creation refetches both Event history and the authoritative
  Plant/PlantGroup state; update and deletion refresh history only.
- Component coverage now exercises Plant and PlantGroup journals, every kind and partial-date
  precision, deterministic ordering, all filters, desktop/mobile structure, empty/loading/error
  states, creation and validation, state-changing refresh, edit/delete semantics, mutation failure,
  warnings, and accessible labels/actions. Verification passed Prettier, ESLint, strict TypeScript,
  Ruff, strict mypy over 122 source files, 169 backend unit tests at 90.72% coverage, 89 frontend
  tests, generated API drift, workflow-helper tests, all 222 disposable PostgreSQL integration tests,
  and production backend/frontend image builds through `make ci`; `git diff --check` also passed.
- Browser QA against an isolated tmpfs PostgreSQL stack confirmed the desktop timeline and the
  responsive 390×844 card layout, including faithful dates, wrapping long notes, visible destination,
  44-pixel action targets, zero horizontal overflow, side-effect warnings, non-rollback dialogs, and
  authoritative Location refresh after movement. No migration or generated API change was needed,
  and no operator database or volume was modified.
- A collection-wide Event timeline remains deferred. `UX-001` now explicitly retains the future
  cross-application review of primary/mobile and detail navigation, tabs/sections, action placement,
  cross-domain hierarchy, visual/interaction coherence, and possible global Event activity. That UX
  work remains planned. `EVENT-002` is verified.

## 2026-09-02 — EVENT-001

- Added first-class UUIDv7 Events for exactly one Plant or PlantGroup, with the controlled initial
  vocabulary, optional precision-preserved occurrence date and notes, exact UTC audit timestamps,
  restrictive relational references, and deterministic target timeline ordering. Alembic revision
  `20260902_0014` enforces target, kind, partial-date, notes, and movement-destination invariants and
  adds target timeline indexes.
- Added authenticated target-aware list/create APIs and Event read/update/delete APIs. Creation
  locks the target and atomically applies movement Location or death/loss/discarded lifecycle
  effects. Event correction and hard deletion intentionally change history only and never replay or
  roll back current target state; ordinary Plant/PlantGroup edits still do not create Events.
- Verified with Ruff and Prettier formatting, Ruff and ESLint, strict mypy over 122 source files,
  strict TypeScript, 169 backend unit tests at 90.72% coverage, 84 frontend tests, generated OpenAPI
  and TypeScript drift checks, workflow-helper tests, production backend/frontend image builds, and
  all 222 disposable PostgreSQL integration tests. Integration coverage includes the
  upgrade/downgrade/re-upgrade cycle, restrictive constraints, authorization and CSRF/Origin,
  transactional rollback, and concurrent movement serialization. The canonical integration wrapper
  was not invoked because its `down --volumes` cleanup was rejected by the execution safety layer;
  the same Compose test service ran in a unique project with tmpfs PostgreSQL and no Docker volumes,
  followed by non-volume container/network cleanup.
- Structured Event payloads beyond movement destination, Event attachments, and the timeline UI
  remain deferred to later increments. `EVENT-001` is verified.

## 2026-09-02 — CI-001 repository automation implemented

- Added stable `quality`, `integration`, and `build` pull-request checks using the repository's
  existing verification, disposable PostgreSQL, and production Compose build paths. The workflow
  has read-only permissions, per-PR stale-run cancellation, explicit timeouts, and unconditional
  integration cleanup.
- Added isolated-tested `feature-start` and `feature-finish` helpers, explicit development database
  upgrade wiring, and `make ci`; centralized the squash auto-merge workflow in contributor guidance.
- Local verification passed Bash syntax checks; isolated workflow-helper tests; pinned Prettier over
  changed Markdown, JSON, and YAML; 209 PostgreSQL integration tests; production backend/frontend
  image builds; `git diff --check`; and a final `make check` (Ruff, ESLint, strict mypy over 112
  source files, strict TypeScript, 141 backend unit tests at 90.17% coverage, 84 frontend tests, and
  generated API drift). One earlier `make check` attempt hit a host load average of 9.49 and 14
  unchanged frontend tests exceeded their five-second timeout; the focused retry and final complete
  run passed without weakening the tests.
- GitHub-side verification is complete: implementation was squash-merged as `a746e4f`, Actions run
  `33605345339` passed `quality`, `integration`, and `build`, and the repository permits squash
  auto-merge while disabling merge commits and rebases. The active `Protect main` ruleset targets
  only `refs/heads/main`, requires pull requests plus strict `quality`, `integration`, and `build`
  checks, and protects against deletion and non-fast-forward updates. The first `make feature-finish`
  execution verified the merged PR, fast-forwarded local `main`, removed local `ci/ci-001`, and left
  the repository clean; automatic remote head-branch deletion was also confirmed after merge.
  `CI-001` is now `verified`.
- The first pull-request run exposed a GitHub checkout ownership difference: Vitest's default
  bundled config loader tried to write a timestamped module under `/app/node_modules/.vite-temp`
  while loading `vite.config.ts`. The frontend test script now uses Vitest's supported runner config
  loader, which evaluates the existing config without writing beside the read-only checkout and
  preserves non-root container execution. Once the frontend suite could complete, the same run
  revealed that API drift verification also regenerated tracked artifacts before comparing and
  restoring them. Both generators now use read-only check modes during verification; the explicit
  artifact-writing path remains `make api-generate`.

## 2026-09-02 — DOCS-001 repository audit

- Reconciled public and engineering documentation with the implemented application through
  `PLANT-004`; rewrote the README, architecture, domain model, roadmap, deployment/development guides,
  and this milestone log around current behavior.
- Added concise contributor and security policies plus a pull-request template. Audited configuration,
  backup/restore, package metadata, GitHub configuration, links, licensing, CI, screenshots, and
  release gaps without adding product behavior.
- Corrected `GEOGRAPHY-002` from `verified` to `planned`: GeographicPlace exists and is used for
  material provenance, but no BotanicalIdentity/Profile native-range relationship is implemented.
- Added planned `CI-001` because Dependabot exists but no GitHub Actions verification workflow does.
  License selection, private vulnerability reporting, screenshots, version/release policy, and the
  first changelog entry remain operator/release decisions.
- Verification passed: Prettier over all changed Markdown/JSON/YAML; JSON/schema, unique-ID,
  dependency-reference, self-dependency, DAG, verified-prerequisite, internal-link,
  `.env.example`/Compose-key, and single-Alembic-head checks; repository stale-state greps;
  `git diff --check`; full `make check` (Ruff, ESLint, strict mypy over 112 source files, strict
  TypeScript, 141 backend unit tests at 90.17% coverage, 84 frontend tests, and generated API drift);
  and all 209 disposable PostgreSQL 18.6 integration tests. `DOCS-001` is verified.

## 2026-09-02 — PLANT-004

- Alembic revision `20260901_0013` added restrictive PlantGroup origin for extracted Plants and
  preserved the mutually exclusive Sowing, direct, or group-origin modes.
- Added an owner-authorized, CSRF-protected atomic extraction operation. It creates one Plant,
  decrements exact group quantity, completes the final exact member, and leaves approximate/unknown
  quantities unchanged. The accessible Plants UI exposes the focused workflow and keeps extraction
  origin read-only during ordinary editing.
- Verified with Ruff, strict mypy, 141 backend unit tests, 209 PostgreSQL integration tests, Prettier,
  ESLint, strict TypeScript, 84 frontend tests, generated API drift, production image builds, and
  responsive browser checks. `PLANT-004` is verified.

## 2026-09-01 — LINEAGE-002

- Alembic revision `20260901_0012` added mutually exclusive Plant/PlantGroup producers for
  collection-produced SeedLots, with restrictive references and cycle validation.
- Added typed authenticated lineage routes for SeedLots, Sowings, Plants, and PlantGroups. A focused
  recursive PostgreSQL traversal follows only supported direct workflow relationships and retains
  inactive history.
- Verified with 139 backend unit tests, 192 PostgreSQL integration tests, 80 frontend tests, static
  checks, generated contracts, production builds, and `make check`. `LINEAGE-002` is verified.

## 2026-09-01 — PLANT-003

- Added the accessible responsive Plants navigation section for Plant and PlantGroup list, search,
  lifecycle/type filtering, detail, creation, and full editing.
- Verified with 80 frontend tests, 138 backend unit tests, 184 PostgreSQL integration tests, static
  checks, generated-contract drift, production builds, responsive browser checks, and `make check`.
  `PLANT-003` is verified.

## 2026-08-31 — PLANT-001 and PLANT-002

- Defined Plant as one specimen with no quantity and PlantGroup as one managed group of one botanical
  identity. Both support incomplete data, Sowing or direct origin, provenance, Location, lifecycle,
  and historical retention.
- Alembic revision `20260831_0011` and protected APIs implemented those contracts without mutating
  SeedLot or Sowing accounting. Migration, invariant, authorization, generated-contract, unit, and
  integration checks passed. Both features are verified.

## 2026-08-31 — SOWING-001 through SOWING-003

- Defined and implemented Sowings as managed attempts from exactly one SeedLot, with optional
  precision-preserved date, quantity, simple germinated total, Location, cultivation details, and
  retained lifecycle.
- Alembic revision `20260831_0010`, protected APIs, and the responsive Sowing UI were verified across
  database invariants, authorization, unit/integration/component tests, generated contracts,
  production builds, and browser layouts. The three Sowing features are verified; PWA installability
  remains planned.

## 2026-08-30 — SeedLot and geography

- `SEED-001` through `SEED-004` defined and delivered the SeedLot schema, protected API, and
  accessible inventory UI. Revisions `20260830_0008` and `20260830_0009` preserve partial dates,
  source/provenance distinctions, optional exact/approximate count or weight, safe zero/exhausted
  semantics, storage Location, and lifecycle without implicit Sowing deduction.
- `GEOGRAPHY-001` installed a reproducible 287-row Unicode CLDR 48.2.1-derived canonical
  GeographicPlace hierarchy and protected custom extensions. `GEOGRAPHY-002` native-range
  relationships were only planned and remain unimplemented.
- Supplier and collection Location vertical slices were delivered in revisions `0005` and `0006`.
  Their protected directories, lifecycle/hierarchy behavior, tests, and generated contracts are
  verified.

## 2026-08-28 to 2026-08-30 — authenticated reference application

- `DOMAIN-001`, `DATABASE-001`, and `BACKEND-001` established the BotanicalIdentity contract,
  revision `0002`, protected REST slice, deterministic directory, validation, and generated types.
- `SECURITY-001` accepted the backend-owned session design. `SECURITY-002` implemented revision
  `0003`, owner bootstrap, Argon2id login, opaque PostgreSQL sessions, secure/loopback cookie modes,
  Origin and CSRF checks, expiry/revocation, and throttling. `FRONTEND-002` delivered browser session
  restoration and logout.
- `FRONTEND-001`, `PROFILE-001`, `PROFILE-002`, and `IDENTITY-001` delivered the accessible botanical
  identity/profile workflows and revision `0004`. All are verified.

## 2026-08-27 to 2026-08-28 — repository foundation

- `FOUNDATION-001` established production-oriented and development Compose stacks, non-root runtime
  images, health/readiness, explicit Alembic migrations, typed FastAPI/React scaffolding, generated
  contracts, and quality tooling.
- `OPS-001` added guarded PostgreSQL custom-format backup/restore and an isolated restore drill.
  `TESTING-001` added disposable PostgreSQL integration testing. All three are verified.

## Current state

- Alembic head: `20261009_0040`; TAXONOMY-003 is independently verified and awaits protected delivery.
- Verified product boundary: local owner authentication; botanical identities/profiles; suppliers;
  collection locations; geographic places/material provenance; seed lots; sowings and simple
  germination totals; Plants/PlantGroups; explicit producer/Sowing/extraction lineage; and the
  protected Plant/PlantGroup Event journal and timeline UI; atomic extraction history; retained
  transferred Plant/PlantGroup history; scope-aware hierarchical collection Locations; direct,
  connected-record Supplier summaries; and exact structured BotanicalProfile native ranges over the
  shared GeographicPlace hierarchy; and guarded local still-image attachment storage with
  authenticated retrieval and coordinated database/content backup.
- `PROPAGATION-001` through `PROPAGATION-003`, `SUPPLIER-002`, `BOTANY-002`, and
  `ATTACHMENT-002` are verified. `LOCATION-002`, `GEOGRAPHY-003`, `MAP-001`, `GEOGRAPHY-002`,
  `ATTACHMENT-003`, `IMPORT-001`, `SEARCH-001`, and `UX-002` through `UX-006` are implemented in the
  graph; UX-004, UX-005, and UX-006 have landed on `main`, but their graph status has not been
  promoted to `verified`.
  `PERF-001` is verified on the frozen 0.1.0 scope. The agreed blocking cross-application UI polish
  is awaiting operator visual review before `RELEASE-001` hardening and acceptance; PERF-001's
  measurement report records the remaining costs and review caveats.
  Optional product candidates are not dependencies of either required increment. Licensing,
  version/upgrade policy, and release readiness remain to be resolved in `RELEASE-001`.
- `CI-001` repository automation is verified through the merged pull-request workflow and protected
  `main` checks.
  Other unblocked P2 product items are listed by the machine-readable dependency graph rather than
  prioritized here.
- Deliberately absent: arbitrary derivative pipelines beyond the fixed cached local 320px WebP,
  identity-cover history, automatic or
  provider image discovery, PWA behavior,
  offline/synchronization behavior, generic graphs, and multi-user collaboration.

## 2026-10-05 — PREVIEW-001 independent final verification

- `make feature-verify` passed on the complete reviewed tree: feature graph and workflow guards, Ruff,
  Prettier, strict mypy (256 application files), TypeScript, backend tests (600 passed, 90.01%
  coverage), frontend tests (375 passed across 41 files), API drift, PostgreSQL integration, production
  backend/frontend image builds, migration-cycle checks (no new Alembic revisions), whitespace and
  verification receipt.
- PREVIEW-001 is **verified** in `docs/features.json`; roadmap and handoff reflect operator UAT and
  independent verification complete. The receipt was recorded for this exact working tree.
- Commit, protected delivery, merge and conservative worktree finish remain the authorized next steps.

## 2026-10-09 — TAXONOMY-003 independent verification

- Independent product/source review accepted the collection-aware classification tree and its WFO
  2026-06 CC0 source contract. Browser review covered desktop, tablet and 390×844 mobile, keyboard
  navigation, filters, linked/unresolved identities and related classification peers; no fixture link
  was confirmed or changed. Broad cross-application visual review remains deferred.
- Canonical `make feature-verify` passed on the final reviewed tree: **895 backend tests, 90.03%
  coverage; 541 frontend tests across 56 files; 699 PostgreSQL integration tests; 329 strict-mypy
  files; API drift clean; production backend/frontend builds passed; migration cycle
  `0039 → 0040 → 0039 → 0040`; whitespace and worktree receipt passed.** Ruff, Prettier, ESLint,
  TypeScript, feature/workflow helpers and environment checks passed as part of the gate.
- TAXONOMY-003 is marked **verified** in `docs/features.json`. Source-index checksum and footprint,
  query counts, cold/warm measurements, UAT evidence and known host-load limits are documented in
  [the handoff](taxonomy-003-handoff.md). Protected delivery and DEV upgrade are the remaining
  lifecycle steps; migration 0040 requires the upgrade after merge.

## 2026-10-10 — CI-003 FULL migration-cycle repair (review handoff)

- Independently reproduced the dependency-only defect on exact base `d86c488`: FULL selected,
  migration command lacked `--force-cycle`, and the actual runner returned “no Alembic revisions
  added” without PostgreSQL. Initialized `fix/ci-003-full-migration-cycle` in the attached worktree;
  prior dependency-audit files remain preserved and are separate from this repair.
- Replaced the competing migration booleans with explicit `skip` / `affected-cycle` / `full-cycle`
  decisions. Every selected cycle uses the existing force mechanism. Automatic and explicit FULL
  execute identical exhaustive migration semantics; affected docs/frontend/domain skips remain safe.
- Corrected v2 receipts require four verified PostgreSQL revision states and successful exact
  disposable cleanup, distinguish required/executed/result from `skipped_by_impact`, and reject
  incomplete or historical v2 evidence through the existing delivery preflight validator.
- Focused selector/execution, fixture receipt/delivery, migration/resource and workflow helper checks
  pass, as do workflow Ruff formatting/lint and strict mypy, backend cycle-helper static checks,
  shell syntax, feature graph and whitespace checks. Real PostgreSQL smoke covers automatic and
  explicit FULL without migration differences, nontrivial synthetic downgrade/re-upgrade, and a
  broken existing migration chain with only a lockfile feature diff. All run-owned resources retire;
  separate real resource smoke proves volume cleanup and unchanged persistent resource identities.
- CI-003 remains `verified`; no new feature, product behavior, dependency baseline or remote CI change.
  Primary main remains clean at `d86c488`. No files staged, no commit/push/delivery; final canonical
  `make feature-verify` / `make verify-full` deliberately reserved for Luna. Dependency maintenance
  remains paused until this repair is delivered. See the
  [repair handoff](ci-003-full-migration-cycle-repair-handoff.md) and its focused evidence.
