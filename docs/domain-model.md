# Domain model

Florabase grows from collection workflows, not from a general-purpose taxonomy database. The
verified `BotanicalIdentity`, `BotanicalProfile`, `SeedLot`, `Sowing`, `Plant`, and `PlantGroup`
contracts and reusable `Supplier` directory are defined here. The collection `Location` and
geographic-provenance `GeographicPlace` directories are also established. Later increments may add
`PlantEvent` and collection attachment relationships, but those future concepts are not part of the
contracts below.

## BotanicalIdentity aggregate contract

A `BotanicalIdentity` is the stable collection-local botanical identity Florabase assigns to seeds,
plants, and future collection material. It represents the operator's current botanical
identification: one scientific name, optionally qualified by one cultivar. A botanical identity may
correspond to a species, an infraspecific taxon, a hybrid or other valid botanical-name expression,
or a taxon qualified by a cultivar. Florabase is not itself a taxonomic authority, and the record
remains useful without an internet connection or external taxonomy service.

The aggregate is deliberately name-centred. Its stable UUID, rather than any spelling of the name,
is its persistent identity. Correcting or updating a name therefore does not require future related
records to copy or retain obsolete taxonomic text.

### First workflows

1. **Create the identity before the material.** The operator enters a known scientific name before
   recording seeds or plants. The BotanicalIdentity UUID later becomes their reference; the
   BotanicalIdentity record contains no quantity, provenance, location, or lifecycle data.
2. **Find before creating.** Creation uses the normalized scientific name and cultivar qualifier to
   detect an existing classification. Capitalization differences do not create a second record.
3. **Correct a misspelling.** A later update will correct the name on the same UUID after checking
   that the corrected identity does not conflict with another record. The first REST slice does not
   yet expose update behavior.
4. **Reconcile duplicates.** If two records are later found to represent the same classification,
   Florabase will require an explicit merge that chooses a survivor and repoints future references.
   It must not silently delete or automatically merge records.
5. **Record an infraspecific taxon.** The operator enters the complete botanical name, including its
   rank marker and epithet, in `scientific_name`, for example `Acer palmatum var. dissectum`.
   Florabase preserves it as one name and does not attempt to parse a hierarchy.
6. **Record a cultivar.** The operator stores the cultivar epithet separately, without quotes, in
   `cultivar_name`. For example, `Acer palmatum` plus `Bloodgood` displays as
   `Acer palmatum ‘Bloodgood’`; cultivar text never becomes part of `scientific_name`.

### Minimum persisted fields

| Field             | Meaning                                                                                           | Required | Normalization                                                                                                                              | Uniqueness                                                                         |
| ----------------- | ------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| `id`              | Stable public aggregate identity                                                                  | Yes      | Application-generated UUIDv7                                                                                                               | Primary key                                                                        |
| `scientific_name` | Botanical taxon name as currently identified by the operator, without author citation or cultivar | Yes      | Trim outer whitespace and collapse internal whitespace runs to one ASCII space; preserve the remaining spelling and case as entered        | Case-insensitive together with `cultivar_name`                                     |
| `cultivar_name`   | Cultivar epithet without surrounding straight or curly quotes                                     | No       | Trim/collapse whitespace; strip one matching pair of surrounding cultivar quotes; blank becomes null; preserve remaining spelling and case | Case-insensitive together with `scientific_name`; null means the unqualified taxon |
| `common_name`     | Optional operator-facing familiar name                                                            | No       | Trim/collapse whitespace; blank becomes null; preserve spelling and case                                                                   | None; it is display metadata, not identity                                         |
| `created_at`      | Authoritative creation time                                                                       | Yes      | Timezone-aware boundary value stored as PostgreSQL `timestamptz` in UTC                                                                    | None                                                                               |
| `updated_at`      | Authoritative last-change time                                                                    | Yes      | Timezone-aware boundary value stored as PostgreSQL `timestamptz` in UTC                                                                    | None                                                                               |

`DATABASE-001` should use practical bounded text lengths: 255 characters for `scientific_name`, 120
for `cultivar_name`, and 160 for `common_name`, measured after normalization. It should reject blank
required values, normalized empty optional values, embedded control characters, and overlong values.
These are input and persistence invariants, not a botanical grammar.

The database uniqueness invariant is the case-insensitive pair
(`scientific_name`, `cultivar_name`), treating a null cultivar as a comparable value. PostgreSQL must
enforce this invariant with a named unique index or constraint; API pre-checks are only for friendly
errors and cannot replace the database race-safety boundary. Because the backend is the only
database writer, it normalizes whitespace before persistence, while database checks ensure stored
values are nonblank and already in normalized form. `DATABASE-001` should review the exact SQL and
prove both qualified and null-cultivar conflicts in PostgreSQL integration tests.

The canonical display label is the normalized `scientific_name`, followed by a space and the
normalized cultivar rendered in Unicode single quotation marks when present. `common_name` may be
shown alongside it but never replaces the canonical label or participates in identity. Florabase
does not automatically italicize stored text; presentation may style botanical and cultivar parts
appropriately.

### Naming decisions

- The aggregate is named BotanicalIdentity. Species is too narrow because the aggregate can hold an
  infraspecific, hybrid, or other botanical-name expression. Taxon is also too narrow because a
  cultivar is not a taxon, while the aggregate may represent a taxon qualified by a cultivar.
- Scientific names are stored after whitespace normalization but otherwise as entered. Florabase
  does not silently change capitalization because it has no taxonomic parser and must not corrupt
  hybrid formulas or other legitimate notation. The UI can explain the usual genus-capitalized,
  epithet-lowercase convention without enforcing it as identity.
- `scientific_name` may contain an infraspecific rank and epithet. Genus, specific epithet, and
  infraspecific parts are not split into columns now: doing so would require parsing and would add no
  current workflow benefit.
- Cultivar is accepted now because collections commonly distinguish material by cultivar. It is a
  separate qualifier, not part of the scientific taxon name. Different cultivar qualifiers produce
  distinct BotanicalIdentity records; the unqualified taxon can also exist.
- Botanical author citation is deliberately excluded from `scientific_name` and deferred. It does
  not distinguish the collection classification in the first workflows. Because Florabase does not
  parse botanical names, the first API can instruct the operator to omit a citation but cannot
  reliably detect one; entered citation text is preserved and participates in duplicate comparison
  like any other name text.
- Family is deferred. Genus is available visually from many names but is neither parsed nor stored
  as authoritative metadata. Both can be added later from operator input or taxonomy enrichment
  when a concrete filtering or validation workflow requires them.
- Common name is optional now because it helps an operator recognize a record, but it is not unique
  and receives no localization model.
- Synonyms and external taxonomy identifiers are deferred. A future enrichment adapter may attach
  source-scoped identifiers and proposed names, but local creation and reads must never require or
  block on an external service.

Normalization is intentionally mechanical, not taxonomic. It handles surrounding/repeated
whitespace and cultivar quotation only. Case-insensitive comparisons prevent obvious capitalization
duplicates; different punctuation, spelling, hybrid notation, or taxonomic meaning requires an
explicit operator decision. No fuzzy matching, nomenclature engine, or background synchronization
is implied.

### Duplicate, rename, and reconciliation policy

- A create that matches the normalized, case-insensitive scientific-name/cultivar pair is an obvious
  duplicate and must fail with a conflict that identifies the existing record. It does not return a
  second success and does not mutate the existing record.
- Whitespace-only and capitalization-only variants normalize or compare to the same identity.
  Spelling variants do not: Florabase may later offer suggestions, but it must not guess.
- Correcting a misspelling or changing the current scientific name preserves the BotanicalIdentity
  UUID and updates `updated_at`. A rename that would collide with another record is a conflict and
  instead requires reconciliation.
- Discovering a synonym does not create a second canonical BotanicalIdentity automatically. Until
  synonym history is implemented, the operator may rename the existing record to the currently
  identified name. A
  future alias/history model can record the former or synonymous name without changing the stable
  UUID.
