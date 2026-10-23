# THEMES-001 implementation handoff

Candidate: `feat/themes-001` in `/home/alessandro/.codex/worktrees/b64e/florabase`, based on
`b3f1de4` (delivered main inspected during this phase). Status: implementation candidate awaiting
independent visual/accessibility review. No staging, commit, push, delivery or canonical gate.

## Combined integration update — 23 October 2026

CONTROLS-001 is now implemented on this same candidate under the operator's explicit combined-branch,
combined-review and later single protected PR approval. The [Controls handoff](controls-001-handoff.md)
is the current evidence record for shared icons, actions, Tooltip and combined checks. Original THEMES
artifacts remain preserved. The historical 850-test result below describes the THEMES-only tree; it
must not be treated as Controls coverage. Current combined evidence includes a complete 859-test run
and post-refinement targeted regressions. Both features remain `implemented`, not `verified`.

## Implemented architecture

`frontend/src/styles/tokens.css` owns all six approved semantic color sets. Root selectors combine
`data-palette` and resolved `data-appearance`; existing aliases point to the semantic roles. Geometry,
typography, routes, information density and scientific-name treatment remain shared. Capability CSS
now consumes semantic roles for surfaces, text, interactive boundaries, states and overlays. Theme
changes do not replace component trees or stylesheets. No global image inversion is used.

| Palette | Light | Dark |
| --- | --- | --- |
| Botanical | Approved existing botanical baseline | Botanical dark surfaces and green accents |
| Herbarium | Approved warm paper and olive accents | Warm dark surfaces and pale olive accents |
| Mineral | Approved cool surfaces and blue accents | Cool dark surfaces and pale blue accents |

Values match `docs/design/themes-controls/palette-proposal.json`; no palette was redesigned. The
existing spacing/type/radius/control-height tokens remain unchanged. Disabled controls retain readable
text/boundaries rather than whole-control opacity. Native form controls follow `color-scheme`.

## Preferences, first paint and controls

`frontend/public/appearance.js` is a blocking, same-origin classic script before application assets.
It validates browser-local `florabase.appearance.v1` JSON with `version`, `palette` and `appearance`.
Defaults are Botanical/System. Invalid fields independently fall back; corrupt/unknown-version data
falls back to defaults. Storage denial/quota failure keeps a working temporary session preference
and Settings explains the limitation. Cosmetic preferences do not touch API, account or database.

The bootstrap applies root attributes and native color scheme before React, and owns the only store.
`useSyncExternalStore` exposes stable snapshots to React. System reads `prefers-color-scheme` and
subscribes to live changes only while selected; explicit modes ignore OS changes. Storage events
update other tabs without echo writes; removal/clear restores defaults and sessionStorage is ignored.
Authentication changes do not reset appearance. Reload reads the same validated preference.
Live browser footer cycling and a Dark reload are recorded in
`review/themes-001/interaction-evidence.json`.
Production serves the bootstrap with revalidation (`Cache-Control: no-cache`); the production build
retains its ordering and public asset. CSS supplies Botanical/System fallback if bootstrap cannot run.
A filmstrip measurement of a throttled cold first paint has not been performed.

The existing footer button now cycles **System → Light → Dark → System**, preserving palette and
persisting each change. Both desktop/mobile controls synchronize with Settings. Monitor/sun/moon
and accessible name describe the current preference, effective System mode and next action.
CONTROLS adds the shared accessible Tooltip instead of native title, retaining the same functional
cycler and preference store. A clean horizontal-sliders glyph replaces the Settings gear under the
operator's explicit request; Settings remains a labelled native navigation link.

Settings → Appearance provides labelled native radio groups for Botanical/Herbarium/Mineral and
System/Light/Dark, compact real-token previews, visible selection text and immediate application.
Keyboard focus stays on the actual radio/button. Browser-local status is independent of General QR
configuration loading, failure and saving. No additional Save/confirmation or navigation destination.

## Maps, media and print

- Native ranges: approved count ramp and five comparison identities use centralized slots. Comparison
  identity stays stable across palettes; appearance changes only approved luminance values. Existing
  overlap stripes, legends, selection and keyboard behavior remain. A neutral casing separates selected
  outlines from colored fills without changing selected territories or evidence semantics.
- Species distribution: provider density colors, raster pixels, URLs and generation behavior remain
  unchanged. UI chrome/inspector use semantic roles. Theme regression tests retain map/evidence/layers
  and assert no new fetch. Review screenshots show a selected identity without downloaded raster;
  the fixture's synthetic GBIF identifier was not used for a provider request. Real downloaded raster
  visual acceptance remains outstanding.
- Collection origins: Leaflet controls, attribution and popup use semantic colors; markers retain dual
  neutral halos and accuracy circles consume the primary role without a map remount. Six theme captures
  retained the same 54 tile-image URLs. This is DOM evidence, not a network trace; renderer tests cover
  layer/camera/selection stability and no theme-triggered fetch.
- MAPS-ORIGINS-001 had not merged into inspected main. This candidate therefore uses the delivered
  renderer; local fallback geography and optional online-basemap behavior belong to that separate
  candidate and need theme integration review after its delivery. No foreign frontend was copied.
- Original botanical images, thumbnails, external-media consent and local media behavior are preserved.
- Print overrides screen palette with white surfaces/black text and explicitly overrides the inline
  native color scheme. Existing Labels mm geometry and black/white QR SVG remain unchanged. A Dark
  screen label preview shows white paper. Review has no QR destination configured, so Print remains
  honestly disabled; no shared setting was changed merely to obtain a screenshot. Physical printer,
  system print dialog and real QR output acceptance remain outstanding.

## Accessibility and responsive evidence

