# Domain model — Collection concepts

> Summary: SeedLot, Sowing, vegetative propagation and transitions, operation receipts, Plant, PlantGroup, lookup labels, and Event.

## Collection concepts

### SeedLot

A SeedLot is one physically managed packet, bag, or lot of seeds. Identical packets remain separate
records. BotanicalIdentity is required; label, Supplier, material provenance, collection Location,
notes, dates, and a purchase Order link are optional.

Acquisition, harvest, and expected-viability dates retain year, month, or day precision. Quantity may
be an exact or approximate whole seed count or weight in grams/milligrams. Unknown quantity is valid;
exact zero is valid only for an exhausted lot. Lifecycle is active, exhausted, discarded, or lost.
Sowing does not silently deduct the SeedLot quantity.

Source kind is purchased, purchased fruit, self-collected, collection-produced, gift/exchange,
other, or unknown. Only `other` accepts short source detail. A collection-produced lot may identify
one Plant or one PlantGroup producer; the producer is optional because historical knowledge can be
unknown. Non-collection-produced lots cannot carry a producer.

Only purchased or purchased-fruit lots may explicitly link one [Order](../../features/sourcing/orders.md). When both
Supplier IDs are known they must match; null knowledge remains absent. Acquisition edit supports
link/unlink/relink through the shared purchase-context preview also used from Order detail. Unknown
source proposes Purchased; known compatible sources retain their exact kind, and incompatible sources require
an explicit saved correction. Known Supplier replacement requires confirmation; unknown Order Supplier
preserves lot knowledge. Acquisition date may be copied with explicit confirmation, retaining its
PartialDate precision; purchase date and receipt date remain distinct. Order total is read-only
transaction context, never a lot price. Unlink retains all confirmed acquisition values.
Creating from Order prefills only purchase context, leaving identity, quantity, harvest date,
provenance and Location for explicit entry, and acquisition date as an optional confirmed copy. Separate physical packets always remain separate records.

### Sowing

A Sowing is one managed attempt using exactly one SeedLot. Botanical identity is obtained from that
required origin rather than copied onto the Sowing. Optional facts include label, precision-preserved
sowing date, quantity sown, germinated count, current Location, substrate, method/container,
pretreatment, temperature bounds, environment, and notes. Lifecycle is active, completed, failed, or
abandoned.

Quantity may be an exact or approximate positive whole seed count or positive weight. Germinated
count is a non-negative operator-maintained total and cannot exceed an exact seed-count denominator.
It stays independent of optional dated observations: neither total updates the other. Each observation
records an exact calendar date and non-negative count of **new** germinations, including zero for a
check with no new germinations. One observation per Sowing per day may be corrected or removed.
The chronological cumulative total is derived, never entered or persisted. When the Sowing has an
exact seed count, this cumulative total cannot exceed that count; Sowing quantity edits preserve the
same bound. Exact Sowing dates cannot follow existing observations. Partial or unknown Sowing dates
retain observations without invented timing.

The dated summary derives first germination from the earliest positive observation and reports days
to first only with an exact Sowing date. Percentage is observed cumulative germination divided by
the exact number of seeds sown, times 100; approximate, weight, and unknown quantities have no
percentage. Florabase 0.1.0 defines T50 as elapsed days from exact sowing to reaching half of the
**exact seeds sown**, including a fractional threshold for odd counts. Between points it linearly
interpolates: previous day + (next day - previous day) × (half the seeds - previous cumulative) /
(next cumulative - previous cumulative). The exact sowing day with cumulative zero is the initial
point where useful. T50 is unavailable without dated observations, an exact Sowing date and count,
or a reached 50% threshold. Decimal results are derived estimates, not measurement precision.
Observations do not create Events, change lifecycle or descendants, or replay propagation.

### Vegetative propagation

Vegetative lots retain the identity, acquisition or taking date, material type, mother or external
source, and original and remaining count of stem, leaf or root cuttings. Rooting attempts retain
their own starting count, recorded rooted count, cultivation setup and dated rooting checks. A
recorded zero and an unknown count remain distinct. Failed and abandoned attempts remain readable.
The [cuttings contract](../../features/collection/cuttings.md) describes stock use, clonal lineage and reversal. The
[architecture decision](../../archive/CUTTING-001/cutting-001-design.md) records the alternatives and implementation differences.

### Explicit propagation transitions

Propagation operations are forward data-entry assistance, not inventory accounting, event sourcing,
or an irreversible workflow engine. Ordinary SeedLot, Sowing, Plant, and PlantGroup creation and
correction APIs remain valid. Executing an explicit transition applies its requested effects once;
later edits do not replay, reverse, or recalculate an earlier source remainder, descendant lineage,
or Sowing lifecycle decision.

