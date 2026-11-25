# CARE-BULK-001 + FN-03 — bulk care logging, batch undo, and Watering/Feeding Journal kinds

Implemented on `feat/care-bulk-001` from `origin/main` at
`b632c5c734fdab55e62230cdee99938ae34ece7e` (writer `neon`), prepared for Batch 13 alongside
`feat/propagation-batch-001` and `docs/docs-004-batch12-followups`.

## Scope delivered

- **FN-03 (`watering`, `feeding` Journal kinds)**:
  - Added `EventKind.WATERING` (`"watering"`) and `EventKind.FEEDING` (`"feeding"`) to
    [`backend/src/florabase/events/model.py`](../../../backend/src/florabase/events/model.py).
  - Single-record `EventJournal` composer offers Watering and Feeding; both per-record Journal and
    global Journal (`#/events`) group them under a **Care** filter category
    ([`frontend/src/events/eventData.ts`](../../../frontend/src/events/eventData.ts),
    [`frontend/src/events/EventJournal.tsx`](../../../frontend/src/events/EventJournal.tsx)).
  - Marked `watering` and `feeding` as informational retainable observations (confirmation-required,
    not blocking) for propagation creation reversal
    ([`backend/src/florabase/propagation/reversal.py`](../../../backend/src/florabase/propagation/reversal.py))
    and PlantGroup reintegration
    ([`backend/src/florabase/plants/service.py`](../../../backend/src/florabase/plants/service.py),
    [`backend/src/florabase/plants/schemas.py`](../../../backend/src/florabase/plants/schemas.py)).
- **CARE-BULK-001 (bulk care logging + undo)**:
  - Per-target Events stay the data model (no batch entity); all events from one apply share a
    nullable `events.batch_id` UUID.
  - Added [`backend/src/florabase/bulk/care_schemas.py`](../../../backend/src/florabase/bulk/care_schemas.py),
    [`backend/src/florabase/bulk/care_service.py`](../../../backend/src/florabase/bulk/care_service.py),
    and [`backend/src/florabase/bulk/care_api.py`](../../../backend/src/florabase/bulk/care_api.py)
    (included in [`backend/src/florabase/api/router.py`](../../../backend/src/florabase/api/router.py)
    without modifying BULK-001):
    - `POST /api/v1/bulk/care/preview` (`previewBulkCare`): selection `{records: [{kind, id}]}` or
      Location subtree `{location_id, include_sublocations}` (reusing the recursive `UNION` CTE from
      `locations/service.py`), allowed kinds (`watering`, `feeding`, `treatment`, `repotting`,
      `pruning`, `observation`, `other`), max 500 targets, inactive records reported as `skipped`,
      SHA-256 `target_signature`.
    - `POST /api/v1/bulk/care/apply` (`applyBulkCare`): re-resolves and locks targets in UUID order,
      rejects signature mismatch with `409 stale_preview` and empty/all-skipped scopes with
      `422 nothing_to_log`, inserts all per-target Events with one shared `batch_id` in one
      transaction.
    - `DELETE /api/v1/bulk/care/batches/{batch_id}` (`undoBulkCare`): enforces `events.service.delete_event`
      guards per event (photos, linked scheduled activity, operation ownership, harvest ownership)
      plus the edit check (`updated_at == created_at`), deleting eligible events in one transaction
      and listing kept events with structured reasons (`edited`, `has_photos`,
      `linked_to_schedule`, `operation_owned`, `harvest_owned`); returns `404 batch_not_found` for
      unknown batches and `"Undo did not complete. Refresh and try again."` on concurrency errors.
  - Added [`frontend/src/bulk/careApi.ts`](../../../frontend/src/bulk/careApi.ts) and
    [`frontend/src/bulk/BulkCare.tsx`](../../../frontend/src/bulk/BulkCare.tsx); wired `"Log care…"`
    into `BulkToolbar` ([`frontend/src/bulk/BulkLocation.tsx`](../../../frontend/src/bulk/BulkLocation.tsx),
    visible only when every selected item is a Plant or PlantGroup, without touching
    `PlantScreen.tsx`) and `"Log care for everything here…"` into active Location detail
    ([`frontend/src/locations/LocationScreen.tsx`](../../../frontend/src/locations/LocationScreen.tsx)).
  - Regenerated [`backend/openapi.json`](../../../backend/openapi.json) and
    [`frontend/src/api/schema.d.ts`](../../../frontend/src/api/schema.d.ts) (`make api-check` clean).
- **Optional stretch skipped**: global Journal batch collapsing in `GlobalEventsScreen.tsx` /
  `EventFeed.tsx` (would require exposing `batch_id` on `EventResponse` in `events/schemas.py`,
  which was kept untouched per the file boundary).

## Approved scope extensions (Alessandro, 2026-11-25)

Two files outside the original file allowlist were approved for minimal edits so the global Journal
(`#/events`) **Care** filter integrates cleanly with URL state and Saved Views without breaking
existing Saved Views:

- [`frontend/src/saved-views/state.ts`](../../../frontend/src/saved-views/state.ts): added `"care"`
  to the `events.category` union/options/canonical order and raised the list length bound from 3 to 4.
- [`backend/src/florabase/saved_views/state.py`](../../../backend/src/florabase/saved_views/state.py):
  added `"care"` to `EventState.category` `Literal`/canonical order and raised `max_length` from 3
  to 4.

## Migration notes (`20261125_0049_event_care_kinds.py`)

