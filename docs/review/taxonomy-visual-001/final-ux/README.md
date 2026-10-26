# Final Taxonomy UX evidence (2026-10-26)

Open [the gallery](gallery.html) and [browser evidence](browser-evidence.json).
The 38 JPEGs are original full-page browser captures, without cropping, resizing
or image edits. `image-dimensions.json` records actual raster sizes and SHA-256.
The normal ready frame proves client/document 1440×844, no horizontal or vertical
document overflow, header search at y=72, workspace y=217–820. Fullscreen frames
measure the shared stage at (0,0), exactly the viewport width and height.
Normal mobile is a vertically scrolling document; fullscreen mobile has one
bounded workspace scroll area and a pannable canvas. Popovers have bounded height.

Browser checks: exact Basil KPI subsets 3/1/2/1, identity detail and return,
source-backed Salvia dependent species, accepted+stored-thumbnail facet history,
unchanged zoomed camera through fullscreen, all six themes at the three requested
sizes, no horizontal overflow, missing source with zero graph/12 accessible local
identities, source restoration and no leftover body scroll lock.

Fallback/denial, native external exit, native exit failure, nested popover Escape,
return focus and unmount cleanup are additionally covered in component tests.
Physical touch, screen-reader certification and final canonical verification remain
independent QA. This phase did not change backend or provider contracts.
