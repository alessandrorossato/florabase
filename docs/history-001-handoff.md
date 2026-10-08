# HISTORY-001 — independent verification and delivery handoff

## Worktree and review boundary

- Worktree: `/home/alessandro/.codex/worktrees/ed24/florabase`.
- Branch: `feat/history-001-operational-history`, initialized with `make feature-init`.
- Base and unchanged HEAD: `f0d9a0ec9806842c847ba8c8a6af1172de75624f` (BULK-001, PR #74).
- Implementation, generated contracts, tests and documentation are unstaged, including new files. The
  implementation phase left everything uncommitted. Operator UAT has now passed,
  including the final Activity/navigation refinement. This review owns canonical verification, the
  feature commit, protected delivery and finish.
- The primary checkout was not modified. No screenshots, environment files, secrets, real operator
  data, dependency changes or generated build output are included in the diff.

## Source audit and deduplication

The complete source/date/subject/reference/duplicate/deep-link matrix is maintained in
[the History contract](operational-history.md#audited-source-matrix). The implementation audit is:

| Audited source | Included | Reason / representation |
| --- | --- | --- |
| Ordinary, movement, death, transfer, extraction and reintegration Events | Yes | Existing recorded journal facts; current corrected values, stable Event identity |
| Harvest-owned Event | Through Harvest | Structured Harvest and its Event represent one collection operation |
| SeedLot → Sowing receipt | Yes, when no Event | Durable propagation receipt; resulting Sowing and source SeedLot |
| Sowing → Plant / PlantGroup receipt | Yes, when no Event | Durable propagation receipt; exact resulting kind and source Sowing |
| Extraction / transfer receipt | Through Event | Receipt supports status; no second row for its Event |
| GerminationObservation | Yes | Exact observed_on day and incremental count, linked to Sowing |
| Harvest and ordered HarvestItems | Yes, one row | Harvest owns date/source; item count is context, not extra operations |
| Partial / use-all HarvestMaterialDisposition | Yes | Stored amount, mode and optional occurrence date; exact inventory context |
| Conversion-owned disposition | Through conversion | A conversion and used_for_propagation disposition are one action |
| HarvestSeedLotConversion application | Yes | Retained operation and exact resulting SeedLot/source inventory |
| Conversion reversal | Yes, separately | Its own persisted reversed_at proves an independently dated occurrence |
| Propagation receipt reversal | Original row status only | Reversed is persisted, but no reversal instant exists to support a new occurrence |
| Ordinary record creation or inventory tracking | No | Current records alone do not establish an approved historical operation |
| Current SeedLot/Sowing lifecycle, Location, quantity or updated_at | No | No historical transition evidence; current state must not fabricate a dated row |
| Supplier, provenance site or geographic-place corrections | No | Reference/current context, not collection operation history |

Historical labels are not reconstructed: references display current record labels. Ordinary Event
deletion removes its projection; corrections update the same typed key. No immutable audit copy or
new operational-history persistence exists.

## Dates, identity and routes

PartialDate precision stays year/month/day. Missing occurrence dates use created_at with a visible
**Recorded** label. Receipt result_date values are descendant Sowing/collection-entry snapshots for
reversal checks, not a separately contracted propagation occurrence date; receipt rows use Recorded.
Conversion reversal uses the UTC day and retains its precise instant. updated_at is never a date
source. Timeline year filters the displayed occurrence year or UTC recording year.

Global order: displayed year descending; known month/day descending with missing components last;
precise reversal or recording timestamp descending; typed key ascending. Sorting never supplies
missing rendered precision. Keys are `event:<uuid>`, `harvest:<uuid>`, `germination:<uuid>`,
`operation_receipt:<uuid>`, `disposition:<uuid>`, `conversion:<uuid>:applied` and
`conversion:<uuid>:reversed`.

Each typed HistoryEntry has source identity/category/subtype, occurrence and recording fields,
date_basis, title, compact factual context, primary reference, at most two direct related references
and supported operation status. Typed references generate ordinary domain links:

| Reference | Authoritative route |
| --- | --- |
| Event target Plant / PlantGroup | Existing detail with `?tab=events` |
| Propagation result Plant / PlantGroup / Sowing | Existing result detail |
| Germination observation | Sowing detail with `?tab=germination` |
| Harvest | Existing Harvest detail |
| Stored inventory | Owning Harvest detail with `?inventory=<uuid>`; loads, scrolls to and focuses the exact inventory line |
| SeedLot / Location | Existing respective detail |

No arbitrary URL is persisted or accepted. Full notes, media, storage paths and generic detail
pages are absent from History responses.

## API and Saved Views

Authenticated read-only `GET /api/v1/history` supports repeated category, primary subject_kind and
timeline year (1–9999). Default limit 50, maximum 100; offset 0–100000. Response: items, filtered
total, offset and limit. Deduplication precedes filtering, deterministic global sorting and paging.
One SQL UNION projection/count/page statement fetches only the page into Python; labels and direct
references are joined, with no per-row queries or external requests. Empty pages still return total.

History Saved Views v1 store only canonical category, subject_kind and year; defaults are omitted,
categories deduplicate in vocabulary order, and unknown/transient state is rejected. Opening a view
uses its normal canonical URL and fresh query at page one, including reopening the identical view.
No result snapshot, pagination or browser persistence is saved.

Migration `20261007_0035` changes only the SavedView surface check constraint. It adds no table,
column or index and performs no operational data backfill. Downgrade locks SavedViews and refuses
while any History views exist, without deleting them. Explicit deletion permits downgrade and
re-upgrade; other surfaces retain their records and validation.

## UI and accessibility review

Activity has separate **Journal** (`#/events`) and **History** (`#/history`) destinations. Journal
explains Plant/PlantGroup observations and actions, keeps correction help secondary, and renders
date → kind → primary target → bounded notes excerpt → secondary relationships. Lifecycle displays
the unchanged `status` filter (transfer, death, loss, discarded); all Event kinds and Saved View
`events` identifiers remain compatible.

History permanently explains its read-only cross-domain role and gaps, linking to Journal. Named
pressed category chips include explicit All activity, with compact primary-type/year controls,
Apply/Clear year, Clear filters and existing paging. A compact semantic ordered timeline uses a
subtle rail/markers and preserves PartialDate precision, explicit Recorded labels, product-facing
action titles, status text and authoritative links. No mutation or scheduling controls are added.

The six desktop sidebar groups have keyboard disclosure buttons, chevrons, visible focus and
`aria-expanded`. First use expands all groups; known collapsed names persist in browser localStorage
only. Malformed/unavailable storage is safe. Route activation expands the active group, including
refresh/deep links and Back/Forward. Mobile keeps its compact navigation and More pattern.

Independent refinement browser review completed Journal/History at 1440×844 and 1024×844,
including sidebar keyboard focus, collapse/refresh persistence, collapsed Activity route expansion,
Journal Saved Views, History multi-category/year Apply/Clear and canonical URLs. At 390×844,
History orientation/filter wrapping, pressed states, semantic timeline DOM and all mobile More
entries were inspected without horizontal overflow (375px document plus scrollbar in a 390px viewport).
Browser control then timed out and its inventory became empty, so this independent pass did not
inspect mobile Journal or the scrolled timeline/long-label cases. The operator subsequently reported
HISTORY-001 UAT passed, including the Activity/navigation refinement; product acceptance is complete.
No UAT records were changed or reseeded during this independent refinement.

## Verification evidence

Final focused results are recorded in the accompanying progress milestone. Commands use existing
isolated QUALITY images with network access disabled for checks, and a uniquely named
disposable PostgreSQL project for integration. The integration fixture project and only its proven
volumes are removed on exit. Canonical coverage/full-suite verification is recorded below.

| Check | Final result |
| --- | --- |
| Canonical non-integration backend suite | 749 passed; 597 integration tests excluded |
| Canonical PostgreSQL integration suite | 597 passed; isolated disposable project cleaned |
| Canonical frontend Vitest suite | Passed; 474 tests across 48 files |
| Formatting, lint and typing | Backend Ruff; workflow Ruff/mypy; frontend Prettier, zero-warning ESLint and TypeScript all passed |
| Generated API drift | Backend OpenAPI and frontend TypeScript declarations passed their checks |
| Feature graph and production build | 93 feature records valid; backend and frontend production images built |
| Migration cycle | Upgrade, guarded downgrade, and re-upgrade through `20261007_0035` passed |
| Whitespace and receipt | `git diff --check` passed; canonical verification receipt recorded for this worktree |

PostgreSQL emitted expected constraint refusals exercised by negative regression tests and 172
existing integration warnings; the final run has no failures. Initial development failures in test
fixtures, strict frontend lint, query-plan literal NULL typing and a missing navigation stub were
corrected. A cold targeted navigation run timed out loading Seeds; the final complete App regression
passed with the normal unchanged timeouts. No test/type/validation/coverage policy was weakened.

- Backend unit regressions cover projection/API argument validation and Saved Views alongside Events,
  germination, Harvests, inventory and conversion contracts.
- Real PostgreSQL coverage includes all six source families, owned backing-row deduplication,
  ordinary corrections/deletion, retained reversals, truthful dates, current-state/reference negative
  cases, auth/query validation, stable mixed-source pages and timezone-independent Recorded years.
- Query checks assert one SQL statement for normal, filtered, later-page and maximum-limit requests.
  An eleven-row mixed dataset crosses three-row pages; 105 tied Events cross the 100-row boundary.
  EXPLAIN ANALYZE/BUFFERS executes the real UNION/count/page statement without brittle latency limits.
- Migration tests preserve existing Event views, exercise History CRUD/validation, reject downgrade
  with History rows and verify compatible downgrade/re-upgrade after explicit deletion.
- Frontend regressions cover History presentation/dates/status/deep links, filters/URL/Back/Forward,
  paging, retry/session expiry, Saved View creation/reopening, exact inventory focus and existing
  Events/Harvest/Stored material/Saved Views/navigation behavior.
- Ruff, strict mypy, Prettier, zero-warning ESLint, strict TypeScript, generated API drift, feature
  graph, production image builds and whitespace are checked separately from the canonical gate.

## Operator-UAT refinement verification (2026-10-07)

The accepted Activity/navigation refinement changes frontend presentation/navigation and documentation only. Event model,
EventKind grouping, backend/API paths, History source projection/dedup/date/query behavior, route
identities and persisted Saved View surfaces are unchanged. Migration 0035 remains the sole migration.

- Focused History and Saved Views backend unit tests: **88 passed** (`--no-cov`).
- Relevant isolated PostgreSQL regressions: **123 passed**, including source/dedup/date/current-state
  exclusions, correction/deletion, reversals, query bounds, Saved Views and migration cycles. The unique
  integration fixture was cleaned; UAT/DEV/operator resources were preserved.
- Frontend focused regressions: **181 passed across 12 files** (172 across ten files plus the final
  corrected two-file rerun with nine tests): App/navigation, Journal, History, Saved Views/state,
  EventFeed, Harvest/Stored material, lazy/transition, UX001 and Dashboard search.
- Whole-frontend ESLint, strict TypeScript and Prettier passed. Existing API declarations pass both
  drift checks. Backend/frontend production images built successfully. Feature graph: **93 valid**.
- Test expectations were updated to allow only the explicit sidebar preference in storage while
  continuing to reject token/credential persistence, distinguish sidebar Reference heading from its
  existing detail heading, and match the unchanged Saved View API call including offset zero.
  No checks or timeout/coverage policies were weakened. One interrupted static run was not counted;
  completed checks supply the evidence.
- `make uat-preview-status`: all three services healthy, live source ed24, DB/code revision 0035,
  fixture v1 / 31 baseline records, existing edits preserved. No reset, reseed or lifecycle action.
- Operator UAT and the accepted Activity/navigation refinement have passed. This phase owns the
  canonical gate, reviewed commit, protected delivery and feature finish.

## UAT Preview and recommended operator scenarios

URL: `http://localhost:15174/#/history`. UAT-only credentials: **preview / preview**.

The previously owned b647 UAT Preview was retired with the supported guarded removal helper,
then `make uat-preview-up` and `make uat-preview-seed` ran from this worktree. Source ownership is
ed24, DB revision is 20261007_0035, and fixture v1 retains its 31 baseline records. DEV, Stable Preview,
Feature Review and production were not changed. Seed contents already expose two undated journal
observations and a month-precision structured Harvest. During the accepted Activity/navigation refinement, UAT data was neither reset nor reseeded.
The fixture has not been extended or versioned;
create additional operation facts through normal UAT UI for the following scenarios.

1. Open History and Journal separately. Check the two Recorded observations and September Harvest;
   follow the Plant Events and Harvest links, then return with browser Back.
2. Create year-only, month-only and day Event dates and an undated Event. Correct/delete an ordinary
   Event and confirm one stable current projection; no false occurrence date or duplicate audit row.
3. Use normal propagation to create Sowing, Plant and PlantGroup results; add a germination observation.
   Confirm result/source links, exact observed day and Recorded receipt dates. Reverse an eligible
   result and inspect the retained Reversed row, without a fabricated reversal occurrence.
4. Move a Plant or PlantGroup and exercise eligible transfer/extraction/reintegration workflows.
   Confirm Event-backed receipts do not appear twice and destination/result links remain authoritative.
5. Open the Basil seed Harvest, explicitly track its remaining material, and record partial/use-all
   dispositions on suitable material. Convert stored seeds to a SeedLot, then reverse an eligible
   conversion. Confirm exact inventory focus, conversion/disposition dedup and distinct reversal date.
6. Change SeedLot/Sowing lifecycle, direct Location/quantity, Supplier or provenance without an
   operation source. Confirm History does not invent transitions. Plant/Group moves still have Events.
7. Combine categories, primary type and year; save/reopen a History view, refresh and use Back/Forward.
   Confirm canonical URL/filter restoration and page-one reset. With over 50 facts, inspect both page
   directions and quiet filtered totals. Try an empty combination and an invalid year.
8. Repeat filters/links/Saved Views with keyboard at desktop/tablet/mobile widths; inspect focus,
   long labels and row wrapping. Retry/error/pagination/status edge cases also have automated coverage.

## Roadmap

Operator UAT and independent canonical verification passed; `docs/features.json` records HISTORY-001
as `verified`. This review owns the protected commit/delivery/finish phase. Protected delivery
completes Collection productivity v2; Orders / Purchases follows. SCHEDULE-001 remains future
scheduling work; BOTANY-003 is unchanged.
