# SCHEDULE-002 implementation handoff

Candidate on `feat/schedule-002`, based on authoritative `main`
`8ed57d63b45286cb2509e9eeca9c2a84ad5b14eb`. Status: independently reviewed and verified by the
canonical FULL gate. The exact candidate tree is staged and committed for protected delivery; no
production migration was added.

## Domain and audit

Calendar is a presentation of **ScheduledActivity**, not another domain. Existing eight kinds,
six optional exact targets, date-only due day, planned/completed/cancelled states, versioning,
terminal retention and atomic/idempotent optional compatible Event linking remain authoritative.
Overdue is still derived only for planned work. Completion alone creates neither Event nor History.
No new database table, migration, timezone, persistence adapter or dependency.

The product relationship is **Schedule → List | Calendar**, under the existing Schedule route
and workspace. Calendar includes every ScheduledActivity matching the shared filters and visible
period, across all eight activity kinds and six supported target types (including whole-collection
work). It never mixes in Journal entries or History facts; no separate Calendar product area exists.

Audited model/schema/API/service, batched target response resolution, locking/version and Event
paths, canonical hash routing, list buckets/filters/contextual creation, tests, UAT lifecycle,
UI Foundation tokens/PageHeader/Page/TaskDialog and existing date/dependency primitives.
Existing React, semantic table/buttons and native Date arithmetic suffice for month rendering.

## View model, calendar and filters

List is the default operational view. `#/schedule?view=calendar&month=2026-10` selects Month;
optional `date=2026-10-12` selects its day. Invalid months/days fall back safely. Default List
presentation remains `#/schedule`, with existing filter keys in their established order.
List/Calendar navigation uses links and history; Back/Forward restore view, filters, month and day.
Search retains replace-state behavior. Month selection and day-detail visibility are separate:
selection is URL state; desktop drawer opening is transient. Direct date links select the day;
activate its date button to open desktop day detail. Switching views preserves compatible filters.

Month only; Previous / Today / Next and a named period. Monday-first semantic table, no ARIA-grid
keyboard contract. Two activity summaries per desktop day, explicit kind/target/state and a
“more” button for all remaining work. Cell content is bounded independently of day density.
Day detail uses the existing native TaskDialog as a right-side drawer, with full filtered-day work,
links and existing action dialogs. Selected-day Add activity prefills the existing creation form.

At ≤48rem the table becomes compact date buttons with counts and an inline selected-day list.
It does not squeeze desktop activity summaries into narrow columns. Day selection updates that
list; create/edit/complete/cancel use the same dialogs. No horizontal calendar scrolling.

Filters are the existing status, date window, activity kind, target kind, exact target and literal
search. Calendar intersects them with its visible month. Status switches keep the existing
window-reset behavior. Reset filters preserves Calendar and its period/day. Schedule Saved Views
were already explicitly deferred in SCHEDULE-001; that decision and other Saved Views adapters
remain unchanged.

## Dates, API and performance

Placement uses `due_on` as a complete calendar day. Browser navigation constructs numeric local
noon dates, preserving date components and avoiding UTC parsing of date-only strings. No optional
time exists; none is added. The API retains browser-supplied local `today` (UTC fallback for other
clients); one month load fixes it across pages. The screen refreshes the projection across midnight.
Terminal lifecycle timestamps retain their existing UTC semantics.

The existing authenticated `GET /api/v1/schedule` gains optional inclusive `due_from` / `due_to`
parameters using the existing strict CalendarDay validator. Reversed ranges return 422 before
queries. Range constraints intersect existing filters; ordering stays due day then ID, capped
100-row pages. Calendar sequentially loads only that month, preserves batched target labels and
aborts superseded requests. Day selection does not refetch the month. Month pages use the normal
list pagination consistency model; they are not a transactional snapshot across multiple reads.
Existing offset limit is retained, with recoverable error if the period exceeds it.

