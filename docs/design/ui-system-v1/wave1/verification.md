> **Superseded review snapshot:** see [28 October final refinements](refinements/README.md), [current gallery](refinements/index.html) and [current verification](refinements/verification.md). The evidence and source hashes below belong to the earlier candidate.

# Wave 1 verification and limits — 27 October 2026

Review boundary: `FLORABASE_UI_SYSTEM_V1_WAVE1_READY_FOR_REVIEW`.
Source is `feat/ui-system-v1`, current fetched main `c77a1c5330de949168bf5f7c90d0f533af1bc320`
plus the preserved unstaged candidate. [Source digests](source-inventory.json) identify code/test inputs;
they are **not** a canonical verification receipt. No staging, commit, push, PR, merge, FULL gate,
DEV upgrade or protected-environment reset was performed.

## Focused checks

| Check                         | Result and scope                                                                                                                                                                                                                                                                           |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Production Seeds              | **52/52** tests, complete owning screen suite.                                                                                                                                                                                                                                             |
| Production Plants             | **60/60** tests, complete owning screen suite.                                                                                                                                                                                                                                             |
| Shared/shell/Media regression | **290 distinct tests in 18 files**, passed across final scoped runs. Dashboard (6), DirectoryPage (12), Controls, CollectionUI, ThemeControl, SavedViews/state, PrimaryPhotoVisual, RecordVisual, BulkLocation, Lab, generated scaffold, three Media files, App, App.lazy, App.transition. |
| Final overlapping rerun       | **134/134**: App (116), Dashboard (6), DirectoryPage (12). These are included in the 290, not additional tests. Overall **402 distinct frontend tests in 20 files**.                                                                                                                       |
| Backend contract              | **3/3** `backend/tests/test_collection_views.py`, with `--no-cov`.                                                                                                                                                                                                                         |
| PostgreSQL integration        | **5/5** `backend/tests/integration/test_dashboard.py`, through the exact-file disposable runner. Automatic cleanup reported zero residual containers/networks/volumes and no retained image.                                                                                               |
| Scaffold generator            | **3/3** `python3 -m unittest discover -s scripts -p test_ui_page.py`; actual generated TSX and its keyboard/state test also pass.                                                                                                                                                          |
| Verification policy           | **24/24** impact-inventory regressions. Existing policy selects FULL for shared primitives/unknown inputs; it was inspected, not executed. No unrelated CI hotfix or weakening.                                                                                                            |
| Static / contracts            | Strict `tsc -b --pretty false`; zero-warning ESLint on changed TS/TSX and lab/example; Ruff check/format on touched backend and Python helpers; mypy on five collection_views files; `make api-check`; feature graph **118 valid**; Prettier and whitespace checks.                        |
| Build                         | Default Vite production build; exclusion check rejects lab paths, fixture digests, showcase strings and generated-example marker in `dist`.                                                                                                                                                |
| Evidence integrity            | `python3 docs/design/ui-system-v1/wave1/validate.py`: exact matrix, JPEG hashes/raster sizes, retained baseline hashes, Dashboard geometry, protected photo URLs, explicit sparse fixture and source digests.                                                                              |

Vitest ran from `frontend/` with `--configLoader runner --pool=threads --maxWorkers=1`.
The shared run initially had two App native-range setup failures. Inspection showed its lazy workspace
was still loading when the unrelated interaction fixture searched for its create control. The fixture
now preloads the identity module, as the SeedLot interaction suite already does; separate App.lazy and
App.transition cases retain deferred-loading acceptance. Both isolated cases and then all 116 App cases
passed without timeout increases, skipped assertions or production loading changes.

Earlier screen failures exposed the disconnected Plant Back focus target and sparse-record placeholder;
these were corrected. Expectations that explicitly required the former empty inspector column or hid
recorded storage were updated to the approved composition. Quantity, lifecycle, extraction/reversal,
atomic-move, URL, save-failure and authentication assertions remain. Group location coverage now uses
an actually located Group fixture. Ordinary lint findings were fixed without suppression.

The photo integration verifies empty/fewer/eight results, binary-content deduplication **before** the
limit, deterministic ordering, pending-delete exclusion, saved external cache version, attribution and
one-query bound. A read-only check of the running primary Review confirmed **8 asset IDs / 8 distinct
content hashes**. No provider fetch, attachment rewrite, cover change or inferred association occurs.

Console logs are retained outside Git and outside the served portal roots in the task visualization
directory under `wave1-verification-logs/`, including the initial shared-run failures and final passing
reruns. The handoff counts distinct cases across the passing scoped runs, not repeated executions.

## Actual browser evidence

[Manifest](captures.json): **58 JPEG captures**, including the complete **40-case production matrix**
(five compositions × four widths × Light/Dark), plus contextual and sparse/developer evidence.
The generated example is explicitly labelled development-only. Retained actual-before captures are
listed in [baseline.json](baseline.json), source `ee34874`, 26 October, same preserved v5 collection.
There is no retained before capture at 880px; the gallery says so instead of scaling another width.