- Reconciling two existing records is a future explicit operation. It will select a survivor,
  transactionally repoint all SeedLot and Plant references, retain enough alias/audit information to
  explain the obsolete identity, and only then retire the duplicate. Foreign keys must therefore
  target `botanical_identity_id`, never name text. No merge table, tombstone, or endpoint is needed
  yet.

This policy leaves room for name history and synonyms without making either necessary for the first
migration. It also avoids irreversible name-based foreign keys or cascade deletion.

### Shared catalog and authorization boundary

BotanicalIdentity is installation-wide shared classification/reference data within one Florabase
installation. It has no `user_id` and is not owned by an individual account. This resolves the
mutable-aggregate scope required by ADR 0005 before schema creation.

Shared catalog scope does not make future collection data shared. SeedLot, Plant, Sowing,
Observation, and other collection records may have their own ownership and scoping rules when their
contracts are designed. Mutating BotanicalIdentity through the future API still requires an
authenticated actor and explicit authorization; shared scope is not anonymous or unrestricted
write access.

### Boundary with future collection entities

BotanicalIdentity answers **what stable botanical identity has Florabase assigned to this
material?** It is not:

- a packet, accession, or lot of seed;
- an inventory quantity or unit;
- a cultivated individual or group of plants;
- a sowing, germination, observation, or lifecycle event;
- a supplier, order, provenance statement, or storage/growing location.

A future SeedLot records a particular acquired or collected batch and references
`botanical_identity_id`. A future Plant records a cultivated individual or group and also references
the appropriate `botanical_identity_id`, either directly or through a concrete lineage established
by a later contract. Future collection records may reference BotanicalIdentity as appropriate. They
must not duplicate scientific or cultivar identity as authoritative data. Accession, provenance,
supplier labels, and inventory-specific cultivar assertions remain questions for their own
workflows rather than reasons to enlarge BotanicalIdentity now.

## Supplier directory contract

A `Supplier` is the reusable installation-wide party or place from which collection material was
acquired. It answers **who or what supplied this material?** Examples are a seed seller, nursery,
supermarket, private person, exchange, or another source. It has no `user_id` and is maintained as
shared collection reference data.

Supplier is independent from biological or geographic origin. For example, material may be
supplied by `Rare Palm Seeds` while its geographic origin is `Madagascar`; neither value implies or
replaces the other. Supplier therefore has no geographic-origin, provenance, SeedLot, Order,
purchase-history, postal-address, or location fields in this increment.

The first persisted record contains application-generated UUIDv7 `id`; required normalized `name`;
required `kind` from `seller`, `nursery`, `supermarket`, `person`, `exchange`, or `other`; optional
`website`, `email`, `phone`, and plain-text `notes`; nullable `retired_at`; and timezone-aware
`created_at` and `updated_at`. Name is trimmed and internal whitespace is collapsed while spelling
and capitalization are preserved. Optional blanks become null. Websites accept only reasonable
HTTP/HTTPS URLs, email receives pragmatic structural validation, phone remains human-entered text,
and notes preserve useful line breaks.

Names are deliberately not unique: two legitimate suppliers or people may share a display name,
and stable UUID is identity. There is no fuzzy duplicate detection. Normal product behavior never
hard-deletes a supplier. Retirement sets `retired_at`; retired records remain readable, editable,
and reactivatable and sort after active records. The deterministic directory order is active first,
then case-insensitive name, kind, and UUID.

Authenticated reads require no CSRF. Create, full-record update, retirement, and reactivation
require an authenticated owner plus the existing exact-Origin and session-bound CSRF protections.
No generic Party, Organization, ContactMethod, Address, acquisition-source inheritance, CRM, or
generic CRUD abstraction is introduced.

## Location directory contract

A `Location` is an installation-wide physical place within the operator's collection. It answers
**where is collection material stored or a plant cultivated?** Examples include `House`,
`Greenhouse`, `Refrigerator`, `Seed cabinet`, and arbitrarily deep practical paths such as
`House → Basement → Seed cabinet → Drawer A`. It has no `user_id` and is shared collection
reference data.

Location is independent from biological or geographic origin. `Greenhouse → Upper shelf` may be a
collection Location while `Ecuador` is future provenance for a particular SeedLot. This capability
adds no geographic-origin, address, coordinate, map, weather, SeedLot, Sowing, or Plant model.

The first persisted record contains application-generated UUIDv7 `id`; required normalized `name`;
nullable self-referencing `parent_id`; nullable `retired_at`; and timezone-aware `created_at` and
`updated_at`. The adjacency list permits roots and arbitrary practical depth, and parent changes
represent real collection-layout changes. The parent foreign key restricts deletion, a database
check rejects self-parenting, and normal product behavior never hard-deletes Locations.

Names are trimmed, accidental internal whitespace is collapsed, blank and unsupported control
values are rejected, and meaningful spelling and capitalization are preserved. Names are not
globally unique and identical sibling names are allowed; stable UUID is identity. Hierarchy-aware
derived paths disambiguate names such as `Greenhouse A → Shelf 1` and `Greenhouse B → Shelf 1`.
There is no fuzzy duplicate handling or broader uniqueness rule. Two identically named siblings are
therefore valid but have the same derived display path in this first UI; they remain distinct by
UUID, and a later concrete workflow may add secondary display context without changing identity or
silently imposing uniqueness.

Application hierarchy mutations lock the current Location rows for a coherent PostgreSQL
transaction snapshot. The backend rejects self-parenting and moving a Location beneath any of its
descendants before writing. `display_path` is derived from current ancestry in API responses and is
never persisted. The deterministic directory sorts active records before retired records, then by
case-insensitive derived path and UUID.

Retirement is deliberate and non-destructive. A Location cannot be retired while any active
descendant remains. A retired Location cannot be reactivated while any ancestor is retired. The
application never automatically retires or reactivates a subtree. Retired records and paths remain
readable for historical references, while active records are the normal choices for new future
assignments.

Authenticated reads require no CSRF. Root/child creation, full name/parent update, retirement, and
reactivation at `/api/v1/locations` require an authenticated owner plus exact Origin and the existing
session-bound CSRF token. The accessible directory uses semantic nested lists, buttons, forms, and
native parent selects; self and descendants are excluded client-side for usability while backend
validation remains authoritative. No drag-and-drop, generic tree framework, materialized path,
closure table, nested set, location category, notes, or advanced search is introduced.

## GeographicPlace directory contract

`GeographicPlace` is installation-wide reference data for provenance and distribution. It answers
**where did biological material originate, get collected, or get grown?** It never answers where
Florabase-managed material currently sits. `House → Refrigerator → Seed drawer` is a collection
`Location`; `World → Asia → Southeast Asia → Thailand → Chiang Mai → Doi Suthep` is geography.

The canonical base is generated from Unicode Common Locale Data Repository (CLDR) JSON release
48.2.1, specifically `cldr-core/supplemental/territoryContainment.json` and the English territory
names in `cldr-localenames-full/main/en/territories.json`. CLDR containment incorporates UN M.49
macro-regions. The snapshot is redistributed under the Unicode License v3 (`Unicode-3.0`) with
attribution to Unicode, Inc. Release 48.2.1 was published on 2026-07-08; its patch concerns timezone
compatibility, while the underlying geography data reports CLDR 48. Florabase records the exact
package release so regeneration remains reproducible.

`scripts/generate_geographic_places.py` accepts those two official pinned JSON files and produces
the minimal normalized snapshot at
`backend/alembic/data/geographic_places_cldr_48_2_1.json`. Generation excludes deprecated and
overlapping grouping-only containment records while retaining CLDR/UN M.49 code `419` as the
applicable Latin America and Caribbean intermediate level. It validates one parent per included
node and one coherent World root, and assigns deterministic UUIDv7 identities from the
source/version/code tuple. No upstream
repository, runtime geography dependency, or network request is shipped. Alembic revision
`20260830_0007` reads only the committed snapshot, so fresh installation, requests, and normal
operation work offline.

