# BOTANICAL-IDENTITIES-VISUAL-001 cross-functional review

## Candidate and review boundary

Final operator-requested IA pass, 2026-10-24. Source:
`/home/alessandro/.codex/worktrees/f6da/florabase`, branch
`feat/botanical-identities-visual-001`, base/HEAD
`e7ade78559803a35b738a669085799f55eb76258`. Status remains `implemented`.
All candidate work is unstaged and uncommitted. No canonical FULL gate, verification receipt,
commit, push, PR, merge, delivery or environment upgrade is claimed. Operator acceptance is pending.

[Current gallery](gallery-cross-functional.html) ·
[Browser measurements](cross-functional/browser-evidence.json) ·
[Checks](cross-functional/verification-results.json) ·
[Previous refinement handoff](handoff-refinement.md) ·
[Previous refinement gallery](gallery-refinement.html) ·
[First-pass gallery](gallery-pass1.html)

## Final information architecture

Exactly six read sections, in order: **Overview, Reference, Taxonomy, Maps, Media, History**.
No Collection tab or nested collection directory remains. Global sidebar/Settings architecture,
the six theme definitions and shared control system are preserved.

| Section   | Final behavior                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Overview  | Compact identity/cultivar/common-name/cover band uses semantic surfaces, including a dark equivalent. Five clickable record totals separate active counts from historical totals. A short actual profile excerpt, taxonomy status, geographic link, four recent recorded facts including Harvests, one eligible next action, metadata disclosure and independent Danger zone form the homepage. Stored remainder is not presented as a Harvest count. |
| Reference | Existing five textual profile fields only, with bounded reading width and responsive columns. Empty profile explains its absence. Contextual Add/Edit opens the existing Reference editor. No map, taxonomy workflow or gallery is embedded here.                                                                                                                                                                                                     |
| Taxonomy  | Existing WFO classification/linking and GBIF reference workflows, with source attribution and truthful loading/unavailable states. Stable local identity remains distinct from linked external classification. No missing lineage, synonym or source certainty is invented.                                                                                                                                                                           |
| Maps      | Three labelled evidence types: native-area assertions, observed occurrences and directly recorded collection provenance. Availability reads are local. Only one explicitly expanded preview mounts at a time; existing map engines, privacy/consent, caching and attribution are reused.                                                                                                                                                              |
| Media     | Existing identity cover management and actual MediaAsset rights/caption/source. Related collection records have bounded owner links, without implying each has a photo. One cover is supported; arbitrary identity attachments and a universal related gallery are not supported by current contracts.                                                                                                                                                |
| History   | Existing authoritative identity-linked Plant/PlantGroup event provider, including structured Harvest facts. Shared Journal feed grammar preserves ordering, deduplication, PartialDate precision and source links. Future planned work and inferred lifecycle facts are excluded.                                                                                                                                                                     |

The compact previous/next controls retain directory ordering and selected main section, truncate
long names, expose full accessible names/titles and preserve directory search return context.
All six section labels remain available through a scrollable tab strip on narrow screens; only
that strip scrolls horizontally. No measured page-level horizontal overflow was found.

## URL compatibility and exact drilldowns

Canonical tab URLs use `#/identities/{id}?tab={section}`. Browser Back/Forward, reload,
keyboard section navigation and old routes are covered by affected tests.

| Historical `tab`                                       | Current destination                                             |
| ------------------------------------------------------ | --------------------------------------------------------------- |
| `events`                                               | History                                                         |
| `collection`, `seeds`, `sowings`, `plants`, `harvests` | Overview, collection footprint anchor                           |
| `profile`                                              | Reference                                                       |
| `source`                                               | Taxonomy, source anchor                                         |
| `taxonomy`                                             | Taxonomy                                                        |
| `native-range`, `occurrences`                          | Maps, corresponding evidence anchor; heavy preview stays closed |
| `edit`                                                 | Existing contextual editor                                      |
| Missing or unknown                                     | Overview                                                        |

`{id}` below is the exact Botanical Identity UUID, never name search.

| Destination         | URL                                                  | Scope                                                   |
| ------------------- | ---------------------------------------------------- | ------------------------------------------------------- |
| Seed lots           | `#/seeds?identity_id={id}&lifecycle=all`             | Actual SeedLot identity                                 |
| Sowings             | `#/sowings?identity_id={id}&lifecycle=all`           | Actual source SeedLot identity                          |
| Plants              | `#/plants?identity_id={id}&lifecycle=all&type=plant` | Actual Plant identity and kind                          |
| Plant groups        | `#/plants?identity_id={id}&lifecycle=all&type=group` | Actual group identity and kind                          |
| Harvests            | `#/harvests?identity_id={id}`                        | Existing server scope over actual sources               |
| Return to identity  | `#/identities/{id}?tab=overview`                     | Visible directory return link                           |
| Native ranges       | `#/native-ranges?mode=species&identity={id}`         | Supported exact species selection                       |
| Occurrence evidence | `#/species-distribution?identity={id}`               | Supported identity selection; download remains explicit |
| Collection origins  | `#/map`                                              | All identities; labelled explicitly as such             |

