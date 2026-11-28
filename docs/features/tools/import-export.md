# Guided CSV import and operator export

> Summary: Guided CSV/XLSX import wizard, per-type CSV import, operator export (IMPORT-001/002), and
> the full data export ZIP (DATA-EXPORT-001).

Import one file and one record type at a time in **Tools → Import / Export**. The workspace provides a
blank template, a valid example, and a field guide for each type. Fill the template with UTF-8 CSV,
validate, review every row and choice, then confirm.
Suggested order: Botanical identities → Suppliers → Locations → Seed lots → Plants → Plant groups.
Each file applies atomically: a failed apply rolls back the entire file. The preview uses read-only
domain queries and never creates collection records. Apply revalidates against current data and
accepts only the exact previewed bytes, using a session-bound confirmation valid for 15 minutes.
Changes after preview require a fresh validation. No background import or saved draft exists.

**CSV IMPORT != BACKUP/RESTORE. CSV EXPORT != COMPLETE BACKUP. CSV IMPORT != FULL-FIDELITY
TRANSFER.** Use the coordinated database and
attachment backup/restore process for recovery. These formats do not carry photos, Events, operation
receipts, provider data, user/session data, or all lineage. Exported collection rows include their
UUID in `record_ref` for identification, but import does not update or skip an existing SeedLot,
Plant, or PlantGroup: an existing `record_ref` reports a conflict. Replaying a blank-template
collection CSV without `record_ref` can create duplicate rows. Reconcile source keys against
saved records before retrying a batch.

## CSV conventions and bounds

- All six formats use the blank-template headers; column order may change. Header capitalization and
  surrounding whitespace are normalized. Duplicate, missing, and unknown headers are errors.
  UTF-8 BOM and LF or CRLF are accepted.
  Standard quoted commas and newlines work. Fully blank records are ignored; record numbers count
  CSV records beginning at 2, including blank records. Rows with missing/extra cells are errors.
- The server reads at most **2 MiB** and accepts at most **2,000 nonblank data rows** per file.
  MIME type is advisory. Invalid UTF-8 and malformed quoting are errors. Empty optional cells
  mean unknown, never a zero, present date, default Supplier, or inferred location.
- Normal templates omit `record_ref` entirely. An advanced CSV may add that optional column with an
  existing Florabase UUID for explicit record identification; a human-created key is not a UUID.
  Exports retain `record_ref` for identification. SeedLot, Plant, and PlantGroup imports remain
  create-only; an existing `record_ref` is a conflict, not an update or silent skip.
- References accept an existing UUID or an **exact** human label. Botanical identity labels are
  `scientific_name` or `scientific_name|cultivar_name` (the vertical bar separates the identity
  tuple). Supplier and ProvenanceSite references use an exact name. Location and GeographicPlace
  references use the full current displayed path; the path is looked up as a whole and never split
  or used to create hierarchy. Zero matches are unresolved; multiple matches are ambiguous. Names
  are not fuzzy matched. Preview offers actual candidate choices when exact labels repeat. An
  existing UUID remains an optional advanced fallback. Supplier is an acquisition party;
  GeographicPlace is a geographic hierarchy node; ProvenanceSite is a precise origin; Location is
  the physical collection place. They are never substituted for one another.
- Dates are `YYYY` (year), `YYYY-MM` (month), or `YYYY-MM-DD` (day). Partial precision is stored
  unchanged. Empty date is unknown. The calendar validates complete dates.
- Controlled values such as Supplier kind, source kind, lifecycle, quantity kind/unit/certainty and
  Location scopes ignore surrounding spaces and capitalization. Preview shows the canonical value
  when normalization occurs. No semantic synonyms are guessed: `Nursery` becomes `nursery`, but
  `garden center` is invalid. Names, labels, notes, and accents are not lowercased.
- When a row matches an existing record, Preview requires an explicit action. **Use existing**
  leaves it unchanged. **Update existing** is available only for a current Supplier and shows each
  effective field change. Blank Supplier CSV cells retain existing values; no clearing syntax is
  defined. **Create separate** is available for Supplier and Location where the domain permits
  duplicates, but never for the same BotanicalIdentity name/cultivar tuple. Botanical identities
  allow Use existing only; collection records are create-only. The file, choices, and candidate
  state are bound to a 15-minute session confirmation. A changed candidate requires a new Preview.
