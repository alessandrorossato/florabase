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

M0 baseline (done) → M1 Field Ledger foundation (accepted) → M2 Workbench shell (accepted) → M3
Today and directories (done, awaiting checkpoint review) → M4 record detail → M5 quick create and QR → M6 remaining areas → M7
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

## M2: Workbench shell and navigation

Commit `307611b` (implementation and tests), frontend only. No backend, API, schema, route, auth
or data change. Field Ledger light and dark and the six UI Foundation themes all render inside the
new shell; the shell reads only semantic and rail tokens.

### Architecture

| Path | Role |
| ---- | ---- |
| `shell/navigation.ts` | The single navigation model: six workspaces, every section once, existing sub-views as deep links (Plant groups, Stored material, Calendar, Collection origins, Species distribution, Native ranges), and the shared creation actions also used by Dashboard Quick add. |
| `shell/WorkbenchShell.tsx` | Rail, context panel, mobile header strip, bottom bar, workspace and account sheets, the global shortcut. Owns no routing. |
| `shell/CommandPalette.tsx` | Finder over sections, creation routes and records from the existing `/api/v1/search`. |
| `shell/workbench.css` | Every rule scoped to `.wb-shell` or a `.wb-*` part, imported after the global sheets and before lazily loaded page CSS. |
| `App.tsx` | Keeps route parsing, workspace rendering, the content region and its handlers. All shell navigation goes through one guarded `navigateTo(href)`: same unsaved-form confirmation as before, push or replace history, and a remount for same-section targets. 1029 → 621 lines. |
| `test/navigation.ts` | `openSection(user, label)`: tests reach any section the way an operator does (the link if visible, otherwise the owning workspace tab first). |

The shell keeps the existing layout contract: one sidebar grid item before `.app-content`, so every
page's `.application-shell:has(…)` rule for full-height directories and document-flow pages applies
unchanged, including the mobile `auto / 1fr` row.

### Interaction model

- **Rail = workspaces.** A vertical `tablist` (Today, Collection, Activity, Explore, Sourcing and,
  pinned at the bottom, Settings). Selecting a tab previews that workspace's sections in the panel
  **without navigating**, like an activity bar, so browsing workspaces never loads a page or adds
  history. Arrow keys, Home and End move a roving tab stop. A dot and the accessible suffix
  ", current location" mark the workspace of the open page. Selecting the open workspace again hides
  the panel, and the next navigation returns the panel to the page's workspace.
- **Context panel = tabpanel.** Global tools (Search with the shortcut shown, and New with all nine
  creation routes), the workspace title in Newsreader with a one-line summary, its sections and
  sub-views with `aria-current="page"` on the exact view, and the account (signed-in owner, theme,
  Hide panel, Sign out). The hidden state is a browser-local preference
  (`florabase.workbench.panel-collapsed.v1`); corrupt values fall back to shown.
- **Command palette.** Ctrl/⌘+K anywhere, or `/` outside text fields. Empty: Create and Go to (every
  section and sub-view). Typed: Records (debounced, at most 8, server-built links), Go to, Create, and
  "All results for …" into the existing filtered Dashboard search. Combobox with listbox semantics,
  arrow keys and Enter, Escape, focus returned to the invoking control. Search loading and failure
  are stated; on failure sections and actions keep working.
- **Mobile (≤ 48rem).** The rail becomes a header (Florabase wordmark, search, account). The panel
  becomes a scrollable strip of the current workspace's sections. A fixed bottom bar of the five
  workspaces opens a sheet with that workspace's sections and sub-views. An account sheet holds
  Settings, Labels, Import / Export, theme and Sign out.
- **Tablet (48–75rem).** Rail and panel stay; the panel narrows to 15rem so content keeps
  roughly the width the previous sidebar left.

### Navigation and interaction coverage

| Journey | Covered by |
| ------- | ---------- |
| Every former destination reachable, once, on desktop and through mobile sheets; each route sets URL, `aria-current`, heading and breadcrumb | `App.test.tsx` "Workbench workspaces, panels and mobile sheets retain every destination and route" |
| Previewing a workspace does not navigate or remount; hide and reopen, focus return, persisted preference | "desktop context panel previews, hides and reopens without remounting the workspace" |
| Tablist keyboard model; panel follows hash navigation | "workspace tabs support arrow keys and the panel follows activated routes" |
| Malformed panel preference | "Workbench tolerates a malformed panel preference" (3 cases) |
| Model completeness, sub-view current state, guarded and modified clicks, New menu, palette (shortcut, local results without network, record search with loading, results, keyboard choice, full-search link, failure, `/` ignored in fields), mobile sheets, account and sign-out busy state | `shell/WorkbenchShell.test.tsx`, 10 tests |
| Legacy and canonical map aliases mark the right sub-view | `GeographyWorkspace.test.tsx` (6 cases) |
| Existing screen suites (Seeds, Sowings, Plants, Settings, Labels, Import / Export, lazy loading, route transitions) | Unchanged behaviour assertions; navigation steps use `openSection` |

### Verification at `307611b`

| Check | Result |
| ----- | ------ |
| Typecheck, ESLint (0 warnings), Prettier, production build | pass |
| Full frontend suite | 1164/1164: 1154 existing (some updated for the new shell) + 10 new shell tests. Serial reruns on the final tree are listed in progress.md |
| Feature graph | valid |

Canonical FULL was not run, as instructed.

### Accessibility and responsive results

- Measured on real renders (capture probe) with Field Ledger light: 43 captures over 12 routes at
  1440, 1024 and 390, plus palette, workspace preview, New menu, workspace and account sheets, and
  keyboard focus. **No control is below 40px with a fine pointer or 44px with touch, and there are no
  console errors.** Dark: 10 captures, same result. Botanical inside the new shell: 7 captures with
  no console errors; one 40px filter chip on mobile, as on main, because the six themes keep their
  original compact sizing (M1).
- ARIA: rail tablist with roving tabindex; panel tabpanel labelled by its tab; page titles keep
  `h2` (the panel title is not a heading, so it never competes with a page title); palette
  combobox with listbox, groups and `aria-activedescendant`; dialogs use the existing focus-trapping
  `TaskDialog`; `aria-current="page"` on the exact view and `aria-current="true"` on the mobile
  workspace of the open page; icon-only buttons are named ("Search and commands", "New record",
  "Account and settings").
- Forced colours: selected tab, current link and active option gain a `Highlight` outline. Print
  hides the shell. No new motion.
- Not covered: screen reader, real browser zoom, physical devices.

### Before and after (real UAT Preview captures, same synthetic data)

Before: `baseline-main-d94f275`. After: `m2-307611b-field-ledger-light`, `-dark` and
`m2-307611b-botanical`. Manifests are in [`m2/`](m2/); images are in `.florabase-next-evidence/`.

### Findings carried from M1

| Finding | M2 outcome |
| ------- | ---------- |
| `geography.css` duplicated `breadcrumbs.css` and, loaded lazily, changed directory breadcrumb spacing app-wide after any Geography visit | **Fixed.** The duplicate is removed and `breadcrumbs.css` alone owns breadcrumb geometry. |
| Leaflet zoom buttons were 30px in every theme (`.leaflet-touch .leaflet-bar a` outranked the app rule) | **Fixed.** The shared rule now matches that specificity: 40px with a pointer and 44px on touch under Field Ledger, 44px in the six themes. Verified on Collection origins. |
| 131-pixel difference in the zoom glyphs on Collection origins | **Superseded, still unexplained.** The resize changes those pixels by design, so the M1 comparison no longer applies. Recheck in the Phase E side-by-side. |
| Intermittent full-suite failures in focus/timing tests (UX004, StoredMaterial, Schedule) under concurrent load | **Still tracked, not classified.** None observed in the M2 full runs listed in progress.md. Main was clean in 3 of 3 runs in M1. |

