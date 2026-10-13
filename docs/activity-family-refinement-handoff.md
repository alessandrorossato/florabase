# Activity family refinement — ACTIVITY-001

Implementation candidate, 2026-10-13, in the existing `a165` worktree on
`feat/journal-history-product-pass`; base HEAD remains `b99bb4af62efbb0c531e656009e0880559fb6f0f`.
Everything is unstaged/uncommitted. Independent QA owns acceptance and canonical verification.
This consolidates the final presentation over the [Journal/History source audit](journal-history-product-pass-handoff.md).

## PRODUCT MODEL PRESERVED

Journal is the recording hub plus operator field notebook fallback. History is the global read-only
past-fact projection. Schedule is future intended work. A delivered structured concept opens its
canonical workflow; otherwise the existing contextual Journal records the observation/note.

The Record catalog, target chooser, correction ownership, backing-row suppression, PartialDate,
labelled UTC recording/completion time and shared Dashboard recent-activity semantics remain intact.
Schedule completion is a persisted terminal planning fact; planned/overdue/cancelled intentions do
not become completed History. Optional occurrence creation remains explicit, atomic and idempotent.
No domain model, schema, provider, migration or Saved Views surface is added here. Existing History/Schedule list endpoints accept bounded repeated enum filters; mutation contracts are unchanged.

## SHARED PAGE HEADER

`ActivityPageHeader` composes the shared `PageHeader` with its optional tools slot. PageIdentity
contains Activity eyebrow, title and short subtitle. PageTools contains the real supported controls.
Journal/History retain their concise subtitles; Schedule says "Future work planned for your collection."
Other PageHeader consumers retain their existing action/description behavior.

Flexible identity/tools bases share one row when space permits; reduced available width wraps tools
under identity. This uses intrinsic flex sizing, practical search basis and wrapping rather than a
fixed page width or desktop-only toolbar rule.

## PAGE TOOLS

Journal: Search → Filters → Saved views → + Record.
History: Search → Filters → Saved views.
Schedule: Search → Filters → + Schedule activity (owner only).

Search fills remaining tool width; buttons keep the Foundation's compact sizing. Active summaries
sit below the header. Schedule List/Calendar sits in the local view heading alongside Calendar period
navigation, below the global PageHeader. Static "Active · All dates" and educational local-day copy are
removed. Counts are quiet list/month metadata using the actual returned totals.

## SEARCH

Journal searches its existing loaded notebook fields. History retains authenticated, bounded,
literal projection search before SQL count/page. Their existing URLs and Saved View states are retained.

Schedule exposes its already-delivered server-side title/notes search. `q` is bounded to 200 characters,
URL-addressable and combined with status/date/kind/target filters. List is paged at 50; Calendar uses
inclusive visible-month bounds and capped pages at 100. Search is not a client filter over partial
results and does not fetch lifetime history. Target labels are not advertised as Schedule search fields.
A PostgreSQL regression checks notes-only matches, literal `%_`, date/kind intersections and counts
on empty/out-of-range pages. Typing replaces URL state; view/filter/period navigation preserves history.

## FILTERS

The common live-filter grammar below supersedes the earlier single-value controls. Dashboard behavior
is preserved. Filters remain scoped to real existing dimensions and values.

## FILTER INTERACTION MODEL

Dashboard applies filters live. All Activity drawers now do the same: checkbox changes and valid
Timeline year changes update results/URL immediately, with one Reset filters / Done footer. There is
no Apply year or staged draft. Empty year removes its restriction; invalid input is labelled, never
sent to the API and leaves the last valid result filter intact. Typing replaces URL state; selection
changes push it. Done/Close/Escape/backdrop dismiss the drawer and restore Filters focus.

Reset clears drawer dimensions and exact target, preserving search. Schedule also preserves view,
month and selected day. Reset appears only when a dimension actually restricts results. Planned is
Schedule's initial active restriction, so a fresh Schedule has Filters (1) and can clear Status.

## MULTI-SELECT

