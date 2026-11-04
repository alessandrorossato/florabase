# Evidence used by this review

**Status: PROPOSED / AWAITING DESIGN APPROVAL.** Everything here is **EVIDENCE (1 Nov)** or
**VERIFIED (source)**. The captures are referenced in place under `docs/design/ui-system-v1/`; this
package does not copy them.

## Browser captures (1 November 2026)

All captures were taken on the Wave 3 branch with the synthetic Review v5 fixture, in Mineral Dark
unless stated otherwise. That branch's frontend source is the source merged into `61fefbb`
(#134–#138; later frontend commits change tests only). The files are JPEG data despite their `.png`
names.

| Capture | Shows | Used for |
| --- | --- | --- |
| [final-interaction-correction/evidence/plants-390.png](../../design/ui-system-v1/consolidation/final-interaction-correction/evidence/plants-390.png) | Plants Gallery, 390×900 | F-01, F-02 re-check |
| [final-interaction-correction/evidence/plants-1024.png](../../design/ui-system-v1/consolidation/final-interaction-correction/evidence/plants-1024.png) | Plants Gallery, 1024×900 | F-15, D1 |
| [final-interaction-correction/evidence/sowings-germination-details.png](../../design/ui-system-v1/consolidation/final-interaction-correction/evidence/sowings-germination-details.png) | Sowing Details, Germination tab, 1440×900 | F-03, F-12, F-14 |
| [details-cover/evidence/supplier-1440.png](../../design/ui-system-v1/consolidation/details-cover/evidence/supplier-1440.png) | Supplier Details, 1440×900 | Reference for the flat Details pattern |
| [final-interaction-correction/evidence/seeds-dedicated-details.png](../../design/ui-system-v1/consolidation/final-interaction-correction/evidence/seeds-dedicated-details.png) | Seed lot Details with the pre-Gate B panel | F-04 (historical only) |
| [final-interaction-correction/evidence/plants-directory-1440.png](../../design/ui-system-v1/consolidation/final-interaction-correction/evidence/plants-directory-1440.png) | Desktop Plants capture, caught "Loading workspace…" | F-17 |

The paths are relative to `docs/design/ui-system-v1/consolidation/`. The same six images are
uploaded to the design artifact's Evidence group for its BeforeAfter card.

## Source scans (`61fefbb`)

The counts in [audit.md](audit.md) and [findings.md](findings.md) come from plain `grep` scans of
`frontend/src`, excluding tests where stated. Examples:

- `window.confirm` calls outside tests: 21, in 14 files.
- `styles.css`: `font-size: <number><unit>` ×149, `font-weight: <3 digits>` ×78, raw `border-radius` ×105, `999px` ×13, raw `box-shadow` ×17.
- `outline-offset` values across all CSS: 2px ×16, −3px ×13, −2px ×10, 3px ×6, −6px ×1.
- `<label` ×192 vs `<FieldLabel` ×64.
- Media queries by width: 48rem ×103, 64rem ×32, 40rem ×17, 75rem ×13, 30rem ×8, 68rem ×7, 850px ×4, 25rem ×4, 1100px ×3.

Contrast ratios were computed with the WCAG 2 relative-luminance formula from the six theme blocks in
`frontend/src/styles/tokens.css`. They were not measured on rendered pixels.

## Not available

- A live authenticated session on current main.
- Physical devices, screen readers, real browser zoom, forced colors.
- A loaded desktop Plants directory capture (F-17).
