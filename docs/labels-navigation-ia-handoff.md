# IA-FREEZE-001 — final Labels, Settings and navigation handoff

Current candidate: `feat/ia-freeze-001`, based on `3fbf0ca4b3948844c71ff39ba26a34c5941a964e`,
provided `/home/alessandro/.codex/worktrees/4ff7/florabase`. Independent delivery review and the
canonical full verification gate passed on 2026-10-14. The tree is ready for the reviewed local
commit and protected delivery workflow. Global visual review and actual theme implementation remain
outside this increment.

## Final physical label content

Printed sheets and screen paper contain only **exact-record QR**, **scientific botanical name**,
**cultivar when recorded**, **common name when recorded**, and a tiny material-category glyph.
There is no printed stock display name, UUID, route ID, Location, source, acquisition, quantity,
material-type text, classification hierarchy or taxonomy breadcrumb at any size.

The existing BotanicalIdentity `common_name` field supplies common name through the current batched
identity read. Blank/unknown names are omitted; no fallback name is invented. Scientific names use
the bundled botanical serif/italic; rank/uncertainty markers and cultivar remain roman. Cultivar is
quoted on its own line, with common name as secondary roman text. Names wrap through the available
label height. Only final printed name blocks participate in measured overflow warnings.

Application pickers/Selected material retain useful human context and acquisition/quantity/source
semantics to distinguish records. Normal rows omit UUIDs. Label content explicitly distinguishes
**Printed names** from **Record details (not printed)**. Removed fields cannot create false print
warnings, but real scientific/cultivar/common-name clipping remains visible.

## Presets, freed space and print geometry

| Preset | Cell       | Grid / capacity | Horizontal / vertical margins | QR    | Scientific / cultivar / common |
| ------ | ---------- | --------------- | ----------------------------- | ----- | ------------------------------ |
| Small  | 40 × 20 mm | 5 × 13 / 65     | 5 / 18.5 mm                   | 16 mm | 8 / 7 / 7 pt                   |
| Medium | 50 × 30 mm | 4 × 9 / 36      | 5 / 13.5 mm                   | 24 mm | 10 / 8 / 8 pt                  |
| Large  | 70 × 40 mm | 2 × 7 / 14      | 35 / 8.5 mm                   | 32 mm | 12 / 10 / 10 pt                |

Padding is 1 / 1.5 / 2 mm and horizontal text/QR gap 0.75 / 1 / 1.5 mm. The old bottom metadata
band is gone; names use full interior height with wrapping. Medium/Large QR grows from 21/25 to
**24/32 mm**, and scientific type from 9/11 to **10/12 pt**. Small retains its 16 mm QR and
prioritizes scientific name before optional cultivar/common name. Its adjacent category mark fits
below the quiet zone within the cell. Large has breathing room without reintroducing metadata.

Cell grids, named A4 margins and absolute print offsets remain deterministic. Screen paper scales
proportionally; print retains millimetres/point type. Mixed batches have exact sources, positive
copies, a 360-label cap, final blank cells and no extra trailing page. Temporary size changes do
not alter the saved default; Print format shows Default or explicit Set as default.

Print at **100% / Actual size**, no Fit to page or browser headers/footers. Browser print/raster
checks do not certify a physical printer, adhesive stock, camera scanning or native print dialog.
Temporary QA PDFs are not a PDF-generation product feature.

## QR payload, glyphs and scannability

Payload stays solely the saved validated public origin plus the existing exact authenticated route:

| Source          | Route after saved origin                            |
| --------------- | --------------------------------------------------- |
| Seed lot        | `/#/seeds/<id>`                                     |
| Plant           | `/#/plants/<id>`                                    |
| Plant group     | `/#/plant-groups/<id>`                              |
| Stored material | `/#/harvests/<harvest-id>?inventory=<inventory-id>` |

Stored material focuses the exact managed item, including on an already-open Harvest. No botanical
name, common name, classification, operational text, browser query, credential or token is encoded.
Existing authentication/authorization remains in force; no second routing vocabulary is introduced.

Pinned local SVG generation uses H correction, full four-module quiet zone and black/white contrast.
A tiny category vector means material type, never taxonomy. Insets avoid functional patterns and
stay under 2.5% of modules; Small uses a clean QR plus an adjacent mark. Unsafe insets also fall
back adjacent. Payloads below **0.22 mm/module** block printing at that size. Unconfigured/loading/
failed settings permit inspection but block Print and browser-menu label output safely.

## Shared public QR destination dialog

Labels now shows **QR destination + Edit**, rather than requiring a Settings page transition.
Edit opens a small native TaskDialog, prepopulated with the current public URL. General and this
contextual editor use the same `savePublicQrBaseUrl` helper and existing settings API/domain.
Server validation remains authoritative and shared: HTTP(S), authority, maximum 200 characters,
no credentials/path/query/fragment, safe normalization of host/default port/trailing slash.
Blank explicitly clears to null. No current-browser/login/preview-origin fallback exists.

