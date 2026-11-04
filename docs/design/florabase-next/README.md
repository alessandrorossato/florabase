# Florabase Next: experimental frontend (UI-REDESIGN-EXPLORATION-001)

**Status: EXPERIMENTAL. Not approved for adoption or merge.** The operator reviews the running
alternative personally before any canonical FULL verification, delivery or merge.

- Design concept (Claude Design canvas, private): https://claude.ai/artifact/GfbbqcoWQnULGwzagEfWX7
- Branch: `feat/ui-redesign-exploration-001`, base `origin/main` `d94f275` (#145)
- Writer: Claude Code, `AGENT_ID=claude-next`. Independent review: a separate Claude session or
  Luna. Codex does not implement.

## Operator decisions (4 November 2026)

| ID | Decision |
| -- | -------- |
| D1 | Workbench is the interaction architecture for the experiment, enriched with Herbarium (typography, photography, specimen character) and Living Lineage (provenance, specimen relationships, collection history). Not a commitment to adopt. |
| D2 | Two complete themes (Field Ledger light and dark) are acceptable on the branch. The six existing themes are not removed or downgraded, on main or on the branch. |
| D3 | 40px controls for desktop pointer use, with focus indication, readable density and pointer-target spacing preserved. Touch targets are at least 44px. Keyboard, zoom and responsive behaviour are tested. |
| D4 | Branch created through the managed workflow; M0 baseline first. Existing capabilities, routes, auth, permissions, backend APIs and schema are preserved. Functionality needing new backend support becomes a separate proposal. |

## M0: worktree and authenticated baseline

### Worktree identity

The session's agent-provided worktree (clean, exactly at fetched `origin/main`) had its session
branch renamed to `feat/ui-redesign-exploration-001`, then `make feature-init` and
`make feature-claim AGENT_ID=claude-next` were run. Main and the primary checkout were not changed.

| Field | Value |
| ----- | ----- |
| Worktree | `.claude/worktrees/florabase-ui-consistency-8e4313` under the primary checkout |
| Branch / feature id | `feat/ui-redesign-exploration-001` / `ui-redesign-exploration-001` |
| Base and HEAD at M0 | `d94f275f5203ea2b0321e5522211d2e21190da5f` (behind main: 0) |
| Writer claim | `claude-next`, claim `b281d2b82410` |

### Baseline environment

| Field | Value |
| ----- | ----- |
| Environment | UAT Preview, Compose project `florabase-uat-preview`, `http://localhost:15174` (loopback) |
| Source | This worktree at `d94f275` = main, clean |
| Migrations | Code head and database both `20261013_0042` |
| Dataset | Synthetic UAT fixture version 4 with its additive extensions: 66 baseline records |
| Owner | UAT-only synthetic fixture owner created by `make uat-preview-seed`. No personal credentials were requested or used. |
| Isolation | Own database, media, dependency volumes and network. DEV (5173) kept running untouched; Stable Preview, Review and Sourcing were not started. |

Commands, from the worktree:

```bash
make uat-preview-up AGENT_ID=claude-next
make uat-preview-seed AGENT_ID=claude-next
```

### Capture

`capture.py` (this folder) signs in through `/api/v1/auth/login` with the fixture owner, resolves
the first real record of each list endpoint for detail routes, and captures 37 routes at 1440×844,
1024×844 and 390×844 (touch and mobile emulation for the last two). It also takes a full-page
desktop image per route and the mobile More navigation. Requests to other origins would be answered
locally and listed. The run made none.

It runs in the pinned official image `mcr.microsoft.com/playwright/python:v1.48.0-noble`
(`sha256:acc6300a…c47ac`), with `playwright==1.48.0` installed into a scratch folder that is mounted
read-only. Nothing is installed on the host or added to the repository's dependencies.

Result, captured 2026-11-04T09:42:54Z:

- 149 images: desktop 74 (37 viewport + 37 full page), tablet 37, mobile 38. None skipped, no
  console errors, no external requests. Every detail route resolved a real record.
- Areas: dashboard, global search, Seeds, Sowings, Plants and Plant groups, Harvests and stored
  material, Locations, Journal, History, Schedule list and calendar, Botanical identities, Taxonomy,
  Media, Geography, Collection origins, Species distribution, Native ranges, Suppliers, Orders,
  Settings, Labels, Import / Export, ten detail pages and two create forms.
- Manifest with route, viewport, SHA-256 and size of every image:
  [`baseline-main-d94f275.manifest.json`](baseline-main-d94f275.manifest.json).
- Images are kept out of Git, following the UI System v1 precedent of manifest plus hashes, in the
  worktree's locally excluded `.florabase-next-evidence/baseline-main-d94f275/`.

Limits: the fixture is small (2 plants, 1 group, 7 lots), so density at realistic collection sizes
is not represented. The extended Review dataset v5 is a Feature Review option for later comparison.
The run had no screen reader, no forced colours, no real zoom and no physical device. Settle time is
network idle plus 900 ms.

## Milestone plan

M0 baseline (done) → M1 Field Ledger foundation → M2 shell → M3 Today and directories → M4 record
detail → M5 quick create and QR → M6 remaining areas → M7 side-by-side comparison, regression
report and recommendation. Checkpoints with the operator come after M1, M2, M4 and M7.

### M1: Field Ledger foundation (next)

Scope, all frontend:

1. **Palette, not replacement.** Add a `field-ledger` palette with light and dark appearances to
   the existing `data-palette` × `data-appearance` matrix (`appearance/theme.ts`,
   `styles/tokens.css`). It is the default on this branch only. Botanical, Herbarium and Mineral stay
   selectable and unchanged. Evidence colours (`comparison-*`, `native-count-*`) keep their identity.
2. **Tokens.** Every existing semantic token gets a Field Ledger value, plus new ones: rail, lineage,
   data font, and pointer-aware control height (40px for fine pointers, 44px under
   `pointer: coarse` and on compact widths).
3. **Type.** Self-hosted Instrument Sans, Newsreader italic and IBM Plex Mono via `@fontsource`,
   alongside the existing Source Sans / Serif. This is a dependency change, recorded for the
   eventual FULL gate.
4. **Primitives restyled through tokens only.** Buttons, inputs, selects, status, tabs, dialogs,
   focus ring and pointer spacing. No layout or shell change yet.
5. **Tests.** Contrast assertions for the new palette in the appearance tests, existing theme tests
   unchanged, focused lint, typecheck and frontend tests.

Exit for the M1 checkpoint: the running branch in UAT Preview shows the current layout in Field
Ledger light and dark, the six original themes are unchanged, and a short capture set compares
the result with the baseline.

## Separate proposals

None yet. Anything that would need a new endpoint or contract change (for example, a per-record
timeline aggregate) is recorded here as a proposal and is not implemented on this branch.
