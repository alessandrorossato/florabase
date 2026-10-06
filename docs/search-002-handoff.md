# SEARCH-002 — global Harvest and Media coverage

Implementation and browser preparation are complete and unstaged. Operator visual acceptance,
independent review and canonical verification have passed. The PREVIEW-001 ownership
regression discovered during SEARCH-002 UAT is fixed narrowly in the workflow files below.

## Worktree

- Source: `/home/alessandro/.codex/worktrees/9f48/florabase`.
- Branch: `feat/search-002-global-coverage`, attached with `make feature-init`.
- Base and unchanged HEAD: `0c36a404eedb89531447581d3769867e44d35490` (PREVIEW-001, PR #71).
- Primary `/home/alessandro/Desktop/github/florabase` remains clean on `main` at that same SHA.
- Intentional runtime, generated declarations, tests and documentation are dirty/untracked; index
  is empty. No migration, screenshots, UAT data, binary assets or secrets enter the source tree.

## Coverage and query contract

All SEARCH-001 kinds remain: SeedLot, Sowing, Plant, PlantGroup, Event, BotanicalIdentity,
BotanicalProfile, Supplier, Location, GeographicPlace and ProvenanceSite. New typed kinds are
`harvest` and `media_asset`; HTTP validation, SearchResponse, OpenAPI and TypeScript are synchronized.

Harvest matches label/current derived title, exact Plant/PlantGroup source label, identity
scientific/common/cultivar names, notes, material kind/human label and description. The ordered
material aggregate reproduces the directory title's distinct-kind order, first two labels and
“+ more”. Context uses bounded identity/source names, source type, true occurrence PartialDate and
material summary; it does not dump notes/descriptions or stringify quantities.

Identity filtering uses the exact source's current identity; `year` with Harvest uses only the
occurrence year. Unknown year fails to match; month/day precision is retained in context. Current
source Location, source lifecycle, Supplier, GeographicPlace and ProvenanceSite are never inferred
Harvest relationships. Their filters exclude Harvest. Lifecycle and Event-kind combinations are
rejected by the API. A Harvest and its owned Event may both match independently. Harvest links open
`#/harvests/<uuid>`; Event routes retain their established target history semantics.

Media shares the Library predicate: asset title, attribution and its own Attachment original
filename, including an external saved copy. No licence/URL/caption/linked-record/primary/cover
inference. Title uses Library fallback: title → original filename → External image reference.
Context contains Local image or External image and bounded attribution, without internal storage,
source URLs or binary metadata. Collection filters exclude Media. Search fetches no binaries and
contacts no external hosts; authentication, CSRF/Origin and binary protection remain unchanged.

Material matching uses EXISTS and summaries group by Harvest ID; source joins cannot multiply rows.
Media joins only its unique Attachment and never its links/covers. Each typed branch performs one
count and one bounded page. Text queries retain SEARCH-001's two shared path lookups: Harvest/Media
mixed text search takes **six SELECTs** for three or 51 matches; all 13 kinds take **28 SELECTs**.
No N+1 source/item/reference queries occur. Limits remain 20 per kind by default, maximum 50; offset
pages every group; sort remains case-insensitive title then UUID. Same-title ordering is tested.

## UI and navigation

Result/filter order is Collection (Harvests between Plant groups and Events), Media, Botany,
Reference. Existing controls add Harvests and Media, and Harvest-only occurrence year. No thumbnails
or gallery controls are added to Dashboard search. Mixed kinds, URL restore, Show more, no-result
state, clear/back-to-Dashboard and existing request cancellation remain covered.

Media already had exact `#/media/<uuid>` detail navigation. SEARCH-002 validates the UUID before any
request and shows an explicit deleted/missing state with the existing Media breadcrumb. Refresh and
browser back/forward retain the exact target. Aborted old requests cannot replace a new target.
UUID comparison normalizes letter case so valid uppercase deep links display the canonical response.
External detail retains Preview once opt-in; search itself never requests images.

## Focused checks

- Baseline search backend: **10 passed** before changes.
- Backend search/API, Harvest, Media and external-copy unit matrix: **100 passed**, `--no-cov`.
- Fresh disposable PostgreSQL search/SEARCH-002, Harvest, shared Media and Supplier Media matrix:
  **69 passed**. Includes all eleven old kinds, auth/invalid kinds, text fields, literal escaping,
  multiple items/links/covers, exact totals, deterministic paging, identity/year/excluded filters,
  fallback titles, full/partial/unknown dates and constant query bounds.
- Independent final-review addition: a real PostgreSQL case confirms an external MediaAsset with a
  saved Attachment matches that Attachment's original filename without exposing its URL. The full
  repository integration wrapper passed **550 tests**, including **40 SEARCH-002 integration cases**.
- DashboardSearch, MediaScreen, HarvestScreen and App lazy-route tests: **36 passed across four files**.
  New tests cover compact groups/no images, repeated new kinds, year controls, history/refresh/exact
  asset navigation, missing/invalid target, uppercase UUID spelling, cancellation and Escape focus return.
- Ruff formatting/check and strict mypy: passed (257 application/test files).
- Feature graph: **90 features valid**. Generated artifacts regenerated through `make api-generate`.
- Zero-warning ESLint, strict TypeScript and production Vite build: passed. Production backend
  runtime image build: passed. Changed frontend/document Prettier checks: passed.
- `make api-check` passed for backend OpenAPI and frontend declarations; `git diff --check` passed.
  No canonical `make feature-verify` was run.

Early failed iterations were ordinary test fixture/readiness/lint issues: missing required external
metadata, unused fixture import, colliding legitimate fallback titles, history state inspected before
navigation settled, and strict lint/type issues. They were corrected without weakening assertions,
validation, rules, timeouts or coverage thresholds. Final diff review also reproduced a valid uppercase
UUID link staying in Loading because the response uses lowercase; case normalization and a dedicated
regression corrected it, then real UAT and the affected frontend checks were repeated. Only fresh
passing runs above count as evidence.
Disposable integration containers/network were cleaned, with no operator volume deletion.

Independent final-review smoke: `make smoke-uat-preview` passed in the unique disposable project
`florabase-uat-preview-smoke-e92b8aceebfa`. Its 18 fixture tests, guarded old-owner retirement,
new linked source startup, empty authentication before seeding, fresh fixture/media/source identity,
successful login and cleanup all passed. Operator environments remained isolated.

## UAT and the isolated PREVIEW-001 retirement correction

UAT remains healthy at **http://localhost:15174**, owned by this dirty `9f48` SEARCH-002 source.
UAT-only credentials: **preview / preview**. The unchanged fixture v1 is initialized with 31 baseline
records, one real owner and generated synthetic local media. No fixture evolution/version bump or
product record edits were needed. DB and code both report `20261005_0033`; DB/backend/frontend are
healthy, and the initializer exited successfully. Browser login succeeded through normal auth.

Delivered PREVIEW-001 correctly refused cross-worktree adoption but offered only stop (ownership
retained) and reset (immediate recreation under the old owner). Its missing retirement operation
blocked consecutive feature UAT. The operator explicitly authorized this narrow regression fix and
retirement of the old synthetic UAT state. The correction is isolated to `Makefile`,
`scripts/uat_preview.py`, `scripts/test-uat-preview.py`, `scripts/smoke-uat-preview.py` and workflow
documentation; it changes no SEARCH-002 product contracts, fixture domain schema or application auth.

New supported command, invoked from the owning linked checkout:

```bash
make uat-preview-remove CONFIRM_REMOVE_UAT_PREVIEW=florabase-uat-preview
```

It validates repository/source, exact project/container settings and mounts, all three named volumes,
scoped network identity and absence of foreign container volume users/network endpoints. It stops
writers first, rechecks resource identities, removes only proved UAT containers/network, then
individually removes `florabase-uat-preview_postgres_data`,
`florabase-uat-preview_attachment_data` and `florabase-uat-preview_frontend_node_modules`.
It performs no rebuild/seed, generic `down -v`, source/Git mutation or change to other environments.
Detached/behind-main owners can retire without branch initialization. Wrong/missing confirmation,
non-owners, unrelated repositories, ambiguous identities, changed resources and restarted writers
refuse. See [canonical transition instructions](development-workflow.md#uat-preview-and-operator-acceptance).

Actual authorized transition on 2026-10-06:

```bash
# Current directory: /home/alessandro/.codex/worktrees/80b3/florabase
# Use the corrected Makefile because this older owner predates the command.
make -f /home/alessandro/.codex/worktrees/9f48/florabase/Makefile uat-preview-remove \
  CONFIRM_REMOVE_UAT_PREVIEW=florabase-uat-preview
# Current directory: /home/alessandro/.codex/worktrees/9f48/florabase
make uat-preview-up
make uat-preview-seed
make uat-preview-status
```

All four commands passed. Removal proved four old scoped containers, one internal network and
exactly the three allowed volumes before stopping writers. No manual Docker deletion or ownership
relabeling was used. Missing confirmation from the old source and removal from non-owning `9f48`
were also exercised live and refused. Old/primary Git identities, unrelated operator container/volume
identities and DEV/Stable Preview/Feature Review/production database digests matched before/after.

Regression checks: **19 UAT helper tests** and **29 environment helper tests** passed; changed
workflow Ruff format/lint and strict mypy passed. Real disposable Compose smoke
`florabase-uat-preview-smoke-2e4782f118e6` passed its **18 PostgreSQL fixture tests** and full
seed/auth/persistence/reset/ahead-refusal matrix. Its new transition scenario refused next-source
adoption/removal, retired the first owner through the supported command, started a separate linked
source in a private temporary Git fixture repository, verified empty auth before seed, fresh fixture
IDs/media/source markers and volume ownership, and logged in successfully after fresh seeding.
Supported removal cleaned both fixture owners; operator environments and primary remained unchanged.
The temporary fixture repository never changed operator worktrees. Logs are under `/tmp/search002-*`;
no logs, fixture media, snapshots or private environment state enter Git.

## Actual browser review

Reviewed the real running `9f48` UAT at **1440×844, 1024×844 and 390×844**. Results and filters fit
without horizontal overflow; all kinds remain accessible and mobile filter fields stack. The mixed
`Preview` search returns one Harvest and two Media assets in Collection → Media order, with zero
image elements in search results. The local asset has three record links but appears once.

Opened the exact Harvest, verified its Plant/identity and `2026-09` month precision, and returned
through browser Back. Opened the exact local Media asset; refresh and back/forward retained its
UUID/detail. The external detail kept Preview once opt-in with no image element or remote load.
A nonexistent valid Media UUID showed the explicit deleted/not-found state and Media breadcrumb.
The final uppercase-UUID correction was also confirmed in real UAT.
Mobile Media detail also fit. Filename search returned the local asset once; exact source-label
search returned the Harvest; Harvest occurrence year `2026` retained the true month context.
Empty search, clear/back-to-Dashboard and keyboard Escape/focus restoration passed. No product
records were created/edited/deleted during browser review. The small baseline does not naturally
exercise Show more; large paging/deduplication remains proven by PostgreSQL tests and frontend tests.

Screenshots are review artifacts outside the source tree:

- [1440×844 results](/home/alessandro/.codex/visualizations/2026/10/06/01a10ff8-adfb-79d2-8bd8-9c2e28e48b58/search-002-desktop.jpg).
- [1024×844 results](/home/alessandro/.codex/visualizations/2026/10/06/01a10ff8-adfb-79d2-8bd8-9c2e28e48b58/search-002-intermediate.jpg).
- [390×844 results](/home/alessandro/.codex/visualizations/2026/10/06/01a10ff8-adfb-79d2-8bd8-9c2e28e48b58/search-002-mobile.jpg).

The browser viewport override was reset, and UAT is left running with a representative mixed search
open. This is implementation browser evidence; operator visual acceptance has passed.

Try these searches on Dashboard:

| Scenario              | Query / filter                                     | Expected result                               |
| --------------------- | -------------------------------------------------- | --------------------------------------------- |
| Harvest label         | `Basil seed collection`, Harvests                  | One fixture Harvest; exact detail link        |
| Exact source/identity | `Basil mother plant` or `Ocimum`, Harvests         | Source-derived Harvest context                |
| Material              | `seed`, Harvests                                   | Harvest material match                        |
| Date                  | Harvests + occurrence year `2026`                  | True September 2026 Harvest; no invented day  |
| Identity              | Harvests + Preview basil identity                  | Exact source identity                         |
| Local title           | `Synthetic leaf illustration`, Media               | Shared local asset once                       |
| Filename              | `uat-preview-synthetic-leaf.png`, Media            | Same local asset once                         |
| External metadata     | `intentionally offline` or `reference-only`, Media | Offline external reference; no remote loading |
| Mixed categories      | `Preview` with Harvests and Media                  | Collection then Media; compact links          |
| Existing behavior     | `Basil` / `Supplier` with existing kinds           | Existing typed matches unchanged              |

Open the exact Harvest and Media hits, refresh Media, navigate back/forward, check remote opt-in,
clear search, open/close filters by keyboard and inspect widths/focus/overflow at all three sizes.
Large pagination and deduplication are proven by the disposable PostgreSQL matrix; the small UAT
baseline does not naturally have more than 20 records per new kind.

## Roadmap and responsibility boundary

SEARCH-002 is verified; operator acceptance and independent QA/canonical verification passed.
Saved filters/views are next; bulk operations and justified unified operational history remain later
Collection productivity v2 work. Orders/Purchases still follows that milestone. BOTANY-003's approved
WFO TLS blocker and historical RELEASE-001 planning are unchanged. No later capability is prebuilt.

Operator visual acceptance passed. The authorized independent reviewer owns canonical verification,
the single reviewed commit, repository delivery, feature finish and final primary-main verification.
