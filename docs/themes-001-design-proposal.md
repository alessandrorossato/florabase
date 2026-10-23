# THEMES-001 — Multi-theme and dark-mode foundation

Status: **proposed**, 22 October 2026. Architecture/design phase only; no production CSS, runtime,
dependency or environment change. Audit base `b3f1de4` includes Maps PR #118 and Sourcing PR #117.
The supplied brief requested an isolated checkout; this existing Codex-managed worktree is reused
under the current repository instructions. No second worktree or protected environment is needed.
No prior THEMES documents existed at this base; these documents establish the requested baseline.

Companions: [token matrix](themes-001-token-matrix.md), [implementation plan](themes-001-implementation-plan.md),
[CONTROLS-001](controls-001-design-contract.md), [visual specimens](design/themes-controls/review.html).
Both features must land before the remaining application-wide visual normalization, with independent
deliveries. These proposals do not supersede the accepted UI contract until implementation approval.

## Identity and decisions

One component grammar, three palettes × Light/Dark. System is an appearance preference resolving to
one of those six variants, not a seventh palette. Botanical Light stays the accepted reference except
for explicitly measured contrast corrections. Preserve typography, density, spacing, heading levels,
navigation, scientific-name treatment and information hierarchy in every variant.

| Palette | Light | Dark |
| --- | --- | --- |
| Botanical (default) | Existing off-white/green workspace | Green charcoal surfaces, restrained pale green action |
| Herbarium | Quiet ivory paper, olive/brown-neutral structure | Warm charcoal, pale olive action; no sepia effects |
| Mineral | Cool white/slate, muted blue action | Deep slate, controlled pale blue action; no neon |

Recommended defaults: Botanical + System, browser-local persistence, one Settings → Appearance section,
a labelled footer chooser until CONTROLS provides the compact accessible trigger, print-safe white
paper in every mode. Retain current font packages and physical layout; no new font or theme package.
Palette names and final values remain proposals. The small Botanical Light AA adjustments require
explicit visual acceptance, not an assertion of pixel identity.

## Audit: sources of truth and risks

`styles/tokens.css` is authoritative for UI roles, typography, spacing and geometry. `styles.css`
imports it; `main.tsx` imports Leaflet CSS, bundled fonts, styles.css, foundation.css and
normalization.css. Lazy capability CSS and higher-specificity selectors can still override later
base rules. A search over source CSS/TSX found **358 matching lines** with hex/RGB/HSL syntax,
including token declarations, fallbacks and intentional print colors; this is an audit index, not
358 defects. Do not replace every literal mechanically.