Reviewed existing due-day/status and exact-target indexes. This is a single shared collection with
authenticated access, not an account-scoped scheduling model. No new index or caching system.
Global overdue/today counts retain existing API semantics. Generated OpenAPI/client also expose exact scientific/cultivar fields on identity targets
so the UI can render scientific typography without guessing boundaries from compound labels.

## Mutations and accessibility

List and Calendar detail share ScheduleActivityRow and the same create/edit/reschedule/cancel/
complete controller, APIs and forms. Expected versions, stale conflict reload/entry retention,
owner/Origin/CSRF checks, explicit actual Event day, compatible target checks, locking and exact
retry behavior remain SCHEDULE-001 paths. Nested action dialogs return focus to the day action;
day dismissal returns it to its date/more trigger.

Heading hierarchy, labelled period navigation, native table/week headers, full date button names,
`aria-current=date`, `aria-pressed` selection, explicit overdue/today/completed/cancelled text,
visible token-based focus and native modal containment/Escape/backdrop/close handling. Compact
summary truncation retains full accessible names and full day detail. Identity scientific names use the botanical italic class and cultivar epithets stay roman, using
exact source fields rather than parsing compound target labels. Other operator labels remain roman.

## UAT, tests and visual self-review

Synthetic seed adds five planned same-day examples across target types, one month-end item and
one next-month item. It preserves all original overdue/today/terminal/six-target examples. A
separate additive manifest marker makes repeat seeding preserve operator edits. Existing fixed
UAT belongs to another worktree and is preserved; review uses the repository's positively owned
SmokeUAT/SmokeLifecycle fixture with isolated DB/media/dependencies and loopback port.

### Focused validation

- Backend: `pytest tests/test_schedule.py --no-cov` — **17 passed**; focused Ruff
  check/format and strict backend mypy — **339 source files**, all pass.
- PostgreSQL: `scripts/test-integration.sh tests/integration/test_schedule.py` —
  **15 passed**. Covers inclusive leap-month/year boundaries, one-sided bounds, deterministic
  ordering/pagination, filter intersections, authenticated API validation, versioned mutations,
  existing concurrent completion and explicit Event/retention behavior. Four existing Alembic
  configuration deprecation warnings remain; no assertion or timeout was weakened.
- Frontend in the worktree Quality runtime: `pnpm test src/schedule` — **28 passed / 3 files**,
  including the existing List actions/Event tests. `calendar.test.ts` additionally passes both
  tests under `Pacific/Honolulu`, `Europe/Rome` and `Pacific/Auckland`.
- `pnpm lint`, `pnpm typecheck`, `pnpm build` and Schedule Prettier check pass.
  `make api-check` confirms no OpenAPI/client drift. `make verify-build SERVICES=backend`
  passed for the backend production image; the frontend production Vite build also passes.
- Synthetic Calendar extension test — **1 passed**; fixture Ruff/format checks pass.
  Real guarded repeat seeding retained the original **18 ScheduledActivity** records, dates and
  media. The additive fixture marker is `schedule_calendar_extension=1`.
- Feature schema validation — **100 features**; final documentation formatting and
  `git diff --check` pass. No migration is introduced or migration check claimed.
- The machine interruption stopped the temporary preview and interrupted an unconfirmed frontend
  run. Its exact positively owned resources were retired; a fresh isolated fixture and the full
  focused frontend/API checks completed successfully after restart. Backend/PG evidence above
  was completed before the interruption, with no subsequent backend or test edits.

### Focused browser review

Actual in-app browser review used isolated synthetic UAT at 1440×844, 1024×844 and 390×844,
with all six target types, overdue/today, terminal examples and same-day overflow. No horizontal
page overflow at any reviewed width (DOM scroll width equals client width). Only Schedule was
reviewed; this does not claim global product visual acceptance.

- **1440:** Foundation PageHeader/view toolbar and full workspace width, Monday-first populated
  month, selected/today treatment and explicit overdue state. Two summaries plus “4 more” for
  six same-day items; keyboard Enter opens complete scrolling day drawer. Visible focus, native
  containment and nested form Escape return to Add activity; day Escape returns to “4 more”.
