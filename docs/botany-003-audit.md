# BOTANY-003 controlled enrichment audit

Audit, investigation and implementation access-check date: 2026-10-02.
Source-capability decision: **APPROVED**. Current outcome: `SOURCE_TLS_PROVIDER_BLOCKED`.

Sections 1–21 preserve the initial adapter audit. Sections 22–30 record the subsequently authorized
source investigation and supersede its request for investigation authorization.
Sections 31–32 record the operator's approved scope/replacement policy and the failed backend
access prerequisite. The source choice has not been reopened or discarded.
Section 33 diagnoses that prerequisite: the observed WFO TLS endpoint omits its issuing intermediate,
while the required public root is already present in the host and both backend images.

The existing provider adapter supplies taxonomy and match diagnostics, but no content with a safe
mapping to BotanicalProfile. Implementing selected apply now would require inventing a mapping,
adding unrequested domain fields, or introducing an unreviewed source. This audit does not claim that
GBIF or Catalogue of Life can never supply descriptive content; it establishes the capability of the
current Florabase adapter/cache contract. No new provider capability was tested live during the initial audit; the subsequent live
source investigation is recorded below.

## 1. Worktree, branch and base

- Worktree: `/home/alessandro/.codex/worktrees/b4a3/florabase`.
- Branch: `feat/botany-003-controlled-enrichment`, attached through `make feature-init`.
- Base: `cd29de9297415add8eb21635181fd5c94020d3d5`, equal to cached `origin/main` and primary `main`
  at initialization. Initialization performs no fetch; remote freshness was not independently checked.
- Initial source was clean. The primary checkout was not switched or modified.

## 2. BOTANY-002 architecture discovered

`external_botany/provider.py` implements one backend-owned GBIF adapter. It uses
`/v2/species/match` with the Catalogue of Life XR checklist key
`7ddf754f-d193-4cc9-b351-99906754a03b`. There is no separately implemented CoL/ChecklistBank
content adapter or multi-provider merge mechanism.

An accepted operator match is an `ExternalTaxonLink`; this is distinct from the provider's taxonomic
status `ACCEPTED`. The database permits one current link per identity/provider. External IDs remain
opaque strings. Confirmation and refresh submit the selected provider scientific name to the matcher
and require the response's exact external ID; enrichment must not add another rematch or crosswalk.

`ExternalProviderCache` has composite key `(provider, resource_key)`, raw JSONB payload and UTC
`fetched_at`. Search keys hash a normalized query; taxon keys hash external ID plus normalized provider
name. Cache entries are independent of links. The default TTL is 86,400 seconds. `TaxonCandidate`
normalizes usage, accepted usage, classification and diagnostics; the frontend receives typed
responses, not raw provider JSON.

## 3. Enrichment matrix

Classification applies to importing into the **existing BotanicalProfile**:

- A: safe direct enrichment.
- B: requires deterministic normalization into an existing compatible destination.
- C: informational only.
- D: unsupported or ambiguous.

| Provider/cache field or category                                           | Class | Existing destination and decision                                                                       |
| -------------------------------------------------------------------------- | ----- | ------------------------------------------------------------------------------------------------------- |
| Scientific name and canonical name                                         | C     | Local scientific name belongs to BotanicalIdentity; external names remain advisory.                     |
| Authorship                                                                 | C     | No matching profile field. Do not synthesize a description from taxonomy.                               |
| Taxonomic rank                                                             | C     | No matching profile field; taxonomic changes remain external reference information.                     |
| Family and genus                                                           | C     | No matching profile field; no local taxonomic placement correction.                                     |
| Kingdom, phylum, class and order                                           | C     | External classification only; no matching profile field.                                                |
| Taxonomic status                                                           | C     | External status only; never an identity lifecycle or profile warning.                                   |
| Accepted taxon ID/name and synonym context                                 | C     | Explain provider taxonomy; do not substitute the locally linked identity.                               |
| Provider ID, external taxon ID, checklist key, fixed provider URL          | C     | Link/source context; never profile narrative content.                                                   |
| Match type, confidence, issues and alternatives                            | C     | Advisory matching diagnostics; not botanical knowledge.                                                 |
| Link time, successful fetch time, attempt time, stale state, refresh error | C     | Retrieval/operational context; not profile content.                                                     |
| Raw name parts, nomenclatural code, formatted name, classification keys    | C     | Taxonomy metadata, some retained only in raw cache; never render provider HTML.                         |
| Raw additional status, such as conservation status                         | D     | Not normalized by the adapter; no reviewed mapping to general profile warnings or attribution contract. |
| Life form / habit                                                          | D     | Not exposed by the implemented matcher normalization; no dedicated profile field.                       |
| Description                                                                | D     | Compatible local section exists, but the current adapter supplies no descriptive-content contract.      |
| Origin/distribution narrative                                              | D     | Compatible local section exists, but the current adapter supplies no such facts.                        |
| Cultivation, uses and warnings narratives                                  | D     | Compatible local sections exist, but the current adapter supplies no such facts.                        |
| Structured native ranges / provider distribution geography                 | D     | No native-status geography in the current contract and no provider-place mapping.                       |
| Occurrence counts, coordinates and density tiles                           | C     | Observations do not establish native range; MAP-002 remains separate.                                   |
| Unknown or malformed raw properties                                        | D     | No generic raw-payload importer or guessed mapping.                                                     |