Canonical rows use `source_name = unicode_cldr` and `source_version = 48.2.1`. Their source code is
typed rather than interpreted by shape alone: numeric region codes use `un_m49`; normal two-letter
country/territory identifiers use `iso_3166_1_alpha_2`; and CLDR-defined territory identifiers not
in ISO 3166-1 use `cldr_territory`. The tuple of source name, code type, and code is unique. Names are
display data, never identity. `World` is the only root; parent foreign keys use restrictive deletion
so later SeedLot provenance can safely reference any broad or precise node.

The canonical adjacency list preserves the source's varying depth. It does not assume every leaf is
exactly continent → subregion → country. A relationship selects one most appropriate known node:
selecting Brazil derives `World → Americas → Latin America and the Caribbean → South America →
Brazil`, while selecting South America records only that valid broader knowledge. Florabase never
automatically descends or persists redundant ancestor foreign keys or display paths.

Operator-defined local nodes extend any active canonical or custom parent, have their own UUIDv7,
name, parent, and timestamps, and deliberately have no fabricated source code. Names need not be
unique. Custom nodes can be renamed and re-parented at arbitrary practical depth; self-parenting,
moving beneath a descendant, missing parents, cycles, and active placement beneath a retired
ancestor are rejected. Canonical nodes cannot be renamed, re-parented, retired, reactivated, or
deleted through normal product behavior.

Custom retirement is non-destructive and does not mutate a subtree. Active descendants must be
retired first, and a node can be reactivated only after its retired ancestors. Retired nodes remain
readable for historical provenance. This matches Location lifecycle safety, except geography has no
custom root and the canonical portion is immutable.

Authenticated directory and item reads at `/api/v1/geographic-places` require no CSRF. Creating,
updating, retiring, and reactivating custom nodes requires an authenticated owner, exact Origin, and
the session-bound CSRF token. Responses derive `display_path` from the hierarchy and expose the
canonical/custom distinction plus source metadata. The accessible Geography UI provides a complete
tree, client-side path filter, broad-node selection, full-path/status detail, local-child creation,
custom editing/re-parenting, and custom lifecycle actions. Coordinates, bounding boxes, polygons,
GeoJSON, GIS, maps, geocoding, reverse geocoding, and external runtime geography integrations are
explicitly deferred.

## SeedLot contract

A `SeedLot` is one physically managed lot, packet, or bag of seeds. Two packets remain two SeedLots
even when every descriptive value matches. Splitting seeds from a lot into another vial or container
does not create another SeedLot in the first implementation; container-level tracking is deferred
until a concrete workflow requires it. Every SeedLot references exactly one existing
`BotanicalIdentity`, while the SeedLot's stable UUID—not its label or descriptive fields—is its
identity.

Partial information is normal. A SeedLot may exist when every optional fact is unknown; the first
persisted record must require only its stable identity, BotanicalIdentity relationship, lifecycle,
and implementation-managed timestamps. Revision `20260830_0008` persists that boundary in the
`seed_lots` table. UUIDv7 is application-generated; `source_kind` safely defaults to `unknown`,
`lifecycle` defaults to `active`, and all optional facts remain nullable. Label and short source
detail are bounded to 255 characters; notes are bounded to 20,000 characters. The database accepts
only trimmed, normalized single-line label/source detail and trimmed LF/tab-compatible multiline
notes without other control characters. The later API boundary owns normalization before writes.

### Informal label and source

A SeedLot may have a short operator-defined `label`, for example `Thailand trip 2026`, `RPS #1847`,
or `Old fridge packet`. The label is non-unique display context. It is not primary identity, a tag
system, a replacement for BotanicalIdentity, or an opening for generic custom fields.

`source_kind` answers **how was this material acquired?** The initial controlled vocabulary is:

| Identifier            | Meaning                                                  |
| --------------------- | -------------------------------------------------------- |
| `purchased`           | Seeds bought directly                                    |
| `purchased_fruit`     | Seeds extracted from purchased fruit                     |
| `self_collected`      | Seeds collected directly by the operator                 |
| `collection_produced` | Seeds produced from the operator's own collection        |
| `gift_exchange`       | Seeds received as a gift or through an exchange          |
| `other`               | Another known source, optionally clarified by short text |
| `unknown`             | The acquisition route is not known                       |

Only `other` uses the optional short `source_detail`; it clarifies that category rather than
becoming another category or general notes field. The vocabulary is not operator-customizable in
the first implementation. Selected controlled vocabularies may later allow operator-defined values
alongside stable Florabase defaults, but only after a concrete workflow demonstrates the need; this
contract creates no generic enum or custom-field framework.

Source, Supplier, and material provenance answer different questions:

- `source_kind` records how the material was acquired;
- optional `supplier_id` records who or what supplied it through the existing `Supplier` directory;
  and
- optional material provenance records where this particular biological material originated, was
  collected, or was grown, when known.

Purchased seeds can therefore have `source_kind = purchased`, Supplier `Rare Palm Seeds`, and
material provenance `Madagascar`. Self-collected seeds can have no Supplier and provenance
`Doi Suthep, Chiang Mai, Thailand`. A gift can identify the person or exchange as Supplier while
retaining the material's actual collection or growing place separately. Supplier location never
substitutes for material provenance, and material provenance is optional for every source kind.

### Reusable geography boundary

Material provenance creates a concrete need for reusable structured geography. `GEOGRAPHY-001`
defines and persists hierarchical `GeographicPlace` reference data before `SEED-002`.
`GeographicPlace` is distinct from collection `Location`:
`GeographicPlace` describes geographic provenance or distribution, while `Location` describes where
Florabase-managed material or plants are physically stored or cultivated now.

The canonical hierarchy provides stable World, region, applicable intermediate region, and country
or territory nodes from the documented CLDR/UN M.49-derived snapshot. Operator-defined local places
can extend canonical nodes, for example `Asia → Southeast Asia → Thailand → Chiang Mai → Doi
Suthep`, while canonical base reference data remains separately maintained and stable.

A geographic relationship stores only the most appropriate known node. Ancestors are inferred from
the hierarchy: provenance known as `Brazil` records Brazil and permits inference of South America,
without redundantly storing both. If only `South America` is known, that broad node is valid. The
system never manufactures greater precision. These semantics preserve future aggregation without
introducing coordinates, GIS, maps, or native-range relationships.

Botanical native range is a separate relationship from SeedLot material provenance. The existing
operator-authored `BotanicalProfile.origin_distribution` remains descriptive text. Planned
`GEOGRAPHY-002` may relate one BotanicalIdentity or profile to one or more nodes in the same
GeographicPlace hierarchy: `Brazil` can express country-level knowledge, `South America` broad
knowledge, and `Brazil` plus `Madagascar` a disjunct range. Multiple areas must not be replaced by
their common ancestor `World`. Native-range references never imply where a particular SeedLot came
from, and SeedLot provenance never changes botanical native-range knowledge.

### Dates, quantity, and viability

Acquisition and harvest are independent optional facts. Acquisition records when the lot was
obtained; harvest records when its seeds were harvested or collected. Either, both, or neither may
be known. Each known date retains its declared precision of year, year and month, or complete date,
so `2024`, `2024-05`, and `2024-05-18` remain distinct claims. Florabase never turns an incomplete
date such as `2024` into `2024-01-01`. Persistence uses four columns independently for each fact:
`*_precision`, `*_year`, `*_month`, and `*_day`. Precision is `year`, `month`, or `day`; a wholly
unknown value has all four columns null. Named checks require exactly the components declared by the
precision, years 1–9999, months 1–12, and PostgreSQL-valid complete calendar dates. These mechanics
are repeated only for acquisition, harvest, and expected viability rather than introducing a
generic temporal framework.