Seeds/Sowings/Plants retain the prior pass's complete-loaded client filtering layer, visible clear
chips, composition with search/lifecycle/kind and version-1 Saved View state. Additive backend UUID
validation and persisted round-trip tests remain preserved; no API/schema change was added in this
third pass. All five footprint destinations and Return links were followed in the live review.

There is no established exact identity filter for global Journal/History. No invented query is used.
The identity event provider does not project sowing/germination, record creation from current state,
all material operations or schedule completion history. History explains this gap and links to
source Sowings and Harvests; a new authoritative projection is a separate domain increment.

## Operations, editor and safeguards

The Add menu uses one menu-item grammar for all five entries: uniform typography, width,
8px/12px padding, 44px height and semantic hover/focus styling in all six themes. Existing shared
keyboard navigation and Escape dismissal remain.

| Operation       | Existing flow                                                                                                             |
| --------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Add seed lot    | `#/seeds?action=create&identity={id}`                                                                                     |
| Start sowing    | Choose an actual eligible active SeedLot, then `#/sowings?action=start&seedLot={lot}`                                     |
| Add plant       | `#/plants?action=create&identity={id}&kind=plant`                                                                         |
| Add plant group | `#/plants?action=create&identity={id}&kind=group`                                                                         |
| Record harvest  | Choose an actual eligible Plant/PlantGroup, then `#/harvests?action=create&sourceType=plant\|plant_group&source={source}` |

No lineage or inherited provenance is inferred. Missing prerequisites explain the absence and
link to existing creation workflows. Source choosers and the identity-prefilled group form were
visually inspected without submitting unintended collection records.

The editor retains Identity, Reference, Native range and Media, mounted drafts and independent
save/reset behavior. A compact editing context and generic heading replace the repeated full-name
heading. Main read navigation is unmounted while editing and remounts with fresh saved reads.
Reference/Maps contextual editing opens its appropriate section. Closing restores the persistent
header Edit control. Dirty/pending guards, validation and backend persistence semantics remain.
Danger zone is independent; both desktop and phone confirmation screenshots show Cancel-first
focus. No deletion or editor save was submitted during this visual pass.

Native confirmation diagnosis: a temporary clearly labelled unsaved common-name value survived
Identity → Reference → Identity. Close invoked the native discard prompt; the supported browser
API returned no dialog handle and input timed out, reproducing the prior browser limitation.
Operator Cancel was requested; no dialog was bypassed, draft discarded or save submitted. Automated
dirty-state protection tests pass. Interactive Cancel/acceptance remains an explicitly pending
browser acceptance item. The prompt also prevented the final tab/temporary viewport reset;
operator Cancel is needed to resume that browser. No page was force-reloaded or closed.

## Geographic and media limits

Native-range preview reuses the collection-aware native selection endpoint and NativeCoverageMap.
Its inspector is labelled Current botanical identity and receives only the selected identity.
Textual recorded areas, missing geometry, broad/unrendered assertions, boundaries and attribution
retain existing meanings. Reference-only identities may have structured assertions but lack a
collection-aware map projection; the UI explains this and retains editing/dedicated workspace links.

Collection origins loads the existing map projection only after explicit expansion, filters records
by exact identity ID, removes unrelated sites and recalculates usage counts. It retains direct
historical source records and recorded coordinate accuracy, with a textual chooser. Coordinate-less
sites are not shown on the map. Storage Locations, Suppliers and source ancestry never imply
native distribution or derived provenance. The dedicated origins workspace lacks an exact identity
filter, so its all-identities link is labelled truthfully. Online basemap access was disabled in
this review deployment; no tile-consent bypass was performed.

The fixture has no approved WFO snapshot or confirmed GBIF reference/cached occurrence raster.
Taxonomy and occurrence captures show actual prerequisites/unavailable states. No provider download
or invented provider data was used. Automated existing provider/map regression passed; approved
provider-backed visual acceptance remains deferred.

Identity media supports one cover. Its actual asset link, creator, licence and source are shown.
Up to 12 actual related record links lead to owner photo sections where supported; Harvest links
open the actual Harvest record. No arbitrary direct attachment gallery or combined related-record
photo API exists. Photo ownership and upload/remove safeguards are unchanged.