JPEGs and DOM sidecars remain outside Git under the task visualization directory's
`ui-system-v1/renders/wave1/`. CSS viewport and returned JPEG dimensions are separate fields: the
browser capture API can scale the content raster when a document scrollbar is present. The complete
1440×844 Dashboard captures have actual 1440×844 rasters. No images were resampled for acceptance.

[Dashboard geometry](dashboard-geometry.json), both Light and Dark:

- CSS/document **1440×844**, DPR **1**, visual scale **1**, sidebar **252px**.
- **8 loaded / distinct protected thumbnails**, four columns × two rows, exact 4:3 image frames.
- Last complete photo card bottom **722.914px**; all **five** planned entries retained.
- Next work bottom **772.883px**; footer bottom **825.883px**.
- No fixed-height clipping or text ellipsis. Recent activity expands naturally and keeps all six facts;
  Journal, History, Schedule, global search, Saved Views and Quick add remain reachable.
- Smaller viewports scroll naturally, including deliberately long fixture names/storage hierarchies.
  All 40 primary cases have no document-level horizontal overflow.

Browser interactions also verified concrete Group bulk checks surviving List/Gallery and real Back/
Forward, search/type/lifecycle retained, inline preview selection and focus return after remount,
native modal preview at 880px with Close initially focused and Escape returning to its trigger,
full mobile SeedLot/Plant detail, long cultivar/storage labels, actual no-matching results, empty
inventories and missing-identity guidance. Gallery labels separate primary/source/reference fallbacks.
A legacy generic hover rule that filled collection buttons with primary color was reproduced and
corrected; Light/Dark use the semantic surface-hover and readable text.

## Runtime ownership and preservation

Primary production Review: **florabase-ui-audit-bc88**, `http://localhost:15279`, this worktree.
Existing database and media were preserved through conservative restart. V4 ledger remains ready/80,
with the retained v5 extension. Current factual KPIs are **17 / 7 / 40 / 12**. Media #127 is delivered
in the selected source. Code/database head is **20261013_0042**, with no schema migration in this wave.
The already-authorized synthetic-owner recovery was limited to authentication; no product reset.

A host restart removed the old temporary launch/credential files and stopped the local servers.
The owned Review, read-only portal and development lab were restarted. Main's browser session survived;
no repeated recovery was necessary. Local adapters in `/tmp/florabase-wave1-bc88/` reuse the canonical
Environment ownership/configuration guards with exact project/port constants and `/dev/null` config.
They are task setup, not a new supported multi-Review mechanism.

With explicit operator authorization, **florabase-ui-wave1-sparse-bc88** was initialized independently:
one synthetic owner, **two** locally stored packaged/licensed illustrations, **zero** collection records.
No changes to the primary Review's assets/relationships were made for this scenario. Its final canonical
origin is **http://127.0.0.1:15285** so its host-scoped sign-in cookie does not replace localhost's primary
Review session. Exact Origin/CSRF checks remain; backend/database have no published host ports.
Private credentials remain outside Git and outside the portal's served asset roots.

Runtime commands from this worktree (temporary adapters must still exist):

```sh
python3 /tmp/florabase-wave1-bc88/environment.py up
python3 /tmp/florabase-wave1-bc88/sparse-environment.py up
python3 docs/design/ui-system-v1/serve.py
make ui-lab
```

If `/tmp` is cleared, reconstruct the adapters with the documented exact source/project/port/origin
and canonical guards; do not substitute stock Feature Review resources or reset any database. The
read-only portal serves only documentation, mapped retained baseline images, packaged photos/fonts
and renders. Standard/foreign Review, DEV, UAT, stable/production and other worktrees remain untouched.
No cleanup of the two owned persistent Reviews is scheduled by this handoff.

## Remaining risks / unverified acceptance

Canonical FULL, coverage thresholds, complete integration/migration-cycle and protected delivery remain
pending after the operator's visual review. UI-SYSTEM-001 is not marked verified. No physical-device,
soft-keyboard, assistive-technology, true browser-zoom or comprehensive WCAG certification; CSS viewport
and keyboard evidence are bounded. No live-provider or large-library performance benchmark.
Loading/error/retry/authentication behavior is exercised by focused tests; no synthetic network-failure
interceptor was put into the real app for a screenshot. Actual empty/no-match states are captured.

The retained collection has many records without images and intentionally extreme storage labels;
those are honest fallbacks and natural wrapping, not artificially completed photography. The separate
Review is labelled a sparse fixture. Page archetypes do not implement future domain APIs or full CRUD.
Wave 2 remains a recommendation in the [handoff](README.md), not an authorized automatic migration.
