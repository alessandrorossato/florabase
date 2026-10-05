# HARVEST-002 — Stored harvested material

HARVEST-002 adds optional current stored material to the historical Harvest capability.
A Harvest records a collected occurrence and owns its HarvestItem lines. Tracking is an
explicit action on one existing line; recording or correcting a Harvest never creates stock.
One line has zero or one `HarvestMaterialInventory`, with a unique restrictive item foreign key.
The inventory retains its item, Harvest and material-kind context through a composite foreign key;
these references cannot be reassigned. `HarvestMaterialDisposition` belongs only to that inventory.

## Quantities and state

Collected quantity and Remaining now are separate facts. Tracking may start below the collected
amount. If both quantities are known, their dimension and unit must match. An exact initial balance
cannot exceed an exact collected amount; approximate values do not create exact ceilings. Unknown
collected quantity permits a separately measured current quantity.

Active stock supports exact, approximate or unknown quantity. Known quantities are positive finite
PostgreSQL NUMERIC values: whole item counts, or weight in mg/g/kg. The API preserves decimal strings;
the UI does no quantity arithmetic. There is no unit conversion or count/weight conversion.
Depleted means no material held and stores no quantity, rather than a fake positive or unknown balance.

Current-state correction explicitly sets active/depleted, quantity and optional storage Location.
It may record a new measurement or reactivate depleted stock. It never recalculates, rewrites or
replays disposition history and is independent of subsequent historical collected-quantity corrections.

## Dispositions

The controlled categories are consumed, processed, discarded, gifted and used_for_propagation.
Each record stores PartialDate (including unknown), notes, created timestamp, mode, the amount used
when known, and typed relational before/after state and quantity snapshots.

| Starting balance | Partial disposition                                                                                | Use all remaining                              |
| ---------------- | -------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| Exact            | Exact compatible positive usage strictly smaller than balance; derive the exact positive remainder | Store that exact balance as used; deplete      |
| Approximate      | Require operator-confirmed compatible approximate remainder; optional compatible usage             | Store the approximate balance as used; deplete |
| Unknown          | Keep remainder unknown; optional independently recorded usage                                      | Keep used quantity unknown; deplete            |

Exact subtraction uses an appropriate Decimal context for the operands, including values beyond
28 digits. PostgreSQL checks independently validate positivity, finiteness, whole counts, units,
PartialDate, allowed transitions and snapshot balance semantics. Snapshots are immutable on update.
There is no disposition update/delete API, generic inventory mutation API, undo, reversal or replay.

Recording a disposition atomically inserts its snapshots and updates current inventory. All five
categories have the same inventory effect. Used for propagation does not create a SeedLot, Plant,
PlantGroup, biological lineage edge or receipt. Discarded does not discard the source Plant.
No disposition creates a source Event or changes source lifecycle, source quantity, source Location,
media ownership or global search.

## Retention and locking

A never-used inventory may be explicitly removed. Once it has a disposition, tracking and history
are retained; current-state correction is the supported remedy. Depleted stock remains protected.
Harvest deletion and item omission/material-kind changes conflict while tracking exists. Historical
labels, descriptions, source, collected quantity and dates may be corrected without recomputing stock.
Retained item IDs survive Harvest correction and resequencing.

All service writes acquire the Harvest owner row first and refresh it, then lock/refresh inventory,
then validate any assigned Location with the existing Location locks. Tracking re-reads the item
under its owner lock. Harvest corrections/deletion use the same owner lock. Unique constraints,
restrictive references and protected source-context triggers complement the application checks.
Transactions serialize competing usage/correction and tracking/source removal without stale ORM
state overwriting the winning result.

## Locations, API and queries

`harvest_inventory` extends the existing Location usage scopes. Existing Locations migrate with
this scope disabled; the operator enables it explicitly. New Location forms offer it alongside
Seed lots, Sowings, Plants and Plant groups. Current storage is independent of source Location.
Scope removal and Location deletion protect active and depleted assignments. Existing hierarchy,
retired ancestors and reparenting rules apply.

Direct usage and descendant-inclusive usage include a fifth inventory count. Total includes depleted
stock, active excludes it. The existing two-query batched Location projection adds inventory to its
canonical-assignment UNION before the recursive hierarchy join; there is no per-Location recursion.