- Text on export that could begin a spreadsheet formula after leading whitespace (`=`, `+`, `-`,
  `@`) receives a leading apostrophe. This protects spreadsheet opening while keeping the visible
  text as faithful as practical. The protection is part of the exported cell; do not treat exports
  as lossless re-import packages. Numeric, date, UUID, enum, and quantity cells are not altered.
- Blank templates contain only exact headers. Downloadable examples use those same headers and are
  validated through the ordinary parser and Preview in the documented import order. Quote fields
  with commas or newlines normally.

## Botanical identities

| Column            | Requirement and accepted value                       | Example              |
| ----------------- | ---------------------------------------------------- | -------------------- |
| `scientific_name` | Required normalized taxon name, up to 255 characters | `Phaseolus vulgaris` |
| `cultivar_name`   | Optional unquoted cultivar, up to 120 characters     | `Borlotto`           |
| `common_name`     | Optional common name, up to 160 characters           | `Bean`               |

The scientific name **plus cultivar** is the case-insensitive domain identity. An exact existing
tuple is shown directly in Preview. Use existing leaves any differing common name unchanged and
shows that difference. A separate duplicate is prohibited. No taxonomy merge or correction occurs.

## Suppliers

| Column    | Requirement and accepted value                                              | Example               |
| --------- | --------------------------------------------------------------------------- | --------------------- |
| `name`    | Required name, up to 255 characters; names are not unique                   | `ABC Seeds`           |
| `kind`    | Required: `seller`, `nursery`, `supermarket`, `person`, `exchange`, `other` | `seller`              |
| `website` | Optional HTTP(S) URL, up to 2048 characters                                 | `https://example.org` |
| `email`   | Optional email, up to 320 characters                                        | `seeds@example.org`   |
| `phone`   | Optional contact number, up to 120 characters                               | empty                 |
| `notes`   | Optional text, up to 20,000 characters; quoted newlines accepted            | empty                 |

An exact existing Supplier name opens human-readable candidate choices with kind, contact details,
and current/retired status. Use existing keeps all current values. Update existing uses the normal
Supplier update service and shows a field-level diff; blank cells keep current values. Create
separate makes another Supplier where the existing domain permits it. With several exact matches,
the operator chooses the intended candidate; no first-match rule applies.

## Locations

| Column         | Requirement and accepted value                                                           | Example             |
| -------------- | ---------------------------------------------------------------------------------------- | ------------------- |
| `import_key`   | Optional unique key within this file; required if another row uses it as parent          | `cabinet`           |
| `name`         | Required physical Location name, up to 255 characters                                    | `Seed cabinet`      |
| `parent_ref`   | Optional existing Location UUID/full exact path or `@import_key` in this file            | `@cabinet`          |
| `usage_scopes` | Required: `plants`, `sowings`, `seed_lots`, or `harvest_inventory`, separated by a vertical bar; at least one | `seed_lots\|plants` |

A child may precede its parent in the file. Preview detects missing or duplicate parent keys,
cycles, and invalid scopes. Scopes do not inherit from parents. For example, a `cabinet` row can
have an empty parent; a `drawer3` row can use `@cabinet`. Existing Location names need not be unique;
an exact full path resolves one; repeated paths require a Preview choice. For a root or an existing
parent, an exact same-name child offers Use existing or Create separate. UUID is an advanced fallback.

Use `harvest_inventory` for stored harvested material. The in-app field guide
and Location CSV export currently omit this scope. Verify it in Location details
after Apply.

## Seed lots

