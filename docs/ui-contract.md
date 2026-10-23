# Florabase UI Foundation v0.1

Authoritative contract for Florabase UI. Dashboard and Activity establish the reference grammar;
GLOBAL-VISUAL-001 extends it to the frozen v0.1 directories and task surfaces. Implementation: `frontend/src/styles/tokens.css` (single token source),
`foundation.css` (base/shell/primitives), `normalization.css` (shared screen grammar), `ReferenceUI.tsx` and `WorkspaceUI.tsx`.

> New Florabase UI must consume semantic design tokens and shared primitives.
> Feature implementations must not invent local colors, typography scales,
> spacing systems, interaction surfaces or page-header patterns without an
> explicit extension of the UI contract.

## Direction

A botanical scientific workspace: calm, precise, medium-compact, collection-oriented and suitable
for everyday work. Prefer meaningful records, dates and unknown states over promotional metrics.
Use typography, spacing and dividers before adding surfaces. No gradients, glass, decorative icons,
fake trend arrows, garden-center greens, colored-card grids or nested card soup.

## Semantic colors

| Token             | Value   | Use                                        |
| ----------------- | ------- | ------------------------------------------ |
| background        | #F6F7F3 | Page                                       |
| surface           | #FFFFFF | Primary surface                            |
| surface-subtle    | #EEF1EC | Sidebar, subtle grouping                   |
| surface-hover     | #E7EDE6 | Interactive hover                          |
| text              | #1E2621 | Primary text                               |
| text-muted        | #667068 | Secondary text                             |
| border            | #DDE3DC | Decorative separation                      |
| border-strong     | #7C8980 | Control boundaries where required          |
| primary           | #2F684F | Actions, active navigation                 |
| primary-hover     | #24533E | Hovered primary actions                    |
| primary-subtle    | #E7F0EA | Selected background                        |
| success           | #2F7D57 | Explicit success                           |
| warning           | #A66A16 | Attention marks/borders                    |
| warning-text      | #85520C | Small attention text; AA on light surfaces |
| danger            | #B54747 | Error/destructive intent                   |
| info / focus-ring | #3D6F8E | External/informational context, focus      |
| on-primary        | #FFFFFF | Text on solid primary                      |

Status always has text, never color alone. The slightly darker `warning-text` is the sole palette
accessibility adjustment: baseline warning is not used for small text. Existing `--color-*`,
`--accent-*`, `--muted` and `--font-editorial` aliases resolve to the semantic source. Do not copy
raw values into new feature CSS. A subtle divider is not sufficient to identify a form input;
use border-strong when the boundary is the distinguishing control cue.

## Typography and scientific names

