# Domain model

This document describes the implemented Florabase model at Alembic head. The executable models,
migrations, Pydantic schemas, and tests remain authoritative when details differ.

Florabase separates shared botanical/reference knowledge from collection records. Partial knowledge
is valid: unknown dates, quantities, locations, suppliers, provenance, and lineage stay absent rather
than becoming invented placeholders.

## Reference concepts

### BotanicalIdentity

A BotanicalIdentity is the stable, installation-wide identity Florabase assigns to material. It has
an application-generated UUIDv7, required normalized scientific name, optional unquoted cultivar
name, optional common name, and UTC timestamps. Scientific name plus cultivar is case-insensitively
unique. An identity can be corrected after creation. Deletion is allowed only while it is unused;
references from SeedLots, Plants, or PlantGroups produce a domain conflict and no collection record
is cascaded. Merging duplicates, synonyms, external taxonomy IDs, and name history are deferred.

Collection records reference its UUID and do not copy botanical names as authoritative data.

### BotanicalProfile

A BotanicalProfile is optional general reference knowledge for exactly one BotanicalIdentity. Its
identity foreign key is also its primary key, enforcing at most one profile. The five optional text
sections are description, origin/distribution, cultivation, uses, and warnings; at least one must be
present. Profiles are operator-authored and distinct from observations of Plants or Sowings.

Structured native-range relationships to GeographicPlace are not implemented. Existing profile
origin/distribution text is independent and must not be silently replaced by future enrichment.

### Supplier

A Supplier is an installation-wide acquisition source such as a seller, nursery, supermarket,
person, exchange, or other source. Name is non-unique; stable UUID is identity. Optional website,
email, phone, and notes are descriptive. Retirement is non-destructive. Supplier answers who or what
supplied material, not where that material originated.

### Location

A Location is a physical place inside the collection, such as `Greenhouse → Shelf 2` or
`Refrigerator → Seed drawer`. It is a non-unique named adjacency tree with optional parent and
non-destructive retirement. The API derives display paths, prevents cycles, blocks retirement while
active descendants exist, and blocks reactivation beneath retired ancestors.

Location answers where managed material currently sits. It is not geographic provenance.

### GeographicPlace

A GeographicPlace represents provenance or distribution. The canonical hierarchy is installed from
the committed Unicode CLDR 48.2.1-derived snapshot and has stable source metadata; operators may add,
move, rename, retire, and reactivate custom descendants. Canonical nodes are immutable. Selecting one
node records the most precise known place and derives its ancestors without manufacturing greater
precision.

Current collection records use GeographicPlace for material provenance. Botanical native-range
relationships remain planned.

## Collection concepts

### SeedLot

A SeedLot is one physically managed packet, bag, or lot of seeds. Identical packets remain separate
records. BotanicalIdentity is required; label, Supplier, material provenance, collection Location,
notes, and dates are optional.

Acquisition, harvest, and expected-viability dates retain year, month, or day precision. Quantity may
be an exact or approximate whole seed count or weight in grams/milligrams. Unknown quantity is valid;
exact zero is valid only for an exhausted lot. Lifecycle is active, exhausted, discarded, or lost.
Sowing does not silently deduct the SeedLot quantity.

Source kind is purchased, purchased fruit, self-collected, collection-produced, gift/exchange,
other, or unknown. Only `other` accepts short source detail. A collection-produced lot may identify
one Plant or one PlantGroup producer; the producer is optional because historical knowledge can be
unknown. Non-collection-produced lots cannot carry a producer.

### Sowing

A Sowing is one managed attempt using exactly one SeedLot. Botanical identity is obtained from that
required origin rather than copied onto the Sowing. Optional facts include label, precision-preserved
sowing date, quantity sown, germinated count, current Location, substrate, method/container,
pretreatment, temperature bounds, environment, and notes. Lifecycle is active, completed, failed, or
abandoned.

Quantity may be an exact or approximate positive whole seed count or positive weight. Germinated
count is a non-negative total and cannot exceed an exact seed-count denominator. Florabase does not
derive percentages when a trustworthy denominator is absent. Dated germination observations are
planned separately.

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
receive no fabricated receipt. Undo, dependency evaluation, reintegration, record archival, reverse
mutation, and Undo UI are not implemented by this increment; `PLANT-006` and `PROPAGATION-003`
remain separate work.

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

