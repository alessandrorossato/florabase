> **Superseded review snapshot:** see [28 October final refinements](refinements/README.md), [current gallery](refinements/index.html) and [current verification](refinements/verification.md). The evidence and source hashes below belong to the earlier candidate.

# UI System v1 — production Wave 1 review

Gate B and Proposal B are approved. This wave migrates the **actual Dashboard, Seeds and Plants**.
It is a review candidate, **unstaged and uncommitted**. UI-SYSTEM-001 remains `in_progress`;
canonical FULL and delivery wait for the operator's review.

- [Actual authenticated production Review](http://localhost:15279/#/dashboard).
- [Before/after and responsive evidence](http://localhost:15283/wave1/index.html).
- [Developer showcase and generated example](http://localhost:15284/ui-lab/#/components).
- [Separate two-image Review](http://127.0.0.1:15285/#/dashboard).
- [Verification, evidence limits and ownership](verification.md).
- [Approved Gate B architecture and historical prototype](../gate-b/implementation.md).

## Source and scope

Branch `feat/ui-system-v1`, base/current fetched main
`c77a1c5330de949168bf5f7c90d0f533af1bc320`: delivered Media #127 (`69814bb`)
and the independently delivered Media test-inventory hotfix #128 (`c77a1c5`).
Normal fast-forwards preserved the candidate. Progress and feature-registry additions were reconciled;
no CI implementation was copied. A preserved external candidate archive and digests remain under
`wave1-candidate-z1k7zf4p/` in the task visualization directory.

No production migration of Sowings, identities, Harvests, Locations, Suppliers or Orders.
Shared shell/control regressions reproduced in the real application were corrected: navigation
icons align with labels, the desktop-only collapse/account controls no longer crowd the mobile
brand bar, and collection card hover uses the theme surface rather than a primary-action fill.
Frozen destinations, sidebar groups and the mobile bottom navigation remain unchanged.

## Production composition and ownership

| Source / component                                                                        | Responsibility and real consumer                                                                                                                                                                                                                                                       |
| ----------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `frontend/src/components/DirectoryPage.tsx`                                               | Typed header, toolbar, selection, feedback, content, pagination and optional inspector slots. Seeds/Plants compose existing owning context/editor boundaries inside content. No API or domain rules.                                                                                   |
| `DirectoryRecords`, `DirectoryRow`, `DirectoryCard`                                       | Same records, stable keys and list ref; composed children preserve domain buttons and independent bulk checkboxes without nested controls.                                                                                                                                             |
| `DirectoryViewSwitcher`                                                                   | Labelled List/Gallery buttons with pressed state and typed decorative icons. Used next to real DirectoryTools search/filters.                                                                                                                                                          |
| `DirectoryInspector`, `TaskDialog`                                                        | Mounted on selection only; inline above 75rem, native modal below it. Remounted triggers and connected list fallback support focus return. Existing full mobile detail workflow remains.                                                                                               |
| `frontend/src/components/directoryPresentation.ts`                                        | Valid `view` URL parameter, then per-surface browser preference, then Seeds List / Plants Gallery defaults. Switching stamps an implicit previous mode before pushing the next history entry.                                                                                          |
| `frontend/src/bulk/useBulkSelection.ts`                                                   | Seeds/Plants opt into retaining checks on presentation-only history traversal. Canonical scope/visible IDs still reset unsafe choices; fresh navigation retains its existing reset policy. Other consumers keep the previous policy.                                                   |
| `frontend/src/seed-lots/SeedLotScreen.tsx`                                                | Owns acquisition, quantities/precision, storage/source, Active/History, search, Saved Views, bulk moves, creation/editing and all existing detail operations.                                                                                                                          |
| `frontend/src/plants/PlantScreen.tsx`                                                     | Owns individual/group distinctions, lifecycle, lineage, extraction/reintegration, transfers and editing. Group quantity never becomes an individual-record KPI.                                                                                                                        |
| `frontend/src/photos/RecordVisual.tsx`                                                    | Gallery caption distinguishes record/source primary image, identity reference cover and unavailable image. Existing protected/external privacy and fallback behavior remain.                                                                                                           |
| `frontend/src/collection/DashboardScreen.tsx`, `DashboardPhotos.tsx`                      | Existing four authoritative counts, membership summary, global search, Saved Views and Quick add. Up to eight stored photos link to Media assets. Five Next work entries remain; all six recent facts remain in an explicit native disclosure with Journal/History access.             |
| `backend/src/florabase/collection_views/{dashboard,schemas,service}.py`                   | Bounded read-only photo projection on the existing Dashboard endpoint. One SQL query deduplicates active stored attachments by SHA before applying the eight-item limit. Remote-only and pending-delete assets are excluded. No migration, provider request or fabricated record link. |
| `backend/openapi.json`, `frontend/src/api/schema.d.ts`                                    | Generated authoritative additive Dashboard photo contract, checked for drift.                                                                                                                                                                                                          |
| `frontend/src/styles/{directory,controls,normalization}.css`, `collection/dashboard.css`  | Existing semantic tokens, 4:3 image frames, flexible tools, compact rows, honest wrapping and theme surfaces. Compact directory titles use existing type-h2; Dashboard uses type-h1/type-metric and existing small/label types.                                                        |
| `navigationIcons.ts`, `Icon.tsx`, `App.tsx`                                               | Typed distinct destination pictograms, decorative to assistive technology; visible navigation names and existing routes remain authoritative.                                                                                                                                          |
| `ActivityPage.tsx`, `scripts/ui_page.py`, `ui-lab/`, `ui-pages/ScaffoldDirectoryExample/` | Approved thin activity recipe and generated directory example. Domain integration TODOs remain explicit; no fake production API or route registration.                                                                                                                                 |

Saved Views v1 still serializes **canonical validated filters only**. Presentation, selection and
pagination are not added to its schema. Reopening a saved filter URL uses the current browser mode
and existing page-one policy. Mode toggles retain the current search, lifecycle, type, selected record
where still valid and bulk choices. Browser Back/Forward follows explicit modes in history.
There is no new pagination mechanism: these existing inventories enumerate the loaded records;
shared slots and view-only URL changes preserve any caller-owned offsets rather than inventing a pager.

Dashboard images represent Media assets, not inferred specimens, native ranges or taxonomy links.
Local thumbnails are protected; saved external copies use Media's content-version URL. Attribution
and licence/source metadata are available in the image-attribution disclosure. A missing image
remains a labelled navigable asset. Fewer images remain fewer, including a real two-image Review.
The retained synthetic fixture's primary images can themselves be illustrations; a primary assignment
is not evidence of specimen provenance.

## Developer demonstration

The retained example was generated with:

```sh
make ui-page NAME=ScaffoldDirectoryExample ARCHETYPE=directory
```

Its actual TSX compiles and its focused keyboard/search/loading/error/retry test passes.
The showcase Components page exposes the example in “Generated directory · keyboard/search/state
example”. This is template coverage, not domain acceptance or proof of production migration.
The generator refuses overwrites and path/symlink escapes. A developer supplies typed domain
filters/records and API ownership; forms reuse EditWorkspace, FormSections, reference pickers and
validation focus. Activity chronology keeps occurrence/recorded-time semantics with the owning domain.
The default production build excludes both the lab and this example.

## Wave 2 recommendation — not implemented

1. Migrate Sowings as one bounded consumer after this review: retain germination precision,
   source SeedLot and create-from-sowing operations; compare its on-demand inspector and bulk scope.
2. Migrate Botanical identities separately, retaining each editor section's independent save and
   explicit source/cover controls. Keep taxonomy and range evidence separate from current collection.
3. Follow with Harvests/stored material and then Locations, each with its own domain acceptance:
   collected vs managed remainder, conversion/reversal, and physical hierarchy/scope rules.
4. Suppliers/Orders follow their reconciled sourcing workflows; do not turn them into collection cards.
   Maps, tree and calendar keep specialist controls and their existing evidence/interaction contracts.

Measurements, Phenology and Propagation can start from these typed slots and the scaffold once their
own data/URL/save contracts exist. No future endpoints, navigation destinations or domain behavior
were pre-built. Run the appropriate FULL gate after visual acceptance, then the requested repository
lifecycle; this handoff does not authorize staging, committing or delivery.
