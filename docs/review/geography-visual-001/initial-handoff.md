# GEOGRAPHY-VISUAL-001 — Geography exploration review candidate

24 October 2026. Source: `/home/alessandro/.codex/worktrees/5430/florabase`;
branch `feat/geography-visual-001`; base `e7ade78559803a35b738a669085799f55eb76258`.
Fetched `origin/main` before `make feature-init`. The supplied clean Codex-managed worktree is the
isolated feature source; the canonical workflow forbids creating a second feature worktree.

Implementation candidate, **not operator accepted or canonically verified**. The backlog status is
`implemented`. Everything remains unstaged and uncommitted. No push, PR, delivery or FULL gate.

## Audit and comparison with Locations

Read the current UI contract, development workflow, THEMES/CONTROLS handoffs and all three delivered
Maps handoffs. Inspected Geography, Locations, ProvenanceSite management, native-range assertions,
collection provenance editors, App routing, directory controls, Saved Views and map state contracts.

| Surface | Existing implementation | This candidate |
| --- | --- | --- |
| Shared grammar | PageHeader, DirectoryTools, ActionButton, QuickPreview, TaskDialog and theme tokens already work | Reuse them. No global CSS rewrite, shared token edit or new dependency |
| Places | Real recursive hierarchy; independent expand and select controls; canonical CLDR/local distinction; large detail-style preview title/actions | Preserve tree and edit rules; consistent strong row title, secondary code/path, compact preview typography/actions and explicit detail/site navigation |
| Locations reference | Physical hierarchy, status/usage metadata, directory selection, compact preview and explicit detail/edit/child actions | Reuse its layout/interaction grammar; do not reuse storage semantics as geographic provenance |
| Site directory | Separate legacy serif heading/row titles, coordinate status buried in metadata; notes and large actions in every preview | Shared UI typography, visible coordinate status, explicit unknown accuracy, compact actions; full notes and exact linked source records on site deep links |
| Tablet headers | Legacy column direction makes horizontal shared flex bases act as enormous heights | Scoped Geography header wrapping keeps natural height, with no shared shell edit |
| Exploration | Three delivered global map destinations; Geography had management tabs only | A local-evidence overview and reusable grouped internal navigation across the existing screens |
| Geography Map mode | Maps all coordinate-bearing sites, including unlinked sites | Preserve `mode=map`; label it **Site map**, explain its management purpose and link to Collection origins |
| URL navigation | Geography passed fresh callback/fallback objects to its view hook on every parent render | Stabilize those arguments. Browser reproduction showed a changed query URL retaining old mode/search; the same transition now updates correctly |

Geography-specific CSS lives in `frontend/src/geography/geography.css`. Shared directory components,
Settings, global sidebar entries, design tokens and unrelated page shells are untouched. Selection
continues to use the shared selected background/accent. A separate focus outline and pressed state
keep keyboard focus distinguishable from selection. Long names and paths wrap.

## Internal navigation and routes

**Geographic exploration:** Overview, Native ranges, Species distribution, Collection origins.
**Manage geographic data:** Places, Provenance sites; the retained Site map is a management view.

`#/geography/overview` is reserved before Geography's existing UUID site route. UUIDs cannot collide
with `overview`. `#/geography` still opens Places; existing global map destinations retain their
names and URLs. The navigation component is internal to Geography and the three Maps workspaces,
so IA-NAV-001 can adopt it without choosing a new global sidebar architecture here.

| URL | Meaning |
| --- | --- |
| `#/geography` / `?mode=places` | Existing Places directory/search and v1 Saved Views |
| `#/geography?place=<id>` | Existing exact place selection; ancestors expand |
| `#/geography?mode=sites` | Existing Provenance sites directory |
| `#/geography/<site-id>` | Existing exact site deep link, now with exact supported source-record links |
| `#/geography?mode=sites&place=<id>` | Narrow frontend extension: sites whose `geographic_place_id` exactly equals that ID; no descendants or name matching |
| `#/geography?mode=map` | Retained all-site coordinate management map |
| `#/native-ranges` | Existing structured reference map |
| `#/native-ranges?mode=species&identity=<id>` | Existing exact species comparison/selection contract, used by overview links |
| `#/species-distribution?identity=<id>` | Existing exact represented-identity occurrence workspace |
| `#/map` | Existing Collection origins workspace |

