# Implementation plan

**Status: PROPOSED / AWAITING DESIGN APPROVAL.** No phase is authorized by this document. Each phase starts only after the operator approves it and any decisions it depends on ([decisions.md](decisions.md)).

**Implementer:** Claude Code. **Reviewer:** an independent read-only session on a different model, in its own detached checkout. **Codex is not assigned implementation work.** Each phase is one backlog increment on its own `feat/ui-design-001-<phase>` worktree (`make feature-worktree`, `feature-claim AGENT_ID=claude-ui-design-001`) and follows PLAN → IMPLEMENT → FOCUSED TESTS → REVIEW → INDEPENDENT QA → FREEZE → CANONICAL VERIFY. Shared UI infrastructure escalates to FULL. No phase touches the backend, API, schema, migrations or fixtures.

Phases are ordered by regression risk, lowest first. Each one is independently revertible.

## Phase 0: Evidence baseline (no code)

- Start an isolated synthetic Review (fixture v4 plus Extended v5) under its own project name. Sign in with the review credential the operator enters.
- Capture Plants, Seeds, Sowings, Harvests and Suppliers directory and Details at 1440/1024/390 in Botanical Light and Botanical Dark, plus Mineral Dark for continuity with the Wave 3 evidence. Include a **loaded** desktop Plants directory (F-17).
- Re-measure the three UI-FLICKER-001 P3 observations with a 400 ms delayed API.
- **Exit:** a capture manifest committed under `docs/review/ui-design-001/evidence/`, so later phases compare like with like.

## Phase 1: Token and cascade hygiene (CSS only)

- Files: `styles/tokens.css` (add `focus-ring-*`, `radius-round`, slot sizes), `styles.css` (delete legacy `button/input:focus-visible` at `:427–431` and the dead `.record-type-badge`, `.ui-status-indicator`, `.seed-overview-facts`), `styles/normalization.css:795` (2px → token), `docs/ui-contract.md` color table (F-16).
- Tests: extend `appearance/styles.test.ts` to assert the focus tokens exist in every theme block and that no `button:focus-visible` outline-offset override remains. Run the full frontend suite, typecheck, lint and build.
- Visual check: Tab through Plants directory, Details and Edit in two themes; compare against phase 0.
- **Exit:** F-08 closed and F-04 dead CSS removed.

## Phase 2: Confirmation contract

- Files: `components/TaskDialog.tsx` (optional `initialFocus`), new `components/ConfirmDialog.tsx`, then **one owner per commit**: Plants → Sowings → Seed lots → Harvest/Inventory/Conversion → Locations → Suppliers → Orders → Identity → Geography/Provenance site → Cover → App.
- Keep every guard's meaning. Pending saves block dismissal. Browser Back first closes the edit entry. Dirty state is detected by the existing owners. Only the prompt changes from synchronous `confirm()` to an awaited dialog.
- Tests: replace each `window.confirm` spy with dialog interaction (keep, discard, Escape keeps); assert Cancel/Keep editing has initial focus; assert pending disables confirm.
- **Exit:** `grep window.confirm` returns 0 outside tests (F-02), and the F01 contract is explicit.

## Phase 3: Details action grammar (needs D3, D4, D5)

- Files: `CollectionUI.tsx` (`headingLevel` default 2), Plant/Sowing `WorkspaceIntro` context row, the callers of `DetailHeader` (labels and prominence), `DetailSummary` callers (drop repeats).
- Rules: one primary; Edit is secondary with the icon; More for the rest; sentence-case labels; Record harvest is primary for both kinds (F-05).
- Tests: update owning screen suites for the heading role and level, the title focus target (UI-POLISH-001 refs), button names (casing) and the mobile return path via breadcrumb. Re-run the App transition and loading suites.
- **Exit:** F-03, F-05, F-09 and F-12 (Details scope) closed; the UI-FLICKER-001 C5 offset re-measured.

## Phase 4: Compact directory tools (needs D6; tablet rail needs D1)

- Files: `DirectoryTools.tsx`, `DirectoryViewSwitcher` / `directoryPresentation.ts` (segmented markup only), `directory-system.css`, `PageHeader` compact slot.
- Preserve the URL `view` precedence, the browser preference key, `aria-pressed`, the filter drawer focus return and the stable chip lane.
- Tests: `DirectoryTools.test.tsx`, `DirectoryPage.test.tsx`, `DirectoryResults.test.tsx` and the eight owning directory suites.
- **Exit:** at 390×844 the first Plants record starts in the top half of the viewport (F-01).

## Phase 5: Type, radius and glyph migration (F-06, F-07, F-10, F-13, F-14; gallery placeholder needs D2)

- `styles.css` selector groups migrated by area, one commit each: notices/forms, directory legacy, details legacy, Sourcing, Activity. Use the mapping tables in [proposed-changes.md](proposed-changes.md). Leave map, tree and calendar internals alone.
- Replace `←` with `<Icon name="back">`. `OriginInspector` adopts `LifecycleStatus`. Sowing germination metrics adopt `DetailSummary` presentation.
- **Exit:** raw `font-size` in `styles.css` ≤ 20, all of them documented exceptions (print labels in mm, map attribution).

## Phase 6: Breakpoint consolidation (F-11, highest cascade risk)

- One stylesheet per commit, with screenshots at 1440/1024/768/600/390 before and after. Remove the `48.01`/`48.001` duplication.
- **Exit:** only the 48/64/75rem queries remain, except a documented 30rem short-height query and print.

## Phase 7: Release screenshots and acceptance

- Run the acceptance checklist. Capture the public set from a fresh synthetic Review on the delivered main.

## Review protocol

- The reviewer receives the phase diff, the [design artifact](https://claude.ai/artifact/T5A2PpURaCtwGxYTU6F8eN) link and the relevant findings IDs. The reviewer checks each "Exit" claim against source and screenshots, and treats the implementer's report as a claim, not evidence.
- The reviewer must reject: a color or token value change; any API, URL or saved-view change; removed tests; a guard that no longer blocks a pending dismissal; focus not returning to the trigger.
