# UI consistency polish

Current branch: `feat/ui-consistency-polish`, HEAD `cd5bf70`. The final operator
pass for items 33–47 is recorded first; the prior A–T receipt below is historical
and preserved. Final operator visual acceptance remains pending.
This pass changes frontend presentation, behavior tests and documentation only. The
initial Event target primary-photo summaries, backend tests and generated contracts
remain in the branch. UX-006 stays `implemented`; operator visual acceptance remains
pending. All work is unstaged and uncommitted.

## Final operator pass: items 33–47

| Item | Status    | Result                                                                                                                                                                            |
| ---- | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 33   | PASS      | Guided Start sowing reuses `sowingFormPanels` and shared fields; locked source, usage review and atomic endpoint remain.                                                          |
| 34   | PASS      | Guided Plant/PlantGroup reuse normal Essentials, date and notes field groups, plus existing explicit Origin and lifecycle constraints.                                            |
| 35   | PASS      | Collapsed shell retains a 32px desktop inset; expanded/resized uses the existing 24px inset.                                                                                      |
| 36   | PASS      | Desktop drag edge and accessible keyboard separator adjust width live without remounting the route; default 248px, minimum 220px, maximum 400px or 35% of viewport.               |
| 37   | PASS      | First successful Places load expands canonical World only, with existing selected-place ancestors; subsequent mounted-session interaction is retained.                            |
| 38   | PASS      | Shared body-portal More popover anchors to its trigger, bounds to viewport, separates destructive actions, closes outside/on Escape and preserves keyboard/focus behavior.        |
| 39   | PASS      | BotanicalIdentity editor has Identity, Reference, Native range and Media sections; nested Profile retains its sections/state. Normal desktop fixture fits without page scrolling. |
| 40   | PASS      | Geography Sites/Map create action lives in the shared page header and opens the existing Site editor.                                                                             |
| 41   | PASS      | Decimal/DMS selector validates both axes and converts into existing signed decimal payloads; unchanged values survive toggles without canonical rewrites.                         |
| 42   | PASS      | Labels uses a bounded control column and dominant preview, compact expandable guidance and naturally stacked tablet/mobile layout; print contract remains intact.                 |
| 43   | FOLLOW-UP | Supplier directory imagery/logo support is explicitly post-release; ownership/schema are undecided and no implementation is included.                                             |
| 44   | FOLLOW-UP | Location Direct here versus Including descendants remains a separate functional increment; direct usage behavior is preserved.                                                    |
| 45   | PASS      | Guided headings, source summaries, breadcrumbs and propagation path cards use the established display-name resolver without persisting labels.                                    |
| 46   | PASS      | Normal create/edit and guided forms reuse actual Sowing/Plant field groups and shared FormSections, with guided source/lineage wrappers.                                          |
| 47   | PASS      | Scoped rendered smoke review covered Geography, Sites, Map, Locations and Botany actions, previews, menus, sections and shell spacing.                                            |

The resize separator updates its announced maximum when viewport bounds change, even
when the chosen width stays unchanged; an automated regression checks route retention.
Native and server validation reveal/focus the owning hidden section, including nested
Profile forms. Mounted panels preserve input while navigating. Guided endpoints,
quantity certainty, germination constraints, lineage, receipts and existing second
Seed usage step are unchanged. New fields create no persisted record-name values.

### Final rendered matrix

The Codex in-app browser reviewed populated synthetic fixtures at all three required
viewports, using the isolated `florabase-ui-review` production-build project on
`http://localhost:18081`. Its database/media were disposable tmpfs. Normal operator
projects and data were untouched. Browser access succeeded. The temporary tab was
closed, viewport override reset and only this review project removed after QA.

