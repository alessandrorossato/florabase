# Product roadmap

Florabase grows through small, dependency-aware increments. This roadmap communicates direction;
[`features.json`](features.json) remains the detailed source for status, dependencies, priority, and
acceptance criteria.

## Product principles

- Partial information is normal, and Florabase does not invent precision.
- Botanical reference knowledge stays separate from collection observations.
- Supplier, collection Location, and geographic provenance answer different questions.
- Historical records and explicit workflow lineage are preserved.
- Ordinary journal Events and authoritative domain operations have distinct mutation semantics.
- Generic infrastructure waits for a demonstrated repeated need.
- The initial product serves one self-hosted owner through a same-origin web application.

## Verified foundation and collection core

The repository now contains a production-oriented Compose topology, PostgreSQL migrations, guarded
backup/restore, local owner sessions, a typed API, an accessible React application, and generated API
contracts.

The verified product supports BotanicalIdentity and BotanicalProfile, Supplier, Location,
GeographicPlace, SeedLot, Sowing with simple germination totals, Plant, and PlantGroup. Explicit
lineage covers SeedLot through Sowing to Plant/PlantGroup, one-at-a-time PlantGroup extraction, and a
Plant or PlantGroup producing a collection-produced SeedLot. The verified EVENT-001 backend adds
typed, partial-date Plant/PlantGroup history with creation-time movement and lifecycle effects.
Inactive records retain history.

This is substantial pre-release functionality, not a declaration of a stable first release.

## First usable release direction

UAT of the verified collection core exposed a more immediate P1 product sequence before release
readiness:

1. `PROPAGATION-001`: define and expose explicit quantity accounting and lifecycle transitions
   across SeedLot, Sowing, and Plant/PlantGroup creation (verified);
2. `PROPAGATION-002`: present those operations as guided contextual transitions and cross-links
   (verified);
3. decide the operator-approved licensing and release/version policy;
4. complete release readiness as a separate release increment.

`PROPAGATION-001` now implements the domain/backend contract without a migration: explicit focused
operations distinguish no adjustment, partial use, and use-all; lock mutable sources; preserve
exact, approximate, and unknown quantity semantics; make Sowing lifecycle outcomes explicit; and
derive descendant accounting only from stored lineage. Corrections remain direct and do not replay
past effects, and propagation does not automatically emit Events. `PROPAGATION-002` now supplies
natural next-step actions from BotanicalIdentity, SeedLot, and Sowing contexts, two-stage source
usage confirmation, explicit Sowing outcomes, authoritative descendant summaries, and restrained
clickable propagation paths. Direct creation and correction remain available, completed Sowings
remain historical, and richer germination observations remain deferred.

`CI-001` now supplies the repository-side pull-request verification and repeatable feature-branch
workflow. The active `Protect main` ruleset requires its `quality`, `integration`, and `build` checks,
and repository merge settings permit squash auto-merge while disabling merge commits and rebases.
`CI-002` makes the final feature verification and protected delivery mechanics deterministic while
leaving independent implementation review as a human/model judgment.

EVENT-001 covers practical movement, repotting, flowering, fruiting, pruning, treatment, harvest,
death/loss/discarded, transfer, extraction, and free observations without separate speculative
tables. Event creation can
atomically change current Location or lifecycle, but later Event edits/deletion never replay or roll
back current state: Florabase is not event-sourced. Collection evidence stays separate from
BotanicalProfile knowledge. EVENT-002 adds the shared protected Plant and PlantGroup journal UI: an
API-ordered vertical desktop timeline that becomes wrapping cards on mobile, lightweight All,
Observations, Cultivation, and Status filters, and accessible create/edit/delete flows. Transfer is
classified as Status and extraction as Cultivation. Creation
effects and historical edit/delete non-rollback behavior are explicit. Further structured payloads beyond
movement destination, transfer recipient, and the extraction-result Plant relation remain deferred;
attachments also remain deferred.

Attachment storage and photos are valuable but currently P2. Whether they are mandatory for the
first public release is an explicit operator/product decision; this roadmap does not silently make
every P2 item release-critical.

## Later collection enhancements

