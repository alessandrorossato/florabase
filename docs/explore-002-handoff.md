# EXPLORE-002 implementation and UAT refinement handoff

**Operator functional acceptance and canonical verification passed; broad visual review is deferred. Reviewed commit and protected delivery are in progress.**

Source: `/home/alessandro/.codex/worktrees/258f/florabase`, branch
`feat/explore-002-native-ranges`, base/HEAD `aa6c1bf2d6554cc877dec407e14d04f1e048997f`.
At the start of independent verification, feature changes were **unstaged and uncommitted**.
The operator has accepted the current functionality for delivery and explicitly deferred the broad
cross-application visual/UX review. Verification and delivery outcomes are recorded in the final
progress milestone once complete.

## Final product and domain contract

[Native ranges contract](native-ranges-explore.md) records the pre-implementation domain and
geometry audit plus the bounded UAT refinement. Only existing GEOGRAPHY-002 structured
BotanicalProfileNativeRange relationships supply native-range facts. Distribution prose,
GBIF occurrences and material provenance remain independent. The existing identity Reference
native-range manager remains the writer, reached through Edit recorded range.

Collection overview counts distinct represented identities per territory. Explicit row checkboxes
select up to **20** represented identities; Selected species (N), checked/text state, deselection,
individual Remove/View only and Clear selection are keyboard accessible. No query-wide selection.
One selected identity retains exact hierarchy paths, broad/precise/custom/no-geometry semantics,
map and identity/edit/occurrence links. Multiple identities use a subset choropleth with distinct
selected-species counts and contributing-species lists, including unavailable territory boundaries.

Per-identity overlap is unioned before counting: A = South America, B = Brazil, C = both gives
Brazil **3**, Argentina **2**. Drawing descendants do not create stored country assertions.
Missing/unrepresented IDs remain explicit; selected IDs excluded by filters remain selected and
contribute no coverage. No species is silently substituted. Loading, empty, missing, API failure
and local geometry failure remain readable, with retry where appropriate.

Collection status stays single-select: All represented / Living / Current / Historical.
**Collection records** uses OR across Seeds, Sowings, Plants, Plant groups and Stored material;
none selected means all types. The same status/categories/search/with-range eligibility governs
directory, overview, selected coverage and totals. Exact FK relationships only:

- All: retained evidence in any selected category.
- Current: active evidence in a selected category, including active managed unknown remainder.
- Living: active Plant/PlantGroup evidence in a selected category; Living + Seeds is empty.
- Historical: retained selected-category evidence and **no Current representation anywhere**.

Global representation badges/counts retain the existing EXPLORE-001 meaning. No lineage/name
matching, recursive category inference, quantity effect, lifecycle change or domain write is added.

## Local API, bounds and persistence

All endpoints require the existing authenticated local reader under
`/api/v1/explore/native-ranges`:

| Endpoint | Parameters | SELECTs |
| --- | --- | --- |
| `/identities` | `q`, `scope`, repeated `record`, `with_range`, `offset`, `limit` | 2 |
| `/overview` | same, exact-place pagination | 4 |
| `/identities/{uuid}` | same filters and exact-place pagination | 4; missing 404 uses 1 |
| `/selection` | repeated `identity` (max 20), `q`, `scope`, repeated `record`, `with_range` | 2 |

Comparison returns bounded metadata, `matches_filters`, missing IDs, territory counts and distinct
contributor IDs. Coverage is bounded by 250 immutable canonical ISO territories. Overview does not
fetch unbounded contributor arrays. Query-count tests cover one/two/twenty requested identities
and page sizes 1/50. Search is literal scientific/common/cultivar substring (max 200 Unicode chars),
limit 1–100 (default 50), offset 0–100000. Paths use one set-based recursive CTE.
Existing Species distribution routes/response fields remain unchanged; API artifacts were regenerated.

Canonical URL/Saved View v1 state contains only `q`, `scope`, `mode`, sorted lowercase UUID set
`identity` (max 20), canonical OR category set `record`, boolean `withRange`. URL parameters repeat
identity/record; duplicates normalise. Invalid or oversized selection is rejected as a whole with
visible feedback, never arbitrarily truncated. Saved v1 singular UUID state still opens as a one-item
set. Opening the same view resets pagination and rereads current facts. Hover, geometry, viewport,
response data, errors and paging remain transient. Migration **0038** still solely extends the Saved
View surface constraint, with writer lock/populated downgrade refusal; no further migration is added.

## Geometry, navigation and responsive inspection

Natural Earth **1:110m Admin 0 map units**, dataset **5.1.1**, repository tag **v5.1.2**, public domain,
supplies drawing boundaries only. The contract and bundled notice retain the official pinned URL,
SHA-256 and licensing/source distinction. Exact ISO metadata maps territory primitives; canonical
M49 uses descendant ISO drawing units; custom and CLDR-only ranges do not borrow parent polygons.
Small/disputed missing boundaries are explicit. No runtime geometry/provider fetch, geocoding,
centroid substitute, GIS persistence or library was introduced.

The unchanged geometry contains **179 SVG paths**, raw JSON **151,910 bytes**, gzip **58,793 bytes**;
final Vite geometry chunk **150.83 kB / 60.46 kB gzip**. The refined workspace chunk is
**20.32 kB / 6.05 kB gzip**. It and geometry remain separate lazy imports. Original local Node parse
median/p95 **0.56/0.99 ms** and React SVG serialization **3.57/7.87 ms** are initial CPU observations,
not current device paint benchmarks; geometry was not changed by this refinement.

