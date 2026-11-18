# Operator UAT Feedback Intake, Restatement & Release-Scope Decision Ledger

- **Branch:** `docs/batch-07-functional-ux-certification`
- **Base commit (`origin/main`):** `fdc75e83fa8818cab791ed82cbba65f4f97db7ae`
- **Writer identity:** `hydrogen-b-functional-ux-cert` (`49ea62281bdc`)
- **Authority:** [`scope-v1.md`](../scope-v1.md#changing-this-scope), [`restatements-v1.md`](../restatements-v1.md), [`certify/README.md`](certify/README.md)

> **Purpose:** Under [`scope-v1.md`](../scope-v1.md#changing-this-scope), only the operator can approve a scope-change record, confirm a proposed restatement, grant a certification exception, or promote an `in_progress` / `implemented` feature to `verified` after reviewing gate evidence. This document consolidates **every open operator decision** across functional certification, UX certification, Page Inventory v2, and release-work reconciliation, and provides a structured intake template for operator UAT feedback. **Nothing in this ledger is self-approved or pre-applied.**

---

## 1. Proposed Acceptance-Criterion Restatements Awaiting Operator Ruling

Per [`restatements-v1.md`](../restatements-v1.md#proposed-changes-awaiting-approval), the 11 rows below rest on later delivered features (`DL` / `DW`) or Wave 3 UI changes without a separate dated scope-change ruling. Until the operator approves a row for addition to the scope-change table in [`scope-v1.md`](../scope-v1.md#scope-change-record), the original criterion wording in `docs/features.json` remains in force:

| Restatement ID | Feature & Criterion | Summary of Proposed Wording ([`restatements-v1.md`](../restatements-v1.md)) | Committed Evidence on `main` (`fdc75e8`) | Operator Decision Needed |
| --- | --- | --- | --- | --- |
| **`R12`** | `ATTACHMENT-003 #4` | Recognize that thumbnails, derivatives, and the identity media gallery were delivered by later features `ATTACHMENT-004` and `ATTACHMENT-005`, while version history, auto-discovery, provider search, albums, and EXIF inspection remain excluded. | `backend/tests/integration/test_identity_covers.py`; [`certify/attachment-003.md`](certify/attachment-003.md). | `[ ] Approve R12` / `[ ] Reject` |
| **`R13`** | `GEOGRAPHY-003 #3` | Recognize that `"without maps"` was an increment boundary superseded by `MAPS-FOUNDATION-001` and `MAPS-ORIGINS-001`, while `"without geocoding"` remains in force. | [`certify/geography-003.md`](certify/geography-003.md). | `[ ] Approve R13` / `[ ] Reject` |
| **`R14`** | `UX-006 #3` | Clarify that explicit operator-entered scheduled activities (`SCHEDULE-001`), explicit primary photos (`ATTACHMENT-004`), and the approved Today Operational layout (`DT`) are not `"invented reminders, care rules, [or] primary record photos"`. | `DashboardScreen.test.tsx`, `ScheduleScreen.test.tsx`; [`certify/ux-006.md`](certify/ux-006.md). | `[ ] Approve R14` / `[ ] Reject` |
| **`R15`** | `ATTACHMENT-005 #2` | Recognize that explicit primary photo selection was extended from `SeedLot`, `Plant`, and `PlantGroup` to `Harvest` (`HARVEST-001 #4`) and `Supplier` (`SUPPLIER-003`). | `backend/tests/integration/test_primary_photo_api.py`, `test_shared_media.py`; [`certify/attachment-005.md`](certify/attachment-005.md). | `[ ] Approve R15` / `[ ] Reject` |
| **`R17`** | `WCVP-VERSION-001 #1` | Recognize that `WCVP-DEFAULT-001` (PR #174) made `v16` the default while keeping `v15` explicitly selectable and preserving historical `v15` links, proposals, and applications. | [`certify/wcvp-default-001.md`](certify/wcvp-default-001.md), [`certify/wcvp-version-001.md`](certify/wcvp-version-001.md). | `[ ] Approve R17` / `[ ] Reject` |
| **`R18`** | `WCVP-VERSION-001 #4` | Recognize that `WGSRPD-CROSSWALK-V2` (PR #175) expanded new proposals to the 20-pair `v2` crosswalk (withdrawing `COS` for new writes) while retaining the 12 `v1` crosswalk identifiers for frozen proposals and applications. | [`certify/wgsrpd-crosswalk-v2.md`](certify/wgsrpd-crosswalk-v2.md), [`certify/wcvp-version-001.md`](certify/wcvp-version-001.md). | `[ ] Approve R18` / `[ ] Reject` |
| **`R19`** | `HARVEST-001 #4` | Confirm that Harvest visual fallback uses the record's own primary image, then the exact identity cover (labelled with its owner), then a placeholder, and never substitutes a source-plant photo. | Tested in `CERT-03` ([`cert-03.md`](cert-03.md), `HarvestScreen.test.tsx`); [`certify/harvest-001.md`](certify/harvest-001.md). | `[ ] Approve R19` / `[ ] Reject` |
| **`R20`** | `BOTANICAL-IDENTITIES-VISUAL-001 #6` | Replace the removed leading inset selection stripe with a selection fill distinct from hover/focus/checkboxes meeting 3:1 non-text contrast against unselected rows in every shipped theme, plus direct `Details`/`Edit` (`DP`). | `DirectoryPage.test.tsx:603`; requires 6-theme contrast measurement in formal `G-UX`; [`certify/botanical-identities-visual-001.md`](certify/botanical-identities-visual-001.md). | `[ ] Approve R20 (subject to G-UX 3:1 contrast measurement)` / `[ ] Reject` |
| **`R21`** | `CONTROLS-001 #3` | Recognize the Workbench shell (`PR #147`) replacement of mobile navigation and Settings, subject to `U04` disposition and `G-UX` rendered control geometry verification. | `WorkbenchShell.test.tsx:285`, `styles.test.ts:188`; [`certify/controls-001.md`](certify/controls-001.md). | `[ ] Hold with U04` / `[ ] Approve R21` |
| **`R22`** | `PORTABLE-COMPOSE-001 #1` | Attach and verify the attested portable Compose asset on the first `v1.0.0-rc.N` prerelease (`G-DIST`) rather than publishing an extra `v0.1.0-beta.6`. | `REL-01` ([`rel-01.md`](rel-01.md)); [`certify/portable-compose-001.md`](certify/portable-compose-001.md). | `[ ] Approve R22` / `[ ] Require beta.6` |
| **`R23`** | `COLLECTION-VISUAL-002 #8` | Replace the obsolete pre-commit process wording (`"Candidate remains unstaged and uncommitted..."`) with formal `G-UX` visual acceptance on the candidate and explicit disposition of items `CV2-01`–`CV2-08`. | [`certify/collection-visual-002.md`](certify/collection-visual-002.md). | `[ ] Approve R23` / `[ ] Reject` |

---

## 2. Unresolved Evidence Gaps & Historical Process Exceptions Awaiting Operator Disposition

| Gap / Item ID | Affected Feature(s) | Exact Gap Description | Options for Operator Ruling |
| --- | --- | --- | --- |
| **`INV-V2`** | `G-UX` Page Inventory ([`g-ux-pre-rc.md`](g-ux-pre-rc.md)) | Frozen [`page-inventory-v1.md`](../page-inventory-v1.md) omits `Settings → Account` (`#/account`), `#/orders?action=create`, `#/labels?qr=edit` (redirect from `#/settings?tab=general`), and the `#/cuttings?record_type=attempts` toggle. | `[ ] Approve Page Inventory v2 for formal G-UX` |
| **`U02`** | `UI-SYSTEM-001 #9` ([`ui-system-001-certification.md`](ui-system-001-certification.md)) | Non-Preview clauses of `#9` (compact Lists/Galleries, stable directory scrolling after Batch 05 + Batch 07 `WS-B`, semantic lifecycle indicators, modifier-assisted bulk selection, Plant-level random Today samples under `R24`, and committed cross-domain bulk proposal). | `[ ] Accept mapped evidence for U02 (subject to formal RC G-UX)` |
| **`U04` & `R21`** | `UI-REDESIGN-EXPLORATION-001 #6, #7, #8`; `CONTROLS-001 #3` | `PR #147` (`fec0398`) merged the Workbench shell, but `docs/design/florabase-next/` has 0 tracked screenshot files, no committed migration plan, and `docs/design/florabase-next/README.md:3` still states `"Not approved for adoption or merge"`. | `[ ] Record an operator exception / adoption ruling for U04 & R21, gated on formal RC G-UX` / `[ ] Require retroactive paired captures & migration document` |
| **`BRAND-01-GAP`** | `BRAND-01 #1, #2, #3` ([`certify/brand-01.md`](certify/brand-01.md)) | No committed archive manifest in the repo proves the committed icon/logo PNGs/SVGs match the externally approved artwork archive, and `apple-touch-icon.png` has transparent corners rather than an opaque fill. | `[ ] Accept committed artwork assets & transparent-corner apple-touch-icon as-is` / `[ ] Require committed artwork hash manifest or icon replacement` |
| **`QA-PROSE-GAP`** | `WCVP-DEFAULT-001 #4`, `WGSRPD-CROSSWALK-V2 #5`, `MEDIA-VISUAL-001 #2` | Independent QA for `#174` / `#175` and operator direction approval for `MEDIA-VISUAL-001 #2` were recorded only in `docs/progress.md` / PR bodies rather than separate committed evidence files. | `[ ] Accept progress.md / PR-body provenance plus candidate canonical FULL & G-UX` / `[ ] Require retroactive standalone QA records` |
| **`CV2-01..08`** | `COLLECTION-VISUAL-002` ([`restatements-v1.md`](../restatements-v1.md#other-proposed-rows)) | `CV2-01` (Harvest/Location visual acceptance), `CV2-02` (native `window.confirm` dirty prompt), `CV2-03` (200% zoom), `CV2-04` (Harvest detail height vs `"one-page"`), `CV2-06` (deferred directory filters beyond identity), `CV2-07` (`handoff:31` stale text), `CV2-08` (seed-conversion fieldset border). | `[ ] Evaluate CV2-01, CV2-02, CV2-03, CV2-04, CV2-08 in formal RC G-UX; rule CV2-06 out of v1.0 scope; close CV2-05/CV2-07` |
| **`FABLE-DP`** | `FABLE-FIX-CUTTINGS #1, #4` ([`certify/fable-fix-cuttings.md`](certify/fable-fix-cuttings.md)) | Criteria `#1` and `#4` mention `"Quick Preview"` and `"preview close"`, which decision **DP** replaced with direct `Details` across directories. | `[ ] Confirm decision DP applies to FABLE-FIX-CUTTINGS #1, #4` |
| **`CERT-05-REC`** | `BETA-IMAGE-001`, `beta-postgres-repro-001` ([`cert-05.md`](cert-05.md)) | `CERT-05` recommendations 1–3: supersession of `v0.1.0-beta.1` by `v0.1.0-beta.5`, acceptance of `#158` QA/FULL for `BETA-IMAGE-001 #6`, and acceptance of hosted rehearsal + `#158` FULL for `beta-postgres-repro-001 #7`. | `[ ] Approve CERT-05 recommendations 1–3 to move BETA-IMAGE-001 and beta-postgres-repro-001 to implemented` |
| **`BATCH-06-SEC`** | `BETA-SECURITY-001` ([`wf-04-batch-06.md`](wf-04-batch-06.md)) | Separate 18 November Grype scanner dispositions / VEX assessment and final digest-bound RC scans ([`wf-04-batch-06.md`](wf-04-batch-06.md#scanner-provenance)). | `[ ] Operator security disposition during RC image preflight (G-SEC)` |

---

## 3. Operator Live UAT Feedback Intake Template

When the operator conducts interactive UAT on the integrated Batch 07 preview or release candidate, record each observation below so it can be triaged into either a bounded WF-04 defect fix, a confirmed restatement, or a post-1.0 backlog item:

| Intake ID | Date | Surface / Route (`#/…`) | Viewport / Theme / Zoom | Observed Behavior vs. Expected Behavior | Classification (`Blocker P0` / `High P1` / `Medium P2` / `Low P3` / `Restatement` / `Post-1.0`) | Operator Disposition |
| --- | --- | --- | --- | --- | --- | --- |
| `UAT-01` | *Pending operator UAT* | | | | | |
| `UAT-02` | *Pending operator UAT* | | | | | |
| `UAT-03` | *Pending operator UAT* | | | | | |
