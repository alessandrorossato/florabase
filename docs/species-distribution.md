# Species distribution (EXPLORE-001)

Explore occurrence-density evidence for BotanicalIdentities represented in the collection.
Occurrences describe observed presence; they do not establish native range. Collection origins
(`#/map`) describes recorded provenance of actual material.
[EXPLORE-002 Native ranges](native-ranges-explore.md) is the separate structured botanical-reference
workspace; the shared representation scopes do not mix its evidence with occurrences.

## Representation contract

An identity is represented only through exact stored collection relationships. No name matching,
provider inference, recursive ancestry, or reference-only identities contribute.

| Collection record | Authoritative identity | State | Living | Current | Retained evidence |
| --- | --- | --- | --- | --- | --- |
| SeedLot | `botanical_identity_id` | active | No | Yes, including unknown quantity | Yes |
| SeedLot | same | exhausted, discarded, lost, reversed | No | No | Yes |
| Sowing | `seed_lot_id` → SeedLot identity | active | No | Yes | Yes |
| Sowing | same | completed, failed, abandoned, reversed | No | No | Yes |
| Plant | `botanical_identity_id` | active | Yes | Yes | Yes |
| Plant | same | dead, lost, discarded, transferred, reintegrated, reversed | No | No | Yes |
| PlantGroup | `botanical_identity_id` | active | Yes | Yes | Yes |
| PlantGroup | same | completed, dead, lost, discarded, transferred, reversed | No | No | Yes |
| Managed stored material | inventory → Harvest → exact source Plant/PlantGroup identity | active | No | Yes, including unknown remainder | Yes |
| Managed stored material | same | depleted | No | No | Yes |
| Harvest without managed inventory | exact source Plant/PlantGroup identity | retained | No additional Living | No additional Current | Already represented through retained source |

Current inventory uses HARVEST-002's explicit `active` state: known remainders are constrained
positive and unknown remainder does not mean depleted. Harvest collected quantity alone never proves
current stock. Collection-produced SeedLots use their own identity, not their producer's identity.
Reversal/reintegration retains evidence; it never makes the retained result current.

All represented is the union of Current and Historical. Living is a subset of Current. Historical
means retained evidence with **no** Current representation anywhere in these domains. One row per
identity, even with multiple lots, descendants or both living and historical records. Row counts
count records, not individuals, quantities or independently acquired species.

## Local discovery and map boundary

Authenticated GET `/api/v1/explore/species-distribution/identities` accepts `q` (200 characters),
`scope=all|living|current|historical`, `offset` (0–100000) and `limit` (1–100, default 50).
Literal case-insensitive substring search covers scientific name, cultivar, common name and the
normal display label; `%` and `_` are literal. Ordering is lowercased scientific name, cultivar
(null first), UUID. Totals and occurrence-ready counts describe the filtered result, not the page.
Grouped UNION ALL projections aggregate collection records before identity joins. Two SELECTs serve
count and page, independent of page size. A selected identity has a separate single-SELECT local
read at `/identities/{uuid}?scope=...`; it checks representation independent of search/pagination.

Occurrence-ready means a confirmed GBIF link exists locally, **not** that eligible occurrences exist.
MAP-002 admits the exact stored opaque ID without checking cached rank/status or refresh age;
EXPLORE-001 preserves that rule. Missing link and unsupported-provider-only link are distinct local
states. Remote removal/network failure is only known after explicit Load.

The occurrence workspace shows one exact linked identity. Opening, searching, filtering, selecting,
reloading and opening a Saved View perform authenticated **local cache reads only**. Available saved
summary and tiles appear automatically; a miss offers explicit Load from GBIF. Explicit Load/Refresh
fetches the two aggregate counts, publishes a new snapshot generation after both succeed, then permits
viewed raster tiles to be downloaded for that generation. Returning to the page resets permission to
contact GBIF, while restoring available local evidence. No background refresh or tile-pyramid prefetch.

Zero eligible records means no records meet the coordinate/quality policy, never species absence.
Only MAP-002's exact opaque provider taxon identifier, fixed checklist/status/quality filters and tile
coordinates leave the backend. No collection metadata, notes, account identity or physical location
is forwarded. The bundled Natural Earth geographic context needs no external request; the optional
configured online basemap requires a separate explicit choice and exposes IP/visible tile area to
its provider. Occurrence evidence does not infer native range or collection provenance.

## URL and Saved Views

`#/species-distribution?q=ocimum&scope=living&identity=<uuid>` stores stable local state only.
Defaults are omitted, invalid manual scope/UUID values fall back safely, and UUIDs are normalized.
Saved Views use `species_distribution`, v1: `scope`, `q`, `identity`. They exclude provider responses,
loaded state, map instance/zoom, errors, offset, scroll and other transient state. Opening restores
page one and local evidence only, including reopening the same state. No view grants permission
to contact GBIF or stores provider results in its JSON. Back/Forward restores ordinary
workspace state. Selection remains explicit when search text excludes it; changing collection scope
shows a mismatch explanation when appropriate, without substituting another identity. Missing or
no-longer-represented selected identities retain their UUID and allow clearing and view management.

Migration `20261008_0037` only extends the SavedView surface constraint. Downgrade locks writers and
refuses while Species distribution views exist, preserving all views; compatible downgrade/re-upgrade
preserves other surfaces.


