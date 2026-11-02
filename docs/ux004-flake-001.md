# UX004-FLAKE-001 investigation

Date: 2026-11-02. Base: freshly fetched `origin/main`
`e5e6b4f4060e2325f356921ea300a7541b7e72d6` (PR #134).
Worktree: `/home/alessandro/.codex/worktrees/2185/florabase`.
Branch: `fix/ux004-flaky-test`, attached with `make feature-init`.

## Finding and correction

The current-main flake is reproducible in **Identity creation menu Add plant reaches the normal
form with identity prefilled**. The unchanged suite passed 19/20 fresh-process repetitions;
one failed at the Botanical identity combobox query with 12 other cases passing. The separate
initial baseline run passed all 13 cases.

`vi.dynamicImportSettled()` waits for Vitest imports, but does not flush React's lazy workspace
commit and effects. Ten temporary instrumented repetitions all observed the correct Plant creation
hash but **Loading workspace…** immediately after that wait. Only auth, health and the identity
directory had been requested; Plant reference loading had not started. Those ten repetitions
eventually passed, showing why the original query could succeed by timing alone.

A temporary controlled probe held `loadWorkspaceChunk` behind an explicitly released promise,
using the real module loader and Plant component. It first asserted the visible workspace loading
state and absent combobox. After release, an immediate combobox/value assertion following import
settlement failed 5/5 times without `act` and passed 5/5 times with async `act`. This probe deliberately
used a synchronous post-settlement query to expose the commit boundary; its 5/5 failures are distinct
from the unchanged test's 1/20 intermittent failures. No sleeps, fake timers or changed timeouts were
used. Temporary probes and console logging were removed.

The correction wraps the existing import-settlement wait in async `act`, following the existing
lazy-route testing pattern in `App.test.tsx`. The existing regression still exercises the real
creation link and Plant form, exact identity prefill and URL, absence of Plant-group mode, and
GET-only Plant requests. All assertions and timeouts are retained. No additional test fixture or
production code change is needed for this scheduling correction.

The two current `waitFor` callbacks contain throwing focus assertions. The detail-to-directory
animation-frame focus restoration is already awaited on this base. User-event operations are awaited,
cleanup restores mocks after every case, the browser bootstrap recreates its complete media-query
stub, and no fake timers are used in this suite. These were not the cause of the reproduced failure.
The controlled probe reaches the correct prefilled form once React work is flushed; no product defect
was demonstrated. The historical TX-001 failure's exact assertion was not supplied, so this evidence
does not establish that it was the same failure.

## Focused verification

All frontend execution uses only this worktree's Quality project
`florabase-quality-c102d54e473d`, Node 24.19.0, pnpm 11.19.0 and Vitest 4.1.11.
Each repetition starts a fresh Vitest process with all 13 UX004 cases:

```sh
python3 scripts/workflow_environment.py quality compose -- run --rm --no-deps frontend \
  node --input-type=module -e '
    import {spawnSync} from "node:child_process";
    let failed = 0;
    for (let run = 1; run <= 30; run++) {
      const result = spawnSync("pnpm", ["test", "src/UX004.test.tsx", "--no-color"],
        {encoding: "utf8"});
      console.log({run, status: result.status});
      if (result.status !== 0) {
        failed++;
        console.log(result.stdout + result.stderr);
      }
    }
    console.log({runs: 30, failed});
    process.exitCode = failed ? 1 : 0;
  '
```

The baseline used the same loop with a bound of 20. Raw local investigation logs are retained at
`/tmp/ux004-baseline.log`, `/tmp/ux004-diagnostic.log`, `/tmp/ux004-controlled.log` and
`/tmp/ux004-after.log`; the temporary controlled probe source is
`/tmp/UX004.controlled-probe.test.tsx`.

Corrected repeated result: **30/30 suite runs passed, 390/390 cases**. Related regression:
**259/259 cases in nine files passed** with the following frontend command:

```sh
pnpm test src/UX004.test.tsx src/App.test.tsx src/UX001.test.tsx \
  src/plants/PlantScreen.test.tsx src/seed-lots/ReferencePicker.test.tsx \
  src/botanical-identities/IdentitySourceAction.test.tsx \
  src/components/CollectionUI.test.tsx src/components/DirectoryPage.test.tsx \
  src/components/ThemeControl.test.tsx --no-color
```

`pnpm typecheck`, `pnpm lint` (zero warnings), `pnpm format:check` and `pnpm build` all passed
through the same Quality frontend wrapper. The production frontend build transformed 274 modules.
The related suites emitted jsdom's existing unsupported `window.confirm()` diagnostic; all tests
passed, and no native-dialog/browser acceptance is claimed. Full command/output evidence is retained
locally at `/tmp/ux004-verification.log`.

Both changed Markdown files passed `pnpm exec prettier --check /documentation/ux004-flake-001.md
/documentation/progress.md`, with this worktree's documentation mounted read-only at `/documentation`
in the same Quality frontend wrapper. An initial attempt using the unavailable `../docs` mount path
was corrected before that successful check. Local output is at `/tmp/ux004-doc-format.log`.
`git diff --check` passed; the final staged diff is reviewed before the local commit.

Canonical verification and protected delivery await explicit coordination; no verification receipt
or feature-status promotion is claimed. Repetition is bounded evidence, not proof against every
possible timing or suite-order interaction. The historical TX-001 failure may have a different cause.
Feature Review, UAT, DEV and Claude's workflow worktree were not used or modified. No workflow,
infrastructure, dependency, API, schema or production component change is included.
