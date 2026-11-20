# Certification evidence maps

Each file maps the committed and frozen pre-RC evidence for one `certify` entry of the
[release-scope manifest](../../scope-v1.json), criterion by criterion, as the
[scope](../../scope-v1.md#certification-of-delivered-features) requires. The first thirteen maps
were written in Batch 03 under registered source identifier `CERT-01` against `main`
`554d74de88a278e2b9a392de9d105d3d62c35f91`; the remaining twenty-seven maps were added and
reconciled in Batch 07 (`docs/batch-07-functional-ux-certification`, reusing registered `tooling`
identifier `CERT-01` without inventing a new identifier or changing release membership) against
`main` `fdc75e83fa8818cab791ed82cbba65f4f97db7ae`.

Approved Batch 07 frozen sources referenced by these pre-RC maps and dossiers (all pending WF-04
integration and combined-candidate verification):

- **Source A — AUTH** (`fix/session-expiry-draft-recovery`, `HEAD` `08c0bb353d98ac752a5828fe8f207fe44ad789cd`, `tree` `0728f6963e1d97642f1d49f102b76e84a7ce586b`; Technical: Opus `PASS`, Security: SOL `PASS` via `BATCH07_AUTH_PRIVATE_ISSUANCE_FINAL_APPROVAL`).
- **Source B — Mobile UX** (`fix/mobile-directory-ux-defects`, `HEAD` `39080cb84145e3e70b4ae38179169fb7af36d7ba`, `tree` `bcac78212b0b80d0faa6e6a72af70067dd599d41`; Independent: Argon `PASS`).
- **Source D — Performance Harness** (`feat/perf-001-comprehensive-harness`, `HEAD` `143bbc8ad69d07a47551f01976017c6218ff9a3b`, `tree` `c661003def6f15934836a31df256310832a04478`; Independent: Sonnet `PASS`).
- **Source E — Golden COMPREHENSIVE Pin** (`fix/golden-comprehensive-crosswalk-pin`, `HEAD` `81848389b93204fb13dabf020aa5061c4d869072`, `tree` `2f3b1dd4928dbabb1309c43960419fedd628faf1`; Independent: Opus `PASS`).

`ENG-02`, `ENG-03`, and Portable Smoke Hardening are approved future-batch sources outside Batch 07
and are not represented as part of Batch 07's implementation or certification evidence.

A map is not certification, and source-level review approval is not formal RC acceptance. These
records change no `features.json` status or `scope-v1.json` membership. A status changes only after
post-WF-04 combined-candidate checks ([`../g-core-pre-rc.md`](../g-core-pre-rc.md#5-required-post-wf-04-combined-candidate-verification-obligations)),
formal candidate gate records (`G-CORE`, `G-UX`, `G-PERF`, `G-SEC`, etc.) exist on the immutable
release-candidate images, and the operator accepts any required restatement or exception.

Related pre-RC Batch 07 certification dossiers:

- [`../g-core-pre-rc.md`](../g-core-pre-rc.md) — Canonical 12-step pre-RC G-CORE functional evidence package, reconciled AUTH closure record, and post-WF-04 combined-candidate verification checklist.
- [`../g-ux-pre-rc.md`](../g-ux-pre-rc.md) — 22-entry pre-RC G-UX matrix and proposed Page Inventory v2 (frozen `page-inventory-v1.md` untouched).
- [`../cutting-001-acceptance.md`](../cutting-001-acceptance.md) — `CUTTING-001` (`FN-01`) and `FABLE-FIX-CUTTINGS` pre-RC acceptance dossier.
- [`../ui-system-001-certification.md`](../ui-system-001-certification.md) — `UI-SYSTEM-001` and related UI architecture certification dossier.
- [`../uat-operator-feedback-intake.md`](../uat-operator-feedback-intake.md) — Consolidated operator decision, restatement, gate status, and live UAT feedback intake ledger.

How to read the State column:

- **Mapped:** committed tests or records cover the criterion. They still need the canonical gate
  result on the candidate commit.
- **Pending G-UX** or **Pending G-CORE step N:** the criterion relies on that part of the gate
  record, which uses the [G-UX](../g-ux-template.md) or [G-CORE](../g-core-template.md) template.
- **Pending candidate gate:** the criterion itself requires canonical verification (`G-VERIFY`,
  `G-MIGRATE`, `G-INSTALL`, `G-UPGRADE`, `G-RESTORE`, `G-DOCS`, or `G-DIST`).
- **Gap:** no committed evidence covers the criterion as currently worded, or the criterion awaits
  an operator ruling on a proposed restatement (`R12`–`R15`, `R17`–`R23`) or open exception (`U04`).

Evidence that exists only in `progress.md` prose, a worktree receipt, a PR body or outside the
repository is listed as "Not counted" in each map.

| Entry | Status | Mapped | Pending | Gaps / Operator Rulings Needed |
| --- | --- | --- | --- | --- |
| [TAXONOMY-002](taxonomy-002.md) | `implemented` | 4/4 | — | — |
| [PHENOLOGY-001](phenology-001.md) | `implemented` | 4/5 | G-UX #4 | — |
| [UI-POLISH-001](ui-polish-001.md) | `implemented` | 4/5 | candidate gate #5 | — |
| [WCVP-DEFAULT-001](wcvp-default-001.md) | `implemented` | 3/4 | candidate gate #4 | #4: no committed independent QA record |
| [WGSRPD-CROSSWALK-V2](wgsrpd-crosswalk-v2.md) | `implemented` | 4/5 | candidate gate #5 | #5: no committed independent QA record |
| [BRAND-01](brand-01.md) | `implemented` | 0/3 | G-UX #2 | #1–#3: no committed record that the artwork is the approved one; the archive manifest is not in the repository |
| [GERMINATION-001](germination-001.md) | `implemented` | 3/3 | — | — |
| [SEARCH-001](search-001.md) | `implemented` | 3/3 | — | — |
| [IMPORT-001](import-001.md) | `implemented` | 3/3 | — | — |
| [LINEAGE-003](lineage-003.md) | `implemented` | 2/3 | G-UX #3 (the captures predate Cuttings) | — |
| [LOCATION-003](location-003.md) | `implemented` | 3/4 | G-UX #3 (restated by R25) | — |
| [GEOGRAPHY-003](geography-003.md) | `implemented` | 2/3 | G-UX #3 | #3: "without maps" conflicts with `main` until proposed R13 is ruled on |
| [MEDIA-VISUAL-001](media-visual-001.md) | `implemented` | 3/5 | G-UX and candidate gate #5 | #2: operator direction approval stated only in prose |
| [ENG-01](eng-01.md) | `implemented` | 1/4 | G-CORE step 11 (#1, #2); G-SEC #4 / G-DIAG & portable smoke (#1, #3) | — |
| [ATTACHMENT-003](attachment-003.md) | `implemented` | 2/4 | G-CORE step 5 (#1) | #4: awaits operator ruling on proposed R12 |
| [ATTACHMENT-005](attachment-005.md) | `implemented` | 3/7 | G-CORE step 5 (#2); G-UX (#4, #7); G-RESTORE (#6); candidate gate (#7) | #2: awaits operator ruling on proposed R15 |
| [HARVEST-001](harvest-001.md) | `implemented` | 4/8 | G-CORE step 8 (#1); G-UX (#4, #5); candidate gate (#7) | #4: awaits operator ruling on proposed R19 (tested in CERT-03) |
| [PWA-001](pwa-001.md) | `implemented` | 2/3 | G-UX Shell surfaces (#1) | #1: physical mobile-browser installability governed by optional `FN-07` disposition |
| [CUTTING-001](cutting-001.md) | `in_progress` | 1/7 | G-CORE step 12 (#2–#7); G-UX Cuttings & Lineage (#2, #6, #7); candidate gate (#7) | #7: requires WF-04 integration of Sources A/B, combined-candidate checks, canonical FULL, formal RC G-CORE step 12 & G-UX, and operator acceptance |
| [UX-002](ux-002.md) | `implemented` | 3/3 | — | — |
| [UX-003](ux-003.md) | `implemented` | 1/3 | G-UX Seeds, Sowings, Plants, Journal (#1, #2) | — |
| [UX-004](ux-004.md) | `implemented` | 1/3 | G-CORE step 2 (#2); G-UX Botanical identities (#1, #2) | — |
| [UX-005](ux-005.md) | `implemented` | 0/3 | G-CORE step 3 (#1); G-UX Suppliers, Locations, Geography (#1–#3) | — |
| [UX-006](ux-006.md) | `implemented` | 2/3 | G-CORE step 7 (#3); G-UX Today, Journal, History (#3) | #3: awaits operator ruling on proposed R14 |
| [LOCATION-002](location-002.md) | `implemented` | 2/3 | G-CORE step 6 & G-UX Locations (#3) | — |
| [MAP-001](map-001.md) | `implemented` | 7/8 | G-UX Geography and sub-views `#/map` (#6) | — |
| [WCVP-VERSION-001](wcvp-version-001.md) | `implemented` | 3/5 | — | #1: awaits operator ruling on proposed R17; #4: awaits operator ruling on proposed R18 |
| [COLLECTION-VISUAL-002](collection-visual-002.md) | `implemented` | 1/8 | G-UX Harvests & Locations (#1–#5, #7, #8) | #7, #8: awaits operator ruling on proposed R23 and items CV2-01–CV2-08 |
| [THEMES-001](themes-001.md) | `implemented` | 2/4 | G-UX all entries column C (#3) and Settings/Labels (#4) | — |
| [CONTROLS-001](controls-001.md) | `implemented` | 2/4 | G-CORE step 9 (#4); G-UX (#3, #4) | #3: awaits operator ruling on R21 / U04 |
| [GEOGRAPHY-VISUAL-001](geography-visual-001.md) | `implemented` | 4/8 | G-UX Geography (#1, #2, #4 U03, #7); candidate gate (#7) | — |
| [BOTANICAL-IDENTITIES-VISUAL-001](botanical-identities-visual-001.md) | `implemented` | 6/10 | G-UX Botanical identities (#1, #3, #6, #10); candidate gate (#10) | #6: awaits operator ruling on proposed R20 and 3:1 theme contrast measurement in G-UX |
| [UI-SYSTEM-001](ui-system-001.md) | `in_progress` | 3/10 | G-CORE step 1 (#4); G-UX (#3, #4, #7–#10); candidate gate (#6) | #9, #10: requires WF-04 integration of Sources A/B, combined-candidate checks, operator acceptance of U02, and formal RC G-UX |
| [UI-SYSTEM-WAVE2-001](ui-system-wave2-001.md) | `implemented` | 3/6 | G-UX Journal, History, Schedule, Suppliers, Orders (#2, #3, #6); candidate gate (#6) | — |
| [UI-REDESIGN-EXPLORATION-001](ui-redesign-exploration-001.md) | `implemented` | 1/8 | G-CORE step 6 (#3); G-UX all entries (#2, #4, #5) | #6, #7, #8: open gap U04 requires explicit operator adoption/exception ruling |
| [PORTABLE-COMPOSE-001](portable-compose-001.md) | `implemented` | 1/5 | G-INSTALL, G-UPGRADE, G-RESTORE, G-DOCS (#3); candidate gate & portable smoke (#4, #5); G-DIST (#1) | #1: awaits operator ruling on proposed R22 |
| [MEASUREMENT-001](measurement-001.md) | `implemented` | 4/5 | G-UX Plants detail (#4) | — |
| [FABLE-FIX-CUTTINGS](fable-fix-cuttings.md) | `implemented` | 1/5 | G-UX Cuttings (#2–#4); candidate gate (#5) | #1, #4: confirm decision DP applies to Quick Preview wording (`FABLE-DP`) |
| [UX-DATE-001](ux-date-001.md) | `implemented` | 4/6 | G-CORE step 3 (#2) and step 5 (#3, restated by R01) | — |
| [UX-TODAY-001](ux-today-001.md) | `implemented` | 2/6 | G-CORE step 1 (#4) and step 7 (#3); G-UX Today (#1, #4, #6) | — |

Gaps need an operator decision. Either commit the missing record, such as an independent QA
report or the approved-artwork manifest, or record an exception in [`../../scope-v1.md`](../../scope-v1.md).