| Surface                    | 1440 × 844                                              | 1024 × 844                                    | 390 × 844                                       |
| -------------------------- | ------------------------------------------------------- | --------------------------------------------- | ----------------------------------------------- |
| SeedLot → Start sowing     | Four panels and seed-usage step                         | Material/usage and reachable footer           | Essentials/material/usage and retained draft    |
| Normal Record Sowing       | Essentials and final shared quantity controls           | Essentials and final shared quantity controls | Essentials                                      |
| Sowing → Create Plant      | Essentials/Origin/Lifecycle                             | Essentials                                    | Essentials/Lifecycle and retained draft         |
| Normal Record Plant        | Actual form Essentials                                  | Actual form Essentials                        | Actual form Essentials; natural footer access   |
| Sowing → Create PlantGroup | Essentials and approximate count                        | Essentials and approximate count              | Essentials and approximate count                |
| Sidebar                    | Default; actual drag to 220/400; collapse               | Default; keyboard 220/358 bounds; collapse    | Existing navigation unchanged, no resize handle |
| Geography Places           | World expanded; collapse preserved across tabs; preview | World/continents                              | World/continents                                |
| Provenance Sites More      | Anchoring, destructive separation, keyboard/Escape      | Bounded anchored menu                         | Bounded anchored menu                           |
| Location More              | Preview, menu, keyboard/Escape                          | Bounded anchored menu                         | Bounded anchored menu                           |
| BotanicalIdentity Edit     | All four sections; all three Profile sections           | All four sections                             | All four sections, wrapping/natural scroll      |
| Geography Map              | Loaded map/marker and header action                     | Loaded map/marker and header action           | Loaded map/marker and header action             |
| ProvenanceSite create/edit | Decimal and DMS                                         | Decimal and DMS                               | Decimal and DMS                                 |
| Labels                     | Empty state and populated controls/sheet                | Populated stacked controls/sheet              | Populated controls and scrolled QR preview      |

QA directly corrected tablet quantity overflow, DMS part-label collisions, excess
Botany editor spacing and oversized Labels guidance. Fresh final CSS confirmed the
1440 × 844 Botany Cultivation view at default 248px sidebar has workspace
`clientHeight = scrollHeight = 796`; other normal-fixture sections had already fit.
DMS fields remain readable in a two-column part grid. Site dialogs and tablet/mobile
forms use their normal vertical scroll to reach footers. No page-wide horizontal
overflow appeared in the inspected final views; menu panels remained within viewport.
Toggling existing Site coordinates preserved `38.166667` and `13.350123`.

There are **108 chronological `operator-final-` review captures**, including preliminary
frames and corrected replacements, plus `operator-final-review.json`, saved outside
Git in `/home/alessandro/.codex/visualizations/2026/09/30/01a0f0f1-4d57-77c0-a34b-ee9a3d20d6e9`.
The final/latest/verified frames supersede earlier frames of the same surface.
Representative final proof: `operator-final-1440-botany-cultivation-latest.png`,
`operator-final-1024-guided-sowing-footer-final.png`, `operator-final-1440-labels-final.png`
and `operator-final-390-labels-preview-final.png`. These populated-fixture checks are
ready for operator acceptance; they do not claim exhaustive content or physical printing.

### Final checks and boundary

- Affected frontend tests: **174 passed across 10 files**. Updated compatibility tests:
  **58 passed across 5 files**. Final Seed/Labels changes: **51 passed across 2 files**.
- Final complete frontend suite: **304 passed across 33 files**, 2026-09-30,
  start 19:57:22, duration 124.57s (`/tmp/florabase-final33-suite-complete.log`).
- Frontend Prettier, zero-warning ESLint, strict TypeScript and production Vite build passed.
  Build includes `tsc -b`; final build log `/tmp/florabase-final33-build-complete.log`.
- Backend OpenAPI exporter `--check` and frontend OpenAPI TypeScript generator `--check`
  passed without drift against the preserved branch contracts.
- Feature graph: **81 features valid**; documentation formatting and `git diff --check` passed.

