# BULK-001 — implementation handoff

Operator UAT: **passed**. Luna's independent review and canonical verification are complete. The
reviewed commit, protected delivery and conservative finish remain. The source began unstaged and
uncommitted at the stated implementation base.

## Worktree

- Path: `/home/alessandro/.codex/worktrees/b647/florabase`.
- Branch: `feat/bulk-001-location-moves`, initialized with `make feature-init`.
- Base and unchanged HEAD: `9ccbf30ac167a3c11c5f51fd4c7ae9531e4911f8` (VIEW-001 / PR #73).
- Primary checkout: `/home/alessandro/Desktop/github/florabase`; its source remains untouched.
- Alembic code/database head: `20261006_0034`. No migration or selection/batch persistence.

## Domain support and side effects

The complete audited matrix, including reasons and authoritative paths, is in
[bulk-operations.md](bulk-operations.md#audited-domain-matrix).

| Kind                                                                                       | Supported                     | Owning move path / reason                                                                                                                                           |
| ------------------------------------------------------------------------------------------ | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SeedLot                                                                                    | Active only                   | `seed_lots.service.assign_location`, shared with `update_seed_lot`; scope validation and timestamp only; preserves origin, producer lineage, quantity and lifecycle |
| Sowing                                                                                     | Active only                   | `sowings.service.assign_location`, shared with `update_sowing`; scope validation and timestamp only; preserves source, germination, quantity and lifecycle          |
| Plant                                                                                      | Active only                   | `events.service.create_event(kind=movement)`; one authoritative Movement Event and current-location/timestamp update                                                |
| PlantGroup                                                                                 | Active only                   | Same Movement Event path for the concrete group; preserves group quantity, extraction and lineage                                                                   |
| HarvestMaterialInventory / Stored material                                                 | Active tracked inventory only | `harvests.inventory_service.assign_location`, shared with ordinary `correct`; owner-first locking, unchanged balance/state/correction_version/dispositions          |
| Inactive collection records, reversed/transferred/reintegrated records, depleted inventory | No                            | Bulk movement never reactivates or rewrites lifecycle/history; ordinary correction paths remain available                                                           |
| Historical Harvest / HarvestItem                                                           | No                            | Historical collected amounts/source context are not current physical stock; Stored material is separately tracked                                                   |
| Event                                                                                      | No                            | Historical destination is evidence; correction/deletion does not replay current state                                                                               |
| MediaAsset / attachment                                                                    | No                            | Media associations are not current collection Location assignments                                                                                                  |
| BotanicalIdentity / Supplier                                                               | No                            | Reference context, not movable physical collection records                                                                                                          |
| GeographicPlace / ProvenanceSite                                                           | No                            | Geographic provenance never implies a physical collection Location                                                                                                  |

Movement Events have `occurred_on = null`: the current service permits an unknown occurrence date,
and the bulk operation never invents precision from its execution timestamp. No-op rows create no
Event and retain their timestamp. Active stored inventory may move even when its historical source
Plant is inactive. No changes to dates, origin, provenance, germination, inventory balance, collected
amount, conversion/disposition history, or lifecycle are inferred.

## Selection and UI

Seeds, Sowings, unified Plants/Groups, and Harvests → Stored material offer an opt-in **Select**.
Normal Quick Preview/detail behavior remains available outside that mode. Named checkboxes and
visible checked/outlined rows accompany a live selected count. Normal **Select** shares the utility
row with conditional Save view and Saved views. Active selection shows a compact contextual bar
immediately before result metadata/list: prominent count, one primary **Move to location**, and
lightweight **Select visible**, **Clear selection**, **Done** actions. Done restores focus to Select.

Selection contains exact typed `(kind, UUID)` references, with a hard maximum of **100** in both
client and server. These directories currently render their full locally filtered lists. Select
visible acts only on those rendered eligible rows; above 100 it is disabled with an explanation,
without truncation or query expansion. Individual selection remains bounded. Inactive rows cannot
be selected. The Plant and PlantGroup identity stays concrete, including equal UUIDs across kinds.

Search, filter, visible membership/eligibility, surface/detail/task navigation, Back/Forward and
Saved View opening reset selection. Reopening an identical Saved View also resets it. Future paging
must participate in that same boundary. Selection/target/preview never enter URL, storage or Saved
View state. Stored-material conversion is hidden while selecting; historical Harvest has no bulk
controls.

Choose an existing compatible Location with the normal picker, request Preview, inspect every
old/new path and move/no-op/conflict status, then explicitly Apply. Target changes and apply failures
invalidate the preview and disable Apply until a successful current server preview permits it.
The moderately wider Move dialog reserves more vertical room for the existing searchable typed
Location chooser. Its native TaskDialog traps focus; Cancel, Escape and a direct backdrop click
close without applying and return focus to the exact Move trigger. Inside clicks retain the dialog.
Apply cannot be dismissed while its outcome is pending. Successful apply closes the dialog, clears selection and
Quick Preview, refreshes directory data, retains normal filters/URL and reports moved/no-op counts.
Network/domain failures retain a recoverable selection. A 403 session-protection refusal requires
reload rather than repeatedly submitting the same invalid token.

## API, atomicity and security

- `POST /api/v1/bulk/location/preview`: exact bounded `records: [{kind, id}]` and
  `target_location_id`.
- `POST /api/v1/bulk/location/apply`: those exact references with each
  `expected_updated_at`, plus the target ID and `expected_target_updated_at` returned by Preview.
- Existing authenticated owner authorization, CSRF and exact Origin enforcement apply to both.
  Kinds are a closed literal set; UUIDs and timezone-aware preconditions are validated. Unknown
  fields, duplicates, empty and oversized selections are rejected with structured 422 validation.
- Preview returns human labels/types, current/target paths and versions, every selected reference,
  exact counts and `can_apply`. Missing/inactive/scope-ineligible rows are conflicts, never omitted.
- Apply takes the existing lineage lock, Harvest-owner locks for inventory, typed rows in fixed
  kind/UUID order, and the target lock; it refreshes all records and validates all versions/eligibility
  before mutation. All selected rows, including no-ops, participate in stale checks.
- One transaction, one route commit; domain/constraint/concurrency failure rolls everything back,
  including an earlier inserted Movement Event. Deadlock/serialization errors are safe 409 conflicts.
- Missing target: 404 `target_location_not_found`; apply: 409 `selection_conflict`, `stale_preview`,
  `all_unchanged`, owning domain error or `concurrent_change`. Bounded affected-row details name
  conflicts. All-no-op Apply is disabled/refused; mixed batches move only changed rows.
- No arbitrary table, action, field map, filter expansion, public endpoint, generic job, queue,
  selection persistence or unified history is introduced.

## Navigation and page categories

| Macroarea / page eyebrow | Existing destinations in order          |
| ------------------------ | --------------------------------------- |
| Overview                 | Dashboard                               |
| Collection               | Seeds, Sowings, Plants, Harvests, Media |
| Activity                 | Events                                  |
| Places                   | Locations, Geography, Provenance map    |
| Reference                | Botanical identities, Suppliers         |
| Tools                    | Import / Export, Labels                 |

Desktop retains its bounded scrollable sidebar. Mobile retains Home/Seeds/Sowings/Plants and More;
More follows the same remaining destination order. Stored material belongs to Collection/Harvests.
All route identities, active `aria-current`, actual titles/descriptions, and detail/form captions
are retained. Events remain recorded occurrences, not future tasks.

## Performance

Lookup uses one joined query per selected kind and one Location-tree read, avoiding redundant
per-record origin/provenance fetching. Inventory label context uses a joined Harvest item/label.
A real PostgreSQL query regression with **100 SeedLots** asserts **3 preview statements** and
**at most 7 apply statements**. Inventory adds one owner-lock query. Plant/Group writes deliberately
retain bounded per-record Event service calls for correctness. No caching infrastructure.

## Independent review and canonical verification

The independent review found no production or workflow defect. It confirmed the finite typed
support matrix, authoritative assignment and Movement Event semantics, bounded explicit-ID requests,
server-side stale checks and atomic rollback, owner/Origin/CSRF protections, query bounds, transient
Saved View interaction, keyboard access, responsive behavior and current directory counts.

The first canonical run exposed a stale Sowing lineage test double: `_require_references` now returns
the reference tuple needed for Location assignment, while the test stub returned `None`. The test
double was updated to return the helper's shape; production behavior and the lineage-cycle assertion
were unchanged. The focused lineage suite passed (**4 tests**).

`make feature-verify` then passed on the complete reviewed tree: **735 backend tests** at **90.54%**
coverage, **462 frontend tests across 46 files**, **582 PostgreSQL integration tests**, API drift,
Ruff, Prettier, zero-warning ESLint, strict mypy (**274 files**), strict TypeScript, production
backend/frontend builds, migration-cycle checks (no Alembic revisions), whitespace checks and the
working-tree verification receipt. The feature graph validated **92 features**. No migration is
included; Alembic head remains `20261006_0034`.

Backend focused commands (development image, test configuration):

```sh
pytest --no-cov tests/test_bulk_location.py tests/test_location.py tests/test_seed_lot.py tests/test_sowing.py tests/test_harvest_inventory.py tests/test_saved_views.py tests/test_saved_views_service.py
alembic upgrade head
pytest --no-cov -m integration tests/integration/test_bulk_location.py tests/integration/test_location_api.py tests/integration/test_seed_lot_api.py tests/integration/test_sowing_api.py tests/integration/test_plant_api.py tests/integration/test_event_api.py tests/integration/test_harvest_inventory.py tests/integration/test_saved_views.py
ruff format --check --no-cache src tests
ruff check --no-cache src tests
mypy --cache-dir /tmp/bulk-mypy
python scripts/export_openapi.py --check
```

The PostgreSQL command ran through `compose.integration.yaml` with a temporary focused command
override and fresh unique project `florabase-integration-bulk-d24cbbcc8ac3`, whose fixture resources
were cleaned after completion. Frontend Vitest ran the two bulk files, SeedLotScreen, SowingScreen,
PlantScreen, HarvestScreen, StoredMaterial, SavedViews, state and App suites with `--configLoader
runner`. Static checks used whole-frontend Prettier and ESLint, `tsc -b`, Vite build and regenerated
OpenAPI TypeScript comparison. Backend production build used the existing Dockerfile's runtime
target. Two final Stored material selection tests were rechecked after hiding its competing
single-record conversion action; both passed.

Integration covers mixed five-kind transactions, current projections, unchanged unrelated rows,
Movement Events, inventory balance/version preservation, every supported kind, stale location/notes/
lifecycle, deletion, target deletion/scope/version, repeated Apply, rollback after an Event insertion,
auth/Origin/CSRF, and the 100-row query bound. No migration cycle was necessary.

Frontend covers the selection bound, concrete Plant/Group kinds, eligibility, filter/visible/Saved
View reset, preview/no-ops/conflicts, explicit Apply, directory refresh/filter retention, failure
recovery, cancellation/focus, Location retry and historical Harvest exclusion. Shell tests exercise
all fourteen destinations, unchanged hashes/active state, macroarea order and page eyebrows.

## UAT Preview and browser review

- URL: `http://localhost:15174`.
- Synthetic UAT-only credentials: **preview / preview**.
- The old c5e8 owner was retired using its supported guarded `make uat-preview-remove` operation.
  b647 used `make uat-preview-up`, `make uat-preview-seed`, then status. Fixture **v1** and its
  **31 baseline records** are retained; no fixture version/code change. DEV, Stable Preview,
  Feature Review, production and real collection data were not changed.
- Browser checks cover **1440×844, 1024×844, 390×844**: Seeds, mixed Plants/Groups, Sowings and
  Stored material selection/picker/preview, no-op state, toolbar wrapping, long labels/paths,
  page/dialog horizontal bounds, visible actions, keyboard focus/trap/Escape return, macroarea
  headers and mobile More. Final mobile Sowing row recheck confirmed readable labels/progress and
  no horizontal overflow after accommodating its selection checkbox.
- Synthetic browser exercises moved Aloe SeedLot to Greenhouse bench; Basil Plant and Basil group
  to Indoor seed shelf; Nursery aloe Plant to Indoor seed shelf. These are normal BULK-001 moves;
  quantities/lifecycle remain unchanged. Three undated Movement Events reflect the Plant/Group
  moves. The Plant Events tab visibly retains its Movement with **Date unknown** and the exact
  destination. Sowings and inventory remain ready for operator moves.
- Fixture v1 has no tracked inventory initially. Through normal Harvest UI, explicitly tracked its
  Dried basil seeds as **Unknown quantity**, at Indoor seed shelf, without inferring a remainder
  from the historical **30 items collected**. The historical amount remains 30. One active inventory
  is ready; its Greenhouse preview passed at all three sizes without applying it. Fixture seeding
  code/version and the 31-record baseline manifest are unchanged.
- Saved a synthetic **BULK UAT — Basil seeds** view using normal UI. Selected its one visible row,
  reopened the identical view and verified selection mode/checkboxes disappeared while `q=Basil`
  remained. Search changes also cleared selection. This view is ready for the operator scenario.
- Final supported `make uat-preview-status` reports frontend/backend/database healthy, b647 source,
  unchanged HEAD, dirty feature source, database/code head `20261006_0034`, fixture v1 and existing
  edits preserved.
- Browser stale testing with two tabs encountered existing CSRF token rotation (403), which refused
  that request before domain mutation. A direct domain-service fixture mutation to create a stale
  preview was rejected by automatic approval review because it was outside the bulk flow and
  considered contrary to the fixture boundary; it was not executed. No approval bypass was used.
  Stale 409/atomic rollback is proven by PostgreSQL tests and frontend feedback tests; this exact
  browser concurrency scenario remains an operator review scenario, not a claimed browser pass.

Suggested operator scenarios:

1. Seeds: select all three and target Greenhouse bench; Preview shows one already there and two
   moves. Apply and confirm search/URL remains and quantity is unchanged.
2. Plants: select a Plant plus group; preview another Location, Apply, then inspect each Events tab
   for its own undated Movement Event. Verify quantities/lineage and the unselected record.
3. Sowings: select Spring basil tray and move to an existing Location; retain germination and seed
   usage values. Stored material: move tracked seed stock without changing collected/remaining
   amounts, dispositions or conversion state; historical Harvest offers no bulk move.
4. Saved Views: open **BULK UAT — Basil seeds**, select rows, change view/search/type; selection must clear.
   Reopen the identical view and confirm no selection was saved. Dialog Cancel/Escape and keyboard Tab
   should return to the exact invoking action.
5. Refusal: preview multiple records, change one through an independently authenticated ordinary
   bulk flow, then Apply the old preview; expect no batch changes and a named stale conflict.
   If session CSRF has rotated, reload first; that protection refusal is a separate auth boundary.
6. Check all sidebar/More destinations and macrocategory eyebrows at the three specified sizes.

## Operator UAT refinements — 2026-10-07

The refinement is frontend/navigation/presentation only. The original bulk API, locking,
preconditions, atomic refusal, domain side effects and migration head are unchanged.

- **Selection:** Select now sits in the Saved Views utility row, including conditional Save view.
  The active bar keeps the count prominent and Move to location primary; Select visible, Clear
  selection and Done are lightweight, visible controls that wrap on mobile. Done returns focus to
  Select. Selection remains independent of Saved Views and resets at the existing boundaries.
- **Move dialog:** desktop width is capped at 48rem, with a 34rem preferred minimum height and a
  viewport-bounded maximum. The existing typed/searchable Location menu occupies normal flow and
  allows up to 22rem / 42dvh before internal scrolling. This reserves useful chooser space while
  retaining mobile bounds. Direct backdrop, Cancel and Escape close safely and restore the exact
  Move trigger; clicks inside retain the dialog. Backdrop dismissal is opt-in for Move, preserving
  peer TaskDialog behavior. All dismissal paths are guarded during final Apply.
- **Confirmation:** Apply starts disabled. Only a successful current server preview can enable it;
  changing the target discards the preview, disables Apply and requires Preview again. Pending Apply
  dismissal, stale feedback and server atomicity contracts are retained.
- **Botanical Identity:** Quick Preview and the equivalent detail action group both expose Add plant
  beside Add seed lot. Both use the existing `#/plants?action=create&identity=<UUID>&kind=plant`
  route and normal prefilled Plant form. No automatic creation, PlantGroup substitution, new
  mutation, or inferred acquisition/provenance/Location values is introduced.
- **Result metadata:** one small quiet `DirectoryResults` component sits immediately before each
  relevant result list, after filters and active selection controls. It provides `0 records`,
  `1 record`, `N records`, page/total and loaded-only `N shown` forms without a live region.

Count audit (all values come from existing responses and filters; no count query was added):

| Surface              | Count source / meaning                                                                |
| -------------------- | ------------------------------------------------------------------------------------- |
| Seeds                | Complete locally filtered visible SeedLots                                            |
| Sowings              | Complete locally filtered visible Sowings                                             |
| Plants / PlantGroups | Complete visible records after current kind/lifecycle/search filters                  |
| Harvests             | Filtered historical Harvest list, retaining its exclusion from bulk moves             |
| Stored material      | Filtered tracked inventory lines in the current state/Location/search view            |
| Events               | Complete filtered global Event response                                               |
| Media                | Current page length and authoritative filtered response total; e.g. `2 of 30 records` |
| Locations            | Matching records, excluding ancestor rows displayed only as tree context              |
| Geography            | Filtered named places in the directory; no count on standalone place detail           |
| Provenance sites     | Current browse/coordinate-filtered list; no count on standalone site detail           |
| Provenance map       | Filtered mapped sites in its companion result list, including filtered zero state     |
| Botanical identities | Complete locally filtered identities                                                  |
| Suppliers            | Complete locally filtered suppliers                                                   |

There are no architecture exceptions requiring new queries. Bare map empty states, detail pages,
forms, Dashboard summaries and Tools receive no decorative count. Existing filtering, pagination,
Saved Views and Quick Preview behavior remain in their owning components.

### Refinement verification and browser evidence

- Focused Vitest: **266 passed in 17 files** with `--configLoader runner`: BulkLocation,
  DirectoryResults, ReferenceInteractions, UX004, MediaScreen, ProvenanceMapScreen, SeedLotScreen,
  SowingScreen, PlantScreen, StoredMaterial, HarvestScreen, Conversion, SavedViews, SupplierScreen,
  ProvenanceSiteManager, UX001 and App. This covers target invalidation, direct backdrop/inside
  clicks, pending-Apply dismissal guards, focus, Identity navigation/prefill, quiet count grammar,
  filtered counts, Media page/total and existing directory/Quick Preview/Saved View regressions.
- Final ProvenanceMapScreen recheck after the filtered-zero metadata addition: **5 tests passed**.
- Whole-frontend Prettier, zero-warning ESLint, strict TypeScript and production Vite build passed.
  Backend tests were not repeated for this frontend-only refinement; initial domain/atomicity
  evidence above remains applicable. No canonical `make feature-verify` was run.
- Browser review at **1440×844, 1024×844 and 390×844** confirmed utility-row placement (including
  conditional Save view), compact selection, result metadata and horizontal bounds. Seeds' modal
  measured 766px on desktop/tablet and 335px on mobile, with four existing Locations visible before
  scrolling. Preview actions remained inside the 844px viewport. Direct backdrop clicks and Escape
  restored Move focus; inside clicks retained the dialog. Changing the previewed target removed
  preview rows and disabled Apply. No final Apply was performed during this refinement.
- Stored material showed **1 record**, one selected inventory line and the same compact toolbar at
  all sizes. Keyboard Shift+Tab wrapped from the target picker to Cancel and Tab wrapped back;
  Escape returned to Move and Done returned to Select. Its existing conversion action returned only
  after exiting selection.
- Count audit in the synthetic browser: Seeds **3** / filtered Basil **1**, Sowings **1**, Plants
  **3**, Harvests **1**, Stored material **1**, Events **6**, Media **2**, Locations **4**, Geography
  **288**, Provenance sites **1**, map companion **1** / filtered **0**, Botanical identities **3**,
  Suppliers **2**. All checked list
  metadata and page widths fit the three viewports. Media's partial-page totals and zero/singular/
  plural rendering are additionally verified in tests; counts have no added live region.
- Botanical Identity Quick Preview shows Add plant beside Add seed lot at the desktop preview
  surface. Existing tablet/mobile row navigation continues directly to detail, whose equivalent
  actions wrap within bounds at all three sizes. Both links opened **Record Plant**, prefilled
  **Ocimum basilicum**, with Location **Not recorded**; the form fit all three sizes. Both exercises
  were cancelled without creating a Plant or changing normal direct-origin semantics.
- The synthetic fixture contains at most three selectable rows per reviewed directory. The full
  100-row bound is tested, but a real browser selection of 100 rows is not claimed. No fixture
  expansion was made solely for visual evidence.
- After a resumed-runtime stop, supported `make uat-preview-up` restored healthy frontend/backend/
  database services at the same URL, unchanged head `20261006_0034`, fixture **v1**, **31 baseline
  records** and preserved edits. The earlier transient empty Harvest Vite transform was resolved by
  refreshing its source watch notification; the production build and Harvest regression pass.
  This refinement introduced no persistent UAT record edits, moves or fixture-code changes.
- At this refinement handoff, diff whitespace passed and the index was empty; the source remained
  unstaged/uncommitted for operator acceptance and Luna's independent final gate.

## Roadmap and review boundary

BULK-001 is verified after operator UAT and independent canonical verification. Justified unified
operational history remains next in Collection productivity v2; Orders/Purchases remain later.
SCHEDULE-001 is only a later Activity candidate. The schedule → completion → historical Event
relationship stays open; a calendar is a possible presentation. BOTANY-003 remains blocked and
unchanged. No other bulk action is justified for immediate implementation by this increment.
