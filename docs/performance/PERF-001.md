# PERF-001 measurement protocol and results

## Protocol frozen before optimization

Use `compose.yaml` runtime targets with the isolated `compose.perf.yaml` override. Like preview,
only the loopback origin/cookie environment differs from production: no Vite, reload, source mounts,
public backend/database, operator data, or normal installation volumes. PostgreSQL and attachments
are disposable tmpfs. Database statistics instrumentation is benchmark-only. Keep baseline results
immutable in separate JSON files outside the worktree; summarize small useful evidence here.

Fixture version 1: 80 identities/profiles, 8 suppliers, 12 locations with hierarchy, 8 coordinate
sites, the migrated canonical geography plus a custom locality, 160 SeedLots, 120 Sowings, 160 Plants,
80 PlantGroups, 960 dated Events, 240 germination observations, 12 bounded local image binaries,
explicit primary photos and an external reference. Fixed IDs, content and dates; no network seeding.

API workload: Dashboard, every reference/collection directory and detail, identity collection/profile,
Events, Photos, lineage, provenance map, germination, search, authenticated thumbnail and original;
create/edit/delete a disposable BotanicalIdentity through Origin/CSRF-protected APIs. One first request and
one warmup, then seven timed repetitions per read; report median and min/max, bytes and SQL counts.
Do not describe seven samples as a reliable p95. SQL counts use isolated PostgreSQL pg_stat_statements,
exclude health/pool pings and instrumentation itself, and include authentication. Investigate slow
statements using EXPLAIN ANALYZE with buffers; add no indexes without demonstrated benefit.

Browser workload: fresh Chromium context authenticated normally; Dashboard, directories/details,
reference, Events, Photos, lineage, provenance map and explicit occurrence load. Capture request
paths, transfer/body sizes, route completion and production chunks. Basemap and occurrence responses
are deterministic browser fixtures only for repeatability; this does not measure external provider
latency or change application privacy. Separately attempt live occurrence evidence and report failure
or variable network timing without folding it into local timings. QR is measured on explicit Labels.

Stability: six heavy/light navigation cycles, force GC only at observation checkpoints to distinguish
retained heap from temporary allocations; record DOM nodes/listeners through Chromium and outstanding
timers/listeners through browser-only instrumentation. Leave authenticated Dashboard idle for 120s,
sample container CPU/RAM/network and PostgreSQL connections every 10s. Inspect request growth and
session touches; health checks remain enabled. One-time lazy module retention is expected.

Startup: time database health, explicit migration/fixture separately, application readiness and full
health. Warmup 20s before workload. Capture production image sizes and container process counts.
Record hardware, tested SHA, dataset, other services and host noise. Timings and tmpfs database costs
are environment-specific; this protocol promises no hardware minimum or flaky CI timing budget.

## Results

Baseline evidence is preserved in [baseline.json](baseline.json), captured from unchanged `d5a9da5`
before optimization. [after.json](after.json) retains the first comparison, warmed repeat and final
runtime repeat (including chunk-download recovery added before final checks). The initial pilot was discarded because route settlement was incomplete and
API activity overlapped its idle window; no pilot resource/query numbers enter the comparison.
The accepted run uses explicit tabs and request-quiescence tracking, and runs sequentially.

Demonstrated hotspots: 587,752-byte initial JS plus 103,469-byte CSS served without compression;
all non-map workspaces eagerly imported; repeated geography dictionary construction consumed
1.899s of a 2.882s focused profile over seven response-builder cycles (4,256 path calls); and
SeedLot/Plant directory responses fetched the same full geography twice. Full directory query
counts were bounded rather than N+1. Changes therefore use native React lazy workspaces,
nginx static-only compression, a response-local geography lookup, reused loaded geography, and
one serialization per distinct referenced site. No shared cache, schema, index, API or security
configuration change is needed. Comparison and final verification follow below.

## Reproduction commands

Run from the repository root. Docker must be available. The controller refuses to overwrite evidence
or replace an existing benchmark project. The fixture refuses a populated collection and checks the
fixed database/origin/disposable marker. The Compose wrapper never loads the operator's `.env`.
Startup also rejects mounted volumes or published database/backend ports before starting anything.
Use the exact wrapper; do not mix these commands with development/preview Compose commands.