| Column                     | Requirement and accepted value                                                                                                    | Example                        |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| `identity_ref`             | Required existing BotanicalIdentity UUID or exact tuple label                                                                     | `Phaseolus vulgaris\|Borlotto` |
| `label`                    | Optional packet/lot label, up to 255 characters                                                                                   | `INCREASE P12`                 |
| `source_kind`              | `purchased`, `purchased_fruit`, `self_collected`, `collection_produced`, `gift_exchange`, `other`, `unknown`; empty means unknown | `gift_exchange`                |
| `source_detail`            | Optional up to 255 characters, only with `other`                                                                                  | empty                          |
| `producer_plant_ref`       | Optional existing Plant UUID, only for `collection_produced`; mutually exclusive with group producer                              | empty                          |
| `producer_plant_group_ref` | Optional existing PlantGroup UUID, only for `collection_produced`                                                                 | empty                          |
| `supplier_ref`             | Optional Supplier UUID or exact name; repeated names require a Preview choice                                                     | `ABC Seeds`                    |
| `geographic_place_ref`     | Optional GeographicPlace UUID or exact full path                                                                                  | empty                          |
| `provenance_site_ref`      | Optional ProvenanceSite UUID or exact unique name                                                                                 | empty                          |
| `acquisition_date`         | Optional partial date                                                                                                             | `2024-05`                      |
| `harvest_date`             | Optional partial date                                                                                                             | empty                          |
| `quantity_kind`            | `seed_count` or `weight` when quantity known; otherwise empty                                                                     | `seed_count`                   |
| `quantity_value`           | Nonnegative whole count or decimal weight; empty for unknown                                                                      | `120`                          |
| `quantity_unit`            | `g` or `mg` for weight; empty for count/unknown                                                                                   | empty                          |
| `quantity_certainty`       | `exact`, `approximate`, or `unknown`/empty with no value                                                                          | `approximate`                  |
| `expected_viability_until` | Optional partial date                                                                                                             | `2027`                         |
| `location_ref`             | Optional Location UUID or full exact path with `seed_lots` scope                                                                  | empty                          |
| `lifecycle`                | `active`, `exhausted`, `discarded`, `lost`; empty means active                                                                    | `active`                       |
| `notes`                    | Optional text up to 20,000 characters                                                                                             | empty                          |

Exact zero is valid only for exhausted lots. Quantity and dates retain their precision/certainty.
Collection-produced producers must already exist and pass current lineage checks. Sowing import is
excluded because the current Sowing and propagation operations have distinct accounting and
receipt semantics; no historical operation receipt is fabricated here.

## Plants and Plant groups

Both formats admit **direct-origin** legacy records only. No originating Sowing, extracted
PlantGroup lineage, propagation accounting, or operation receipts are imported. The existing create
services enforce normal domain validation. A Plant represents one individual and has no quantity.
A PlantGroup is a managed group and may have exact, approximate, or unknown count.

| Column                  | Requirement and accepted value                                                                                  | Example              |
| ----------------------- | --------------------------------------------------------------------------------------------------------------- | -------------------- |
| `identity_ref`          | Required existing BotanicalIdentity UUID or exact tuple label                                                   | `Phaseolus vulgaris` |
| `label`                 | Optional record label, up to 255 characters                                                                     | `South bed`          |
| `direct_origin_kind`    | `purchased`, `gift_exchange`, `collection_produced`, `other`, `unknown`; empty means unknown                    | `unknown`            |
| `direct_origin_detail`  | Optional up to 255 characters, only with `other`                                                                | empty                |
| `supplier_ref`          | Optional Supplier UUID or exact name; repeated names require a Preview choice                                   | empty                |
| `geographic_place_ref`  | Optional GeographicPlace UUID or exact full path                                                                | empty                |
| `provenance_site_ref`   | Optional ProvenanceSite UUID or exact unique name                                                               | empty                |
| `collection_entry_date` | Optional partial date                                                                                           | `2023`               |
| `location_ref`          | Optional Location UUID or exact full path with `plants` scope                                                   | empty                |
| `quantity_value`        | PlantGroup only: nonnegative whole count, empty for unknown                                                     | `8`                  |
| `quantity_certainty`    | PlantGroup only: `exact`, `approximate`, or `unknown`/empty                                                     | `approximate`        |
| `lifecycle`             | Plant: `active`, `transferred`, `dead`, `lost`, `discarded`. Group additionally `completed`; empty means active | `active`             |
| `notes`                 | Optional text up to 20,000 characters                                                                           | empty                |

`reversed` and Plant `reintegrated` lifecycle values are assigned only by their owning operations.
PlantGroup exact zero follows the current lifecycle rule. A `source_kind` or `direct_origin_kind`
of `collection_produced` states the known direct origin kind; it does not invent parent lineage.

## Downloadable examples

The workspace provides one valid example CSV for every supported type. These files are generated
from the same column list as the blank template and are exercised by the import Preview in tests.
Import them in this order when using an empty collection:

1. Botanical identities: `Acmella oleracea` with common name `Paracress`, and `Allium fistulosum`.
2. Suppliers: Unicode name `Cercatoridisemì`, canonical kind `nursery`.
3. Locations: `Seed cabinet`, then `Drawer 3` using the local `@cabinet` parent key.
4. Seed lots: a month-precision, approximate Paracress count using exact human-readable identity,
   Supplier, and Location references; a second lot with unknown quantity.
5. Plants: one direct-origin Paracress specimen with a year-precision entry date.
6. Plant groups: a direct-origin clump with a month-precision entry date and approximate count.

The example records are illustrative collection data. Download a **blank template** for your own
records; do not import examples into a live collection unless you want those sample records.

## Preview outcomes and export

Every Preview row shows its CSV record number, label, resolved references, canonicalized values,
and issues. Ready rows create records. Rows with exact existing candidates ask for a deliberate
action; ambiguous relationship references show actual candidates to choose. Use existing leaves a
record unchanged, Update existing displays its exact Supplier changes, and Create separate creates
a new permitted record. Unresolved references, invalid rows, and conflicts block the **whole** file;
correct the CSV and validate again. Apply never partially imports valid rows from a file with errors.
A concurrent edit invalidates the signed choice and requires a new Preview.

Export routes require authentication and return deterministic UUID-sorted, UTF-8 CSV with a BOM for
spreadsheet compatibility. Separate files preserve partial dates, quantity certainty, lifecycle,
UUID relationships, and record type. Export adds `parent_path` for Locations, plus readable
`identity_label`, `supplier_name`, `geographic_place_path`, `provenance_site_name`, and
`location_path` companion columns for collection records. SeedLot export also adds producer labels.
The companion columns are export-only presentation; UUIDs remain authoritative and the export
headers are intentionally different from import templates. Export does not include attachment
binaries or secret material.

For source mapping, batch reconciliation and the manual workflows needed for
first collection entry, see the [onboarding runbook](../../archive/BETA-DATA-001/beta-data-001.md).

## Full data export (DATA-EXPORT-001)

**Export all data** in Tools → Import / Export (above the per-type exports) downloads
`florabase-export-<UTC time>.zip` from `GET /api/v1/exports/full.zip`, with the same authentication
as the per-type CSV export. It is an exit and portability guarantee: **it is not a backup and cannot
be imported back** (re-import is the planned `TRANSFER-001`; recovery uses
[backup and restore](../../operate/backup-restore.md)).

- One CSV per exported table (UTF-8 with BOM, RFC 4180, CRLF, header always present) plus
  `lineage_edges.csv` (every recorded parent → child source relationship, from the lineage
  module's own edge query), `README.txt` and `manifest.json` (format version, Florabase version,
  Alembic revision, UTC export time, include-files flag, and rows, bytes and SHA-256 per file).
- `backend/src/florabase/data_export/registry.py` is the single list of exported tables (`TABLES`)
  and excluded tables (`EXCLUDED`, each with a reason). Contract tests fail when a model or
  database table is in neither list, and when an exported table gains a column that is not in
  `backend/tests/fixtures/data_export/reviewed_columns.json` or `dropped` with a reason. **A new
  table or column must be classified there in the same change.**
- Excluded: users, web and device sessions, login throttles, undo receipts, provider caches and
  native-range provider evidence. Account ids become `*_display_name`; external links keep provider
  ids only. Geographic places are limited to the ones the collection references and their ancestors.
- Columns follow the database: ids are UUIDs, a `<column>_label` follows a reference to an
  identity, location, supplier or collection record, a partial date becomes `<name>` (ISO
  `YYYY`, `YYYY-MM` or `YYYY-MM-DD`) plus `<name>_precision`, timestamps are UTC ISO 8601 and
  booleans `true`/`false`. Free text uses the same formula-injection protection as the CSV export.
- Rows are ordered by `(created_at, id)` (or primary key) and ZIP entries carry a fixed
  timestamp, so two exports of unchanged data differ only in `manifest.json`.
- **Include photos and files** (off by default) adds `files/<attachment uuid>.<ext>`;
  `attachments.csv` maps each attachment to its `file_path`. A file missing on disk is skipped and
  counted in the manifest. `GET /api/v1/exports/full/summary` gives the record count and the photo
  size the card shows as an estimate.