Shared ActivityChoices uses native clickable labelled checkboxes within a fieldset/legend. Its grid
has two columns at wide drawer widths and one on narrow/mobile screens. No pseudo All entry/activity/
record-type choice is rendered. No selected values means no restriction within that dimension.
Values are unioned within dimensions and intersected across dimensions/search. Existing scalar
Saved Views and single-value URLs remain readable; new states use deterministic repeated keys.

## JOURNAL FILTERS

Entry type supports Observations, Cultivation and Lifecycle together, using existing category-to-kind
membership. Empty selection includes every notebook entry, including Other. Selecting all three
named groups still excludes Other and therefore remains one active dimension. The notebook/backing-row
rules and current loaded-field search are unchanged. `category=all` remains readable as an empty
selection; new URLs/Saved Views omit it and serialize category arrays in stable order.

## HISTORY FILTERS

Fact type and Primary record type both support multiple existing values. Backend support is a narrow
SQL IN extension over the existing projection, before global count/page; no disproportionate rewrite
or single-select exception is needed. Repeated category/subject_kind parameters are enum validated
and bounded to six/seven values. Search, PartialDate, deduplication and stable ordering remain intact.
Timeline year stays single, live and validated from 1 to 9999. Primary record type filters the primary
record, not related references. Full finite enum selections do not count as a restriction.

## SCHEDULE FILTERS

Status, Activity kind and Target type use multiple existing enum values. Date window stays a single
select (All dates, Overdue, Today, Next 7 days, Later). Overdue still intersects with planned status
and due_on before today; it never becomes a stored status. Combining only terminal statuses with
Overdue truthfully yields no results. SQL uses IN for status/kind and OR across selected target FKs,
then intersects search/date bounds before count/page. Enum lists cap at 3/8/6; due-day/ID ordering,
paging, batched labels and planned attention counts are preserved.

Backward compatibility keeps omitted Status as planned for old Schedule URLs/API calls. Unrestricted
Status explicitly encodes all three real values (`status=planned&status=completed&status=cancelled`)
and restores as no selection; selecting every status normalizes to that same unrestricted state.
No artificial all status is introduced. Other empty dimensions are omitted. Exact target IDs require
one target type; changing Target type clears the ID, and ambiguous API requests return 422.

## FILTER COUNT

Filters (N) counts restricting dimensions, never the number of selected values or search text:
Journal Entry type; History Fact type / Primary record type / Year; Schedule Status / Date window /
Activity kind / Target type / Exact target. Complete exhaustive enum selections are unrestricted. Journal's three named groups still exclude
Other; Schedule's six typed targets still exclude valid untargeted plans, so these remain active. Period/view alone do not
count. Several values in one dimension still count as one.

## ACTIVE FILTER SUMMARY

Each restricting multi-value dimension has one compact removable chip, e.g. Fact type: Journal +1 ×.
Removing it clears that dimension, preserving the other filters and query. Year/window/exact-target
chips remain individually removable. Clear filters shares the drawer reset contract. Search stays
in PageTools and does not become a chip. Summaries wrap without large action-style walls.

## LIST / CALENDAR POSITION

The standalone Schedule view toolbar is removed. One local heading directly below the PageHeader
and active summary contains the view switcher in its right-hand control region in both representations.
Switching preserves query, repeated filters, month and selected day in the URL, including List URLs;
refresh and browser Back/Forward restore them. No extra global toolbar is introduced.

## CALENDAR VIEW HEADING

Month identity is on the left. List / Calendar followed by Previous / Today / Next sits in the local
right-hand region. Navigation retains bounds, selected-day behavior and filters. Mobile puts the month
above compact wrapping view/period controls. All controls remain reachable and viewport bounded.

## LIST VIEW HEADING

The left label is the actual filtered total (N activities), or Activities while loading. List / Calendar
uses the same local control region. List has no period navigation. Planned due-date buckets remain;
combined statuses additionally show Completed/Cancelled buckets based on each row's actual status.

## ACCESSIBILITY

Native checkbox state, clickable labels, fieldset legends, 44px option targets and Foundation focus
styles expose selection beyond color. Filters' accessible name includes its dimension count. Shared
TaskDialog contains keyboard focus; all dismissal routes restore the invoking Filters button. The
content-sized drawer caps at the viewport, scrolls its fields and keeps header/footer outside that
scroll area. Native keyboard Space, refresh, Back and focus restoration are covered by browser checks.
Full screen-reader and independent product acceptance remain deferred.

