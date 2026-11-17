# RC UX Defect Remediation (F-01 through F-05)

Date: 17 November 2026
Branch: `fix/rc-gux-functional-defects`
Baseline: `ed5747c20d181c93b5cf78dab1656a24c576ba9b`

## Environment and dataset

Browser verification ran against a disposable isolated Compose stack owned by this worktree
(`florabase-uat-preview-smoke-08150aea6b0c`) seeded with `uat_fixture` (v4, 66 baseline records)
and authenticated through the UI sign-in form. Headless Chromium (`deviceScaleFactor` 1 and 2)
measured rendered geometry before and after the changes across `1440×844`, `1024×844`, `390×844`,
and 200% zoom (`720×422` CSS px, `dpr: 2`, `mobile: false`). After final checks completed,
`env_ctl.py down` tore down all owned containers, volumes, networks, and images.

## Before and after results

| Defect | Surface / Viewport | Before | After |
| --- | --- | --- | --- |
| **F-01** | Directory scroll at 200% zoom (`720×422`, `dpr: 2`) on Plants, Seeds, Harvests | `.workspace` / `.harvest-workspace` clamped to `153px` (`overflow: hidden`); toolbar sliced off (`top: -178..-20` on Plants, `-159..-1` on Seeds, `-61..37` on Harvests) | Clamps released to document flow: `wsStyle.h` expands to `787px` (Plants), `1342px` (Seeds), `494px` (Harvests); `toolsRect.top` is `204` / `204` / `272`, `pagRect.top` is `378` / `378` / `370`, `listRect.top` is `503` / `503` / `473` |
| **F-02** | `ReferencePicker` inside `TaskDialog` (`Edit Plant`) | First `Escape` closed both `.reference-menu` and the enclosing `dialog[open].edit-workspace-modal` (`dialogOpenAfterFirstEsc: false`) | Registered `.reference-menu` with `registerControlLayer` (priority 3) and `suppressFocusOpen` refocus guard: first `Escape` closes only `.reference-menu` and focuses `combobox`; second `Escape` closes `TaskDialog` |
| **F-03** | Mobile directories at `390×844` (Seeds, Sowings, Plants List, Plants Gallery) | `.directory-pagination` trapped overlapping `.wb-bottombar` (`pagBox.bottom` 796–802 vs `barBox.top: 780`); Plants Gallery capped `.ui-directory-records` at `422px` (`50dvh`), clipping the first card (`listClippedCard: true`) | Natural mobile document flow removes `50dvh` list clipping (`listClippedCard: false`, gallery `listRect.h: 1519`) and preserves `6rem + env(safe-area-inset-bottom)` bottom clearance (`pagBoxAtBottom`: `635..748` <= `barBox.top: 780`) |
| **F-04** | Mobile filter chips at `390×844` (Seeds, Sowings, Plants List/Gallery) | `.directory-filter-summary` squeezed into `w: 102` beside toolbar icons while the `Lifecycle: Active` button required `w: 142`, clipping its `×` button off-edge (`chipClipped: true`) | `.directory-filter-summary` wraps onto a full-width row (`w: 358`, `chipBtn` `16..158`, `chipClipped: false`) |
| **F-05** | Botanical Identity detail tabs at `390×844` | `.identity-detail-tabs` (`left: 0`, `w: 390`) and `.detail-tabs` (`left: -16`, `right: 374`) extended past `.detail-tab-panel` (`left: 16`, `right: 374`, `w: 358`) | Added `margin-inline: 0` on `.identity-detail-tabs` and `margin-inline: 0; padding-inline: 0` on `.detail-tabs`: `wrapper`, `tabs`, and `panel` all align at `left: 16`, `right: 374`, `w: 358` |

## Cross-viewport and regression checks

- Document horizontal overflow (`scrollWidth > clientWidth`): `false` on every checked route and
  viewport (`1440×844`, `1024×844`, `390×844`, and `720×422` 200% zoom across `Plants`, `Seeds`,
  `Sowings`, `Harvests`, `Identities`, `Today`, and `Journal`).
- Runtime errors during final browser verification: `consoleErrors: []`, `pageErrors: []`,
  `failedRequests: []`.
- Conversation artifact evidence: `brain/ca7d982e-6cc1-45c9-9ac8-8dd65e926882/scratch/remediation/`
  (`before/` and `after/` `report.json` and PNG captures).

## Frontend checks

Run in `frontend/` after the final edit:

- `pnpm run format:check` — passed (Prettier)
- `pnpm run lint` — passed (`eslint . --max-warnings 0`)
- `pnpm run typecheck` — passed (`tsc -b --pretty false`)
- `pnpm test` (`vitest run --configLoader runner`) — 126/126 test files passed (1378/1378 tests),
  including new regression tests in `src/seed-lots/ReferencePicker.test.tsx` (Escape and native
  dialog `cancel` layering inside `TaskDialog`) and `src/appearance/styles.test.ts` (CSS layout
  contracts for F-01, F-03, F-04, F-05, alongside unchanged theme token hashes)

## Scope notes and deferred items

- **F-06** (mobile navigation focus management) remains deferred per operator approval.
- Theme tokens (`frontend/src/styles/tokens.css`), `U04`, `R21`, and `UI-SYSTEM-001` status remain
  untouched.
- Independent QA and canonical verification remain pending integration handoff.
