# Reviewable structured native-range enrichment (ENRICHMENT-001)

The optional trusted-source panel in BotanicalIdentity → Native ranges uses the reviewed
**Kew WCVP version 16** archive by default (updated from v15 by `WCVP-DEFAULT-001`), while retaining
explicit **version 15** support, historical links, proposals, and applications.
[WCVP-VERSION-001](wcvp-version-001.md) documents both pinned releases and crosswalks. [Exact source approval](native-range-enrichment-source-v15.md)
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

New proposals use `wcvp15-wgsrpd2-cldr48.2.1-v2` or
`wcvp16-wgsrpd2-cldr48.2.1-v2`, depending on the confirmed release. Both use the
same 20 reviewed literal pairs. The review checked level-3 membership, reverse ISO
entries and the gazetteer in Brummitt's WGSRPD second edition (2001), Tables 3–6,
against modern ISO assignments and the CLDR seed. An `OO` child alone is insufficient.
Destinations resolve by the exact tuple `unicode_cldr / 48.2.1 / iso_3166_1_alpha_2 / <code>`.
[Official TDWG standard](https://www.tdwg.org/standards/wgsrpd/) · [CLDR seed evidence](geography-data.md)

| Decision | WCVP level-3 → ISO alpha-2 |
| --- | --- |
| Nine added | ALB→AL, BLR→BY, DEN→DK, GER→DE, ICE→IS, POL→PL, ROM→RO, SWE→SE, SWI→CH |
| Eleven retained | BOL→BO, BUL→BG, CBD→KH, HUN→HU, LAO→LA, OMA→OM, PAR→PY, PER→PE, THA→TH, URU→UY, VIE→VN |

`COS` is partial. WGSRPD Tables 4–6 place Cocos Island separately under `CPI-CO`.
Cocos Island is part of Costa Rica, so the v1 `COS→CR` mapping is withdrawn for new writes.
`FIN` includes Åland, while the modern reference seeds separate `FI` and `AX` destinations.
`BLT` remains a split covering Estonia, Latvia, Lithuania and Kaliningrad (part of Russia).
Table 4 prints `RU` for Latvia, while Table 5 and the gazetteer support `LV`.
`CZE` and `LBS` remain unsupported splits. Italy, France, Spain and Brazil partials remain
excluded. Unknown codes and missing or retired exact destinations remain unresolved.
[WGSRPD Tables 3–6](https://raw.githubusercontent.com/tdwg/wgsrpd/master/109-488-1-ED/2nd%20Edition/TDWG_geo2.pdf) ·
[Costa Rica Constitution, Article 5](https://sinalevi.go.cr/ResultadosNormativa/Informacion?param1=871&param2=147492&param3=3&param4=4853) ·
[ISO assignment of AX](https://www.iso.org/files/live/sites/isoorg/files/archive/pdf/en/newsletter_v-9_aland_islands.pdf)

The reviewed WGSRPD PDF SHA-256 is
`079221f42c20686591780676c115bcd8ca6bcb1abb10d225ef0ceff66cea78ec`.
Only the literal decisions are included in Florabase.

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
original v15 or v16 evidence even if the optional index disappears or is reprovisioned. Apply requires no
provider/cache access; it validates durable source/link evidence and the original approved
pinned release and its matching crosswalk. Link reconfirmation invalidates earlier proposals. A deliberate release change requires a new exact-taxon confirmation and fresh proposals. A source failure cannot silently refresh or
replace evidence. Confirm Apply explicitly names the frozen source version.

### Historical crosswalk compatibility

History retains the stored v1 or v2 evidence and version. Apply recognizes the two
release-specific v1 IDs and their v2 successors. It checks each selected destination against the
linked frozen native assertions and the literal map for the stored release and crosswalk.
A submitted v1 selection containing the COS-backed CR choice returns 409 with code
`native_range_mapping_withdrawn` and writes no ranges or application. The operator may deselect
CR and retry the safe subset of that proposal while it remains current. A fresh proposal retains
already recorded CR as CURRENT-ONLY. Existing source links can create v2 proposals without
reconfirmation when their identity and exact source still match.

### Read-only review of historical COS additions

Run against an operator-authorized backup or read replica, using an account with read-only
permissions. The query identifies actual v1 additions linked to a frozen COS assertion.
The application receipt's `kept` list includes pre-existing ranges and is unsuitable for this
purpose. `currently_recorded` indicates present membership. A range could have been independently
removed and re-added since the historical application.

```sql
BEGIN READ ONLY;

SELECT a.identity_id, a.proposal_id, a.applied_at,
       (c.choice ->> 'place_id')::uuid AS geographic_place_id,
       (r.geographic_place_id IS NOT NULL) AS currently_recorded
FROM native_range_applications AS a
JOIN native_range_proposals AS p ON p.id = a.proposal_id
CROSS JOIN LATERAL jsonb_array_elements(p.evidence -> 'choices') AS c(choice)
LEFT JOIN botanical_profile_native_ranges AS r
  ON r.botanical_profile_id = a.identity_id
 AND r.geographic_place_id = (c.choice ->> 'place_id')::uuid
WHERE (p.evidence #>> '{source,version}', p.evidence ->> 'crosswalk_version') IN (
    ('15', 'wcvp15-wgsrpd2-cldr48.2.1-v1'),
    ('16', 'wcvp16-wgsrpd2-cldr48.2.1-v1')
)
AND c.choice ->> 'code' = 'CR'
AND c.choice ->> 'change' = 'ADD'
AND (a.evidence -> 'added') ? (c.choice ->> 'place_id')
AND EXISTS (
    SELECT 1
    FROM jsonb_array_elements(p.evidence -> 'assertions') AS source(assertion)
    WHERE assertion #>> '{original,area_code_l3}' = 'COS'
      AND assertion ->> 'mapping' = 'equivalent'
      AND assertion ->> 'status' = 'native'
      AND (c.choice -> 'assertions') ? (assertion ->> 'assertion_id')
      AND (assertion -> 'place_ids') ? (c.choice ->> 'place_id')
)
ORDER BY a.applied_at, a.proposal_id;

ROLLBACK;
```

For recovery, use a build that recognizes both revisions and retains the COS write guard.
Rolling back to a v1-only binary can restore the withdrawn Apply behavior and reject v2 Apply.
Suspend enrichment writes if only that binary is available. Keep the frozen evidence intact.

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

## Optional coverage qualification

Use trusted, complete indexes built from the pinned archives. For v16 bundles, verify the
existing seal through the normal provisioning verification first. The check opens each index
read-only through Florabase's hardened SQLite opener. It has no runtime or CI dependency.
Save the Python block as `qualify.py` and run `python qualify.py 16 /path/to/v16/index.sqlite`
in the backend Python environment. Use `15` and the v15 path for the second release.

```python
"""Compare reviewed native-range policies using an existing complete WCVP index."""
from contextlib import closing
from pathlib import Path
import sys

from florabase.core.reference_index import open_reference_index
from florabase.native_range_enrichment.crosswalk import CROSSWALK_VERSIONS, frozen_equivalences
from florabase.native_range_enrichment.source import SCHEMA, WcvpSource

version, filename = sys.argv[1:]
if version not in ("15", "16"):
    raise SystemExit("Supply WCVP release 15 or 16 and the corresponding trusted index path.")
path = Path(filename)
source = WcvpSource(path, version)
source.metadata()
historical, current = CROSSWALK_VERSIONS[version]
old = set(frozen_equivalences(version, historical))
new = set(frozen_equivalences(version, current))
added = new - old
assert len(added) == 9 and old - new == {"COS"}

with closing(open_reference_index(path, SCHEMA, "WCVP coverage")) as connection:
    for label, codes in (
        ("original ten", added | {"FIN"}),
        ("added nine", added),
        ("historical twelve", old),
        ("current twenty", new),
    ):
        placeholders = ", ".join("?" for _ in codes)
        row = connection.execute(
            f"""
            WITH assertions AS (
              SELECT t.external_id,
                     json_extract(d.payload, '$.area_code_l3') AS area,
                     json_extract(d.payload, '$.introduced') = '0'
                       AND json_extract(d.payload, '$.extinct') = '0'
                       AND json_extract(d.payload, '$.location_doubtful') = '0' AS native,
                     t.status = 'Accepted' AND t.accepted_id = t.external_id
                       AND t.rank IN ('Species', 'Subspecies', 'Variety', 'Form') AS eligible
              FROM distributions AS d
              JOIN taxa AS t ON t.external_id = d.external_id
            )
            SELECT count(*), count(DISTINCT external_id),
                   count(*) FILTER (WHERE native),
                   count(DISTINCT external_id) FILTER (WHERE native),
                   count(*) FILTER (WHERE native AND eligible),
                   count(DISTINCT external_id) FILTER (WHERE native AND eligible)
            FROM assertions WHERE area IN ({placeholders})
            """,
            sorted(codes),
        ).fetchone()
        print(label, *tuple(row))
```

Columns are raw rows, distinct source taxon IDs, unqualified native rows, distinct unqualified
taxa, eligible native assertions and distinct eligible taxa. These are source counts. Eligibility
requires the same self-accepted ranks as the application.

| Release | Original ten native rows, including FIN | Nine new native rows | Nine new eligible assertions / taxa | v1 eligible assertions | v2 eligible assertions | Net |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 15 | 45,754 | 41,965 | 35,785 / 14,963 | 107,656 | 131,806 | +24,150 |
| 16 | 45,864 | 42,065 | 35,904 / 15,057 | 108,197 | 132,438 | +24,241 |

## Optional snapshot provisioning and deployment

The standalone CLI is independent of startup, PostgreSQL and health checks:

```sh
python -m florabase.native_range_enrichment.snapshot /wcvp/wcvp-v16.sqlite
```

It accepts only the two pinned official HTTPS releases, with `--version 15|16` (default `16`);
no user-supplied URL. Use a separate destination for each release. Connect/read timeouts
are 10/60 seconds, total streamed-download bound 240 seconds, compressed bound 100 MB, redirects
rejected, ZIP/octet-stream content required and SHA-256 pinned. ZIP members must match the exact
three reviewed names and uncompressed sizes; members stream without extraction. UTF-8, pipe
headers, row widths, identifier uniqueness, binary flags and distribution/taxon references are
validated. A temporary index is atomically renamed only after complete success. Failed download
or parse leaves an existing index intact. Files are limited to 2 GB; index permissions are 0600.

For an already audited archive, preserve its **actual retrieval timestamp**, not installation time:

```sh
python -m florabase.native_range_enrichment.snapshot /wcvp/wcvp-v15.sqlite \
  --version 15 --archive /audit/wcvp_v15.zip \
  --retrieved-at 2026-10-09T06:16:20.117071+00:00
```

The reviewed complete index holds 1,441,152 taxa and 1,986,879 distribution assertions and occupies
948,400,128 bytes. Allow roughly 2 GB for existing/temporary indexes plus the 89,508,082-byte archive
in download temporary storage. Download scratch space is removed on completion/failure. Only the
current index for each separately configured release is retained; reprovisioning is an explicit operator action, with no automated refresh.
Use only an index this builder produced from a pinned archive; a file from anywhere else is
untrusted input to SQLite. Every connection requires the exact layout the builder writes for both
reviewed releases (`metadata`, `taxa`, `distributions`, their primary-key indexes, `taxa_search`
and `distribution_taxon`) and refuses views, triggers, virtual tables or any other object before
a query runs, read-only with SQLite defensive hardening
([record](security/beta-distribution-001/sqlite-reference-indexes.md)). A builder also refuses to
publish an index that would fail that check.
The index is replaceable reference data, not collection backup authority. PostgreSQL provenance
belongs in normal database backups; optional source indexes can be rebuilt from the pinned archive.

Production starts normally without this optional file. Provision it as the backend container's
runtime user into a separately managed directory, then supply a read-only bind mount and
`FLORABASE_WCVP_V16_SNAPSHOT_PATH=/wcvp/wcvp-v16.sqlite` (and optionally
`FLORABASE_WCVP_SNAPSHOT_PATH=/wcvp/wcvp-v15.sqlite` for explicit v15) in a deployment override. Keep it outside
source/build contexts and uploads; do not expose a database or introduce startup downloads.
The default setting is absent. No production/DEV/Stable Preview source cache was provisioned here.

For the original ENRICHMENT-001 synthetic UAT, the existing source bind contains the ignored
`backend/src/.source-cache/wcvp-v15.sqlite`; `compose.uat.yaml` selects that optional path.
`.gitignore` and the backend Docker exclusion keep it out of Git and images. The official audit
archive remains outside the repository. The [handoff](enrichment-001-handoff.md) records validation
and operator scenarios. ENRICHMENT-002 automatic refresh remains planned; BOTANY-003 text enrichment
and the deferred broad product/visual review retain their independent ownership.
