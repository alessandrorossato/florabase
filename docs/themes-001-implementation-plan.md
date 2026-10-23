# THEMES-001 and CONTROLS-001 — Implementation plan

Proposed 22 October 2026, source base `b3f1de4`. **Execution update, 23 October:** the operator
approved one combined implementation branch, one final visual review and one later protected PR.
Both features are implemented candidates; neither is verified. The design-stage independent delivery
sequence below is historical and is superseded for this run: complete THEMES, then CONTROLS, review
them together, obtain authorization for the canonical gate/delivery, then address remaining-page
normalization before the final application-wide review. Preserve separate feature scopes and evidence.
See [THEMES handoff](themes-001-handoff.md) and [CONTROLS handoff](controls-001-handoff.md).
The operator selected the functional footer System → Light → Dark cycler and a Settings sliders glyph.

Read [themes](themes-001-design-proposal.md), [values/evidence](themes-001-token-matrix.md) and
[controls](controls-001-design-contract.md) together. Existing `docs/ui-contract.md` remains the
accepted production reference until approved changes land.

## Order and ownership

**THEMES-001 → CONTROLS-001 → remaining-page visual normalization → final application-wide review.**
Both features are required predecessors of the final review, not a hard dependency on one another.
Original design recommendation: separate branches/PRs and acceptance gates. The explicit combined
execution approval above controls this candidate; no lifecycle action is authorized by this plan.
Do not mark either verified from this design work. The design milestone recorded both as planned; implementation status is tracked separately in the feature graph.

| Stage | Owner | Deliverable / exit condition |
| --- | --- | --- |
| 0. Approval and source reconciliation | Each feature | Confirm design choices; inspect/fetch newest main through normal workflow. Reconcile Maps/Sourcing/shared UI changes before edits; preserve other worktrees and environments. |
| 1. Tokens + bootstrap/store | THEMES | Six complete value sets, compatibility aliases, browser-local resolver, cross-tab/OS updates and first paint. Internal development stage, no exposed partial Dark release. |
| 2. Real selection | THEMES | Settings Appearance and footer chooser; remove preview-only state atomically. Use labelled trigger and existing action/menu patterns. No dependency on new Tooltip. |
| 3. Shared + capability color migration | THEMES | Shell, auth, forms, menus/dialogs/drawers, directory/preview/details, Activity, Explore/Sourcing/media; resolve raw UI colors and specificity. Preserve interaction geometry. |
| 4. Maps/data-viz + print | THEMES | Local SVG/Leaflet style updates, five-species/legend semantics, unchanged provider requests/imagery; white labels and print. |
| 5. THEMES acceptance and independent delivery | THEMES | Whole six-variant compatibility, measured pairs, no-flash and browser behaviors verified; authorized repository gate and own delivery boundary. |
| 6. Icon/actions/Tooltip + overlay host | CONTROLS | One local SVG vocabulary, three action patterns, refs/names preserved, top-layer positioning and Escape ordering proven. |
| 7. Shared consumer adoption | CONTROLS | DirectoryTools/Search/SavedViews/OverflowMenu, Activity adapters, preview/detail actions, dialogs, footer/mobile, existing map controls. Remove duplicate action glyphs without relocating domain state. |
| 8. CONTROLS acceptance and independent delivery | CONTROLS | Tooltip keyboard/pointer/touch and responsive controls verified against all six values; own authorized gate and delivery boundary. |
| 9. Remaining-page normalization | Later increment(s) | Evaluate remaining page-family layout defects using final colors and controls; classify blocker/normalization/polish, preserve domain/IA. |
| 10. Final application-wide visual review | Operator | Review integrated product, remaining page coverage, actual zoom and responsive behavior after both features and later fixes. |

Why this order: THEMES touches color ownership once while preserving geometry and text actions.
CONTROLS then changes control composition once against stable tokens. In particular, THEMES owns
ThemeControl state/Settings and CONTROLS only replaces its glyph/trigger styling. Agree the tooltip
overlay-host seam now, but implement it in CONTROLS; THEMES does not create a temporary tooltip.
No button geometry redesign or broad page cleanup is hidden in the theme migration.

Independent delivery alternative: if CONTROLS lands first, use existing Botanical Light semantic
tokens and synthetic token-inheritance tests; do not implement palette persistence. Its old Theme
preview must remain explicitly a preview until THEMES replaces it, preferably labelled. THEMES
can later reuse the new action primitives without altering the controls' accessibility contract.
Reverting one feature should not remove the other's state or API; any resulting incompatibility is
a release-blocking integration defect. Maintain separate acceptance evidence even when reviewed together.

## Atomicity and exclusions

