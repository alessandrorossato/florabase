# Florabase documentation

Documentation is organized by audience and topic. Agents should start with [`agent-map.md`](agent-map.md).

## Guides by folder

- [End-user guide](user-guide/README.md) — everyday collection guide for home growers and small-collection keepers.
- [Install & operate](operate/README.md) — self-hosting `compose.yaml`, upgrades, backup/restore, security, versioning, mobile, and PWA.
- [Develop](develop/README.md) — local development, split workflow guides, Golden DEV, reference indexes, UI contract, and contributor tooling.
- [Architecture & domain](architecture/README.md) — system boundaries, split domain model, lineage integrity, geography data, and botanical matching.
- [Feature guides](features/README.md) — workspace guides for Collection, Activity, Explore, Sourcing, and Tools.
- [Product roadmap](product/README.md) — post-v1.0.0 themes and scope boundaries.

## Project tracking, decisions & release

- [Agent reading map](agent-map.md) — task-oriented map naming the exact file and section to read.
- [Engineering progress](progress.md) — recent milestones (archived history in [`archive/progress-until-beta-7.md`](archive/progress-until-beta-7.md)).
- [Feature backlog](features.json) — machine-readable feature graph (`make feature-show ID=<ID>`).
- [Architecture Decision Records](decisions/) — numbered ADRs (`0001`–`0011`).
- [Release scope & acceptance](release/scope-v1.md) — v1.0.0 scope manifest (`release/scope-v1.json`), reconciliation, acceptance checklist, and evidence.
- [Security workbooks](security/) & [Performance benchmarks](performance/) — beta security analysis and `PERF-001` measurements.
- [Contributing](../CONTRIBUTING.md), [Agent guide](../AGENTS.md), and [Third-party notices](../THIRD-PARTY-NOTICES.md).

## Archive & historical evidence

- [`archive/`](archive/) — per-increment handoffs, design notes, audits, and evidence (`docs/archive/<FEATURE-ID>/`).
- [`archive/review/`](archive/review/) — historical visual-review captures and fixtures (new screenshots are not committed; only curated images under `docs/assets/` are committed).
- [`design/`](design/) — historical UI design explorations and Gate A/B design-system records.
