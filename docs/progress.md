# Progress

## 2026-08-31 — PLANT-002

- Resumed and completed the interrupted Plant/PlantGroup backend slice without replacing its
  existing work. Alembic revision `20260831_0011` adds separate `plants` and `plant_groups` tables
  with application-generated UUIDv7 identity, each record's own required BotanicalIdentity,
  optional restrictive Sowing/Supplier/GeographicPlace/Location references, direct-origin
  exclusivity, precision-preserving collection-entry dates, lifecycle, notes, UTC timestamps, and
  database-enforced text and reference invariants. Plant has no quantity; PlantGroup supports only
  unknown or exact/approximate whole counts, with exact zero restricted to completed, dead, or
  discarded history.
- Added protected list/create/detail/full-update routes at `/api/v1/plants` and
  `/api/v1/plant-groups` using the existing session, owner, exact-Origin, and session-bound CSRF
  architecture. Full PUT atomically corrects direct versus Sowing origin and lifecycle/quantity
  combinations. Joined projections resolve compact BotanicalIdentity, originating Sowing with its
  upstream SeedLot identity context, Supplier, material provenance, and current Location summaries;
  list ordering is deterministic and does not manufacture complete dates from partial dates. No
  DELETE or frontend Plant workflow was added.
- PostgreSQL and API coverage proves minimal and full creation, every direct-origin and lifecycle
  value, inactive Sowing origins, independent downstream BotanicalIdentity, direct/Sowing
  transitions, reference summaries, deterministic ordering, all group quantity/zero combinations,
  atomic corrections, missing and restrictive references, retained history, and authentication,
  Origin, CSRF, and non-owner failures. Regression assertions capture SeedLot quantity plus Sowing
  quantity and germinated count before and after Plant/PlantGroup mutations and prove they remain
  unchanged. Migration coverage exercises `0010 -> 0011 -> 0010 -> 0011`, capability-only downgrade,
  schema inventory, indexes, checks, restrictive foreign keys, invalid database writes, and final
  head restoration.
- Exact successful checks: Ruff formatting/lint; strict mypy over 106 source/test modules; strict
  TypeScript; 138 backend unit tests at 93.37% coverage; all 184 disposable PostgreSQL 18.6
  integration tests, including 30 Plant/PlantGroup API cases and 2 focused migration cases; all 71
  existing frontend tests; OpenAPI and generated TypeScript regeneration/drift; production backend
  and frontend image builds; and a final clean `make check`.
- The three existing `PLANT-002` acceptance criteria remain unchanged and are fully exercised, so
  `PLANT-002` is `verified`. `PLANT-003` and `LINEAGE-002` are now dependency-unblocked but were not
  started. PlantGroup extraction, collection-producer traversal, events, attachments, PWA work, and
  Plant UI remain deferred. Git operations were intentionally not attempted per the workspace
  boundary.

## 2026-08-31 — SOWING-003, PWA-001

- Added the authenticated Sowings collection to primary navigation using generated API declarations
  and the existing session/CSRF client. The responsive screen preserves backend ordering, provides
  compact BotanicalIdentity-first rows, partial-date and germinated/sown summaries without invented
  percentages, case-insensitive BotanicalIdentity/Sowing-label/Location/SeedLot-label search, and
  Active/History/All lifecycle discovery. Desktop uses a compact master/detail layout; narrow screens
  switch between a full-width list and selected detail with Back, detail focus, and row-focus restore.
- Added one progressively disclosed create/edit form backed by POST and full PUT. SeedLot is the only
  required choice; active and historical lots remain understandable and selectable. The form
  preserves year/month/day precision, unknown/exact/approximate seed-count or `g`/`mg` quantity,
  unknown/zero/positive germination totals, exact-count-only denominator validation, optional active
  Location selection with retained retired references, all four correctable lifecycle states,
  cultivation text, independent decimal Celsius bounds including negative values, and notes. Failed
  saves retain input; selected detail groups origin, Sowing facts, non-empty cultivation, and notes.
- Added 12 Sowing component/integration tests covering list/detail loading, empty and failure states,
  summaries, all four search fields, lifecycle filters, selection, list-to-detail-to-Back focus,
  minimal and full creation, every partial-date precision, quantity kinds, germination bounds,
  Location, temperature, lifecycle, full editing, failed-edit retention, CSRF, forbidden responses,
  and session expiry. Exact successful final checks: Prettier; complete ESLint; strict TypeScript;
  strict mypy over 96 files; 113 backend unit tests at 92.95% coverage; all 71 frontend tests (12 new);
  generated OpenAPI/TypeScript drift; host and production-container frontend builds; production
  backend image build; and a final clean `make check`. An earlier parallel host Vitest run passed 44
  tests while 27 changed and unchanged tests exceeded fixed five-second timeouts under saturation;
  an immediate serial host rerun and the unchanged-timeout container run passed all 71.
- Added planned P2 `PWA-001`, dependent on `FRONTEND-002` and `SOWING-003`, for safe authenticated-app
  installability and reliable application-shell behavior. Its boundary explicitly excludes offline
  mutation/synchronization, push, and native integrations; any later offline writes require a
  separate queued-write, conflict, stale-data, auth-expiry, replay/idempotency, and multi-device
  contract. No manifest, service worker, cache, icon, offline write, Plant behavior, germination
  observations/history, backend domain/API change, or percentage calculation was added.
- All three existing `SOWING-003` acceptance criteria remain unchanged and are exercised, so
  `SOWING-003` is `verified`; `PWA-001` remains `planned`. `PLANT-002` is the next dependency-aligned
  P1 implementation increment and was not started. Git status/history/diff remain unavailable because
  this workspace exposes an unusable empty `.git` directory.

## 2026-08-31 — SOWING-002

- Added focused Alembic revision `20260831_0010` after unchanged `20260830_0009`. The new
  `sowings` table owns application-generated UUIDv7 identity, required restrictive SeedLot lineage,
  optional restrictive current Location, precision-preserving sowing date, strictly positive
  exact/approximate seed-count or `g`/`mg` quantity, optional non-negative germinated count, bounded
  normalized cultivation text, independently optional decimal Celsius bounds, retained lifecycle,
  safe multiline notes, and timezone-aware UTC timestamps. PostgreSQL independently enforces date,
  quantity, exact-count germination, temperature, text, lifecycle, and reference invariants.
- Added protected `GET/POST /api/v1/sowings` and `GET/PUT /api/v1/sowings/{sowing_id}` behavior.
  Minimal creation requires only an existing SeedLot; full PUT validates the proposed final state in
  one operation and may correct SeedLot lineage. List/detail responses resolve compact current
  SeedLot, BotanicalIdentity, and Location display context through joined projections, accept
  inactive SeedLots and retired Locations, retain completed/failed/abandoned history, and order
  active records first followed by precision-preserving descending dates, null-last labels, and UUID.
  No DELETE or lifecycle side effects were added.
- Unit and PostgreSQL regression coverage proves that creating, updating, completing, failing, or
  abandoning a Sowing never mutates either SeedLot quantity. Authenticated integration coverage
  exercises quick entry, full cultivation data, all date/quantity/lifecycle cases, raw germination
  totals, atomic denominator corrections, temperatures, resolved summaries, ordering, missing and
  retired references, not-found, malformed payloads, authentication, Origin, CSRF, and retained
  historical records. Migration coverage exercises `0009 -> 0010 -> 0009 -> 0010`, schema inventory,
  indexes, restrictive FKs, database rejection paths, capability-only downgrade, and final-head
  restoration.
- Exact successful checks: Ruff format and lint; strict mypy over 96 source/test modules; 113 backend
  unit tests at 92.95% coverage; all 152 disposable PostgreSQL 18.6 integration tests, including 22
  Sowing API cases and 2 focused migration/invariant cases; frontend Prettier, ESLint, strict
  TypeScript, and all 59 existing component tests; OpenAPI/TypeScript regeneration and drift check;
  production backend/frontend image builds; and a final clean `make check`. An earlier frontend run
  under severe host saturation passed 34 tests while 25 unchanged tests exceeded their five-second
  timeouts; the immediate normal-load rerun passed all 59 in 10.16 seconds. The first `make check`
  attempt was stopped after its frontend container stalled fetching pnpm and a later partial run was
  interrupted during mypy; the final full run and every constituent check passed with the repository
  or bundled pinned toolchain.
- Regenerated the authoritative OpenAPI artifact and updated frontend declarations. No Sowing UI,
  frontend navigation, Plant/PlantGroup persistence, germination observations/percentages, SeedLot
  deduction or ledger, attachment, event, or generic-lineage work was introduced. All three existing
  `SOWING-002` acceptance criteria remain unchanged and are exercised, so `SOWING-002` is `verified`;
  `SOWING-003` is now the next Sowing implementation task and was not started. Git status/history/diff
  remain unavailable because this workspace exposes an unusable empty `.git` directory.