- **1024:** readable date overview with two-line compact titles, bounded overflow and no
  horizontal scroll. Completed (two items) and cancelled (one item) filters remain terminal
  states. List switch and browser Back retain completed filter and Calendar month/day.
- **390:** compact month/date counts, inline full selected-day work and existing action dialogs;
  day click opens no drawer. Shared filter controls fit; next-month work and filtered empty
  explanation/reset are usable. Selected-date create saved a synthetic November 5 activity;
  native keyboard reschedule moved it to December 5; completion without Event persisted and
  terminal detail explicitly says “Completed without a Journal Event”.
- Browser automation's date `fill()` changed the native displayed value without triggering
  React's change handler; the real native keyboard edit was used to verify persistence. No
  product workaround or alternative mutation path was introduced.
- Loading/error/retry, stale edit conflict and atomic explicit Event behavior have focused
  automated coverage; no artificial network failure was injected during browser review.

Screenshots (captured before disposable UAT cleanup):

| Evidence                             | Screenshot                                                       |
| ------------------------------------ | ---------------------------------------------------------------- |
| Desktop populated month              | [1440 Calendar](review/schedule-002/calendar-1440.png)           |
| Desktop day overflow/focus           | [1440 day drawer](review/schedule-002/day-drawer-1440.png)       |
| Tablet populated month               | [1024 Calendar](review/schedule-002/calendar-1024.png)           |
| Tablet completed filter              | [1024 completed](review/schedule-002/completed-1024.png)         |
| Mobile compact month and full agenda | [390 Calendar](review/schedule-002/calendar-390.png)             |
| Mobile selected-day actions          | [390 selected day](review/schedule-002/selected-day-390.png)     |
| Mobile filtered empty state          | [390 empty](review/schedule-002/empty-390.png)                   |
| Real Calendar-triggered completion   | [390 completion](review/schedule-002/browser-completion-390.png) |

Both interrupted and final preview lifecycles retired only their exact owned containers,
networks, volumes and unshared images, reporting zero residual containers/networks/volumes.
Operator DEV, fixed UAT, Preview and unknown resources were preserved; shared build cache retained.
Independent QA still owns the canonical gate and final acceptance. No unresolved implementation
blocker was found in this focused review.

## Final UX refinement before independent QA

Only the requested Schedule surfaces were refined. Calendar placement, month navigation,
shared filter/URL conventions, target coverage and domain/API/mutation behavior remain unchanged.
The pre-refinement evidence above remains applicable to the unchanged backend and Calendar code;
current visual evidence below supersedes the older toolbar and activity-form screenshots.

- List/Calendar is a compact segmented navigation control, with Filters and the primary
  Schedule activity action on one wrapping toolbar. Controls use Foundation tokens and 44px
  targets. Concise subordinate guidance retains the local projection day and the fact that
  overdue work stays planned.
- Empty List has a compact ruled explanation. It renders no pagination or redundant zero count;
  populated List pagination appears only when multiple pages exist. Successful mutation returns
  to the first page. A concurrently emptied later page also reloads page one, preventing a
  now-empty last page from stranding navigation or falsely claiming the Schedule is empty.
- Default empty copy is “No planned activities yet”; terminal statuses say “No completed/cancelled
  activities”. None claims the entire Schedule database is empty from a status-scoped result.
  For an empty narrowed List, one existing bounded `limit=1` request checks the same status with
  other filters removed to distinguish underlying status emptiness. Reset now belongs to the
  shared toolbar whenever filters differ from defaults, as requested in the persistent-UAT pass
  below; it restores default Active/all-date filters while preserving the view/month/day.
  Aborted/stale/auth-expired probes retain the existing safety behavior.
- Create/edit uses TaskDialog and FormActions, a viewport-bounded form, one scrolling content
  region and a fixed reachable header/footer. Title/notes/target span the form; kind/date share
  a desktop row and stack on mobile. Footer labels are Cancel and Save activity.
