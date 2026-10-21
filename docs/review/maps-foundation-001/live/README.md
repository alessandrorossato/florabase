# Authenticated Native ranges review — 2026-10-19

**Historical first live pass. [Current overview/chooser refinement](../refinement/README.md) supersedes this layout.**

Source: `c606`, branch `feat/maps-foundation-001`, HEAD `9a73d3f`, dirty candidate.
Review: <http://localhost:15174/#/native-ranges>, isolated `florabase-feature-review`.
Owner `owner` was created with the supported interactive bootstrap; password supplied privately
in chat, never stored in this evidence. Fixture v4/80, DB/code `20261013_0042`.
All botanical assertions in this fixture are synthetic examples, not botanical evidence.

These captures use the real authenticated application, backend, collection fixture and bundled
geometry through the in-app Chromium browser. They supersede the earlier offline snapshots for
visual acceptance. Actual viewport sizes are measured from the DOM in [measurements.json](measurements.json).
The screenshot exporter omits/rescales scrollbar space: for example a 1440×844 DOM viewport exports
1425×835 pixels, 1024×844 exports 1009×832, and 390×844 exports 375×812. Do not infer zoom from raster size.
Entries prefixed `final-` describe the final refinement. Earlier measurements retain the investigation.

## Visual evidence

| State | Desktop/tablet | Mobile |
| --- | --- | --- |
| Overview | [1440](overview-1440.jpg), [1024](overview-1024.jpg) | [390](overview-390.jpg) |
| Two-species overlap | [1440](comparison-1440.jpg), [1024](comparison-1024.jpg) | [390](comparison-390.jpg) |
| One species | [1024](single-1024.jpg) | [390](single-390.jpg) |
| Scientific names and selection | Comparison above | [Long-name species list](species-list-390.jpg) |
| Exact evidence | [Full document: broad, precise and unsupported boundaries](overview-exact-evidence-1440.jpg) | [Full document: custom place](single-custom-evidence-390.jpg) |
| Keyboard / textual selection | [Keyboard focus](keyboard-territory-1440.jpg), [textual territory](territory-list-1440.jpg) | Same native controls and pane switch |
| Saved View | [Saved comparison](saved-view-1440.jpg) | Responsive dialog exercised |
| Empty and validation | [Initial unseeded empty collection, 1280×720](empty-1280.jpg) | [No range](no-range-390.jpg), [no search matches](filtered-empty-390.jpg), [invalid URL selection](invalid-selection-390.jpg) |
| Filters | Compact toolbar in overview | [Expanded active filters](filters-390.jpg) |

Full-document captures and the initial empty state are supplementary, not required-height viewport proof.
Exact-evidence, empty/error and saved-dialog captures document behavior during the pass; the overview,
comparison, single-species and species-list viewport images were refreshed after the final layout edits.

## Findings and corrections

- Initial mobile comparison map began at y=735. A redundant visible comparison heading and long
  explanation preceded it. The heading remains available to assistive technology; the explanation
  now follows the evidence. Supporting single-species metadata and links follow the map.
- Filters now sits beside representation when space permits, removing a whole mobile row.
  Narrow layout gaps were reduced locally. No global shell or shared Collection styles changed.
- Final overview map: y=374–797 at 1440×844, y=418–789 at 1024×844, y=603–776 at 390×844.
  Final comparison: y=330–753, y=374–745, y=545–718 respectively. Single species: y=403–775
  at 1024 and y=575–747 at 390. Mobile navigation stays below the useful canvas. Legends and
  inspectors continue in normal document flow; there is no overlay obscuring map interactions.
- No horizontal document overflow at the three required widths or the three reduced-width proxies.
  Long cultivar/custom-place paths wrap. Pane buttons measure 44px high; species label targets are
  129–151px high. Tiny world polygons are not suitable touch targets; the textual buttons are required.
- Legend uses explicit integer counts or binary coverage plus a neutral category. The absence caveat
  and Natural Earth attribution remain visible; further boundary methodology is a disclosure.

## Live interaction and scientific checks

- Overview: six represented identities, four ranged, two without a structured range.
- Aloe + Lavandula: Italy counts two distinct species, Thailand one. Adding historical Raphanus
  increases Thailand to two. Territory inspection never changes the chosen species or URL.
- Brazil counts one for the identity with both South America and Brazil recorded; the exact two
  assertions remain separate. Broad South America is explicitly partial (14/16 boundaries), Southeast
  Asia 10/11. Bouvet Island, South Georgia & South Sandwich Islands, and Singapore are listed as
  unavailable. Lavandula's custom Brazilian place adds no Brazil polygon or geographic precision.
- Polygon click, textual territory click, arrows, Home/End and Enter/Space update the same inspector.
  One SVG tab stop was observed; focus stroke uses the focus-ring token. Clear restores polygon focus.
- Mobile Map & evidence / Species list switches preserve both checked species and Italy inspection,
  retain the URL, and leave focus on the activated switch. Hidden panes disappear from the exposed tree.
- Clear selection shows an explicit choose-species state. Salvia shows no-range guidance with edit/detail
  links. Empty collection, no search matches and invalid URL IDs expose truthful messages.
- Saved View `Maps review — Italy overlap` was created, cleared and reopened. It restores exactly two
  IDs. Real browser Back restores the empty selection and Forward restores both IDs; reload preserves
  that URL state and does not restore transient territory inspection. Saved View remains for the operator.
- Filters/with-range wrapping and reset were exercised. No occurrence provider was loaded. No domain
  range or collection record was edited; only the Review fixture and the named Saved View were created.

## Accessibility and acceptance limits

Actual keyboard behavior, visible focus, semantic names, pressed/checked states, a polite status region,
textual equivalents and dialog/pane focus were inspected. No screen reader was used, so announcement
quality and SVG support in a real screen reader remain operator acceptance items. No physical touch
hardware was used. Essential evidence does not depend on color or hover alone.

The in-app browser exposes viewport resizing but no zoom capability. Ctrl+plus left viewport/DPR
unchanged. **No real 125% or 150% zoom is claimed.** Supplemental proxies are
[1152×675 for 1440/125%](overview-125-proxy.jpg),
[960×563 for 1440/150%](overview-150-proxy.jpg), and
[819×675 for 1024/125%](tablet-125-proxy.jpg). They test reflow only. The shorter proxies require
vertical scrolling to see the entire canvas; the map and evidence remain reachable without horizontal
scrolling. Actual zoom remains an operator check in their browser.

API/asset failure and authentication expiry are covered by focused component regressions, not injected
into the live Review. Live invalid-selection feedback was inspected. Complete service interruption,
real screen-reader output and physical touch acceptance remain unclaimed. Browser error log was empty
at the end of the observed session.
