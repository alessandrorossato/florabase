# Domain model — Reference concepts

> Summary: BotanicalIdentity, external botanical references and occurrences, distribution, native ranges, profiles, taxonomy, suppliers, locations, and provenance.

This document describes the implemented Florabase model at Alembic head. The executable models,
migrations, Pydantic schemas, and tests remain authoritative when details differ.

Florabase separates shared botanical/reference knowledge from collection records. Partial knowledge
is valid: unknown dates, quantities, locations, suppliers, provenance, and lineage stay absent rather
than becoming invented placeholders.

## Reference concepts

### BotanicalIdentity

A BotanicalIdentity is the stable, installation-wide identity Florabase assigns to material. It has
an application-generated UUIDv7, required normalized scientific name, optional unquoted cultivar
name, optional common name, UTC timestamps, and optional duplicate-merge tombstone fields
(`merged_into_id`, `merged_at`). Scientific name plus cultivar is case-insensitively unique across
active (`merged_into_id IS NULL`) identities. Deletion is allowed only while an identity is unused,
unmerged, and has no reconciliation history; references from SeedLots, Plants, or PlantGroups produce
a domain conflict and no collection record is cascaded.

Per [ADR 0007](../../decisions/0007-accepted-name-reconciliation.md) (`TAXONOMY-001`), accepted-name
reconciliation is advisory until explicit operator confirmation. Inspecting an identity aggregates
advisory accepted-name suggestions and source/version conflicts across confirmed WFO links, confirmed
WCVP links, local WCVP `15`/`16` reference indexes, and confirmed GBIF external taxon links. Two
explicit operator actions are distinguished:

- **In-place accepted-name correction** updates the identity's current `scientific_name` (and optional
  `cultivar_name`/`common_name`) without changing its UUID or touching any `SeedLot`, `Plant`,
  `PlantGroup`, or `ScheduledActivity` foreign key. It never silently merges into an existing
  identity.
- **Explicit survivor duplicate-identity merge** repoints all holdings (`SeedLot`, `Plant`,
  `PlantGroup`, `ScheduledActivity`) transactionally to an operator-selected active survivor, unions
  `BotanicalProfileNativeRange` rows, adopts missing `BotanicalProfile` fields (refusing conflicting
  non-empty profile text unless `profile_resolution="keep_survivor"` is chosen) and missing cover/source
  links, and soft-retires the duplicate as a single-hop tombstone (`merged_into_id = survivor.id`,
  `merged_at = now`). Retained `NativeRangeProposal` and `NativeRangeApplication` receipts stay on the
  tombstone for `ENRICHMENT-001` auditability, and propagation reversal snapshot invariants remain
  unchanged.

Both reconciliation actions and ordinary `PUT /api/v1/botanical-identities/{id}` name edits append
superseded names to `botanical_identity_names` (`initial_recorded`, `former_accepted`,
`merged_duplicate`, `source_synonym`, or `operator_synonym`) and write immutable JSONB-evidenced receipts to
`botanical_identity_reconciliations` (protected by a PostgreSQL trigger against `UPDATE`/`DELETE`).
Global search matches historical names on active identities and includes the matched former name in
the result context while excluding retired tombstones from active directories, pickers, Explore, and
exports. Full manual synonym authoring (`TAXONOMY-002`) builds on `botanical_identity_names` later.

Collection records reference its UUID and do not copy botanical names as authoritative data.

### External botanical references

An optional provider taxon link associates a BotanicalIdentity with at most one current taxon per
stable provider ID. GBIF is the first supported provider. Its taxon key is stored as an opaque string
alongside link-time name, authorship, rank, status, accepted-name context, higher classification,
link time, last refresh attempt, and last successful refresh. The external reference is advisory:
search and match candidates require explicit operator confirmation, and linking, replacing,
refreshing, or unlinking never changes the BotanicalIdentity scientific name, cultivar, common name,
relationships, or BotanicalProfile.

GBIF access is backend-only and fixed to the documented API host. Matching selects the Catalogue of
Life eXtended Release with `checklistKey=7ddf754f-d193-4cc9-b351-99906754a03b`, following GBIF's
current taxonomy interpretation guidance; diagnostics and alternatives remain visible evidence, not
automatic authority. A trusted provider function constructs GBIF taxon-page URLs. API callers cannot
supply a provider host or URL.