UI: Source Sans 3 Variable, with system sans fallback. Botanical accent: Source Serif 4 Variable,
with Georgia fallback. Both are exactly pinned Fontsource 5.3.0 packages (2026-07-19 release),
OFL-1.1, served from bundled same-origin WOFF2 assets with font-display swap. Runtime needs no CDN.
Font licenses are also shipped under `/licenses/`. The package release-age policy is unchanged.
See [Fontsource Sans](https://fontsource.org/fonts/source-sans-3/about) and
[Serif delivery](https://fontsource.org/fonts/source-serif-4/use).

| Semantic token          | Size/line height in px | Weight    |
| ----------------------- | ---------------------- | --------- |
| type-display (rare)     | 40/44                  | 650       |
| type-h1 (page title)    | 32/38                  | 650       |
| type-h2 (section)       | 22/28                  | 650       |
| type-h3 (subsection)    | 17/24                  | 650       |
| type-body / type-strong | 15/22                  | 400 / 600 |
| type-small              | 13/18                  | 400       |
| type-label              | 12/16                  | 600       |
| type-eyebrow            | 11/16, tracking .08em  | 650       |
| type-metric             | 32/36, tabular numbers | 650       |

Use semantic font shorthand tokens; do not invent a scale. PageHeader uses UI sans, not serif.
Use `.scientific-name` only around the scientific-name portion: `<i className="scientific-name">
Ocimum basilicum</i>`, followed by a roman cultivar epithet when present. Do not italicize full
operator labels, cultivar names, authorities or all taxonomic ranks automatically. Existing
legacy editorial usages are not a mandate for new UI.

## Spacing, density, geometry and elevation

4/8/12/16/24/32/48/64 px via space-1/2/3/4/6/8/12/16. Medium-compact: list rows use 12px
vertical padding, metric surfaces 16px, related sections 24–32px. Radius-small 6px, normal 10px,
large 14px. Default surfaces use borders, no shadow. Overlay elevation only:
`0 8px 32px rgb(30 38 33 / 16%)`. Controls are not pills by default.

## Page grammar and shared components

AppShell → Page → PageHeader → optional PageToolbar → PageContent → optional DetailPanel.
These are semantic regions, not a requirement to build a component for every wrapper.
Reuse PageHeader from ReferenceUI: optional eyebrow, title, optional concise description, actions.
For the Activity family, its optional `tools` slot gives PageHeader two regions: PageIdentity
(eyebrow, title, short subtitle) and PageTools (search, Filters, supported Saved views, primary action).
ActivityPageHeader composes that slot with the existing Dashboard toolbar and native filter drawer.
Identity and tools use flexible bases and wrapping: wide layouts share one row, tools wrap as available
space shrinks, and mobile places identity first. Search retains a practical basis and fills remaining
space; buttons remain compact. Available width, including actual browser zoom, drives adaptation.
The shell owns the brand h1; page titles are h2, sections h3, subordinate headings h4.
`Page`, `SectionHeader`, `Metric`, `StatusBadge`, `EmptyState`, `LoadingState`, `ErrorState`
are the small immediate vocabulary in WorkspaceUI. A source badge uses StatusBadge with literal
Journal/History text, not a separate styling system. Existing StatStrip, FormSection/FormActions,
RecordPreview, DirectorySearch, OverflowMenu and TaskDialog remain available.

Metric: concise label, tabular value, explicit qualifier, navigable destination. Directory
navigation must not suggest a filtered result if the destination does not support that filter.
Rows use meaningful links, metadata and source labels; partial dates retain their precision.
Empty sections remain visible with factual explanations. Loading does not show fabricated zeros;
errors offer retry and authentication expiry returns to the existing session flow.

## Page archetypes

| Archetype           | Primary organization                                          |
| ------------------- | ------------------------------------------------------------- |
| Dashboard           | Current summary, attention, recent facts, supporting counts   |
| Directory / List    | Header, search/filter toolbar, bounded list, optional preview |
| Detail              | Identity, read-first facts, contextual actions and sections   |
| Create / Edit       | Explicit task, grouped fields, save/cancel, validation        |
| Activity / Timeline | Source/date semantics, chronological entries, filters         |
| Map Workspace       | Map plus usable list/selection context                        |
| Tree Workspace      | Hierarchy plus selected-node detail, keyboard path            |
| Schedule / Calendar | Intended work, date windows and explicit state                |
| Utility Workspace   | Focused inputs, operation and result                          |
| Compare / Review    | Source/target evidence, explicit selection/apply              |

These archetypes guide page organization; analytical maps and trees retain their specialized
workspaces within the common visual grammar.

## Interaction surfaces

- Popover: compact contextual actions/selection/mini filters, never a complex form. Outside click
  and Escape close it. Escape/action dismissal returns focus to the trigger; clicking or tabbing
  to another control preserves that intentional focus destination. Reuse OverflowMenu.
- Dialog: short blocking decision, destructive confirmation or small atomic task. Escape/backdrop
  only when safe; pending/dirty/destructive states must not disappear accidentally. TaskDialog
  provides native modal focus containment and return focus; the caller owns dismissal safety.
- Drawer: secondary inspector/preview, medium editing or advanced filters that preserve context.
  Do not invent a drawer merely to avoid a real detail page. Dashboard advanced filters reuse
  TaskDialog's native modal handling in a right-side drawer; choices apply immediately, reset
  preserves search text, and Escape/backdrop/Close return focus without reverting filters.
- Full page: important deep-linkable objects, many fields, independent state or substantial work.
- Contextual edit workspace: SeedLot proves a substantial native modal above its existing directory
  or canonical Details page. Preserve the mounted background, active tab, filters and trigger; block
  background scrolling and scroll long form panels inside bounded desktop geometry. Keep direct
  section tabs and Cancel/Save available. Narrow mobile may use the viewport above bottom navigation.
  Dirty/pending dismissal is guarded; Back closes the edit entry before departing. Direct edit URLs
  and reloads use the same full-page editor without a fabricated background. Reuse EditWorkspace and
  the normal record-route helper only for equivalent editors selected in a later pass.
- Inline disclosure: small local secondary information. Native details/summary is appropriate.

## Accessibility

AA contrast, semantic heading order, visible focus (3px focus-ring with 3px offset), real buttons
for actions and links for navigation, meaningful names, logical focus order. Interactive borders
must meet non-text contrast when needed. Do not rely on hover or color alone. Main touch controls
retain approximately 44px targets; compact text links have clear spacing. No new motion; honor
prefers-reduced-motion. Long labels wrap, numbers never clip, content remains available at zoom.

## Responsive behavior

Review at 1440×844, 1024×844 and 390×844. Dashboard uses four metrics on desktop, two at ≤64rem;
attention/recent columns become one at ≤48rem. Supporting sections reflow to one at ≤64rem.
Dashboard uses document scrolling and the available workspace width; no independently trapped
content panels. Its sidebar remains sticky on desktop. The toolbar orders flexible Search,
Filters, Saved views, Quick add and wraps on mobile. Quick add reuses OverflowMenu; SavedViews
can use its optional compact dialog presentation with the same state/routing and CRUD behavior. Mobile uses the existing
shell navigation, reachable actions and naturally growing rows. Inspect representative old
Directory, Detail and Schedule screens whenever global base/shell styles change. GLOBAL-VISUAL-001
normalizes their shared screen grammar while retaining the specialized workflows.

## Do / don't

Do: “3 active groups; size may be unknown.” Don't: silently convert groups into plant totals.
Do: “Journal · recorded 11 Oct (UTC)” when occurrence is unknown. Don't: assign an occurrence date.
Do: a section heading and ruled list. Don't: wrap every heading, row and badge in another card.
Do: consume primary/text/space/type tokens. Don't: add a feature-specific green or font scale.
Do: show planned overdue work in Schedule. Don't: present completion as an event that occurred.

## Activity recording and timeline pages

Journal/History/Schedule reuse the Dashboard control grammar and native right-side filter drawer:
flexible Search, Filters, supported adjacent Saved views, compact removable active-filter summary.
Use concise page subtitles. Journal's + Record action belongs in PageTools and uses OverflowMenu.
Schedule's primary creation action is in PageTools; List/Calendar belongs in the local view heading,
with month identity and temporal navigation in Calendar and count/identity alone in List.
Schedule has no Saved Views contract. Structured Journal choices navigate
to delivered canonical forms; notebook choices reuse contextual Journal creation. History has no
primary mutation action and uses concise source labels/links, not repeated product prose.

Operational lists prefer a grouped white surface with compact rows and subtle dividers over an
oversized card per short record. Schedule preserves its due-date buckets; chronology keeps original
order/precision without forcing uncertain dates into relative-day groups. Borders carry structure;
shadows are restrained and reserved for overlays. Row secondary actions use OverflowMenu, including
inside a modal where the menu remains in that modal's interactive subtree and Escape closes it first.

Activity pages use the available desktop width and document scrolling with intrinsic wrapping.
Newly touched pages must adapt to available width, including actual browser zoom. Review Dashboard
as reference and Activity at desktop 80/100/125/150%, tablet 100/125%, and 390×844 mobile, including
PageTools, date columns, drawers, row actions and Calendar. Sidebar/global normalization stays deferred.

Activity filters apply live, following Dashboard: one Reset filters / Done footer, including a valid
single Timeline year. Multi-valued dimensions use native checkbox fieldsets with compact two-column
wide grids and one-column narrow grids. Empty selection means unrestricted, not a selected All
pseudo-value. Preserve existing default-query contracts when encoding unrestricted state using real
supported values. Filters (N) counts restricting dimensions consistently; search stays separate.
Compact dimension summaries are removable and reset preserves query and local representation/period.
Content-sized Activity drawers cap at the viewport and scroll fields while keeping their footer
reachable. All dismissal routes restore focus to Filters. This is a narrow Activity contract update;
Dashboard interaction and the broader product remain unchanged.

## Labels, Settings and frozen workspace navigation

Labels is a document-flow workspace with Print as the final primary action. The chooser/selected
list keeps useful recorded context and hides UUIDs. Physical sheets contain only exact-record QR,
scientific botanical name, optional roman cultivar/common name and a tiny category glyph.
Operational metadata and classification hierarchy do not print or contribute to overflow warnings.
Presets explicitly define cell/type/QR dimensions; paper scales on screen while print retains mm.

Settings is one focused page with General and Tools; Labels → Print format retains explicit Set as
default / Default. Public QR URL stays server persisted in General. Labels → QR destination Edit
opens a small TaskDialog for the same setting, with shared validation/save, pending/dirty dismissal
protection and return focus. Save updates QR in place without losing the batch or temporary preset.

Primary navigation remains Overview, Collection, Activity, Explore and Sourcing. Maps is a plain
subgroup with three children; plant groups and Stored material stay local modes. The footer places
signed-in identity above labelled sliders Settings and a quiet appearance cycler, then
separate Sign out. Hidden/collapsed desktop navigation reopens access; mobile More retains the same
controls and shared appearance state. Modified-click links and existing route semantics remain.

The appearance control cycles System → Light → Dark → System and applies immediately, preserving
the selected palette. Monitor/sun/moon, accessible name and shared Tooltip describe the current
preference (including the effective System mode) and next action. Settings → Appearance offers
Botanical, Herbarium and Mineral independently from System/Light/Dark, using labelled native radios
and compact previews. One browser-local store synchronizes both footer controls, Settings, reloads,
authentication transitions, operating-system changes and other tabs. There is no backend write.
CONTROLS-001 supplies one local SVG vocabulary, shared action adapters and accessible Tooltip.
Settings uses horizontal sliders, distinct from the funnel Filters and monitor/sun/moon Appearance.
See [THEMES handoff](themes-001-handoff.md) and [Controls handoff](controls-001-handoff.md).

Secondary icon buttons keep explicit accessible names and concise hover/focus descriptions. Labels
return at phone/tablet widths and on coarse/no-hover devices; mobile Appearance is always labelled.
Filters and Saved views stay labelled at every width; supported active-filter badges count restricting
dimensions. Primary creation, Save and destructive/domain confirmations retain immediately readable
text. Shared actions have 44px minimum targets, 18px decorative icons (20px in the shell), 1.75 strokes
and semantic theme colors. Native links, refs, disabled states and existing domain callbacks remain.

Tooltip appears after 500ms fine-pointer hover or immediately on keyboard focus-visible, allows 150ms
pointer transfer, and dismisses on activation, blur/leave or Escape without moving focus. It supplements
the trigger name through `aria-describedby`; it is not a menu or essential-only help. Manual popovers
and dialog-local fixed hosts avoid clipping; placement flips/shifts within the visual viewport.
Escape dismisses Tooltip, then menu, then dialog. No motion or additional keyboard stop is introduced.
See [Controls contract](controls-001-design-contract.md) for the canonical action matrix and exclusions.

## Directory and task normalization

Collection, Botanical identities, Geography and Sourcing use the same intrinsic PageHeader tools
slot. WorkspaceIntro delegates to PageHeader while retaining its context-only detail header mode.
DirectoryTools owns presentation only: pages retain search, filter, pagination, URL and Saved View
state. Search flexes from a practical 14rem basis; Filters, supported Saved views and
one primary creation action wrap naturally. Saved views uses its existing compact dialog mode.
Single-select lifecycle/type/scope controls use labelled native selects. Advanced directory filters
use a native right drawer with live application, removable dimension chips, Reset filters and Done;
reset clears every dimension together while preserving search. No unsupported filter or Saved View
capability is added for symmetry.

A directory is one grouped semantic surface with row dividers and a subtle selected inset edge.
Rich Media summaries retain thumbnail cards; maps retain their analytical area. Directories and
reference workspaces use document flow; the desktop sidebar remains sticky and its destination list
scrolls independently. A preview may remain sticky with its own bounded height. Important task forms
use one semantic surface with a 56rem default maximum (60rem for the proven SeedLot editor), existing semantic sections and tabs, two columns where
reading order permits and one column on mobile. Date/quantity/currency controls use narrower widths.
Edit is a secondary action; Save/Create/Complete remain primary, and destructive intent uses danger.

Existing BULK directories place **Select records** beside their result count. Selection mode reveals
checkboxes and a visible toolbar: selected count, Select visible, Clear, Actions and Exit selection.
Actions contains only supported operations (currently Move to location); future operations can join
the menu without changing mode entry/exit. Zero selection disables actions, historical eligibility
and the 100-record bound remain authoritative, and scope/membership/navigation changes clear and exit
the mode. Entry focuses a usable toolbar control; exit restores the directory entry control.

Sectioned **create** workflows may use Back/Next/Create when progression helps. Sectioned **edit**
workflows use direct tabs with Cancel and Save changes on every editable section, retaining drafts
and revealing the exact invalid/error section. `FormSections` opts into edit mode explicitly; create
wizards and coordinators with independently saved nested sections retain their existing behavior.
SeedLot edit proves a restrained sticky footer inside the form at sufficient viewport height, with
scroll clearance for fields/focus; shorter viewports use an ordinary reachable action row. This sticky
geometry and SeedLot detail's main/facts grid remain local pending equivalent sibling visual proof.

Shared controls retain a 44px minimum target and the existing radius/space/type scales. Page and
ordinary section titles use UI sans; serif/italic remains for structured scientific names. Inputs and
search use border-strong; overlays use elevation-overlay and overlay-backdrop. Danger/warning subtle
surfaces are semantic tokens. Physical label geometry and print typography remain owned by Labels.
Native dialog focus excludes inactive hidden panels, disabled fieldsets, inert descendants and
negative tab stops. Sign-in and recovery use the same quiet surfaces and type hierarchy.

THEMES-001 centralizes six approved semantic color sets in `styles/tokens.css`; dimensions and type
remain shared. Capability colors consume these roles. Map comparison identities and provider density
ramps retain their scientific meaning; third-party imagery and botanical photographs are not inverted.
Print explicitly uses white paper and black text/QR with existing physical dimensions. Independent
visual/accessibility acceptance and later Origins integration remain bounded as recorded in the handoff.

## SeedLot family refinement

Seeds and Sowings share the existing proportional directory/Quick Preview split through
`directory-preview-layout`; the list remains primary and mobile retains its existing adaptation.
SeedLot Details uses the available content width, with readable internal prose/summary columns.
Other detail families remain unchanged pending independent visual review.

The contextual SeedLot editor treats backdrop, Cancel, Escape and Back as the same guarded dismissal.
Section navigation reserves intrinsic wrapped height and focus clearance; subtle selected/hovered
navigation stays visually subordinate to Save. Only panels scroll in the bounded editor.

SeedLot attached media uses the opted-in compact image gallery: stable 4:3 cover thumbnails, concise
identity/badges, image-to-details links, and an always reachable named overflow for keyboard/touch.
Hover/focus adds a quiet Open hint. External references disclose host/privacy and require Preview
once before creating a remote image. Default Photos consumers retain their current presentation.

### SeedLot create, dates and Overview reference

SeedLot **Create** is a canonical full-page workspace with one ordered form: Identity, Inventory,
Acquisition, Origin and Seed details. All sections stay visible, the persisted optional lot label is
secondary to Botanical identity, and Cancel / Add seed lot end the form. It opts into `FormSections`
page mode; other existing create coordinators retain their progression. **Edit** remains a contextual
modal with direct section navigation and persistent actions; a direct edit URL retains its full-page
fallback. Both presentations share the same controlled values, validation and domain payload.

Shared PartialDate controls reserve one precision column and place Year / Month / Day parts beneath
it in fixed slots. Precision changes must not move adjacent fields horizontally or infer omitted
parts. Independent SeedLot Supplier and acquisition date use aligned title/control slots. Normal
Unknown and linked-Order Acquisition fit the desktop editor; known parts can scroll inside its panel.

Candidate reusable principle: **entity Overview = small current-state dashboard, not a read-only edit
form**. SeedLot proves a compact lifecycle / remaining quantity / storage summary, readable Acquisition
and Origin context, and inline Dates & condition. Upcoming activities and Notes have natural height.
This principle is documented for later Plant/Sowing/Supplier/Order review; their Overviews are unchanged.
Quantity progress requires an authoritative persisted baseline. SeedLot has only current quantity, so
its directory uses exact / approximate / unknown remaining quantities without a denominator or ratio.

New external images created through Photos or the Media editor default to **Save a local copy in
Florabase**. Explicit opt-out retains a reference only. Creation reuses existing reference/link and
safe-copy operations; failed downloads retain the saved reference and offer Retry save. A saved copy
renders through protected same-origin thumbnails/content; Preview once remains an explicit remote
browser-only choice for references. Historical references are unchanged until explicit copy saving.

### Detail empties and form labels

Informational Details tabs with no records use a concise message aligned to the normal content gutter,
without a border, card, minimum height or filler illustration. SeedLot Sowings and root Lineage are the
reference examples. A visible empty workspace is appropriate when the area itself explains an
interactive or visual collection: Photos retains a restrained gallery placeholder and its Add media,
Link existing and External actions. Map canvases and upload workspaces retain their meaningful surfaces.

Form captions use `Label *` only when that field is required by the existing domain validation in the
current form state. Optional captions use `Label`, without an optional suffix. The shared `FieldLabel`
renders a quiet semantic-token marker; controls independently expose native `required` or
`aria-required`. Do not add native validation merely to obtain a marker or turn required captions into
errors. Preserve explanatory prose about unusual optional semantics.

Conditional captions follow their controls: known PartialDate parts, explicit quantity amounts/units,
Order price/currency pairing, movement destinations and external-media attribution. SeedLot identity
is required; its defaulted Source/Lifecycle and nullable Supplier remain unmarked, including Purchased
source. Create and Edit share these rules. A checkbox group requiring at least one choice marks its legend
and exposes the existing rule through its group description; do not require every checkbox. No
repetitive required-field legend is necessary.

### SeedLot dashboard and transient picker reference

The refined SeedLot Overview is the candidate grammar for later entity pages: one current-state band
with stronger values above quieter explanatory labels; then semantic information sections and
operational context, followed by natural-width notes. Desktop uses three summary metrics and a
restrained two-column lower grid, with dividers rather than individual cards. Narrow screens collapse
the sections; mobile stacks the band and content. Full origin paths wrap at body size. Date terms and
values preserve exact/partial/unknown knowledge. Other Overviews await their own product review.

Compact SeedLot Photos uses the tab as its visible title and retains an accessible section name. Its
right-aligned media action row precedes the gallery without global helper prose. Privacy/remote-load
explanation belongs to the individual external tile and Preview once action; local media needs no
repeat warning. The gallery-empty workspace remains the intentional exception to plain detail empties.

ReferencePicker popups anchor to a control-only wrapper, with a 4px separation, input-aligned width,
existing transient-surface styling and bounded internal scroll. They fit the available viewport or
clipping panel and can open above the input. Help text and field grid stretch must never determine
popup position. Preserve label association, listbox IDs, required/expanded/active-descendant state,
Arrow/Enter selection and focus. Escape first dismisses an open picker before its enclosing task.
Native selects remain native; this normalization does not introduce another picker framework.

## Sowing and Plant normalization candidate

COLLECTION-VISUAL-001 applies the accepted SeedLot directory split, coherent page creation and
contextual EditWorkspace to Sowings and Plants, pending operator visual acceptance. Direct edit links
retain the full-page fallback. Current-state Overview bands expose Sowing lifecycle/date/germination/
location and Plant lifecycle/location/entry precision, followed by actual domain sections. Do not
invent SeedLot-style inventory or current measurements for individual Plants. Percentages remain
specific to exact positive Sowing seed-count denominators; null, zero and uncertain quantities retain
their existing meanings. PlantGroup only participates in the existing shared workflows.

Contextual propagation entry also shows its fields together; SeedLot's separate seed-usage review
remains a meaningful inventory decision before its atomic operation.

Both families use the same compact PhotosSection as SeedLot. Compact gallery styling now belongs to
PhotosSection; privacy and local-copy behavior remain unchanged. Narrow record tabs wrap, modal Save
stays reachable and returning from Edit restores its trigger without refocusing the Overview. These
sibling geometry rules stay scoped to Sowing/Plant workspaces; other detail families await review.

Second operator pass: Collection rows follow Botanical Identity's full 4rem tile and beside-tile
identity, with only lifecycle/entity metrics on the right; source/date/Location remain in previews
and Details. Create uses the available workspace with semantic columns; contextual Edit uses a compact
identity header and stable action footer. Overview recaps material relationships and links to canonical
Lineage; graphs belong on Lineage. Existing reversal eligibility lives behind a secondary header action
and a focused native dialog. A small shared DetailEmptyState replaces large absence panels for reviewed
Seed/Sowing/Plant detail content and shared Photos/Lineage. These refinements remain pending acceptance.

### Collection third-pass candidate: pages, actions and lineage

Directory identity uses the botanical serif role at quiet normal weight, scientific names use the
botanical italic role, and operational metadata/tooling retain the UI sans role. This exception is
scoped to Collection lists and optional Quick Preview identity, not form or Details-body typography.

Full-page Collection create/operation forms share the delivered Add SeedLot canvas shell. Record
creation has its category directory as logical history parent; an operation with an explicit source
has that source Details page as parent. Establish the parent at in-app entry, preserve older history,
and use a canonical Cancel fallback for direct links. Successful creation replaces the operation entry
with its result. Ordinary Details and guarded contextual Edit retain their own navigation contracts.

Details use one shared action group: at most one dominant daily action, visible secondary/Edit actions,
and the established More menu for rare actions such as Print label and Undo creation. A sibling task
dialog returns to the stable More trigger. Primary links must use on-primary text even in entity scopes
with older botanical-link rules.

Material diagrams read ancestor to descendant in DOM order: horizontal with rightward connectors when
wide, vertical with downward connectors when narrow. Use only explicit authoritative relationships;
show the current entity where helpful. API traversal order is not automatically presentation order.
The compact empty-state grammar remains. All third-pass refinements are pending operator acceptance.

### Collection fourth-pass form/workflow candidate

The full-page Collection footer follows one shared canvas rule: normal flow, matching form edges,
one top border, SeedLot padding/gutters and a transparent background. Contextual Edit retains its
bounded footer. Meaningful field names remain visible; redundant nested captions may be visually
hidden with their accessible field/group names retained. PartialDate exposes this as an opt-in,
leaving date precision and unrelated families unchanged.

Guided descendant creation uses compact linked source context, semantic page columns and one page
identity. Four native Sowing-state radios show one selected consequence; conditional completion facts
remain. Plant/group maintenance Transfer lives in More, with stable dialog focus return. The guided
source Details tab is preserved in its canonical parent history entry. These refinements await the
operator's visual acceptance.

## Harvest and Location normalization candidate

COLLECTION-VISUAL-002 completes the primary Collection family using the accepted SeedLot, Sowing
and Plant references. Historical Harvest rows keep identity/media on the left and occurrence date
and a bounded material-kind summary on the right. Desktop Quick Preview uses the same 12rem media
area, source/date context and Open details/Edit hierarchy. Collected quantity never represents stock.

Substantial Harvest creation uses the existing full-page Collection canvas, semantic Source, Harvest,
Materials collected and Notes sections, row-specific controls and the shared continuous footer.
Contextual correction retains the aggregate in Details/Materials/Notes tabs in EditWorkspace, a stable
footer and a direct full-page fallback;
Escape, backdrop, Cancel and contextual history departure use the same pending/dirty guard.
A Harvest stays a single full-width detail page, with historical collected lines and distinct current
Stored material, Notes, related history and shared Photos. Conversion remains an explicit contextual
operation with Source stored material, Resulting Seed lot and Conversion quantities sections.

Locations remain a nested list with native expand/collapse buttons, capped indentation and full
path/parent context for deep nodes. Names use Collection serif identity; paths, scopes, counts and
state use UI sans. Rows and Quick Preview show only occupied record types. Small native create/edit
dialogs retain explicit non-inherited scopes; at least one scope is required, not every checkbox.
Full-width Details retains a semantic usage table: Directly here/Including sublocations, total/active
record counts and explicit zeroes. Counts are never seed amounts, group membership or material mass.
Rare maintenance/deletion actions use More. Operator visual acceptance remains pending.

The second refinement uses one shared leading-edge selection rule for Harvests, Locations and the
accepted Collection rows: primary-subtle fill, green leading accent and neutral remaining boundaries.
Stored material supplies complete media/identity/metric columns, grouped search/Filters/Saved views,
removable chips and a standard immediate-filter drawer. Per-line conversion is important, disposition
secondary and print/edit/removal live in More, with stable focus return. Unknown remainder stays unknown.
Location row metrics use explicit `incl.` when descendants contribute; preview and Details retain full
comparisons. Typed identity/Location filters on Seeds/Sowings/Plants remain deferred because their list
APIs do not support those parameters. No Harvest Location is inferred. See the current handoff for
measured desktop fit and the live native-confirmation/browser-zoom acceptance limits.

Harvest/Stored material list text now matches the accepted Plants directory: normal serif record title,
light italic scientific identity, sans metrics and state badge. Row actions have normal-radius corners
and content-aligned gutters. New Harvest aligns the first Source and Material controls and keeps unknown
Quantity full-width. Location State defaults to Active with Retired/All available in the shared drawer;
Saved Views records this preference. Contextual Parent location uses the existing reference picker, not
an unbounded native options menu; full paths wrap inside the control width and root is explicit.