Earlier compatibility failures were fixed by navigating the new sections and asserting
required server-error reveal before continuing; no assertions, quantity protections,
timeouts or validation were weakened. An interrupted intermediate test run is not
counted as verification. The final full suite above completed successfully.

This final pass adds **no backend, API/generated-contract or migration delta**. Initial
branch Event-target photo summary backend/tests/generated changes remain preserved in
the branch manifest below. No backend suite or canonical feature gate was run for this
frontend-only final pass. UX-006 stays `implemented`; all changes remain unstaged and
uncommitted at `cd5bf70`. No push, merge, delivery or feature-finish occurred.

### Exact files changed by the final 33–47 pass

- `docs/product-roadmap.md`
- `docs/progress.md`
- `docs/ui-consistency-polish.md`
- `frontend/src/App.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/Propagation002.test.tsx`
- `frontend/src/UX001.test.tsx`
- `frontend/src/UX004.test.tsx`
- `frontend/src/botanical-identities/BotanicalIdentityScreen.tsx`
- `frontend/src/botanical-identities/ExternalBotanicalDataPanel.test.tsx`
- `frontend/src/botanical-profiles/BotanicalProfilePanel.tsx`
- `frontend/src/components/FormSections.tsx`
- `frontend/src/components/ReferenceInteractions.test.tsx`
- `frontend/src/components/ReferenceUI.tsx`
- `frontend/src/components/SidebarResizeHandle.tsx`
- `frontend/src/components/formValidation.ts`
- `frontend/src/components/sidebarWidth.ts`
- `frontend/src/geographic-places/GeographyScreen.tsx`
- `frontend/src/labels/LabelsScreen.test.tsx`
- `frontend/src/labels/LabelsScreen.tsx`
- `frontend/src/labels/labels.css`
- `frontend/src/plants/PlantFormFields.tsx`
- `frontend/src/plants/PlantScreen.tsx`
- `frontend/src/propagation/GuidedForms.test.tsx`
- `frontend/src/propagation/SeedLotSowingWizard.tsx`
- `frontend/src/propagation/SowingDescendantWizard.tsx`
- `frontend/src/provenance-sites/CoordinateFields.test.tsx`
- `frontend/src/provenance-sites/CoordinateFields.tsx`
- `frontend/src/provenance-sites/ProvenanceSiteManager.tsx`
- `frontend/src/provenance-sites/coordinates.test.ts`
- `frontend/src/provenance-sites/coordinates.ts`
- `frontend/src/seed-lots/SeedLotScreen.test.tsx`
- `frontend/src/sowings/SowingFormFields.tsx`
- `frontend/src/sowings/SowingScreen.tsx`
- `frontend/src/styles.css`

**35 files** in this pass; existing changes in these files are preserved.

## Prior A–T implementation and receipt

### Shared workspace and forms

The shared shell now keeps its max-width workspace left-aligned with a 24px desktop
inset; the surplus viewport space remains on the right. A containing editor can add
12px internally, keeping its content within the requested 24–40px range. Mobile uses
the existing natural document scroll and bottom navigation. Small Seed rows put
quantity and storage below the name, avoiding a location column that squeezed titles.

`FormSections` is a small navigation primitive inside each existing form. Exactly
one panel is visible, all panels remain mounted, and one underlying state/payload
survives direct tabs and Back/Next. Arrow keys and Home/End use roving tab focus.
Cancel stays available; the single Save/Create action appears only in the last panel.
Native validation reveals its first invalid field. API validation locations and the
existing client messages reveal/focus the corresponding hidden field. Next has a
separate DOM identity from Save so advancing to the final panel cannot submit it.

| Form                                            | Sections                                                              |
| ----------------------------------------------- | --------------------------------------------------------------------- |
| SeedLot create/edit                             | Essentials; Inventory; Acquisition; Origin; Seed details              |
| Sowing create/edit                              | Essentials; Material & location; Outcome & status; Cultivation; Notes |
| Plant/PlantGroup create/edit, extraction editor | Essentials; Origin; Lifecycle & notes                                 |
| BotanicalProfile add/edit                       | Description & origin; Cultivation; Uses & warnings                    |
| ProvenanceSite create/edit                      | Essentials; Coordinates; Notes                                        |

