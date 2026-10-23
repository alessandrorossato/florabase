# CONTROLS-001 — Shared toolbar iconography, action hierarchy and accessible tooltips

Status: **proposed design contract**, 22 October 2026. No runtime implementation or visual acceptance.
Audit base: `b3f1de4`. Companion: [THEMES-001 proposal](themes-001-design-proposal.md),
[token matrix](themes-001-token-matrix.md), [joint sequencing](themes-001-implementation-plan.md).
The operator requires both features before the remaining application-wide visual normalization.
They retain separate implementation branches, acceptance criteria, verification and delivery.

## Intent and boundaries

Keep the Botanical Scientific Workspace: Source Sans 3 controls, Source Serif 4 only for scientific
names, medium-compact density, restrained borders, familiar routes and contextual actions.
Improve recognition and consistency without making operators decode a row of symbols. Do not add
filters, Saved View support, map layers, shortcuts or domain operations merely for visual symmetry.
Do not change URL state, query behavior, pagination, record selection, API calls or permissions.

## Audit and component inventory

Paths below are relative to `frontend/src/`. Findings are source observations, not live browser defects.

| Surface / owner | Current evidence | Contract and migration risk |
| --- | --- | --- |
| `components/ReferenceUI.tsx`: PageHeader | Separate `tools` and `actions` slots; identity and tools wrap | Keep slots and heading order. Do not duplicate an operation across both slots. Low risk. |
| `components/DirectoryTools.tsx` | Text Filters with dimension count; live native-dialog drawer; removable chips; Reset filters / Done | Add one filter icon; preserve count, accessible names, reset/search separation and return focus. Medium risk. |
| `events/ActivityPageHeader.tsx`, `ActivityFilters.tsx`, `collection/DashboardSearch.tsx` | Parallel filter/toolbar compositions outside DirectoryTools | Reuse action presentation without moving their state or default-query semantics. Medium risk. |
| `components/ReferenceUI.tsx`: DirectorySearch | Unicode `⌕`; separately labelled search input | Replace glyph with shared Search SVG; it is decoration, not an extra submit button. Preserve hidden label and typing focus. Low risk. |
| `saved-views/SavedViews.tsx` | Inline/dialog presentations; Save view, active view and CRUD controls | Retain explicit Saved views entry and active/modified/default context. Bookmark icon is supplemental. Do not invent a second save mechanism. Medium risk. |
| `components/ReferenceUI.tsx`: OverflowMenu | Text More; native buttons/links inside a group; portal to nearest dialog; viewport positioning; keyboard arrows and Escape | Shared More icon/tooltip at trigger only. Keep existing group semantics until a separate menu-widget decision; no partial `role=menu` conversion. High focus risk. |
| `components/TaskDialog.tsx`, `EditWorkspace.tsx` | Native `showModal`, Tab containment, Escape handler and return focus; inner forms can scroll | Tooltip layer must be nonfocusable, dialog-local and outside the scroller. Escape ordering requires coordination with dialog `keydown` and `cancel`. High risk. |
| `components/ReferenceUI.tsx`: RecordPreview, `CollectionUI.tsx`, record screens | Shared action slot but page-owned Details/Edit/domain operations | Keep Details and Edit labelled; preserve remounted invoker restoration, contextual Edit and direct-route fallback. Medium risk. |
| `seed-lots/SeedLotScreen.tsx`, `orders/OrderScreen.tsx`, `botanical-identities/BotanicalIdentityScreen.tsx` | Textual `+ New…`, varied record labels, details and related-record actions | Replace the literal plus with decorative Add; preserve precise nouns and page-specific eligibility. No icon-only creation. |
| `App.tsx`, `components/ThemeControl.tsx`, `settings/SettingsScreen.tsx` | Duplicate hand-authored gear SVGs; 1.7-unit theme strokes; Theme preview uses native title and cycles nonfunctional states | Reuse one icon vocabulary. THEMES owns real chooser behavior; CONTROLS owns trigger presentation and tooltip. Keep Settings labelled. |
| `maps/MapWorkspace.tsx`, `MapLegend.tsx`, `native-ranges/NativeCoverageMap.tsx` | Labelled pane switch, selection, discrete comparison colors and map controls | Keep Map & evidence / browser labels and scientific legends visible. Actions may gain shared icons; data marks are not action icons. High scientific-context risk. |
| `provenance-map/ProvenanceMapScreen.tsx`, `ProvenanceMap.tsx` | Separate inline record-type/identity filters, inline Saved Views, Manage provenance sites; Leaflet zoom/markers | Preserve that layout and provider behavior. Do not replace it with a generic Filters drawer in this increment. |
| `occurrence-map/OccurrenceMapPanel.tsx`, `species-distribution/SpeciesDistributionScreen.tsx` | Explicit evidence-loading/refresh and source navigation | Refresh evidence remains labelled because it can contact a provider; a generic circular arrow cannot communicate the operation. |
| `styles.css`, `styles/foundation.css`, `styles/normalization.css`, capability CSS | Legacy button padding/radii plus normalized 44px controls; footer uses small text and 1.1rem icons; search and leaf controls have separate rules | Centralize touched control geometry, not all page CSS. Check computed specificity and Leaflet controls separately. |
| `photos/RecordVisual.tsx`, `BotanicalIdentityCover.tsx`, `media/MediaPreview.tsx` | Custom placeholders and `▧`; image affordances are distinct from actions | Share action glyphs only; retain botanical illustration/placeholder semantics and external-image consent. |
| `labels/CategoryGlyph.tsx`, `LabelQr.tsx` | Dedicated category SVG, 1.6 stroke and black/white QR geometry | Deliberate print exceptions. Do not replace QR/category artwork with toolbar icons. |
| `components/SidebarResizeHandle.tsx` | Native title with resize instructions | Keep instructions available as description/help; a tooltip cannot be the only keyboard-resize documentation. |

