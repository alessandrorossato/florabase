# LOCATION-003 — Derived hierarchical collection usage

## Contract and scope

Implemented on `feat/location-descendant-aggregation`, based on `c1fc7c5`. The canonical sequence
already contains LOCATION-001 (hierarchy foundation) and LOCATION-002 (scope-aware browsing), so this
increment is LOCATION-003. It remains `implemented` pending final commit and delivery.

Supported canonical assignments are SeedLot, Sowing, Plant and PlantGroup `location_id`. Direct usage
means exactly this Location. Including sublocations means this Location plus every descendant at any
depth, counted once per record. These are record counts, not PlantGroup quantities or seed amounts.
`total` retains every existing lifecycle state; `active` includes only `lifecycle = active`. Null
assignments, Events, botanical identity, provenance, source records and lineage never infer physical
containment. Explicit assignment eligibility scopes do not inherit through the hierarchy.

The Location responses add `direct_usage` and `usage_including_descendants`. Each contains `plants`,
`plant_groups`, `sowings` and `seed_lots`, with `active` and `total`. The existing `usage` response
retains its direct meaning and combined Plant/PlantGroup `plants` field. All list, detail and mutation
responses use the additive contract; generated OpenAPI and TypeScript declarations are updated.

No schema migration, speculative index, persisted counter, backfill, synchronization job or new
Location-supported record type is introduced. Existing direct-only assignment-scope removal and
leaf/direct-reference/Event-history deletion guards are unchanged. There is no deletion-policy ambiguity.

## Queries and reparenting

The directory uses two domain queries: one read of Locations for hierarchy/current paths, and one
batched PostgreSQL aggregate for every Location and supported record type. Auth/session queries are
separate. Single-record reads retain their initial record lookup and the same two batched queries.
Writes retain their existing hierarchy/assignment guards; they do not synchronize aggregates.

The recursive CTE starts with self-pairs and derives `(ancestor_id, descendant_id)` containment pairs.
Recursive `UNION` deduplicates pairs, terminates even for malformed persisted cycles and does not count
self-membership twice. The four record tables are each grouped once by canonical current Location
before `UNION ALL` combines their type-labelled count rows. Joining those rows to containment pairs
and grouping by ancestor/type produces both direct conditional sums and inclusive sums in one query.
Only aggregate rows reach application memory; no per-Location query or record-table load occurs.
Existing `locations.parent_id` and four `location_id` indexes are retained.

A synthetic PostgreSQL `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` inspection on September 30 used
206 Locations (200 benchmark Locations across 20 ten-level branches plus six review Locations) and
4,015 current assignments (4,000 benchmark assignments plus 15 review assignments). It reported
1,110 containment pairs, 806 grouped assignment rows, 811 output rows, planning **1.870 ms** and
execution **6.107 ms**. Each of the four record-table scans/aggregations ran once, while the recursive
work-table join ran ten iterations. There were no temporary reads/writes. This is local fixture evidence,
not a production latency guarantee; no micro-optimization or index migration was justified.

Reparenting changes containment pairs on the next read and immediately moves usage between roots.
The integration test moves a twelve-level subtree from Greenhouse to Outside, checks all four types,
verifies current descendant paths and verifies that every record's stored Location remains unchanged.

## Presentation and listing decision

Directory rows and desktop Quick Preview show only occupied record types. Inclusive usage leads when
it differs, with an explicit direct count: `Plants: 7 including sublocations · 2 directly here`. Equal
leaf counts appear once: `Plants: 5 directly here`. Empty rows/previews say `No collection records`.
PlantGroups have their own labelled record count, including inactive retained groups.

Detail presents a semantic table with record-type row headers and `Directly here` / `Including
sublocations` column headers, explicit zeroes and active counts. It explains lifecycle inclusion and
subtree scope. Existing collection-directory links remain general browse links.

