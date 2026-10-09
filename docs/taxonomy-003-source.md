# TAXONOMY-003 source decision — WFO 2026-06

SOURCE GO, reviewed 9 October 2026 before production implementation. Classification only.

Official [release](https://zenodo.org/records/20782718), DOI `10.5281/zenodo.20782718`,
World Flora Online Plant List **2026-06**, published **21 June 2026**. Secure host curl retrieved
release API metadata and the complete [ColDP archive](https://zenodo.org/api/records/20782718/files/wfo_plantlist_2026-06.zip/content).
Archive: **132,643,291 bytes**, retrieved **2026-10-09T14:48:29Z**; SHA-256
`75f1ad1f371978c9e46f3044152c07ed276fe57be9fb9a15b3621b19cf231987`.
Measured MD5 `02f989b01b8eb142ec5934bd634b3876` matches release metadata.
Zenodo version is `2026-06`; embedded metadata version is `2026-06 01`, issued `2026-06-21`.
Both independently specify **CC0**. [CC0 notice](https://creativecommons.org/publicdomain/zero/1.0/).
Acknowledge World Flora Online; retain release DOI, retrieval, license and checksum. Embedded citation
identifies World Flora Online (2026), World Flora Online Plant List 2026-06, World Flora Online,
with its editors and concept DOI `10.5281/zenodo.7460141`; release DOI above disambiguates bytes.
No images, descriptive prose, traits or source content license is inherited from this taxonomy GO.

## Actual schema and full scan

Six regular ZIP members, streamed without extraction:

| Member           | Uncompressed bytes |
| ---------------- | -----------------: |
| name.tsv         |        380,612,911 |
| taxon.tsv        |         96,789,455 |
| synonym.tsv      |        121,225,634 |
| reference.tsv    |        321,277,092 |
| typematerial.tsv |         55,447,515 |
| metadata.json    |            109,295 |

The publisher uses quoted tab-delimited UTF-8 in this artifact. Full strict decoding/width scans
of the three classification tables found **1,663,770 names**, **454,688 accepted concepts** and
**1,026,322 synonym usages**. Unique name/taxon/synonym IDs; unique synonym name references;
all taxon name references and synonym accepted/name references resolve. Taxon ID equals its
accepted name ID in this exact release. Bare names have no classified usage; do not place them.
`name.tsv`: `ID`, `scientificName`, `authorship`, `rank` supply names, not name-string hierarchy.
`taxon.tsv`: `ID`, `nameID`, `parentID` supply accepted concepts and direct classification parents.
`synonym.tsv`: `ID`, `nameID`, `taxonID` associate a synonymous name with its accepted concept.
The [ColDP specification](https://github.com/CatalogueOfLife/coldp/blob/master/README.md)
defines these relationships separately. Synonyms are advisory attachments to accepted classification,
never taxonomic child edges, local renames or canonical name history.

Preserve all 29 observed ranks, including subclass, superorder, suborder, subfamily, tribe,
subtribe, supertribe, subgenus, section, subsection, series, subseries, infraspecific ranks,
prole, lusus, convar and unranked. No rank sorting reconstructs parentage.

## Reviewed non-taxonomic root boundary

The full parent scan found exactly one external reference:
`Plantae / wfo-4100001250 → wfo-9971000003`. No self-parent or cycles.
The [official publisher exporter](https://github.com/worldflora/wfo-backbone-management/blob/main/scripts/gen_coldp.php)
explicitly excludes database root 1, described as the **code** name (lines 119/154), but exports
its parent reference (349–351). Its taxonomic source walk stops at rank code (287–288).
The [official JSON exporter](https://github.com/worldflora/wfo-backbone-management/blob/main/scripts/gen_plant_list.php)
also stops classification ancestry at code (329–330). This is an organizational nomenclatural-code
container, not a botanical ancestor. No HTML species page was acquired or scraped.

Approved exact boundary: retain the raw Plantae parent ID as provenance; terminate biological
classification at this exact kingdom node. Do not invent a Code taxon, delete arbitrary parents,
or guess roots by rank/name. Every other missing parent fails validation. The root ID/name/rank
and external-parent tuple are pinned with the archive. A changed tuple requires a new source audit.
All accepted concepts must reach this boundary; disconnected/orphan graphs fail closed.

## Identity and runtime boundary

Confirm literal WFO name IDs after local candidate/name/authorship/rank/status/path inspection.
GBIF/WCVP IDs and similar names never establish a WFO link. A linked synonym retains its literal
ID and accepted relationship while its collection placement follows the reviewed accepted concept.
Names with no classified usage cannot be confirmed for placement. Local identities remain unchanged.

Provision an optional ignored SQLite index explicitly from the pinned archive. Runtime uses indexed
local reads and set-based ancestor traversal, never network or full-source serialization. PostgreSQL
stores only operator-confirmed links and their release/identity/path review evidence. Reprovisioning
cannot reinterpret links from another release; explicit review is required. Missing/corrupt source
is optional and must leave app startup and canonical collection/reference data usable.