Missing affordances: search uses a font-dependent glyph; Filters and Saved views lack repeated visual
anchors; duplicated settings geometry has no canonical owner. Redundant presentation includes literal
plus signs once an Add icon exists, repeated drawer heading/Close/Done emphasis, and generic More
names that omit record context. Keep useful repetition (a drawer title and safe dismissal), but make
Close quiet, Done secondary, Save/Create primary. Long action text is not inherently redundant.
Do not shorten “Move to location”, “Link existing seed lot”, “Undo creation” or “Refresh evidence”.

## Iconography contract

**Recommendation: consolidate the existing repository SVG approach into one local `Icon` vocabulary.**
There is no general icon-library dependency in `frontend/package.json`. Reuse the monitor/sun/moon
and gear geometry already owned by the repository; add a small audited set of simple action paths
in the same 24-unit grammar. No icon font, emoji, Unicode action glyphs or remote assets. This avoids
a new package for fewer than twenty action symbols. Do not mix a later library with this set: any
future adoption must replace the complete action vocabulary and satisfy licensing/dependency policy.
Custom botanical artwork, QR, map symbols and data-viz marks are separate content, not competing
control icon systems.

| Action / proposed Icon name | Canonical shape | Visible label / accessible name | Default pattern |
| --- | --- | --- | --- |
| Search / `search` | Magnifier | Search seed inventory / Search Orders | Decorative leading input icon; label remains |
| Filters / `filter` | Funnel | Filters (2); name “Filters, 2 active dimensions” | Icon + label + visible count |
| Saved views / `saved-views` | Bookmark with short horizontal lines | Saved views | Icon + label, never icon-only |
| Add/New / `add` | Plus | New seed lot / New Order / New botanical identity | Primary text-first with optional icon |
| Edit / `edit` | Pencil | Edit / Edit seed lot | Icon + label in headers/previews |
| More / `more` | Horizontal ellipsis | More actions for [record name] | Icon-only allowed on fine-pointer row actions; labelled on touch |
| Print / `print` | Printer | Print labels | Icon + label; primary when the final workspace operation |
| Refresh / `refresh` | Circular arrow | Refresh list / Refresh evidence | Labelled for evidence/network-sensitive operation |
| Download / `download` | Down arrow into tray | Download [format or object] | Icon + label; filename/format stays discoverable |
| Settings / `settings` | Gear | Settings | Icon + label in footer/navigation |
| Back / `back` | Left arrow | Back to Seeds / Back | Labelled navigation link; no history guessing |
| Clear selection / `clear-selection` | Selection box with cross | Clear selection | Text or icon + label; never reuse Delete/trash |
| Map layers / `layers` | Stacked planar sheets | Map layers | Icon + label, only where a layer chooser already exists |
| Expand / `chevron-down` | Down chevron | Show [section] | Labelled disclosure, `aria-expanded` |
| Collapse / `chevron-up` | Up chevron | Hide [section] | Same disclosure trigger and state |
| Close / `close` | Cross | Close quick preview / Close dialog | Icon-only only with persistent surface title and touch label |
| Theme / `monitor`, `sun`, `moon` | Existing shapes | Appearance: System (Dark), Botanical | Compact desktop affordance; mobile labelled Appearance |

