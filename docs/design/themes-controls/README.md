# THEMES-001 / CONTROLS-001 design review assets

These are documentation artifacts, not application runtime code, a functional prototype, or accepted
product screenshots. Open `review.html` in a browser and select one of six palette/mode variants and
1440, 1024 or 390 CSS px. All six requested control contexts are included in each combination,
followed by form/modal, map, Settings/footer and icon/tooltip specimens.

The sheet uses content-area excerpts rather than reproducing the full sidebar and 844px viewport.
Its desktop widths are review canvases, not a claim of real application viewport acceptance. Source
Sans/Serif font families and existing scale are requested, with local fallbacks; no font assets are
copied or downloaded. Map outlines reuse the repository's Natural Earth public-domain geometry;
unselected outlines intentionally make no range/provenance claim. No API, storage or provider calls.

Regenerate from repository source:

```sh
python3 docs/design/themes-controls/check-contrast.py
python3 docs/design/themes-controls/build-review.py
```

`palette-proposal.json` supplies proposed values. The calculator writes `contrast-evidence.md`,
compares unrounded sRGB ratios and exits unsuccessfully on failure. `build-review.py` reads that
proposal and the existing map geometry to write a self-contained `review.html`. These are bounded
review utilities and are not imported by the application or verification gate.

Browser evidence on 22 October 2026: the review sheet loaded in the Codex in-app browser; all 18
palette/width combinations had sheet scrollWidth equal to chosen width and no visible action/search/
tool-group/directory/map-layout bounds escaping the sheet. Phone Botanical Dark was inspected visually.
This is **specimen geometry evidence**, not real app reflow, full-browser resizing, browser-zoom,
tooltip-interaction, screen-reader or physical-printer certification. Design calculation: 72/72 pairs
pass; remaining production validation is in the implementation plan.