Provider match and taxon responses are bounded and cached in PostgreSQL under deterministic request
keys. The default freshness period is one day and is configurable with
`FLORABASE_BOTANICAL_CACHE_TTL_SECONDS`; no scheduler or background refresh exists. A failed explicit
refresh retains cached link metadata, records the failed attempt, and identifies it as stale rather
than presenting it as newly fetched. Unlinking does not delete shared cache entries.

Only the searched botanical name or selected opaque taxon ID is sent to GBIF. Florabase sends no
account, note, Supplier, Location, ProvenanceSite, SeedLot, Plant, or other collection data during
link search and refresh. This foundation does not enrich BotanicalProfile, import native ranges, or
alter the MAP-001 collection-provenance map.

### External occurrence evidence

The MAP-002 occurrence view is live, source-scoped evidence for the exact current GBIF taxon link.
The backend supplies the stored opaque Catalogue of Life XR identifier directly to GBIF occurrence
search and Maps APIs with the fixed Catalogue of Life XR checklist key. It never rematches the
BotanicalIdentity scientific name, translates to the obsolete numeric GBIF Backbone, substitutes an
accepted taxon, or broadens the link. GBIF's own taxon-filter interpretation determines inclusion of
records classified beneath the selected usage.

The normalized summary reports all matching PRESENT occurrence records and the eligible mapped
subset. The subset requires usable coordinates and excludes records GBIF flags as having a
geospatial issue. Both live counts are retrieved independently and can change between requests;
the eligible count is the map's current reference. A deliberate operator action retrieves the summary, then a fixed-purpose,
authenticated Florabase endpoint proxies zoom-appropriate hex-binned raster tiles from GBIF. The
browser never receives an arbitrary provider URL and never sends the linked taxon directly to GBIF;
the server sends only the opaque taxon ID, fixed checklist and quality policy, and requested tile
coordinates. No Florabase user identity, collection record, provenance, Supplier, Location, note,
or physical browser location is sent. The separately configurable basemap retains MAP-001's direct
tile-request privacy boundary.

Occurrence density is record density, not plant abundance, and the raster does not expose exact
per-bin totals. Occurrences may be generalized, obscured, uncertain, erroneous, historical,
cultivated, or introduced and never establish native range. The view does not write occurrence facts
to BotanicalIdentity, BotanicalProfile, GEOGRAPHY-002 ranges, GeographicPlace, ProvenanceSite, or
collection records. Nothing is stored in PostgreSQL; provider and browser HTTP caching may apply.
GBIF and contributing publishers are attributed, and underlying records retain their
dataset-specific licences and attribution requirements rather than receiving a Florabase-wide
licence.

EXPLORE-001 reuses this exact component and provider path from the collection-aware
[Species distribution workspace](../../features/explore/species-distribution.md); discovery remains local until explicit Load.

### Collection-aware Species distribution

EXPLORE-001 derives represented identities from exact SeedLot/Plant/PlantGroup identity links,
Sowing → SeedLot and managed inventory → Harvest → source relationships. Living means active Plants
or PlantGroups. Current additionally includes active SeedLots, Sowings and active stored material
(including unknown remainder). Historical means retained evidence with no Current representation.
Terminal, reversed and reintegrated records remain evidence only; unmanaged Harvest quantities do
not confer inventory. Reference-only identities are excluded, and one identity appears once.
The [full lifecycle matrix and endpoint contract](../../features/explore/species-distribution.md) are authoritative.

The authenticated bounded projection is local and never calls a provider. Selection and private
Saved Views restore local state, while the shared MAP-002 component waits for explicit Load.
Occurrence-ready means an existing confirmed GBIF link, never a promise of actual records. No
collection-domain or occurrence persistence is introduced. Native ranges and Collection origins
keep their independent evidence and semantics.

### Collection-aware Native ranges

EXPLORE-002 reads the existing GEOGRAPHY-002 profile-owned structured relationships for
identities represented by the exact EXPLORE-001 projection. Collection overview counts distinct
identities per canonical territory drawing unit after union within each identity. Broad and
precise overlaps count once on the map, while the exact-place list retains every recorded link.
Selected species preserves exact paths, disjoint areas, custom/unmapped places and missing-range
states. Only structured links participate; origin_distribution prose, GBIF occurrences and actual
material origins are independent. Static Natural Earth boundaries are application presentation
data, never botanical assertions or persisted inferred descendants. See [Native ranges](../../features/explore/native-ranges-explore.md).

