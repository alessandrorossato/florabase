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
  It uses relative API URLs and never connects to PostgreSQL. Workspaces and propagation wizards
  load on navigation through React lazy/Suspense; optional maps and Labels/QR remain lazy. Failed
  workspace downloads retain the authenticated shell with a reload action. Public static assets
  use nginx compression; authenticated API/media responses retain their existing behavior.
  See [PERF-001 measurements](performance/PERF-001.md).
  LABEL-001's temporary browser composer derives SeedLot, Plant, and PlantGroup labels from existing
  protected APIs, generates SVG QRs locally, and prints through CSS physical units. Lookup uses the
  application's existing hash detail routes and configured canonical origin; no public endpoint,
  new URL setting, persistence, worker, external image request, or PDF service is added. See
  [labels.md](labels.md).
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
The authenticated session returns that configured canonical origin to UI features that need to
construct stable public links; request Host and forwarded headers do not select it.
Development explicitly uses `http://localhost:5173` and a loopback-only cookie mode. See
[deployment.md](deployment.md).

## Persistence and migrations

PostgreSQL uses `postgres_data`; guarded local attachments use the separate `attachment_data` named
volume mounted only by the backend at `/var/lib/florabase/attachments`. The image prepares that
mount point for the existing non-root UID/GID 10001 runtime account. Server-generated storage keys
remain beneath one centrally configured trusted root, and neither uploaded filenames nor URL values
select filesystem paths. Nginx does not mount or expose the volume. Container layers hold no durable
state. See [ADR 0006](decisions/0006-local-attachment-storage.md).

Alembic is the only schema-change path, and migrations run explicitly rather than at application
startup. Application-generated UUIDv7 identifiers and UTC timestamps follow
[ADR 0004](decisions/0004-identifier-strategy.md).

## API and generated types

All application routes are under `/api/v1`. The backend generates committed `backend/openapi.json`;
`openapi-typescript` generates committed `frontend/src/api/schema.d.ts`. `make api-generate` refreshes
both and `make api-check` detects drift.

## Implemented domain modules

The application currently persists and exposes BotanicalIdentity, BotanicalProfile, structured
BotanicalProfile native ranges, external botanical reference links, Supplier, Location,
GeographicPlace, ProvenanceSite, SeedLot, Sowing, Plant, PlantGroup, Event, and typed authoritative
operation receipts. Direct foreign keys express the supported workflow lineage: SeedLot to Sowing
to Plant/PlantGroup, PlantGroup extraction to Plant, and Plant/PlantGroup production of a
collection-produced SeedLot. Events record Plant and PlantGroup history without making the system
event-sourced; operation receipts support the deliberately bounded reintegration and propagation
reversals. Attachment metadata and guarded local binary storage are implemented without collection
photo relationships. The implementation does not use a generic graph, polymorphic collection item,
generic event framework, or generic media subsystem.

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

Attachments and uploads, richer germination observations and Event payloads, advanced search,
analytical dashboards, import/export, PWA installability, multi-user collaboration, automatic
taxonomy reconciliation, provider-backed profile enrichment, and additional external integrations
remain backlog items. Their storage and service infrastructure will be designed only when a
concrete feature requires it.
