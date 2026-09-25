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

This is substantial pre-release functionality, not a declaration of a stable first release. The
first distributable pre-1.0 release is planned as `0.1.0`; a future `1.0.0` remains a stability
milestone after real-world use and compatibility expectations mature. The older **V1 scope** names a
broader product direction, not the `0.1.0` release boundary.

## Florabase 0.1.0 release boundary

Florabase is ready for `0.1.0` when it can hold and operate a real personal botanical collection
without the operator reasonably fearing data loss, an unusable core workflow, or an undocumented
deployment or upgrade path. Advanced botanical enrichment, automatic taxonomy reconciliation, every
propagation material type, advanced analytics, multi-user collaboration, generic integrations, and
full offline synchronization are outside that criterion.

### Required before 0.1.0: PERF-001 and RELEASE-001

[`PERF-001`](features.json) is the planned P0 resource-efficiency increment after the operator
freezes product scope. It will **measure → identify demonstrated hotspots → optimize → re-measure**
representative production-like workflows, including startup and idle use; Dashboard; collection and
reference directories/details; Events, Photos, and lineage; provenance and explicitly loaded
occurrence maps; and a create/edit path. The baseline will inspect CPU, memory, startup, transfer and
chunk cost, requests, queries, response timing, media and map loading, and production image/process
footprint. It will investigate the current Vite chunk-size advisory against actual initial-load
cost, not change the warning threshold to hide it. It will also inspect repeated navigation and
idle use for resource growth. Changes must address measured problems without weakening product
semantics, security, privacy, reproducible builds, or operability. The same workload will be
re-measured and practical expectations for modest self-hosted hardware documented; no arbitrary
CPU, RAM, or hardware guarantee is set at planning time. This prevents avoidable resource problems
from first surfacing in an operator's deployment.

[`RELEASE-001`](features.json) is the planned P0 release-hardening increment. It is the release
acceptance gate after `PERF-001`, not a claim that hardening or release acceptance has already passed.
Its contract covers:

- Clean installation and upgrade of an existing installation through the production Compose topology
  and full Alembic chain; health/readiness, owner bootstrap, login/logout/session behavior,
  production-safe configuration, and browser use after upgrade.
- Complete recovery of PostgreSQL data **and** local attachment binaries, including their metadata
  correspondence, into an isolated fresh environment with usable collection records. A PostgreSQL
  dump alone is not a complete backup once attachments exist.
- Real end-to-end UAT: BotanicalIdentity and optional cover/profile/reference → SeedLot with Supplier,
  provenance, and Location → Sowing → Plant/PlantGroup → Events and Photos → transfer/extraction →
  supported reversal or reintegration → maps and history navigation.
- Security sanity for owner bootstrap, session restoration and expiry/invalidation where practical,
  CSRF, exact Origin, attachment/binary authorization, production cookies/origin, and existing
  insecure-configuration startup rejection. This extends verification, not the auth architecture.
- Browser review at desktop, intermediate, and about 390×844 mobile sizes; keyboard and focus,
  dialogs, menus, forms, maps with accessible companion lists, and key error/empty/loading states.
  This is a practical review, not a claim of formal WCAG certification.
- Representative API, provider, occurrence-map, external-image, missing-binary, validation/conflict,
  empty-data, and implemented stale-source failures. Final performance/resource sanity checks that
  the release candidate remains within documented `PERF-001` expectations, has no material
  regression, and shows no obvious runaway CPU, memory, or request behavior. The primary measurement
  and optimization work belongs to `PERF-001`.
- Accurate clean-system installation, environment, origin, storage, backup/restore, upgrade, and map
  instructions; coherent `0.1.0` version surfaces, pre-1.0 upgrade expectations, and a first
  changelog entry. Current-state prose must match the feature graph and merged code. Final UAT defects
  and small blocking polish should be fixed without starting another redesign.

This planning increment defines the contracts only. Resource measurement and optimization belong to
`PERF-001`; release tooling, drills, documentation rewrite, and hardening belong to `RELEASE-001`.

### Selected before 0.1.0

