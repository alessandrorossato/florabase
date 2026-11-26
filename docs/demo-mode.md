# Public Read-Only Demo Mode (`DEMO-001`)

Florabase supports an explicit, opt-in **public read-only demo mode** (`FLORABASE_DEMO_READONLY=true`)
designed for hosting a public showcase instance (such as `https://demo.florabase.eu`) backed by the
sample [Golden dataset](dev-golden.md) without exposing owner credentials or allowing database writes.

By default, `FLORABASE_DEMO_READONLY` is `false` and **none** of the demo middleware, auto-session
resolution, or guided-tour UI is active. Standard production authentication (`G-SEC` / `ENG-03`)
remains unchanged.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `FLORABASE_DEMO_READONLY` | `false` | Enables read-only demo mode. Blocks all non-safe HTTP methods (`POST`, `PUT`, `PATCH`, `DELETE`) with `403` (`demo_read_only`), advertises `"demo-readonly"` in `GET /api/v1/system/info`, and resolves read requests against the single enabled owner without writing `auth_sessions` rows. |
| `FLORABASE_WORKERS` | `1` | Optional Uvicorn worker count (`1`–`8`) passed by `release_schema serve`. Useful on multi-vCPU VPS hosts during public traffic spikes. |

## Security invariants

1. **Default-off isolation:** When `FLORABASE_DEMO_READONLY=false`, `DemoReadOnlyMiddleware` is not
   mounted, `GET /api/v1/system/info` omits `"demo-readonly"`, `GET /api/v1/auth/session` returns
   `demo_readonly: false` only for authenticated actors, and unauthenticated requests return `401`.
2. **Defense-in-depth write blocking:** When `FLORABASE_DEMO_READONLY=true`:
   - `DemoReadOnlyMiddleware` rejects every non-`GET`/`HEAD`/`OPTIONS` HTTP request at the ASGI
     boundary with HTTP `403`, `Cache-Control: no-store`, and `detail.code = "demo_read_only"`.
   - `require_authenticated_actor` and `require_csrf` independently reject non-safe methods and
     CSRF-protected mutations.
   - Read resolution queries only the single enabled owner (`users`) and constructs an ephemeral
     in-memory session — zero rows are written to PostgreSQL while visitors browse.
3. **Zero extra bundle weight for normal owners:** The frontend lazy-loads `DemoExperience` (slim
   top banner, read-only mutation notice, and 7-step interactive guided tour across real workspaces)
   only when `session.demo_readonly === true`.

## Guided tour entry

- First-time demo visitors automatically see the 7-step guided tour walking through **Today**,
  **Botanical identities**, **Seeds & Sowings**, **Plants & Cuttings**, **Lineage & Taxonomy**,
  **Geography**, and **Schedule & Self-hosting**.
- External links (such as from `https://florabase.eu`) can force-open the tour at any time with
  `/?tour=1#/dashboard`.
- Visitors can dismiss the tour with `Esc` or **Skip tour** and restart it anytime from the top
  demo banner.

## Reverse-proxy caching for high-traffic launches

Because `FLORABASE_DEMO_READONLY=true` never mutates collection data and requires no per-visitor
session cookie on `GET` requests, an edge or host reverse proxy (Caddy/Nginx) can safely:

- Micro-cache `GET /api/v1/*` JSON responses (excluding `/api/v1/auth/session` and
  `/api/v1/system/info`) in RAM for 60–300 seconds.
- Cache thumbnail responses (`/api/v1/attachments/*/thumbnail`) for 24 hours.
- Apply per-IP rate limits to external provider lookups (`/api/v1/external-botany/*`).