```bash
scripts/perf/compose.sh build
python3 scripts/perf/measure.py start --out /tmp/perf-environment.json
sleep 20
python3 scripts/perf/measure.py api --out /tmp/perf-api.json
python3 scripts/perf/measure.py transfer --out /tmp/perf-transfer.json
# Run browser only AFTER the API command completes: no concurrent SQL-count or idle measurements.
PERF_PLAYWRIGHT=/path/to/node_modules/playwright \
PLAYWRIGHT_BROWSERS_PATH=/path/to/installed/browsers \
node scripts/perf/browser.mjs /tmp/perf-environment.json /tmp/perf-browser.json
PERF_PLAYWRIGHT=/path/to/node_modules/playwright \
node scripts/perf/verify-chunk-recovery.mjs /tmp/perf-chunk-recovery.json
scripts/perf/compose.sh exec -T backend python - < scripts/perf/profile.py
scripts/perf/compose.sh exec -T backend python - < scripts/perf/plans.py
python3 scripts/perf/measure.py stop --out /tmp/perf-cleanup.json
```

Use an externally installed Playwright and its matching Chromium; no browser framework is added to
application dependencies. On this machine the existing bundled Playwright was used and its matching
Chromium downloaded into `/tmp/florabase-perf-browser` with the Playwright CLI `install chromium`.
The browser collector uses Chromium's performance/heap protocol and intentionally waits for 500ms
network quiescence per interaction. Its route elapsed values include that wait and sometimes two tab
interactions; they are diagnostic traces, **not** user-visible paint latency or comparable API timings.
Browser routing fixtures disable HTTP cache, so transfer evidence is a fresh-cache case; loaded ES
modules remain available within the same document. No steady-state HTTP-cache efficiency claim is made.

Stop removes only `florabase-perf` containers/network; tmpfs state disappears with the containers.
It never removes named volumes. Rebuild, start, and rerun the exact same commands with **new** output
filenames for the comparison. Keep both summaries; do not regenerate the baseline from optimized code.
The four controller safety tests run with `python3 scripts/perf/test_measure.py` without Docker.

## Environment and fixture

Tested on 2026-09-27: Linux 6.19.8-surface-3 x86_64, Intel Core i5-1035G4 (4 cores/8 logical CPUs),
7,903,653,888 bytes RAM reported by Docker, Docker Engine/client 29.8.1, Compose 5.5.1, default
Docker context. Production targets use Python 3.14.7/Uvicorn, PostgreSQL 18.6-alpine and unprivileged
nginx 1.29.4; build Node 24.19.0, Chromium 151.0.7922.34. Baseline commit is
`d5a9da53bea675e16aeba75a1f8e6cd272e6cd99`; comparison is that commit plus the unstaged PERF-001
implementation. This is a runtime-image benchmark with preview-style loopback cookies, not an HTTPS
release/security acceptance run. Production security settings and validators were not changed.

The existing development stack and other operator services were left running to avoid disrupting
operator state. No development requests were intentionally generated during accepted measurements.
Host load varied (roughly 2–4 during benchmark observations); thermal/power state and other services
were uncontrolled. PostgreSQL and media use tmpfs: disk durability/write latency, TLS, remote-network
latency, browser machine diversity and large media archives are outside the measured envelope.

The fixture has 80 profiles/native ranges, 288 geographic places (287 migrated canonical plus one
locality), explicit SeedLot→Sowing→Plant/PlantGroup relationships, fixed dates/counts, 960 observations
as Events, 240 dated germination rows, 11 selected local collection primaries and one local identity
cover. Twelve 900×600 deterministic JPEGs are 360,310 bytes each; the fixed thumbnail is 4,720 bytes.
An attributed external reference stays unloaded; the synthetic GBIF link is browser-test metadata,
not a claim that a botanical identity was reconciled with a real provider taxon.

## Backend evidence and comparison

All 28 measured read payload lengths are unchanged, including direct stored provenance, lifecycle,
primary-photo, quantity, germination and lineage responses. First endpoint calls are reported in the
JSON; the service/process and database become warm across the workload, so “first” is not a disk-cold
claim. Each table timing is the median of seven requests; bracketed values are min–max milliseconds.
The first comparison had slower unchanged controls, so a complete warmed repeat was retained rather
than discarded. Both comparison runs and a final-tree repeat after serial verification are reported; no baseline
numbers were revised. The final run also improves unchanged controls by about 25–35%, so its lower
absolute times cannot all be attributed to the code changes.