### BotanicalProfile

A BotanicalProfile is optional general reference knowledge for exactly one BotanicalIdentity. Its
identity foreign key is also its primary key, enforcing at most one profile. It is the aggregate for
meaningful profile-owned knowledge rather than only a text-section container. A profile exists while
it owns at least one populated text section or structured native-range relationship, and a deferred
database invariant rejects a completely empty profile at transaction completion.

The five optional text sections are description, origin/distribution, cultivation, uses, and
warnings. Adding the first native range atomically creates a profile when necessary, without
placeholder text. Clearing the last text section preserves a profile that still owns a native range;
removing its last range deletes the profile only when no text or other profile-owned data remains.
Profiles are operator-authored and distinct from observations of Plants or Sowings.

A structured native range records each exact GeographicPlace explicitly selected as an area where
the taxon is considered botanically native. A profile may retain zero, one, or many places at mixed
granularity. Ancestors, descendants, neighbors, and common ancestors are neither inferred nor
persisted as additional ranges; explicitly selected parent and child places may coexist. Paths are
derived from the current Geography hierarchy, so reparenting changes display without changing the
relationship. Existing profile origin/distribution text remains independent and is never silently
overwritten.

### Reviewable structured range proposals

ENRICHMENT-001 adds separate operator-confirmed WCVP links and frozen source proposals. Its exact
version-16 (default) and version-15 Native assertions use reviewed twelve-unit TDWG crosswalks; introduced, qualified,
partial and unresolved units remain source context. Only explicit selective Apply adds canonical
`BotanicalProfileNativeRange` links. Existing ranges and all profile text are kept. Immutable
application evidence retains original source assertions and mapping decisions independently of
replaceable source indexes and later manual range edits; it is not collection operational History.
A monotonic range revision plus locked identity/link/source/geography checks reject stale Apply.
Applied evidence restricts identity deletion. See [the contract](../../features/explore/native-range-enrichment.md).

### Approved BOTANY-003 contract — not implemented

The operator approved WFO / Flora of China general descriptions for `description` and Kew WCVP
`geographic_area` for `origin_distribution`; all other profile fields and structured native ranges
remain excluded. Retrieval must remain advisory, require exact provider-specific source confirmation,
and never create or edit a profile. Empty destinations require explicit Apply; populated destinations
require Current vs Proposed review and concrete Replace confirmation.

The approved persistence requirement is typed, append-only applied-value history retaining nullable
previous value, applied value and exact source/license/reference/release/application evidence. A
field-specific association with an application distinguishes current imported content from manual
content. Editing that field clears its association while preserving history; editing unrelated fields
does not clear it. Mutable retrieval cache and source links cannot replace this durable evidence.
Apply must reject stale destination state and stale proposals rather than overwrite intervening edits.

These structures and behaviors are not present in the implemented model. A fresh 2026-10-09
[source re-audit](../../features/explore/botanical-profile-enrichment-sources.md) reproduced secure WFO acquisition failure
on the host, existing backend images and the freshly built worktree backend. The issuing intermediate
is still absent from the observed served chain. A separate Kew SEPASAL review approved exactly three
Flora Zambesiaca description records. That narrow source GO is insufficient coverage for general
description enrichment. WCVP v15 geographic text remains a suitable candidate;
structured range proposals do not provide text application history or text revision safety.
No trust exception or placeholder implementation was introduced. The existing operator-authored
profile model above remains authoritative. See [the approved complete contract](../../features/explore/botanical-profile-enrichment.md).

Cultivation, uses and warnings remain manual pending BOTANY-004's exact field/source GO.
SEPASAL is an approved source for only those three description records; it is not an imported domain
source.

### Collection taxonomy

TAXONOMY-003 adds optional **WfoLink**: one operator-confirmed literal WFO name ID per
BotanicalIdentity, UUIDv7 relationship version, UTC confirmation timestamp, reviewed source release/
checksum/license/taxon/full-path evidence and the identity revision observed during confirmation.
PostgreSQL owns this relationship only; the complete provider taxonomy belongs to an optional
explicitly provisioned local SQLite reference index. Confirmation/unlink locks the identity and
compares expected relationship version; confirmation also revalidates identity revision and source.
Local names, profiles, source-provider links and collection material relationships remain independent.

