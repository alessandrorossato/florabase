# ENG-02 bundled security headers source evidence

Standalone source at the verified base `fdc75e83fa8818cab791ed82cbba65f4f97db7ae`, prepared
2026-11-19 for independent security review. ENG-02 remains optional under the
[release scope](../scope-v1.md#3-optional-pre-10-improvements). Its two criteria are registered in
the [release acceptance table](../acceptance-v1.md#optional-pre-10-improvements). The base feature graph and
machine-readable release manifest have no ENG-02 row.

The initial browser campaign and production results below apply to source
`b31048dd332e8ac6e21753b11f21a5fcac765a8c`, tree `dad6eb225dc905edb5981fb83bc5f41299d0ec0e`.
The focused corrective checks are recorded separately at the end.

1. **A bundled nginx response for `/` has nosniff, a referrer policy, a frame restriction and
   CSP.** The 19-response portable smoke check passed. It checks one copy of each header with
   its exact value on the root, SPA fallback, static cache locations, liveness, readiness and
   both API proxy locations, including 401 and 404 responses. Separate probes covered a 304
   with revalidation, an nginx-generated 413, and a 502 during a backend outage.
2. **Every inventory page loads in a light and a dark theme without policy violations, including
   external images and configured tiles.** A Chromium sweep visited 62 routes per appearance,
   including all 25 destinations and subdestinations and detail and task routes with synthetic
   records. A targeted pass confirmed the record-specific label composer, command palette and
   mobile record sheet in both appearances. There were zero unexpected policy events or policy
   console messages, and no uncaught page errors in the route sweep. Repeat the complete
   inventory and shell-state matrix on the integrated release candidate.

## Policy and browser observations

- Bundled nginx 1.30.6 passed `nginx -t`. Server-level `add_header_inherit merge` keeps
  `always` security headers alongside per-location `Cache-Control`. The production image pins
  an nginx version with this directive. The outer proxy passes headers through and owns HSTS.
  [nginx headers module](https://nginx.org/en/docs/http/ngx_http_headers_module.html)
- CSP denies unspecified resources, embedded documents, plugins and base overrides.
  Scripts, stylesheets, fonts, API connections, workers, manifest and form submissions use the
  same origin. The image directive allows same-origin assets, inlined data images, blob images
  and configured HTTPS sources. The referrer policy permits an origin-only referrer for external
  tiles. External photos retain their element-specific no-referrer behavior.
- The initial strict style trial logged three enforced `style-src-attr` violations each time
  Chromium created an original-image document. Diagnostic navigation reproduced them with
  both a protected attachment URL and a blob original. CSP therefore grants inline style
  attributes specifically. A style element probe still hit `style-src-elem`; an inline script
  and a blob script each hit `script-src-elem`. Cross-origin application fetch hit
  `connect-src`, changing the base hit `base-uri`, and embedding the site from another origin
  hit `frame-ancestors`.
- Chromium 157.0.8103.38 with Playwright Core 1.65.1 used separate 1280×720 sessions for light
  and dark. Both verified a secure HttpOnly Strict login cookie, authenticated list/detail
  navigation, production CSS and 94 distinct same-origin JavaScript assets, and local Leaflet
  rendering. Each opt-in caused nine OpenStreetMap image requests with an origin-only referrer.
  Requests started only after the map toggle. An acknowledged external botanical cover and
  a one-time external media preview rendered with no referrer. The tile and external image
  requests were fulfilled with synthetic PNGs to exercise browser enforcement independently
  of provider availability.
- The browser rendered an authenticated thumbnail, opened the original in a new tab, and
  downloaded a CSV containing the synthetic identity. An isolated probe fetched an authenticated
  image and exercised rendering and opening a blob URL, and saved a synthetic blob CSV.
  Unauthenticated media reads returned 401. The original remained `private, no-store` and the
  thumbnail remained `private, max-age=86400, must-revalidate`. A foreign-Origin login and an
  authenticated logout without CSRF each returned 403.
- The service worker activated when Chromium trusted the disposable proxy certificate. An
  offline navigation served the cached offline page with its CSP, rendered the icon, and
  exposed neither the SPA root nor cached API data. The camera scanner was unavailable in
  this headless browser.

## Provenance and follow-up

- The checked-in PWA suite passed 65 tests and the offline runtime/controller suite passed
  51 tests, including disclosure. The changed portable smoke test passed Ruff checks, Ruff
  formatting and strict mypy. The new HTTP assertions ran against the disposable production
  stack. The full portable install and restore smoke was outside this source check. Prettier
  reports an existing table-alignment difference in `docs/security.md`.
- Both application images built from the actual runtime stages on Docker Engine 29.10.0.
  The frontend build used the base application tree and the nginx configuration in this source
  with SHA-256 `06f3410972b00ab14ff2ff76024c095e762fab3690ee5f9a32f7165923bd8eb5`.
  The built frontend ID was
  `sha256:9aae5d9fcf84d13462b0f25f1c404d3abb75952e6e8c710a93e4eb153ac1cf12`, and the backend
  ID was `sha256:8a0fcce28ec7d4aea84f442c2fe5d52273b762b41a22a7e9de0712d4f250bcbe`.
  The local PostgreSQL 18.6 Alpine image was
  `sha256:9ba53c7d41ea093baf5c1ba635ba5434c4f979880527d49bb7d9237d3193085b`.
  A temporary HTTPS nginx proxy forwarded browser traffic into the stack. The only runtime
  asset override set the shipped basemap flag to true with its default HTTPS tile URL.
- The targeted browser pass rebuilt the same source with frontend ID
  `sha256:588ad58926f5358605fbe4a59ba7da2bfa4bc0a3fc67781f6886fde09d036ae0` and backend ID
  `sha256:7e6f9d03571607d83741d43093fdeeb02300ee93fc88a392ed6dbb242be71e5e`.
- All runs held the shared verification capacity lock and used repository disposable ownership.
  `florabase-workflow-smoke-fa2691cffd10`, `florabase-workflow-smoke-66f8059ec8c7` and
  `florabase-workflow-smoke-d2eb963714de` each
  retired four containers, one network and two image tags, with zero owned volumes or residual
  resources. The database used tmpfs. Shared BuildKit cache was retained.
- The committed and in-progress Batch 07 path inventories at inspection covered AUTH
  (`a622ad8`), mobile directories (`39080cb`), functional and UX certification (`f54ac87`),
  the performance harness (`143bbc8`) and the Golden pin (`8184838`). The nginx, portable
  smoke or operating-guide changes are disjoint. The performance harness and Golden pin both
  edit `docs/progress.md`. Preserve all milestones when reconciling.
- After Batch 07, repeat the header matrix and test the actual protected JSON, thumbnail,
  attachment, original-open and CSV paths, including expiry and reauthentication. Recheck the
  combined candidate in both appearances with the frozen inventory, configured external
  resources and a supported deployment proxy. Independent security review, canonical FULL,
  formal ENG-02 acceptance and G-SEC remain pending.

## Bounded corrections after independent QA

- The portable header and cache checks now raise an explicit failure on a missing, duplicate or
  incorrect field. All six focused regressions passed with normal Python, `python3 -O` and
  `PYTHONOPTIMIZE=1`. An independent empty-header control was accepted by the historical code
  in both optimized modes and rejected by the corrected code in all three modes. Earlier smoke
  assertions for service identity, schema checks, credentials and logs, and persistence and
  restore also disappear under optimization. Those earlier assertions were outside this change.
- The [security baseline](../../operate/security.md) now distinguishes metadata, browser Preview once,
  owner-requested guarded Save/Refresh, acknowledged botanical covers and online tile opt-in.
- The pinned nginx 1.30.6 passed `nginx -t`. A production-runtime HTTP probe compared the
  historical and corrected nginx configurations against the same live backend. The authenticated
  thumbnail (200 and 304), attachment original (200) and CSV export (200) each carried two
  `nosniff` fields through historical nginx, one directly from the backend, and one through
  corrected nginx. The correction hides only the upstream copy of that field at the bundle
  boundary. Cache-Control, ETag, Vary, Content-Type and Content-Disposition matched where present.
  An anonymous thumbnail still returned 401 with the bundled headers. The 19-response matrix
  passed and the new authenticated thumbnail check rejected the historical configuration.
- The corrected nginx configuration had SHA-256
  `1881401e79e1ee80b4d288d05a1e58bb7af5d5c9c4bdee1ecd4d3281fda133fc`. The probe built the
  frontend image `sha256:bea0db2a20b29c7942c001d7a0ce7378e9bc6a1ebeea6b706c1e2a5dc4284a9b`
  and backend image `sha256:f874b28b35bfdabb08edc84294ad413d701aca08b30ec6eab08d3c72e162b803`.
  The disposable project `florabase-workflow-smoke-8347f042ff16` retired four containers, a
  network and both image tags. Its database used tmpfs. No owned resources remain.
- The historical browser campaign remains evidence for its recorded source. SOL's focused
  review and the combined candidate checks above remain pending.
