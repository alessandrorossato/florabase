# DEMO-001 — Opt-in Public Read-Only Demo Mode & Guided Tour

- **Branch:** `feat/demo-001-readonly-tour`
- **Base:** `7b667a4781fd6213d66ef291851e3d252c97eb33` (`origin/main` post Batch 14b, realigned from `08ff2f9`)
- **Writer:** `antigravity-demo-001`
- **Proposed release class in `docs/release/scope-v1.json`:** `best-effort` (operator confirmation requested at delivery)

## Scope summary (including independent review fixes)

1. **Opt-in read-only backend (`FLORABASE_DEMO_READONLY=true`, default `false`):**
   - **Explicit startup marker guard (Must-Fix #2):** `verify_demo_marker` refuses startup in both
     `release_schema serve` and FastAPI `lifespan` unless a regular, non-symlink
     `.florabase-demo-readonly.marker` file inside attachment storage contains
     `florabase-public-read-only-demo-v1`. When accepted, logs
     `PUBLIC READ-ONLY DEMO: no login required`.
   - **Layered write blocking:** `DemoReadOnlyMiddleware` rejects every non-`GET`/`HEAD`/`OPTIONS`
     request with `403` (`detail.code = "demo_read_only"`, `Cache-Control: no-store`);
     `require_authenticated_actor` and `require_csrf` independently enforce read-only behavior.
   - **Cache-only external provider GETs (Must-Fix #1):** `GET /external-taxa/search`,
     `GET /occurrence-map/summary`, and `GET /occurrence-map/tiles/{z}/{x}/{y}.png` never call GBIF,
     never insert `ExternalProviderCache` rows, and never write tile files on cache miss in demo
     mode (returning cached data or `403 demo_external_lookup_disabled` / `404 occurrence_tile_not_cached`).
   - **Neutral public identity (Should-Fix #3):** `GET /api/v1/auth/session` returns
     `user_id: 00000000-0000-0000-0000-000000000000`, `login_name: ""`, `display_name: "Demo visitor"`,
     `owner: false`, `demo_readonly: true`; `GET /api/v1/auth/device-sessions` returns `{"items": []}`.
   - **Transient placeholder session (Nit #7):** `resolve_demo_actor` constructs a transient
     in-memory `AuthSession` never added to SQLAlchemy (zero `auth_sessions` DB writes).
   - **Public demo thumbnail caching (Should-Fix #6):** the three thumbnail GET endpoints emit
     `Cache-Control: public, max-age=86400` without `Vary: Cookie` in demo mode (unchanged
     `private` + `Vary: Cookie` in standard mode).
   - **Standard mode untouched:** when `FLORABASE_DEMO_READONLY=false`, `PUBLIC_OPERATIONS`
     (`ENG-03`/`G-SEC`), `system/info` (`capabilities: ["device-auth"]` + `runtime_config`),
     login/CSRF/session handling, and private thumbnail headers remain unchanged.
2. **Optional multi-worker scaling (`FLORABASE_WORKERS`, `1..8`, default `1`, Should-Fix #4):**
   - Single source of truth in `release_schema.uvicorn_workers_from_environment` (duplicate unused
     `Settings.workers` removed); passes `--workers <N>` to `uvicorn` only when `> 1`.
   - Documented NAS default `1`, memory cost per worker, and `REF-SETUP-001` multi-worker lock/retry
     behavior in `docs/installation.md` and `docs/demo-mode.md`.
3. **Frontend 1-click entry, neutral demo shell & 7-step interactive guided tour:**
   - `AuthProvider` skips `POST /api/v1/auth/csrf` when `session.demo_readonly === true` and forwards
     `403 demo_read_only` errors to `shell/demo/readonlyNotice.ts`.
   - `WorkbenchShell` hides `Sign out`, `Record`, `+ New`, saved-view removal controls, and
     owner-only Settings links (`Account`, `Media`, `Import / Export`), displaying
     `Demo visitor (read-only)`.
   - `App` lazy-loads `shell/demo/DemoExperience.tsx` (0 bytes in normal builds), rendering the
     semantic-token `Read-only demo` banner, polite read-only mutation notice, and 7-step guided
     tour across real workspaces (`#/dashboard`, `#/identities`, `#/seeds`, `#/plants`, `#/lineage`,
     `#/geography`, `#/schedule`) with keyboard `Escape`, progress dots, restart button, `?tour=1`,
     private-mode `sessionStorage` `try/catch` (Nit #8), and GitHub `docs/installation.md` link
     (Should-Fix #5 — no unowned domain hardcoded).

## Audited GET routes (Must-Fix #1)

| Route group | Demo behavior | Outbound HTTP | DB writes | Disk writes |
| --- | --- | --- | --- | --- |
| `external_botany` (`external-taxa/search`, `occurrence-map/summary`, `occurrence-map/tiles`) | Cache-only (`403` / `404` on miss) | None | None | None |
| `external_botany` (`external-taxon-link`, `occurrence-map/cache`) | Local DB read | None | None | None |
| `botanical_identities`, `native_range_enrichment`, `taxonomy` | Local DB / SQLite snapshot reads | None | None | None |
| `media` metadata & `attachments` (`/{id}`, `/{id}/content`) | Local DB / original file reads | None | None | None |
| Thumbnail GETs (`media-assets`, `cover-image`, `collection-photos`) | Reads local original; public cache headers in demo | None | None | Bounded: at most one 320px WebP derivative per pre-existing seeded asset under `.thumbnails/` on first view |

## Acceptance criteria verification

- Default-off `G-SEC` / `ENG-03` preservation: `backend/scripts/test_check_api_routes.py`,
  `backend/tests/test_system_info.py`, `backend/tests/test_auth_api.py`,
  `backend/tests/test_infrastructure.py`, `backend/tests/product/test_demo_readonly.py`.
- Demo marker startup refusal/acceptance, loud warning, cache-only external GETs, transient
  session, neutral visitor identity, empty device sessions, public demo thumbnail headers, and
  `FLORABASE_WORKERS` single-source parsing: `backend/tests/product/test_demo_readonly.py` and
  PostgreSQL integration `backend/tests/integration/product/test_demo_readonly_api.py`.
- Guided tour pipeline, private-mode `sessionStorage`, `WorkbenchShell` demo filtering,
  `AuthProvider` CSRF skip, and 403 notice UX: `frontend/src/shell/demo/DemoExperience.test.tsx` and
  `frontend/src/auth/SessionRecovery.test.tsx`.
- OpenAPI/TypeScript alignment, feature graph, doc links, and canonical verification gate:
  `make api-check`, `scripts/check-features.py`, `scripts/check-doc-links.py`, and
  `make verify-full AGENT_ID=antigravity-demo-001`.