### Deviations from the Claude Design concept

1. **The rail previews rather than navigates.** In the concept a rail click opened a workspace.
   The activity-bar model avoids loading pages and history entries just to look around, and maps
   directly onto the ARIA tabs pattern. Opening a section is one more click; the palette remains a
   one-step route to any section.
2. **No global top bar.** Search and New sit at the top of the context panel, because a separate
   top bar would break the existing page layout contract (`.application-shell > .app-content`)
   that full-height directories depend on. When the panel is hidden, a search button appears in the
   rail.
3. **No counts or saved views in the context column.** There is no endpoint with counts for every
   section (the dashboard aggregate covers four active kinds), and saved views have no direct
   route. Showing either would mean new API work or extra requests on every page, so they are
   deferred rather than faked.
4. **Settings is a sixth workspace** holding Settings, Labels and Import / Export, so the Tools are
   discoverable without opening the Settings page.
5. **Mobile bottom bar holds workspaces, not Today / Scan / Record.** Scan and record belong to M5
   (QR and quick capture). Today is the first workspace.
6. **Dashboard is unchanged** and keeps its own search and Quick add next to the panel's Search and
   New; M3 replaces it with Today. The creation list is already shared.
7. **The inspector, lineage strip and timeline** are not part of the shell; they arrive with the
   directories and record detail in M3 and M4.

### Removed and replaced

- The flat grouped sidebar, its collapsed-groups preference
  (`florabase.sidebar.collapsed-groups.v1`, now ignored), the resize handle
  (`SidebarResizeHandle.tsx`, `sidebarWidth.ts`), and the mobile Home / Seeds / Sowings / Plants +
  More bar.
- About 620 lines of now-dead sidebar CSS across `styles.css`, `foundation.css`,
  `normalization.css`, `controls.css` and four page sheets. Removal matched whole class tokens only;
  live selectors in mixed lists were kept.

### Outstanding for review

- One more click to reach a section in another workspace (deviation 1). The palette mitigates
  this, but it is a real change to habit.
- Botanical, Herbarium and Mineral render the rail with their light `surface-subtle`, which is
  coherent but less distinctive than Field Ledger's dark rail.
- The page-level duplication of Search and Quick add on the Dashboard remains until M3.

## M3: Today and directories

Commit `b59a21c` (implementation and tests), frontend only. No backend, API, schema, route, auth or
data change. Today stays on `#/dashboard` and its existing `/api/v1/dashboard` endpoint.

### Today

Today replaces the Dashboard presentation. Every line comes from returned data, and each panel
states where its data comes from:

| Area | Source | Honesty rule |
| ---- | ------ | ------------ |
| Lede ("1 overdue and 7 due today in the Schedule. You hold 2 active Plants…") | Schedule counts and active record counts | Composed only from returned numbers. With nothing due it says so; no greeting, trend or inference. The eyebrow date is the operator's local calendar day. |
| Collection snapshot | Active record counts, current identity membership | A ruled ledger of four record counts, labelled as records, not plant totals or quantities. |
| Next work | Schedule (overdue, today, next seven days, earliest planned items) | Labelled "Planned in Schedule". Overdue is explained as derived from the due date, not a statement that work did or did not happen. |
| Plants in your collection | Selected active Plants with their own primary photo or a labelled identity reference | Specimen plates with Newsreader scientific names; the photo source is shown on the plate, and attribution stays available. |
| Recent activity | Journal and History projection | Each entry keeps its Journal or History origin, Reversed state and recorded-time labelling. |
| Record keeping | The existing derived dashboard counts | Labelled "Derived counts of current records. Prompts to review, not tasks or conclusions." The six counts carry their exact definitions, and the panel states that zero is a recorded count, not a failure. |

**Deliberate reversal for review:** DASHBOARD-001 / GLOBAL-VISUAL-001 removed the Propagation,
Sourcing and Botanical coverage modules from rendering for v0.1 focus, and deferred additional
summaries to a later Dashboard review. Record keeping brings those counts back as one compact,
explicitly derived panel, because this exploration is that review. It is easy to remove if the
v0.1 decision should stand.

Global search, Filters and Saved views stay in the Today header, and search results still replace
the overview. **The page-level Quick add is consolidated into the Workbench New menu.** Shell
creation routes now go through the same `openCollectionPage` path as content links, so Back from
a creation task returns to its directory wherever it started. This is covered by the existing
"New Sowing Back uses Sowings as parent" and "New plant/group Back" tests, now entered from Today
through New.

### Directories (Ledger grammar)

Applied to every `DirectoryPage` directory (Seeds, Sowings, Plants and Plant groups, Harvests,
Locations, Botanical identities, Suppliers, Orders and others), reviewed first on Seeds and Plants. It
is implemented as edits to the owning rules in `directory-system.css` (the UI System v1 directory
contract), `directory.css` and `status.css`, not as a new override layer:

- **List rows** in a single bordered ledger with hairline separators, a row hover, framed 3rem
  thumbnails, the scientific name in Newsreader italic, the summary (quantity, type) end-aligned
  with tabular figures, and the existing inset bar for selection.
- **Row actions** (More, Open details, Edit) are borderless until hover or open, at the shared control
  height: 44px in the six themes as before, and 40/44px in Field Ledger.
- **Gallery** cards are specimen plates: a full-bleed 4:3 photograph, or a hatched plate with the
  record's icon where no photo exists. The selected card gets a primary outline.
- **Phones:** the record takes the full line and its actions follow on their own row, replacing
  the cramped title-beside-stacked-actions layout.
- **Status** chips become a dot and the word on a faint tint of their colour, with an outline in
  forced colours.
- **Typography:** in Field Ledger, page, record and section titles use Newsreader 500 through
  `--type-h1` and `--type-h2`, so directories, Today, dialogs and record titles share the botanical
  serif. The six themes are unchanged; their token blocks remain pinned to main.

Every directory capability is preserved and untouched in code: search, lifecycle and type filters,
the filter drawer and chips, List and Gallery, Saved views per surface, Select records and bulk
moves, pagination and page size, row Details, Edit and More menus, direct Details routes and
Back/Forward focus restoration. The existing directory test suites pass. Only their Dashboard entry
steps changed (Today and New instead of Dashboard and Quick add); no directory behaviour
assertion was altered.

### Saved Views discoverability

Saved views stay private shortcuts to existing directory URLs. The shell now lists them without
any new API or route:

- `shell/useSavedViewLinks.ts` lists the owner's views through the existing
  `GET /api/v1/saved-views` and turns each into its ordinary URL with the existing `savedViewHash`
  serializer. Only views it accepts are shown; an incompatible view stays in its directory's own
  dialog, which explains it.
- They appear in the panel of the owning workspace (Seeds views under Collection), all of them under
  Today, in mobile workspace sheets, and in the command palette ("Saved view · Seed lots").
- The list refreshes when the existing Saved views dialog creates, renames, updates or deletes a
  view (a window event from `saved-views/events.ts`). A listing failure simply hides the group.
- Opening a view takes one click from the panel. On main it took three: open the directory, then
  Saved views, then the view.

### Workspace-preview evaluation (requirement 6)

This is an analytical keystroke-level comparison, not user testing (no user testing was possible
here).

