<p align="center">
  <img src="docs/assets/florabase-logo.png" alt="Florabase" width="300">
</p>

<p align="center">
  <img src="docs/assets/readme-showcase.png" alt="Florabase screens: Today, a botanical identity, native ranges, taxonomy, collection origins, the Schedule calendar and two phone views" width="100%">
</p>

Florabase is a self-hosted web application for managing a personal botanical collection. It keeps
botanical reference information separate from the material and plants in a collection, while
preserving explicit provenance through real collection workflows.

Florabase is under active pre-release development. The current application is usable for one local
owner, but no stable public release has been published yet. The public pre-release (beta) series
(`v0.1.0-beta.N`) leads to release candidates (`v1.0.0-rc.N`) and then v1.0.0, the first
public stable release.
The [v1.0.0 release scope](docs/release/scope-v1.md) defines what that release contains, its
gates and its exclusions.

## What works today

- **Today** (operational dashboard): current holdings, due work, recent activity, global search, and
  saved operator views
- **Collection → Seeds & Sowings**: seed lots with source, partial dates, quantity, storage,
  lifecycle and optional producer lineage; sowings with cultivation details and dated germination
  observations
- **Collection → Cuttings**: vegetative propagation lots and rooting observations (delivered and
  being finished and certified for v1.0.0)
- **Collection → Plants & Plant groups**: individually tracked plants and quantity-aware plant
  groups, with extraction, height measurements and explicit transfers
- **Collection → Harvests & Stored material**: structured harvests collected from a plant or plant
  group, stored material inventory, and explicit conversion to new seed lots (see the
  [Harvest guide](docs/harvests.md))
- **Collection → Locations**: scoped hierarchical collection locations with atomic bulk moves
- **Activity → Journal & History**: plant and plant-group journal events (including phenology
  observations) and read-only cross-domain operational history
- **Activity → Schedule & Calendar (planned work)**: concrete planned work in list and month
  calendar views
- **Explore → Botanical identities**: incomplete-friendly operator-authored profiles, structured
  native ranges, accepted-name correction with retained name history and synonyms, optional covers,
  and explicit links to external GBIF references
- **Explore → Taxonomy & Lineage**: classification taxonomy tree backed by a local reviewed WFO
  snapshot, plus explicit material and identity lineage (`SeedLot → Sowing → Plant / PlantGroup`,
  extraction, collection-produced seed lots) with receipt-proven reversal for supported operations
- **Explore → Media**: [shared media library](docs/media-library.md) with reusable local/external
  images, per-record captions and order, explicit primary selection, collection-photo galleries,
  protected thumbnails, retained unlinked assets and guarded deletion
- **Explore → Geography**: local places and provenance sites, **Collection origins** provenance map,
  **Species distribution** (on-demand GBIF occurrence density), and **Native ranges** map with
  reviewed WCVP enrichment
- **Sourcing → Suppliers & Orders**: supplier directory and purchase orders linking received
  material
- **Settings → Account, Theme, Labels, Import / Export, Data sources & Help**: local owner
  authentication with server-side sessions and CSRF protection, multi-theme light/dark appearances,
  printable labels with authenticated QR lookup, guided CSV import/export, transparent data-source
  attribution and layered contextual help
- **Installable web app ([PWA](docs/pwa.md))**: installable as a progressive web app (installation
  on physical phones is not yet verified)

Each increment's implementation and verification status is in the
[feature backlog](docs/features.json) and its
[reconciliation against the release scope](docs/release/feature-reconciliation-v1.md). Mobile quick
capture and the other themes after v1.0.0 are in the [product roadmap](docs/product-roadmap.md).

## Screenshots

The showcase above uses invented demonstration data (no real collection, provenance or locations):
Today, a botanical identity, native ranges, the WFO taxonomy, collection origins and the month
calendar on desktop, plus Today and an identity on a phone, in the light and dark appearances. A
curated public screenshot set remains a release gate.

## Architecture

Florabase is a modular monolith:

- React and strict TypeScript in the browser
- FastAPI and typed Python for the versioned `/api/v1` API
- PostgreSQL as the relational source of truth
- Alembic as the only schema migration path
- Docker Compose for development and self-hosting
- backend-owned OpenAPI with committed generated TypeScript declarations

The production-oriented Compose stack publishes only the frontend proxy on `127.0.0.1`.
PostgreSQL and the backend publish no ports (and can be isolated on a separate `internal: true`
network via the optional hardened override in [docs/security.md](docs/security.md#optional-container-hardening)).

## Requirements

Repository development requires Docker Engine with Docker Compose **2.24.4 or newer**, GNU Make,
Python 3 and `curl`. The development overlay uses Compose's `!override` tag (see
[Docker Compose merge rules](https://docs.docker.com/reference/compose-file/merge/)). Host Node.js
is optional.

For self-hosting, follow [Install Florabase](docs/installation.md) using `compose.yaml` from the
latest release tag (Compose 2.20 baseline; no container runs as root). The single Compose stack
initializes a fresh installation automatically and writes a verified backup before upgrades. Put it
behind an HTTPS reverse proxy (or Tailscale Serve) with your exact canonical HTTPS origin.

[Building from a source checkout](docs/deployment.md) is for development only.

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

- [Documentation index](docs/README.md)
- [v1.0.0 release scope](docs/release/scope-v1.md)
- [Installation, upgrade, backup and restore](docs/installation.md)
- [Source-build deployment and upgrades](docs/deployment.md) (development)
- [Development guide](docs/development.md)
- [Domain model](docs/domain-model.md)
- [Architecture](docs/architecture.md)
- [Security architecture](docs/security.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Third-party notices](THIRD-PARTY-NOTICES.md)
- [Changelog](CHANGELOG.md)
- [Versioning and compatibility](docs/versioning.md)
- [Product roadmap](docs/product-roadmap.md)
- [Engineering progress](docs/progress.md)

## License

Copyright (C) 2026 Alessandro Rossato

Florabase is free and open-source software licensed under the
GNU Affero General Public License v3.0 or later.

SPDX-License-Identifier: AGPL-3.0-or-later

See [LICENSE](LICENSE) for the full license text. Bundled assets and external data sources keep
their own licences; see [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