SeedLot-to-Sowing supports no source adjustment, partial use, and explicit use-all. No adjustment
leaves the SeedLot untouched. Partial use of an exact quantity requires an exact Sowing quantity in
the same dimension and unit; the locked source row is authoritatively subtracted, oversubscription is
rejected, and an exact zero remainder exhausts the lot. Partial use of an approximate source requires
the operator to submit a confirmed resulting approximate quantity in the same dimension and unit.
A UI may propose an estimated remainder, but the persisted estimate is explicitly confirmable and
editable rather than silent arithmetic. Partial use of an unknown source leaves it unknown. Use-all
marks any active source exhausted; exact material becomes exact zero, while approximate or unknown
material keeps its honest quantity semantics and no exact zero is invented. Count and weight are
never mixed, and the existing `g` and `mg` units must match because Florabase has no established
cross-unit conversion rule.

Sowing-to-Plant and Sowing-to-PlantGroup operations create explicit Sowing lineage and apply the
operator-selected resulting Sowing lifecycle atomically under a row lock. The existing vocabulary
remains active, completed, failed, or abandoned; there is no partially-completed state, and creating
a descendant never completes a Sowing automatically. `germinated_count` remains an independent
operator-entered current observation and is neither rewritten nor required to equal materialized
descendants.

Batch pot-on (`PROPAGATION-BATCH-001`) extends this workflow to create 1–200 individual Plants from
an active Sowing (or split 1–200 individual Plants from an active PlantGroup) in one database
transaction without introducing a new receipt kind or grouping identifier. For a Sowing batch, the
Sowing row is locked once, optimistic concurrency rejects a stale `expected_sowing_updated_at`
snapshot (`stale_preview`), and one existing `SOWING_TO_PLANT` receipt is written per created Plant.
Iterations 1 through N−1 leave the Sowing lifecycle unchanged (`before_lifecycle == after_lifecycle`);
only the Nth iteration applies `resulting_sowing_lifecycle`. Reversal therefore remains
`REVERSAL-001` newest-first per source: reversing the newest created Plant restores the Sowing's
prior lifecycle, and reversing every created Plant newest-first returns the Sowing (and, once
reversed, its SeedLot) to the original state. There is no whole-batch reversal operation.
`germinated_count` remains an advisory UI hint and is never enforced as a backend cap. For an active
PlantGroup batch split, the locked group loops the existing single-Plant extraction (one extraction
Event and one `PLANT_GROUP_EXTRACTION` receipt per Plant), capping exact-quantity groups at their
current exact count while allowing approximate or unknown groups up to 200 without modifying group
quantity; `PLANT-006` newest-first reintegration remains unchanged. Any failure mid-batch rolls back
the entire transaction.

The protected Sowing propagation summary derives descendants only from stored immediate Sowing and
PlantGroup-extraction links. Every Plant with that explicit ancestry contributes exactly one tracked
individual. An exact PlantGroup contributes its current exact quantity; approximate and unknown
PlantGroups are reported separately and never converted to exact individuals. This keeps extraction
accounting coherent without a counter. Matching BotanicalIdentity values do not imply lineage.
Propagation transitions do not automatically create Events, and no propagation-history table or
redundant counter is persisted. PlantGroup extraction is the narrow exception: its authoritative
operation records an extraction Event with a structured resulting-Plant link without adding a
second lineage model.

### Reversible authoritative-operation receipts

`REVERSAL-001` introduces a deliberately small operation-receipt boundary, not event sourcing.
Every newly executed SeedLot-to-Sowing, Sowing-to-Plant, Sowing-to-PlantGroup, PlantGroup extraction,
Plant transfer, or PlantGroup transfer operation creates one receipt in the same transaction. The
receipt has a UUIDv7 identity, UTC creation timestamp, controlled kind and status, explicit foreign
keys for its source/result records and operation-owned Event where applicable, adjustment mode where
applicable, and typed lifecycle and quantity state before and expected after the operation. There is
no generic JSON payload or public receipt CRUD API.

The relational shape is closed by database checks for each supported kind. Quantity snapshots store
kind/dimension, value, unit, and exact/approximate state; all four fields are absent for unknown.
Original receipt facts are database-immutable, while the separate status may later move from applied
to reversed through a purpose-specific undo operation. Aggregate rows remain the only current-state
authority. Corrections made after an operation update those aggregates without modifying the
receipt, deliberately leaving a detectable difference from its expected after-state.

The migration does not backfill historical operations: their before-state is no longer safely
reconstructable. Existing Sowings, lineage, transfer Events, and extraction Events remain valid but
receive no fabricated receipt. `PLANT-006` uses only recorded PlantGroup-extraction receipts;
`PROPAGATION-003` uses only complete version-1 propagation receipts. Older propagation receipts
remain readable but return `legacy_receipt_missing_result_snapshot`; no current record is used to
backfill missing historical facts.

