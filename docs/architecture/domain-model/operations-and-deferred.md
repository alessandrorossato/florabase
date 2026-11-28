# Domain model — Operations and deferred capabilities

> Summary: Propagation reversal, harvests and seed conversion, global search, saved views, bulk location moves, operational history, orders, and schedule.

## Deferred capabilities

Richer structured Event payloads, Order lines/general purchasing, other propagation
material, analytical dashboards, PWA installability, enrichment,
taxonomy reconciliation, deeper Supplier analytics, reminders, weather, and multi-user ownership
remain planned. `docs/features.json` is the detailed source for dependencies and acceptance criteria.

### Propagation reversal

The three focused reversals are SeedLot → Sowing, Sowing → Plant, and Sowing → PlantGroup.
One action compensates one receipt in one transaction. Source lifecycle and SeedLot quantity return
to the immutable BEFORE snapshot; no inverse arithmetic or unit conversion occurs. Sowing
transitions restore only their captured lifecycle; quantity is checked, and the independent
`germinated_count` is never rewritten.

New propagation receipts capture version-1 typed relational result snapshots on their original
INSERT: lifecycle, quantity kind/value/unit/approximation, BotanicalIdentity where applicable,
Location, and partial sowing/collection-entry date. Source IDs and result IDs prove the origin;
source Location and Sowing's SeedLot plus source quantity guard later corrections. Original facts
remain immutable under the existing database trigger. Labels, notes, cultivation descriptions,
and germinated counts are informational; they do not themselves block reversal and are retained.
There is no JSON snapshot, generic receipt CRUD, reconstruction, or event-sourcing framework.

Eligibility is `safe`, `confirmation_required`, or `blocked`. Current source and result state must
match their expected snapshots. Later applied operations sharing the source require newest-first
reversal, even when they did not change its lifecycle or quantity. Applied downstream operations,
uncompensated lineage, produced SeedLots, transfer, terminal state, structural corrections, and
non-informational Events block reversal. Observation, flowering, and fruiting Events on Plants and
PlantGroups are the narrow explicit-confirmation category; they remain attached. Sowings have no
such journal Events. Confirmation never overrides a structural blocker.

Causal ordering is downstream-first, without cascading. Reversed propagation receipts with reversed
results, and reintegrated extraction receipts with reintegrated Plants, are historical rather than
active dependencies. Their lineage and operation-owned historical Events remain stored.

Results retain their UUID, notes, history, and lineage permanently with lifecycle `reversed`.
This differs from `reintegrated`, which identifies an extracted Plant returned to its original group.
Reversed results remain readable through detail and All/history views, but do not contribute to
active holdings or propagation material totals. They cannot be reactivated through correction,
acquire a new origin, create descendants, produce new SeedLots, transfer, extract, or receive
current-state Events. A repeated forward transition creates a distinct new result and receipt.
Propagation reversal emits no journal Event and never deletes lineage or results.

Lock order follows receipt → SeedLot → Sowing → PlantGroup → Plant where applicable; a reversal
locks only its own receipt and affected source/result rows. Forward descendant and producer creation
also lock their source, Event operations lock their target, and correction validates refreshed locked
rows. Competing duplicate reversals serialize and the loser gets an explicit conflict. Transaction
failure rolls back source, result, and receipt together. Expected-state reads are advisory until the
mutation repeats all validation under locks.

Migration `20260907_0018` adds nullable typed snapshot fields and the three `reversed` lifecycles.
It does not backfill. Downgrade refuses while new snapshot or reversal history exists, rather than
discard immutable evidence; an empty disposable database supports the full downgrade/re-upgrade cycle.

### Harvest and HarvestItem (HARVEST-001)

A Harvest records one historical collection occurrence from exactly one retained Plant or PlantGroup,
with one or more ordered material lines, partial date, optional label/notes and one explicit owned
harvest Event. BotanicalIdentity derives through the source; Harvest has no storage Location or stock.
Each item records controlled material, optional description and an exact/approximate positive whole
item count or decimal weight (mg/g/kg), or honest absence. Aggregate create/correct/delete keeps the
owned Event coherent atomically. Source correction is allowed; referenced source hard deletion is
restricted. Existing free-form harvest Events remain independent. Neither Harvest nor seed-material
lines change lifecycle, PlantGroup count, Location or SeedLot inventory. Harvest media and explicit
primary use the shared library and central safe visual resolver. See [Harvest contract](../../features/collection/harvests.md).

