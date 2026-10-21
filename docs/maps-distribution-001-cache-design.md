# Occurrence evidence reuse — architecture audit and implementation decision

2026-10-21, before cache implementation, same MAPS-DISTRIBUTION-001 candidate.

Current aggregate counts and every tile are live GBIF reads. ExternalProviderCache is an
existing PostgreSQL JSONB cache for taxon responses, with atomic upsert and fetched_at;
it can hold small versioned aggregate evidence without a new domain table or migration.
The occurrence raster proxy already restricts coordinates, provider URL, PNG type and size.
Attachment storage is a durable per-environment Docker volume. Its backup tool archives
only `objects/`, so a separate cache directory in that volume survives restart but is not
part of the authoritative media archive. Reusable cache files are disposable, not attachments.

## Diagnosis

Candidate backend logs show real GBIF 503 responses for `z=2,y=0,x=1/2`, successful other
tiles, and HTTP 204 for empty tiles such as `2/0/0` and `2/3/0`. Returning 204 directly to
Leaflet's IMG layer triggers image decode failure. The previous UI also latched any error
forever and rebuilt both layers/viewport on retry. No authentication failure is evidenced
in these observed requests. Never reinterpret a 503 as an empty tile.

## Selected design

- Small summary snapshots reuse ExternalProviderCache, keyed by exact provider/taxon plus
  the fixed checklist, filters, renderer/style/bin/resolution and version contract hash.
  A new generation UUID is published only after both counts succeed. Failed refresh keeps
  the old summary/generation and reports the provider error. At most 256 occurrence entries.
- Validated PNG/empty-tile entries live under `attachment_storage_root/occurrence-cache-v1`.
  Flat server-derived names, flock serialization, bounded reads, atomic replace, 64 MiB per
  taxon contract / 512 MiB overall, 4096 files maximum and 90-day inactivity retention.
  Eviction removes oldest access first. Quotas count committed entries; one bounded temporary
  tile can exist during atomic replacement. No raw occurrence dataset or new application schema.
- New authenticated cache GET performs local reads only; owner/CSRF POST explicitly loads
  or refreshes; owner/CSRF DELETE clears that exact taxon cache. Raster requests name the
  generation and explicitly choose cache-only or provider-enabled mode. No fallback to
  network on a cache-only miss. Link changes segregate the cache by exact taxon/contract.
- Summary and tiles share a generation, but tiles are fetched only for viewed areas after
  explicit Load/Refresh. A generation is a progressive visualization cache, not a GBIF
  transactional dataset snapshot. Missing/evicted/failed areas remain explicitly incomplete.
- GBIF 204 renders as a transparent successful tile. Overlay fetches use bounded retries
  (two retries, increasing delay), cancellation and current-visible failure tracking. Retry
  targets failed visible tiles and preserves successful tiles and the viewport.
- A local Natural Earth contextual basemap reuses the already bundled public-domain asset,
  converting its documented equirectangular vertices to latitude/longitude for Leaflet's
  existing projection. No native assertions or provider requests. Optional configured online
  basemap requires its own explicit action, with separate error tracking and privacy note.
  Direct OSM tiles are never archived or automatically requested during cache playback.

## Rights and HTTP policy audit

Primary references: [GBIF Maps API](https://techdocs.gbif.org/en/openapi/v2/maps),
[official map use and citation guidance](https://data-blog.gbif.org/post/2023-03-24-maps-api/),
[GBIF data-user agreement](https://www.gbif.org/terms/data-user),
[GBIF citation training](https://docs.gbif.org/course-introduction-to-gbif/en/data-publisher-visibility-and-recognition.html).
The direct agreement page returned 403 to the documentation reader; official training
reproduces its publisher-attribution and licence obligations. No source found imposes a
specific prohibition on private raster reuse. A single actual successful occurrence tile
returned `Cache-Control: public, max-age=1200`, PNG, 14610 bytes. This is positive HTTP
cache permission, not a new blanket licence for underlying publisher records. Retain the
provider/publisher attribution, licence link, exact filters and obtained timestamp. Treat
no-store/no-cache/must-revalidate responses conservatively as unavailable for offline reuse.
Old locally held evidence is visibly dated, never silently revalidated. No wholesale tile
pyramid prefetch, redistribution package or raw-record extraction is introduced.

## Separate future raw-record capability

Individual records would need the official asynchronous GBIF download request/status/
retrieval flow, a bounded selected-taxon/filter scope, storage/import limits, dataset keys,
licences and downloadable citation/DOI retention. DWCA includes rights.txt, citations.txt,
metadata and interpreted/verbatim records; Simple CSV/Parquet have different content/cost.
See [official download formats](https://techdocs.gbif.org/en/data-use/download-formats).
That is a distinct ingestion and provenance project, outside this visualization cache.
