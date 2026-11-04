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

M0 baseline (done) → M1 Field Ledger foundation (done, awaiting checkpoint review) → M2 shell → M3
Today and directories → M4 record detail → M5 quick create and QR → M6 remaining areas → M7
side-by-side comparison, regression report and recommendation. Checkpoints with the operator come
after M1, M2, M4 and M7.

## M1: Field Ledger foundation

Commits `8ce52fa` (foundation), `b39fa50` and `ecadaf3` (touch-target fixes found by the capture
probe). Frontend only: no backend, API, schema, route, auth or data change.

### What Field Ledger is

Field Ledger is a **system**, not a fourth colour palette. It is selected through the existing
`data-palette` × `data-appearance` matrix, so the same bootstrap, Settings control and
browser-local preference apply, but it also owns type, geometry and focus:

| Layer | Field Ledger | UI Foundation (six themes) |
| ----- | ------------ | -------------------------- |
| UI face | Instrument Sans Variable | Source Sans 3 Variable |
| Scientific names | Newsreader Variable italic (optical size) | Source Serif 4 Variable italic |
| Recorded data | IBM Plex Mono 400/500: metrics, pagination positions | UI face |
| Body / strong | 14/20 px, weights 400/600 | 15/22 px, weights 400/600 |
| Titles | 30/34 and 20/26 px at 600, −0.012em tracking | 32/38 and 22/28 px at 650 |
| Radii | 8 controls, 12 surfaces, 14 dialogs | 6, 10, 14 |
| Pointer controls | 40px; 44px under `max-width: 48rem` or `any-pointer: coarse` | 44px (compact icons 40px) |
| Focus | 3px ring, 2px offset | 3px ring, 3px offset |
| New roles | rail, rail text and active, lineage and lineage tint | resolve to existing semantic tokens |

Minimum contrast under the rules the existing tests enforce for every theme, with text 4.5:1 and
cues 3:1 on background, surface, subtle, hover and primary-tint surfaces:

| Appearance | Text (worst pair) | Boundary cue (worst pair) | On primary | Rail muted text |
| ---------- | ----------------- | ------------------------- | ---------- | --------------- |
| Light | 5.37:1 muted on hover | 3.29:1 control border on hover | 6.92:1 | 9.94:1 |
| Dark | 5.48:1 muted on primary tint | 3.41:1 control border on primary tint | 9.86:1 | 9.76:1 |

### How it is built

- **Tokens, not overrides.** New system tokens (`--font-data`, `--focus-ring-width`,
  `--focus-ring-offset`, `--tracking-heading`, `--control-height-touch`,
  `--control-height-compact`, `--rail-*`, `--lineage*`) default in `:root` to the exact UI Foundation
  values. Shared rules read them. Field Ledger overrides them in one system block plus one block per
  appearance in `styles/tokens.css`. Shared rules in `foundation.css`, `normalization.css`,
  `styles.css`, `directory.css`, `directory-workspace.css` and `settings.css` swapped literals for
  those tokens: focus outlines, title tracking, detail-tab height, pagination position font, and
  the heights of pagination and row-action icons, the active-filter chip lane and the sidebar group
  toggles. No page-local Field Ledger CSS exists.
- **The six themes are pinned.** A test hashes the six original palette blocks and must match
  main `d94f275` byte for byte. Saved Botanical, Herbarium or Mineral preferences are honoured; only
  a missing, corrupt or unknown preference falls back to Field Ledger. That fallback applies on this
  branch only. Main is untouched.
- **Fonts** are exact-pinned Fontsource 5.3.0 packages (OFL-1.1), bundled as same-origin WOFF2, with
  each package's licence shipped under `/licenses/` (`instrument-sans.txt`, `newsreader.txt`,
  `ibm-plex-mono.txt`). There is no CDN, and a test rejects Google Fonts or remote `@import`.
  Faces load only when the active system uses them: a Botanical page loads only Source Sans. The
  production build adds 20 WOFF2 files (Instrument Sans 88 KB, Newsreader 516 KB, Plex Mono 120 KB,
  all subsets). Unicode-range subsetting means a Latin page fetches only its Latin subsets.
- **Settings swatches** now render each system's own UI face, so the Field Ledger option previews
  Instrument Sans and the others preview Source Sans.

### Verification at `ecadaf3`

| Check | Result |
| ----- | ------ |
| Typecheck, ESLint (0 warnings), Prettier | pass |
| Focused: appearance, theme bootstrap, Controls, ThemeControl, Settings, components, plants, seed lots, sowings | pass, 23 files and 313 tests on the final tree |
| Full frontend suite, three serial runs | 1153/1153 each time; main `d94f275` passed 1145/1145 three times |
| Production build | pass; no Google Fonts references in `dist` |
| Feature graph | valid |

