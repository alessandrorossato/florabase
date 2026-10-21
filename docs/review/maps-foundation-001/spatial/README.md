# Native ranges — spatial workspace evidence

Current operator refinement, 2026-10-19–20. Same dirty `c606` candidate, HEAD `9a73d3f`,
`feat/maps-foundation-001`, Maps-owned <http://localhost:15174/#/native-ranges>.
Owner credential is unchanged and supplied privately; it is not recorded in these files.
The candidate is **not accepted for delivery**.

## What changed

The Collection PageHeader search is visible beside Filters/Saved views/Choose species. Explore all
and Compare species separate complete scoped coverage from explicit comparison. The wide layout
uses about 70% map and 30% inspector, preserving the geographic 2:1 extent. Compact KPIs have explicit
destinations. Territory/selection bottom menus are replaced by the inspector, labelled comparison
legend and About/Places evidence dialogs. The five-species legend follows the map so long names do
not postpone the mobile canvas. Map/Inspector controls switch mounted panes at ≤64rem.

Every compared identity has a stable active color, scientific label and remove action. Solid fills
represent one contributor; diagonal stripes contain all contributors for overlap. Shared borders and
inward-clipped selection/hover/focus stay in separate inert layers above fills. Text counts and exact
contributors remain necessary for small polygons and non-color comprehension.

Territories toggle independently, without a modifier. Chips remove one or clear all. The inspector
returns distinct union results by default, or explicit intersection. Explore all uses the complete
active collection scope; Compare additionally restricts to the chosen IDs. Results separate explicit
country records from drawing coverage through broad recorded places. No inventory/abundance or
occurrence claim is introduced.

## Authenticated captures

| Capture | Actual requested viewport | Evidence |
| --- | --- | --- |
| [Explore all, desktop](overview-1440.jpg) | 1440×844 | Compact KPIs, visible header search, map and permanent inspector |
| [Explore all, tablet](overview-1024.jpg) | 1024×844 | Map and explicit inspector switch, no horizontal overflow |
| [Explore all, mobile](overview-390.jpg) | 390×844 | Compact labelled KPI strip; complete map above bottom navigation |
| [Saved View](saved-view-1440.jpg) | 1440×844 | Preserved Italy overlap view restores exactly Aloe and Lavender |
| [Cultivar search](cultivar-search-1440.jpg) | 1440×844 | Genovese result, two prior comparison IDs remain chosen |
| [Distinct union](union-1440.jpg) | 1440×844 | Italy/Thailand produce three identities, including broad Southeast Asia drawing coverage |
| [Five species, desktop](five-species-1440.jpg) | 1440×844 | Header, canvas, five labelled colors, independent selected territories and useful right inspector |
| [Intersection](intersection-1440.jpg) | 1440×844 | Italy and Thailand, one distinct matching identity: Aloe; explicit scope and evidence |
| [Five species, tablet](five-species-1024.jpg) | 1024×844 | Map/panel control and useful undistorted map; legend with long cultivar |
| [Five species, mobile](five-species-390.jpg) | 390×844 | Map visible before the five-name legend; no horizontal overflow |
| [Mobile inspector](inspector-390.jpg) | 390×844 | Direct panel switch, two distinct Italy contributors, chips, evidence and scroll containment |

Measurements from the actual rendered DOM: desktop comparison map **798.69×399.34**, y **201.98**,
inspector **342.31** wide at the same y; all five legend entries end near y **757.33**. Document height
is **931**, allowing ordinary secondary-content scrolling. Phone map **343×171.5**, y **495.17–666.67**;
the mobile switch reaches the inspector without scrolling through all legend entries. Tablet map
**741×370.5** at the capture. Scroll/client widths were **1425/1425**, **1009/1009**, **375/375**.
The final overview phone KPI refinement puts its **343×171.5** map at **y 553.14–724.64**, fully above the bottom navigation. [Measured overview/navigation captures](measurements.json) include actual viewport and scroll offsets.
These are browser viewport inspections, not actual browser zoom or physical-device proof.
Screenshot export pixels can differ from requested viewport because of scrollbar/device scaling.

The real v4/80 fixture has six represented identities: four ranged and two no-range. Five chosen
identities include the long historical cultivar and a no-range cultivar; no color is falsely mapped
for the latter. Italy and Thailand each have two relevant contributors. Union across them returns
three distinct identities; intersection returns Aloe alone. The sixth checkbox is disabled and all
selected checkboxes remain available for deselection. The fixture, owner and saved preset were not
replaced, reseeded or edited.

