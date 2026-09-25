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

Groups remain distinct: Collection includes SeedLot, Sowing, Plant, PlantGroup, and Event; Botany
includes BotanicalIdentity and operator-authored BotanicalProfile reference knowledge; Reference
includes Supplier, Location, GeographicPlace, and ProvenanceSite. Profile matches open the identity's
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
collection-only filters exclude Botany and Reference matches. Location selection includes the exact
node and descendants through persisted parent links, based on each record's own current Location.
The provenance filters match only a directly recorded place or site on a SeedLot or directly entered
Plant/PlantGroup; they do not propagate to Sowings or Events. Supplier also matches a Sowing through
its required SeedLot. `lifecycle` requires exactly one applicable record kind. `event_kind` requires
Event. `year` requires one collection kind and tests its recorded acquisition, sowing, collection
entry, or occurrence year respectively; it never fills in an unknown month or day. The interface
omits a photo filter because local versus external associated-photo semantics deserve a separate
explicit product choice. No new database table, index, or migration was added.

Dashboard Quick actions open the current Add seed lot, Add plant, Add plant group, and Import / Export
workflows. Start sowing stays on a chosen SeedLot's authoritative propagation path.