Future `PLANT-006` will compensate only the recorded extraction of a Plant back into its immutable
originating PlantGroup, never arbitrary group membership. It restores an exact group quantity from
the extraction receipt; approximate and unknown group quantities receive no invented arithmetic.
The Plant and its existing Events and lineage must remain accessible. The preferred retention model
is a non-active, historically retained reintegrated Plant plus one operation-owned reinsertion Event
on the PlantGroup linked to that Plant. Product approval is required on whether `reintegrated` is a
new lifecycle or a separate immutable reintegration marker, and on whether a paired Plant-targeted
Event is worth the extra duplicated journal history. Hard deletion is excluded unless a later
approved contract proves that no Event, correction, lineage, or reference can be lost.

### Plant

A Plant is exactly one individually tracked specimen and never has quantity. It requires its own
BotanicalIdentity and may have a label, precision-preserved collection-entry date, current Location,
notes, and active, transferred, dead, lost, or discarded lifecycle. Transferred means the living
specimen left the currently held collection; its historical record, last Location, provenance,
lineage, labels, notes, and Events remain.

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

### Event

An Event is an explicitly recorded historical occurrence for exactly one Plant or PlantGroup. It
has a UUIDv7 identity, a controlled kind, an optional year/month/day-precision occurrence date,
optional notes, and exact UTC creation/update timestamps. The initial vocabulary is observation,
movement, repotting, flowering, fruiting, pruning, treatment, harvest, extraction, transfer, death,
loss, discarded, and other. Collection observations remain separate from BotanicalProfile reference
knowledge.

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
or deletable and never reverses current state. A transfer or extraction Event created by an
authoritative operation has a one-to-one receipt relationship and ordinary deletion is rejected;
editing remains correction of journal history and never changes the immutable receipt or aggregate
state. A future purpose-specific undo request will resolve that receipt, validate dependencies, and
apply its inverse atomically. No undo behavior or UI is implemented yet.

Plant and PlantGroup detail pages expose the same protected Event journal. Desktop presents the
API-ordered history as a vertical timeline, while narrow screens use compact wrapping cards. The UI
supports All, Observations (observation, flowering, fruiting), Cultivation (movement, repotting,
pruning, treatment, harvest, extraction), and Status (transfer, death, loss, discarded) filters;
`other` remains in All.
Creation explains current-state effects, and correction/deletion explains the non-event-sourced
boundary. A protected global Event read endpoint uses the same deterministic ordering and includes
target and BotanicalIdentity summaries. The collection-wide Events page applies the same filters and
links each item to its Plant or PlantGroup Event context. Generic Event creation cannot fabricate an
extraction; only the authoritative extraction operation creates one and its resulting-Plant link.
Structured per-kind payloads beyond movement destination, transfer recipient, and the extraction
result are deferred.

## Collection information architecture

The authenticated application opens on a Dashboard backed by one focused aggregate endpoint. It
reports authoritative counts for active Plants, active PlantGroups, active SeedLots, active Sowings,
all BotanicalIdentities, and all Events, plus the six most recent Events. These are current overview
counts, not the analytical/statistical definitions planned for `DASHBOARD-001`; transferred Plants
and PlantGroups are excluded from the active counts while remaining in historical lists and identity
aggregation.

Desktop navigation groups Dashboard, the Plants/Seeds/Sowings/Events collection workflows,
Botanical identities, and Location/Supplier/GeographicPlace reference data in a persistent sidebar.
Mobile exposes Home, Plants, Seeds, Events, and More in a fixed bottom navigation; More reaches the
same secondary destinations.

BotanicalIdentity is a collection hub with Overview, Seeds, Sowings, Plants, and Events tabs. Its
Plants tab intentionally combines Plant and PlantGroup cards while labeling their distinct types.
The overview separates active and transferred Plant and PlantGroup counts rather than treating
transferred material as currently held.
The hub uses stored identity relationships only: a Sowing belongs through its required SeedLot and
Events belong through their current Plant or PlantGroup target. This aggregation never creates a
lineage edge. Dedicated record details link back to the identity hub and retain their explicit
lineage view separately.

Plant and PlantGroup details use Overview, Events, and Lineage tabs; SeedLot uses Overview, Sowings,
and Lineage; Sowing uses Overview and Lineage. Breadcrumbs and tab query parameters provide stable
orientation and deep links. User-created BotanicalIdentity, SeedLot, Sowing, Plant, PlantGroup,
Location, Supplier, and custom GeographicPlace data have visible correction flows. Canonical
GeographicPlaces remain immutable by design, and lifecycle-bearing records retain their existing
non-destructive lifecycle semantics.

