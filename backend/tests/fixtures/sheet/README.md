# Synthetic import samples (IMPORT-002)

Fake data, 1–2 rows per record type. Same content as CSV and XLSX so CSV/XLSX equivalence can be
tested. Copy into `backend/tests/fixtures/sheet/` (keep names).

| File | Row type | What it exercises |
|---|---|---|
| `plants.csv` / `.xlsx` | Plant | cultivar, new supplier, nested location path, day date vs year-only (`2023`), empty supplier |
| `plant-groups.csv` / `.xlsx` | Plant group | quantity + approximate flag (`yes`/`no`), month precision (`2025-03`), shared location with plants |
| `seed-lots.csv` / `.xlsx` | Seed lot | harvest year, seed count, new suppliers |
| `it-edge-cases.xlsx` | Plant | Italian headers, two sheets (data on sheet 2 `Piante`), blank first row (header on row 2), real date cell, text partial date, a formula cell (`=4+4`, written by openpyxl so **no cached value** → must be reported invalid if mapped, ignored if unmapped), an extra unmapped column (`Prezzo`) for "append to notes" |

In the XLSX files ISO day dates are real Excel date cells and quantities are numbers; in the CSVs
everything is text.