- Revision: `20261125_0049`, linear `down_revision = "20261123_0048"` (`alembic heads` reports one
  head: `20261125_0049`).
- Upgrade: acquires `LOCK TABLE events IN ACCESS EXCLUSIVE MODE`, recreates `ck_events_kind` with
  `'watering'` and `'feeding'`, adds nullable `batch_id uuid`, and creates partial index
  `ix_events_batch_id ON events (batch_id) WHERE batch_id IS NOT NULL`. No backfill.
- Downgrade: acquires `LOCK TABLE events IN ACCESS EXCLUSIVE MODE`, refuses with an explicit
  `RuntimeError` if any `watering` or `feeding` events exist, then drops `ix_events_batch_id`,
  drops `batch_id`, and restores the previous `ck_events_kind` constraint.
- Golden baseline: updated [`scripts/fixtures/golden/scenarios.json`](../../../scripts/fixtures/golden/scenarios.json)
  `schema_revision` (`20261123_0048` → `20261125_0049`), `tables.events.sha256`, and
  `canonical_sha256` for `smoke` (20 event rows) and `comprehensive` (851 event rows); no other
  table digest or row count changed.

## Test evidence

Tested on the frozen `feat/care-bulk-001` branch tip commit (full canonical FULL gate executed via
`make feature-verify AGENT_ID=neon`; see handoff report for the frozen tip commit SHA and receipt):

| Acceptance area | Automated test coverage |
| --- | --- |
| Migration `0049` upgrade with existing events, downgrade refusal when watering/feeding exist, clean downgrade/re-upgrade, single head | `backend/tests/integration/events/test_event_care_migration.py`, `backend/tests/integration/test_event_migration.py`, `backend/tests/integration/test_autogenerate_checks.py` |
| Bulk care schema validation, 500 target cap, disallowed kinds, service preview/apply/undo, API error mapping | `backend/tests/bulk/test_bulk_care.py` |
| Selection preview/apply/undo (3 plants + 1 group, shared `batch_id`, edited event kept), photo-guarded undo (batch of 3 with 1 photo → 2 deleted, 1 kept with `has_photos`), Location subtree with sub-locations & inactive skipping, empty location rejection, stale `target_signature` 409, owner/CSRF guards | `backend/tests/integration/bulk/test_bulk_care_api.py` |
| Watering/feeding informational reversal (`confirmation_required`, not `blocked`) for Sowing-created Plant and PlantGroup-extracted Plant | `backend/tests/integration/bulk/test_bulk_care_api.py` (`test_watering_keeps_sowing_reversal_and_reintegration_confirmation_required`) |
| Single Journal entry with Watering/Feeding & Care filter | `backend/tests/integration/bulk/test_bulk_care_api.py`, `frontend/src/bulk/BulkCare.test.tsx` |
| Saved Views `events` category (`["care"]` + unchanged legacy three categories) | `backend/tests/bulk/test_bulk_care.py`, `frontend/src/bulk/BulkCare.test.tsx`, `backend/tests/test_saved_views.py`, `frontend/src/saved-views/state.test.ts` |
| Frontend toolbar visibility, selection flow, partial undo, Location launcher, dialog states (sub-locations, empty, 409 stale) | `frontend/src/bulk/BulkCare.test.tsx`, `frontend/src/bulk/BulkLocation.test.tsx`, `frontend/src/App.test.tsx` |
| OpenAPI / TypeScript schema drift & feature manifest | `make api-check`, `scripts/check-features.py`, `scripts/check-doc-links.py` |

## Screenshots (uncommitted, attached to handoff)

Captured from the production Vite build in headless Chromium with zero horizontal overflow at both
viewports (kept outside Git per `AGENTS.md`):

- `care-bulk-dialog-desktop.png` (`1280×800`): Location bulk care dialog (`Log care in Greenhouse →
  Bench 2`) with `Include sub-locations` checked, Today preselected, notes, preview summary
  (`Watering on 37 records (31 plants, 6 groups) in Greenhouse → Bench 2 and 2 sub-locations`),
  expanded skipped list, and primary/secondary actions.
- `care-bulk-dialog-phone.png` (`390×844`): Same dialog preview state at phone width with clean
  wrapping and zero horizontal scroll.
- `care-bulk-success-desktop.png` (`1280×800`): Post-apply Location detail showing the inline
  `Logged Watering for 37 records (2 skipped).` notice with **Undo** and **Dismiss**.

## Review remediation (M1, N1 — 2026-11-25)

- **M1**: `undo_bulk_care` now reuses `events.service.delete_event` per unedited batch event in a
  single transaction instead of calling `database.delete()` directly. Events protected by attached
  photos (`has_photos`), a completed scheduled activity (`linked_to_schedule`), an authoritative
  operation (`operation_owned`), or a Harvest record (`harvest_owned`) are kept and listed alongside
  edited events (`edited`), while unguarded events are deleted. Covered by unit tests in
  `backend/tests/bulk/test_bulk_care.py`, PostgreSQL integration test
  `test_bulk_care_undo_keeps_event_with_photo_and_deletes_others` in
  `backend/tests/integration/bulk/test_bulk_care_api.py`, and frontend reason rendering in
  `frontend/src/bulk/BulkCare.test.tsx`.
- **N1**: `DELETE /api/v1/bulk/care/batches/{batch_id}` uses its own concurrency conflict message
  (`"Undo did not complete. Refresh and try again."`), verified in
  `backend/tests/bulk/test_bulk_care.py`.
