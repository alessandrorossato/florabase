# Florabase Next M8: final responsive QA remediation

**Input:** Codex Luna's second independent M8 review (functional PASS with nonblocking
findings; accessibility and mobile, page fit and scrolling PASS with findings; canonical
FULL NO-GO). Scope: only the two reproducible responsive corrections below. No theme,
Settings, authentication, backend, API, Docker or infrastructure change; no redesign.

## Commits

| Commit | Finding | Change |
| ------ | ------- | ------ |
| `177a01e` | P1 | Pinned phone header detected against the layout viewport; measured geometry published |
| `41a5c35` | P2 | 320px floor subtracts a classic scrollbar's width |
| `e5a430a` | P1, P2 | Real-browser geometry regression (`responsive_geometry.py`) |

## P1 — Schedule focus hidden by the sticky header

- **Cause:** the shell decided whether the phone header is pinned across the top by
  comparing its width with `window.innerWidth`. With a classic vertical scrollbar,
  `innerWidth` (390) includes the scrollbar while the layout viewport
  (`documentElement.clientWidth`) and the header are 375px, so the header was not
  recognised, `--wb-obscured-top` stayed 0 and `scroll-padding-top` resolved to 0.
- **Fix:** compare against the layout viewport (left edge at 0, right edge at
  `clientWidth`, shorter than half of `clientHeight`) and publish the measured geometry
  rounded up: the header's height, and the bottom bar's coverage of `clientHeight`. The
  bar was previously published from `offsetHeight`, which rounded 64.4px down to 64; it is
  now 65. A zero-size bar never counts.
- **Unit tests:** a shell laid out as a 390 window with a 375 layout viewport (classic)
  and with an equal one (overlay), plus a desktop side rail. On the old code the classic
  and overlay cases fail.

## P2 — Page-wide horizontal overflow at 320 CSS px

- **Cause:** `body { min-width: 320px }` is measured against the layout viewport, which a
  classic scrollbar narrows to 305px in a 320px window: 15px of page-wide overflow pushed
  "Account and settings" and the section strip past the edge.
- **Fix:** `min-width: calc(320px - (100vw - 100%))`: the window-width floor minus the
  scrollbar's own width (305px beside a classic scrollbar, 320px with overlay scrollbars,
  and still a floor below 320px windows). No `overflow-x: hidden`; History chips,
  workspace tabs, the section strip and bounded directory panels keep their own
  horizontal or vertical scrolling.

## Real-browser regression

`docs/design/florabase-next/responsive_geometry.py` runs in the pinned Playwright image
against UAT Preview. Playwright's headless default (`--hide-scrollbars`) hides classic
scrollbars, which is why earlier checks missed both findings; this check launches
Chromium **with** classic scrollbars and separately with mobile overlay scrollbars, and
asserts on a tall page which model is active (scrollbar width 15 vs 0).

- Viewports: 390×844, 320×640, 1280×800 at 200% (640×400) and 400% (320×200); desktop
  1440 and tablet 1024 with the Workbench panel expanded and collapsed (classic).
- Pages: Schedule Month, Theme (`#/settings`), Labels, Import / Export, History, Plants,
  Plant detail, identity detail.
- Measured: `documentElement.scrollWidth` vs `clientWidth`; controls outside the layout
  viewport and not inside an intentional scroller; `scroll-padding` vs the pinned bars'
  measured coverage after scrolling; keyboard focus walked 25 steps forward and back,
  with the focused control's visible box (clipped by its own scrollers) against the bars
  (1.5px sub-pixel tolerance); on Schedule, the focused heading's bounds, that the
  document (not an inner element) scrolled, and Escape restoring the visible day.

| Run | Result |
| --- | ------ |
| Unchanged candidate `61baa3f` | **74/96**: fails every classic case at 390 (P1), 320 and 400% (P2) |
| Committed fix `e5a430a`, light | **96/96** |
| Committed fix `e5a430a`, dark | **96/96** |

### Schedule Month, November 4 selected (heading bounds, y)

| Condition | innerWidth / clientWidth | Header ends | scroll-padding-top | Heading before | Heading after | Escape |
| --------- | ------------------------ | ----------- | ------------------ | -------------- | ------------- | ------ |
| Classic 390 | 390 / 375 | 117 | 0 → 117 | **36–60 (hidden)** | 153–177 | day 4, visible |
| Classic 320 | 320 / 305 | 117 | 117 | 153–177, page scrollWidth 320 | 153–177, scrollWidth 305 | day 4, visible |
| Classic 400% (320×200) | 320 / 305 | not pinned | 0 | 36–60, scrollWidth 320 | 36–60, scrollWidth 305 | day 4, visible |
| Overlay 390 / 320 | equal | 117 | 117 | 153–177 | 153–177 | day 4, visible |
| 200% (640×400), both | 640 / 625 or 640 | not pinned | 0 | 37–61 | 37–61 | day 4, visible |

Evidence: `.florabase-next-evidence/m8-responsive/` (before and after JSON, Schedule
screenshots per condition, `p1-p2-before-after.png`).

## Other checks on `e5a430a` (tree `dcdfac2`)

- Prettier, TypeScript, ESLint (`--max-warnings 0`) and the production build pass.
- Full frontend suite **1220/1220 in three consecutive runs** (1217 plus three new tests).
- Captures: 155 light and 155 dark (`.florabase-next-evidence/m8r-e5a430a-field-ledger-{light,dark}/`):
  0 console errors, 0 controls below target, 0 state failures; identical images only
  between a desktop page and its own full-page image.
- Backend, generated API, Compose, scripts: no diff from `main`.

## Observation (pre-existing, not changed)

At 320×640 the Plants directory's bounded record list (its own 320px scroller) can hold
a focused card taller than the list (391px), so part of the card is clipped by the list
itself. Nothing is under the pinned header. Recorded for review, outside this scope.

## Still open

- F6 Geography stays on the watch list (no speculative fix).
- Manual screen-reader, physical zoom, Windows high-contrast and real-touch passes, and
  Android QR scanning, as before. Safari/Firefox scrollbar models were not run here;
  `100vw` includes a classic scrollbar in both, as in Chromium.