## 2026-08-31 — LINEAGE-001

- Defined lineage as explicit material/workflow provenance using only the direct
  `SeedLot → Sowing → Plant / PlantGroup`, `PlantGroup → extracted Plant`, and single
  Plant-or-PlantGroup producer to collection-produced SeedLot relationships. Every Sowing requires
  exactly one SeedLot; downstream Sowing origins remain optional and one-to-many; a Plant has at
  most one immediate workflow origin; PlantGroup producers are valid without fictional individual
  Plants; and unknown links remain absence rather than inferred or placeholder records.
- Kept BotanicalIdentity independently correctable across lineage, persisted only immediate edges,
  retained lineage through inactive lifecycle and retired supporting reference data, distinguished
  direct-origin metadata from workflow edges, required explicit operator corrections, and recorded
  the no-self-ancestor invariant without introducing a generic graph, genealogy, polymorphic
  reference, cycle engine, event, or attachment relationship.
- Assigned future persistence narrowly: `SOWING-002` owns required Sowing-to-SeedLot persistence,
  `PLANT-002` owns applicable Sowing origins, `PLANT-004` owns the extracted-Plant transaction and
  direct PlantGroup origin, and `LINEAGE-002` owns the single collection producer plus authorized
  traversal. Refined `LINEAGE-002` and `PLANT-004` wording to include PlantGroup production and avoid
  redundant ancestor edges while preserving their feature intent.
- Baseline `make check` could not enter its first formatting command because this workspace cannot
  access the Docker socket. The bundled Node runtime and repository-pinned Prettier then completed
  write/check validation for all changed documentation; JSON parsing, unique/allowed feature ID,
  status and priority checks, dependency existence, dependency DAG acyclicity, unchanged
  `LINEAGE-001` criteria, focused contract assertions, and dependency-status checks all passed over
  57 features. No migration, persistence, backend or frontend application code, API/generated
  contract, runtime dependency, extraction transaction, event history, traversal endpoint, or help
  UI was added.
- All three existing `LINEAGE-001` acceptance criteria remain unchanged and are explicitly covered,
  so `LINEAGE-001` is `verified`. Every declared `SOWING-002` dependency is now verified, making it
  the next dependency-aligned implementation task; it was not started. Git status, history, and diff
  remain unavailable because this workspace exposes an unusable empty `.git` directory.

## 2026-08-31 — PLANT-001

- Defined `Plant` as exactly one individually tracked living or historical specimen with no quantity,
  and `PlantGroup` as multiple individuals of exactly one BotanicalIdentity intentionally managed as
  one record. Both have stable application-generated UUIDv7 identity, reference exactly one
  authoritative BotanicalIdentity, allow a non-unique display label, and remain separate concrete
  concepts without polymorphic collection-item or inheritance infrastructure.
- Made BotanicalIdentity the only operator-required fast-entry fact. Existing and historical Plants
  and groups remain valid without invented SeedLot or Sowing history. Where known, one originating
  Sowing preserves the explicit SeedLot-to-Sowing path; otherwise direct origin uses only
  `purchased`, `gift_exchange`, `collection_produced`, `other`, or `unknown`. Optional direct Supplier,
  GeographicPlace material provenance, and current collection Location remain independent facts and
  are never copied from upstream SeedLot data for convenience.
- Established precision-preserving optional collection-entry date, optional current Location, notes,
  correctable retained lifecycle vocabularies (`active`, `dead`, `lost`, `discarded` for Plant;
  additionally `completed` for PlantGroup), and optional exact/approximate whole-number group count.
  Exact zero is restricted to genuinely empty `completed`, `dead`, or `discarded` groups; active,
  approximate, negative, and lost-zero cases are invalid, while every inactive state may retain an
  unknown quantity when the final count is not known.
- Preserved the future extracted-Plant provenance path through PlantGroup, Sowing, and SeedLot while
  deferring quantity reduction, Plant creation, transaction mechanics, and concurrency to
  `PLANT-004`. Explicit lineage consistency/traversal remains with `LINEAGE-001`; current-state edits,
  chronological events, photos/attachments, persistence, API routes, and Plant UI remain deferred to
  their owning capabilities. Documented likely layered contextual-help needs without implementing
  `UX-002`.
- Baseline `make check` passed: Prettier and Ruff formatting, ESLint and Ruff lint, strict mypy over
  86 source files, strict TypeScript, 100 backend unit tests at 92.90% coverage, 59 frontend tests,
  and generated API drift. Final Prettier, JSON parsing, backlog integrity, DAG, and focused contract
  assertions passed. A final `make check` rerun passed formatting, lint, strict typing, and all 100
  backend tests, then 11 unchanged frontend tests exceeded their fixed five-second timeouts under
  host load; an immediate focused rerun passed all 59 in 9.49 seconds, and the separately rerun API
  drift check passed. No runtime dependency, application code, migration, generated API artifact,
  API route, or frontend screen was added.
- All three existing `PLANT-001` acceptance criteria remain unchanged and are explicitly supported,
  so `PLANT-001` is `verified`. `LINEAGE-001` is now the next dependency-aligned contract step before
  `SOWING-002` and was not started. Git status, history, and diff remain unavailable because this
  workspace exposes an unusable empty `.git` directory.

## 2026-08-31 — SOWING-001

- Defined Sowing as one intentionally managed, internally homogeneous attempt using material from
  exactly one SeedLot, with separate records for intentionally different initial treatments or
  broadly different conditions. The minimum record is UUIDv7 identity, one SeedLot, defaultable
  operator-controlled lifecycle, and implementation-managed UTC timestamps; all dates, quantities,
  cultivation facts, results, Location, label, and notes remain optional.
- Specified a non-unique display label; precision-preserving optional sowing date; strictly positive
  exact/approximate count or `g`/`mg` weight; no automatic SeedLot deduction; and an optional current
  non-negative whole-number germinated count. Only exact seed count supplies a trustworthy
  denominator and upper bound, so approximate count, weight, or unknown quantity cannot support a
  claimed precise germination percentage.
- Established correctable `active`, `completed`, `failed`, and `abandoned` lifecycle states without
  inferred outcomes or destructive deletion. Current collection Location is independent of SeedLot
  storage. Optional substrate, method/container, pretreatment, environment, and notes remain text;
  optional structured Celsius minimum/maximum allow either bound and require minimum <= maximum when
  both are present.
- Preserved the explicit `SeedLot → Sowing → Plant / PlantGroup` boundary: germination creates no
  Plant automatically, unknown historical lineage remains possible, and dated observations stay with
  `GERMINATION-001`. Sowing is documented as a future attachment/photo target without adding media
  storage or relationships. Added planned P2 `UX-002` for layered inline, accessible-control, and
  deeper contextual help after the core collection forms exist.
- Baseline `make check` passed with formatting, lint, strict typing, 100 backend unit tests, 59
  frontend tests, and generated API drift. Final Prettier and JSON/backlog/DAG validation passed. A
  final `make check` rerun passed formatting and lint, then produced no output in unchanged backend
  mypy for over two minutes and was stopped; the full baseline remains the completed repository
  check. No application code, migration, API, generated contract, UI, runtime dependency, quantity
  accounting, event table, or Plant persistence changed. The three existing `SOWING-001`
  acceptance criteria remain unchanged and are fully documented, so `SOWING-001` is `verified`;
  `SOWING-002` is the next implementation step and was not started. Git status, history, and diff
  remain unavailable because this workspace exposes an unusable empty `.git` directory.

## 2026-08-31 — SEED-004 collapsible creation refinement

- Standardized the current primary creation workflows behind one shared disclosure controller. Seeds,
  Botanical identities, Suppliers, Locations, and Geography now start with their existing create form
  closed and expose an accessible `+ New …` button with expanded state. Opening focuses the first
  meaningful field; cancel and successful creation close the form and restore trigger focus, while
  validation and API failures retain both the open form and entered values.
- Reused every existing form and API path. The SeedLot fast-entry form now spans above the desktop
  master-detail grid, so the closed inventory and selected detail/editor begin on the same row;
  contextual BotanicalIdentity, Supplier, Location, and GeographicPlace creation remains intact. The
  four reference directories use the same full-width-above-directory pattern on desktop and the same
  disclosure interaction on narrow screens.
