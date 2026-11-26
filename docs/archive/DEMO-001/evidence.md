# DEMO-001 — Opt-in Public Read-Only Demo Mode & Guided Tour

- **Branch:** `feat/demo-001-readonly-tour`
- **Base:** `08ff2f92d6f9b5496c04ed3b0ae5828451e35269` (`origin/main`)
- **Writer:** `antigravity-demo-001`
- **Proposed release class in `docs/release/scope-v1.json`:** `best-effort` (operator confirmation requested at delivery)

## Scope summary

1. **Opt-in read-only backend (`FLORABASE_DEMO_READONLY=true`, default `false`):**
   - `DemoReadOnlyMiddleware` rejects every non-`GET`/`HEAD`/`OPTIONS` request with `403`
     (`detail.code = "demo_read_only"`, `Cache-Control: no-store`).
   - `require_authenticated_actor` and `require_csrf` independently enforce read-only behavior when
     `demo_readonly=True`, resolving read traffic against the single enabled owner without writing
     `auth_sessions` rows.
   - `GET /api/v1/system/info` appends `"demo-readonly"` to `capabilities` only when enabled;
     `GET /api/v1/auth/session` includes `demo_readonly`.
   - Standard production mode (`FLORABASE_DEMO_READONLY=false`) leaves `PUBLIC_OPERATIONS` (`ENG-03` /
     `G-SEC`), login/CSRF/session handling, and normal production behavior completely unchanged.
2. **Optional multi-worker scaling (`FLORABASE_WORKERS`, `1..8`, default `1`):**
   - Validated in `Settings` and `release_schema.uvicorn_workers_from_environment`; passes
     `--workers <N>` to `uvicorn` only when `> 1`.
3. **Frontend 1-click entry & 7-step interactive guided tour:**
   - `AuthProvider` skips `POST /api/v1/auth/csrf` when `session.demo_readonly === true` and forwards
     `403 demo_read_only` errors to `shell/demo/readonlyNotice.ts`.
   - `App` disables Sign out and lazy-loads `shell/demo/DemoExperience.tsx` (0 bytes in normal self-hosted
     builds), rendering the semantic-token `Read-only demo` banner, polite read-only mutation toast,
     and 7-step guided tour across real workspaces (`#/dashboard`, `#/identities`, `#/seeds`,
     `#/plants`, `#/lineage`, `#/geography`, `#/schedule`) with keyboard `Escape`, progress dots,
     restart button, and `?tour=1` entry support.

## Acceptance criteria verification

- Default-off `G-SEC` / `ENG-03` preservation: verified by `backend/scripts/test_check_api_routes.py`,
  `backend/tests/test_system_info.py`, `backend/tests/test_auth_api.py`, and
  `backend/tests/product/test_demo_readonly.py`.
- Read-only enforcement & zero session DB writes against real PostgreSQL: verified by
  `backend/tests/integration/product/test_demo_readonly_api.py`.
- Multi-worker validation & launch command: verified by `backend/tests/product/test_demo_readonly.py`
  and `backend/tests/test_release_schema.py`.
- Guided tour pipeline, `AuthProvider` CSRF skip, and 403 notice UX: verified by
  `frontend/src/shell/demo/DemoExperience.test.tsx` and `frontend/src/auth/SessionRecovery.test.tsx`.
- OpenAPI/TypeScript contract alignment, backlog graph, doc links, and canonical gate: verified by
  `make api-check`, `scripts/check-features.py`, `scripts/check-doc-links.py`, and
  `make feature-verify AGENT_ID=antigravity-demo-001`.
