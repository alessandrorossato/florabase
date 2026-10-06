# Product roadmap

Florabase grows through small, dependency-aware increments. This roadmap communicates direction;
[`features.json`](features.json) remains the detailed source for status, dependencies, priority, and
acceptance criteria.

## Current operator direction — October 2026

This section supersedes the older sequencing below. Historical 0.1.0 planning and RELEASE-001's
original acceptance contract remain useful records, but RELEASE-001 is not the immediate next
implementation. Product work continues in the approved sequence before final hardening and the
1.0.0 stability milestone. Feature statuses remain those in features.json, not inferred from delivery.

Already landed: core lineage integrity audit; LOCATION-003 (`implemented`); ATTACHMENT-005 shared
Media Library (`implemented`); HARVEST-001 (`implemented`); HARVEST-002 (`verified`); MAP-002
(`verified`); SEARCH-001 baseline (`implemented`); the UX-004/005/006 visual consistency work
(`implemented`); and PERF-001 (`verified`). Older selected/next wording below describes its original
planning period and does not supersede this direction.

HARVEST-003 is landed and `verified`. SUPPLIER-003 Supplier imagery / practical Reference
completion is independently verified after operator visual UAT passed. It uses explicit shared-media
links and primary selection, without new roles or Orders; delivered through PR #70.
**PREVIEW-001 is verified**, with operator UAT passed and independent canonical verification
complete. It uses the current dirty feature worktree and isolated persistent synthetic state through
Feature Review primitives. The **next product milestone remains Collection productivity v2**.

The approved sequence, retaining completed steps for context, is:

1. HARVEST-003: explicit stored seed inventory → SeedLot, with approved guarded reversal. Retain
   the reversed SeedLot, original disposition, producer lineage and conversion evidence; restore
   source snapshots only while safe and dependent work is resolved. Converted origin is protected.
   This does not add generic HARVEST-002 disposition undo.
2. SUPPLIER-003 Supplier imagery / practical Reference completion uses shared
   MediaAsset/RecordMediaLink and link-based Collection/Supplier filters; operator UAT and
   independent review passed, with delivery through the canonical repository workflow.
3. PREVIEW-001: persistent isolated operator UAT Preview with a reusable synthetic dataset,
   idempotent seeding and explicit guarded reset; distinct from developer DEV and production.
4. Collection productivity v2: broader global search, saved filters/views, bulk operations and
   justified unified operational history.
5. Orders / Purchases, separate from Supplier and biological/geographic provenance.
6. Daily-use biological/collection improvements: measurements, justified flowering/fruiting work,
   germination analysis, viability/aging, seasonal planning, operational history and later reviewed
   Dashboard attention rules.
7. Final UI review of concrete surfaces/defects, mobile and accessibility; no new mega-redesign.
8. Performance re-check after product increments against PERF-001's existing baseline.
9. Public Docker distribution: GHCR preferred, immutable/versioned images, practical multi-arch,
   production Compose using published images and explicit upgrade/migration expectations.
10. Repository presentation/documentation review as a newcomer: README, screenshots, overview,
    installation, configuration, deployment, upgrades, backup/restore, examples, architecture,
    terminology, links and stale prose.
11. Technical finalization/release hardening: dead code/workarounds/fixtures/scripts, dependencies,
    licensing/security, final CI, clean install, upgrade, complete DB+media restore and release notes.
12. 1.0.0 stability milestone.

BOTANY-003 stays a parallel `planned` track. Its approved WFO source/product contract is unchanged;
implementation remains blocked by that endpoint's incomplete public TLS chain. It does not block
other roadmap work. No source reselection or TLS workaround is introduced.

RELEASE-001 remains the planned historical release-hardening feature, without deletion or
repurposing of its acceptance criteria. Any change to that feature contract requires a separate
explicit feature-graph decision.

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

## Historical Florabase 0.1.0 release boundary

Florabase is ready for `0.1.0` when it can hold and operate a real personal botanical collection
without the operator reasonably fearing data loss, an unusable core workflow, or an undocumented
deployment or upgrade path. Advanced botanical enrichment, automatic taxonomy reconciliation, every
propagation material type, advanced analytics, multi-user collaboration, generic integrations, and
full offline synchronization are outside that criterion.

### Required before 0.1.0: PERF-001 and RELEASE-001

[`PERF-001`](features.json) is verified on the frozen product scope.
Its [measurement report](performance/PERF-001.md) preserves the production-like baseline, identical
workload comparisons, bounded query regressions, resource observations and limitations. Demonstrated
costs justified response-local geography reuse, native workspace lazy loading and public static
compression. Domain, security, privacy, API and schema contracts are unchanged; no speculative index,
generic cache or hardware guarantee was added. The Vite advisory threshold is unchanged. Release
acceptance remains pending. `RELEASE-001` should repeat the report's resource
sanity checks on its exact candidate, real target hardware/persistent storage and HTTPS.

The agreed final cross-application UI coherence pass follows PERF-001 and precedes RELEASE-001. It
compacts the shell and headings, gives desktop directories and timelines the remaining viewport with
one principal result scroll, keeps natural mobile scrolling, presents Suppliers as a list, and shows
Places, Provenance sites, and Map as peer Geography views. This is blocking polish within the frozen
product perimeter, not another feature or a change to the domain and API contracts.

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
The ATTACHMENT-004 implementation keeps the designation relational and explicit. Supported local
photos use a fixed authenticated thumbnail in collection directories/details; external primaries
remain a neutral compact indicator until the operator chooses to load the remote image in Photos.