Search, `mode`, unknown valid query parameters and native browser history remain owned by the
existing view hook. Geography v1 Saved Views still persist only `q` and `mode`; the place-scoped
record context does not offer a misleading Save action. No Saved View schema or API change.
The new overview itself has no invented Saved View type. Example identity/site lists are bounded to
two examples, not presented as complete result lists.

## Three evidence destinations

The overview makes four authenticated local reads: native-range overview and a bounded identity
page, represented-identity readiness, and the existing provenance map projection. The three summaries
load and fail independently, show truthful empty states and offer retry while their navigation stays
available. Requests abort on departure; 401 uses the existing session-expiry flow. No map engine,
geometry, external imagery, provider cache refresh or provider request is mounted/started there.

- **Native ranges:** represented identity coverage, recorded named areas and missing structured
  ranges, plus exact Botanical Identity/Reference and species-scoped map links. Only existing explicit
  profile/place assertions count. Broad-derived drawing coverage remains distinct from exact records;
  custom/unsupported places do not acquire invented boundaries.
- **Species distribution:** represented identities and compatible confirmed taxon-link availability.
  A ready link is not a downloaded occurrence dataset or a coverage claim. Open the existing workspace
  to explicitly load/refresh GBIF. Local cache behavior, attribution, eligibility, privacy, quality and
  failure handling remain unchanged. Density is neither abundance nor evidence of native status.
- **Collection origins:** coordinate-bearing sites and distinct `(record_type,id)` direct records,
  coordinate-less site count, exact example site and source-material links. Historical records remain.
  Counts are records, not quantities. The dedicated map, local Natural Earth context, explicit optional
  online detail and configured privacy/attribution controls are reused unchanged.

## Geographic data workflows and preserved contracts

Local places still require an existing non-retired parent; cycle, retirement, deletion and usage
constraints remain server authoritative. Canonical CLDR names/ancestry are read-only. Selection and
creation reveal existing ancestors without flattening relationships. Parent/site navigation selects
exact IDs and reveals the corresponding branch.

Sites retain exact decimal WGS84 values, nullable paired coordinates, recorded/unknown accuracy,
place relationship and notes. Full notes are visible on the exact site route and remain in the
existing editor. There is no separate structured site source field to fabricate; existing operator
notes remain notes. Usage counts are existing server counts. Site edit, create, delete conflicts,
CSRF and coordinate validation are unchanged.

SeedLot and direct Plant/PlantGroup provenance editors retain their explicit operator confirmation.
Neither Supplier, physical Location, scientific-name matching, ancestry nor a native range creates
collection provenance. Source links reuse the existing origins projection and record-link helper,
including retained historical material. Nothing changes the direct-origin qualification of derived
Sowings, extracted Plants or other descendants.

Structured native-range creation/deletion remains in the Botanical Identity Native range module.
Existing operator assertions and assisted enrichment review/source evidence remain unchanged. No
unapproved provider import, automatic range inference, source assertion, polygon upload or broad API
extension was added.

## Missing link contracts and integration dependencies

The site directory API returns usage **counts**, not linked record IDs. The existing origins
projection supplies exact direct-record IDs only for coordinate-bearing sites. Site details reuse
those IDs. Sites without coordinates explicitly explain that exact links are unavailable, retain
truthful usage totals and offer the Collection origins workspace. This limitation was reported before
implementation; no scientific-name search or guessed material link is used as a substitute.

Place-to-site scope is exact/direct, not a recursive descendant filter. There is no new place-scoped
native-range identity listing contract, global provenance filter or completeness endpoint. Geography
and origins remain unpaginated existing APIs; this candidate adds no real-large-collection performance
claim. The overview does not download or scan occurrence rasters for readiness.

