# UX-SORT-002 evidence

- **Branch:** `feat/ux-sort-002` from `feat/fn-05-directory-sort`
  `760283a6ed05f9b65111b5c25720dfd6bb13c02c` (UX-SORT-001, carried by batch 13 and not yet on
  `main` then). It reuses that branch's `DirectorySortSelect`, `DirectorySort` types and saved-view
  sort fields. After batch 13 landed as `08ff2f9` (#227) the branch merged `origin/main`; conflicts
  were additive (saved-view state, features/scope registers, `progress.md` kept both).
- **Writer:** `claude-ux-sort-002`
- **Feature:** `UX-SORT-002` (`implemented`; proposed release class `best-effort` in
  [`docs/release/scope-v1.json`](../scope-v1.json), next to `UX-SORT-001`)
- **Migrations:** none. **OpenAPI:** additive optional `sort` query parameter on four list
  operations plus `sort` on the Orders, Media and Cuttings saved-view state schemas;
  `make api-generate` regenerated `backend/openapi.json` and `frontend/src/api/schema.d.ts`.

## Scope

UX-SORT-001 skipped Orders, Media and Cuttings because they paginate on the server
(`limit`/`offset`), so sorting the loaded page in the browser would be wrong. This increment moves
the order to SQL.

1. **Backend.** `backend/src/florabase/db/ordering.py` owns the shared `DirectorySort` literal
   (`name`, `name_desc`, `newest`, `oldest`) and `directory_order()`, which builds the `ORDER BY`
   from a name expression, a date (one timestamp or partial year/month/day) and the record id.
   Names compare with `lower()`; a missing month or day sorts as the start of its year or month
   (same rule as the client `sortDirectory`); records without a name or date stay last in both
   directions; the id breaks ties in the sort direction, so `limit`/`offset` pages never repeat or
   skip rows. FastAPI validates the `Literal`, so any other value is a 422 and no caller text
   reaches SQL. `saved_views/state.py` now imports the same literal instead of redefining it.
2. **Saved views.** `OrderState`, `MediaState` and `CuttingsState` (backend) and `orders`, `media`,
   `cuttings` in `frontend/src/saved-views/state.ts` accept `sort`; unknown values are rejected.
3. **Frontend.** Orders, Media and Cuttings render `DirectorySortSelect` with dated options, send
   `sort` only when chosen, and return to the first page on change. Cuttings keeps the choice when
   switching between Material lots and Rooting attempts and on filter reset (both offer the same
   options); every screen keeps it on filter reset like UX-SORT-001.

## Directory keys

| Screen | Endpoint | Name key (mirrors the displayed name) | Date key (`dateLabel`) | Default when absent |
| --- | --- | --- | --- | --- |
| Orders | `/api/v1/orders` | `order_reference` (unset references, shown as "Purchase order", last) | `ordered_on` partial date ("order date") | Unchanged: newest order date, undated last, id desc (now expressed as `newest`) |
| Media | `/api/v1/media-assets` | `coalesce(title, original_filename, attribution)` | `created_at` ("added") | Unchanged: `created_at` desc, id desc (now expressed as `newest`) |
| Cuttings · Material lots | `/api/v1/vegetative-lots` | `coalesce(label, common_name, cultivar_name, scientific_name)` | `taken_on` partial date ("taken or acquired date") | Unchanged: id desc |
| Cuttings · Rooting attempts | `/api/v1/propagation-attempts` | `coalesce(label, scientific_name ‖ ' ' ‖ cultivar_name)` | `started_on` partial date ("start date") | Unchanged: id desc |

`/api/v1/vegetative-lots` now always inner-joins its required botanical identity (previously only
when searching) so the name key is available; the join is on a non-null foreign key and does not
change counts or filters.

## Known limits

- SQL `lower()` under the database collation is close to, but not identical with, the browser's
  `localeCompare(..., { numeric: true, sensitivity: "base" })` used by client-side directories: for
  example `Batch 10` sorts before `Batch 9` on the server. Natural numeric collation was not
  requested and would need an ICU collation.
- The lot name fallback ignores the client rule that hides a cultivar equal to the scientific
  name; both spell the same text, so only ties between such records change, and the id resolves
  them.
- History stays without Sort by: it is a chronological feed, as recorded in UX-SORT-001.

## Acceptance evidence

| Criterion | Evidence |
| --- | --- |
| Whitelisted optional `sort`, 422 otherwise, default unchanged | `backend/tests/integration/product/test_directory_sort.py::test_sort_parameter_is_whitelisted` (under the owned `product` integration scope) (four endpoints × four values = 200; `created`, `id`, `name;drop`, empty = 422); each ordering test asserts `None` equals the previous default |
| Server order before pagination, nulls last, stable ties | `test_orders_sort_by_reference_and_partial_order_date`, `test_media_sort_by_displayed_title_and_date_added`, `test_cutting_lots_and_attempts_sort_by_record_name_and_date`: exact order for every sort, case-insensitive name ties and same-date ties resolved by id, and a one-record page walk equal to the full order |
| UI, first-page reset, record-type switch, URL and Saved View state | `frontend/src/orders/OrderScreen.test.tsx`, `frontend/src/media/MediaScreen.test.tsx`, `frontend/src/ui-pages/Cuttings/Cuttings.test.tsx` (UX-SORT-002 tests); `frontend/src/saved-views/state.test.ts`; `backend/tests/test_saved_views.py` accepted/rejected cases |
| Generated contract | `make api-generate`, then `make api-check` passes |

## Checks run (focused, before the canonical gate)

- `ruff format`, `ruff check`, `mypy` (390 files): pass.
- `pnpm format`, `pnpm lint`, `pnpm typecheck`: pass.
- `pnpm vitest run src/orders src/media src/ui-pages/Cuttings src/saved-views src/components`:
  pass.
- `pytest -m "not integration"` on saved views, media, orders and cuttings unit tests: 200 passed
  (the coverage threshold only applies to the full suite).
- `./scripts/test-integration.sh` on `product/test_directory_sort.py`, `test_orders.py`,
  `test_cuttings_api.py`, `test_shared_media.py`, `test_saved_views.py`,
  `test_history_saved_views.py`: 68 passed.
- `make api-check`: pass.

The canonical `make feature-verify` runs from the operator's terminal; its receipt is not claimed
here.
