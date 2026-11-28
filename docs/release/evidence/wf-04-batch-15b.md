# WF-04 Batch 15 integration evidence (candidate `ci/batch-15b`)

Integration branch `ci/batch-15b`, base `origin/main` `c83d81638d643590fd83590b63b2b7374dabeaaa`,
writer `claude-batch-15`. Manifest: [batch-15b.json](batches/batch-15b.json).

The first candidate `ci/batch-15` (reconciliation `070463f`) was abandoned: its integration review
found `tsc -b` failing at `frontend/src/mobile/NativeRemindersSettings.test.tsx` (MOBILE-004 session
fixture missing DEMO-001's required `demo_readonly`). The fix was made at the source (DEMO-001
`ffb4cea7`), and this candidate was prepared fresh from the same base.

## Sources (merge order)

| # | Feature(s) | Branch | Tip | Source evidence | Proposed release class |
| --- | --- | --- | --- | --- | --- |
| 1 | UAT-INSTANCE-002 | `ci/uat-instance-002` | `bd890eeb` | `docs/archive/UAT-INSTANCE-002/uat-instance-002-handoff.md` | best-effort |
| 2 | MOBILE-004 (contains `bd890eeb`) | `feat/mobile-004-notifications` | `707a8331` | `docs/archive/MOBILE-004/evidence.md` | post-1.0 |
| 3 | UI-POLISH-006 | `fix/ui-polish-006-collection` | `a5f43a98` | `docs/archive/UI-POLISH-006/evidence.md` | best-effort |
| 4 | QUICK-ADD-001, UX-ENTRY-002, BULK-002 | `feat/market-phase1` | `7e3937b3` | `docs/release/evidence/market-phase1.md` | best-effort |
| 5 | DEMO-001 (contains `707a8331`) | `feat/demo-001-readonly-tour` | `ffb4cea7` | `docs/archive/DEMO-001/evidence.md` | best-effort |

Each source tip has an independent review by a reviewer other than its writer; all five
sources ran a source gate before integration: UAT-INSTANCE-002, MOBILE-004, UI-POLISH-006 and
DEMO-001 in their Neon worktrees, and QUICK-ADD-001's canonical FULL on the operator workstation
(worktree `feat/market-phase1` at `7e3937b3`, after its evidence file was written).

## Conflict handling

- Pre-integration simulation found non-progress conflicts, resolved at the sources before
  preparation: `docs/mobile.md` (UAT-INSTANCE-002 and MOBILE-004 both rewrote the
  `make mobile-sync` bullet; MOBILE-004 merged `bd890eeb` and keeps UAT-INSTANCE-002's
  `cd mobile && pnpm …` wording plus `@capacitor/local-notifications`), and the tails of
  `docs/features.json` / `docs/release/scope-v1.json` (DEMO-001 moved its entries after
  RUNTIME-IDLE-001 / DEV-REFERENCES-001). DEMO-001 then merged MOBILE-004 `707a8331` and set
  `demo_readonly: false` in `NativeRemindersSettings.test.tsx`, so DEMO-001 now depends on
  MOBILE-004 and UAT-INSTANCE-002 and they must ship together.
- Preparation: only `docs/progress.md` conflicted (UI-POLISH-006, QUICK-ADD-001) and was
  resolved additively by the batch tool. `backend/openapi.json`, `frontend/src/api/schema.d.ts`,
  `frontend/src/App.tsx` and `frontend/src/plants/PlantScreen.tsx` auto-merged; the generated API
  artifacts were re-exported with no drift. `frontend/src/mobile/NativeApp.test.tsx` was merged at
  the source (DEMO-001 `1a561e57`).
- DOCS-005 (`docs/docs-005-structure` `bdd2e180`) is excluded: it moves files the other sources
  edit (`docs/README.md`, `docs/installation.md`, `docs/development-workflow.md`, `docs/mobile.md`).
  Operator decision 27/11: deliver it alone, realigned on the post-batch `main`.

## Shared files and migrations

- No Alembic migration in any source.
- Shared frontend files merged cleanly: `App.tsx` (MOBILE-004 reminders, QUICK-ADD-001 route,
  DEMO-001 lazy demo shell), `PlantScreen.tsx` (UI-POLISH-006 record mask, UX-ENTRY-002 inline
  identity create), `shell/navigation.ts` and `components/navigationIcons.ts` (QUICK-ADD-001).
- `scripts/verification-impact.json` gains the `quick-add` scope (QUICK-ADD-001);
  `scripts/feature_batch.py` gains UAT-INSTANCE-002's post-prepare stale-launch hint
  (`except` clauses kept Python 3.12-parsable for the CI host).

## Pre-review checks on the integrated tree (a3535d9f + reconciliation)

Run in a separate container on the exact merge head `a3535d9f` plus this reconciliation, each exit
code read directly (not through a pipe): OpenAPI `--check` exit 0 and `openapi-typescript`
regeneration with no `schema.d.ts` change; `tsc -b` exit 0 (0 errors); Prettier `format:check` and
`eslint src` on the whole frontend exit 0; Vitest 158 files / 1576 tests passed; backend unit tests
outside `tests/integration`: 1495 passed, 12 failed, all environment-only (missing
`/var/lib/florabase`, root-writable directories) and also failing on `main` in the same container;
`check-features.py`, `check-doc-links.py` (405 documents) and `test-beta-runtime.py` (21 tests) exit 0.

## Follow-ups (not part of this reconciliation)

- In demo mode the "Quick add plant" action still shows on the Today header and in the command
  palette (the POST is rejected with 403 by the demo middleware, so it is cosmetic). Hide it with
  the other create actions in a later batch.