- Component coverage verifies initial closed state, the five top-level actions, opening and focus,
  cancel/close, successful close, failure retention, Seed master-detail structure, and contextual
  SeedLot creation. Exact successful checks: frontend Prettier, ESLint, strict TypeScript, all 59
  component tests, Vite production build, and generated API drift. A combined verification attempt
  later encountered only fixed five-second test timeouts under sustained host load; the same unchanged
  59-test suite had already passed in a normal-load run. No backend application, migration, API,
  dependency, generated contract, or domain behavior changed, and `SOWING-001` remains `planned` and
  untouched. Git status/history/diff remain unavailable because this workspace exposes an unusable
  empty `.git` directory.

## 2026-08-31 — SEED-004 UI refinement, ATTACHMENT-003 roadmap refinement

- Refined the verified Seeds inventory into one responsive master-detail workspace. At normal desktop
  widths the compact, searchable lifecycle-filtered inventory remains on the left while the selected
  detail or existing full editor occupies a flexible right pane with a form-safe minimum width. The
  same semantic inventory and detail regions collapse to one column at narrower widths; selected rows
  retain their visible inset marker, contrast, and `aria-pressed` state. All existing creation,
  contextual reference creation, progressive details, validation, history, and failure behavior was
  preserved.
- Added consistent top-level `+ New` actions to Botanical identities, Suppliers, Locations, and
  Geography. Each action focuses the first field in the page's original create form, which is now
  visually ordered before its directory; no second form, API path, or modal implementation was added.
  Existing create, duplicate, hierarchy, refetch, selection, authentication, and keyboard behavior
  remains owned by the reused forms, and SeedLot contextual creation is unchanged.
- Refined planned `ATTACHMENT-003` and the product roadmap without implementing it. Future collection
  photos explicitly distinguish Florabase-managed uploaded/local images from untrusted external image
  source references with optional attribution/captions and broken-link, privacy, security, and
  fetch/proxy decisions. SeedLot, Plant, PlantGroup, and justified history/events are the intended
  explicit targets; records remain usable without photos, while an optional primary/cover image may
  later support compact inventories without deciding persistence mechanics early.
- Exact checks passed: baseline and final `make check`; frontend Prettier format/write and format
  check, ESLint, strict TypeScript, all 59 component tests, and the Vite production build; generated
  API drift verification; JSON parsing and backlog dependency/status validation. No backend
  application file, migration, generated API contract, runtime dependency, attachment storage/API,
  image downloading/hotlinking, or Sowing capability changed. `SOWING-001` remains the next core P1
  product-contract step. Git status/history/diff remain unavailable because this workspace exposes an
  unusable empty `.git` directory.

## 2026-08-31 — SEED-004

- Added Seeds as the next real primary application section and built a collection-first responsive
  inventory rather than another reference-data administration screen. The compact desktop rows and
  stacked narrow-screen layout lead with BotanicalIdentity display labels, retain backend ordering,
  show useful quantity/storage/lifecycle context, and open complete details without exposing internal
  identifiers. Active is the default view; History retains exhausted, discarded, and lost lots; All
  and a composed client-side search cover botanical label, lot label, Supplier, provenance, and
  Location, with distinct global-empty and no-match states.
- Added generated-contract-typed SeedLot list/create/full-resource-PUT helpers and one coherent fast
  create/edit form. Only BotanicalIdentity is user-required; source and lifecycle defaults are sent
  without asking the operator to manufacture source, date, quantity, Supplier, provenance, Location,
  viability, or notes. More details progressively reveals material provenance, three independent
  precision-aware partial dates, lifecycle, and notes. Source labels are domain-facing and Other alone
  retains its optional detail.
- Presented quantity as one value plus seeds/g/mg and an Approximately choice. Unknown remains an empty
  input; count, gram, milligram, and approximate mappings use the generated contract. Friendly client
  validation permits exact zero only for exhausted lots and validates the final form state, so direct
  historical exhausted-zero entry, lost-to-active correction, and exhausted-zero-to-active-positive
  correction each use one create or PUT rather than intermediate saves.
- Added a narrow accessible searchable combobox/listbox shared by the four SeedLot references. Compact
  modal editors reuse the independent BotanicalIdentity, Supplier, Location, and custom
  GeographicPlace APIs; created records are refreshed and selected automatically while every unsaved
  SeedLot field remains in place. Botanical duplicate conflicts select the existing identity, root or
  child Locations and child custom places are supported, canonical geography is not mutated, and
  contextual failures retain the lot form. Modal focus enters the first control, traps Tab safely,
  supports Escape/cancel, and returns to the triggering picker.
- Retired Supplier, Location, and custom-place choices are omitted from ordinary new selection but a
  currently referenced retired choice remains visible, labelled, editable, and saveable. Initial load,
  empty/success/validation, stale reference, create/update, contextual create, session expiry,
  forbidden, and network/server failures are explicit. No migration, backend route, dependency,
  Sowing, Plant, Order, dashboard, advanced search, import/export, or attachment capability was added.
- Exact checks passed before the final repository gate: baseline `make check`; frontend Prettier,
  ESLint, strict TypeScript, and 59 component tests (45 preserved plus 14 SeedLot workflow tests);
  generated API drift; both production image builds including the Vite production build; and all 128
  disposable PostgreSQL 18.6 integration tests. A real local browser smoke check reached the healthy
  owner login UI; authenticated Seeds behavior was not manually entered because no credentials were
  requested or changed, and is exercised by the component integration suite instead. All three
  unchanged acceptance criteria are exercised, so `SEED-004` is `verified`; `SOWING-001` is now the
  dependency-aligned next product-contract step and was not started. Git status/history/diff remain
  unavailable because this workspace exposes an unusable empty `.git` directory.

## 2026-08-30 — SEED-003

- Added the protected `/api/v1/seed-lots` create, complete-list, get, and full-resource `PUT`
  workflow. Reads require an authenticated session; writes reuse the verified owner, exact-Origin,
  and session-CSRF dependencies. Lifecycle correction remains part of the atomic normal update and
  deliberately permits direct correction among `active`, `exhausted`, `discarded`, and `lost`; no
  DELETE or separate lifecycle route was introduced.
- Added SeedLot-local structured partial-date and quantity contracts rather than exposing persistence
  columns. Minimal creation requires only `botanical_identity_id` and applies `unknown` source plus
  `active` lifecycle defaults. Exact decimal inputs accept JSON numbers or strings, while responses
  always serialize decimals as strings for a lossless generated TypeScript read contract. API text
  normalization, precision/calendar validation, source-detail rules, quantity/unit/approximation,
  and zero/lifecycle invariants mirror the verified database boundary.
- Validated BotanicalIdentity, Supplier, GeographicPlace provenance, and collection Location as
  independent references without rejecting explicitly retired historical records. Responses retain
  the stable IDs and derive compact current display summaries. List projection joins all four
  references in one query, loads each needed hierarchy once, and orders active lots first, then by
  case-insensitive botanical display components, optional label, and UUID. Related renames therefore
  appear on later reads without snapshots or per-lot N+1 lookups.
- Added focused schema tests and 33 real PostgreSQL API integration cases covering minimal/full and
  duplicate lots, every source kind, all three precisions for all three date fields, malformed dates,
  exact/approximate count and `g`/`mg` weight, exhausted zero/unknown quantity, invalid zero states,
  atomic lifecycle corrections, retired and missing references, live summary renames, deterministic
  retained inactive listings, not-found, authentication, owner/Origin/CSRF failures, and absence of
  DELETE. Regenerated backend OpenAPI and frontend declarations; no frontend SeedLot UI, migration,
  dependency, Sowing, Plant, Order, lineage, import/export, map, attachment, or contextual creation
  work was added.
- Exact checks passed: Ruff formatting/lint; strict mypy over 86 source files; 100 backend unit tests
  at 92.90% coverage, including 20 focused SeedLot schema/model/service/API assertions; all 128
  PostgreSQL 18.6 integration tests; 45 frontend component tests; strict TypeScript; generated API
  drift verification; production backend/frontend image builds; and final `make check`. The
  unchanged three `SEED-003` acceptance criteria are exercised, so `SEED-003` is `verified`. Git
  status/history/diff remain unavailable because this workspace exposes an unusable empty `.git`
  directory.

## 2026-08-30 — SEED-002 historical zero-quantity refinement

- Added focused Alembic revision `20260830_0009` after unchanged revision `20260830_0008`. It
  replaces the named SeedLot quantity check with one coherent quantity/lifecycle invariant mirrored
  exactly by the SQLAlchemy model: positive exact or approximate counts and `g`/`mg` weights retain
  their existing behavior, while exact zero is valid only for an `exhausted` count or weight.
  Negative values, approximate zero, and zero on `active`, `discarded`, or `lost` lots are rejected;
  the all-null unknown tuple remains valid for every lifecycle.