Save reads current settings to retain the latest saved default preset, persists, closes and
immediately regenerates destination/QR. Selected records, copies, picker state and current temporary
preset survive. Validation/failure retains the draft and offers retry. Pending save prevents
Cancel/Escape/backdrop dismissal. Pristine dismissal closes; dirty dismissal asks to Continue
editing or Discard changes. All paths restore focus to Edit. Clearing disables printing without
clearing composition. Settings → General reads the same persisted value when opened.

Settings stays a focused single page with **General** and compact **Tools** links to canonical
Labels and Import / Export routes. No duplicate label default selector or empty future tabs.
Labels → Print format still explicitly persists the installation default. Neither setting uses
localStorage; public URL is separate from security/login `canonical_origin`.

This correction adds no backend/API/schema/dependency change. Earlier migration **20261013_0042**
creates only typed singleton preferences, Medium/unconfigured defaults and constraints. Startup
never migrates; downgrade loses only preferences. The existing unmapped `app_metadata` is an
infrastructure initialization marker. Generated OpenAPI/TypeScript from that earlier addition remain.

## Theme icon cycler and footer hierarchy

Theme is one quiet **icon-only button**: monitor **System → sun Light → moon Dark → monitor System**.
There is no menu, popover or visible explanatory paragraph. Title/accessible name says
**Theme preview: [mode]. Theme switching is not enabled yet.** Each click or keyboard activation
changes only the SVG and those labels. A shared in-memory preview state keeps desktop/mobile footer
instances consistent. No colors/tokens, backend settings or localStorage change; actual theming
remains deferred and the preview resets when the application shell is recreated.

Signed-in identity precedes labelled gear Settings and the compact Theme icon; Sign out is a separate
quiet account action. Expanded sidebar, narrow/zoomed desktop and mobile More retain accessible
names and focus-visible targets. Collapsed desktop means hidden navigation, with Show navigation
restoring the same workspace and footer access. Primary groups stay **Overview → Collection →
Activity → Explore → Sourcing**. Maps remains a non-actionable three-child subgroup; Geography stays
outside it. Plant groups/Stored material remain local modes. All routes, contextual labels and
modified-click navigation semantics remain intact.

## Focused verification and visual evidence

Implementation-owner baseline **53 frontend tests / three files** passed. Its reported final serial
**147 tests / six files** remains useful evidence, not independent acceptance. Independent review ran:

- Application-settings backend unit suite: **23 passed**.
- Settings API, settings migration, and updated schema-table integration suites: **26 passed** in
  the isolated PostgreSQL workflow.
- Labels frontend suite: **54 passed** and lazy navigation: **1 passed** in an isolated serial run.
- The broader selected frontend run passed **246/249**; three Labels tests timed out under host CPU
  and full-swap pressure. The full Labels suite and affected lazy-navigation test passed separately;
  no test timeout or assertion was changed. Other selected app, Settings, Theme, Plants, Seeds,
  Stored material, and Sowing tests passed in that broader run.
- Independent ZXing-C++ **3.1.1** rerun: **48/48** checks across four source kinds, three presets,
  300/200 dpi, slight blur, and complete printed labels.

Scoped formatting/lint, strict typing, production backend/frontend builds, generated API checks,
feature graph, whitespace and exact-tree receipt passed in `make feature-verify`. The candidate adds
application settings and migration 0042, so backend/API/migration verification was required. The
independent integration run exposed a stale expected table set in the existing botanical-identity
schema test; the test now includes `application_settings`. The stale Settings navigation assertion
was corrected to follow the actual Settings → Tools section links. The first canonical run stopped at
the verification-map coverage test because the new backend package was unclassified; the module is
now explicitly included in the map's FULL prefixes. This keeps its future changes on the all-checks
path. Three stale Import / Export test navigations now follow Settings → Tools. Lazy-route assertions
allow up to five seconds for chunk loading; their assertions are unchanged. Final canonical results:
**939 backend unit tests, 734 PostgreSQL integration tests, and 664 frontend tests passed**. Workflow,
lint, formatting, strict typing, API drift, backend/frontend production builds, and the full 0041 ↔
0042 migration cycle passed. Migration-cycle cleanup verified zero owned container/network/volume
residuals. The exact-tree receipt was recorded. The local Quality-only Compose profile caps Vitest at
one worker to prevent host resource contention; all files and assertions still run. No product
behavior or validation was weakened.