Desktop Explore now reads Botanical identities, Media, Geography, **Maps** text, Species distribution,
Native ranges, Collection origins. Maps is non-actionable and non-collapsible; no landing route or
internal/SavedView identifier changes. Geography remains reference management outside Maps.
Mobile More retains all destinations in a flat list.

Live authenticated DOM/accessibility checks at **1440×844, 1024×844 and 390×844** found no horizontal
overflow in comparison/single-detail controls, category wrapping and contributor lists. Verified
Aloe+Basil+Lavender comparison, Plants-only exclusion, Plants+Seeds, Stored material, single Aloe
exact Italy/Thailand and its existing links, refresh of the repeated-ID set and mobile More order.
Scope/filter/selection URL and Back/Forward/Saved View restoration also have component regressions.
No screenshots were captured or saved. Functional operator UAT passed. Visual treatment is
provisionally accepted; broad visual/product review remains a later cross-application checkpoint
before release hardening.

## Focused verification of the refinement

- **97 backend unit tests passed**: native-range contracts, EXPLORE-001, Saved Views/state/service
  and existing structured-range domain rules (`pytest --no-cov`).
- **39 isolated PostgreSQL tests passed**: category OR/status/search/with-range parity, no duplicate
  identities, one/two/twenty-ID query bounds, per-identity overlap/contributors, missing/filter-excluded
  IDs, API validation/authentication/no-provider behavior, Saved Views, 0038 downgrade safety and
  existing native-range API/migration regressions. Existing 18 Alembic path-separator warnings remain.
  The unique project used an isolated /28 and removed only its containers/network; no volume deletion.
- **152 distinct affected frontend tests passed**: main run passed 151, then the remaining navigation
  test passed after correcting its expected route-order array for the requested IA change. This includes
  multi-selection, 20-ID bound, stale/invalid state, exact detail, contributors, categories, legacy and
  multi-species Saved Views, Back/Forward, geometry, Species distribution and App navigation.
- Focused Ruff/format and strict mypy (**6 changed source files**), CLI fixture syntax/import lint,
  frontend ESLint/Prettier/strict TypeScript and final Vite production build passed.
- `make api-generate`, `make api-check`, feature graph (**95 valid**) and `make test-uat-preview`
  (**19 host guard tests**) passed. **23 read-only runtime/fixture tests** passed, including preservation
  and idempotence of pre-existing operator-managed inventory.
- Guarded additive seed and repeated seed both report **v4 / 42 records**, preserving existing edits.
  An initial seed overlapping the status one-off was correctly refused as ambiguous; retry after the
  status completed succeeded. No preview reset or manual UAT cleanup occurred in this refinement.
- Canonical `make feature-verify` passed on the reviewed tree: 804 backend unit tests at 90.06%
  coverage, 528 frontend tests, all 673 selected PostgreSQL integration tests, strict mypy (303 files),
  API drift, both production image builds, migration cycle 0037 → 0038 → 0037 → 0038, whitespace checks
  and a working-tree receipt. The three hard-coded pre-0038 head expectations found during the run
  were made migration-head-aware in tests and passed focused and full integration reruns. Existing
  Alembic path-separator deprecation warnings remain. Reviewed commit and delivery are pending.

## UAT Preview and operator scenarios

URL: **http://localhost:15174/#/native-ranges**. Synthetic credentials: **preview / preview**.
Task-owned Preview is healthy on schema **0038**, fixture **v4 / 42**. DEV, Stable Preview and
production state were not changed. The original v4 manifest remains readable; explicit seed validates
it before adding managed basil inventory, adopting existing inventory without changing its state.
This additive extension requires no reset and repeated seed preserves operator range edits.

Synthetic baseline: six identities, five represented; All **5**, Living **2**, Current **4**,
Historical **1**; with structured range **4**, without **1**. Basil spans several categories and stores
South America+Brazil. Aloe has Italy+Thailand; Lavender has Italy+custom-under-Brazil; historical
radish has broad Southeast Asia; sage has no range; reference-only Viola remains excluded.
Stored material now yields Basil. All assertions are labelled synthetic and establish no botanical fact.

1. Select Aloe+Basil+Lavender: count 3, Italy contributes Aloe+Lavender, Brazil counts Basil once.
2. Remove/View only until one remains: inspect exact ranges, custom/unavailable states and existing links.
3. Try Plants, Seeds, both and Stored material across statuses; check excluded selections remain explicit.
   Living+Seeds yields no eligible species; Historical requires no Current representation globally.
4. Save several IDs plus categories, reopen/refresh/Back/Forward; preserve the same set, with no provider load.
5. Review Maps IA and 1440/1024/390 layouts, keyboard focus, long names, maps and companion lists.

## Planned follow-up, not implemented

The [official Kew WCVP/POWO audit](native-range-enrichment-audit.md) records accepted backbone,
Native/Introduced distinction, TDWG level 3, current official downloads/version archives/citation,
and the reviewed-match → explicit crosswalk → proposal → operator Apply → retained provenance path.
The complete feature graph was audited; existing **ENRICHMENT-001** is refined, still **planned**,
for consideration immediately after successful EXPLORE-002 delivery before SCHEDULE-001 unless
reprioritised. BOTANY-003's blocked text enrichment contract is unchanged.

The [roadmap](product-roadmap.md) preserves the later broad cross-application product review after
this feature wave and before release hardening. No remote enrichment, crosswalk/provenance schema,
second native-range table, scheduling, Maps landing page, BOTANY-003 workaround or mega-review
was implemented in this refinement.
