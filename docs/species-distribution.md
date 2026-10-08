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

The existing OccurrenceMapPanel and authenticated MAP-002 summary/tile endpoints are reused, for one
selected identity only. Opening, searching, filtering, selecting, refreshing the page and opening a
Saved View never fetch occurrence summaries/tiles. Explicit Load performs normal MAP-002 requests.
Changing selection/search/scope or reopening a view resets external-load state. Zero eligible records means
no records currently meet MAP-002's coordinate/quality policy, never species absence. Failures leave
the local directory usable and allow retry; attribution, density legend and textual companion stay
with MAP-002. No occurrence data or range geometry is persisted.

Only MAP-002's exact opaque provider taxon identifier, fixed checklist/status/quality filters and
tile coordinates leave the backend. Collection metadata never leaves Florabase. No geolocation,
rematching, native-range inference, density aggregation or occurrence prefetch exists. The separately
configured basemap retains its existing direct-tile privacy model.

## URL and Saved Views

`#/species-distribution?q=ocimum&scope=living&identity=<uuid>` stores stable local state only.
Defaults are omitted, invalid manual scope/UUID values fall back safely, and UUIDs are normalized.
Saved Views use `species_distribution`, v1: `scope`, `q`, `identity`. They exclude provider responses,
loaded state, map instance/zoom, errors, offset, scroll and other transient state. Opening restores
page one and an unloaded map, including reopening the same state. Back/Forward restores ordinary
workspace state. Selection remains explicit when search text excludes it; changing collection scope
shows a mismatch explanation when appropriate, without substituting another identity. Missing or
no-longer-represented selected identities retain their UUID and allow clearing and view management.

Migration `20261008_0037` only extends the SavedView surface constraint. Downgrade locks writers and
refuses while Species distribution views exist, preserving all views; compatible downgrade/re-upgrade
preserves other surfaces.