| Owner / files in `frontend/src/` | Observation and migration | Risk |
| --- | --- | --- |
| `styles/tokens.css` | Semantic roles already exist, including danger/warning-subtle, backdrop and elevation. Keep names; add six value tables, not six component stylesheets. | Medium |
| Compatibility aliases | color-ink→text, color-muted/color-leaf→text-muted, color-paper→background, color-surface→surface, color-sage/color-external→surface-subtle, color-border→border, color-accent/accent-strong→primary, color-error→danger, color-focus→focus-ring, accent-soft→primary-subtle, muted→text-muted. Keep radius-panel and font-editorial aliases too. | Medium |
| `styles.css` and `taxonomy/taxonomy.css` | Many raw white/green/gray/alpha values; taxonomy uses undefined `--border-color` fallback. Identify actual consumers and replace with existing roles; do not create another independent legacy theme. | High |
| `styles/foundation.css`, `styles/normalization.css` | Most shared primitives tokenized; dynamic imports/specificity and old disabled opacity can defeat semantics. Test computed styles, not just variable definitions. | High |
| `App.tsx`, `ThemeControl.tsx` | Preview state in App, no persistence or palette; title explicitly says unavailable. Replace behavior and label atomically; keep mobile More synchronized. | High |
| `settings/SettingsScreen.tsx`, `settings.css` | Server QR/general settings and Tools; no Appearance panel. Add a browser-local section independent of General loading/errors and Save settings. | Medium |
| `ReferenceUI.tsx`, `DirectoryTools.tsx`, `saved-views/SavedViews.tsx` | Search, filters, selected rows, modal view picker and portals need active/hover/focus contrast. Do not alter state ownership. | High |
| `TaskDialog.tsx`, `EditWorkspace.tsx`, `components/edit-workspace.css` | Native modal; contextual overlay has literal `rgb(14 36 28 / 35%)`. Use semantic backdrop and retain dirty/pending focus behavior. | High |
| Dashboard, Journal/History/Schedule | `collection/dashboard.css`, `events/activity.css`, `schedule/calendar.css`, `schedule.css`: selected date, overdue/status and source badges must retain their meanings. | Medium |
| Collection and Sourcing | Seed refinements, `harvests/collection-visual.css`, `orders/orders.css`, general styles: statuses, selected rows, related links, quantities, forms and empty facts. No workflow/quantity/date changes. | High |
| Explore taxonomy/geography/identities | Trees, focused/selected nodes, reference badges and external-source sections rely on legacy selectors. No inferred geography or taxonomy semantics. | High |
| Login/recovery/auth states | Base `.auth-*`, form, notice and card rules in styles.css plus normalization. Theme must apply before authentication and during session expiry. | High |
| Media/photo surfaces | `MediaPreview.tsx`, `photos/compact-gallery.css`, RecordVisual and BotanicalIdentityCover placeholders: frame/controls theme; image pixels remain unchanged. Consent to load external images remains explicit. | Medium |
| Labels/QR | `labels/labels.css`, `LabelQr.tsx`, `CategoryGlyph.tsx`: white paper, black QR, mm geometry are intentional. Theme surrounding chooser/toolbar only. | High |
| Native ranges | SVG geography; local native tokens, color-mix count scale, fixed five-color comparison and hard-coded striped fallback in native-ranges.css. Separate evidence palette from UI palette. | High |
| Species distribution | Leaflet density raster + optional online basemap; local geometry uses CSS values. No theme-triggered tile refresh, provider swap or cache-generation changes. | High |
| Collection origins | Leaflet configured online tiles; DOM markers and popup; literal `#30624b` accuracy stroke, 0.08 fill. Update local styling without recreating map or transmitting metadata. | High |
| Charts/lineage | No general chart-library dependency; inspect existing numeric summaries/lineage and map legends as data-viz consumers. Do not introduce charts as part of themes. | Medium |

The controls audit adds button geometry, icons and Tooltip scope without expanding these color tasks.
No live app screenshots or environment smoke were performed for this source audit.

## Token architecture

Proposed root attributes: `data-palette="botanical|herbarium|mineral"` and
`data-appearance="light|dark"` hold effective values. Preference System stays in application state.
Define a complete default Botanical Light `:root` for failure-safe rendering, then explicit palette/
appearance blocks containing **values only**. Component selectors remain common. Compatibility
aliases point one-way to semantic roles, never independently overridden per palette.

Keep every demonstrated role in the matrix: background; surface/subtle/hover; text/muted; borders;
primary/hover/subtle/on-primary; success, warning/warning-text/subtle, danger/subtle; info, focus;
backdrop/elevation. No new tooltip colors or generic accent rainbow. Disabled uses muted/subtle
with explicit state, no compounded alpha. Preserve typography/spacing/radii/control-height constants.
Retain native-range-specific tokens under a data-viz namespace; do not turn all categories into
primary color. Provider raster/media colors have no UI semantic alias.

State use: selected navigation/row has primary-subtle fill plus primary edge/check and text/ARIA;
hover fill alone is never selection. Status keeps literal text, with danger/warning-text/success
foreground. Focus uses a 3px outline with 3px offset on an unambiguous background; retain the
component's visible edge if a ring crosses map imagery. Scrollbars/native form widgets use effective
`color-scheme`; avoid custom scrollbar palettes. Inputs/selects/date/file controls use text/surface
and border-strong; inspect native popup widgets in real supported browsers. Do not invert CSS colors.

## Preference model and first paint