The initial A–T pass kept the three-field BotanicalIdentity name editor compact.
The final 33–47 pass now groups it with the existing Profile, Native range and Media
edit controls as described above; independent resource payloads remain unchanged.
Location, Supplier and local-place editors retain their compact existing forms.
The payload builders, quantity certainty, partial dates, germination observations,
lineage, transfer and reintegration contracts are preserved.

### Actions, images and names

Sowing Quick Preview leads with Open details, then a maintenance group (Edit and
Record germination), then a separated descendant group (Create Plant/Plant group).
Buttons wrap within those groups at smaller widths. Existing Reference pages reuse
page headers, directory search, selection, previews and the shared inset focus ring.

`RecordVisual` owns collection imagery: safe local designated primary, then an
eligible BotanicalIdentity cover, then a subtle record-type SVG placeholder. A failed
primary falls through to cover; a failed cover falls through to placeholder. Metadata
comes from each directory's existing identity read, with one identity read for
Dashboard, Events and Sowings. There are no per-row requests or cross-session cache.

The resolver is used by Seed, Sowing, Plant/PlantGroup and BotanicalIdentity directory
rows and relevant previews, Dashboard activity and Events. Event visuals resolve
from the exact Event target. Collection/activity do not automatically load external
identity covers or external designated photos. Botany retains its existing explicitly
configured compact external-cover policy (lazy, asynchronous, no-referrer); other
external photo/cover views retain their explicit loading choice. No Event attachments
or new media ownership mechanism were introduced.

Photo evidence uses bounded cards (maximum 20rem), a responsive gallery and 14rem
aspect-preserving image canvases. One portrait photo stays a card rather than a full
workspace band. Primary designation, details, removal, attribution and external-image
operations remain associated with each card. Botany's larger Quick Preview uses a
bounded 12rem frame with `object-fit: contain` for portrait, landscape and square.
Compact directory crops retain their existing purpose.

Inspection of the SeedLot, Sowing, Plant and PlantGroup models confirmed UUID primary
keys and optional labels with no label uniqueness constraint. Display names resolve
as explicit label → common name → useful nonredundant cultivar → scientific name →
existing generic fallback only without botanical naming. Nothing generates or saves
names, changes record keys or introduces numbering. Summary botanical names and
placeholders remain usable if the supplementary identity read fails.

### Rendered review receipt

The isolated `florabase-ui-review` project used synthetic records and tmpfs database
and media storage at `http://localhost:18081`. Normal operator and performance
projects were untouched. The review project was removed after QA without deleting
operator volumes. The temporary browser tab was closed and viewport override reset.

| Surface actually inspected                                               | 1440 × 844                       | 1024 × 844                                 | 390 × 844                                  |
| ------------------------------------------------------------------------ | -------------------------------- | ------------------------------------------ | ------------------------------------------ |
| Dashboard and recent activity                                            | Yes                              | Yes                                        | Yes, including scrolling to activity       |
| Seed directory and all five Edit panels                                  | Yes                              | Yes                                        | Yes                                        |
| Seed Photos                                                              | Portrait and three-photo gallery | Portrait card                              | Portrait card and item controls            |
| Sowing directory, preview/detail and all five Edit panels                | Preview and detail               | Preview and detail                         | Direct detail after row selection          |
| Plant directory with primary/cover/placeholder and all three Edit panels | Yes                              | Yes                                        | Yes                                        |
| BotanicalIdentity directory, name editor and three Profile panels        | Yes                              | Yes                                        | Yes                                        |
| BotanicalIdentity larger preview image                                   | Portrait, landscape, square      | Existing responsive direct-detail behavior | Existing responsive direct-detail behavior |
| Locations, Suppliers, Geography                                          | Yes                              | Yes                                        | Yes, including search/focus                |
| ProvenanceSite three-panel editor                                        | Yes                              | Yes                                        | Yes                                        |
| Events, Provenance map, Import / Export                                  | Yes                              | Yes                                        | Yes                                        |