### Stored Harvest material (HARVEST-002)

An explicit Track stored material action creates zero or one HarvestMaterialInventory per material
line. The collected HarvestItem quantity stays historical; the independently confirmed balance means
remaining now. Existing Harvests receive no inventory. The current row is authoritative: positive exact
or approximate count/weight (mg/g/kg), or unknown, with `active` state; `depleted` stores no remaining
quantity and means no material held. Current corrections can reactivate or remeasure without history
replay. Initial numeric tracking must match a known collected dimension/unit, without conversions;
exact current quantity cannot exceed a directly comparable exact collected quantity.

Inventory retains item/Harvest/material-kind context using a restrictive composite foreign key.
BotanicalIdentity/source names and lifecycle derive through Harvest. Source/date/notes/label/collected
quantity corrections never recalculate stock. Tracked lines retain their UUID and material kind;
Harvest/line deletion is blocked until eligible never-used tracking is explicitly removed. Any
disposition permanently blocks ordinary tracking removal. Inactive biological sources remain valid.

HarvestMaterialDisposition records consumed, processed, discarded, gifted or used_for_propagation,
explicit partial/use-all mode, optional PartialDate, amount when known, immutable typed before/after
quantity/state, notes and UTC creation time. Exact partial usage requires a compatible exact amount
strictly smaller than stock and derives a positive remainder without decimal rounding. Approximate
partial usage requires a compatible operator-confirmed approximate remainder. Unknown stays unknown,
even when an amount used is recorded. Explicit use-all depletes and preserves prior precision.
Neither ordinary disposition CRUD nor undo/reversal is exposed; correcting current stock retains facts.

Storage uses the shared Location hierarchy and explicit `harvest_inventory` eligibility scope.
Existing Locations receive that flag disabled; operators can enable it. Active current counts exclude
depleted rows, while totals retain them. One set-based query computes direct/inclusive usage. The
Harvest workspace has a Stored material peer directory and a distinct detail section with focused
dialogs and on-demand disposition history. No separate media ownership, global-search extension,
Plant/PlantGroup Event/lifecycle mutation or lineage node exists. Explicit Harvest seed → SeedLot
conversion is the separate HARVEST-003 capability. See [inventory contract](../../features/collection/harvest-inventory.md).

### Harvest seed conversion (HARVEST-003)

Explicit active managed seed stock creates a collection-produced SeedLot through one atomic
used_for_propagation disposition and typed HarvestSeedLotConversion. Producer/source origin is
protected; identity remains correctable. Guarded reversal restores captured stock while safe,
retains all evidence/lineage and keeps the resulting SeedLot historically as `reversed`. This
lifecycle excludes current holdings and new propagation. Standalone dispositions have no undo.
See [conversion contract](../../features/collection/harvest-seed-conversion.md) for snapshots, dependencies and locks.

## Global search coverage (SEARCH-002)

Dashboard global search exposes Harvest and MediaAsset as separate typed hits alongside SEARCH-001.
Harvest identity derives from its exact Plant/PlantGroup source and year derives from its occurrence
PartialDate. Label/current derived title, source identity names, notes and material kind/description
are searchable; current source Location, lifecycle, Supplier or provenance never become Harvest
relationships. Multiple material lines produce one hit. Harvest and its owned Event may independently
match; history is not suppressed.

MediaAsset search reuses the Library's direct title, original filename and attribution predicate.
Links, primary designations and identity covers do not infer text matches or duplicate results.
Search is compact text navigation to existing authenticated Harvest and exact Media details, with
no image/external fetching. See [search semantics](../../features/tools/search.md). No persistence or migration is added.

## Saved operator views

VIEW-001 adds owner-private `SavedView` records with UUIDv7 identity, User owner, trimmed Unicode
name (120 characters), finite surface, explicit state version 1, validated canonical JSONB state and
UTC creation/update timestamps. Names are case-insensitively unique per owner and surface. These
are shortcuts to existing live queries, with no saved results, record ownership changes or new
filters. Exact stale filter UUIDs remain present; unsupported versions stay manageable without
being silently reinterpreted. Rename changes only the name, Update with current view explicitly
replaces state, and deletion removes only the shortcut. See [surface contracts](../../features/tools/saved-views.md).

