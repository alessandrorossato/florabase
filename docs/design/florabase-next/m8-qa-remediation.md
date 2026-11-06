# Florabase Next M8: independent QA remediation

**Input:** Codex Luna, `FLORABASE-NEXT-M8-INDEPENDENT-QA.md` (frozen candidate `19dfd8a`,
tree `47fc856`). Functional QA and Design & UX: PASS WITH FINDINGS; canonical FULL: not
authorised. This is a focused remediation cycle, not a redesign.

**Candidate:** executable commit `61867c0` (tree `ec3fd56`); this record and the progress
entry follow in a documentation-only commit. No backend, API, schema or infrastructure
change. Canonical FULL not run; nothing pushed, delivered or merged.

## Commits

| Commit | Finding | Change |
| ------ | ------- | ------ |
| `a9bf9e5` | F2 | Location hierarchy test waits for its data (test only) |
| `33f427b` | F3 | `TaskDialog` returns focus in the commit that removes it |
| `9744409` | F1 | Phone Schedule day panel: focus, announcement, scroll, Escape; shell keeps scrolled/focused content clear of pinned bars |
| `b164650` | F4 | History fact type chips form one scrolling row on phones |
| `61867c0` | F7 | Identity title takes focus in the commit that mounts it |

## Reconciliation of every finding

| ID | Finding | Status | Evidence |
| -- | ------- | ------ | -------- |
| F1 · P1 | Phone Schedule day inspector not discoverable or announced | **Fixed** | Below; 4 new tests; real browser at 390, 320 and 1280×800 at 400% |
| F2 · P1 | Location hierarchy fails under shuffle seed 3 | **Fixed (root cause: test synchronization)** | Deterministic before (alone and seed 3); passes alone, seed 3 and the final seed sweep |
| F3 · P1 | Schedule pending-save intermittent | **Fixed (root cause: real focus gap, not duplicate mutation or lost work)** | 2/48 before → 80/80 after under the same stress; regression test fails 5/5 before |
| F4 · P2 | History phone chips take three rows | **Fixed** | Chip block 148 → 56 px; first fact 92 px higher; shared state verified |
| F5 · P2 | "Three full passes" spanned two commits | **Fixed (evidence now commit-specific)** | Three consecutive full runs on `61867c0` itself |
| F6 · P2 | Geography record states failed once at seed 18 | **Verified nonblocking; not reproduced** | Seeds 17–19 pass; 80/80 under 8-way contention; final sweep. Not claimed fixed |
| F7 · Advisory | Identity Back/Forward intermittent | **Fixed (reproduced, root-caused)** | Seed 31 under load; 9/128 before → 80/80 after under the same stress |
| Design: Journal photo scale | Consider a larger mount | **Deferred** | Advisory only; current provenance and size retained |
| Design: History table semantics | Validate with assistive technology | **Deferred** | Needs a manual screen-reader pass (below) |
| Design: Settings / QR | Real-device scan | **Deferred** | Needs a physical Android device |
| Limitation | Manual screen reader, zoom, high contrast, touch | **Partly addressed; still open** | Automated keyboard, touch-emulation and 400%-zoom checks done; manual passes not available here |

Nothing remains blocking in the reviewer's sense from this cycle's findings; the
manual checks above remain open and are listed, not claimed.

## F2 — Location hierarchy under shuffle seed 3

- **Reproduced** exactly: `vitest run src/App.test.tsx --sequence.shuffle --sequence.seed=3`
  fails with "Unable to find … list "Location hierarchy"" at the synchronous `getByRole`
  after navigation; `main` was empty. Running the test **alone** also fails deterministically.
- **Cause:** the list renders only after the locations request resolves. In default order an
  earlier Locations test has already resolved the lazy `LocationScreen` chunk, so the data
  arrives inside the click's `act()`. When this test is the first Locations test, the chunk
  and data land after the click returns. A shared module cache (`React.lazy`) leaked
  between tests; no product behaviour is wrong.
- Rejected fix: eagerly importing every section module (still failed — `lazy` suspends on
  its first render regardless).
- **Fix:** wait for the list (`findByRole`), then assert that nested locations start
  collapsed, a check only meaningful once data exists. Nothing weakened.
- **Main:** the test and the lazy boundary are byte-identical on `main` (`d94f275`); not
  executed there (no isolated `main` dependency environment), so "pre-existing" is by source.

