# Collection taxonomy — TAXONOMY-003

`#/taxonomy` explores classification of represented BotanicalIdentities. **Taxonomy is classification**;
collection **Lineage** remains explicit recorded material ancestry. Classification does not establish
phylogeny, genetic distance, evolutionary branch lengths or divergence ages.

## Source and explicit association

[Source GO and schema](taxonomy-003-source.md) pin official World Flora Online Plant List **2026-06**,
CC0, its archive SHA-256 and an independently reviewed biological-root boundary. Provision explicitly:

```bash
# Obtain the exact official archive using normal verified HTTPS; retain its actual retrieval time.
python -m florabase.taxonomy.snapshot /path/to/wfo_plantlist_2026-06.zip \
  /path/to/wfo-2026-06.sqlite --retrieved-at <actual-UTC-timestamp>
```

Set `FLORABASE_WFO_SNAPSHOT_PATH` to that SQLite file and mount its sibling `.sha256` validation seal
read-only. In UAT the optional files live in ignored `backend/src/.source-cache/` and are excluded from
Git and images. Normal startup, navigation and API reads make no WFO request and send no collection
data externally. Provisioning validates archive checksum/size/members/metadata, strict UTF-8/tabular
schema, identifiers/duplicates, reviewed ranks, exact parent and synonym references, root reachability,
cycles, controls and bounds. Validation failures leave the previous SQLite artifact untouched.
The index seal detects later byte corruption and is verified once per artifact identity per process;
requests use indexed reads, never reparse the archive. A source replacement can briefly be unavailable
until its matching seal exists; it cannot silently acquire different meaning.

BotanicalIdentity Reference → Taxonomy searches at most 25 literal source-name prefix candidates.
Inspect scientific name, authorship, rank, accepted/synonym/unplaced status and complete classification;
**Confirm taxonomy link** is a separate operator action. Existing links are visibly replaced only by
explicit confirmation. No GBIF/WCVP ID conversion, crosswalk, fuzzy matching or local name correction.
Unplaced bare names have no classification and cannot be confirmed. A source synonym remains the exact
linked name; WFO's accepted concept provides its advisory classification. No synonyms/name-history or
reconciliation capability is implemented.

The canonical `wfo_links` table stores one current relationship per identity, opaque WFO ID, UUIDv7
link version, confirmation timestamp, reviewed source/taxon/path evidence and identity update timestamp.
A writer locks the identity and compares both its update timestamp and the expected current link
version, including expected absence. Concurrent confirmation/unlink cannot silently overwrite a
changed relationship. Identity edits make placement unresolved until explicit review. Same-release
reprovision preserves meaning; a different release/checksum or changed path is unresolved, requiring
review. Source version mismatch never silently upgrades a relationship. Links are optional references
and follow deletion of an otherwise unused BotanicalIdentity; they never cascade collection records.

## Collection filters, counts and unresolved knowledge

Reuse `explore.service.filtered_projection` exactly, including EXPLORE-002's category qualification.
All represented / Living / Current / Historical and OR across Seeds / Sowings / Plants / Plant groups /
Stored material drive the same identity set for tree, search, totals, node detail and related peers.
No category selected means unrestricted. Living + Seeds is empty. Historical means no Current evidence
anywhere, with retained evidence in the chosen categories. Reference-only identities are excluded.

Every node counts **distinct represented BotanicalIdentities** below it. Several collection records
or a source-synonym association still contribute one identity per ancestor. Living is a subset of
Current; Historical is disjoint from Current. These are identities, not plants, quantities, source taxa
or occurrences. Only linked eligible taxa and connecting ancestors reach the browser. Parent edges
come from the reviewed source, never from scientific-name tokens or flat GBIF classification.

Search is literal case-insensitive substring over local scientific/common/cultivar display names and
source classification names, including genus/family and retained intermediate nodes. `%` and `_` are
literal characters. No provider search or source confirmation occurs per keystroke. Missing links,
stale identity evidence, missing placement and mismatched versions stay in **Unresolved taxonomy**
with a contextual source-link action. Optional source absence/corruption leaves the whole collection
and identity/profile workflows usable and explains source unavailability without guessed placement.

## Hierarchy, details and navigation

Accessible nested lists use native keyboard buttons with `aria-expanded` and labelled expansion,
`aria-pressed` selection, visible focus and an explicit Selected label/border. Default presentation
emphasizes major ranks, branching ranks and the selected node. Nonbranching intermediate ranks may be
compressed visually, never removed from source evidence or counts. Show every source rank restores
them; node details and identity breadcrumbs retain the full path. Higher ranks/families start open,
genera start collapsed. Expansion is transient. Deep indentation contracts on mobile; tree/detail
stack below 850px rather than becoming a horizontally scrolling diagram.

Node detail shows filter-respecting representation counts, genera and identities. BotanicalIdentity
shows a read-only full source breadcrumb and View in Taxonomy navigation. Related in my collection
orders Same source taxon, Same genus, Same family, Same order, then deterministic display label/UUID.
Those are classification labels, with no genetic-distance claim. The identity panel explicitly uses
All represented and unrestricted categories; identity API callers can request the same scope/categories/
search as the tree. Missing/stale links preserve local identity usability.

URL keys: `scope`, repeated canonical-order `record`, literal `q`, selected `taxon`. Back/Forward and
refresh restore them. An ineligible selected node remains visibly missing; filters are never broadened.
Selection and expand/collapse do not trigger provider calls. Search changes replace URL history;
filter/selection changes create navigable history entries. Expansion, scroll and hover are not saved.

**Saved Views deliberately deferred.** The narrow educational workspace's filter/selected-node URL is
shareable locally and persistent across refresh. VIEW-001 was audited; a new private surface would
require another durable contract/migration for convenience rather than an essential current workflow.
This increment adds only the durable source relationship migration, not a Saved View surface.

## API and bounds

Authenticated local reads:

- `GET /api/v1/explore/taxonomy/tree`: `scope`, repeated `record` (max 5), `q` (max 200).
- `GET /api/v1/explore/taxonomy/nodes/{source_taxon_id}`: identical filters, filtered 404 when absent.
- `GET /api/v1/botanical-identities/{uuid}/taxonomy`: source/link/breadcrumb and represented related peers;
  same filters accepted, default All represented/unrestricted categories.
- `GET /api/v1/botanical-identities/{uuid}/taxonomy/candidates?q=...`: explicit local prefix search,
  2–200 characters, at most 25 results and source paths.
- `PUT .../taxonomy/link`: owner/Origin/CSRF, exact source ID/checksum, identity update timestamp and
  expected link version. `DELETE .../taxonomy/link?version=...`: same write guards and version check.

Tree/node detail use at most two PostgreSQL SELECTs (shared filtered collection projection + link batch),
independent of identity or ancestor count. One recursive SQLite CTE reads the union of required source
paths; local metadata reads are constant. No source query per ancestor. Eligible sets over **5,000**
identities fail explicitly with a narrow-filter instruction; no silent truncation. Hierarchy depth is
bounded to 64, fetched union to 100,000 nodes, installed index to 1 GB. The whole source is never shipped.

Migration `20261009_0040` follows `0039`, adds only `wfo_links`. Empty downgrade/reupgrade preserves
other domain state. Downgrade takes an exclusive writer lock and refuses if confirmed links exist,
preventing loss of operator review evidence. No migration occurs at app startup.

[Implementation and UAT evidence](taxonomy-003-handoff.md). Broad cross-application product/visual
review remains a future operator checkpoint. TAXONOMY-001/002, PHYLOGENY-001, BOTANY-003/004 and
ENRICHMENT-002 keep their separate planned ownership.
