# Domain model — Collection IA, lineage, attachments and ownership

> Summary: Collection information architecture, explicit lineage graph rules, attachment storage contract, and ownership/mutation boundary.

## Collection information architecture

The authenticated application opens on a Dashboard backed by one focused aggregate endpoint. It
reports authoritative counts for active Plants, active PlantGroups, active SeedLots, active Sowings,
all BotanicalIdentities, and all Events, plus the six most recent Events. These are current overview
counts, not the analytical/statistical definitions planned for `DASHBOARD-001`; transferred Plants
and PlantGroups are excluded from the active counts while remaining in historical lists and identity
aggregation.

The Dashboard also hosts authenticated global collection search. Typed, bounded server results
separate Collection, Botany, Reference, and Sourcing records; stored relationship matches do not infer
provenance or turn BotanicalProfile text into an observation. URL query parameters retain search
and structured filter state. [Search and filter semantics](../../features/tools/search.md) define exact applicability,
location scope, partial-year behavior, and result paging. Local directory search remains available.

Desktop navigation uses these macroareas, in order: **Overview** (Dashboard), **Collection**
(Seeds, Sowings, Plants, Harvests, Locations), **Activity** (Journal, History, Schedule), **Explore**
(Botanical identities, Media, Geography, Collection origins), **Sourcing** (Suppliers, Orders), and
**Tools** (Import / Export, Labels). Page-level eyebrows follow the macroarea. Routes are unchanged;
Collection origins retains `#/map` and Saved View surface `provenance_map`. Mobile More retains every
destination. Unknown old Places/Reference collapse preferences are ignored; active groups expand.

Collection origins describes where actual collection material is recorded as coming from.
Species distribution describes where a species is observed/distributed; Native range describes where
it is considered biologically native/original. Neither is inferred from collection provenance,
Supplier or current Location. EXPLORE-001 adds the separate collection-aware Species distribution
workspace; EXPLORE-002 adds the separate recorded Native ranges workspace.

Activity contains the focused Event Journal, read-only unified operational History and date-only
Schedule workspace. Schedule stores future intention separately from historical occurrences.
Completion can omit an Event or explicitly link one atomically; a calendar remains a presentation.

Desktop macro-groups use accessible disclosures. All start expanded; a browser-only localStorage
presentation preference remembers collapsed groups. Route activation expands the active group.
This preference never enters PostgreSQL or Saved Views; mobile keeps its existing More navigation.
The Journal name changes only the global UI vocabulary, preserving Event/API/route/surface identities.

BotanicalIdentity is a botanical/reference and collection hub with Overview, Reference, Seeds,
Sowings, Plants, and Events tabs. The Reference tab contains operator-authored profile/native-range
knowledge and advisory external occurrence evidence and avoids eagerly loading hidden collection
content. Its
Plants tab intentionally combines Plant and PlantGroup cards while labeling their distinct types.
The overview separates active and transferred Plant and PlantGroup counts rather than treating
transferred material as currently held.
The hub uses stored identity relationships only: a Sowing belongs through its required SeedLot and
Events belong through their current Plant or PlantGroup target. This aggregation never creates a
lineage edge. Dedicated record details link back to the identity hub and retain their explicit
lineage view separately.

Plant and PlantGroup details use Overview, Events, and Lineage tabs; SeedLot uses Overview, Sowings,
and Lineage; Sowing uses Overview and Lineage. Breadcrumbs and tab query parameters provide stable
orientation and deep links. User-created BotanicalIdentity, SeedLot, Sowing, Plant, PlantGroup,
Location, Supplier, and custom GeographicPlace data have visible correction flows. Canonical
GeographicPlaces remain immutable by design, and lifecycle-bearing records retain their existing
non-destructive lifecycle semantics.

The collection pages provide a guided `BotanicalIdentity → SeedLot → Sowing → Plant / PlantGroup`
entry path. Identity tabs preselect identity context but require the operator to choose a real
SeedLot or Sowing before storing lineage. SeedLot-to-Sowing entry separates normal Sowing details
from a visible source-effect confirmation: exact compatible quantities can show an authoritative
subtraction preview, approximate remainders remain editable estimates, unknown quantities stay
unknown, and incompatible dimensions do not offer arithmetic. No adjustment and use-all remain
explicit choices governed by the backend contract.