| Journey | Main | M2 | M3 |
| ------- | ---- | -- | -- |
| Today → Seeds | 1 click | 2 (tab, link) | 2 first time; 1 from Recent afterwards; or Ctrl K, type, Enter |
| Seeds → Plants (same workspace) | 1 | 1 | 1 |
| Plants → Orders (another workspace) | 1 | 2 | 2, or 1 from Recent once visited |
| Open a Saved View | 3 | 3 | 1 from the panel or palette |
| Start a new sowing from anywhere | 2 (Dashboard Quick add, from the Dashboard only) | 2 (New, item) | 2 (New, item), from every page |
| Return to Today | 1 | 1 (brand mark) | 1 (brand mark) |

Conclusion: keep the preview model. It reduces what the panel shows at once (at most five sections with
their sub-views, instead of fifteen destinations) without page loads. The extra click for a cold cross-workspace trip is offset for
repeated trips by Recent, and for named destinations by Saved views and the palette. M3 adds those
rather than reverting to an always-expanded list. Worth testing with the operator: whether Recent
should be pinned higher, and whether single-section workspaces should navigate on selection.

### Verification at `b59a21c`

| Check | Result |
| ----- | ------ |
| Typecheck, ESLint, Prettier, production build | pass. Main JS 251.5 → 262.7 kB (gzip 78.1 → 81.5 kB) from the Saved Views serializer in the shell; main CSS 224.9 → 223.4 kB |
| Full frontend suite | 1169/1169. Serial reruns are listed in progress.md |
| New tests | Today: summary composed from counts, sources stated, record-keeping definitions and values, the empty Schedule wording. Shell: Saved Views by workspace, Today and palette, incompatible omitted, refresh on change; listing failure; Recent. Ported: Quick add menu keyboard and dismissal tests now exercise the New menu |
| Feature graph | valid |

### Evidence

Captured from UAT Preview serving `b59a21c`. A temporary Saved View ("Basil lots", Seeds, `q=basil`)
was created through the authenticated API to show discoverability, then deleted. The UAT data
returned to its fixture state (verified: zero Saved Views).

| Set | Images | Probe |
| --- | ------ | ----- |
| Field Ledger light: 10 routes at 1440/1024/390, desktop full pages, palette, preview, New menu, sheets, keyboard focus | 47 | min 40px desktop, 44px touch; 0 below target; 0 console errors |
| Field Ledger dark: Today, Seeds, Plants, plant detail at 1440/390 | 8 | same result |
| Botanical: Today, Seeds, Plants at 1440/390 | 6 | 0 console errors; the 40px filter chip on mobile is unchanged from main |

Before/after composites (main baseline against M3) for Today desktop (full page), Today mobile,
Seeds desktop, Plants dark, Plants tablet and Seeds mobile are in
`.florabase-next-evidence/m3-before-after/`. Manifests are in [`m3/`](m3/).

### Limitations and known regressions

- **Quick add is no longer on the page.** Creation from Today is through New (two clicks, the same
  as before), now global. Anyone used to the in-page button needs to find it in the panel.
- **The Dashboard title is now Today.** The route and Saved View surface (`global_search`) are
  unchanged, but the visible name changed.
- **Record keeping** contradicts the v0.1 decision to hide these modules (see above).
- **Gallery plates** show a thin band above the photograph; it is a padding left by an earlier
  rule and is minor polish for M6.
- **Phone headers** in directories still stack the search, view switch, Filters, Saved views and
  New over three lines before the first record. The tools grammar is shared with M4 and M6 work.
- **The main JS chunk is 11 kB larger** (3.4 kB gzipped) because the shell now carries the
  Saved Views serializer.
- The 30px Leaflet zoom fix and the breadcrumb fix from M2 still apply. The M1 glyph variance stays
  unexplained until the Phase E side-by-side.

## M4: Record detail and lineage

Commits `94a1675` (implementation and tests), `bfb23b4` (Order detail target size) and
`380e6f4` (Harvest de-duplication). Frontend only: no backend, API, schema, route, auth or data
change. Every record reads existing endpoints.

### M3 decisions applied

| Decision | Outcome |
| -------- | ------- |
| Keep the record-keeping counts as secondary, collapsible **Data quality** | Today ends with a full-width, collapsed `Data quality` disclosure with a dashed neutral border. It has no warning colour, badges or counts in the closed state. Open, it keeps the six exact definitions, the "Derived counts of current records. Prompts to review, not tasks or conclusions." source line, and the "zero is a recorded count, not a failure" note. Recent activity takes the full width above it. |
| Saved Views stay usable with many views | The panel and mobile sheets show the first five, then a "Show all N saved views" button (`aria-expanded`, `aria-controls`) that expands in place and collapses with "Show fewer". The arbitrary eight-item cap is removed, so every compatible view is reachable from the panel as well as the palette. Tested with 12 views. |
| Mobile directory header density | **Carried as a required item before final visual acceptance.** Not addressed in M4, which is about record detail. It is listed under Outstanding below so it cannot drop out of the plan. |

### Record identity header (all ten record types)

`CollectionUI.DetailHeader` and `detail-page.css` own the header for Plants, Plant groups, Seed
lots, Sowings, Harvests, Stored material, Locations, Botanical identities, Suppliers and Orders.
There are no per-page overrides.

- A 6rem specimen plate (4.5rem on phones), framed, holding the record's own photo or its
  labelled identity or kind fallback, exactly as before.
- Kind eyebrow, then the record title on a new `--type-record-title` step. That step is defined only
  in Field Ledger (Newsreader 2.375rem); the six themes fall back to their `--type-h1`.
- Scientific names linked from the header (`#/identities/…`) render in the botanical face, as in
  directory rows.
- A lifecycle line, then actions in the top right (stacked under the identity at ≤ 64rem). The
  record-actions group, the overflow menus, Edit and every primary action are unchanged.
- An optional `lineage` slot spans the header for records with recorded sources.

**Less repetition.** Lifecycle is stated once, in the header. It is removed from the At a glance
band of Plant, Plant group, Seed lot and Sowing. The location stays in At a glance, where it is
labelled "Current location", "Last recorded location" or "Storage". The Sowing's Seed lot moves
from the header facts into the lineage strip. On Harvest, Source stays in the header and the date
only in At a glance, where it keeps its recorded precision.

### Recorded lineage strip

`lineage/LineageStrip.tsx` with `lineage/useRecordedLineage.ts`. `LineagePanel` now shares the hook
and has the same output.

- **Sources:** the existing `/api/v1/{plants|plant-groups|seed-lots}/{id}/lineage` endpoints. The
  backend walks one recorded source per record, so the path is linear. It is reversed to read
  oldest first and ends at "This Plant", "This Plant group", "This Seed lot" or "This Sowing".
- **Sowings** have no lineage endpoint. They read their recorded Seed lot's path and include that
  Seed lot. This uses the same explicit relationships, not inference.
- **Shown:** kind, linked label and any lifecycle other than active (for example exhausted or
  reversed). "Full lineage" opens the Lineage tab and is hidden while that tab is open.
- **Not shown:** descendants, shared Botanical identity, or anything else that would need
  inference. With no recorded source, the strip says "No recorded source material."
- **States:** loading and failure (with "Retry lineage") are visible but not live regions, because
  the strip is secondary to the page heading. The separator arrows are decorative CSS
  (`content: "→" / ""`); the ordered list carries the sequence.

Plant, Plant group, Seed lot and Sowing details carry the strip. Harvests and Stored material have
no lineage endpoint. Harvest keeps its recorded Source in the header facts.

### Record timeline

`timeline/RecordTimeline.tsx` replaces `schedule/UpcomingActivities.tsx` in the Plant, Plant group,
Seed lot and Sowing overviews. It has two lanes on one rule:

