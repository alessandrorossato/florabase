# MAPS-FOUNDATION-001 visual evidence

**Current: [spatial exploration and five-layer comparison, 2026-10-20](spatial/README.md).**
[Earlier overview/chooser refinement](refinement/README.md) is historical.
[Previous authenticated review](live/README.md) and the offline snapshots below are historical evidence.

2026-10-18. **Offline synthetic component snapshots, not the authenticated Feature Review.**

The React NativeRangesScreen and real local geometry were rendered in the existing Vitest/jsdom
harness with mocked local API responses. The fixture was aligned across the directory, overview
and comparison: four represented identities, three with ranges and one without; overview Brazil 3 /
Argentina 2. Two selected synthetic identities contribute once each to Brazil and Argentina.
Names and botanical relationships are deliberately synthetic and make no real botanical assertion.

The resulting DOM was serialized (including live checkbox properties), then loaded as a local HTML
file in headless Firefox with a dedicated ignored profile under this worktree's node_modules.
Current token/base/foundation/normalization/map CSS and bundled Latin fonts were embedded. The shell
is an explicitly labelled static context, **not the actual App navigation or mobile navigation**.
Temporary fixture code/HTML/profile are not part of the candidate. No web server, backend, Compose
project, Review, UAT, DEV, Stable Preview or production environment was started or changed.

## Captures

| Capture | Viewport | Inspection |
| --- | --- | --- |
| [Overview](overview-1440.png) | 1440×844 | Map dominates left area; compact toolbar; species rail; counts and discrete legend |
| [Comparison](comparison-1440.png) | 1440×844 | Two checked species; inspected Brazil outlined; map precedes selected-species list |
| [Single species](single-1024.png) | 1024×844 | Compact header, explicit pane switch, recorded identity and existing links, full-width map area |
| [Mobile overview](overview-390.png) | 390×844 | Wrapped header/actions; compact summary; map starts in first viewport and continues in document flow |
| [Mobile species](species-list-390.png) | 390×844 | Selected browser pane; real checkbox/text selected state, long cultivar wrapping |
| [Comparison detail](comparison-1440x1800.png) | 1440×1800 | Supplementary tall viewport exposes legend, inspector, contributor list and Remove/View only |
| [Mobile map detail](overview-390x1600.png) | 390×1600 | Supplementary tall viewport exposes map, legend, caveat, territory buttons and exact-place section |

Each capture includes a diagnostic footer reporting viewport and document scroll/client widths.
At required widths the reports are **1428/1428**, **1012/1012**, **378/378** respectively: no horizontal
page overflow in these static fixtures. Scrollbars account for the difference from window width.
The tall desktop capture has **1440/1440**; tall mobile has **378/378**. Tall viewports are explicitly
additional content inspection, not a claim that everything fits at 844px height.

Initial snapshots exposed excess space above the map, an inherited column/flex-basis interaction
at tablet width, and over-tall mobile summary rows. Scoped Native ranges corrections were made and
these captures replaced the initial images. No shared header or global style was changed.

## Limits and next review

These screenshots establish CSS/layout and visible content for synthetic states. They do not test
live React event behavior, database/API integration, actual browser zoom, screen-reader announcement,
physical touch targets on a device, mobile bottom-navigation clearance, or live network traffic.
Interaction tests cover the real components separately; static pane snapshots do not certify browser
switching. Real Review must cover those items once its owner explicitly makes a slot available.

The first sandboxed Firefox process failed; an approved isolated-profile launch succeeded. One later
launch was stopped by an automatic approval-service usage limit (not an unsafe-action decision).
After the operator requested continuation, approved renders completed. No blocked launch was bypassed.