The collection pages provide a guided `BotanicalIdentity → SeedLot → Sowing → Plant / PlantGroup`
entry path. Identity tabs preselect identity context but require the operator to choose a real
SeedLot or Sowing before storing lineage. SeedLot-to-Sowing entry separates normal Sowing details
from a visible source-effect confirmation: exact compatible quantities can show an authoritative
subtraction preview, approximate remainders remain editable estimates, unknown quantities stay
unknown, and incompatible dimensions do not offer arithmetic. No adjustment and use-all remain
explicit choices governed by the backend contract.

Sowing detail links its source and displays the authoritative descendant summary without converting
approximate or unknown PlantGroups into exact individuals. Plant and PlantGroup creation asks for an
explicit resulting Sowing lifecycle and defaults to keeping it active. Completing an exact
seed-count Sowing can display `not germinated` as `quantity - germinated_count`; approximate,
unknown, and weight-based Sowings do not fabricate that remainder. Completed Sowings remain
clickable under the Completed and All filters, while failed and abandoned history remains reachable
through All. The Sowing propagation view and the SeedLot and Plant/PlantGroup Lineage views
visualize only stored lineage.

Ordinary direct Plant/PlantGroup creation, retroactive entry, and all correction forms remain valid.
Later corrections do not replay previous source effects or lifecycle choices. Rich dated germination
observations remain deferred to `GERMINATION-001`.

The intended product narrative is `BotanicalIdentity → SeedLot → Sowing → Plant / PlantGroup →
Events / terminal state`. It is an interaction and comprehension direction over the explicit model,
not a new relationship, automatic state machine, or claim that every record has complete ancestry.
Later navigation work should make that lifecycle easier to follow across desktop and mobile without
conflating BotanicalIdentity aggregation with recorded lineage.

Future Location presentation may scope the one shared Location hierarchy by its Seeds, Sowings, or
Plants usage and render it as a collapsible tree. This does not split Location into separate domain
entities. Future Supplier detail may summarize explicitly connected records; it must not imply
spending or price totals before an Order model exists. Finer-grained geography remains compatible
with carefully scoped custom/local GeographicPlace nodes, while a canonical global city dataset is
not part of the current or first-release model.

## Explicit lineage

Florabase persists only direct relationships created by supported workflows:

```text
SeedLot → Sowing → Plant / PlantGroup
```

```text
PlantGroup → extracted Plant
```

```text
Plant / PlantGroup → collection-produced SeedLot
```

The arrows show material/workflow descent. The lineage API walks the reverse direction from a
SeedLot, Sowing, Plant, or PlantGroup to its recorded ancestors and returns typed summaries in
immediate-first order.

A Plant's Sowing origin, PlantGroup extraction origin, and direct origin are mutually exclusive. A
PlantGroup's Sowing and direct origins are mutually exclusive. An extracted Plant does not duplicate
the group's Sowing or SeedLot links; those ancestors are derived by traversal. Producer assignment
to a collection-produced SeedLot is also exclusive between Plant and PlantGroup, and application
validation prevents a proposed producer from creating a cycle.

BotanicalIdentity is deliberately independent at every applicable level. A downstream correction
does not rewrite upstream records or invalidate lineage. Inactive SeedLots, Sowings, Plants,
PlantGroups, Suppliers, Locations, and custom GeographicPlaces retain historical references.

Unknown or partial lineage remains honest absence. Florabase does not infer a Sowing from matching
names, create placeholder ancestors, or use a generic genealogy graph. Maternal/paternal pairs,
pollen donors, controlled crosses, multiple producers, reverse extraction/merge, and visual lineage
navigation are deferred.

## Ownership and mutation boundary

The current installation supports one enabled owner. Domain and reference records are
installation-wide and do not carry per-user ownership columns. Reads require an authenticated
session; mutations require owner authorization, exact Origin, and a session-bound CSRF token. Normal
product workflows preserve historical rows rather than hard-deleting them.

## Deferred capabilities

Event attachments, richer structured Event payloads, attachment/photo
storage, richer germination observations, Orders, other propagation material, advanced search,
analytical dashboards, contextual form help, import/export, PWA installability, enrichment, taxonomy
reconciliation, scope-aware
Location browsing, richer Supplier summaries, reminders, weather, and multi-user ownership remain
planned. `docs/features.json` is the detailed source for dependencies and acceptance criteria.
