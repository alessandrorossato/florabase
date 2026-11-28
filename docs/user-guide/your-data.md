# Your data: CSV import and export

Your collection records belong to you. Florabase includes guided **CSV export and import** for
working with spreadsheets or onboarding existing lists of species, suppliers, locations, seed lots,
plants, and plant groups.

## 1. Export collection records to CSV

You can download a UTF-8 `.csv` spreadsheet for any of the six supported record types:

1. In the left rail, open **Settings** → **Import / Export** (on a phone, tap **Account and
   settings** at the top right, then **Import / Export**).
2. In **Record type**, choose what you want to export:
   - `Botanical identities`
   - `Suppliers`
   - `Locations`
   - `Seed lots`
   - `Plants`
   - `Plant groups`
3. Under **Export CSV**, click **Download CSV**.

Your browser downloads the `.csv` file immediately, containing every record of that type in your
collection.

### Export all your data at once

**Export all data**, at the top of the same screen, downloads one ZIP with every record of your
collection: one CSV file per record type, a `README.txt` explaining the columns, and a
`manifest.json`. Tick **Include photos and files** to add your photos in a `files/` folder; the
card shows about how big that download will be. The CSV files open in any spreadsheet and stay
readable without Florabase. **This is not a backup**: it cannot be imported back (see section 3).

## 2. Validate and preview a CSV import

Florabase never writes an uploaded CSV file blindly to your collection. Every import starts with a
read-only **Validate and preview** step so you can inspect every row, resolve any duplicate or
missing-reference questions, and cancel safely if anything looks wrong.

### Recommended import order

Because collection records refer to identities, suppliers, and locations, import files in this order
when bringing in a new collection:

`Identities` → `Suppliers` → `Locations` → `Seed lots` → `Plants` → `Plant groups`

### Run an import preview (and optionally confirm)

1. Open **Settings** → **Import / Export**.
2. In **Record type**, select the type of record you want to test or import (for example,
   `Botanical identities`, `Suppliers`, or `Seed lots`).
3. Under **Import CSV**, you can download a starting file at any time:
   - Click **Blank template** to download an empty CSV with the exact required and optional column
     headers.
   - Click **Example CSV** to download a sample CSV with realistic example rows (great for testing
     the import preview on a fresh database).
   - Click **Field guide** to open a summary of every column, which columns are required, and how
     partial dates (`2024`, `2024-03`, `2024-03-15`) and quantities are formatted.
4. Click **CSV file** and select a `.csv` file from your computer (such as the **Example CSV** you
   just downloaded, or your own edited spreadsheet).
5. Click **Validate and preview**.
6. Inspect the `Preview:` panel below (showing the uploaded file name): <!-- TODO(DOC-04 verify): ImportExportScreen builds the preview heading dynamically as `Preview: ${preview.filename}` (`frontend/src/import-export/ImportExportScreen.tsx:664`). -->
   - The summary counters show how many rows are **Ready** and how many **Needs attention** (you can
     filter the table by clicking **All**, **Ready**, or **Needs attention**).
   - If a row matches an existing record or has an ambiguous reference, Florabase explains the issue
     on that row and lets you pick what to do (such as **Use existing**, **Update existing**,
     **Create separate**, or **Choose this record**).
7. When you finish inspecting the preview:
   - Click **Confirm import** to create (or update) the records once all rows are ready.
   - Or click **Cancel preview** to close the preview without changing a single record in your
     database.

<!-- TODO(DOC-04 screenshot): Settings Import / Export screen showing Download CSV, Blank template, Example CSV, Validate and preview, and the Preview table with Ready rows and Confirm import / Cancel preview buttons -->

## 3. Backups, restores, and upgrades

> **Important:** CSV export and the **Export all data** ZIP are designed for spreadsheets, record
> onboarding and taking your data elsewhere. They are **not** a system backup: neither can be
> restored or imported back, and the per-type CSV files do not contain photos, history or every
> record type.

Full backups (which pair the database and your uploaded media directory together), restores, and
version upgrades are run by the instance operator on the host machine. For step-by-step instructions,
see the [Installation and operations guide](../operate/installation.md).

Next, continue to **[Optional reference data](reference-data.md)** to see what optional external
botanical datasets add to Florabase and what works without them.