All routes below are under `/api/v1` and use existing authenticated reads and owner-only writes,
including session CSRF and Origin validation:

- `GET /harvest-inventory` with optional Harvest, state, material and Location filters.
- `GET /harvest-inventory/{inventory_id}`.
- `POST /harvest-items/{item_id}/inventory` for explicit tracking.
- `PUT /harvest-inventory/{inventory_id}` for current-state correction.
- `DELETE /harvest-inventory/{inventory_id}` for never-used tracking only.
- `GET /harvest-inventory/{inventory_id}/dispositions` for on-demand history.
- `POST /harvest-inventory/{inventory_id}/dispositions` for atomic usage.

The inventory projection fetches inventory/items with a correlated history-existence flag, reuses
one batched Harvest/source/identity projection and reads the Location tree once when necessary.
Rows do not load full history. A PostgreSQL query-count test covers twelve rows and deep Location
aggregation, with a constant upper bound of ten statements for the combined projections.
OpenAPI is authoritative; `backend/openapi.json` and `frontend/src/api/schema.d.ts` are generated.

## UI and implementation review

Harvests and Stored material are peers within the Harvest workspace. Their workspace navigation
reuses the Geography peer-view button treatment, with `aria-pressed` selection and native Tab,
Enter and Space behavior. `#/harvests` and `#/harvests?tab=stored-material` retain the selected
view across browser Back/Forward and refresh; this is not record-level DetailTabs navigation.

Both directories offer the shared searchable ReferencePicker for Botanical identity, defaulting
to All botanical identities, with a labelled clear action that restores picker focus. Choices
are deduplicated exact identities represented by the current directory's sources. Harvests reuse
the existing `botanical_identity_id` list query and retain all identity choices while narrowed;
identity, local text, Material and Source type filters compose. Stored material derives the exact
identity from its existing inventory/source projection and composes it locally with state,
material, Location and text, without another fetch or history loading. Titles and notes never
establish identity membership. Global-empty and filtered-empty messages remain distinct.
The backend API, schema, generated declarations and domain relationships are unchanged by this UAT
correction.

The Stored material directory starts with active stock. Rows link to the owning Harvest and show
material, source context, remaining amount and storage. Aligned 44px filter controls use compact
four-column Harvest and balanced three-column Stored material desktop grids, two columns on tablet,
and full-width search/identity controls with paired small selectors on mobile.
Harvest detail labels the historical amount Collected and gives each line a separate Stored material
section: Not tracked or Remaining now, explicit tracking, disposition, current correction and guarded
tracking removal. Retained history is fetched only when expanded and shows before/after snapshots.
Native task dialogs retain existing keyboard/focus behavior and expose validation/server conflicts.

Feature Review uses only synthetic data in `florabase-feature-review`, with source binds from this
worktree, at `http://localhost:15174`. It is separate from DEV and Preview. Migration head in Review
is `20261003_0031`. Earlier desktop, tablet and mobile Review observations are recorded in
[engineering progress](progress.md); final-QA browser smoke was unavailable because Review was
stopped.

## Migration and handoff

`20261003_0031_harvest_inventory` follows `20261002_0030`. Upgrade creates the two tables,
constraints/indexes, protected-context triggers and explicit Location scope flag. It does not
backfill inventory or interpret old Harvest Events, attachments or harvested quantities as stock.
The migration test retains a real historical Harvest across upgrade and an empty downgrade/re-upgrade.
Downgrade refuses any inventory/disposition data, and also refuses a Location whose only enabled
scope would disappear. The guard runs before destructive changes under table locks.

HARVEST-002 is verified. Independent final QA and canonical verification are recorded in
[engineering progress](progress.md). Browser smoke for this final QA was unavailable because the
Review frontend/backend were stopped; no browser result is claimed for this phase.

## HARVEST-003 boundary

Active tracked seeds may explicitly create one ordinary SeedLot per conversion. Its
used_for_propagation disposition stays immutable; typed conversion history and cross-links explain
the result. Guarded Undo Seed lot creation may restore before-state and retain a reversed lot,
without exposing general disposition reversal. A source correction counter protects against
intervening stock corrections. See [conversion contract](harvest-seed-conversion.md).