- The downgrade restores the exact strictly-positive `SEED-002` check. Disposable PostgreSQL 18.6
  exercised `0007 -> 0008 -> 0009 -> 0008 -> 0009`, including rejection of zero at `0008` and
  acceptance after each upgrade. Direct SQL coverage now includes exhausted exact zero counts,
  grams, and milligrams; exhausted unknown quantity; all inactive-state distinctions; approximate
  and negative rejection; and retained positive exact/approximate count and weight behavior.
- Refined the domain contract so zero means known physical exhaustion, exhausted may still have an
  unknown historical quantity, and lost/discarded never imply zero. Clarified that historical lots
  may be entered directly as exhausted with zero or unknown quantity. The collection-first roadmap
  also now requires future contextual BotanicalIdentity, Supplier, Location, and GeographicPlace
  creation to reuse normal resource APIs instead of coupled nested collection-record writes.
- Exact checks passed: reviewed focused offline upgrade/downgrade SQL; Ruff formatting/lint; strict
  mypy; 82 backend unit tests at 92.85% coverage; 45 frontend component tests; API drift; and all 95
  PostgreSQL integration tests after one diagnostic run identified and corrected the expected-head
  assertion and migration-probe cleanup. Final `make check` passed. No dependency changed.
- The unchanged `SEED-002` acceptance criteria remain fully exercised, so `SEED-002` stays
  `verified`. No API schema, service, route, generated contract, frontend implementation, Sowing, or
  Plant work was started. `SEED-003` remains `planned` and is ready as the next increment. Git
  status/history/diff remain unavailable because this workspace exposes an unusable empty `.git`
  directory.

## 2026-08-30 — UX-001, IMPORT-001 roadmap refinement

- Recorded the long-term collection- and activity-first information architecture in the product
  roadmap. BotanicalIdentity, Supplier, Location, and GeographicPlace directories remain necessary
  secondary administration surfaces; future core workflows may select or create reference data in
  context only where a concrete interaction warrants it. No current navigation or UI changed.
- Added planned P2 `UX-001`, dependent on the SeedLot, Sowing, and Plant/PlantGroup UIs, so the later
  navigation refinement cannot block the core path. Confirmed that planned `ENRICHMENT-001` already
  owns source-reviewed, reviewable BotanicalProfile enrichment and clarified that later
  `TAXONOMY-001` reconciliation remains separate; no provider was selected.
- Added planned P2 `IMPORT-001`, dependent on stable SeedLot and Plant collection interfaces, for a
  documented CSV-oriented format and templates, validation-before-mutation, dry-run preview,
  ambiguity-safe reference handling, row-level errors, and simple CSV or useful structured exports.
  It remains distinct from backup/restore and P3 `TRANSFER-001`, which preserves high-fidelity
  references, lineage, provenance, lifecycle, and attachments.
- Documentation-only baseline `make check` could not start because this workspace cannot access the
  Docker socket. Completion checks validate formatting, JSON schema conventions, dependency
  existence, and an acyclic dependency graph. No migration, backend/frontend application code,
  generated API artifact, dependency, or verified feature criteria/status changed. `SEED-003`
  remains the next P1 implementation increment and was not started.

## 2026-08-30 — SEED-002

- Added only the SeedLot persistence slice at Alembic revision `20260830_0008`. The concrete
  SQLAlchemy mapping and table require application-generated UUIDv7 identity, exactly one
  BotanicalIdentity, default `unknown` source, default `active` lifecycle, and UTC timestamps;
  label, source detail, Supplier, GeographicPlace material provenance, acquisition/harvest dates,
  quantity, viability horizon, collection Location, and multiline notes remain independent and
  optional. Matching physical lots have no descriptive uniqueness constraint.
- Preserved year/month/day claims through independent precision/year/month/day groups for
  acquisition, harvest, and expected viability. Named PostgreSQL checks reject missing or extra
  components, unsupported precision, out-of-range values, and invalid complete calendar dates.
  Quantity is an all-null unknown tuple or a positive exact/approximate seed count or `g`/`mg`
  weight; database checks reject fractions, absent or misplaced units, missing values/flags, and
  non-positive values.
- Added restrictive, independently nullable Supplier, GeographicPlace, and Location foreign keys
  alongside the required restrictive BotanicalIdentity foreign key. Indexed the four relationship
  columns and lifecycle for expected joins and inventory filtering. Retired reference rows remain
  valid historical targets, and `exhausted`, `discarded`, and `lost` lots remain persisted. No
  Sowing, Plant, Order, lineage, container, movement, API, OpenAPI contract, navigation, or UI was
  introduced; no dependency changed.
- Exact checks passed: baseline `make check`; Ruff formatting/lint; strict mypy over 80 files; 82
  backend unit tests at 92.85% coverage; complete disposable PostgreSQL 18.6 suite (94 tests),
  including `0007 -> 0008 -> 0007 -> 0008`, direct-SQL constraints, all foreign-key failures and
  restrictive deletes; reviewed offline upgrade and downgrade SQL; production backend/frontend
  image build; API drift and existing frontend checks through final `make check`. The first database
  run exposed nullable `CHECK` expressions that could evaluate to SQL `NULL`; wrapping the complete
  date and quantity predicates with `IS TRUE` closed that boundary before the passing full rerun.
- All three unchanged `SEED-002` acceptance criteria are exercised, so it is `verified`.
  `SEED-003` is the dependency-aligned next increment and was not started. Git status/history/diff
  remain unavailable because this workspace exposes an unusable `.git` directory.

## 2026-08-30 — GEOGRAPHY-001

- Added a complete GeographicPlace vertical slice distinct from collection Location. Alembic
  revision `20260830_0007` installs 287 canonical rows from the committed normalized Unicode CLDR
  48.2.1 snapshot, with deterministic UUIDv7 identities, one restrictive adjacency tree, typed
  `un_m49`, `iso_3166_1_alpha_2`, or `cldr_territory` source codes, immutable canonical metadata,
  and no runtime network dependency.
- Preserved broad-node precision and inferred ancestry, including `World → Americas → Latin America
and the Caribbean → South America → Brazil` and `World → Asia → Southeast Asia → Thailand`.
  Operator-defined local nodes extend any active canonical/custom parent without fabricated codes;
  rename/re-parent, arbitrary practical depth, cycle rejection, and non-destructive custom-only
  retire/reactivate behavior follow the documented hierarchy rules.
- Added protected deterministic list/get/create/update/retire/reactivate behavior at
  `/api/v1/geographic-places`. Reads require authentication without CSRF; mutations require owner,
  exact Origin, and session CSRF. Canonical mutation attempts return the stable
  `canonical_geographic_place_immutable` conflict. Responses derive paths rather than storing
  redundant ancestry.
- Added Geography navigation and an accessible complete tree/filter/selection workflow. Brazil,
  South America, Thailand, and any broad region are selectable; canonical/custom status and full
  paths are explicit. Operators can create `Chiang Mai → Doi Suthep`, edit/re-parent custom nodes,
  and deliberately retire/reactivate them, with loading, error, validation, authorization, session
  expiry, keyboard, and lifecycle states covered.
- Documented the official CLDR source files, pinned release, Unicode-3.0 license and attribution,
  upstream and normalized checksums, reproducible generator, offline migration strategy,
  GeographicPlace/Location distinction, precision semantics, and deferred coordinates/GIS/maps.
  Fixed the stale domain introduction that described verified Location as future work. No runtime
  dependency was added.
- Exact focused checks passed: deterministic dataset regeneration and validation; Ruff; strict mypy
  over 76 files; 80 backend unit tests at 92.52% coverage; 45 frontend component tests; and 86
  PostgreSQL 18.6 integration tests, including migration upgrade/downgrade/re-upgrade. Generated
  OpenAPI and frontend declarations were regenerated. Both production container images built, and
  final `make check` passed with formatting, lint, strict typing, unit/component tests, and API
  drift verification.
- All refined `GEOGRAPHY-001` acceptance criteria are exercised, so it is `verified`.
  `GEOGRAPHY-002` and `SEED-002` were not started. `SEED-002` now has all declared dependencies
  verified and is ready to start.

## 2026-08-30 — SEED-001

- Defined SeedLot as one physically managed lot, packet, or bag with stable UUID identity and exactly
  one BotanicalIdentity reference. Identical packets remain distinct lots; first-version container
  splits do not create lots, an optional non-unique operator label is only display context, and
  substantial unknown information remains valid.
- Fixed the initial source vocabulary as `purchased`, `purchased_fruit`, `self_collected`,
  `collection_produced`, `gift_exchange`, `other`, and `unknown`, with short optional clarification
  only for `other`. Source kind, optional Supplier, and optional material provenance answer separate
  questions; Supplier location never substitutes for material provenance.
