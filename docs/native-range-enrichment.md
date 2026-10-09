# Reviewable structured native-range enrichment (ENRICHMENT-001)

The optional trusted-source panel in BotanicalIdentity → Native ranges uses the reviewed
**Kew WCVP version 15** archive. [Exact source approval](native-range-enrichment-source-v15.md)
records its schema, licence, attribution, complete inspection and checksum. Only explicit Apply
writes canonical `BotanicalProfileNativeRange` relationships. Opening, searching, confirming a
source link and retrieving proposals never create a profile or change recorded ranges or text.
EXPLORE-002 continues reading those same canonical relationships.

## Source and taxon review

A separately provisioned local SQLite index serves bounded literal name-prefix searches (25
results). Results retain the exact WCVP `plant_name_id`, authorship, rank, status, accepted ID/name,
POWO ID and reviewed marker. Duplicate names remain separate choices. Synonyms and non-accepted
names are context only; the operator must explicitly confirm an Accepted, self-accepted Species,
Subspecies, Variety or Form. This confirmation authorises that exact provider ID for the current
BotanicalIdentity snapshot. It does not infer identity from names, cultivars, GBIF or CoL.

WCVP confirmation has its own `wcvp_links` table. Existing `ExternalTaxonLink`/GBIF services have
GBIF-specific matching and occurrence behavior; reusing them would give an unrelated provider
false meaning. No existing opaque external IDs or provider links are rewritten.

## Geography contract

