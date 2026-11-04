# Audit — current UI at `61fefbb`

**Status: PROPOSED / AWAITING DESIGN APPROVAL.** Labels follow the [package legend](README.md#how-to-read-this-package).

**Method.** A source scan of `frontend/src` at `61fefbb`, plus browser captures from the 1 November
Wave 3 evidence sets (synthetic Review v5 fixture). There was no live session on current main.
Every visual claim cites either a 1 November capture or a source line, never a fresh observation.

## Verdict

**EXISTING.** Florabase already has a sound, documented system: six themes, a nine-step type scale,
semantic tokens, shared Directory/Detail/Activity compositions and an accessible control vocabulary.

**VERIFIED (source).** Every text/ground pair in `tokens.css` passes WCAG AA in all six themes, by
computation (lowest 5.05:1, `focus-ring` on Botanical Light `background`; `border-strong` on `surface`
≥ 3.65:1).

The remaining inconsistency is **drift at the edges**, not a missing system:

1. **VERIFIED (source).** The 8,751-line legacy `styles.css` still carries its own scale: 149 raw
   `font-size` declarations in about 30 values, 105 raw radii, 17 raw shadows and 13 pill shapes. Part
   of it out-specifies the contract.
2. **VERIFIED (source) + EVIDENCE (1 Nov).** Shared primitives cover structure, but action grammar
   (which action is primary, casing, back affordance) and confirmation (native `window.confirm`) are
   still decided per page.
3. **EVIDENCE (1 Nov).** Compact layouts spend most of the first viewport on tools.

A small set of reusable rules ([proposed-changes.md](proposed-changes.md)) addresses most of this
without redesigning individual screens. That is a **PROPOSAL**.

## By criterion

| Criterion | Current state | Label | Evidence |
| --- | --- | --- | --- |
| Visual hierarchy and typography | Token scale is used by the newer layers. The legacy layer uses about 30 sizes (0.65–2rem) and weight 700. Record titles render as `h3` in 9 of 10 Details families | VERIFIED (source) | `styles.css` scan: 149 `font-size`, 78 `font-weight`, 0 `font: var(--type-*)`. `components/CollectionUI.tsx:94` `headingLevel = 3`; only `botanical-identities/BotanicalIdentityScreen.tsx:468` passes `2` |
| Spacing and density | Desktop directories are consistent after Gate B. On a 390px phone, tools wrap into three rows plus a two-row results bar; the first Plants card starts at ≈533 of 900 px | EVIDENCE (1 Nov) | [plants-390](../../design/ui-system-v1/consolidation/final-interaction-correction/evidence/plants-390.png) |
| Buttons, icons, actions | One geometry (`control-action`, 44px) and a direct Details/Edit pair (EXISTING). Prominence and casing vary: Record harvest is primary on a Plant, secondary on a Plant group; "Edit Sowing" vs "Edit seed lot"; Sowing Details shows two filled primaries; 8 typed `←` labels although the `back` icon exists | VERIFIED (source) + EVIDENCE (1 Nov) | `plants/PlantScreen.tsx:455–476`; label scan; [sowings-germination-details](../../design/ui-system-v1/consolidation/final-interaction-correction/evidence/sowings-germination-details.png) |
| Accessibility and keyboard | Visible focus everywhere (EXISTING), but the 3px/3px contract is undercut: `styles.css:427–431` `button/input:focus-visible` (2px offset) beats the zero-specificity `:where()` rule at `styles/foundation.css:17`. Offsets in use: 2px ×16, −3px ×13, −2px ×10, 3px ×6, −6px ×1. Dirty-draft guards use 21 native `window.confirm` calls in 14 files | VERIFIED (source) | CSS scan; `grep window.confirm` |
| Responsive usability | No page-level overflow in the Wave 3 matrix (EXISTING). Breakpoints: 48/64/75rem dominate, plus 12 one-off queries (68rem, 40rem, 30rem, 25rem, 850px, 1100px, 800/700/600px) and duplicates (`48.01rem` vs `48.001rem`) | VERIFIED (source) | media-query scan |
| Information architecture | Primary navigation (Overview, Collection, Activity, Explore, Sourcing) is stable and clear (EXISTING). Sowing and Plant Details still render a context row (← Back, New) above the breadcrumb (C5), so their titles sit lower than other families | VERIFIED (source) + EVIDENCE (1 Nov) | `plants/PlantScreen.tsx:2484–2494`, `sowings/SowingScreen.tsx:1057` |
| Cross-area consistency | `LifecycleStatus` is the norm (EXISTING), but `.lifecycle-badge` (pill, 700) survives in `provenance-map/OriginInspector.tsx:26`, and `.record-type-badge` and `.ui-status-indicator` are CSS with no TSX users. Metrics: DetailSummary, StatStrip and uppercase-eyebrow metric blocks (Sowing germination) coexist | VERIFIED (source) + EVIDENCE (1 Nov) | CSS/TSX scan; sowing capture |

## Earlier findings re-checked against main

| Finding | Status on `61fefbb` | Label |
| --- | --- | --- |
| RELEASE-VISUAL-AUDIT F09: tablet header grew to 880px | **Resolved.** `styles/normalization.css:113` sets `flex-direction: row` alongside the flex bases | VERIFIED (source) |
| RELEASE-VISUAL-AUDIT F01: destructive dialog focused Delete | **Resolved at callers.** In every dialog in the 12 files with danger buttons, the danger button follows Cancel. The shared `TaskDialog` still focuses "first focusable" (`components/TaskDialog.tsx:64`), so safety depends on markup order. An explicit `initialFocus` is a PROPOSAL | VERIFIED (source) |
| RELEASE-VISUAL-AUDIT F02: mobile chrome | **Partially resolved.** The mobile top line is brand-only; tool rows still consume most of the first viewport | EVIDENCE (1 Nov) |
| UI-DETAIL-001: Details parity | **Closed for Wave 3 by operator UAT.** The documented residue is still in source: the C5 context row (Plant/Sowing), lifecycle shown in both header and DetailSummary (`plants/PlantScreen.tsx:444` and `:525`), unused `.seed-overview-facts` | VERIFIED (source) |
| UI-FLICKER-001: title flicker | **Still partially resolved; not re-measured.** No layout source changed after the 1 November measurements, so the three P3 observations (390px direct-load title gap, long-breadcrumb wrap, C5 offset) are presumed open. Closure needs a live delayed-network re-measure (implementation plan, phase 0) | VERIFIED (source, `git log`); not observed live |
| Wave 3 QA-1 to QA-4 | Addressed by UI-POLISH-001 (status `implemented`, not `verified`) | EXISTING (documented) |
| Wave 3 QA-5 to QA-10 | Open; not revalidated here. QA-8 (Locations without `h2`) extends to the `h3` default above | EXISTING (documented) + VERIFIED (source) for the heading default |

## Evidence limits

- No live browser session on current main. Screenshots are from 1 November.
- The 1 November desktop Plants capture shows "Loading workspace…". The evidence set has **no
  loaded desktop Plants directory capture**.
- Real browser zoom, screen readers, physical touch devices and forced colors were not exercised.
  Contrast figures are computed from `tokens.css`, not measured on rendered pixels.
