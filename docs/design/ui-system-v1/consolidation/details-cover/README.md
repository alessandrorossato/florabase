# Details consolidation and botanical cover fallback — 1 November 2026

**Pending final operator UAT.** No protected delivery or canonical FULL gate has run.
Authoritative worktree: `548f`, branch `feat/ui-system-v1-wave3`.

- Previous completed interaction correction: `107f719273085ec7c2c51a3bb5ed720e31a245ba`.
- TX-001 main: `4ca5fe0ae85da0f48e3f4df4f370f98c3747a311`, reconciled by normal merge
  `31ef765f19d414a00a350167f08b3887898f7195`. Both progress histories were retained.
- Part A: `83e1c3bad6c4977bdf2a82f2fb3cc2b000f93add`.
- Batch 1 `3669869`, consolidation `db1e71f`, independent QA/Schedule `d09fd86` remain ancestors.

[Evidence gallery](evidence/index.html), [verification](verification.txt),
[exact changed files](changed-files.txt), [source fingerprint](source-fingerprint.json).
Earlier screenshot sets remain historical; the final direct-Details contract remains authoritative.
Quick Preview has not been reintroduced.

## A. Hierarchies and Details

The hierarchy defect originated in composition: the border belonged to the record button while
Details/Edit occupied a separate third grid track. `HierarchyRow` now places record and trailing
commands inside one normal-flow bordered surface. The independent chevron remains outside.
Both explorers share this row, two-track branch layout, wrapping and nested connectors; there is
no absolute action positioning. Record Enter/Space and expansion remain independent.

`DetailPage` extends CollectionUI rather than introducing another component system. It reuses
DetailHeader, Breadcrumbs, DetailTabs, existing semantic status and domain-owned summaries/sections.
DetailHeader accepts formatted names and an explicit heading level/id while retaining its existing
focus ref. Existing Seeds/Sowings/Plants header defaults are preserved. Identities now keep one
compact header across tabs. Dedicated place records no longer mount directory search/header tools.

| Surface | Presentation adapted | Domain evidence and exceptions retained |
| --- | --- | --- |
| Locations | Shared hierarchy row and Details shell; full path wraps | Parent/children, direct/inclusive counts, explicit non-inherited scopes, cycle protections, Create child/Edit and usage links |
| Botanical identities | Shared formatted h2, cover, actions and stable tab header | Scientific name/cultivar, footprint, separate reference/taxonomy/maps/media/history, source-choice operations and deletion guards; no invented lifecycle |
| Geography Places | Shared hierarchy row, breadcrumb/header and summary treatment | Canonical read-only/custom-only Edit, parent navigation, child count, reference codes, provenance/native-range counts and local-child creation; Sites/Maps remain specialist views |
| Suppliers | Shared Details shell, header, tabs, typography and metrics | Kind/state, contact data, photos, Orders, linked material and acquisitions |
| Orders | Shared Details shell, header, tabs, typography and metrics | Exact reference/currency, optional Supplier, PartialDate, unknown prices, physical SeedLots and guarded add/link/unlink/delete |

## B. Display-only image resolution

Collection callers use **usable own designated photo → exact referenced botanical cover → placeholder**.
Seeds and Plants/PlantGroups Details previously gated their image slot on an own photo, suppressing
identity fallback. Those gates are removed. Sowings Details now has the same resolver as its List/
Gallery. A summary containing a scientific name no longer accidentally prevents enrichment from
existing reference metadata; explicit cover metadata/removal on the record still takes precedence.
Harvest and Stored material no longer borrow a Plant/PlantGroup photo as if it were their own.
Activity's explicitly supplied source-photo evidence remains supported and regression-tested.

No new per-page lookup, per-record request, API/schema change, media write, attachment, primary
selection, copied image or remote download was introduced. Existing family reference reads and
RecordPresentationProvider are reused. Resolution is by id, never by name or inferred ancestry.
A missing/ambiguous reference stays a placeholder even when other identities have covers.

Eligible covers are existing protected local thumbnails or already-saved protected media URLs.
Collection callers do not opt into remote external covers. Identity directory's existing explicit
compact-cover policy and no-referrer behavior remain. Failed images fall through; a later usable
own photo immediately supersedes the reference. Alt text and source title identify a botanical
reference rather than a specimen. Noncompact source text is screen-reader-only to avoid an overlay
or footer band; existing compact directory presentation remains.

Sowings currently has Photos but no designated-primary contract. Inventory likewise has no own
photo designation. This increment does not invent one or guess among attachments: they use the
eligible identity cover/placeholder. Photos management remains with its existing owner. A group's
reference is used only when explicitly supplied by its existing single-identity contract.

## Harvests access investigation

The reported blank Review page was reproduced. Vite returned a 175-byte empty transformed module
for StoredMaterial although the source exported StoredMaterialDirectory. Invalidating that cached
module restored Harvests without changing source, records or Docker resources. Fresh full reload,
Details activation, Stored material and exact inventory navigation were verified afterwards.
Production build verifies the actual exports. This was a development module-serving failure;
no Harvest domain or persistence behavior was altered to mask it.

## Verification

Final frozen source: **458/458 tests across 20 suites**, strict TypeScript, full frontend ESLint,
affected-source Prettier, production build, 123 valid features and diff checks pass.
The run includes original Batch 1 owning safety suites and Activity image compatibility.
An earlier run passed 449 tests but typing caught the remaining Activity caller; compatibility
was restored before the final run. No failing expectation was removed to conceal a defect.
Historical standalone 69-case evidence is preserved; no separate new 69-only run is claimed.
Canonical FULL and final operator UAT have not run.