No leaf for Filters, heart for Saved views, recycle symbol for Refresh or trash for clearing selection.
Chevrons disclose local content; use separate expand-arrows if an existing fullscreen action needs it.
Back follows locale direction where the application supports it; download and map symbols do not mirror.

Geometry: 24×24 viewBox, 1.75-unit stroke, round caps/joins, no fill except intentional small dots.
Default display size 18×18 CSS px; 20×20 for shell/standalone map controls only. Never enlarge icons
instead of targets. Centre in the inline flex box, not the font baseline; `flex-shrink: 0`, 8px gap,
12px horizontal button padding, 6px radius, 44px minimum height and width for icon buttons.
Text uses existing `type-strong`; footer may retain `type-small`. Allow multiline labels to grow.
SVG uses `currentColor`, `aria-hidden=true`, `focusable=false`; a control supplies the name.
Do not add SVG titles that duplicate the control name. No decorative icon on every heading or datum.

## Three action patterns and state styling

| Pattern | Use / appearance | Naming and state |
| --- | --- | --- |
| Icon-only secondary | Familiar More/Close or low-risk Refresh list in bounded tool groups; neutral surface or quiet background, text-colored icon | Required explicit name and Tooltip. Never the only entry to an ambiguous operation. |
| Icon + label | Filters, Saved views, Edit, Print, Download, Settings, supported Map layers | Visible text supplies the name; decorative icon. Tooltip only adds useful supplementary detail. |
| Text-first primary / destructive | New record, Save changes, Complete, Move to location, Delete confirmation | Action and object remain visible at every width. At most one primary emphasis per operation group. Destructive button is explicitly worded and uses danger treatment. |

Reuse `.button--secondary`, `.button--quiet`, `.button--danger` and primary semantics. A shared
ActionButton/IconButton adapter can enforce icon, name and Tooltip requirements, but must forward
refs, native button props, pending/disabled state and event handlers. Navigation remains a real
anchor with its existing URL and modified-click behavior; no catch-all action router.

Normal secondary icons/text use `text`; hover uses `surface-hover`; selected uses `primary-subtle`
with a `primary` edge/check plus `aria-pressed` only for toggles. Primary uses `primary/on-primary`;
hover uses `primary-hover`. Destructive uses `danger` text/border on `surface`, hover `danger-subtle`.
Never put white text on danger without separately validating that pair. Focus stays the existing
3px `focus-ring` outline with 3px offset, visible outside the real button. Do not focus wrappers.
Disabled controls use muted text on subtle surface, native disabled behavior and a nearby visible
reason when material. Avoid whole-control opacity. Busy controls keep their action label, expose
pending text/`aria-busy`, prevent duplicate submission, and do not depend on a spinning icon.

## Tooltip primitive: interaction and accessibility

A single reusable, noninteractive `Tooltip` belongs beside the shared primitives. Proposed API:
trigger ref/one native trigger, concise content, placement preference and disabled option. It must
compose existing refs, handlers and `aria-describedby` IDs. Do not wrap a button in another button.
Do not use `title` on migrated triggers. No links, inputs, buttons or multi-step instructions inside.

| Event / state | Required behavior |
| --- | --- |
| Fine-pointer enter | Open after 500ms; cancel if trigger is left before then. No long introductory animation. |
| Keyboard focus | Show immediately on focus-visible; retain focus on trigger. Pointer click must not create a sticky focus tooltip. |
| Pointer over tooltip | Keep it open while trigger or tooltip is hovered; 150ms close grace permits crossing the 8px gap. |
| Focus leaves | Close if neither tooltip nor trigger is hovered. Tab proceeds through the existing UI; tooltip has no tab stop. |
| Escape | Dismiss immediately; suppress reopening until pointer leaves/re-enters or focus leaves/returns. Consume this Escape only when a tooltip is open. |
| Activate trigger / open menu | Close tooltip before the action opens its surface. No tooltip over its own open popover. |
| Scroll / resize / content resize | Recompute placement; dismiss if trigger becomes hidden, inert, disconnected or outside its scroll viewport. |
| Touch | No hover or long-press dependency and no first-tap tooltip interception. Show text on secondary action triggers under coarse/no-hover input. Tap executes the action once. |
| Unmount / route / parent close | Cancel timers/observers, remove description association and tooltip; do not move focus. |