## SAVED VIEWS

Journal/History retain their real owner-private Saved Views controls and CRUD, canonical URLs and
page-one reset. New Journal category and History primary-record arrays canonicalize in stable enum
order. Existing v1 scalar category/subject states normalize without a data migration or rewrite of
stored rows. Invalid/new unknown values remain rejected. No result snapshot or new state system is
introduced. Schedule has no Saved Views contract or placeholder.

## JOURNAL VISUAL MODEL

One grouped white chronology surface uses compact date/content rows and subtle dividers, with a
source badge, entry type, target, useful note excerpt and direct context links. + Record is in PageTools.
Global rows navigate to the contextual editor; no large per-row Edit/Delete controls are introduced.
The existing chooser, uncertainty, pristine/dirty dismissal, focus and canonical routing remain intact.

## HISTORY VISUAL MODEL

One grouped white operational log retains stable ordering, typed source links, effective date precision,
concise source badges and useful secondary context. It has no create/edit controls or repeated "why"
disclosures. Unknown/partial dates are not forced into Today/Yesterday groups or invented days.
Schedule completion remains explicitly labelled Completion recorded, distinct from actual occurrence.

## SCHEDULE LIST VISUAL MODEL

The existing Overdue / Today / Next 7 days / Later buckets each have a white list surface with compact
rows and dividers. Combined status filters place Completed/Cancelled facts in their corresponding existing buckets. Rows prioritize
title, due date/state, activity kind and target. Long notes have a bounded, muted two-line preview;
full notes remain in inspection. Synthetic fixture notes retain their disclaimer without a large prose
block. No notes or source records are rewritten for appearance.

## SCHEDULE CALENDAR

Calendar uses the same header, search and drawer. The local month heading combines view selection and period navigation. Selected-day URL, two cell
summaries plus overflow, day drawer and mobile selected-day agenda remain unchanged. Existing forms
and expected versions still handle creation/reschedule/completion/cancellation. Add activity retains
selected-date prefill. The low-value persistent "dates are intended work" paragraph is removed.
Calendar's white month surface and restrained borders retain the Foundation's visual grammar.

## ROW ACTIONS

Only planned owner rows expose Complete plus a compact overflow menu. Edit/reschedule and Cancel
activity live in that menu; Cancel uses the danger text token without coloring the entire row.
Terminal/non-owner rows retain inspection and source navigation without invalid write controls.

Shared OverflowMenu preserves outside dismissal, arrows, Escape and focus return. Inside a native
modal it portals into the enclosing dialog's interactive subtree; Escape closes the menu before the
parent drawer. Selecting an action opens the existing versioned form/confirmation and returns focus
to the row launcher on dismissal. Conflict reload, dirty protection and pending-action safety remain.

## RESPONSIVE / ZOOM

Actual Chrome browser zoom matrix: 1440×844 at 80/100/125/150%; 1024×844 at 100/125%; 390×844 at 100%.
All five presentations are measured: Dashboard reference, Journal, History, Schedule List and Calendar.
All 35 page checks pass with no horizontal document/main overflow and document scrolling. Wide
headers put tools beside identity; reduced width/mobile wraps naturally without an unused right band.
Drawers, Saved Views, Record, chooser and both editors fit the viewport; long modal content scrolls.
Activity drawers use a 34rem maximum width, content-sized height and viewport cap. All 28 drawer
measurements verify two-column wide / one-column mobile checkbox grids and reachable footers.

Zoom is Chrome `tabs.setZoom`, changing CSS viewport and device pixel ratio, not CSS zoom or a
scale-only simulation. The zoom harness activates normal DOM handlers because automated native
pointer/key targeting does not reliably follow browser zoom. Native normal-zoom browser interactions
and focused keyboard/focus tests are separate evidence. Full screen-reader/global acceptance is deferred.

## SHARED COMPONENTS