There are **zero A or B writable mappings**. Existing normalization of taxonomic strings does not
make them compatible with a curated narrative section. The current official
[GBIF taxonomy contract](https://techdocs.gbif.org/en/data-processing/taxonomy-interpretation)
documents usage, classification and matching diagnostics; it does not establish a reviewed mapping
from those facts into Florabase's five narrative sections.

## 4. Model/schema changes

None. BotanicalIdentity owns scientific, cultivar and common names, plus creation/update timestamps.
BotanicalProfile owns only `description`, `origin_distribution`, `cultivation`, `uses`, `warnings`
and its native-range relationships. Text sections are optional plain text, limited to 20,000
characters, with existing whitespace/newline and control-character validation.

## 5. Normalized proposal design

Not implemented. No writable proposal can be derived from the current accepted link and cache.
An empty or informational-only preview/apply scaffold would not deliver the requested enrichment
workflow. Provider interpretation must remain backend-owned when an eligible source is selected.

## 6. Explicit apply semantics

Not implemented. No generic replacement or taxonomy-to-description conversion was added. Selected
apply and non-selected preservation regressions require actual supported proposal fields first.

## 7. Stale/concurrency protection

No enrichment concurrency contract was introduced. Profiles currently have no revision timestamp or
version token. Ordinary nonempty profile PUT uses a PostgreSQL upsert; empty PUT and native-range
changes use row locks. Links/caches use unique constraints and upserts for concurrent creation.
These mechanisms do not by themselves provide the required preview/apply precondition.

CSV import has session-bound signed preview content, but does not establish botanical profile/cache
version semantics. A later implementation must cover ordinary profile edits, profile creation and
deletion, link replacement/unlink, cache refresh and racing applies within the transaction; adding
a check only to the enrichment path would be insufficient.

## 8. BotanicalIdentity protection

No identity, name, lineage, collection provenance or taxonomy mutation was added. Existing external
source UI displays source taxonomy separately, including accepted-name differences.

## 9. BotanicalProfile creation semantics

Existing semantics remain: a profile exists only while it owns text or structured native ranges.
Revision `20260909_0022` enforces this with deferred constraint triggers. The first range can create
a profile atomically; clearing text preserves a range-only profile; removing the last range removes
an otherwise empty profile. Link viewing, matching and refresh do not call profile creation.

## 10. Native-range behavior

No import mapping is available. GeographicPlace uses an explicit CLDR-derived canonical hierarchy
and custom places; native ranges identify exact selected UUIDs. Existing parent and child selections
can coexist, with no inferred ancestor/descendant additions. The composite range primary key prevents
duplicate exact-place relationships. Occurrences were not repurposed as native-range evidence.

## 11. Provenance/explainability

Links already retain provider/external IDs, normalized source taxonomy and link/fetch/attempt times.
Caches retain raw response/fetch time. Neither stores a durable record of which profile values were
imported; link replacement, unlink and cache replacement mean those records alone would not explain
historical enrichment. A receipt decision remains dependent on the approved source/content contract;
no generic audit framework or raw-payload duplication was added.

## 12. Refresh semantics

Refresh explicitly forces the provider request. Success replaces cache payload/fetch time and updates
normalized external link data. Provider failure retains usable cached data and existing link facts,
recording the refresh error/attempt. Cache persistence precedes taxon normalization; malformed or
different-ID responses cannot be assumed to preserve the prior cache in every path. This distinction
needs consideration in any future proposal precondition. No refresh mutates curated profile fields.

## 13. Frontend UX

Audited BotanicalIdentityScreen, BotanicalProfilePanel, ExternalBotanicalDataPanel,
BotanicalNativeRangeManager and their APIs/tests. Reference navigation mounts separate Profile,
Native range, Botanical source and Occurrences modules. Profile edit and range management are explicit;
source search/confirmation, refresh, replacement and unlink are distinct operations.

No enrichment UI was added. No established safe-empty-field preselection convention was found in
these components. That choice is deferred until there are actual importable values; it is not the
present blocker. Normal source rendering reads the local link; provider refresh and occurrence loads
remain explicit.

## 14. Migrations

None added. Audited profile, external-link/cache and native-range migrations and their tests.
Alembic head remains `20261002_0030` (confirmed by the isolated database upgrade).

## 15–17. Tests and checks

Baseline evidence is recorded in `progress.md`. These are existing-behavior checks, not evidence of
an implemented enrichment feature. No enrichment tests, generated API artifacts, application code,
runtime dependencies or schema were changed. No canonical gate, Feature Review acceptance, commit,
push, delivery, merge or finish was performed.

## 18–19. Documentation and changed files

Only `docs/botany-003-audit.md` and `docs/progress.md` changed. `docs/features.json` keeps BOTANY-003
`planned`. The existing roadmap already requires a reviewed content, source and provenance contract
before enrichment resumes; this audit makes the current mapping gap explicit.

## 20. Unsupported/informational fields

The matrix lists the supported normalized taxonomy, raw taxonomy metadata, absent narrative/native
facts and separate occurrence data. No provider-wide authority, HTML importer, source discovery,
numeric ID translation or cross-provider merge was introduced.

## 21. Required product decision

Select an approved source/content/provenance contract that can supply at least one existing profile
section from an accepted external link, with an example exact linked taxon and eligible content;
alternatively explicitly authorize a bounded source-capability investigation to establish that
contract. Required evidence includes retrieval addressing, content semantics, source attribution,
licensing and field-level mapping. No new profile fields or synthetic taxonomy narratives should be
introduced just to create a writable proposal.

Initial audit outcome: `NEEDS_PRODUCT_DECISION`; the operator subsequently authorized the investigation below.

## 22. Source decision and bounded responsibility recommendation

Recommend **C: both sources, with non-overlapping responsibilities**, restricted to the two
dataset elements demonstrated below:

| Responsibility              | Precisely bounded recommendation                                                                                                                                                                                                                  |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Existing GBIF/CoL adapter   | Taxonomy, explicit match confirmation and reference information only.                                                                                                                                                                             |
| WFO                         | Flora of China description extension, English `general` text with an exact WFO taxon ID, source-reference join and effective CC BY 4.0/MBG metadata, from the inspected structured archive snapshot. Propose only `BotanicalProfile.description`. |
| Kew WCVP                    | `wcvp_names.csv.geographic_area` from an identified, licensed WCVP release. Propose only `BotanicalProfile.origin_distribution`, preserving the provider's generalized distribution statement.                                                    |
| Structured native ranges    | Informational/unmapped. No automatic `BotanicalNativeRange` additions.                                                                                                                                                                            |
| Other narratives and traits | No cultivation, uses or warnings import; no taxonomy-to-narrative synthesis.                                                                                                                                                                      |

This recommends capability eligibility, **not permission to implement or import now**. The operator
must accept the WFO archive's weaker publication contract, choose this subset, and authorize the
small durable attribution extension and exact source-link contract before implementation resumes.
The WFO recommendation is for structured snapshot consumption, not a claimed supported live content
API. A source field without established licensing, attribution, addressing or compatible semantics
remains ineligible. Coverage is neither universal nor guaranteed for every linked species.

No third botanical provider was investigated. The two sources demonstrate two existing narrative
destinations; cultivation/uses/warnings remain explicit deferrals. Expanding the survey is unnecessary
for this bounded source choice. Flora of China and the other contributors discussed below were
examined as WFO/POWO content provenance, not as independent integrations.

## 23. WFO capability, access and licensing evidence

The [WFO terms](https://www.worldfloraonline.org/termsOfUse) distinguish CC0 taxonomy from
content-element licenses and require acknowledgement of both the original source and WFO.
The [download page](https://www.worldfloraonline.org/downloadData) offers the CC0 taxonomic
backbone; it does not establish a licensed descriptive-content export. The publisher's
[Plant List repository](https://github.com/worldflora/wfo-plant-list) documents taxonomy/name
services; these are not proof of a description API. The
[WFO technical paper](https://onlinelibrary.wiley.com/doi/10.1002/tax.12373) describes a content
API historically, but a current supported descriptive API contract was not established here.

The live [Flora of China organisation](https://www.worldfloraonline.org/organisation/Flora%20of%20China%20%40%20efloras.org)
points to [resource 33516](https://www.worldfloraonline.org/resource/33516). That resource identifies
an HTTPS Darwin Core Archive, a completed harvest on 2026-08-03 and annual harvesting. Its configuration
imports descriptions/references and skips distributions. The
[published archive](https://files.worldfloraonline.org/files/eFloras/Flora_Of_China/Flora_Of_China.zip)
was actually downloaded and inspected. It contains `classification.txt`, `description.txt`,
`reference.txt`, `image.txt` and `meta.xml`. Exact WFO IDs for both example taxa occur in the core
and description/reference extensions. No website text was scraped to build these samples.

**Access classification: PUBLIC STRUCTURED BUT WEAKLY DOCUMENTED.** The archive is publicly
identified by the provider and machine-readable, but its exposed documentation is a harvesting
resource, not a promised consumer API/SLA or immutable release service. This is sufficient evidence
to propose a pinned structured-data subset for product approval; it is not evidence of supported
continuous API access. The changing URL must not substitute for a retained snapshot fingerprint.
Public portal narratives alone are **HTML-ONLY evidence** where no structured source was inspected.
No internal endpoint is approved. The resource's private harvester address was not accessed.

Observed Description schema (indices in `meta.xml`): taxon ID 0; description 1; type 2; source 3;
language 4; created 5; contributor 7; audience 8; license 9; rights holder 10; rights 11.
Description source joins exactly to Reference identifier index 1 for the same taxon; references
carry bibliographic citation and original URL. For both examples the row-level rights/license values
are empty and the schema supplies explicit defaults: CC BY 4.0, rights holder/rights Missouri
Botanical Garden. These defaults agree with the element-specific portal provenance. Overrides must
take precedence in any later parser; a missing effective license must reject the element.

CC BY 4.0 permits verbatim copying, redistribution and adaptation, including commercial use; it
has no NC or SA condition. Required credit, license link, supplied notices and modification indication
must accompany reuse. Retain Flora of China, MBG/Harvard reference, original URL and WFO acknowledgement
per imported value. See the [license deed](https://creativecommons.org/licenses/by/4.0/).
AGPL application code does not replace this data license: imported material must retain its own
notices and permissions in display/export/redistribution. No additional restrictions on that material
should be implied by the application's code license.

Other elements cannot inherit this approval: on the inspected WFO records WCVP and assembled
distribution contributors are marked All Rights Reserved; Global Tree Search traits are CC BY-NC-ND
4.0; Annona images are CC BY-NC-ND 3.0; Flore du Gabon descriptions are All Rights Reserved.
Some other flora descriptions are CC BY 4.0, but no corresponding structured artifact was inspected
or approved. Neither WFO's CC0 backbone nor its default footer overrides these notices.

## 24. POWO/WCVP capability, access and licensing evidence

[POWO documentation](https://powo.science.kew.org/about) separates contributor content from WCVP
taxonomy/distributions and advertises a structured WCVP download. The
[WCVP account](https://powo.science.kew.org/about-wcvp) distinguishes native from introduced
wild populations; merely cultivated, non-self-reproducing plants are not introduced distributions.
The [official download directory](https://sftp.kew.org/pub/data-repositories/WCVP/) supplies
`wcvp.zip` and `wcvp_dwca.zip`. This investigation downloaded `wcvp.zip`, not the alternative DwCA.

**WCVP download: SUPPORTED CONTRACT.** The inspected release has pipe-delimited UTF-8 names and
distribution CSVs plus `README_WCVP.xlsx`, version 16, extracted 2026-06-04. README terminology
still refers to earlier `checklist_*.txt` names; actual files are `wcvp_names.csv` and
`wcvp_distribution.csv`. Their headers and the two real records were inspected directly.
The release identifies CC BY 3.0 and its recommended citation:

Govaerts R (ed.). 2026. _WCVP: World Checklist of Vascular Plants_. Facilitated by the Royal Botanic
Gardens, Kew. [Dataset DOI](https://doi.org/10.34885/egs6-cp24) [accessed 04 Jun 2026]. For a Florabase receipt,
retain that release citation/extraction date and separately record actual retrieval on 2026-10-02.

`geographic_area` is a generalized distribution narrative. `lifeform_description` is a modified
Raunkiaer life-form term; `climate_description` is habitat derived from published information.
Neither is cultivation advice. `reviewed` is a family-review flag, not a per-element accuracy warranty.
The structured distribution CSV has TDWG levels 1/2/3, exact three-letter level-3 area codes,
`introduced`, `extinct`, `location_doubtful` and local record IDs. README defines `introduced=0`
as native and 1 as introduced; extinction and doubt are independent flags. Preserve them separately.

CC BY 3.0 permits commercial copying/adaptation with attribution, license link and supplied notices;
there is no NC or SA condition. Keep the title/creator/release citation and mark transformations as
appropriate. [License deed](https://creativecommons.org/licenses/by/3.0/). The
[Kew scientific-data terms](https://www.kew.org/science/collections-and-resources/data-and-digital/terms-of-use)
make each dataset's license authoritative; metadata licensing does not license every underlying
element. Both live example pages also identify Kew Backbone Distributions as CC BY 3.0 with the
supplied WCVP copyright notice. These rights do not extend to unrelated POWO contributors.

Kew's own [pykew documentation](https://github.com/RBGKew/pykew) and
[implementation](https://github.com/RBGKew/pykew/blob/master/pykew/powo.py) describe lookup with
`fields=distribution`. **POWO API: PUBLIC STRUCTURED BUT WEAKLY DOCUMENTED for current deployment**:
the published client uses a historical hostname and its descriptive-data availability statements
are inconsistent. A secured request to that documented hostname for Annona returned HTTP 403.
Current two-taxon machine proof therefore comes from the supported download, not the API. No
current documented live narrative API, versioning/SLA or complete element-rights contract was proved.
An internal browser endpoint would remain INTERNAL / NON-CONTRACTUAL without further evidence.

The [Annona general-information page](https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:927235-1/general-information)
shows real uses from Useful Plants and Fungi of Colombia (UPFC), with CC BY-NC-SA 3.0.
Its small raw example is `Use Food: Used for food.`; `Use Poisons: Poisons.` is a use category,
not a clinical toxicity warning. These are HTML-ONLY evidence in this investigation, absent from
the inspected WCVP release. NC restricts commercial reuse and SA imposes separate redistribution
conditions; do not reinterpret those terms as an unrestricted AGPL import contract. The Colombia
catalogue and IUCN material also have separate restrictive licenses. Kew's CC BY distribution license
does not license them. The publicly visible risk prediction is conservation, not profile warnings.

## 25. Real taxa and reproducible samples

Common, documented example: **Acer palmatum Thunb.**, used in existing UX/schema fixtures.
Project example: **Annona cherimola Mill.**, used in collection/profile fixtures. These are real
provider records; choosing them does not establish that any operator database already has the
required source link. Species-level content must not silently become cultivar-specific advice.

### WFO: two exact archive joins

| Taxon / stable record                                                                                     | Actual element sample and metadata                                                                                                                                                                                                | Destination / normalization                                                                                                                                                      | License and attribution / machine method / importability                                                                                                                                                                                                                                                    |
| --------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Acer palmatum Thunb.; `wfo-0000514777`; [record](https://www.worldfloraonline.org/taxon/wfo-0000514777)   | Description begins `Trees deciduous, andromonoecious, to 15 m tall.`; type `general`; language `English`; created `2008-04-19`; source `E69CC6F4-E393-4FFA-A0BA-72A4A2121BF1`. Full element 1,237 characters, with italic markup. | `description`; B: decode structured rich text into plain text without changing botanical content; existing whitespace/control/length validation. No automated section splitting. | Effective CC BY 4.0, MBG; source Flora of China, MBG/Harvard (2008), [original reference](http://www.efloras.org/florataxon.aspx?flora_id=2&taxon_id=200013064), WFO acknowledgement. DwCA exact taxon/reference join. YES as candidate, conditional on durable attribution and approved snapshot contract. |
| Annona cherimola Mill.; `wfo-0000537707`; [record](https://www.worldfloraonline.org/taxon/wfo-0000537707) | Description begins `Trees 3-7 m tall, deciduous.`; type `general`; language `English`; created `2011-03-27`; source `B2E6A434-1B44-48E1-9FA9-3C6900A65BB1`. Full element 1,063 characters, plain text.                            | `description`; B: plain-text/whitespace validation with no botanical paraphrase, translation or taxonomy correction.                                                             | Effective CC BY 4.0, MBG; Flora of China, MBG/Harvard (2011), [original reference](http://www.efloras.org/florataxon.aspx?flora_id=2&taxon_id=200008505), WFO acknowledgement. Same DwCA exact join. YES under the same conditions.                                                                         |

The Annona bibliography preserves the historical spelling `Annona cherimolia`; do not rewrite the
reference or local identity. Its WFO page's legacy IPNI link points to `72172-1`, while its POWO link
and the inspected WCVP record use `927235-1`. This observed inconsistency prohibits assuming all
provider cross-links are interchangeable. WFO distributions/traits on these pages remain NO for
import for the reasons in the matrix, irrespective of the eligible description.

### Kew WCVP: two accepted records, exact CSV samples

| Taxon / stable record                                                                                                                           | Names CSV raw values → proposed value                                                                                                                                                         | Actual structured distribution samples                                                                                                                                                                              | License / access / importability                                                                                                                                                    |
| ----------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Acer palmatum Thunb.; plant ID `2616153`; IPNI/POWO `927504-1`; [record](https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:927504-1)   | `geographic_area=SW. Korea, C. & S. Japan` → same text in `origin_distribution` (A); `lifeform_description=tree`; `climate_description=temperate`; `taxon_status=Accepted`; `reviewed=N`.     | Native `JAP` Japan (locality `2007955`), `KOR` Korea (`2007956`), each `(introduced,extinct,location_doubtful)=(0,0,0)`. Introduced `GRB` Great Britain and `IRE` Ireland have `(1,0,0)`.                           | CC BY 3.0; WCVP v16/Kew citation and release fingerprint. Supported CSV download. Distribution text YES as candidate with receipt; native ranges NO; traits/taxonomy informational. |
| Annona cherimola Mill.; plant ID `2640812`; IPNI/POWO `927235-1`; [record](https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:927235-1) | `geographic_area=W. South America` → same text in `origin_distribution` (A); `lifeform_description=shrub or tree`; `climate_description=wet tropical`; `taxon_status=Accepted`; `reviewed=N`. | Native `BOL` Bolivia (`2027998`), `CLM` Colombia (`2027999`), `ECU` Ecuador (`2028000`), `PER` Peru (`2028001`), all `(0,0,0)`. Introduced `SPA` Spain (`4434649`) and `CVI` Cape Verde (`2328894`) have `(1,0,0)`. | Same CC BY 3.0/release attribution and supported CSV method. Distribution text YES as candidate; ranges NO. Live UPFC food/poison categories NO for `uses`/`warnings`.              |

All identifiers remain opaque. No numeric conversion or scientific-name join establishes a provider
link. Name matching may offer candidates later, but proposal addressing must use an explicitly
confirmed WFO/WCVP record or a separately approved, exact published identifier relationship.
Changing the linked taxon or release must invalidate a preview, not follow synonyms automatically.

Snapshot evidence retrieved 2026-10-02 (SHA-256):

- WFO Flora of China archive: `4c0b89280efdcfd0ef8dc753cca5d63566ddf8c34542b0bb4a78cdce799b63a9`.
- Kew `wcvp.zip` v16: `d32ea2b3a85e489b14e83bcc9eae7274532e1d113753f7be290d4b2dfde573fa`.

Only the short excerpts above are reproduced; no botanical narratives or downloaded archives were
added to the repository or application data. The download is not a new runtime dependency.

## 26. Complete source-capability matrix

`YES*` means source capability eligible for the proposed subset after product approval, durable
attribution and exact source confirmation; it does not mean current Florabase can import it.
Classes A/B/C/D retain the initial audit definitions. Semantic fit alone cannot override access or
license failure. `P1` provenance means provider, exact taxon ID, dataset/content owner, retrieval time,
original reference/URL, effective license/rights/credit, source element identity, normalized-value
fingerprint and dataset version/hash. `P2` additionally retains geography code scheme/level and all
native/introduced/extinct/doubt flags, plus any future reviewed crosswalk version. These requirements
apply per value, not just once to a page or provider.

| Source                        | Capability           | External field / element                              | Florabase target       | Structured?                                | Machine access                                                 | License                                               | Attribution                                | Deterministic mapping?                                      | Provenance                          | Importable? | Reason                                                                         |
| ----------------------------- | -------------------- | ----------------------------------------------------- | ---------------------- | ------------------------------------------ | -------------------------------------------------------------- | ----------------------------------------------------- | ------------------------------------------ | ----------------------------------------------------------- | ----------------------------------- | ----------- | ------------------------------------------------------------------------------ |
| WFO / Flora of China          | Description          | Description `description`, English `type=general`     | `description`          | Yes; keyed extension                       | Public DwCA; weak consumer documentation                       | Effective CC BY 4.0                                   | MBG, Flora of China/Harvard reference, WFO | B: rich text → plain text; exact ID/source join             | P1                                  | YES*        | Two licensed real elements verified; no whole-provider approval.               |
| WFO / assembled distributions | Native range         | Portal Distribution elements / contributing sources   | `BotanicalNativeRange` | Not established for licensed subset        | HTML-only evidence; inspected FoC resource skips distributions | Inspected contributors All Rights Reserved            | Individual provider plus WFO               | D; no CLDR crosswalk                                        | P2                                  | NO          | Both license/access and geography gates fail.                                  |
| WFO / assembled distributions | General distribution | Distribution statements                               | `origin_distribution`  | Not established for licensed subset        | HTML-only evidence                                             | Inspected contributors All Rights Reserved            | Individual provider plus WFO               | D for approved import; possible narrative fit insufficient  | P1                                  | NO          | Visibility and backbone CC0 grant no reuse of this element.                    |
| WFO                           | Cultivation          | No dedicated eligible element demonstrated            | `cultivation`          | Not established                            | No verified structured contract for this capability            | Not established                                       | Not established                            | D                                                           | P1 required                         | NO          | Do not extract advice from description prose or trait tags.                    |
| WFO                           | Uses                 | No dedicated eligible element demonstrated            | `uses`                 | Not established                            | No verified structured contract for this capability            | Not established                                       | Not established                            | D                                                           | P1 required                         | NO          | No tested source/type/license mapping.                                         |
| WFO                           | Warnings             | IUCN status; no eligible warning element              | `warnings`             | No warning contract                        | Portal only in these examples                                  | Source-specific; not licensed warning text            | IUCN/source plus WFO                       | C for conservation; D for warning                           | P1 required                         | NO          | Conservation classification is not a warning.                                  |
| WFO / backbone, BGCI          | Taxonomy / habit     | Names/classification; tree trait                      | None                   | Backbone yes; trait contract unproved      | Published taxonomy services/download; portal trait             | Taxonomy CC0; trait CC BY-NC-ND 4.0                   | Source/WFO; BGCI for trait                 | C                                                           | Exact source/rights if displayed    | NO          | No compatible profile destination; restrictive trait distinct from taxonomy.   |
| Kew / WCVP v16                | General distribution | Names CSV `geographic_area`                           | `origin_distribution`  | Yes; string in keyed row                   | Supported structured download                                  | CC BY 3.0                                             | Kew/WCVP release citation and notices      | A: preserve provider statement, existing validation         | P1                                  | YES*        | Existing compatible narrative destination; no code-to-country synthesis.       |
| Kew / WCVP v16                | Native range         | Distribution CSV `area_code_l3`, status flags         | `BotanicalNativeRange` | Yes; TDWG level 3                          | Supported structured download                                  | CC BY 3.0                                             | Kew/WCVP release citation and notices      | C: informational/unmapped                                   | P2                                  | NO          | Exact place crosswalk absent; flags must not be discarded.                     |
| Kew / WCVP v16                | Description          | No morphological description column                   | `description`          | Absent in release                          | No such content in inspected download                          | WCVP license does not license absent contributor text | Per actual flora needed                    | D                                                           | P1 required                         | NO          | Habit/climate/generated summary are not replacement descriptions.              |
| POWO / contributor narratives | Description          | Labelled flora/general elements                       | `description`          | Current public narrative API unproved      | HTML-only inspected narrative evidence                         | Dataset-specific; Annona catalogue CC BY-NC-SA 3.0    | Exact contributor/reference                | D for import                                                | P1                                  | NO          | No approved open-license machine narrative subset established.                 |
| Kew / WCVP and POWO           | Cultivation          | `climate_description`; habitat; cultivated status     | `cultivation`          | Habitat yes; advice absent                 | CSV supports habitat only                                      | CC BY 3.0 for CSV; contributor terms separate         | Kew or actual contributor                  | C for habitat; D for advice                                 | P1                                  | NO          | Habitat/biome and cultivated occurrence do not establish growing instructions. |
| POWO / UPFC                   | Uses                 | `Use Food`, `Use Medicines`, other use categories     | `uses`                 | Categories visible; verified export absent | HTML-only in investigation                                     | CC BY-NC-SA 3.0                                       | UPFC, underlying references, POWO          | Category semantics visible; D for approved narrative import | P1                                  | NO          | Restricted data license and no approved machine subset.                        |
| POWO / UPFC, IUCN, AERP       | Warnings             | `Use Poisons`; conservation/predicted risk            | `warnings`             | Categories visible                         | HTML-only inspected evidence                                   | UPFC/IUCN NC-SA; AERP CC BY 4.0                       | Individual content provider/reference      | C for source concept; D for warning                         | P1                                  | NO          | Poison-use category is not toxicity advice; extinction risk is not a warning.  |
| Kew / WCVP v16                | Taxonomy / traits    | Names/authors/status; life form, climate, review flag | None                   | Yes                                        | Supported structured download                                  | CC BY 3.0                                             | Kew/WCVP                                   | C                                                           | Source/release/license if displayed | NO          | Useful reference context, not synthetic profile text or identity correction.   |

## 27. Native-range crosswalk feasibility

Florabase's canonical CLDR 48.2.1 snapshot has 287 places, with `source_code_type=un_m49` for
macroregions and `iso_3166_1_alpha_2` for countries/territories. It contains no WGSRPD/TDWG code
crosswalk. Arbitrary custom place labels do not supply one. Provider area names must not match local
names fuzzily, and parent membership must not create range relationships.

The [official TDWG standard](https://www.tdwg.org/standards/wgsrpd/) and its
[second-edition tables/gazetteer](https://github.com/tdwg/wgsrpd/blob/master/109-488-1-ED/2nd%20Edition/TDWG_geo2.pdf)
show why a three-letter-code → ISO lookup is insufficient:

- WCVP `KOR` contains level-4 North/South Korea (`KOR-NK`, `KOR-SK`), while Florabase has distinct
  `KP` and `KR`. A level-3 presence does not identify the occupied level-4 unit. Acer's narrower
  narrative says southwest Korea; do not turn that prose into a guessed code conversion.
- `JAP` excludes Nansei-shoto and other island units which still belong to political Japan `JP`.
  Native in `JAP` cannot be stored as a lossless assertion for the whole CLDR Japan place.
- `ECU` excludes `GAL` Galápagos; both map politically to `EC`. For Annona, the provider explicitly
  distinguishes native mainland Ecuador from introduced Galápagos. Mapping native `ECU` to whole
  Ecuador would erase that distinction.

Some units may admit individually reviewed exact equivalences (potentially Bolivia, Colombia, Peru),
but none is approved here merely from a matching name. A future crosswalk needs versioned, explicit
boundary equivalence/precision semantics and a product decision for unmatched or partial units.
This investigation does not create subnational places, infer descendants, replace the geographic
dataset or define a generalized-country meaning for exact native-range relationships. Even a
crosswalk must specify doubtful/extinct handling; introduced rows are never native additions.
WCVP's structured geography and WFO's displayed geography remain **INFORMATIONAL / UNMAPPED**
for this increment; no licensed WFO structured distribution subset was established.
Occurrence records, cultivated observations and MAP-002 density remain unrelated evidence.

## 28. Narrative feasibility and current provenance adequacy

WFO's demonstrated general descriptions and WCVP's generalized distribution string fit existing
sections without new domain fields. Preserve source text and punctuation; deterministic conversion
of source markup to plain text is allowed only as an explicitly recorded transformation. Never render
raw source HTML, silently truncate over 20,000 characters, translate, synthesize taxonomy prose or
split mixed narratives into cultivation/uses/warnings using guesses. Unknown content types, languages,
licenses or ambiguous source joins fail closed. A proposed value can be unavailable for an individual
taxon even when the capability is eligible for the source.

Current Florabase provenance is **insufficient**. Links retain provider/taxon IDs and fetch/link
times; raw cache retains retrieval time. They do not supply persistent dataset/element license,
attribution, original reference, applied destination/value fingerprint or release identity. Cache
replacement and unlink/relink destroy the ability to explain an imported value historically. Current
`provider=gbif` addressing also cannot silently identify a WFO or WCVP record.

A small capability-owned source-attribution extension is necessary: retain P1 per selected applied
value and preserve it independently of mutable link/cache state and local subsequent edits. It must
distinguish original imported value/version from the current edited value and preserve required
notices wherever that imported content is displayed or exported. Native-range provenance would
add P2 if that capability is approved later. This is an assessment, not a schema proposal implemented
now; a generic auditing framework is unnecessary. Existing stale/concurrency gaps from section 7
also remain implementation requirements, not solved by a dataset hash alone.

## 29. Remaining uncertainties and decision boundary

- WFO's content archive consumer support, immutable release/version policy and backend-runtime
  retrieval need resolution before operational implementation. Verified browser download succeeded
  with normal certificate validation; local curl failed issuer-chain validation for WFO and its
  file host. No TLS bypass or private harvester access was used. This environment issue does not
  erase the actual structured-data proof, but browser download is not a backend integration design.
- Current WFO descriptive API support was not established. Current POWO descriptive API support and
  unrestricted contributor-text licensing were not established. The old pykew hostname returned
  403; POWO Acer web access through the web-fetch tool returned 429, while normal browser inspection
  succeeded. These are access observations, not evidence that providers lack all such content.
- The archive harvest date is not the description's publication/update date. The tested descriptions
  originate in 2008/2011 and references record source access in 2018. Do not label them updated in 2026.
- No universal source crosswalk from the accepted GBIF/CoL opaque ID to WFO/WCVP exists in the current
  contract. Exact confirmed source records and treatment of inconsistent external cross-links require
  an explicit source-link decision; names alone do not settle taxonomic equivalence.
- Approve C only for the two demonstrated dataset fields, snapshot-based WFO access and durable
  attribution requirements above. Keep native ranges, cultivation, uses, warnings and all uninspected
  contributors deferred. This is enough evidence for a bounded product/source choice; it does not
  authorize application implementation by itself.

## 30. Research-only verification and changed documents

Changed documents remain `docs/botany-003-audit.md` and `docs/progress.md`. BOTANY-003 remains
`planned`; branch/base are unchanged. No adapter, route, API artifact, frontend, schema, migration,
apply mechanism or new runtime dependency was added. The previously reported frontend baseline
failure was neither rerun nor investigated. No canonical gate was run for this documentation-only
source decision, and no staging, commit, push, delivery, merge or finish occurred.

Document verification: pinned Prettier checks for both documents, feature-registry validation and
`git diff --check`. Live evidence consists of both sources' two taxa, WFO archive schema/content
joins/element licenses, WCVP release metadata/CSV rows and official geography/license documents.
No search snippets or third-party client assertions serve as capability/license evidence.

Investigation outcome before operator approval: `SOURCE_CAPABILITY_DECISION_REQUIRED`.

## 31. Approved product/source decision

The operator approved option C on 2026-10-02, with precisely these capabilities:

- WFO / Flora of China English general description → `BotanicalProfile.description`, with
  deterministic conversion to plain text preserving source wording and reference/CC BY 4.0 credit.
- Kew WCVP `geographic_area` → `BotanicalProfile.origin_distribution`, preserving the distribution
  statement apart from necessary deterministic transport normalization and retaining CC BY 3.0 credit.

Replacement policy 3 is approved: retrieval produces an advisory proposal only. Empty fields require
explicit Apply; nonempty fields require Current vs Proposed review and concrete Replace confirmation.
Successful application must retain typed relational, immutable history of the field, nullable previous
value, applied value, exact provider/dataset/record/reference, license/credit, retrieval time,
release fingerprint and application time/operator where available. A separate field-specific pointer
must identify the current enrichment application; manual edits clear that field's association while
preserving history, and unrelated field edits preserve it. Identical value and source evidence are a
no-change state; materially changed source evidence cannot rewrite old history. Stale destination or
proposal/source-version reviews must reject apply. Retrieval, refresh failure, source disappearance,
cache expiry and unlink cannot erase canonical profile content or application history.

Provider-specific explicit source confirmation is mandatory; existing GBIF/CoL IDs or name equality
do not establish WFO/WCVP links. Cultivation, uses, warnings, traits, taxonomy, occurrences and
structured native ranges remain excluded. These are approved implementation requirements, not
implemented persistence/API/UI behavior. No new design approval is being requested.

## 32. Backend access prerequisite failed — implementation stopped

Before adding application structures, securely probed the exact approved archive:

`https://files.worldfloraonline.org/files/eFloras/Flora_Of_China/Flora_Of_China.zip`

Both existing backend images were run independently with no application/data mounts, a read-only
filesystem, dropped capabilities, `no-new-privileges`, and UID/GID 10001. The ephemeral containers
were automatically removed. Neither DEV nor Review nor production services/data were changed:

- `florabase-quality-8b4474e4d89f-backend-development:latest`
- `florabase-prod-backend:latest`

Each used the installed HTTPX 0.28.1 and certifi 2026.07.22, default certificate verification, a
fixed URL, disabled redirects, a 10-second connect/20-second other timeout, `Range: bytes=0-0`,
and at most one 16-byte streamed chunk if retrieval succeeded. Both exited 1 before any HTTP
response or archive bytes were available:

```text
ConnectError [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
unable to get local issuer certificate (_ssl.c:1082)
```

An independent host curl probe also exited 60 with issuer-chain validation failure. The precise
certificate-chain/root-cause diagnosis is not established; this is a secure access failure in both
tested application runtimes, not a claim that the source content or license is invalid. The earlier
browser download remains valid investigation evidence, but is not a backend-controlled retrieval
mechanism and cannot substitute for the failed runtime prerequisite.

The operator expressly required stopping if the reviewed source mechanism cannot be used safely.
Application implementation therefore stopped at this prerequisite: no alternate provider/API/path,
manual browser-download integration, insecure HTTP, certificate-verification bypass, custom trust
exception or placeholder enrichment implementation was introduced. Secure retrieval of this exact
archive must succeed with an appropriate validated certificate chain before implementation resumes.
The approved two-field source decision and replacement policy remain intact; no provider selection
decision is being reopened. WCVP eligibility remains established by the earlier investigation, but
no partial WCVP-only feature was substituted for the approved combined increment.

Updated the audit, feature acceptance contract, domain-model approved/deferred note, roadmap and
progress. BOTANY-003 remains `planned`, not `implemented` or `verified`. Formatting, feature graph
and diff checks cover documentation only. Parser/API/migration/frontend/browser checks did not run
because no implementation was added. The unrelated baseline failure was not revisited. No canonical
`make feature-verify`, staging, commit, push, delivery, merge or finish occurred.

`SOURCE_IMPLEMENTATION_BLOCKED`

## 33. TLS trust-path diagnosis — provider chain incomplete

Diagnosis performed 2026-10-02, approximately 21:30–21:34 UTC, without changing any image, trust
store, dependency, application code or operator environment. Target remained exactly
`https://files.worldfloraonline.org/files/eFloras/Flora_Of_China/Flora_Of_China.zip`.
All three environments resolved `files.worldfloraonline.org` to `192.104.39.152` and received the
same leaf certificate through direct SNI connections. No alternate source or distribution path was
tested. Official issuer documentation was read only to identify the expected public hierarchy;
no issuer certificate was downloaded or installed.

### Actual image and trust inventory

`backend/Dockerfile` pins `python:3.14.7-slim-bookworm` for builder and runtime; development derives
from builder. There is no explicit `ca-certificates` provisioning command, but absence of that command
does **not** mean that the built images lack public trust. Both images already contain the package
and a functioning populated public root store. Diagnostics used the existing images, not rebuilt
or repaired images, in isolated automatically removed containers with read-only filesystem, no
mounts, UID/GID 10001, dropped capabilities and `no-new-privileges`:

- Development: `florabase-quality-8b4474e4d89f-backend-development:latest`, image ID
  `sha256:cb84002e65b7d69fc1b881a316217b7d461dbb8139aad1b09ddc364d557b36d4`.
- Runtime: `florabase-prod-backend:latest`, image ID
  `sha256:c3b257f01430dcb8967ba518b267e33aa911feaba4f404805f9874576251dd91`.

| Diagnostic                                           | Host                                                         | Development image                                            | Production/runtime image                                     |
| ---------------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| OS                                                   | Linux Mint 22.3, Ubuntu noble                                | Debian GNU/Linux 12 bookworm                                 | Debian GNU/Linux 12 bookworm                                 |
| Debian-family `ca-certificates` status               | `install ok installed`                                       | `install ok installed`                                       | `install ok installed`                                       |
| Installed package version                            | `20260601~24.04.1`                                           | `20250419~deb12u1`                                           | `20250419~deb12u1`                                           |
| `/etc/ssl/certs`                                     | Present directory, 246 entries                               | Present directory, 301 entries                               | Present directory, 301 entries                               |
| `/etc/ssl/certs/ca-certificates.crt`                 | Present, 182,140 bytes, 121 certificates                     | Present, 224,449 bytes, 150 certificates                     | Present, 224,449 bytes, 150 certificates                     |
| Python                                               | 3.12.3                                                       | 3.14.7                                                       | 3.14.7                                                       |
| Python OpenSSL                                       | 3.0.13, 30 Jan 2024                                          | 3.0.20, 7 Apr 2026                                           | 3.0.20, 7 Apr 2026                                           |
| `SSL_CERT_FILE` / `SSL_CERT_DIR`                     | Both unset                                                   | Both unset                                                   | Both unset                                                   |
| Conventional HTTP(S)/ALL proxy environment variables | None set                                                     | None set                                                     | None set                                                     |
| certifi version                                      | 2023.11.17, distribution-patched system path                 | 2026.07.22                                                   | 2026.07.22                                                   |
| certifi path                                         | `/etc/ssl/certs/ca-certificates.crt`                         | `/opt/venv/lib/python3.14/site-packages/certifi/cacert.pem`  | `/opt/venv/lib/python3.14/site-packages/certifi/cacert.pem`  |
| HTTPX                                                | Not installed in host system Python                          | 0.28.1; default certifi bundle                               | 0.28.1; default certifi bundle                               |
| Python default system trust                          | 121 CA certificates; verification required; hostname checked | 150 CA certificates; verification required; hostname checked | 150 CA certificates; verification required; hostname checked |
| Python explicit certifi trust                        | 121 CA certificates; verification required; hostname checked | 121 CA certificates; verification required; hostname checked | 121 CA certificates; verification required; hostname checked |
| DigiCert Global Root G2                              | Present in system/certifi bundle                             | Present in system and certifi bundles                        | Present in system and certifi bundles                        |

In all three environments `ssl.get_default_verify_paths()` returned:

```text
cafile=/usr/lib/ssl/cert.pem
capath=/usr/lib/ssl/certs
openssl_cafile_env=SSL_CERT_FILE
openssl_cafile=/usr/lib/ssl/cert.pem
openssl_capath_env=SSL_CERT_DIR
openssl_capath=/usr/lib/ssl/certs
```

The paths resolve to `/etc/ssl/certs/ca-certificates.crt` and `/etc/ssl/certs` respectively.
System bundle SHA-256: host
`6602a85a36afc2e51c66a0df5ae3d383c5b7c2fed93339ccef7d37e01faf09e8`;
both images `714d457d580922dbf1d0be8bd35ba236a842b50b0072ae791582a19adef772a5`.
These are diagnostic identities only, not application pins or new trust anchors.

The implemented external provider uses HTTPX 0.28.1 with its default secure context. The intended
enrichment probe uses the same library/version: default HTTPX context had required verification,
hostname checking and 121 certifi CA certificates. Explicitly passing Python's normal system
context also failed. Thus HTTPX's certifi default differs from Debian system trust, but switching
between them does not fix this failure and is not a demonstrated configuration defect.

### Chain actually served and verification results

Verified diagnostics used Python `ssl.create_default_context()` with `server_hostname`, host curl
verbose HEAD on the exact archive URL, OpenSSL SNI/hostname verification, and bounded HTTPX range
GET on the exact archive URL. All contexts required verification and hostname checking. No request
accepted the invalid chain; no response/body was available to HTTPX or curl.

OpenSSL command, run on the host and independently in each image:

```sh
openssl s_client -connect files.worldfloraonline.org:443 \
  -servername files.worldfloraonline.org \
  -verify_hostname files.worldfloraonline.org \
  -verify_return_error -showcerts < /dev/null
```

Every run exited 1 and showed **exactly one served certificate**, the leaf:

| Leaf attribute           | Observed value                                                                                    |
| ------------------------ | ------------------------------------------------------------------------------------------------- |
| Subject                  | `C=US, ST=Missouri, L=St. Louis, O=Missouri Botanical Garden, CN=*.worldfloraonline.org`          |
| Issuer                   | `C=US, O=DigiCert Inc, OU=www.digicert.com, CN=GeoTrust TLS RSA CA G1`                            |
| SANs                     | `DNS:*.worldfloraonline.org`, `DNS:worldfloraonline.org`                                          |
| Validity                 | 2026-07-14 00:00:00 UTC through 2027-01-28 23:59:59 UTC                                           |
| SHA-256 fingerprint      | `3B:B5:77:AF:79:6F:D3:AE:FD:C7:AB:A7:A8:D8:F7:92:C8:67:54:28:5E:CA:A7:D5:D4:A9:94:F3:FD:0E:68:2D` |
| Authority key identifier | `94:4F:D4:5D:8B:E4:A4:E2:A6:80:FE:FD:D8:F9:00:EF:A3:BE:02:57`                                     |
| CA Issuers AIA           | `http://cacerts.geotrust.com/GeoTrustTLSRSACAG1.crt` (observed only; not fetched)                 |
| Verification failure     | Error 20, `unable to get local issuer certificate`, depth 0                                       |

Offline `openssl x509 -checkhost files.worldfloraonline.org` confirms the SAN matches the host.
This name check alone is not successful trust validation. The leaf is within its date interval at
the measured current time. Its issuer is not the leaf itself. The missing issuer intermediate
`GeoTrust TLS RSA CA G1` is **not** in the served chain. Absence of a root in a served chain is
normal; absence of this issuing intermediate prevents the observed standard clients from building
the chain to an already trusted public root.

[DigiCert's authoritative hierarchy listing](https://knowledge.digicert.com/general-information/digicert-trusted-root-authority-certificates)
identifies GeoTrust TLS RSA CA G1 as issued by DigiCert Global Root G2. That root was found in every
tested system/certifi bundle, with validity 2013-08-01 through 2038-01-15 and fingerprint
`CB:3C:CB:B7:60:31:E5:E0:13:8F:8D:D3:9A:23:F9:DE:47:FF:C3:5E:43:C1:14:4C:EA:27:D4:6A:5A:B1:CB:5F`.
The issuer intermediate is not expected to be a public-root-store entry and was not found there.
No certificate from the endpoint was trusted or copied into any application/image trust database.

Host curl used `/etc/ssl/certs/ca-certificates.crt` and `/etc/ssl/certs`, exited 60, and reported the
same issuer failure. Host Python system/certifi and both images' Python system/certifi contexts
failed with `SSLCertVerificationError.verify_code=20`. Both images' HTTPX default and explicitly
system-trusting requests failed with `ConnectError` wrapping `CERTIFICATE_VERIFY_FAILED`.
An OpenSSL aborted-session summary printed a trailing `Verify return code: 0 (ok)` despite the
fatal error and no established cipher; this is not success. Exit 1, depth-0 error 20 and aborted
handshake are the authoritative outcome. No protocol downgrade or cipher override was requested.

### Classification, safe action and scope boundary

- **Case C demonstrated on the observed endpoint:** the issuing intermediate is absent from the
  server chain, with reproducible depth-0 issuer failure on host/development/runtime public stores.
- **Case A not supported:** both images already have Debian CA packages/stores, and the necessary
  public root exists. A missing normal public CA store is not the defect.
- **Case B not supported as the cause:** both HTTPX's normal certifi store and explicitly selected
  normal system trust reject the same chain with verification and hostname checking enabled.
- **Case D ruled out for this leaf:** SAN matching succeeds; the dates are currently valid.
- **Case E has no positive evidence:** no conventional proxy variables, no different/interception
  issuer certificate, and identical endpoint IP/leaf across all three contexts. This does not claim
  to audit every possible transparent network device or an independent off-site network path.
- **Case F/stale root not demonstrated:** the expected root is already present and valid; no unrelated
  dependency or base-image upgrade is justified by this evidence.

The standard correction belongs to the WFO TLS deployment: serve the appropriate issuing intermediate
with the leaf so ordinary clients can chain to their existing public root. Browser success remains
compatible with alternate chain-building/cached-intermediate behavior and does not override these
backend verification failures. The browser mechanism was not used in this diagnostic run.

Provider-specific intermediate augmentation is only an **option requiring explicit operator approval**
and a separate security/maintenance contract. It is neither the chosen remediation nor implemented.
No custom CA, leaf pin, runtime intermediate download, hostname override or verification exception
was added. No official alternate distribution endpoint was investigated or adopted.

There is no justified standard Florabase CA/runtime fix here, so no image rebuild, trust mutation or
regression test for a nonexistent fix was performed. Invalid-chain rejection was directly observed
in all tested clients. Existing GBIF/CoL/other HTTPS code and global verification remain unchanged.
No application implementation, partial WCVP-only feature, migration, staging, commit or canonical
gate was introduced. BOTANY-003 remains `planned`; the two-field scope and replacement/history
decision remain approved. Resume only after the exact approved archive validates normally, or after
an explicit separately reviewed change to the access/trust contract. Documentation checks cover
formatting, feature registry and whitespace only; no WFO-dependent CI test was added.

`SOURCE_TLS_PROVIDER_BLOCKED`
