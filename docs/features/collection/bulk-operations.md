# Safe bulk Location moves — BULK-001

> Summary: Atomic preview-and-apply bulk Location moves across selected collection records (BULK-001).

BULK-001 implements one operator action: select exact current collection records, choose an existing
Location, inspect the server preview, then explicitly Apply. Operator UAT passed; independent final
verification passed. No migration is added; Alembic head remains `20261006_0034`.

## Audited domain matrix

| Record kind                             | Current assignment                     | Single-record path and side effects                                                                                                                                               | Bulk support and eligibility                                                                                                                                      |
| --------------------------------------- | -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SeedLot                                 | `SeedLot.location_id`                  | `seed_lots.service.update_seed_lot`: scope-validated assignment, updated timestamp, no Event; converted producer lineage remains protected                                        | Yes, active only. Shares domain `assign_location`; no origin, quantity, date, lifecycle or producer change                                                        |
| Sowing                                  | `Sowing.location_id`                   | `sowings.service.update_sowing`: scope-validated assignment, updated timestamp, no Event; source and germination invariants remain protected                                      | Yes, active only. Shares domain `assign_location`; no source, seed usage, germination, date or lifecycle change                                                   |
| Plant                                   | `Plant.location_id`                    | Ordinary Edit corrects current state; `events.service.create_event(kind=movement)` records an authoritative move and changes location/timestamp                                   | Yes, active only. Uses Movement Event creation, including extracted Plants without changing protected origin                                                      |
| PlantGroup                              | `PlantGroup.location_id`               | Ordinary Edit corrects current state; authoritative Movement Event changes location/timestamp                                                                                     | Yes, active only. Uses one Movement Event for the group; no extraction, quantity, member or lifecycle change                                                      |
| Stored material                         | `HarvestMaterialInventory.location_id` | `harvests.inventory_service.correct`: Harvest owner → inventory locks, scope validation, current-state correction; location-only correction does not increment correction_version | Yes, active tracked inventory only. Shares domain `assign_location`; preserves balance, state, correction_version, historical collected quantity and dispositions |
| Harvest / HarvestItem                   | Historical occurrence/source context   | Historical correction is not a current physical move                                                                                                                              | No. Stored material is a separate explicit inventory projection                                                                                                   |
| Event                                   | Historical occurrence/destination      | Editing/deleting an Event never replays current state                                                                                                                             | No; destinations are historical evidence                                                                                                                          |
| MediaAsset, BotanicalIdentity, Supplier | No current collection Location meaning | Reference/media semantics                                                                                                                                                         | No                                                                                                                                                                |
| GeographicPlace, ProvenanceSite         | Geographic provenance                  | No physical collection assignment                                                                                                                                                 | No; provenance never implies Location                                                                                                                             |

Inactive, reversed, reintegrated, transferred, completed, lost, discarded, exhausted and depleted
records retain their normal correction/history paths. Bulk movement does not reactivate them. An
active inventory can move independently of an inactive historical source Plant. Movement Events take
the occurrence date chosen in the Move dialog (BULK-002): the dialog asks "When did it happen?" only
when the selection includes Plants or PlantGroups, preselects Today, and also offers Another date or
Date unknown. Apply sends it as optional `occurred_on` (a partial date, same contract as Journal
Events); `null` or an omitted field keeps the Events undated, and execution timestamps never invent
an occurrence date. SeedLots, Sowings and Stored material record no Movement Event, so they take no date. No-op records create no Event and do not advance `updated_at`.

## Explicit transient selection

Seeds, Sowings, unified Plants/PlantGroups and Harvests → Stored material expose **Select**. Historical
Harvests and unrelated directories do not. Checkboxes appear only in selection mode and name each
record. Typed references preserve Plant versus PlantGroup even when IDs happen to be equal.

Normal Select shares the existing utility row with conditional Save view and Saved views. In active
mode, a compact contextual bar immediately before result metadata/list keeps the selected count
prominent and Move to location as its only primary action. Select visible, Clear selection and Done
remain visible lightweight controls. Done exits selection and restores focus to Select. Select visible
targets only the currently rendered eligible directory rows.
These four directories currently render their whole locally filtered list; there is no cross-page
query expansion. If more than **100** eligible rows are rendered, Select visible is disabled with an
explicit limit explanation; individual selection up to 100 or narrower filters remains available.
Nothing is silently truncated. Inactive rows are visibly unselectable.