The extraction is limited to ActivityPageHeader, native ActivityChoices, small selection helpers,
PageHeader's tools slot and scoped semantic-token styles. Dashboard supplies the existing control/drawer grammar and remains the reference. Grouped
surfaces reuse the existing ordered lists and Schedule buckets. OverflowMenu's modal hosting fix is
covered by shared interaction and Calendar tests; no dependency, generic registry or architecture
rewrite is introduced. Dashboard product behavior, navigation and aggregate semantics are unchanged.

## UI CONTRACT

The narrow [UI Foundation update](ui-contract.md) documents PageIdentity/PageTools, intrinsic wrapping,
practical flexible search, compact controls, grouped white surfaces and subtle dividers. Borders carry
structure; shadows remain restrained overlays. Newly touched pages must adapt to available width,
including actual browser zoom. This is not the global cross-product visual migration.

## TESTS

Focused checks only; no canonical `make feature-verify`:

- Baseline: 129 Activity filter/Saved View/Schedule frontend tests passed before this correction.
- Backend: 148 History/Saved Views/Schedule/Event/schema tests passed with `pytest --no-cov`.
  Final Ruff lint/format across 384 files and strict mypy across 339 files pass.
- PostgreSQL: 60 distinct focused tests pass across History, History Saved Views, Schedule,
  Dashboard and Event API. Initial selection passed 59/60; the added History fixture was corrected
  to search an existing primary-label field and expect both matching actual facts. Final History
  rerun passes 22; final Schedule rerun passes 17, including typed versus untargeted plans.
  Tests cover real combinations, repeated API values/bounds, pre-page count, stable ordering,
  literal search, completion/dedup, legacy Saved Views and untouched mutation/aggregate contracts.
  Every guarded disposable integration cleanup reports zero residual owned resources.
- Frontend: 204 affected tests pass across Journal/History, contextual Plant Journal, Saved Views,
  Schedule List/Calendar, DashboardSearch, UX001 and shared ReferenceInteractions. The final
  Final Schedule rerun passes all 56 tests after the target-count correction. ESLint, strict
  TypeScript, scoped formatting and the final production build pass.
- API artifacts are regenerated for repeated enum queries; `make api-check` passes without drift.
  Feature graph remains valid at 102; all 101 pre-existing definitions are unchanged.
  `git diff --check` passes; index is empty and base HEAD remains unchanged.

No full release gate, migration cycle, global visual review or independent acceptance is claimed.

## VISUAL EVIDENCE

Current screenshots and [35 page / 28 drawer measurements](review/activity-family/filter-consistency/zoom-evidence.json)
are in `docs/review/activity-family/filter-consistency/` (168 PNGs). Earlier parent-folder and
Journal/History captures are historical candidates. Actual Chrome zoom covers 1440×844 at
80/100/125/150%, 1024×844 at 100/125%, and 390×844 at 100%. All document/main overflow, drawer/grid,
footer and local view-control assertions pass. Journal's short drawer measures approximately
334–337 CSS px wide-screen height and 384 px on mobile; it no longer stretches into a blank sheet.
Long Schedule/History content scrolls inside the fields, with the footer remaining reachable.

Compare [Journal drawer](review/activity-family/filter-consistency/events-filters-1440-100.png),
[History selections](review/activity-family/filter-consistency/history-filters-selected-1440-100.png),
[Schedule drawer on mobile](review/activity-family/filter-consistency/schedule-filters-selected-390-100.png),
[Calendar heading](review/activity-family/filter-consistency/schedule-calendar-1440-100.png) and
[List heading](review/activity-family/filter-consistency/schedule-1440-100.png).

Final native browser checks pass for Record routes/chooser, Journal correction/date/search/deletion,
Schedule notes search/versioned reschedule/completion/cancellation, Calendar modal menu/Escape/month/
mobile agenda, clickable multi-select labels, keyboard Space, dimension counts, query-preserving
reset, refresh/Back restoration, local switcher/period preservation and mobile footer reachability.
The zoom harness uses normal DOM handlers because automated pointer targeting does not reliably
track actual browser zoom; these native checks are separate evidence.

The existing synthetic v4 fixture suffices; repeated seed preserves fixture/record state. Final
positively owned disposable preview `florabase-uat-preview-smoke-c50bf9eb3778` is retired with zero
residual owned containers/networks/volumes. All four browser runs return success.

