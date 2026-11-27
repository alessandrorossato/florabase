# RELEASE-VISUAL-AUDIT-001 — operator review package

**Start with the [navigable screenshot gallery](http://localhost:15282/gallery.html) and
[eight before/after proposals](http://localhost:15282/before-after/index.html).**
This is an audit/design candidate on `docs/release-visual-audit-001`; no production UI change.
Baseline is fetched delivered main `ee3487412fe458cbdf7145154c54a58b66132cae` (#126), 26 October 2026.

## Decision summary

The existing UI Foundation is sufficient. Consolidate its current primitives instead of building
another framework. Two concrete **P1** corrections should precede broad visual polish:

1. **F09 — tablet shared header:** at 1024×844, legacy column direction turns16rem/38rem flex bases
   into vertical height. Measured Media/Seeds header is 880 px; Media gallery starts at 1102.8 px,
   Seeds inventory at 1031 px. Correct the shared axis/basis collision once.
2. **F01 — destructive initial focus:** Media's permanent-delete confirmation initially focuses
   Delete. Give dangerous confirmations an explicit safe Cancel target; keep caller safety rules.

The remaining findings cover mobile reading space, header alignment, redundant detail surfaces,
interactive-surface composition, consistent recovery and optional cosmetics. Media density/preview
belongs to the independent Media design; Taxonomy's delivered graph model remains intact.
No P0 was established in the observed scope. Uncaptured states are not implicitly passing.

## Review contents

| Artifact                                                           | Purpose                                                                                                                                                             |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [gallery.html](gallery.html)                                       | 270 selected real browser captures, filters by macro-area/page/archetype/viewport/palette/mode/state, original images/DOM and selectable side-by-side comparison    |
| [coverage.md](coverage.md)                                         | 27 source-discovered primary states × 1440/1024/390×844 × Botanical Light/Dark =162 current primary captures; contextual and theme samples; explicit missing states |
| [route-inventory.json](route-inventory.json)                       | Canonical routes plus direct/detail/edit/task/subview contracts, including PlantGroups/Stored material and moved Geography routes                                   |
| [findings.md](findings.md)                                         | Nine consolidated P1–P3 findings, actual evidence, ownership, complexity and risks                                                                                  |
| [component-inventory.md](component-inventory.md)                   | Existing shared owners, APIs/slots, tokens, variants, mobile/accessibility rules, consumers and migration boundaries                                                |
| [component-consumers.json](component-consumers.json)               | Source-derived non-test TSX references for 25 shared primitives                                                                                                     |
| [design-system-proposal.md](design-system-proposal.md)             | Directory/Detail/Activity/Map/Tree/Calendar/Utility grammar, surfaces and proposed safe-focus extension                                                             |
| [before-after/index.html](before-after/index.html)                 | Eight targeted proposals; real current screenshots beside clearly labelled static compositions; no simulated implemented result                                     |
| [implementation-plan.md](implementation-plan.md)                   | Prioritized B0/A0 and incremental A–E waves, files/consumers, verification and review dependencies                                                                  |
| [integration-boundaries.md](integration-boundaries.md)             | Delivered vs pending work, explicit Media coordination, exact Review ownership/fixture setup and retention                                                          |
| [capture-index.json](capture-index.json)                           | Per-capture route, source SHA, fixture/environment, time, CSS viewport, JPEG raster dimensions, theme/state, digest and limitations                                 |
| [interaction-evidence.json](interaction-evidence.json)             | Observed destructive focus, Cancel return, drawer Escape return, failed actual-zoom attempt and desktop header measurements                                         |
| [tablet-header-measurements.json](tablet-header-measurements.json) | Reproduced shared-header geometry and computed flex rules                                                                                                           |

## Clear approval choices

- **Recommended:** accept the consolidation direction and authorize two narrowly scoped implementation
  increments for F01 safe destructive focus and F09 tablet header sizing; review the other proposals
  as a ranked backlog, with Media independently accepted.
- Accept F01/F09 only and retain current visual composition pending the missing source/print/zoom checks.
- Request changes to named proposal examples before authorizing any implementation.

These choices do not authorize a broad refactor, IA change, delivery or this phase's canonical FULL gate.
Shared UI infrastructure still requires conservative FULL escalation in the later implementation phase.

## Exact evidence limits

- WFO absent: current Taxonomy List/Tree images are legitimate local-identity fallback. Placed graph,
  graph fullscreen and source-backed KPI interaction need a separately recorded integration capture.
- Labels QR base URL is unset. Batch/physical preview shows “QR not configured” and Print disabled.
  No server setting was changed for screenshots. Native print, QR decode and paper output remain open.
- Ctrl+Plus changed neither layout nor DPR/visual scale. Actual 125%/150% browser zoom is unverified.
  Screen reader, physical touch/keyboard, forced colors, reduced motion and 320px acceptance remain manual.
- The browser screenshot API emits scaled content JPEGs: measured CSS viewport and raster dimensions
  are both recorded. There is no manufactured pixel-perfect viewport or browser-zoom claim.
- The coverage matrix lists all missing contextual states. Risk-based samples are not a full
  state×viewport×theme Cartesian certification. The17-asset fixture does not provide a second Media
  page; Media's independent 35-asset fixture is a separate evidence source.
- Session-expired acquisitions from localhost cookie collision, initial image-incomplete captures
  and incorrect PlantGroups hash-transition states are excluded from current primary evidence.
  Corrected PlantGroups direct-entry captures verify the actual Groups filter at all six combinations.
- No page-level horizontal overflow was measured; internal regions/focus/soft keyboard still need
  the stated manual acceptance. Static proposals show structure and use the house token/font stack;
  local font fallback can differ and controls have no production handlers.

## Runtime and retention

Authenticated synthetic Review: **http://localhost:15279**, project `florabase-ui-audit-bc88`.
V4/80 baseline plus Extended Botanical Review Dataset v5 ready/252 references; 37 identities,
43 SeedLots,19 Plants / 7 groups,17 media. The dedicated synthetic credential was shared only in the
operator-authorized Media coordination; existing owner data/credentials were not reused or changed.
See the ownership document for all counts, source checks and the exact local harness.

Static read-only gallery: **http://localhost:15282**. The local server script is
`/tmp/florabase-ui-audit-bc88/gallery_server.py`; it serves this document folder, maps `/evidence/`
to the external screenshot directory, and permits only the single token CSS file under `/source/`.
It is bound to loopback, not public hosting. If the server stops, run that existing script locally;
it performs no application writes. The normal app itself is unchanged.

External images/DOM/raw logs live at:
`/home/alessandro/.codex/visualizations/2026/10/26/01a178c9-0d81-73f2-96a2-42047619aba9/release-visual-audit-001/`.
Keep this directory with the package to retain images; the compact Git candidate deliberately does
not embed the270-image collection. Copying/rehosting this package needs the same evidence mapping or
an explicitly updated local base URL. Review resources remain available; no reset/removal scheduled.

## Phase boundary

No production CSS/components, API/schema/domain workflows or application records were changed after
initializing the new isolated synthetic fixture. No existing Review/UAT/DEV/Preview/production takeover,
foreign worktree change, staging, commit, push, PR or merge. No canonical FULL gate was run.
The audit feature is an implemented document/evidence candidate awaiting operator acceptance;
`verified` is not claimed. Current validation evidence is recorded in `validation.json` and progress.

`FLORABASE_GLOBAL_UI_AUDIT_READY_FOR_REVIEW`
