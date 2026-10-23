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

These checks support integration review. No canonical `make verify-full` or delivery receipt was run
or claimed; independent QA must gate the accepted final candidate before protected delivery.