LABEL-001 implements the selected browser-print workflow: a temporary A4 composer for SeedLot,
Plant, and PlantGroup, with fixed 50 × 30 mm labels in a 4 × 9 grid. Botanical identity, record type,
optional existing label, and a local SVG QR identify the exact existing authenticated detail route.
Printing requires 100% / Actual size; no photos, new numbering, persistent jobs, migration, public
lookup, or server PDF subsystem is introduced. See [labels.md](labels.md).

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

- **PREVIEW-001** is a verified P1 infrastructure increment with operator UAT passed and independent
  verification complete. It provides persistent, isolated operator Preview/UAT with Preview-only
  credentials, a reusable synthetic dataset, idempotent
  seeding and explicit guarded reset. It follows SUPPLIER-003 and precedes Collection productivity v2.
- **Supplier directory imagery** is implemented by SUPPLIER-003 under the approved shared-media
  target contract; operator visual UAT passed and independent verification is complete. Multiple media
  and one explicit primary support directory, Quick Preview and shared detail management; link-based
  Collection/Supplier filters keep Supplier-only imagery out of collection browsing. No logo role,
  asset category or Orders are added.
- **Location descendant usage counts** are implemented by LOCATION-003. HARVEST-002
  extends the same direct/inclusive projections to managed harvested material;
  operator scope eligibility remains explicit.

- `BOTANY-003` remains `planned`, but does **not** block `0.1.0`. The operator approved WFO / Flora
  of China general descriptions → `description` and Kew WCVP `geographic_area` → `origin_distribution`.
  Replacement policy 3 requires explicit Apply for empty fields, explicit Replace confirmation for
  populated fields, retained typed applied-value history and field-specific current attribution.
  Manual edits clear only the edited field's source association; history remains. Exact provider
  confirmation and stale-current/stale-proposal protection are required. Implementation is blocked
  by the approved WFO endpoint omitting its issuing intermediate despite the public root being
  present in both backend runtimes;
  resume only after that exact mechanism can be retrieved securely. Source selection is approved,
  not reopened. No scraping, TLS bypass, assumed identifier crosswalk or broader field import is allowed.
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
  Advanced media processing such as general derivatives, EXIF workflows, albums, advanced ordering and
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
remain historical. GERMINATION-001 now adds independent dated observations in Sowing detail; it
does not change propagation transitions or create Events.

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
`BOTANY-003` profile enrichment remains separately planned with the two-field source/replacement
contract approved, but secure backend access to the reviewed WFO archive blocked. The complete
approved scope and access evidence remain in `docs/botany-003-audit.md`. `UX-003` is
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

## Historical pre-1.0 milestone planning after shared media

ATTACHMENT-005 establishes reusable assets and exact record links; it does not execute the work below.
Each milestone requires a separate bounded increment and product contract before implementation.

1. HARVEST-001 structured harvest records are implemented for operator visual acceptance: explicit
   sources, ordered materials, quantities, partial dates, owned Events and shared media.
   HARVEST-002 was the selected P1 pre-1.0 increment for optional stored remainder, Location and
   consumed/processed/discarded/gifted/propagation-use history. Historical collected quantities stay
   independent. Explicit harvested seed → SeedLot conversion is a separate future increment.
2. Supplier imagery was subsequently implemented as SUPPLIER-003 with normal explicit media
   links and one representative primary. No logo role or asset category was introduced.
3. Broader global search, saved views and explicit bulk operations beyond the implemented SEARCH-001
   baseline; preserve deterministic search and destructive-operation boundaries.
4. Further botanical enrichment and distribution maps beyond existing provider links and occurrence
   density, with live-provider, attribution, precision and privacy acceptance.
5. Performance and resource optimization on the expanded scope: measure CPU/memory, original and
   derivative storage, queries, loading and chunk sizes before making demonstrated narrow changes.
6. Public downloadable versioned Docker images through GHCR or equivalent: version/immutable release
   tags, practical architecture support, production Compose using published images, clean install,
   upgrade, backup-before-migration, visible version and release notes. Users should not need local
   repository builds. No publishing tooling is added on this branch.
7. Repository presentation and documentation review from a new external user's perspective: README
   structure, description, screenshots, feature overview, installation, Docker deployment, upgrades,
   migrations, backup/restore, configuration, import examples, architecture, terminology, doc links,
   stale history and presentation consistency. Prove that somebody without project-history context
   can understand and deploy Florabase. This is a separate future audit, not the current media docs update.
8. Final technical repository cleanup and release hardening: dependency/tooling health, security and
   migration/recovery drills, CI, tests, installation/upgrade acceptance and release-candidate checks.
   Keep this technical gate distinct from the presentation/documentation audit above.

The LOCATION-003 descendant aggregation milestone remains implemented alongside shared media.
Controlled botanical enrichment, botanical distribution mapping, global search/saved views/bulk
operations, measured resource optimization, public Docker images, repository presentation/documentation
review and final technical cleanup/release hardening retain their separate pre-1.0 boundaries.
HARVEST-001 does not perform those future milestones or the final documentation audit.