The operator has selected `IMPORT-001`, `SEARCH-001`, `GERMINATION-001`, `LABEL-001`, and
`ATTACHMENT-004` for implementation before scope freeze. `ATTACHMENT-004` covers one explicitly
selected primary associated photo on a SeedLot, Plant, or PlantGroup; it does not include Sowing or
change BotanicalIdentity cover behavior. Selection does not make any of these release dependencies.

### Product candidates and boundaries

The table records the selected work above alongside the remaining optional candidates. None blocks
`PERF-001`, `RELEASE-001`, or `0.1.0`. `PERF-001` measures whichever product scope the operator
freezes for `0.1.0`.

| Candidate         | Pre-release value and boundary                                                                                                                                                                                 |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `IMPORT-001`      | Guided documented CSV import with validation, dry-run preview, unresolved-reference handling and no silent guesses; simple human-readable CSV export. Separate from backup/restore and full-fidelity transfer. |
| `SEARCH-001`      | Filter implemented structured collection fields while keeping reference knowledge distinct from collection records; no speculative search engine or natural-language search.                                   |
| `LABEL-001`       | Printable physical labels and QR lookup using stable, non-secret record references and normal authorization; QR codes carry no session credentials.                                                            |
| `GERMINATION-001` | Optional dated observations alongside existing simple totals; derive percentages, timing or T50 only from sufficient data.                                                                                     |
| `PWA-001`         | Installable shell, manifest/icons, safe service-worker caching and update behavior; no offline mutations, synchronization, push or native integrations.                                                        |
| `LINEAGE-003`     | Visual navigation of recorded explicit relationships, with no inferred ancestry or generic genealogy graph.                                                                                                    |
| `ORDER-001`       | Purchase transaction tracking, with Order distinct from Supplier and SeedLot.                                                                                                                                  |
| `DASHBOARD-001`   | Defined analytical statistics after richer data, including `GERMINATION-001`; distinct from the existing UX dashboard summary.                                                                                 |

`PWA-001`, `LINEAGE-003`, `ORDER-001`, and `DASHBOARD-001` are post-0.1.0 by default unless the
operator reprioritizes them. They are not release-readiness dependencies.

### Post-0.1.0 by default

- `BOTANY-003` remains `planned`, but does **not** block `0.1.0`. The confirmed exact provider path
  has not supplied eligible descriptive content under the accepted narrow contract. Source licensing
  and field-level capability must be adequate before retrieval resumes. Florabase must not use name
  rematching, arbitrary scraping, unsupported numeric crosswalks, or unreviewed source mixing to
  force enrichment. Resume only with a reviewed source, content, and provenance contract.
- `ENRICHMENT-001`/`ENRICHMENT-002` follow a reviewed retrieve → proposed values → source and
  provenance → operator review → selective apply path; manual BotanicalProfile data is never silently
  overwritten. Occurrence-map caching is a later optimization requiring bounded freshness, source
  and retrieval time, stale-state truthfulness, attribution, and licensing review.
- `EVENT-003` waits for real use to justify deeper structure. `TUBER-001` and `CUTTING-001` remain
  dedicated material workflows; cutting lineage records a parent Plant where known. Other bulbs,
  rhizomes, graft material, scions, and divisions need concrete workflows rather than a generic base.
- `TAXONOMY-001`/`TAXONOMY-002` require careful reconciliation, synonyms, and name history that
  preserve stable references. `WEATHER-001`, `REMINDER-001`, and `ANALYSIS-001` wait for concrete
  comparison, reminder, and sufficient-data use cases; reminders do not make a generic task manager.
- `TRANSFER-001` is full-fidelity collection transfer, distinct from simple CSV exchange and
  backup/restore. `INTEGRATION-001` waits for proven repeated automation workflows, and
  `SECURITY-003` for a real multi-user requirement.
- Full offline mutation and synchronization is a larger contract than `PWA-001` installability.
  Advanced media processing such as general derivatives, EXIF workflows, albums, photo ordering and
  version history also remains later work.

### Sequence to release

1. **Foundation complete:** UX-004, UX-005, and UX-006 have landed; their graph status remains
   `implemented` where recorded.
2. **Selected product work:** each of the five chosen increments receives its own implementation,
   relevant operator UAT, independent review, canonical verification, and delivery.
3. **Scope freeze:** after the operator declares pre-release product work complete, admit only
   release defects and agreed blocking polish.
