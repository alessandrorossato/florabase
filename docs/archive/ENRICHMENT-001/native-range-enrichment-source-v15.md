# ENRICHMENT-001 source decision: WCVP v15

Source GO, reviewed 2026-10-09 before provider implementation. This approval covers structured
distribution only. It does not change BOTANY-003's text contract.

## Exact release and acquisition evidence

- Provider: Royal Botanic Gardens, Kew, World Checklist of Vascular Plants (WCVP).
- Official archive: <https://sftp.kew.org/pub/data-repositories/WCVP/Archive/wcvp_v15.zip>.
- README: `README_WCVP.xlsx`, sheet `README`, A7/A8: version 15, extracted 6 January 2026.
- Retrieved completely: **2026-10-09T06:16:20.117071Z** over verified HTTPS.
- Archive size: **89,508,082 bytes**.
- SHA-256: `693e05b31ea6ce724c88ccf38bb964db2f22424b396f7ed1fd04fdb203af7e81`.
- Official release record, reached through the README DOI:
  <https://kew.iro.bl.uk/entities/product/2b0078f6-c4fe-45b4-a654-8666fd3d9b38>.
  This explicitly identifies version 15, publication 6 January 2026, and **CC BY 3.0**.
- Licence confirmation in the companion official
  <https://sftp.kew.org/pub/data-repositories/WCVP/Archive/wcvp_dwca_v15.zip>:
  `eml.xml` intellectualRights identifies CC BY 3.0 Unported;
  `meta.xml` distribution-extension defaults identify the same licence and Kew rights holder.
  Companion SHA-256: `30398c912d3322b513876f99e8e32db33ce50aa79fdeb0e550be7d09091d808a`.
  Its metadata identifies version 15.0 and publication 2026-01-06.
- The plain README itself contains no licence statement. Release-specific repository and companion
  metadata establish it; neither the website footer nor an older release citation is used as proof.

README A4 citation (retain with proposals/applications):

> Govaerts R (ed.). 2026. WCVP: World Checklist of Vascular Plants. Facilitated by the Royal Botanic
> Gardens, Kew. [WWW document] URL https://doi.org/10.34885/rvc3-4d77 [accessed 06 Jan 2026].

Florabase must additionally identify its actual retrieval date, transformations and crosswalk.
[Kew Science terms](https://www.kew.org/science/collections-and-resources/data-and-digital/terms-of-use)
require attribution, no endorsement implication and disclosure that Kew cannot warrant accuracy.
Licence URI: <https://creativecommons.org/licenses/by/3.0/>. No images or narratives are imported.
Kew's [citation page](https://powo.science.kew.org/cite-us) explicitly defers to the downloaded
version's README; its v13 example is not this release. Directory timestamps are not version evidence.

## Archive/schema inspection

Exactly three regular members, no directory extraction required:

| Member | Uncompressed bytes | Rows excluding header |
| --- | ---: | ---: |
| README_WCVP.xlsx | 17,827 | n/a |
| wcvp_names.csv | 298,218,467 | 1,441,152 |
| wcvp_distribution.csv | 141,066,449 | 1,986,879 |

Both CSVs are strict UTF-8, pipe-delimited, with **no quoting** (README D10/D11, D46/D47).
A complete streaming inspection found no malformed-width rows and no duplicate `plant_name_id`
or `plant_locality_id`. Names contain 31 fields; distributions contain 11 fields. The README's
legacy `checklist_names.txt` / `checklist_distribution.txt` headings refer to these actual CSVs.

Identity fields: `plant_name_id` is the opaque WCVP identifier, `taxon_name`, `taxon_authors`,
`taxon_rank`, `taxon_status`, `accepted_plant_name_id`, `powo_id`, `reviewed`. Accepted names
self-reference their accepted ID. IPNI/POWO identifiers are separate; GBIF/CoL IDs are not crosswalks.
Preserve unexpected/nonaccepted ranks/statuses as context and reject them for linking/applying.
`reviewed` describes family peer review, not operator match confirmation.

Distribution fields: `plant_locality_id`, `plant_name_id`, `continent_code_l1`, `continent`,
`region_code_l2`, `region`, `area_code_l3`, `area`, `introduced`, `extinct`, `location_doubtful`.
README A58:D60 explicitly defines 0/1 flags: introduced=0 means native, extinct=1 means local
extinction, doubtful=1 means doubtful presence. Only **0/0/0** can propose a canonical addition.
Introduced records (237,134), extinct records (2,781) and doubtful records (2,503) retain their
original evidence and are context only. Blank and lowercase area codes occur; no automatic
uppercasing or guessing is permitted. Missing/unknown units remain unresolved.

Kew's [distribution documentation](https://powo.science.kew.org/about-wcvp) defines TDWG level 3
and explains naturalisation, question marks and extinction daggers. Those narrative conventions
are not parsed as substitutes for the CSV flags. There is no separate extinct-in-the-wild flag
in this CSV and no authority to invent one. Native status is never derived from occurrences.

## Source boundary

Pin this exact archive and schema, build a replaceable indexed local snapshot explicitly, and
reject checksum/schema changes. Ordinary startup and page navigation require no provider network.
Only an explicit reviewed taxon link can produce a proposal. A proposal freezes version 15
evidence; later source releases cannot silently alter it. The TDWG crosswalk and atomic Apply
contract require their own documented implementation review. No supported Kew API was established.