The button/link always has an accessible name independently of the tooltip. For icon-only “More”,
use “More actions for Ocimum basilicum”; tooltip can say “More actions”. The visible tooltip has a
stable ID and `role=tooltip`; the trigger references it with `aria-describedby` while present, merged
with existing descriptions. Do not put `aria-label` on the tooltip itself, use `aria-live`, or depend
on delayed tooltip text to name a control. A visible button label is part of its accessible name.
`aria-expanded`/`aria-haspopup` belong to the underlying chooser/menu, never to the tooltip.
Verify actual screen-reader verbosity; do not copy the exact name into a second hidden description.

Render into an overlay host owned by the nearest open dialog, outside its scrolling content; root
triggers use the root overlay host. The preferred escape from clipping is a **manual native popover**
for the tooltip, logically inside that host so it participates in the correct modal subtree and top
layer. Opening it must neither focus it nor light-dismiss another popover. Feature-detect support;
fallback uses an unclipped, fixed-position host within that dialog, with no transformed/clipping
ancestor. If the current dialog geometry cannot support that fallback, fix the overlay host contract
before adopting icon-only triggers. A larger z-index on document.body cannot escape the native
modal top layer. Test nested menu-in-dialog and scrollable drawer explicitly.

Prefer top centre, 8px gap; flip below/side when needed; shift inside the **visual viewport** with
8px clearance. Max width `min(18rem, viewport width - 16px)`; wrap long text, never truncate the
explanation. Account for soft keyboards and zoom. Observe trigger and tooltip size plus relevant
scroll/viewport changes. Keep clear of trigger focus and the surface's active controls.
An overlay dismissal coordinator must handle tooltip → menu → dialog, with one layer per Escape;
TaskDialog's native `cancel` must not also close the dialog on the consumed event. Existing dirty
form protection remains authoritative.

Tooltip styling reuses `surface`, `text`, `border-strong`, `elevation-overlay`, `type-small`, 8px/12px
padding and 6px radius. No tooltip-only palette is required. No motion is necessary; reduced-motion
must never introduce movement. Forced colors uses Canvas/CanvasText borders and system focus; do
not suppress forced color adjustment. Explain disabled actions next to the action or in persistent
help, since native disabled buttons cannot reliably receive focus. Tooltips are never essential help.

