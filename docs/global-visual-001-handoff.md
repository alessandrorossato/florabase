# GLOBAL-VISUAL-001 — implementation handoff

## Current delivery review — 2026-10-16

The operator has completed the authenticated Feature Review walkthrough and accepted the reviewed
GLOBAL-VISUAL-001 scope, including SeedLot as the reference Collection-family pattern. Independent QA
is complete with no material blocker found. Canonical FULL verification passed on the candidate
working tree; the verified receipt is recorded. The recorded 125%/150% captures remain
explicitly labelled viewport proxies; actual browser zoom could not be automated in the available
browser surface and is reported as a limitation, not as completed zoom evidence. Historical readiness
notes below describe the state at their respective checkpoints and are superseded by this current
status.

Candidate: `feat/global-visual-001`, based on clean current main `cd63c18`.
The candidate remains unstaged and uncommitted pending the authorized delivery steps. FULL
verification passed: 939 backend unit tests, 707 frontend tests, 735 PostgreSQL integration tests,
workflow/environment/Review ownership and fixture checks, API drift, strict typing and lint, both
production builds, and the migration cycle at `20261013_0042`. Navigation membership, routes, domain
semantics, API contracts, dependencies, migrations and actual theme behavior are unchanged.

## Visual target and audit summary

Calm, contemporary, precise botanical collection workspace; medium-compact density, white grouped
surfaces, subtle borders, restrained accent, predictable tools and pleasant data entry. Source Sans 3
and Source Serif 4 remain bundled locally. [Pre-change inventory](review/global-visual/audit.md) covers
all 22 primary route states, important creation forms and Seeds/Sowings/Plants detail/edit flows.
Findings distinguish BLOCKER, NORMALIZATION and POLISH before implementation. No product/IA defect
requires reopening the freeze.

## Design system and shared primitives

PageHeader remains the common identity/tools grammar. WorkspaceIntro now composes it. DirectoryTools
provides flexible search, existing compact Saved Views, native live filter drawers, dimension counts,
removable summaries and one creation action. DirectoryFilterSelect provides labelled native
single-select controls. State and persistence remain with their owning pages. Reset is supplied as
one page-owned operation so multiple URL fields clear atomically without stale-state overwrites.
Taxonomy tree/detail/unresolved sections now follow the shared semantic heading hierarchy.

`normalization.css` consolidates the demonstrated screen patterns; tokens add control-height,
form-width, overlay-backdrop, danger-subtle and warning-subtle. Controls retain 44px minimum targets;
search and inputs use stronger boundaries. Ordinary headings use UI sans. BotanicalName formats only an explicitly structured scientific-name
prefix, keeping the complete display label and roman cultivar suffix. Seed/Plant rows and their
identity pickers reuse already loaded identity fields through a memoized lookup; abbreviated contracts
without a structured scientific name keep their truthful existing label. No parsing or new request is added. There is no new UI framework,
asset dependency, animation or icon library.

## Dashboard and Activity

Dashboard composition, metrics and authoritative facts remain the reference. Journal, History,
Schedule List and Calendar keep their existing semantics, tools, recording/completion flows and
calendar structure. Shared control/surface changes require regression checks across all of them;
no planned/overdue work is reinterpreted as occurrence.

## Collection, lists and details

Seeds, Sowings and Plants/PlantGroups share header tools, native lifecycle/type drawers, compact
active summaries and a grouped white row surface. Results, selection, bulk Location moves,
unknown/approximate/exact quantities, dates, germination, lineage and guarded reversals retain their
existing behavior. Location search/Saved Views/scope joins the header; hierarchy and usage counts
remain intact. Harvest filters move into the shared drawer; Stored material remains its contextual
peer with its existing inventory/conversion operations. Context-only detail navigation and read-first
summary facts stay in place. Edit uses secondary hierarchy; operational actions remain explicit.

## Explore, maps and Media

Botanical identities and Geography align search, supported views and creation tools. Identity
summaries use a grouped row surface while preserving scientific names and cultivar hierarchy.
Taxonomy, Native ranges and Species distribution use native single-select representation scope;
category checkboxes retain their OR/no-selection semantics and URL state. Native ranges, occurrence
distribution and Collection origins remain distinct analytical workspaces with usable map/list areas.
No provider query is added by normalization. Media retains visual thumbnail cards and reference
metadata, with search, source/link/target filtering in the shared drawer and tokenized selection.
The missing optional WFO index is a truthful source limitation, not a fabricated classification.

## Sourcing

Suppliers and Orders align tools and operational rows with Collection. Supplier creation groups
related inputs in two desktop columns and a full-width Notes row. Order date/price/currency and
reconciliation remain unchanged; currency and price controls have bounded widths. Links, fact
alignment, secondary actions and modal typography use the shared language.

## Settings / Labels / Import Export

Settings and Labels receive shared screen-control regression checks; neither workflow is rebuilt.
Physical label dimensions, QR payloads and print content remain in their own stylesheet. Import /
Export now uses the shared PageHeader and restrained surface/padding instead of the legacy elevated
card, retaining guided templates, upload, validation, preview and result flows. Sign-in and session
recovery use the same calm surface/type grammar.

## Forms and interaction surfaces

Existing task sections and tabs remain mounted, with native validation/error associations preserved.
Collection forms use a single white 56rem maximum surface; dates/quantities/statuses use content
appropriate widths, and mobile collapses columns. Labels are close to controls and helper/error copy
uses consistent secondary type. Menus and reference pickers use semantic overlay elevation.
TaskDialog initial focus and its Tab trap now ignore hidden/inert/disabled/non-tabbable controls,
including inactive FormSections and disabled fieldsets; return focus and dismissal remain native.
Directory drawers use the same safety contract and immediate filter state as Activity.

## Empty / loading / error states

Existing factual copy, retries and validation behavior remain. Empty grouped surfaces are quiet and
readable; success/warning/error surfaces use semantic tokens and explicit text. No fabricated counts,
skeleton data or network behavior is introduced. Sign-in restoration errors remain explicit.

## Sidebar / mobile navigation / responsive / zoom

Frozen Overview, Collection, Activity, Explore (with Maps subgroup) and Sourcing membership remains.
Shared document flow retains the sticky desktop sidebar and independently reachable footer; collapse
and resize behavior remain. Mobile navigation keeps the existing native dialog; its heading stays
visible while destinations scroll. Intrinsic wrapping and bounded forms are implemented for mobile,
intermediate and desktop widths. Browser evidence and the precise limits of live candidate review
are recorded below; viewport resizing must never be reported as actual browser zoom.

## Accessibility and dark-mode readiness

Visible focus, native labels/selects, explicit text statuses and large touch targets remain central.
Behavior tests cover drawer dismissal, filter resets/search preservation, hidden-panel keyboard
containment and focus return. Shared normalized surfaces use semantic color/type/geometry tokens.
Actual Light/Dark/System theming remains outside scope. Remaining theme blockers include legacy raw
colors in capability CSS, print-specific colors and third-party Leaflet/tile/analytical palettes.

## Visual evidence and environment

`docs/review/global-visual/` contains the inventory and representative evidence. Before images come
from preserved synthetic UAT owned by `4ff7`, revision 0042, fixture v4/66. No seed, reset, source sync,
volume deletion or operator-record edit was performed. Normal browser session activity may occur.
After inspection, the existing owner helper stopped UAT and preserved its DB/media/dependency state.
Temporary task-owned previews and browser tabs were closed; no other review environment was adopted.

The candidate's separate loopback Vite preview cannot authenticate against the other owner's canonical
origin. The earlier proposed frontend-only UAT replacement never ran; original UAT frontend/backend/DB
containers remain stopped and its persistent resources are preserved. The original resource identities
are in `review/global-visual/uat-frontend-restoration-baseline.json`.