Additional desktop PlantGroup checks confirmed the separate exact-count control and
retained an unsaved count through Back/Next. Seed, Sowing and Plant unsaved labels
survived Back/Next at all three widths; profile text survived panel switching. The
browser exercised hidden Seed client validation, hidden coordinate native validation,
and server coordinate-pair validation; both coordinate paths revealed/focused Longitude.
Mobile name/profile footers and gallery item controls were reached through normal
keyboard/scroll behavior. No page-wide horizontal overflow appeared in measured
views; inspected panels/action stacks had no accidental horizontal overflow. Existing
scrollable detail tab strips remain intentional. Collection/activity renders contained
no remote image elements; map basemap tile requests retain their existing policy.

117 `sections-` screenshots and `sectioned-ui-review.json` are saved outside the repo
in this task's visualization directory:
`/home/alessandro/.codex/visualizations/2026/09/30/01a0f0f1-4d57-77c0-a34b-ee9a3d20d6e9`.
Final captures replace the initial loading states and the Sowing action, small Seed
row, focus-ring and mobile activity-badge defects discovered during QA. These are
representative populated-fixture checks, not exhaustive content combinations or
operator acceptance. Browser limitations reported in the earlier pass are resolved
for this requested matrix.

### Verification

Affected frontend checks passed 108 tests across 10 files; the complete final suite
passed 281 tests across 30 files. Frontend formatting, lint, strict TypeScript and
production build passed. Backend OpenAPI export and frontend declaration generation
reported no drift. The feature graph validated 81 features; Markdown formatting and
`git diff --check` passed. The final milestone is recorded in `docs/progress.md`.
No canonical feature gate or unrelated backend suite ran in this frontend-only
refinement. All changes remain unstaged/uncommitted at `cd5bf70`; no push, delivery,
merge or feature-finish ran. UX-006 remains `implemented` pending operator acceptance.

### Separate follow-ups

**Shared media library:** retain `MediaAsset` ↔ `RecordMediaLink` ↔ SeedLot / Sowing /
Plant / PlantGroup / BotanicalIdentity / other supported records as a candidate for a
separate domain increment. Potential capabilities include one physical asset reused
across records, per-record context/captions, ordering and explicit primary designation,
a central gallery, provenance/attribution, deduplicated local storage and privacy-safe
external references. Existing attachment ownership/locking and migration/history need
an explicit contract. No model, API or library UI is implemented here.

**Location descendant counts:** current usage summaries group exact `location_id`
references, so they remain direct-only. Existing descendant-aware search filtering
is separate from usage aggregation. A later increment should distinguish
`Direct here: 2` from `Including sublocations: 7`, define active/total and group-record
count semantics, and cover hierarchy aggregation, API declarations, directory/detail/
preview totals and help. Deletion/retirement guards need separate review; no aggregation
or GeographicPlace semantics change belongs in this branch.

## Exact complete branch change manifest

This includes both preserved earlier work and the final 33–47 pass.

