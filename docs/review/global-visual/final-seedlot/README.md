# Final SeedLot-family visual refinement

Candidate: `/home/alessandro/.codex/worktrees/996d/florabase`, branch `feat/global-visual-001`,
base HEAD `cd63c185f7bcb0544cd9c3cff984b29564e6bc84` **plus the current dirty/uncommitted source**.
Review serves the live source bind at [localhost:15174](http://localhost:15174).
Sign in normally with the existing `owner` account and its unchanged Review password.

## Saved responsive evidence

`responsive-probes.json` records **57 real observations**, all without horizontal document overflow.
Screenshots carry the same state/case names. The CSS viewport in each probe matches its stated case.

| Cases          | CSS viewport | Meaning                                       |
| -------------- | ------------ | --------------------------------------------- |
| 1440-100       | 1440 x 844   | desktop                                       |
| 1440-125-proxy | 1152 x 675   | reduced viewport proxy; not real browser zoom |
| 1440-150-proxy | 960 x 563    | reduced viewport proxy; not real browser zoom |
| 1024-100       | 1024 x 844   | tablet / smaller desktop                      |
| 1024-125-proxy | 819 x 675    | reduced viewport proxy; not real browser zoom |
| 390-100        | 390 x 844    | mobile                                        |

- `create-top-*`, `create-actions-*`: all six cases, one ordered visible form, full-width desktop
  workspace, single-column mobile, final Cancel / Add seed lot clear of mobile navigation.
- `edit-acquisition-{unknown,year,month,day}-*`: all six cases. Stable precision column and fixed parts
  slots; no horizontal jump. Known date parts require 55px of internal panel scrolling at normal
  desktop, with footer actions retained outside it. Unknown and linked states fit without panel scroll.
- `edit-acquisition-linked-*`: all six cases. Read-only transaction context and retained lot facts.
- `overview-*`, `lineage-empty-*`: 1440 / 1024 / 390. Compact current-state dashboard, natural-height
  context and aligned small empty Lineage.
- `edit-first-tab-focus-*`, `edit-last-tab-focus-*`: normal desktop tab focus boundaries.
- `sowings-*`: one canonical entity Start sowing, existing linked sowing facts and navigation.
- `photos-protected-*`: accepted gallery using existing protected synthetic media; no new fixture.
- `external-default-*`, `external-reference-choice-*`: checked new-copy default and explicit opt-out.
  The dialog was cancelled without creating media or contacting any external host.
- `seeds-quantity-*`: stronger remaining quantity, approximation and unknown states without ratios.
- `shared-order-create-*`, `shared-order-month-*`: representative shared PartialDate layout.

`additional-probes.json` and `shared-order-day.png` capture the resumed Order Day layout. The fieldset
is block flow, with all required components beneath precision and no horizontal overflow. Its native
discard confirmation subsequently stalled browser automation; live cancellation is not certified.
Read-only Sowing navigation was revisited after the pause, but a new Sowing form capture was not
obtained. Shared behavior is covered by focused consumer tests. Actual zoom and dirty native-prompt
handling remain operator checks. No browser screenshots claim a printer, print-dialog or real zoom test.

## Media contract and controlled proof

Existing Photos external creation saves a reference and record link atomically. The new checked UI
choice then invokes the existing protected local-copy operation. Gallery creation uses the same
copy operation after metadata creation. Failure retains the created reference, reports the partial
success and retries the same asset. No server API/schema/storage model or safe-fetch rules changed.

Controlled frontend tests cover default save, opt-out, retained-reference failure/retry, protected
rendering, existing references, Gallery/Quick Preview and refresh/remove behavior. PostgreSQL HTTP
proof creates a SeedLot external photo, saves a snapshot, reads Photos again, checks protected
thumbnail/content bytes, safely refreshes and removes only the copy while retaining reference/link.
Photos versions thumbnail URLs by fetch timestamp; Media versions by content hash. Both identify the
same protected image. Reads do not trigger remote fetches. Existing address/redirect/MIME/size/pixel
safeguards are retained and tested. Live Review uses only its existing synthetic protected image;
no arbitrary external host was contacted for visual proof.

## Validation

`focused-tests.json`, `serial-tests.json`, `shared-tests.json` and `backend-tests.json` record exact
executed scopes and results. **270 unique frontend tests in 17 suites, 69 backend unit tests and
15 PostgreSQL tests pass.** Strict TypeScript, zero-warning targeted ESLint, Prettier and production
build pass. Final source checks and bundle evidence are recorded in `validation.json`.
Intermediate Sowing interaction runs had cold chunk-loading timeouts; `serial-tests.json` retains that
historical failed run. The final interaction setup preloads SowingScreen, while App.lazy.test.tsx
separately proves chunk loading. `final-regression-tests.json` passes all 48 tests with the original
assertions/timeouts intact. API/schema and migrations are unchanged, so no new
API generation or migration-cycle claim is made. The canonical feature gate was not run.

## Environment and operator boundary

Review stopped during the pause. Only supported `make feature-review-up` restarted the exactly owned
candidate environment. Its existing database/media/dependency volumes, owner/password and v4/66
managed dataset were preserved; database revision remains `20261013_0042`. Operator-added records
are not part of the 66 managed count and were not reset or reseeded. `review-status.txt` records the
final supported status. UAT, DEV, Stable Preview and production were untouched.

All changes remain unstaged/uncommitted and GLOBAL-VISUAL-001 remains in_progress. No stage, commit,
push, delivery or canonical feature-verify. This is readiness for operator visual review.

Final bundle: SeedLot 45.60 kB / 12.39 kB gzip; main 227.89 kB / 70.84 kB gzip. Compared with the
preceding family pass, SeedLot changes -0.28 kB (+0.08 kB gzip), main +0.06 kB (+0.01 kB gzip).
`operator-ready.png` shows the restored authenticated Overview at the browser's normal 1280x720 viewport.
