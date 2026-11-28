# DATA-EXPORT-001 design: full collection data export

> Summary: one authenticated download, `GET /api/v1/exports/full.zip`, streams a ZIP with one
> CSV per exported table, `manifest.json` and `README.txt`, optionally with photo files. It is an
> exit/portability guarantee, not a backup and not a re-import format (TRANSFER-001). No migration.

## Registry and contract

`backend/src/florabase/data_export/registry.py` holds one `ExportTable` per exported table:
table name, CSV file name, ordering, row filter (only `geographic_places`), dropped columns with a
reason, and label columns. Every other column is exported. Two contract tests over
`Base.metadata`: every table is in `TABLES` or `EXCLUDED` (with a reason), and every column of an
exported table is exported or dropped with a reason. A new table or a new column that nobody
classified therefore fails CI (IDENTIFICATION-001's `identifications` table must register).

**Excluded tables**: `users` (credentials; owner shown only as `display_name` labels),
`auth_sessions` (web and device sessions, token digests), `login_throttles` (security state),
`operation_receipts` (internal undo snapshots), `external_provider_cache` (licensed provider
payloads), `native_range_proposals` / `native_range_applications` (provider evidence payloads; the
applied result is in `botanical_profile_native_ranges`), `native_range_revisions` (internal
concurrency counter).

**Dropped columns**: `attachments.storage_key` (internal path), `media_assets.copy_cleanup_attachment_id`
(internal cleanup), `events.reversed_operation_receipt_id` (points to an excluded receipt; `kind =
reintegration` stays), `saved_views.owner_id` and `botanical_identity_reconciliations.actor_user_id`
(replaced by `*_display_name`), `wfo_links.evidence`, `wcvp_links.taxon/source/identity_snapshot`,
and the copied provider names/classification in `external_taxon_links` (ids, rank, status and
dates stay), as the brief allows provider ids only.

## Files (one CSV per exported table, 36, plus lineage)

`botanical_identities`, `botanical_identity_names`, `botanical_identity_reconciliations`,
`botanical_identity_cover_images`, `botanical_profiles`, `botanical_profile_native_ranges`,
`external_taxon_links`, `wfo_links`, `wcvp_links`, `geographic_places` (only places referenced by
the collection, plus their ancestors), `provenance_sites`, `locations`, `suppliers`, `orders`,
`seed_lots`, `sowings`, `germination_observations`, `plants`, `plant_groups`, `events`,
`event_measurement_corrections`, `vegetative_lots`, `propagation_attempts`,
`rooting_observations`, `harvests`, `harvest_items`, `harvest_material_inventory`,
`harvest_material_dispositions`, `harvest_seed_lot_conversions`, `scheduled_activities`,
`saved_views`, `attachments`, `media_assets`, `record_media_links`, `collection_primary_photos`,
`application_settings`, plus derived `lineage_edges.csv` (`parent_kind, parent_id, child_kind,
child_id`, built from the lineage service's single edge query, so it matches the Lineage views).

Key columns: `id` first, FK columns keep their DB names and hold UUIDs. Every reference to an
identity, location, supplier or collection record (seed lot, sowing, plant, plant group, vegetative
lot, propagation attempt, harvest) is followed by `<column>_label` (for example
`botanical_identity_label`, `location_label`). `attachments.csv` adds `file_path`
(`files/<uuid>.<ext>` when included, else empty). The column contract is pinned in
`backend/tests/fixtures/data_export/reviewed_columns.json`.

Approved by Alessandro 28/11 13:26Z, including the three open points below.

## CSV rules

UTF-8 with BOM, RFC 4180, CRLF, header always present (empty tables give a header-only file).
Partial dates: the `<prefix>_precision/_year/_month/_day` group becomes `<prefix>` (ISO partial
`YYYY`, `YYYY-MM` or `YYYY-MM-DD` via `import_export.service.date_cell`) plus `<prefix>_precision`.
Timestamps ISO 8601 UTC, booleans `true`/`false`, decimals as stored, JSON compact with sorted
keys. Every text cell goes through `import_export.service.safe_cell(..., text_field=True)`.
Rows ordered by `(created_at, id)`, or primary key when a table has no `created_at`.

## Streaming

The endpoint returns a `StreamingResponse`. The generator opens its own session in a read-only
`REPEATABLE READ` transaction (one consistent snapshot of all tables), reads each table with
`yield_per`, and writes into `zipfile.ZipFile` on an unseekable sink that hands out chunks as they
are produced: memory stays bounded by one row batch, entries use zip64, and photos are copied from
`AttachmentStorage.active_path` in 1 MiB chunks. Every entry has a fixed timestamp
(1980-01-01), so two exports of unchanged data differ only in `manifest.json`. A photo missing on
disk is skipped and recorded, not fatal.

## Manifest

`manifest.json`: `format: "florabase-data-export"`, `format_version: 1`, `florabase_version`,
`alembic_revision`, `exported_at` (UTC), `include_files`, `files: [{path, rows, bytes, sha256}]`
for every CSV and `README.txt`, `attachment_files: {included, missing}`.

## Auth, demo, logging

Same dependency as the per-type CSV export (`require_authenticated_actor`). In demo mode
(`demo_readonly`) the export works and `include_files` is forced to false (manifest says so). Logs
record only start/end, row totals and duration, no record content.

## Size estimate and UI

`GET /api/v1/exports/full/summary` returns record count, attachment count and attachment bytes
(sum of `byte_size` for active attachments) and `files_allowed`. The card shows "about X MB with
photos" from that sum (CSV size is negligible next to photos). New `FullExportCard.tsx` above the
per-type exports in Tools → Import / Export: checkbox "Include photos and files" (hidden in demo),
download button with idle/downloading/error states, and "This is not a backup" linking the backup
guide.

## Open points for approval

1. `lineage_edges.csv` reuses the lineage module's private `_CHILD_EDGES` query by import (no edit
   to `lineage/`), so the edge definition stays in one place.
2. The small extra `summary` endpoint for the size estimate.
3. `botanical_identity_reconciliations` (merge/rename history) is exported, not excluded.
