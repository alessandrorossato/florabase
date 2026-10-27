# MEDIA-VISUAL-001 — Approved Media implementation and review

2026-10-26 · operator-approved implementation · `docs/media-visual-001` · base `ee3487412fe458cbdf7145154c54a58b66132cae`

**Current phase:** the operator approved the photographic direction, all three P1 corrections, and
the final Quick Preview local-copy enhancement. The real React application contains the approved
implementation. Independent QA and the policy-selected canonical gate are in progress; protected
delivery remains pending those results. The original HTML proposal and earlier screenshots remain
historical evidence, separately labelled.

**Media-owned live Review:** http://localhost:15280/#/media. See the
[ownership, reproduction and fixture guide](review/media-visual-001/live/README.md) and
[actual current dataset](review/media-visual-001/live/dataset.json).

[Visual study](review/media-visual-001/proposal.html) ·
[Browsable evidence](review/media-visual-001/gallery.html) ·
[Read-only dataset snapshot](review/media-visual-001/dataset-snapshot.json)

## Implementation scope and current validation

The latest operator request explicitly authorizes product implementation, superseding the earlier
planning-only boundaries. Fetch succeeded and confirmed `origin/main` remains `ee348741…` (including
Geography #122, CI-004 #125 and Taxonomy #126); no merge, reset or stash was necessary. The earlier
uncommitted review packet is preserved. All changes remain unstaged and uncommitted.

| Component / file | Implemented responsibility |
| --- | --- |
| `frontend/src/media/MediaScreen.tsx` | Full-width directory; preserved filters, Saved Views, pagination and all existing mutation controls; prominent contained detail original; explicit shared-vs-link metadata; safe Cancel-first confirmations; contextual breadcrumb and safe route focus |
| `frontend/src/media/media.css` | Media-scoped wrapping header, responsive 4:3 cropped thumbnail frames, compact bounded titles, larger contained originals, responsive house-dialog preview; existing semantic palette/appearance tokens |
| `frontend/src/media/MediaQuickPreview.tsx` | Existing PhotoDialog with explicit Close/details actions, one on-demand protected original and detail read, actual record and cover context, attribution/licence, external preview consent, and explicit protected-copy save with pending/error/success/focus states |
| `frontend/src/media/navigation.ts` | Existing URL filter grammar plus validated 24-row offset; canonical detail/return URLs; browser history and invoking-card focus state; clamp an emptied last page without a Back loop |
| `frontend/src/media/{MediaScreen,MediaNavigation,navigation}.test.*` | Behavior coverage including authenticated explicit copy save, existing-copy/local distinctions, failure/double-submit handling, refreshed gallery/preview, preserved route/focus, real App remounts, and safe confirmation |
| Documentation/evidence | Updated contract, implementation inventory and validation; original design artifacts preserved |

### P1 resolutions and shared ownership

1. **Tablet header:** the old shared `column` direction turned 16rem/38rem horizontal flex bases into
   880px of vertical header. Media now explicitly composes PageHeader on the wrapping row axis with
   bounded readable identity/tool bases. It reuses DirectoryTools, filters and Saved Views. The
   header fix is scoped under `.app-content .media-workspace`; there is no global override.
2. **Delete focus:** Media's existing PhotoDialog focuses its first control. Cancel is now first in
   all three Media destructive confirmations (delete, unlink, remove saved copy). Detail navigation
   focuses the safe title. Delete stays keyboard-operable, disabled when references block it and
   protected by the unchanged server eligibility check, including pending-delete retries.
3. **Return context:** q/kind/association/target and a validated offset travel with detail URLs.
   Browser history records the invoking card separately from Saved View state. The breadcrumb and
   successful delete return preserve applicable filters/page; focus returns to the displayed card,
   or the Media heading if absent. Browser Back/Forward and reload use URL-backed state. An emptied
   last page replaces its invalid offset with the last valid page. No free-form return URL is used.

The global audit chat **Audit and consolidate Florabase UI** confirmed it has no frontend changes
in progress. PageHeader, DirectoryTools, generic filters, TaskDialog, OverflowMenu and tokens remain
owned by that normalization wave. Media reuses PhotoDialog and makes a local confirmation-order
correction. The shared header defect on other consumers remains open; this change does not claim
to resolve Seeds or normalize all shared headers. There is no second modal system.

### Preservation boundaries

Gallery cards load authenticated lazy thumbnails only. Deliberate desktop preview fetches one
asset detail graph and its original for complete framing. Mobile retains direct detail navigation
at the existing 48rem single-column layout boundary. Both detail and preview contain the image;
only card thumbnail presentation crops. Original files and thumbnails are not rewritten.

Local uploads, external references and explicit saved-copy operations, metadata editing, exact link
caption/order, record-specific primary choices, separate Identity covers, retention and guarded
asset deletion still use the existing APIs/components. No backend, schema, migration, generated API,
sidebar destination, new filter facet, tag, bulk operation or media type changes are included.
The gallery shows reference counts rather than inventing one owning botanical record or list-level
primary flags that the existing list response does not provide.

### Validation record

The pre-change Media baseline passed 22 tests. The expanded focused pass covered 119 tests in eight
files (Media, Photos, primary visual, Identity media, DirectoryTools and Saved View state), with a
later 40-test Media/navigation pass after the final refinements. A real App regression independently
passed breadcrumb return, Back/Forward, direct reload, filter/page persistence and focus across its
keyed Media screen remounts. Static/build and final browser results are recorded in the final review
section below. No canonical FULL verification, staging, commit, push, PR or merge is authorized here.

## Baseline and evidence quality

The supplied worktree began clean and detached at current `origin/main`, including merged Geography,
Botanical Identities, CI-004 and Taxonomy #126. An explicit remote SHA read later confirmed the same
`ee348741…` main. The supported `make feature-init BRANCH=docs/media-visual-001` attached this worktree;
no other checkout or worktree was created or switched.

| Evidence | What it establishes | Limits |
| --- | --- | --- |
| Current source and delivered contracts | Gallery, detail, Photos, picker, linker, covers, security and retention semantics | Code inspection is not browser acceptance |
| Retained c902 v5 PostgreSQL, `BEGIN READ ONLY` | 17 assets, 9 local, 8 external-only, 18 record links, 37 identities, **0 covers**; actual titles, attribution, dimensions, hashes and per-asset counts | No active v5 frontend/backend; no association labels captured |
| Packaged v5 photographs | Eight distinct local photographs; all file sizes and SHA-256 match the manifest **and retained attachment metadata** | Max 640px derivatives; no real specimen or cultivar claims |
| Existing Taxonomy Review at `http://localhost:15278/#/media` | Real authenticated React/FastAPI UI with two local images and three cover relationships; desktop gallery, preview, detail, deletion guard and linker inspected | Separate synthetic dataset/source, not v5 or a Media-owned environment |
| Screenshots | Actual 1440×844 gallery, preview, detail and linker; 1024×844 error/filter states | Tablet gallery capture is an error state, not populated gallery evidence |
| Design study | Proposed framing, density, overlay, detail and mobile layout using captured data and existing six-theme tokens | No API writes, saved views, add/edit/link/primary/delete simulation |

`make feature-review-status` correctly refused: `florabase-feature-review` belonged to
`/home/alessandro/.codex/worktrees/c902/florabase`. Only its database was running; port 15174 refused
browser connections. The independently owned Taxonomy Review was initially healthy and already
authenticated. During inspection its API became unavailable, then reloading port 15278 also refused
connections; a later attempted read found the c902 DB container no longer present. This task issued
**no** stop/remove/reset/up/seed command. Treat the changing runtime and generic media error as an
environment limitation, not a diagnosed product regression.

**Initial-phase limitation, now resolved by isolation:** neither foreign environment was adopted or
repaired. The operator's continuation authorized a distinct Review alternative. The small
`live-review.py` adapter reuses the existing Environment ownership, volume, network, source, health
and migration checks, specializing exact identities only in its process/runtime copy. Media's
`florabase-media-review-1d44` project uses loopback 15280, its own `florabase_media_review` database,
and its own media/dependency volumes. No Sourcing slot or standard Review volumes are reused.

## Live continuation: dataset, isolation and shared UI coordination

The new Review is initialized from this candidate's current source and unchanged v4/80 + v5/252
fixtures. It has **35 assets, 27 stored locally, 8 external-only references, 20 record links,
11 primary uses and 2 Identity covers**. One cover is unlinked; the other is a secondary SeedLot
image. A retained Aloe original now has two same-Identity record links with independent captions.
The original photo SeedLot has more than one image with only its explicit original primary.

There are **eight distinct licensed photographs**, ten photographic asset rows (including two
deliberate cover-upload reuse cases), and 17 explicitly generated drawings. Sixteen new calibration
drawings test portrait/landscape/square geometry, a long title and >24 pagination; they are not
botanical photographs and do not establish a 35-distinct-photograph UX. The unchanged v5 photography
is still at most 640px. Source attribution/licences/modification notices are retained exactly.
No remote acquisition, production collection data or botanical provenance was introduced.

Repeat seed preserved IDs/counts/ledgers. Asset originals match attachment hashes; actual service
responses confirm both kinds of references block deletion. Six runtime negative checks reject
foreign role/project/source/origin/database configurations; three host identity checks refuse
before Docker access. Unauthenticated real HTTP requests for an original and thumbnail both return401.
Four focused adapter tests cover host refusals, canonical-fixture preservation, private credentials
and missing-credential refusal for a retained owner. These are scoped checks, not a canonical gate.

The operator-authorized coordination with **Audit and consolidate Florabase UI** confirmed:

| Ownership | Boundary |
| --- | --- |
| Global UI audit (`bc88`) | Proposed shared PageHeader, DirectoryTools, TaskDialog and QuickPreview contracts; no shared implementation in either review phase |
| MEDIA-VISUAL-001 (`1d44`) | Photographic card framing/density, Media preview content, Media detail layout, association labels, return-context behavior and scoped acceptance evidence |
| Integration | Link shared findings into the global audit; implement any shared primitive correction once in the owning increment after operator approval, then consume it from Media |

The audit's separate Review is at 15279. This task writes no audit records/settings/files/resources.
Both environments' default development cookies share the `localhost` host even on different ports;
concurrent sign-ins replaced each other's session. Capture batches are coordinated in sequence and
expired-session screenshots are excluded. This is a Review-environment constraint, not evidence of
broken Media pagination. Host memory/swap pressure is also recorded separately from product defects.

### Assumptions revised by actual contracts/data

- A gallery “Set as cover” operation is **not** available: the Identity cover workflow uploads a new
  asset or creates an external cover reference. Do not add existing-asset assignment as visual polish.
- A 35-asset fixture is not a 35-photograph library. Filtered real-photo evidence and generated layout
  stress evidence must be shown separately. External-only placeholders remain honest and useful.
- The design study's abbreviated sidebar is not authoritative shell geometry. Final column count
  must use the real sidebar width, readable card widths and existing control wrapping, not a fixed
  screenshot-derived number. Four/three/two columns remain a target pending implementation.
- “Unlinked” remains a record-link facet: the actual cover-only asset cannot be deleted. No orphan
  cleanup or automatic replacement primary may follow from that label.
- A contained 320px thumbnail is cheap but cannot prove high-resolution inspection. Current detail
  loads the original; proposed preview needs an explicit original-load boundary and clear quality limits.

### Functional and accessibility risk priorities

The global audit reported a P1 in the real Media deletion confirmation: its first focused control
is the destructive button. Source inspection agrees: Media renders Delete before Cancel, and
PhotoDialog focuses the first available control. Media independently reproduced and cancelled this
in its owned Review: `document.activeElement` was `BUTTON`, text `Delete media asset`. Cancel
restored focus to the trigger and the asset remained. The smallest proposed correction is safe initial
focus on Cancel, preferably through existing dialog behavior or local control ordering; do not
duplicate a global dialog API. No deletion is required to establish this issue.

Other implementation risks are loss of filtered gallery position on detail return, stale preview
responses naming the wrong image's records, focus return to an unmounted card, truncation removing
access to the full title, nested overlay traps and uncontrolled original/remote image loading.
The bounded plan must cover each explicitly rather than treating visual approval as functional proof.

### Completed current-application observations

| Scenario | Confirmed result | Evidence / implication |
| --- | --- | --- |
| Many assets | Actual pages show 1–24 and 25–35 of 35 | `all-page-1-1440.jpg`, `all-page-2-1440.jpg`; calibration rows are labelled drawings, not extra photographs |
| Photo subset | Search `Review v5` + Local yields eight actual distinct photographs | Botanical Light/Dark at all three requested viewport settings; matching proposal now uses the same ordering, titles and current link counts |
| Tablet reload | At 1024×844 the actual shared header is **880px** high and the photo grid starts at **1102.8px** | `tablet-reload-1024.{jpg,json,txt}`; a real P1, independently confirmed by the global audit |
| Header root cause | Legacy `styles.css` sets column direction below 68rem; normalization keeps 16rem/38rem child flex bases | Those become vertical heights: 256 + 608 + 16px gap = 880px. Shared owner must reconcile direction/bases once |
| Desktop preview | Keyboard Enter selects the actual Aloe thumbnail and counts two links; the image remains only 8rem high and no linked record names are shown | `preview-aloe-1440.jpg`; existing thumbnail-only gallery/preview loading is efficient but inspection is cramped |
| Original detail | Actual 480×640 Aloe original is displayed with `object-fit: contain`, including at 390px | Detail captures at 1440/1024/390; mobile card activation goes straight to this original-loading route |
| Record associations | Two actual SeedLot names, independent captions/order and primary/secondary state are displayed | Aloe detail and SeedLot Photos captures; source/cover ownership stays distinct |
| Cover-only | Unlinked filter includes the Lavender cover; detail reports 0 record links, 1 cover and disabled deletion | `cover-only-unlinked-390.jpg`, `cover-only-detail-1440.jpg`; Identity Media shows the same cover separately from collection-record photos |
| Filters/mobile | Labelled Source/Record links/Target drawer; Local + Unlinked narrows eight photos to the actual unlinked tomato | `filters-390.jpg`, `unlinked-photo-390.jpg`; no need for unsupported taxonomic facets |
| Browser Back | From mobile direct detail, Back restores `q=Review v5&kind=local` | `mobile-back.json`; **focus remains at page root**, so invoking-card focus needs explicit restoration |
| Media breadcrumb | Returning through the breadcrumb yields `#/media` and an empty search | Independently reproduced in the live browser; this differs from Back and loses the working filter context |
| Linker | Seven supported target types are available; Escape dismisses and returns focus to Link to another record | `linker-1440.jpg`; no link write was submitted |
| Themes | Actual owned Media captured in Botanical Light/Dark at three widths and Herbarium/Mineral Light/Dark at desktop | Additional global-audit Media captures are attributed supplements, not substituted for owned data |
| Privacy/failure | External-only detail initially has zero image elements; explicit Preview once against the controlled `.invalid` reference becomes Image unavailable | Before/after external reference captures; no real provider outage or saved snapshot is claimed |

The photograph subset confirms why cropping needs a boundary: Fill can trim flower/leaf edges in
portrait photographs. Keep 4:3 composition at thumbnail level, and make the entire uncropped frame
available immediately in preview/detail. The long real attribution and actual record captions also
invalidate an always-short inspector assumption. The study now keeps Open media details and Close
in its preview header; it uses real association labels rather than placeholders. This changes only
the proposal artifact, not the application.

Viewport requests are 1440/1024/390×844. Screenshot raster sizes can exclude scrollbar pixels;
the later JSON sidecars record the actual DOM viewport independently. These are viewport tests,
not physical touch or browser-zoom evidence. Browser capture timeouts were recovered and do not
establish product failures; the tablet issue was specifically repeated after a clean reload.

## Functional inventory and truthful semantics

| Surface | Existing supported behavior | Design boundary |
| --- | --- | --- |
| Media Gallery | One reusable MediaAsset per card; 24 per page; fixed newest-created ordering with ID tie-break; title/filename/attribution search | No species/tag search, custom sort, batch selection or list mode |
| Filters and Saved Views | Source: local/external; record links: all/linked/unlinked; Target: Collection or one of seven target types; URL and v1 Saved Views | Source means origin kind, not whether bytes are stored; external with saved copy is still external |
| Quick Preview | Desktop selected asset, thumbnail, source and aggregate record/cover counts; Open media details | At ≤1024px a card navigates directly to detail; it does not currently open a preview |
| Asset detail/edit | Shared title, attribution, licence; available MIME/size/dimensions; local image original; actual record/cover references | No capture date, identification, tags, shared description, media History tab or association inference |
| Link management | One target at a time; target search/pagination; caption/order on each link; unlink separately | Exactly SeedLot, Sowing, Plant, PlantGroup, Event, Harvest, Supplier; Identity is not an ordinary link target |
| Primary photo | Explicit per SeedLot, Plant, PlantGroup, Harvest or Supplier | No global primary switch; Sowing/Event have no primary API |
| Identity Media | Separate single cover plus a bounded gallery from actual linked collection records | No inherited media ownership or arbitrary direct Identity attachments; cover management stays on Identity |
| Contextual Photos | Shared PhotosSection, upload/external/link-existing paths, contextual caption/order and eligible primary controls | Reuse compact photo presentation; verify each consuming screen before restyling globally |
| External references | Protected stored snapshot if present; explicit Preview once otherwise; save/refresh/remove copy actions | No external requests on gallery/hover/search; saved copy preserves external kind and attribution |
| Deletion | Zero record links **and** zero covers required; server guard/409; pending-delete and cleanup retry | Unlink retains asset; cover removal retains asset; no cascade or inferred safe deletion |

Collection filter includes SeedLot/Sowing/Plant/PlantGroup/Event/Harvest links and excludes Supplier-only
assets. Cover-only assets are unlinked. The UI's `collection_link_count` is the record-link count,
including Supplier; display it as “record links” to avoid a second definition of Collection.

Current source anchors: `frontend/src/media/{MediaScreen,MediaPreview,MediaPicker,MediaLinker,MediaEditor}.tsx`,
`frontend/src/media/{api,targets}.ts`, `frontend/src/photos/PhotosSection.tsx`,
`frontend/src/botanical-identities/{IdentityMedia,IdentityRecordMedia}.tsx`,
`frontend/src/photos/BotanicalIdentityCover.tsx`,
`backend/src/florabase/media/{service,schemas,api}.py`, `docs/media-library.md`, `docs/ui-contract.md`.

## Pre-implementation prioritized findings

Severity distinguishes observed problems from proposed improvements. No P0 data-loss or dangerous
functional behavior was established; this is not a certification that none exists.

| ID | Priority | Evidence and user impact | Bounded response |
| --- | --- | --- | --- |
| M01 | P1 | Desktop grid reserves a permanent 15–19rem inspector even with nothing selected. Actual screenshot shows a large empty preview while photography occupies a small fraction of the workspace. | Give the gallery the full width; show preview only on deliberate activation. |
| M02 | P1 | Selected Quick Preview image is 8rem high versus 12rem gallery images. Browser confirms that inspection makes the image smaller; aggregate counts provide no direct associated-record inspection. | Larger contained image, source/credit, actual record names and covers loaded on demand from existing detail endpoint. |
| M03 | P1 | Live Media breadcrumb clears query/source filters. Mobile browser Back preserves filters but leaves focus at page root. ≤64rem card activation directly loads original detail. | Restore query, facets, page, scroll and invoking-card focus through explicit return context; preserve working Back behavior. |
| M04 | P2 | Gallery cards have 0.65rem padding, 1rem gaps, 12rem contain frames and several text rows. Portrait photos show side gutters; actual narrow preview compounds the loss of image area. | Stable 4:3 edge-to-edge frames, 12–16px gutters and compact two-line titles; full framing in preview/detail. |
| M05 | P2 | Full detail image is constrained to 20rem (17rem mobile), alongside a long facts list. The real cover-only detail makes relationships/deletion less scannable than the image. | Photo gets roughly two-thirds of upper desktop content, bounded by viewport height; concise provenance beside it, relationships below. |
| M06 | P2 | “Unlinked”, cover counts and primary actions are correct but easy to conflate; real two-photo Review has zero record links yet three covers and blocked deletion. | Separate “Record links”, “Identity covers” and per-record “Primary” labels; retain explicit delete reason and independent actions. |
| M07 | P2 | v5 contains eight external-only references: almost half of its 17 cards cannot display local photography. Filling these cards from the network would violate privacy and distort performance. | Keep honest placeholders with source host; expose current Source filter; stored-copy facet requires separate API scope. |
| M08 | P2 | Original v5 has 17 assets. The isolated extension now proves 35-row pagination, shared relationships and cover-only cases, but still only eight unique photographs and no saved external copy. | Use current evidence honestly; defer high-volume photographic and saved-copy acceptance until those specific fixtures are available. |
| M09 | P2 | Current read failure says “could not complete this media change,” even on a gallery read; observed during runtime loss. | Use operation-specific loading/error/empty copy in future polish; preserve retry, prior successful data and explicit failure provenance. |
| M10 | P3 | Dense mode, global next/previous lightbox, contact-sheet list and broader facets may help large libraries, but are not supported by this dataset evidence. | Defer pending a proven task and explicit contract decision. |
| M11 | P1 | Clean reload at 1024×844 produces an 880px shared header; no gallery image is initially visible. Legacy column direction conflicts with normalized child flex bases. | Global audit F09 / Wave A0 owns the shared header sizing correction and cross-family checks. Media consumes that correction; no local masking override. |
| M12 | P1 | Permanent-delete confirmation initially focuses Delete media asset, independently reproduced and cancelled in Media and the global audit. | Safe initial focus on Cancel; Media owns the confirmation consumer, coordinating any shared dialog API once. Keep confirmation, server reference guards and retry unchanged. |

The existing compact header, labelled Filters/Saved views/Add action, separate cover references,
protected thumbnail paths and explicit remote consent are strengths to retain. No sidebar move.

## Proposed v0.1 visual direction

### Gallery and compact header

Use the existing PageHeader/WorkspaceIntro and DirectoryTools. One short title, flexible search,
Filters, Saved views and Add new media; reuse the current right drawer and live removable chips.
Keep the search placeholder truthful: “Title, filename or attribution.” Move repeated retention
explanation into contextual help; preserve a visible explanation when Unlinked is active.

Use one photographic grid, without a permanent inspector or nested card borders. At the reference
widths aim for four columns at 1440, three at 1024 and two at 390; allow available content width and
actual zoom to determine final wrapping. A 4:3 image frame reuses the accepted compact Photos grammar.
Use `object-fit: cover` only for thumbnail composition, explicitly showing the uncropped photograph
on activation. Portrait cropping must be checked on these actual photographs; no persistent focal
point editor or masonry layout. The study includes Fill/Fit comparison solely to make that decision.

Titles retain original shared text, wrap to two lines without changing stored data, and have full
text available in the preview. Do not turn a free-form title into an asserted scientific name or
automatically italicize it. A single secondary line distinguishes Local, External with saved copy,
or External not stored, with actual record and cover counts. A small credit line or accessible
caption must retain required photo attribution; full credit/licence/modification notice stays nearby.
Retain stable placeholder geometry, visible focus and a text equivalent for every image state.

### Quick Preview and detail

Recommend **one on-demand dialog** activated by click, tap, Enter or Space; avoid a hover-only popup.
Desktop: contained photo roughly 60% of the dialog, concise source/attribution and actual linked
records on the right; Close and Open media details remain visible. Mobile: the same information
stacks in a full-height scrollable dialog. Keep one predictable scroll region and no nested modal
editing: Open details closes preview first. Focus enters a sensible control, Escape dismisses only
the top overlay, and closing returns to the invoking card.

The current list payload has counts, not record labels. Fetch existing `getMedia(id)` only when a
preview opens; abort stale requests and show loading/error/Retry without replacing the selected
image or claiming absent links. Reuse the house TaskDialog/PhotoDialog focus behavior; do not create
a new overlay framework. Initial preview uses the protected thumbnail. Explicit Enlarge or detail
may request the original for that one asset; no originals on grid mount or hover. With a 320px
thumbnail, an enlarged preview must not promise original detail before that explicit load.

Detail uses a large contained photograph, full title, source kind, genuine available technical
metadata and complete attribution/licence. Do not label `created_at` as photographed date or
`fetched_at` as acquisition. Unknown values say “Not recorded” where useful, never inferred values.
The study photos are only 640px: increased display area cannot manufacture resolution.

Place actual association rows below, with record type/name/link, that link's caption/order and
primary status. Keep Edit shared metadata apart from Edit link details. “Set as primary for [record]”
exists only on eligible rows. Identity covers get their own section linking to Identity Media;
there is no global “Set as cover” switch. Link to another record reuses MediaLinker. Asset deletion
stays in a separated danger section with current server reference counts, confirmation and retry.
External save/refresh/remove copy remains a separate explicit operation with its existing safeguards.

### Mobile, themes and state behavior

At 390px retain two columns and 44px controls; search uses its own row, other header controls wrap.
Filters use the existing accessible full-height drawer. Preview/detail put the photograph before
metadata, with captions, licence and real record links reachable by normal scrolling. Retain the
existing application navigation; the study's abbreviated shell does not propose new mobile navigation.

Reuse all six delivered semantic token sets (Botanical/Herbarium/Mineral × Light/Dark), shared radius,
typography and focus. Photos are never inverted or tinted. Display selection by outline and text,
not color alone. Loading reserves frame geometry; failed thumbnails do not auto-load originals or
remote URLs. Distinguish empty library, no matches, missing asset, external-only, preview failure,
pending deletion and interrupted copy cleanup. Preserve prior good content on retryable failures.

## Filter decision table

| Facet or control | Current contract | Decision |
| --- | --- | --- |
| Local / External origin | Existing kind filter | Keep; an external snapshot remains External |
| All / Linked / Unlinked record links | Existing association filter | Keep; cover-only remains Unlinked |
| Collection / one record type | Existing target filter | Keep exact meaning; rename visible label “Linked record type” if clearer |
| Used as Identity cover | Counts available, no filtering API | Useful candidate; separately approve API/URL/Saved View contract before adding |
| Primary use | Known per detail link, no list facet | Defer; any future filter must mean primary on at least one eligible record |
| Stored bytes / external-only | Distinct from origin; no exact list facet | Useful candidate, separate approval; never relabel kind as storage |
| Exact botanical record / Identity | Target picker supports explicit records, global gallery does not | Defer exact association facet; never infer from filename/title or ancestry |
| Missing attribution / licence | Fields exist, no completeness definition/filter | Defer until “missing” and licence rules are agreed |
| Fit/Fill, density | Display preference, not evidence filter | Study comparison only; no persisted preference necessary for first slice |
| Date, species/genus/family, tags, videos/documents, batch operations | No approved Media contracts | Exclude; mockup controls do not establish capability |
| Sorting, next/previous across pages, new list view | No current user-facing contract | Defer; retain fixed ordering and page boundary |

## Bounded implementation plan after direction approval

| Order | Slice and reach | Acceptance and checks |
| --- | --- | --- |
| 0 — completed | Media-owned populated Review and additive relationship/layout fixture; ordinary app, existing domain services and licence metadata. | 35 assets, 20 links, 2 covers; repeat IDs preserved, scoped ownership checks passed. Eight distinct photographs remain a stated limit. |
| A0/B0 — prerequisites | Consume the global audit's shared header sizing correction (A0) and safe initial-focus contract (B0); correct the Media destructive confirmation consumer once. | Tablet header fits content; gallery starts in viewport; Cancel receives initial focus; Escape/Cancel restores trigger; no weakening of deletion eligibility. |
| 1 | `MediaScreen.tsx` and Media-scoped CSS: full-width 4:3 grid, compact metadata and stable empty/error states. Reuse header, filters, Saved Views and existing API. | Search/facets/24-row pagination/URL restoration unchanged; responsive card/focus checks on real photos. No API or dependency change. |
| 2 | On-demand preview using existing detail read and house dialog; preserve gallery position/selection return. Reach MediaScreen/MediaPreview and focused interaction tests. | Click/keyboard/tap, Close/Escape/backdrop/focus, loading/failure/aborted stale detail, exact record links, no auto remote fetch; grid/preview/original request boundaries. |
| 3 | Media detail layout and context labels; reuse editor/linker/picker and existing per-record primary operations. | Uncropped photo, full attribution, independent link captions/order, clear target-specific primary and cover references; blocked/pending delete and copy cleanup regressions. No write semantics change. |
| 4 | Audit contextual consumers; change only reproduced inconsistencies. PhotosSection, MediaPicker, IdentityMedia/Cover and target-specific Photos call sites are regression reach, not automatic redesign scope. | SeedLot, Sowing, Plant, PlantGroup, Harvest, Supplier and Event supported photo entry; Identity single cover independent; no invented primary on Sowing/Event. |
| 5 | Operator acceptance at 1440/1024/390, all six themes, keyboard and actual zoom. Update evidence and acceptance coverage. | Review exact final diff; only after separate authorization run canonical gate and delivery lifecycle. |

Historical design-stage boundary: MEDIA-VISUAL-001 was **planned** at this point. The later operator approval above authorizes the current implementation phase; verification remains separate. No additional dependency, backend schema,
new media type, global tagging, batch API, navigation move or global style normalization is needed for
the proposed first three product slices. If defects require API changes, return with that concrete scope.

## Dataset completion plan and licences

The original v5 snapshot covers eight real photographs, four portrait and four landscape; the ninth
local asset is a generated 96×96 square with four links. Seven photographed assets have one primary
record use, one photograph is unlinked, and one external reference is unlinked. It has no covers or
saved external snapshots. These measured gaps supersede aspirational examples in the reference images.

First reuse existing photographs as **separate relationships**, not duplicate assets: several images
on one synthetic record, a genuinely shared photo asset, several Identity covers including cover-only,
and saved-copy examples only through an explicit guarded offline test fixture. Include supported
targets, long captions, unknown metadata, retained primary/non-primary distinctions and deletion/copy
failure states. Do not make a real photograph stand in for a verified cultivar or owned specimen.

For >24 assets, acquire additional distinct, suitable licensed botanical photographs with explicit
source review; target roughly 30–50 only if available. Include genuine square photos and higher
resolution where practical. Packaging a source photo is not permission to fetch it from the live app.
Do not clone files, count links as assets, crop one photograph into nominally different assets, or
fill external-only cards with unseen fetched photos. Broken/unavailable external cases should use
an explicitly labelled controlled fixture; never call a live provider broken without evidence.

No new photographs were acquired here. Eight existing JPEGs are reused by relative reference in
the study, without modification. Their earlier resizing/recompression/EXIF removal remains disclosed
in captured attribution and the [NOTICE](../scripts/fixtures/botanical-v5/NOTICE.md) and
[per-photo manifest](../scripts/fixtures/botanical-v5/media-manifest.json). Creators include
Merstel007, Daria Sitnikova, Caroline Léna Becker, Homoarborea, Cliff Hutson, Lena Jaginyan and
AnRo0002, under their recorded CC0 / CC BY 2.0 / 3.0 / 4.0 licences. No application licence overrides
those terms. Source licences were documented by the v5 author on 2026-10-22; this task verified
packaged integrity, not a new legal or remote-source audit. Taxonomy screenshots retain its own
attribution; its two photographs are not substituted for the v5 files.

## Historical live-review validation and limits

- Fresh owned Review migrated to `20261013_0042`; v4/80 and v5/252 plus additive Media fixtures are
  ready. Repeat seed preserved IDs/relationships; hashes and reference eligibility passed. Four
  adapter tests, six runtime refusal cases, three host refusal cases and both unauthenticated image
  HTTP401 checks passed. Focused Ruff, Python syntax, feature graph and whitespace checks passed.
- Real current-application evidence covers three widths, Light/Dark and representative palettes,
  actual gallery/preview/detail, pagination, mobile filtering/Back, Identity covers, contextual Photos,
  guarded delete eligibility, safe cancellation, linker focus return and controlled external failure.
  Fixture initialization wrote only Media-owned synthetic data; browser review submitted no domain
  mutation, delete, primary change, unlink or copy-save/refresh/remove operation.
- Updated proposal captures are visibly labelled as design, matched to the same eight photographs
  and actual labels/counts. They prove artifact rendering/interaction, not an implemented redesign.
  The original 30 captures remain as historical evidence with their earlier dataset limits.
- No canonical FULL gate, staging, commit, push, PR or merge ran. Physical touch, screen reader,
  actual 125%/150% zoom, saved external-copy operations, pending-delete/copy-cleanup failure/races and
  high-volume/high-resolution photographic performance remain explicit future acceptance limits.
  The retained 35-asset fixture does not substitute generated drawings for a large photo collection.

**Handoff: `MEDIA_VISUAL_001_LIVE_REVIEW_READY_FOR_APPROVAL`.** This is current-application evidence
and an implementation proposal. Operator design approval, product implementation, canonical
verification and protected delivery remain separate phases.


## Completed implementation acceptance evidence

[Updated before/after gallery](review/media-visual-001/gallery.html) contains **31 inspected actual
implementation captures**, alongside the preserved 42 previous live/proposal captures and original
30-capture gallery. Product captures are distinct from the original HTML proposal. Saved pixels were
inspected; early-paint and mismatched viewport captures were replaced rather than treated as proof.
[Capture manifest](review/media-visual-001/implementation/capture-manifest.json) records actual raster
sizes and exact DOM viewport/geometry sidecars. Browser capture rasters can omit scrollbars or be
proportionally scaled; these are not real browser-zoom measurements.

| Requested viewport | Final header | Grid columns / start | Observed behavior |
| --- | --- | --- | --- |
| 1440×844 | 98px | 4 / y237 | Full-width photographic gallery; no permanent preview rail |
| 1024×844 | 186px | 3 / y325 | Search, filters, Saved Views and Add wrap without the old880px header |
| 880×844, expanded sidebar | 186px | 2 / y325 | Controls remain visible; no horizontal overflow |
| 880×844, collapsed sidebar | 98px | 3 / y282 | Uses the available width, retaining the Show navigation control |
| 390×844 | 212px | 2 / y446 | Compact title/controls; full description hidden only at narrow width; native filter drawer |

Expanded/collapsed navigation was inspected without moving Media's destination. Sidebar widths are
user-controlled (220/248px observed), so column count follows available content width rather than a
nominal device label. The 10rem search basis was chosen against the measured880px/248px-sidebar row;
it wraps gracefully when less space remains. The Unlinked explanation is retained with its filter,
removing repetitive text above the photographs. Three active mobile facets use 260px of header;
these existing chips remain visible and independently removable rather than clipped.

All six actual Botanical/Herbarium/Mineral × Light/Dark combinations were inspected and captured.
Gallery image elements use only protected lazy thumbnails with 4:3 cover frames. Portrait Aloe and
landscape Basil Quick Preview load one protected original after deliberate activation, using contain
framing and safe Close focus. The preview shows real labels, per-record primary state and distinct
cover references; the cover-only Lavender remains unlinked and deletion-blocked. The detail original
is prominent, metadata/attribution are intact, and its link actions remain target-specific.

Actual navigation covered keyboard-open, Close/Escape, preview→detail, linked SeedLot→Photos→browser
Back, Media breadcrumb return, mobile card→detail, Back/Forward/reload, filtered and offset 24 return.
The initiating card regains focus. The live URL-removal check found an inherited-facet fallback bug;
Media now supplies detail-filter fallback only on detail routes. Removing facets from a directory URL
clears them; Back restores them. The real App regression covers both outcomes.

Actual first/second pages display 1–24 and 25–35 of 35. Mixed calibration shapes remain explicitly
synthetic; they do not inflate the eight-photo claim. External preview has no image element before
Preview once; no provider request or saved-copy operation was submitted. Delete confirmation was
opened with mouse and keyboard, focused Cancel, then cancelled by Escape and Cancel with trigger
focus restored. No live asset deletion, unlink, primary change or collection mutation was submitted.
Successful confirmation, 409 conflict, blocked references and pending retries are covered by UI tests.

### Environment, access and preservation

Only `florabase-media-review-1d44` was restarted, using its guarded exact source/project ownership;
DB schema remains 20261013_0042. No seed/reset, foreign-resource adoption or environment cleanup ran.
The temporary credential file had disappeared; the operator explicitly approved recovery of the
existing synthetic `media-review` owner. A one-off exact-owner/project/source/origin/database-guarded
transaction set a new random password and revoked its four old sessions. The owner ID, account role,
collection, media and relationships were preserved; no product authentication code changed. The
new private access file is referenced in the ownership guide and is outside the served gallery.

A final read-only check compares **every asset-detail field** to the earlier snapshot: all 35 assets,
20 links, two covers, titles/licences/attribution, captions/order and explicit primary flags are
unchanged. All six foreign-runtime refusals still pass. See
[dataset-check.json](review/media-visual-001/implementation/dataset-check.json).

### Final checks and remaining release work

- **122 tests / nine files passed** across Media, Photos, primary visuals, Identity media,
  DirectoryTools and Saved Views. After the final route/composition refinements, **40 affected tests /
  three files passed**, including the real App's keyed remounts, URL removal, Back/Forward/reload,
  initiating-card focus, safe confirmation and original/thumbnail request boundaries.
- Full frontend ESLint passed; final affected-file ESLint, Media Prettier, TypeScript and production
  frontend build passed. Early failures were fixed without suppressions, weakened assertions,
  quarantines, arbitrary sleeps or dependency changes. The routing regression preloads the real
  Media chunk to exclude cold compilation latency from its routing/focus contract.
- Feature graph:116 valid entries. `git diff --check` passes; staged diff is empty. Backend/API/schema
  are unchanged, so no generated API or migration drift check was needed. No canonical FULL ran.

[Validation/source hashes](review/media-visual-001/implementation/validation.json),
[focused test log](review/media-visual-001/implementation/focused-regression.txt),
[final affected tests](review/media-visual-001/implementation/final-navigation-tests.txt) and
[build log](review/media-visual-001/implementation/frontend-build.txt) are retained.

Operator visual acceptance is next, then independent QA and one separately authorized policy-selected
canonical gate. Physical-device touch, assistive technology and real 125%/150% browser zoom remain
unverified. High-resolution/high-volume photographic performance, live pending-delete/copy-cleanup
failure/race scenarios and live saved-copy mutation acceptance remain separate checks. The v5 photos
are at most 640px. Shared header/dialog normalization for other consumers stays with the global UI
system work; this Media-local correction is not a global fix. No release-blocking Media defect is
known from the completed scope, but these checks do not substitute independent QA or acceptance.

### Final Quick Preview local-copy enhancement

The operator explicitly approved a small extension: an external reference without a saved copy now
offers **Save local copy** in Quick Preview. The button states that it contacts the external source
and stores a protected copy. It calls the existing authenticated `saveLocalCopy` request with the
current CSRF token; no external-fetch logic was added to React. A ref guards rapid duplicate submits.
Pending text disables the action; API/network failures stay actionable in the dialog; on success the
returned asset metadata replaces the preview's source state, the existing protected original is
shown, the gallery is refreshed, filters/page/selection remain in place, and focus moves to the
success status. Local assets and external assets already holding a copy do not show the action.
Detail retains the existing Refresh/Remove controls.

Focused tests now pass 42 cases across Media, route and URL modules. They exercise CSRF, explicit
activation/no remote image request on render, local/already-saved/unsaved cases, success/failure,
pending/double-click, protected-image transition, open-preview retention, and exact filtered page URL
and focus after refresh. A real Quick Preview screenshot of the unsaved external reference and its
retryable failure was inspected in the authenticated Review. Two v5 Wikimedia sources returned the
existing “The external image is unavailable. Try again.” response from the Review backend. No saved
copy was created, and no association/metadata write occurred. Thus the live failure state is confirmed;
real upstream success presentation remains unverified. The mock/API-response success path is covered
by focused UI tests and is not reported as a live external-fetch success.

The Media-owned Review was rebuilt and restarted through its exact ownership-guarded adapter. It
remains at schema `20261013_0042`; no fixture reseed/reset or other project lifecycle action ran. The
existing v5 dataset and relationship ledger were checked read-only after both failed requests.
Screenshots for previous widths/themes and P1 states remain in the implementation capture set; the
new error screen was visually inspected live. Actual external success, device touch, AT certification,
and real browser zoom remain explicit acceptance limits.

**Handoff: `MEDIA_VISUAL_001_IMPLEMENTATION_READY_FOR_REVIEW`.** All changes remain unstaged and
uncommitted. No canonical FULL, PR, merge or protected delivery ran.
