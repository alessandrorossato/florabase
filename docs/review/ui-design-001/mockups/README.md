# Design mockups — not production screenshots

**Status: PROPOSED / AWAITING DESIGN APPROVAL.** Every image in this folder is a **design mockup**.
None of them is a screenshot of the Florabase application. Each one has a visible banner reading
"DESIGN MOCKUP · UI-DESIGN-001 proposal · … · not a screenshot of the production application". Never
use these images as release, marketing or public screenshots.

## What they are

- **PROPOSAL** compositions from the [UI-DESIGN-001 design artifact](https://claude.ai/artifact/T5A2PpURaCtwGxYTU6F8eN)'s
  `PlantsWorkspace` showcase. They are hand-built React recreations of the house primitives, styled
  only by the existing semantic tokens (copied from `frontend/src/styles/tokens.css`).
- They illustrate the proposed option for D1, D2, D4, D5 and D6. That is not a decision; see
  [decisions.md](../decisions.md).
- **Data is synthetic and invented for the mockup.** "Bench maple" and "Kitchen aloe" are made-up
  records, not fixture rows, owner data or real locations.
- They were rendered on 4 November 2026 with html2canvas 1.4.1 at emulated CSS viewports. See
  [manifest.json](manifest.json) for each viewport, raster size, theme, state, the findings it
  illustrates, and its SHA-256.

## Known raster artifacts

These come from the rasterizer, not the design. The live artifact renders them correctly:

- The search icon is clipped to its left arc.
- Native `<select>` controls lose their chevrons.
- The dialog body shows a faint inner surface edge.
- 1320px captures are 1305px wide (the page scrollbar is excluded).

## Images

| File | Screen | Viewport · theme | Illustrates |
| --- | --- | --- | --- |
| [mockup-plants-directory-list-1320-botanical-light.png](mockup-plants-directory-list-1320-botanical-light.png) | Plants directory, List | 1320 · Botanical Light | F-01, F-04, F-08 |
| [mockup-plant-details-1320-botanical-light.png](mockup-plant-details-1320-botanical-light.png) | Plant details, Overview | 1320 · Botanical Light | F-03, F-05, F-09, D4, D5 |
| [mockup-plant-edit-discard-confirmation-1320-botanical-dark.png](mockup-plant-edit-discard-confirmation-1320-botanical-dark.png) | Plant edit + discard confirmation | 1320 · Botanical Dark | F-02, F-13 |
| [mockup-plants-empty-filtered-1320-herbarium-light.png](mockup-plants-empty-filtered-1320-herbarium-light.png) | Empty filtered result | 1320 · Herbarium Light | States |
| [mockup-plants-gallery-1024-botanical-dark.png](mockup-plants-gallery-1024-botanical-dark.png) | Gallery, tablet | 1024 · Botanical Dark | D1, D2, F-15 |
| [mockup-plants-directory-390-botanical-light.png](mockup-plants-directory-390-botanical-light.png) | Directory, phone | 390 · Botanical Light | F-01, D6 |
| [mockup-plant-details-390-mineral-dark.png](mockup-plant-details-390-mineral-dark.png) | Details, phone | 390 · Mineral Dark | F-03, D4, D5 |

The paired "before" evidence is listed in [evidence.md](../evidence.md). The interactive comparison
(captured current UI beside the proposal) is the BeforeAfter card in the design artifact.
