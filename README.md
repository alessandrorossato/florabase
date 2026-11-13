# Florabase

Florabase is a self-hosted web application for managing a personal botanical collection. It keeps
botanical reference information separate from the material and plants in a collection, while
preserving explicit provenance through real collection workflows.

Florabase is under active pre-release development. The current application is usable for one local
owner, but no stable public release has been published yet. The private beta series
(`v0.1.0-beta.N`) leads to release candidates and then v1.0.0, the first public stable release.
The [v1.0.0 release scope](docs/release/scope-v1.md) defines what that release contains, its
gates and its exclusions.

## What works today

- Botanical identities, incomplete-friendly operator-authored profiles, structured native ranges,
  and explicit links to external GBIF references
- Supplier, scoped hierarchical collection Location, GeographicPlace, and ProvenanceSite directories
- Seed lots with source, partial dates, quantity, storage, lifecycle, and optional producer lineage
- Sowings with partial dates, quantities, cultivation details, and simple germination totals
- Individually tracked Plants and quantity-aware PlantGroups
- Plant and PlantGroup Journal Events and read-only cross-domain operational History
- Operational Dashboard and concrete planned work in Schedule List and Month Calendar
- Global search, saved operator views, atomic bulk Location moves and purchase Orders
- Guided CSV import/export, dated germination observations and printable labels with authenticated QR lookup
- Collection-aware occurrence/native-range Maps, reviewed native-range enrichment and a classification Taxonomy tree
- Explicit lineage through `SeedLot → Sowing → Plant / PlantGroup`, PlantGroup extraction, and
  collection-produced seed lots, with receipt-proven reversal for supported authoritative operations
- A collection provenance map for coordinate-bearing ProvenanceSites
- [Shared media library](docs/media-library.md): reusable local/external images, per-record captions
  and order, explicit primary selection, protected thumbnails, retained unlinked assets and guarded deletion.
- Collection-photo galleries and optional BotanicalIdentity covers; layered contextual form help
- Local owner authentication with server-side sessions and CSRF protection
- Structured Harvests of material collected from a Plant or Plant group, with stored material and
  explicit conversion to new seed lots; see the [Harvest guide](docs/harvests.md)
- A material ancestry explorer, accepted-name correction with retained name history and synonyms,
  Plant height measurements and phenology observations in the Journal
- Cuttings (vegetative propagation); delivered and still being finished and certified for v1.0.0
- Installation as a web app ([PWA](docs/pwa.md)); installation on physical phones is not yet verified

Each increment's implementation and verification status is in the
[feature backlog](docs/features.json) and its
[reconciliation against the release scope](docs/release/feature-reconciliation-v1.md). Mobile quick
capture and the other themes after v1.0.0 are in the [product roadmap](docs/product-roadmap.md).

## Screenshots

Feature-review screenshots exist in engineering handoffs; a curated public screenshot set remains
a release gate. Before the first public release, capture the authenticated
desktop Plants view, the mobile Seed lots or Sowings workflow, and a lineage-aware PlantGroup
extraction result using non-sensitive demonstration data.

## Architecture

Florabase is a modular monolith:

- React and strict TypeScript in the browser
- FastAPI and typed Python for the versioned `/api/v1` API
- PostgreSQL as the relational source of truth
- Alembic as the only schema migration path
- Docker Compose for development and self-hosting
- backend-owned OpenAPI with committed generated TypeScript declarations

The production-oriented Compose stack publishes only the frontend proxy. PostgreSQL and the backend
remain on an internal network.

## Requirements

Repository development requires Docker Engine with Docker Compose **2.24.4 or newer**, GNU Make,
Python 3 and `curl`. The development overlay uses Compose's `!override` tag. Host Node.js is optional.
[Docker Compose merge rules](https://docs.docker.com/reference/compose-file/merge/)

For self-hosting, [install with portable Docker Compose](docs/portable-installation.md) from
verified release assets on linux/amd64. This is the official installation; its Compose stack
supports the 2.20 baseline. It requires an operator-managed HTTPS reverse proxy and the exact
public HTTPS origin.

[Building from a source checkout](docs/deployment.md) is for development. The
[controller bundle](docs/installation.md) is an advanced, best-effort alternative and is not a
separately certified installation path.

## Quick start for development

Run this in the primary checkout:

```bash
make setup
```

`make setup` copies `.env.example` to the ignored `.env` file and preserves an existing
configuration. Review the file and replace its example credentials before starting DEV.

```bash
make dev-up &&
make dev-upgrade &&
make dev-bootstrap-owner LOGIN=owner
```

- `make dev-up` builds and starts persistent DEV from the primary checkout. It preserves existing
  data and leaves schema migration to the next step.
- `make dev-upgrade` applies pending Alembic migrations to DEV and verifies that its database reaches
  the code's migration head.
- `make dev-bootstrap-owner LOGIN=owner` creates the initial DEV owner and prompts for the password
  without echoing it.

Open `http://localhost:5173` with the default development port.

## Development

`make check` runs formatting checks, lint, strict Python and TypeScript typing, backend and frontend
tests, and generated API drift checks. PostgreSQL integration tests run separately with
`make test-integration`. See [development.md](docs/development.md) for focused workflows, migrations,
code generation, and Git practices.

## Backup and restore

`make backup` stops backend writes while creating a paired custom-format PostgreSQL dump and local
attachment-volume archive. `make restore` deliberately replaces both and requires explicit
confirmation. Read [backup-restore.md](docs/backup-restore.md) before restoring; deployment
configuration and secrets still need a separate protected backup.

## Project information

- [v1.0.0 release scope](docs/release/scope-v1.md)
- [Portable Docker Compose installation](docs/portable-installation.md)
- [Advanced controller-based installation and recovery](docs/installation.md) (best-effort)
- [Source-build deployment and upgrades](docs/deployment.md) (development)
- [Development guide](docs/development.md)
- [Domain model](docs/domain-model.md)
- [Architecture](docs/architecture.md)
- [Security architecture](docs/security.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Product roadmap](docs/product-roadmap.md)
- [Engineering progress](docs/progress.md)

## License

Florabase is free and open-source software licensed under the
GNU Affero General Public License v3.0 or later.

SPDX-License-Identifier: AGPL-3.0-or-later

See [LICENSE](LICENSE) for the full license text.
