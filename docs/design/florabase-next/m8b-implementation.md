# Florabase Next M8 Stage B: implementation record

**Status:** experimental, committed locally only, stopped for operator visual and functional
acceptance. No canonical FULL, push, delivery or merge. Backend diff against `35f9eb2` is empty.

Stage B followed the Stage A proposal ([m8a-design-refinement.md](m8a-design-refinement.md)) and
the operator's additional findings A–C. The operator's M8B message referred to "the current M8B
implementation"; it was taken as approval of the recommended Stage A direction (R1 Herbarium Mount,
T1 Collection Bench).

## Commits (oldest first)

| Commit | Content |
| ------ | ------- |
| `e1efaa9` | Stage A design record |
| `42929cf` | **Operator finding B (P1):** Workbench panel collapse |
| `e5e7abe` | **Operator finding C:** extended Review and WFO recommendation ([m8-extended-review-environment.md](m8-extended-review-environment.md)) |
| `edc25b8` | **Audit P1:** detail tabs follow later routes; captures assert route state |
| `0495b81` | Specimen sheet, image mount, lineage stem and phone disclosure, panel default on records, Today bench |
| `a94d02f` | **Operator finding A:** ledger directory language |
| `b92e6ca` | Identity tab grid on phones; palette record identification |

## Defects found and fixed, with cause

1. **Workbench panel did not collapse (operator P1).** `.wb-shell--collapsed .wb-panel
   { display: none }` came before `.wb-shell .wb-panel { display: flex }` with equal specificity,
   so the later rule won. The panel stayed in layout, wrapped into an implicit grid row under the
   rail at the rail's width (text clipped) and kept 13 focusable controls. Fix: order the rule after
   the base rule. Regression test loads the real stylesheet (without `@media` blocks, which jsdom
   applies unconditionally) and **fails on the previous order**. Browser check at 1440 and 1100:
   collapsed panel width 0, sidebar = rail, 0 reachable panel controls, Tab moves into the page,
   six further toggles stable, phone strip still shown at 390, desktop state restored on resize,
   another workspace reopens it. Captures: `.florabase-next-evidence/m8-panel-collapse/`.
2. **Plant lineage capture equalled Plant detail (audit P1).** Cause in the app, not only the
   capture: Plant, Sowing, Seed lot and Supplier read `?tab=` only on mount, so a route to another
   tab of the already open record (for example the Record sheet's lineage action) changed the
   address but kept Overview selected. Fix: the render-time sync the Botanical identity screen
   already used. Regression test **fails on the previous Plant screen**. The capture script now
   refuses an image whose address or selected tab differs from its route and flags byte-identical
   distinct keys; run against the previous Plant screen it refused `plant-lineage` with
   "selected tab 'Overview' != 'Lineage'".

## Audit and operator findings: status

| Finding | Status | Notes |
| ------- | ------ | ----- |
| Specimen hierarchy, soft images (P1) | Built | Herbarium sheet aside; 60px serif title; larger scientific name; plates uncropped and never enlarged beyond 2× natural size (`RecordVisual` reports natural size; CSS caps it) |
| Missing-photo stripes (P1) | Built | All four striped backgrounds replaced (plate, directory card, Today); flat mat, inset hairline, small mark |
| Today (P1) | Built, partly | Bench of small sheets above the work; Recent activity beside Next work; compact work windows; one visible search (shell search hidden on Today, Ctrl/⌘K kept). The four counts became a lighter ledger row, **not** the one-line form of the proposal: their "derived" context lines are kept |
| Phone record detail (P1) | Built | Identity row (image beside title), actions grid, lineage folded to a disclosure row, one-row tabs. The proposal's context bar replacing the workspace strip was **not** built: Back and New stay, in one compact row |
| Phone directories ≤ 240px (P1) | Built, near target | First record at Suppliers/Orders 236px, Seeds/Sowings 244px, Plants 247px (M7 264–272px); Harvests 284px (its extra Harvests/Stored material switch). Filter chips were **not** moved into the Filters button (shared DirectoryTools markup) |
| Lineage capture (P1) | Fixed | Above |
| Identity tabs on phone (P2) | Built | 3 × 2 grid |
| Command palette (P2) | Built, partly | Glyph per kind; italic identity line. Per-kind group headers with totals were **not** built |
| Sparse Almanac (P2) | **Not built** | Season strip remains a proposal |
| Directory language (operator A) | Built in shared CSS, partly | Seeds, Sowings, Plants/groups, Harvests, Stored material, Suppliers, Orders and Botanical identities through the shared records list. Unknown quantities marked in Seed lot and Plant group summaries. **Not covered:** Locations (its own hierarchy list), Journal/History rows and the Taxonomy list/inspector, and column captions; these remain proposals on the canvas (page 5) |
| Panel collapse (operator B, P1) | Fixed | Above |
| Extended Review + WFO (operator C) | Reported, not activated | No supported environment combines v5 and WFO today; see the environment report |
| Record pages: panel collapsed by default | Built | The rail reopens it there; saved preference unaffected (test) |

## Intermittent and order-dependent tests

| Test | Evidence | Classification |
| ---- | -------- | -------------- |
| App: identity section keyboard navigation retains Back/Forward | M8: 0 failures in 21 orders of `App.test.tsx` (default + `--sequence.shuffle --sequence.seed=1…20`) and 12 runs under contention (6 parallel copies × 2), in the isolated Quality environment. With M7's 30 runs: 63+ consecutive passes since the single M6 failure | **Not reproduced.** No product defect found; the test was not changed. Remains tracked |
| App: location hierarchy renders paths and supports keyboard selection | Fails deterministically with `--sequence.shuffle --sequence.seed=3` (2 of 2): "Unable to find … list "Location hierarchy"". Passes in default order | **New finding: order-dependent test isolation defect** (state from a preceding test in that order; storage and width are reset). Not yet checked against main |
| App: Geography dedicated record states | Failed once with seed 18, passed on repeat | Intermittent, unclassified |
| Schedule: pending save cannot dismiss or submit twice… | Failed once in 3 full suite runs on the final tree; 10/10 in isolation; 2 further full runs 1210/1210 | Intermittent under load, unclassified; detail not captured |

Reproduce: `python3 ./scripts/workflow_environment.py quality compose -- run --rm --no-deps -T frontend sh -c 'pnpm exec vitest run src/App.test.tsx --sequence.shuffle --sequence.seed=3'`.

## Checks on the final tree (`b92e6ca`)

- `pnpm format:check`, `pnpm typecheck`, `pnpm lint` (0 warnings), `pnpm build`: pass.
- Full Vitest: 1210 tests; 1209/1210 on the first run (Schedule intermittent above), then
  1210/1210 and 1210/1210.
- Main bundle 285.7 kB (gzip 88.0 kB); M7 285.0 kB (87.8 kB).
- Contrast of every new text pair ≥ 5.70:1 (light and dark); decorative placeholder marks
  3.49:1 light, 4.11:1 dark.
- Backend diff against `35f9eb2`: empty.

## Not performed

Manual screen reader, physical zoom, Windows High Contrast and touch-device passes; Android QR.
Live activation of the extended Review environment and WFO (awaiting approval).