| API/workload                   | Baseline median | After first median | After warmed repeat (range) | Final tree repeat (range) | SQL baseline → after |
| ------------------------------ | --------------: | -----------------: | --------------------------: | ------------------------: | -------------------: |
| Dashboard                      |            43.7 |               60.3 |            45.5 [43.1–53.4] |          33.4 [31.5–36.7] |              10 → 10 |
| BotanicalIdentity directory    |            16.8 |               22.8 |            16.1 [15.0–19.9] |          11.5 [10.9–13.9] |                3 → 3 |
| SeedLot directory (160 rows)   |           122.3 |               90.7 |           66.3 [63.3–202.0] |          46.0 [44.6–48.5] |              11 → 10 |
| Sowing directory (120 rows)    |            27.6 |               36.8 |            27.1 [25.6–32.0] |          19.5 [18.4–21.0] |                4 → 4 |
| Plant directory (160 rows)     |            82.8 |               82.1 |            65.7 [64.6–76.2] |         47.2 [44.8–111.4] |              11 → 10 |
| PlantGroup directory (80 rows) |            38.3 |               52.8 |            39.0 [37.3–43.6] |          28.2 [26.5–30.1] |                6 → 6 |
| Supplier directory             |            10.7 |               14.0 |            10.6 [10.1–12.2] |            7.7 [7.3–10.0] |                3 → 3 |
| Location directory             |            13.5 |               20.6 |            12.4 [12.2–13.1] |            8.7 [8.3–10.5] |                7 → 7 |
| Geography directory (288 rows) |            64.2 |               25.4 |            22.4 [21.5–43.7] |          15.4 [14.7–20.3] |                8 → 8 |
| Events directory (960 rows)    |           108.9 |              142.2 |         118.8 [106.7–158.7] |         75.9 [73.4–149.4] |                4 → 4 |
| Provenance map dataset         |            30.0 |               40.6 |            30.1 [28.3–57.5] |          21.9 [21.4–24.4] |                8 → 8 |
| Search, all matching kinds     |           165.1 |              219.1 |         164.3 [155.9–295.0] |       122.0 [114.6–125.9] |              26 → 26 |
| Identity collection detail     |           108.1 |               94.8 |           90.2 [87.2–111.7] |          70.0 [64.7–72.1] |              22 → 21 |
| SeedLot detail                 |            36.4 |               41.0 |            34.9 [31.0–39.3] |          23.3 [21.8–28.4] |              11 → 10 |
| Local thumbnail                |            32.5 |               33.2 |            32.1 [31.8–43.0] |          27.6 [27.3–29.2] |                3 → 3 |
| Local original                 |            10.3 |               10.0 |              9.6 [9.5–10.2] |             6.9 [6.7–7.6] |                3 → 3 |

The other detail, profile, Photos, lineage, germination and provenance-site endpoints are retained in
[baseline.json](baseline.json) and [after.json](after.json), including all three comparison runs. Normal protected create/edit/delete took 42.6ms baseline, 48.8ms first comparison, 31.5ms final repeat;
this is one composite workflow trace, not a reliable latency percentile. Origin, session cookies and
CSRF were used; no anonymous benchmark endpoints or security bypasses were introduced.

Interpretation: the warmed repeat reduces SeedLot median about 46%, Geography about 65%, Plant about
21%, and identity collection about 17%. The first comparison supports a Geography/SeedLot improvement
but does not establish a Plant timing improvement. Events repeat median is about 9% slower and its
ranges overlap baseline; unchanged controls and outliers demonstrate noise. Do not claim every route
became faster or infer a reliable tail percentile from seven samples. There are no CI wall-clock,
CPU/RAM, or hardware budgets.

The focused profile executes the same SeedLot and Geography response builders seven times: 4,509,486
calls/2.882s baseline versus 698,696/0.864s comparison. Profiler instrumentation exaggerates hot-loop
cost and is **supporting evidence**, not HTTP latency. Reusing the hierarchy dictionary eliminates
repeated full-list indexing; serializing 8 distinct sites avoids 160 repeated site responses. Passing
already-loaded geography avoids one repeated SELECT. All reuse ends with the response; no global or
session cache is added. Existing missing-parent/cycle errors and API ordering remain enforced.

