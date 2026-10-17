> **Superseded first-pass evidence.** The current candidate and operator decisions are documented in the [fourth-pass index](fourth-pass/README.md). First-pass checks and hashes below are historical, not current-source verification.

# Sowings and Plants visual evidence

Live authenticated **Feature Review**, source `ef73`, branch `feat/collection-visual-001`, base/HEAD
`1e3df6adf9afdfd4a213396666b336f6d1b5136c` plus the unstaged source. DB/code revision
`20261013_0042`, synthetic fixture **v4 / ready / 66 records**. No operator collection records were
created or changed during the browser walkthrough. Normal local authentication/session activity occurs.

[Audit](audit.md) · [Handoff](../../../collection-visual-001-handoff.md) ·
[Measured matrix](responsive-matrix.json) · [check summary and source hashes](checks.json)

## Representative captures

| State                          | Sowing                                                                                                    | Plant                                                                                  |
| ------------------------------ | --------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Directory and preview, desktop | [Quick Preview](sowing-preview-desktop.jpg)                                                               | [Quick Preview](plant-preview-desktop.jpg)                                             |
| Directory, mobile              | [Sowings](sowing-directory-390-100.jpg)                                                                   | [Plants](plant-directory-390-100.jpg)                                                  |
| Create, full page              | [Desktop](sowing-create-1440-100.jpg), [mobile](sowing-create-390-100.jpg)                                | [Desktop](plant-create-1440-100.jpg), [mobile](plant-create-390-100.jpg)               |
| Contextual Edit                | [Desktop](sowing-edit-desktop.jpg), [tablet](sowing-edit-1024-100.jpg), [mobile](sowing-edit-390-100.jpg) | [Desktop](plant-edit-1440-100.jpg), [mobile](plant-edit-390-100.jpg)                   |
| Overview                       | [Desktop](sowing-overview-1440-100.jpg), [mobile](sowing-overview-390-100.jpg)                            | [Desktop](plant-overview-1440-100.jpg), [mobile](plant-overview-390-100.jpg)           |
| Explicit relationships         | [Propagation desktop](sowing-propagation-1440-100.jpg), [mobile](sowing-propagation-390-100.jpg)          | [Lineage desktop](plant-lineage-1440-100.jpg), [mobile](plant-lineage-390-100.jpg)     |
| Photos                         | [Empty gallery](sowing-photos-1440-100.jpg)                                                               | [Compact primary media](plant-photos-1440-100.jpg), [mobile](plant-photos-390-100.jpg) |

Additional evidence: [mobile identity picker](plant-picker-mobile.jpg),
[explicit mixed-kind selection](plant-selection-desktop.jpg), and
[accepted SeedLot gallery regression](seed-gallery-regression-desktop.jpg). The gallery's named overflow was opened
on mobile and exposed media details, primary, edit and unlink operations without mutating them.

Contextual creation also has [12 supplemental checks](propagation-matrix.json):
[Plant from Sowing desktop](plant-from-sowing-1440-100.jpg) / [mobile](plant-from-sowing-390-100.jpg),
[Start sowing desktop](sowing-from-seed-1440-100.jpg) / [mobile](sowing-from-seed-390-100.jpg), and the
[genuine source-usage review](seed-usage-review-mobile.jpg). The review was inspected with a local
synthetic draft and cancelled before submission; no collection data changed.

## Responsive scope and limitations

The final matrix contains 72 checks: six states per family, at 1440×844, 1024×844 and 390×844 plus
1152×675, 960×563 and 819×675 **viewport proxies** for the requested larger browser-zoom scenarios.
No final measured control/page has horizontal overflow. Record tabs wrap on mobile; existing mobile
row selection opens canonical Details instead of showing the desktop inspector beside the list.

The tooling exposes viewport resizing and no actual browser zoom control. **No actual 125%/150%
zoom completion is claimed.** Captures are real candidate UI with synthetic application data, not
static test DOM or substituted screenshots. Full-page form/Overview captures include content beyond
the first screen; modal captures show bounded panel scrolling and visible Cancel/Save.

The mobile picker input is 348px wide; its inner popup is 346px with a 5px outer gap (borders included).
Escape closes the popup while retaining the modal. Plant Save bounds remain inside every measured
modal viewport, including the shortest 563px proxy and 390px-wide mobile surface.

## Focused checks

Commands run from `frontend/` with the checked-in Vitest configuration and original timeouts. Existing domain assertions remain; create-form interaction expectations now follow the visible named regions rather than wizard tabs.
The existing exact-lockfile dependencies were reused in ignored node_modules; no manifest changed.

- `node node_modules/vitest/vitest.mjs run --configLoader runner src/seed-lots/SeedLotScreen.test.tsx --maxWorkers=1`: **48 passed**.
- Same command with PhotosSection, MediaScreen, FormSections, ReferencePicker, PartialDateField and BulkLocation test files: **64 passed / 6 files**.
- SowingScreen **26 passed**, final isolated PlantScreen **50 passed**: **76 cases / 2 files**, including group aliases, changed-revision Save focus/tab retention, conditional required markers and cross-record draft initialization.
- Journal, History, Schedule and Settings: **75 passed / 4 files**. The five-file attempt also ran Labels, with one unchanged Labels timeout and 53 passes; the isolated full Labels repeat **54 passed**, with no test or timeout edits.
- Guided propagation and guarded creation reversal: **14 passed / 2 files**. Atomic source-usage and resulting-lifecycle assertions remain intact.
- **331 distinct focused tests across 16 files passed** across those bounded runs. This is not a whole-frontend or canonical-gate claim.
- Strict TypeScript, targeted ESLint (zero warnings), targeted Prettier, production frontend build, the **105-feature** graph and complete whitespace checks pass. Production build runs `tsc -b && vite build`; no API/backend/migration changes are present.

The initial baseline passed **61** Sowing/Plant tests. New focused coverage adds contextual/direct
edit, focus containment/return, all dismissal routes, retained detail tabs and cross-record direct-edit
initialization. A longer combined regression attempt was terminated before completion and is not
counted as passing; bounded replacements supply the results above. A later combined family run
completed Sowing but hit five Plant timeouts under load; the unchanged isolated full Plant repeat
passed all 50. No test timeout or validation was changed. Earlier browser timeouts and the
interruption's stopped application containers were recovered through supported browser/Review APIs.

The unchanged domain payload builders and both client validators were independently compared with main; the germination denominator function is also unchanged. Final Review identity/health/revision/fixture output is saved in [review-status.txt](review-status.txt).

No backend, PostgreSQL, API regeneration/drift or migration tests are needed for this frontend-only
contract-preserving diff. No canonical `make feature-verify` or delivery receipt is run/claimed.
