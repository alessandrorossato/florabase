# Final directory interaction correction — 1 November 2026

Current follow-up: [Details consolidation and botanical cover fallback](../details-cover/README.md);
this earlier milestone is retained as historical evidence. Final operator UAT is pending.

Pending final operator UAT. This is an uncommitted follow-up to
`db1e71fb85f1396408ed6f07800d4992dea0233d` on `feat/ui-system-v1-wave3` in worktree `548f`.
Batch 1 checkpoint `3669869` and independent QA/Schedule reconciliation `d09fd86` remain ancestors.
No FULL, push, PR, merge, delivery commit or feature-finish has run.

This operator-confirmed contract replaces the earlier interaction-cleanup interpretation.
The older 397/412-test and Preview screenshot sets are retained as historical evidence.
Use [the current evidence gallery](evidence/index.html), [verification](verification.txt),
[the exact changed-file inventory](changed-files.txt), and the UAT checklist below.

## Root causes and corrections

Seeds, Sowings and Plants previously kept the directory mounted when entering a full record.
After the inspector geometry changed, Details could flow underneath the list. The correction
makes directory and full Details/editor composition mutually exclusive and assigns the full
record its own workspace class. It changes actual rendering and route activation, rather than
hiding content or scrolling past the list. Existing Overview, lineage, journal and photo tabs remain.
Geography Places likewise renders its hierarchy and dedicated record exclusively.

Direct Edit exposed another dependency on the removed Preview: Sowings and Plants did not
initialize the selected record before opening their editor. They now initialize the correct
record and draft directly. Existing save, eligibility, dirty-dismiss and pending guards remain.
Botanical identity direct Edit also now reopens when browser Back restores its Edit URL.
An authoritative identity returned by duplicate selection remains available to full Details
while the directory refreshes. Supplier Edit and identity Back restore connected focus targets.

Hierarchies needed a third layout track for their direct actions; without it, icons wrapped
beneath the branch. Shared hierarchy CSS now keeps chevron, record and actions aligned and
wraps long names/statuses safely. No domain hierarchy was flattened.

## Current compliance matrix

| Surface              | Activation and direct actions                                               | Creation menu / preserved distinction                                                                                   | Evidence                                                         |
| -------------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Seeds                | Row/card → dedicated Seed Details; direct Details/Edit                      | Active eligible Start sowing; exact/approximate/unknown/zero quantities retained                                        | Seeds suites, desktop/mobile Details and menu captures           |
| Sowings              | Row/card → dedicated Details; direct Details/Edit                           | Create Plant, Create Plant group, Record germination under existing eligibility; seed source/lineage/lifecycle retained | Sowings suites, actual germination and group-creation navigation |
| Plants / groups      | Row/card → correct kind's Details; direct Details/Edit                      | Existing Record harvest; extraction, transfer, reintegration and provenance stay on their owners                        | Plants suites and live Details/Edit                              |
| Harvests             | Historical row/card → Harvest Details; direct Details/Edit                  | No invented row creation menu or lifecycle; owned Event/material/history retained                                       | Harvest suites, live Details/Edit and responsive captures        |
| Stored material      | Exact Harvest inventory destination; direct Details and inventory Edit      | Active seed conversion only; correction, disposition, printing and removal stay in Harvest owner                        | Inventory regression, live exact Edit and Escape/focus           |
| Suppliers            | Row/card → Supplier Details; direct Details/Edit                            | No empty creation menu; usage, lifecycle and sourcing relationships retained                                            | Supplier and App suites; live direct commands                    |
| Orders               | Row/card → Order Details; direct Details/Edit                               | No empty creation menu; authoritative server pagination, prices, partial dates and links retained                       | Order suites; row Enter and live editor                          |
| Botanical identities | Row → identity Details; direct Details/Edit                                 | Add seed lot/plant and owned source-choice dialogs for sowing/harvest; no invented lifecycle                            | App/UX001/UX004/source-action suites and live Edit/Back          |
| Locations            | Chevron expands; row/direct Details opens full record; direct eligible Edit | Explicit scopes, direct/inclusive counts, parent protections and creation retained                                      | App hierarchy/guard cases; three widths                          |
| Geography Places     | Chevron expands; row/direct Details opens full record; custom-only Edit     | Canonical/local distinction, protected parent rules and local creation retained                                         | App geography cases; three widths and full Details               |

Quick Preview, its placeholders and reserved columns are absent from all ten listed workspaces.
Shared inspector APIs remain for consumers outside this scope. No Schedule, Journal, History,
Taxonomy graph, Maps, Media, Settings, schema or API behavior was redesigned.

## Shared impact and status mapping

`DirectoryRecordActions` exposes direct bordered Details/Edit and a separate creation-only menu.
Existing `OverflowMenu` retains mounted owned dialogs where required; event handling prevents
portal actions from activating the underlying row. Domain callbacks and native route targets
remain page-owned. Borders, hover and focus follow existing shared button controls.

`LifecycleStatus` and `status.css` provide one textual mapping: success = Active/Completed;
danger = Dead/Failed/Abandoned/Lost; warning = Transferred/Cancelled; muted = Exhausted,
Depleted, Discarded, Reintegrated, Archived, Retired, Reversed, Inactive and Unknown.
Labels retain exact domain distinctions. The measured semantic text/surface contrasts across
all six themes range from **5.90:1 to 9.08:1**; text is always present.

Eight record directories were captured at 1024 and 390 CSS px with no document horizontal
overflow or Preview nodes. Desktop records, creation menus, dedicated Details and both
hierarchies are also captured. Six Sowings theme captures and measured semantic tokens cover
status styling. These are representative browser checks, not every page × theme × state.

## Operator UAT checklist

1. Open Seeds, Sowings and Plants in List/Gallery. Activate a row with pointer and keyboard;
   Details must replace the directory and retain Overview and other record tabs. Back must
   retain meaningful search, filters, presentation and page context.
2. Open direct Edit from each applicable directory. Confirm the correct record and existing
   editor. Cancel/Escape without changes; change a field and reject dismissal to check the
   draft guard. No operation should require a Preview first.
3. Open each eligible Create or record menu. Check source-prefilled sowing, individual/group
   creation, germination, harvest and seed conversion. No Details/Edit, print or deletion in
   these menus. Historical Harvests, Suppliers and Orders have no empty creation menu.
4. Select records in supported bulk modes, including modifier selection. Rows must select
   without navigating; lifecycle eligibility, visible-page scope and bulk guards remain intact.
5. From Stored material, open Details/Edit for a specific inventory, including two inventories
   on one Harvest. Verify exact quantity/storage and Escape focus. Print/correction/disposition
   and destructive controls remain on the owning Harvest, with their existing safety guards.
6. Expand Locations/Geography independently of opening records. Check custom Geography Edit,
   canonical read-only records, parent protections, scopes and direct/inclusive counts.
7. Check long labels, photos/placeholders, status text/colors and direct action alignment at
   desktop/tablet/mobile widths and your preferred theme. No empty inspector space remains.
8. Check editor/menu keyboard focus and dismissal. An already visible tooltip is the top
   dismissible layer; Escape first dismisses that tooltip, then the menu returns to its trigger.

Physical devices, screen readers, actual browser zoom and native dirty-confirm rejection remain
operator checks. Synthetic Review navigation opened/cancelled workflows without saving or deleting
records. Historical automated 69-case Batch 1 evidence is preserved; current regression includes
its owning domain and guard suites. Passing focused checks are not final release verification.
