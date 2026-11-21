# v1.0.0 acceptance-criterion restatements

Version 1. This page is part of the [v1.0.0 release scope](scope-v1.md). It was prepared against
`main` `554d74de88a278e2b9a392de9d105d3d62c35f91` and re-checked against `main`
`836bf80305a19fdd7f49845b8bc00ae423553a93` after Batch 02 (#192) merged. The approach was
approved by the operator on 2026-11-16: one versioned record of the acceptance criteria
superseded by later operator-approved product decisions.

## Rules

- A restatement changes the wording against which a criterion is certified. It is not evidence,
  and it neither certifies a criterion nor changes a `features.json` status.
- Only a criterion with **traceable** operator decision evidence is a *confirmed supersession*.
  Where the only trace is a delivered change, the row is a *proposed change awaiting approval*.
  Where no decision is found, the row is an *unresolved defect or gap* and stays open.
- The original text stays in `features.json`. Certification rows cite the restatement ID next to
  the criterion they certify.
- No row grants an exception. "Verification still required" must be met on the release candidate.
- A later version of this page adds rows; it never deletes one. A withdrawn row is marked withdrawn.
- Two questions are kept apart in every row. **Change accepted** means that the operator decision
  accepts the implementation change, so the original wording no longer applies. **Criterion
  fulfilled** means that committed evidence shows the restated criterion is met on the candidate.
  No row in this version is fulfilled by the restatement alone.
- A *proposed* row becomes *confirmed* only by an operator ruling recorded in the scope-change
  table of `scope-v1.md`, dated, naming the row ID. Until then the original criterion applies.

## Decisions referred to

| Ref | Decision | Evidence |
| --- | --- | --- |
| D1 | A new Journal entry opens with Today selected. | `scope-v1.md` §"UX-DATE-001 decision D1"; scope-change row 2026-11-13 (operator). |
| DP | Directory contract of 2026-11-01: Quick Preview and idle inspector columns removed from eight directories and both hierarchy explorers; direct bordered Details/Edit; creation-only overflow. | `progress.md` §"2026-11-01 — Final directory interaction contract correction (operator UAT pending)" ("explicitly confirmed replacement"); `docs/design/ui-system-v1/consolidation/final-interaction-correction/README.md:11` ("operator-confirmed contract"); `progress.md` §"UI System v1 Wave 3 closure disposition — 1 November 2026" ("Operator reports the six Gate B UAT checks complete"); delivered in #134 (`e5e6b4f`, auto-merge enabled by the operator, 2026-11-01). |
| DT | Today A — Operational approved; reverses the photo-first DASHBOARD-001 layout. | `docs/dashboard-001-handoff.md:223` ("The operator approved 'Today A — Operational' on 2026-11-12"); `progress.md` §"UX-TODAY-001 — work-first Today (Variant A, Operational), 13 November 2026"; delivered in #177. |
| DL | Later backlog features delivered and `verified`: ATTACHMENT-004, MAPS-FOUNDATION-001, MAPS-ORIGINS-001, SCHEDULE-001, DASHBOARD-001, SUPPLIER-003. | `features.json` entries and their verification records. Several entries were added in their own delivering PRs (for example MAPS-FOUNDATION-001 #116, SCHEDULE-001 #83, SUPPLIER-003 #70). **No separate written ruling found**, so rows resting only on DL are proposed. |
| DW | WCVP v16 default (WCVP-DEFAULT-001, #174 `b94757e`) and WGSRPD crosswalk v2 (WGSRPD-CROSSWALK-V2, #175 `51f7884`). | Both PRs merged by the operator on 2026-11-13 (#175 by auto-merge the operator enabled). Each backlog entry was added in its own delivering PR. **No separate written ruling found.** |

## Confirmed supersessions

Each row: original requirement → intent → decision → replacement wording → implementation evidence
→ verification still required → release scope. None alters release scope.

**R01 — UX-DATE-001 #3.**
- Original: "…the initial choice is a prop and defaults to no selection with saving blocked until chosen".
- Intent: no date is ever recorded without an explicit or visible choice.
- Decision: D1.
- Replacement: "Journal entries offer an accessible Today / Another date / Date unknown radio
  group; Today shows and records the device-local calendar day. A new Journal entry opens with
  Today selected (D1) and can be saved without another date action. A stored entry opens with
  its stored choice and precision."
- Implementation: delivered by FN-05 (source `a470811`) in Batch 02, #192, merge commit `836bf80`.
  The record is at `docs/release/evidence/fn-05.md`. It made two changes:
  - The Journal consumer `EventJournal` defaults `newEntryDateChoice` to `"today"`
    (`EventJournal.tsx:194`). It passes the choice explicitly as `initialChoice` for a new entry,
    and `"unknown"` when editing (`EventJournal.tsx:967`).
  - The shared `OccurrenceDateChoice` component's own default `initialChoice` is also `"today"`
    (`OccurrenceDateChoice.tsx:30`). `"unset"` remains available as an explicit prop and is
    tested: `OccurrenceDateChoice.test.tsx` "when initialChoice is unset, nothing is preselected
    and an unanswered choice is invalid".

  D1 governs the Journal behaviour only. The component default change is not required by D1. It
  is harmless on `main` because `EventJournal` is the component's only consumer and passes the
  choice explicitly. A future consumer would silently inherit Today; that is noted, not a defect.
- Journal tests on `main` (`frontend/src/events/OccurrenceDateChoice.test.tsx`):
  - "EventJournal preselects Today for new entries and saves Today, Another date and Date
    unknown as chosen";
  - "EventJournal preserves stored full, year-month, year-only and unknown dates on untouched
    save";
  - "EventJournal keeps stored and drafted dates stable across kind switches, cancel/restore,
    record navigation, and height validation".
- Verification: these tests in the canonical gate on the candidate commit, and G-CORE step 5 on
  the candidate.

**R02 — COLLECTION-VISUAL-002 #1.** Original: Harvest directory "…and a privacy-safe desktop
Quick Preview". Intent: inspect a harvest without leaving the list, without leaking source photos.
Decision: DP. Replacement: the same text with "and direct Details/Edit; no Quick Preview (DP)".
Evidence: `HarvestScreen.test.tsx` (navigation without Preview; no source-photo substitution).
Verification: G-UX Harvests entry.

**R03 — COLLECTION-VISUAL-002 #4.** Original: Location directory "…and useful Quick Preview".
Decision: DP. Replacement: "…search ancestors and nonzero occupied types; records open directly
(DP)". Evidence: `App.test.tsx:3935`, `:3328`. Verification: G-UX Locations entry.

**R04 — GEOGRAPHY-VISUAL-001 #1.** Original: Places "…contextual preview, focus and exact
associated-site navigation". Decision: DP (both hierarchy explorers). Replacement: drop
"contextual preview"; a place opens its dedicated record. Evidence: `App.test.tsx:4698`.
Verification: G-UX Geography entry.

**R05 — BOTANICAL-IDENTITIES-VISUAL-001 #1.** Original: "Directory and compact Quick Preview
retain search, selection…". Decision: DP. Replacement: "The directory retains search, selection,
real counts and route state; a record opens full Details, with Open details, Edit and the
eligible creation actions". Evidence: `UX004.test.tsx:242`, `:140`, `:526`. Verification: G-UX
identity directory entry.

**R06 — UI-SYSTEM-WAVE2-001 #3.** Original: Suppliers and Orders use "explicit
Preview/Details/Edit and close-first responsive preview dialogs". Decision: DP. Replacement:
"explicit Details/Edit without a preview, retaining exact canonical search, Supplier scope,
pagination, URL/browser history and focus return". Evidence: `SupplierScreen.test.tsx:608`,
`OrderScreen.test.tsx:762`. Verification: G-UX Suppliers and Orders.

**R07 — UI-SYSTEM-001 #9, Preview clause only.** "record-surface nonmodal Preview with explicit
Details/Edit actions" becomes "explicit Details/Edit actions (DP)". The other clauses of #9 are
unchanged and still need evidence. Verification: as for #9's remaining clauses.

**R08 — UI-SYSTEM-001 #10, inspector clause only.** "typed row/card/inspector/action
presentation" becomes "typed row/card/action presentation (DP)". The remaining clauses stand,
including the six-theme evidence and the open UI-FLICKER-001 observations.

**R09 — UX-005 #1.** "browse, compact inspection and read-first detail" becomes "browse and
read-first detail (DP)" for Supplier, Location and Geography. Verification: G-UX entries.

**R10 — HARVEST-001 #5.** "compact preview" is removed from the list (DP). Other clauses stand.

**R11 — CONTROLS-001 #3, "previews" only.** Remove "previews" from the audited surfaces (DP).
The Workbench navigation and Settings part is R21.

**R16 — UI-SYSTEM-001 #3, Dashboard clause.** "a prominent factual Dashboard strip" becomes
"the Today page of DT". Verification: G-UX Today entry; UX-TODAY-001 #6 (first work row visible
at 390×844).

**R25 — LOCATION-003 #3** (added 2026-11-16, found while mapping evidence).
- Original: "Location directory, compact Quick Preview and detail communicate descendant
  content…".
- Decision: DP, which removed Quick Preview from both hierarchy explorers.
- Replacement: "Location directory and detail communicate descendant content with explicit scope
  labels, accessible controls and responsive wrapping without duplicating equal leaf counts in
  compact surfaces."
- Verification: G-UX Locations entry.
- Related: `docs/location-descendant-aggregation.md:54` still describes a desktop Quick Preview;
  correct it as ordinary documentation.

**R24 — UI-SYSTEM-001 #4 (formerly U01).**
- Status: confirmed by the operator decision of 2026-11-16 (U01 approved), recorded in the
  scope-change table of `scope-v1.md`. The eight-photo grid is not restored.
- Original requirement: "Dashboard review evidence shows up to eight distinct randomly selected
  actual Plant records with truthful primary, identity-reference or missing imagery in a 4x2
  grid; header, KPIs and useful Next work fit the measured 1440x844 baseline while smaller
  layouts scroll naturally".
- Intent: a small, honest sample of the real collection on the start page, without placeholder
  or misattributed imagery.
- Decision:
  - The explicit operator decision of 2026-11-16, consistent with DT (Today A — Operational,
    approved 2026-11-12).
  - Delivered implementation: PR #177, merge commit `947d77f`, 2026-11-13, feature UX-TODAY-001.
- Approved replacement: "Today shows up to four distinct randomly selected actual Plant records,
  with truthful image attribution and responsive layout."
- Implementation evidence already in the tree, still to be confirmed against the candidate:
  - Selection: `backend/src/florabase/collection_views/dashboard.py` `photographs()` samples
    active individual Plants with `order_by(func.random())` (eight sampled).
  - Display: `frontend/src/collection/DashboardPhotos.tsx:19` shows at most four.
  - Tests:
    - `backend/tests/integration/test_dashboard.py:332`
      `test_photographs_sample_actual_plants_with_explicit_primary_and_reference_fallbacks`.
    - `frontend/src/collection/DashboardScreen.test.tsx:165` "authoritative KPI units and at most
      four distinct protected photographs retain Plant destinations and attribution".
    - `DashboardScreen.test.tsx:210` (no duplicates, no placeholders, no remote loading).
    - `DashboardScreen.test.tsx:252` (stable visit sample; broken primary falls back to a
      labelled "Identity reference").
    - `DashboardScreen.test.tsx:462` (no usable image gives one line).
- Outstanding verification, not met by this decision:
  1. Selection behaviour: distinct, random, active individual Plants only, and the sample stable
     during a visit. Map the tests above in the evidence record; confirm them on the candidate in
     G-CORE step 1 or 7.
  2. Actual Plant records: each image links to its own Plant (G-UX Today).
  3. Image fallback and truthful attribution: the record's own primary image, else a labelled
     identity reference, else nothing. Covered by the tests above; confirm in G-UX Today.
  4. Responsive presentation: G-UX Today entry at 390, 1024 and 1440 px, both themes, 200 %
     zoom.
- Not affected: UI-SYSTEM-001 stays `in_progress`. Its other criteria are unchanged: #3 and #10
  partly met (R16, R08), #5 needs gate wiring, #6 partly met, #9 open apart from R07. This
  decision verifies nothing.
- Release scope: unchanged.

**R26 — PORTABLE-COMPOSE-001 description, #2, #3 and the upgrade part of #4** (added 2026-11-21).
- Original (stays in `features.json`): a three-service portable Compose shipped alongside the
  controller bundle; the runtime "never initializes PostgreSQL or migrates on startup"; one-time
  cluster and schema initialization, owner bootstrap and an explicit upgrade are documented manual
  steps; the smoke proves the explicit upgrade.
- Intent kept: the database never silently starts empty in place of existing data, an image update
  never changes data without a backup, and the backend process never migrates.
- Decision: [ADR 0008](../decisions/0008-self-initializing-single-compose.md), accepted by the
  operator on 2026-11-21 and recorded in the scope-change table (INSTALL-001, WF-09).
- Replacement: "The release attaches one self-initializing `compose.yaml` (INSTALL-001). Its
  one-shot `prepare` accepts only an empty data folder or the installation its marker records, and
  `db` creates a cluster only for a new installation. The backend process never migrates; the
  one-shot `migrate` initializes an empty database, leaves an at-head database unchanged, upgrades
  only from the exact previous release head after a verified dump, and refuses anything else.
  Owner bootstrap is one-time from the environment or offline; paired backup and isolated restore
  are documented. The smoke proves these cases on the rendered asset."
- Implementation: INSTALL-001 on branch `feat/install-001` (`compose.yaml`,
  `release_schema deploy`, `scripts/smoke-portable-compose.py`). PORTABLE-COMPOSE-001 keeps its
  delivered evidence and status; criteria #1 (attested asset, digests, one published port) and #5
  are unchanged.
- Verification still required: INSTALL-001 delivery, its publication in the next beta and the
  G-INSTALL, G-UPGRADE and G-RESTORE real-host runs.
- Release scope: unchanged; INSTALL-001 is already a release-work blocker.

## Proposed changes awaiting approval

### Rows resting only on later delivered features

R12–R15 were first marked confirmed. Independent review on 2026-11-16 found that their only trace is
later delivered backlog features (DL), whose entries were added in their own delivering PRs. That
is the same kind of trace as DW, so these rows are proposed until the operator rules. R12 also
relies on ATTACHMENT-005, and R15 on HARVEST-001, both still `implemented`.

**R12 — ATTACHMENT-003 #4.** Original: identity covers have "no … thumbnails, derivatives, …
BotanicalIdentity gallery". Intent: the boundary of that increment, not a permanent prohibition.
Decision: DL (ATTACHMENT-004) and ATTACHMENT-005. Replacement: "Identity covers support safe
replacement and removal. Thumbnails, derivatives and the identity media gallery are governed by
ATTACHMENT-004 and ATTACHMENT-005; no version history, automatic discovery, provider search,
albums or EXIF inspection." Evidence: `test_identity_covers.py` replacement and removal tests.
Verification: none beyond the mapping.

**R13 — GEOGRAPHY-003 #3.** "…map-ready internal provenance data without maps, geocoding, or
external services" becomes "…map-ready internal provenance data, without geocoding; maps are
governed by MAPS-FOUNDATION-001 and MAPS-ORIGINS-001 (DL)". Verification: none beyond the mapping.

**R14 — UX-006 #3.** The clause "without inventing reminders, care rules, primary record photos"
stays. Add: "Explicit scheduled activities (SCHEDULE-001), explicit primary photos
(ATTACHMENT-004) and the Today layout (DT) are not invented content." The intent was "no
fabricated data", and the later features are explicit, operator-entered data. Verification: G-UX
Today and Journal.

**R15 — ATTACHMENT-005 #2.** "primary selection remains explicit and limited to SeedLot, Plant
and PlantGroup" becomes "…explicit, for SeedLot, Plant and PlantGroup and for the targets later
features add: Harvest (HARVEST-001 #4) and Supplier (SUPPLIER-003, DL)". Evidence:
`test_primary_photo_api.py`, `test_shared_media.py`.

### Other proposed rows

Each row gives the delivered change, its exact references, the original requirement that stays
in force until a ruling, the operator's recommended disposition of 2026-11-16 (a recommendation,
not an approval), and the wording that the ruling would adopt.

**R17 — WCVP-VERSION-001 #1.**
- Original (in force): "Exactly the reviewed v15 and v16 releases are provisioned separately with
  strict archive pins, schema and destination ownership validation; v15 remains the default".
- Delivered change: v16 became the default; v15 stays explicitly selectable.
  - PR #174, merge commit `b94757e`, merged by the operator on 2026-11-13.
  - Feature WCVP-DEFAULT-001, whose backlog entry was added in that same PR.
  - Code: `DEFAULT_VERSION = "16"` in `backend/src/florabase/native_range_enrichment/source.py`.
  - No written ruling was found.
- Recommended disposition: keep v15 compatibility and historical evidence, and recognise the
  delivered v16 default.
- Wording on approval: "…validation; v16 is the default (WCVP-DEFAULT-001, #174); v15 stays
  explicitly selectable, and historical v15 links, proposals and applications are preserved."
- Still to verify: WCVP-DEFAULT-001 criteria 1–3 tests in the canonical gate on the candidate.
- Scope: unchanged.

**R18 — WCVP-VERSION-001 #4.**
- Original (in force): "The exact twelve approved geographic equivalences have distinct
  release-specific crosswalk identifiers; unsupported geography and non-native assertions remain
  context only".
- Delivered change: crosswalk v2 has 20 pairs (nine added, eleven retained), and COS is withdrawn
  for new writes.
  - PR #175, merge commit `51f7884`; the operator enabled auto-merge on 2026-11-13.
  - Feature WGSRPD-CROSSWALK-V2, whose backlog entry was added in that same PR.
  - The v1 identifiers `wcvp15-wgsrpd2-cldr48.2.1-v1` and `wcvp16-wgsrpd2-cldr48.2.1-v1` remain
    (`native_range_enrichment/crosswalk.py:10-11`).
  - No written ruling was found.
- Recommended disposition: keep the historical crosswalk evidence, and recognise v2 for new
  proposals.
- Wording on approval: "The twelve approved v1 equivalences keep their release-specific v1
  identifiers and stay readable for frozen proposals and applications; new proposals use the
  v2 crosswalk (WGSRPD-CROSSWALK-V2, #175); unsupported geography and non-native assertions
  remain context only."
- Still to verify: a v1 frozen-application test and a v2 fresh-proposal test in the gate.
- Scope: unchanged.

**R19 — HARVEST-001 #4.**
- Original (in force): "…unlink/deletion retains shared assets and safe visual fallback resolves
  direct primary, source and identity context".
- Delivered change: Harvest and Stored material no longer substitute a physical source-record
  photo.
  - PR #134, merge commit `e5e6b4f`, 2026-11-01. It is recorded in `progress.md` §"2026-11-01 — Botanical cover fallback and final Details evidence, Part B (UAT pending)", a
    section headed "UAT pending".
  - Covered generally by the Wave 3 closure (`progress.md` §"UI System v1 Wave 3 closure disposition — 1 November 2026"); no ruling on this specific
    change was found.
  - Test: `HarvestScreen.test.tsx` "Harvest directory never substitutes source-record photos…".
- Recommended disposition: keep media attribution truthful, and keep fallback context distinct
  from images the record owns.
- Wording on approval: "…safe visual fallback uses the record's own primary image, then the exact
  identity cover, then a placeholder; a source-record photo is never shown as the harvest's
  image, and any fallback image is labelled with its actual owner."
- Owner labelling is now evidenced. CERT-03 (#193) added `HarvestScreen.test.tsx` "Harvest
  fallback image is labelled with its actual owner". It checks the thumbnail, alt text and
  reference label of an identity-cover fallback, the thumbnail and owner label of a record-owned
  primary photo, and that no source Plant photo is shown.
- Still needed: operator approval of the wording. Until then the original criterion is in force.
- Scope: unchanged.

**R20 — BOTANICAL-IDENTITIES-VISUAL-001 #6.**
- Original (in force): "Comparable directory rows share compact identity visuals and a semantic
  leading selection accent distinct from hover, focus and bulk checkboxes; all five valid
  operations use a consistent accessible shared action-menu grammar".
- Delivered change:
  - The stripe was removed: "Selected fill loses the inset stripe" (`progress.md` §"2026-11-01 — Shared directory interaction cleanup (operator review pending)", PR #134
    `e5e6b4f`). That cleanup section was "operator review pending".
  - The action grammar was replaced by decision DP.
- Recommended disposition: accept the selection fill only with adequate accessibility evidence.
- Wording on approval: "…a selection fill distinct from hover, focus and bulk checkboxes, meeting
  3:1 non-text contrast against the unselected row in every shipped theme; direct Details/Edit
  with creation-only overflow (DP)."
- Still to verify: a contrast measurement of selected against unselected rows in every theme
  (G-UX), and keyboard and screen-reader exposure of the selected state.
  `DirectoryPage.test.tsx:603` covers the shared row only.
- Scope: unchanged.

**R21 — CONTROLS-001 #3, Workbench navigation and Settings.**
- Original (in force): "…mobile navigation and existing map controls adopt consistent geometry
  without changing routes or domain state".
- Delivered change: mobile navigation and Settings were rebuilt by the Workbench shell, PR #147,
  merge commit `fec0398`.
- Disposition: depends on U04, so no ruling is proposed.
- Evidence that already exists:
  - `WorkbenchShell.test.tsx:285` "mobile workspace and account sheets navigate, theme and sign
    out" (function).
  - `styles.test.ts:188` and `tokens.css:65`: `--control-height-touch: 2.75rem` (44 px) on coarse
    pointers and narrow widths (token level).
- Still to verify: geometry of the rendered controls, through a G-UX record.

**R22 — PORTABLE-COMPOSE-001 #1.**
- Original (in force): "The new prerelease attaches an independently attested Compose with
  immutable PostgreSQL, backend and frontend digests, explicit durable binds and one published
  frontend port".
- Facts: the latest published release is `v0.1.0-beta.5`. Beta.6 was never published, and the
  REL-01 RC channel was delivered in PR #191, merge commit `554d74d`.
- Recommended disposition: use the first v1.0.0 release candidate, without an extra beta.
- Wording on approval: "The first `v1.0.0-rc.N` prerelease attaches…" with the rest unchanged.
- Still to verify: the RC publication through the protected workflow (G-DIST), and the attested
  asset inspected and recorded.
- Scope: unchanged. Requiring beta.6 instead would add a publication.

**R23 — COLLECTION-VISUAL-002 #8.**
- Original (in force): "Candidate remains unstaged and uncommitted for operator visual acceptance
  before independent review and canonical verification".
- Facts: delivered in PR #113, merge commit `9a73d3f`, 2026-10-18. The reconciliation records
  "pending operator acceptance and independent canonical verification".
- Recommended disposition: replace the obsolete process step with equivalent verifiable visual
  acceptance, without discarding unresolved defects.
- Wording on approval: "Operator visual acceptance of the Harvest and Location directories is
  recorded in the G-UX record on the candidate, and every defect open in the
  `collection-visual-002-handoff.md` record is fixed or dispositioned."
- Still to verify: that G-UX record, and every item below.
- Scope: unchanged.

Items recorded for COLLECTION-VISUAL-002, compiled 2026-11-16. Sources are
`docs/collection-visual-002-handoff.md`, `docs/review/collection-visual-002/` and `progress.md`;
PR #113 has no review comments. No source assigns a severity. Whatever R23's outcome, none of
these is discarded.

| ID | Source | Item | State on `main` | Proposed disposition |
| --- | --- | --- | --- | --- |
| CV2-01 | handoff:33, :206-212; `progress.md` §"2026-10-17 — COLLECTION-VISUAL-002 implementation and visual-review handoff" | Operator visual acceptance of the Harvest and Location directories and details was never recorded | Open. The October captures predate the Wave 3 details pages, decision DP and the Workbench shell (#147) | G-UX on the candidate |
| CV2-02 | handoff:33, :181-184; `progress.md` §"2026-10-17 — COLLECTION-VISUAL-002 second visual refinement" | Live native dirty-confirmation prompt and the keyboard, Back and Save steps after it were never certified; component tests only | Open. `window.confirm` is still used at `HarvestForm.tsx:122` and `LocationScreen.tsx:544`, `:734` | Manual check in G-UX, or an operator ruling that component tests suffice |
| CV2-03 | handoff:172, :209-210; `progress.md` §"2026-10-17 — COLLECTION-VISUAL-002 implementation and visual-review handoff" | True browser zoom was never exercised; viewport proxies only | Open | G-UX at 200 % zoom |
| CV2-04 | handoff:72-74, :80-81 | Harvest Details does not fit one viewport (criterion 3 says "one-page") | Open as a recorded limit; current geometry unmeasured since the shared detail pages replaced the layout | G-UX measurement, then an operator ruling if it still scrolls |
| CV2-05 | handoff:210-211 | Possible stale dirty draft in an old Review tab | Superseded: that Review was removed on 2026-10-19 (`progress.md` §"2026-10-19 — MAPS-FOUNDATION-001 authenticated operator review") | Closed |
| CV2-06 | handoff:148-165 | Directory filters deferred because the APIs lacked them (Seeds, Sowings, Plants) | Partly fixed: identity filter added in `5778da7` (#121). Location, Supplier/Source/Order, source Seed lot/germination and origin filters remain absent | Operator records the remainder as out of scope, or new work |
| CV2-07 | `progress.md` §"2026-10-17 — COLLECTION-VISUAL-002 implementation and visual-review handoff"; handoff:31 | Independent review and canonical verification outstanding at handoff | Partly resolved: only the PR #113 body states a local canonical pass; no committed review or record. handoff:31 still says "Candidate remains unstaged and uncommitted" | Covered by the candidate gate; correct handoff:31 as a historical note |
| CV2-08 | `docs/review/collection-visual-002/second-pass/README.md` | Seed-conversion captures predate the final fieldset border change | Undetermined | G-UX (conversion dialog) |

Criteria 1 and 4 of COLLECTION-VISUAL-002 are already restated by R02 and R03, which follow
decision DP. The reconciliation's `progress.md` line references for this entry (1099, 1116, 1135) are stale;
this page cites `progress.md` by section heading, because line numbers move as entries are added.

## Unresolved gaps (not restated)

**U01 — UI-SYSTEM-001 #4.** Resolved by the operator decision of 2026-11-16 and moved to R24.
History of this row:
- The server samples eight Plants (`dashboard.py:47`), and through #147 (`fec0398`) the client
  showed every sampled photo.
- PR #177 (`947d77f`) limited the display to four.
- No decision on the count was recorded until 2026-11-16.
- The Wave 1 eight-photo review evidence stays as history (`progress.md` §"2026-10-27 — UI-SYSTEM-001 Gate B review candidate, Proposal B refined";
  `docs/design/ui-system-v1/wave1/dashboard-geometry.json`).

**U02 — UI-SYSTEM-001 #9, clauses other than Preview.** Open evidence, unchanged.

**U03 — GEOGRAPHY-VISUAL-001 #4.**
- Not a supersession. The evidence on `main` supports the criterion:
  - `GeographyWorkspace.tsx` renders no tab list.
  - The sub-destinations are shell navigation entries (`navigation.ts:140-160`).
  - Legacy and canonical routes are tested: `GeographyWorkspace.test.tsx:165`, `:213`, `:238`.
- Still to verify: a G-UX check that no persistent tab strip is visible.

**U04 — UI-REDESIGN-EXPLORATION-001 #6, #7, #8.**
- Original criteria are in force; no restatement is proposed.
- PR #147 (merge commit `fec0398`, 2026-11-06; the operator enabled auto-merge at
  2026-11-06T18:40:28Z) integrated the shell. Integration is not proof of formal adoption.
- Against adoption at the time:
  - The last record before the merge cites a "FULL NO-GO" review and "Canonical FULL not run"
    (`progress.md` §"UI-REDESIGN-EXPLORATION-001 — M8 final responsive QA remediation, 6 November 2026").
  - `docs/design/florabase-next/README.md:3` says "Not approved for adoption or merge".
- Requirements that stay open until evidenced or explicitly dispositioned:
  - #6: no screenshot under `docs/design/florabase-next/` (0 image files tracked), and one UAT
    environment recorded instead of two.
  - #7: no migration plan in `docs/design/florabase-next/` or `progress.md`.
  - #8: no committed operator approval of FULL, delivery and merge.

## What the PR #147 frontend satisfies on `main`

Checked against the gaps the certification audit marked. Tests named here are in the frontend
suite that the canonical gate runs. Classified as **met by tests**, **partly met** or **still
missing**.

| Criterion | Requirement previously marked missing | Result |
| --- | --- | --- |
| UI-REDESIGN-EXPLORATION-001 #2 | Route preservation recorded only as a README claim | **Partly met.** `WorkbenchShell.test.tsx:82` asserts every former destination once; `:151` every creation route; legacy URLs are tested per area (`GeographyWorkspace.test.tsx:165`, `:238`; `ProvenanceMapScreen.test.tsx:343`; `SowingScreen.test.tsx:1354`; `PlantScreen.test.tsx:2840`). Record routes are not enumerated by one test. |
| UI-REDESIGN-EXPLORATION-001 #4 | Touch targets of at least 44 px only from capture probes | **Partly met.** `styles.test.ts:188` asserts the coarse-pointer and narrow-width token switch; `tokens.css:65` sets 2.75rem (44 px); `styles.test.ts:148` keeps the six themes byte-identical. Rendered sizes still need G-UX; Botanical keeps 40 px controls at touch widths (`progress.md` §"UI-REDESIGN-EXPLORATION-001 — M2 Workbench shell and navigation, 4 November 2026"). |
| UI-REDESIGN-EXPLORATION-001 #5 | Manual screen reader, zoom and touch passes | **Still missing.** Not testable by unit tests; G-UX and the DOC-04 trial cover part of it. |
| UI-REDESIGN-EXPLORATION-001 #6, #7, #8 | Screenshots, migration plan, approval | **Still missing** (U04). |
| UI-SYSTEM-001 #3 | Distinct labelled navigation icons | **Met by tests**, apart from the Dashboard clause (R16). |
| CONTROLS-001 #3 | Mobile navigation and Settings | **Partly met** (R21): function tested, geometry not. |
| GEOGRAPHY-VISUAL-001 #4 | No persistent tab strip under the Workbench shell | **Met in code and tests** (U03); visual check remains. |

## Status of every row

| Row | Feature and criterion | Change accepted | Criterion fulfilled |
| --- | --- | --- | --- |
| R01 | UX-DATE-001 #3 | Yes (D1) | No: FN-05 delivered in #192; candidate gate and G-CORE step 5 remain |
| R02–R11, R25 | Preview and inspector clauses (DP) | Yes (DP) | No: G-UX entries |
| R12, R13, R15 | Increment boundaries (DL) | Proposed | No: per-criterion mapping |
| R14 | UX-006 #3 | Proposed | No: G-UX |
| R16 | UI-SYSTEM-001 #3, Dashboard clause | Yes (DT) | No: G-UX Today |
| R17, R18 | WCVP-VERSION-001 #1, #4 | Proposed | No |
| R19 | HARVEST-001 #4 | Proposed | No: awaiting approval; owner labelling tested (CERT-03, #193) |
| R20 | BOTANICAL-IDENTITIES-VISUAL-001 #6 | Proposed, with an accessibility condition | No |
| R21 | CONTROLS-001 #3, Workbench clause | Depends on U04 | No |
| R22 | PORTABLE-COMPOSE-001 #1 | Proposed | No: RC not published |
| R23 | COLLECTION-VISUAL-002 #8 | Proposed | No |
| R24 (was U01) | UI-SYSTEM-001 #4 | Yes (operator decision 2026-11-16, scope-change record) | No: selection, Plant links, fallback, responsive (G-UX Today) |
| R26 | PORTABLE-COMPOSE-001 description, #2, #3, upgrade part of #4 | Yes (ADR 0008, 2026-11-21) | No: INSTALL-001 delivery and real-host gates |
| U02, U03 | UI-SYSTEM-001 #9; GEOGRAPHY-VISUAL-001 #4 | Not applicable | No |
| U04 | UI-REDESIGN-EXPLORATION-001 #6–8 | No | No |
