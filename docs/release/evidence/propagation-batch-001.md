# PROPAGATION-BATCH-001 evidence

- Branch: `feat/propagation-batch-001` from `origin/main` `1a78476` (writer
  `neon-propagation-batch-001`), prepared for Batch 13 alongside `feat/care-bulk-001`.
- Proposed release class in `docs/release/scope-v1.json`: `best-effort` (registered right after
  `PROPAGATION-003`). No database migration, no new receipt kind or grouping ID, and no changes to
  `propagation/reversal.py` or `SowingDescendantWizard.tsx`.

## Scope implemented

- **Pure label expansion** (`backend/src/florabase/propagation/labels.py`): single-line whitespace
  normalization, control-character rejection, `{n}` placeholder expansion with `counter_start`
  (default 1) and `counter_padding` (default: digits of last number), 1–200 count bounds, and
  ≤255-character expanded-label enforcement. Patterns without `{n}` for N > 1 are permitted and
  surfaced as a UI warning.
- **Sowing batch pot-on** (`POST /api/v1/sowings/{sowing_id}/pot-on`, `operation_id: potOnSowing`):
  `SowingPotOnCreate`/`SowingPotOnResponse` in `propagation/schemas.py` and
  `create_plants_from_sowing_batch` appended at the end of `propagation/service.py`. Locks the
  Sowing once, checks `expected_sowing_updated_at` (409 `stale_preview`), rejects reversed (409
  `reversed_sowing_is_historical`) and inactive (409 `sowing_not_active`) sowings, creates N Plants
  in one transaction with one existing `SOWING_TO_PLANT` receipt each, keeps Sowing lifecycle
  unchanged on iterations 1…N−1 and applies `resulting_sowing_lifecycle` only on iteration N.
  `germinated_count` is an advisory hint and never enforced. Reversal remains `REVERSAL-001`
  newest-first per source.
- **PlantGroup batch split** (`POST /api/v1/plant-groups/{plant_group_id}/extract-batch`,
  `operation_id: extractPlantsFromGroup`): `PlantGroupExtractBatchCreate` /
  `PlantGroupExtractBatchResponse` and `extract_plants_batch` appended at the end of
  `plants/schemas.py` and `plants/service.py` (middle untouched to avoid Batch 13 conflicts with
  `feat/care-bulk-001`). Loops existing `extract_plant` (one extraction Event and one
  `PLANT_GROUP_EXTRACTION` receipt each), caps exact-quantity groups at current exact quantity
  (409 `plant_group_quantity_exceeded`), allows approximate/unknown groups up to 200 without
  modifying group quantity, checks `expected_plant_group_updated_at` (409 `stale_preview`), and
  preserves `PLANT-006` newest-first reintegration. Any failure at plant k rolls back the entire
  transaction.
- **OpenAPI & TypeScript contract**: regenerated `backend/openapi.json` and
  `frontend/src/api/schema.d.ts` (`make api-check` clean).
- **Frontend**: `frontend/src/propagation/api.ts`, `frontend/src/propagation/PotOnDialog.tsx`, and
  minimal launchers in `frontend/src/sowings/SowingScreen.tsx` ("Pot on seedlings…") and
  `frontend/src/plants/PlantScreen.tsx` ("Split into plants…"). Supports N individual Plants or one
  PlantGroup of N (using existing `createPlantGroupFromSowing`), germinated hint, live `{n}` preview
  (first 3 + last), searchable `ReferencePicker` for identity and plant-scoped location, today's
  `PartialDateField`, smart Completed default when N ≥ germinated, explicit preview sentence before
  confirm, 409 `stale_preview` refresh, and links to created records.

## Acceptance mapping and test evidence

Tested on the frozen tip of `feat/propagation-batch-001` (canonical gate receipt binds the exact
HEAD commit and tree digest):

| Criterion | Coverage |
| --- | --- |
| 1. Pot on 12 from a sowing (12 plants, 12 receipts, sowing completed, one request) | `backend/tests/integration/propagation/test_propagation_batch_api.py::test_pot_on_12_plants_receipts_and_newest_first_full_reversal`, `frontend/src/propagation/PotOnDialog.test.tsx` |
| 2. Newest-first reversal of all 12 restores sowing (and reversing sowing restores seed lot) | `backend/tests/integration/propagation/test_propagation_batch_api.py::test_pot_on_12_plants_receipts_and_newest_first_full_reversal` |
| 3. Split 5 from exact group of 20 (group 15, 5 plants, 5 extraction events, PLANT-006 reintegration) | `backend/tests/integration/propagation/test_propagation_batch_api.py::test_group_split_exact_approximate_exceeded_reintegration_and_rollback` |
| Rollback on plant k failure, limits 0/201, >255 label, stale/inactive/reversed sowing, owner/CSRF | `backend/tests/propagation/test_propagation_batch.py` (8 passed), `backend/tests/integration/propagation/test_propagation_batch_api.py` (4 passed), `backend/scripts/test_check_api_routes.py` (27 passed) |
| Frontend dialog states, live preview, group mode, 409 stale refresh, screen integration | `frontend/src/propagation/PotOnDialog.test.tsx`, `GuidedForms.test.tsx`, `SowingScreen.test.tsx`, `PlantScreen.test.tsx` (4 files, 135 tests passed) |
| Static, contract, docs & scope manifest | `ruff format --check`, `ruff check`, `mypy`, `pnpm typecheck`, `pnpm lint`, `make api-check`, `scripts/check-features.py` (187 valid), `scripts/check-doc-links.py` (370 docs) |

Note on test paths: the two new backend test files live under the existing `propagation` scope
directories (`backend/tests/propagation/test_propagation_batch.py` and
`backend/tests/integration/propagation/test_propagation_batch_api.py`) so
`scripts/verification-impact.json` owns them automatically without modifying `scripts/`.

## Visual review screenshots (not committed; attached in handoff)

Captured in headless Chromium against the built production frontend bundle at desktop (1440×900)
and phone (375×812) widths; verified zero horizontal document or dialog overflow:

- `pot-on-dialog-desktop-form.png` — Sowing pot-on form step at 1440×900 (mode toggle, germinated
  hint, `{n}` pattern with auto padding and first-3 + last preview, searchable identity/location
  pickers)
- `pot-on-dialog-desktop-preview.png` — Sowing pot-on preview step at 1440×900 ("Will create 12
  Plants HOY-24-07-01 … HOY-24-07-12 in Greenhouse → Bench 2; sowing becomes Completed.")
- `pot-on-dialog-desktop-success.png` — Sowing pot-on success step at 1440×900 with clickable links
  to all 12 created Plants and live Descendants refresh behind the modal
- `pot-on-dialog-phone-form.png` — Sowing pot-on form step at 375×812 (stacked single column, zero
  horizontal overflow)
- `pot-on-dialog-phone-preview.png` — Sowing pot-on preview step at 375×812
- `group-split-dialog-desktop.png` — Active PlantGroup "Split into plants" dialog at 1440×900
- `group-split-dialog-phone.png` — Active PlantGroup "Split into plants" dialog at 375×812