The operator subsequently authorized exact-owner removal of the obsolete `a165` Feature Review through
`make feature-review-remove CONFIRM_REMOVE_REVIEW=florabase-feature-review`. Stopped containers, absent
Review network, all three `a165` volume owners, absence of foreign volume users, and unchanged primary
Git were checked before removal. The candidate at `/home/alessandro/.codex/worktrees/996d/florabase`
then started through `make feature-review-up`. Frontend/backend/DB are healthy at
`http://localhost:15174`, migration `20261013_0042`. Its existing `owner` account was created with the
interactive supported bootstrap; credentials are not recorded in source. This Review DB is now seeded.

## Supported synthetic Feature Review dataset

The subsequent GLOBAL-VISUAL-001 request authorizes the missing `make feature-review-seed` capability.
It reuses `scripts/uat_fixture.py` v4 and its additive manual-review/domain-service extensions; it does
not copy or connect to persistent UAT data/media. Host guards require exact `florabase-feature-review`
role/project/source, owned volumes/network with no foreign users, live isolated database/media mounts,
healthy services and schema at code head. Runtime identity independently checks `florabase_review`,
development loopback authentication and `.review-identity.json`. The existing single enabled owner is
retained; no new credentials, account replacement or session fabrication are introduced.

`.review-fixture.json` and `.review-fixture.lock` live only in Review's media volume. Reruns validate
managed IDs and media hashes, preserve edits and apply recognized extensions only once. Ambiguous
nonempty collections, foreign owners, incompatible/incomplete ledgers or missing managed records/media
refuse without ordinary reset/repair. The shared fixture supplies 66 records, or 68 with the existing
approved WFO snapshot. That source remains optional, external media is intentionally offline-safe,
and no occurrence evidence is invented.

```bash
make feature-review-up
make feature-review-bootstrap-owner LOGIN=owner    # first use only; already done here
make feature-review-seed
make feature-review-status
# Open http://localhost:15174 and sign in with your Review owner.
```

The live read-only seed preflight passes for the candidate. Focused checks pass: **33** environment
workflow tests, **19 + 15** UAT workflow/source tests, **21** Review fixture tests (20 runtime guard tests
and the live seeded preservation test), and **5** existing additive fixture tests. Ruff lint/format and
strict mypy pass for the five changed/related helpers. Runtime Review guards are also included in the
existing disposable fixture smoke runner for future verification. No disposable Compose smoke or
canonical gate ran in this phase.

Automatic approval review initially rejected execution under the earlier no-fixture restriction. The
operator then directly authorized the scoped seed in chat. The first permitted run safely refused
Alembic's 287 canonical geographic references; the fresh-baseline guard was corrected and regression
tested to permit canonical references while refusing custom/operator data. Supported seed and repeat
seed now pass: **v4/66**, ready, all managed IDs/counts and media retained. A rollback-only edit probe
verifies ordinary operator edits survive repeat seed. The existing owner identity/credential hash is
unchanged. [Preservation evidence](review/global-visual/review-seed-preservation.json) confirms protected
UAT/DEV/Stable Preview/production Docker resource metadata and primary Git match the pre-seed snapshot;
no UAT record or media read was performed.

Real browser sign-in with the existing `owner` succeeded. Read-only browser inspection shows populated
Dashboard, Collection, Activity, Explore and Sourcing, and reachable Settings/Labels/tools. Screenshots
`review-authenticated-dashboard.jpg`, `review-populated-seeds.jpg`, `review-populated-journal.jpg`,
`review-populated-identities.jpg`, `review-populated-orders.jpg`, `review-settings.jpg` and
`review-labels-composition.jpg` in the evidence
directory capture the authenticated candidate, using the normal in-app browser viewport. This is
review-readiness evidence, not completion of the full operator visual/zoom matrix. The optional WFO
snapshot is absent; no taxonomy tree or occurrence evidence is fabricated. Review settings retain a
blank QR base URL, so printing still requires normal operator configuration. Review stays running.
Labels selected a seeded packet and composed one temporary label; that batch was cleared afterward.

**OPERATOR_VISUAL_REVIEW_READY** — `http://localhost:15174`, login `owner` with its unchanged Review
password. Served source `/home/alessandro/.codex/worktrees/996d/florabase`, branch `feat/global-visual-001`,
base/launched HEAD `cd63c185f7bcb0544cd9c3cff984b29564e6bc84` plus live dirty/uncommitted changes.
DB `20261013_0042`, fixture **v4/66 ready**. Full operator visual acceptance remains outstanding.

Isolated frontend test DOM may be exported as **static synthetic layout fixtures** for browser
inspection without a session, backend or auth service. Such screenshots prove CSS/markup layout only;
they do not claim an authenticated live UAT interaction or actual browser zoom. The actual unauthenticated
candidate sign-in is separately capturable through the normal real 401 response.

## Initial normalization tests and performance

All **666 frontend tests across 64 files passed**, using the unchanged checked-in Vitest configuration
with one file per process to bound host memory. App, Dashboard search, Labels and SeedLot transient
timing failures passed on unchanged reruns; no assertion, test timeout or validation was weakened.
Independent final diff review then corrected Taxonomy headings to page h2 / section h3 / subordinate
h4 and its shared surface geometry; the focused Taxonomy suite passed **7/7** with heading-level assertions. The final CSS also sets a
44px minimum target on labelled checkbox/radio rows. Final static/build checks cover those corrections. See `review/global-visual/frontend-tests.json` for the exact evidence scope. Baseline `make check` checked backend
formatting (392 files) then stopped during frontend exact-lockfile dependency installation because npm
registry requests timed out. Local package downloads also failed. Exact already-installed UAT frontend
dependencies were copied read-only into this worktree's ignored node_modules; manifests/lockfiles did
not change. Direct Node invocations use the same checked-in Vitest/ESLint/Prettier/TypeScript/Vite versions.
Earlier overlapping checks were stopped after host swap exhaustion and transient source-reading failures;
no assertions or test timeouts were weakened. Final checks run serially on formatted source.

Final frontend TypeScript build-mode checking, ESLint (zero warnings), Prettier and Vite production
build passed after the last CSS edit. Feature graph **104 valid**, `git diff --check` passed and staged
diff is empty. Markdown/evidence Prettier checks pass; an additional whole-documents probe flagged
the established expanded-array format of `docs/features.json`. That repository-wide style is retained
instead of reformatting unrelated feature entries; schema/dependency validation passes.

The Review fixture addition changes workflow/helper code only; backend production behavior, schema and
API contracts remain unchanged. Focused workflow/fixture checks cover this addition. Canonical
`make feature-verify` is explicitly prohibited and was not run.
No release CPU/RAM benchmark is claimed. Lazy screen boundaries and existing self-hosted fonts remain.
The initial normalization baseline/candidate emitted-asset comparison is in `review/global-visual/bundle-impact.json`;
it uses the same installed dependency versions and excludes runtime/network claims. Initial JS grows
by **107 gzip bytes**, all JS chunks by **2,530 gzip bytes**, and all CSS by **2019 gzip bytes**.
Font assets are byte-identical; no dependency or new runtime request is introduced.

## Deferred

Authenticated candidate visual acceptance now uses supported Feature Review and its new guarded
seed action. The seeded candidate is ready for operator inspection; the full visual walkthrough and
true-browser zoom matrix remain outstanding. The optional WFO
index-backed Taxonomy state needs that source installed in an authorized environment. Actual themes,
physical printer/label-stock acceptance, resource benchmarks, packaging/distribution, post-v0.1 workflows
and public documentation polish remain outside this increment. No domain or IA redesign is proposed.