Quantity is optional and independently supports exact seed count, approximate seed count, exact
weight, approximate weight, or unknown quantity. Counts are normally whole positive values; weights
are normally positive decimal values paired with an explicit supported unit. Thus `120 seeds`,
`about 100 seeds`, `4.5 g`, and `about 5 g` are representable without implying false precision.
An exact zero count or weight is also meaningful when an exhausted lot is known to contain no
remaining material. Zero is not an approximation or a generic marker for unavailability. Ranges are
deferred.
Persistence uses nullable `quantity_kind`, `quantity_value`, `quantity_unit`, and
`quantity_is_approximate`. An unknown quantity has the entire tuple null. A known tuple uses kind
`seed_count` or `weight`; the approximation boolean is explicit. Counts reject fractions and units,
while weights require the unconverted entered unit `g` or `mg`. Positive exact and approximate
values remain valid for every lifecycle. Zero is valid only with lifecycle `exhausted` and an exact
quantity; negative values and approximate zero are always invalid.
The first SeedLot contract does not automatically deduct quantity when a later Sowing uses seeds;
`SOWING-001` must decide accounting behavior from its actual workflow.

The protected SeedLot API exposes each partial date as one structured value with `precision`,
`year`, and nullable `month`/`day` components rather than exposing the persistence columns. It also
exposes quantity as one structured value with kind, exact decimal value, optional unit, and explicit
approximation. Requests accept decimal JSON numbers or decimal strings for ergonomic clients and
exact import paths; responses always serialize the value as a decimal string, and the generated
TypeScript contract reflects that distinction. This avoids silently rounding a stored decimal when
a JavaScript client reads a response.

An optional operator-entered `expected_viability_until` may retain a viability or germination-
confidence horizon with partial date precision. Passing that horizon can produce only an
informational warning such as “Expected viability period has passed; germination may be reduced.” It
does not prove that seeds are dead or unusable, does not change lifecycle, and must not create an
`expired` state. The first implementation does not infer this date from BotanicalProfile or external
species knowledge. Future reviewed knowledge may suggest an expectation but must never silently
overwrite operator data.

### Lifecycle, storage, and notes

The non-destructive lifecycle vocabulary is `active`, `exhausted`, `discarded`, and `lost`:

- `active` means material is still considered available;
- `exhausted` means no seeds remain or are available;
- `discarded` means the operator intentionally removed the remaining material; and
- `lost` means the physical lot can no longer be located or accounted for.

Lifecycle is retained history rather than a deletion instruction. An inactive SeedLot remains
available to later Sowing, Plant, and PlantGroup lineage. Viability uncertainty never automatically
changes lifecycle. Exhausted does not require a known-zero quantity: a historical lot may be entered
directly as exhausted with exact zero or with an unknown all-null quantity. Discarded and lost are
not synonyms for zero; they may retain a positive last-recorded quantity or an unknown quantity,
but never use zero merely because the lot is inactive.

Optional `location_id` references the existing collection `Location` where the packet is stored now,
such as `House → Refrigerator → Seed drawer`. It is not material provenance. Missing storage is
valid, moving storage later must not alter provenance, and movement history is deferred.

The required `botanical_identity_id` and optional `supplier_id`,
`material_provenance_place_id`, and `location_id` are four independent restrictive foreign keys.
They preserve historical lots even when a referenced directory record is retired; active-state
selection is deliberately deferred to later API policy. Each foreign key and lifecycle has a simple
B-tree index for expected joins, filtering, and future inventory access patterns. No descriptive
combination is unique because matching physical packets remain separate lots.

Optional plain-text `notes` contain information genuinely specific to the lot and preserve useful
Unicode and multiple lines. Notes must not duplicate BotanicalProfile reference knowledge, Supplier
contact information, the geographic hierarchy, or future Plant observations.

### Orders and lineage boundaries

SeedLot contains no purchase price, currency, order number, shipping price, or other transaction
fields. Those belong to future `ORDER-001`. A purchased SeedLot may initially reference Supplier
without an Order; later one Order may group multiple acquired lots without merging the separate
physical SeedLots.

Lineage remains explicit rather than generic. The intended workflow is
`SeedLot → Sowing → Plant / PlantGroup`. A `collection_produced` SeedLot may have one known
collection producer, either a Plant or PlantGroup, while an unknown producer remains valid.
`SEED-001` adds no producer foreign key or generic genealogy graph; the relationship is completed by
the later persistence capabilities identified in the lineage contract.

### First persistence boundary

`SEED-002` may refine a focused relational representation for stable identity, exactly one
BotanicalIdentity, optional label, source kind and `other` detail, optional Supplier, optional
GeographicPlace material provenance, independent acquisition and harvest values with precision,
optional quantity value/unit/approximation semantics, optional expected viability horizon, optional
collection Location, lifecycle, notes, and UTC timestamps. It must not add container tracking,
automatic quantity accounting, Sowing, Plant, Order or pricing data, tags, generic custom fields,
geography tables or APIs, native-range persistence, attachments, or import/export.

## Sowing contract

A `Sowing` is one intentionally managed, internally homogeneous sowing attempt using material from
exactly one existing `SeedLot`. Its practical boundary is seeds from the same SeedLot that are
intentionally started together under the same initial treatment and broadly shared initial
cultivation conditions. Twenty seeds scarified and placed in one tray under shared conditions are
one Sowing; ten scarified seeds and ten untreated seeds from that lot are two independent Sowings.
Intentionally different treatments or experimental conditions normally create separate records
rather than incompatible conditions inside one record. This does not introduce a generic experiment
framework.

One SeedLot may have zero, one, or many Sowings. Multiple Sowings retain the same upstream lot
lineage but remain independent even when they share a BotanicalIdentity. A Sowing has its own stable,
application-generated UUIDv7 identity; descriptive values never identify or merge it.

### Minimum record and fast entry

Partial information is first-class. The minimum Sowing requires only its stable UUID, exactly one
SeedLot relationship, lifecycle (defaulting to `active`), and implementation-managed timezone-aware
UTC creation and update timestamps. Sowing date, quantity, label, germinated count, Location,
cultivation details, and notes are optional. The operator must never invent them to save a current or
historical attempt.

`SOWING-002` persists this contract in the Alembic-managed `sowings` table. Each row has one
restrictive `seed_lot_id` foreign key, an optional restrictive current `location_id`,
application-generated UUIDv7 identity, and timezone-aware UTC timestamps. The protected `/api/v1`
resource supports list, create, detail, and complete-state PUT without DELETE. Responses resolve the
current SeedLot/BotanicalIdentity display context and Location path through joined projections
rather than snapshots; inactive SeedLots, retired Locations, and historical Sowing lifecycles remain
valid references. The persistence/API slice does not adjust SeedLot quantity or add Plant,
observation, attachment, event, or generic lineage persistence.

An optional short, non-unique operator `label`, such as `Tray 1`, `GA3 test`, `Autumn 2026`, or
`Scarification batch`, supplies display context only. It is not identity, a tag system, or a treatment
taxonomy.

The optional sowing date preserves exactly the declared precision: year, year and month, or complete
date. Thus `2024`, `2024-05`, and `2024-05-18` remain different claims, and Florabase never fills a
missing month or day. It follows the product semantics established for SeedLot partial dates and may
reuse a focused representation where appropriate, without creating a broad temporal framework.

Future fast entry should lead with SeedLot and offer label, sowing date, and quantity sown without
requiring any of the optional values. Cultivation, Location, lifecycle, germinated count, and notes
should be progressively available rather than blocking the primary workflow. UI implementation
belongs to `SOWING-003`, not this contract.

### Quantity sown and SeedLot accounting

Quantity sown is optional. When known, it is an exact or approximate seed count or an exact or
approximate weight in `g` or `mg`, using the useful SeedLot quantity concepts. Examples include
`30 seeds`, `about 30 seeds`, `0.5 g`, and `about 200 mg`. Unknown is represented by absence of the
quantity value, not by zero. Counts are whole numbers; known count or weight values are strictly
positive because sowing zero material is never meaningful. Ranges are deferred.