Sowing detail links its source and displays the authoritative descendant summary without converting
approximate or unknown PlantGroups into exact individuals. Plant and PlantGroup creation asks for an
explicit resulting Sowing lifecycle and defaults to keeping it active. Completing an exact
seed-count Sowing can display `not germinated` as `quantity - germinated_count`; approximate,
unknown, and weight-based Sowings do not fabricate that remainder. Completed Sowings remain
clickable under the Completed and All filters, while failed and abandoned history remains reachable
through All. The Sowing propagation view and the SeedLot and Plant/PlantGroup Lineage views
visualize only stored lineage.

Ordinary direct Plant/PlantGroup creation, retroactive entry, and all correction forms remain valid.
Later corrections do not replay previous source effects or lifecycle choices. Dated germination
observations appear in the Sowing's Germination detail tab, separately from the simple total.

The product navigation follows `BotanicalIdentity → SeedLot → Sowing → Plant / PlantGroup →
Events / terminal state`. It is an interaction and comprehension direction over the explicit model,
not a new relationship, automatic state machine, or claim that every record has complete ancestry.
Natural next-step actions appear in the record header ahead of correction, transfer, reversal, or
destructive controls. Record lists lead with the record's own label and show BotanicalIdentity as
supporting context. Direct links follow stored identity, source, Location, Supplier, provenance, and
Event relationships without conflating BotanicalIdentity aggregation with recorded lineage.

Location presentation scopes the one shared Location hierarchy by its Seeds, Sowings, or Plants
usage without splitting Location into separate domain entities. Supplier detail summarizes only
explicitly connected material and links separately to its Orders. It does not aggregate spending
or combine currencies. Finer-grained geography remains compatible with carefully scoped custom/local
GeographicPlace nodes, while a canonical global city dataset is not part of the current or
first-release model.

## Explicit lineage

Florabase persists only direct relationships created by supported workflows:

```text
SeedLot → Sowing → Plant / PlantGroup
```

```text
PlantGroup → extracted Plant
```

```text
Plant / PlantGroup → collection-produced SeedLot
```

The arrows show material/workflow descent. The lineage service walks the reverse direction from a
SeedLot, Sowing, Plant, or PlantGroup to its recorded ancestors and returns typed summaries in
immediate-first order. Public upstream endpoints exist for SeedLot, Plant and PlantGroup; Sowing
exposes its direct SeedLot and descendant propagation summary.

A Plant's Sowing origin, PlantGroup extraction origin, and direct origin are mutually exclusive. A
PlantGroup's Sowing and direct origins are mutually exclusive. An extracted Plant does not duplicate
the group's Sowing or SeedLot links; those ancestors are derived by traversal. Producer assignment
to a collection-produced SeedLot is also exclusive between Plant and PlantGroup, and application
validation prevents every source correction from creating a cycle. PostgreSQL also serializes
lineage writes and rejects cycles on every concrete edge; new operation receipts must correlate
their concrete source/result/Event references at insertion. See the
[lineage integrity audit](../lineage-integrity.md) for correction, retention and concurrency invariants.

BotanicalIdentity is deliberately independent at every applicable level. A downstream correction
does not rewrite upstream records or invalidate lineage. Inactive SeedLots, Sowings, Plants,
PlantGroups, Suppliers, Locations, and custom GeographicPlaces retain historical references.

Unknown or partial lineage remains honest absence. Florabase does not infer a Sowing from matching
names, create placeholder ancestors, or use a generic genealogy graph. Maternal/paternal pairs,
pollen donors, controlled crosses, multiple producers, arbitrary group merge and graphical lineage
navigation are deferred. Receipt-proven extraction reintegration is already implemented.

## Attachment storage contract

An `Attachment` is one Florabase-managed local still-image binary plus the narrow metadata required
to store and recover it safely. It has an application-generated UUIDv7 ID, a separate unique
server-generated storage key, a normalized display filename, validated `image/jpeg`, `image/png`, or
`image/webp` media type, a positive byte size of at most exactly 25 MiB (26,214,400 bytes), a
SHA-256 digest, an `active` or `pending_delete` state, and a timezone-aware UTC creation timestamp.
The binary is in the backend-only durable attachment volume, never PostgreSQL. The filename is not a
path, and the API exposes neither the storage key nor a filesystem location.

JPEG, PNG, and WebP content must pass signature, declared-type, and image-decoder validation. SVG,
GIF, HEIC/HEIF, AVIF, documents, audio, video, empty files, malformed files, and animated images are
outside the first contract. The backend streams bounded chunks to generated temporary files beneath
the trusted root, hashes and validates them, atomically renames within that filesystem, then commits
metadata. Ordinary failures clean temporary or newly placed files; a crash after rename and before
metadata commit can leave an inaccessible orphan for operator reconciliation.

