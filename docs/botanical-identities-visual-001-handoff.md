# BOTANICAL-IDENTITIES-VISUAL-001 visual composition review

## Candidate and boundary

2026-10-24 final composition pass. The operator accepted the six-section information architecture;
this pass refines its presentation and usability. Source:
`/home/alessandro/.codex/worktrees/f6da/florabase`, branch `feat/botanical-identities-visual-001`,
base/HEAD `e7ade78559803a35b738a669085799f55eb76258`. Feature status stays `implemented`.
Changes remain unstaged and uncommitted. No canonical FULL gate, receipt, push, PR, merge,
delivery or environment upgrade was performed. Composition acceptance remains pending.

[Current gallery](review/botanical-identities-visual-001/gallery.html) ·
[Composition measurements](review/botanical-identities-visual-001/composition/browser-evidence.json) ·
[Composition checks](review/botanical-identities-visual-001/composition/verification-results.json) ·
[Accepted IA handoff](review/botanical-identities-visual-001/handoff-cross-functional.md) ·
[Previous IA gallery](review/botanical-identities-visual-001/gallery-cross-functional.html) ·
[Refinement handoff](review/botanical-identities-visual-001/handoff-refinement.md) ·
[Refinement gallery](review/botanical-identities-visual-001/gallery-refinement.html) ·
[First-pass gallery](review/botanical-identities-visual-001/gallery-pass1.html)

## Composition changes

| Area            | Final composition                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Shared surfaces | One primary bounded semantic surface per detail section; shared radius, border, padding and horizontal alignment. Internal structure uses restrained dividers. Overview retains its distinct elevated identity band; other headers use a quieter semantic surface. No global theme/token/sidebar/Settings architecture was changed.                                                                                                                                                                               |
| Header          | Breadcrumb and adjacent navigation share one row. Duplicate header/tab separators and excess gaps are removed. Desktop actions sit beside the identity; at intermediate widths both actions move together below the name. The long-name 860px check exposed a squeezed Overview name column; the corrected two-column/name-plus-action-row layout is recaptured. Phone preserves readable name/cultivar wrapping and a scrollable six-tab strip.                                                                  |
| Maps            | A three-column evidence comparison becomes two columns on tablet and one on phone. Native entry count, confirmed reference/saved occurrence evidence where supported, and exact direct provenance site/record counts appear immediately. Concise explanations/actions replace the long sparse list. Exactly one activated inspection region appears below the summary and reuses the existing map engines. Activation focuses and scrolls to its heading; Close inspection returns focus to the evidence trigger. |
| Media           | Actual cover is featured first, with a restrained Cover marker, title/rights and collapsed existing management disclosure. A separate responsive gallery shows actual linked-record thumbnails, captions, media type, owner links and rights. Portrait/landscape images use contain sizing without stretching. Existing Media detail handles opening/viewing; no duplicate viewer or cover assignment flow was introduced.                                                                                        |
| Reference       | Text begins immediately in the primary surface. Edit profile is in the compact heading row. Short fields share two columns; fields over 600 characters span a readable bounded width. All stored text stays readable, without nested scrolling or truncation. The populated desktop fixture shows description, origin/distribution, cultivation, uses and the start of warnings in one viewport.                                                                                                                  |
| Taxonomy        | Existing WFO/source workflows sit within the same primary surface, with restrained dividers. Stable local identity context remains separate from external classification. No empty classification or invented source linkage is drawn.                                                                                                                                                                                                                                                                            |
| History         | Shared surrounding surface; the inner feed's redundant outer border is removed. Existing operational chronology, timeline marks, source links, month/day precision, deduplication and Harvest facts remain unchanged.                                                                                                                                                                                                                                                                                             |

Exactly **Overview, Reference, Taxonomy, Maps, Media, History**, in that order. Core identity filters,
Saved Views, all five collection operations/source eligibility, editor saves/reset/drafts, Danger zone,
old URLs and Back/Forward remain covered by the affected regression. No API, schema, migration,
provider acquisition or domain projection was added.

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
validation and persisted round-trip tests remain preserved; the accepted IA pass and this composition refinement add no further API/schema change. The prior
IA review followed all five footprint destinations and Return links in the live application.

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

## Geographic evidence and media scope

Maps summary reads existing local native-range assertions, external link, saved occurrence cache
(only with a confirmed link), and the provenance map projection. These metadata reads mount no
map and invoke no GBIF acquisition. Native and occurrence dedicated links preserve supported exact
identity scope. Native entry counts do not claim all assertions have drawable geometry. The native
preview retains existing boundaries, textual evidence, missing/unrendered warnings and attribution;
its inspector remains limited to the current identity. Reference-only identities may have assertions
without a collection-aware map projection; the captured unavailable state explains this honestly.

Origins summary and preview use exact identity IDs from actual direct source records, remove unrelated
sites and recalculate usage counts. The already-scoped summary data is reused by its explicitly
activated preview. Recorded coordinate accuracy and retained historical material remain visible;
coordinate-less sites, storage Locations, Suppliers and ancestry do not create mapped or biological
origin. The dedicated Collection origins workspace still has no exact identity filter: its existing
all-identities link is labelled explicitly. No unsupported query parameter was invented.

