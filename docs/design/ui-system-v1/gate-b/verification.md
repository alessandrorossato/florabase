# Gate B focused verification — 27 October 2026

Candidate branch `feat/ui-system-v1`, base `ee3487412fe458cbdf7145154c54a58b66132cae`.
The original audit/Gate A files were preserved while switching this same managed
worktree to the implementation branch. `make feature-init` accepted the managed
source. No staging, commit, push, PR, merge or canonical FULL was performed.
UI-SYSTEM-001 remains `in_progress`: the broader migration and delivery gate are pending.

## Automated checks

- Focused frontend coverage: **203 distinct tests in 9 files passed** across the
  development runs. Files: DirectoryPage, Lab, Controls, CollectionUI, Saved Views
  state, PrimaryPhotoVisual, App, App.lazy and App.transition.
- Final shared-template/navigation rerun: **16/16 in 4 files**; the subsequent
  active-Sowing fixture correction and its new regression passed **4/4 Lab tests**.
  These are overlapping reruns, not additional unique tests. The new DirectoryPage
  and Lab tests total **15 cases**.
- URL view toggles preserve search, scope, selection, offsets and history.state.
  Actual canonical adapters exclude presentation from Saved Views. Back/hashchange,
  preference precedence and unavailable browser storage are covered. Modal/inline
  focus recovery covers remounted and removed triggers and search retaining focus.
  Protected thumbnail failure, scientific/cultivar formatting, missing images,
  unique decorative icons/visible labels, active-only Sowing facts and eight distinct
  reference-photo sources are covered.
- `python3 -m unittest discover -s scripts -p test_ui_page.py`: **3/3**. Both archetypes,
  overwrite refusal, path/symlink escape, invalid inputs and dry-run behavior.
- Both `make ui-page` archetypes were generated in uniquely owned smoke directories;
  TypeScript checked their actual imports. Only those generated smoke files were removed.
- Targeted zero-warning ESLint; Prettier for changed frontend/design artifacts;
  strict `tsc -b --pretty false`; Ruff check/format for new Python helpers;
  Python scaffold/evidence validation and `git diff --check` passed.
- Default Vite production build passed (257 modules). `scripts/check_ui_lab_build.py`
  confirms no lab path, showcase markers/styles or fixture-photo digest in `dist`.
  No build input, dependency manifest, lockfile, API or generated schema change.
- Feature graph: **117 valid**. Gate A's own validator remains separate from the new
  `python3 docs/design/ui-system-v1/gate-b/validate.py` evidence checks.

Commands used the existing dependency tree and direct Node binaries in `frontend/`.
Vitest used `--configLoader runner --pool=threads --maxWorkers=1`. An earlier default
fork run failed at worker startup **before any tests ran** under host contention;
it is not counted as a passing run. Sequential thread runs completed without changing
test assertions, timeouts or protected checks. Earlier type/lint failures were fixed
and rerun; no suppression was introduced. API/integration/backend/migration suites
were not run for this frontend/template review boundary. The normal CI-004-selected
canonical gate is intentionally deferred until operator acceptance and main alignment.

## Browser evidence

Acquired through the app's connected browser, using the actual React laboratory.
**72 JPEGs**: 27 primary viewport captures (9 compositions × 3 dimensions), 36 theme
specimens (Dashboard and Gallery × 6 themes × 3 dimensions), 9 contextual captures.
[Manifest](asset-manifest.json) records file digests and actual raster dimensions.
[Primary geometry](capture-metadata.json), [theme state](theme-metadata.json) and
[Dashboard fit](dashboard-geometry.json) record measured CSS dimensions separately.
The external binaries are not staged or copied into Git.

| Dashboard baseline                       | Measured result                                                 |
| ---------------------------------------- | --------------------------------------------------------------- |
| CSS viewport                             | 1440×844, DPR 1, visual scale 1                                 |
| Document extent                          | 1440×844; no document scrolling                                 |
| Photographs                              | 8 loaded, 8 distinct URLs, object-fit cover; 4 columns × 2 rows |
| Image frame                              | 207.5×155.625 CSS px, 4:3                                       |
| Last complete photo card including label | bottom 730.453125px                                             |
| Complete Next work panel                 | bottom 787.171875px                                             |
| Smaller screens                          | 1024×844 and 390×844; natural vertical scrolling                |
| Horizontal overflow                      | none in 27 primary or 36 theme specimens                        |

Browser exercises confirmed search/checkbox/preview selection surviving List/Gallery,
Back restoring List and query, closing inline preview returning focus to the remounted
trigger, compact native-dialog Escape returning focus, More exposing the frozen groups
and utilities, house Filters, canonical Saved View exercise, loading/error/empty states
and a long cultivar wrapping without horizontal overflow. Saved View restoration uses
the saved filter URL and the current browser presentation preference, not an invented
saved mode. Light/Dark palette selections were verified against the actual root attributes.

The first capture attempt lost the browser transport; later the foreground Vite process
terminated and some illustrations fell back to unavailable. Those temporary primary
captures were replaced after a detached local restart and reload. The final Dashboard
proof confirms all eight actually loaded, rather than just counting eight placeholders.
The read-only review portal and lab require local processes; restart commands are in README.

## Limits and review boundary

No actual browser zoom sweep, physical touch/device, soft-keyboard, printer, assistive
technology or live large-library performance validation. Native labels/keyboard and
CSS viewport evidence do not establish those checks. Theme evidence is screenshot/DOM
verification, not a new automated WCAG certification. No live collection records were
created, edited, assigned covers or deleted. The lab is a bounded fixture composition,
not a live server integration or full implementation of every existing filter/detail/form.

Media #127 is now on main (`69814bba`), with no shared-file overlap in its delivered diff.
This candidate's checks cover the stated `ee34874` base plus this dirty tree. Its integration
with later main is not claimed. Preserve the Media delivery and rerun affected verification
after aligning, before a delivery gate. Operator review of the final Dashboard, template
density, two views, icons, responsive tools and inspector precedes broad migration.
