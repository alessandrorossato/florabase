# Dashboard collection search

The authenticated Dashboard is Florabase's global search entry point. Its normal view keeps the
collection snapshot, Quick actions, and recent Events. Query text or any structured filter replaces
that content with grouped results. The URL stores the query and filters under `#/dashboard?...`;
refresh and browser history restore them. Existing directory searches remain available.

`GET /api/v1/search` returns an atomic typed response: the trimmed `query`, `total`, `offset`,
`limit`, and groups with `kind`, `total`, and bounded `items`. Each item has its kind, stable ID,
human label, concise context, and an existing application route. An unauthenticated request is
rejected. A blank query without filters returns no results. A filter alone is valid. Search text is
case-insensitive literal substring matching; `%` and `_` are treated as text. Results within each
kind sort by case-insensitive title and stable ID. This is deterministic text search, with no fuzzy,
taxonomic, semantic, or AI interpretation.

Groups remain distinct: Collection includes SeedLot, Sowing, Plant, PlantGroup, Harvest, and Event; Media includes MediaAsset; Botany
includes BotanicalIdentity and operator-authored BotanicalProfile reference knowledge; Reference
includes Location, GeographicPlace, and ProvenanceSite; Sourcing includes Supplier and Order. Profile matches open the identity's
Reference tab. Event matches open the target's Events tab. No notes or contact details are copied
into snippets. The group count is exact; each response contains at most 20 items per kind by default
(`limit` up to 50). `offset` pages every kind consistently. The UI shows each group's loaded count
and total, then appends the next bounded page on Show more.

The query covers identity scientific, cultivar, and common names; labels and notes on collection
records; Event kinds, notes, target labels and identity names; Supplier names and notes; Location
names/paths; GeographicPlace names/paths; ProvenanceSite names and associated place names; and
BotanicalProfile text. Explicit relationship matches allow collection records to surface through
their stored identity, current Location, direct Supplier, direct place/site, or Sowing's source
SeedLot. No lineage, native-range, occurrence, or descendant-provenance inference is made.

`kind` accepts repeated record kinds. `identity_id`, `location_id`, `supplier_id`,
`provenance_place_id`, and `provenance_site_id` constrain applicable collection records; the
collection-only filters exclude Botany, Reference and Sourcing matches. Location selection includes the exact
node and descendants through persisted parent links, based on each record's own current Location.
The provenance filters match only a directly recorded place or site on a SeedLot or directly entered
Plant/PlantGroup; they do not propagate to Sowings or Events. Supplier also matches a Sowing through
its required SeedLot. `lifecycle` requires exactly one applicable record kind. `event_kind` requires
Event. `year` requires one collection kind and tests its recorded acquisition, sowing, collection
entry, or occurrence year respectively; it never fills in an unknown month or day. The interface
omits a photo filter because local versus external associated-photo semantics deserve a separate
explicit product choice. SEARCH-001 added no database table, index, or migration.

Dashboard Quick actions open the current Add seed lot, Add plant, Add plant group, and Import / Export
workflows. Start sowing stays on a chosen SeedLot's authoritative propagation path.

## SEARCH-002 — Harvest and Media coverage

SEARCH-002 is implemented; operator UAT has passed and independent verification is underway. Collection places
Harvests between Plant groups and Events; the dedicated Media category follows Collection, before
Botany and Reference. Repeated `kind=harvest` and `kind=media_asset` compose with all existing kinds.
Results remain compact text links without thumbnails, binary requests or external-image loading.

Harvest text matches its optional label, current derived display title, exact Plant/PlantGroup source
label, source identity scientific/common/cultivar names, Harvest notes, and each material kind or
human material label and description. Distinct materials follow the directory's item order and
bounded title summary. Notes/descriptions are searchable but never copied into snippets. Context
contains bounded identity/source labels, source type, the recorded partial date and material summary.
`identity_id` uses only that exact source's identity; `year` with `kind=harvest` uses only the occurrence
PartialDate year, including year-only/month-only dates. Unknown dates do not match. No created/updated
or acquisition timestamp supplies a year. Source lifecycle, current Location, Supplier and direct or
ancestor provenance are neither Harvest text nor structured relationships. Those structured filters
exclude Harvest. Harvest has no lifecycle; `event_kind` still requires Event and is not a Harvest
filter. A structured Harvest and its owned Event can independently match, with distinct typed routes.

Media text shares the Media Library predicate: title, the asset's own Attachment original filename
(including a saved external copy), and attribution, with literal escaping. Licence, source/image URLs,
record-link captions, linked-record labels, primary targets and botanical cover targets do not confer
matches. Collection relationship/year/lifecycle/Event filters exclude Media. Title falls back to
original filename then “External image reference”, matching the Library. Context is Local image or
External image and at most 160 attribution characters; storage keys, paths, URLs and binary metadata
are absent. `#/media/<uuid>` reuses the existing exact Library detail, supports refresh/back/forward,
rejects malformed UUIDs before requesting data, and reports deleted/missing assets with a Media return
link. Detail retains its existing explicit remote-image opt-in policy.

Material matching uses correlated EXISTS; an ordered aggregate provides one material summary per
Harvest. Source/identity joins are one-to-one through the exact source. Media joins only its own
Attachment, with no reference joins. Counts and pages use the same typed projection, sorted by lower
case title then UUID. Each kind adds exactly two SQL statements, independent of item/link/result
count. Existing text path lookups add two shared statements: mixed Harvest/Media text search uses six;
at the SEARCH-002 boundary unrestricted text search used at most 28 for 13 kinds;
ORDER-001 extends this to 30 for 14 kinds. Blank unfiltered queries use none. SEARCH-002 introduced no
schema, index, search engine, cache, saved view, bulk operation or generic history.

## Saved operator views

VIEW-001 lets the signed-in operator persist meaningful Global Search state in PostgreSQL. Open
uses the same canonical `#/dashboard?...` parser/serializer and live SEARCH-002 query, with offset
zero. Exact UUID filters survive missing references. Manual filter edits do not update a Saved View;
Update with current view is explicit. Dashboard also opens views from supported directories.
See [Saved Views contracts](saved-views.md).

## Purchase Orders (ORDER-001)

`kind=order` adds direct transaction reference/Supplier/notes matching and exact Order detail links.
Supplier and Order results are presented together as Sourcing. Case-insensitive literal substring
matching escapes `%` and `_`; no linked-lot joins or botanical matching multiply results. Context
retains only known date precision, Supplier and optional exact total/currency. Collection-specific
structured filters keep their existing meaning and exclude Orders. Count/page queries remain two
per selected kind; all 14 kinds plus shared paths are bounded to 30 SELECTs. Orders directory offers
its own exact Supplier filter and Saved Views. See [Orders](orders.md).