This makes the numerical contract explicit. Exact compatible values are restored exactly, including
`100 → 80 → 100` for a consumed SeedLot and `10 → 9 → 10` for an extracted PlantGroup. Approximate
and unknown values are restored only from the recorded before-state: an operator-confirmed
`~100 → ~80` returns to recorded `~100`, and unknown returns to unknown. No inverse may derive an
estimate, change count into weight, or convert `g` and `mg` without a separately approved conversion
contract. The receipt also restores lifecycle snapshots, including use-all exhaustion and any future
transfer predecessor, rather than inferring them from the currently visible Event.

The inverse must lock every affected aggregate and verify deterministic dependency guards. It is
safe automatically only when the receipt is still applied, the recorded post-state still matches,
and no later dependent operation, correction, state-changing Event, or lineage has touched the
operation's scope. A later non-state-changing observation can be a confirmation-required retained
fact only where the operation contract explicitly says it remains truthful. Later lifecycle,
Location, identity, quantity, transfer, or extraction changes; later Sowing/Plant/PlantGroup work;
produced SeedLots; and descendants block undo until the dependent action is resolved. Neither
confirmation nor Event deletion may override a database or numerical invariant.

`PLANT-006` compensates only the recorded extraction of a Plant back into its immutable originating
PlantGroup, never arbitrary group membership. Eligibility is proven by the applied extraction
receipt and is safe, confirmation-required, or blocked. Retainable observation, watering, feeding,
flowering, and fruiting Events require confirmation and remain on the historical Plant; lifecycle,
identity, Location, transfer, produced SeedLot, lineage, later group operation, or source-group
snapshot changes block restoration rather than being overwritten.

Successful reintegration restores the receipt's exact captured PlantGroup before-state, including
lifecycle and exact, approximate, or unknown count representation, without inverse arithmetic. The
Plant remains permanently readable with its origin, lineage, notes, and Events but moves to the
non-active `reintegrated` lifecycle and cannot be reused by a future extraction. One new
group-targeted reintegration Event structurally links that Plant; there is no duplicate Plant Event.
The original extraction Event and immutable receipt facts remain, while the receipt status becomes
reversed. A later extraction creates a distinct new Plant.

### Plant

A Plant is exactly one individually tracked specimen and never has quantity. It requires its own
BotanicalIdentity and may have a label, precision-preserved collection-entry date, current Location,
notes, and active, reintegrated, transferred, dead, lost, or discarded lifecycle. Transferred means
the living specimen left the currently held collection. Reintegrated means a recorded extracted
individual was returned to its original PlantGroup and is no longer separately active. Both retain
their historical record, last Location, provenance, lineage, labels, notes, and Events.

Its immediate origin is exactly one of:

- an originating Sowing;
- an originating PlantGroup created by extraction; or
- direct origin using purchased, gift/exchange, collection-produced, other, or unknown, with
  optional Supplier and material provenance where allowed.

BotanicalIdentity and Location remain correctable after creation. Ordinary Plant editing cannot
detach or replace an extraction origin.

### PlantGroup

A PlantGroup represents multiple individuals of one BotanicalIdentity intentionally managed as one
record. It shares Plant's optional label, collection-entry date, Location, notes, Sowing-or-direct
origin, and provenance fields. Lifecycle is active, transferred, completed, dead, lost, or
discarded. Transfer always applies to the entire managed group and preserves its historical
quantity. To transfer one individual, the operator first extracts it as a Plant and then transfers
that Plant; direct partial-group transfer and decrement-on-transfer do not exist.

Quantity is unknown or an exact/approximate whole count. Zero is allowed only as exact historical
quantity for completed, dead, or discarded groups. A dedicated active-group extraction transaction
creates one Plant with the group as immutable immediate origin. Exact quantities decrement; the last
exact member completes the group. Approximate and unknown quantities remain unchanged because
subtracting one would imply false precision. The same transaction creates an extraction Event on
the source PlantGroup with a restrictive structured reference to the resulting Plant.

### Physical lookup labels

LABEL-001 derives temporary physical lookup labels from existing SeedLot, Plant, and PlantGroup
responses. BotanicalIdentity display text and the record's optional label remain owned by their
existing capabilities. The fixed A4 / 50 × 30 mm composer creates no domain entity, identifier,
database copy, or print job. QR codes carry only stable existing record URLs and retain normal
authorization. Sowing, Event, BotanicalIdentity, and reference records are not label targets. See
[labels.md](../../features/collection/labels.md).

### Event