4. **Resource baseline and optimization:** implement `PERF-001` with measurement, focused changes,
   and repeat measurement on the frozen product scope.
5. **Release hardening:** implement `RELEASE-001` against its full acceptance contract, including
   final resource sanity.
6. **Exploratory UAT:** use representative real workflows and data; correct concrete release defects.
7. **Release candidate validation:** repeat fresh install, upgrade, complete restore, production
   deployment, browser/mobile/accessibility, security, documentation, and version/changelog review.
8. **Tag/release `0.1.0`:** only after the exact release tree passes canonical repository gates.

## Delivered collection foundation

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
effects and historical edit/delete non-rollback behavior are explicit. Further structured payloads
beyond movement destination, transfer recipient, and the extraction-result Plant relation remain
deferred. Guarded local Attachment storage and explicit Event photo relationships are implemented.

Guarded attachment storage (`ATTACHMENT-002`) now provides the local durable binary foundation.
Collection photos (`ATTACHMENT-003`) add distinct local-upload and attributed external-reference
semantics for SeedLot, Sowing, Plant, PlantGroup, and Event without making any record depend on an
image. Galleries are available on each collection detail and contextually for Events. External
collection images require explicit browser loading and are never fetched by the backend. A separate
optional BotanicalIdentity representative cover may be locally managed or an explicitly configured
external HTTPS image; saving an external cover is informed opt-in to future browser requests on that
identity's detail page. Automatic discovery, provider-backed search, cover history, albums or
reordering, EXIF inspection, thumbnails, derivatives, background media workers, and
BotanicalIdentity galleries remain outside this increment.

## Collection capability and design context

The release groups above set the timing for planned work. The following detail records current
capabilities and design boundaries that those future increments must preserve.

PWA work means installability and a safe application shell, not offline-first mutation,
synchronization, push, or a native mobile app. Those behaviors require separate contracts.

`UX-001` establishes the collection-first application structure: a persistent grouped desktop
sidebar, five-destination mobile bottom navigation, an authoritative current-collection Dashboard,
a global Event timeline, and a BotanicalIdentity hub that aggregates Seeds, Sowings, Plants,
PlantGroups, and Events. Major record details share breadcrumbs, visible Edit actions, tabs, cards,
and responsive states. Botanical identity aggregation is explicitly not lineage. `DASHBOARD-001`
still represents later analytical/statistical work. `UX-002` adds layered contextual help within
forms without changing those domain or navigation contracts.

The product/UX direction is an understandable collection lifecycle:
`BotanicalIdentity → SeedLot → Sowing → Plant / PlantGroup → Events / terminal state`. This is a
workflow narrative over explicit records, not a new persisted super-entity and not permission to
infer missing lineage. `UX-003` now refines Seeds, Sowings, Plants, Events, and their detail pages
with lifecycle-ordered navigation, record-first labels, consistent headers and action priority,
accessible tab relationships, and direct links to stored identity, source, Location, Supplier, and
provenance context. Rare reversals and destructive actions remain separated from natural next-step
workflows. BotanicalIdentity reference data has its own lazy Reference tab, distinct from collection
aggregation and explicit lineage.

Compact BotanicalIdentity directory imagery follows a bounded rule: local covers use an
authenticated server-generated WebP thumbnail with a maximum 320-pixel edge, no upscaling, private
caching, and an attachment-digest validator. External covers use stored, explicitly configured URLs and render directly in visible browser
cards with lazy loading and a no-referrer policy. Browsers contact the configured host; Florabase
does not proxy, cache, discover, or choose external covers. Missing covers use a clean fallback. No generic transformation API,
persisted derivative, background worker, or automatic image discovery is introduced.

`PLANT-005` implements transferred/ceded outcomes for Plants and entire PlantGroups. A locked focused
operation atomically records the transfer Event and lifecycle, with optional free-text recipient,
partial date, and notes; transferred records remain historical and direct lifecycle edits remain the
correction path. Partial group transfer is deliberately absent: the operator extracts one Plant,
then transfers it. Extraction now atomically records a source-group Event with a structured link to
the resulting Plant. Event edits and deletes never replay or reverse either operation. `LOCATION-002` retains one
Location concept while adding usage-scoped Seeds, Sowings, and Plants views plus an accessible
collapsible hierarchy. `SUPPLIER-002` adds a focused Supplier hub with explicit direct-reference
counts, linked SeedLots and directly acquired Plants/PlantGroups, BotanicalIdentity context, and
precision-preserving recent acquisition summaries. Propagated or extracted descendants do not
inherit Supplier, retained historical records do not become active holdings, and financial totals
wait for the separate `ORDER-001` transaction model.