- Pristine Escape, backdrop and Cancel close and return focus. Dirty dismissal opens a short
  second TaskDialog: Continue editing retains entries; only Discard changes closes the form.
  Escape/backdrop on this decision also retain entries and return focus to the form. Reverting
  fields to their initial values restores pristine dismissal. Pending saves cannot dismiss or
  submit twice. Completion's explicit Event input is protected by the same comparison.
- No shared overlay component or global styles were changed. No schema, dependency, backend,
  fixture, Journal/History or unrelated workspace changes were introduced by this refinement.

### Current focused validation

- Schedule frontend in the worktree Quality runtime: `pnpm test src/schedule --maxWorkers=1` —
  **45 passed / 3 files**. Includes empty pagination suppression, truthful status/filter emptiness,
  concurrent last-page recovery, pristine Escape/backdrop/Cancel, dirty confirmation for all three
  dismissal paths, confirmation dismissal retaining entries, edit/revert behavior, focus return,
  pending-save protection and existing versioned save/Event behavior. No arbitrary timeout or
  weakened assertion was introduced.
- Focused `pnpm exec eslint src/schedule --max-warnings 0`, strict `pnpm typecheck`, production
  `pnpm build` and Schedule Prettier check all pass after the final source edit.
- Backend Schedule unit checks rerun: **17 passed**. Guarded disposable PostgreSQL Schedule
  integration rerun: **15 passed**, with the same four Alembic configuration deprecation warnings.
  Integration cleanup reports zero residual containers/networks/volumes.
- No canonical feature-verify, staging, commit or delivery. Backend/API and Calendar placement
  source did not change during this refinement; earlier API drift evidence remains applicable.
- Handoff/progress Prettier checks, feature schema validation (**100 features**) and final
  `git diff --check` pass. The index is empty and HEAD remains the recorded base commit.

### Current visual evidence

The repository-supported isolated SmokeUAT/SmokeLifecycle review used the existing synthetic
fixture: **18 ScheduledActivity** records, **13 planned** in October, six activities on today's
day (“4 more”), overdue and future dates, and all six supported target types. The operator-created
Feature Review database's empty state is not treated as a Calendar defect. No persistent UAT or
real data was seeded, reset or edited.

- **1440×844:** populated Calendar and compact toolbar reviewed; create form fields and both footer
  actions fit inside the viewport. Pristine backdrop dismissal restores focus to Schedule activity.
  Dirty Cancel/Escape opens the concise discard dialog; Continue editing retains the draft and
  explicit Discard changes closes it and restores focus. Existing-target edit also fits with its
  footer visible (bottom 825px).
- **1024×844:** populated Calendar, compact toolbar, overflow day detail and create/edit reviewed.
  Expanded target picker and notes fit in the 808px bounded dialog; Cancel/Save footer remains
  visible. Pristine edit Cancel returns focus to its day-detail action. Dirty create Cancel requires
  explicit discard and returns focus to Schedule activity.
- **390×844:** compact view switcher remains 132px wide with 44px targets and a wrapping toolbar.
  Create and edit fit inside the viewport. Expanded edit content scrolls independently (809px
  content in a 670px region); scrolling reveals all notes while the footer stays at 749–826px.
  No content is unreachable or clipped outside its intended scroll region. Pristine Escape,
  backdrop and Cancel each close and return focus to Schedule activity. Dirty edit backdrop opens
  the discard decision; Escape on that decision retains the edited notes. Real Save activity
  persists those notes, and a separate whole-collection creation persists through the same form.
- **Empty List at all three sizes:** a nonmatching search renders an 82px compact ruled state,
  a meaningful Reset filters and no pagination. Reset restores the shared List URL. No redundant
  zero count or oversized empty panel is rendered. Unfiltered/status-empty distinctions also have
  focused automated coverage; no synthetic fixture records were deleted to manufacture emptiness.