Creating or editing a Sowing must not silently deduct from or otherwise alter its SeedLot quantity.
The SeedLot amount and quantity sown may differ in approximation, unit, or update time, so automatic
subtraction could manufacture precision. A future workflow may offer a separate explicit,
reviewable SeedLot update, but `SOWING-001` defines no quantity ledger, movement transaction, or
automatic accounting behavior.

### Simple germination summary and integrity

An optional `germinated_count` is the current simple summary, not dated observation history. The
operator may update it from `3 germinated` on day 5 to `11 germinated` on day 10. When known, it is a
non-negative whole number. `GERMINATION-001` may later add optional dated observations and derive
cumulative germination, first germination, percentages, timing, and T50 without invalidating this
basic workflow.

When quantity sown is an exact seed count, `germinated_count` must not exceed that count: 15 of an
exact 20 is valid and 21 is not. An approximate count, weight, or unknown quantity is not a
trustworthy denominator. A simple germinated count remains valid in those cases, but Florabase must
not claim a precise germination percentage. Derived statistics require sufficient evidence and
belong to the later germination capability.

### Lifecycle and retention

The first operator-controlled, correctable lifecycle vocabulary is:

- `active`: the Sowing is still monitored or managed;
- `completed`: the operator considers the sowing process complete;
- `failed`: the attempt concluded unsuccessfully; and
- `abandoned`: the operator intentionally stopped or discarded the attempt.

Lifecycle is not inferred from germination count. Zero germinated does not automatically mean
failed, some germination does not automatically mean completed, and an incorrectly entered outcome
can be corrected. Normal product behavior does not destructively delete Sowings; completed, failed,
and abandoned attempts remain available as historical collection evidence.

### Current Location and cultivation details

An optional `location_id` references the existing collection `Location` for the Sowing's current
physical position, such as `House → Germination cabinet`, `Greenhouse → Upper shelf`, or
`Indoor grow rack`. It is distinct from the SeedLot's storage Location, material provenance,
Supplier geography, and botanical native range. Changing it must not move or otherwise mutate the
SeedLot. The first record stores current state only; movement history is deferred.

The first cultivation description remains deliberately small and optional:

| Concept                | Representation and boundary                                                                                                                                 |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Substrate              | Operator text such as `coco coir + perlite`, `seed compost`, or `sphagnum`; no taxonomy                                                                     |
| Method/container       | Concise operator text such as `covered tray`, `zip-bag method`, `7 cm pot`, or `direct sowing`; no container inventory                                      |
| Pretreatment           | Operator text such as `scarification`, `24 h soak`, `cold stratification`, or `GA3`; no treatment taxonomy                                                  |
| Temperature            | Independently optional structured minimum and maximum decimal values in degrees Celsius; when both are known, minimum must be less than or equal to maximum |
| Environment/conditions | Operator text such as `bright indirect light`, `heated propagator`, `dark until emergence`, or `high humidity`                                              |
| Notes                  | Optional multiline Sowing-specific observations that do not duplicate BotanicalProfile reference guidance                                                   |

Either temperature bound may be absent when genuinely unknown. Celsius is the persisted product
unit; Fahrenheit storage, presentation conversion, and environmental sensor integration are
deferred. These editable fields describe current or best-known state rather than maintaining a
version for every edit.

### Plant, lineage, observations, and attachment boundaries

Germination does not automatically create a persisted `Plant` or `PlantGroup`. The explicit workflow
remains `SeedLot → Sowing → Plant / PlantGroup`: Sowing retains the propagation attempt and its
result, while later Plant/PlantGroup workflows decide when established material becomes a collection
plant record. Plants or groups created from a successful Sowing retain that Sowing as provenance
where known, while unknown and historical relationships remain valid. No implicit transition,
destructive merge, Plant persistence, or generic genealogy graph belongs here.

The first Sowing is an editable current record with a simple germination summary, not a full event
history. Dated germination observations are deferred to `GERMINATION-001`.

Sowing is an appropriate future attachment/photo target for its initial container, emergence,
progress, failure symptoms, or treatment comparisons. The existing attachment architecture must own
uploaded/local media and external image references. This contract adds no image column, file store,
URL, attachment relationship, or API.

### Contextual field help

Future collection forms follow a layered help principle: ambiguous domain fields receive a short
inline explanation; examples or extra detail may use a small accessible information control; and
genuinely complex concepts may link to deeper Florabase Help or glossary content. Information
controls must work by keyboard and focus, expose screen-reader context through appropriate
`aria-describedby` or accessible popover semantics, and never rely on hover alone. Ordinary form
completion must not require external documentation, while self-explanatory fields should not gain
noisy help chrome.

Likely candidates include material provenance versus storage Location, Supplier versus source,
approximate quantity, Sowing lifecycle, germinated count, current Location, and partial-date
precision. `UX-002` retains this P2 implementation need without blocking the P1
SeedLot-to-Sowing-to-Plant path; no help UI is implemented by this contract.

## Plant and PlantGroup contract

`Plant` and `PlantGroup` are two concrete collection concepts with related workflows. They are not
variants of a generic polymorphic `CollectionItem`, and this contract introduces no inheritance or
base-table design.

A `Plant` is one individually tracked living or historical specimen, such as one avocado tree, one
tamarillo, or one specimen extracted from a formerly grouped batch. The record itself always means
exactly one specimen, so Plant has no quantity.

A `PlantGroup` is multiple individuals intentionally managed as one collection record, such as 12
tamarillo seedlings, approximately 30 young Albizia plants, or a tray whose seedlings are not worth
tracking separately yet. Every group contains material of exactly one `BotanicalIdentity`.
Mixed-species beds and generic collection containers are not PlantGroups.

Each Plant and PlantGroup has its own stable, application-generated UUIDv7. Labels, locations,
quantities, and botanical names never identify or merge records. Each record references exactly one
existing `BotanicalIdentity`, which remains authoritative for its scientific and cultivar names;
Plant and PlantGroup do not duplicate those names as authoritative text.

### Minimum records and labels

Incomplete and historical collection entry is first-class. The minimum product workflow for either
concept requires only one `BotanicalIdentity`. Behind that workflow, the record also has its stable
UUID, defaultable operator-controlled lifecycle, and implementation-managed timezone-aware UTC
creation and update timestamps. Origin, label, collection-entry date, Supplier, material
provenance, current Location, notes, and group quantity may all remain unknown. Plant additionally
has no quantity field.

This permits a BotanicalIdentity-only old Plant, a nursery Plant with Supplier but unknown
provenance, a group with unknown original quantity, or a historical record with incomplete lineage.
The operator must not invent a SeedLot, Sowing, date, location, or quantity merely to save it.

An optional short, non-unique operator label supplies display context only. Examples include
`Avocado #1`, `Tamarillo mother plant`, `Tamarilli 2026`, and `Tray A`. It is neither stable identity
nor a generic tag system.

### Origin and provenance routes

Where known, a PlantGroup or a Plant created directly from propagated material may originate from
exactly one existing `Sowing`. An extracted Plant instead has one originating PlantGroup and no
duplicated Sowing origin. The explicit workflow remains
`SeedLot → Sowing → Plant / PlantGroup`, but no relationship is inferred from a shared
BotanicalIdentity. One Sowing may eventually result in zero, one, or many Plants, one or more
PlantGroups, or a mixture as tracking changes. Germination does not create either record
automatically; creation is a deliberate collection-management decision.

When no workflow parent—Sowing or, for an extracted Plant, PlantGroup—is known, the record supports
one small direct-origin value:

- `purchased`: acquired as an already living Plant or PlantGroup;
- `gift_exchange`: received from another person or exchange;
- `collection_produced`: produced within the operator's collection without a recorded Sowing,
  including incomplete historical workflows or propagation capabilities that do not yet exist;