| Lane | Source | Honesty rule |
| ---- | ------ | ------------ |
| **Planned** ("in Schedule, not yet done") | Existing `listSchedule` with the record's `target_kind`/`target_id`, planned status, first three | Hollow, dashed nodes. Each item says Planned, Due today, or "Overdue · not recorded as done", with the overdue node in the warning colour. Nothing planned is shown as having happened. "View all N in Schedule" and "Schedule activity" keep the existing filtered links (the latter only for active records). |
| **Recorded** ("in the Journal") | Existing `listEvents` for Plants and Plant groups, in the API's order (dated newest first, undated last), first three | Solid nodes. Dates use `formatPartialDate`, so year-only stays `2024`, month-only `2025-04` and an undated entry "Date not recorded". The source (Journal, Harvest or Collection operation) is kept. "Open Journal (N entries)" opens the Journal tab. |
| Recorded, other records | No per-record event API | Seed lot: "Seed lots have no Journal" with a link to its Sowings tab. Sowing: points to the Germination tab, where its dated observations are. |
| System history | Not available per record | A footnote links History filtered by the record's kind. A per-record History filter is a separate proposal (below). |

The lanes sit side by side when the section is wider than 36rem and stack otherwise. Overdue is
recomputed when the local day changes, without polling.

### Preserved functionality

Code paths were untouched for editing (all edit dialogs and the unsaved-change guard), deletion
and reversal, permissions-driven action visibility, tabs and their `?tab=` deep links, Journal,
Photos and media, Germination, Lineage tabs, Order seed-lot linking, Print label, Record harvest,
Create Plant or group from a Sowing, and Back/breadcrumb navigation. The detail suites pass. Only
three assertions changed, each for an intended design change:

- the Seed lot summary no longer lists Lifecycle, which is now asserted in the header;
- the "Upcoming activities" heading became the Timeline with Planned and Recorded regions;
- one Plant Journal fixture now serves two reads, because the Overview and the Journal tab each
  read the Journal.

### Verification

| Check | Result |
| ----- | ------ |
| Typecheck, ESLint (0 warnings), Prettier, production build | pass. Main JS 262.7 → 263.1 kB (gzip 81.5 → 81.6 kB) |
| Full frontend suite | 1177/1177 at `94a1675` and again at `380e6f4` (1169 at M3, +1 Saved Views, +7 strip and timeline; the Upcoming activities test was ported, not added). Serial reruns are listed in progress.md |
| New tests | `LineageStrip.test.tsx` (4): oldest-first explicit path with links and `aria-current`, the subject not repeated, Sowing via Seed lot, empty wording, retry. `RecordTimeline.test.tsx` (3): planned versus overdue wording, links, filter; day, month and year precision and undated entries; source labels; Journal open; History link; records without a Journal; inactive records cannot schedule; empty, failed and retry for both lanes. Shell: 12 Saved Views disclosure. Today: Data quality collapsed by default. |

### Evidence

Captured from UAT Preview serving `380e6f4`: nine detail routes (Seed lot, Sowing, Plant, Plant
group, Harvest, Location, Botanical identity, Supplier, Order) at 1440 (viewport and full page),
1024 and 390.

| Set | Images | Probe |
| --- | ------ | ----- |
| Field Ledger light | 36 | 0 console errors; min 40px; 0 below target |
| Field Ledger dark | 36 | 0 console errors; min 40px; 0 below target |
| Botanical | 36 | 0 console errors. Order detail's inline action is 40px at touch widths, because the six themes keep their original pointer geometry (M1, D2) |

The first capture pass found Order detail's "View physical seed lots" at a fixed 2rem in every
theme. `bfb23b4` sizes it from `--control-height-compact`, so it is 40px everywhere and 44px on
touch in Field Ledger. Earlier milestones did not capture Order detail, so this was not a
regression from M1–M3.

Before/after composites (main `d94f275` against M4, Field Ledger light) are in
`.florabase-next-evidence/m4-before-after/`. There are nine desktop full pages; Plant, Sowing and
Seed lot at 390 and 1024; and Plant in dark. Manifests are in [`m4/`](m4/).

### Deviations from the Claude Design concept

1. **No descendant branch in the strip.** The concept drew lineage both ways. Descendants exist
   only as Sowing propagation summaries and group extraction lists, and those stay in their
   Overview sections and Lineage tabs. Drawing them in the header would mix counts with recorded
   paths.
2. **One timeline section, two lanes, not one merged chronology.** Partial dates (a year, a month)
   cannot be honestly interleaved with exact due dates, so planned and recorded entries keep
   separate orderings on a shared visual rule.
3. **No system-history lane.** It needs a per-record History filter that does not exist.
4. **No inspector side panel on details.** The header, strip and tabs already carry identity and
   navigation; an inspector would duplicate them.

### Outstanding for review

- **Required before final visual acceptance:** mobile directory header density (M3 decision 3).
- The programmatic focus outline on the record title (focus moves there on navigation, as on main)
  is prominent in direct-load screenshots. It is correct keyboard behaviour and was left unchanged.
- The Overview and the Journal tab each read the Journal (one extra request on Plant and Plant
  group details).
- Origin and provenance on Plants still lists the originating Sowing and Seed lot that the strip
  also shows. It keeps them because it adds context (group botanical context, direct origin
  kind). Review whether the duplication is wanted.
- Locations, Suppliers, Orders, Botanical identities, Harvests and Stored material only get the
  shared header in M4. Their overviews keep their existing layouts.
- The StoredMaterial focus test ("a QR inventory hash change focuses the retained record…") failed
  in one full-suite rerun and 2 of 30 isolated runs. Its component, test and API are unchanged on
  this branch and import no M4 code. It stays tracked (since M1), and is not classified as
  pre-existing until it is reproduced on main.

## M5: Advanced interactions and mobile workflows

Commit `e593c50`, frontend only. No backend, API, schema, route or auth change. M4 is accepted
as an experimental milestone, not as final visual acceptance of record detail.

### Record sheet

One place to start recording, from every page:

- **Where it opens:** the accent item at the top of the rail (desktop and tablet, visible even
  with the panel hidden), and the first item of the phone bottom bar.
- **This record:** on a Plant, Plant group, Sowing or Seed lot detail, the sheet leads with that
  record's own actions:
  - Add Journal entry (Plants and Plant groups).
  - Add germination observation (Sowings).
  - Open recorded lineage.
  - Print label.
  These are the actions the page itself offers regardless of lifecycle. Lifecycle-dependent
  actions (Start sowing, Create Plant, Schedule activity) stay on the page, so the shell never
  shows an action the page would withhold.