Actual review matrix: **1440×844 at 80/100/125/150%; 1024×844 at 100/125%; 390×844 at 100%**.
It checks all three icon states, footer access, QR dialog in bounds, no horizontal overflow,
Small/Medium/Large screen/print dimensions, preview width and default control. All optional-name
combinations (neither, cultivar only, common only, both) and long scientific/cultivar/common/combined
stress use read-only intercepted fixtures, never domain writes. Independent decoder samples come
from actual print-media A4 PDF rasterization with complete quiet zones and full physical labels.

- [Current browser evidence](review/labels-navigation/final-browser-evidence.json)
- [Current Labels](review/labels-navigation/final-workspace.png)
- [Narrow QR dialog](review/labels-navigation/final-qr-dialog-390-100.png)
- [Theme monitor](review/labels-navigation/final-theme-1440-100-system.png),
  [sun](review/labels-navigation/final-theme-1440-100-light.png),
  [moon](review/labels-navigation/final-theme-1440-100-dark.png)
- [Current decoder evidence](review/labels-navigation/final-qr-decode.json)
- [Review evidence guide](review/labels-navigation/README.md)

`cleanup-*`, `refinement-*` and unprefixed UI images are historical and do not prove this final
printed-content/dialog/theme contract. Headless regression uses DOM activation and a private
extension for true zoom, with renderer settling between print and screen media. Native connected-
browser checks separately exercise keyboard/pointer theme cycling, dirty Escape, normalized Save
and focus return. Physical printer/system-dialog acceptance remains with the operator.

All **seven** boundaries and **21** preset screen/print geometry probes pass within **0.02 mm**.
**12** optional-name/preset combinations fit without warnings; **12** long-name/preset stress cases
warn on real clipping. All **12** actual print-media PDFs are one-page A4 within Chromium's 0.5 pt
page rounding tolerance. Independent ZXing-C++ **3.1.1** passes **48** checks across four categories
and three sizes: QR at 300/200 dpi, slight 0.4 px blur, and complete label at 300 dpi.

Initial combined runs had timeouts in unchanged directory/mixed-batch tests while swap was full;
those tests passed unchanged in the final serial run after owned browser resources retired. No
repository timeout or assertion was altered. The first PDF harness mistakenly retained screen
media; those temporary samples were replaced with explicit print-media A4 output before decoder
acceptance. The final print harness completed cleanly and drained response interceptors before close.

A broad earlier Alembic autogenerate probe found pre-existing unrelated schema drift (unmapped
`app_metadata`, botanical-profile constraints and old indexes/names). It is not claimed clean; the
new settings table comparison and actual migration cycles passed. This UI correction does not
reconcile unrelated schema.

## Review environment and preservation

Browser/decoder review uses uniquely owned **florabase-uat-preview-smoke-bff8e2a5be73**, seeded
from existing v4 fixtures. Repeated seed preserves fixture state. Only its application preferences
are changed; name stress alters browser responses. Final exact retirement and before/after
protected snapshots are recorded in [current preservation](review/labels-navigation/final-preservation.json).
Exact retirement removed **4 containers, 2 images, 1 network and 3 volumes**, with **zero owned
residual resources**. Disposable domain rows, fixture manifest and media match after review;
repeated seeding also matched. Shared cache, Quality, unknown and protected resources are retained.
Persistent UAT is never reset/reseeded/synchronized/migrated or used for settings writes by this
correction.

Current protected runtime identities/states/mounts/volumes and primary Git identity match. Every
other protected database digest matches. The live UAT raw dump digest differs; one authentication
session was seen during review. No per-table baseline was captured, so the exact cause and full
live-UAT data equivalence remain **unproven**. No live state was reverted to force a match.

The prior cleanup snapshot matched protected resources and available raw DB digests. An earlier
QR/preset review had a differing live-UAT digest with authentication activity and no per-table
baseline; that older full data equivalence remains unproven. The independent read-only UAT check
signed in with its synthetic account, read the existing General setting and composed a temporary
SeedLot label. It did not save settings or collection data. Login refreshed authentication session
activity, so a later raw digest difference alone does not establish data loss. No per-table baseline
exists to reconstruct the historical variance; exact cause and complete live-UAT data equivalence
remain unproven. Later matching comparisons do not retroactively resolve it; see historical
`refinement-preservation.json` and `cleanup-preservation.json`.

## Freeze readiness and deferred work

**FUNCTIONAL_IA_FREEZE_READY** is reconfirmed after independent review, full canonical verification,
and resized decoder review: no material v0.1 workflow/IA issue remains in QR editing, label content or navigation. Actual
System/Light/Dark themes, mobile QR capture/PWA, Location labels, arbitrary templates, thermal
protocols, partially used sheets, PDF product generation, global visual normalization, future domains
and release benchmarking remain deferred. Physical printer/stock/native-dialog acceptance remains
deferred. Canonical verification is complete; reviewed local commit, protected PR delivery and
conservative feature finish remain in progress.

**FUNCTIONAL_IA_FREEZE_READY**