- Defined independent acquisition and harvest dates at year, month, or complete-date precision;
  optional exact or approximate positive whole-seed count or positive decimal weight; and an optional
  operator-entered viability horizon that can only produce a caution, never an `expired` state or
  automatic lifecycle change. Automatic Sowing deduction and quantity ranges remain deferred.
- Defined non-destructive `active`, `exhausted`, `discarded`, and `lost` lifecycle states; optional
  current collection Location storage distinct from provenance; lot-specific multiline notes; the
  Order/price boundary; and explicit future `SeedLot → Sowing → Plant / PlantGroup` plus optional
  parent-Plant lineage without a generic graph.
- Added planned `GEOGRAPHY-001` for maintained hierarchical GeographicPlace reference data and made
  it a prerequisite of `SEED-002`. Added planned `GEOGRAPHY-002` to retain the independent future
  BotanicalIdentity/Profile native-range relationship. Broad known nodes and disjunct ranges remain
  valid, ancestors are inferred, precision is never manufactured, and no dataset, migration, API,
  UI, GIS, map, or integration was implemented.
- Baseline checks passed: Prettier over the three target files; JSON parsing; unique feature IDs;
  allowed status and priority values; nonempty acceptance criteria; existing dependencies; acyclic
  dependency graph; and exact preservation of the three `SEED-001` acceptance criteria. The focused
  post-change contract audit passed 36 content assertions plus geography/backlog assertions. Final
  formatting and complete backlog validation are recorded by this task's completion checks.
- All three unchanged `SEED-001` acceptance criteria are explicitly supported, so `SEED-001` is
  `verified`. `GEOGRAPHY-001` is the exact dependency-aligned next capability and remains `planned`;
  `SEED-002` is not implementation-ready until it is complete. No application, migration, generated
  API, UI, Sowing, Plant, Order, or external geography file changed. Git status, history, and diff
  remain unavailable because this workspace exposes an unusable empty `.git` directory.

## 2026-08-30 — LOCATION-001

- Added the installation-wide Location directory at Alembic revision `20260830_0006` with UUIDv7,
  normalized non-unique name, nullable restrictive self-reference, non-destructive retirement, and
  UTC timestamps. The adjacency list supports arbitrary practical depth; no user ownership,
  persisted path, geographic provenance, address, GIS, generic tree framework, SeedLot, Sowing, or
  Plant model was introduced.
- Added protected deterministic list, create-root-or-child, get, rename/re-parent, retire, and
  reactivate behavior at `/api/v1/locations`. Reads use authenticated sessions without CSRF;
  mutations require owner authorization, exact Origin, and session-bound CSRF. Hierarchy mutations
  lock the current rows, reject self/descendant cycles, block retirement with active descendants,
  and block reactivation beneath retired ancestors. API responses derive `display_path` without
  duplicating ancestry in storage; OpenAPI and frontend TypeScript declarations are current.
- Added Botanical identities, Suppliers, and Locations navigation plus an accessible semantic tree
  and detail/editor workflow. Native controls support selection, fast root/child creation,
  hierarchy-aware parent labels, rename/re-parent, deliberate lifecycle changes, retired-state
  discovery, client-side invalid-parent prevention, keyboard use, and explicit
  loading/empty/validation/conflict/session/forbidden/network states.
- Exact checks passed: Ruff formatting/lint and strict mypy; 76 backend unit tests at 92.72%
  coverage; fresh PostgreSQL 18.6 migration upgrade/downgrade/re-upgrade plus 82 integration
  tests; 42 frontend component tests; Prettier, ESLint, strict TypeScript, production frontend and
  backend image builds; generated API drift; and final `make check`. No dependency was added.
- All three unchanged acceptance criteria were exercised across PostgreSQL/API and accessible UI
  coverage, so `LOCATION-001` is `verified`. `SEED-001` is the next dependency-aligned product
  contract and was not started.

## 2026-08-30 — SUPPLIER-001

- Added the installation-wide Supplier directory at Alembic revision `20260830_0005` with UUIDv7,
  required normalized name and six-value kind, optional website/email/phone/notes, nullable
  retirement timestamp, and UTC creation/update timestamps. Names are intentionally not unique;
  retirement retains records and no user, geographic-origin, SeedLot, Order, address, or generic
  party/contact abstraction was introduced.
- Added protected deterministic list, create, get, full update, retire, and reactivate behavior at
  `/api/v1/suppliers`. Reads use the verified session boundary without CSRF; every mutation requires
  owner authorization, exact Origin, and session-bound CSRF. Regenerated OpenAPI and frontend
  TypeScript declarations.
- Added the second application navigation section and an accessible Supplier directory/detail
  workflow with fast name-and-kind creation, optional contact/details, client-side filtering,
  keyboard selection, editing, deliberate retirement/reactivation, retired-state labeling, safe
  links, and explicit loading/empty/validation/session/forbidden/network states.
- Exact focused checks passed: Ruff and strict mypy; 69 backend unit tests at 92.32% coverage; fresh
  PostgreSQL 18.6 migration upgrade/downgrade/re-upgrade plus 76 integration tests; and 37 frontend
  component tests with Prettier, ESLint, and strict TypeScript. The final production build, API drift,
  and consolidated `make check` results are recorded in the completion report.
- All three unchanged acceptance criteria were exercised across PostgreSQL/API and accessible UI
  coverage, so `SUPPLIER-001` is `verified`. `LOCATION-001` is the next dependency-aligned collection
  reference capability and was not started.

## 2026-08-27 — FOUNDATION-001

- Established the documented modular-monolith foundation, explicit configuration/migrations, health/readiness API, generated OpenAPI boundary, React health UI, Compose production/development modes, quality tooling, and guarded backup/restore workflows.
- Local checks executed: backend Ruff format/lint, strict mypy, pytest (9 tests, 99% coverage); frontend Prettier, strict TypeScript, Vitest (2 tests), ESLint, and Vite production build. See task report for final consolidated results.
- Accepted ADRs 0001–0004. Botanical normalization and authentication remain deliberately unresolved.
- Docker socket access was unavailable during implementation; container health, migration, persistence, and backup verification remain outstanding and FOUNDATION-001 is therefore `implemented`, not `verified`.

## 2026-08-27 — FOUNDATION-001, OPS-001

- Verified the production-oriented stack on Docker Engine 29.7.2 and Compose 5.5.0: production images built, PostgreSQL/backend/frontend became healthy, Alembic upgraded PostgreSQL to `20260827_0001`, the frontend document loaded, and liveness/readiness returned HTTP 200 through nginx.
- Fixed runtime defects discovered by verification: backend development tools were absent from `PATH`; non-root development checks could not write ephemeral caches; the frontend image omitted the repository's pnpm policy files and seeded an unwritable dependency volume; and PostgreSQL 18 required the named volume at `/var/lib/postgresql`.
- Exact project checks passed: `make format-check`, `make lint`, `make typecheck`, `make test` (9 backend tests at 98.13% coverage and 2 frontend tests), `make check` including generated API drift, `make build`, `make up`, `make migrate`, and `make health`. `docker compose ps` showed all three services healthy; current service and isolated-restore logs contained no unexpected application or database errors.
- Persistence was exercised by inserting `runtime_persistence_probe`, force-recreating only the database container, and confirming the container ID changed while `florabase_postgres_data`, Alembic revision `20260827_0001`, `schema_initialized=true`, and the probe survived. The probe was removed afterward; no PostgreSQL volume was deleted.
- `make backup` created and validated `backups/florabase-20260827T200939Z.dump` (2,720 bytes; SHA-256 `c58e9c977816fde81e78ff28034c5a81f0ad2c55810d3fdea0375b3e737b7c29`). The dump restored into a network-isolated, tmpfs-backed PostgreSQL 18 container; its revision and metadata matched the source, and the disposable container was removed. The reusable drill and cleanup procedure is documented in `docs/backup-restore.md`.
- `FOUNDATION-001` and `OPS-001` are now `verified`. Git status/history/diff remained unavailable because this task environment exposed an empty `.git` directory; runtime acceptance did not depend on Git metadata.

## 2026-08-28 — SECURITY-001, runtime verification review

