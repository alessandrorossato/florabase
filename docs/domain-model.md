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
unique. Renaming corrects the same identity; merging duplicates, synonyms, external taxonomy IDs,
and name history are deferred.

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

### Plant

A Plant is exactly one individually tracked specimen and never has quantity. It requires its own
BotanicalIdentity and may have a label, precision-preserved collection-entry date, current Location,
notes, and active, dead, lost, or discarded lifecycle.

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
origin, and provenance fields. Lifecycle is active, completed, dead, lost, or discarded.

Quantity is unknown or an exact/approximate whole count. Zero is allowed only as exact historical
quantity for completed, dead, or discarded groups. A dedicated active-group extraction transaction
creates one Plant with the group as immutable immediate origin. Exact quantities decrement; the last
exact member completes the group. Approximate and unknown quantities remain unchanged because
subtracting one would imply false precision.

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

Plant events and observations, attachment/photo storage, richer germination observations, Orders,
other propagation material, advanced search, dashboards, contextual help, import/export, PWA
installability, enrichment, taxonomy reconciliation, reminders, weather, and multi-user ownership
remain planned. `docs/features.json` is the detailed source for their dependencies and acceptance
criteria.