Official WFO Plant List 2026-06 supplies direct accepted-concept parents. A linked source synonym
retains its literal identity and advisory accepted concept; no automatic reconciliation or name history
is implemented. All intermediate source ranks remain in evidence. A collection-pruned projection
includes only represented linked identities and required ancestors; each identity counts once per
ancestor. Scope/category eligibility comes from the existing Explore collection projection, including
Historical's global absence of Current evidence. Unlinked, stale, mismatched-release or unplaceable
identities remain visible unresolved; source absence/corruption never blocks ordinary workflows.

Explicit future source replacement cannot silently reinterpret reviewed links. A changed release,
checksum, identity revision or hierarchy requires operator review. Read-only identity breadcrumbs and
Related in my collection describe classification, without evolutionary-distance claims. Taxonomy is
separate from recorded collection **Lineage** and planned **PHYLOGENY-001**. TAXONOMY-001/002 and
BOTANY-003/004 remain planned. See [collection taxonomy](../../features/explore/collection-taxonomy.md) and
[exact source decision](../../archive/TAXONOMY-003/taxonomy-003-source.md).

### Collection phylogeny source gate

PHYLOGENY-001 remains planned after the [2026-10-09 source audit](../../archive/PHYLOGENY-001/phylogeny-001-source.md).
Current Open Tree API and actual pinned archive identify opentree16.1 / OTT 3.7draft3, but exact
current synthetic/annotation data-rights scope did not pass the requested review. No OTT link,
canonical phylogenetic state, schema, API or local source has been introduced. The
[planned contract](../../features/explore/collection-phylogeny.md) preserves explicit operator-reviewed mapping,
shared representation/category eligibility, distinct identities, cultivar/species sharing and
visible unresolved knowledge for later implementation. WFO confirmation never implies OTT mapping.
Taxonomic classification is not phylogeny, and neither describes recorded material Lineage.
Synthetic topology is not an evolutionary time estimate; no branch lengths or dates are inferred.

### Supplier

A Supplier is an installation-wide acquisition source such as a seller, nursery, supermarket,
person, exchange, or other source. Name is non-unique; stable UUID is identity. Optional website,
email, phone, and notes are descriptive. Retirement is non-destructive. Supplier answers who or what
supplied material, not where that material originated or where it is currently kept.

The Supplier hub derives connected material only from explicit `supplier_id` references on
SeedLots and directly entered Plants or PlantGroups. It reports active/current and retained-total
counts for each type, combines Plant and PlantGroup presentation under the established Plants UI,
and links every record and BotanicalIdentity. Propagated Plants and PlantGroups and extracted Plants
do not inherit their ancestor's Supplier, so lineage-derived descendants do not inflate direct
counts. Historical lost, discarded, exhausted, completed, dead, transferred, reversed, or
reintegrated records remain readable where a direct relationship can validly exist, but only the
`active` lifecycle contributes to current counts.

Recent acquisitions merge the existing SeedLot acquisition date and direct Plant/PlantGroup
collection-entry date, preserve their year/month/day precision, omit undated records from the
recency claim, and use record type and stable UUID as deterministic ties. Undated records remain in
the linked-material sections. Supplier retirement preserves every relationship and there is no
Supplier hard-delete workflow. The compact Orders section links to the exact Supplier-filtered
purchase directory. Transaction date/reference/price belong to [Order](../../features/sourcing/orders.md); Supplier material
counts and recency retain their existing meaning, without spending analytics.

### Location

A Location is a physical place inside the collection, such as `Greenhouse → Shelf 2` or
`Refrigerator → Seed drawer`. It is a non-unique named adjacency tree with optional parent and
non-destructive retirement. The API derives display paths, prevents cycles, blocks retirement while
active descendants exist, and blocks reactivation beneath retired ancestors.

Each Location explicitly enables one or more independent usage scopes: `plants`, `sowings`,
`seed_lots`, and `harvest_inventory`. The `plants` scope covers both Plant and PlantGroup. Scopes do not inherit through the
physical containment hierarchy. Every assignment is checked by backend domain logic, and a scope
cannot be removed while any current or historical record still uses it. Assignment selectors show
only compatible Locations and use the derived path to disambiguate repeated names.

Reparenting moves the subtree without changing collection assignments or scopes. A Location may be
deleted only when it is a leaf and no Plant, PlantGroup, Sowing, SeedLot, stored Harvest material, or Event history references
it; retirement remains the non-destructive choice for retained reference data. Renames and moves
change the current derived path. Florabase does not event-source historical Location names or paths.