SQL counts include two authentication reads, exclude BEGIN/COMMIT, pool/health pings and the collector
itself. Directory counts are bounded (3–11 for the measured collection/reference reads); search's 26
statements are typed group count/page reads, not one query per row. New PostgreSQL regressions compare
1 and 20 records for SeedLot, Plant and PlantGroup: one geography SELECT and six service statements at
either size, with identical explicit geographic paths. No N+1 fix or speculative connection tuning
is claimed. Existing request bursts retain five idle pooled database connections.

EXPLAIN ANALYZE/BUFFERS was run against exact captured service statements. SeedLot's 160-row projection
uses small hash joins, an existing geographic primary-key lookup, and a 113KiB quicksort; execution
5.406ms baseline/2.934ms comparison. Recent Events joins 960 rows with a 31KiB top-N heapsort,
8.554/6.565ms. Geography scans/sorts 288 rows with a 67KiB quicksort, 0.764/0.518ms. These are one plan
sample each, with unchanged SQL/plans and no disk sort spill; timing differences are not index gains.
The demonstrated CPU hotspot was Python response construction. No index, migration, denormalization,
materialized view, generic cache, pool setting or PostgreSQL tuning was justified.

## Frontend, media and maps

The production build now loads each workspace and propagation wizard through React lazy/Suspense.
Dashboard/authentication do not fetch collection/reference workspaces, map code or QR code. Leaflet
remains a separate optional shared chunk (~149KB raw); its existing global CSS is retained to avoid
changing map styling. Labels/QR (~28KB raw) loads on explicit Labels navigation. The 500KB Vite warning
threshold is unchanged; the largest chunk is now ~208KB and the advisory is absent.

Public static HTML/JS/CSS/SVG are compressed inside nginx's static location. `/api/` retains its
existing response behavior, including authenticated data, photos, CSRF and session responses; local
media remain authorized and unmodified. `Vary: Accept-Encoding` is set. The comparison collector
records actual encoded browser asset body sizes, not hypothetical gzip sizes printed by Vite.
The JS/CSS totals below cover `/assets/` only; the unchanged 244-byte runtime configuration script,
HTML, HTTP headers and API bodies are separate and remain visible in the request/resource evidence.

First comparison: initial Dashboard JS 587,838→88,559 bytes, CSS 103,469→28,679 bytes (total
691,307→117,238, about 83% less). Initial request count rises 9→18 because useful shared modules are
separate requests. This is an actual transfer reduction, not a demonstrated paint-time speedup:
single initial settled traces were 775/826ms and include the collector's 500ms quiescence wait.
All-workspace JS increases 747,705→758,936 bytes raw (~1.5%) and independently gzipped chunks total
196,708→222,465 bytes (~13%, 25.8KB more). This is a real tradeoff for substantially less initial
work; no manual package partitioning or advisory-threshold change is used. Final-build transfer
including failed-download recovery is 88,685-byte JS + 28,679-byte CSS = **117,364 bytes**, still
about 83% below baseline, with 18 initial requests and a 749ms settled trace. All-workspace JS is
759,387 raw bytes over 39 chunks; independently gzipped total 222,537 bytes. The largest raw chunk
is 207,746 bytes. The final collector recorded no browser errors. A separate actual-response check
decoded nginx gzip back to the identical JS/CSS bytes and confirmed the 604,487-byte authenticated
Events response is uncompressed and identical for identity/gzip requests.

Directory and ordinary SeedLot/Plant detail browsing use bounded thumbnails; no original collection
photo downloads occur there. Photos fetches its metadata and lazily loads the visible local original.
Identity detail intentionally uses its accepted full cover. The attributed external collection image
was never requested. There are no remote images, map instances, tiles or provider requests on unrelated
routes. Provenance mounts one map, occurrence mounts one only after explicit load, and Dashboard
returns to zero. Controlled basemap/density PNG responses exercise real Leaflet mounting/cleanup;
this does not benchmark external bandwidth or server tile-proxy latency.

Separately, three existing authenticated live occurrence summary requests succeeded in 0.41, 0.27
and 0.42s with zero eligible records for the synthetic fixture token `6SHN2`. They establish live
endpoint/failure-boundary reachability only, not botanical matching, populated density latency or a
provider performance guarantee. Real populated-provider/TLS/network checks remain release sanity work.