Crosswalk **`wcvp15-wgsrpd2-cldr48.2.1-v1`** derives exact equivalence from the official
[WGSRPD second edition](https://www.tdwg.org/standards/wgsrpd/), Table 4's level-3, single
level-4 `OO`, and single ISO code entries. It resolves canonical GeographicPlaces only by the
existing source tuple `unicode_cldr / 48.2.1 / iso_3166_1_alpha_2 / <code>`.

| WCVP level-3 | Canonical ISO code | Geographic unit |
| --- | --- | --- |
| BOL | BO | Bolivia |
| BUL | BG | Bulgaria |
| CBD | KH | Cambodia |
| COS | CR | Costa Rica |
| HUN | HU | Hungary |
| LAO | LA | Laos |
| OMA | OM | Oman |
| PAR | PY | Paraguay |
| PER | PE | Peru |
| THA | TH | Thailand |
| URU | UY | Uruguay |
| VIE | VN | Vietnam |

This intentionally small whitelist does not claim global mapping completeness. `CZE`, `BLT`
and `LBS` contain multiple country units: they are **unsupported splits**, visible but excluded.
`ITA/SAR/SIC`, `FRA/COR`, `SPA/BAL` and the five Brazilian subregions are explicitly partial,
not rounded to ISO countries. Every other code (including blank/lowercase codes) is unresolved.
The reviewed official WGSRPD PDF has SHA-256
`079221f42c20686591780676c115bcd8ca6bcb1abb10d225ef0ceff66cea78ec`.
No display-name joins, geometry-based intersections, inferred descendants, geographic hierarchy
expansion or inferred botanical detail occurs. Missing or retired exact places remain unresolved.

An assertion is eligible only when `introduced=0`, `extinct=0` and `location_doubtful=0`.
Introduced and qualified assertions remain separate context, with all original flags and the
complete 11-field distribution row retained. Empty distributions and unmapped units do not mean
absence of native distribution. Natural Earth remains drawing geometry only.

## Proposals and Apply

Retrieve source proposal freezes the identity, confirmed link version, taxon, exact source metadata,
retrieval time, crosswalk version, current canonical IDs and monotonic destination revision, raw
assertions and their mapping decisions. A diff shows **ADD**, **KEEP** and **CURRENT-ONLY**.
Current-only ranges are preserved even if the source omits them. Select mapped Native additions
(or a KEEP for a deliberate no-change application), review Add/Keep counts, then Confirm Apply.
Removals and replacement are not supported in this increment; Apply always keeps every existing
range and removes none. Empty selection is rejected. Introduced/unresolved assertions cannot be
selected. No source narrative is generated or copied into profile text.

Apply locks selected places in stable order, then the identity (the same order used by canonical
range writers), and rechecks exact geography metadata, identity snapshot, confirmed link version,
source/taxon snapshot, destination IDs/revision and crosswalk version. Any stale value rejects the
entire transaction with 409. A database trigger increments the destination revision for every
range insertion/update/deletion, so edit-and-restore cannot conceal an intervening change.
Concurrent applications of one frozen proposal yield one success and one conflict.

**Frozen-source policy:** an already retained proposal may be applied against its explicitly displayed
version-15 evidence even if the optional index disappears or is reprovisioned. Apply requires no
provider/cache access; it validates durable source/link evidence and the current implementation's
pinned release and crosswalk. Link reconfirmation invalidates earlier proposals. Future approved
source/crosswalk versions will require fresh proposals. A source failure cannot silently refresh or
replace evidence. Confirm Apply explicitly names the frozen source version.

## Durable provenance and lifecycle

Migration `20261009_0039` adds `wcvp_links`, `native_range_revisions`, `native_range_proposals`
and `native_range_applications`. PostgreSQL guards proposal updates and application updates/deletes.
One application per proposal is enforced by its primary key. The application retains the complete
proposal, selected IDs, added/kept IDs, no removals, destination revision after Apply and UTC time.
The UI can reopen the latest ten retained proposals and inspect applied Add/Keep outcomes; every
proposal remains individually readable by ID. Evidence survives cache deletion, link replacement,
manual canonical range edits and geography display changes. Identity deletion serializes with Apply; applied evidence blocks identity
removal through the ordinary referenced-identity conflict and restrictive FKs. Unapplied proposals
and links can disappear with explicitly deleted unreferenced identities.

Empty downgrade is supported, preserving canonical ranges and text. Downgrade takes exclusive
locks and refuses if **any** WCVP link, proposal or application exists, preventing reviewed evidence
loss. No backfill, startup migration or extra migration path is introduced. Source-only activity
never creates an empty BotanicalProfile; Apply creates one only when adding its first actual range.
Provenance is reference evidence, not operational History or a Saved View.

## API and security

All routes are beneath `/api/v1/botanical-identities/{identity_id}/native-range-enrichment`:

| Method | Suffix | Effect |
| --- | --- | --- |
| GET | `/source` | Optional index status and existing confirmed link |
| GET | `/taxa?q=…` | Literal prefix search, 2–200 characters, maximum 25 |
| PUT | `/link` | Confirm exact taxon and reviewed checksum |
| POST | `/proposals` | Freeze bounded source evidence, maximum 500 assertions |
| GET | `/proposals` | Latest ten frozen proposals |
| GET | `/proposals/{proposal_id}` | Exact frozen proposal and application outcome |
| POST | `/proposals/{proposal_id}/apply` | Unique explicit selection, 1–100 places; atomic Apply |

Reads require authentication; writes require owner role, Origin and CSRF checks. Inputs reject
extra fields. Source failures return retryable 503 (status instead reports availability); stale
Apply returns 409; missing identity/proposal returns 404. API requests never make outbound network
calls. Missing/corrupt/unapproved local snapshots fail closed without affecting recorded ranges.

## Optional snapshot provisioning and deployment

The standalone CLI is independent of startup, PostgreSQL and health checks:

```sh
python -m florabase.native_range_enrichment.snapshot /wcvp/wcvp-v15.sqlite
```

It accepts only the fixed official HTTPS v15 archive; no user-supplied URL. Connect/read timeouts
are 10/60 seconds, total streamed-download bound 240 seconds, compressed bound 100 MB, redirects
rejected, ZIP/octet-stream content required and SHA-256 pinned. ZIP members must match the exact
three reviewed names and uncompressed sizes; members stream without extraction. UTF-8, pipe
headers, row widths, identifier uniqueness, binary flags and distribution/taxon references are
validated. A temporary index is atomically renamed only after complete success. Failed download
or parse leaves an existing index intact. Files are limited to 2 GB; index permissions are 0600.

For an already audited archive, preserve its **actual retrieval timestamp**, not installation time:

```sh
python -m florabase.native_range_enrichment.snapshot /wcvp/wcvp-v15.sqlite \
  --archive /audit/wcvp_v15.zip \
  --retrieved-at 2026-10-09T06:16:20.117071+00:00
```

The reviewed complete index holds 1,441,152 taxa and 1,986,879 distribution assertions and occupies
948,400,128 bytes. Allow roughly 2 GB for existing/temporary indexes plus the 89,508,082-byte archive
in download temporary storage. Download scratch space is removed on completion/failure. Only the
current index is retained; reprovisioning is an explicit operator action, with no automated refresh.
The index is replaceable reference data, not collection backup authority. PostgreSQL provenance
belongs in normal database backups; optional source indexes can be rebuilt from the pinned archive.

Production starts normally without this optional file. Provision it as the backend container's
runtime user into a separately managed directory, then supply a read-only bind mount and
`FLORABASE_WCVP_SNAPSHOT_PATH=/wcvp/wcvp-v15.sqlite` in a deployment override. Keep it outside
source/build contexts and uploads; do not expose a database or introduce startup downloads.
The default setting is absent. No production/DEV/Stable Preview source cache was provisioned here.

For this worktree's synthetic UAT, the existing read/write source bind contains the ignored
`backend/src/.source-cache/wcvp-v15.sqlite`; `compose.uat.yaml` selects that optional path.
`.gitignore` and the backend Docker exclusion keep it out of Git and images. The official audit
archive remains outside the repository. The [handoff](enrichment-001-handoff.md) records validation
and operator scenarios. ENRICHMENT-002 automatic refresh remains planned; BOTANY-003 text enrichment
and the deferred broad product/visual review retain their independent ownership.