## Acceptance state

Implementation and source review are ready as an unstaged candidate. GLOBAL-VISUAL-001 remains
**in_progress**, because authenticated candidate inspection across the required page families and
the actual browser zoom matrix are outstanding. The 15 isolated width probes, 9 passing semantic
contrast pairs and representative fixture screenshots have the limited scope recorded in the evidence
index. They do not satisfy full live visual acceptance. No canonical receipt or verified status is claimed.

## First operator page-family refinement — 2026-10-14

This pass refines Dashboard, Seeds directory, SeedLot edit and SeedLot detail in the same dirty
candidate. The earlier bundle measurements and 666-test run describe the initial normalization
snapshot, not the emitted assets or full-suite verification of this refinement. Review remains the
operator acceptance environment at `http://localhost:15174`; use the existing `owner` credentials.
Source is `/home/alessandro/.codex/worktrees/996d/florabase`, branch `feat/global-visual-001`,
HEAD `cd63c185f7bcb0544cd9c3cff984b29564e6bc84` plus the live unstaged/uncommitted candidate.

### DASHBOARD REFINEMENT

Existing search, Filters, Saved views and Quick add now use `PageHeader.tools`. At 1440×844, their
top coordinates align at approximately 46px and all controls are 44px high. Search takes the flexible
tools width; narrower layouts wrap. Snapshot metrics use label/value columns with context below.
Recent-activity metadata and titles share a line where space permits and wrap without truncation.
Section and row gaps are moderately reduced without reducing type size or control targets. With
the current fixture, all four metrics, five Upcoming entries and six recent entries are visible in
the desktop viewport; the lower support sections begin around 829px and continue by normal scrolling.
No arbitrary-volume zero-scroll guarantee is claimed.

### FILTER DRAWER

Desktop width uses `clamp(40rem, 62vw, 60rem)` with a viewport maximum. Record kinds use compact
related groups, botanical/sourcing fields two columns and geography three columns. At 1440×844 the
default drawer measures about 893px wide, with client/scroll heights both 844px. Smaller widths use
single-column groups and safe vertical scrolling. Existing real filters, dialog focus/escape behavior,
checkbox/radio semantics and API parameters are retained.

### SELECTION MODE

`Select records` sits beside the result count. Default browsing has no row checkboxes or selection
toolbar. Entering selection reveals checkboxes and a visibly bounded toolbar with count, Select
visible, Clear, Actions and Exit selection; focus moves into the toolbar. Actions is disabled at zero.
Exit clears selection and returns focus to the entry. Existing search/filter, visible-membership and
navigation resets still clear and exit; selection remains limited to eligible visible records and 100
references. Select visible refuses an oversized set rather than silently truncating it.

### BULK ACTION EXTENSIBILITY

The shared toolbar exposes an Actions menu; its sole current operation is Move to location. The
existing selection hook, atomic move request, validation, confirmation and result handling are
unchanged. Future supported operations can join this menu without changing selection mode. No new
bulk operation, speculative action registry or domain capability is introduced.

### EDIT FORM GRAMMAR

`FormSections` accepts explicit create/edit mode. Existing create behavior retains Back/Next and a
final submit. Edit keeps direct tab navigation and offers its existing submit on every section,
without Back/Next progression. Panels remain mounted, preserving dirty values; native invalid and
server field errors still reveal the relevant section. Opt-ins cover SeedLot, Sowing, Plant/group,
Provenance Site and Botanical Profile edits. Other consumers keep their prior default behavior.

### SAVE CHANGES

SeedLot shows Cancel and Save changes on all five editable sections. A real authenticated Review
save from Acquisition, with the fixture's existing values unchanged, succeeded and returned focus
to the saved record heading. This was a normal application save and may update ordinary version/time
metadata; no session/CSRF state was fabricated. Bulk Move was opened and cancelled without applying.
The SeedLot footer sticks within its form only on desktop widths above 48rem and viewport height
of at least 40rem; scroll clearance protects focused fields. Mobile and shorter viewports use an
ordinary reachable footer. Final 390×844 inspection caught fixed mobile-navigation overlap; the
desktop-only condition removes it. After scrolling, Save ends around 723px, above navigation at
780px, with its 44px height retained.

### FORM DENSITY

SeedLot uses a comfortable 60rem maximum rather than full canvas width, with existing compatible
field pairs, moderate padding and tighter section spacing. The identity picker and long textarea
content span their available columns so helpers and validation retain room. Controls retain 44px
minimum height. The width and sticky-footer exception are scoped to SeedLot; no broad form geometry
change is applied to sibling dialogs.

### SEEDLOT DETAIL

The existing breadcrumb, record header and actions form one coherent hierarchy. The detached Back
button and duplicate detail-page creation button are removed; Seeds directory and existing quick-add
routes retain creation. Browser Back and Collection/Seeds navigation remain supported. Overview has
a main column for Upcoming/conversion/notes and one white facts surface with internal dividers for
purchase, inventory, source and dates. Empty Upcoming stays compact and populated content expands.
Overview, Sowings, Photos and Lineage tabs and their actions remain intact; Photos uses the same
detail workspace width. Saved records receive heading focus.

### SHARED PROPAGATION

Count-row selection and the toolbar apply only to existing BULK consumers: Seeds, Sowings,
Plants/groups and Stored material. `DirectoryResults.actions` is optional, preserving ordinary
count-only consumers. The edit mode is shared only by genuinely equivalent multi-section saves.
The Botanical Identity outer editor retains its existing coordinator because Identity, Reference,
Native range and Media save independently; those saves do not require outer Next progression. Its
nested Profile edit now offers Save profile from every subsection. Sibling inspection confirms the
Sowing, group, site and profile save controls. Plant/Sowing/Supplier/Order details have different
content/action hierarchies, so the Seed overview grid remains local. Maps, taxonomy, media, Activity
timeline/calendar and Labels layout receive no mechanical propagation in this pass.

### RESPONSIVE / ZOOM

Authenticated browser evidence is indexed in
[first-family evidence](review/global-visual/first-family/README.md). The twelve requested states
were inspected at real 1440×844, 1024×844 and 390×844 viewports. Additional 1152×675, 960×563 and
819×675 captures approximate the effective space available at increased zoom. Those are viewport
proxies, **not actual browser zoom**. No horizontal document overflow was observed. Drawer and short
form scrolling remain available. Screenshots include mode zero/several, inspector, Essentials,
Acquisition, long Seed details, real save success, populated/empty Overview and Photos empty.

The enabled in-app browser did not apply the requested zoom shortcuts; a subsequent shortcut probe
stalled and required session recovery. Actual 125%/150% zoom remains an explicit operator check,
including text rendering, focus clearance and long-section scrolling. Readiness does not mark this
matrix accepted. Journal, Settings and Labels were checked read-only at normal desktop size, with
their existing layout and actions retained. No settings or print configuration was saved.

### TESTS

Focused refinement checks passed: Dashboard screen/search, FormSections, BulkLocation and SeedLot
**65/65 across five files**; current shared consumers **118/118 across nine files**; accepted Activity
family, Settings and Labels regressions **129/129 across five files**. The 48-test SeedLot/form/bulk
rerun passed after the final record-header change, and the final BulkLocation focus assertion passed
in its 12-test rerun. Tests cover direct saves, preserved tab values, validation reveal, creation,
selection entry/exit, zero/one/several, actions/move, resets and the 100-record bound. A prior overlapping
run exited 143; its serial rerun passed without weakening checks or timeouts.