## F3 — Schedule pending save

- **Reproduced** 2 of 48 shuffled runs under 6-way contention (seeds 404 and 108), and 1 of
  10 runs of the test alone. Full output retained. The failing assertion was always the
  last one, `expect(trigger).toHaveFocus()`; focus was on `<body>`. Every pending-save
  guarantee before it passed in every run: one `writeActivity` call, Escape and backdrop
  ignored while pending, no discard prompt, a second submit ignored.
- **Mechanism, measured:** a probe recorded focus at the moment the dialog left the DOM:
  `<body>` in 48 of 48 runs. React commits the removal first; the `TaskDialog` cleanup that
  returns focus is a passive effect flushed in a later scheduler task (`setImmediate`, React
  scheduler 0.27.0). `waitFor` resolves on the DOM mutation and RTL 16.3.3 then drains with
  `setTimeout(0)`; Node's ordering of the two is not fixed, so the assertion sometimes ran
  inside the gap. Browsers have the same one-task gap after an asynchronous close.
- **Classification:** a real but brief product focus gap (keyboard or screen-reader users
  could land on the document), surfaced by test timing. No duplicate mutation, lost work
  or wrong state was ever observed.
- **First attempt rejected:** moving the whole `TaskDialog` effect to a layout effect made a
  Taxonomy test fail deterministically. Traced: React records the focused element before a
  commit and restores it afterwards (`flushMutationEffects`), undoing focus changes made in
  layout cleanups during an *update* (Taxonomy's modal-to-inline switch).
- **Fix:** an additional unmount-only layout cleanup that returns focus in the same commit,
  only when focus is inside a modal dialog being removed (the previously focused element
  then leaves the document, so React has nothing to restore). The existing passive effect
  is unchanged.
- **Evidence:** new `TaskDialog.test.tsx` fails 5/5 before and passes after; the unchanged
  Schedule test passed 80/80 shuffled runs under 8-way contention afterwards.

## F7 — Identity Back/Forward (found during this cycle's sweep)

- **Reproduced** at seed 31 of a 40-seed `App.test.tsx` sweep while other stress jobs ran;
  seed 31 alone passed 4/4. Under 8-way stress of the test alone: 3/64, then 6/64 with
  tracing. Failure: after End on Overview the address never gained `?tab=history`.
- **Trace:** the test focused Overview, then `BotanicalIdentityScreen`'s mount effect moved
  focus to the record title, so End landed on the heading.
- **Fix:** the title focus moves from a passive to a layout effect (a layout-effect mount
  runs after React's focus restoration, so it sticks). Same behaviour without the window.
  80/80 under the same stress; the test is unchanged; the effect is identical on `main`.

## F6 — Geography dedicated record states

Not reproduced: seeds 17, 18, 19 pass; the test passed 80 of 80 runs under 8-way
contention; the final seed sweep is below. The original failure output was not retained in
M8B. It belongs to the same class as F3 and F7 (assertions racing deferred effects), but
without a reproduction no cause is claimed and it is **not** reported as fixed. Residual
risk: low; it stays on the watch list.

## F1 — Phone Schedule day panel

Selecting a day in Month on a phone (touch or Enter/Space):

- focus moves to the panel's date heading; the region is labelled "Scheduled work,
  ‹date›" and shows a "Scheduled work" eyebrow, so the date and purpose are announced;
- the panel scrolls into view (`block: nearest`, instant under reduced motion), clear of the
  pinned header and bottom bar;
- Tab reaches Close day, then Add activity and each row; Escape or Close day closes it and
  returns focus to the originating day; month, filters and selected date are unchanged;
  Escape inside a row's ⋯ menu closes only the menu;
- opening from the address alone (reload, shared link) never moves focus or scrolls.

Found while verifying, fixed in the same commit:

- the sticky phone header (117 px) covered the scrolled-to panel; the shell now publishes
  the area its pinned header and bottom bar cover (`--wb-obscured-top/bottom`, 0 where
  nothing is pinned) and the document uses it as `scroll-padding`, so scrolled-to and
  keyboard-focused content anywhere stays clear of both;
- at 1280×800 and 400% zoom (320×200 CSS px) the pinned bars left about 20 px for content;
  on short phone-width viewports they no longer pin.

Real browser (Chromium 1.48, UAT Preview):

| Viewport | Heading after open | First action | Bottom bar | Return on close | Horizontal overflow |
| -------- | ------------------ | ------------ | ---------- | --------------- | ------------------- |
| 390×844 touch | y 147–171, below header (117) | Add activity y 182–226 | top 780 | day 4 focused, address unchanged | 0 |
| 390×844 keyboard | focused, focus ring visible | Tab → Close day → Add activity | top 780 | Escape → day 4 | 0 |
| 320×640 | y 145–169 | y 234–278 | top 576 | day 4 | 0 |
| 1280×800 @ 400% (320×200) | y 28 (nothing pinned) | y 117–161 | in flow | day 4 | 0 |

Below 320 CSS px (for example 390 px at 200% zoom) the whole app scrolls horizontally:
`body { min-width: 320px }` is a deliberate app-wide floor, unchanged and also on `main`.

Evidence: `.florabase-next-evidence/m8-qa-remediation/f1-day-panel/`.

## F4 — History phone chips

- One horizontally scrolling row at ≤ 48rem: the chip block is 56 px instead of 148 px;
  the first fact moves from y 570 to 478 at 390 px and 590 to 498 at 320 px (before
  measured on the same page with the M8 wrapping restored).
- All seven chips stay in the row and in the tab order with unchanged `aria-pressed`
  semantics and the same filter update, so chips, the Filters drawer, Saved Views and the
  URL keep one state (existing shared-state test unchanged; drawer verified in the browser).
- A fade marks each side that has more chips; the thin scrollbar remains for pointer users.
  A focused chip is scrolled fully into view (the browser left a partly clipped chip under
  the fade); a selected chip from the address starts in view without moving the page.
  44 px touch targets. More-menu alternative rejected: it would hide categories.

Evidence: `.florabase-next-evidence/m8-qa-remediation/f4-history-chips/`.

## Tests changed

- `App.test.tsx`: the Location hierarchy test waits for data (F2). No assertion removed.
- `ScheduleScreen.test.tsx`: two phone-panel tests look the region up by its new name
  ("Scheduled work, ‹date›"); four new tests (touch focus and return, keyboard only,
  address-opened panel, Escape in a row menu).
- New `TaskDialog.test.tsx` (focus at removal after an asynchronous close).
- `HistoryScreen.test.tsx`: one new test (overflow cues; every chip stays in the row).
- The pending-save, identity Back/Forward and Taxonomy tests are unchanged.

## Final verification on `61867c0`

All on the committed, clean executable tree `61867c0` / `ec3fd56` (Quality environment):

- Prettier, TypeScript, ESLint (`--max-warnings 0`) and the production build pass.
- Full frontend suite: **1217/1217 in three consecutive runs** on this tree (1211 before, plus
  six new tests).
- Shuffled order under contention: `App.test.tsx` seeds 1–40 in four parallel copies,
  **40/40** (includes seed 3 for F2, 18 for F6, 31 for F7); Schedule plus `TaskDialog`
  tests, 40 shuffled seeds in four further parallel copies, **40/40**.
- Captures: 155 per appearance (light and dark; the M8 set of 118 plus 37 desktop
  full-page images): 0 console errors, 0 controls below target, 0 state failures. Identical
  images occur only between a desktop page and its own full-page image where the page fits
  one viewport; Plant detail and lineage remain distinct.
  `.florabase-next-evidence/m8qa-61867c0-field-ledger-{light,dark}/`.
- Phone interactions in light and dark: `.florabase-next-evidence/m8-qa-remediation/`.
- Backend, generated API, Compose and scripts: no diff from `main`.
- UAT Preview data and the other environments were read only; nothing imported, reseeded
  or reset. Canonical FULL not run.

## Remaining risks and manual checks

- Manual screen-reader (VoiceOver/TalkBack/NVDA), physical zoom, Windows high-contrast and
  real-touch passes were not available; automated keyboard, touch-emulation, focus, reflow
  and 400%-zoom checks stand in for them, not replace them.
- Android QR scanning on a physical device remains unverified.
- F6 is not reproduced, so it is not claimed fixed.
- The F2 comparison with `main` is by identical source, not by execution.
- The shell scroll-padding applies app-wide on phones; captures show no regressions,
  but other screens were not individually keyboard-walked at 390 px.
