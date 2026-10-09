# Collection taxonomy tree — original TAXONOMY-003 plan

Historical planning record. TAXONOMY-003 is now implemented for visual/UAT review; the current
[contract](collection-taxonomy.md), [source GO](taxonomy-003-source.md) and
[handoff](taxonomy-003-handoff.md) resolve the questions below. Statements about unavailable code or
unmeasured artifacts describe the original planning audit, not the current implementation.

The complete feature graph was audited on 2026-10-09. **TAXONOMY-001 already owns assisted identity
reconciliation**, and TAXONOMY-002 owns synonyms/name history. Neither owns taxonomy browsing.
The requested educational collection tree therefore uses the next free ID **TAXONOMY-003**;
existing owners retain their contracts. It follows BOTANY-003 in operator direction, with no tree,
source ingestion, routes, UI or database changes implemented here.

Use the product name **Taxonomy**. Existing **Lineage** means explicit collection-record ancestry;
it must keep that meaning. A botanical classification tree does not establish propagation ancestry
or evolutionary relatedness.

## Planned product contract

- Authoritative classification, emphasizing only taxa represented in the collection. Reuse
  EXPLORE-001 All represented / Living / Current / Historical semantics rather than new inferred
  lifecycle rules. Review optional Collection record category filters against EXPLORE-002.
- Higher ranks → family → genus → species, preserving meaningful intermediate ranks. Counts must
  explicitly count distinct BotanicalIdentities, rather than quantities or provider observations.
- Inspect represented identities from family/genus nodes, with BotanicalIdentity breadcrumbs and
  Related in my collection. Exact hierarchy and missing/unlinked states stay visible.
- Confirm provider identity explicitly with provenance; names or GBIF/WCVP/WFO ID equality never
  create links. Source synonyms/accepted taxa remain reference context, not automatic local merges.
- Optional locally provisioned snapshot, bounded queries, accessible responsive tree/list navigation,
  independent of live provider availability and ordinary startup. No identity/profile changes.

## Preferred source candidate: official WFO Taxonomic Backbone / Plant List

The [official WFO download page](https://www.worldfloraonline.org/downloadData) advertises static
CC0 taxonomy. Its referenced [December 2025 release](https://zenodo.org/records/18007552) has a newer
version link to [June 2026](https://zenodo.org/records/20782718), version **2026-06**, published
**21 June 2026**. The latter advertises classification packages, JSON/SQL, family DwCA and identifier
lookups; the publisher describes six-month releases. Its listed artifacts total approximately
2.1 GB; the Catalogue of Life package is 132.6 MB and JSON ZIP 660.5 MB. These are publisher file
sizes, not measured Florabase index footprints. No archive or local tree index was built here.

The [publisher-owned software repository](https://github.com/worldflora/wfo-plant-list) and
release metadata establish a credible candidate, not final source GO. Recheck exact release license
and members before ingestion; the CC0 backbone license never approves unrelated Flora prose.
Retain WFO acknowledgment, release DOI/checksum, retrieval and hierarchy provenance.

Resolve these questions in that increment before implementation:

1. Which exact fields express parent relationships, and what do they mean for names versus accepted
   taxonomic concepts? Inspect actual package schema instead of guessing parentNameUsageID semantics.
2. How are arbitrary intermediate/unranked nodes, cycles, missing parents and deprecated IDs handled?
3. How are accepted/synonym/deduplicated-name records displayed without changing local identities?
4. Which reviewed identity-link mechanism covers WFO? What direct published crosswalk evidence, if
   any, is acceptable? GBIF and WCVP remain different providers.
5. How does one BotanicalIdentity count once across accepted/synonym placement and collection scopes?
6. Which source version/checksum is pinned, how do explicit updates retain prior link provenance,
   and what happens to absent or changed placement?
7. What are measured archive/index disk size, provisioning time, lookup bounds and runtime memory?

## Separate later direction: PHYLOGENY-001

Phylogeny concerns evolutionary relationships, not taxonomic classification. PHYLOGENY-001 is a
separate planned source/product audit. Open Tree of Life is a candidate for future investigation;
its acquisition, licensing, exact tip matching, uncertainty and coverage were not approved here.
No evolutionary branch lengths, MRCA, synthetic tree retrieval or phylogenetic inference belongs
in BOTANY-003 or this taxonomy plan. A later feature must review those semantics independently.