Occurrence preview remains opt-in. Only the existing cache-read endpoint is used for summary
indicators; no provider refresh, tile load or download is triggered by opening Maps. This fixture
has no approved WFO snapshot, confirmed GBIF reference or occurrence raster, so live captures show
actual prerequisite states. Automated provider/cache/missing-tile coverage is retained; approved
provider-backed image acceptance remains pending. Online provenance basemap access stays disabled
in this review deployment; no consent/privacy protection was bypassed.

The previous identity-wide gallery limitation is resolved using established **per-record photo lists**
and actual MediaAsset detail reads, rather than a new global identity media query. Only records in
the exact identity collection response are queried. Six source records are checked initially;
Show images from more linked records expands by six and keeps scope visible. Repeated asset reads
are shared within each batch; images retain their individual owner/caption even if an asset is shared.
A failed source list or asset read is reported with Retry; older photo entries lacking an asset ID
remain available through source-record links and are not presented as proof of no images.

The gallery reuses MediaPreview and protected thumbnails. External assets without a saved local copy
show a reference placeholder and open the existing viewer; their remote image hosts are not contacted
by this gallery. Pending deletion/broken images retain existing truthful fallback states. Actual asset
attribution/licence/source are shown when recorded. No upload authorization, storage, photo ownership,
delete behavior or media-to-cover eligibility was changed. Identity-level media is still one cover;
arbitrary additional direct identity attachments are unsupported. The related gallery is visibly
separate and never assigns collection photos as identity covers.

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
[Fixture manifest](review/botanical-identities-visual-001/cross-functional/fixture-manifest.json)
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

Two additional offline illustrations (portrait Aloe and landscape Ficus) were added only to the
existing fictional review Plant to demonstrate multiple real thumbnails. Its existing sage image
and identity cover remain. Creator/licence/source/derivative notices are retained in actual assets;
all captions explicitly deny identification of the fictional Plant. No external download or original
fixture record update was used. [Additive media manifest](review/botanical-identities-visual-001/composition/media-fixture.json).

## Verification and acceptance

### Accepted visual debt

The operator accepts the current excess card, elevated-surface and background nesting as non-blocking
visual debt. Track it as a separate cross-application visual-normalization follow-up: reduce
unnecessary nested containers, reuse established page surfaces and separators, keep useful grouping,
and align with the eventual global IA. This delivery does not include another broad styling redesign.

- Focused baseline: **9 passed / 3 files**. Development focused check: **13 passed / 4 files**.
- Final affected selection: **501 passed / 31 files**, clean exit 0. A final **22 passed / 3 files**
  focused follow-up covers inspection activation/close focus and cross-section/keyboard regressions. Includes the prior 28-file identity/directory/editor/map regression plus
  IdentityRecordMedia, existing PhotosSection and MediaScreen coverage. The first composition run
  passed every assertion but failed overall on an unhandled old App mock shape; its result/log are
  retained as attempt1 evidence. The fixture now returns the real empty map shape and explicitly
  awaits the zero-site summary. No assertion, timeout or error policy was weakened.
- Strict TypeScript/production build: **237 modules**. ESLint checks **11 affected TS/TSX files**,
  zero warnings. Scoped formatting covers all **51 changed frontend source/CSS files**.
  Exact final outcomes, feature graph, whitespace, index and gallery-link checks are in the summary.
- No backend/API/schema change in this composition pass. Previous **88 unit + 15 PostgreSQL
  integration** checks remain historical evidence, not a claimed rerun. No full repository suite or
  canonical FULL verification is claimed.
- Current gallery covers all six sections at **1440×844, 1024×844 and 390×844** in Botanical Light;
  all six at dark desktop/phone, with dark tablet Overview/Maps/Media. All six theme variants include
  Overview/Maps/Media review. Added activated native/origins inspection, empty/unavailable map and
  media states, long-name/intermediate **860×844** layouts, and uniform Add menu evidence.
  **63 captures / 63 measured states**, including pristine editor regression. Browser measurements record zero page-level horizontal overflow. Full-page images are labelled.

Earlier source/type/lint and interrupted host-pressure attempts were corrected; only final successful
checks count. Existing jsdom native-confirm diagnostics were not suppressed. Physical touch,
assistive technology, zoom, real approved provider imagery and independent/operator composition
acceptance remain pending.

The new inspection tab also opened and closed the pristine editor at desktop and phone sizes, returned to Media and restored focus, without changing fields or invoking a dirty prompt.

The retained browser tab was restored at an editor URL. This pass uses a separate read-only inspection
tab and leaves that editor untouched. No dirty editor was closed, force-reloaded, saved or deleted to
obtain screenshots. The earlier unsupported native-confirm Cancel/acceptance exercise remains a
manual acceptance item; this pass does not claim that browser limitation was fixed. The inspection
tab is left on populated Media with Botanical Light restored and temporary viewport override reset.

Next: inspect the populated hub, gallery and long-name/empty examples; accept the composition and
complete manual safeguards/provider/physical review. Canonical FULL, commit and delivery require
separate authorization.

`BOTANICAL_IDENTITY_VISUAL_COMPOSITION_READY`
