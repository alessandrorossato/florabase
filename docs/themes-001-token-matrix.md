# THEMES-001 — Proposed six-variant token matrix

Status: proposed values, 22 October 2026. Source of reproducible proposal data:
[palette-proposal.json](design/themes-controls/palette-proposal.json). No production tokens changed.

## Semantic UI values

All hex values are opaque sRGB. Typography, spacing and geometry stay in the existing UI Foundation.
Columns BL/BD/HL/HD/ML/MD mean Botanical, Herbarium, Mineral × Light/Dark.

| Role | BL | BD | HL | HD | ML | MD |
| --- | --- | --- | --- | --- | --- | --- |
| background | `#f6f7f3` | `#151c18` | `#f7f4ed` | `#1d1b17` | `#f3f6f8` | `#151c23` |
| surface | `#ffffff` | `#1d2721` | `#fffdf8` | `#28251f` | `#fcfdff` | `#1d2832` |
| surface-subtle | `#eef1ec` | `#242f28` | `#f0ece2` | `#302d25` | `#eaf0f4` | `#25323e` |
| surface-hover | `#e7ede6` | `#2d3b32` | `#e9e4d7` | `#3b372d` | `#e2eaf0` | `#2d3d4b` |
| text | `#1e2621` | `#e5ece6` | `#2b2921` | `#eee9dd` | `#202a33` | `#e3ebf3` |
| text-muted | `#5c665e` | `#b1beb4` | `#655f50` | `#c4bba8` | `#566571` | `#b2c2d0` |
| border | `#dde3dc` | `#3b4a40` | `#ded8c9` | `#4c473a` | `#d4dfe6` | `#3d4e5e` |
| border-strong | `#7c8980` | `#82978a` | `#827967` | `#9c9179` | `#6d7f8c` | `#8299ae` |
| primary | `#2f684f` | `#8dc5a3` | `#62613b` | `#c6c18b` | `#345f7c` | `#9bbfdc` |
| primary-hover | `#24533e` | `#acd8bd` | `#4b4b2c` | `#dcd6a4` | `#294b62` | `#b8d4e9` |
| primary-subtle | `#e7f0ea` | `#283e30` | `#ecebdc` | `#3a3b29` | `#e4edf4` | `#293d4e` |
| on-primary | `#ffffff` | `#14251c` | `#ffffff` | `#252517` | `#ffffff` | `#172735` |
| success | `#276d4c` | `#8bc8a3` | `#276d4c` | `#8bc8a3` | `#276d4c` | `#8bc8a3` |
| warning | `#a66a16` | `#e2b66e` | `#a66a16` | `#e2b66e` | `#a66a16` | `#e2b66e` |
| warning-text | `#85520c` | `#e8c184` | `#85520c` | `#e8c184` | `#85520c` | `#e8c184` |
| danger | `#a13b3b` | `#f0a3a3` | `#a13b3b` | `#f0a3a3` | `#a13b3b` | `#f0a3a3` |
| danger-subtle | `#fbefef` | `#3b272b` | `#fbefef` | `#3b272b` | `#fbefef` | `#3b272b` |
| warning-subtle | `#fbf4e7` | `#3b3223` | `#fbf4e7` | `#3b3223` | `#fbf4e7` | `#3b3223` |
| info | `#3d6f8e` | `#9bc5e0` | `#35627d` | `#9bc5e0` | `#35627d` | `#9bc5e0` |
| focus-ring | `#3d6f8e` | `#9bc5e0` | `#35627d` | `#9bc5e0` | `#35627d` | `#9bc5e0` |
| overlay-backdrop | `rgb(30 38 33 / 55%)` | `rgb(0 0 0 / 64%)` | `rgb(30 38 33 / 55%)` | `rgb(0 0 0 / 64%)` | `rgb(30 38 33 / 55%)` | `rgb(0 0 0 / 64%)` |
| elevation-overlay | `0 8px 32px rgb(30 38 33 / 16%)` | `0 8px 32px rgb(0 0 0 / 32%)` | `0 8px 32px rgb(30 38 33 / 16%)` | `0 8px 32px rgb(0 0 0 / 32%)` | `0 8px 32px rgb(30 38 33 / 16%)` | `0 8px 32px rgb(0 0 0 / 32%)` |

## Data-viz values (independent of UI palette)

