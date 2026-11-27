# Cultivation, uses and warnings source discovery — 2026-10-09

These fields remain **operator-authored**. This separate discovery does not add a source to the
approved BOTANY-003 two-field import contract. BOTANY-004 records the future review work.

## Kew SEPASAL: credible static candidate, no production import GO yet

The official [SEPASAL README](https://sftp.kew.org/pub/data-repositories/sepasal/README.txt)
identifies a discontinued dryland economic-botany database, a static CSV/SQL export, **CC BY 4.0**,
source-local **TaxKey** and bibliographic joins. It reports 6,988 taxa, 28,220 uses and 4,951
publications. It includes cultivation details as well as ecological information. This is distinct
from POWO presentation and from WCVP life-form/climate columns. Its stated license covers SEPASAL
data, not unrestricted copying of the full underlying books.

Retain this citation, actual retrieval time, exact file/checksum, note/use ID and bibliography:
Royal Botanic Gardens, Kew (1999). Survey of Economic Plants for Arid and Semi-Arid Lands (SEPASAL)
database. Published on <https://sftp.kew.org/pub/data-repositories/sepasal/> [accessed date/time].

Three official CSVs were independently retrieved completely over normally verified HTTPS with
redirects refused and a 40 MB bound per file. Strict UTF-8 CSV parsing rejected malformed row widths.
This establishes acquisition and inspectable data, not complete import correctness or horticultural
suitability. Data was used only for the audit; no source index or production ingestion was added.

| File under official /sepasal/data/ | UTC retrieval, 2026-10-09 |      Bytes | SHA-256                                                            | Rows / distinct TaxKey |
| ---------------------------------- | ------------------------- | ---------: | ------------------------------------------------------------------ | ---------------------- |
| sepasal_taxa.csv                   | 12:34:29.201809           |  1,443,583 | `90914f2926b6c4dac8bd290ad60c86c95d8e21fb0e888494f0b4ee9fdd640e4c` | 17,853 / 6,988         |
| sepasal_uses_major_references.csv  | 12:34:30.022896           |    822,607 | `894f4537adfd93255f5485fa2ba1e2644e6326df1843baf6bb1d5b1fb533397e` | 3,080 / 1,032          |
| sepasal_notes_references.csv       | 12:34:36.139813           | 30,762,595 | `5c900968f31382f6afb283aa0dfbb01234f9695576565d4c109a3fadee2a905c` | 94,084 / 3,398         |

Observed schema: taxa carry TaxKey, name-component keys, rank/authorship and NamAccLink; one TaxKey
can have multiple name rows. Major-use evidence carries TaxKey, Use12Key and category levels plus
BiblKey and bibliographic fields. Notes carry TaxKey, NoteCatKey/NoteCatText, NoteKey, NoteText,
BiblKey and author/year/title/publisher/language. A generic unique-TaxKey rule would discard valid
synonym/reference rows. Source-local IDs must be reviewed directly; they are not WFO/WCVP/GBIF IDs.

| Destination | Actual machine evidence                                                                                               | Current decision / remaining source review                                                                                                                                                                                                                                         |
| ----------- | --------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| cultivation | notes category CULTIVATION; observed TaxKey 46, NoteKey 9008, BiblKey 1159, a horticultural reference                 | Promising semantic/acquisition/license candidate. Before import GO, review dated/reference-specific advice, target climate/context, coverage, length/markup, all joins and exact reviewed taxon selection. Never select climate/habitat/distribution notes as advice.              |
| uses        | Food, medicines, materials, environmental uses and other distinct major-use categories; source/reference IDs included | Promising candidate. Categories are structured facts rather than canonical narrative text. Approve an exact source-specific text representation or individual eligible notes first; preserve references and reported traditional-use context, with no synthesis or medical advice. |
| warnings    | explicit TOXICITY/POISONOUS COMPOUNDS notes; observed TaxKey 25, NoteKey 19853, BiblKey 549                           | Higher-risk NO-GO for now: historical locality-specific reports require statement-level authority/context and exact taxon review. Poison-use categories and medicines-for-poisonings are different concepts. No general safety boolean or completeness claim.                      |

Versioning is a dated checksum snapshot; directory modification dates are not releases or verified
freshness. Updates must be explicit, reviewed and source-specific. Remaining checks include all
reference/name relationships, supported languages, duplicate note/reference identity, content bounds,
rights notices, exact acceptance/synonym treatment and a read-only local index. No automatic name
crosswalk, one-text-per-TaxKey concatenation, generic note importer or historical-truth assertion is
approved. The medicinal subset contains large separate files and was not downloaded or validated.

## Other authoritative discovery

[Kew's Economic Botany collection access page](https://www.kew.org/science/engage/accessing-our-science/access-our-collections/economic-botany-collection)
provides a searchable specimen collection. A compatible versioned taxon-level narrative export and
its reuse license were not established; artifact uses are not universal taxon advice.

The [official Economic Botany Bibliographic Database export](https://sftp.kew.org/pub/data-repositories/bibliographies/README.txt)
is static CSV under CC BY 4.0, but contains citations rather than usable profile statements. Its
README warns of inconsistent older citations. It can inform research, not silently populate uses.

[Poison Control's plant reference](https://www.poison.org/articles/plant) has useful clinical context,
but no licensed machine-readable exact-taxon warning export was established here. Some entries are
at genus level. Public visibility does not license scraping or justify a safety claim.

The earlier approved audit's POWO/UPFC findings remain historical, contributor-specific evidence;
no fresh export/license GO was established for UPFC here. WFO's CC0 taxonomy and portal footer
cannot approve every contributor's narrative. No suitable RHS machine export/license was established
by the bounded search. This is not a claim that such horticultural datasets cannot exist.

All three sections stay manual. A future BOTANY-004 source GO must retain exact source-specific
values and field provenance, followed by operator review/selective Apply and stale safety.
Absence of an imported warning never means confirmed safety. No additional profile schema is planned
merely because these exports also contain habitat, physiology or traits.