- DOM document scroll width equals client width at every reviewed size, including dialogs and
  empty List. The page scrollbar accounts for 15px at desktop; it is not horizontal overflow.

Browser access returned after the interruption. A fresh guarded isolated preview completed all
missing checks; no current viewport-review blocker remains. Its initial fixture again contained
18 activities. The real mobile creation added one synthetic record (19 total, 14 planned in
October), and an existing synthetic activity received the review note. Calendar placement and
activity counts reflected the ordinary server-authoritative saves. This remains a focused
self-review; independent QA still owns final acceptance and canonical verification.

After the preview harness ended with exit 143, the guarded exact-owner recovery retired only
`florabase-uat-preview-smoke-02321d4d1441`: four containers, one network, three volumes and two
unshared images. Cleanup reports zero residual containers/networks/volumes; shared build cache,
persistent Feature Review, DEV, fixed UAT and other environments were preserved. The temporary
loopback preview was closed. The resumed review used the same repository-supported isolated
mechanism with a new exact owner. Its harness also ended with exit 143; guarded recovery retired
only `florabase-uat-preview-smoke-22744152206f` (four containers, one network, three volumes and
two unshared images), reporting zero residual containers/networks/volumes and retaining shared
build cache. Both temporary preview URLs are closed. No persistent operator environment was
removed, reset, seeded or edited.

| Current evidence              | Screenshot                                                           |
| ----------------------------- | -------------------------------------------------------------------- |
| Refined desktop Calendar      | [1440 Calendar](review/schedule-002/refined-calendar-1440-final.png) |
| Bounded desktop create        | [1440 create](review/schedule-002/refined-create-1440.png)           |
| Existing-target desktop edit  | [1440 edit](review/schedule-002/refined-edit-1440.png)               |
| Explicit discard decision     | [1440 discard](review/schedule-002/refined-discard-1440.png)         |
| Refined tablet Calendar       | [1024 Calendar](review/schedule-002/refined-calendar-1024-final.png) |
| Expanded tablet create        | [1024 create](review/schedule-002/refined-create-1024.png)           |
| Existing-target tablet edit   | [1024 edit](review/schedule-002/refined-edit-1024.png)               |
| Refined mobile Calendar       | [390 Calendar](review/schedule-002/refined-calendar-390.png)         |
| Compact mobile toolbar        | [390 toolbar](review/schedule-002/refined-toolbar-390.png)           |
| Bounded mobile create         | [390 create](review/schedule-002/refined-create-390.png)             |
| Scrollable mobile edit        | [390 edit](review/schedule-002/refined-edit-390.png)                 |
| Notes and fixed mobile footer | [390 scrolled edit](review/schedule-002/refined-edit-scroll-390.png) |
| Mobile dirty protection       | [390 discard](review/schedule-002/refined-discard-390.png)           |
| Persisted mobile edit         | [390 saved notes](review/schedule-002/refined-save-390.png)          |
| Desktop compact empty List    | [1440 empty](review/schedule-002/refined-empty-1440.png)             |
| Tablet compact empty List     | [1024 empty](review/schedule-002/refined-empty-1024.png)             |
| Mobile compact empty List     | [390 empty](review/schedule-002/refined-empty-390.png)               |

## Persistent manual-review UAT and final control refinement

### Schedule controls

- Target search, selection, count and any page navigation form one accessible Target record
  group. Count is subordinate; zero/single-page results show no pager. Multiple pages use compact
  chevrons and a page label, full accessible Previous/Next records names, native disabled states,
  muted disabled styling and Foundation focus/touch targets. Server search, 50-row offsets and
  retained selection are unchanged. Keyboard accessibility and retained selection across pages
  have focused tests; no extra fixture records were created just to manufacture multiple pages.
- Reset filters sits beside Filters in the shared Schedule toolbar, only when status/date-window/
  activity-kind/target/search differ from defaults. It restores Active/all-date/no-kind/no-target/
  empty-search filters and preserves List/Calendar, month and selected day. It is absent from
  Calendar content. Back/Forward restores the prior filters and reset state.