Recommend **one THEMES feature with internal stages**, because exposing a global Dark preference while
forms, maps or authentication remain unreadable is unacceptable. Do not ship an enabled selector
until all stage 1–4 consumers work. A preparatory token refactor may be independently delivered only
if separately authorized, visually equivalent in current Light, and no new palette is exposed.
CONTROLS is a second coherent feature: icon-only adoption and functioning Tooltip/touch alternatives
must ship together. Consumer adoption can be developed in batches, but scope completeness is checked
before claiming the feature complete.

No backend/database, theme-account sync, new icon dependency, redesigned navigation, invented map
layers, print dimensions, QR encoding, evidence/source changes, global environment work, or remaining
page visual normalization belongs to these two feature scopes. Do not update DEV/UAT/Preview or
other feature-owned environments as part of design or source inspection.

## Verification strategy

| Layer | Run once / all variants / selected risk cases |
| --- | --- |
| Resolution unit tests | All enum/default/corrupt/version cases; denied read/write, removal, cross-tab no-echo, OS change in System vs explicit mode, listener cleanup, bootstrap/store parity. |
| Selection components | Once behaviorally: both choosers synchronized, keyboard radio groups, current/effective labels, immediate apply, focus preserved, general settings failure independent. |
| No-flash browser tests | Cold/hot reload under stored Light/Dark conflicting with OS, all palette attributes before first paint, throttled app loading, CSP failure fallback, auth route, storage denied. Capture before React effects. |
| Color/contrast | All six variants, all meaningful foreground/background pairs including hover/selected/errors, SVG/canvas resolved colors; run the design calculator then assert production computed values. |
| Shared behavior regression | Once per feature: filters/search, Saved Views, menus, focus return, dirty/pending dialog safety, contextual/direct editors, selection, modified-click navigation. |
| Visual captures | All six: directory + selected row/Quick Preview, one detail, form/modal, map shell and Settings/footer. Controls specimens additionally cover six requested toolbar contexts. |
| Risk-based real browser expansion | Botanical Light + Dark across all families and 1440×844, 1024×844, 390×844; Herbarium/Mineral Light/Dark capture their highest-risk text/overlay/map states. Do not multiply all unit suites by six. |
| Native widgets / media | Date/select/file inputs, scrollbars, tooltip at viewport edges, dialogs/drawers and images under both modes; no external media request on theme switch. |
| Maps | Three renderers: selection/camera persists, five species distinguishable beyond hue, unknown/unmapped and overlap, legend/attribution readable; network spy proves no theme-caused provider requests. |
| Print | Both screen modes, all existing presets, black/white QR and unchanged mm/quiet-zone geometry. Browser print/PDF evidence and physical printer evidence labelled separately. |
| Accessibility | Keyboard, screen reader names/descriptions, coarse pointer and touch, forced colors, reduced motion, long names/unknown data, 320px reflow and actual browser zoom 125%/150%. Proxy captures are not zoom evidence. |

Component focus for CONTROLS is detailed in its contract. Include timer/hover-transfer cases plus real
native-dialog top-layer tests; jsdom cannot certify clipping. Record exact browser/AT versions and
which combinations were actually tested. Contrast calculations do not replace perceived-focus,
color-vision, provider-image or native-widget checks.

For each later implementation: narrow meaningful baseline, focused tests while editing, independent
domain/UI/diff review, fix ordinary defects, freeze source, then the authorized canonical
`make feature-verify`. Do not manually duplicate covered gate stages. Final tree changes invalidate
the receipt. Respect that phase's precise stage/commit/delivery marker; this plan is not permission
to run any lifecycle command now beyond initializing this design branch.

## Proposed Phase 2 prompts

**THEMES prompt outline:** implement approved THEMES design/token matrix on the provided managed
worktree after reconciling current main; preserve accepted typography/layout and UI/domain contracts;
implement browser-local bootstrap/store and two-axis chooser; migrate all UI colors, three map
renderers and print policy atomically; use labelled existing controls; run the scoped evidence matrix;
update docs/features/progress and stop at the operator's explicit review/delivery boundary. Do not
implement CONTROLS or remaining-page normalization in that branch.

**CONTROLS prompt outline:** implement approved controls contract as a separate increment after
checking current main and THEME integration; consolidate local icons and three action patterns,
accessible Tooltip/overlay host and responsive adoption across audited consumers; retain action
labels, queries, routes, focus, print artwork and evidence semantics; prove modal/touch/keyboard
behavior and six-variant styling; update evidence/docs and stop at the operator's explicit boundary.
No theme-state rewrite or broad page normalization.

## Design-phase evidence and limits

Baseline `python3 scripts/check-features.py`: 108 valid; baseline `git diff --check`: passed.
The design calculator and artifact structural checks are recorded in the progress milestone.
No runtime suites, canonical verification, server, protected environment, physical printer or product
visual acceptance is claimed. Review specimens are proposals, not captures of an implemented product.