## MAPS-DISTRIBUTION-001 presentation

The workspace reuses the delivered Native ranges presentation language: Collection PageHeader
search/actions, Filters, compact Saved Views, a bounded TaskDialog chooser and the mounted
MapWorkspace map/inspector switch. The desktop map receives about 70% of the available width;
at tablet/mobile sizes the operator switches panes without unloading the evidence or replacing
Leaflet. A ResizeObserver resizes the revealed canvas without changing its viewport.

The chooser selects **one** identity. Scientific/common/cultivar search is the same durable local
query in the header and chooser. Hover/keyboard focus previews eligibility without selecting or
loading; choosing commits the identity and returns focus to the header trigger. Local totals
count matching represented identities and confirmed eligible GBIF links, never occurrences.
Both count actions open the bounded chooser with per-identity eligibility; they do not claim a
new eligibility filter. Backdrop and Escape dismiss transient search without changing the selected
identity; internal controls do not dismiss. Focus returns to the actual invoking button/KPI.
Search/scope/URL/Saved View changes reset external permission and may restore local evidence.

The inspector provides the selected identity, collection representation, exact linked taxon,
loaded aggregate counts, retrieval time and source. Quality, taxonomy/coordinate uncertainty,
licensing and interpretation share one Data details disclosure. Desktop inspector scrolling is
bounded to the viewport; mobile uses the mounted map/inspector switch. Locally cached summaries
older than one day are marked potentially outdated; this is Florabase policy, not a GBIF expiry guarantee.
Missing or incompatible local links remain separate from provider failure after explicit Load.

For an identity without a supported GBIF taxon link, the unavailable state offers **Link botanical
source**. Its `#/identities/<identity-id>?tab=source` route opens that exact identity's Reference →
Botanical source module on direct load and refresh. The source screen reads Florabase's local link
state; it does not search or contact GBIF unless the operator explicitly searches.

Keep the existing GBIF `purpleYellow-noborder.poly` hex raster and Leaflet. The legend describes
relative recording density; numeric color thresholds and per-cell counts are not in the returned
contract. Bin geography changes with zoom. Blank pixels cannot distinguish missing evidence,
filtered-out records and true absence; failed tiles have an explicit warning and retry. No exact
locations, hover cell facts, native status or multi-species comparison are manufactured from pixels.
Comparable occurrence overlays remain future work requiring comparable provider data and scales.

See [the visual-review handoff](maps-distribution-001-handoff.md) for current checks, responsive
browser evidence, Review ownership and operator acceptance items.

## Durable evidence cache (2026-10-21 refinement)

Aggregate summaries reuse PostgreSQL ExternalProviderCache in a separate occurrence-v1 namespace,
limited to 256 snapshots. Keys include exact taxon, CoL XR checklist, quality filters, projection,
hex renderer/style and version. PNG/204 entries use the same contract plus snapshot generation and
z/x/y under `attachment_storage_root/occurrence-cache-v1`, in the existing durable Docker volume.
The cache holds at most 512 MiB overall, 64 MiB per taxon contract and 4096 files; writes evict entries
inactive for 90 days and then least recently accessed entries to satisfy quotas. Atomic file replace,
validated PNG dimensions/content/size, safe paths and interprocess locking bound the storage. Equal
in-flight tile requests are deduplicated per process, with at most four active upstream tile calls.

Authenticated GET `/{identity}/occurrence-map/cache` reads locally; owner/CSRF POST refreshes;
owner/CSRF DELETE clears the exact linked taxon's cache (also used by other identities with that
same link). The API prefix is `/api/v1/botanical-identities`. Tile GET adds `generation` and
`local_only`; cache-only misses return 404 and obsolete generations return 409, with no GBIF fallback.
Legacy explicit summary/tile routes remain supported. Browser transport uses no-store for tiles so
server generation/link checks remain authoritative. OpenAPI and TypeScript declarations are updated;
no schema migration, new dependency or raw occurrence table is introduced.

Failed refresh keeps the last successful summary/generation and cached tiles readable. Successful
refresh creates a new generation, preserving the map viewport while replacing overlay data; old
and new generations are never silently mixed. This is a progressive visualization snapshot, not a
transactionally frozen GBIF dataset: counts and viewed tiles are obtained separately. A link change
selects another exact contract. Only downloaded, retained areas/zooms are available offline. Eviction,
missing tiles and provider failures retain honest incomplete-coverage warnings and readable counts.

GBIF 204 is a transparent successful tile. Transient 502/503/504 and network errors get at most two
retries with bounded backoff; auth, rate-limit, cache-miss and generation-conflict responses are not
automatically retried. Explicit retry targets failed/missing visible tiles, preserving successful
ones and viewport. Unloaded/aborted tiles leave no warning. Optional online basemap failures are
tracked and retried separately.

Upstream no-store/no-cache/must-revalidate responses are conservatively excluded from persistence.
Attribution and publisher licence obligations remain visible; cache age never claims scientific
currency. Summaries are in ordinary DB backups. The standard media archive contains `objects/`
only, so raster cache files survive restart but are excluded from that archive. Operators needing
restored offline raster evidence must preserve the cache directory with the matching DB backup;
otherwise missing tiles remain explicit until a requested refresh. Raw records and bulk downloads
remain a separate decision. See [the audit and storage/licensing design](maps-distribution-001-cache-design.md).
