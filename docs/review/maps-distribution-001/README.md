# MAPS-DISTRIBUTION-001 initial browser evidence (before cache refinement)

These captures precede the final refinement and do not demonstrate its persistent cache or
expanded Data details layout. The old unloaded-restoration behavior described below is
superseded by local-only restoration. See [current handoff](../../maps-distribution-001-handoff.md)
for current behavior, live HTTP cache replay and remaining browser checks.

Captured 2026-10-21 from the candidate-owned `florabase-feature-review` at
<http://localhost:15174/#/species-distribution>, `b139` / `feat/maps-distribution-001`,
base `9275947`. The Review uses a fresh supported v4/80 synthetic collection and its
own DB/media/dependency volumes. No production or Sourcing data appears here.

| File | Viewport | State |
| --- | --- | --- |
| [Desktop ready](desktop-ready.png) | 1440×844 | Selected linked Basil, explicitly unloaded; map placeholder and identity inspector |
| [Desktop loaded](desktop-loaded.png) | 1440×844 | Real GBIF density and textual inspector, with incomplete-tile warning |
| [Tablet map](tablet-map.png) | 1024×844 | Corrected compact header, map pane, explicit Inspector switch, live density |
| [Mobile map](mobile-map.png) | 390×844 browser viewport, full document capture | Compact header/counts, map pane and density legend with incomplete-tile warning |

These are live authenticated application captures, not fixture-only renderer mockups.
The first request returned 3,783 eligible mapped / 9,775 all matching PRESENT GBIF records.
Provider values are request-specific. Some tiles failed; the warning is retained rather
than presenting the map as complete. Tile retry kept the textual summary available.

Measured document width did not exceed viewport width at 1440, 1024 or 390 pixels.
The desktop map was about 777×439 px, beginning around y=345 even with the tile warning.
Mobile and tablet Map/Inspector switching retained the loaded identity and counts.
A further compact warning/count adjustment occurred after the desktop/tablet captures;
the current candidate is authoritative for that minor wrapping refinement.

Additional direct checks: mobile cultivar search for Genovese, keyboard-focus eligibility
preview without selection, selection focus returning to Choose species, missing-link
explanation, and actual Back/Forward between selected and unselected local state.
The live Saved View `Distribution review — Basil` was saved in Review. After browser
input timeouts, keyboard activation successfully reopened it: the selected identity
restored, the explicit Load button was visible and the interactive map-region count was
zero. This confirms same-identity restoration unloads previously loaded occurrence
evidence. Automated tests also cover create/open, pagination reset and unloaded restoration.
A separate screenshot of the reopened view timed out; this additional observation is DOM
and keyboard evidence, not a claimed image capture.

The initial tablet capture revealed legacy flex-basis rules creating excessive vertical
header gaps. A scoped correction was applied and the tablet capture replaced after
verification. No shared header/Native ranges stylesheet was changed.

Actual browser zoom, an actual screen reader and physical-touch validation were not
performed. Viewport emulation and DOM snapshots do not certify those behaviors.
See [the handoff](../../maps-distribution-001-handoff.md) for final checks and ownership.