- `other`: another known direct route, optionally clarified by short text; and
- `unknown`: the route is not known.

This vocabulary does not include `self_collected`, customizable enums, or a generic propagation
material hierarchy. Until `CUTTING-001` and `TUBER-001` provide dedicated workflows, an incomplete
historical or vegetatively propagated record may legitimately use `collection_produced` or
`unknown` without being forced through SeedLot or Sowing.

Directly acquired records may independently reference an optional `Supplier` and an optional
`GeographicPlace` for material provenance. These answer different questions:

- Supplier: who or what supplied the living material?
- Material provenance: where did the biological material originate, grow, or get collected?
- Current Location: where is this Plant or PlantGroup physically kept now?

For example, a purchased Musa may name a nursery Supplier, Thailand as material provenance, and
`Greenhouse → Shelf 1` as current Location. None substitutes for another. A known Sowing already
provides a route to upstream SeedLot facts, so its Supplier and provenance are not copied onto the
Plant merely for convenience. The lineage contract defines how those explicit upstream
relationships fit together; the Plant contract does not persist them.

### Collection-entry date and current Location

An optional collection-entry date records when the specimen or group entered, or began being
tracked in, the collection. It preserves the established partial-date precisions: year, year and
month, or complete date. Thus `2022`, `2024-05`, and `2026-08-31` remain distinct claims, and an
unknown month or day is never manufactured. This neutral date is not automatically acquisition,
Sowing, germination, or biological birth, and it does not claim biological age.

An optional `Location` is the current physical cultivation or storage position, such as
`Garden → South bed`, `Greenhouse → Shelf 2`, or `House → South window`. Missing Location is valid.
The first contract stores current state only. Editing it must not mutate a Sowing or SeedLot
Location; meaningful movement history belongs to the later event workflow.

### Plant lifecycle

Plant uses exactly these operator-controlled, correctable states:

- `active`: the specimen is currently maintained as part of the collection;
- `dead`: the specimen died;
- `lost`: the specimen can no longer be located or accounted for; and
- `discarded`: the operator intentionally removed or disposed of it.

State is not inferred from dates, observations, or upstream records. Historical Plants remain
retained and are not normally hard-deleted.

### PlantGroup lifecycle and quantity

PlantGroup uses these operator-controlled, correctable states:

- `active`: the group is still maintained together;
- `completed`: the group is intentionally no longer managed as that group, for example because its
  members moved into other tracked records or the grouped phase ended;
- `dead`: the group ended through mortality;
- `lost`: the group can no longer be located or accounted for; and
- `discarded`: the operator intentionally removed or disposed of the grouped material.

No state is destructive deletion, and state is not inferred automatically from quantity.

Group quantity is optional and supports only an exact whole-number individual count, an explicitly
approximate whole-number individual count, or unknown. Known positive values describe examples such
as `12 plants` or `about 30 plants`; unknown remains absence, not a fake value. Weight and ranges are
not supported.

Exact zero is meaningful only when the group is historical and the operator genuinely knows no
tracked individuals remain. It is valid with `completed`, `dead`, or `discarded`. `active + 0`, any
approximate zero, and every negative value are invalid. An inactive group may instead retain unknown
quantity when its final count is unknown; lifecycle never manufactures zero. In particular, `lost`
does not mean zero: a lost group retains a positive last-known count or unknown quantity, never an
invented zero. `PLANT-002` must express these same rules coherently at PostgreSQL and application
boundaries.

Alembic revision `20260831_0011` implements this first persistence boundary with separate `plants`
and `plant_groups` tables. Both retain their own required BotanicalIdentity and may independently
reference one Sowing, Supplier, material-provenance GeographicPlace, and current Location through
restrictive foreign keys. A Sowing origin excludes all direct-origin provenance, while full PUT can
atomically correct between those final states. Protected collection and detail routes live at
`/api/v1/plants` and `/api/v1/plant-groups`; responses resolve compact reference summaries, retain
inactive history, and do not mutate upstream Sowing or SeedLot accounting. This revision adds no
PlantGroup extraction, collection-producer lineage, event, attachment, deletion, or frontend
workflow.

### Individual extraction and lineage boundary

A PlantGroup may later yield one or more individually tracked Plants. The new Plant preserves its
originating PlantGroup so known provenance can be followed through
`Plant → PlantGroup → Sowing → SeedLot`; extraction never erases or rewrites the group's origin.
This is a real workflow relationship, not an arbitrary graph edge.

The atomic operation that reduces group quantity, creates the Plant, records extraction provenance,
and handles concurrency belongs to `PLANT-004`. This contract defines only the provenance
requirement. It does not define a transaction schema or implement extraction. More broadly,
`LINEAGE-001` owns the explicit `SeedLot → Sowing → Plant / PlantGroup`,
`PlantGroup → extracted Plant`, and Plant/PlantGroup producer to collection-produced SeedLot
contract. Later capabilities own persistence and traversal. Unknown links remain optional; no
generic graph, relationship-type registry, or genealogy engine is introduced.

### Notes, current state, events, and photos

Optional multiline notes contain facts specific to that Plant or PlantGroup, such as identifying
characteristics, unusual growth, acquisition context, or incomplete history. They do not duplicate
general BotanicalProfile cultivation or reference knowledge by design. A statement about this
specimen flowering is collection evidence; a statement about what the species generally prefers is
BotanicalProfile knowledge.

The first records contain current or best-known label, source, Supplier, provenance, Location,
quantity, lifecycle, and notes. Ordinary edits do not create generic versions. Meaningful
chronological movement, repotting, flowering, fruiting, pruning, treatment, harvest, death or loss,
and free observations belong to `EVENT-001` and `EVENT-002`.

Plant and PlantGroup are future first-class photo/attachment targets for whole specimens, organs,
symptoms, or developmental stages. Uploaded/local media and external image references follow the
existing attachment architecture, and a future inventory may use an optional primary or cover
image. `ATTACHMENT-003` owns those relationships and presentation semantics. This contract adds no
image column, URL, upload, storage, or attachment relationship.

### Fast entry and contextual help

Future fast entry leads with BotanicalIdentity and may immediately offer label, originating Sowing,
originating PlantGroup for an extracted individual, or direct origin; current Location and group
quantity appear where applicable. Additional provenance, Supplier, date, lifecycle, and notes can
be progressively available. Selecting a known workflow parent should make lineage easy without
requiring duplicated upstream information. `PLANT-003`, not this contract, owns the UI.

Layered help is especially useful for Plant versus PlantGroup, direct origin versus originating
Sowing or PlantGroup, Supplier versus material provenance, provenance versus current Location,
approximate group quantity, lifecycle, and collection-entry date. Concise inline text comes first;
an accessible
keyboard-, focus-, and screen-reader-compatible information control may provide examples; deeper
Help or glossary content is reserved for genuinely complex concepts. `UX-002` owns implementation,
and no help UI is added here.

## Collection-workflow lineage contract

Florabase lineage records explicit material provenance created by real collection workflows. It
answers which SeedLot a Sowing used, which Sowing produced a Plant or PlantGroup, whether an
individual Plant was extracted from a PlantGroup, and which tracked Plant or PlantGroup produced a
collection SeedLot. It is not a taxonomic hierarchy, synonym graph, family-tree abstraction, event
system, or arbitrary relationship framework.

The primary propagation chain is:

```text
SeedLot → Sowing → Plant / PlantGroup
```

Every arrow is a known direct material relationship. Missing history is represented by an absent
optional link, never by inference or a synthetic placeholder.

### Explicit relationships and cardinalities

- Every Sowing originates from exactly one SeedLot. A SeedLot may have zero, one, or many Sowings.
  `seed_lot_id` must not become optional, and intentionally combining multiple SeedLots in one
  Sowing is outside the current contract.
- A Plant may originate directly from at most one Sowing. One Sowing may produce zero, one, or many
  Plants.