## Renderer-only overlap proof — explicitly separate

| Capture | Contributors in the same Brazil polygon |
| --- | --- |
| [Solid](renderer-overlap-1.jpg) | 1 |
| [Two stripes](renderer-overlap-2.jpg) | 2 |
| [Three stripes](renderer-overlap-3.jpg) | 3 |
| [Five stripes](renderer-overlap-5.jpg) | 5 |

These four captures are labelled **Synthetic drawing fixture, not authenticated collection data**.
They serialize the actual NativeCoverageMap component with controlled contributor IDs and the real
local geometry, then render it in the in-app browser. They prove overlap fill composition, not real
botanical assertions, API selection or live five-way fixture coverage. The temporary helper/HTML
was removed from source/public after capture; a local helper copy is retained in ignored candidate
backups. No Review rows were written. Their legend placement precedes the final mobile layout
adjustment; only the common renderer's solid/stripe encoding is being evidenced here.

## Interaction and scientific checks

- Real fixture: explicit five-ID selection and disabled sixth; no-range cultivar remains chosen.
- Map and text buttons toggle independent territories. Italy/Thailand union is three distinct IDs;
  intersection is Aloe. Choosing a territory does not change species URL parameters.
- Brazil evidence reports one Basil identity, explicit Brazil plus broad South America, never two.
  Custom Brazilian places keep no inherited polygon. Unavailable canonical boundaries remain textually
  selectable and explicitly labelled unavailable. Generalized drawing coverage never becomes an
  extra stored country relationship.
- One SVG tab stop, arrows/Home/End, Enter/Space toggles, distinct focus/selection paint, Escape preview
  dismissal; textual chooser and result links are named. Mobile panel selection persists through
  switching and focus stays on its control. No actual screen reader or physical touch device used.
- Live continuation additionally restores the existing Italy-overlap Saved View, verifies actual Back/Forward and keeps both IDs through scientific/common/cultivar search; Genovese returns one identity, basil/Ocimum return two.
- Tests cover larger v1 restoration (6–20 IDs, count mode, explicit removal), stale IDs, query/category/
  scope restrictions, URL/actual Back/Forward, Saved Views, retries/authentication, boundary failures,
  exact-place pagination without map remount, and neutral retained territories after scope changes.

## Completed validation

From the candidate-owned Review frontend:

```sh
pnpm test src/native-ranges src/maps --reporter=dot
pnpm test src/species-distribution src/occurrence-map src/provenance-map src/provenance-sites src/saved-views src/components/DirectoryTools.test.tsx src/components/ReferenceInteractions.test.tsx --reporter=dot
pnpm exec eslint src/maps src/native-ranges --max-warnings 0
pnpm exec prettier --check src/maps src/native-ranges
pnpm build
```

**39 + 101 = 140 tests / 15 files pass.** Zero-warning scoped lint/format, strict TypeScript and Vite
production build pass. Native JS about **38.38/10.86 kB gzip**, CSS **15.21/2.78 kB gzip**; unchanged lazy
geometry **150.83/60.46 kB gzip**. Generated API declarations and OpenAPI drift checks pass.

Backend scoped Ruff lint/format, strict mypy and **6 Native ranges unit tests** pass. Supported isolated
`./scripts/test-integration.sh backend/tests/integration/test_native_ranges_explore.py` passes
**10 tests**, including authenticated endpoint validation, union/intersection, three-query nonempty
page bound, deduplication, pagination and category/scope/query/reference/custom isolation. The owned
disposable integration workflow reports `RESOURCE_CLEANUP_PASSED`; it does not use the Review database.
**107-feature graph**, whitespace and empty-index checks pass. No canonical feature-verify was run.
An earlier combined host test process ended 143 without a final result; completed container suites
above supersede that incomplete run. Initial layout assertions were adapted to the new interactions.

## Remaining operator acceptance

Inspect palette and stripes at world scale, inspector density, full-workspace search scope, five-layer
limit, compatibility behavior and the responsive panel model. A browser with actual 125/150% zoom,
an actual screen reader and a physical touch device still require operator checks. No viewport proxy
is represented as real zoom. If authenticated three/five-way overlap data is desired, authorize a
separate fixture-data pass; this review preserved the existing fixture and distinguishes the renderer
proofs. No accepted-for-delivery, canonical gate, stage, commit or delivery is implied.