## Browser evidence and limits

The existing Review remains owned by `548f` at `http://localhost:15174`; frontend/backend/database
healthy, code/DB `20261013_0042`, fixture v4 ready (80 managed baseline records), extended synthetic
records retained. Source binds include the current changes. No records were saved/deleted.

- Five Details families × 1440/1024/390: 15 DOM/layout checks, with representative captures.
- Five families × six themes at desktop: 30 checks; six identity header/theme captures.
- Both hierarchies × three widths: six checks, keyboard expansion and actions contained in rows.
- Five families at 320 CSS px: narrow-width stress only, **not actual browser zoom**.
- Live long Location path; Edit opens focused on Name, Escape closes and returns focus to Edit.
- Harvest directory reload, keyboard Details, Stored Space activation and exact inventory URL.
- Seeds own protected photo loads; Gallery first-row photo/placeholder heights align.

The viewport requests are CSS widths. Captures can exclude native scrollbars/viewport chrome;
manifest records actual raster dimensions. Some screenshot attempts failed during resize and were
recaptured; only saved images are evidence. DOM checks do not by themselves prove visual quality.

All 37 identities in the existing Review directory had no assigned cover. Positive inherited-cover,
external-cover suppression, broken-image and later-own-photo transitions are therefore automated
cases, **not claimed as live fixture demonstrations**. No identity/media association was created to
manufacture evidence. Operator UAT should exercise those cases with an eligible existing cover.
Physical devices, assistive screen readers and actual browser zoom remain manual checks.

## Deferred operator UAT findings — 1 November 2026

Wave 3 is accepted as a checkpoint for continued roadmap planning only. Final operator UAT is
still pending. These findings remain open and must be reviewed before UAT acceptance.

### UI-DETAIL-001 — Details visual inconsistencies

**Status: open; not resolved by this checkpoint.** Affected detail pages: Harvests, Stored
material, Locations, Suppliers and Orders. The operator reports that these pages do not yet
fully match the approved Collection detail-page presentation. Reconcile the DetailHeader,
breadcrumb, action placement, content width, spacing, typography, at-a-glance metrics and section
layout across the affected pages while retaining their domain-specific information and actions.
Do not treat the shared `DetailPage` shell or the current evidence gallery as resolution of this
finding; visual parity still requires operator review and targeted follow-up.

### UI-FLICKER-001 — Title flickering during navigation

**Status: open; cause not yet established.** The operator reports visible page-title flicker
during view changes. Investigate route remounts, asynchronous loading states, conditional
rendering, layout shifts, CSS transitions/animations, and shared `DetailPage`/`PageHeader`
behavior before selecting a fix. Do not suppress animations globally or make a speculative
change without reproducing and identifying the cause.

Reproduction paths to capture in follow-up UAT: open a Collection directory, open a record's
Details, then return to the directory; repeat navigation between the affected Details pages
(Harvests, Stored material, Locations, Suppliers and Orders). Record the source/destination,
loading state and whether the title changes, disappears or shifts. **No dedicated recording or
reproducible visual evidence is attached yet**; capture a short recording or before/during/after
screenshots when the issue is reproduced.

### Acceptance gate

Keep both IDs open in the next UAT pass. UI-DETAIL-001 needs a visual review of all five affected
pages against the approved Collection detail pattern. UI-FLICKER-001 needs a reproducible path,
visual evidence and cause-based investigation before any correction is accepted. Neither finding
changes the current checkpoint's implementation status, and neither is evidence that Wave 3 UAT
has been completed.

## Updated operator UAT

1. Resolve and review open finding UI-DETAIL-001 across Harvests, Stored material, Locations,
   Suppliers and Orders. Compare all five Details families at desktop/tablet/mobile and in your
   preferred theme; check formatted botanical names, paths, optional images, actions, tabs,
   metrics and empty data.
2. Reproduce and record UI-FLICKER-001 using the paths above. Investigate route remounts, async
   states, conditional rendering, layout shifts, transitions/animations and shared header behavior;
   accept a fix only after the cause is demonstrated.
3. Expand Locations/Geography with pointer and Enter. Open records separately; direct Edit must
   invoke only its owner. Confirm canonical places have no Edit and custom places do.
4. Check Location scopes, cycle exclusions, direct/inclusive counts and child navigation. Cancel
   editors, then reject dirty dismissal on a temporary draft; do not save unintended changes.
5. Check identity Reference/Taxonomy/Maps/Media/History and Add to collection source-choice flows.
   Keep reference classification distinct from collection footprint and lineage.
6. Inspect Supplier contacts/material/Orders and Order exact prices, missing data, partial dates
   and physical SeedLot relationships. Check guards before any approved destructive action.
7. Check Harvests on a fresh reload, historical source/materials, Edit, exact Stored inventory,
   approximate versus unknown remaining quantity, and its existing correction/conversion guards.
8. With an eligible existing botanical cover, verify fallback in Collection List/Gallery/Details,
   own-photo priority, reference attribution, failure fallback and later own-photo replacement.
   Verify blocked external references never load automatically and ambiguous identities never guess.
9. Test real browser zoom, physical touch devices and screen-reader navigation. Final operator UAT
   and protected verification remain pending; targeted checks are not release verification.
