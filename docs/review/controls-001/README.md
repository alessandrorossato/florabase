# Controls review evidence

Combined THEMES + CONTROLS candidate on `feat/themes-001`, base `b3f1de4`.
See [handoff](../../controls-001-handoff.md) for source inventory, validation and pending acceptance.
[Gallery](gallery.html) links original exports. [DOM measurements](browser-evidence.json) and
[checks](evidence-check.json) record exact layout viewport, resolved theme, icon/action geometry,
open-tooltip computed colors and visible hit tests.

- 113 authenticated product screenshots; all six variants. Seeds and the filter drawer cover
  1440×844, 1024×844 and 390×844. Other representative desktop/mobile and page-family checks are
  enumerated in the handoff and gallery. No root viewport overflow was measured.
- Three component-fixture PNGs are separate from product screenshots: native manual popover,
  fixed fallback escaping modal clipping, and scroll-panel Tooltip. Their keyboard/Escape/scroll
  results are in [interaction evidence](interaction-evidence.json). Fixture-only actions wrote no
  application data; the temporary development harness was removed.
- [System reload](system-reload.json) confirms checked Botanical/System and resolved Dark after
  an actual reload. [Origins tiles](origin-theme-tiles.json) records unchanged DOM URLs across six
  variants; this is not a network trace or downloaded-raster acceptance.
- The in-app browser can scale an image export on scrolling pages. `width`/`height` are actual DOM
  layout viewport dimensions; `bitmapWidth`/`bitmapHeight` are the export dimensions. No images
  were upscaled. These are not proxy/browser-zoom captures.
- Earlier Controls frames precede final navigation-label and trailing-chevron refinements; the
  later Dashboard/utility frames reflect the final source. The original 143 Themes PNGs and design
  specimens are preserved separately, not represented as current Controls evidence.
- Open Tooltip computed text/border contrast and hit tests pass in all six variants; existing
  production theme tests cover common text/buttons/focus. Physical touch, screen readers, browser
  zoom, OS forced colors, physical printing and real provider raster remain pending.

Review remains at [Settings](http://localhost:15174/#/settings) with retained authentication/data.
The source ownership mismatch and split runtime are explicit in both handoffs; this is not a supported
full Review transfer or production smoke. No gate, staging, commit or delivery is claimed.