- A PlantGroup may originate from at most one Sowing. One Sowing may produce zero, one, or many
  PlantGroups.
- A Plant deliberately separated from a PlantGroup records that one PlantGroup as its direct
  material origin. It does not also persist the group's Sowing merely to duplicate an ancestor.
- A PlantGroup cannot originate from another PlantGroup; hierarchical groups are not introduced.

A Sowing may produce Plants, PlantGroups, both, or neither. Plant and PlantGroup origin links are
optional so imported, historical, or directly acquired records remain valid without fake Sowings.
The atomic extraction operation, grouped-quantity reduction, concurrency behavior, and any related
event belong to `PLANT-004`, not this contract.

### Immediate-origin exclusivity and direct origin

A Plant has at most one immediate workflow parent: one originating Sowing, one originating
PlantGroup, or none. `originating_sowing_id` and `originating_plant_group_id` must never both be set
on the same Plant. For an extracted Plant, upstream material is followed through
`Plant → PlantGroup → Sowing → SeedLot` where those links are known; an additional direct Sowing
or SeedLot edge would be redundant and could contradict the group.

A PlantGroup has at most one originating Sowing or no workflow parent. When no workflow parent is
known, Plant and PlantGroup may use the direct-origin metadata defined by the Plant contract.
Direct origin is root-level provenance metadata, not another graph edge. When workflow lineage is
known, upstream Supplier, GeographicPlace provenance, or SeedLot facts are reached through that
lineage and are not silently copied into descendants.

### Collection-produced SeedLots

A SeedLot with `source_kind = collection_produced` may record at most one known collection producer:
one Plant or one PlantGroup. Both at once are invalid. A PlantGroup is a valid producer when seeds
were collected from a managed group but the producing individual is unknown; Florabase must not
require a fictional Plant.

The relationship means that the identified tracked Plant or PlantGroup is the collection material
from which the seeds were harvested or produced. It does not model maternal and paternal pairs,
pollen donors, controlled crosses, multiple contributors, parentage percentages, or a breeding
pedigree. For an open-pollinated fruit collected from Plant A, Plant A is the one known producer and
the pollen parent remains unknown.

Producer lineage and SeedLot source answer different questions. `source_kind` records how material
entered the SeedLot workflow; the producer link records which tracked collection material produced
it. A historical `collection_produced` SeedLot with no known producer is therefore valid. A known
producer should be semantically compatible with collection production, but attaching one must not
silently rewrite `source_kind`; later persistence/API work must validate the complete proposed
state explicitly.

### BotanicalIdentity independence

Lineage records physical history, not equality of `BotanicalIdentity`. Identity equality is not a
condition for any lineage relationship, including SeedLot to descendant Plant, PlantGroup to
extracted Plant, or producer Plant/PlantGroup to produced SeedLot. Material may be reidentified more
precisely as it develops, for example `Solanum sp.` at SeedLot stage and `Solanum quitoense` for a
mature Plant.

Changing or correcting a BotanicalIdentity assignment does not change lineage. Correcting lineage
does not change BotanicalIdentity, and neither operation silently copies or rewrites the other fact.
A future UI may show an informational mismatch warning, but a difference alone does not invalidate
the known material relationship.

### Direct edges, unknown history, and corrections

Only immediate relationships are persisted. For
`SeedLot A → Sowing B → PlantGroup C → Plant D`, Plant D needs only its direct PlantGroup origin;
it does not duplicate Sowing B or SeedLot A. A Plant directly from Sowing B does not duplicate
SeedLot A because Sowing owns that relationship. Later traversal may derive ancestors without
denormalizing them.

Future traversal may follow the same direct links upstream from Plant through an originating group
or Sowing to SeedLot and, when present, its collection producer. It may follow them downstream from
a producer through produced SeedLots and Sowings to resulting Plants or PlantGroups. `LINEAGE-001`
defines those semantics only; `LINEAGE-002` owns concrete authorized traversal APIs and completion
behavior, while `LINEAGE-003` owns visual navigation.

Unknown lineage is legitimate for Plants, PlantGroups, and collection-produced SeedLots. Known
parts of a chain remain recorded even when other parts are absent. Florabase never infers or
reparents lineage from BotanicalIdentity, dates, labels, Location, Supplier, quantities, or similar
names. Operator corrections are explicit current-state edits; audit/version history is deferred.

### Retention and acyclicity

Lineage survives lifecycle changes. Exhausted SeedLots, failed or completed Sowings, dead, lost,
discarded, or completed Plants and PlantGroups, and producers that later become inactive remain
valid historical ancestors. Retirement of a referenced Supplier, Location, or other supporting
reference record also does not invalidate lineage. Lifecycle transitions must not cascade-delete
provenance.

The workflow direction is acyclic by construction:

```text
producer Plant / PlantGroup → SeedLot → Sowing → Plant / PlantGroup
```

A descendant may later produce another SeedLot, continuing the generation chain, but no record may
become its own ancestor. In particular, an extracted Plant cannot use a PlantGroup that is already
downstream of that Plant through collection-produced material. Concrete persistence tasks must
choose the smallest safe enforcement for the relationships they own; this contract introduces no
generic cycle engine.

### Ownership and deferred behavior

The small relational ownership boundary is:

- Sowing owns its required SeedLot relationship in `SOWING-002`;
- Plant and PlantGroup persistence owns their applicable Sowing origins in `PLANT-002`;
- the extracted Plant's PlantGroup relationship and transaction belong to `PLANT-004`; and
- `LINEAGE-002` completes the single Plant-or-PlantGroup producer relationship for
  collection-produced SeedLots and supported upstream/downstream traversal.

These relationships must use explicit aggregate-owned foreign keys and integrity constraints where
implemented. A polymorphic `lineage_edges(source_type, source_id, destination_type, destination_id,
relationship_type)` table, generic genealogy engine, or speculative relationship vocabulary is
outside the contract. Lineage itself is structural provenance, not a PlantEvent; photos and
attachments may document related records but never form lineage.

`LINEAGE-001` is documentation only. It adds no persistence, migration, API route, Plant/Sowing
backend slice, traversal endpoint, extraction transaction, event history, or frontend navigation.
Likely future layered-help topics include Originating Sowing, Extracted from PlantGroup, Collection
producer, BotanicalIdentity differences across known lineage, and direct origin versus workflow
lineage. `UX-002` owns that accessible help implementation.

## BotanicalProfile aggregate contract

A `BotanicalProfile` is the current operator-maintained reference text answering **what general
information is known about this BotanicalIdentity?** It belongs to exactly one existing
`BotanicalIdentity`. A BotanicalIdentity may exist without a profile, and the first product model
allows at most one current manual BotanicalProfile for each BotanicalIdentity. A profile cannot
move to or survive independently of its BotanicalIdentity.

It does not answer **what happened to my particular seeds or plants?** That question belongs to
collection records and events even when a collection observation may be botanically interesting.

This is a product-level aggregate and cardinality decision, not a persistence design. `PROFILE-002`
will decide whether the profile has its own UUID primary key, uses `botanical_identity_id` as its
primary key, or uses another equivalent relational representation. No second independent manual
profile, history/version model, or source-enrichment representation is implied.

BotanicalProfile extends an identity with general knowledge; it does not rename or duplicate the
identity. The BotanicalIdentity canonical `display_label` remains the title. Scientific, common,
and cultivar names stay in BotanicalIdentity rather than being copied into the profile.

### Shared scope and authorization boundary

BotanicalProfile is deliberately installation-wide shared botanical reference data, like
BotanicalIdentity. It is not initially user-owned, has no `user_id`, and does not represent one
operator account's private observation. This explicitly resolves the mutable-aggregate scope
required by ADR 0005 before schema creation.

Shared scope is not unrestricted write access. Future profile mutations require an authenticated
actor and explicit authorization. A later multi-user capability may decide who may edit shared
reference knowledge without changing the profile into a private collection record.