Planned P2 work deepens existing workflows: guarded attachment storage and photos, dated germination
observations, Orders, richer events, tuber and cutting lots, labels/QR lookup, advanced search,
analytical dashboards, contextual form help, guided import/export, visual lineage, and reviewable
profile enrichment.

PWA work means installability and a safe application shell, not offline-first mutation,
synchronization, push, or a native mobile app. Those behaviors require separate contracts.

`UX-001` establishes the collection-first application structure: a persistent grouped desktop
sidebar, five-destination mobile bottom navigation, an authoritative current-collection Dashboard,
a global Event timeline, and a BotanicalIdentity hub that aggregates Seeds, Sowings, Plants,
PlantGroups, and Events. Major record details share breadcrumbs, visible Edit actions, tabs, cards,
and responsive states. Botanical identity aggregation is explicitly not lineage. `DASHBOARD-001`
still represents later analytical/statistical work; `UX-002` still represents layered contextual
help within forms.

The longer product/UX direction is an understandable collection lifecycle:
`BotanicalIdentity → SeedLot → Sowing → Plant / PlantGroup → Events / terminal state`. This is a
workflow narrative over explicit records, not a new persisted super-entity and not permission to
infer missing lineage. `UX-003` will revisit Seeds, Sowings, Plants, Events, and their detail pages
after the guided transitions exist, improving page purpose, consistent actions, cross-linking, and
mobile/desktop navigation without changing what the verified `UX-001` increment delivered.

`PLANT-005` implements transferred/ceded outcomes for Plants and entire PlantGroups. A locked focused
operation atomically records the transfer Event and lifecycle, with optional free-text recipient,
partial date, and notes; transferred records remain historical and direct lifecycle edits remain the
correction path. Partial group transfer is deliberately absent: the operator extracts one Plant,
then transfers it. Extraction now atomically records a source-group Event with a structured link to
the resulting Plant. Event edits and deletes never replay or reverse either operation. `LOCATION-002` retains one
Location concept while adding usage-scoped Seeds, Sowings, and Plants views plus an accessible
collapsible hierarchy. `SUPPLIER-002` may add connected-record summaries, but financial totals wait
for the separate `ORDER-001` transaction model.

The remaining V1 surface order is `LOCATION-002`, `GEOGRAPHY-003`, `SUPPLIER-002`, then the
botanical/map increments. `UX-003` follows those feature-specific surfaces as global stabilization
and polish; it is not a prerequisite for their implementation.

### Reversible authoritative operations

Before `LOCATION-002` or further geography work is selected in product sequencing, Florabase should
complete a small reversible-workflow path: `REVERSAL-001` then `PLANT-006` and
`PROPAGATION-003`. This is sequencing, not a new technical prerequisite for Location or geography:
their existing feature-graph dependencies remain unchanged.

`REVERSAL-001` now provides the persistence foundation: each newly executed SeedLot-to-Sowing,
Sowing-to-Plant or PlantGroup, PlantGroup extraction, and Plant or PlantGroup transfer writes one
immutable relational receipt in the same transaction. Its controlled kind, status, source/result
identities, one-to-one operation-owned Event link, and typed before/expected-after lifecycle and
quantity snapshots are fixed original facts. The migration deliberately creates no receipts for
historical operations. This is not a general Event log: current aggregate rows remain authoritative,
ordinary direct corrections remain corrections, and journal Events still do not replay.

Receipts have no generic JSON/custom metadata and no public creation, update, or delete API.
Operation-owned Events reject ordinary deletion so the application cannot imply that state was
reversed; ordinary Events keep their existing deletion semantics. `PLANT-006` now supplies the one
focused extraction-reintegration inverse. Other reverse quantity mutation and propagation undo
remain in `PROPAGATION-003`; there is still no generic Undo API or Event replay.

The numerical rule is restoration, not reverse arithmetic. An exact SeedLot can therefore round
trip `100 → use 20 → 80 → undo → 100`, and an exact PlantGroup can round trip
`10 → extract 1 → 9 → undo → 10`. A partial-use estimate such as `~100 → ~80` restores its
recorded `~100` snapshot; it never computes a value by adding a delta. Unknown remains unknown.
Undo accepts only the recorded quantity kind and unit, so count and weight (including `g` and `mg`,
for which no conversion contract exists) cannot be mixed.