- Reviewed the runtime-verification changes in both Dockerfiles, production/development Compose rendering, backup/restore documentation and scripts, and foundation backlog/progress claims. PostgreSQL 18 correctly persists the version-specific `PGDATA` below the named volume mounted at `/var/lib/postgresql`; production still publishes only the frontend and runs application images without development dependencies.
- Corrected concrete review findings: excluded host caches and dependencies from Docker build contexts; restored backend dependency-layer caching; removed the development image's world-writable `/app`; redirected development caches to `/tmp`; replaced the inherited production frontend port/healthcheck in development; removed the unused uploads volume declaration; disabled backend trust of forwarded headers; and made destructive restore confirmation include the exact running database name.
- Accepted ADR 0005: the backend will own a real initial owner account and opaque PostgreSQL-backed sessions using Argon2id, a secure HTTP-only same-site cookie, synchronizer CSRF tokens, bounded lifetimes, revocation, PostgreSQL-backed login throttling, explicit HTTPS/origin configuration, and no proxy-asserted identity. JWT, OAuth/OIDC, Redis, third-party identity, multi-user enrollment, recovery, MFA, and API tokens remain deliberately deferred.
- Exact checks passed: backend Ruff format/lint, strict mypy, and pytest (9 tests, 99.07% coverage); frontend Prettier, ESLint, strict TypeScript, Vitest (2 tests), and Vite production build; production and development `docker compose config` assertions; `bash -n` for backup/restore scripts; feature JSON parsing/status/dependency assertions; Uvicorn option inspection; and a stubbed restore attempt proving a mismatched database confirmation exits before any stop/drop command.
- Docker image rebuild and live service health were attempted but could not be rerun in this task environment: direct Docker socket access was denied and passwordless sudo was unavailable. Git status/history/diff also remain unavailable because `.git` is exposed as an empty directory. These limits do not prevent verification of the documentation-only `SECURITY-001` criteria; `SECURITY-001` is `verified`, while authentication implementation is explicitly tracked as planned `SECURITY-002`.

## 2026-08-28 — TESTING-001, SECURITY-002 readiness

- Added a separate `florabase-integration` Compose workflow using PostgreSQL 18.6, the real Alembic chain, no published database port, and tmpfs-backed disposable state. One database is shared per run; each test receives a SQLAlchemy transaction that is rolled back.
- Destructive setup now requires both `FLORABASE_ENVIRONMENT=test` and `FLORABASE_DATABASE_DISPOSABLE=true` before migrations. Unit and runtime checks proved a normal development configuration is rejected without connecting to or changing its database.
- `make test-integration` passed twice from fresh databases (2 tests each run), confirmed PostgreSQL major version 18, revision `20260827_0001`, infrastructure metadata, API database readiness, transaction isolation, cleanup, and repeatability. Before and after the runs, the normal `florabase` database remained at revision `20260827_0001` with `schema_initialized=true` and no integration isolation probe; no integration containers remained.
- Compose rendering, shell syntax, Ruff formatting/lint, strict mypy, normal backend/frontend tests, TypeScript/ESLint/Prettier/build, and generated API drift were included in the final verification. No dependency was added for `TESTING-001`; it reuses Compose, pytest, SQLAlchemy, psycopg, Alembic, and PostgreSQL.
- Gave development Compose images distinct names after verification exposed that a production `make build` could otherwise replace the cached development image and make the next check lose its tools. A full `make check` passed immediately after the production build with the separated images.
- Reviewed ADR 0005 for `SECURITY-002`: use `pwdlib[argon2]` for password hashing/verification, Python security primitives for random tokens/digests/comparison, Starlette cookies, SQLAlchemy/PostgreSQL persistence and atomic throttling, and minimal FastAPI dependencies for Florabase session/CSRF/origin policy. No custom cryptography, session framework, rate-limit framework, Redis, or additional orchestration is justified.
- `TESTING-001` is `verified`; its acceptance criteria and dependency are satisfied. `SECURITY-002` is ready to start with the implementation boundary recorded in `docs/security.md`.

## 2026-08-28 — DOMAIN-001

- Defined what was then called Species as a stable, collection-local botanical identification with one required scientific name and an optional separate cultivar qualifier; documented create-first, find-before-create, correction, reconciliation, infraspecific, and cultivar workflows. The canonical aggregate was subsequently renamed BotanicalIdentity in the terminology decision below.
- Fixed the minimum migration contract at six fields: UUIDv7 `id`, normalized `scientific_name`, optional `cultivar_name` and `common_name`, and UTC `created_at`/`updated_at`. Parsed taxonomy, family, author citation, synonyms, external identifiers, hierarchy, and all material/inventory entities remain deferred.
- Made canonical display, mechanical normalization, case-insensitive composite uniqueness, API validation/conflict/not-found semantics, rename behavior, and future survivor-based reconciliation explicit. Future SeedLot and Plant records reference `species.id` (the then-proposed name); they do not belong to or duplicate this aggregate contract.
- Documentation formatting passed with the repository's Prettier executable using the bundled Node.js runtime; JSON parsing plus feature status, dependency, acceptance-criteria, and contract-section assertions passed. The existing non-destructive `make format-check` baseline could not use Compose because this environment denied access to `/var/run/docker.sock`. No application, schema, generated API, authentication, or infrastructure file changed.
- All three `DOMAIN-001` acceptance criteria are satisfied by the reviewed contract, so `DOMAIN-001` is `verified`. `DATABASE-001` is ready for its one-table Alembic increment; `SECURITY-002` remains required before `BACKEND-001` and was not started.

## 2026-08-28 — DOMAIN-001 terminology and scope decision

- Renamed the canonical aggregate from Species to BotanicalIdentity because it may represent a species, infraspecific taxon, hybrid or other valid botanical-name expression, or a taxon qualified by a cultivar; Species is too narrow, while Taxon cannot include the cultivar-qualified aggregate meaning.
- Kept the verified six-field contract unchanged. Clarified that `scientific_name` is the operator's current botanical taxon name, `cultivar_name` is a separate non-taxon qualifier, `common_name` is optional display metadata, and Florabase is not a taxonomic authority.
- Resolved the ADR 0005 scope requirement: BotanicalIdentity is installation-wide shared classification/reference data without `user_id`; future collection records define their own ownership, and future mutations still require authenticated authorization.
- Established future naming as aggregate `BotanicalIdentity`, SQL table `botanical_identities`, foreign key `botanical_identity_id`, and REST resource `/api/v1/botanical-identities`. Future SeedLot, Plant, and other appropriate collection records reference the UUID rather than duplicating scientific/cultivar identity.
- Exact checks passed: Prettier over the four changed documentation files; JSON parsing plus feature status/dependency assertions; and assertions for the exact six-field contract, shared-scope/authorization decision, aggregate rationale, SQL table, foreign key, and REST path. The repository `make format-check` baseline was attempted but Docker socket access was denied before its first check.
- No migration, table, endpoint, generated API, frontend, authentication, taxonomy hierarchy, parser, or collection entity was created. `DOMAIN-001` remains `verified`; `DATABASE-001` and `SECURITY-002` were not started.
- The terminology, scope, persistence naming, and API naming decisions are now explicit enough for product brainstorming before `DATABASE-001` begins.

## 2026-08-28 — Product roadmap and collection backlog

- Converted the approved product workflows into an MVP, Phase 2, and Phase 3 roadmap while keeping `BotanicalIdentity` at its verified six-field boundary. Added 40 planned items covering BotanicalProfile, Supplier, Location, SeedLot, Sowing, Plant/PlantGroup, lineage, history, attachments, later propagation material, analysis, and integrations; preserved every existing feature, dependency, priority, status, and verified claim.
- Recorded partial-data, unknown-precision, historical-retention, provenance, and operator-authorship principles. Product contracts preserve a known date value with its declared precision and optional exact or approximate count or weight, but deliberately defer persistence representation and unit design.
- Kept BotanicalProfile knowledge separate from collection observations; made TuberLot and CuttingLot parallel Phase 2 workflows rather than SeedLot variants; and based lineage on explicit SeedLot-to-Sowing-to-Plant/PlantGroup and parent-Plant-to-descendant-SeedLot relationships rather than a generic graph or material hierarchy.
- Recommended `DATABASE-001`, then `SECURITY-002`, `BACKEND-001`, and `FRONTEND-001` before the first collection-material slice. No migration, model, endpoint, authentication, UI, dependency, external research, scheduler, or framework abstraction was added, and neither `DATABASE-001` nor `SECURITY-002` was started.
- Exact checks passed: Prettier over the changed Markdown and JSON files; JSON parsing plus unique-ID, nonempty-criteria, allowed-status, priority, existing-dependency, acyclic-graph, preserved-existing-status, and newly-planned-status assertions; and roadmap section, principle, phase mapping, capability-boundary, and deliberately-deferred assertions. A broader documentation baseline identified a pre-existing Prettier issue in `docs/security.md`, which this planning task did not modify.
- Git status, history, and diff remained unavailable because this task environment exposed an empty `.git` directory. The dependency graph is coherent enough to resume implementation with the single recommended next item, `DATABASE-001`, in a later task.

## 2026-08-28 — DATABASE-001

