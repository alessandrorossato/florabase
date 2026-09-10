# Florabase

Florabase is a self-hosted web application for managing a personal botanical collection. It keeps
botanical reference information separate from the material and plants in a collection, while
preserving explicit provenance through real collection workflows.

Florabase is under active pre-release development. The current application is usable for one local
owner, but no stable public release or supported-version policy has been published yet.

## What works today

- Botanical identities, incomplete-friendly operator-authored profiles, structured native ranges,
  and explicit links to external GBIF references
- Supplier, scoped hierarchical collection Location, GeographicPlace, and ProvenanceSite directories
- Seed lots with source, partial dates, quantity, storage, lifecycle, and optional producer lineage
- Sowings with partial dates, quantities, cultivation details, and simple germination totals
- Individually tracked Plants and quantity-aware PlantGroups
- Plant and PlantGroup Events/history, including the collection-wide Events view
- Explicit lineage through `SeedLot → Sowing → Plant / PlantGroup`, PlantGroup extraction, and
  collection-produced seed lots, with receipt-proven reversal for supported authoritative operations
- A collection provenance map for coordinate-bearing ProvenanceSites
- Local owner authentication with server-side sessions and CSRF protection

Attachments and photos, richer germination observations, advanced search and analytics,
import/export, contextual help, and PWA installability are planned, not implemented. See the
[product roadmap](docs/product-roadmap.md) and the detailed [feature backlog](docs/features.json).

## Screenshots

No current screenshots are committed. Before the first public release, capture the authenticated
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

The primary workflow requires Docker Engine with Docker Compose v2, GNU Make, and `curl`. The
repository currently uses multi-architecture upstream images; host Python and Node are optional.

A public deployment requires an operator-managed HTTPS reverse proxy. Florabase production mode
requires the exact public HTTPS origin and secure same-origin session cookies.

## Quick start for development

```bash
make setup
make dev
```

`make setup` copies `.env.example` to the ignored `.env` file and never overwrites an existing one.
Review the file and replace its example credentials. The development override uses
`http://localhost:5173`; open that exact URL.

In another terminal, apply migrations and create the first owner:

```bash
make migrate
docker compose run --rm backend python -m florabase.auth.bootstrap owner
```

The bootstrap command prompts for the password without accepting it as a command argument. For a
public or durable installation, follow the [deployment guide](docs/deployment.md) instead of treating
the development stack as production.

## Development

`make check` runs formatting checks, lint, strict Python and TypeScript typing, backend and frontend
tests, and generated API drift checks. PostgreSQL integration tests run separately with
`make test-integration`. See [development.md](docs/development.md) for focused workflows, migrations,
code generation, and Git practices.

## Backup and restore

`make backup` creates a custom-format PostgreSQL dump. `make restore` deliberately replaces the
configured database and requires explicit confirmation. Read [backup-restore.md](docs/backup-restore.md)
before restoring. No attachment storage exists yet, so current backups cover application-managed
data in PostgreSQL only; deployment configuration and secrets need a separate protected backup.

## Project information

- [Deployment and upgrades](docs/deployment.md)
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