[WCAG hover/focus guidance](https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus.html)
requires dismissible, hoverable, persistent content. The
[APG tooltip pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tooltip/) informs the semantics above
but explicitly remains a work in progress; real assistive-technology testing is required.
[Native popover behavior](https://developer.mozilla.org/en-US/docs/Web/API/Popover_API/Using)
informs the proposed top-layer host, not a claim that the repository already supports it.

## Responsive contract and representative designs

[Review sheets](design/themes-controls/review.html) show all six palettes/modes and the same six
control contexts at desktop, tablet and phone widths. They are static design specimens with review
selectors, not production screenshots or functional application controls. Layout/typography grammar
is retained; final pixel equivalence must be checked in the actual application.

Available container width drives wrapping; viewport examples are 1440×844, 1024×844 and 390×844.
Desktop sidebar width is resizable, so these are evidence sizes, not device-detection breakpoints.
Keep DOM order Search → Filters → Saved views → creation. Search retains its 14rem basis; at narrow
widths give it a full row. Never replace search input with an unexplained icon. Group labels/counts
stay together; allow groups to wrap. No horizontal toolbar scrolling or clipped primary action.

At ≤48rem available content width, a fine-pointer secondary **More/Close/Refresh list** may collapse
to its icon with Tooltip and name. Edit may collapse only in a row with an immediately visible
record identity and an equivalent labelled action in its preview; default header/preview Edit stays
labelled. Filters, Saved views, Back, Print, Download and domain operations never collapse in this
initial increment. On `(any-pointer: coarse)` or `(hover: none)`, restore visible labels even if this
adds a row. Keep the same DOM trigger/ref when changing label visibility. More exposes supplementary
actions; never move creation/Save/essential operations there solely to fit a width.

| Context | Desktop | Tablet | Phone / touch |
| --- | --- | --- | --- |
| Seeds | Search · Filters (1) · Saved views · + New seed lot | Title above tools; same controls wrap if needed | Search full row; Filters (1) + Saved views; New seed lot on next row if necessary |
| Botanical identities | Search · Filters · Saved views · + New botanical identity | Long creation label wraps as a complete action | Keep full New botanical identity text; no plus-only creation |
| Orders | Search · Filters (1) · Saved views · + New Order | Preserve Supplier filter semantics and pending creation guard | Supplier chip wraps; search stays usable during result loading |
| Collection origins | Manage provenance sites in header; Saved views; inline types + identity search; existing zoom controls | Same stacked regions and map/list content | Stack existing filter fields and map/list; keep labels, attribution and Manage provenance sites; no invented layer switch |
| Detail / Quick Preview | Back to Seeds; Edit; supported domain action; More | Header actions wrap; preview retains Details / Edit | Full action words and record identity; Move to location/Print labels only on supporting records |
| Navigation | Existing sidebar groups; Settings + compact Appearance; Sign out separate | Existing sidebar/collapse behavior | Existing bottom destinations + More remain; More dialog exposes labelled Settings, Appearance and Sign out |

Filters count **restricting dimensions**, not selected checkbox values; search remains separate.
Always show the nonzero count alongside Filters, including wrapped layouts, plus existing removable
chips. Do not use a colored dot alone. Saved views stays labelled at every width; current view and
modified state remain text in the existing control/panel. Do not conflate Save view with Save record.
No new Saved Views capability is introduced for Schedule or any unsupported surface.

## Theme integration and independently deliverable boundaries

CONTROLS consumes only existing semantic colors and geometry. It can ship on accepted Botanical
Light without THEMES; test token inheritance with synthetic alternate values until THEMES lands.
THEMES can ship using existing text controls, without CONTROLS or its Tooltip. THEMES uses a labelled
Appearance trigger so no new icon-only affordance depends on an unavailable primitive. Afterward,
CONTROLS applies the shared icon/tooltip to the same trigger without rewriting preference state.
Keep the print category glyph, QR black/white and data-viz palette outside the action Icon API.

## Migration and focused verification

1. Inventory supported actions and record labels; freeze contracts above. Establish Icon, action
   adapters, Tooltip and overlay-host/Escape contract together. Do not publish icon-only consumers
   until the Tooltip works in a real native modal and touch labels are present.
2. Migrate DirectorySearch, DirectoryTools, SavedViews and OverflowMenu; then Activity/Dashboard
   adapters. Preserve parent-owned query/filter/selection state and remounted invoker focus.
3. Migrate detail/preview actions, dialog dismissals, Settings/Appearance and existing mobile shell.
   Replace duplicates, not layouts. Shared wrappers must not drop `href`, refs or disabled props.
4. Migrate only existing map actions; keep Leaflet navigation, evidence-refresh text, legends and
   provider/network semantics. Audit remaining ad hoc action SVG/glyphs with an explicit print/data
   exception list. No general page normalization in this feature.
5. Review domain behavior, then UI, then diff; fix defects and run the authorized final gate only in
   the later implementation phase. Deliver CONTROLS separately from THEMES.

Focused tests: Icon accessible hiding/currentColor; action name and ref forwarding; all Tooltip
transitions with fake timers; hover transfer and Escape suppression; composed descriptions; disabled
and busy behavior; DOM-order stability during responsive label changes. Reuse DirectoryTools,
SavedViews, ReferenceInteractions, ThemeControl, App navigation and record-screen test suites for
live filters, URL state, selection, nested dialogs, modified clicks and return focus.

Real browser tests must exercise top-layer positioning (jsdom cannot prove this), scroll clipping,
visual viewport/keyboard changes, edge collisions, opening a menu while focused, nested Escape and
one-tap touch activation. Verify keyboard Tab/Shift+Tab, visible trigger focus and screen-reader
names/descriptions with one desktop and one mobile AT/browser combination; record exact versions.
Use 1440×844, 1024×844, 390×844 plus 320px reflow, long names, 125%/150% actual browser zoom,
forced colors and reduced motion. Target 44px interactive controls throughout, exceeding the
[WCAG 2.2 AA minimum target criterion](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html).
Check text ≥4.5:1 and essential symbols/focus ≥3:1 against actual adjacent colors using the theme
matrix; count/selected/disabled/error meaning must remain available without color.

Run behavioral suites once, token/contrast checks for all six variants, full six-variant captures of
one directory and open tooltip, then risk-based forms/maps/mobile captures in Botanical Light/Dark
plus Herbarium/Mineral extremes. Preserve Seeds, identities, Orders and Collection origins visual
examples in all themes through review artifacts. This avoids multiplying every functional test by six.

Acceptance: one action vocabulary; all three patterns demonstrated; labelled essential operations;
Filters counts and Saved Views discoverability unchanged; no clipping or focus regressions; touch
alternatives; six-variant token compatibility; no domain/API/print-geometry changes. Screenshots
alone do not satisfy interaction acceptance. No acceptance criterion is marked implemented here.
