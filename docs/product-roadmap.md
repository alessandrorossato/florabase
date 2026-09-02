# Product roadmap

Florabase grows through small, dependency-aware increments. This roadmap communicates direction;
[`features.json`](features.json) remains the detailed source for status, dependencies, priority, and
acceptance criteria.

## Product principles

- Partial information is normal, and Florabase does not invent precision.
- Botanical reference knowledge stays separate from collection observations.
- Supplier, collection Location, and geographic provenance answer different questions.
- Historical records and explicit workflow lineage are preserved.
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

The clearest remaining P1 product sequence is:

1. implement the protected Plant/PlantGroup history timeline UI (`EVENT-002`);
2. decide the operator-approved licensing and release/version policy;
3. complete release readiness as a separate release increment.

`CI-001` now supplies the repository-side pull-request verification and repeatable feature-branch
workflow. The active `Protect main` ruleset requires its `quality`, `integration`, and `build` checks,
and repository merge settings permit squash auto-merge while disabling merge commits and rebases.

EVENT-001 covers practical movement, repotting, flowering, fruiting, pruning, treatment, harvest,
death/loss/discarded, and free observations without separate speculative tables. Event creation can
atomically change current Location or lifecycle, but later Event edits/deletion never replay or roll
back current state: Florabase is not event-sourced. Collection evidence stays separate from
BotanicalProfile knowledge. Structured payloads beyond movement, attachments, and the timeline UI
remain deferred.

Attachment storage and photos are valuable but currently P2. Whether they are mandatory for the
first public release is an explicit operator/product decision; this roadmap does not silently make
every P2 item release-critical.

## Later collection enhancements

Planned P2 work deepens existing workflows: guarded attachment storage and photos, dated germination
observations, Orders, richer events, tuber and cutting lots, labels/QR lookup, advanced search,
dashboards, collection-first navigation, contextual help, guided import/export, visual lineage, and
reviewable profile enrichment.

PWA work means installability and a safe application shell, not offline-first mutation,
synchronization, push, or a native mobile app. Those behaviors require separate contracts.

## Longer-term capabilities

P3 work includes automated enrichment refresh, assisted botanical identity reconciliation and name
history, weather context, reminders, comparative analysis, full-fidelity collection transfer,
external integrations, and multi-user collaboration. External data sources require licensing,
terms, availability, attribution, and quality review before selection.

## Deliberate boundaries

Florabase does not currently provide an Event timeline UI, Event attachments, dashboards, advanced
collection search, offline writes, import/export, a generic propagation-material hierarchy, a
generic graph engine, or multi-user ownership. Future work should extend concrete workflows without
weakening unknown-data, history, authorization, or provenance semantics.
