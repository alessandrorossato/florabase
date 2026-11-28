# THEMES-001 review evidence

Candidate source: `/home/alessandro/.codex/worktrees/b64e/florabase`, `feat/themes-001`, base `b3f1de4`.
All screenshots and measurements are candidate evidence pending operator acceptance.

The operator authorized a handover preserving Review database and media. The existing repository
helper cannot transfer source-labelled volumes without deleting them. The candidate therefore uses
an explicitly labelled split runtime: this worktree's frontend, launched through its isolated Quality
Compose helper on loopback `15174`, connected to the retained Feature Review backend/API. The database,
media, fixtures, login and sessions remain owned by `c902`; no volumes or database contents were reset,
removed, copied or reseeded. Its production backend source equals the current base (only its separate
frontend/maps/workflow candidate differs). The candidate frontend uses its own dependency volume and
source bind. This is not a claim that `make feature-review-status` recognizes a full ownership transfer.

## Captures

Open [gallery.html](gallery.html) for the full-resolution image index.

- 126 actual browser viewport captures cover all six variants with the same content on each surface.
- Settings, Dashboard, directory/Quick Preview, edit modal and native comparison cover
  1440×844, 1024×844 and 390×844. Other representative surfaces cover 1440×844.
- Detail dashboard, create form, filter drawer, native-range exploration, Species distribution and
  Collection origins have six desktop variants.
- 16 additional Botanical Dark captures cover the remaining page families. Plants and PlantGroups
  were recaptured after confirming populated records (24 combined; seven filtered groups).
- An additional `labels-preview-botanical-dark-1440.png` shows white label paper in Dark mode;
  no QR destination was configured or saved.
- `browser-evidence.json` records actual root attributes, route, viewport, scroll width and 20 computed
  semantic colors for each six-theme image. `family-evidence.json` records the additional pages.
- `evidence-check.json`: no root horizontal overflow; all 2,520 measured color values equal the approved
  palette matrix. This checks the root contract, not every descendant contrast or internal scroller.
- Cross-tab preference changes drove the actual app during capture; these are not iframe/viewport
  proxies. Preliminary proxy files were removed. No browser zoom or physical device claim is made.

## Limits

Screenshots are candidate review evidence, not independent acceptance. Species distribution shows
selected identity with no downloaded raster: the fixture's GBIF identifier is synthetic, so no provider
load was requested. Original density ramp and generation/layer behavior have regression coverage.
Origins screenshots use the delivered main renderer; the separate MAPS-ORIGINS-001 candidate had not
merged. Its local geography/online toggle must receive a later integration review. The existing tile
URL set stayed unchanged across six themes (`origin-theme-tiles.json`, 54 images); this is a DOM check,
not a browser network trace. Unit renderer tests additionally assert no theme-triggered fetch/remount.

Real zoom, touch hardware, assistive technology, OS forced-colors and physical printing were not
certified. Existing browser login and populated fixture/media data were retained. No screenshots or
metadata contain login credentials. Review data is synthetic fixture content.

## Validation snapshot

Final frontend run: **850/850 tests, 74 files, zero failures/skips**. See `test-results.json`.
The initial UX004 test-stub leak was repaired by resetting the complete browser API stub before each
bootstrap; its 27-test targeted retry and the complete rerun pass without weakened assertions or
timeouts. Full raw reports remain ignored under `frontend/coverage/themes-001-results/`.
