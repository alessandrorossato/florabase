# Feature reconciliation for the v1.0 scope

Reconciles every entry of [`features.json`](../features.json) as it stood at the audit baseline
`947d77fc8bd2a757cdf49e28ec2e0f85b0374f1b` (156 entries) with the approved
[v1.0 release scope](scope-v1.md). Line numbers refer to [`progress.md`](../progress.md) at that
commit; files are under `docs/`; `#NNN` are pull requests on `main`.

## Rules applied

- A status changes only when the repository itself demonstrates the new status. Code on `main`
  or a passing broad CI run is not evidence that a feature's acceptance criteria were exercised.
- `implemented` → `verified` needs recorded evidence for every acceptance criterion: a passed
  canonical gate on the delivered tree, independent QA, and operator acceptance where the feature
  asked for it. One entry met this. Two more are named as candidates and left unchanged.
- `in_progress` → `implemented` needs the delivering commit on `main`. Two entries met this.
- No entry was demoted. Verified entries with later contrary evidence are flagged, not changed.
- The release target is **proposed** here and is not stored in `features.json`; see the
  [schema follow-up](release-target-schema-followup.md).
- Evidence that exists only as a worktree-local verification receipt is not in the repository
  and could not be inspected. Such entries are stated as recorded, not confirmed.

## Totals

| Status | Baseline | After this change |
| --- | --- | --- |
| `verified` | 77 | 78 |
| `implemented` | 52 | 53 |
| `in_progress` | 11 | 9 |
| `planned` | 16 | 16 |
| Total | 156 | 156 |

The feature graph also gains one entry for this documentation increment (RELEASE-SCOPE-001),
which is outside the 156 reconciled here.

| Proposed release target | Entries | Meaning |
| --- | --- | --- |
| 1.0 baseline | 78 | Verified and part of the delivered 1.0 baseline. |
| PRE-1.0 certify | 38 | On `main` and in scope; its acceptance criteria must be evidenced on the release candidate. |
| PRE-1.0 release work | 6 | Distribution and acceptance work that the release gates consume. |
| best-effort (not certified) | 3 | Controller bundle; kept, not certified (approved decision 3). |
| tooling (not a release deliverable) | 13 | Development workflow or test data; its status does not gate the release. |
| historical record | 3 | Audit or design record with no product deliverable; close without certification. |
| internal foundation | 1 | Delivered foundation with no user-facing surface. |
| POST-1.0 | 14 | Outside the 1.0 contract. |

## Status changes made in this increment