Search/filter changes, rendered membership changes, detail/task navigation, surface changes,
Back/Forward and Saved View opening clear selection and close its dialog. Reopening the identical
Saved View also clears it through the existing fresh-directory navigation event. Future paging must
participate in this same reset boundary; selection never remains hidden across a page change.
Selection mode, IDs, target and preview never enter a URL, browser storage or Saved View payload.

## Preview and apply API

Both endpoints are authenticated, owner-only POSTs under `/api/v1`, protected by the existing exact
Origin and session CSRF checks. Requests forbid unknown fields, validate UUIDs and finite record-kind
literals, and reject empty, duplicate or over-100 typed selections.

- `POST /bulk/location/preview`: `{records: [{kind, id}], target_location_id}`.
- `POST /bulk/location/apply`: the same exact references with each `expected_updated_at`, plus
  `target_location_id` and `expected_target_updated_at` from the server preview, and optional
  `occurred_on` for the Plant/PlantGroup Movement Events. Preconditions must be timezone-aware
  timestamps.

Preview returns the exact selected count, human labels and kinds, current Location IDs/paths, target
ID/path/version, every record version, per-record move/unchanged/conflict status, counts and
`can_apply`. A missing selected record stays in the result as a conflict. Target Location must exist
and explicitly enable every selected domain's normal usage scope; the Plant scope covers both types.
The picker reuses the normal Location list and ReferencePicker and offers non-retired compatible
Locations. Backend scope eligibility follows the existing Location contract; retirement does not
silently change that contract. There is no bulk clear-Location action.

Preview is informative. Apply independently refreshes and locks the exact records and target,
checks active state and scopes, and compares all persisted versions before any mutation. A changed
record, including an unchanged/no-op selection member, or target version requires re-preview.
Record deletion, wrong concrete type, target deletion, scope changes and lifecycle changes abort the
entire batch. All-no-op batches are refused with `all_unchanged`; mixed batches move only changed
records while retaining the no-ops in validation and confirmation.

Apply acquires the existing lineage advisory lock before aggregate locks, Harvest owners in UUID
order for inventory, and typed record rows in a fixed kind/UUID order. It refreshes ORM objects under
locks. Inventory keeps its owner-first contract. Domain services perform the final assignments or
Movement Event creation inside one transaction. The route commits once and rolls back on domain,
constraint or concurrency failure, including failure after an earlier Movement Event was inserted.
No record or history survives a failed batch. PostgreSQL deadlock/serialization errors produce a
safe concurrency conflict requiring refresh, without database internals.

Malformed/unsupported kinds, malformed UUIDs, extra fields, empty/oversized batches and duplicate
references use normal structured 422 validation. Missing target uses 404 `target_location_not_found`.
Preview row conflicts use `record_not_found`, `record_not_active` or `location_scope_not_supported`.
Apply conflicts use 409 `selection_conflict`, `stale_preview`, `all_unchanged`, existing domain codes,
or `concurrent_change`, with bounded affected-row details where available. No failed ID is silently
omitted. Apply never expands a filter or accepts an action registry, arbitrary model or field map.

## Product flow and queries

Move opens the existing native TaskDialog focus trap. Choose Location → Preview move → inspect the
exact rows and no-ops/conflicts → Apply move is explicit. Target changes invalidate the preview.
Failed applies invalidate it and explain re-preview; successful apply closes the dialog, clears
selection/Quick Preview, refreshes the directory and reports moved/already-there counts while
preserving filters and Saved View URL state. Dialog Cancel, Escape and a direct backdrop click
close without applying and return focus to the exact Move trigger; inside clicks retain the dialog.
Apply-in-flight cannot be dismissed while its transaction outcome is pending. The Move dialog is
moderately wider, with more vertical chooser space and bounded viewport height. Mobile controls
wrap and the preview scrolls within the dialog; long names wrap.

Record lookup is batched per selected kind, with no per-record reference/provenance projections.
Preview reads the Location tree once. SeedLot, Sowing and inventory assignment loops do not refetch
unrelated references; Plant/Group writes deliberately retain the existing per-record Event service.
The maximum is 100 and all preview/error rows are bounded accordingly. Query regression evidence is
recorded in [the handoff](../../archive/BULK-001/bulk-001-handoff.md); there is no caching or background processing.

## Safe bulk care logging — CARE-BULK-001 (with FN-03)

