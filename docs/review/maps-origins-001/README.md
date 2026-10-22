# Collection origins candidate evidence

All captures use the actual React application and Leaflet renderer from the `c902`
candidate, with **synthetic API responses**. The bottom watermark and synthetic
owner label distinguish them from authenticated collection/Feature Review evidence.
No real record, persistent fixture or database was edited. This is visual candidate
evidence, not independent QA or operator acceptance.

`fixture.json` is the retained reproducible fixture: nine sites, seven with stored
coordinates, eighteen direct records, five identity IDs, two missing-coordinate
sites, one mapped site without linked records, two coincident sites, approximate
and unknown accuracy, long names/deep paths, and actual lifecycle-shaped values.
These are deliberately synthetic associations, not botanical source assertions.

| Capture | Purpose |
| --- | --- |
| [Desktop overview](desktop-overview.png) | 1440×844, 70/30 map/inspector, functional counts, local context |
| [Desktop site inspector](desktop-inspector.png) | Long name/path, exact coordinates, accuracy, identity groups, lifecycle and links |
| [Desktop provider failure](desktop-provider-failure.png) | Injected tile failure; local geometry, exact markers and records remain |
| [Tablet map](tablet-map.png), [inspector](tablet-inspector.png) | 1024×844, mounted pane switching |
| [Mobile map](mobile-map.png), [inspector](mobile-inspector.png) | 390×844, wrapped controls and paths, ordinary vertical scrolling |
| [No sites](no-sites.png), [no coordinates](no-coordinates.png) | Separate non-map Geography paths |
| [API failure](api-failure.png) | Readable failure and Retry |

Measurements and completed browser assertions are in `measurements.json`. Tile
requests are observed and then **aborted locally**, so the provider-failure evidence
is injected, not a claim about a real OpenStreetMap outage. The audit records actual
renderer-created URLs and referrer headers, never private metadata. Repeated requests
come from the deliberate responsive fits and state reloads; no remote tiles were
successfully fetched by this fixture harness.

The browser audit checks real Leaflet Enter/Space, Escape, local record visibility,
map DOM preservation through pane switches, actual Back/Forward, legacy Saved View
opening/reopening, no-coordinate/no-site/API failure and Retry, and horizontal
bounds. The screenshot loops use Fit visible sites after resizing; ordinary
inspection preserves the viewport. Some coincident/nearby marker hit areas overlap:
use keyboard markers or the textual site list to inspect every exact site. There
is no jitter, invented geometry or clustering.

Reproduce with a candidate-only Vite server on an available loopback port:

```sh
cd frontend
pnpm dev --port 15176 --strictPort --host 127.0.0.1
# From repository root, in another terminal with Playwright available:
REVIEW_URL=http://127.0.0.1:15176 node docs/review/maps-origins-001/capture.cjs
```

The harness intercepts every `/api/` request and contacts no backend. Optionally set
`PLAYWRIGHT_MODULE` and `PLAYWRIGHT_BROWSERS_PATH` for an installed runtime. The run
used the bundled Playwright package and a temporary `/tmp/maps-origins-browsers`
Chromium shell; neither is added as an application dependency.

True browser zoom, an actual screen reader and physical touch remain operator
checks. Headless keyboard zoom is attempted and recorded separately; unchanged
viewport/device ratio is not zoom evidence. Screenshot dimensions are CSS viewport
sizes, not a device or browser-zoom certification. The accepted shared mobile shell
retains its bottom navigation; the map/inspector panes use document scrolling on
narrow screens. Generalized 1:110m geography is context only and lacks local detail.

Feature Review 15174 and its persistent data still belong to delivered `b139`.
No replacement, startup, removal, reseed or adoption occurred. Live authenticated
candidate acceptance requires a separately authorized available Review slot.