| Role | All Light palettes | All Dark palettes |
| --- | --- | --- |
| Comparison identity slot 1 | `#287c67` | `#77bda8` |
| Comparison identity slot 2 | `#aa562d` | `#d9a07b` |
| Comparison identity slot 3 | `#5467b2` | `#a6b3ed` |
| Comparison identity slot 4 | `#9a477a` | `#dca0c2` |
| Comparison identity slot 5 | `#81701f` | `#ccbf79` |
| Native count low | `#b5cdc0` | `#547764` |
| Native count mid | `#729f86` | `#77a58a` |
| Native count high | `#2f684f` | `#8dc5a3` |

Native count bins retain `coverageScale` semantics; compare colors retain identity slots, not literal
stored hex strings. Proposed appearance mapping is display-only and must not mutate Saved View
state. Unselected land uses border, map background uses surface; neutral text/strong borders and
numeric/pattern equivalents carry meaning where fills are low contrast. Comparison swatches are
checked against surface, not arbitrary external raster pixels or each other. Accuracy circles use
primary stroke and current 0.08 fill opacity, with a neutral casing where needed; coordinates and
accuracy never change. Provider density ramps, basemaps and photographs keep their original colors.

## Calculated evidence and permitted use

Run `python3 docs/design/themes-controls/check-contrast.py` to regenerate
[72 contrast cases](design/themes-controls/contrast-evidence.md). Every proposed case passes the
unrounded threshold. The calculator uses the WCAG sRGB transfer function (`c/12.92` up to 0.04045,
otherwise `((c+0.055)/1.055)^2.4`), luminance weights 0.2126/0.7152/0.0722 and
`(lighter + 0.05)/(darker + 0.05)`. Ratios displayed to two decimals are not used for acceptance.
See [WCAG text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) and
[non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html).

The worst UI surface is the minimum over background, surface, surface-subtle, surface-hover and
primary-subtle. Additional status cases include their subtle backgrounds. Tests cover normal/muted
text, primary normal/hover labels, quiet/selected primary text, boundaries, info/focus, status text,
warning symbols, tooltip text and all five comparison swatches. Large text inherits passing normal
text colors. Tooltip border inherits the tested surface/border-strong pair. Disabled muted text uses
the same opaque colors; actual disabled controls are contrast-exempt but still get readable labels.

Selected navigation/list rows use text or primary on primary-subtle with a primary edge/check;
selection fill alone is not sufficient contrast. Focus-ring has a 3px outline and 3px offset on
neutral UI; a gap/backplate isolates it from filled actions or arbitrary map imagery. If implementation
places focus directly against another colored fill, calculate that pair or use the contrasting gap.
No single ring color is guaranteed against every provider image.

The ordinary border is decorative and intentionally not 3:1. Use border-strong when a boundary is
the identifying input/control cue. Warning is for symbols/edges; small text must use warning-text.
Danger uses readable text/border on surface or danger-subtle, not untested white-on-danger. Form
validation pairs text with field identifiers/messages and state, not just a red border. Success has
explicit text; unknown and disabled do not borrow success/warning meanings.

Overlay backdrop is composited over variable content, so no standalone AA ratio is claimed for it.
Dialog and tooltip content sits on opaque surface, not on the translucent backdrop. Shadows are
nonessential; never use them as the only boundary. Native low/mid count fills are not claimed as
independently contrasting UI controls; neutral boundaries plus numeric legends/inspection provide
an equivalent reading path. Five colors passing against surface does not establish color-vision
separability; paired number/pattern labels and simulations remain required.

## Botanical Light compatibility adjustments

Keep background/surfaces, text, primary/hover/subtle, warning, info/focus and on-primary exactly as
accepted, including border-strong `#7c8980`. Propose only these targeted foreground corrections
for shared use on all permitted surfaces: text-muted `#667068` → `#5c665e`;
success `#2f7d57` → `#276d4c`; danger `#b54747` → `#a13b3b`. These protect smaller text on
hover/selection surfaces. Against the current surface-hover
`#e7ede6`, the original muted/success/danger values calculate to 4.3243:1, 4.2114:1 and
4.4614:1 respectively; all fall below 4.5:1. The existing strong border calculates to
3.0719:1 and is preserved. They require visual acceptance; “visually equivalent” does not
mean unchanged hex values. Herbarium/Mineral Light use darker info/focus `#35627d` because `#3d6f8e`
failed the shared small-info-text threshold on their darkest permitted subtle surface.

## Evidence limits

These are proposed foreground/background computations, not a WCAG conformance claim for the app.
Implementation must verify actual computed styles, alpha compositing, SVG strokes, overlays, native
widgets, provider backgrounds and disabled overrides. Color-vision, forced-colors, browser zoom,
focus visibility, touch, screen readers and paper print remain in the implementation matrix. The
[visual review sheets](design/themes-controls/review.html) are schematic design artifacts, not
production screenshots. No theme is enabled by adding these documents.
