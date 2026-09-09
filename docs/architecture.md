# Architecture

## System boundary

Florabase is a self-hosted modular monolith. A React browser application calls a versioned FastAPI
REST API, and the API is the only application component that reads or writes PostgreSQL.

```text
Browser → frontend nginx → /api/v1 → FastAPI → PostgreSQL
                    └────→ static React application
```

The host, HTTPS reverse proxy, DNS, TLS material, database backups, and host hardening remain operator
responsibilities.

## Responsibilities

- The backend owns validation, authentication and authorization, business rules, transactions,
  OpenAPI, and structured logs.
- The frontend owns accessible interactions and explicit loading, empty, success, and failure states.
  It uses relative API URLs and never connects to PostgreSQL.
- PostgreSQL is the source of truth for accounts, sessions, reference data, collection data,
  constraints, timestamps, and migration state.
- The production frontend nginx serves built assets and proxies `/api/`; it is not the public TLS
  boundary.

## Runtime and configuration

`compose.yaml` is production-oriented: PostgreSQL and FastAPI are internal, the frontend alone
publishes a port, services have health checks, and application containers run non-root where
practical. `compose.dev.yaml` adds bind-mounted source, hot reload, and loopback-only development
ports. `compose.integration.yaml` owns an isolated tmpfs PostgreSQL test project.

Backend settings are centralized in `florabase.core.config`. Production requires an exact HTTPS
canonical origin, secure cookies, and empty CORS configuration for the same-origin application.
Development explicitly uses `http://localhost:5173` and a loopback-only cookie mode. See
[deployment.md](deployment.md).

## Persistence and migrations

The `postgres_data` named volume is the only durable application data store today. No uploads or
attachment volume exists. Container layers hold no durable state.

Alembic is the only schema-change path, and migrations run explicitly rather than at application
startup. Application-generated UUIDv7 identifiers and UTC timestamps follow
[ADR 0004](decisions/0004-identifier-strategy.md).

## API and generated types

All application routes are under `/api/v1`. The backend generates committed `backend/openapi.json`;
`openapi-typescript` generates committed `frontend/src/api/schema.d.ts`. `make api-generate` refreshes
both and `make api-check` detects drift.

## Implemented domain modules

The application currently persists and exposes BotanicalIdentity, BotanicalProfile, structured
BotanicalProfile native ranges, Supplier, Location, GeographicPlace, SeedLot, Sowing, Plant, and
PlantGroup. Direct foreign keys express the
supported workflow lineage: SeedLot to Sowing to Plant/PlantGroup, PlantGroup extraction to Plant,
and Plant/PlantGroup production of a collection-produced SeedLot. The implementation does not use a
generic graph, polymorphic collection item, event framework, or attachment subsystem.

See [domain-model.md](domain-model.md) for semantics and current limitations.

## Authentication and observability

FastAPI owns local accounts and opaque PostgreSQL-backed sessions. Production uses a Secure,
HttpOnly, SameSite=Strict cookie; state changes additionally require exact-Origin and session-bound
CSRF validation. Reverse-proxy headers never assert identity. See
[ADR 0005](decisions/0005-authentication-and-sessions.md) and [security.md](security.md).

Application logs go to stdout. Production defaults to JSON. `/api/v1/health` is liveness;
`/api/v1/ready` executes a database readiness check. `make health` reaches both through the frontend
proxy.

## Deliberately deferred

Attachments and uploads, Plant events and observation history, advanced search, dashboards,
import/export, PWA installability, multi-user collaboration, taxonomy reconciliation, and external
integrations remain backlog items. Their storage and service infrastructure will be designed only
when a concrete feature requires it.