## Repeated navigation, idle and footprint

Both measured runs perform six heavy/light cycles after all representative routes. Each cycle has
53 requests; no growth or duplicate provider traffic develops. Dashboard checkpoints retain one
document, no maps, zero intervals/timeouts and stable node/listener counts (baseline 326/329;
comparison 358/331 after lazy loading). Forced-GC heap moves from ~5.0MB to ~5.8MB, with the last cycle
adding only ~34KB in either run; this short test supports stabilization, not a proof of no leak over
hours. Final-build checkpoints are retained separately. No frontend cache or leak fix was warranted.
The final build again has 53 requests in each of six cycles, stable 358 nodes/331 listeners, no
Dashboard maps/timers, and ~5.03→5.82MB retained heap (last cycle +31.5KB, unchanged after idle).

Authenticated idle lasts 122s including collection overhead, with **zero browser requests** in both
runs. Backend/frontend/database memory settles around 160.6/8.2/126MiB baseline and 159.1/8.2/128.5MiB
comparison; total about 296MiB. These are cgroup working-set-style Docker measurements, not private
RSS, and include this fixture's tmpfs pages. Initial/periodic samples can show backend ~30–40% and
PostgreSQL ~4% CPU during short health activity; snapshots should not be read as sustained idle load.
An additional 20.2s cumulative cgroup measurement gives 2.38%/0.42%/0.89% of one logical CPU for
backend/frontend/database, with health checks enabled. Five idle app connections remain stable.
No arbitrary zero-allocation target, health removal, polling removal or pool-size tuning was applied.
Final-build idle is again 122s with zero browser requests and five idle database connections.
Supplemental aggregate session samples have three active test sessions with unchanged count,
`last_seen_at` and `idle_expires_at` throughout the observation. Final backend/frontend/database
memory is 159.6/9.6/129.1MiB (about 298MiB total); this includes test instrumentation, media and tmpfs
costs, and is not a lower-RAM capacity guarantee.
The final supplemental 20.0s cumulative cgroup counter delta is 1.61%/0.24%/0.60% of one logical
CPU for backend/frontend/database. It includes enabled health checks, and should be interpreted with
the short observation window and uncontrolled host load. These values are measurements, not limits.

Startup (already-built images, one fresh Compose start per tree): database healthy 5.9s both;
explicit migration 3.5/3.6s; backend/frontend fully healthy 12.1s both; fixture 4.5/4.2s. Migration and
fixture are not application startup. Health cadence affects these times. There is no startup speedup
claim or measured peak-build-memory guarantee. Runtime has one Uvicorn process plus init, nginx
master/eight workers plus init on this eight-CPU host, and PostgreSQL background processes plus five
idle pooled connections; no Vite, Node runtime or reload watcher is in application images.
Final start reports database health 5.8s, migration 2.7s, full application health 11.5s and fixture
3.1s; unchanged control timings are also lower in that run. No startup optimization was made.

Images before/first comparison (Docker logical uncompressed size): backend 227,178,144/227,180,587
bytes, frontend 54,607,769/54,619,224, PostgreSQL 303,729,906 unchanged. Shared image layers mean summing
these is not an exact disk requirement. No image/package/security-update removal was justified.
Final image sizes are backend 227,180,587 bytes, frontend 54,619,675 bytes and unchanged PostgreSQL;
image IDs and runtime-source SHA-256s are recorded in `after.json` so the unstaged tree is identifiable.
Media/fixture sizes and application runtime cost are modest on **this** ~7.36GiB host; no lower-RAM
or ARM deployment was tested. Reserve RAM/storage for host services, the proxy, PostgreSQL persistence,
media growth and backups. A constrained operator should use production runtime images and run
builds/tests serially. Concurrent verification/builds on this host left ~153MiB available RAM and
heavy load; those intervals were excluded from benchmark comparisons and checks were serialized.

## Remaining costs and release sanity

- Full directories retain the accepted complete-record contracts. SeedLot transfers ~233KB, Plants
  ~193KB, geography ~146KB and Events ~604KB for this fixture; Events/query serialization and typed
  search remain noticeable costs. Do not silently trim fields, paginate, change filters or add broad
  caches without a separate product contract and new measurements.
