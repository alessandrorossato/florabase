# MAPS-ORIGINS-001 — independent verification handoff

2026-10-22 · `/home/alessandro/.codex/worktrees/c902/florabase` ·
`feat/maps-origins-001-candidate` · base `b3f1de4693f50a12396344d251a16a0b4ded4b92`.
Operator visual acceptance, independent implementation/domain review, and canonical full verification
are complete. The candidate is **verified** and ready for guarded delivery. All changes remain
unstaged and uncommitted; no delivery has occurred.

## Working authenticated Review

[Collection origins](http://localhost:15174/#/map) runs from this exact dirty c902 source.
Frontend, backend and PostgreSQL are healthy; code/database revision is `20261013_0042`.
Login is **owner**, display name **Origins Review owner**. Use the existing owner password;
the authorized secure bootstrap credential remains in an operator-readable mode-0600 temporary
file outside the repository. No password is included in evidence or committed files.

The previous delivered b139 environment was removed only after explicit operator approval through
its owning worktree's guarded command. This phase kept c902's existing Review database/media and
added data without reset/removal/recreation. DEV, UAT, Stable Preview, Sourcing, production and other
worktrees are preserved. Disposable integration resources were removed by their own exact workflow;
Quality retains its candidate-owned resources.

## Collection origins implementation

The [design](maps-origins-001-design.md) audits existing APIs/services, geography and shared UI before
changes. PageHeader, DirectoryTools/TaskDialog, SavedViews, MapWorkspace and Leaflet are reused;
there is no new mapping stack, API, schema, dependency or global UI-contract change.

Desktop is approximately 70/30 map/inspector. Functional site/record/identity KPIs open searchable
breakdowns; the unfiltered missing-coordinate KPI opens Geography's existing site view. Counts use
distinct site IDs, `(record_type,id)` and identity IDs, never material quantity. A selected inspector
shows exact coordinates, recorded/unknown accuracy, grouped linked identities, record links and
actual lifecycle. Lists are progressively bounded. Exact coincident markers retain distinct keyboard
and list entries without jitter. Selection preserves the viewport; membership/coordinate changes or
explicit Fit fit sites. Responsive panes remain mounted and resize without panning/recreation.

`#/map`, `provenance_map` v1, `q`, `seed_lots`, `plants` are unchanged. Query still matches botanical
identity labels only; plants includes Plants and PlantGroups. Historical direct records remain.
Unlinked mapped sites remain inspectable under unrestricted filters. Restrictions require eligible
matching records; excluding a selection clears it permanently. Back/Forward and Saved Views restore
filters while clearing transient inspection. The backend continues to exclude Sowing-derived and
extracted descendants from direct-origin qualification. No provenance is inferred from Supplier,
Location, names, taxonomy, native ranges, GBIF or lineage.

## Operator corrections

The earlier renderer used no-referrer for OSM tiles. A request audit intercepted 12 outgoing tile
requests and confirmed missing Referer. That contradicts the
[official OSM Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/).
The previously recorded “loaded image” count was not proof of valid geography: policy-block artwork
can itself decode as an image. Earlier reports/captures remain historical evidence, not current claims
of provider compliance.

Collection origins now defaults to bundled Natural Earth 1:110m generalized context, reprojected vertex
by vertex into Leaflet. Markers retain exact WGS84 coordinates and positive recorded accuracy circles.
The UI explicitly distinguishes this overview from street-level detail. `mapOnlineEnabled` ships false;
permitted deployment configuration plus an explicit visitor action enables optional online tiles.
The canonical OSM endpoint has no rotating subdomains; browser UA and caching remain native, and
cross-origin Referer discloses only app origin. No proxy, impersonation, bulk acquisition or prefetch.
A first tile image error removes the entire online layer, retains local evidence and disables retry
for that visit. HTTP status / HTTP-200 artwork cannot reliably be diagnosed from browser image errors;
operators must resolve provider access before enabling online detail. Attribution remains explicit.
External photo privacy remains the separate no-referrer, explicit Preview once contract.

Filters has two compact semantic checkbox rows: Seed lots; Plants and plant groups. Each label covers
the whole 44px row with adjacent 16px control and wrapping text. Scoped styles avoid affecting other
drawers. Shared DirectoryTools applies changes as chosen; Done, Close, Escape and backdrop dismiss
without undoing them, with return focus. There is no invented Cancel transaction.

## Extended Botanical Review Dataset v5

The [dedicated dataset document](review/extended-botanical-dataset-v5.md) describes exact counts,
relationships, uncertainty, native/provenance matrices, licensed media and recovery limits.

| Live total | Count | Live total | Count |
| --- | ---: | --- | ---: |
| Identities | 37 | Profiles / identities with ranges | 25 / 24 |
| SeedLots | 43 | Plants / PlantGroups | 19 / 7 |
| Sowings | 16 | Orders / Suppliers | 12 / 10 |
| ProvenanceSites | 14 | Locations | 18 |
| Harvests / items | 5 / 8 | Stored-material inventories | 4 |
| Journal/operation events | 13 | Germination observations | 2 |
| Scheduled activities | 27 | Local images / external references | 9 / 8 |
| Media assets / record links | 17 / 18 | Protected attachments | 9 |

The origins API/UI reports **12 mapped sites, 2 without coordinates, 42 direct records, 22 identities**.
The extension has 248 plan nodes and 252 managed references. Ready v4 remains separate with its original
80 references. Two live seed runs returned identical references/counts; pre/post read-only fingerprints
confirmed byte-identical v4 ledger, baseline references and unchanged owner credentials.

New records use existing domain services, legitimate extraction/harvest/inventory workflows and exact
nullable/partial-date contracts. They include rich, missing, approximate, historical and reconciliation
cases. New structured ranges and coordinates are explicitly synthetic; no authority or external taxon
IDs are fabricated. Baseline verified GBIF link remains ready for explicit Load without fake cached
occurrences. Eight small licensed photos (508,755 bytes total) are protected local ingestions; seven
new external references are metadata-only until explicit preview. Source, author, licence, changes,
size and SHA-256 are in the packaged manifest. Photos stay outside production build contexts.

`make feature-review-extended-seed` and `make feature-review-extended-status` repeat exact host and runtime
ownership/DB/media/revision checks, require ready v4 and one enabled owner, share the fixture lock and
use a separate protected v5 ledger. Logical references are deterministic; service-generated UUIDv7 IDs
remain stable on reruns. Ready repeats validate without overwriting edits/primary photos or creating
records. Changed plan/version/owner/missing content refuses. Failed creation rolls back uncommitted
rows and records diagnostics without claiming ready; complete prepared graphs can finish after an
interruption. Failed uploads may leave explicitly listed orphan files for inspection; no automatic
shared-media cleanup or v5 destructive command exists. UAT seeding semantics remain unchanged.

## Review evidence and canonical full verification

[Authenticated v5 browser reports and screenshots](review/maps-origins-001/refinement-v5/README.md)
cover actual database-backed UI; isolated provider refusals are clearly labelled doubles. Map and
Filters captures exist at 1440×844, 1024×844 and 390×844. Browser checks verify all 12 markers, exact
KPIs, keyboard selection, multi-identity inspection, whole-row checkbox clicks, shared dismissal,
zero-result filters, native 1–5 comparison and collection directories. No automatic third-party contact
or runtime page errors occurred. Optional online refusal removes imagery and does not retry.

- Frontend: **130 tests / 15 files passed**, covering origins, native ranges, occurrence rendering,
  shared maps/drawers, photos and media. Full zero-warning ESLint, strict TypeScript and production
  Vite build passed. The new origins-specific label/dismissal test is included. Long-name tooltip width was corrected
  after screenshot inspection and rechecked in the browser/build. Tooltips show the site name/count;
  the full deep geographic path remains in the inspector and native marker title.
- Final tooltip/drawer correction: **17 origins tests / 2 files passed**, affected ESLint/Prettier
  and a fresh TypeScript/Vite build passed after the final source edit.
- Backend and runtime Review guards: **109 passed, 1 skipped** (optional live-environment test),
  with `--no-cov`. Strict fixture/workflow typing and integration-test typing passed.
- PostgreSQL fixture/provenance/orders/native ranges: **38 passed**, using guarded disposable workflow.
  Final stronger fixture no-network/edit-preservation selection: **3 passed** (17.08s).
- Workflow/environment unit guards: **35 passed**, including Review-only extension refusal and
  guard-before-compose ordering. Existing exact foreign-resource/DB/media tests remain in force.
- Backend OpenAPI and TypeScript API drift checks passed. No API artifact changes.
- Operational-script lint/format/typing, frontend formatting and `git diff --check` are checked before
  handoff. No canonical gate, receipt, staging, commit, push, PR or delivery is claimed.

Earlier [synthetic renderer evidence](review/maps-origins-001/README.md) and
[v4 authenticated captures](review/maps-origins-001/live/README.md) are historical. Their former online
default/retry behavior and sparse one-site data are superseded by this phase. Intermediate harness
selector failures and an incorrect API-check module invocation were corrected; only completed
successful commands are counted.

Independent live review reconfirmed exact project/source/health/revision and v5 ownership through the
guarded status workflows. Authenticated browser interactions on the live v5 data verified 12 mapped
sites, 42 distinct directly linked records, 22 identities, two coordinate-less sites, marker and list
selection, recorded WGS84 coordinates/accuracy, grouped exact record links, category filtering and
recomputed KPIs. Keyboard Enter on a textual site row selected the inspector; Escape cleared it. The
record-type filter retained its existing `plants=false` URL meaning. The tested small viewport showed
the map and inspector switch controls without horizontal overflow. The accepted Review database and
owner were left intact. Fresh `origin/main` is still the exact `b3f1de4` base (zero divergence).

Independent source review checked all eight packaged photo descriptions and licence terms against
their individual Wikimedia Commons pages; local derivatives total 508,755 bytes, have no EXIF, and
match the included manifest hashes. Natural Earth terms confirm the generalized base layer is public
domain. The current [OSM tile policy](https://operations.osmfoundation.org/policies/tiles/) requires
an accurate web Referer, visible attribution and ordinary caching, and forbids scraping/offline
prefetch. Online detail remains deployment-disabled by default; configured use sends only the app
origin cross-site, makes no identity/record requests and removes the failed tile layer without retry.

The first `make verify-full` completed successfully on the reviewed implementation and evidence tree
and recorded its tree-specific verification receipt. Backend unit tests passed **953** with **1** optional
live-environment skip; the full frontend suite passed **844 tests in 72 files**; PostgreSQL integration
passed **740 tests** with **953 deselected**. Full ESLint, Ruff, formatting, strict TypeScript/mypy,
production backend/frontend builds, OpenAPI/API drift, workflow ownership/resource guards, migration
cycle, whitespace and staged/untracked checks passed. The tested migration schema remained
`20261013_0042`; no feature schema/API/dependency changes were introduced. The guarded integration
project and migration test resources were cleaned up with zero residual containers, networks or
volumes. `origin/main`, merge-base, and candidate base remain
`b3f1de4693f50a12396344d251a16a0b4ded4b92` with zero branch divergence. This handoff/status
update is followed by a final full gate to refresh the receipt for the exact delivery tree.

## Remaining limits

Actual browser 125%/150% zoom, screen-reader use and physical touch remain pending. Viewport resizing is
not zoom evidence. Local geography is generalized, not a detailed offline street map. Policy artwork
delivered as HTTP 200 cannot be reliably detected. Public OSM was not bulk retried or used for
automated pan/zoom checks. External photo refusal is an isolated double; no remote photo was fetched by
seeding. New ranges are synthetic acceptance data, not botanical reference claims. History is
projected; Schedule overdue states evolve with time. Large real-collection performance is not claimed.
Coincident sites rely on list/keyboard selection; clustering/spiderfying and a paginated map API are
deferred. Protected delivery remains pending.

**READY_FOR_DELIVERY**
