# Florabase product roadmap

The scope of v1.0.0 is defined only in the [v1.0.0 release scope](release/scope-v1.md): the
approved decisions, the release gates, the work required before the release and the exclusions.
This page does not repeat that contract. It keeps the product themes that come after 1.0.

[`features.json`](features.json) remains the machine-readable source for bounded increments and
their statuses; its reconciliation against the release scope is in the
[feature reconciliation](release/feature-reconciliation-v1.md). A roadmap entry is not evidence of
implementation or verification.

The earlier roadmap, with the PRE-0.1 freeze path, the v0.1.0 release gates and the beta framing,
is preserved at [release/history/product-roadmap-2026-11-11.md](release/history/product-roadmap-2026-11-11.md).

## Version strategy

Florabase uses [Semantic Versioning 2.0.0](https://semver.org/).

- **`v0.1.0-beta.N`** — the existing private beta series.
- **`v1.0.0-rc.N`** — release candidates evaluated against the release gates.
- **`v1.0.0`** — the first public stable release. There is no intermediate public 0.1 stable.

From 1.0.0, compatible additions use minor versions, compatible fixes use patches, and a change
that breaks a supported contract requires a major version. The supported contracts are listed in
the release scope. Source tags use the `v1.0.0` style and container tags the `1.0.0` style.
Published version contents are never replaced. The `/api/v1` namespace is an application
boundary, not a compatibility promise.

## Delivered since the earlier roadmap

The earlier roadmap listed these as future themes. They are on `main`; their verification state
is in the feature reconciliation.

| Earlier theme | Increment |
| --- | --- |
| Material lineage | LINEAGE-003 |
| Accepted-name reconciliation | TAXONOMY-001 |
| Synonyms and name history | TAXONOMY-002 |
| Measurements (height) | MEASUREMENT-001 |
| Phenology | PHENOLOGY-001 |
| Vegetative propagation / cuttings | CUTTING-001, to be finished and certified for 1.0 |
| PWA installability | PWA-001 |

Further measurement quantities, and the propagation extension cases (division, offsets, layering,
grafting), remain post-1.0.

## Post-1.0 themes

The order is proposed and can change. None of these is a v1.0.0 dependency; adding one to 1.0
requires a scope change as described in the release scope. Unscheduled themes have no feature
IDs. The theme numbers are those of the earlier roadmap.

| Order | Theme | Existing increment anchor |
| --- | --- | --- |
| 7 | Recurring care plans | Builds on SCHEDULE-001/002 |
| 8 | Plant health / issue workflow | Reuses Journal, Schedule and History |
| 9 | Contextual entity timelines | Reuses HISTORY-001 semantics |
| 10 | QR labels + mobile quick capture | LABEL-001 baseline |
| 11 | Acquisition / receiving / reconciliation | ORDER-001 and Supplier baseline |
| 12 | Calendar export / reminders | REMINDER-001 |
| 13 | Portable export enhancements | TRANSFER-001 |
| 14 | User-imported phylogeny | Separate future source and import contract |

A later Dashboard review may reassess operational value after real use; configurable modules and
additional summaries are not part of 1.0.

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
required unless later evidence justifies them. This is separate from the delivered label audit.

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
This blocker does not prevent v1.0.0. Continue source
research separately if desired, or select the user-provided-tree path after its own review.

**BOTANY-003** remains `planned`: [source decisions](botanical-profile-enrichment-sources.md) record
SOURCE_BLOCKED secure acquisition for the approved general-description path. WCVP geographic-area
source approval and three individually approved alternative description records do not implement
broad text enrichment or resolve its coverage gate. Manual profiles and delivered ENRICHMENT-001
native ranges remain available. **BOTANY-004** source-reviewed cultivation/uses/warnings and
**ENRICHMENT-002** automatic refresh stay DEFERRED; none blocks v1.0.0. Source access/rights
constraints are prerequisites, not failed implementation, and must not be bypassed.

Other DEFERRED candidates retain their graph IDs: TUBER-001, WEATHER-001,
ANALYSIS-001, INTEGRATION-001 and SECURITY-003 multi-user collaboration. Full offline mutations/sync,
generic task management and broad media pipelines are outside the agreed core roadmap. Reconsider
through a concrete workflow and scope decision, not as implicit release dependencies.
