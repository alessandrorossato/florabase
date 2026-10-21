> Historical layout evidence. [Current spatial workspace review](../spatial/README.md) supersedes this pass.

# Native ranges overview/chooser refinement — 2026-10-19

Current authenticated evidence for the existing dirty `feat/maps-foundation-001` candidate in `c606`,
HEAD `9a73d3f`. [Review](http://localhost:15174/#/native-ranges) remains isolated and Maps-owned,
fixture v4/80, revision `20261013_0042`. Existing owner/credential and saved preset are retained.
All botanical relationships in these captures are synthetic acceptance examples, not botanical evidence.

This pass supersedes the [previous live layout](../live/README.md). The existing architectural and
scientific contracts remain; see [the updated handoff](../../../maps-foundation-001-handoff.md).

## Layout and selection

- PageHeader places Filters, Saved views and Choose species on the right. Current filters have
  removable chips; the established drawer carries search, representation and record restrictions.
- Five grounded KPIs precede a full-width map. Represented/ranged species open the paged chooser;
  mapped coverage/exact places reveal and focus the relevant detail. Ranged browsing explicitly
  applies the existing with-range filter. The no-range count is informational: there is no inverse
  range API or fabricated client-side result set.
- The species rail is replaced by a secondary TaskDialog with a sticky Done action, explicit
  checkboxes, scientific/common/cultivar search, selected count, clear and the existing 20-ID limit.
  Desktop rows use two compact columns; mobile rows wrap. The page retains selected count in its
  mode control and formatted comparison names above the map. Full selection management is a disclosure.
- Coverage, unavailable boundaries, exact places, methodology and selected-species details are closed
  initially. Opening them is explicit drill-down. The desktop overview document measures about 952px
  with all details closed; the operator does not scroll through a long list before seeing the map.
- KPI/toolbar chooser entry points restore focus. If search or selection replaced the invoking KPI,
  focus returns to the stable Choose species button. Opening/closing without changes retains inspection.

## SVG interaction and boundary fix

The previous SVG interleaved background/coverage fills with selected/hover strokes. Later neighboring
paths could paint over emphasis; hover and selected styles also competed on one path. The new order is
neutral land and coverage fills, fixed boundaries, then inward-clipped selected/hover/focus outlines.
Emphasis uses non-scaling strokes, cannot paint outside its territory, and ignores pointer events.
Only the covered fill paths are interactive or exposed as territory buttons.

Pointer hover and keyboard focus show territory name, grounded count and “Drawing coverage.” They
never change species IDs or committed inspection. Selected borders remain solid; focus adds a dashed
ring. Escape hides the preview while retaining selection. The selected Brazil / hovered Argentina
capture demonstrates adjacent states without a broken or overpainted shared edge.

## Actual viewport evidence

[Measurements](measurements.json) record DOM viewport size, document width/height, scroll position,
map bounds and focus. The final overview captures have no chosen species; the additional mobile
retained-selection capture checks two species remain selected while browsing the overview.

| State | 1440×844 | 1024×844 | 390×844 |
| --- | --- | --- | --- |
| Overview | [Overview](overview-1440.jpg) | [Overview](overview-1024.jpg) | [Overview](overview-390.jpg), [retained selection](overview-390-retained-selection.jpg) |
| Comparison | [Two species](comparison-1440.jpg) | [Two species](comparison-1024.jpg) | [Three species and long cultivar](comparison-390.jpg) |
| Chooser | [Dense rows](chooser-1440.jpg) | Same modal model | [Long-name selection](chooser-390-long-name.jpg), [cultivar search](chooser-cultivar-search-390.jpg) |
| Drill-down | [Exact-place KPI](kpi-exact-1440.jpg) | Same open/focus action | [Textual territory selection](text-territory-390.jpg) |
| Preview / selection | [Selected + hovered Brazil](selected-hover-brazil-1440.jpg), [selected Brazil / hovered Argentina](selected-brazil-hover-argentina-1440.jpg), [keyboard focus](keyboard-focus-1440.jpg) | Same renderer | Textual companion and keyboard access retained |
| Exact scientific evidence | Overview/selected drill-down | Same disclosure | [Single species](single-390.jpg), [custom place](custom-exact-390.jpg), [broad + precise](broad-precise-390.jpg), [no range](no-range-390.jpg) |
| Saved View | Existing preset retained | Same state contract | [Restoration dialog](saved-view-390.jpg) |

The custom and broad/precise images are **full-document** captures; the others are viewport captures.
The browser exporter excludes/rescales scrollbar space: a 1440×844 DOM viewport commonly exports
1425×835, 1024×844 exports 1009×832, and 390×844 exports 375×812. Some short-dialog captures export
390×844 directly. The measured DOM viewport, rather than raster dimensions, establishes the test size.
No real browser zoom is claimed in this pass.

Final map bounds, rounded to pixels:

| View | 1440×844 | 1024×844 | 390×844 |
| --- | --- | --- | --- |
| Overview | y=296–756, 1129×460 | y=352–708, 713×357 | y=549–721, 343×172 |
| Comparison | y=211–671, 1129×460 | y=233–589, 713×357 | y=469–641, 343×172 (three species) |

No horizontal document overflow occurred at these sizes. The long-name mobile chooser measured
client width = scroll width = 322px, within a 339px modal; its 828px height contains internal scrolling.
Mobile navigation does not cover the useful map canvas. The legend wraps into readable labelled rows.
At ≤1024px the map uses its natural 2:1 proportions, eliminating unused vertical canvas space.

## Live acceptance exercised

- Overview shows six represented identities, four with ranges, two without, 25 mapped territories and
  six exact places. Three canonical drawing boundaries are explicitly unavailable.
- Exact-place KPI opens/focuses the exact disclosure. Represented-species KPI restores focus to itself;
  ranged-species KPI applies `withRange=true` and restores focus to Choose species after replacement.
- Brazil inspection remains selected while Argentina preview appears, with Argentina unselected.
  Clear restores focus to Brazil. End/Enter focuses and inspects Vietnam; one SVG tab stop remains.
  Escape hides preview without clearing inspection. The HTML Thailand button selects that polygon
  while three chosen species and their URL remain intact.
- Two selected species yield Italy 2 and Thailand 1; adding historical Raphanus yields Thailand 2.
  Comparison names use the existing BotanicalName primitive, with roman cultivar text.
- Opening/closing the chooser preserves Italy inspection and the URL. Done/Escape focus return was
  inspected. Scientific “Ocimum” and common “basil” searches each yield two identities; “Genovese”
  yields the cultivar while all three previously chosen IDs remain selected through search exclusions.
- Salvia exposes no-range guidance and no misleading blank map. Lavandula's custom Brazilian place
  remains unmapped alongside exact Italy. Basil retains South America + Brazil, with broad coverage
  explicitly partial at 14/16 boundaries and no duplicate identity count for Brazil.
- Actual browser Back/Forward restores overview versus comparison while retaining the same chosen IDs.
  Clearing and reopening the existing “Maps review — Italy overlap” preset restores exactly two IDs.
  A real URL reload restores comparison and leaves transient territory inspection unselected.
- Final fresh-tab rendering, URL reload and keyboard smoke passed; final browser error log was empty.
  During edits, a previous development session had hook/lazy-module errors; supported Review rebuild
  and a fresh browser session resolved them. No loader or dependency safeguard was changed.

## Validation and limits

Baseline: **25 tests / 4 files** before refactoring. Affected suite: **131 tests / 15 files passed**.
After the final geometry-failure KPI correction, the Native/maps subset passed **30 tests / 4 files**.
The 131-test run also includes shared DirectoryTools/ReferenceInteractions and unchanged Species
Distribution, occurrence, provenance and Saved Views regressions. Existing assertions were adapted
for explicit chooser/disclosure actions, not removed or weakened.

Frontend commands (run from `frontend/`):

```bash
pnpm test src/native-ranges src/maps src/species-distribution src/occurrence-map src/provenance-map src/provenance-sites src/saved-views src/components/DirectoryTools.test.tsx src/components/ReferenceInteractions.test.tsx --reporter=dot
pnpm test src/native-ranges src/maps --reporter=dot
```

Final static/build checks (repository root):

```bash
python3 scripts/workflow_environment.py review compose -- exec -T frontend pnpm exec eslint src/maps src/native-ranges --max-warnings 0
python3 scripts/workflow_environment.py review compose -- exec -T frontend pnpm exec prettier --check src/maps src/native-ranges
python3 scripts/workflow_environment.py review compose -- exec -T frontend pnpm build
python3 scripts/check-features.py
git diff --check
make feature-review-status
```

All pass: scoped zero-warning lint/format, strict TypeScript/Vite build, 107-feature graph and whitespace.
Final Native ranges chunks: **29.61 kB JS / 8.44 kB gzip**, **10.34 kB CSS / 2.13 kB gzip**.
The separate geometry chunk remains **150.83 kB / 60.46 kB gzip**; no new library or dataset.

No actual screen reader, physical touch hardware, true 125%/150% zoom or deliberate live API/asset
failure injection was used. Keyboard/DOM structure and actual viewport layouts were inspected;
component regressions cover failures/auth expiry, selection bounds and URL/Saved View history.
No canonical `make feature-verify`, full backend/integration suite, commit or delivery. Operator
acceptance remains required. Review is left running; all changes remain unstaged/uncommitted.