Proposed storage key `florabase.appearance.v1`, JSON `{version:1,palette,appearance}`. Defaults:
`botanical`, `system`; resolve System with `matchMedia('(prefers-color-scheme: dark)')`. Stored keys
are enum-validated independently; invalid fields fall back to defaults, unknown version/corrupt JSON
falls back entirely. Storage access is always caught, including SecurityError and quota failures.
Use in-memory state when writing fails; show a quiet Settings status that the preference is temporary.
No database schema, API, account setting, cookie or server persistence in this release.

Browser-local follows this origin/browser profile across routes, reloads, sign-in/out and session
expiry. Sign-out does not reset cosmetic settings. Shared-device users share this preference;
Settings says “This browser”. No account preference is inferred or synced. Separate origins may
have different choices. Hybrid/account persistence is deferred unless a real cross-device need is
approved; it would need explicit conflict/default rules, not a silent later backend write.

A single resolver owns validation/defaults and effective appearance. A small same-origin blocking
bootstrap in the document head, before the application styles/React, reads validated storage and
sets both attributes plus `color-scheme`. Reuse its contract in the reactive store; test parity to
prevent duplicate interpretation. CSP must allow the chosen same-origin bootstrap or a hashed inline
build asset; never weaken policy with unrestricted inline code. Bootstrap must fail closed to the
CSS default, without waiting for authentication, API responses or React effects.

Subscribe to OS appearance changes only while preference=System; explicit Light/Dark ignores them.
Listen to `storage` for cross-tab updates (including key removal/reset); validate new values and apply
without echo-writing them back. Same-tab controls share one store; switching palettes does not
change appearance. Cleanup listeners under StrictMode. Apply attributes before notifying renderers;
local Leaflet style updates preserve map instance, viewport, selection and cached data.

If localStorage is unavailable, startup defaults to System and works for that session. If JavaScript
is unavailable, default CSS supports Botanical with a prefers-color-scheme dark fallback when no
explicit effective attribute exists; the React application itself is unavailable, so do not claim an
interactive no-JS experience. CSS `color-scheme` must agree with that fallback. The preference may
be unrecoverable without JS; avoiding the wrong theme under that condition is not guaranteed.

## Theme selection UX

Settings gains **Appearance**, not a primary-navigation destination: a labelled native radio group
for three palettes, each with a restrained surface/text/action swatch and palette name; a separate
System / Light / Dark radio group. Show “System · currently Dark” as appropriate. Immediate apply,
no Save/confirmation, selected indicator beyond color. A short “Applies to this browser” description
separates this from server-owned QR/general settings. Swatches are previews, not interactive nested
controls. Palette changes leave keyboard focus in place and do not remount the page.

Footer Appearance opens a compact chooser with the same two groups and a link to Appearance in
Settings. Use existing popover dismissal/focus conventions; narrow mobile More keeps it labelled
and may link directly to Settings Appearance to avoid stacked modal complexity. Outside click
closes while preserving intentional new focus; Escape returns to trigger; Tab does not trap in a
nonmodal chooser. Do not cycle invisibly through six/nine states. During THEMES implementation use
an understandable labelled trigger; CONTROLS later supplies the compact desktop icon/Tooltip.
Remove the preview-only text and old cycling state together. Current mode is a state, not an action
named “switch to next”; accessible name includes Appearance, preference/effective mode and palette.

## Maps, data visualization and media

Keep three scientific contracts separate: structured native-range coverage, observed occurrence
density and recorded collection provenance. Themes change local rendering, never evidence/query
parameters, geometry, accepted taxonomy, geographic precision or recorded site coordinates.

