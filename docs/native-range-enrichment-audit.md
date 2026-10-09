# Future structured native-range enrichment: Kew candidate audit

Historical planning audit, 2026-10-08. No provider import, taxon link, crosswalk, provenance schema,
proposal service or range mutation is implemented by EXPLORE-002.

## Official Kew evidence

Kew's [WCVP description](https://powo.science.kew.org/about-wcvp) describes an expert-reviewed
accepted-name backbone based on IPNI nomenclature, used by POWO. Its geographical-distribution
section distinguishes native from introduced wild distribution and supplies narrative and
structured **TDWG level 3** regions. Natural colonisation belongs to native distribution;
human introduction includes naturalised populations. Uncertainty and extinction markers need
an explicit future handling policy. These statements establish a promising source, not an
approved Florabase import contract.

The official [download index](https://sftp.kew.org/pub/data-repositories/WCVP/) currently exposes
`wcvp.zip` and `wcvp_dwca.zip`, both about 84 MB, with 2026-06-04 modification timestamps.
The [official archive](https://sftp.kew.org/pub/data-repositories/WCVP/Archive/) exposes versioned
plain and Darwin Core archives v10–v15; v15 entries are dated 2026-01-07. An index timestamp is
not a verified dataset release/version. No archive was imported or its full contents validated.

Kew's [citation guidance](https://powo.science.kew.org/cite-us) directs users of names, taxonomy,
maps and distributions to WCVP and the downloaded version's README citation. Its v13/2024 example
must not be treated as the current release identifier. Before source approval, inspect the exact
chosen archive's README, schema, version, licensing/terms and citation; retain its official URL,
checksum and retrieval time. Prefer that official downloadable dataset, or a separately documented
supported API, over scraping POWO pages. This audit does not establish a supported public API.

## Intended separately reviewed workflow

Trusted provider → exact/reviewed taxon match → native TDWG assertions → reviewed explicit
TDWG-to-Florabase GeographicPlace crosswalk → proposed changes → operator review → Apply →
structured BotanicalProfileNativeRange plus retained source provenance.

Four decisions blocked implementation at that planning checkpoint:

1. **Taxon identity:** establish a stable, reviewed WCVP/POWO identifier and accepted-taxon
   relationship. Scientific-name equality, a GBIF/CoL link or a synonym alone cannot authorise import.
2. **Geography:** TDWG units are not Florabase ISO 3166/UN M49 units. Review an explicit, versioned
   crosswalk, including splits, partial overlaps, unresolved units and uncertainty. No fuzzy/name
   matching, silent rounding to a country, or inferred finer native assertions.
3. **Provenance:** the current range relationship stores only profile/place IDs. A future approved
   schema must retain provider, exact taxon, source/version, original TDWG assertion, crosswalk
   version, retrieval and application evidence. Rendering geometry does not supply provenance.
4. **Replacement:** review add/replace/remove proposals against current operator-authored ranges,
   with explicit Apply and concurrent-change revalidation. Opening, fetching or refreshing cannot
   silently overwrite or remove ranges. Native and Introduced assertions must stay distinct.

Natural Earth supplies drawing polygons only. Kew distribution remains botanical reference
knowledge; it never supplies a collection record's origin or ProvenanceSite.

## Feature graph ownership and sequence

The complete 95-feature graph was audited before choosing an owner: BOTANY-002 owns advisory
external taxon links; BOTANY-003's approved WFO/Kew two-field **text** enrichment contract leaves
structured ranges unchanged and remains blocked; GEOGRAPHY-002 owns structured ranges;
EXPLORE-002 reads them; planned ENRICHMENT-001 already owns reviewable profile proposals;
ENRICHMENT-002 owns later automated refresh. Reuse/refine **ENRICHMENT-001**, with this narrow
structured-range candidate, rather than creating a duplicate ID or bypassing BOTANY-003.

ENRICHMENT-001 remains **planned**. Consider this candidate immediately after successful
EXPLORE-002 delivery, before SCHEDULE-001 unless the operator reprioritises. Provider approval,
exact scope, crosswalk policy, migration/provenance design and proposal semantics require their
own reviewed increment; this planning entry authorises no implementation.


## 2026-10-09 — exact source approved and narrow increment implemented

ENRICHMENT-001 now implements structured ranges only. The exact official version-15 plain archive
and its full row schemas were inspected, with DOI/companion metadata confirming CC BY 3.0.
[Source approval](native-range-enrichment-source-v15.md) records checksum, citation, retrieval,
licence evidence and row-quality results. The earlier planning statements above are historical.

The [implemented contract](native-range-enrichment.md) resolves taxon review with an explicit
operator-confirmed WCVP ID, a deliberately small reviewed twelve-unit crosswalk, visible excluded
splits/partial/unresolved units, unqualified Native assertions only, durable frozen proposals and
immutable applications. Apply adds only selected mapped ranges and keeps all current ranges.
Removal/replacement is not supported. Frozen v15 evidence can be applied without the optional
index after durable link/identity/destination/crosswalk revalidation. This feature does not change
BOTANY-003's blocked text contract or implement ENRICHMENT-002 automated refresh.

Status is **verified** after operator UAT and the independent canonical gate; see the
[handoff](enrichment-001-handoff.md). SCHEDULE-001 stays future work and the broad
cross-application product/visual review remains deferred before release hardening.