Final TypeScript build-mode checking, targeted ESLint (zero warnings), source/document Prettier and
Vite production build pass. `git diff --check` passes and the staged diff remains empty. After an
interruption the Review frontend/backend were found stopped with the DB still healthy; supported
`make feature-review-up` recovered Review, retaining revision 0042, the owner/session and v4/66 ready
dataset. No seed/reset/remove ran. Final status identifies this dirty candidate and healthy services.
The pass's evidence index records the detailed scope.
GLOBAL-VISUAL-001 remains **in_progress**. No canonical `make feature-verify`, stage, commit, push or
delivery occurs at this handoff. UAT, DEV, Stable Preview and production remain outside this pass.

## Second operator refinement — acquisition decision boundary (resolved)

The inspection initially reported **NEEDS_PRODUCT_DECISION** before implementation of the requested Dashboard/SeedLot pass. The
requested purchased-Supplier authority is understood; its transition from existing recorded
knowledge is not yet defined. No application code, schema, record, media or environment state was
changed during this inspection. The prior first-family candidate remains available.

### PURCHASE ORDER / SUPPLIER AUTHORITY

ORDER-001 currently stores SeedLot Supplier independently. Its documented and PostgreSQL-tested
contract preserves a known lot Supplier when the selected Order Supplier is unknown, preserves
Supplier on unlink, permits purchased lots without Orders, and rejects Order Supplier corrections
that contradict linked lots. See `docs/orders.md` (Supplier consistency and shared purchase-context
review), `orders/reconciliation.py`, `orders/service.py`, and integration tests for both contracts.
Supplier hub counts/links and collection projections also consume the direct SeedLot reference.

Purely hiding the Supplier picker would leave the old authority and conflict behavior in place;
changing the invariant without a retention policy could hide or erase known facts. The necessary
product decisions are:

- How existing purchased lots with a direct Supplier but no Order retain that recorded knowledge,
  without inventing a purchase transaction or silently clearing it.
- How existing lot Supplier knowledge is retained when an Order is unknown/cleared or the lot is
  unlinked, while the commercial Supplier display becomes Order-derived.
- Whether Order Supplier corrections replace the current linked-lot conflict rule, and how the
  old independently confirmed fact remains recoverable.

No migration is proposed or asserted necessary yet; the storage/transition policy must be explicit
first. This boundary comes from the operator's instruction to stop when broader model semantics
are ambiguous, not from an additional permission requirement.

### UNCERTAIN ORDER DATE

The existing Order model already accepts all descriptive fields as unknown, including null
PartialDate, Supplier, reference and total/currency. An actual transaction can be explicitly created
with incomplete facts; no synthetic date or placeholder-order domain is needed. Acquisition date
remains separate, with the existing optional reviewed copy action. This portion is not blocked by
schema limitations.

### DASHBOARD V0.1 SCOPE / FUTURE DASHBOARD V1 REVIEW

The requested next v0.1 scope is PageHeader/search, Collection snapshot, Attention/Upcoming and Recent
activity, removing Propagation/Sourcing/Botanical coverage from rendering only. It is not implemented
at this decision boundary. The roadmap now records an unscheduled post-v0.1/v1.0 review of configurable
modules, operator-selected widgets and additional summaries; no controls or customization are added.

### EDIT MODAL / DETAIL OVERVIEW / PHOTOS

The requested route-aware edit workspace, background-context preservation, direct-link full-page
fallback, acquisition/origin summary separation and compact attached media remain pending this pass.
Existing TaskDialog, recordNavigation, SeedLot edit/purchase paths and OrderPicker were inspected.
No speculative modal/history or media abstraction is added before resolving the semantic boundary.

### REVIEW / TESTS

Read-only `make feature-review-status` confirms frontend/backend/database healthy, source `996d`,
branch `feat/global-visual-001`, HEAD `cd63c185f7bcb0544cd9c3cff984b29564e6bc84` plus existing dirty
changes, DB `20261013_0042`, fixture v4/66 ready, at `http://localhost:15174`. Review remains running.
No restart, reset, seed, removal or UAT action ran. This inspection introduces only documentation;
no new runtime/test result or completed responsive/accessibility acceptance is claimed. Canonical
verification remains prohibited; work remains unstaged/uncommitted.

## Second operator refinement — implementation after product decision

The operator resolved the boundary: **Order Supplier is contextual UI authority when known and
linked; SeedLot Supplier remains independent persisted knowledge and fallback.** The earlier request
for full Order authority is superseded. ORDER-001's original persistence and reconciliation contract
is retained, without a migration or backend/API change.

### DASHBOARD V0.1 SCOPE

Dashboard now renders PageHeader/search/tools, Collection snapshot, Attention/Upcoming and Recent
activity. Propagation, Sourcing and Botanical coverage modules and their unused presentation rules
are removed. Their service/API data and domain tests remain intact; this does not remove those
capabilities. No empty placeholder module or customization control replaces them.

### FUTURE DASHBOARD V1 REVIEW

The product roadmap records an unscheduled post-v0.1/v1.0 review after actual use, including possible
configurable modules, operator-selected widgets and further summaries/metrics. None is implemented.

### PURCHASE ORDER / SUPPLIER AUTHORITY

Acquisition adapts to the existing facts. With no Order, Supplier stays independently editable. With
a known linked Order Supplier, it displays read-only as **From linked Order**, with purchase-context
review available. It does not render a competing ordinary Supplier picker. With an unknown Order
Supplier, the independent picker/recorded fact remains, labelled as retained lot knowledge; neither
known produces explicit Not recorded information. Loading/failure never pretends that Order Supplier
is unknown; the transaction's existing retry path remains available.

The original reconciliation service still handles blank/matching/conflicting Suppliers. A mismatch
requires explicit reconciliation; Order correction still refuses conflicting linked lots. No hidden
bulk synchronization is added. Unlink removes only the Order relationship: Source, confirmed
SeedLot Supplier and acquisition date remain. Supplier never populates provenance, biological origin,
native range or Location. The overview reads current Order context separately from recorded lot facts.

### UNCERTAIN ORDER DATE

Order date, Supplier, reference and total can retain the existing unknown states. **Create Order
(new tab)** opens the existing Order form through its supported create route; Refresh Order choices
then reloads the selector. Nothing automatically creates a transaction, date or price. Acquisition
date stays independent and copies an Order date only through the existing explicitly reviewed action.

### EDIT MODAL WORKSPACE

SeedLot is the first contextual-edit consumer. `EditWorkspace` reuses native TaskDialog, while
`useEditRoute` adds one normal edit entry using existing hash-route helpers. Desktop editing is
bounded to 60rem/88dvh. Header and direct section tabs remain above an internally scrolling panel;
Cancel/Save remain below it. Existing create progression stays outside this change. No other entity
editor is migrated. Seed context-creation tasks now also use native TaskDialog so they can appear
above the workspace without a competing custom focus trap.

### EDIT ROUTING / BACKGROUND CONTEXT

Opening Edit from Details leaves the same Detail component and active tab mounted underneath.
Opening from directory/inspection keeps that workspace, filters/search and inspector underneath.
Save updates the existing entity data, closes the edit entry and restores focus to its trigger.
Cancel restores that same context. Dirty dismissal asks before discarding; pending writes and active
purchase/context subdialogs refuse parent dismissal. A reviewed acquisition Apply still saves those
fields immediately under ORDER-001, and only remaining form drafts are considered unsaved.

Browser Back closes a clean modal before leaving the background. A refused dirty Back restores the
existing forward entry before App reads the departure, retaining the draft without replacing history
or adding an entry. The hook does not maintain an alternative route stack or persist fake background
state. Normal directory/detail helpers continue to own source URL state.

### DIRECT EDIT FALLBACK