Honest note on flakiness: earlier full runs on this branch, executed while screenshot captures
and the main comparison ran concurrently, each showed one different intermittent failure:
UX004 legacy deep links, StoredMaterial QR hash focus, and Schedule pending-save focus return. All
three are focus or timing assertions in suites that run `appearance.js` but apply no CSS (jsdom).
None reproduced in isolated reruns (UX004 5/5, StoredMaterial 6/6) or in the three serial full runs.
Main was not observed failing in three runs, so branch involvement cannot be fully excluded from
this sample; it is listed for the independent reviewer.

Canonical FULL was not run, as instructed.

### Screenshot evidence (representative, not the full matrix)

Captured from UAT Preview (same isolated project, synthetic fixture, preview owner) serving
`ecadaf3`, with `capture.py`. New options: route and viewport filters, a theme preference seeded
before page scripts, a keyboard-focus capture, and a probe that records the active palette, UI
face, `--control-height` and every rendered control below the target (40px desktop, 44px touch).
Manifests are in [`m1/`](m1/); images are in `.florabase-next-evidence/m1-ecadaf3-*`.

| Set | Images | Probe result |
| --- | ------ | ------------ |
| Field Ledger light: 7 routes desktop + mobile, keyboard focus, mobile More | 16 | min 40px desktop, 44px mobile, 0 controls below target, 0 console errors |
| Field Ledger light, tablet: dashboard, Seeds, plant detail | 3 | min 44px, 0 below target |
| Field Ledger dark: 7 routes desktop + mobile | 14 | min 40px desktop, 44px mobile, 0 below target, 0 console errors |
| Botanical preservation: all 37 baseline routes, desktop, baseline order | 37 | see below |

Botanical preservation against the main baseline: **33 of 37 pixel-identical.** The four
differences:

- **Settings:** intended. The Field Ledger option is added to the theme picker.
- **Dashboard:** capture nondeterminism. Two identical repeat runs of the same build differ from
  each other; one of them matched main exactly.
- **Geography:** 62 pixels of rounded-corner anti-aliasing, one or two levels per channel. It was
  pixel-identical to main in two earlier M1 runs.
- **Collection origins:** 131 pixels inside Leaflet's zoom +/− glyphs, consistent across M1 runs.
  The computed font (`700 22px "Lucida Console", Monaco, monospace`) and the loaded faces (Source
  Sans only) match main's rules, and no changed rule applies to that control. **Unexplained;**
  rechecked live in the Phase E side-by-side.

The baseline is unchanged: 149/149 images still match their committed hashes.

### Findings recorded during M1

- **Pre-existing on main:** Leaflet's touch stylesheet (`.leaflet-touch .leaflet-bar a`, 30px)
  outranks the app's `.leaflet-bar a` control-height rule, so map zoom buttons are 30px in every
  theme. Maps keep their own controls in this plan; this is listed for M6 or a separate fix and
  was not changed in M1.
- **Pre-existing on main:** `geography.css` re-declares `.app-content .workspace > .breadcrumbs`
  with the same specificity as `breadcrumbs.css`, and it loads lazily. After any Geography visit,
  directory breadcrumb spacing changes from the intended 20px to 8px for the rest of the session.
  This made baseline captures route-order dependent. Not changed in M1.
- **Fixed on this branch for Field Ledger:** pagination arrows, row-action icons, active-filter
  chips and sidebar group toggles were 40px on touch (also on main). They now follow the
  pointer-aware height under Field Ledger and keep their values in the six themes.

### M1 limits and what M1 deliberately does not do

- Layout, navigation and component structure are unchanged; M1 restyles through tokens only. The
  Workbench shell, rail, command palette, inspector, lineage strip and timeline begin in M2–M4.
- Status badges keep their current outlined form. The dot-and-word status from the design arrives
  with the M3 directory primitives.
- Tests use jsdom, which applies no CSS. Visual behaviour is evidenced by the captures and probe,
  not by unit tests. There was no screen reader, forced-colours, browser-zoom or physical-device
  check.
- A browser that already stored a Botanical preference for `localhost:15174` keeps it; choose Field
  Ledger in Settings → Appearance.

## Separate proposals

None yet. Anything that would need a new endpoint or contract change (for example, a per-record
timeline aggregate) is recorded here as a proposal and is not implemented on this branch.
