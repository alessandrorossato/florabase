# Florabase UI Foundation v0.1

Authoritative contract for new UI. Dashboard is the pilot; legacy screens migrate only in
explicit later increments. Implementation: `frontend/src/styles/tokens.css` (single token source),
`foundation.css` (base/shell/primitives), `ReferenceUI.tsx` and `WorkspaceUI.tsx`.

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

These are future review contracts; this increment does not rebuild them all.

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
Directory, Detail and Schedule screens whenever global base/shell styles change; fix introduced
regressions only. Full cross-product visual migration is a separate feature.

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
