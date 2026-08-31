# Architecture

## Context and boundaries

Florabase is a self-hosted personal botanical collection manager. This repository starts as a modular monolith: a browser application calls a versioned REST API; the API is the only component that reads or writes PostgreSQL. There are no botanical features in the initial scaffold.

```text
Browser -> frontend reverse proxy -> /api/v1 -> FastAPI -> PostgreSQL
                              \---- static React application
```

The host reverse proxy and the Docker host are outside the application boundary. Backups, TLS certificates, DNS, and host hardening remain operator responsibilities.

## Responsibilities

- **Backend:** validation, API contracts, future business rules, authorization, database transactions, and structured container logs.
- **Frontend:** accessible user interaction, explicit loading/error states, and calls through the documented API boundary. It never connects to PostgreSQL.
- **PostgreSQL:** relational source of truth, constraints, UTC timestamps, migration state, and future domain data.
- **Frontend proxy:** serves immutable production assets and forwards `/api/` to the backend. It is not the internet-facing TLS boundary.

## Data and persistent storage

PostgreSQL uses the `postgres_data` named volume. No uploads volume or writable application data directory exists yet; attachment storage will be added only with a concrete capability and migration/backup plan. Application code must treat future configured upload roots as trusted roots and validate filenames, media types, sizes, and content.

The database and uploads require coordinated, separately protected backups. Container layers hold no durable state. Operators must ensure Docker-managed volumes have suitable ownership and that backup processes can read them without broadening runtime permissions.

## API boundary

The backend owns OpenAPI and exposes APIs under `/api/v1`. The committed `backend/openapi.json` is generated from the application, and `frontend/src/api/schema.d.ts` is generated from that artifact. `make api-generate` regenerates both; `make api-check` detects drift.

- Browser and production Compose: relative `/api/v1` requests pass through the frontend proxy.
- Local Vite development: relative `/api/v1` requests are proxied to `BACKEND_PROXY_URL` (default `http://backend:8000` inside Compose).
- A future external reverse proxy should route to the frontend container; it need not expose the backend directly.

## Configuration

Backend configuration is centralized in `florabase.core.config` and read from environment variables with the `FLORABASE_` prefix. The frontend uses a relative API path, avoiding environment-specific browser hostnames. Compose interpolates database credentials and published ports from `.env`; safe development examples live in `.env.example`.

Production sets `FLORABASE_ENVIRONMENT=production`, JSON logs, no debug mode, and an explicit CORS origin list. Production startup rejects wildcard CORS. Secrets must be supplied by the operator, never baked into images or committed.

## Development and production

`compose.yaml` is the production-oriented baseline: versioned multi-architecture upstream images, non-root application processes, internal database/backend networking, health checks, and an nginx frontend. `compose.dev.yaml` adds source mounts, hot reload, and localhost-only database, backend, and Vite ports. The development override replaces the production frontend port and healthcheck; it does not change the database or API architecture.

Migrations never run as an application startup side effect. `make migrate` is explicit. Production deploys should back up, deploy images, run migrations as a deliberate release step, and then replace application containers.

## Migrations and identifiers

Alembic is the only schema-change mechanism. Migrations must be deterministic, reviewable, and reversible where practical. Future public identifiers use application-generated UUIDv7 values; see ADR 0004. Timestamps are timezone-aware at boundaries and stored as PostgreSQL `timestamptz` in UTC.

## Domain data scope

`BotanicalIdentity` is the canonical aggregate for the stable collection-local botanical identity
Florabase assigns to seeds, plants, and future collection material. It is installation-wide shared
classification/reference data, not data owned by one user, so its table does not include a
`user_id`. Shared reference scope does not determine the ownership of future `SeedLot`, `Plant`,
`Sowing`, `Observation`, or other collection records; each capability must define its own scope.

Future collection entities reference `botanical_identity_id` rather than copying scientific or
cultivar identity as authoritative data. The SQL table is `botanical_identities`, and the protected
REST resource is `/api/v1/botanical-identities`. The first API slice supports owner-authorized,
Origin- and CSRF-protected creation, authenticated read-by-UUID, and an authenticated deterministic
directory read. The directory returns the complete lightweight collection ordered
case-insensitively by scientific name and cultivar, with an unqualified identity first and UUID as
the stable tie-breaker. This matches the expected first-release scale of one self-hosted operator;
server-side pagination can be added if observed collection size later requires it. BotanicalIdentity
mutations remain protected operations under ADR 0005.

`BotanicalProfile` is the optional, installation-wide general-reference extension of one
BotanicalIdentity. Its `botanical_identity_id` is both primary key and cascading foreign key, so
PostgreSQL directly enforces at most one profile per identity without a second profile identifier.
The table stores only the five verified nullable plain-text sections and rejects empty, untrimmed,
control-containing, or overlong persisted values; a table check requires at least one section.

The protected nested resource is
`/api/v1/botanical-identities/{botanical_identity_id}/profile`. Authenticated `GET` returns the
current profile or a stable profile-not-found response. Owner-authorized, exact-Origin,
CSRF-protected `PUT` is an idempotent full replacement: it returns `201` when creating and `200`
when replacing. Clearing the final populated section removes the profile and returns `204`; an
all-empty first replacement returns `422`. A PostgreSQL upsert makes concurrent first replacements
converge on the identity-keyed row. This two-operation interface represents the one-to-one current
resource directly and avoids unrelated generic CRUD or a separate destructive-delete workflow.

## Logging and observability

Backend application logs go to stdout. Production defaults to JSON records with UTC timestamps, levels, logger names, and messages; development may use readable text. Uvicorn access/error logs remain visible. Secrets and request bodies are not logged by the scaffold. `/api/v1/health` is liveness only; `/api/v1/ready` performs `SELECT 1` against PostgreSQL.

## Authentication and security

Authentication uses the backend-owned local accounts and opaque PostgreSQL-backed cookie sessions
defined by ADR 0005. Protected features resolve an authenticated actor from the HttpOnly session
cookie, and state changes additionally require exact-Origin and session-bound CSRF validation.
Reverse-proxy identity is not trusted.

The internet-facing reverse proxy must terminate HTTPS, restrict request sizes, set appropriate HSTS
and security headers, and protect administrative routes. The backend does not trust forwarded
headers or proxy-asserted identity; security-sensitive public URL behavior uses explicit
configuration. Upload validation remains deferred; domain operations must continue to avoid
disclosing stack traces and require explicit authorization.

## Backup and restore

`make backup` creates a timestamped PostgreSQL custom-format dump without overwriting an existing file. `make restore FILE=...` requires an explicit dump, destructive-action confirmation, and the exact target database name because it replaces database contents. See `docs/backup-restore.md`.

## Unresolved questions

- Whether a later concrete requirement justifies multi-user enrollment, external identity federation, or non-browser API credentials.
- Retention, size limits, thumbnailing, and backup consistency for attachments.
- Taxonomy enrichment, name-history persistence, and BotanicalIdentity reconciliation implementation
  deferred by the focused contract in `docs/domain-model.md`.
- Whether production should eventually use immutable registry images instead of local Compose builds.
