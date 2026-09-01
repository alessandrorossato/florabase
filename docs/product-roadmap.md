# Product roadmap

Florabase will grow from the canonical `BotanicalIdentity` reference into a useful personal
collection manager through small, dependency-aware capabilities. This roadmap records approved
product boundaries and sequencing; it does not choose database columns, API shapes, or user
interface layouts for future entities.

## Product principles

1. Partial data entry is normal.
2. Optional information remains optional unless identity or integrity requires it.
3. Florabase never invents precision the operator does not know.
4. Historical records are preserved rather than normally deleted.
5. The source and provenance of collection material remain traceable.
6. Descent through collection workflows remains traceable.
7. General botanical knowledge is separate from collection observations.
8. External enrichment supplements operator-authored data; it never silently replaces it.
9. `BotanicalIdentity` remains a small shared reference concept.
10. Generic infrastructure and abstractions wait for a concrete, repeated need.
11. The primary product experience becomes collection- and activity-centric as those workflows
    become available; reference-data directories remain supporting administration surfaces.

## Long-term information architecture

The current top-level Botanical identities, Suppliers, Locations, and Geography directories are
necessary foundation and reference-data administration surfaces. They are not intended to remain
the primary focus of Florabase. Once the core collection workflows exist, primary navigation and
workflows should emphasize the Dashboard, SeedLots, Plants and PlantGroups, Sowings and germination,
acquisitions or Orders, and collection activity/history such as movement, repotting, observations,
and harvest.

Reference directories remain available for maintenance, correction, and deliberate administration,
but become secondary to the records and activities the operator manages day to day. Where a
concrete workflow justifies it, reference data may also be selected or created in context—for
example, selecting an existing Supplier or creating one while recording a SeedLot acquisition—so
the operator does not have to abandon the current task. The same pattern may later apply to
BotanicalIdentity, Location, or GeographicPlace, but only when the owning workflow defines its
validation and interaction needs. Contextual creation must reuse each reference resource's normal
API and validation boundary; it must not introduce coupled nested writes owned by SeedLot, Plant,
CuttingLot, or another collection record.

This is sequencing guidance, not a redesign of the current navigation. `UX-001` becomes actionable
only after the SeedLot, Sowing, and Plant/PlantGroup interfaces exist; it does not authorize dead
navigation, speculative screens, or contextual-creation mechanisms during foundation work.

## Capability boundaries

`BotanicalIdentity` answers: **What botanical identity does Florabase assign to this material?** Its
verified six-field contract remains unchanged. Quantity, acquisition, provenance, storage,
cultivation, observations, photos, and lineage belong to collection capabilities that reference its
stable identifier.

`BotanicalProfile` answers: **What general information is known about this botanical identity?** Its
first increment is a small, manually editable, incomplete-friendly profile rather than one field per
possible botanical fact. Later structured facts require a concrete filtering or comparison
workflow.

Collection records answer: **What material exists, where did it come from, and what happened to it
here?** A `SeedLot` is one physical packet or bag, even when another packet has the same identity and
supplier. A `Sowing` records one intentionally managed, internally homogeneous attempt using
material from exactly one SeedLot. Separate initial treatments or broadly different conditions are
separate Sowings. `Plant` represents exactly one individually tracked specimen and has no quantity;
`PlantGroup` represents multiple individuals of one BotanicalIdentity intentionally managed as one
record. They remain distinct concrete concepts rather than a polymorphic collection-item hierarchy.
Their observations are collection evidence, not reference facts in BotanicalProfile.

`Supplier` records from whom or where material was obtained. It may represent a seller, nursery,
supermarket, person, or exchange source. Geographic origin records where material was collected or
originally sourced. They are distinct and independently optional.

`Location` is a simple parent-child hierarchy used where appropriate for stored material and
cultivated plants, such as `Home / Greenhouse / Shelf 2` or `Refrigerator / Seed box A`. It is not a
generic asset-location framework.

## Product-level data contracts

Dates may be exact or explicitly incomplete, such as a year or a year and month. The product
contract therefore carries the value the operator knows together with its stated precision; it does
not fill an unknown month or day. Acquisition date and production or harvest date are separate
concepts. The representation in PostgreSQL and APIs will be decided by the first concrete contract
and schema task that needs partial dates.

Material quantity is optional and may be an exact or approximate count or weight. Examples include
`20 seeds`, `approximately 300 seeds`, `2.5 g`, and `approximately 0.8 g`. A later contract will
choose supported units and validation without assuming every material item can be counted.

Origin vocabularies remain owned by their concrete workflow rather than forming one generic enum.
SeedLot distinguishes purchased material, material extracted from purchased fruit, personal
collection, production by the operator's plants, and gift or exchange. A directly entered living
Plant or PlantGroup instead uses purchased, gift or exchange, collection-produced, other, or unknown.
In every workflow the category, optional Supplier, optional geographic origin, and explicit lineage
relationships answer different provenance questions.

