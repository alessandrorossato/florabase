# UI-POLISH-001 — focused Wave 3 follow-up

Committed implementation and QA correction candidate, 2 November 2026. Owner: `codex-ui-polish-001`.
Worktree: `/home/alessandro/Desktop/github/florabase-worktrees/ui-polish-001`.
Branch: `feat/ui-polish-001`. Starting HEAD and cached `origin/main`:
`9ac7b6cf8ebc7771b22016b2e67fa254b21a9f23` (clean, zero commits behind).
`make feature-context` validated identity and `make feature-claim AGENT_ID=codex-ui-polish-001`
confirmed the existing operator-prepared claim; no takeover was used. No fetch or remote freshness
claim is made. The separate Codex-provided checkout remains detached and unchanged.

## Audit before implementation

The [Wave 3 closure matrix](design/ui-system-v1/consolidation/details-cover/README.md#wave-3-closure-disposition)
is the historical source. Its later closure disposition supersedes its earlier open-UAT text.
The P2 findings and chosen refinements were checked against current source before implementation; this is a code and
automated-interaction audit, not a new visual acceptance pass.

| Finding | Evidence at starting HEAD | Severity | Proposed fix | Tests | Design decision needed? |
| --- | --- | --- | --- | --- | --- |
| QA-1: unknown/malformed Seed Details is blank | SeedLotScreen clears absent selections after list load; its open detail branch renders null without a selected lot | P2 | Existing Details shell, explicit unavailable message and Return to Seeds | Missing/malformed IDs; valid Details; existing inventory failure and authentication cases | No |
| QA-2: Plant/Group Forward retains directory under Details URL | PlantScreen route effect returns when routedKey equals selectedKey, leaving mobileDetail false after Back | P2 | Reopen retained Details without clearing save feedback or reloading the selected record | Real jsdom Back/Forward for each kind; creation/extraction regressions | No |
| QA-3: Details/Back loses record focus | Directory records unmount; old trigger refs become disconnected; Seeds/Harvest have no entry focus effect and Sourcing focuses only after edits | P2 | Reuse title refs and stable existing row identifiers for bounded entry/return focus | Six owning screen suites; delayed readiness, remount, absent row, intentional focus and editor ownership | No |
| QA-4: Plant/Sowing focuses content section | Plant heading ref is on DetailSummary; Sowing ref is on Source h4, absent on other tabs | P3 | Move existing heading refs to DetailHeader | Title-focus assertions for Plant, Group and Sowing | No |
| C5: Plant/Sowing context actions precede the title | WorkspaceIntro contextActions still render a separate workspace-context-actions region | P3 | Present options below, preserve layout | Existing operation/creation tests | Yes |
| Repeated header/summary values | Closure explicitly defers content selection; Plant lifecycle and Sowing quantity are examples | P3 | Present content options, retain all facts | Existing domain assertions | Yes; separate content concern |
| Mobile title gap and long breadcrumb wrap | Closure records one idle Plant/Group render and name-dependent wrap; existing loading/layout styles remain | P3 | Retain pending fresh delayed-network visual evidence | Existing loading/transition cases, no new geometry claim | Visual evidence needed |
| Unused seed-overview-facts CSS | Closure lists harmless unused rules; no current styling change is needed for this increment | P3 | Leave for separate cleanup | Not applicable | No |
| Accepted domain exceptions | Identity navigation, Place back link, distinct tabs/sections, identity footprint, provenance StatStrip and Stored material without Details remain documented contracts | Accepted | Preserve; Stored Details requires product approval | Existing owning regressions | Yes for new Stored Details |
| QA-5–QA-10 (historical, not revalidated here) | Closure also defers Edit/Cancel focus, initial editor focus, hierarchy expansion, Location h2, absent tab-panel targets and retryable unknown-ID presentation | P3 | Keep visible as separate follow-up scope | Existing tests are not proof these findings are resolved | Some require separate interaction/content decisions |
| Real zoom, assistive technology, devices, other browsers | Historical report explicitly did not verify these | Gap | Operator/manual follow-up | Not exercised here | No |
| Completed C1–C4-related work | Shared DetailPage/DetailLoading, flat Details shell, title scale, mobile gutters, directory header declarations and DetailSummary are already present | Closed work | Preserve approved architecture | Existing App/transition/loading and owning screen suites | No |

The checked-in reports explicitly label C1/C3 and mention C5; C2/C4 are not assigned invented
definitions. The operator confirmed that C6 was an incorrect brief reference and removed it from
scope. Repeated metrics are a separate documented content concern.

## Bounded implementation

- Seeds show a truthful unavailable-record state after a successful inventory load, including malformed
  and unknown IDs. Existing request-failure/retry and session-expiry handling remain authoritative.
- Browser Forward reopens retained Plant or Group Details. The same-selection path changes only
  visibility, preserving authoritative data and existing creation/extraction success messages.
- A small focus hook shares only presentation focus timing. Each owner still supplies its route/visible
  key, readiness, editor pause state and existing refs. Seeds, Plants/Groups, Sowings, Suppliers, Orders
  and Harvests adopt it. It focuses the loaded record title only when focus is on body, reconnects the
  corresponding remounted row on browser Back, and falls back to the connected directory if that row
  is absent, then the existing Search input if the empty directory has no list. It preserves intentional focus during slow loads and existing editor/workflow ownership.
  Plant and Sowing refs now target the title on all detail tabs.
- The existing `previewId`/`data-preview-id` attribute is reused as a stable row identifier; no Preview
  interface is reintroduced. Harvest uses the same attribute on its existing li. No new component,
  CSS, token, route, API, dependency, backend, migration or fixture infrastructure is introduced.

QA-1 and QA-2 have scoped corrections. QA-3 is addressed for the six listed owners only; Botanical
Identity, Locations and Geography were not migrated to this hook, so application-wide QA-3 closure
is not claimed. Explicit domain Back buttons retain their pre-existing connected-list fallback;
this increment tests row restoration for browser history. Other deferred P3s remain open.

## Operator decisions retained

**C5 action placement:** (A) retain the current separate context row and its stable vertical offset;
(B) place the existing context commands in DetailHeader's existing actions slot. Option B requires an
approved action order, mobile wrapping and a decision on whether context creation and record mutation
commands share a group. Either option must preserve Extract/Harvest/create eligibility and source links.
No speculative move or new action menu is included. Exact evidence: the closure matrix at
`docs/design/ui-system-v1/consolidation/details-cover/README.md:200`, its C5 explanation at line 169,
`frontend/src/components/CollectionUI.tsx:60`, `frontend/src/plants/PlantScreen.tsx:2485` and
`frontend/src/sowings/SowingScreen.tsx:1582`. No later approved placement decision was found.

**Repeated metrics (separate content concern):** (A) retain repetition for scanning; (B) retain lifecycle/status
in the header and remove only the exact repeated summary item; (C) keep all at-a-glance values in the
summary and reduce header metadata. Choose per-family facts explicitly, preserving unknown/zero,
quantity precision and reference-versus-record semantics. No value has been removed here. Exact
evidence: closure matrix line 205; Plant status/header and summary in
`frontend/src/plants/PlantScreen.tsx:405` and `frontend/src/plants/PlantScreen.tsx:520`.
Stored material's accepted exception is closure matrix line 204 and remains unchanged.

## Verification and review

Baseline: **120/120** existing Seed/Plant tests passed. New cases reproduced the missing-Seed,
Plant Forward and Seed focus defects before correction. The committed implementation checkpoint passed
**396/396 tests in 13 suites**, strict TypeScript, whole-frontend ESLint, whole-frontend Prettier
check and frontend production build. Feature graph: **125 valid features**. Whitespace checks pass.
The final run completed successfully in the worktree's Quality frontend container with:

```sh
pnpm test src/seed-lots/SeedLotScreen.test.tsx src/plants/PlantScreen.test.tsx \
  src/sowings/SowingScreen.test.tsx src/suppliers/SupplierScreen.test.tsx \
  src/orders/OrderScreen.test.tsx src/harvests/HarvestScreen.test.tsx \
  src/components/useRecordDetailFocus.test.tsx src/components/CollectionUI.test.tsx \
  src/components/DirectoryPage.test.tsx src/components/recordNavigation.test.ts \
  src/App.test.tsx src/App.transition.test.tsx src/App.lazy.test.tsx
pnpm typecheck
pnpm lint
pnpm format:check
pnpm build
```

Host checks: `python3 scripts/check-features.py`, `git diff --check` and final staged whitespace
review. Final full console evidence is retained locally in `/tmp/ui-polish-001-final-focused.log`.
The existing App suite emits jsdom's unimplemented `window.confirm` diagnostic; the suite and final
command pass. No test or validation rule was weakened.

A separate read-only agent reviewed the six integrations, missing-record state ordering, history,
success-feedback preservation, title refs, editor/workflow ownership and timing. It identified the
empty-directory fallback gap; the implementation now uses each owner's existing Search input and
has a zero-row regression. Re-review found **no unresolved objective correctness defects**. That
reviewer ran whitespace and feature-graph checks, but did not independently run Docker or browser
checks. At that checkpoint, Supplier/Order/Harvest focus regressions rerendered route props; Seed/Plant/Group/Sowing tests
use real jsdom history. These are automated DOM/interaction results, not real-browser visual proof.

Live responsive/theme/zoom/screen-reader/device acceptance was not run. No API contract changed;
backend tests, database integration/migration checks and API regeneration were not selected for
this frontend-only focused increment. Canonical FULL, operator graphical acceptance and delivery
remain separate and were not run. Shared-component changes require eventual policy-selected FULL,
which the operator explicitly withheld. No verified status or usable canonical receipt is claimed.
The implementation was committed as `22ab055cfdc5b267bf7ac0304edc33ff3d73db40`, tree
`f994e66f04772ee630c70dc8320577c9715ffc79`, following explicit operator authorization.
It is implemented and committed, independently reviewed, but not canonically verified or delivered
and merged. Canonical FULL and delivery remain separately authorized phases.
Only worktree-owned Quality resources are used (`florabase-quality-13b42dece81a`); no persistent DEV,
shared Feature Review, UAT, TEST-DATA-001 worktree, fixture, resource or branch is operated on.


## Independent Claude QA and final corrections — 2 November 2026

The operator supplied Claude's **CONDITIONAL PASS** on implementation commit `22ab055` and tree
`f994e66f04772ee630c70dc8320577c9715ffc79`: 396/396 documented tests, 10/10 adversarial probes,
and 6/6 mutation checks detected regressions, with no confirmed functional delivery blocker.
Those independent results are attributed to Claude's review, not re-claimed as local executions.

- B1: corrected the historical staged/uncommitted wording here and in progress. The implementation
  commit and independent review are distinct from canonical verification, delivery and merge.
- N3: existing Plant creation, Group creation and extraction tests now traverse Forward and assert
  retained success feedback. Extraction explicitly seeds a result history entry because its task
  replaces history; assertions cover the retained same-record route rather than a refetched result.
- N4: unavailable Seed routes assert title focus; Supplier owner-level App tests exercise real
  jsdom Back/Forward and an empty-directory Search fallback, including deliberate focus ownership
  when returning from another workspace. No production code changed.
- N1, N2, N5 and N6 remain deferred and nonblocking per independent QA. Their detailed external
  descriptions were not supplied in this correction request; no new requirements are inferred.
  C5, repeated summary metrics, broader QA-3/P3 and live visual acceptance remain outside this fix.

Final correction evidence: **7/7 targeted cases** passed (242 unrelated cases skipped by the focused
name selector), then **398/398 tests in the same 13 owning/shared/App suites listed above** passed
without a name selector. `pnpm typecheck`, `pnpm lint`, `pnpm format:check` and `pnpm build` passed.
Host `python3 scripts/check-features.py` (125 features) and whitespace checks passed. Full local
console evidence: `/tmp/ui-polish-corrections-new3.log` and `/tmp/ui-polish-final-corrections.log`.
The correction commit contains only three test files and these two documentation files. No canonical FULL, push, PR, merge,
feature-finish, TEST-DATA-001 change or shared-environment operation is part of this correction.