`PLANT-006` is deliberately narrow: it reinserts the particular Plant created by a particular
recorded extraction into that Plant's original PlantGroup. The approved representation retains the
individual historically with its origin, lineage, prior Events, and explicit non-active
`reintegrated` lifecycle. It restores the group before-snapshot from the receipt without inverse
arithmetic, marks that receipt reversed, retains the original extraction Event, and adds exactly one
group-targeted reintegration Event linked to the Plant. There is no paired Plant-targeted Event,
hard deletion, arbitrary group assignment, merge, split, bulk reintegration, or lineage rewrite.

Eligibility is safe only while the resulting Plant and source group still match the receipt and
have no dependent facts. Ordinary observation, flowering, and fruiting Events are the narrow
confirmation-required class and remain historical. Lifecycle, identity, Location, transfer,
produced SeedLot, downstream lineage, manual source-group correction, or later group operation is a
typed block. The API and UI show the original group and these reasons; concurrent requests serialize
on the receipt and affected rows. A future extraction creates a new Plant rather than reactivating
the reintegrated record.

`PROPAGATION-003` adds focused receipt-proven reversals for SeedLot-to-Sowing and Sowing-to-Plant
or PlantGroup. New typed result snapshots prove lifecycle, quantity, identity, Location, and date;
legacy receipts without those snapshots are explicitly non-reversible and are never backfilled.
Reversal restores the source BEFORE snapshot without inverse arithmetic and retains the result
permanently as `reversed`, distinct from extraction's `reintegrated`. It preserves lineage and
informational history, requires downstream-first causal ordering, and never cascades. SAFE,
CONFIRMATION_REQUIRED, and BLOCKED outcomes support contextual detail actions; repeated forward work
creates a new record. No propagation journal Event, generic undo API, or receipt CRUD is introduced.

Undo is dependency-aware. It may proceed automatically only when the receipt remains applied and
every affected record still has the recorded post-operation state with no later dependent work. A
later non-state-changing observation may be presented as a confirmation-required retained fact when
the selected operation contract can preserve it honestly. Later lifecycle or Location changes,
transfer, a new extraction, manual identity or quantity correction, any descendant or produced
SeedLot, later Sowing/Plant/PlantGroup propagation, or another operation using the same mutable
source blocks automatic undo and must be resolved first. Confirmation is never an override for a
referential or numerical invariant.

For transfer, the inverse restores the lifecycle captured in the transfer receipt; it must not
assume `active`, even though the current forward contract admits only active targets. It is allowed
only while the target is still in the recorded transferred state and has no incompatible later work.
The recipient remains historical metadata in the receipt. The transfer Event is removed from the
active journal or archived only inside the same successful inverse transaction; the receipt retains
the audit evidence of the original action and its undo.

The eventual UI boundary is explicit: an ordinary Event continues to offer **Delete event**, which
changes only that journal item. An Event linked to an applied operation offers **Undo action**. That
request calls the authoritative inverse first; only a successful atomic inverse may remove or archive
the operation-owned Event. The UI must never delete such an Event and imply that the associated
current state was reversed when it was not.

Geography remains precision-preserving and extensible. `GEOGRAPHY-003` adds descriptive custom
city/town, locality, and other named-area descendants beneath the preserved canonical World-rooted
hierarchy without shipping a global city catalogue. Precise collection origin is represented by the
separate `ProvenanceSite` concept with optional WGS84 coordinates and accuracy. This internal data
prepares MAP-001 without implementing maps, geocoding, external providers, or the independently
planned GEOGRAPHY-002 botanical native-distribution relationships.

## Longer-term capabilities

P3 work includes automated enrichment refresh, assisted botanical identity reconciliation and name
history, weather context, reminders, comparative analysis, full-fidelity collection transfer,
external integrations, and multi-user collaboration. External data sources require licensing,
terms, availability, attribution, and quality review before selection.

## Deliberate boundaries

Florabase does not currently provide Event attachments, analytical dashboards, advanced collection
search, offline writes, import/export, a generic
propagation-material hierarchy, a generic graph engine, or multi-user ownership. Future work should
extend concrete workflows without weakening unknown-data, history, authorization, or provenance
semantics.