An Event is an explicitly recorded historical occurrence for exactly one Plant or PlantGroup. It
has a UUIDv7 identity, a controlled kind, an optional year/month/day-precision occurrence date,
optional notes, an optional nullable `batch_id` linking per-target Events created by one bulk care
operation (no separate batch entity), and exact UTC creation/update timestamps. The controlled
vocabulary is observation, watering, feeding, movement, repotting, flowering, fruiting, pruning,
treatment, harvest, extraction, transfer, death, loss, discarded, reintegration, measurement, and
other. Watering and feeding (`FN-03`) are non-state-changing care kinds usable on both single
Journal entries and bulk care operations (`CARE-BULK-001`), and count as informational retainable
events for propagation reversal and PlantGroup reintegration (confirmation-required rather than
blocking). Undoing a bulk care batch (`DELETE /api/v1/bulk/care/batches/{batch_id}`) enforces the same
per-event deletion guards as single Event deletion (attached photos, linked scheduled activities,
operation ownership, harvest ownership) and deletes only unedited, unguarded events in the batch
(`updated_at == created_at`); kept events are listed with their structured reason (`edited`,
`has_photos`, `linked_to_schedule`, `operation_owned`, or `harvest_owned`). Collection observations
remain separate from BotanicalProfile reference knowledge.

A measurement Event (MEASUREMENT-001) records one Plant height as an exact positive decimal with its
recorded unit (`mm`, `cm` or `m`), an approximation flag and a required PartialDate. It never
changes current state, is refused for PlantGroups, and counts as a retainable observation.
Corrections keep each replaced value in an append-only correction trail. See
[measurements](../../features/activity/measurements.md).

A phenology observation (PHENOLOGY-001) is an observation, flowering or fruiting Event with an
optional controlled phenological stage (for example bud break, flowering onset, fruit ripening or
dormancy entry, each tied to its kind) and an approximate-date flag. It never changes current state,
keeps PartialDate precision or an unknown date, may repeat within a season, and is a retainable
observation. Stage-less flowering and fruiting Events remain valid. Absence of a recorded stage
never means the stage did not occur. See [phenology](../../features/activity/phenology.md).

Movement additionally requires one destination Location. Creating a movement Event atomically
updates the target's current Location. Creating death, loss, or discarded Events atomically updates
the target's lifecycle to dead, lost, or discarded, subject to the existing PlantGroup quantity and
lifecycle invariant. A focused transfer action locks a Plant or PlantGroup and atomically creates a
transfer Event and sets lifecycle to transferred. Transfer may carry a partial occurrence date,
optional free-text recipient, and notes; recipient is not a Supplier, Location, or GeographicPlace.
Target rows are locked for these state-changing transactions. Events remain
usable for inactive targets, and restrictive foreign keys preserve history when targets or movement
destinations are referenced.

Florabase is not event-sourced. The Plant or PlantGroup row is authoritative current state, and only
initial Event creation applies a side effect. Correcting an Event's kind, partial date, notes,
movement destination, recipient, or extraction result changes history only; editing or deleting an
Event never replays, reverses, or recomputes current Location, lifecycle, quantity, lineage, or
resulting Plant. Ordinary Plant/PlantGroup edits do not create Events and remain the correction path
for current lifecycle.

The receipt boundary preserves this rule. An ordinary journal Event remains independently editable
and never reverses current state; deletion is also blocked when a completed Schedule retains it. A transfer or extraction Event created by an
authoritative operation has a one-to-one receipt relationship and ordinary deletion is rejected;
transfer editing remains correction of journal history and never changes the immutable receipt or
aggregate state. Authoritative extraction and reintegration Events cannot be edited through the
ordinary Event API. The focused reintegration action resolves an applied extraction receipt,
validates and locks its PlantGroup and resulting Plant, restores the snapshot, records one compensating reintegration
Event, and marks the receipt reversed in one transaction. Other operation receipts have no undo UI.

Plant and PlantGroup detail pages expose the same protected Event journal. Desktop presents the
API-ordered history as a vertical timeline, while narrow screens use compact wrapping cards. The UI
supports All, Care (watering, feeding), Observations (observation, flowering, fruiting), Cultivation
(movement, repotting, pruning, treatment, harvest, extraction, reintegration), and Status (transfer,
death, loss, discarded) filters;
`other` remains in All.
Creation explains current-state effects, and correction/deletion explains the non-event-sourced
boundary. A protected global Event read endpoint uses the same deterministic ordering and includes
target and BotanicalIdentity summaries. The collection-wide Journal page (`#/events`) applies the same filters and
links each item to its Plant or PlantGroup Event context. Generic Event creation cannot fabricate an
extraction; only the authoritative extraction operation creates one and its resulting-Plant link.
Structured per-kind payloads beyond movement destination, transfer recipient, the extraction
result, the measurement value and the phenological stage are deferred.

