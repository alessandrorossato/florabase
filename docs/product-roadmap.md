# Florabase product and release roadmap

Canonical product direction from **v0.1.0 to v1.0.0**, agreed 2026-10-13. This replaces the
superseded sequences previously collected on this page. Historical decisions and delivered-state
milestones remain in [engineering progress](progress.md) and the linked feature handoffs.

This document owns release scope, product sequencing, themes and acceptance gates.
[`features.json`](features.json) remains the machine-readable source for bounded implementation
increments, dependencies, priorities and implementation statuses. A roadmap entry is not evidence
of implementation or verification. Create new feature IDs only when a concrete increment is selected;
keep existing IDs when refining their product contract. No release date or intermediate 0.x version
is promised here.

## Version strategy

Florabase uses [Semantic Versioning 2.0.0](https://semver.org/): `MAJOR.MINOR.PATCH`.

- **v0.1.0 — first real public/self-hosted release:** a coherent personal collection product with
  proven installation, upgrade, recovery and documented limits. Existing package version strings
  do not establish a published release or passed release gates.
- **0.x — subsequent product increments:** core workflows, data model and API contracts can still
  evolve. Florabase's policy is to use a new 0.x minor for product increments or incompatible
  contracts, and patches for compatible fixes. Release notes must identify compatibility changes,
  supported upgrade origins, required migrations and recovery steps; pre-1.0 is not permission to
  discard collection data silently.
- **v1.0.0 — stable product contract:** core collection workflows, data model and documented API
  contracts are mature enough for supported real use and compatibility commitments. The stability
  decision is evidence-based, not a count of roadmap items. Feature development continues after 1.0.

At 1.0 and later, compatible additions use minor versions, compatible fixes use patches and
incompatible public-contract changes require a major version. Source tags use `v0.1.0` style;
container tags use `0.1.0` style. Published version contents must not be replaced. The `/api/v1`
namespace is an API boundary, not proof that the product has reached v1.0.0.

## Status vocabulary and release boundary

| Roadmap status | Meaning                                                                                                      |
| -------------- | ------------------------------------------------------------------------------------------------------------ |
| DELIVERED      | Capability landed on main; the graph's recorded implementation/verification status is stated separately.     |
| PLANNED        | Agreed future product work; no implementation completion is implied.                                         |
| DEFERRED       | Intentionally outside the current release boundary; reconsider only through a concrete scope decision.       |
| SOURCE_BLOCKED | A prerequisite source/access/rights decision prevents implementation; this is not an implementation failure. |
| RELEASE_GATE   | Required acceptance evidence before publishing the release; unresolved until recorded and accepted.          |

**PRE-0.1** and **POST-0.1 / 1.0 ROADMAP** indicate release placement. These categories do not replace
the graph's `planned`, `in_progress`, `implemented`, `verified` vocabulary. In particular,
SOURCE_BLOCKED work stays `planned` in JSON; DELIVERED does not promote an `implemented` feature to
`verified`.

| Area                                                               | Status / placement                   | Blocks v0.1.0?                                             |
| ------------------------------------------------------------------ | ------------------------------------ | ---------------------------------------------------------- |
| Existing collection core, Dashboard, Schedule List and Calendar    | DELIVERED / PRE-0.1                  | No new implementation required; release UAT still applies. |
| Journal / History product pass                                     | PLANNED / PRE-0.1                    | Yes: semantic and workflow acceptance.                     |
| Labels product/workflow audit                                      | PLANNED / PRE-0.1                    | Yes: coherent first-release print/lookup scope.            |
| Functional/IA freeze, global visual review and UI normalization    | RELEASE_GATE / PRE-0.1               | Yes.                                                       |
| Release-readiness audit, public documentation and distribution     | RELEASE_GATE / PRE-0.1, RELEASE-001  | Yes: every gate below requires evidence.                   |
| New product themes in the post-0.1 priority list                   | PLANNED / POST-0.1 / 1.0 ROADMAP     | No.                                                        |
| Global-source phylogeny, PHYLOGENY-001                             | SOURCE_BLOCKED / outside core gates  | No: does not block v0.1 freeze, v0.1.0 or core v1.0.0.     |
| Profile text enrichment, BOTANY-003; source research, BOTANY-004   | SOURCE_BLOCKED / DEFERRED, see below | No.                                                        |
| PWA installability, weather, broader analytics, multi-user/offline | DEFERRED / later scope decisions     | No; none is an automatic v1.0 requirement.                 |

## Delivered baseline

Snapshot of current main, `f54648f`, on 2026-10-13. This is a pre-release application, not release
acceptance. The feature graph retains its historical statuses, including landed increments still
recorded as `implemented`.

| Delivered area                                                                                   | Existing IDs and evidence / graph state                                                                                                                                                                                                                     |
| ------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Self-hosted foundation, local owner authentication, typed API and guarded DB/media recovery      | FOUNDATION-001, SECURITY-001/002, OPS-001, CI-001/002/003 are `verified`; [workflow](development-workflow.md), [security](security.md), [recovery](backup-restore.md).                                                                                      |
| Botanical identities/profiles, suppliers, collection Locations and geographic provenance         | Core identity/profile/supplier/location features are `verified`; GEOGRAPHY-002/003, LOCATION-002/003 and MAP-001 remain `implemented`; [domain](domain-model.md), [Location aggregation](location-descendant-aggregation.md).                               |
| Seed lots, Sowings, dated germination observations, Plants and Plant groups                      | SEED-001–004, SOWING-001–003 and PLANT-001–006 are `verified`; GERMINATION-001 remains `implemented`. Unknown quantity/date precision is retained.                                                                                                          |
| Explicit material ancestry, propagation, extraction and supported guarded reversals              | LINEAGE-001/002 and PROPAGATION-001–003 are `verified`; [integrity audit](lineage-integrity.md). First-class visual lineage remains LINEAGE-003, `planned`.                                                                                                 |
| Journal and read-only cross-domain History                                                       | EVENT-001/002 and HISTORY-001 are `verified`; [History contract](operational-history.md), [handoff](history-001-handoff.md). Product pass remains required.                                                                                                 |
| Harvests, stored material and explicit harvested-seed conversion                                 | HARVEST-001 remains `implemented`; HARVEST-002/003 are `verified`; [Harvests](harvests.md), [inventory](harvest-inventory.md), [conversion](harvest-seed-conversion.md).                                                                                    |
| Shared media, collection photos and primary imagery                                              | ATTACHMENT-002 and SUPPLIER-003 are `verified`; ATTACHMENT-003/004/005 remain `implemented`; [Media library](media-library.md), [Supplier handoff](supplier-003-handoff.md).                                                                                |
| Global search, Saved Views, atomic bulk Location moves, Orders and CSV import/export             | SEARCH-002, VIEW-001, BULK-001 and ORDER-001 are `verified`; SEARCH-001 and IMPORT-001 remain `implemented`; [Saved Views](saved-views.md), [Orders](orders.md), [CSV](import-export.md).                                                                   |
| Explore occurrence maps, native ranges, reviewed native-range enrichment and classification tree | MAP-002, EXPLORE-001/002, ENRICHMENT-001 and TAXONOMY-003 are `verified`; [Maps](native-ranges-explore.md), [Taxonomy](collection-taxonomy.md). Classification is not phylogeny.                                                                            |
| Printable physical labels with exact authenticated QR lookup                                     | LABEL-001 is `verified`; [workflow](labels.md), [review and outstanding physical checks](label-001-review.md). Mobile quick capture remains planned.                                                                                                        |
| UI Foundation and operational Dashboard                                                          | DASHBOARD-001 is `verified`, delivered in PR #101; [handoff](dashboard-001-handoff.md), [UI contract](ui-contract.md). Older UX-002–006 remain `implemented`; global normalization is pending.                                                              |
| Concrete future work in Schedule List and Month Calendar                                         | SCHEDULE-001/002 are `verified`; Calendar delivered in PR #105; [Schedule](schedule.md), [Calendar handoff](schedule-002-handoff.md). No recurrence/reminder implementation is implied.                                                                     |
| Persistent synthetic UAT and measured performance baseline                                       | PREVIEW-001 and PERF-001 are `verified`; INFRA-MAINT-001 landed in PR #106 but remains `implemented`; [infrastructure handoff](infra-maint-001-handoff.md), [performance evidence](performance/PERF-001.md). Measurements predate later product increments. |

## Immediate PRE-0.1 product freeze path

The required sequence is:

1. **Journal / History product pass.** Accept the semantic and navigation decisions below; select
   only bounded corrections required for the first release.
2. **Labels audit.** Review the existing print and QR workflow and decide the minimum coherent
   first-release scope.
3. **Functional / information-architecture freeze.** Record the intended v0.1 workflow inventory,
   accepted navigation, exclusions and remaining release defects. Freeze major functionality and IA;
   stop adding large features before visual review. PHYLOGENY-001 is not a freeze dependency.
4. **Global visual review, page by page.** Record findings across the complete inventory below.
5. **UI normalization/refactor using [UI Foundation](ui-contract.md).** Resolve accepted findings
   through shared semantic tokens, primitives and interaction grammar; review the resulting pages.
6. **Release-readiness audit.** Exercise the functional, operational, resource and security gates on
   the frozen candidate; fix concrete release blockers and retain evidence.
7. **Documentation / public presentation.** Complete newcomer-facing instructions, screenshots,
   license/source notes and release notes against the accepted release tree.
8. **v0.1.0 release.** Publish versioned source and images only after every release gate is accepted.

Documentation can be drafted earlier; final presentation follows the audited candidate. Later
corrections must reopen the affected review/gate explicitly. Delivered Schedule and Dashboard are
baseline inputs to UAT and page review, not new implementation increments in this roadmap task.

### Journal / History product pass

The bounded implementation candidate is ACTIVITY-001; see its [semantic audit and QA handoff](journal-history-product-pass-handoff.md). Independent acceptance remains pending.

- **Journal:** recording hub plus operator notebook. Delivered structured actions open their canonical
  workflows; observations and notes reuse the Plant/PlantGroup Journal. Future observation domains
  are not implemented by this pass.
- **History:** read-only authoritative facts that actually happened, projected from their owning
  records. It is not an immutable audit log: supported corrections affect its projection.
- **Schedule:** future intended collection work. Overdue is derived and never means that work occurred.

The pass examines Journal/History overlap, contextual entity timelines, links between related records,
filters, terminology, presentation, Schedule completion and duplicate representations of one fact.
Respect the existing [source/deduplication matrix](operational-history.md). Distinguish occurrence
PartialDate from a visibly labelled recording-time fallback; never manufacture a day. Schedule
completion retains its terminal planning fact and may explicitly link an actual compatible Event;
it does not automatically manufacture a Journal occurrence or assign the due date as occurrence.

Acceptance: document which surface owns each fact, how the operator reaches and corrects its owning
record, which overlap is intentional, and how representative completed-work/Harvest/propagation
examples avoid duplicate facts. Review record-context navigation now; the richer unified contextual
timeline below remains post-0.1 unless a narrow correction is required for release coherence.

### Labels product/workflow audit

Review **label → QR → Florabase record → mobile quick actions** as the long-term workflow.
LABEL-001 already supplies browser printing and QR URLs for SeedLot, Plant and PlantGroup; do not
relabel that delivered lookup as future work. Audit supported records, legibility, long names,
physical print size/alignment, scanability, configured canonical origin, exact-record routing,
normal authorization and mobile arrival after login. Existing review leaves physical printer/system
print-dialog checks with the operator; retain that open evidence requirement.

Acceptance: record the minimal coherent v0.1 scope and its physical print/scan evidence, with any
necessary corrections scoped separately. New QR capabilities and mobile quick-action UI are not
implemented here and remain post-0.1; full PWA/native/offline behavior does not block this audit.

### Global page-by-page visual review and normalization

Use a review matrix with page/state, viewport, finding, severity, shared-contract correction and
recheck evidence. Cover at least:

- Dashboard; Seeds; Sowings; Plants; Plant groups; Harvests / stored material; Locations.
- Journal; History; Schedule List; Schedule Calendar.
- Botanical identities; Taxonomy; Media; Geography / Maps; Suppliers; Orders; Labels; Import / Export.
- Dialogs; drawers; popovers; filters; Saved Views; empty/loading/error states.
- Desktop, tablet and mobile, including the UI contract's 1440×844, 1024×844 and 390×844 sizes.

Review width use, density, action buttons, toolbar grammar, page headers, list/detail/edit
consistency, excessive cards, alignment, whitespace, responsive behavior, accessibility and
interaction consistency. Include keyboard/focus paths, zoom/long content, reachable actions,
dialog dismissal and errors as well as populated screenshots.

Acceptance: every inventory item has evidence or a documented non-applicable state; no critical
usability/accessibility finding remains; accepted corrections are rechecked. All UI work converges
on [ui-contract.md](ui-contract.md). Repeated problems belong in shared primitives or an explicit
contract extension, not page-local colors, scales or interaction rules.

## v0.1.0 release gates — RELEASE_GATE / PRE-0.1

[RELEASE-001](features.json) remains `planned`, with its existing dependencies and acceptance
history retained. The product/release checklist below supplements those technical dependencies;
a satisfied feature graph alone does not establish release readiness. Gate acceptance remains pending.

For each gate, record the exact source SHA/image version, environment/host, dataset, command or
manual procedure, expected/actual result, evidence and acceptance decision. Open critical failures
block release; lesser limitations require explicit disposition and truthful documentation.

| Gate                                | Measurable acceptance evidence                                                                                                                                                                                                                                                                                          |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Functional                          | Every intended frozen v0.1 workflow passes an agreed UAT checklist; no known critical workflow blocker; Journal/History and Labels decisions accepted; functional/IA freeze recorded.                                                                                                                                   |
| Testing                             | Exact final release tree passes canonical **full** verification under the [workflow](development-workflow.md); disposable clean-database migration chain/cycle passes; generated OpenAPI/TypeScript have no drift; representative UAT is accepted.                                                                      |
| Installation                        | Follow the documented production install on a fresh supported host, recording host/runtime versions; Compose starts healthy without developer-only state, source caches or populated dev volumes; owner/bootstrap, login/logout/session restoration and normal browser use pass.                                        |
| Upgrade                             | Define supported starting version/revision(s), then demonstrate backup-before-upgrade, explicit forward Alembic migration, healthy startup and usable records/media/session flow after upgrade. Document unsupported origins and recovery; startup must not silently migrate or downgrade.                              |
| Backup / restore                    | Paired PostgreSQL and local-media backup restores into an isolated environment; retained records, relationships and binary integrity match, and the application can use them. Document protected configuration/secrets backup, external-media limits and recovery instructions; a DB dump alone is incomplete recovery. |
| Performance / resources             | Complete the measurement inventory below on the frozen candidate, publish reproducible results and accepted limits, compare applicable PERF-001 baseline costs, and investigate material regressions or continuing resource growth. Publish minimum/recommended resources only after tested host evidence.              |
| Security                            | Record auth/session/cookie, CSRF/origin and binary authorization review; production surfaces/internal DB/backend boundaries inspected; no production secrets baked into images; dependency/security status reviewed with findings resolved or explicitly dispositioned.                                                 |
| Accessibility / responsive          | Representative core workflows pass desktop/tablet/mobile use, keyboard navigation, visible focus and focus return, dialogs/forms and map companion lists; no critical accessibility blocker. Record actual coverage rather than claiming formal certification.                                                          |
| Documentation / public presentation | README, installation, configuration, upgrades, paired backup/restore, troubleshooting, architecture summary, licenses/data-source notes, non-sensitive screenshots and release notes/changelog match the final artifact. A newcomer can follow deployment/recovery without project-history knowledge.                   |
| Release / distribution              | Versioned source release and reproducible versioned production Docker images identify the same accepted commit; documented Compose deployment resolves published artifacts; version surfaces and release notes agree; install/upgrade smoke uses those artifacts.                                                       |

Representative UAT includes identity/profile → Supplier/Order acquisition and provenance → SeedLot →
Sowing → Plant/PlantGroup → Journal/History, photos, movement/extraction and supported reversal →
Harvest/stored material/conversion, plus Dashboard, Schedule List/Calendar, Labels, search/Saved Views,
CSV exchange, Maps and Taxonomy. Include unknown/partial data and representative provider/API/media,
validation/conflict, authentication expiry and empty/loading/error paths. Optional missing source
indices/providers must not break ordinary collection use.

### Performance and resource measurement inventory

Reuse [PERF-001](performance/PERF-001.md) methodology and retain its historical baseline. Later
Dashboard/Calendar/Taxonomy and other product additions require final-candidate measurements;
an old baseline is not a current hardware guarantee. Record host/storage, container versions,
dataset size/shape, cold/warm runs, duration and repeat observations.

Measure idle CPU; idle RAM; normal navigation; Dashboard; large lists/filter/search; Calendar;
Maps; Taxonomy tree; upload/media; import/export; backup; PostgreSQL footprint; startup time;
container/image sizes; and memory growth during extended use. Use relevant latency, throughput,
CPU/RAM, request/query counts and storage observations for each workflow. Investigate demonstrated
hotspots and compare the same workload after any fix. Do not guess minimum/recommended hardware,
invent universal budgets or conceal uncertainty with arbitrary benchmark numbers.

### Docker and distribution direction

Target reproducible production images and a versioned Docker/Compose deployment. **GHCR is the
preferred publication route** unless release review documents a reason to choose another route.
Publish explicit tags such as `0.1.0` and record immutable digests/source provenance; `latest` must
not be the only deployment contract. Declare and test the supported architecture matrix before
advertising support. End users should deploy published artifacts without local development builds.

Keep the production topology and explicit migration/backup boundaries in
[deployment](deployment.md) and [the environment workflow](development-workflow.md). Document
artifact selection, upgrade, backup and recovery. Publishing, registry automation and release
packaging belong to release readiness.

## POST-0.1 / 1.0 ROADMAP — PLANNED product themes

The order is proposed and can change when dependencies or domain decisions justify it. This is a
product priority list, not a promise that every integration must ship before 1.0. Unscheduled themes
have no invented feature IDs or fixed 0.x version assignment. HIGH / NEXT / LATER describes the
post-0.1 theme order; existing graph P0–P3 implementation priorities remain unchanged until an
increment is selected and its queue priority is reviewed.

| Priority            | Proposed order | Theme                                       | Existing increment anchor                                      |
| ------------------- | -------------- | ------------------------------------------- | -------------------------------------------------------------- |
| HIGH                | 1              | Material lineage                            | LINEAGE-003                                                    |
| HIGH                | 2              | Accepted-name reconciliation/correction     | TAXONOMY-001                                                   |
| HIGH                | 3              | Synonyms and BotanicalIdentity name history | TAXONOMY-002                                                   |
| HIGH                | 4              | Measurements / growth history               | Theme; select bounded increment later.                         |
| HIGH                | 5              | Phenology                                   | Theme; EVENT-003 is related, not blanket implementation scope. |
| HIGH                | 6              | Vegetative propagation / cuttings (talee)   | CUTTING-001; domain design required first.                     |
| NEXT                | 7              | Recurring care plans                        | Theme building on delivered SCHEDULE-001/002.                  |
| NEXT                | 8              | Plant health / issue workflow               | Theme reusing Journal / Schedule / History.                    |
| NEXT                | 9              | Contextual entity timelines                 | Theme reusing HISTORY-001 semantics.                           |
| NEXT                | 10             | QR labels + mobile quick capture            | LABEL-001 baseline; PWA-001 optional installability.           |
| NEXT                | 11             | Acquisition / receiving / reconciliation    | ORDER-001 / Supplier baseline.                                 |
| LATER / INTEGRATION | 12             | Calendar export / reminders                 | REMINDER-001                                                   |
| LATER / INTEGRATION | 13             | Portable export enhancements                | TRANSFER-001, beyond IMPORT-001 CSV.                           |
| LATER / INTEGRATION | 14             | User-imported phylogeny                     | Separate future source/import contract; not global-source GO.  |

### 1. Material lineage

Provide a first-class view of **MATERIAL ANCESTRY**, anchored in LINEAGE-003:

```text
SeedLot → Sowing → Plant / PlantGroup → Harvest → new SeedLot
```

Operators should navigate origin, propagation, descendants, harvested descendants, generations and
provenance continuity. Render only explicit recorded relationships, keeping unknown parents,
inactive/reversed ancestors and independently acquired material honest. A Harvest connects to a
new SeedLot only through the explicit conversion/producer evidence; shared identity, Location or
media does not prove ancestry. This is neither taxonomic lineage nor phylogeny.

Acceptance direction: branching/generational navigation stays authorized and usable at realistic
sizes; each edge identifies its owning evidence. Integrate vegetative propagation after its domain
decision. Existing lineage integrity/receipts remain the foundation; no generic graph engine is implied.

### 2–3. Taxonomy reconciliation and botanical name history

Restore **TAXONOMY-001 — accepted-name reconciliation / correction** as high-priority work.
An operator can move an identity toward a currently accepted botanical name without losing the
identity/name under which material was originally acquired or recorded. Source candidates remain
advisory until explicit confirmation. Name correction and duplicate-identity reconciliation are
separate decisions; a name update must not silently merge material. Retain the graph's explicit
survivor/reference safety contract where a merge is actually selected.

**TAXONOMY-002 — synonyms and BotanicalIdentity name history** retains historical names,
distinguishes accepted/current names and preserves stable identity references. Acquisition and
provenance evidence must remain historically accurate; historical-name search must not create a
new identity for every synonym. No destructive rename may erase botanical history.

Acceptance direction: demonstrate an accepted-name change and, separately, a justified duplicate
reconciliation while all material links and originally recorded names remain attributable. The
current History projection uses current labels; historically accurate naming requires a dedicated
design decision, not a claim that this evidence already exists. Name-retention design must inform
TAXONOMY-001 before any mutation, even though TAXONOMY-002 delivery follows it in the graph.

### 4. Measurements / growth history

Plan structured height, stem/trunk diameter, canopy width, weight and custom numeric measurements
with units. Define validation, subject, unit meaning, correction and uncertainty rules in a bounded
domain design. Preserve observation PartialDate where relevant; do not derive false day precision.

Acceptance direction: longitudinal lists/graphs use recorded values, units and dates, without
hard-coding a column for every possible botanical measurement or silently mixing incompatible units.
Use Journal/History context and mobile capture when available.

### 5. Phenology

Plan structured bud break, flowering, fruit set, fruit ripening, dormancy, leaf loss and renewed
growth observations. Support meaningful year-to-year history such as first flowering dates.

Acceptance direction: comparable seasonal observations preserve uncertainty and distinguish recorded
first flowering from proof that no earlier flowering occurred. Integrate Journal/History rather
than introducing disconnected duplicate timelines; decide the needed structure before extending Events.

### 6. Vegetative propagation / cuttings (talee)

A cutting is not a SeedLot. Seed-based and vegetative propagation can share higher-level workflow
concepts, but their material/evidence semantics remain distinct. Target lineage:

```text
Mother Plant → vegetative material / cutting batch
             → rooting / propagation attempt → resulting Plant / PlantGroup
```

Keep the existing **CUTTING-001** identifier, without treating its older CuttingLot wording as an
approved final schema. Before v1.0, perform a dedicated propagation-domain design decision comparing
**VegetativeLot + PropagationAttempt**, a broader **Propagation model with typed source material**,
or another architecture demonstrated to fit the existing domain. No final schema is chosen here.
Avoid a Cutting-only model that makes other vegetative methods awkward, and avoid speculative
inheritance without concrete workflow evidence.

The future contract must preserve:

- Source/mother Plant when known and explicit clonal lineage; unknown source stays unknown.
- Taken/start dates using Florabase PartialDate; one or multiple cuttings and known or unknown
  starting quantity.
- Initially unknown rooting outcome; successful, failed or partial results; starting quantity kept
  separately from rooted/surviving quantity. Never erase failed propagation evidence or equate
  unknown success with failure.
- Resulting Plant and/or PlantGroup; appropriate Location; notes; media; Journal observations;
  History facts; Schedule follow-up/check-rooting work.
- Material ancestry and provenance continuity in the first-class lineage view, without routing
  vegetative material through SeedLot or Sowing.

Design must consider division, offsets/pups/suckers, layering/air layering and grafting as extension
cases, without implementing them all immediately. TUBER-001 remains a separate deferred material
candidate, not permission to force all organs into seeds. Acceptance direction: prove complete,
failed, partial and still-unknown rooting examples with retained starting/outcome evidence and
correct descendant links before declaring this core propagation contract stable.

### 7. Recurring care

Schedule currently represents concrete future work. Plan recurrence as a separate rule/template
that generates or schedules concrete ScheduledActivity occurrences: fertilize every N days,
germination checks, periodic inspections and watering cadence.

Acceptance direction: define generation boundaries, edits/cancellation and completed-occurrence
retention; distinguish each concrete intention from the rule. Do not redefine ScheduledActivity as
recurrence itself or turn Florabase into a generic task manager.

### 8. Plant health / issue workflow

Plan a lightweight **issue observed → treatment/action → scheduled follow-up → observation →
resolved / unresolved** lifecycle for pest damage, suspected disease and stress/injury.

Acceptance direction: retain suspicion/uncertainty, actions and follow-up evidence with Journal /
Schedule / History reuse. Decide only the additional linkage/state that concrete collection use
needs; do not create a disconnected case-management product.

### 9. Contextual entity timelines

Plan record-context timelines for Plant, PlantGroup, SeedLot, Sowing, Location and BotanicalIdentity
where appropriate. Potential facts include acquisition, sowing, propagation origin, movement,
repotting, observations, measurements, phenology, completed scheduled work, Harvest and lifecycle end.

Acceptance direction: reuse the Journal/History source, date and deduplication decisions; link to
owning records; expose only facts supported by evidence. Potential facts are not promises that
current records already retain them. Do not invent a parallel event system or turn intended work
into an occurrence.

### 10. QR labels + mobile quick capture

Extend the delivered lookup into **physical label → QR scan → exact Florabase record → quick
mobile action**. Useful actions: observation, photo, measurement, move, schedule follow-up and
Harvest where appropriate. Normal record authorization remains authoritative.

Acceptance direction: retain the scanned target through login/navigation, show only valid contextual
actions and persist through the owning server workflow. Web/PWA is acceptable; native apps are not
required for v1.0 unless later evidence justifies them. This is separate from the pre-v0.1 label audit.

### 11. Acquisition / receiving / reconciliation

Streamline **Supplier → Order → received material → SeedLot / other acquired material → provenance**.
Build on delivered ORDER-001 and direct supplier/material references rather than requiring operators
to reconcile independent pages manually.

Acceptance direction: record received material and its purchase/provenance links without conflating
Supplier, Order or physical lot, fabricating quantities/prices, or inventing open/closed Order
lifecycle states. Any receiving lifecycle needs an explicit later product-domain decision.

### 12. Calendar export / reminders

Plan optional ICS/external calendar export and reminders/notifications around Schedule.
ScheduledActivity stays authoritative; integrations are presentation/delivery of its concrete
intentions, not a new task domain. Acceptance direction: define identity/update/cancellation,
timezone, privacy and failure behavior before selecting an integration. Recurrence and notification
delivery are distinct contracts.

### 13. Portable data / user ownership

Plan robust portable export of structured data and media, human-readable formats where practical,
and a documented restore/import strategy without avoidable lock-in. TRANSFER-001 remains distinct
from delivered IMPORT-001 CSV and technical PostgreSQL backup.

Acceptance direction: round-trip stable relationships, precision, provenance, lifecycle and lineage,
with explicit media completeness/limits and previewed conflict handling. PostgreSQL recovery remains
required but is not the whole user-ownership/portability story.

### 14. User-provided phylogeny

Plan an alternative **USER-PROVIDED PHYLOGENY** path: import Newick and/or Nexus supplied by an
operator entitled to use the tree; match imported taxa to BotanicalIdentity records; visualize the
collection-relevant subset; preserve imported tree source/provenance metadata.

Acceptance direction: review parser limits, ambiguous/unmatched taxa, topology/branch-length meaning,
authorization and provenance without inferred name matches or evolutionary claims. This can provide
useful phylogenetic functionality without Florabase redistributing a problematic global source
dataset. It needs its own bounded contract; it does not waive PHYLOGENY-001's source gate.

## Source-blocked and deliberately deferred work

**PHYLOGENY-001 = SOURCE_BLOCKED.** The repository's
[exact source audit](phylogeny-001-source.md) and [blocked handoff](phylogeny-001-handoff.md) retain
the Open Tree synthetic/annotation rights boundary and reopening criterion. No production phylogeny
implementation is claimed. A taxonomic tree is not a phylogenetic tree; neither is material ancestry.
This blocker prevents neither v0.1 freeze/release nor v1.0 core collection management. Continue source
research separately if desired, or select the user-provided-tree path after its own review.

**BOTANY-003** remains `planned`: [source decisions](botanical-profile-enrichment-sources.md) record
SOURCE_BLOCKED secure acquisition for the approved general-description path. WCVP geographic-area
source approval and three individually approved alternative description records do not implement
broad text enrichment or resolve its coverage gate. Manual profiles and delivered ENRICHMENT-001
native ranges remain available. **BOTANY-004** source-reviewed cultivation/uses/warnings and
**ENRICHMENT-002** automatic refresh stay DEFERRED; none blocks v0.1 or core v1.0. Source access/rights
constraints are prerequisites, not failed implementation, and must not be bypassed.

Other DEFERRED candidates retain their graph IDs: PWA-001 installability, TUBER-001, WEATHER-001,
ANALYSIS-001, INTEGRATION-001 and SECURITY-003 multi-user collaboration. Full offline mutations/sync,
generic task management and broad media pipelines are outside the agreed core roadmap. Reconsider
through a concrete workflow and scope decision, not as implicit release dependencies.

## What must be stable before v1.0.0

After v0.1, select small 0.x increments from the themes above and learn from real collection use.
Before declaring v1.0, record a stable-core scope and disposition any remaining theme explicitly;
later integrations and source-blocked work do not silently become blockers.

Required stability evidence:

- Core acquisition/receiving, seed and vegetative propagation, material ancestry, inventory/lifecycle
  and correction/reversal boundaries have accepted domain decisions and representative retained-data
  UAT. Vegetative propagation design must be resolved before 1.0, with no silent seed reinterpretation.
- Stable botanical identity references, accepted/current names and historical acquisition/provenance
  evidence survive name correction/reconciliation. Unknown quantities, units and PartialDate retain
  honest meaning across views, API, migrations and portable data contracts.
- Journal, History, contextual timelines and Schedule/recurrence have clear ownership, date and
  deduplication contracts; observations/measurements/phenology do not require competing event systems.
- Document the public API/data contract, compatibility/deprecation policy, supported upgrade paths,
  migration safety and recoverability. Demonstrate upgrade and paired DB/media restore across the
  versions actually supported, without destructive history loss.
- Reapply release gates on the exact stable candidate: canonical verification, core UAT, security,
  accessibility/responsive use, fresh installation, resource measurements, documentation and
  reproducible versioned distribution. Address material regressions found during sustained real use.

Remaining product-domain decisions include vegetative material/attempt boundaries, historical-name
retention, measurement/unit semantics, phenology structure, recurrence generation, lightweight
health linkage, evidence coverage for contextual timelines, receiving reconciliation and portable
round trips. Decide them in their selected increments, not by speculative schema in this roadmap.
1.0 establishes a mature stable contract; it leaves room for continued compatible product development.