Direct `#/seeds/<id>?tab=edit` and `?action=edit` URLs render the same editor as a full-page fallback.
Reload/bookmark/external navigation does not fabricate a background. Canonical Details remains a
normal full page. Full-page Cancel returns to that record; contextual Cancel returns to its actual
background, including an active Photos tab.

### DETAIL OVERVIEW / ACQUISITION SUMMARY

Upcoming activities and natural-height Notes remain primary context. The secondary **At a glance**
summary groups Inventory, Acquisition, Origin and Dates & condition with compact responsive facts.
Purchase Order belongs inside Acquisition beside Source, Supplier and acquisition date; Origin
contains only material provenance/site. Unknown facts stay explicit. Empty Upcoming remains compact.
Overview/Sowings/Photos/Lineage and exact Order/Schedule/identity/action links remain supported.

### PHOTOS COMPACTION

Photos opts into a compact presentation of the existing shared PhotosSection. Its header has compact
Add media/Link existing/External actions. Cards use a thumbnail and concise metadata, explicit primary
status, discoverable Open media details and an overflow for primary/edit/unlink actions. Existing
unlink confirmation remains; no media deletion is silently performed. Remote previews still require
Preview once; protected local copies and attribution keep their existing behavior. Default consumers
retain their original DOM composition through fragments, so other page families are not restyled.

### ACCESSIBILITY

Native dialog semantics supply the editor title and background modality. The preserved Seed context
also has explicit inert/aria-hidden while its edit modal is active. Focus enters the editor, cycles
through visible controls and returns to the original Edit trigger. Escape shares dirty/pending
dismissal rules. Body/workspace scrolling is locked while modal panels scroll. Mobile uses a viewport
surface in the top layer above bottom navigation, with safe-area action padding. Existing native
validation/section reveal, server errors and direct section saves remain covered.

### TESTS / RESPONSIVE / ZOOM

Final focused runtime results: **43 SeedLot tests** and **30 Dashboard/Photos/Order/reconciliation UI
tests** pass. Coverage includes modal origin/context, preserved Photos component/tab, Save/Cancel,
focus containment/restoration, dirty Escape/Back, clean Back, unchanged history length on refused
Back, direct edit URLs, every-section Save, Supplier adaptation/unknowns/unlink/date preservation,
compact media management and retained standard media workflows. Backend persistence/schema/API code
is unchanged, so no new PostgreSQL behavior or migration verification is claimed.

The additional Order create-route test submits an explicit real Order with null date, Supplier,
reference, total/currency and notes; no request occurs before the operator's Create action.

An overlapping lint/test run under exhausted host swap caused transient unrelated loading timeouts;
serial core reruns pass without changing assertions or timeouts. The DashboardSearch first-load
timeout recurred alone: its behavior suite now awaits the real lazy-module import in beforeAll,
keeping every assertion and timeout unchanged. Its final 13 tests pass. Final source/static/build and live
responsive evidence are recorded separately below. The earlier first-family captures do not prove
this new modal/media layout, and actual 125%/150% zoom remains an operator check unless explicitly
recorded as completed.

### FINAL REVIEW EVIDENCE / LIMITS

The second-family [evidence index](review/global-visual/second-family/README.md) records seven states
at six viewport sizes (42 captures; saved geometry covers 12 Dashboard/Overview cases), actual
native-modal focus/scroll checks, normal authenticated
Save back to Photos, clean browser Back and the retained directory inspector. The final route hook
also observes App's parsed route and explicitly closes on completion; TaskDialog receives the actual
Edit invoker for reliable focus restoration.

The Acquisition captures precede the final scoped checkbox alignment rule. A later browser-control
URL-policy rejection prevented refreshing those screenshots; they prove the recorded interaction
and geometry, not final checkbox styling. Actual browser zoom at 125%/150% remains an operator check;
effective-space proxy captures are labelled explicitly. No browser-policy workaround was attempted.

Review source remains the dirty worktree `/home/alessandro/.codex/worktrees/996d/florabase`, branch
`feat/global-visual-001`, base HEAD `cd63c185f7bcb0544cd9c3cff984b29564e6bc84`. Use the existing `owner`
login and its unchanged password/session at `http://localhost:15174`. Review retains revision
`20261013_0042` and synthetic dataset v4/66, covering the requested Collection, Explore, Sourcing,
Activity and utility walkthrough; optional WFO setup and QR printing configuration remain explicit
operator requirements. This is readiness for operator inspection, not completed visual acceptance.

No backend/API/schema change is introduced by this second UI refinement. UAT/DEV/Stable/production
were not changed. No reset/remove/reseed, canonical verification, staging, commit, push or delivery.

Final validation (2026-10-15): **107 tests pass across nine suites** (73 core and 34 shared
regressions). TypeScript, targeted ESLint with zero warnings, source/document Prettier, production
Vite build and `git diff --check` pass. The final Vite SeedLot chunk is 45.04 kB / 12.19 kB gzip;
main index is 227.78 kB / 70.80 kB gzip. See `second-family/validation.json` for exact suite counts.
Supported recovery and final `feature-review-status` confirm frontend/backend/DB healthy, current
candidate live source, revision 0042 and v4/66 ready. The staged diff remains empty. Feature status
remains **in_progress** pending operator visual acceptance and separately authorized canonical gate.

## Consolidated SeedLot / Dashboard refinement — 2026-10-15

This section supersedes the earlier refinement descriptions for the current SeedLot family.
The consolidated operator contract preserves the same dirty `996d` candidate and ORDER-001
persistence. Sowings/Plants visual review has not begun.

### DASHBOARD FINAL V0.1 SCOPE

Dashboard renders identity/tools, Collection snapshot, Attention & upcoming and Recent activity.
Propagation/Sourcing/Botanical coverage remain absent from rendering, with their services intact.
The wider organized filter drawer and live filter semantics remain. No customization is implemented.
Live 1440x844 checks now show all high-value sections and the populated filter drawer without avoidable scrolling.

### SEEDS DIRECTORY / QUICK PREVIEW

Seeds and Sowings now opt into `directory-preview.css`, using the established Sowings directory
split: primary list 1.3fr and preview 0.8fr with a 16rem minimum above the existing mobile breakpoint.
The Seeds-only 21rem cap is removed; both use the same intrinsic proportional allocation and existing
stacking/detail behavior. Preview content, selection eligibility, Select records, generic Actions,
Start sowing, Open details and Edit are unchanged. No Sowing detail/form redesign is included.

### DETAILS FULL-WIDTH WORKSPACE / OVERVIEW HIERARCHY

SeedLot overrides the inherited 70rem detail-pane cap and centered margins; the workspace uses the
available width after the sidebar and normal page gutters. Breadcrumb/header/actions/tabs and all
four tabs share that shell. Internal Overview retains primary Upcoming/Notes beside one At a glance
surface with Inventory, Acquisition, Origin and Dates & condition. Notes text is bounded to 65ch;
empty Upcoming and Lineage remain compact. No narrow width is imposed on the whole entity page.

### EDIT MODAL / BACKDROP DISMISSAL

Edit remains contextual above the actual mounted directory/preview or Details tab. Direct edit URLs
retain the full-page fallback. EditWorkspace now opts into TaskDialog's existing backdrop dismissal:
clicks outside bounds share Cancel/Escape/Back's dirty/pending policy and focus restoration. Pristine
and rejected/accepted dirty backdrop tests preserve Photos and return focus to the actual trigger.

### EDIT TAB CLIPPING / HIERARCHY

