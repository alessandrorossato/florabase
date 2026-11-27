# IMPORT-002 — Single-sheet CSV/XLSX import wizard

Branch `feat/import-002-sheet-wizard`: backend pass `220821e` and review fixes `e421fc6` (M1, M2)
and `7dcbfd8` (L1, L2) by `neon`; frontend pass, `main` merge (`b632c5c`) and the first-sheet fix
below by `claude-import-002`. User guide: [import-export.md](../../features/tools/import-export.md#spreadsheet-wizard-single-sheet-csv-and-xlsx).

## Acceptance criteria (`docs/features.json` IMPORT-002)

| # | Criterion | Evidence |
| --- | --- | --- |
| 1 | Bounded CSV/XLSX inspect, preview and apply; IMPORT-001 byte-identical | `backend/tests/test_import_wizard.py` (size, row, column, zip-bomb, ratio, DTD/entity, formula and header-row cases), `backend/tests/integration/test_import_wizard_api.py`; IMPORT-001 suites `test_import_export.py`, `test_import_export_api.py` and `integration/test_import_export_api.py` unchanged and green. |
| 2 | EN/IT suggestions, notes append, grouped review with skip, 15-minute HMAC confirmation | Unit mapping and review tests; integration confirmation-mismatch and "Location added after preview → 409, nothing created" tests; UI: `it-edge-cases.xlsx` sheet `Piante` auto-mapped Italian headers, `Prezzo` appended to notes, the uncached formula reported when mapped (`Column "Prezzo" contains a formula without a cached value`). |
| 3 | Atomic apply with full rollback | Integration rollback test (row k fails → nothing created); UI: Import disabled while any row is not ready; refused apply returns to review (`SheetImportWizard.test.tsx`). |
| 4 | Accessible wizard imports each sample CSV and XLSX end to end with the same records; IMPORT-001 under Advanced | `frontend/src/import-export/SheetImportWizard.test.tsx` (4 tests: full walk, rejected file, mapping validation and memory, refused apply); manual run below. |

## Review notes folded in

- **L1** trailing formula-only rows are scanned up to the scan cap: `test_xlsx_trailing_formula_only_row_detected_and_counted`.
- **L2** formulas indexed by row and formula-only rows counted toward the nonblank limit in pass 2 (same commit `7dcbfd8`).
- **First sheet empty** (found in the UI run): `it-edge-cases.xlsx` opens on an empty `Info` sheet,
  so inspect failed before the sheet picker could appear. Without an explicit sheet the parser now
  opens the first sheet with data; an explicit empty sheet still reports "no data rows"
  (`test_it_edge_cases_xlsx_sheets_header_dates_formula_and_notes`,
  `test_xlsx_default_sheet_reports_first_error_when_no_sheet_has_data`).

## Manual end-to-end run (2026-11-25, per-worktree UAT instance, golden SMOKE data)

Through the wizard UI on `http://localhost:15180`:

- `it-edge-cases.xlsx` → Plants: sheet `Piante`, header row 2 detected, 2 Plants, 2 identities,
  2 locations (one created under `Golden collection → Golden greenhouse bench`) and 1 supplier.
  Stored values: real date cell → day `2024-09-01`, text `2022-06` → month precision, notes
  `Foglia a cuore / Quantità: 1 / Prezzo: 12.5`.
- `plants`, `plant-groups`, `seed-lots`: each `.xlsx` then each `.csv` imported. For every label
  (`HOY-001`, `MAM-001`, `ECH-TRAY-01`, `LIT-TRAY-01`, `BEAN-2024`, `FER-SEED-01`) the two
  resulting records have identical identity, dates and precision, quantity, notes, location and
  supplier; the CSV runs reused the identities, locations and suppliers the XLSX runs created.
- Phone width (375 px): no horizontal page scroll on the mapping, review and rows steps; the
  mapping table stacks one block per column.

Screenshots (desktop and phone) are attached to the delivery report, not committed.

## Checks

- Backend: `ruff format`, `ruff check`, strict `mypy` (396 files); `pytest tests/test_import_wizard.py
  tests/test_import_export.py tests/test_import_export_api.py` (53 passed);
  `./scripts/test-integration.sh backend/tests/integration/test_import_export_api.py
  backend/tests/integration/test_import_wizard_api.py` (20 passed).
- Frontend: Prettier, `tsc -b`, ESLint, Vitest `src/import-export` (8 passed); `make api-check` no drift.
- Canonical FULL (`make feature-verify`) is run by the operator on the frozen tree.

## Limits

- WFO suggestions for new names reuse `WfoNameInput` as-is; they appear only where the local WFO
  index is installed (not in the UAT instance used here).
- Re-importing the same sheet creates the records again: the wizard is create-only by design.