[Review gallery](review/themes-001/gallery.html), [evidence notes](review/themes-001/README.md),
[approved contrast calculations](design/themes-controls/contrast-evidence.md).

126 actual browser viewport captures cover representative surfaces across all six variants. Settings,
Dashboard, directory/Quick Preview, edit modal and five-species native comparison cover 1440×844,
1024×844 and 390×844. Detail dashboard, create form, filter drawer and all three map workspaces have
six desktop variants. Another 16 Botanical Dark captures cover Sowings, Plants/PlantGroups,
Harvests/Stored material, Locations, Journal, History, Schedule, identities, taxonomy, Geography,
Suppliers, Orders, Media and Labels. Additional label-preview evidence is separate from those totals.

Measured root attributes and 20 computed roles per six-theme capture match the approved matrix
(2,520 values); captured roots have no horizontal viewport overflow. This does not assert that every
internal scroller or every descendant color was measured. Cross-tab changes drove the same-content
six-theme captures. Preliminary iframe proxies were removed; captures use real browser viewport
sizes. Gallery includes full-resolution originals for independent review.

Automated contrast tests calculate actual implemented token pairs: shared normal/muted/status text
≥4.5:1, interactive boundary/focus cues ≥3:1, primary/hover button labels ≥4.5:1 and danger/warning
subtle pairs ≥4.5:1 across all six sets. Selection/status retain existing textual/structural cues.
Forced-colors system roles and selected/focus outlines are supplied. Existing reduced-motion rules
apply; appearance switching introduces no animation. Native radios/footer keyboard behavior is tested.

Real browser zoom was unavailable through the provided controls. No physical touch device, screen
reader or OS forced-colors/reduced-motion emulation was certified. Independent visual/accessibility
acceptance remains required; screenshots and calculated pairs are implementation evidence.

## Review runtime and ownership

Review URL: `http://localhost:15174/#/settings` with populated retained fixture/media data and the
existing authenticated session. The operator explicitly authorized handover preserving database/media.
The repository helper cannot transfer source-labelled volumes without deleting them. Consequently
this review uses a documented split runtime rather than claiming a full helper ownership transfer:

- Current candidate frontend: this worktree's isolated Quality Compose runner,
  `florabase-themes-review-frontend`, loopback `15174`, own dependency volume/source bind.
- Existing Feature Review backend/database/media retain the `c902` owner and existing volumes.
  Its production backend matches this candidate's base; its separate frontend/workflow edits are not used.
- `make feature-review-status` continues to report source mismatch for `b64e`. This is an operational
  limitation, not a successful supported ownership transfer. The Quality helper launches the candidate
  frontend and its proxy connects to the retained backend on the existing Review network.
- Database/media were not reset, removed, copied or reseeded. DEV, UAT, Stable Preview and production
  were not changed. Unknown/foreign resources were retained.

If the review runner is no longer present, inspect ownership with `make workflow-resources` and
`make feature-review-status` before restoring this same authorized split runtime. Do not delete volumes
to make ownership labels match. Persistent runtime takeover support remains an infrastructure concern.

## Validation

- Baseline before implementation: 11 tests in three focused files passed.
- Focused implementation checks: 45/45 tests in eight files passed.
- First complete frontend run: 838/850 tests passed across 74 files; all 82 App tests passed.
  UX004 had one lazy-workspace timeout and eleven subsequent failures because its partial
  `matchMedia` mock leaked into the next test bootstrap. The shared setup now recreates a complete
  browser API stub before each bootstrap. No assertions or timeout values changed.
- Targeted retry after the isolation repair: 27/27 tests in UX004 and both theme contract files passed.
- Final complete frontend rerun: **850/850 tests passed in 74 files**, zero failures/skips.
  Summary: `review/themes-001/test-results.json`. Full reports from the initial run, targeted retry
  and final run are retained under ignored `frontend/coverage/themes-001-results/`.
- Final static/build checks passed on the corrected source: `pnpm typecheck`, `pnpm lint`
  (zero warnings), `pnpm format:check`, and `pnpm build` (214 modules; Vite production bundle).
  The built `appearance.js` exists and precedes the module bundle in the built index. This is a
  frontend production build, not a production deployment or container health certification.
- Approved palette calculator: 72 contrast cases, zero failures. Actual implemented token contrast
  assertions are included in the passing targeted retry. Feature graph: 110 features valid.
- `git diff --check` passes; index remains empty. No backend/API/schema/migration change justifies
  backend tests here. Canonical `make feature-verify`/`make verify-full` were explicitly forbidden
  and were not run. No verification receipt or `verified` feature status is claimed.

The host had concurrent worktree test activity, less than 1 GiB available RAM and full swap during
parts of the run. Test timeouts/assertions remain unchanged. Independent QA must use its own final
source-tree gate after visual acceptance and explicit authorization.

## Scope and next steps

The two features retain distinct implementation responsibilities. The operator now requests one
combined branch, one combined visual review and one later protected PR; this overrides the original
independent-delivery sequence. CONTROLS follows the completed semantic theme foundation and is now
included before remaining-page visual normalization. Approved palettes were not reopened.

Remaining operator work is independent combined visual/accessibility acceptance and authorization of
later canonical QA/delivery. The split runtime can support current frontend product review against the
matching retained backend; it does not establish supported full Review ownership transfer or a
production-runtime smoke. See the Controls handoff for current runtime state and its acceptance limits.
Later Origins integration, real provider raster, actual browser zoom/assistive technology and physical
print checks remain explicit. All source and design/review artifacts stay unstaged and uncommitted.

`READY_FOR_THEMES_CONTROLS_VISUAL_REVIEW`