- On-demand thumbnails cost ~32ms here because safe image decoding/transformation remains on request;
  private ETag/cache behavior and authorization stay intact. Large original archives need operator
  storage planning. External image opt-in is unchanged.
- Initial lazy splitting adds module requests and slightly more total code for someone who visits all
  workspaces; first-load paint/slow-network claims need separate measurements. CSS still includes the
  existing Leaflet styles. No speculative manual chunks or CSS redesign was added.
- Maps and providers remain separate, explicit and network-dependent. Controlled fixtures demonstrate
  initialization/cleanup but not live populated density throughput. Real external-provider errors,
  attribution, tile proxy authorization, privacy and HTTPS need RELEASE-001 sanity checks.
- Repeat the fixed API/browser workload on the exact release tree, inspect initial asset transfers,
  bounded query counts, unchanged payloads, media behavior, no unrelated map/QR/provider work, six
  navigation cycles and two-minute idle stability. Repeat on actual target hardware/persistent storage
  and HTTPS before describing its resource capacity. No statistical tail or hardware guarantee is set.
- Confirm preserved security, migrations, installation/upgrade/recovery and accepted mobile/keyboard
  workflows in RELEASE-001; this performance report does not replace release acceptance.

## Verification and handoff

Implementation-side verification ran serially on the final runtime source:

- `make check` completed with exit 0: Ruff formatting/lint, Prettier, zero-warning ESLint, strict
  mypy (215 source files), TypeScript, 425 backend unit tests, 230 frontend tests in 25 files, and
  `make api-check` with no generated-artifact drift. **Coverage caveat:** pytest printed
  `FAIL Required test coverage of 90% not reached. Total coverage: 89.82%`, even though its process
  and `make check` continued successfully. Independent review inspected `backend/pyproject.toml`,
  Makefile/CI invocations and installed coverage.py 7.15.4/pytest-cov 7.1.0 source. Coverage
  precision is not set, so coverage.py defaults to zero decimal places; its threshold comparison is
  `round(total, precision) < fail_under`, and 89.82 rounds to 90. pytest-cov separately prints its
  red `FAIL` text from the unrounded total in `pytest_terminal_summary`; that hook does not set
  pytest's exit status. The displayed message is misleading while the configured whole-percent gate
  passes. The repository's `--cov-fail-under=90` and zero-precision default are unchanged; no
  coverage policy was weakened or reinterpreted during review.
- `make test-integration`: 357 passed, 425 deselected, 118 warnings in 132.97s; existing isolated
  PostgreSQL/migration/security suites plus the three new query-count regressions. A separate focused
  query-count run passed all three cases in 3.81s.
- Development-focused runs passed 36 backend cases and 54 frontend cases before the broader suites.
  Host Python 3.12 could not collect existing `uuid7` imports; Docker Python 3.14.7 was used for the
  successful backend checks. The initial integration run was interrupted under host memory pressure;
  its fixture's invalid second geography root was corrected by reusing the migrated root. Initial
  frontend failures from synchronous lazy-route assertions were corrected with readiness awaits,
  preserving assertions and timeouts, then the full suites above were rerun successfully.
- Production runtime images built successfully with the unchanged Vite warning threshold and no
  large-chunk advisory. Four benchmark isolation-guard tests pass without Docker; helper Python
  formatting and `ruff check --select E,F,B scripts/perf` pass. No CI timing/resource assertion was
  added. Static gzip, `Vary`, MIME, identity fallback, runtime configuration caching, health and
  protected API integrity are checked by the final transfer measurement. A separate Chromium probe
  rewrites the real SeedLot chunk request to a nonexistent asset; production nginx returns the SPA
  HTML fallback with status 200 and `text/html`, exercising the actual browser dynamic-import MIME
  failure. The error message appears, the authenticated shell remains, no page error escapes, and no
  document reload occurs automatically.

Regression coverage includes read-only hierarchy lookup/integrity errors, a shared directory lookup,
constant service SQL counts at 1 and 20 records for all three collection response builders, deferred
workspace initialization/module reuse, rejected-chunk recovery with the shell retained, and isolation
guards that reject durable volumes, published database ports, the wrong/existing project. Existing
authentication, privacy, primary photos, lineage, germination, labels and propagation suites remain
in the broad checks. Render-loop investigation uses request quiescence, stable DOM/timers and idle
activity; this run does not instrument React commit counts or claim to reduce individual renders.