CARE-BULK-001 adds one-action care logging for many Plants and PlantGroups at once, together with
the `watering` and `feeding` Journal kinds (`FN-03`, migration `20261125_0049_event_care_kinds.py`).
Per-target Events stay the data model: no batch entity is introduced. Every Event created by one
bulk care apply shares a generated `batch_id` (`events.batch_id uuid NULL`, indexed partially via
`ix_events_batch_id WHERE batch_id IS NOT NULL`).

### Scope and allowed kinds

- **Eligible targets**: active Plants and active PlantGroups only. Inactive records (dead, lost,
  discarded, transferred, reintegrated) are reported as `skipped` with an explicit reason and never
  receive an Event.
- **Target sources**:
  - Explicit transient selection from the Plants/PlantGroups directory (`BulkToolbar` → **Log
    care…**, visible only when every selected record is a Plant or PlantGroup).
  - Location detail (`Log care for everything here…` on active Locations), optionally including
    descendant sub-locations (`include_sublocations`, default on, reusing the Location containment
    CTE).
- **Allowed kinds**: `watering`, `feeding`, `treatment`, `repotting`, `pruning`, `observation`,
  `other`. State-changing, structured, operation, or terminal kinds (`movement`, `measurement`,
  phenology stages, `harvest`, `extraction`, `reintegration`, `transfer`, `death`, `loss`,
  `discarded`) are rejected. Notes carry free-text product/dose details (no structured care payload).
- **Cap**: maximum **500** targets per preview/apply (`422 too_many_targets`).

### Preview, apply, and undo API

All three endpoints live under `/api/v1/bulk/care` and require owner authentication plus exact
Origin and session CSRF checks (same contract as bulk moves):

- `POST /api/v1/bulk/care/preview` (`previewBulkCare`): accepts either
  `{records: [{kind, id}]}` or `{location_id, include_sublocations}`, plus `kind`, optional partial
  `occurred_on`, and optional `notes`. Returns per-target rows (`log` or `skipped` with reason),
  plant/group/sub-location counts, `can_apply`, and a SHA-256 `target_signature` over the sorted
  resolved target IDs and their `updated_at` timestamps.
- `POST /api/v1/bulk/care/apply` (`applyBulkCare`): accepts the same target/event fields plus
  `target_signature`. Re-resolves and locks targets in deterministic UUID order (and subtree
  locations when targeting a Location), recomputes the signature, rejects mismatches with `409
  stale_preview`, rejects empty/all-skipped sets with `422 nothing_to_log`, and creates all
  per-target Events with one shared `batch_id` in a single atomic transaction.
- `DELETE /api/v1/bulk/care/batches/{batch_id}` (`undoBulkCare`): enforces the same per-event
  deletion guards as `events.service.delete_event` (attached photos, linked scheduled activity,
  operation ownership, harvest ownership) in addition to the edit check (`updated_at ==
  created_at`). Eligible events are deleted in one transaction; kept events are returned in `kept`
  with an explicit structured reason (`edited`, `has_photos`, `linked_to_schedule`,
  `operation_owned`, or `harvest_owned`) alongside `deleted_count` and `kept_count`. Missing
  batches return `404 batch_not_found`, and unexpected concurrency conflicts return `409` with
  `"Undo did not complete. Refresh and try again."`.

### Product flow

The dialog preselects Today (with the existing partial/unknown date controls from `FN-05`), accepts
notes, previews the exact summary (for example,
`"Watering on 37 records (31 plants, 6 groups) in Greenhouse → Bench 2 and 2 sub-locations"` with
skipped records listed), and requires explicit confirmation before apply. On success, an inline
notice exposes **Undo** for the batch and reports any edited Events kept if the batch was partially
edited before undo.

## Navigation and later work

Desktop and conceptual mobile order: Overview (Dashboard); Collection (Seeds, Sowings, Plants,
Harvests, Media); Activity (Events); Places (Locations, Geography, Provenance map); Reference
(Botanical identities, Suppliers); Tools (Import / Export, Labels). Page eyebrows match these
macroareas without changing page titles, descriptions, routes or record-level captions.

No Bulk page, persistence, migration, batch job, queue, scheduler, audit engine, unified history,
bulk delete/status/quantity/identity/provenance/media/labels/import/disposition/conversion action is
introduced. Justified unified operational history remains the next Collection productivity v2 topic,
with Orders/Purchases later. SCHEDULE-001 is only a later candidate for explicit future activities;
its schedule/completion/historical Event relationship remains open. Existing Events are facts that
happened. BOTANY-003 remains unchanged and blocked.