Location collection usage distinguishes **Directly here** (current `location_id` equals this
Location) from **Including sublocations** (this Location plus every descendant at any depth).
SeedLot, Sowing, Plant, PlantGroup and managed Harvest material are counted separately as records, never quantities. Both
scopes retain every state in `total`. `active` includes active biological records and active inventory;
depleted inventory is excluded.
Retained historical records count only at their retained current assignment; Events, provenance,
identity, source records and lineage never supply or infer an assignment. Location eligibility scopes
do not inherit and never hide material assigned to eligible descendants beneath another scope.

The authenticated Location API preserves legacy `usage` as direct membership, including its combined
Plant/PlantGroup `plants` count. Additive `direct_usage` and `usage_including_descendants` summaries
separate `plants`, `plant_groups`, `sowings`, `seed_lots` and `harvest_inventory`, each with `active` and `total` counts.
All counts are derived at read time, not persisted. Reparenting immediately changes inclusive usage
and display paths without editing the records in the moved subtree. Independent roots stay isolated.
Assignment-scope removal and deletion continue to use direct references and existing child/history
guards; descendant totals do not change those policies.

The directory and compact preview show nonzero inclusive usage, add the direct count when it differs,
and show equal leaf counts once. Detail compares both scopes for all five supported record types,
including explicit zeroes and active counts. Location detail currently links to collection directories;
it does not list associated records, so LOCATION-003 introduces no record-list scope or default change.

Location answers where managed material currently sits. It is not geographic provenance.
It also does not identify a Supplier.

### GeographicPlace

A GeographicPlace represents provenance or distribution. The canonical hierarchy is installed from
the committed Unicode CLDR 48.2.1-derived snapshot and has stable source metadata; operators may add,
move, rename, retire, and reactivate custom descendants. Canonical nodes are immutable. Selecting one
node records the most precise known place and derives its ancestors without manufacturing greater
precision.

Current collection records use GeographicPlace for material provenance. BotanicalProfile uses the
same hierarchy for independently managed botanical native ranges; its exact-place associations do
not imply collection origin.

Custom GeographicPlaces may describe a city or town, locality, or another named local area. These
types are descriptive; parent links remain authoritative and impose no country-specific
administrative-depth rules. The one canonical World root and canonical CLDR nodes remain immutable,
while custom descendants can be renamed, reparented, retired, or safely deleted. Paths are derived
from current ancestry, so rename and reparent operations update every displayed descendant path.
No global city catalogue is bundled and no parent is inferred from a name.

### ProvenanceSite

A ProvenanceSite is a precise known real-world origin site, distinct from the named area represented
by GeographicPlace. It has a stable UUID, name, optional GeographicPlace, optional notes, and an
optional WGS84 decimal latitude/longitude pair. Both coordinates must be present together;
latitude is -90 through 90, longitude is -180 through 180, and optional accuracy is a non-negative
distance in metres. A site with unknown coordinates remains valid historical provenance. Florabase
does not fabricate coordinates from its parent place, geocode, or call an external service.

SeedLots and directly entered Plants or PlantGroups may reference a ProvenanceSite wherever they may
already record material provenance. Propagated and extracted records continue to derive origin from
their stored lineage rather than duplicating provenance. A referenced site cannot be deleted, and a
GeographicPlace cannot be deleted while children, ProvenanceSites, or direct collection references
depend on it. Reparenting a GeographicPlace changes the site's derived place path but never its
coordinates or collection relationships.

ProvenanceSite coordinates are the authoritative marker boundary for the MAP-001 collection
provenance map. One marker represents one coordinate-bearing site and may expose several directly
associated SeedLots, directly entered Plants, or directly entered PlantGroups. Retained historical
records remain provenance history with their actual lifecycle. Propagated and extracted descendants
do not acquire a duplicate direct site for map convenience, and Florabase never guesses coordinates
from a GeographicPlace name or centroid.

This map describes origins recorded for the operator's collection. It is not the independently
managed GEOGRAPHY-002 botanical native-range dataset or MAP-002 external occurrence-density view.
Location remains the current physical storage/cultivation place, and Supplier remains who supplied
the material. The map performs no geocoding, reverse geocoding, browser geolocation, or external
botanical lookup.