The App change is one lazy workspace and one reserved Geography route branch. The other three map
screens add only the internal navigation import/render. IA-NAV-001 may touch that same router; resolve
that small integration explicitly. BOTANICAL-IDENTITIES-VISUAL-001 may refine identity tabs: preserve
its existing `tab=reference` and Native range module routes when integrating. No other agent's worktree
was edited. Recheck current main before any later accepted verification/delivery.

## Review environment

[Open isolated Geography review](http://localhost:15276/#/geography/overview).
Login: `geography-review`. Its generated password is retained only in the operator-readable,
mode-0600 file `/tmp/geography-5430-owner-password`; it is absent from repository evidence.

The separately named `florabase-geography-5430` project owns its DB, media and network. Backend uses
this worktree's read-only source/migrations over the existing compatible development image;
frontend is this worktree's Vite source and locked local dependencies, served by detached container
`florabase-geography-5430-frontend` with restart policy `unless-stopped`. DB revision is
`20261013_0042`. Temporary Compose configuration is `/tmp/geography-5430-compose.yaml`.
Only loopback ports 15276 (frontend) and 18276 (backend) are used. PostgreSQL has no published port.
The first attempted 15176/18176 pair was occupied and startup refused; no existing listener was stopped.

The fixture was created through authenticated APIs in this new database only: canonical geography,
two nested local places, one coordinate-bearing site, one coordinate-less site, two identities,
two SeedLots (including historical material), one explicitly synthetic profile/range. No external
taxon ID, provider occurrence or scientific evidence was fabricated. DEV, UAT, Review, Sourcing,
Stable Preview, the primary checkout and other worktrees retain their data and ownership.

This is a candidate-owned manual review runtime, not a new supported lifecycle role. Do not run the
fixed `feature-review-*` helpers to take ownership of another worktree's retained Review. Temporary
runtime files are outside the delivered implementation; no environment/workflow mechanism is added.

## Verification and visual evidence

Final check totals and browser evidence are recorded in
[the review evidence index](review/geography-visual-001/README.md). Captures use the requested
1440×844, 1024×844 and 390×844 viewports with Botanical Light/Dark, Herbarium Light and Mineral Dark.
Authenticated fixture evidence is distinguished from explicitly injected empty/error/large-data
renderer checks. Viewport resizing is not browser zoom or physical-device evidence.

No backend/domain/API/schema change was made, so backend/integration, migration-cycle and API
regeneration suites were not rerun. The new Review database was migrated normally to existing head;
that is startup evidence, not a new migration acceptance claim. The canonical FULL gate is explicitly
reserved for after operator acceptance. No receipt or verified status is claimed.

Remaining acceptance: operator visual/product review; true browser zoom; actual screen-reader and
physical touch-device checks; real large-collection performance; live GBIF/online imagery availability.
Provider-offline, cache and tile handling remain covered by the delivered map behavior and affected
regressions; this task does not perform provider traffic to manufacture new live evidence.

## Future concepts — not delivered

- Assisted native-range import: first approve a licensed botanical source, exact identity matching,
  source assertions and review/apply/undo behavior. The operator must confirm assertions explicitly.
- Provider refresh: define source/version/acquisition metadata, stale-state and provenance retention
  before extending the existing approved enrichment flow.
- User-provided boundaries/GeoJSON: validate size, coordinate reference system, geometry, topology,
  attribution and record ownership; never silently replace named-area or provenance evidence.
- Data completeness: introduce an agreed denominator and unknown/not-applicable meanings; current
  availability counts are not a new completeness score.
- Geographic cross-filtering/comparison: define exact ID, descendant, evidence type and Saved View
  contracts before linking broader result sets.
- Physical collection layout mapping belongs under **Locations**, with its own storage/layout model;
  it must not infer or overwrite biological provenance.

GEOGRAPHY_EXPLORATION_REVIEW_READY
