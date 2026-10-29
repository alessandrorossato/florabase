# Final refinement verification — 29 October 2026

Historical framework-review evidence on `feat/ui-system-v1`, base/main `c77a1c5`.
The [final Plants Gallery handoff](gallery-final.md) supersedes this phase boundary.
No canonical FULL, delivery, PR, merge, schema migration or environment/data reset was performed.

## Focused checks

- **317 distinct frontend tests across 13 files** passed across scoped runs: the nine-file
  domain/shared/MediaScreen/lab/scaffold run contains 305 cases, with its one Plant focus defect
  corrected and all 62 Plants rerun successfully; BulkLocation's added cap test brings that set
  to 306; four additional Media navigation/lazy-transition files contribute 11 distinct cases.
  Earlier overlapping 289-case and final targeted 8-case runs are not added to this total.
- Seeds **55**, Plants **62**, BulkLocation **15**, Dashboard **7**, DirectoryPage **12** and
  App **117** cover quantity/lifecycle, routing, overlays, focus, Ctrl/Cmd entry, checkbox/count,
  100-item limits, scope resets, view/history preservation, existing Location moves, Plant sample
  stability, primary/reference/missing fallback, Plant links and nine Quick Action icons.
- Three backend contract unit tests passed. **7/7 final isolated PostgreSQL Dashboard tests passed**, with zero residual disposable resources. Cases verify
  empty/fewer/eight active individuals, exclusion of groups/historical records, explicit primary
  and identity reference separation, unavailable imagery, bounded five-query resolution,
  seeded sampling beyond the first 100 records, remote-only reference exclusion and cultivar title.
- Strict TypeScript, scoped zero-warning ESLint, Prettier, Ruff/mypy, generated OpenAPI/TypeScript
  drift, default production build, lab/example exclusion, feature graph and whitespace checks pass.
  Commands use installed executables; pnpm's automatic reinstall was not used after it attempted
  a dependency refresh. No dependency or lockfile was changed.

The initial broad screen run used ambiguous old one-button row selectors; these now distinguish
record bodies from the three named actions. Assertions requiring storage in primary rows now
require it in Preview. Modal cancellation assertions distinguish the editor from the retained
Preview dialog; removed/remounted triggers return to the connected inventory fallback.
The later extraction Cancel regression was a real focus race: generic detail-heading autofocus
could override the restored Extract command. The owning effect now respects the existing return
intent; the original assertion and all domain tests remain. No timeout increase or skipped assertion.
JSDOM emitted an unimplemented `Window.confirm` warning in the broad run; actual dirty-confirmation
behavior is separately exercised with the existing confirmation mocks, not certified by that warning.

## Actual application evidence

[Gallery](index.html), [manifest](captures.json), [source inventory](source-inventory.json).
**80 original JPEG captures**: 40 List/Gallery/Dashboard matrix cases, 32 overlay/selection cases,
and eight same-record comparison, long-label/footer, history and group-context captures.
All four CSS sizes (1440, 1024, 880, 390 × 844) and Light/Dark are present without horizontal overflow.
JPEG raster dimensions are recorded separately from CSS viewport; the browser capture API may scale
content when a scrollbar is present. Acceptance images were not resampled.

Both 1440×844 Dashboard appearances have eight distinct canonical Plant links, 4×2 4:3 frames,
five Next work entries and footer bottom **825.766px**, with document extent **1440×844**, DPR/scale 1.
The eight Plant IDs remain identical through all eight appearance/viewport captures of that visit.
This particular random sample has missing photographs; placeholders are honest. The previous
MediaAsset gallery must not be mistaken for eight photographed owned Plants. Primary/reference
fallback is covered by domain/component tests and the actual same-record Basil preview comparison.

Real browser interaction additionally verified Ctrl and Cmd initiation, checkbox continuation,
Gallery/List plus Back/Forward retaining two choices, and a material search resetting selection.
[Selection history](selection-history.json) records this proof. Native Close receives initial focus;
Escape returns to the named invoking action. Long cultivar/location facts remain accessible.
Keyboard Tab reaches the long SeedLot overlay's Edit footer after **44px internal scrolling**;
its bottom is **827.203px** at the 844px viewport, with no obscured control.

The old right-inspector and new overlay comparison uses the **same retained Basil mother Plant**,
search, 1440px width and Dark theme. Historical screenshots remain under the earlier Wave 1 report;
its source fingerprint is intentionally superseded, not a current verification receipt.

## Preservation, integration and limits

The 29 October resume found the host restarted, `/tmp` logs removed and the two application
containers stopped. Their exact Review/source/branch/project labels were checked before restarting
only `florabase-ui-audit-bc88-{backend,frontend}-1`. The database remained healthy and persisted;
no volume reset, fixture reinitialization, photo assignment or collection write occurred.
The interrupted last PostgreSQL result was re-executed in a disposable project with persistent log.
Older focused results above remain evidenced by this chat's tool outputs; those temporary raw logs
were lost on restart. New final logs are outside Git and served roots under `wave1-final-logs/`.

Latest fetched integration base includes Media #127 and its separate CI inventory fix #128.
There is no migration or new endpoint. Existing unrelated candidate inputs retain their prior hashes.
The cross-domain [bulk proposal](bulk-operations.md) is for separate approval; the planned
`DASHBOARD-CUSTOMIZATION-001` adds no production settings/drag-and-drop implementation.

Independent QA/canonical FULL, full coverage/migration-cycle verification, physical devices,
assistive technology, actual browser-zoom certification, large-library performance and live-provider
checks remain pending. SQL random sampling scans the eligible population; measure before adopting
it for very large collections. Viewport geometry is not a claim of physical-device certification.

The last added remote-reference fixture initially omitted Media's mandatory attribution; that fixture
was corrected without relaxing the database constraint. Docker then exhausted its automatic address
pools. An external temporary adapter supplied only the integration network IPAM subnet
`10.231.7.0/28`, checked against existing Docker networks and host routes. The canonical disposable
runner, ownership labels and exact-project cleanup remain in use; no unrelated networks were removed.
This adapter is test setup outside the repository, not a workflow/configuration change.