- `backend/openapi.json`
- `backend/src/florabase/events/schemas.py`
- `backend/src/florabase/events/service.py`
- `backend/tests/integration/test_event_api.py`
- `backend/tests/integration/test_primary_photo_api.py`
- `backend/tests/test_event.py`
- `docs/product-roadmap.md`
- `docs/progress.md`
- `docs/ui-consistency-polish.md`
- `frontend/src/App.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/Propagation002.test.tsx`
- `frontend/src/UX001.test.tsx`
- `frontend/src/UX004.test.tsx`
- `frontend/src/api/schema.d.ts`
- `frontend/src/botanical-identities/BotanicalIdentityScreen.tsx`
- `frontend/src/botanical-identities/ExternalBotanicalDataPanel.test.tsx`
- `frontend/src/botanical-identities/IdentitySummary.tsx`
- `frontend/src/botanical-profiles/BotanicalProfilePanel.tsx`
- `frontend/src/collection/DashboardScreen.tsx`
- `frontend/src/collection/DashboardSearch.tsx`
- `frontend/src/components/CollectionUI.tsx`
- `frontend/src/components/FormSections.test.tsx`
- `frontend/src/components/FormSections.tsx`
- `frontend/src/components/RecordPresentationProvider.tsx`
- `frontend/src/components/ReferenceInteractions.test.tsx`
- `frontend/src/components/ReferenceUI.tsx`
- `frontend/src/components/SidebarResizeHandle.tsx`
- `frontend/src/components/formValidation.ts`
- `frontend/src/components/recordPresentation.test.ts`
- `frontend/src/components/recordPresentation.ts`
- `frontend/src/components/sidebarWidth.ts`
- `frontend/src/events/EventFeed.test.tsx`
- `frontend/src/events/EventFeed.tsx`
- `frontend/src/events/EventJournal.tsx`
- `frontend/src/events/EventTargetPhoto.tsx`
- `frontend/src/events/GlobalEventsScreen.tsx`
- `frontend/src/geographic-places/GeographyScreen.tsx`
- `frontend/src/labels/LabelsScreen.test.tsx`
- `frontend/src/labels/LabelsScreen.tsx`
- `frontend/src/labels/labels.css`
- `frontend/src/photos/PrimaryPhotoVisual.test.tsx`
- `frontend/src/photos/PrimaryPhotoVisual.tsx`
- `frontend/src/photos/RecordVisual.test.tsx`
- `frontend/src/photos/RecordVisual.tsx`
- `frontend/src/plants/PlantFormFields.tsx`
- `frontend/src/plants/PlantScreen.test.tsx`
- `frontend/src/plants/PlantScreen.tsx`
- `frontend/src/propagation/CreationReversal.test.tsx`
- `frontend/src/propagation/CreationReversal.tsx`
- `frontend/src/propagation/GuidedForms.test.tsx`
- `frontend/src/propagation/SeedLotSowingWizard.tsx`
- `frontend/src/propagation/SowingDescendantWizard.tsx`
- `frontend/src/provenance-map/ProvenanceMapScreen.tsx`
- `frontend/src/provenance-sites/CoordinateFields.test.tsx`
- `frontend/src/provenance-sites/CoordinateFields.tsx`
- `frontend/src/provenance-sites/ProvenanceSiteManager.test.tsx`
- `frontend/src/provenance-sites/ProvenanceSiteManager.tsx`
- `frontend/src/provenance-sites/coordinates.test.ts`
- `frontend/src/provenance-sites/coordinates.ts`
- `frontend/src/seed-lots/SeedLotScreen.test.tsx`
- `frontend/src/seed-lots/SeedLotScreen.tsx`
- `frontend/src/sowings/SowingFormFields.tsx`
- `frontend/src/sowings/SowingScreen.test.tsx`
- `frontend/src/sowings/SowingScreen.tsx`
- `frontend/src/styles.css`

**66 unstaged/untracked files**; no staged changes.

## ORDER-001 navigation update

The current approved sidebar is Overview (Dashboard); Collection (Seeds, Sowings, Plants, Harvests,
Locations); Activity (Journal, History); Explore (Botanical identities, Media, Geography, Collection
origins); Sourcing (Suppliers, Orders); Tools (Import / Export, Labels). Page eyebrows follow these
areas. Desktop disclosure/localStorage and mobile More behavior remain intact. Collection origins
keeps `#/map`, API/domain provenance names and Saved View `provenance_map`; its copy describes actual
recorded material origin. No Species distribution, Native range or Schedule destinations are shipped.