The audit found a shrinking grid row around wrapped tabs and no left inset for focus rings in the
scrolling panel. Editor navigation now reserves intrinsic height, includes eight-pixel focus clearance,
and stays outside the scrolling panel. Selected and hovered tabs explicitly use primary-subtle/green
text/subtle border, overriding generic primary-button hover. Save retains the primary action fill.
Panel controls have focus padding on every side. First/last focused tabs now have six-viewport live evidence without clipping. Actual browser zoom remains operator acceptance.

### ACQUISITION CONDITIONAL UI

Source precedes a two-column Find an Order/Order chooser, with compact Create/Refresh/all-Suppliers
controls. With no Order, independent optional Supplier and PartialDate fields appear immediately below
those controls. With any linked Order, ordinary Supplier/date inputs are absent; transaction Supplier
and Order date are read-only and retain actual precision or explicit Not recorded/Date unknown.

A concise **Recorded on this seed lot** summary always exposes retained independent Supplier/date
knowledge alongside linked context. Unlink restores those same editable values. Linking/Apply still
uses the existing authoritative preview, explicit conflict/date choices and stale versions. No dates,
Suppliers or Orders are inferred, silently overwritten or synchronized. Backend/API/schema unchanged.
The default standalone OrderPicker transaction presentation remains available to other consumers.

### PHOTOS MINI-GALLERY / GALLERY HOVER / FOCUS / TOUCH

The SeedLot-only compact presentation now uses image-first tiles in an intrinsic auto-fill grid with
14rem minimums and consistent 4:3 image areas. Normal thumbnails use object-fit:cover. Captions/type,
quiet Primary and saved-copy indicators remain concise; detailed attribution/source/management live
in media details and the existing editor/menu. Default Photos consumers retain their standard DOM.

Local/saved/previewed images with asset identity link directly to their media details. A restrained
Open hint appears on hover or focus-within. The named overflow button remains visible and works with
keyboard/touch, including Open, metadata edit, primary designation and confirmed unlink. Focused
image links draw their ring inside the image boundary so rounded cropping does not cut it off.
No persistent large action row, decorative scrim, animation or hover-only function is introduced.

### EXTERNAL IMAGE PRIVACY

An unpreviewed external reference shows a compact External image/host/privacy disclosure and explicit
Preview once. No remote image element is created before that action. Saved copies remain protected
same-origin thumbnails. Previewed external images share the tile geometry and existing no-referrer,
loading/error/retry behavior. The host remains available as text; detailed metadata stays in media
management. No remote image was fetched during automated unit checks.

### LINEAGE SEMANTICS

Lineage remains a read-only tab over the existing API. Root lots may have no upstream path; recorded
producer Plant/PlantGroup ancestry retains exact ancestor links. Botanical identity, location,
Supplier, photos and Harvest existence do not generate ancestry. Added SeedLot root/producer cases
cover the projection request and navigation; no lineage/domain code or inferred edge is added.

### RESPONSIVE / ZOOM / ACCESSIBILITY / REMAINING OPERATOR ACCEPTANCE

After the operator reopened Review, a fresh authenticated HTTP tab worked. The completed matrix
contains 60 cases: ten states at 1440x844, 1152x675, 960x563, 1024x844, 819x675 and 390x844.
The reduced dimensions are explicitly **effective-space proxies, not actual 125%/150% browser zoom**.
Actual zoom remains an operator check where browser tooling cannot set it.

Every retained probe has no horizontal document overflow. At 1440x844, ordinary linked/no-Order
Acquisition panels have clientHeight=scrollHeight=414px. Live inspection found inherited fieldset
margins, legend margins and action padding; scoped overrides and a compact transaction/retained-facts
row removed that waste. Unknown dates and Supplier independence remain unchanged. Shorter viewports
scroll only the form panel, with actions retained. Quiet detail-tab hover also keeps navigation contrast.

The gallery's first tile spans about y344-627 at 1440x844, with header, tabs and Photos tools above it.
Keyboard and mobile overflow, metadata-editor cancellation and image-to-media-details navigation
work. Native modality/inert background/focus wrapping, pristine backdrop, clean Back to Photos and
focus return are recorded. Dirty backdrop produced the expected discard prompt; its rejection
outcome was not captured live and remains a focused-test/operator check. A normal save of unchanged
Basil values returned to Photos with Edit focused and no fallback; version/time metadata may update.
After the fresh direct-edit tab, normal CSRF protection rejected the first save; cancelling and
reloading the main tab through the normal auth flow resolved it. No session/CSRF state was fabricated.

A final regression exposed a timing window where a contextual close could launch the direct URL
fallback before history.back completed. Contextual edit entries are now marked handled; the existing
missing-history-event test also asserts no fallback reopens. Fresh direct Edit still renders full-page.

Read-only sibling captures cover Sowings directory/preview, History, Settings and Labels. No sibling
visual redesign began. The reviewed SeedLot has a single gallery item and no upstream producer; the
seeded external asset is linked to a Plant. Multi-item/external gallery and producer SeedLot states
have focused tests but no fresh live fixture capture. No new fixtures, links or inferred ancestry
were introduced for screenshots. The QR base URL remains unconfigured; no printing acceptance is claimed.

See [third-family evidence](review/global-visual/third-family/README.md). All screenshots/probes describe
their actual scope. Actual zoom, dirty-prompt refusal and unavailable fixture states remain operator
acceptance; this is readiness for manual visual review, not feature verification.

### TESTS / ENVIRONMENT BOUNDARY

The first changed-surface run passed 64 tests (SeedLot 45, Photos 11, OrderPicker 4, Lineage 4).
Shared regressions passed 138 tests in ten suites: Dashboard 4, DashboardSearch 13, FormSections 5,
ReferenceInteractions 4, History 9, Labels 54, Media 18, PurchaseContext 7, Settings 5, Sowings 19.
Final source/static/build results and exact limitations will be recorded in the third-family index.
No backend persistence/API/schema change requires a new PostgreSQL/migration/API-drift claim.

Feature Review remains candidate-owned at localhost:15174, schema 20261013_0042, v4/66 ready, existing
owner/session retained. No reset/remove/reseed, persistent UAT/DEV/Stable/production action, stage,
commit, push, delivery or canonical feature-verify. Feature remains in_progress.

Final code checks for this refinement: **202 tests pass in 14 suites**, strict TypeScript,
zero-warning targeted ESLint, Prettier, production build and diff whitespace pass. Minor new-test
lint issues were corrected without changing assertions or timeouts. The staged diff is empty.
The [third-family validation](review/global-visual/third-family/README.md) now includes the live
matrix, interactions, final checks and remaining operator acceptance. Earlier pending-browser notes
are historical; the browser block was resolved by the fresh HTTP tab.

Final live-refinement validation: **202 unique tests in 14 suites pass**, including the 45-test
serial SeedLot rerun after the route/fallback guard. Nearly full host swap caused intermediate
unrelated loading/time-limit failures; serial verification passed with unchanged assertions and
timeouts. Final strict typing, targeted zero-warning lint, formatting, production build and diff
whitespace pass. Review is left available for manual inspection; feature remains in_progress and
canonical verification has not run.

## Final SeedLot-family refinement — 2026-10-16

This section supersedes earlier SeedLot create, Overview and external-create presentation notes.
The accepted Photos mini-gallery remains intact. No broad Sowing or Plant redesign has started.

### CREATE SEEDLOT FULL-PAGE FORM

Add seed lot uses the workspace width after the sidebar and normal responsive gutters, with
Collection / Seeds / New breadcrumbs and a concise description. Identity, Inventory, Acquisition,
Origin and Seed details form one ordered page with headings/dividers, genuine desktop pairs and
single-column mobile flow. Every existing field remains, including the optional persisted lot label.
Cancel and Add seed lot end the form. There are no create tabs, Next or Back. Validation retains values,
focuses the first mapped invalid field and places an explanation in its visible section.