Location detail had no associated-record list: only usage counts and links to the general collection
directories. This increment adds no record-list filter, scope control or default change. Actual
Location-scoped inherited-record rows therefore do not exist to label. Current Location paths remain
visible in detail/preview and supported by the existing assignment selectors.

Rendered review found that unlimited indentation left a twelve-level mobile row only 26 px wide.
Indentation now stops growing after three levels; deeper rows show `Within <parent name>` and retain
the full current path in their title/preview/detail. Nested semantic lists and keyboard-operable
collapse/selection remain. The corrected twelfth-level row was 211 px wide without internal overflow
at 390 × 844.

## Verification and visual review

Focused backend unit checks passed 12 tests. Focused PostgreSQL checks passed 16 tests across the
Location API and migration suites. Added coverage includes direct/inclusive API values, leaf,
descendant-only, mixed, sibling branches, isolated roots, empty parent/child, twelve levels, all four
record types, every supported lifecycle state, no source-location inference, no duplication,
reparenting, unchanged direct assignments/guards and bounded query count (exactly two domain queries).
A deliberately malformed persisted cycle is checked with a bounded PostgreSQL statement timeout.

Frontend tests cover equal leaf counts, descendant-only and mixed counts, explicit column labels,
empty directory/preview/detail, separate PlantGroups, ancestor scope differences, keyboard selection
and deep-tree parent/path context with collapse/reopen. The final complete suites, formatting, lint,
typing, production builds, API drift, feature graph and whitespace checks are run through the canonical
local gate; its completed outcome and receipt are reported in the handoff.

Rendered review in the Codex in-app browser on October 1 used only synthetic data in the separate
`florabase-location-review` tmpfs PostgreSQL project. Reviewed 1440 × 844, 1024 × 844 and 390 × 844:

- Directory hierarchy and count wrapping at all three widths.
- Desktop Quick Preview: descendant-only parent, occupied leaf and empty Location; Enter selection.
- Detail comparison at all three widths, including direct-plus-descendant counts and inactive groups.
- Mobile long Location name/path, naturally scrolling usage table and twelve-level expanded tree.
- Keyboard collapse/reopen and parent context in deeply nested filtered results.

No page-wide horizontal overflow was observed in the reviewed final frames. Desktop Quick Preview
remains hidden below the existing 1088 px breakpoint; tablet/mobile selection continues to open detail.
There is no list-scope selector to review. Operator visual acceptance and independent final review
are complete.

Screenshots are saved under
`/home/alessandro/.codex/visualizations/2026/09/30/01a0f3ed-0b93-7780-96ec-427c5329b796/`:
`location-1440-directory-preview.jpg`, `location-1440-detail.jpg`,
`location-1440-empty-preview.jpg`, `location-1440-leaf-preview.jpg`,
`location-1024-directory.jpg`, `location-1024-detail.jpg`, `location-390-directory.jpg`,
`location-390-mixed-detail.jpg`, `location-390-usage.jpg`, `location-390-long-path.jpg`,
`location-390-deep-tree.jpg`.

## Changed files

- Backend: `backend/src/florabase/locations/{schemas,service,api}.py`, `backend/openapi.json`.
- Backend tests: `backend/tests/test_location.py`, `backend/tests/integration/test_location_api.py`.
- Frontend: `frontend/src/locations/LocationScreen.tsx`, `frontend/src/api/schema.d.ts`,
  `frontend/src/styles.css`.
- Frontend tests: `frontend/src/App.test.tsx`, `frontend/src/locations/api.test.ts`.
- Documentation: `docs/features.json`, `docs/domain-model.md`, `docs/architecture.md`,
  `docs/progress.md`, this audit.

Work remains unstaged and uncommitted on the requested branch. No branch switch, push, delivery,
merge, commit or feature-finish is part of this handoff.

## BULK-001 interaction

BULK-001 moves active current collection records to a concrete existing scope-compatible Location. Updated-at preconditions include the target, and normal scope/deletion guards remain authoritative. Usage projections reflect the new direct assignments without changing containment or geographic provenance. See [bulk operations](bulk-operations.md).