### First content sections

The first profile has only these five manually editable free-text sections:

| Section               | General reference meaning                                                                                                        |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `description`         | Botanical description, habit, characteristic appearance, lifecycle, or other concise identifying or general information          |
| `origin_distribution` | Native origin and/or general geographic distribution of the botanical identity                                                   |
| `cultivation`         | Broadly applicable guidance about light, water, soil or substrate, temperature, climate, propagation, or other cultivation needs |
| `uses`                | Culinary, ornamental, traditional, practical, or other general uses                                                              |
| `warnings`            | Known toxicity, handling cautions, invasive potential, or other relevant general warnings                                        |

There is no generic `notes` section in the first contract: general reference knowledge already has
a clear home in these sections, while a catch-all would make it too easy to mix collection evidence
into the profile.

Every section is individually optional. Partial entry is normal and the operator may record any
subset without completing unrelated sections. A BotanicalProfile exists only when at least one
section contains meaningful text; the product does not preserve an entirely empty shell. Creating
a profile therefore requires at least one provided section. Clearing an optional section is
allowed, and clearing the final populated section makes the BotanicalIdentity have no current
profile. `PROFILE-002` will choose the persistence and API mechanics for that outcome without
changing this product rule.

At the product-contract boundary, surrounding whitespace is trimmed and blank or whitespace-only
content means not provided. Normal Unicode text, punctuation, capitalization, paragraphs, and
useful line breaks are preserved. Control characters other than meaningful text formatting are
rejected. The safe first assumption is plain text: Markdown or HTML is not rendered as trusted
content. Generous implementation-safety bounds may be selected in `PROFILE-002`; this contract does
not invent small limits or database constraints.

### Boundary from collection records and observations

BotanicalProfile contains general reference knowledge, not facts about the operator's particular
seeds, plants, or events. It must not contain:

- seed quantity, acquisition information, Supplier, storage location, or collection lineage;
- the geographic provenance of a particular SeedLot;
- sowing dates, germination observations, repotting, death, or loss;
- actual conditions experienced by a plant;
- flowering or fruiting observed in this collection; or
- photographs of a particular specimen.

`origin_distribution` describes the botanical identity's general native origin or geographic
distribution. For example, “Native to the Andean regions of Colombia, Ecuador and Peru” is profile
knowledge, while “Seeds collected near Quito” is provenance of one SeedLot and belongs to that
collection record.

Likewise, `cultivation` is general guidance such as “Prefers warm conditions and protection from
frost.” Collection evidence such as “This specimen survived 4 °C in greenhouse on 12 January”
belongs to the relevant Plant observation or event. Collection evidence must not silently become a
general claim merely because it may later inform one.

The optional `warnings` section is informational botanical reference content. Its absence does not
assert that a plant is safe, edible, or non-toxic, and its presence does not constitute medical,
veterinary, pesticide, or guaranteed-safety advice.

### Manual authorship and future enrichment

The first BotanicalProfile is operator-authored. The operator may write or summarize knowledge from
books, websites, nursery information, personal botanical knowledge, or other references. This text
remains identifiable conceptually as operator-authored and does not pretend to be authoritative
taxonomy. Structured citations and external-source provenance are not part of the first persisted
profile contract.

Future `ENRICHMENT-001` data is a separate, source-scoped concern. When a concrete source is selected,
its identity must be retained; retrieval time and external identifiers may also be retained when
useful. Source-derived content must not silently overwrite operator-authored profile text. Conflicts
must remain reviewable or otherwise distinguishable, and operator-authored text must remain
identifiable as such. These rules do not add speculative profile fields such as `wikipedia_url`,
`gbif_id`, `powo_id`, `fetched_at`, or `source_json`; enrichment will design its own representation
after source licensing, terms, attribution, API availability, and data quality are reviewed.

### Editing and display semantics

The future protected interaction must let an authorized operator create the one profile when none
exists, read it, update individual sections, clear an optional section, and preserve its
BotanicalIdentity relationship. The profile is the current reference text; history/versioning is
deferred until a concrete workflow needs it. This contract defines no routes, HTTP verbs, request
schemas, UI layout, or persistence mechanics.

Incomplete sections should simply be absent or empty in a future display. The UI should not pressure
the operator to complete all sections, editing should remain straightforward, and profile reference
knowledge must be visually distinguishable from later collection observations. The canonical
BotanicalIdentity `display_label`, not profile content, identifies and titles the plant.

### Deferred structured facts

The first profile deliberately does not split knowledge into structured fields for minimum
temperature, USDA zone, exact hardiness, mature height, soil pH, light, watering, flowering month,
lifespan, growth rate, edibility, or toxicity. Nor does `cultivation` become separate light, water,
soil, temperature, climate, or propagation columns. A fact becomes structured only when a concrete
workflow needs filtering, sorting, comparison, validation, or analysis. Until then, useful manual
knowledge capture takes priority over speculative precision and one-field-per-fact design.

## Readiness for the next increments

### `PROFILE-002`

The first protected persistence/API/UI increment uses `botanical_identity_id` as the profile's
primary key and foreign key. Its nested authenticated `GET` and owner-authorized `PUT` expose the
current one-to-one resource; `PUT` creates or fully replaces the optional sections, while clearing
the final section deletes the row and returns HTTP 204. Each section is plain text bounded at 20,000
characters. Outer whitespace is trimmed, CRLF is normalized to LF, meaningful internal whitespace
and line breaks are preserved, and unsupported controls are rejected. PostgreSQL independently
enforces the parent, cardinality, per-section storage rules, and nonempty-profile rule.

The integrated BotanicalIdentity UI labels the profile as general reference knowledge, explicitly
separates it from observations about particular collection material, and describes cultivation as
general guidance rather than recorded measurements or outcomes. External enrichment, structured
botanical facts, collection observations, and history remain outside this increment.

### `DATABASE-001`

One focused Alembic migration can create only `botanical_identities` with the six fields above, a
UUIDv7 primary key, UTC `timestamptz` timestamps, bounded/nonblank/normalized text checks, and the
composite case-insensitive unique invariant. Future foreign keys should be named
`botanical_identity_id`. No taxonomy hierarchy, synonym, external-identifier, SeedLot, Plant, or
other botanical table belongs in that migration.

### `BACKEND-001`

The canonical resource path for the authenticated REST slice is
`/api/v1/botanical-identities`. It should provide these semantics:

- **Create:** accept `scientific_name` plus optional `cultivar_name` and `common_name`; reject unknown
  or read-only fields; normalize before validation/persistence; generate UUIDv7 and timestamps in
  the application; return the created representation and a location for its UUID.
- **Read:** return one BotanicalIdentity by UUID with all six fields and the canonical display label
  either derived by the client or exposed as an explicitly derived response field. It must not be
  persisted.
- **Validation failure:** return the project's standard FastAPI validation response for blank,
  malformed, control-containing, or overlong input. Invalid UUID path input is also a validation
  failure.
- **Conflict:** map both a friendly duplicate pre-check and the authoritative unique-constraint race
  to HTTP 409 with one stable, non-sensitive error shape and the existing BotanicalIdentity UUID
  when safe.
- **Not found:** a well-formed UUID with no active BotanicalIdentity returns HTTP 404 with a stable,
  non-sensitive error shape.

This canonical internal resource terminology does not prescribe the eventual user-facing frontend
label.

`BACKEND-001` implements this create/read slice after the verification of `DATABASE-001` and
`SECURITY-002`. This contract does not authorize an unauthenticated botanical endpoint.

## Deliberately deferred

The following need concrete workflows before they become fields, tables, or services: parsed genus
and specific epithet, authoritative family, author citation, synonym/name history, external taxonomy
source identifiers, taxonomic rank columns, hierarchy or Tree of Life data, fuzzy search, accepted
name synchronization, localization, generic metadata, and every future collection entity named at
the start of this document.