## Populated review data and runtime

Open the [populated synthetic identity](http://localhost:15176/#/identities/01a16cb5-e4fe-77c4-8458-2e1873f1e9dd).
The synthetic review account and password remain in the isolated review environment and are not
included in the repository.

The operator requested test data for visual inspection. The clearly fictional **Demonstratio visualis
‘Cross-functional review’** was added through authenticated APIs: three SeedLots (two active),
one Sowing, two Plants, one PlantGroup, one Harvest with two material lines, four recorded events,
a complete textual profile, one explicitly fabricated manual Italy range and one illustrative
city-scale provenance site linked directly to a packet and direct Plant. Derived records do not
inherit that site. Unknown quantities stay unknown; month-only dates remain month-only.
[Fixture manifest](cross-functional/fixture-manifest.json)
records exact new IDs, actions, source rights and unchanged original fixture counts.

The illustration reuses the repository's offline sage fixture, by Caroline Léna Becker,
[CC BY 3.0](https://creativecommons.org/licenses/by/3.0/),
[original Commons source](https://commons.wikimedia.org/wiki/File:Sauge_officinale.JPG).
Its actual metadata states resized/recompressed/EXIF removed and makes clear that sage is only an
illustration, not identification of this fictional identity. No image was downloaded for this pass.

Owned services are exactly `florabase-botanical-visual-f6da-db-1`,
`florabase-botanical-visual-f6da-backend-1` and
`florabase-botanical-visual-f6da-frontend-1`, with `io.florabase.source` pointing to this worktree.
The frontend is loopback port 15176; the current backend has no published host port. Use the
frontend proxy, not old port 18176. Existing DB/media volumes and project network are retained;
no migration was introduced (existing revision `20261013_0042`).

After host restarts, the old positively owned `backend-1-pass1` was running with the current backend
DNS alias while the current backend lacked a network attachment. Only that exact backup was
stopped and the current backend reconnected to its own existing network. No volume/container
removal, reset, reseeding of existing records or foreign environment operation occurred. Runtime
ownership was checked again before final capture. DEV/UAT/Preview/production and other worktrees
remain untouched. Recheck exact ownership after future restarts rather than assuming port ownership.

Original basil fixture counts remain 8/1/1/1/1 and two events; the long-name reference-only identity
remains empty. Earlier synthetic packets, Saved View, handoffs and screenshots are preserved.

## Verification and review evidence

- Final affected frontend: **458 tests passed across 28 files**, single worker.
  [Exact result](cross-functional/final-test-results.json).
  This covers all six routes/legacy aliases, exact filters/Saved Views, Harvest History, source
  eligibility, editor/draft/focus, keyboard navigation, maps isolation/lazy loading, media ownership
  and existing map/provider regressions. Vitest reports 43 suites including nested describe suites;
  the actual selected file count is 28.
- Strict TypeScript and production build passed: **236 transformed modules**. ESLint passed all
  **45 changed TS/TSX files**, zero warnings. Source was frozen before the final affected run.
- Scoped formatting, **112-feature graph**, whitespace and gallery local-link checks are recorded
  in the check summary. Staged diff remains empty.
- Prior pass backend **88 unit + 15 PostgreSQL integration** checks and API drift/Ruff/mypy evidence
  remain archived. They were not rerun in this UI-only third pass. No third-pass API/schema change
  requires another backend migration or generated artifact.
- Gallery covers six themes and desktop 1440×844, tablet 1024×844, phone 390×844. All six sections
  have Botanical Light desktop/tablet/phone and Mineral Dark desktop/phone captures, plus Botanical
  Dark tablet Overview/Maps. Native range, origins, occurrence prerequisites, actual media rights,
  Harvest History, all five drilldowns, source choosers, editor and Cancel-first deletion are included.
  Browser measurements report zero root/body horizontal overflow. Full-page captures are labelled.

No full repository suite or canonical FULL gate is claimed. Earlier exploratory failures, resolved
mock readiness issues and historical checks are not substitutes for the final affected result.
Existing jsdom `window.confirm` diagnostics were not suppressed. Physical touch, assistive
technology, zoom, real approved provider imagery and independent/operator acceptance remain pending.

Next: inspect the populated hub and gallery, confirm information architecture and density, review
truthful unavailable states and finish interactive editor discard/focus acceptance. Operator visual
acceptance precedes separate authorization for canonical FULL and commit/delivery.

`BOTANICAL_IDENTITY_CROSS_FUNCTIONAL_REVIEW_READY`