- Added the single `botanical_identities` table at Alembic revision `20260828_0002` with the verified six fields only: application-generated UUIDv7 `id`, bounded scientific/cultivar/common names, and explicit application-generated UTC `created_at`/`updated_at` values persisted as PostgreSQL `timestamptz`. No ownership, soft-delete, taxonomy, collection, API, or frontend fields/tables were introduced.
- Added a minimal typed SQLAlchemy mapping and shared declarative metadata for Alembic. Named PostgreSQL checks reject null/blank required names, normalized-empty optional names, unnormalized whitespace, control characters, surrounding cultivar quotes, and overlong text; normalization itself remains the later backend input boundary.
- PostgreSQL authoritatively enforces case-insensitive `(scientific_name, cultivar_name)` identity through `uq_botanical_identities_name_cultivar_ci`, an expression index using `lower(...)` and `NULLS NOT DISTINCT`. Integration tests proved conflicts for both null and present cultivars and allowed qualified and unqualified identities to coexist.
- Exact checks passed: backend Ruff format/lint and strict mypy; backend unit tests (13 passed, 98% coverage); `make test-integration` (26 passed) against fresh PostgreSQL 18.6; offline Alembic SQL rendering/review; updated-document Prettier/JSON validation; and final `make check`, including frontend format/lint/typecheck/tests and generated API drift. The integration suite exercised head creation, downgrade to `20260827_0001`, re-upgrade, a second downgrade, and final re-upgrade, verified native types/constraints/indexes, UUIDv7/UTC round trips, valid/invalid rows, optional fields, duplicate behavior, and the absence of unrelated botanical tables.
- All three acceptance criteria were exercised, so `DATABASE-001` is `verified`. `SECURITY-002` is the recommended next item and was not started. Git status/history/diff remain unavailable because this task environment exposes an empty `.git` directory.

## 2026-08-28 — SECURITY-002

- Added the focused local-authentication capability and Alembic revision `20260828_0003` with real
  UUIDv7 owner, server-side session, and expiring login-throttle records. PostgreSQL stores Argon2id
  password encodings plus SHA-256 digests of independent 32-byte session/CSRF tokens; plaintext
  passwords and raw bearer credentials are never persisted.
- Implemented the guarded one-shot owner CLI, JSON login, secure production and explicit loopback
  development cookies, authenticated-actor and owner-authorization dependencies, non-cacheable
  session metadata, CSRF/Origin enforcement, logout, bounded idle touches, idle/absolute expiry,
  per-session and user-wide revocation, transparent hash upgrade, unknown-user dummy verification,
  and PostgreSQL-serialized exponential login backoff. No login UI, botanical endpoint, JWT,
  Redis, recovery, MFA, external identity, or multi-user enrollment was added.
- Locked `pwdlib[argon2]` 0.3.1 and its exact Argon2 runtime dependencies. The selected Argon2id
  parameters (65,536 KiB, 3 iterations, parallelism 1) produced five supported-container samples
  of 182.5, 176.2, 177.5, 179.0, and 175.5 ms (177.5 ms median).
- Exact checks passed: backend Ruff format/lint and strict mypy; backend unit tests (33 passed,
  95.11% coverage); disposable PostgreSQL 18.6 integration tests (43 passed) including real CLI,
  concurrency, redaction, cookie/origin/CSRF/throttle/session policy, and
  `20260828_0002 -> 20260828_0003 -> downgrade -> re-upgrade` while preserving
  `botanical_identities`; frontend Prettier, ESLint, strict TypeScript, Vitest (2 passed), and Vite
  build; regenerated OpenAPI/TypeScript declarations and drift check; production/development
  Compose rendering; shell syntax; offline Alembic SQL review; production backend/frontend image
  build; and final `make check`.
- The final audit found no command-line/environment password path, plaintext password storage, raw
  session/CSRF persistence, credential logging, UUID bearer token, weak cookie path, production
  development-cookie path, forwarded-header trust, session-fixation path, revocation/expiry bypass,
  Origin/CSRF bypass, account-existence disclosure, or permanent throttle state. All four existing
  acceptance criteria are exercised, so `SECURITY-002` is `verified`. Git status/history/diff remain
  unavailable because this task environment exposes an empty `.git` directory.

## 2026-08-28 — BACKEND-001, browser-auth backlog correction

- Added only the protected BotanicalIdentity create/read slice at
  `/api/v1/botanical-identities`: owner-authorized create requires the existing authenticated
  session, exact Origin, and session-bound CSRF token; authenticated read-by-UUID remains a safe
  GET without CSRF. No list, update, delete, migration, ownership field, derived-label persistence,
  generic CRUD abstraction, or frontend UI was added.
- Create accepts only `scientific_name`, optional `cultivar_name`, and optional `common_name`.
  BotanicalIdentity-specific Pydantic validators trim and collapse whitespace, remove one matching
  cultivar quote pair, map optional blanks to null, reject remaining control characters and
  overlong values, and preserve spelling/case. Responses contain the verified six persisted fields
  plus the derived Unicode-quoted canonical display label; creation returns HTTP 201 and `Location`.
- Added a friendly case-insensitive duplicate pre-check and retained PostgreSQL's named unique index
  as the race-safe boundary. The insert flush runs in a savepoint so the request transaction remains
  usable after the exact unique violation; friendly and authoritative conflicts map to the same
  stable HTTP 409 shape with the existing UUID when available, while unrelated integrity failures
  are re-raised.
- Added focused normalization/response and transaction-boundary unit tests plus 13 real-ASGI,
  PostgreSQL-backed API integration cases covering UUIDv7/UTC creation, optional values, validation,
  read-only/unknown fields, duplicate combinations, persistence constraints, 401/403 security,
  404 versus malformed-UUID validation, and authenticated GET without CSRF. Backend unit tests pass
  (38 tests, 90.90% coverage), disposable PostgreSQL 18.6 integration tests pass (56 tests), strict
  mypy and Ruff pass, OpenAPI drift passes, TypeScript compilation passes, frontend tests pass
  (2 tests), and final `make check` passes.
- Regenerated `backend/openapi.json` and `frontend/src/api/schema.d.ts` with stable
  `createBotanicalIdentity` and `getBotanicalIdentity` operations and documented create/read
  responses. Added planned `FRONTEND-002` for accessible owner login, session restoration, safe CSRF
  recovery after reload, logout, generic failures, and the existing HttpOnly/no-browser-storage
  boundary; `FRONTEND-001` now depends on both `BACKEND-001` and `FRONTEND-002`.
- All three existing `BACKEND-001` acceptance criteria were executed, so it is `verified`.
  `FRONTEND-002` is the recommended next capability, followed by `FRONTEND-001`. Git status,
  history, and diff remain unavailable because this task environment exposes an unusable `.git`
  directory.

## 2026-08-29 — FRONTEND-002

- Added `POST /api/v1/auth/csrf`, an authenticated exact-Origin CSRF recovery operation that
  replaces only the current session's stored CSRF digest, returns the new raw token once with
  `Cache-Control: no-store`, invalidates the old token, and leaves the session identifier/bearer
  unchanged. No migration, refresh token, JWT, new table, or persistent browser token was added.
- Added a small generated-contract-typed frontend request boundary and React context with explicit
  restoring, unauthenticated, submitting-login, authenticated, logging-out, recovery-failed, and
  logout-failed states. Protected shell content remains hidden until session and CSRF restoration
  both succeed; network failures remain distinct from logout or bad credentials.
- Added the accessible owner login and logout flow with semantic labels/form submission,
  autocomplete, disabled/busy handling, focused live failure feedback, generic 401 and 429
  messages, `Retry-After` display, password clearing, and safe expired-session/network-failure
  logout behavior. Actor and CSRF data remain in React memory only; the session bearer remains in
  the backend-issued HttpOnly cookie.
- Added backend unit and real-ASGI/PostgreSQL coverage for recovery, exact Origin, 401/403,
  old-token invalidation, new-token validation, unchanged session digest, non-caching, and raw-token
  redaction; added 12 frontend tests for restoration, login, throttling, failures, keyboard and
  label behavior, storage audit, and logout outcomes.
- Exact checks passed: backend Ruff and strict mypy; backend unit tests (38 passed, 91.04%
  coverage); disposable PostgreSQL 18.6 integration tests (59 passed); regenerated OpenAPI and
  TypeScript declarations; frontend Prettier, ESLint, strict TypeScript, Vitest (12 passed), and
  production Vite build; API drift and final `make check`. No dependency was added.
- All three existing `FRONTEND-002` acceptance criteria are exercised, so it is `verified`.
  `FRONTEND-001` is now ready and was not started. Git status/history/diff remain unavailable
  because this workspace exposes an unusable `.git` directory.

