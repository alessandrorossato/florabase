# COLLECTION-VISUAL-002 — visual-review candidate

## Current refinement — operator feedback, 2026-10-18

The same candidate now includes the requested follow-up. [Third-pass evidence](review/collection-visual-002/third-pass/README.md)
supersedes the earlier directory, New Harvest and Location parent-menu images.

- Harvest/Stored material rows match Plants' text roles: normal serif titles, lighter italic scientific
  names, sans metrics and state badges. The Harvest empty preview and directory proportions use the
  accepted Collection treatment. Stored-material buttons align with row identity, have proper gutters,
  and use 10px corners; Location rows and expansion buttons use the same normal radius.
- New Harvest's first Material and Source type controls share the exact top coordinate on desktop.
  Material, unknown Quantity and Description share equal left/right edges. Known quantities still
  use their grouped controls and mobile stacking.
- Locations has State: Active/Retired/All, default Active, composed with search/scope and retained by
  URL and Saved Views. Counts are matching records; necessary ancestors remain structural context.
  Manual expansion survives state switches, retired Details remain reachable, and excluded records
  cannot remain as a stale Quick Preview.
- Contextual Edit Location uses the established ReferencePicker for Parent location, with wrapping
  full paths and menu width equal to its input (558px desktop, 320px mobile in the fixture). Explicit
  root selection and server cycle/lifecycle guards remain. Typed but unselected parent searches cannot
  silently save a root assignment. Escape first closes the reference menu, then the dialog.
- Backend scope is one Saved Views state allowlist field (`active|retired|all`) plus contract tests.
  There is no new Location query, schema, migration or inventory/hierarchy business rule. The generic
  Saved Views JSON API shape is unchanged; existing views without State inherit the active default.
- Focused evidence: **186 distinct frontend tests / seven files**, including an additional final
  Location/StrictMode subset, and **85 backend Saved Views contract/service tests**. Ruff and focused
  mypy pass; frontend lint, format and strict production build are recorded in the evidence index.
- Nine new live viewport captures cover desktop/mobile rows, alignment, active/retired state and the
  bounded parent menu. Live observations did not submit domain edits. Review was not reset or reseeded;
  persistent UAT was not touched. Candidate remains unstaged and uncommitted; no canonical gate or delivery.

Operator acceptance remains required. Native dirty-confirmation and true zoom limits from the previous
pass still apply; the current parent menu was exercised live and cancelled without saving.

## Second-pass record — 2026-10-17