### CREATE VS EDIT GRAMMAR

Create opts into shared FormSections page presentation. Edit retains the guarded native modal over
its invoking directory or Details context, quiet tabs, retained draft and reachable Save / Cancel.
Direct Edit still has the existing full-page fallback. Both presentations use the same fields,
quantity/uncertainty rules and server payload. Other create coordinators keep their existing behavior.

### PARTIALDATE ALIGNMENT

The shared PartialDateField now uses stacked precision and fixed three-part slots beneath it. Unknown,
Year, Month and Day keep the same horizontal geometry. Independent Supplier/date controls align their
control rows without a full-width date grid child. Normal linked and Unknown states fit at desktop
1440x844 (414px client and scroll height); known date parts use 55px of safe internal panel scrolling.
Tabs/actions remain outside that scrolling panel. Shared consumers audited: Order, Sowing, Plant,
Journal Event, Harvest and inventory/conversion forms. Schedule uses native date-only fields, with
its existing semantics unchanged. Exact focused regressions are indexed below.

### DETAIL OVERVIEW DASHBOARD GRAMMAR

At a glance starts with a restrained lifecycle / quantity / storage summary. Acquisition and Origin
have lead facts and contextual links; Dates & condition use compact inline facts and a divider.
Upcoming activities and Notes retain natural-height primary context. Reading/DOM order matches the
responsive visual order. All authoritative dates, links, provenance and retained lot knowledge remain.
The UI contract records: entity Overview = small current-state dashboard, not a read-only edit form.
No sibling Overview has been redesigned.

### SOWINGS DUPLICATE ACTION REMOVAL

Removed only Start another sowing from the Sowings tab. The upper entity Start sowing remains, with
linked sowing navigation, lifecycle, quantity used, date, germination and location content preserved.

### EXTERNAL MEDIA DEFAULT LOCAL COPY

Audit result: Photos and Media external creation previously saved reference metadata only. Preview
once loads a remote browser image and does not persist a snapshot. Existing explicit safe-copy
operations publish protected URLs correctly; controlled PostgreSQL tests prove the actual Photos HTTP
response after saving, reload and refresh. No backend explicit-save persistence defect was reproduced.

New Photos and Media-editor external creation now default the checkbox Save a local copy in Florabase
ON. Existing reference creation/linking is committed before the explicit guarded copy request, so a
failed fetch can retain the reference/link. A successful copy refreshes the Photos list / Media result.
Gallery and Quick Preview use protected local URLs. Photos remote-preview state is keyed by snapshot
URL, so a previous remote load failure cannot masquerade as a saved-local failure after replacement.
The accepted mini-gallery layout was not redesigned.

### REFERENCE-ONLY OPT OUT

The operator can uncheck Save a local copy in Florabase. Explicit help explains that this retains an
external reference only. No copy request is sent. Historical reference-only assets remain unchanged
until an explicit existing Save local copy action. No background fetch, migration or new fixture.

### MEDIA FETCH FAILURE

Photos reports External reference saved. Local copy could not be downloaded, with Retry save using
the same asset. The Media editor offers Retry save or Keep reference only after partial success;
it cannot repeat reference creation on retry. A post-save list refresh failure is distinguished from
a download failure. Existing SSRF/address pinning, redirect, MIME, byte-size, image/pixel validation,
authentication and protected-storage behavior remain unchanged. No arbitrary live external hosts were
contacted. Controlled tests cover download persistence; existing synthetic protected media proves UI.

### LINEAGE EMPTY ALIGNMENT

Empty Lineage uses the normal tab gutter and a small intentional text treatment, without the generic
dotted full-width box. Recorded upstream relationships, ordering, lifecycle and destination links
are unchanged; no lineage is inferred from identity or current state.

### SEED DIRECTORY QUANTITY HIERARCHY

Remaining quantity is emphasized immediately after row identity, ahead of secondary storage context:
48 seeds remaining, About 80 seeds remaining or Quantity unknown. Historical lots retain the Recorded
quantity qualifier, exact known zero stays exact and approximate values retain their qualifier.

### DENOMINATOR DECISION

The persisted SeedLot model/API contain current quantity only; no stable original-quantity baseline
exists. No ratio, percentage, progress bar, fake zero or reconstructed historical denominator was added.
Corrections, transfers and history are not repurposed as a baseline.

### RESPONSIVE / ZOOM

[Final SeedLot evidence](review/global-visual/final-seedlot/README.md) indexes 57 saved observations with
no horizontal document overflow. Create top/actions and all four independent date precisions plus
linked Acquisition cover 1440x844, 1152x675, 960x563, 1024x844, 819x675 and 390x844. The smaller desktop
sizes are explicitly viewport proxies for 125%/150% zoom; real browser zoom was not available and
remains operator acceptance. Overview and empty Lineage cover 1440 / 1024 / 390. Additional captures
cover first/last edit tab focus, Sowings, protected Photos, external default/opt-out, quantity rows and
Order PartialDate. No create or external-media data was persisted during this live pass.

Browser automation stalled on Escape/cancellation in an unsaved Order draft; the successful Order
month geometry capture is retained, but that cancellation is not claimed as a passed live check.
Sibling date semantics and recovery remain covered by focused tests. Dirty native-prompt acceptance
and actual zoom remain manual checks. Review stopped during the pause and is restarted only through
its supported, ownership-guarded workflow, preserving its existing volumes and dataset.

### TESTS

Final focused, shared-consumer, backend/PostgreSQL and source/build results are recorded in the
final-seedlot evidence index and JSON summaries. Feature status remains in_progress. Canonical
feature-verify, staging, commit, push and delivery remain explicitly unperformed. Review remains the
candidate-owned environment; UAT, DEV, Stable Preview and production are untouched.

Final validation for this pass: **270 unique frontend tests in 17 suites**, **69 backend unit tests**
and **15 disposable PostgreSQL tests** pass. Strict TypeScript, targeted ESLint with zero warnings,
Prettier, production build and whitespace checks pass. Sowing interaction setup now preloads its
component; separate App.lazy coverage passes, with no weaker assertions or timeouts. Historical
failed-run summaries remain labelled and superseded in the evidence. Final bundles: SeedLot
45.60 kB / 12.39 kB gzip; main 227.89 kB / 70.84 kB gzip. Final supported Review status confirms all
three services healthy, schema 20261013_0042 and managed v4/66 ready. The existing owner is signed in;
normal manual login uses the unchanged Review password. Temporary viewport overrides were reset.
The final `operator-ready.png` shows authenticated Overview at normal 1280x720. Candidate source is
`/home/alessandro/.codex/worktrees/996d/florabase`, branch `feat/global-visual-001`, base HEAD
`cd63c185f7bcb0544cd9c3cff984b29564e6bc84` plus all current dirty/uncommitted edits.


## Detail empty states and required labels — 2026-10-16

### DETAIL TAB EMPTY-STATE GRAMMAR

Informational Details tabs use `.detail-empty-message`: the normal tab gutter, muted readable text,
natural content height, no border or minimum height. Empty SeedLot Sowings reads “No sowings use this
seed lot yet.” Root Lineage reads “No recorded upstream material lineage.” Recorded lineage and its
links are unchanged. The same plain pattern replaces read-only related-record placeholders in
Botanical identity, Supplier and Order details. Directory/search empties retain their own grammar.

### PHOTOS EMPTY-WORKSPACE EXCEPTION

Photos retains its restrained dashed gallery placeholder and Add media / Link existing / External
actions. The surface explains a visual media workspace. No gallery, upload, map, persistence or
external-copy behavior was redesigned in this pass.