| Renderer | Theme response | Evidence safeguards |
| --- | --- | --- |
| Native ranges local SVG | Theme ocean/surface, unselected land/borders, text/focus and selection. Explicit count and comparison tokens independent of UI palette. | Preserve inclusive count bins and five identity slots; same identity keeps its slot across switching. Overlap patterns/numbers and named legend supplement hue. |
| Species distribution | Theme local background, panels, Leaflet controls and local outline strokes. Keep provider density tiles and online basemap unchanged. | Preserve density legend/provider scale, cache generation, dates and refresh consent. No CSS inversion, automatic layer reload or alternate provider URL. |
| Collection origins | Theme DOM marker rings, popup/buttons and accuracy-circle stroke through a local style update; use dual light/dark marker casing over unknown raster pixels. | Preserve accuracy metres, fill-opacity meaning, selected point, camera and provider attribution. No remount/flyTo solely due to theme. |
| Other data marks | Dedicated sequential/categorical tokens, readable neutral labels and numeric/shape equivalents. | Do not reuse danger/primary as unrelated categories or imply trends/metrics absent from data. |
| Photographs/QR | Unmodified images and black/white QR; surrounding frame follows theme. | No filters/blend modes, new remote image loads or QR payload changes. |

Five comparison colors retain hue identity across appearance, supplemented by stable species numbers
1–5 in the legend/list and inspectable membership; matching pattern keys provide a color-independent
reading route. Proposed swatches pass 3:1 against the neutral map/legend surface (see evidence),
which does **not** prove pairwise discrimination. Maintain neutral double boundary/selection casing
when fills adjoin; inspect deuteranopia/protanopia/tritanopia simulations and grayscale, then actual
keyboard/list equivalence. No “colorblind certified” claim from a palette alone. Use explicit neutral
contrast edges when a low count fill is below 3:1; numeric bins and selected territory text remain
available. Basemap imagery has arbitrary contrast, so a single colored stroke is insufficient.

Canvas/Leaflet APIs that require resolved colors read computed tokens and update local styles in
place; SVG/DOM may inherit CSS variables. Check SVG fill/stroke and patterned overlaps separately.
Do not pass unresolved CSS expressions into a renderer that only accepts numeric/hex values.
Attribution remains visible with legible control backing and is never hidden by responsive toolbars.
The existing Collection origins online basemap is retained; this contract does not invent an offline
geography feature for it. A theme change alone must produce zero new remote provider requests.

## Print, accessibility and release constraints

Physical labels and their previews always show white paper, black type/QR and existing physical mm
geometry, font sizes, quiet zones, inset/category glyphs and encoding. The surrounding screen can
be dark. Browser print media selects a dedicated light/black-on-white treatment, removes application
chrome, retains meaningful data/unknown states and does not depend on background graphics printing.
Future reports inherit this print policy but are outside scope. Actual printer acceptance remains a
separate check; browser preview is not certification of paper output.

Calculated pair coverage and caveats are in the matrix. All normal UI text must meet 4.5:1; large
text 3:1; identifying borders/icons and state/focus cues 3:1 against actual adjacency. Our matrix
uses 4.5:1 for shared info/focus colors because info can be small text. Disabled controls are exempt
from WCAG contrast thresholds but the proposal retains readable muted labels and explicit reasons.
Unknown data remains text, never a color-only status. Avoid opacity chains on text/borders.

Use system colors in forced-colors mode; retain visible outlines, selected checks/borders, native
controls and textual map equivalents. Do not globally set forced-color-adjust:none. Preserve
reduced-motion preferences; no theme-transition animation, map flyTo or fade is added by themes.
Focus must remain visible and unobscured by sticky bars, portals or the soft keyboard.

## Operator decisions and implementation handoff

Decided by the operator: both features precede final remaining-page visual normalization; independent
delivery; this phase ends at design review with no runtime changes, canonical gate or Git delivery.
Recommended for approval: palette names/values and the documented Botanical corrections; browser-local
scope + System default; explicit two-axis chooser; local SVG vocabulary; non-collapsing Filters/Saved
views labels; 44px control geometry; manual-popover tooltip with tested modal fallback.

Outstanding validation is implementation evidence, not permission to broaden scope: computed styles
on real pages, all native-widget browsers, dialog/popover compatibility, screen readers/touch, actual
zoom and physical print. Follow the [implementation plan](themes-001-implementation-plan.md); do not
start Phase 2 merely because this contract is ready for review.