After the implemented collection, geography, supplier, provenance-map, external botanical-data,
structured native-range, MAP-002 occurrence-density, and ATTACHMENT-003 photo foundations,
`BOTANY-003` profile enrichment remains separately planned while the approved provider lacks a
reviewed profile-content contract. `UX-003` is
implemented as global stabilization and polish over those feature-specific surfaces. `UX-002` is
implemented as static local form guidance: concise described field help, accessible expandable
examples, and focused deep help for complex corrective operations. It adds no onboarding state,
backend help service, or change to the botanical, geography, map, or photo domain contracts.

`BOTANY-002` keeps Florabase BotanicalIdentity and BotanicalProfile data authoritative. GBIF is the
first fixed advisory provider, accessed only by the backend. Search results require explicit
operator confirmation before a provider taxon is linked; no match automatically renames, reparents,
merges, or enriches an identity. Provider responses are cached with truthful fetch/freshness
metadata, and botanical-name queries are disclosed as external requests. MAP-002 builds only on a
confirmed link: an explicit load sends the stored opaque Catalogue of Life XR taxon ID through the
backend for PRESENT occurrence counts and quality-filtered hex-density tiles. The map is not a
native-range surface, does not persist occurrences, and sends no collection metadata to GBIF.
Profile enrichment remains separately planned. Structured native ranges are separately
operator-managed BotanicalProfile knowledge and are never refreshed from GBIF occurrence evidence.

`UX-004` establishes the refreshed visual vocabulary with BotanicalIdentity as the reference:
separate directory, compact preview, dedicated detail, integrated covers, and Overview / Collection /
Reference / Events navigation. Its status is `implemented`, and the operator has accepted the reference direction after desktop
and mobile review. `UX-005` carries that vocabulary into Supplier, Location and Geography
management, adds a stored-coordinate Provenance-site map, and presents the separate collection
provenance map as a map-first record workspace. It retains explicit provenance and hierarchy
semantics. `UX-006` carries the same vocabulary into SeedLot, Sowing, Plant/PlantGroup, guided
propagation, collection Events, Photos, Lineage and Dashboard. The operator has accepted its general
design direction, and independent final verification has passed. See [the reference guide](ux-004-reference.md)
for the established patterns and review.
Possible later work is recorded without implementation: occurrence-map cache or persistence needs a
freshness, invalidation, licensing and privacy contract, and a post-0.1.0 **Retrieve botanical data**
action needs an approved provider-content and provenance contract before it can enrich a profile.
The approved release-hardening contract is now `RELEASE-001` above.

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
separate `ProvenanceSite` concept with optional WGS84 coordinates and accuracy. `MAP-001` uses that
internal data for an authenticated collection-provenance map with one marker per coordinate-bearing
site, filtered direct collection links, and an accessible companion list. It does not geocode,
derive coordinates, map Locations or Suppliers, or show the independent GEOGRAPHY-002
botanical native-distribution relationships or MAP-002 occurrence data. MAP-002 is instead a
BotanicalIdentity-context view of GBIF occurrence-record density for the confirmed external taxon.
Its browser loads provider data only through authenticated, fixed-purpose Florabase summary and tile
boundaries, while the existing configurable basemap behavior remains separate.

## Longer-term capabilities

P3 work includes automated enrichment refresh, assisted botanical identity reconciliation and name
history, weather context, reminders, comparative analysis, full-fidelity collection transfer,
external integrations, and multi-user collaboration. External data sources require licensing,
terms, availability, attribution, and quality review before selection.

## Deliberate boundaries

Florabase does not currently provide analytical dashboards, offline
writes, a generic
propagation-material hierarchy, a generic graph engine, or multi-user ownership. Future work should
extend concrete workflows without weakening unknown-data, history, authorization, or provenance
semantics.