Inactive states are historical outcomes, not deletion instructions. Exhausted SeedLots, failed
Sowings, dead or lost Plants, completed PlantGroups, and consumed material remain available for
statistics, provenance, lineage, observations, and collection history.

## Major workflows

### External seed to cultivated plant

1. Find or create a BotanicalIdentity.
2. Record one SeedLot for each physical packet or bag, with incomplete and optional details allowed.
3. Record a Sowing using material from that SeedLot without silently deducting its recorded quantity.
4. Record a simple total germination result, or later add dated germination observations.
5. Continue successful material as one or more Plants or PlantGroups while retaining its origin.
6. Add lightweight history, observations, locations, and photos without altering reference data.

### Collection-produced descendants

When a tracked Plant or PlantGroup produces seed, the resulting collection-produced SeedLot may
record that one Plant or PlantGroup as its known collection producer. A group is valid when the
operator knows the managed group but not the individual producer; unknown production history also
remains valid. Maternal/paternal pairs, pollen donors, controlled crosses, and multiple contributors
are deferred. A later Sowing and its resulting Plants or PlantGroups continue the chain. Lineage is
formed by direct relationships created by these real workflows; Florabase does not need a generic
graph or genealogy engine.

### Individual and group tracking

Plants worth individual attention are recorded as `Plant`; batches are recorded as `PlantGroup`.
Either can be entered with BotanicalIdentity alone when its history is unknown, can retain one known
originating Sowing, or can use the small direct-origin vocabulary when no workflow parent is known.
An extracted Plant instead records its one originating PlantGroup and does not duplicate that
group's Sowing or SeedLot ancestors. Direct Supplier, material provenance, and current Location
remain independent optional facts. Extracting an
individual from a PlantGroup will preserve the originating group and upstream provenance while
reducing the grouped quantity. The detailed extraction transaction is Phase 2 so the first
PlantGroup capability can stay small.

### Other propagation material

`TuberLot` and `CuttingLot` are planned as parallel material workflows leading toward cultivated
plants. They are not SeedLots, and cuttings or tubers are not Sowings. Similar interaction patterns
may be reused, but a shared `PropagationMaterial` inheritance or base-table design will be considered
only if concrete implementations demonstrate a repeated need.

## MVP

MVP is a sequence of usable increments, not one release-sized feature:

- the existing BotanicalIdentity contract, persistence, authenticated API, and accessible UI;
- a small manually maintained BotanicalProfile;
- a Supplier/source directory and simple Location hierarchy;
- one-record-per-packet SeedLots with optional, precision-preserving dates, quantity, provenance,
  storage, notes, and lifecycle state;
- Sowings with quick basic entry and optional cultivation details;
- simple germination totals, with advanced observations remaining optional;
- individually tracked Plants and grouped Plants;
- explicit workflow lineage from SeedLot through Sowing to Plant or PlantGroup, from PlantGroup to
  an extracted Plant, and from one Plant or PlantGroup producer to collection-produced SeedLots;
- lightweight plant history and observations;
- historical retention across material and cultivation records; and
- attachment storage followed by photos linked to appropriate collection records or history.

The MVP backlog is represented by `DATABASE-001`, `SECURITY-002`, `BACKEND-001`, `FRONTEND-001`,
`PROFILE-001`–`PROFILE-002`, `SUPPLIER-001`, `LOCATION-001`, `SEED-001`–`SEED-004`,
`SOWING-001`–`SOWING-003`, `PLANT-001`–`PLANT-003`, `LINEAGE-001`–`LINEAGE-002`,
`EVENT-001`–`EVENT-002`, and `ATTACHMENT-001`–`ATTACHMENT-003`. Existing verified foundation,
security-decision, domain-contract, and testing items remain prerequisites rather than new work.

### Future collection photos

The existing `ATTACHMENT-001`–`ATTACHMENT-003` sequence owns future photo support; it remains P2 and
does not move ahead of the Seed, Sowing, and Plant product path. Photos are expected first for
`SeedLot`, `Sowing`, `Plant`, `PlantGroup`, and collection history or events where a concrete workflow
justifies the relationship. Every collection record must remain complete and usable without an
image.

Future design must keep two concepts distinct:

- An **uploaded/local image** is managed by Florabase attachment storage. Attachment work owns file
  validation, durable storage, authorization, size and type limits, deletion and lifecycle behavior,
  and coordinated backup and restore.
- An **external image reference** is an optional source/reference URL to an image available on the
  internet, not trusted local attachment content. It may carry source or attribution and a caption.
  Design must account for changed or broken links, privacy and security when loading third-party
  media, and an explicit choice between fetching/proxying thumbnails and linking without fetching.

An appropriate collection entity may later designate one related image as its primary or cover image
for compact inventory views. Persistence and lifecycle mechanics for that designation remain deferred
until the attachment relationship is implemented. Florabase must not add a one-off `image_url` field,
download remote images implicitly, or hotlink arbitrary third-party media as a shortcut.

## Phase 2

Phase 2 deepens established workflows without changing the MVP boundaries:

- dated germination observations and derived statistics when enough data exists;
- Orders and purchases distinct from lots and suppliers;
- richer PlantEvent workflows;
- Plant extraction from PlantGroup with preserved lineage;
- TuberLot and CuttingLot workflows;
- QR codes and labels;
- dashboards, collection statistics, and advanced search/filtering;
- collection-first navigation and contextual reference-data workflows after the core collection UI
  exists;
- safe installability of the authenticated web app as a mobile PWA;
- layered, accessible contextual field help after the owning collection forms exist;
- guided tabular import with preflight preview and human-oriented export for supported core records;
- visual lineage navigation; and
- assisted, reviewable BotanicalProfile enrichment with source provenance.

The Phase 2 backlog is `GERMINATION-001`, `PWA-001`, `ORDER-001`, `EVENT-003`, `PLANT-004`,
`TUBER-001`, `CUTTING-001`, `LABEL-001`, `SEARCH-001`, `DASHBOARD-001`, `UX-001`, `UX-002`,
`IMPORT-001`, `LINEAGE-003`, and `ENRICHMENT-001`.

`PWA-001` is intentionally an installability and reliable application-shell increment, not an
offline-first data system. It must not claim offline mutation or synchronization. Any future offline
writes require a separate contract for queued writes, conflicts, stale data, authentication expiry,
replay and idempotency, and multi-device changes before implementation.

## Phase 3

Phase 3 adds integrations and advanced analysis only after the local workflows are proven:

- automated refresh of source-scoped enrichment;
- assisted taxonomic reconciliation;
- synonyms and botanical name history;
- weather integration;
- reminders and calendar workflows;
- comparative cultivation analysis;
- advanced full-fidelity collection transfer;
- other automation and integrations; and
- multi-user capabilities when a concrete ownership and collaboration requirement exists.

The Phase 3 backlog is `ENRICHMENT-002`, `TAXONOMY-001`–`TAXONOMY-002`, `WEATHER-001`,
`REMINDER-001`, `ANALYSIS-001`, `TRANSFER-001`, `INTEGRATION-001`, and `SECURITY-003`.

Before any enrichment implementation, source licensing, terms, API availability, attribution, and
data quality must be reviewed. Wikipedia/Wikidata, Kew Plants of the World Online, GBIF, and other
authoritative sources are candidates, not selected integrations. `ENRICHMENT-001` covers
source-scoped, reviewable BotanicalProfile proposals; later `TAXONOMY-001` remains a separate
BotanicalIdentity reconciliation workflow and must not be collapsed into basic profile enrichment.

`IMPORT-001` is the guided operator workflow for documented tabular input, validation and preview,
clear row-level errors, and simple exports of explicitly supported core records. It may add a useful
structured JSON export, but does not claim to preserve every reference, lineage edge, provenance
detail, lifecycle fact, or attachment. `TRANSFER-001` remains the later advanced Florabase-to-
Florabase transfer contract for that high-fidelity collection scope. Neither is a substitute for
the separately documented backup and restore process.

## Dependency direction and recommended order

The recommended implementation sequence is:

1. `DATABASE-001` — persist only the verified BotanicalIdentity contract.
2. `SECURITY-002` — implement the accepted owner/session architecture.
3. `BACKEND-001` — expose the authenticated BotanicalIdentity REST slice.
4. `FRONTEND-002` — provide browser owner login, session restoration, CSRF recovery, and logout.
5. `FRONTEND-001` — provide the first BotanicalIdentity interaction.
6. Define the small BotanicalProfile, Supplier, Location, SeedLot, Sowing, Plant/PlantGroup, lineage,
   and event contracts before each corresponding schema change.
7. Implement Supplier and Location reference slices, then SeedLot persistence, API, and UI.
8. Define Sowing and Plant/PlantGroup, then define their explicit workflow lineage; implement Sowing
   and basic germination before Plants and groups.
9. Add lightweight plant events and historical views.
10. Complete `ATTACHMENT-001`, implement guarded storage, then relate photos to collection records and
    events.
11. Take Phase 2 and Phase 3 items one at a time in dependency order.

The SeedLot, Sowing, Plant/PlantGroup, and explicit lineage contracts and their first concrete
backend/UI increments through `LINEAGE-002` are verified. Collection-produced SeedLots can reference
one known Plant or PlantGroup, and authenticated typed traversal follows the supported workflow
relationships without generic graph infrastructure. `EVENT-001` remains the dependency-unblocked P1
contract task; `PLANT-004` is now dependency-unblocked at P2. No next feature is selected here.

## Deliberately deferred

This roadmap does not decide future table layouts, partial-date storage, quantity-unit persistence,
PlantGroup extraction transactions, event subtype storage, ownership beyond accepted boundaries,
attachment polymorphism, or enrichment APIs. It does not introduce a generic material hierarchy,
event-table family, location framework, graph engine, scheduler, background worker, or integration
framework. Each decision belongs to the first small workflow that genuinely needs it.
