# COLLECTION-VISUAL-002 review evidence

Candidate: `feat/collection-visual-002`, base `a36c6cffb938c5ed20f93942e1eac1070897962c`,
worktree `/home/alessandro/.codex/worktrees/fb05/florabase`.
[Feature Review](http://localhost:15174), owner login `owner`, known credentials supplied in chat.
DB `20261013_0042`, deterministic v4 fixture, 80 managed records. See the
[handoff](../../collection-visual-002-handoff.md) for scope and limits.

## Current operator follow-up

The [third-pass evidence](third-pass/README.md) covers the latest typography, rounded row controls,
New Harvest alignment, Active/Retired filtering and bounded Parent location menu.

## First-pass screenshots (historical)

The current [second-pass evidence](second-pass/README.md) supersedes these images for the refined
Harvest, stored-material and Location surfaces. These original images remain useful for creation,
media and retained workflow context.

## Screenshots

These 23 representative images cover the requested families and responsive extremes. Full-page
captures may include content below the initial viewport; the mobile Create footer is captured
separately at the bottom of its natural scroll. No stock, record, hierarchy or retirement mutation
was submitted during this visual pass.

| State                                 | Desktop                                                                                          | Mobile                                                                                                    |
| ------------------------------------- | ------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| Harvest directory / Quick Preview     | [Selected preview](harvest-directory-desktop.jpg)                                                | [Directory](harvest-directory-mobile.jpg)                                                                 |
| New Harvest                           | [Default canvas](harvest-create-desktop.jpg)                                                     | [Default top](harvest-create-mobile.jpg), [multiple-material footer](harvest-create-mobile-footer.jpg)    |
| Contextual Create                     | [Plant preselection](harvest-contextual-create.jpg)                                              | Source Cancel/Back observed without a separate image                                                      |
| Harvest Details / Photos              | [Mixed historical materials and shared Photos](harvest-detail-desktop.jpg)                       | [One-page details](harvest-detail-mobile.jpg)                                                             |
| Harvest correction                    | [Contextual aggregate](harvest-edit-desktop.jpg)                                                 | [Contextual editor](harvest-edit-mobile.jpg), [direct full-page fallback](harvest-direct-edit-mobile.jpg) |
| Stored material / explicit conversion | [Tracked source](harvest-stored-material-desktop.jpg), [conversion](seed-conversion-desktop.jpg) | [Conversion](seed-conversion-mobile.jpg)                                                                  |
| Location directory / preview          | [Hierarchy and selected preview](locations-directory-desktop.jpg)                                | Deep hierarchy below                                                                                      |
| Deep Location tree                    | [Full path in preview](location-deep-desktop.jpg)                                                | [Capped indentation and parent context](location-deep-mobile.jpg)                                         |
| Location Details                      | [Direct/inclusive table](location-detail-desktop.jpg)                                            | [Responsive details](location-detail-mobile.jpg), [retired empty Location](location-retired-mobile.jpg)   |
| Location create/edit                  | [Small Edit dialog](location-edit-desktop.jpg)                                                   | [Create](location-create-mobile.jpg), [Edit](location-edit-mobile.jpg)                                    |

## Responsive observations

[Machine-readable measurements](responsive-measurements.json) contain **66 unique state/viewport
observations**. The six requested effective sizes are 1440×844, 1152×675, 960×563, 1024×844, 819×675
and 390×844. The reduced sizes are **viewport proxies** for 125%/150%; actual browser zoom was not
controlled. Checks waited for settled browser state after resizing. No observation reports document
width above viewport width or an off-screen form control. Deep Location child bounds were also
inspected. This is scoped DOM/browser evidence, not a claim that every possible aggregate fits
without vertical scrolling.

Default New Harvest footer measured 811px from the top at 1440×844. It is static and transparent;
known quantities, day precision and more material lines increase page height naturally. Contextual
Harvest Edit and seed conversion use one scrolling form with a visible sticky footer. At mobile,
Create's captured bottom clears the navigation bar. Location dialogs retain compact controls and
explicit required-group scope copy.

Live interaction checks: source picker placement and Escape; Add/Remove material focus; Plant-source
Cancel; PlantGroup-source and generic Create browser Back; desktop Location Quick Preview Edit;
mobile Location/Harvest row-to-detail; deep-tree ancestor search; direct Harvest Edit fallback;
retired and empty Location display. The source picker popup measured approximately 5px below the
input border, aligned to its control width. An initial hidden-browser Cancel attempt stalled input;
showing the browser restored normal interaction. That first dirty-native-confirmation attempt is
not claimed as live proof. Component tests cover rejected dirty dismissal via Escape, Cancel and
backdrop, plus focus return and shared history behavior.

## Checks

All commands used the candidate-owned Review frontend/backend or repository scripts. No canonical
verification receipt was requested or written.

| Check                                                                                        | Result                                                                           |
| -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Harvest/Stored material/conversion/navigation/PartialDate/ReferenceInteractions/FormSections | 68 passed / 7 files                                                              |
| App, Plant, SeedLot, Sowing                                                                  | 213 passed / 4 files                                                             |
| Dashboard, History, Schedule, Settings, Labels, EventFeed, repeated navigation               | 144 passed / 7 files; 16 navigation cases overlap the first run                  |
| Final changed Harvest + navigation recheck                                                   | 29 passed / 2 files; overlaps above                                              |
| **Distinct frontend total**                                                                  | **409 passed / 17 files**                                                        |
| Review fixture isolation/guards + live read/rollback preservation                            | **23 passed**                                                                    |
| Targeted ESLint                                                                              | Zero warnings/errors after a test-only unsafe-history-state access was corrected |
| Strict TypeScript and frontend production build                                              | Passed; final Harvest chunk 47.23kB / 11.61kB gzip                               |
| Touched frontend/Markdown formatting; fixture Ruff format/check                              | Passed                                                                           |
| Feature graph                                                                                | 106 valid features; new feature `implemented`                                    |
| Whitespace                                                                                   | `git diff --check` passed                                                        |
| Review fixture repeat                                                                        | v4/80 retained; existing owner/edits preserved                                   |

Focused frontend command groups used `pnpm test` with the exact files named in the table. Final static
validation used `pnpm exec eslint <changed TS/TSX paths> --max-warnings 0`, `pnpm build` (including
`tsc -b`), and touched-file `pnpm exec prettier --check`. Fixture verification mounted only the current
scripts into the exact Review backend and ran `pytest --no-cov /workflow/test-review-fixture.py` with
Review identity and `REVIEW_FIXTURE_LIVE_TEST=1`, followed by scoped Ruff format/check. Feature JSON preserves the existing repository formatting and passes parsing/graph validation. Repository
checks used `python3 scripts/check-features.py` and `git diff --check`.

An early baseline attempt overlapped dependency initialization and the then-incomplete stylesheet;
it is not counted. Initial presentation assertions were updated for minimal rows, the More action,
explicit total labels and untracked-material copy while retaining domain assertions. A stored-material
filter test timed out during exhausted host swap, then passed unchanged in subsequent complete focused
runs. New test query options and unsafe history-state access were corrected after static checks. No
timeout, domain validation, business assertion or error handling was weakened.

There is no backend application/API/schema/migration/dependency change. Application backend,
PostgreSQL integration, API drift and migration-cycle gates were not run. Canonical feature-verify,
operator visual acceptance and independent review remain subsequent gates. Persistent UAT and other
operator environments were not modified.