Final before/after audit: protected Git/container/volume metadata and non-UAT database digests match.
All 38 persistent UAT tables other than auth_sessions have identical full-row counts/digests.
auth_sessions retains one row but its digest changes, also changing the raw UAT database digest.
The exact changed fields/cause are not established; this is not reported as complete 39-table
preservation. A preceding full browser run matched all 39 tables/raw digests. No persistent UAT
reset/reseed/repair or session rewrite was performed; all task browser URLs/mutations target the
owned disposable preview. No secret/session contents were emitted by the audits.

## SIDEBAR IA NOTES

No macro-category or ordering change. A recording hub that routes into Collection operations still
raises a later Activity/Collection membership question. Defer Overview/Collection/Activity/Explore/
Maps/Sourcing/Tools naming, membership and daily-workflow ordering to the dedicated IA pass after
Labels and before the functional/IA freeze.

## DEFERRED

Labels; sidebar restructuring; global visual review; Schedule Saved Views; target-label expansion of
Schedule search; recurrence/reminders; new observation/Health/Phenology/Measurement/Cutting domains;
Material Lineage; universal contextual timeline; Calendar drag/drop or new modes. No post-v0.1 feature
is pre-built. Independent QA owns final acceptance and canonical verification.

Handoff boundary: **READY_FOR_VISUAL_REVIEW**. Candidate remains unstaged/uncommitted.

## INDEPENDENT REVIEW — 2026-10-13

Manual source and product review found no material Journal/History/Schedule defect. The current
`filter-consistency` screenshots show the final native checkbox drawers; the older screenshots in
the parent `activity-family/` directory predate the final multi-select correction and are not used
as final drawer evidence. Persistent UAT was inspected without reset/reseed: Dashboard, Journal,
History, Schedule List, Calendar, filters, source navigation, linked completion/Journal context,
and query/period-preserving List/Calendar switching all rendered expected synthetic fixture state.
No collection, schedule, Journal or fixture records were created, edited or removed. Sign-in can
refresh the existing UAT authentication session through the normal session-touch contract.

The earlier auth_sessions audit variance is non-blocking environment/session activity, not a
candidate regression. The table predates this feature and no authentication code changed. Its
existing `resolve_session` behavior updates `last_seen_at` and `idle_expires_at` when an authenticated
request arrives after `session_touch_interval_seconds` (default 300 seconds), as covered by the
retained authentication integration test. The earlier preservation audit retained only aggregate
row counts and digests, so it cannot establish which fields caused that exact digest change; the
current read-only UAT sign-in also exercises the intended session activity. No manual session
rewrite, UAT reset/reseed, or business-data change was performed. Therefore the variance is explained
by normal session activity to the level available, while exact historical changed-field attribution
remains unproven.


## INDEPENDENT REVIEW AND CANONICAL VERIFICATION — 2026-10-13

Independent review found no material product or domain defect. Live UAT checks covered Dashboard,
Journal, read-only History, Schedule List and Calendar, filters, source navigation, linked completion
context, and List/Calendar URL preservation. No collection, schedule, Journal or fixture record was
created, edited or removed. The authenticated read refreshed the existing UAT session under its
normal touch contract (`last_seen_at` and `idle_expires_at`); the earlier aggregate audit does not
prove the exact historical changed fields. No session was manually rewritten and no UAT reset or
reseed occurred.

The first canonical full run had three 15-second timeouts in unchanged Sowing tests under suite
load. The complete Sowing file passed 19/19 in isolation and in the successful subsequent full gate;
no test timeout or behavior was changed. Final `git diff --check` and `make feature-verify` pass.
The full gate reports 916 backend, 618 frontend and 731 PostgreSQL integration tests passing, with
formatting, Ruff, ESLint, mypy, strict TypeScript, API drift, backend/frontend production builds,
workflow/resource guards and the full `20261009_0041` migration cycle passing. No application
migration is part of this candidate. ACTIVITY-001 is verified; the reviewed candidate is ready for
local staging and commit, followed by the requested guarded delivery and finish workflow.