Only active attachments are retrievable through owner-protected opaque-ID routes. Retrieval resolves
the persisted server key beneath the configured root, rejects missing, mismatched, traversal, and
symlink-escape states, and returns validated content type, safe inline disposition, `nosniff`, and
private, no-store cache handling.
Deletion commits `pending_delete` before unlinking, immediately blocks retrieval, and removes the row
only after content is absent. Failed unlink retains the pending row for a deterministic DELETE retry;
an unexpectedly missing active file is reported before a later pending retry completes cleanup.

`ATTACHMENT-005` separates reusable MediaAsset from exact RecordMediaLink. Attachment remains
technical metadata for one local original; each asset has at most one original and one shared,
regenerable 320px WebP derivative. Gallery assets may have no links. Record uploads create asset and
link atomically. Captions and nonnegative display order belong to each link; source, attribution,
licence and optional dimensions belong to the asset. No automatic binary deduplication is performed.

RecordMediaLink supports exactly SeedLot, Sowing, Plant, PlantGroup, Event, Harvest and Supplier through concrete
foreign keys, one target per link and a unique asset/target pair. Target identity is immutable.
Event hard deletion is blocked while links remain; the existing lifecycle rules of other targets
are unchanged. Supplier has shared links and an explicit representative primary; Harvest uses the
same shared links and primary selection. BotanicalIdentity uses a distinct cover
reference, excluded from RecordMediaLink.

CollectionPrimaryPhoto remains an explicit designation for SeedLot, Plant, PlantGroup, Harvest and Supplier,
referencing a link on that exact target. Unlink clears only that link's primary, retains the asset
and never guesses a replacement. Each record can independently designate the same shared asset.
Safe batched summaries retain local primary, eligible local identity-cover fallback, then placeholder;
external primaries with saved snapshots use protected local thumbnails; reference-only primaries
remain unloaded until explicit Preview once in Photos or media detail.

Supplier media never inherits through acquisition or lineage: its primary applies only to that Supplier.
Collection media means assets with at least one explicit SeedLot/Sowing/Plant/PlantGroup/Event/Harvest
link. Suppliers means at least one Supplier link. Shared Supplier + Plant media appears in both;
Supplier-only media never appears in a Plant gallery or Collection media. MediaAsset remains global
and reusable, with no Supplier category or persistent role. Supplier has retirement/reactivation,
no ordinary hard-delete API; restrictive media FKs also guard direct SQL deletion.

BotanicalIdentityCoverImage keeps one current cover per identity, backed by a MediaAsset. It is an
active reference independent of collection links. Cover replacement/removal retains the former
asset. Existing local upload and external privacy acknowledgement remain; the accepted external
cover can render in the existing Botany compact/detail views with no referrer, without granting
Gallery or collection views permission to load it automatically.

Unlinked means zero RecordMediaLinks; fully unreferenced additionally means zero cover references.
Local and external assets remain valid Gallery items with either state and are never automatically
cleaned up. Explicit asset deletion is blocked until fully unreferenced. Eligible local deletion
uses pending-delete retry for original, derivative and metadata; unlink and cover removal never
perform that deletion. PostgreSQL constraints and asset/target locks protect concurrent linking,
primary selection, unlinking and deletion. Historical mixed-owner metadata migrates without moving
files or changing references. Populated downgrade requires the paired pre-upgrade backup.

An external MediaAsset may own one persistent Attachment snapshot and fetched-at timestamp while
retaining external kind, canonical URL, attribution and UUID. Explicit save/refresh/remove actions
never change its links, primary selections or covers. Refresh validates before publishing and retains
a valid copy on fetch failure. The snapshot is included in paired backups and adds no logical
reference for deletion eligibility. One pending-attachment pointer supports interrupted cleanup,
without version history or automatic cleanup. Revision 0028 introduces absent copies for old data.

See [shared media contract, APIs, migration and review evidence](../../features/explore/media-library.md).

## Ownership and mutation boundary

The current installation supports one enabled owner. Domain and reference records are
installation-wide and do not carry per-user ownership columns. Reads require an authenticated
session; mutations require owner authorization, exact Origin, and a session-bound CSRF token. Normal
product workflows preserve historical rows rather than hard-deleting them.