- **Choose a record:** Plant, Plant group or Sowing, through the existing Schedule target picker
  (the one the Journal's Record menu uses), then straight into that record's form.
- **Open a label:** see QR below.
- **Other recording:** Record harvest, Record sowing, Complete scheduled work (existing routes).

**No form copies.** Following the Journal's own rule ("Target-dependent workflows reuse their own
detail route"), a one-time `?entry=new` parameter opens the record's real Journal or germination
form. Its validation, permissions, unsaved-change guard and history behaviour are therefore
unchanged. The parameter is read in a pure state initialiser (safe under StrictMode) and removed
from the address once the form is open, so reload, Back and remounts do not reopen it. From a
Sowing on a phone, a germination count is two taps away: Record, then Add germination
observation.

### QR and label links

Labels already encode an ordinary record URL (`<canonical origin>/#/seeds|plants|plant-groups/<id>`,
or a Harvest URL with `?inventory=<id>`). A phone camera already opens them. M5 adds what existing
capabilities support:

- **Label link field.** A typed or pasted link, or a USB/Bluetooth scanner, which types the code
  and presses Enter. Only the exact shapes labels encode are accepted, and only their in-app
  route is used, so a code can never leave Florabase or start an action (`create`, `edit`). The
  canonical origin is not compared, because labels may carry the public address while the app is
  open on a LAN one. Refusals are stated.
- **Scan with camera**, only where the browser has `BarcodeDetector` and a camera in a secure
  context. That means Chromium on Android and some desktops; not Safari or Firefox, and not plain-HTTP LAN
  addresses. The button is absent elsewhere rather than broken. Frames stay on the device, the
  camera is released when a label is read or the sheet closes, and foreign codes are refused.
  **Not tested on a real device or camera**; covered by unit tests with a stub detector and
  stream.
- No fake scanner, no upload, no backend change.

### Command palette and focus

- On a record detail, the palette's first group is "This Plant" (or Sowing, …) with the same
  record actions as the sheet. They are filterable.
- **Fixed (from M2):** palette group ids contained the label's spaces ("Saved views"), so
  `aria-labelledby` split into two broken references. Ids are now index-based.
- **Title focus ring (M4 finding).** Navigation still moves focus to the page or record heading
  (`tabindex="-1"`) for screen readers. `focusModality.ts` records the last input on
  `<html data-input>`, and those headings draw the ring only after keyboard use. Verified in
  UAT: on direct load the heading is focused with no ring; after a key press the ring is solid.
  Interactive controls are unaffected.
- Keyboard-only path verified in UAT: Record (rail), Enter, Add Journal entry, Enter. This lands
  in the real Add entry dialog with focus inside it and a clean address.

### Findings carried into release acceptance

| Finding | M5 outcome |
| ------- | ---------- |
| Record detail not distinctive enough for final adoption | **Open, M6.** M5 was interaction work. |
| Title focus ring shows on direct load | **Fixed** (above). |
| Lineage with real multi-step and partial chains | **Partly.** UAT has a recorded two-step chain (Seed lot → Sowing → Plant and Plant group). Multi-step, reversed, unlabelled and missing-source cases are covered by `LineageStrip` and `LineagePanel` tests. Creating a three-step UAT chain (a Plant extracted from a group) is **open for M6**. |
| Details with only the new header | **Open, M6** (Harvest, Stored material, Location, Identity, Supplier, Order overviews). |
| Plant Journal loaded twice | **Investigated, open for M6.** The Overview timeline and the Journal tab each call `GET …/events`, never concurrently (only one panel is mounted). Deduplicating without changing API behaviour means sharing one fetch per record version, either a request cache keyed by record and `updated_at` and invalidated by Journal mutations, or the detail owning the list and passing it down. Both touch `EventJournal`'s mutation and refresh paths, so it is deferred rather than rushed. |
| Plant provenance partly duplicates lineage | **Open, M6.** |
| Mobile directory headers too tall | **Open, required, M6.** |
| StoredMaterial focus test | **Resolved, with evidence.** The test dispatched `hashchange` and asserted focus synchronously, but the section registers its listener in a passive effect that may not have flushed. The effect also focuses from the current hash when it registers, so the app is not affected. Before: 2 failures in 30 isolated runs (M4). After waiting for focus (same assertion: the exact record must receive it): 40/40. Not classified as pre-existing, because main was not run. |
| New: `MediaScreen.test.tsx` "detail return preserves filters and page…" | Failed once in one full-suite run; 0 of 30 isolated runs; `frontend/src/media` is untouched on this branch. Tracked, not classified. |

### Verification

| Check | Result |
| ----- | ------ |
| Typecheck, ESLint (0 warnings), Prettier, production build | pass. Main JS 263.1 → 269.9 kB (gzip 81.6 → 83.4 kB): Record sheet, camera reader, label validation |
| Full frontend suite | 1203/1203 on the committed tree. One earlier full run had the single MediaScreen failure above. |
| New tests (26) | Record sheet (5): context actions, chooser to germination form, label refusal and scanner Enter, camera offered only with support, scan → navigate and release camera, foreign code refused. `labelRoute` (16): accepted and refused shapes. `recordContext` (3). Focus modality (1). `entry=new` end to end through `App` (1). |

### Evidence (UAT Preview serving `e593c50`)

| Set | Images | Probe |
| --- | ------ | ----- |
| Interactions: direct-load focus, Record sheet on a Plant (desktop, phone, phone dark) and on Today (phone), `entry=new` Journal and germination, contextual palette, refused label, keyboard-only flow | 10 | 0 console errors; no sheet, bottom-bar or rail control under 40px |
| Field Ledger light: Plant, Plant group, Sowing, Seed lot details, Today, Seeds at three widths | 24 | 0 console errors; 0 below target |

Manifests are in [`m5/`](m5/).

### Deviations

1. **Record, not "Scan" and "Record" as separate bottom-bar items.** Scanning only exists where the
   browser supports it, so it lives inside Record rather than as a control that would be dead on
   most devices.
2. **No inline quick-capture forms.** The sheet routes to the record's own forms, as above.
3. **No motion added.** Sheets and dialogs keep their existing behaviour. Motion stays a polish
   item for M6, with reduced-motion respected.

## M6B: Specimen Sheet implementation

Direction A (Specimen Sheet) was approved in M6A, with Direction C's date-precision grouping.
Commits `81ba6b9`, `85b726a`, `659e053`, `70810bb`, `353ea39`, plus the checkpoint commit (MediaScreen test hardening, docs and manifests). Frontend only:
no backend, API, schema, route or auth change. The design reference is the M6A canvas
(https://claude.ai/artifact/B3TWNaSJvnjxUz2GmdXRCx).

### What was built

| Part | Implementation |
| ---- | -------------- |
| Specimen Sheet layout | `DetailHeader` specimen mode with `SpecimenPlate` and `SpecimenLabel` (CollectionUI, `specimen.css`). The detail page is a size container. At 50rem and wider the plate and label float in a left column (18rem, or 24rem from 72rem) and every later sibling keeps a matching start margin, so tabs and panels stay in the right column. At medium widths (a tablet with the panel open) plate and label sit side by side above the record. On phones there is one column: the plate is a 3:2 banner and the label follows the content. |
| Specimen label | One ruled, double-framed fact list per record. DetailSummary metrics move into it unchanged, keeping their list's accessible name ("Current inventory", "Current Sowing state", …) and the Order price note. Missing values that domains already write ("Not recorded", "Unknown", "Quantity unknown") are set in italics as unknown. |
| Record types | Plant and Plant group (label replaces At a glance, Managed group and Origin and provenance), Seed lot, Sowing, Harvest, Order, Supplier (plate and label), Location (label only: locations have no images). Stored material opens inside its Harvest (`?inventory=`), so it shares the Harvest sheet. **Botanical identity keeps its reference-hub composition** (see deviations). |
| Lineage sequence | `LineageStrip`, now with step cards. Each step's relationship to the one before is written as text and named only from the recorded kinds: Seed lot → Sowing "sown as", Sowing → Plant or Plant group "grown into", Plant group → Plant "extracted", Plant or Plant group → Seed lot "produced". |
| Almanac | `RecordTimeline`, renamed Almanac, gains a month axis (`aria-hidden`; at most twelve months covering today and every dated entry). Recorded days are dots, month-only and year-only dates are spans, and planned items are hollow dashed rings, with overdue in the warning colour. Undated entries are not drawn, and a visible sentence says so. Recorded entries are grouped by the precision actually recorded ("November 2026", "September 2026 · day not recorded", "2024 · month not recorded", "Date not recorded"). The planned lane, links and History footnote are unchanged. Geometry and grouping are pure functions in `timeline/almanac.ts`. |
| One Journal request (R2) | `JournalScope` and `useJournalReader`. Inside a Plant or Plant group view, the Overview Almanac and the Journal tab share one response per record and version. Every Journal mutation and retry invalidates before re-reading. Leaving the record discards the scope. No API change. |
| Compact phone directories (R4) | At 40rem and below, the breadcrumb is hidden (the section strip names the section) and the page title is kept for assistive technology only. Search has its own row; view, Filters, Saved views and New become 44px icon buttons with unchanged accessible names. Filter chips scroll beside them, and pagination and Select records follow the list. Applied to DirectoryPage directories and to the Harvests workspace. |
| Today | Next work is grouped by target record: the record is named once (linked, with its kind and any non-active lifecycle) above its planned items. The schedule target carries no image, so no plates are shown. |
| Record sheet v2 | The open record's actions are tiles, the first being primary. One search across Plants, Plant groups and Sowings via the existing `/api/v1/search` with kind filters replaces the type radios and the two picker fields. Each result says which entry form it opens. |

### Verification

| Check | Result |
| ----- | ------ |
| Prettier, typecheck, ESLint (0 warnings), production build | pass. Main JS 269.9 → 285.0 kB (gzip 83.4 → 87.8 kB): the Specimen Sheet, Almanac, Journal scope and Record search |
| Full frontend suite on the final tree | 4 runs. 3 passed 1207/1207. 1 had one failure: SowingScreen "old Sowing propagation URL opens the canonical Lineage tab and empty summary". It then passed in 15 of 15 isolated runs and in the next 2 full runs. Its message was not captured, so it is **tracked, not diagnosed and not classified**. Sowing detail changed in M6B (strip, label), so it is not assumed unrelated. |
| New and changed tests | 1207 total. New tests: Almanac geometry, grouping and windows (3); the shared Journal request (1); lineage relationship text. Changed assertions only where the design moved a fact (progress.md lists them). |
| Captures at `353ea39` | 144 route captures in Field Ledger light, Field Ledger dark and Botanical: 12 routes (nine details, Today, Seeds, Plants) at 1440 (viewport and full page), 1024 and 390. 0 console errors; Field Ledger 0 below target. Botanical shows 40px controls at touch widths, from the original themes' geometry (M1). Plus 6 interaction captures. Manifests are in [`m6b/`](m6b/). |

### Real three-step lineage (R5)

The illustrative three-step chain from the Design was validated with real data. In the isolated
UAT Preview, a Plant was extracted from "Preview — Basil seedlings" through the existing
`POST /api/v1/plant-groups/{id}/extract-plant`:
- label "Preview — Basil seedling (extracted for M6B lineage check)";
- collection entry month-only 2026-10;
- id `01a1a834-8b02-72d9-bb23-61bef95dcca9`.

`GET /api/v1/plants/{id}/lineage` returns Plant group → Sowing → Seed lot. The sheet draws Seed lot
"sown as" Sowing "grown into" Plant group "extracted" This Plant, and the label shows the
month-only entry as 2026-10. **UAT data note:** the extraction lowered the group's quantity from
6 to 5 and added one Plant, so UAT Preview now differs from fixture v4 by this record. Reseeding
restores the fixture.

### Acceptance checklist (M6A findings R1–R13)

| # | Finding | Status | Evidence |
| - | ------- | ------ | -------- |
| R1 | Consistent Details across the ten types | **Met for nine; one deliberate exception.** Plant, Plant group, Seed lot, Sowing, Harvest (and Stored material inside it), Order, Supplier and Location use the sheet. Botanical identity keeps its reference-hub layout. | Captures `m6b-*`; deviation 1 |
| R2 | Duplicated Journal requests | **Met.** One request per record view and version. | `RecordTimeline.test.tsx` "share one Journal request"; Plant Journal deep-link test |
| R3 | Provenance repeating lineage | **Met.** The label states only the record's direct origin (kind of origin, and the direct source group or sowing as a link, so it stays reachable if lineage fails); indirect sources stay in the lineage sequence. | Plant tests; captures |
| R4 | Phone directory header height | **Met.** First record at 264–296px instead of about 580px (390×844); no header control under 44px. | Probe in progress.md; phone captures |
| R5 | Realistic multi-step lineage | **Met in UAT** (three steps, above); unit tests keep reversed, unlabelled and missing-source cases. | `three-step` captures |
| R6 | MediaScreen intermittent | **Hardened, not reproduced** (the separate SowingScreen intermittent was diagnosed and fixed in the M6 final pass). The final focus assertion raced a passive effect (same mechanism as the StoredMaterial race) and now waits for the same focus. 0 of 32 stressed isolated runs failed before the change. Still tracked. | progress.md |
| R7 | Real-device QR camera acceptance | **Open: needs the operator** (Android phone over HTTPS or localhost, printed label). | — |
| R8 | Almanac accessibility | **Met.** Axis `aria-hidden`; grouped lists carry every entry, its date text and its precision in words; the undated sentence is visible text; forced colours draw the marks. | `almanac.test.ts`, timeline tests |
| R9 | Phone action dock | **Not built** (deviation 3); no overlap risk introduced. | — |
| R10 | Muted text contrast on tints, both appearances | **Partly verified.** Uses the existing token pairs already measured in M1. The new pairs (muted on `--lineage-subtle`, label text on `--surface`) are token pairs from the M1 palette work; a measured pass of every new pair is still owed. | — |
| R11 | Screen reader, real zoom, forced colours | **Open.** Automated probes only; needs a manual pass. | — |
| R12 | Preserve functionality, APIs, permissions, themes | **Met.** No domain behaviour change; every existing suite passes; the six palette blocks remain pinned (token test). Assertions changed only where the design intentionally moved a fact (listed in progress.md). | Test runs |
| R13 | Six themes on the new layout | **Met.** Specimen components use tokens only; Botanical captures show the sheet. | `m6b-*-botanical` |

### Compared with the M6A artboards (material deviations)

1. **Botanical identity** keeps its reference-hub layout (taxonomy, maps, media, collection
   footprint). Its page styles conflict with the floated plate column, and an identity is not a
   specimen. Making it a sheet needs a dedicated pass.
2. **Plates use thumbnails.** The API exposes only the thumbnail rendition for collection
   photos, so a large plate can look soft. A larger rendition would need a backend proposal.
3. **No phone action dock.** Header actions stay in the page as before. The dock is a later
   refinement.
4. **No thumbnails in Today's groups** (schedule targets carry no image) and **no recent-record
   chips** in the Record sheet (the shell's Recent list holds pages, not entry targets).
5. **Location has no plate** (no location imagery).
6. **The Journal tab's own list is not regrouped yet.** The Almanac on Overview uses the
   precision groups; regrouping EventJournal's editable list is left for a follow-up to avoid
   changing its editing interactions now.

## M6 final refinement and visual review

Frontend only, on top of M6B. This is a refinement and review checkpoint, not M7.

### Live UAT review environment

- **Address:** http://localhost:15174 (isolated Compose project `florabase-uat-preview`; it serves
  this worktree's frontend source live).
- **Sign in:** the synthetic UAT fixture owner `preview` / `preview`. It is not a personal account,
  and the data is synthetic.
- **Theme:** Field Ledger is the branch default. Switch light and dark from the theme control in
  the panel footer or the account sheet.
- **Suggested review path:**
  1. Today.
  2. Collection → Plants → "Preview — Basil mother plant": dense record, photo, two-step lineage,
     Almanac with month-only and undated entries.
  3. "Preview — Basil seedling (extracted for M6B lineage check)": real three-step lineage.
  4. Seeds → "Preview — Aloe unknown stock": sparse record, unknown quantity.
  5. Sowings → "Preview — Spring basil tray".
  6. Explore → Botanical identities → "Aloe vera": reference sheet.
  7. Any record's Journal tab: precision periods.
  8. The same pages at phone width, with the Record button.
- The UAT data equals fixture v4 plus the M6B extracted Plant (the Basil seedlings group is
  now 5 plants).

### Representative screenshots

`.florabase-next-evidence/m6-final-review/`, 16 images, numbered for review order:

| # | View |
| - | ---- |
| 01, 03 | Plant, desktop, light and dark |
| 02 | Real three-step lineage, desktop |
| 04 | Seed lot (purchased, linked Order), desktop |
| 05 | Sowing, desktop dark |
| 06 | Botanical identity reference sheet, desktop |
| 07 | Today, desktop |
| 08, 09 | Plant (light) and Seed lot (dark), tablet 1024 |
| 10, 11 | Plant (light) and Sowing (dark), phone 390 |
| 12 | Seeds directory, phone (compact header) |
| 13 | Botanical identity, phone dark |
| 14 | Journal tab with precision periods |
| 15 | Plant in forced colours |
| 16 | Record sheet v2, phone |

The full route sets are `m6b-353ea39-*` (144 images; manifests in [`m6b/`](m6b/)).

### Visual review against the approved Direction A

| Area | Finding | Action |
| ---- | ------- | ------ |
| Composition | The plate and label column with the record flowing on the right matches Direction A on Plant, Plant group, Seed lot, Sowing, Harvest, Order and Supplier. The Workbench panel narrows the right column at 1440 compared with the artboard (which had a rail only). | Kept; the panel can be hidden and the layout adapts. |
| Typography | Label values were all in the monospace data face, so place paths and links broke into narrow fragments. | **Fixed:** links and paths use the UI face; recorded values (dates, counts, quantities) stay in the data face. |
| Image rendering | The plate shows the API's thumbnail scaled up, which looks soft or pixelated. This is the weakest point against the artboard. | Approach documented below; not changed (it needs an additive backend rendition). |
| Almanac | With little dated data (two or three months), the axis is sparse; on Seed lot it sits in a narrow second column. | Accepted for now. The axis only covers the dated range, so it never pads the window with invented months. |
| Consistency | Botanical identity had no shared treatment. | **Done:** reference sheet (below). |
| Whitespace | No excessive gaps found in the review set; the old empty "At a glance" bands are gone. | — |

### Botanical identity: reference sheet

An identity is a reference, not a physical specimen, so it keeps its hub layout (record navigation,
overview, reference, taxonomy, maps, media, history). It now speaks the system's language: a framed
4:5 plate for the identity cover, the record-title serif scale for the scientific name, and a ruled
foot under the header. The styles are scoped to the identity page's own stylesheet.

### Journal precision periods

The Journal tab (EventJournal) now opens each recorded period with its precision, using the
Almanac's `precisionGroups`: "November 2026", "March 2025 · day not recorded",
"2024 · month not recorded", "Date not recorded". The period is plain text at the top of the
period's first entry, so the list keeps one item per entry, filters keep working, and screen
readers read the period with that entry. Groups follow the API's order and never re-sort.
Covered by the Plant Journal test.

### Evaluated, not implemented

| Candidate | Decision |
| --------- | -------- |
| Phone action dock | **Not added.** The record's header actions are already on the first screen on phones, and the bottom bar's Record button opens the open record's own actions (Journal entry, germination, lineage, label) within thumb reach. A dock would duplicate that and compete with the bottom bar. |
| Today thumbnails | **Not added.** Schedule targets carry no image, so thumbnails would need one extra request per record on every Today load. |
| Record sheet recent chips | **Not added.** The shell's Recent list holds sections, not records; record-level recents would need new client tracking for a small gain, since the sheet already leads with the open record and has search. |

### Accessibility evidence

**Automated (performed):**
- **Contrast**, WCAG 2.x formula, for every colour pair the new components use, in Field Ledger
  light and dark:
  - all text pairs ≥ 5.58:1 (minimum: muted on the lineage tint, light);
  - lineage text on its tint 6.18:1 light, 6.90:1 dark;
  - non-text marks ≥ 4.08:1 (requirement 3:1); the overdue ring is 4.48:1 in light.
- **Keyboard:** 45 Tab presses through a Plant record at 1440. Every stop shows a visible focus
  indicator (the one exception is focus returning to `<body>` at the end of the document). The order
  is DOM order: back bar, breadcrumb, specimen label, then title, actions, lineage, tabs and panel.
  Titles focused by navigation draw the ring only after keyboard use (M5).
- **Browser zoom (emulated by CSS viewport):**
  - 200% of 1440×900 (720 px wide): no horizontal overflow on Plant, Sowing, Seeds or Today.
  - 400% of 1280×1024 (320 px): no element extends beyond the viewport. Seeds reports 16 px
    `scrollWidth − clientWidth`, which is the 16 px classic vertical scrollbar of the test browser,
    not content overflow.
- **Forced colours** (Chromium `forced-colors: active`): Plant renders with no console errors;
  Almanac marks use `CanvasText`. Screenshot 15.

**Manual (not performed here, owed):** a screen reader pass (NVDA or VoiceOver), real browser zoom
on a physical display, Windows High Contrast themes on real hardware, and touch on physical phones.

### Larger specimen images: recommended approach

Today the collection photo contract (`PrimaryPhotoResponse`) exposes only `thumbnail_url`. The
original image is served by `GET /api/v1/collection-photos/local/{photo_id}`, but loading
originals into every plate would download full camera files (often several MB) for a
24rem-wide frame, so the frontend does not do that.

Recommended, as a **separate backend proposal** (not implemented):
1. Add a bounded *display* rendition, generated lazily and cached like thumbnails. For example,
   1200 px on the long edge, JPEG or WebP, with the same authorization and cache headers.
2. Expose it additively as an optional `display_url` on `PrimaryPhotoResponse`. Existing clients
   are unaffected.
3. Frontend: render the plate as
   `<img src={thumbnail_url} srcset="{thumbnail_url} 320w, {display_url} 1200w" sizes="(min-width: 72rem) 24rem, (min-width: 50rem) 18rem, 100vw">`.
   The browser then fetches the display rendition only for large or dense screens, and phones
   keep the thumbnail.
4. External references keep their cached thumbnail until the same rendition exists for them.

### SowingScreen intermittent: diagnosed and fixed

- **Observed:** "old Sowing propagation URL opens the canonical Lineage tab and empty summary"
  failed once in 8 full-suite runs and never in 15 isolated runs. Four further full runs with
  failure output preserved all passed, so the original message was never captured.
- **Mechanism (in code from main, `a36c6cf`):** the Sowing screen sets the Lineage tab
  synchronously, but it rewrote the legacy `?tab=propagation` address in a *passive* effect. The
  test asserts the canonical address right after the selected tab appears.
- **Proof:** a temporary probe (not committed) rendered the screen 150 times and found the tab
  selected while the address still read `?tab=propagation` in **2 of 150** renders.
- **Fix (app, not test):** the rewrite now runs in `useLayoutEffect`, inside the same commit and
  before paint, so the address and the selected tab never disagree. The probe then showed
  **0 of 300**. The test is unchanged and as strict as before.
- **Classification:** the mechanism is in code that predates this branch. It is still not called
  pre-existing, because it was not reproduced on main. M6B added asynchronous work to Sowing
  detail (the lineage strip), which may have changed the timing.

### Final verification and a newly observed intermittent

- Prettier, typecheck, ESLint and the build pass (main JS 285.0 kB, gzip 87.8 kB).
- Full suite: four runs before the Sowing fix all passed 1207/1207. On the final tree, run 1
  passed 1207/1207. Run 2 had one failure in a different test: App "identity section keyboard
  navigation retains browser Back and Forward boundaries". The preserved message is a hash
  mismatch that the reporter truncates (both values begin `#/identities/0190…`), so which of
  the test's three `waitFor` hash checks failed is unknown. It passed 20 of 20 isolated runs.
- This branch does not change identity behaviour (only identity CSS in this pass), and the test
  is unchanged. A plausible mechanism is jsdom's asynchronous history traversal racing
  `waitFor`'s 1 s default under full-suite load, but **it is not proven**. It is tracked, not
  classified, and not "fixed" by loosening the test.

### Real-device QR camera

**Pending operator acceptance on Android** (HTTPS or localhost, a printed Florabase label). Not
claimed as tested.

## M7: side-by-side evaluation, regression review and recommendation

Commits `2d95552` (refinements) and `4571f03` (fixes), plus the M7 checkpoint (docs). Main
`d94f275` is still `origin/main`, the branch's merge base (read-only check). The review package
is [INDEPENDENT-REVIEW.md](INDEPENDENT-REVIEW.md).

### Visual refinements

- **Lineage:** the sequence never wraps onto a second row. Wider screens get one row that scrolls
  sideways when it does not fit; phones get a vertical top-to-bottom sequence with "Full lineage"
  below it. Verified with the real three-step record.
- **Tablet:** the name and actions come first, then the plate and label side by side.
- **Phone:** breadcrumb, name, identity, actions and lineage come before a shorter 16:9 image
  banner; the label follows the content.
- **Almanac:** the axis appears only with at least three dated entries across two or more months.
  Otherwise the precision-grouped lists stand alone.

### Regressions found and fixed in M7

1. **Phone directories were 16 px too wide** (Seeds, Plants, Sowings and other DirectoryPage
   directories). This pushed the fixed bottom bar partly off-screen, so the Collection workspace
   sheet could not be tapped in the capture interaction. **Introduced in M6B** by the visually
   hidden title (absolute, no inset). Fixed; all 14 phone routes now measure 390 px with the bar
   fully visible. This also corrects the M6 record, which attributed the 16 px at 400% zoom to a
   scrollbar; it was this overflow.
2. **Taxonomy "About taxonomy search" disclosure was 32 px.** Pre-existing on main (`ee34874`);
   now 40 px.

### Functional comparison against main `d94f275`

Evidence:
- **(a) Test inventory.** Main has 894 uniquely named tests; the branch has 937. Eight main test
  names are absent:
  - seven are the replaced sidebar, Quick add and Dashboard-navigation tests (superseded by the
    Workbench shell and Today tests);
  - one was renamed and extended in M1 (contrast pairs now cover the two Field Ledger sets).
  - No other behaviour test was removed, and the full suite passes.
- **(b) Route sweep.** All 37 main routes are reachable on the branch at desktop, tablet and phone,
  in light and dark, with 0 console errors and 0 controls under target in Field Ledger. The only
  absent capture key is the old mobile "More" menu, replaced by workspace sheets.
- **(c) Workflow smoke.** On the writable synthetic UAT: 10/10 checks passed.
  - Created a month-precision Journal entry through the record's own form (`entry=new`).
  - Saw it under "October 2026 · day not recorded" in the Journal and in the Overview Almanac.
  - Deleted it; the record's event count was restored.
  - Record sheet search found a Sowing and opened its germination form.
  - A foreign label link was refused; a label link opened its Plant.
  - No console errors.

| Area | Main | Florabase Next | Status |
| ---- | ---- | -------------- | ------ |
| Navigation | Grouped sidebar, mobile Home/Seeds/Sowings/Plants + More | Rail workspaces, context panel, Saved views, Recent, palette, mobile workspace sheets | All destinations kept; one extra click across workspaces (mitigated by Recent and the palette) |
| Record CRUD (all types) | Detail pages and edit dialogs | Same domain forms and dialogs inside the Specimen Sheet | Unchanged behaviour (suites pass) |
| Saved Views | Per-directory dialog | Same dialog; also listed in the panel (5 + "Show all") and the palette | Improved discoverability |
| Bulk actions | Select records, bulk move | Unchanged; on phones Select follows the list | Kept |
| Media | Media directory and detail | Unchanged behaviour; the plate shows the primary photo thumbnail | Kept |
| Lineage | Lineage tab, Origin rows | Lineage tab kept; header sequence with relationship text; label states the direct source | Improved (explicit only) |
| History | History page | Unchanged; the Almanac links History by kind | Kept (a per-record filter is a backend proposal) |
| Permissions and auth | Session, CSRF | Untouched; no backend change | Kept |
| Mobile capture | Journal Record menu → record route | Record sheet (contextual actions, record search, label links, guarded camera scan) → the record's own form | Improved |
| Filters and search | Directory filters, global search | Same; compact phone header; palette record search | Kept |
| Import / Export, Labels, Settings, Schedule, Maps | Existing pages | Same pages in the shell | Kept |
| Dashboard Quick add | In-page button | Global New menu | **Changed** (same routes, different place) |
| Page title "Dashboard" | — | "Today" (same route `#/dashboard`) | **Changed** |
| Themes | Six themes | Six unchanged (pinned by test) plus Field Ledger light/dark (branch default) | Kept |

### Comparison and recommendation

| Dimension | Original Florabase | Florabase Next |
| --------- | ------------------ | -------------- |
| Usability | Familiar flat sidebar; dense but text-heavy pages; Saved Views hidden in directories | Workspaces plus palette; records lead with identity, lineage and planned versus recorded; capture in two taps; compact phone directories. Cost: one extra click across workspaces and habit change |
| Visual quality | Coherent but generic administrative UI | Distinctive botanical identity (Field Ledger, Specimen Sheet, reference sheet); image softness from thumbnails |
| Accessibility | Established baseline | Automated contrast, keyboard, zoom and forced-colours evidence passes; focus ring only after keyboard use; **manual screen reader pass not yet done** |
| Maintainability | Large shared stylesheets with overrides | Shared components (Specimen, Almanac, Journal scope, shell) and scoped CSS; about 1,200 lines of dead CSS removed; some legacy sheets remain |
| Performance | Main JS 251.5 kB (gzip 78.1) | 285.0 kB (gzip 87.8); one Journal request per record view; no polling |
| Feature completeness | Complete | Complete; no backend capability added or removed; Quick add and the Dashboard title moved or renamed |

**Recommendation: adopt the full redesign, with specific blocking corrections.** Do not merge
until all of these are done:
1. an independent review against INDEPENDENT-REVIEW.md;
2. a manual screen-reader pass (and real zoom and high-contrast) on the Specimen Sheet, the shell
   and the Record sheet;
3. classification of the identity navigation intermittent;
4. operator acceptance of the changed habits (Quick add moved to New, "Today", workspace
   navigation);
5. canonical FULL and the normal delivery, only after the operator's approval.

Non-blocking but high priority:
- the display-image rendition proposal;
- Android QR acceptance before advertising camera scanning;
- bundle review.

If the operator prefers less change at once, the components integrate selectively in this
order, each as its own reviewed delivery:
1. Field Ledger tokens (opt-in theme);
2. the Specimen Sheet with Almanac and lineage sequence;
3. capture (Record sheet and entry links);
4. the Workbench shell.

The shell has the largest habit change and the lowest independent value, so it goes last.

## Separate proposals

1. **Per-record History filter.** The record timeline's System history lane needs
   `GET /api/v1/history` to accept a subject id (today it filters by `category`, `subject_kind`,
   `year` and `q` only). Until then the timeline links History filtered by kind. This is not
   implemented on this branch.

Anything else that would need a new endpoint or contract change is recorded here and is not
implemented on this branch.
