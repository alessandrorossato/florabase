# Themes, Controls and delivered Collection origins integration

The integration merges `46ade479fb3955b1d020a321c8256211cd2af869` (main, MAPS-ORIGINS-001,
PR #119) into `feat/themes-001` after reviewed implementation
`564f479ef2c6dc657fc213d2f9636ddac9ccd590`. Original candidate base:
`b3f1de4693f50a12396344d251a16a0b4ded4b92`.

## Conflict resolutions and corrections

- `ProvenanceMap.tsx`: use the delivered layers/marker implementation, which already uses
  `var(--primary)` for precise noninteractive accuracy circles. Preserve local geometry loading,
  explicit online consent, origin-only Referer, failure latch, camera preservation and responsive
  resize behavior. No renderer changes relative to main are needed.
- `ProvenanceMapScreen.tsx`: remove the obsolete inline SiteDetails implementation and its duplicate
  imports. Keep main's complete workspace, inspector, counts, filter and Saved View synchronization.
  Transfer the shared labelled edit action into `OriginInspector`, where the delivered Manage
  provenance site link now lives; its exact destination and label remain unchanged.
- `ProvenanceMap.test.tsx`: retain every delivered main test and its richer Leaflet fixture. Adapt the
  former theme regression to the new renderer: all six theme combinations must preserve selected
  marker, camera, accuracy, map instance and local/explicit-online consent without new provider work.
  The old expectation that opening the map automatically creates an online layer is intentionally
  replaced by zero online layers until explicit consent.
- `docs/features.json`: preserve every authoritative main entry exactly, including verified Origins
  dependencies/status, then retain Themes and Controls as implemented. Graph: 111 valid.
- Leaflet marker tooltip CSS now consumes semantic text/surface/border/elevation tokens including its
  arrow. This corrects the native white tooltip surface in dark themes without recoloring map imagery.
- Settings' direct-QR focus regression exposed a race between DOM availability and its focus effect.
  Wait for actual focus with the existing timeout; preserve the focus assertion and production behavior.

## Actual browser checks

The existing authenticated split runtime was reused without lifecycle changes. The live candidate
frontend source bind serves the merged app; retained Review backend, database, media and credentials
remain unchanged. No DEV/UAT/foreign source modifications or data reset/reseed occurred.

Keyboard Space selected synthetic origin 02 and opened the delivered inspector showing exact
coordinates, unknown recorded accuracy, identity grouping and links. Six theme changes through the
actual Settings page in another tab preserved that selected marker, all 12 markers, the identical
camera transform and zero online tile elements. JSON records actual layout sizes and computed marker
Tooltip colors; screenshots are browser exports, not zoom proxies or accessibility certification.

Filters opens the shared drawer with labelled category controls. Escape dismisses the focused Close
Tooltip first, then the drawer, returning focus to Filters. Saved Views opens its labelled native dialog.
At 390×844, Inspector switching retains the mounted 12-marker map and selected site with no measured
horizontal viewport overflow. Tablet inspector is captured separately at 1024×844. External online
consent remains disabled by deployment configuration; online success/failure behavior is covered by
renderer tests, not a live provider request.

## Scope and remaining acceptance

No changes to the primary checkout, other worktrees, backend contracts, database schema, provider
requests, record semantics, theme preference model, IA-NAV-001 or approved palette values.
The ownership mismatch remains: this is current candidate Quality frontend plus retained c902
Review backend/media, not a supported whole-environment ownership transfer or production smoke.

Independent QA, canonical FULL verification and protected delivery remain pending. Real AT, physical
touch, OS forced colors, actual browser zoom, downloaded GBIF raster, throttled first-paint filmstrip
and physical printing/QR acceptance retain their previously documented limits. The existing 143
Themes PNGs and prior Controls evidence remain historical artifacts. No previous full verification
receipt is reused for the integrated tree.

## Validation completed

- Affected first run: 132/133; sole failure was the asynchronous Settings focus assertion described
  above. Isolated Settings retry passed; the complete suite subsequently includes the corrected test.
- Complete frontend suite: **872/872 passed, 75 files, zero failures/skips**, actual exit 0. Includes
  **19 Provenance Map cases** (8 renderer, 11 workspace), all 82 App cases and Themes, Settings,
  Controls, navigation and Saved Views regressions. Two new renderer cases cover six variants with
  local-only and explicitly enabled online layers. No delivered map tests were removed.
- TypeScript passed; full ESLint passed with zero warnings after two callback block-body style fixes;
  `pnpm format:check` and `pnpm build` passed. All invoked check exit statuses were collected. Raw logs
  remain under ignored `frontend/coverage/themes-origins-*`; portable totals are in `test-results.json`.
- `python3 scripts/check-features.py`: 111 valid. Conflict marker scan, unmerged index scan and
  `git diff --check` / staged whitespace check passed.
- Six actual browser variants, keyboard marker selection, drawer/Tooltip Escape layers, Saved Views,
  selected inspector navigation and phone/tablet mounted-pane behavior were checked as described above.

## Independent QA — 23 October 2026

- Reconfirmed `HEAD` is merge commit `1a712ca7d01ee7705433f98622ae625cd228be82`, with original
  combined implementation `564f479ef2c6dc657fc213d2f9636ddac9ccd590` and delivered
  `origin/main` `46ade479fb3955b1d020a321c8256211cd2af869` as its parents. The fetched `origin/main`
  remains at that SHA and is an ancestor of the candidate.
- Independently reviewed the map conflict resolutions, theme/action implementations, test changes,
  and feature graph. `ProvenanceMap.tsx` and `ProvenanceMapScreen.tsx` have no candidate-side edits
  beyond main's delivered implementation. The retained graph entries keep authoritative main statuses
  and dependencies; Themes and Controls are still `implemented`.
- The live browser frontend at `127.0.0.1:15174` is container
  `florabase-themes-review-frontend`, from candidate Quality project
  `florabase-quality-ab1b459cfd98`, source bind `/home/alessandro/.codex/worktrees/b64e/florabase`.
  The Feature Review backend and persistent DB/media belong to
  `/home/alessandro/.codex/worktrees/c902/florabase` at launch SHA `b3f1de4693f50a12396344d251a16a0b4ded4b92`;
  its Review frontend is exited. The supported Review status command refuses cross-owner use. No
  Review lifecycle or data changes were made. Consequently, current live browser observations are
  frontend/accessibility-tree checks only; they are not independent full-stack or fixture-data proof.
- The live Settings tree exposes labelled native Botanical/Herbarium/Mineral and System/Light/Dark
  radios. Keyboard selection of System kept the effective OS-dark scheme and changed the footer
  announcement to `Appearance: System (Dark), Mineral. Switch to Light.` Selecting Dark restored the
  original Mineral/Dark preference. The Origins accessible tree exposes named Filters, Saved views,
  inspector and Manage provenance site actions. Pointer clicks timed out in this browser session;
  keyboard checks and the automated interaction suites remain the evidence for those controls.
- Six-theme token coverage and approved contrast pairs are directly tested in
  `frontend/src/appearance/styles.test.ts`; System/storage behavior in `appearance/theme.test.ts`;
  Tooltip focus, Escape and hover transfer in `components/Controls.test.tsx`; map theme preservation
  in `provenance-map/ProvenanceMap.test.tsx`; print/raster invariants in `appearance/styles.test.ts`
  and the Labels tests. These are implementation tests, not physical-device acceptance.
- No reproducible integration defect was found, so no production correction or additional regression
  test was needed during independent review. The full frontend suite and static checks recorded above
  are the completed integrated-tree results; the canonical FULL gate and exact-tree receipt are still
  pending at this point.

Actual screen-reader/AT use, physical touch, OS forced-colors/reduced-motion emulation, 125%/150%
browser zoom, downloaded GBIF raster appearance, throttled cold first paint, native print dialog,
QR output and physical printer output remain unverified. Screenshots, accessible-tree snapshots and
calculated token contrast do not certify those checks.

These checks support integration review. No canonical `make verify-full` or delivery receipt was run
or claimed; independent QA must gate the accepted final candidate before protected delivery.