- The ZIP streams from one read-only `REPEATABLE READ` snapshot with zip64 entries, so memory stays
  bounded on the server. The web app still assembles the download in browser memory before saving,
  like other protected downloads.
- In the public demo (`DEMO-001`) the export works but never includes files.

## Spreadsheet wizard (single-sheet CSV and XLSX)

In addition to the six per-type CSV workflows above (which remain unchanged as the canonical
round-trip import contract), Florabase provides a single-sheet spreadsheet import wizard for
creating one collection record type per sheet (**Plants**, **Plant groups**, or **Seed lots**):

- **Endpoints**: `POST /api/v1/sheet-imports/inspect`, `POST /api/v1/sheet-imports/preview`, and
  `POST /api/v1/sheet-imports/apply` (distinct from `/api/v1/imports/{kind}/*`). All three require
  owner authentication; apply also requires CSRF protection and the `X-Import-Confirmation` header.
- **Bounds and safety**: uploads are capped at **2 MiB**, **2,000 nonblank data rows**, **60
  columns**, and **one sheet** per import. Header row selection defaults to the first nonblank row
  and may be adjusted within rows 1–10. Before opening `.xlsx` files with `openpyxl`
  (`read_only=True`, `data_only=True`), the server rejects archives whose uncompressed member sizes
  exceed **30 MiB**, whose member compression ratio exceeds **100:1**, or whose XML members contain
  `<!DOCTYPE` or `<!ENTITY` declarations. Formulas are never evaluated: cached values are read as
  stored, and formula cells without a cached value are reported invalid if mapped and ignored if
  unmapped.
- **Types and dates**: real Excel date cells normalize to day-precision `YYYY-MM-DD`; integer-valued
  numbers normalize to whole-number strings; text dates such as `2023` or `2023-05` preserve their
  partial precision.
- **Mapping and grouped review**: EN and IT header synonyms suggest column mappings for the chosen
  record type (for example `Species`/`Nome scientifico`, `Location`/`Posizione`,
  `Supplier`/`Fornitore`, `Bought`/`Data acquisto`, `Quantity`/`Quantità`, `Notes`/`Note`);
  `quantity_value` is not suggested for individual Plants. Unmapped columns may optionally be
  appended to `notes` as `Column: value` lines. New botanical identities, locations (never
  auto-split on `/` or `→`), and suppliers (default kind `other`) are reviewed once per distinct
  value rather than per row, with exact matches, near-match suggestions, or explicit **skip**
  (which visibly records that the location or supplier will be left empty).
- **Atomic apply**: confirmation tokens bind the session, file bytes, and options for 15 minutes
  via HMAC-SHA256. Apply creates missing identities, suppliers, and locations first, rebuilds
  references from the database to revalidate every row against the confirmed preview, and creates
  all collection records in a single transaction—rolling back everything on any error or state
  change. Collection records remain create-only; no events, photos, lineage, or server-side drafts
  are created.
- **Sheet choice**: without an explicit choice the first sheet that has data opens, so a leading
  cover or instructions sheet does not block the upload; the wizard then offers every sheet.

### Using the wizard

Settings → Import / Export → **Import a spreadsheet** opens six steps; the per-type CSV import stays
below it, marked **Advanced**.

1. **Upload** a `.csv` or `.xlsx` file; pick the sheet and the header row when needed.
2. **Row type**: Plant, Plant group or Seed lot.
3. **Columns**: each column shows sample values and a Florabase field (or Ignore). Scientific name is
   required and a field can be used once. The last mapping for the same headers and row type is
   remembered in this browser only.
4. **Names and places**: species, locations and suppliers are listed once per distinct value. New
   scientific names can be edited (with local WFO suggestions when that index is installed);
   locations and suppliers can use an existing record, be created (a new location under a chosen
   parent, a new supplier with a kind) or be left empty.
5. **Rows**: counts of ready rows and rows needing attention, with an "Only problems" filter and the
   per-row messages of the shared preview vocabulary. Import stays disabled until every row is ready.
6. **Import** creates everything in one transaction and lists the created records with links. If the
   collection changed since the preview, nothing is created and the wizard returns to step 4.
