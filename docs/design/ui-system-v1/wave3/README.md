# Wave 3 — Batch 1 progress handoff

29 October 2026. Branch `feat/ui-system-v1-wave3`, isolated Codex checkout `548f`,
base `5b2e2a1` (merged Wave 1 #129 plus enrichment #130). Wave 2 remains unmerged;
its worktree, environments and implementation are not changed. This is a partial
implementation handoff, not Wave 3 UAT acceptance or delivery readiness.

## Implemented scope

- Harvest deletion and Remove inventory tracking place Cancel first, matching
  TaskDialog's existing initial-focus behavior. Destructive actions use danger styling.
  Pending dismissal locks, retryable errors and stable More-trigger focus return remain.
- Location creation captures its initial payload, including prefilled parent and scopes.
  Cancel and Escape protect changed drafts; pristine forms close immediately.
- Inventory/disposition and seed conversion retain initial controlled drafts and use
  one page-owned dismissal guard for their Cancel/Escape paths. Conversion backdrop
  dismissal also uses that guard through the existing EditWorkspace callback.
- No shared component contract, API, schema, migration, domain mutation or new bulk operation.
  UI-SYSTEM-001 remains `in_progress`.

## Compliance update

| Surface | Batch 1 status | Remaining scope |
| --- | --- | --- |
| SeedLots | Existing approved implementation retained | Targeted later integration regressions |
| Sowings | Unchanged | Batch 2 List/Gallery, explicit actions, overlay and typography |
| Plants / PlantGroups | Existing approved implementation retained | Targeted later integration regressions |
| Harvests | Safe destructive confirmation implemented | Batch 3 directory adaptation |
| Stored material | Safe tracking confirmation and changed-draft guards implemented | Batch 3 exact inventory destination and integration |
| Locations | Creation dirty-dismiss protection implemented | Batch 4 direct-detail loading/error/missing recovery |

## Checks and limits

The initial focused baseline passed 44 tests across HarvestScreen, StoredMaterial
and Conversion. The first changed-tree run passed 49 domain tests and 19 selected
Location tests (99 unrelated App tests excluded by name filter), and strict TypeScript.
Initial targeted ESLint identified one unnecessary async test callback, corrected
without changing behavior assertions. Final targeted results are recorded in progress.md.
Tests cover Enter on initial Cancel, danger styling, pending/error retention, focus
return, unchanged-form cancellation, rejected dirty dismissal and accepted discard.

One isolated reusable Quality project is used: `florabase-quality-8b4474e4d89f`.
No live Review was provisioned and no existing Review/DEV/UAT environment was modified.
There is no new Review URL or screenshot gallery for this partial handoff.
No canonical gate, production build, backend/integration checks or browser visual
acceptance is claimed. Real browser native confirmation, backdrop interaction,
all six themes, 1440/1024/390/320 widths, actual zoom, physical devices and assistive
technology remain to be exercised in the later owned Review environment.

## UAT checklist for continuation

- Open both destructive dialogs by keyboard; Cancel is focused, Enter cancels with
  no mutation, Escape returns to More. Pending Escape/Cancel cannot dismiss; server
  failure remains actionable without losing the selected record.
- Close pristine Location, inventory, disposition and conversion tasks immediately.
- Change Location name, parent or scope; reject discard and retain all input, then
  accept discard. Include prefilled Create child and reopening the create task.
- Change inventory state/quantity/storage or disposition/date/notes; repeat rejection
  and accepted discard. Preserve precision, units, collected amounts and remainder.
- Change conversion target/quantity/remainder; test Cancel, Escape and backdrop.
  Declining discard must retain the complete draft and focus containment.
- Test save pending/failure/success without altering existing domain eligibility.

## Continuation boundary

After Wave 2 protected delivery, fetch main and inspect its final shared contracts
before reconciling this branch. Implement Batches 2–4 only then. Page-owned files
currently have no overlap with Wave 2's committed product changes; progress.md is
an expected append-only reconciliation point. Do not duplicate TaskDialog,
EditWorkspace or directory abstractions. Do not push, create a PR, merge or finish
before operator acceptance. No Wave 3 completion marker is appropriate yet.

## Final focused evidence

- Domain suites: HarvestScreen **16**, StoredMaterial **24**, Conversion **10**;
  selected Location App cases **19**. **69 distinct tests passed** across scoped
  runs. The final StoredMaterial rerun passed 24/24 after its test-only lint fix.
- `pnpm typecheck`: passed on the final frontend tree.
- Affected-file `pnpm exec eslint ... --max-warnings 0`: passed.
- All nine changed TSX files formatted by Prettier; final seven plus Harvest test
  checked, StoredMaterial test formatter reported unchanged.
- `python3 scripts/check-features.py`: 120 valid. `git diff --check`: passed.
- Commands ran through `python3 scripts/workflow_environment.py quality compose --
  run --rm --no-deps frontend ...`; test commands used the three named domain files
  and `pnpm test src/App.test.tsx -t '[Ll]ocation'`.
- Two test-callback lint errors were corrected. One attempted Compose invocation
  with unsupported `--no-build` failed before tests; the supported invocation passed.
  The selected App run emitted JSDOM's native-confirm-not-implemented warning in
  an existing case; real native-confirm acceptance remains explicitly unverified.

Product files changed: `HarvestScreen.tsx`, `StoredMaterial.tsx`,
`InventoryDialog.tsx`, `ConversionDialog.tsx`, `LocationScreen.tsx`.
Regression files changed: `HarvestScreen.test.tsx`, `StoredMaterial.test.tsx`,
`Conversion.test.tsx`, `App.test.tsx`. Shared components changed: **none**.
Documentation changes: this handoff and the progress milestone. The operator accepted
Batch 1 for a standalone local implementation checkpoint. The recorded 69-test
evidence is preserved; no verified status, canonical receipt or final Wave 3 UAT
acceptance is claimed. Wave 2 remains unmerged at checkpoint review (branch tip
`c910b2c`, fetched main `5b2e2a1`). Reconcile its delivered main and inspect the final
shared contracts before starting Batches 2–4.