## 2026-08-29 — FRONTEND-001

- Replaced the authenticated foundation placeholder with the first BotanicalIdentity workflow while
  preserving the verified restoration, login, in-memory CSRF, logout, and HttpOnly session boundary.
  The restrained application shell now presents owner identity and logout, a three-field create form,
  a truthful no-selection state, the current created or loaded identity, and a secondary backend status.
- Added generated-contract-typed create and read requests only. Creation sends the existing in-memory
  CSRF token; read-by-UUID is used only to open a known duplicate and sends no CSRF. HTTP 401 returns to
  the existing login boundary, 403 does not trigger a stale-token retry, and no browser token storage or
  new API model was introduced.
- Added explicit submitting, loading-existing, success, backend-validation, duplicate, forbidden,
  session-expiry, server/network-failure, and empty states. Duplicate conflicts expose a keyboard-
  accessible action when `existing_id` is available; returned `display_label` remains canonical and the
  UUID is secondary reference information.
- Added eight focused frontend tests alongside the 12 auth regressions, exercising authenticated
  composition and protected-content hiding, labelled/required/max-length fields, truthful empty copy,
  keyboard creation, pending-submit guarding, response rendering, accessible focused validation,
  duplicate-to-GET navigation, GET without CSRF, differentiated failure handling, no stale-CSRF retry,
  and authentication-expiry handoff.
- Exact checks passed: local frontend Prettier, ESLint, strict TypeScript, Vitest (20 tests), and Vite
  production build; generated TypeScript declarations regenerated identically from committed OpenAPI;
  and final Docker-based `make check`, including backend Ruff formatting/lint, strict mypy, 38 backend
  unit tests at 91.04% coverage, all frontend checks and 20 tests, and full backend OpenAPI/frontend type
  drift verification. No dependency, backend behavior, endpoint, migration, or later capability was
  added.
- All three existing `FRONTEND-001` acceptance criteria were exercised, so `FRONTEND-001` is `verified`.
  Git status/history/diff remain unavailable because this workspace exposes an unusable empty `.git`
  directory. `PROFILE-001` is the recommended next capability and was not started.

## 2026-08-29 — PROFILE-001

- Defined BotanicalProfile as the current operator-authored general reference knowledge for exactly
  one BotanicalIdentity, with at most one current manual profile per identity and no requirement for
  every BotanicalIdentity to have one. Persistence identity and relational representation remain
  deferred to `PROFILE-002`.
- Resolved ADR 0005 scope before schema creation: BotanicalProfile is deliberately installation-wide
  shared reference data without `user_id`; future mutations still require authentication and explicit
  authorization. It is not a private collection observation.
- Selected five individually optional plain-text sections: `description`, `origin_distribution`,
  `cultivation`, `uses`, and `warnings`. A profile exists only when at least one section contains
  meaningful text; blank content is absent, and clearing the last populated section returns the
  identity to having no profile. A generic `notes` field and premature structured fact fields remain
  excluded.
- Kept general origin/distribution distinct from SeedLot provenance and general cultivation guidance
  distinct from conditions and outcomes observed in this collection. Documented informational warning
  limits, safe plain-text behavior, current-text editing semantics, canonical BotanicalIdentity display,
  and incomplete-friendly future UI guidance.
- Established a separate source-scoped future enrichment boundary: source identity is retained,
  retrieval metadata and external identifiers are added only when useful for a selected source,
  conflicts remain distinguishable or reviewable, and source-derived content never silently overwrites
  identifiable operator-authored text. No enrichment field, integration, or background capability was
  added.
- Baseline Prettier passed over the four relevant documentation/backlog files; JSON parsing and unique
  feature-ID, nonempty-criteria, allowed-status/priority, existing-dependency, acyclic-graph, and original
  `PROFILE-001` assertions passed. After formatting the domain contract, focused assertions passed for
  relationship/cardinality, shared scope, all five optional sections, nonempty-profile behavior,
  collection boundaries, authorship/enrichment, text/safety behavior, deferred structure, editing/UI
  guidance, and deferred persistence. Final formatting and backlog validation are recorded by this
  task's completion checks.
- All three unchanged `PROFILE-001` acceptance criteria are explicitly supported, so `PROFILE-001` is
  `verified`. `PROFILE-002` is contract-ready but remains `planned` and was not started. Git
  status/history/diff remain unavailable because this workspace exposes an unusable empty `.git`
  directory.

## 2026-08-30 — PROFILE-002

- Added one focused Alembic migration for `botanical_profiles`, using
  `botanical_identity_id` as both the primary key and cascading BotanicalIdentity foreign key. The
  table contains only the five verified nullable plain-text sections; PostgreSQL enforces the
  parent, one-profile cardinality, 20,000-character bounds, trimmed/nonempty stored values,
  supported controls, and at least one populated section.
- Added authenticated nested `GET` and owner-authorized, exact-Origin, session-CSRF-protected
  idempotent `PUT` operations. `PUT` creates with HTTP 201, fully replaces with HTTP 200, and removes
  the row with HTTP 204 when the last populated section is cleared; an empty first replacement and
  nonexistent parent have stable 422 and 404 responses. A PostgreSQL upsert deliberately converges
  concurrent first writes without misclassifying unrelated integrity failures.
- Normalization trims meaningless outer whitespace, maps blank sections to null, normalizes CRLF to
  LF, preserves ordinary Unicode, punctuation, capitalization, paragraphs, internal whitespace and
  useful line breaks, and rejects unsupported controls. Responses contain only the parent UUID and
  the five sections; no profile UUID, ownership, timestamps, sources, enrichment, structured facts,
  history, or collection observations were added.
- Integrated a generated-contract-typed Botanical profile panel into the selected BotanicalIdentity
  detail. It explicitly labels content as general reference knowledge, separates it from observations
  about particular collection material, describes cultivation as general guidance rather than
  recorded measurements, and provides semantic multiline labels, loading/no-profile/editing/saving/
  saved/validation/authorization/session-expiry/network states with duplicate-submit prevention and
  accessible announcements.
- Exact checks passed: backend Ruff formatting/lint and strict mypy; 49 backend unit tests at 92.17%
  coverage; disposable PostgreSQL 18.6 integration tests (65 passed), including migration
  upgrade/downgrade/re-upgrade, constraints, security, final-section clearing, and a two-session
  concurrent first-write race; regenerated OpenAPI and TypeScript declarations plus drift check;
  frontend Prettier, ESLint, strict TypeScript, Vitest (27 passed), and the production Vite build;
  and final Docker-based `make check`.
- All three unchanged `PROFILE-002` acceptance criteria were exercised, so `PROFILE-002` is
  `verified`. Git status/history/diff remain unavailable because this workspace exposes an unusable
  empty `.git` directory.

## 2026-08-30 — IDENTITY-001

- Added the authenticated, non-mutating `GET /api/v1/botanical-identities` directory operation,
  reusing `BotanicalIdentityResponse` and its backend-derived `display_label`. PostgreSQL returns
  the complete lightweight collection ordered case-insensitively by scientific name, then cultivar
  with the unqualified identity first, and finally UUID. No CSRF or Origin is required for this safe
  read; create security remains unchanged.
- Reworked the authenticated BotanicalIdentity screen into a responsive directory/detail workflow
  with a one-entry navigation shell, labelled client-side substring filter, global empty and
  zero-filter-match states, semantic selection buttons, selected details, and the existing
  `BotanicalProfilePanel`. Creation authoritatively refetches and selects the new record; duplicate
  conflicts select a loaded match or retain the existing safe GET fallback. No router, cache,
  server-side search, pagination framework, migration, or runtime dependency was added.
- Retained complete-list delivery for the expected first-release single-operator scale and documented
  that server-side pagination can follow observed collection growth. The PROFILE-002 rendering audit
  confirmed saved multiline text already uses `white-space: pre-wrap`; no profile change was needed.
- Exact checks passed: backend Ruff formatting/lint, strict mypy, and 49 unit tests at 91.87%
  coverage; disposable PostgreSQL 18.6 integration tests (67 passed), including the empty/read-only/
  authentication contract and deterministic qualified/unqualified ordering; frontend Prettier,
  ESLint, strict TypeScript, 32 Vitest tests, and Vite production build; regenerated OpenAPI and
  TypeScript declarations, API drift, and final `make check`. No dependency or migration was added.
- All three unchanged `IDENTITY-001` acceptance criteria are exercised, so `IDENTITY-001` is
  `verified`. `SUPPLIER-001` was not started and is now the next planned P1 capability. Git status,
  history, and diff remain unavailable because this workspace exposes an unusable empty `.git`
  directory.
