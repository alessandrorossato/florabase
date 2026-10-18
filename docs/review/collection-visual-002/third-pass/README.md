# COLLECTION-VISUAL-002 — operator screenshot follow-up, 2026-10-18

Same dirty candidate at HEAD `a36c6cffb938c5ed20f93942e1eac1070897962c`, branch
`feat/collection-visual-002`, [Review](http://localhost:15174). No domain mutation, reset/reseed,
UAT operation, staging, commit, canonical verification or delivery in this pass.

## Changes and live evidence

| Requested correction                                   | Desktop                                                          | Mobile                                          |
| ------------------------------------------------------ | ---------------------------------------------------------------- | ----------------------------------------------- |
| Harvest list typography / accepted empty preview       | [Harvests](harvest-directory-desktop.jpg)                        | Existing responsive structure retained          |
| Stored material type, state and rounded/spaced actions | [Stored material](stored-material-desktop.jpg)                   | [Stored material](stored-material-mobile.jpg)   |
| New Harvest right-hand alignment                       | [Aligned Material/Quantity/Description](new-harvest-desktop.jpg) | [Stacked fields](new-harvest-mobile.jpg)        |
| Rounded Location rows and Active default               | [Active: 10 records](locations-active-desktop.jpg)               | Shared responsive tree retained                 |
| Retired filter                                         | [Retired: one record](locations-retired-desktop.jpg)             | Same URL-backed state                           |
| Parent menu constrained to field                       | [Wrapped full paths](location-parent-menu-desktop.jpg)           | [Bounded menu](location-parent-menu-mobile.jpg) |

Measured at 1440×844: Source type and first Material have identical top `254.03125px`;
Material, unknown Quantity and Description each have width `715.546875px` and left `700.453125px`.
Parent input and menu are both 558px wide. At 390×844 both are 320px wide, menu right 355px,
document width 390px. New Harvest mobile has no controls outside the viewport; document width 375px
(the scrollbar accounts for the remaining width). Stored row buttons use the normal 10px radius.
Scientific identity is normal-weight 13px Source Serif 4; metrics are 13px Source Sans 3.

Locations uses Active/Retired/All, default Active, with immediate chips and filter composition.
Necessary ancestors remain structural context; only matching records contribute to the result count.
Manual expansion survives state switches, and a hidden record cannot remain a stale preview.
Existing direct retired Details work. The Saved Views strict allowlist accepts the new state, while
its generic JSON API/schema and Location list query remain unchanged. Old views without State use Active.

Contextual parent selection preserves cycle/lifecycle exclusions and explicit root choice. A typed
but unselected search cannot submit a root move. The existing reference menu closes on the first Escape;
the dialog closes on the next. Live selection was restored to the original root and Cancelled; no save.

## Validation

- **186 distinct frontend tests / seven files**: App 80, HarvestScreen 15, StoredMaterial 20,
  saved-state adapters 50, SavedViews 10, ReferencePicker 7, ReferenceInteractions 4.
- The final Location/StrictMode subset reran after the last selection/expansion refinements.
- **85 backend tests**: Saved Views canonical state/validation and service behavior; no PostgreSQL needed
  for the one-field allowlist change. Scoped Ruff formatting/lint and mypy run on affected Python.
- Targeted frontend ESLint, touched-file Prettier and strict TypeScript/Vite production build.
- Feature graph and `git diff --check`; no staged files and unchanged HEAD.

The initial App run exposed outdated native-select/Escape expectations and a scope-fixture mistake;
tests now exercise actual picker choices and two-stage Escape while retaining payload/cycle/focus checks.
The strict build also caught an unreachable old native-select branch after the edit picker return;
that branch was removed. Final check results are recorded in [verification](verification.txt).

No canonical full gate, integration, API-generation or migration-cycle command was run. No schema or
OpenAPI shape changed. Native dirty-confirmation and true browser zoom remain operator checks from the
previous pass; current field/menu sizing, cancellation and filters were exercised live.
