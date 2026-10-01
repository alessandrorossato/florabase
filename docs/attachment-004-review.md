# ATTACHMENT-004 implementation handoff

Current shared-media behavior supersedes ownership/removal and derivative details below; see
[ATTACHMENT-005](media-library.md). The remainder is the historical ATTACHMENT-004 review record.

Status: **ATTACHMENT-004 review record**; operator visual review passed.
Branch: `feat/attachment-004`.

## Persistence and mutations

Alembic `20260925_0026` creates `collection_primary_photos`: UUIDv7 identifier, exactly one
SeedLot/Plant/PlantGroup foreign key, exactly one local/external collection-photo foreign key, and
UTC creation/update timestamps. PostgreSQL checks and unique constraints enforce one target/source
per designation and at most one designation per target and source. Source deletion has a defensive
cascade; target deletion is restrictive. Upgrade makes no inferred selection. Downgrade removes only
designation metadata and never touches binaries or existing photo/cover metadata.

Selection locks the target row, then the selected photo, then its Attachment for local sources.
The service checks the photo's exact immutable target and local active state and resolves the
stored file through the trusted attachment resolver before committing. Concurrent selections on
one target serialize on its row; deletion locks the photo before clearing its designation. Reads
omit mismatched target/source or inactive local state. No replacement is inferred.

Changing or clearing primary changes only designation metadata. Photo order, caption, attribution,
and photo timestamps remain intact. Editing photo metadata retains selection. Inactive records
retain their primary. External deletion explicitly clears primary in the deletion transaction and
does not contact a remote host. Local deletion clears primary when committing `pending_delete`,
before unlink, so a failed unlink leaves a retry-only photo with no primary. Final cleanup also
clears designation. Direct Attachment deletion retains existing collection-photo ownership guards.

## API and presentation

All routes use the existing `/api/v1` authentication. Mutations require owner authorization,
CSRF, and the configured exact Origin.

| Operation | Route |
| --- | --- |
| Read, set, clear | `GET`, `PUT`, `DELETE /api/v1/collection-records/{target_type}/{target_id}/primary-photo` |
| Local thumbnail | `GET /api/v1/collection-photos/local/{photo_id}/thumbnail` |

`target_type` accepts only `seed_lot`, `plant`, and `plant_group`. PUT identifies an existing photo
with explicit `kind: local | external` and `photo_id`. Missing target/photo returns 404; wrong target
or unavailable local content returns a stable 409 domain error. Unsupported target and invalid
request data follow typed 422 validation. Compact summaries contain kind, photo ID, and a local
thumbnail URL only, with no storage path/key or external URL.

The fixed thumbnail uses the existing identity-cover safe image renderer through a separate
collection-photo route: oriented decode, maximum edge 320px, no upscale, WebP, private caching,
digest/transform-version ETag, Cookie variation, and no saved derivative. Photo existence, active
Attachment, and trusted file resolution are checked before a response, including a conditional 304.

Existing directory responses batch designation and local/external source queries for the displayed
projection list (at most three added queries per list). Rows request only their selected local
thumbnail; they do not fetch individual primary metadata, galleries, or Attachment metadata.
No-primary rows retain their neutral presentation. Failed thumbnails show an unavailable fallback.

SeedLot, Plant, and PlantGroup detail use a restrained thumbnail below the established header.
Photos offers contextual accessible **Set as primary**, **Primary**, and **Remove primary** controls,
retaining chronological order. Set/clear responses and deletion's authoritative primary refresh
update the gallery, mounted header, and directory state. Successful photo deletion immediately
clears its displayed designation even if the subsequent metadata refresh fails. External primary renders neutral text;
the gallery retains explicit **Load external image**, its privacy disclosure, and no-referrer loading.
Sowing/Event have no primary controls, route target, table target, or directory primary image.
BotanicalIdentity covers have separate ownership, APIs, thumbnail routes, and selection semantics.

## Browser fixture review

An isolated temporary API, frontend, and tmpfs PostgreSQL database were used; the development
database was not migrated. The fixture and services were removed after review.

| Case | Observed result |
| --- | --- |
| A: no photos | Empty Photos state; no primary image or action. |
| B: one photo, no selection | Gallery photo has Set as primary; header/directory show no inferred primary. |
| C: selected local | Directory uses a 52px square thumbnail; mobile detail uses the fixed protected route. |
| D: multiple/change | Switching updates badge and mounted header URL; gallery order remains unchanged. |
| E: remove designation | Header image disappears and the gallery photo remains with Set as primary. |
| F: delete selected local | Protected API deletion then browser refresh shows empty Photos and no header image. |
| G: Plant | Compact directory and detail thumbnail; correct Photos primary controls. |
| H: PlantGroup | Same behavior, including mobile detail and actions. |
| I: external primary | Neutral directory/detail state; no remote image element; explicit loading disclosure remains. |
| J: Sowing | Existing gallery and actions, with no primary control. |