| ID | Change | Evidence |
| --- | --- | --- |
| ATTACHMENT-004 | `implemented` → `verified` | PROMOTED. Canonical gate passed, independent QA fixed a race with a regression, operator manual review passed (progress 3382-3432); each of the four criteria maps to recorded checks. |
| UI-REDESIGN-EXPLORATION-001 | `in_progress` → `implemented` | CORRECTED from `in_progress`: the Workbench shell is on main since `fec0398` (#147, 159 files; adds `frontend/src/shell/WorkbenchShell.tsx`). The description still says experimental. "Canonical FULL not run" at the last record, so not `verified`. |
| FABLE-FIX-CUTTINGS | `in_progress` → `implemented` | CORRECTED from `in_progress`: delivered on main in `947d77f` (#177, cherry-pick of `e325040`); batch browser QA recorded (progress 8765-8801). Not `verified`: persisted before/after screenshots (criterion 5) are outstanding. |

## Promotion candidates left unchanged

These have a recorded canonical pass and independent QA and lack only one recorded item. The
operator can close them with a one-line acceptance record.

- **GERMINATION-001** — Promotion candidate: canonical gate and independent QA passed (progress 3456). Missing only a recorded operator visual-review outcome.
- **MULTIBRANCH-UAT-001** — Promotion candidate: FULL passed in 933 s, smoke and delta QA passed (progress 8199-8222). "Unresolved: operator UAT".

## Verified entries that need attention

- **TAXONOMY-001** — Two concurrency findings recorded open (progress 138, 408). Status not changed here; needs a fix or a written accepted-risk record before the RC.
- **DASHBOARD-001** — Its photo-first layout was deliberately reversed by UX-TODAY-001 (progress 8740); the verified evidence describes the earlier layout.
- Eleven verified entries depend on entries that are not verified; each is marked in the matrix.
  Dependency satisfaction was never a verification rule, so no status changes, but the release
  certification should close the dependencies first.

## Matrix

| ID | Status | Proposed target | Existing evidence | Gap or note |
| --- | --- | --- | --- | --- |
| FOUNDATION-001 | `verified` | 1.0 baseline | progress.md mentions only (1) |  |
| OPS-001 | `verified` | 1.0 baseline | progress.md mentions only (1) |  |
| DOCS-001 | `verified` | 1.0 baseline | progress.md:4502 |  |
| CI-001 | `verified` | 1.0 baseline | progress.md:4470 · 4556026#9 |  |
| CI-002 | `verified` | 1.0 baseline | progress.md:4205, 4213 · 0259cef#19 |  |
| CI-003 | `verified` | 1.0 baseline | progress.md:1216, 1239, 2622, 2643 · `ci-003-resource-impact-handoff.md`; `ci-003-full-migration-cycle-repair-handoff.md` |  |
| CI-004 | `implemented` | tooling (not a release deliverable) | progress.md:803, 837, 853 · `ci-004-verification-efficiency-handoff.md`; `ci-004-verification-efficiency-evidence.json` | Log: "CI-004 remains `implemented`, not `verified`"; final FULL pending at the last record. |
| CI-HYGIENE-001 | `implemented` | tooling (not a release deliverable) | progress.md:8131 | Canonical evidence is said to live in the worktree receipt, which is not in the repository. |
| AGENT-WORKFLOW-001 | `implemented` | tooling (not a release deliverable) | progress.md:7332 · `agent-workflow-001-handoff.md` | Log: "pending re-review, then a new canonical FULL"; status stays `implemented`. |
| PREVIEW-001 | `verified` | 1.0 baseline | progress.md:2013, 2089, 2140, 4634 · `preview-001-handoff.md` |  |
| RELEASE-001 | `planned` | PRE-1.0 release work | progress.md mentions only (9) | Written for 0.1.0; superseded in substance by `scope-v1.md` gates. Keep the ID, re-scope when the schema follow-up lands. |
| PERF-001 | `verified` | 1.0 baseline | progress.md:3275 | Depends on unverified: UX-006. |
| SECURITY-001 | `verified` | 1.0 baseline | progress.md mentions only (1) |  |
| SECURITY-002 | `verified` | 1.0 baseline | progress.md mentions only (1) |  |
| DOMAIN-001 | `verified` | 1.0 baseline | progress.md mentions only (1) |  |
| DATABASE-001 | `verified` | 1.0 baseline | progress.md mentions only (1) |  |
| BACKEND-001 | `verified` | 1.0 baseline | progress.md mentions only (1) |  |
| FRONTEND-002 | `verified` | 1.0 baseline | progress.md mentions only (1) |  |
| FRONTEND-001 | `verified` | 1.0 baseline | progress.md mentions only (1) |  |
| IDENTITY-001 | `verified` | 1.0 baseline | progress.md mentions only (1) |  |
| ATTACHMENT-001 | `verified` | 1.0 baseline | no progress.md record |  |
| TESTING-001 | `verified` | 1.0 baseline | progress.md mentions only (1) |  |
| PROFILE-001 | `verified` | 1.0 baseline | progress.md mentions only (1) |  |
| PROFILE-002 | `verified` | 1.0 baseline | progress.md mentions only (1) |  |
| BOTANY-002 | `verified` | 1.0 baseline | progress.md:3980 |  |
| BOTANY-003 | `planned` | POST-1.0 | progress.md:1439, 2467, 2497, 2524 · `botany-003-audit.md`; `botany-003-handoff.md` | SOURCE_BLOCKED (`botanical-profile-enrichment-sources.md`). |
| SUPPLIER-001 | `verified` | 1.0 baseline | no progress.md record |  |
| LOCATION-001 | `verified` | 1.0 baseline | no progress.md record |  |
| GEOGRAPHY-001 | `verified` | 1.0 baseline | progress.md mentions only (2) |  |
| GEOGRAPHY-002 | `verified` | 1.0 baseline | progress.md:3957 |  |
| SEED-001 | `verified` | 1.0 baseline | progress.md mentions only (1) |  |
| SEED-002 | `verified` | 1.0 baseline | no progress.md record |  |
| SEED-003 | `verified` | 1.0 baseline | no progress.md record |  |
| SEED-004 | `verified` | 1.0 baseline | progress.md mentions only (1) |  |
| SOWING-001 | `verified` | 1.0 baseline | progress.md:4561 |  |
| SOWING-002 | `verified` | 1.0 baseline | no progress.md record |  |
| SOWING-003 | `verified` | 1.0 baseline | progress.md:4561 |  |
| PLANT-001 | `verified` | 1.0 baseline | progress.md:4552 |  |
| PLANT-002 | `verified` | 1.0 baseline | progress.md:4552 · 09f42e6 |  |
| PLANT-003 | `verified` | 1.0 baseline | progress.md:4544 · 1c07096 |  |
| LINEAGE-001 | `verified` | 1.0 baseline | no progress.md record |  |
| LINEAGE-002 | `verified` | 1.0 baseline | progress.md:4534 · 59a96de |  |
| EVENT-001 | `verified` | 1.0 baseline | progress.md:4447 |  |
| EVENT-002 | `verified` | 1.0 baseline | progress.md:4418 |  |
| ATTACHMENT-002 | `verified` | 1.0 baseline | progress.md:3846 |  |
| ATTACHMENT-003 | `implemented` | PRE-1.0 certify | progress.md:3809 | Log records the canonical gate's coverage; no independent QA or operator acceptance record. |
| ATTACHMENT-004 | `implemented` → **`verified`** | 1.0 baseline | progress.md:3382, 3420 · `attachment-004-review.md` | PROMOTED. Canonical gate passed, independent QA fixed a race with a regression, operator manual review passed (progress 3382-3432); each of the four criteria maps to recorded checks. |
| ATTACHMENT-005 | `implemented` | PRE-1.0 certify | progress.md:2789, 2811 | Log: "awaiting operator visual acceptance". |
| HARVEST-001 | `implemented` | PRE-1.0 certify | progress.md:2756 | Log: "remains `implemented` pending operator acceptance". HARVEST-002/003 (verified) depend on it. |
| HARVEST-002 | `verified` | 1.0 baseline | progress.md:2288, 2340, 2366, 2402 | Depends on unverified: HARVEST-001, LOCATION-003. |
| GERMINATION-001 | `implemented` | PRE-1.0 certify | progress.md:3433, 3456 | Promotion candidate: canonical gate and independent QA passed (progress 3456). Missing only a recorded operator visual-review outcome. |
| PWA-001 | `implemented` | PRE-1.0 certify | progress.md:181 | Physical Android/iOS installation unverified (`pwa.md`). Certify on devices or label experimental in 1.0. |
| ORDER-001 | `verified` | 1.0 baseline | progress.md:1694, 1708, 1738 · `order-001-handoff.md` |  |
| EVENT-003 | `planned` | POST-1.0 | no progress.md record | No work recorded. The watering/feeding kinds (decision 5) need their own bounded increment ID, not this entry. |
| PLANT-004 | `verified` | 1.0 baseline | progress.md:4522 · 5a9fb41 |  |
| TUBER-001 | `planned` | POST-1.0 | no progress.md record | No work recorded. |
| CUTTING-001 | `in_progress` | PRE-1.0 certify | progress.md:8432, 8446, 8463, 8481 · `cutting-001-design.md` · 18dda87#168 | Delivered on main in #167 (routes, migration 0047, navigation) but acceptance pending; an active writer (`codex-cutting-31a6`) holds uncommitted Cuttings work. Decision 6: finish and certify. |
| LABEL-001 | `verified` | 1.0 baseline | progress.md:3332, 3354 · `label-001-review.md` |  |
| SEARCH-001 | `implemented` | PRE-1.0 certify | progress.md:3471, 3485, 3501 | Log: canonical gate "remains for later review"; no later record. |
| SEARCH-002 | `verified` | 1.0 baseline | progress.md:2013, 2038 · `search-002-handoff.md` | Depends on unverified: SEARCH-001, HARVEST-001, ATTACHMENT-005. |
| VIEW-001 | `verified` | 1.0 baseline | progress.md:1927, 1945, 1965, 1987 · `view-001-handoff.md` |  |
| BULK-001 | `verified` | 1.0 baseline | progress.md:1856, 1874, 1895 · `bulk-001-handoff.md` |  |
| HISTORY-001 | `verified` | 1.0 baseline | progress.md:1786, 1800, 1830 · `history-001-handoff.md` | Depends on unverified: GERMINATION-001. |
| DASHBOARD-001 | `verified` | 1.0 baseline | progress.md:4704, 4721, 4743 · `dashboard-001-handoff.md`; `dashboard-001-audit.md` | Its photo-first layout was deliberately reversed by UX-TODAY-001 (progress 8740); the verified evidence describes the earlier layout. Depends on unverified: GERMINATION-001. |
| UX-001 | `verified` | 1.0 baseline | progress.md:4393 |  |
| UX-002 | `implemented` | PRE-1.0 certify | progress.md:3748 | Canonical gate passed (progress 3748); "pending independent review and release UAT". |
| PROPAGATION-001 | `verified` | 1.0 baseline | progress.md:4351 |  |
| PROPAGATION-002 | `verified` | 1.0 baseline | progress.md:3898, 4317 · 110ef07#15 |  |
| PLANT-005 | `verified` | 1.0 baseline | progress.md:4289 |  |
| REVERSAL-001 | `verified` | 1.0 baseline | progress.md:4247 |  |
| PLANT-006 | `verified` | 1.0 baseline | progress.md:4161, 4170, 4182 · e9cee60#21 |  |
| PROPAGATION-003 | `verified` | 1.0 baseline | progress.md:4134 |  |
| UX-003 | `implemented` | PRE-1.0 certify | progress.md:3774 | "pending independent review and final browser UAT". |
| UX-004 | `implemented` | PRE-1.0 certify | progress.md:3668, 3718 · `ux-004-reference.md` | Operator accepted the direction on 2026-09-22; no per-criterion verification record. Shell since replaced by the Workbench (#147). |
| UX-005 | `implemented` | PRE-1.0 certify | progress.md:3647, 3652, 3658 | Operator accepted the general direction and deferred refinements; no verification record. |
| UX-006 | `implemented` | PRE-1.0 certify | progress.md:3639 | Independently reviewed; "pending delivery workflow". RELEASE-001 and PERF-001 depend on it. |
| LOCATION-002 | `implemented` | PRE-1.0 certify | progress.md:4115 | Log: canonical gate "intentionally not run"; pending independent review. |
| LOCATION-003 | `implemented` | PRE-1.0 certify | progress.md:2844 | Final review confirmed the contract and a matching receipt; "pending final commit and delivery". |
| GEOGRAPHY-003 | `implemented` | PRE-1.0 certify | progress.md:4091 | Canonical gate "reserved for independent review"; no later record. |
| MAP-001 | `implemented` | PRE-1.0 certify | progress.md:4042 | Canonical gate "reserved for independent review"; no later record. |
| EXPLORE-001 | `verified` | 1.0 baseline | progress.md:1643, 1661 · `explore-001-handoff.md` |  |
| EXPLORE-002 | `verified` | 1.0 baseline | progress.md:1548, 1567, 1605 · `explore-002-handoff.md` |  |
| MAP-002 | `verified` | 1.0 baseline | progress.md:3871 |  |
| SUPPLIER-002 | `verified` | 1.0 baseline | progress.md:4069 |  |
| SUPPLIER-003 | `verified` | 1.0 baseline | progress.md:2155 · `supplier-003-handoff.md` | Depends on unverified: ATTACHMENT-005. |
| IMPORT-001 | `implemented` | PRE-1.0 certify | progress.md:3527, 3538, 3555, 3584 | Operator UAT on real collection data outstanding. Carries the CSV contract promised by decision 4. |
| LINEAGE-003 | `implemented` | PRE-1.0 certify | progress.md:364 | Delivered in #167; "pending canonical verification" at the feature record. |
| ENRICHMENT-001 | `verified` | 1.0 baseline | progress.md:1477, 1498 · `enrichment-001-handoff.md` |  |
| WCVP-VERSION-001 | `implemented` | PRE-1.0 certify | progress.md:335 · `wcvp-version-001.md` | "Operator acceptance remains pending". |
| WCVP-DEFAULT-001 | `implemented` | PRE-1.0 certify | progress.md:35 · b94757e#174 | Delivered in #174; FULL and independent QA said to run on the rebased commit, result not recorded in the log. |
| WGSRPD-CROSSWALK-V2 | `implemented` | PRE-1.0 certify | progress.md:8657 | Delivered in #175; verification recorded only in the worktree receipt. |
| ENRICHMENT-002 | `planned` | POST-1.0 | progress.md mentions only (6) | Deferred in the roadmap. |
| TAXONOMY-001 | `verified` | 1.0 baseline | progress.md:266, 8422 · 48f35ea#165 | Two concurrency findings recorded open (progress 138, 408). Status not changed here; needs a fix or a written accepted-risk record before the RC. |
| TAXONOMY-002 | `implemented` | PRE-1.0 certify | progress.md:172 | Delivered in #167; log: no individual canonical receipt (consolidated integration policy). |
| WEATHER-001 | `planned` | POST-1.0 | no progress.md record | No work recorded. |
| REMINDER-001 | `planned` | POST-1.0 | no progress.md record | No work recorded. |
| ANALYSIS-001 | `planned` | POST-1.0 | no progress.md record | No work recorded. |
| TRANSFER-001 | `planned` | POST-1.0 | no progress.md record | No work recorded. Not required by decision 4 (paired backup and CSV are the 1.0 data contracts). |
| INTEGRATION-001 | `planned` | POST-1.0 | no progress.md record | No work recorded. |
| SECURITY-003 | `planned` | POST-1.0 | no progress.md record | Multi-user; outside the single-owner 1.0 contract. |
| HARVEST-003 | `verified` | 1.0 baseline | progress.md:2209 · `harvest-003-handoff.md` |  |
| BOTANY-004 | `planned` | POST-1.0 | progress.md mentions only (2) | Depends on source-blocked BOTANY-003. |
| TAXONOMY-003 | `verified` | 1.0 baseline | progress.md:1402, 4645 · `taxonomy-003-source.md`; `taxonomy-003-handoff.md` |  |
| PHYLOGENY-001 | `planned` | POST-1.0 | progress.md:1364 · `phylogeny-001-source.md`; `phylogeny-001-handoff.md` | SOURCE_BLOCKED (`phylogeny-001-source.md`, `phylogeny-001-handoff.md`). |
| SCHEDULE-001 | `verified` | 1.0 baseline | progress.md:1288, 1311 · `schedule-001-handoff.md` |  |
| SCHEDULE-002 | `verified` | 1.0 baseline | progress.md:4755, 4776, 4801, 4831 · `schedule-002-handoff.md` |  |
| INFRA-MAINT-001 | `implemented` | tooling (not a release deliverable) | progress.md:4852 · `infra-maint-001-handoff.md`; `infra-maint-001-evidence.json` | Log: "No canonical feature-verify" at the feature record; landed in PR #106. |
| ACTIVITY-001 | `verified` | 1.0 baseline | progress.md:4913, 4945, 4982, 5024 |  |
| IA-FREEZE-001 | `verified` | 1.0 baseline | progress.md:5086, 5124, 5164, 5195 | Depends on unverified: IMPORT-001. |
| GLOBAL-VISUAL-001 | `verified` | 1.0 baseline | progress.md:5287, 5325, 5356, 5386 · `global-visual-001-handoff.md` |  |
| COLLECTION-VISUAL-001 | `verified` | 1.0 baseline | progress.md:1165, 5619, 5651, 5677 · `collection-visual-001-handoff.md` |  |
| COLLECTION-VISUAL-002 | `implemented` | PRE-1.0 certify | progress.md:1099, 1116, 1135 · `collection-visual-002-handoff.md` | "pending operator acceptance and independent canonical verification". |
| MAPS-FOUNDATION-001 | `verified` | 1.0 baseline | progress.md:5757, 5785, 5812, 5837 · `maps-foundation-001-handoff.md`; `maps-foundation-001-design.md` |  |
| MAPS-DISTRIBUTION-001 | `verified` | 1.0 baseline | progress.md:5898, 5926, 5961, 5983 · `maps-distribution-001-cache-design.md`; `maps-distribution-001-handoff.md` |  |
| MAPS-ORIGINS-001 | `verified` | 1.0 baseline | progress.md:6005, 6042, 6106, 6128 · `maps-origins-001-handoff.md`; `maps-origins-001-design.md` | Depends on unverified: MAP-001. |
| THEMES-001 | `implemented` | PRE-1.0 certify | progress.md:915, 941, 968 · `themes-001-implementation-plan.md`; `themes-001-token-matrix.md` · e7ade78#120 | Delivered in #120; assistive technology, zoom, raster and printing checks explicitly pending. |
| CONTROLS-001 | `implemented` | PRE-1.0 certify | progress.md:915, 968 · `controls-001-design-contract.md`; `controls-001-handoff.md` | Delivered with THEMES-001; same pending checks. |
| GEOGRAPHY-VISUAL-001 | `implemented` | PRE-1.0 certify | progress.md:6269, 6316, 6356, 6415 · `geography-visual-001-handoff.md` | "Canonical FULL, protected delivery and feature-finish remain pending" at the last record. |
| BOTANICAL-IDENTITIES-VISUAL-001 | `implemented` | PRE-1.0 certify | progress.md:6146, 6169, 6195, 6230 · `botanical-identities-visual-001-handoff.md` | Provider imagery, touch/AT/zoom and operator composition acceptance pending. |
| TAXONOMY-VISUAL-001 | `verified` | 1.0 baseline | progress.md:744, 773, 6488, 6511 · `taxonomy-visual-001-handoff.md` | Depends on unverified: THEMES-001, CONTROLS-001, BOTANICAL-IDENTITIES-VISUAL-001. |
| MEDIA-VISUAL-001 | `implemented` | PRE-1.0 certify | progress.md:645, 671, 694, 723 · `media-visual-001-design-review.md` | Delivered in #127; "remains `implemented` until all acceptance and receipt evidence is complete". |
| RELEASE-VISUAL-AUDIT-001 | `implemented` | historical record | progress.md:611 | Audit/design record with no product deliverable; operator decision was pending. Close without certification. |
| UI-SYSTEM-001 | `in_progress` | PRE-1.0 certify | progress.md:578, 6539, 6572, 6601 | Gate B review candidate; later waves closed around it. Needs an operator decision to close at the delivered state. |
| DASHBOARD-CUSTOMIZATION-001 | `planned` | POST-1.0 | progress.md mentions only (1) | Deferred in the roadmap. |
| UI-SYSTEM-WAVE2-001 | `implemented` | PRE-1.0 certify | progress.md mentions only (2) | No heading in `progress.md`; two mentions only. |
| ACTIVITY-CONCEPT-001 | `implemented` | historical record | progress.md mentions only (1) | Audit and prototype record; SCHEDULE-UX-001 (verified) built on it. Close without certification. |
| SCHEDULE-UX-001 | `verified` | 1.0 baseline | progress.md:555 | Depends on unverified: ACTIVITY-CONCEPT-001. |
| UI-POLISH-001 | `implemented` | PRE-1.0 certify | progress.md:7352, 7376 · `ui-polish-001-review.md` | "independently reviewed does not mean canonically verified, delivered or merged". |
| TEST-DATA-001 | `in_progress` | tooling (not a release deliverable) | progress.md:7393, 7407, 7424 · `test-data-001-design.md` · af2372c#139 | Stays `in_progress`: criterion 5 names a STRESS profile that is not generated (`test-data-001-design.md:204`). |
| BETA-FOUNDATION-001 | `implemented` | historical record | progress.md:441, 470 · `beta-foundation-001.md`; `beta-foundation-001-qa-corrections.md` | Beta acceptance contract and audit. Its gates are absorbed by `scope-v1.md`; retained as history. |
| BETA-IMAGE-001 | `in_progress` | PRE-1.0 release work | progress.md:7439, 7492, 7501 · `beta-image-001-qa-corrections.md`; `beta-image-001.md` | Images published through beta.5; criteria written for beta.1. Feeds gate G-DIST. |
| beta-postgres-repro-001 | `in_progress` | PRE-1.0 release work | progress.md:412 | Hosted reproduction pending at the feature record. Feeds G-DIST. |
| BETA-SECURITY-001 | `in_progress` | PRE-1.0 release work | progress.md:7508, 7533, 7579 · `beta-security-001-lookup-correction.md`; `beta-security-001.md` | PostgreSQL scan findings and approvals recorded as open at the feature record. Feeds G-SEC. |
| BETA-RUNTIME-001 | `in_progress` | best-effort (not certified) | progress.md:7546, 7555, 7568, 7579 · `beta-runtime-001-qa-handoff.md`; `beta-runtime-001.md` | Controller runtime. Decision 3: advanced/best-effort, not a certified path. Real-host acceptance pending. |
| BETA-DATA-001 | `in_progress` | PRE-1.0 release work | progress.md:8276, 8304 · `beta-data-001.md`; `beta-data-001-templates.md` · 7665df3#159 | Real source inventory, published bundle and Synology acceptance outstanding. Feeds G-SOAK. |
| BETA-ACCEPTANCE-001 | `planned` | PRE-1.0 release work | no progress.md record | Becomes the RC soak (decision 8: 14 days, extendable). |
| WORKFLOW-RETIRE-AUTH-001 | `implemented` | tooling (not a release deliverable) | progress.md:229 | Delivered in #167; QA findings resolved; no canonical receipt recorded. |
| TEST-DATA-002 | `implemented` | tooling (not a release deliverable) | progress.md:7461, 7477 · `test-data-002-design.md` · 1e44c3f#141 | "Delta QA pending" at the feature record; Golden DEV runs on this profile. |
| UI-DESIGN-001 | `verified` | 1.0 baseline | progress.md:7587, 7594 · d94f275#145 | Depends on unverified: UI-POLISH-001, RELEASE-VISUAL-AUDIT-001. |
| UI-REDESIGN-EXPLORATION-001 | `in_progress` → **`implemented`** | PRE-1.0 certify | progress.md:7600, 7608, 7616, 7634 | CORRECTED from `in_progress`: the Workbench shell is on main since `fec0398` (#147, 159 files; adds `frontend/src/shell/WorkbenchShell.tsx`). The description still says experimental. "Canonical FULL not run" at the last record, so not `verified`. |
| VERIFICATION-FAST-001 | `implemented` | tooling (not a release deliverable) | progress.md:7863 · `verification-fast-001-handoff.md` | "Independent infrastructure QA is pending". |
| BETA-DISTRIBUTION-001 | `in_progress` | best-effort (not certified) | progress.md:7891, 7916, 7938, 7959 · `beta-distribution-001.md`; `beta-distribution-001-evidence.json` | Controller bundle distribution. Decision 3: best-effort. Independent QA corrections recorded; publication of beta.6 pending. |
| INSTALL-GUIDE-001 | `implemented` | best-effort (not certified) | progress.md mentions only (1) | Controller guide (`installation.md`); no heading in `progress.md`. |
| SETUP-SAFETY-001 | `implemented` | tooling (not a release deliverable) | progress.md mentions only (1) | No heading in `progress.md`; one mention. |
| MULTIBRANCH-UAT-001 | `implemented` | tooling (not a release deliverable) | progress.md:8199, 8223 · `multibranch-uat-001-handoff.md` · 6f17913#162 | Promotion candidate: FULL passed in 933 s, smoke and delta QA passed (progress 8199-8222). "Unresolved: operator UAT". |
| DEV-GOLDEN-001 | `implemented` | tooling (not a release deliverable) | progress.md:8615 | Delivered in #172; receipt-only evidence. Golden DEV contract is preserved by `scope-v1.md`. |
| DEV-REFERENCES-001 | `implemented` | tooling (not a release deliverable) | progress.md:8637 | Delivered in #173; receipt-only evidence. |
| GOLDEN-REFERENCE-001 | `planned` | POST-1.0 | progress.md mentions only (1) | Planned tooling; not required for 1.0. |
| PORTABLE-COMPOSE-001 | `implemented` | PRE-1.0 certify | progress.md:8240, 8265 | The official 1.0 installation (decision 3). beta.6 publication and a real HTTPS host remain pending; certified by G-INSTALL, G-UPGRADE, G-RESTORE. |
| MEASUREMENT-001 | `implemented` | PRE-1.0 certify | progress.md:266, 8343, 8393, 8403 · 5fbcfd5#163 | Delivered in #163; "stays `implemented` until the operator approves the domain decisions". |
| PHENOLOGY-001 | `implemented` | PRE-1.0 certify | progress.md:143 · `phenology-001-handoff.md` | Delivered in #167; canonical FULL deferred to the consolidated tree. |
| VERIFICATION-EVIDENCE-001 | `implemented` | tooling (not a release deliverable) | progress.md:8515 · `verification-evidence-001-handoff.md` | Delivered in #167; two policy decisions recorded as pending. |
| FABLE-FIX-CUTTINGS | `in_progress` → **`implemented`** | PRE-1.0 certify | progress.md:8709 | CORRECTED from `in_progress`: delivered on main in `947d77f` (#177, cherry-pick of `e325040`); batch browser QA recorded (progress 8765-8801). Not `verified`: persisted before/after screenshots (criterion 5) are outstanding. |
| BOTANICAL-MATCH-1A | `implemented` | internal foundation | progress.md:8 | Read-only foundation with no route or UI; later slices are post-1.0. Nothing user-facing to certify. |
| UX-DATE-001 | `implemented` | PRE-1.0 certify | progress.md:8674 | Delivered in #177; decision D1 unresolved (see `scope-v1.md`). |
| UX-TODAY-001 | `implemented` | PRE-1.0 certify | progress.md:8740 | Delivered in #177; log status IMPLEMENTED_UNVERIFIED. |