### REQUIRED FIELD LABELING

The small caption-only `FieldLabel` renders a muted 12px semantic-token asterisk; it does not own
controls, validation, values or submission. SeedLot Botanical identity is required in Create/Edit.
Source and Lifecycle have backend defaults and remain unmarked. Lot label, quantity as a whole,
storage, Purchase Order, Supplier, dates, provenance and notes remain nullable; Purchased does not
require Supplier. Schema requirements were audited before caption propagation.

### OPTIONAL LABEL SIMPLIFICATION

Removed redundant optional suffixes from current form labels and contextual creation controls.
Temperature retains its °C unit. Meaningful prose about optional coordinates and the CSV field guide
remain. There is no repeated required-field legend and no permanent validation/error styling.

### CONDITIONAL REQUIREMENTS

PartialDate itself may stay Unknown; Year/Month/Day parts become marked and ARIA-required only at the
selected precision. Explicit Sowing quantity requires Amount (and Unit for weight); known PlantGroup
quantity requires Count. Order price and currency dynamically require one another and can both stay
blank. Existing conditional movement destinations, originating Sowing, external attribution/URLs and
media privacy confirmation retain their native rules. No native `required` expression changed. Location’s Used for group is marked as requiring at least
one selection, with its existing rule exposed as the fieldset description; individual checkboxes
remain independently optional.

### ACCESSIBILITY

The marker is hidden from the accessible name, with native `required` or `aria-required` on the actual
control exposing the state independently. A required ReferencePicker remains ARIA-required after a
valid selection while retaining its original native free-text constraint. Labels/IDs, descriptions,
keyboard behavior and validation timing remain intact. Notes tests now distinguish textareas from
read-only regions and tab panels that share the simpler name.

### SHARED FORM PROPAGATION

Applied the proven caption pattern to existing clear requirements in auth, identity/reference search,
Supplier, Location/Geography/provenance, Sowing/PlantGroup quantities, Harvest/inventory, Schedule,
Journal movement, Media/Photos and label Copies. Settings QR base URL remains optional because blank
is valid. This is label/empty-state normalization; no Plant/Sowing visual redesign or form framework.

### TESTS

Final focused results, source checks and responsive evidence are indexed in
[labels/empty-state evidence](review/global-visual/labels-empty/README.md). Candidate remains dirty,
unstaged and uncommitted on `feat/global-visual-001`, base HEAD
`cd63c185f7bcb0544cd9c3cff984b29564e6bc84`. Feature remains in_progress; canonical verification, stage,
commit, push and delivery are not authorized. Existing Feature Review resources/data are preserved;
UAT, DEV, Stable Preview and production are untouched.

This pass passes **448 unique frontend tests across 27 files**, plus **15 final Location regressions**.
Strict TypeScript, targeted zero-warning ESLint, 47-file Prettier check, production build and whitespace
checks pass. The final staged diff is empty. All mandatory views were checked at 1440x844, 1024x844
and 390x844 at 100%, with 29 saved observations and no horizontal overflow. Feature Review remains
authenticated and running at http://localhost:15174; normal manual login uses `owner` and the unchanged
Review password. The final normal-viewport capture is `labels-empty/operator-ready.png`.


## SeedLot reference dashboard, compact Photos and connected pickers — 2026-10-16

### OVERVIEW DASHBOARD HIERARCHY

SeedLot now proves the candidate entity-dashboard grammar: one current-state summary band, semantic
information sections, operational context, then notes. Acquisition/Origin and Dates/Upcoming are
separated by restrained rules, consistent section headings and deliberate gaps. No read-only form
labels or repeated widget cards. Other entity Overviews were not migrated.

### AT-A-GLANCE SUMMARY STRIP

The single subtle summary band has three desktop columns: Lifecycle, Remaining/Recorded quantity and
Storage. Values appear above quieter explanatory labels, using semantic definition-list markup.
Lifecycle retains its badge; Storage remains a navigable full path. Exact, approximate, unknown and
historical quantity meanings are unchanged; no ratio or historical denominator was invented.

### OVERVIEW SEMANTIC GRID

Wide desktop uses Acquisition / Origin, then Dates & condition / Upcoming activities. Notes span the
final row, with readable natural-width prose. Acquisition retains source, Supplier provenance and
Order link/state; Origin wraps the complete geographic/site path in normal body typography. Dates
are compact term/value rows preserving PartialDate precision and Unknown values. Upcoming activities
retain their authoritative records/actions and natural empty/populated height. Harvest conversion
history remains available in its own full-width operational row when applicable.

### PHOTOS HEADER SIMPLIFICATION

Compact SeedLot Photos keeps its section name for assistive technology through a visually hidden
heading. The repeated visible heading and global saved-copy helper paragraph are removed. The action
row aligns right directly beneath the Details tabs; the gallery begins immediately after it. The
accepted empty gallery placeholder remains. Default Photos consumers retain their presentation.

### PHOTOS CONTEXTUAL PRIVACY

External tiles retain their own host, privacy explanation and explicit Preview once action. Live
Lavender Photos shows this without a remote img source; the remote host was not contacted during this
pass. Locally saved Basil media remains protected. Media/link/external creation, primary selection,
reference-only opt-out and safe-copy failure/retry behavior are unchanged and covered by regressions.

### PICKER POPUP ALIGNMENT

The previous popup used the entire field as its containing block, including helper text and stretched
grid space: the observed Add SeedLot identity gap was 45.984px. A small control-only relative wrapper
now anchors the shared ReferencePicker menu 4px from the input at the same width. Transient styling,
botanical option typography and existing row density remain. The menu has bounded internal scrolling,
fits the viewport/enclosing scroll panel and can open above when necessary. The old Bulk dialog
in-flow positioning exception was removed so this shared menu no longer pushes that form down.

### SHARED PICKER REGRESSION

Live checks cover Add SeedLot Botanical identity, Storage location and Supplier at all three sizes,
plus the unchanged Plant create identity picker. All measured popups match input width and have a
4px gap. Native Order search/selection and native Plant/Sowing location fields remain native; they
were inspected rather than redesigned. Live Supplier Arrow navigation and Enter selection close the
menu with focus retained; the temporary choice was cleared without saving. Escape consumes an open
picker before the enclosing task, and internal option selection restores input focus. Listbox IDs,
expanded/active-descendant state, required semantics and selection callbacks remain covered.

### RESPONSIVE CHECKS

[Dashboard/picker evidence](review/global-visual/seed-dashboard/README.md) records the actual
1440x844, 1024x844 and 390x844 viewports at 100%. Wide desktop has three summary columns and a two-column
semantic grid; 1024 collapses the lower sections and mobile uses one readable column throughout.
Both populated and empty activity states, exact/approximate stock, long origin, notes, protected media,
external privacy and empty Photos are captured. There is no horizontal document overflow. Temporary
viewport overrides are reset; no records or media were saved, linked, removed or fetched remotely.

### TESTS

Focused SeedLot, Photos/Media, shared ReferencePicker, Order and representative Plant/Sowing/Bulk/
Labels consumer regressions pass **247 unique tests across 13 files**. The updated Overview test checks
individual date terms/values instead of old layout whitespace. Picker tests cover opening, Arrow/Enter
selection, Escape priority, focus return and ARIA state without pixel assertions. Source/build details
and supported Review health are retained in the evidence index. No backend/API/schema/migration change
was needed. Candidate remains dirty, unstaged and uncommitted; GLOBAL-VISUAL-001 stays in_progress.
Canonical feature-verify, stage, commit, push and delivery remain unperformed. Review resources and
existing dataset are preserved; UAT, DEV, Stable Preview and production were not operated on.
