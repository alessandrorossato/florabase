# Florabase Next M8 final UX: implementation record

**Status:** experimental, committed locally, stopped at the final M8 acceptance checkpoint.
No canonical FULL, push, delivery or merge. Backend diff against `35f9eb2`: empty.
Approved design: canvas page 6 ([proposal](m8-final-ux-proposal.md)) with operator decisions
D1 (History chips) and D2 (Month inspector on selection).

## Commits

| Commit | Content |
| ------ | ------- |
| `15dc04f` | Settings: Theme, Labels (QR destination), Import / Export |
| `c1146b4` | Journal as a botanical field journal |
| `7f4a222` | History as an audit trail with fact type chips (D1) |
| `5eb5691` | Schedule Agenda lanes, Month cells, day inspector (D2) |
| `0127aa0` | Fix: History chips met the 40/44px target only after the capture probe flagged 36px |
| `784c975` | Fix: legacy Settings QR link lost its dialog under React development double-invocation |

## What changed

- **Settings.** The Settings workspace reads Theme · Labels · Import / Export (desktop panel
  and phone account sheet share the list, so no duplicates). `#/settings` stays the Theme
  route: palette and appearance only, no server request. The QR destination is a section at
  the top of Labels (purpose, value or warning, existing dialog, validation and persistence;
  printing stays disabled while unset). `#/settings?tab=general` opens Labels with the QR
  dialog and its field focused, via `#/labels?qr=edit`, which Labels removes once open.
- **Journal.** Entries under headings of the precision they were recorded with (order and
  precision unchanged); the note as body text in the serif; the record's own primary photo,
  captioned "Plant primary photo" (or Plant group / Harvest), only when one exists. Titles,
  links, filters, Saved Views and Record actions unchanged.
- **History.** Desktop ≥ 64rem: a ruled table (When · Fact type · What happened · Record ·
  Related · State) built by placing each row's existing elements in columns. Occurred dates
  show "occurred · day/month/year"; recorded dates already say "Recorded …". Fact type chips
  use the same category state, helper and URL update as the Filters drawer (test proves it).
- **Schedule.** Agenda lanes carry a count and, for Overdue, "Planned, not recorded as done";
  rows show the planning distance ("2 days overdue", "Due today", "in 3 days") and a state
  edge. Month uses fixed columns (titles truncate; full text in each button's name and the
  inspector), a state mark per activity (warm ring = overdue) and a warm tint for days with
  overdue work. D2: the grid starts full width; a day opens the side inspector (desktop) or an
  inline panel with "Close day" (phones); closing never changes month, filters or date.

## Verification on `784c975`

- `pnpm format:check`, `typecheck`, `lint` (0 warnings), `build`: pass.
- Full Vitest: 1211/1211, three consecutive runs over the final changes (two on `5eb5691`,
  one on `784c975`). New tests: Theme content and no request; `#/settings` route and nav
  (Theme current, Labels and Import / Export once each); legacy link to the Labels dialog;
  QR failures/default-preserving/expiry moved from Settings to Labels; chips ↔ Filters
  shared state; planning-distance wording; phone day panel closes without state change.
- Captures: `.florabase-next-evidence/m8f-784c975-field-ledger-{light,dark}/`, 118 each,
  0 console errors, 0 controls below target, 0 address/tab state failures (manifests in
  `docs/design/florabase-next/m8-final/`). Before/after against `dba7078`:
  `.florabase-next-evidence/m8f-before-after/` (13).
- Real-browser checks: every deep link (`#/settings`, legacy QR, `#/labels`,
  `#/import-export`, `#/events`, `#/history?category=harvest`, Month with `date`) resolves with
  the right page and navigation highlight; chips toggle with Space and Back restores; a Month
  day opens with Enter, Escape closes the inspector and returns focus to the day; no
  horizontal overflow at 390px.

## Tests changed and why

- `settings/SettingsScreen.test.tsx`: rewritten; the page no longer holds the QR form or Tools
  cards (approved). Its QR behaviours are kept as Labels tests.
- `labels/LabelsScreen.test.tsx`: the persistence check remounts Labels instead of Settings;
  one test added for the behaviours moved from Settings.
- `import-export/ImportExportScreen.test.tsx`: opens Import / Export from the navigation (the
  removed Tools card was the old path). `App.lazy.test.tsx`: Settings → Theme heading.
- No assertion was loosened; Journal and Schedule tests pass unchanged.

## Deviations from the design boards

- Journal precision periods are labelled regions with a visual heading, not `h3`s, so the
  entries keep their `h3` contract; History chips have no counts (the API gives totals only
  for the current filter); History's State column shows only "Reversed" (the API has no
  status for non-operation facts); Month keeps two titles per cell plus "N more" (existing
  behaviour) instead of three; the Agenda's pre-existing "N matching activities" status line
  and heading remain; the desktop inspector remains the existing accessible side dialog,
  restyled flush with the workspace. Theme and Labels show a "Settings" eyebrow instead of
  a breadcrumb.

## Limitations

Manual screen reader, physical zoom, high contrast and touch passes; Android QR. Long-content
and loading/error states are covered by the existing unit tests, not by new screenshots.