Independent review narrowed workspace recovery after confirming the original boundary mislabeled all
render exceptions as failed downloads. Only recognized browser `TypeError` messages for dynamic-module
fetch or module MIME failures receive the dedicated chunk error; ordinary import/evaluation and render
errors propagate. The optional provenance and occurrence maps use the same classifier. Tests cover the
browser fetch rejection shape, unrelated module errors and ordinary component render failures. On the
rebuilt production image, I temporarily hid the actual generated Seeds chunk in the disposable
container; its URL returned nginx's status-200 SPA fallback (`text/html`, 578 bytes), Chromium showed
the recovery message with the authenticated shell intact, and access logs showed no automatic document
reload. The response helper checks `Vary`, MIME preservation, identity fallback, runtime-config
no-store behavior, health and protected API representation.

A fresh independent run rebuilt and started the reviewed production topology from tmpfs, migrated and
seeded the same fixture, then completed all 28 authenticated reads. The fresh 160-row results were 10
SQL statements for SeedLots and Plants and 6 for PlantGroups; their payload lengths remained
233,095/193,055/91,187 bytes. These timing medians (59.3/63.7/37.6ms) are one new host-specific run,
not replacements for the saved seven-sample comparisons. The final transfer check measured the built
entry JS/CSS at 208,364/100,981 raw bytes and 75,883/28,679 gzip bytes, retained `Vary: Accept-Encoding`,
left the 604,487-byte authenticated Events response uncompressed and byte-identical, kept runtime
configuration uncompressed with `no-store`, and confirmed `/healthz` is uncompressed `text/plain`.
The health check exposed a duplicate content-type header in the previous nginx config; using
`default_type text/plain` fixes it without changing the response body or status. Current reviewed
image and source hashes are recorded in `after.json` separately from the original baseline.

No migration is added; Alembic remains `20260925_0026`. Existing migrations were exercised by the
integration suite and each fresh fixture start. No new index or SQL plan change had measured
justification. The independent `make feature-verify` run passed all stages, and `PERF-001` is now
`verified` in the feature graph. The branch remains unstaged and uncommitted; no push, delivery,
merge or branch finish was performed.
After measurements, only the `florabase-perf` containers/network were removed; no named volumes were
deleted, and the operator's frontend/backend/database remained healthy. The branch remains
`feat/perf-001` with an empty index and all intentional changes unstaged/uncommitted.

Intentional files:

- Runtime: `backend/src/florabase/geographic_places/{api,service}.py`,
  `backend/src/florabase/{provenance_sites,seed_lots,plants}/service.py`, `frontend/src/App.tsx`,
  `frontend/src/components/WorkspaceBoundary.tsx` and `frontend/src/components/workspaceChunk.ts`,
  `frontend/src/occurrence-map/OccurrenceMapPanel.tsx`,
  `frontend/src/provenance-sites/ProvenanceSiteManager.tsx`, `frontend/nginx.conf`.
- Tests: `backend/tests/test_geographic_place.py`,
  `backend/tests/integration/test_performance_responses.py`, `frontend/src/App.lazy.test.tsx`,
  `frontend/src/components/WorkspaceBoundary.test.tsx`; readiness updates in `App.test.tsx`,
  `Propagation002.test.tsx`, `import-export/ImportExportScreen.test.tsx`,
  `seed-lots/SeedLotScreen.test.tsx`.
- Narrow disposable measurement tooling: `compose.perf.yaml`, and `scripts/perf/{compose.sh,
fixture.py,measure.py,browser.mjs,verify-chunk-recovery.mjs,profile.py,plans.py,test_measure.py}`.
- Documentation/evidence: `docs/performance/{PERF-001.md,baseline.json,after.json}`,
  `docs/{architecture,deployment,development,product-roadmap,progress}.md`, `docs/features.json`.

The environment/dataset/protocol sections cover handoff items 1–3; immutable baseline and backend
comparison cover 4–8; frontend/maps, repeated navigation/idle and footprint cover 9–11; this section
covers migration/files/tests/checks (12–16); remaining costs/resource expectations/release sanity
cover 17–19. Large raw profiles/plans, browser/cache artifacts and fixture binaries stay in `/tmp`.
