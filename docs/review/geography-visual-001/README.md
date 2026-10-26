# Geography visual review evidence

**Current candidate:** [Operator corrections](operator-corrections/README.md).
[Final UX evidence](final-ux/README.md) is preserved as the superseded layout.
[Unified-navigation evidence](refinement/README.md) is also preserved.
The captures and checks below are preserved initial-phase evidence; their grouped navigation and
sidebar descriptions are superseded by the current handoff and refinement gallery.

Candidate source: `/home/alessandro/.codex/worktrees/5430/florabase`.
Review: <http://localhost:15276/#/geography/overview>. Login `geography-review`;
password is in `/tmp/geography-5430-owner-password` (mode 0600), outside repository evidence.
See [the handoff](../../geography-visual-001-handoff.md) for ownership, scope and limitations.

All ordinary captures show authenticated, API-created **synthetic** review data in the separately
owned Geography database. The synthetic native-range link is a UI fixture, not a botanical claim.
There are no invented external taxon IDs, occurrence downloads or external photos.

## Device and appearance matrix

PNG dimensions match 1440×844, 1024×844 and 390×844. Additional scrolled views show mobile previews
and the lower overview destination without claiming a taller viewport. The shell and existing bottom
navigation remain visible. These captures are browser emulation, not browser zoom or physical devices.

| Appearance | Desktop overview | Tablet overview | Mobile overview | Tablet sites | Mobile selected preview |
| --- | --- | --- | --- | --- | --- |
| Botanical Light | [1440](overview-1440-botanical-light.png) | [1024](overview-1024-botanical-light.png) | [390](overview-390-botanical-light.png) | [Sites](sites-1024-botanical-light.png) | [Places](places-preview-390-botanical-light.png) |
| Botanical Dark | [1440](overview-1440-botanical-dark.png) | [1024](overview-1024-botanical-dark.png) | [390](overview-390-botanical-dark.png) | [Sites](sites-1024-botanical-dark.png) | [Sites](sites-preview-390-botanical-dark.png) |
| Herbarium Light | [1440](overview-1440-herbarium-light.png) | [1024](overview-1024-herbarium-light.png) | [390](overview-390-herbarium-light.png) | [Sites](sites-1024-herbarium-light.png) | [Places](places-preview-390-herbarium-light.png) |
| Mineral Dark | [1440](overview-1440-mineral-dark.png) | [1024](overview-1024-mineral-dark.png) | [390](overview-390-mineral-dark.png) | [Sites](sites-1024-mineral-dark.png) | [Sites](sites-preview-390-mineral-dark.png) |

Each matrix combination also has `places-*` and `sites-*` captures, mobile `*-preview-390-*`,
and tablet/mobile `overview-origins-*` lower-destination captures. The JSON manifest enumerates them.

| Existing destination, Botanical Light | Desktop | Tablet | Mobile |
| --- | --- | --- | --- |
| Exact selected native range | [1440](native-1440-botanical-light.png) | [1024](native-1024-botanical-light.png) | [390](native-390-botanical-light.png) |
| Exact identity, external taxon not linked | [1440](distribution-1440-botanical-light.png) | [1024](distribution-1024-botanical-light.png) | [390](distribution-390-botanical-light.png) |
| Collection origins | [1440](origins-1440-botanical-light.png) | [1024](origins-1024-botanical-light.png) | [390](origins-390-botanical-light.png) |
| Retained Site map | [1440](siteMap-1440-botanical-light.png) | [1024](siteMap-1024-botanical-light.png) | [390](siteMap-390-botanical-light.png) |
| Site details/source links | [1440](siteDetail-1440-botanical-light.png) | [1024](siteDetail-1024-botanical-light.png) | [390](siteDetail-390-botanical-light.png) |

[Browser matrix](browser-matrix.json) records viewport and document/contained horizontal-overflow
checks for each capture. The final captures supersede intermediate full-page/diagnostic images.
No horizontal overflow, browser page errors or attempted third-party requests were observed in the
completed matrix. No GBIF refresh or online basemap opt-in was invoked.

## Interactions and explicitly labelled doubles

[Interaction report](browser-interactions.json) records these authenticated browser checks:

- Places expand/collapse, Enter selection, separate focus outline and canonical edit restriction.
- New-place dialog Escape and focus return without saving.
- Exact place-to-site filtering, stored decimal coordinates, source SeedLot link, record navigation
  and Back to the exact site.
- Management Back/Forward, search restoration and preservation of an unrelated query parameter.
- Coordinate-less site/unknown accuracy, existing edit dialog and real persisted Geography v1 Saved
  View creation/restoration. The retained view is synthetic review state in this database only.
- Overview's exact native-range identity opens `mode=species` with one selected identity.

[Keyboard selection](keyboard-selection-1440.png) is real fixture UI. The following captures are
**browser-only response doubles**, not persisted collection facts or backend performance evidence:

- [1000-site searchable renderer](large-data-renderer-double-1440.png): 1000 in-memory site rows,
  search reduces to one exact name; document horizontal width remains within the viewport.
- [Empty overview](overview-empty-double-1440.png): all evidence sources return empty local results.
- [Partial summary error](overview-partial-error-double-1440.png): native overview returns 503 while
  other summaries and all destination actions remain usable. Retry/session expiry are also unit tested.

The interaction run records no page errors or attempted external requests. It does not test live
provider outages, runtime cache downloads, true zoom, an actual screen reader or physical touch.
The 1000-site case is a bounded renderer smoke, not a benchmark of real collection API performance.

## Verification

- Final affected frontend run: **148 passed in 7 files**, no failures or skips. See
  [portable test totals](test-results.json). This covers App routing/Geography, overview/source
  summaries, site management, all three map screens and Saved Views.
- Baseline before implementation: **47 passed in 4 files** (site management and the three map screens).
- Strict `pnpm typecheck`, full zero-warning `pnpm lint`, full `pnpm format:check` and `pnpm build`
  passed. No dependency or generated API files changed.
- `python3 scripts/check-features.py`: **112 features valid**. `git diff --check` passed; the index
  remains empty. Backend/API/schema and shared tokens/navigation were not changed.
- **67** final device/theme captures and **9** completed browser interaction groups passed their
  assertions. All matrix PNG dimensions were independently checked against their JSON entries.
  Browser reports contain zero page errors, attempted third-party requests or horizontal overflow.
- An earlier combined run had one summary-retry test timeout under host memory/swap pressure.
  The unchanged final seven-file run passed all 148 cases; assertions and timeouts were not weakened.
  Intermediate locator errors and the tablet header/navigation defects are superseded by the final
  successful reports and captures.

Backend/integration/API regeneration and the canonical FULL gate were not run: this is a frontend
implementation/review phase with unchanged domain/API/schema. Receipt, staging, commit, push and
delivery are intentionally excluded before operator acceptance. Actual browser zoom, screen-reader,
physical-device and live-provider checks remain acceptance limits.