## Safe explicit bulk Location moves (BULK-001)

[Bulk operations](../../features/collection/bulk-operations.md) documents the audited support matrix. Active SeedLots,
Sowings, Plants, PlantGroups and managed Stored material can move to one existing scope-compatible
Location through an explicit server preview and atomic revalidated apply. The bounded selection
contains exact typed IDs, never an expanded filter, and is transient outside Saved Views.
`updated_at` preconditions on every record and the target prevent stale overwrites; any conflict
changes zero records. No-op records keep their timestamp/history. SeedLot/Sowing assignment reuses
ordinary editing primitives without changing origins, balances or lifecycle. Inventory location-only
correction preserves its owner-first locks, disposition history and correction version. Plants and
groups use authoritative Movement Event creation with an unknown occurrence date and one Event per
changed record. Historical Harvest occurrences, inactive records, Event destinations, geography,
reference and media are not bulk-movable. BULK-001 adds no migration or history store.

### Unified operational history (HISTORY-001)

History projects existing Events, propagation OperationReceipts without Events, GerminationObservations,
structured Harvests, material dispositions and seed conversions. It stores no new historical facts.
Owned Harvest Events, Event-backed receipts and conversion-owned dispositions are suppressed in this
projection only. Corrections change the same typed entry; deleting an ordinary Event removes it.
PartialDate remains precise only to its stored level. Durable facts without occurrence dates use an
explicit Recorded timestamp. Receipt status supports a Reversed badge without inventing a reversal
time; conversion reversed_at supports a distinct reversal occurrence. Current lifecycle, Location,
stock, Supplier, provenance and updated_at never manufacture missing history. One SQL statement
filters, counts and globally paginates normalized candidates with joined labels and bounded typed
references. History v1 Saved Views persist filters; migration 0035 extends only their surface
constraint and refuses populated History-view downgrade. See [operational history](../../features/activity/operational-history.md).

### Purchase Orders (ORDER-001)

[Orders](../../features/sourcing/orders.md) records a purchase transaction separately from Supplier and physical SeedLot.
UUIDv7/UTC records have optional Supplier, PartialDate `ordered_on`, non-unique normalized reference,
exact non-negative Numeric total with a paired uppercase currency, and bounded notes. Zero is known
zero; null is unknown. Amounts travel as decimal strings without rounding, allocation or FX.

SeedLots may explicitly link one Order only for purchased/purchased-fruit sources. Known Supplier
IDs must agree on both edit paths; null knowledge remains absent. Order row locks serialize these
checks. Both link directions and new-lot creation use one purchase reconciliation contract. Apply
checks Order/SeedLot versions and atomically confirms source, Supplier and optional precision-preserving
date copy; stale conflicts apply nothing. Linked lots remain physically independent with no changes
to quantities, lifecycle, material origin, Location or lineage. Unlink does not roll back confirmed
acquisition facts. Order total remains read-only transaction context, without per-lot pricing. Retired Suppliers retain existing links;
referenced Orders cannot be deleted. Migration 0036 preserves existing unlinked lots and refuses a
populated downgrade. Orders adds bounded REST/detail/directory, Saved Views and direct Global Search;
it does not expand History or purchasing to Plants/general inventory.

## Scheduled collection activities — SCHEDULE-001

ScheduledActivity is an explicit future intention with a concrete `due_on` day, bounded kind,
title/notes, optional exact Identity/SeedLot/Sowing/Plant/PlantGroup/Location reference and version.
It remains a planning record when completed or cancelled. `overdue` derives from planned status
and a due day before the displayed current calendar day. Overdue does not mean occurred; completed
Schedule does not necessarily mean Event. No background mutation, recurrence or delivery exists.

References are restrictive and retained in all statuses. Lifecycle changes preserve links and show
the current target lifecycle; existing intentions can be edited/rescheduled/closed after retirement.
New work requires a current target. Hard deletion cannot orphan retained planning evidence.
Completion without Event is always possible. Explicit compatible Plant/PlantGroup Events are created
with actual full occurrence day through the existing Event service, in the same transaction. Exact
completion retry returns the same durable link; changed completion details and stale writes conflict.
See [Schedule contract](../../features/activity/schedule.md) for dates, supported kinds and lifecycle policy.
