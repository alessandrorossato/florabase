# BOTANY-003 source decisions — 2026-10-09

The existing two-field content contract is approved. These decisions distinguish content eligibility
from secure acquisition and from implemented product behavior. BOTANY-003 remains **planned**.
The exact WFO / Flora of China description source remains blocked. A later bounded alternative-source
review approved only three Kew SEPASAL / Flora Zambesiaca records; see the [current bounded decision](botany-003-audit.md#35-final-bounded-official-source-fallback--2026-10-09).

## Flora of China description: SOURCE_BLOCKED

- Provider: World Flora Online; original source: Flora of China / Missouri Botanical Garden,
  Harvard University Herbaria and the treatment's named contributors.
- Exact resource: [WFO resource 33516](https://www.worldfloraonline.org/resource/33516),
  Flora of China @ efloras.org Darwin Core Archive.
- Official artifact: <https://files.worldfloraonline.org/files/eFloras/Flora_Of_China/Flora_Of_China.zip>.
- Publication identity: mutable URL, no immutable release established. Official indexed provider
  metadata advertises annual harvesting, last completed 2026-08-03, with description/reference import.
  Research-tool direct resource-page reads failed; indexed metadata is discovery evidence only.
- Retrieval timestamp / checksum: **none for this run**; all verified requests failed during TLS.
- Previously approved schema: `classification.txt`, `description.txt`, `reference.txt`, `meta.xml`;
  description taxon ID, text, type, source/reference ID, language, created, contributor, audience,
  license, rights holder and rights. Exact taxon/reference join; never join by scientific name.
- Previously approved field: English `general` description, deterministically converted to plain text.
  Preserve source wording; separate candidates for separate references; no automatic concatenation.
- Previously inspected effective license: CC BY 4.0 with Missouri Botanical Garden rights/defaults;
  explicit element overrides take precedence. This historical eligibility does not approve unseen
  current bytes. Credit the original Flora/reference/contributors and WFO, with license and original URL.
- Exact example IDs from the earlier approved audit: `wfo-0000514777` and `wfo-0000537707`.
  They are WFO IDs, not WCVP, IPNI or GBIF IDs.
- Required update policy: explicit provisioning, retained immutable dated snapshot plus checksum;
  reinspection before accepting changed bytes, then bounded local lookup. Startup stays independent.

[The earlier complete content/license audit](botany-003-audit.md#23-wfo-capability-access-and-licensing-evidence)
remains historical evidence. It cannot substitute for the failed current secure acquisition check.

### Fresh secure access evidence

Host curl used normal system TLS, HTTPS-only, 10-second connect/25-second total timeout,
`Range: bytes=0-15`, and a 1,024-byte response limit. It exited **60**, HTTP **000**, downloaded
**0 bytes**, verification error **20**, `unable to get local issuer certificate`. The first sandboxed
attempt could not resolve DNS; the authorized host-network retry established the actual TLS failure.

Isolated existing images, no mounts, read-only root, UID/GID 10001, dropped capabilities and
`no-new-privileges`, used HTTPX 0.28.1 with normal certifi 2026.07.22 verification, redirects disabled
and 10-second connect/20-second other timeouts:

| Image                                | Image ID                                                                  | UTC probe time              | Result                                   |
| ------------------------------------ | ------------------------------------------------------------------------- | --------------------------- | ---------------------------------------- |
| florabase-backend-development:latest | `sha256:c4339cd762412c3942559f23f79869efa4f754b28471e571f6a9f57564fb14b4` | 2026-10-09T12:30:03.979078Z | ConnectError / CERTIFICATE_VERIFY_FAILED |
| florabase-prod-backend:latest        | `sha256:850d83352a9a7a4c281700e1c5f666e0b76489a813fc4c779bf26bc41d4727b0` | 2026-10-09T12:30:20.430974Z | Same failure                             |

The newly built worktree quality development image
`sha256:3e2a3a96518411dafe96c5e185547826dbe7b72d11ca47d916f9893d77a56a2b`
also failed a streamed range request at **2026-10-09T12:33:30.613952Z**, before headers/body.
No service, trust store or operator volume was mounted or changed by these probe containers.

A fresh bounded OpenSSL probe required SNI, hostname checking and `-verify_return_error`.
It exited **1**, showed exactly one leaf certificate, issuer **GeoTrust TLS RSA CA G1**, and fatal
verification error **20 at depth 0**. Leaf dates were 2026-07-14 to 2027-01-28. The observed issuing
intermediate is still absent. Its trailing aborted-session `Verify return code: 0` is not success;
no cipher/session was established. The prior public-root inventory was not repeated in this run.

### Official static alternatives investigated

The [official download page](https://www.worldfloraonline.org/downloadData) advertises a CC0 backbone.
Its indexed metadata links December 2025 DOI 10.5281/zenodo.18007552; that publisher release has a
newer version link to the [June 2026 release](https://zenodo.org/records/20782718), version **2026-06**,
published **2026-06-21**. The current release describes taxonomy/name/classification packages,
JSON/SQL, family DwCA and identifier lookups. It does not establish a Flora of China descriptive
content replacement. This is an inference from the published package descriptions; archive members
were not downloaded/inspected here. No taxonomy-to-description conversion is authorized.

The [publisher's repository](https://github.com/worldflora/wfo-plant-list) concerns the Plant List.
Official resource searches identified the same Flora of China archive. At the time of this initial
re-audit, no alternative licensed, securely usable official machine-readable description artifact
had been established. This bounded search is not a claim that no other flora resource exists anywhere.
No species-page scraping or browser acquisition was used. A later bounded review established the
separate, narrow Kew alternative below and in audit section 35; it does not repair the Flora of China
TLS path or support broad description coverage.

## Origin/distribution: source-field GO; product implementation pending

Provider: Royal Botanic Gardens, Kew. Exact dataset: World Checklist of Vascular Plants **v15**,
published/extracted **6 January 2026**. Fixed official archive:
<https://sftp.kew.org/pub/data-repositories/WCVP/Archive/wcvp_v15.zip>.

- Independent complete verified-HTTPS retrieval: **2026-10-09T12:32:17.250119Z**.
- Bytes: **89,508,082**.
- SHA-256: `693e05b31ea6ce724c88ccf38bb964db2f22424b396f7ed1fd04fdb203af7e81`.
- Three members: README_WCVP.xlsx (17,827 bytes), wcvp_names.csv (298,218,467 bytes),
  wcvp_distribution.csv (141,066,449 bytes). No filesystem extraction.
- Names schema: strict UTF-8, pipe-delimited, no quoting, 31 exact columns. A fresh complete scan
  checked row widths for all **1,441,152** names records. Prior complete uniqueness and distribution
  validation belongs to [the exact v15 audit](native-range-enrichment-source-v15.md).
- Exact field: **wcvp_names.csv.geographic_area**, a separate provider distribution statement.
  Never fabricate it by joining structured ranges, geography names or EXPLORE geometry.
- Exact source taxon identifier: opaque **plant_name_id**, separately confirmed by the operator.
  Existing ENRICHMENT-001 WCVP confirmation can inform a future reviewed reuse; it never authorizes
  GBIF/WFO ID translation or silent text application.
- License: **CC BY 3.0**, established in the repository's exact v15 release/companion metadata
  audit. This run verified identical complete plain-archive bytes; it did not re-download the
  companion DwCA or establish license from a footer.
- Citation: Govaerts R (ed.). 2026. WCVP: World Checklist of Vascular Plants. Facilitated by the
  Royal Botanic Gardens, Kew. URL <https://doi.org/10.34885/rvc3-4d77> [accessed 06 Jan 2026].
  Additionally retain actual retrieval time, release checksum, license URL, no endorsement and
  any deterministic normalization applied.
- Update policy: explicit replacement of a reviewed pinned local snapshot, fresh proposals for
  changed evidence; historical applications remain immutable and canonical text remains unchanged.

Fresh exact record samples:

| plant_name_id | Provider name    | geographic_area          |
| ------------- | ---------------- | ------------------------ |
| 2616153       | Acer palmatum    | SW. Korea, C. & S. Japan |
| 2640812       | Annona cherimola | W. South America         |
| 298116        | Aloe vera        | N. Oman (Hajar Mts.)     |

These name labels identify the sampled source records; they do not establish collection matches.
Life form and climate columns remain reference context, never cultivation instructions.
The existing ENRICHMENT-001 SQLite index omits geographic_area from its taxa table. A future
BOTANY-003 text snapshot/index must retain that exact field separately; do not reopen structured
range ownership or manufacture prose from the index's distribution assertions.

## Description alternative: `DESCRIPTION_SOURCE_GO` for three reviewed records

The follow-up review approved exactly three English general-description records in the official
Kew SEPASAL export, cited to Flora Zambesiaca. The source file is the discontinued static export
at <https://sftp.kew.org/pub/data-repositories/sepasal/data/sepasal_notes_references.csv>,
Last-Modified **2020-09-23 16:12:04 GMT**, retrieved **2026-10-09T13:07:03.610025Z**;
30,762,595 bytes; SHA-256
`5c900968f31382f6afb283aa0dfbb01234f9695576565d4c109a3fadee2a905c`. It has UTF-8 CSV fields
TaxKey, NoteCatKey/NoteCatText, NoteKey, NoteText, BiblKey and bibliography; category 9 is
BOTANICAL DESCRIPTION. The complete source schema, three exact record/text hashes, full four-file
snapshot manifest, joins, language and content exclusions are in [audit section 35](botany-003-audit.md#35-final-bounded-official-source-fallback--2026-10-09).

Kew's README explicitly releases SEPASAL data under **CC BY 4.0**. Preserve Kew's SEPASAL citation,
access time, license link, exact snapshot/record identifiers, and Flora Zambesiaca bibliography
reference 5701. This applies to the selected text as republished in Kew's licensed export, not the
underlying book or other providers. Source-local TaxKey is deterministic inside the snapshot; any
future Florabase association requires an explicit reviewed TaxKey link. No existing collection
identity is inferred or approved by these rows.

**Scope:** TaxKey/NoteKey/BiblKey `78/104262/5701`, `624/98287/5701`, and `1152/98358/5701` only.
This proves a narrow source capability; three records are insufficient coverage for general BOTANY-003
description enrichment. It is not a global provider, an automatic fallback for Flora of China, or
approval for the other 180 category-9 rows. No implementation is authorized by this source decision.