- Period navigation is one compact `‹ Today ›` group beside the month heading. Chevrons retain
  Previous month/Next month accessible names, keyboard activation and Foundation focus styling.
  Native disabled behavior at calendar bounds is retained and visually muted.
- The viewport-bounded shared TaskDialog editor, scrolling body, reachable Cancel/Save footer,
  pristine Escape/backdrop/Cancel, dirty confirmation and focus return remain intact. Compact
  target metadata reduces the expanded desktop/tablet editor to about 786px high; mobile has
  737px of content in its 670px scrolling region, with the footer fixed at 749–826px.

### Fixture audit and additive evolution

The existing fixture already provided most of the requested coverage; its architecture and
ownership rules were reused. **Fixture version remains 4**, with the existing stored-material,
taxonomy, Schedule, Calendar and Dashboard extensions and new **manual_review_extension=1**.
Recognized ready v4 manifests gain exactly three records: a Genovese identity, an unknown-quantity
packet linked to the partial Order and whole-collection planned work. The new identity receives
explicitly synthetic description/cultivation text. Cultivar spelling follows
[Richters' 2025 catalogue, page 8](https://richters-prod.s3.ca-central-1.amazonaws.com/public%2Fd0005_Richters_CAD_5d5a98cac2.pdf#page=8);
the name check covers typography, while the material and profile content remain synthetic.

All records use existing domain services/UUIDv7 generation and the existing external manifest.
Repeating seed validates identities/binaries and skips applied extensions, preserving operator
titles, quantities, notes, dates, source links and primary media. Unrelated operator records are
preserved. New extension work marks the manifest building first; an interrupted extension or
missing/incompatible baseline requires the existing explicit guarded reset. No automatic repair,
duplicate-object creation or rolling date rewrite is introduced.
Both pre-existing Schedule extensions now use that same building/ready pattern. Tests simulate
a successful commit followed by marker-write interruption: the on-disk manifest remains building
and ordinary seed refuses, preventing a silent second set of activities.

Schedule dates follow the existing first-seed UTC-day convention. Repeating seed does not move
overdue/today/future examples to a new day. Refresh those examples deliberately with
`make uat-preview-reset CONFIRM_RESET_UAT_PREVIEW=florabase-uat-preview`, which discards UAT edits.
The additive upgrade itself requires no reset of a recognized intact v4 fixture.

The pinned optional **WFO 2026-06** archive was installed through the existing snapshot validator:
132,643,291 bytes; SHA-256 `75f1ad1f371978c9e46f3044152c07ed276fe57be9fb9a15b3621b19cf231987`;
release metadata/CC0 and index seal checked. Ignored owning-worktree cache is
`backend/src/.source-cache/wfo-2026-06.sqlite` and sibling `.sha256`. Its existing extension adds
Holy basil and five explicit reviewed links. No source download occurs during seed/startup.
Genovese and lavender remain unresolved in Taxonomy. Existing offline CoL XR basil metadata,
synthetic range assertions and geographic/provenance examples are preserved.

### Persistent environment and normal workflow

- **URL:** http://localhost:15174 — **UAT-only credentials:** `preview / preview`, as the current
  guarded fixture policy specifies. Normal production password validation/authentication is
  unchanged.
- **Owner/source:** `/home/alessandro/.codex/worktrees/6147/florabase`, branch `feat/schedule-002`,
  current dirty/untracked candidate at recorded base HEAD. Compose project `florabase-uat-preview`;
  schema/code head `20261009_0041`; loopback frontend only, internal backend/PostgreSQL.
- The operator-authorized old synthetic `51ba` owner was retired from that checkout using this
  repository's guarded `uat-preview-remove` target and exact confirmation token. Only its UAT
  resources were retired. This worktree's Feature Review was stopped to release shared port 15174;
  its independent volumes/data were preserved. DEV, Stable Preview, production and unknown
  resources were preserved.
- This worktree ran supported up/explicit seed/status. Persistent DB/media/dependencies are
  retained; **leave this UAT running for ongoing manual review**. Feature Review/disposable smoke
  remains separate.

```bash
# From the owning worktree:
make uat-preview-up       # Normal start/rebuild; preserves existing UAT state
make uat-preview-status   # Source, health, schema, fixture and owner status
make uat-preview-seed     # Explicit first initialization or missing additive extension
make uat-preview-stop     # Preserves DB/media/dependencies
make uat-preview-up       # Resume the same persistent collection
```

Two explicit repeat seeds and a real fixed-UAT stop/up cycle preserved every database-table row
digest, count, manifest identity and media checksum. Disposable UAT smoke additionally proved
ordinary operator edits/new records survive repeated seeds and stop/start, normal session login,
wrong-owner refusal, guarded reset and old-owner/new-owner transition. The UAT identity/credential
and lifecycle implementation was not changed.

### Representative manual coverage

Current persisted fixture: **68 manifest records** (66 without optional WFO), **8 identities**, **5
profiles**, **9 SeedLots**, **4 Sowings**, **2 Plants**, **1 PlantGroup**, **1 Harvest/material line**,
**1 active stored inventory**, **4 Locations**, **4 Events**, **19 ScheduledActivity**, **2 Suppliers**,
**2 Orders**, **2 media assets**, **4 media links**, **5 WFO links**. Quantities/relationships remain
explicit and may be unknown; the fixture does not infer balances, occurrence dates or conversions.

All requested major screens were inspected through the browser using persistent UAT:

| Workspace                  | Representative visible state                                                                                                                                     |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Dashboard                  | 2 individual plants, 1 group, 8 active lots, 3 active sowings; 1 overdue, 7 today, 4 next-7; propagation/sourcing/coverage and recent Journal/History            |
| Seeds                      | 48 exact seeds, about 80 seeds, unknown quantities, Genovese cultivar, linked/unlinked purchases and a historical exhausted packet                               |
| Sowings                    | 8/12 germinated, zero and unknown counts; completed lavender trial also inspected                                                                                |
| Plants                     | Purchased aloe, sowing-derived basil and a six-member group                                                                                                      |
| Harvests / Stored material | Month-precision basil Harvest with 30 items; separately tracked active remainder with unknown quantity                                                           |
| Locations                  | Preview collection and three storage/growing child locations with holdings                                                                                       |
| Journal                    | Four entries: two observations with recorded-day fallback, explicit repotting and month-precision Harvest                                                        |
| History                    | Four deduplicated Event/Harvest facts retaining actual/partial/unknown occurrence precision                                                                      |
| Schedule List              | 16 planned work records across overdue/today/next-7/later buckets; completed/cancelled records retained                                                          |
| Schedule Calendar          | 14 October planned items, seven today including collection-wide work, five-more day detail, overdue/future and next-month work                                   |
| Botanical identities       | Eight identities and roman cultivar epithet; Genovese profile detail inspected with synthetic description/cultivation                                            |
| Taxonomy                   | Seven represented identities, five linked through real WFO classification and two explicit unresolved identities                                                 |
| Suppliers / Orders         | Nursery/exchange; exact-date EUR purchase with two physical packets; partial-date/unknown-price Order with one linked packet; unlinked purchased packet retained |

### Current focused checks and visual review

- Schedule frontend: **51 passed / 3 files**; empty/one/full-single-page target pager suppression,
  multi-page boundaries/selection/search offset, toolbar-only Reset/default behavior/history,
  month navigation and all preceding dialog/save protection tests. Focused ESLint, TypeScript,
  production Vite build and Schedule formatting pass.
- Backend Schedule: **17 passed**. PostgreSQL Schedule: **15 passed**, with the same four Alembic
  configuration deprecation warnings; owned integration resources cleaned with zero residuals.
- Fixture extension unit checks: **5 passed**, including v4 additive upgrade/idempotence,
  interrupted-building refusal and both post-commit marker-write failures. Real disposable
  fixture/guard checks: **25 passed**. UAT workflow
  unit checks: **19 passed**. Full focused UAT Compose smoke passed persistence, edits, reset and
  ownership transition, retaining protected environments and reporting zero residual disposable
  resources. Temporary migration markers were removed. The first smoke completed before persistent
  startup; the final repeat after interruption protection also proved the running persistent UAT
  and other protected environments unchanged.
- Changed fixture/test/smoke Ruff checks/format pass; strict fixture/UAT-helper mypy passes on six
  files. Current `make api-check` passes with no generated-artifact drift. Backend/API contracts
  did not change in this control/fixture pass. No dependency, production-domain schema or
  migration was added.
- Persistent visual review at **1440×844, 1024×844, 390×844** confirms compact target count and
  zero/single-page suppression, coherent toolbar Reset, `‹ Today ›`, populated month, full overflow
  day across targets, editor scrolling/footer access, pristine dismissal/focus and retained dirty
  draft. DOM document width equals client width at all sizes, including the active-filter toolbar.
  Calendar upper-bound Next is natively disabled, muted and uses not-allowed cursor. Current
  creation/save behavior also has automated coverage and the earlier real synthetic save evidence.

Screenshots are in [persistent review evidence](review/schedule-002/persistent/): Calendar at all
three sizes; toolbar Reset at all three; desktop/mobile edit, tablet create and zero target results;
mobile scroll/discard; day overflow and disabled navigation; Dashboard, Seeds, Sowings/completed,
Plants, Harvests/stored material, Locations, Journal, History, identities/profile, Taxonomy,
Suppliers and Orders. Only browser state/view choices and discarded drafts were changed during
manual inspection; the persistent domain fixture remains available for the operator.

## Independent QA and canonical verification

Independent QA reviewed the complete diff against this handoff and `docs/ui-contract.md`, including
ScheduledActivity boundaries, inclusive bounded month queries, local date handling, deterministic
ordering, shared filters and URL history, List lifecycle/actions, target pagination, dialog focus and
dirty protection, synthetic fixture ownership, generated API synchronization, and responsive states.
No production/domain/workflow defect was found. The two Schedule List density/desktop-width polish
items remain deferred to the planned global page review.

`make feature-verify` selected **FULL** because the diff includes guarded UAT fixture/workflow files.
The exact candidate tree passed with feature graph **100 valid**, backend **912 passed at 90.25%
coverage**, frontend **599 passed across 60 files**, PostgreSQL integration **720 passed**, all eight
workflow suites, repository formatting/lint/strict typing/API drift, backend and frontend production
builds, whitespace checks, and an exact working-tree receipt. The forced migration cycle passed at
the existing head `20261009_0041` in all four base/head transitions; no migration was introduced.
The isolated integration, build and migration resources were cleaned by their exact owners; shared
BuildKit cache and unknown/legacy resources were retained. Persistent UAT at
http://localhost:15174 remains healthy with fixture v4, 68 records, and owner `preview / preview`.
DEV, Stable Preview, production and unrelated environments were preserved.

`SCHEDULE-002` is marked `verified` in `docs/features.json`. This handoff records the feature and
review evidence; protected delivery and `make feature-finish` are managed by the repository's
separate lifecycle commands.

## Deferred

Week mode, drag/drop, recurrence/RRULE, reminders/notifications, priorities, assignments,
subtasks/boards, external synchronization, iCal/Google Calendar, Schedule Saved Views, global
visual migration and new History/Journal semantics. Rescheduling remains explicit and versioned.
Legacy directory/detail cards, control density and page-specific styling observed during the
fixture inspection remain for the later global UI review. Existing empty cover placeholders and
the intentionally offline external media reference are expected fixture states. No unrelated
screen redesign or external occurrence/enrichment loading was attempted.