The same dirty candidate is ready for operator review at [Feature Review](http://localhost:15174),
login `owner`; the existing Review-only password was supplied in chat. No credentials are stored here.

- Worktree: `/home/alessandro/.codex/worktrees/fb05/florabase`.
- Branch: `feat/collection-visual-002`; unchanged HEAD `a36c6cffb938c5ed20f93942e1eac1070897962c`.
- Review: candidate-owned `florabase-feature-review`, revision `20261013_0042`, fixture v4/80.
- No reset, removal, reseed, persistent-UAT operation, staging, commit, push or delivery in this pass.
- Feature remains `implemented`. Canonical `make feature-verify` was explicitly not run.
- [Second-pass evidence](review/collection-visual-002/second-pass/README.md) supersedes earlier images
  for the refined surfaces. Earlier evidence remains available for full-page creation and media.

## HARVEST SELECTED STATE

Harvests, Locations and the accepted Seed/Sowing/Plant rows share one selection rule in
`collection-directory.css`: primary-subtle background, 3px leading accent, neutral boundaries.
The old Harvest selection outline is suppressed by that shared rule. Keyboard focus has its own
visible ring and remains distinguishable from selection.

## HARVEST DIRECTORY

Rows retain the complete 4rem media tile, Source Serif title, italic scientific name and right-hand
occurrence date/material summary. Source prose is removed from the row. Actual kinds are summarized
as two plus a truthful additional-kind count. Tablet/mobile rows open Details directly.

## HARVEST QUICK PREVIEW

Media, title, botanical identity, source/date, concise materials and Open details/Edit remain in that
order. Reduced paragraph spacing keeps the ordinary preview within the desktop viewport. Existing
Harvest-primary/source-primary/botanical/placeholder resolution and remote-image privacy are preserved.

## HARVEST DETAILS

The overview band, compact collected rows, compact stored rows and lower Notes/Related history grid
read as one material dashboard. Collected quantity remains historical; stored remainder remains a
separate operational fact. At real 1440×844, the one-line fixture's Notes/History grid ends at about
766px. Shared Photos follows below and makes the entire document taller than one viewport; it is not
claimed to fit. No collection, Event, quantity, source-correction or media semantics changed.

## HARVEST EDIT

Contextual EditWorkspace now has Details, Materials and Notes tabs, mounted fields and a stable footer.
Details groups source type, source, optional label and occurrence date. Both Details and the one-line
Materials panel have equal client/scroll heights at 1440×844 (465px), with no inner scrolling. Multiple
lines, smaller screens, validation and zoom may scroll. Full-page creation and direct-edit fallback
remain available. Errors reveal and focus the relevant material panel without resetting input focus
on subsequent typing. Existing dirty, pending and dismissal guards remain.

## MATERIAL ROW GRAMMAR

Visible labels are Material, Quantity and Description. Quantity kind/value/precision share a desktop
row; numbers and precision retain row-specific accessible labels. Weight retains its unit control.
Mobile stacks controls in logical order. Exact/approximate/unknown values, item UUIDs, ordered add/remove,
100-line bound, source correction and payload shape are preserved. Occurrence-date precision retains
its accessible name while the redundant visible subtitle is hidden.

## STORED MATERIAL DIRECTORY

Fixed the collapsed-column defect: the shared three-column row now receives media, identity and metrics
as three actual children. Measured identity widths are approximately 914px/498px/264px at 1440/1024/390.
Rows show material/source Harvest title, scientific identity, state, remaining quantity and storage.
Search, Filters and dialog Saved views are grouped together; the filter drawer and removable chips
use DirectoryTools. Result count and BULK selection remain. This directory retains its existing direct
link to source Harvest Details rather than adding a second preview interaction. Print/conversion remain
reachable outside selection mode. Unknown stock displays Unknown quantity, never inferred zero.

## STORED MATERIAL ACTIONS

Eligible active seeds have an intrinsic-width Create Seed lot button. Record disposition is secondary.
Per-line More contains Print label, Edit stored material and Remove tracking only when eligible.
Tracking with dispositions remains retained; conversion and disposition histories remain available.
Inventory correction/removal dialogs explicitly restore focus to the stable More trigger rather than
a removed popover item. No page-level action absorbs an item-specific operation.

## SEED CONVERSION

The contextual two-column task places compact definition-list source facts and conversion quantities
on the left, resulting Seed lot fields on the right. Target quantity precision and viability precision
keep accessible names without duplicate visible labels. The ordinary unknown-remainder fixture has
741px client/scroll height at 1440×844, with footer visible. Mobile source context precedes resulting
fields and the footer remains reachable. Exact subtraction, explicit approximate remainder, unknown
preservation, use-all, producer identity, Location scopes, eligibility, atomic creation and guarded undo
are unchanged; all nine conversion tests pass.

## LOCATION DIRECTORY

Hierarchy, expansion, capped indentation, deep parent context and full-path titles remain. Only nonzero
occupied categories appear in short structured metrics. A descendant contribution is explicitly marked
`incl.`; accessible names carry both inclusive and direct counts. No ancestor usage is represented as
direct assignment. Twelve-level behavior remains covered by App tests; the live fixture has six added
nested shelf levels.

## LOCATION SELECTED STATE

The same shared leading-accent rule applies to Location rows; indentation and expansion controls remain
separate. Full green selected rectangles are removed. Keyboard focus remains visible.

## LOCATION QUICK PREVIEW

Name/path, state/scopes and child count precede concise usage comparisons. Open details spans the action
area; Edit and Create child use equal secondary geometry. Complete direct/inclusive comparisons remain
accessible. Retired records preserve their state and eligibility.

## LOCATION DETAILS

The compact State/Parent/Children band precedes Hierarchy/Enabled scopes on the left and Collection
usage on the right. Child links, explicit scope non-inheritance, all five usage categories, active/total
counts and both assignment columns are preserved. Introductory copy and browse links are shorter.
The representative root ends around 803px in a real 1440×844 viewport; document height is 844px.
Reparenting, retirement/deletion guards and aggregation logic are unchanged.

## FILTER NORMALIZATION

All four Collection families use DirectoryTools, immediate filters, common drawer spacing, reset,
removable chips and dialog Saved views grouped with search. The existing capabilities are:

| Directory       | Existing typed filters, in display order              | Explicitly deferred                                               |
| --------------- | ----------------------------------------------------- | ----------------------------------------------------------------- |
| Seeds           | Lifecycle                                             | Botanical identity, Location, Supplier/Source/Order filters       |
| Sowings         | Lifecycle                                             | Botanical identity, Location, source Seed lot/germination filters |
| Plants          | Lifecycle, Record type                                | Botanical identity, Location, origin filters                      |
| Harvests        | Botanical identity, Material, Source type             | Lifecycle does not apply; no Harvest Location is inferred         |
| Stored material | Botanical identity, State, Storage Location, Material | No new API filtering                                              |

The `list_all` Seed/Sowing/Plant APIs and frontend list functions accept no typed identity/Location
query parameters. This pass does not add backend parameters or promote free-text search to a new exact
filter contract. Harvest exact identity filtering and stored-material projection filtering remain as
already supported. Drawer tests enforce actual field availability and preserve search when removing a
Lifecycle/State chip. Harvest has no copied Location and no Location filter.

## RESPONSIVE

[31 second-pass captures](review/collection-visual-002/second-pass/README.md) cover all requested desktop
states, representative 1024×844/390×844 directories, details, editing, conversion and nested Locations.
No measured document is wider than its viewport. Stored text remains readable at all three widths.
1152×675 and 960×563 are explicitly labelled 125%/150% viewport proxies, not actual browser zoom.
Temporary viewport settings were reset in the recovered operator tab. Small screens and proxies
naturally scroll; one-page targets apply to the ordinary desktop fixture only.

## ACCESSIBILITY

Semantic tabs retain mounted inputs, accessible row numbers, hidden precision labels, native-invalid
field reveal, error focus, selection semantics and keyboard focus. Tests cover dirty Escape, backdrop,
Cancel, browser Back refusal/acceptance, successful Save focus and stored-menu dialog return focus.
Live clean editing and responsive captures ran before a dirty-Escape attempt stalled the browser's
CDP input channel; its confirmation was not exposed through the dialog API. A fresh candidate tab was
opened for review and read-only evidence. Live dirty confirmation, later keyboard input and Save are
therefore **not certified** by this pass and remain operator checks. No domain mutation was submitted.

## TESTS

Second-pass successful focused results total **316 distinct tests across 15 files**:

- App **78**, HarvestScreen **15**, StoredMaterial **20**, Conversion **9**.
- PlantScreen **58**, SeedLotScreen **50**, SowingScreen **31**.
- Dashboard, SavedViews, BulkLocation, ReferenceInteractions/EditWorkspace, FormSections,
  DirectoryTools, PartialDateField and recordNavigation: **55 across eight files**.

The long shared command completed all three page-family suites before exiting 143. Its eight remaining
suites were run separately and passed. Presentation assertions now follow the filter drawer, definition
list and More menu; domain, quantity, conversion and retention assertions remain intact. Added Back/Save
checks use the fixture's actual optional label, not its derived display title. No timeout or guard was
weakened. Strict TypeScript and production Vite build passed. Final targeted ESLint, touched-file
formatting, feature-graph validation and whitespace checks are recorded in the evidence index.

No backend application/API/schema/migration/dependency code changed. PostgreSQL and canonical full
verification were not run. Earlier Review-only fixture work remains in the candidate; this second pass
neither changed nor reseeded that fixture.

## OPERATOR ACCEPTANCE REMAINING

Accept the visual hierarchy and density, especially stored rows, selection, tabbed correction, conversion
and desktop fit. Complete live native dirty-confirmation/Back/Save checks and true 125%/150% browser zoom
if available. One earlier Review browser tab may still hold the unsubmitted synthetic dirty draft;
close/dismiss that browser view if its native confirmation remains blocked. The fresh operator view
shows persisted data. Actual canonical verification and delivery require a later authorized phase.

READY_FOR_VISUAL_REVIEW
