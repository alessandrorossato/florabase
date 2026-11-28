# Public Read-Only Demo Mode (`DEMO-001`)

Florabase supports an explicit, opt-in **public read-only demo mode** (`FLORABASE_DEMO_READONLY=true`)
designed for hosting a public showcase instance (such as `https://demo.example.org`) backed by the
sample [Golden dataset](dev-golden.md) without exposing owner credentials, allowing database writes,
or forwarding public visitor traffic to external botanical providers.

By default, `FLORABASE_DEMO_READONLY` is `false` and **none** of the demo middleware, auto-session
resolution, or guided-tour UI is active. Standard production authentication (`G-SEC` / `ENG-03`)
remains unchanged.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `FLORABASE_DEMO_READONLY` | `false` | Enables public read-only demo mode. Requires an explicit demo marker file in attachment storage (see below); blocks all non-safe HTTP methods (`POST`, `PUT`, `PATCH`, `DELETE`) with `403` (`demo_read_only`); forces external GBIF GET endpoints into cache-only mode; advertises `"demo-readonly"` in `GET /api/v1/system/info`; returns a neutral `"Demo visitor"` identity on `GET /api/v1/auth/session` without writing `auth_sessions` rows. |
| `FLORABASE_WORKERS` | `1` | Optional Uvicorn worker count (`1`–`8`) parsed once by `release_schema serve`. Keep at `1` on single-owner NAS installations; each additional worker adds ~150–200 MiB RAM. When `FLORABASE_WORKERS > 1`, each worker runs its own `ReferenceSetupCoordinator` (serialized by the build file lock, with per-worker retry timers on failure), so pre-provisioning references or setting `FLORABASE_REFERENCES_SETUP=off` is recommended on multi-worker demo hosts. |

## Explicit startup guard (preventing accidental exposure)

Because `FLORABASE_DEMO_READONLY=true` serves read requests without login, setting the environment
variable alone is **refused at startup** (both in `release_schema serve` and in FastAPI `lifespan`).

To start a demo instance, the demo provisioning step must explicitly write a regular, non-symlink
marker file at `<FLORABASE_ATTACHMENT_STORAGE_ROOT>/.florabase-demo-readonly.marker` containing:

```text
florabase-public-read-only-demo-v1
```

If the marker is missing, a symlink, unreadable, or has any other content, the backend exits before
serving requests. When accepted, the backend logs a loud startup warning:
`PUBLIC READ-ONLY DEMO: no login required`.

## Security invariants & GET route audit

1. **Default-off isolation:** When `FLORABASE_DEMO_READONLY=false`, `DemoReadOnlyMiddleware` is not
   mounted, `GET /api/v1/system/info` omits `"demo-readonly"`, `GET /api/v1/auth/session` returns
   `demo_readonly: false` only for authenticated actors, and unauthenticated requests return `401`.
2. **Defense-in-depth write blocking:** When `FLORABASE_DEMO_READONLY=true`:
   - `DemoReadOnlyMiddleware` rejects every non-`GET`/`HEAD`/`OPTIONS` HTTP request at the ASGI
     boundary with HTTP `403`, `Cache-Control: no-store`, and `detail.code = "demo_read_only"`.
   - `require_authenticated_actor` and `require_csrf` independently reject non-safe methods and
     CSRF-protected mutations.
   - `resolve_demo_actor` builds a transient in-memory `AuthSession` placeholder that is never added
     to SQLAlchemy — **zero database rows** are written while visitors browse.
3. **Neutral public identity:**
   - `GET /api/v1/auth/session` returns a neutral identity (`user_id: 00000000-0000-0000-0000-000000000000`,
     `login_name: ""`, `display_name: "Demo visitor"`, `owner: false`, `demo_readonly: true`) instead
     of exposing the real database owner’s login name or UUID.
   - `GET /api/v1/auth/device-sessions` always returns `{"items": []}`.
   - The frontend shell hides `Sign out`, `Record`, `+ New`, saved-view removal buttons, and
     owner-only Settings destinations (`Account`, `Media`, `Import / Export`), while preserving
     read-only and local client tools (`Theme`, `Labels`, `Data sources`, `Help`, `About`).
4. **GET route side-effect audit (zero DB writes, zero outbound GBIF calls):**
   - `external_botany` (`GET /botanical-identities/{id}/external-taxa/search`,
     `GET /botanical-identities/{id}/occurrence-map/summary`,
     `GET /botanical-identities/{id}/occurrence-map/tiles/{z}/{x}/{y}.png`): strictly **cache-only**
     in demo mode. Cached entries are served normally; cache misses return `403`
     (`demo_external_lookup_disabled`) or `404` (`occurrence_tile_not_cached`) without calling GBIF,
     inserting `ExternalProviderCache` rows, or writing tile files to disk.
   - `external_botany` (`GET /external-taxon-link`, `GET /occurrence-map/cache`),
     `botanical_identities`, `native_range_enrichment`, `taxonomy`, `media` metadata, and
     `attachments`: pure local DB, local SQLite snapshot, or local original file reads.
   - **Bounded thumbnail derivatives** (`GET /media-assets/{id}/thumbnail`,
     `GET /botanical-identities/{id}/cover-image/thumbnail`,
     `GET /collection-photos/{id}/thumbnail`): may lazily generate and persist at most one
     deterministic 320px WebP file per pre-existing seeded media asset into `.thumbnails/` on first
     view (bounded by the fixed demo dataset; zero DB writes, zero outbound HTTP calls; can be
     pre-warmed before opening the demo publicly).
5. **Zero extra bundle weight for normal owners:** The frontend lazy-loads `DemoExperience` (slim
   top banner, read-only mutation notice, and 7-step interactive guided tour across real workspaces)
   only when `session.demo_readonly === true`.

## Guided tour entry

- First-time demo visitors automatically see the 7-step guided tour walking through **Today**,
  **Botanical identities**, **Seeds & Sowings**, **Plants & Cuttings**, **Lineage & Taxonomy**,
  **Geography**, and **Schedule & Self-hosting**.
- External links can force-open the tour at any time with `/?tour=1#/dashboard`.
- Visitors can dismiss the tour with `Esc` or **Skip tour** and restart it anytime from the top
  demo banner. Tour dismissal state uses `sessionStorage` wrapped in `try/catch` so private-browsing
  restrictions degrade cleanly.

## Caching & rate limiting notes

- **Thumbnails:** In demo mode, the three thumbnail GET endpoints send
  `Cache-Control: public, max-age=86400` without `Vary: Cookie`, allowing a reverse proxy or CDN to
  cache them across visitors. In standard mode (`FLORABASE_DEMO_READONLY=false`), thumbnails retain
  `Cache-Control: private, max-age=86400, must-revalidate` and `Vary: Cookie`.
- **Non-cacheable endpoints:** `GET /api/v1/auth/session`, `GET /api/v1/system/info`, and
  `GET /api/v1/botanical-identities/*/occurrence-map/cache` send `no-store`.
- **Rate limiting and periodic resets:** Not implemented inside the application container; per-IP
  rate limiting belongs at the reverse proxy / edge layer today, with dedicated demo security
  hardening, rate limiting, and optional periodic reset tooling planned separately (Batch 17).