Representative directory/detail/gallery layouts were visually checked at 1440px, 1024px, and
390×844. Mobile actions remain reachable and page scroll width equals viewport width. Tab strips
retain their existing internal overflow behavior. A full Network-panel capture was unavailable;
DOM inspection showed zero external image elements before opt-in, and the existing frontend test
checks explicit loading with `referrerPolicy="no-referrer"`. This is implementation review, not UAT.

## Focused verification

Commands ran with the repository Docker development images (Python 3.14 / Node 24) and disposable
integration Compose project `florabase-primary-focus`. Local Python 3.12 and missing host Node were
unsuitable, so runtime/type/build checks used the configured containers.

- Backend: `ruff format --check .`, `ruff check .`, `mypy`, and
  `python scripts/export_openapi.py --check`.
- Photo unit tests: `pytest --no-cov tests/test_collection_photos.py tests/test_collection_photo_api.py`
  — 13 passed.
- PostgreSQL: `pytest --no-cov tests/integration/test_attachment_api.py
  tests/integration/test_collection_photo_migration.py tests/integration/test_primary_photo_api.py
  tests/integration/test_primary_photo_migration.py` — 19 passed. Includes explicit local/external
  selection, switching/clearing, foreign-target rejection, fail-safe corrupt read, no automatic
  primary on upload, pending-delete unlink failure/retry, external deletion, unsupported targets,
  protected thumbnail, and migration preservation/constraints.
- Frontend: `pnpm format:check`, `pnpm lint`, `pnpm typecheck`, `pnpm build`, and
  `pnpm exec openapi-typescript ../backend/openapi.json --output src/api/schema.d.ts --check`.
- Screen tests: `pnpm test src/seed-lots/SeedLotScreen.test.tsx src/plants/PlantScreen.test.tsx`
  (run together with the photo tests) — 39 existing screen tests passed.
- Photo tests: `pnpm test src/photos/PhotosSection.test.tsx src/photos/PrimaryPhotoVisual.test.tsx`
  — 11 passed, including explicit switching/clearing, primary-preserving edits, authoritative refresh
  and refresh-failure recovery after deleting primary, Sowing/Event exclusion, and
  bounded/local/external/failed representations.
- Existing response unit tests: `pytest --no-cov tests/test_seed_lot.py tests/test_plant.py
  tests/test_seed_lot_schemas.py tests/test_plant_schemas.py` — 50 passed.
- Existing directory/detail API tests: `pytest --no-cov tests/integration/test_seed_lot_api.py
  tests/integration/test_plant_api.py` — 88 passed.
- Production backend: `docker compose -f compose.yaml build backend` — passed.
- Feature graph: `python3 scripts/check-features.py`; whitespace: `git diff --check`.

OpenAPI/frontend declarations, domain model, roadmap, feature status, and progress are updated.
Observed warnings are the existing Alembic `path_separator` deprecation and Vite chunk-size warning.
No unresolved product issue was found in focused implementation checks. Luna retains independent
integrity/security/concurrency test-gap review, the canonical `make feature-verify`, and final commit.

## Independent QA review (2026-09-27)

The independent code review confirmed the explicit-selection contract, exact-target checks,
target/source relational constraints, protected 320px WebP thumbnail route, bounded batched summary
queries, and external-image opt-in behavior. No scope leak to Sowing/Event or BotanicalIdentity
cover selection was found in the changed routes and screen integration.

The review found a writer race between deleting the currently designated photo and selecting a
replacement. The designation lookup in `set_primary` now uses `SELECT FOR UPDATE`, so the replacement
waits for deletion to commit before creating the new designation. A PostgreSQL concurrency test
proves that ordering. The repository's exact migration-head and table-set tests also still asserted
the pre-ATTACHMENT-004 schema; they now expect revision `20260925_0026` and its designation table.
Additional unit tests cover summary fail-closed cases, target locking, selection failures, route
error mapping, thumbnail privacy/cache validators, and upload error normalization.

Focused review tests passed: 13 backend unit/API tests; 28 PostgreSQL tests covering schema-head,
table-set, primary-photo API, migration, and the deletion/replacement race. The complete gate passed:
`make feature-verify` reported `FEATURE_VERIFICATION_PASSED`; 422 backend unit tests, 197 frontend
tests, 351 PostgreSQL integration tests, production builds, API drift checks, and the migration cycle
passed. The migration cycle selected `20260925_0026` and completed `0025 → 0026 → 0025 → 0026`.
Coverage investigation confirmed pytest-cov enforces `fail-under=90` after rounding to its default
precision of zero; 89.75% rounds to 90%, so the pytest process and gate succeed. pytest-cov's
terminal summary separately compares the raw percentage and prints `FAIL`; this is a misleading
reporting inconsistency in the installed pytest-cov version, not a gate failure. No coverage
threshold or policy was changed. Existing Alembic `path_separator` and Vite chunk-size warnings remain.

**Operator visual review passed.** The independent QA browser tool could not inspect the local
review app, as recorded above; the operator subsequently completed the manual viewport and lifecycle
review and reported a pass. This status is based on the operator's explicit review result.
