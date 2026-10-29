# Critical UX review and page-archetype decisions

The same questions were applied to all 28 page families (27 primary/contextual groups plus shell). KEEP means the composition serves its task; it does not waive shared P1 fixes. REFINE means the current information architecture survives. REDESIGN means information hierarchy or interaction allocation changes substantially. Evidence IDs refer to the preceding audit, not these mockups.

## Decision matrix

| Family               | Decision     | Proposed composition                  |
| -------------------- | ------------ | ------------------------------------- |
| dashboard            | **REDESIGN** | ActivityPage + factual overview       |
| seeds                | **REDESIGN** | DirectoryPage                         |
| sowings              | **REFINE**   | DirectoryPage + DetailPage            |
| plants               | **REDESIGN** | DirectoryPage                         |
| harvests             | **KEEP**     | DirectoryPage + DetailPage            |
| stored-material      | **KEEP**     | DirectoryPage                         |
| locations            | **REFINE**   | DirectoryPage + DetailPage            |
| journal              | **REFINE**   | ActivityPage                          |
| history              | **KEEP**     | ActivityPage                          |
| schedule-list        | **REFINE**   | ActivityPage                          |
| schedule-calendar    | **KEEP**     | CalendarWorkspace                     |
| identities           | **REDESIGN** | DirectoryPage                         |
| taxonomy-list        | **KEEP**     | SpatialWorkspace / current list       |
| taxonomy-tree        | **KEEP**     | SpatialWorkspace                      |
| media                | **KEEP**     | MediaWorkspace dependency             |
| geography            | **KEEP**     | SpatialWorkspace index                |
| native-ranges        | **KEEP**     | SpatialWorkspace                      |
| species-distribution | **KEEP**     | SpatialWorkspace                      |
| origins              | **KEEP**     | SpatialWorkspace                      |
| places               | **REFINE**   | DirectoryPage within geography        |
| sites                | **REFINE**   | DirectoryPage within geography        |
| suppliers            | **REFINE**   | DirectoryPage + DetailPage            |
| orders               | **REDESIGN** | DirectoryPage + DetailPage            |
| labels               | **KEEP**     | FormWorkspace + physical preview      |
| import-export        | **REFINE**   | FormWorkspace / staged operation      |
| settings             | **KEEP**     | FormWorkspace sections                |
| plant-groups         | **REDESIGN** | DirectoryPage variant + DetailPage    |
| shell                | **REDESIGN** | App shell around all seven archetypes |

## Daily-use critique

### dashboard — REDESIGN

- **Primary goal:** Find today's work and enter a collection task.
- **Attention priority:** Overdue/today/next work, then current holdings and recorded facts.
- **Space without enough value:** Repeated large metric surfaces and navigation chrome compete with the useful queue.
- **Navigation effort:** Use one direct Schedule entry and compact collection entry points rather than a wall of destinations.
- **Interaction complexity:** Separating operational History, Journal occurrences and future work must remain explicit.
- **Removal/reorganization and layout decision:** A makes work the large first region; B makes a photographic collection portrait first. Recommend A for daily use.
- **Tradeoff:** A reduces visual discovery; B delays work and depends on real assigned imagery.

Evidence: 037, 064, 091, 118, 145, 199.

### seeds — REDESIGN

- **Primary goal:** Locate a physical lot, check remaining stock and act.
- **Attention priority:** Identity/lot, quantity knowledge/unit, storage and acquisition precision.
- **Space without enough value:** Unselected Quick Preview reserves a column; enclosing directory headings repeat the title.
- **Navigation effort:** One explicit preview before detail, preserve query/page/selection on Back.
- **Interaction complexity:** Selection, bulk eligibility and current/history cannot be collapsed into a generic card action.
- **Removal/reorganization and layout decision:** A uses full-width inventory columns; B uses richer rows. Recommend A; open inspector only with a selected record.
- **Tradeoff:** A scans stock faster but pictures are secondary; B offers recognition with fewer records visible.

Evidence: 002, 038, 065, 092, 119, 200, 226, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 339, 341, 346, 351, 356, 361, 363, 365, 367, 369, 371, 373, 376.

### sowings — REFINE

- **Primary goal:** Review a propagation record and its outcomes.
- **Attention priority:** Source SeedLot, stage, recorded dates and result quantities.
- **Space without enough value:** Repeated summary framing and verbose per-record action surfaces.
- **Navigation effort:** Keep source chooser and a direct source link; don't introduce another wizard entry layer.
- **Interaction complexity:** Sowing outcomes and source lineage have distinct validation/eligibility.
- **Removal/reorganization and layout decision:** Reuse compact header, rows and explicit actions; retain guided creation and outcome ownership.
- **Tradeoff:** Less decorative framing; do not erase meaningful propagation detail for density.

Evidence: 039, 066, 093, 120, 201, 227, 265, 287, 288, 305.

### plants — REDESIGN

- **Primary goal:** Locate an owned individual or managed group and act.
- **Attention priority:** Record identity, type, physical location and lifecycle.
- **Space without enough value:** Large cards give equal emphasis to repeated context when scanning maintenance work.
- **Navigation effort:** Preview on selection, direct detail and return context; retain one Plants destination with explicit type filter.
- **Interaction complexity:** Groups are managed records, not a count of individual Plants; source relationships remain explicit.
- **Removal/reorganization and layout decision:** A operational table vs B photographic browse. Recommend A as default; B is a secondary representation only after acceptance.
- **Tradeoff:** B is attractive with real primary photos but weak with missing images and long cultivar labels.

Evidence: 040, 067, 094, 121, 202, 228, 267, 290, 291, 307, 319, 334.

### harvests — KEEP

- **Primary goal:** Read collected historical material and manage related operations.
- **Attention priority:** Harvest occurrence, collected quantity/unit and source.
- **Space without enough value:** Extra border/heading layers can be reduced but the historical/material split has real value.
- **Navigation effort:** Retain explicit links to managed stored remainder rather than folding it into collected stock.
- **Interaction complexity:** Conversions and reversals require existing guards; a merged stock number would mislead.
- **Removal/reorganization and layout decision:** Keep domain composition; adopt intrinsic header and row spacing as a later narrow refinement.
- **Tradeoff:** Some detail remains dense because collected and stored are different facts.

Evidence: 042, 069, 096, 123, 204, 230, 269, 293, 294, 309, 335.

### stored-material — KEEP

- **Primary goal:** Manage the remainder of collected material.
- **Attention priority:** Remaining quantity/unit, Harvest linkage and current location.
- **Space without enough value:** Generic repeated helper copy can shrink; quantitative distinctions stay.
- **Navigation effort:** Keep contextual access from Harvests and Labels; no new top-level sidebar category.
- **Interaction complexity:** Available, converted and consumed quantities retain their server-owned ledger.
- **Removal/reorganization and layout decision:** Keep bounded inventory; share controls/states without making it a photographic browse page.
- **Tradeoff:** Compact rows need clear units; never trade quantity truth for uniform cards.

Evidence: 043, 070, 097, 124, 205, 231.

### locations — REFINE

- **Primary goal:** Find a physical place and understand direct/inclusive use.
- **Attention priority:** Hierarchy path, scopes, active state and direct vs descendants counts.
- **Space without enough value:** An empty detail placeholder is unhelpful; selected context is useful.
- **Navigation effort:** Keep outline and selected context together; full detail remains directly addressable.
- **Interaction complexity:** Scopes do not inherit; location is not provenance or supplier lineage.
- **Removal/reorganization and layout decision:** Retain hierarchy; selection opens useful contextual panel, collapse to one mobile path. Existing full detail already uses a suitable usage table.
- **Tradeoff:** Split view helps orientation but must close/stack at narrow width; 297 is not valid evidence of a broken detail.

Evidence: 044, 071, 098, 125, 206, 232, 271, 296, 297, 311.

### journal — REFINE

- **Primary goal:** Read and record observations and performed work.
- **Attention priority:** Occurrence precision, activity kind, target and useful note.
- **Space without enough value:** Multiple bordered cards and expanded boilerplate notes slow chronological scan.
- **Navigation effort:** Keep direct target access and Record action, no detour through History.
- **Interaction complexity:** Occurred date can be unknown; recorded UTC timestamp is a different fact.
- **Removal/reorganization and layout decision:** Compact chronology, clear source/target and expandable note; preserve mutation ownership.
- **Tradeoff:** Collapsed notes reduce passive visibility; first useful context should remain in the row.

Evidence: 045, 072, 099, 126, 207, 233.

### history — KEEP

- **Primary goal:** Inspect authoritative operational evidence.
- **Attention priority:** What happened, target/source and honest time semantics.
- **Space without enough value:** Repeated card framing can reduce; read-only status is useful context.
- **Navigation effort:** Direct source/target links, preserve query; no edit affordance for projection facts.
- **Interaction complexity:** Deduplication and recorded completion without an occurrence remain explicit.
- **Removal/reorganization and layout decision:** Keep read-only projection, refine chronology using the same frame as Journal.
- **Tradeoff:** Uniform chronology must not imply every History row is an operator event.

Evidence: 046, 073, 100, 127, 208, 234.

### schedule-list — REFINE

- **Primary goal:** Find intended work and complete/cancel it correctly.
- **Attention priority:** Due precision, derived overdue, target and state.
- **Space without enough value:** Expanded notes and repeated action borders consume scan space.
- **Navigation effort:** Retain direct Calendar/List choice and target context; completion workflow stays owned.
- **Interaction complexity:** Completion time is not occurrence time; completing may optionally record a Journal Event.
- **Removal/reorganization and layout decision:** Compact due/work/action rows, notes secondary; don't invent Saved Views dimensions or Week view.
- **Tradeoff:** Shorter rows require clear labels and preserved completion evidence.

Evidence: 047, 074, 101, 128, 209, 235, 328.

### schedule-calendar — KEEP

- **Primary goal:** Understand intended work by month and open a task.
- **Attention priority:** Current period, due date and intended task.
- **Space without enough value:** Standardize surrounding controls only; grid cells need space.
- **Navigation effort:** Keep period navigation, Today and mobile agenda; no fake alternate temporal model.
- **Interaction complexity:** Multi-day/partial due dates and overdue retain existing semantics.
- **Removal/reorganization and layout decision:** Preserve accepted monthly calendar/agenda; high-fidelity specimen demonstrates framing and selection.
- **Tradeoff:** Monthly planning is less dense than a list; that is intentional, not a reason to force tables.

Evidence: 048, 075, 102, 129, 210, 236, 327, 329, 342, 347, 352, 357.

### identities — REDESIGN

- **Primary goal:** Recognize a botanical identity and inspect collection coverage.
- **Attention priority:** Scientific name/cultivar, common name, actual active SeedLot/Plant coverage, real cover availability.
- **Space without enough value:** Empty Quick Preview takes width; repeated directory headings compete with reference names.
- **Navigation effort:** Open the hub directly from the full-width index and preserve result context; a second preview would repeat the name and coverage already visible. Keep the six-section destination.
- **Interaction complexity:** Species and cultivar identities cannot borrow counts/covers from each other.
- **Removal/reorganization and layout decision:** A visual reference index vs B analytical table; recommend A when actual covers exist, B remains efficient no-cover alternative.
- **Tradeoff:** Photography adds recognition but current captured covers are absent; don't hide unknown imagery with unrelated specimen photos.

Evidence: 049, 076, 103, 130, 211, 237, 277, 278, 279, 280, 281, 282, 283, 284, 285, 317, 337, 375.

### taxonomy-list — KEEP

- **Primary goal:** Inspect collection-aware classification and placement evidence.
- **Attention priority:** Local identity, confirmed source and unresolved placement.
- **Space without enough value:** Only surrounding duplicated chrome needs convergence.
- **Navigation effort:** Preserve accepted list/tree navigation and local fallback.
- **Interaction complexity:** WFO availability/source confirmation are not interchangeable with local labels.
- **Removal/reorganization and layout decision:** Keep delivered Taxonomy composition; no second classification hierarchy.
- **Tradeoff:** Missing WFO is an environmental/source state, not license to fabricate a graph.

Evidence: 050, 077, 104, 131, 212, 238.

### taxonomy-tree — KEEP

- **Primary goal:** Explore accepted taxonomy graph.
- **Attention priority:** Selected branch, ancestry, viewport and source evidence.
- **Space without enough value:** Avoid added cards around the scientific canvas.
- **Navigation effort:** Retain selected branch/camera/fullscreen and textual equivalent.
- **Interaction complexity:** Graph keyboard and identity selection are specialist contracts.
- **Removal/reorganization and layout decision:** Preserve accepted graph architecture; shared header/dialog changes require its regressions.
- **Tradeoff:** This audit only captured local fallback; live graph acceptance remains with its delivered evidence.

Evidence: 051, 078, 105, 132, 213, 239, 343, 348, 353, 358.

### media — KEEP

- **Primary goal:** Browse, inspect and link photographic assets.
- **Attention priority:** Image, real metadata and actual linked records.
- **Space without enough value:** The approved Media workstream already redesigns photographic composition.
- **Navigation effort:** Keep its gallery/detail/offset/card-focus model.
- **Interaction complexity:** Record primary photo, Identity cover, linked media and external load remain separate.
- **Removal/reorganization and layout decision:** Integrate approved Media candidate; don't produce a rival photographic redesign.
- **Tradeoff:** Owner evidence is reported separately; global template work must not regress its scoped F01/F09 fixes.

Evidence: 052, 079, 106, 133, 214, 240, 322, 323, 324, 325, 326, 338, 344, 349, 354, 359, 385.

### geography — KEEP

- **Primary goal:** Choose the right scientific geography workspace.
- **Attention priority:** Evidence type and workspace purpose.
- **Space without enough value:** Do not turn this small index into a metrics dashboard.
- **Navigation effort:** Keep direct workspace entries and frozen Geography macro destination.
- **Interaction complexity:** Reference ranges, occurrences and recorded origins are three different contracts.
- **Removal/reorganization and layout decision:** Keep index; align shared controls only.
- **Tradeoff:** An extra explicit choice is useful when it prevents mixing evidence.

Evidence: 053, 080, 107, 134, 215, 241.

### native-ranges — KEEP

- **Primary goal:** Inspect structured botanical reference geography.
- **Attention priority:** Selected identity, source assertions, legend and textual equivalent.
- **Space without enough value:** Cards surrounding the map should not displace the map.
- **Navigation effort:** Keep map/list selection synchronization and source review access.
- **Interaction complexity:** Structured range is not occurrence density or recorded provenance.
- **Removal/reorganization and layout decision:** Preserve map-dominant composition; use optional context without new inference.
- **Tradeoff:** Source gaps remain visible; attractive map fill cannot imply unsupported native range.

Evidence: 018, 054, 081, 108, 135, 216, 242, 330, 331, 332, 345, 350, 355, 360.

### species-distribution — KEEP

- **Primary goal:** Explicitly load observed occurrence density for one identity.
- **Attention priority:** Provider state, selected identity, evidence qualifier and map.
- **Space without enough value:** Only standardize shared surrounding chrome.
- **Navigation effort:** Retain explicit provider load; selection/search/restore must remain provider-free.
- **Interaction complexity:** Do not infer native range, provenance or multi-species support from occurrences.
- **Removal/reorganization and layout decision:** Keep accepted bounded occurrence workspace.
- **Tradeoff:** Provider latency/source limits remain; UI density is not a reason for implicit loading.

Evidence: 055, 082, 109, 136, 217, 243.

### origins — KEEP

- **Primary goal:** Inspect recorded collection origins.
- **Attention priority:** Recorded material evidence, precision and associated targets.
- **Space without enough value:** No additional summary cards without actual aggregate value.
- **Navigation effort:** Keep records synchronized with map and a textual list.
- **Interaction complexity:** Origins are recorded provenance, not storage, supplier or botanical native range.
- **Removal/reorganization and layout decision:** Keep scientific composition and explicit uncertainty.
- **Tradeoff:** Sparse genuine evidence is preferable to a visually complete invented map.

Evidence: 056, 083, 110, 137, 218, 244.

### places — REFINE

- **Primary goal:** Inspect geographical reference places used by existing records.
- **Attention priority:** Place name, type and available recorded geography.
- **Space without enough value:** Repeated headings/helper surfaces can be condensed.
- **Navigation effort:** Keep contextual geography routes rather than sidebar expansion.
- **Interaction complexity:** A reference place is not a precise provenance site.
- **Removal/reorganization and layout decision:** Reuse directory frame and optional selection; preserve actual domain fields.
- **Tradeoff:** More shared presentation is safe only while types and precision remain explicit.

Evidence: 057, 084, 111, 138, 219, 245.

### sites — REFINE

- **Primary goal:** Inspect precise recorded provenance sites.
- **Attention priority:** Recorded site identity and available exact/uncertain position.
- **Space without enough value:** Duplicated framing competes with the useful record list.
- **Navigation effort:** Direct context and selected detail without empty preview reservation.
- **Interaction complexity:** Do not create provenance from current Location or Supplier.
- **Removal/reorganization and layout decision:** Reuse directory controls, compact records and truthful empty states.
- **Tradeoff:** No-map/no-position state remains legitimate and useful.

Evidence: 058, 085, 112, 139, 220, 246.

### suppliers — REFINE

- **Primary goal:** Find an acquisition source, contact and linked context.
- **Attention priority:** Supplier name and recorded contact/source relationships.
- **Space without enough value:** Generic cards repeat helper text; no value in fake purchase metrics.
- **Navigation effort:** A compact list opens contextual detail, distinct from Order transaction detail.
- **Interaction complexity:** Direct material sources and Orders remain separate link groups.
- **Removal/reorganization and layout decision:** Use richer compact rows; detail groups real relationships and suppresses empty framing.
- **Tradeoff:** Contact-heavy suppliers may need variable-height rows; don't force equal photography cards.

Evidence: 059, 086, 113, 140, 221, 247, 273, 299, 300, 313.

### orders — REDESIGN

- **Primary goal:** Locate a transaction and reconcile its physical packets.
- **Attention priority:** Reference, Supplier, date precision and total price/currency.
- **Space without enough value:** Card framing reduces cross-order comparison; packet and transaction headings compete.
- **Navigation effort:** One transaction table, detail with explicit Add/Link packet action.
- **Interaction complexity:** Unknown Supplier/price stay unknown; Order date doesn't fill acquisition date.
- **Removal/reorganization and layout decision:** Table-led directory and concise transaction detail; reconciliation and deletion guards unchanged.
- **Tradeoff:** Tables suit financial comparison but must become labelled mobile records rather than hiding currency or unknowns.

Evidence: 060, 087, 114, 141, 222, 248, 275, 302, 303, 315, 336, 362, 364, 366, 368, 370, 372, 374.

### labels — KEEP

- **Primary goal:** Compose and print bounded collection labels.
- **Attention priority:** Record kind, copies/totals/pages, chosen format and configured QR destination.
- **Space without enough value:** Shared chrome can shrink; physical print geometry must stay explicit.
- **Navigation effort:** Keep canonical composer and contextual source access.
- **Interaction complexity:** SeedLot/Plant/PlantGroup/Stored only; unknown values and physical units remain honest.
- **Removal/reorganization and layout decision:** Keep accepted label architecture; refine shared controls only.
- **Tradeoff:** Screen mockups cannot certify A4 or 50×30mm output or unset QR configuration.

Evidence: 061, 088, 115, 142, 223, 249, 333.

### import-export — REFINE

- **Primary goal:** Inspect, validate and deliberately import/export supported data.
- **Attention priority:** File/scope, validation result, conflicts and explicit apply boundary.
- **Space without enough value:** Flatten helper text and avoid unrelated decorative cards.
- **Navigation effort:** Keep staged preview/validation before mutation, not a single magic upload.
- **Interaction complexity:** No silent overwrite, invented relationships or rollback promise.
- **Removal/reorganization and layout decision:** Condense into clear ordered operation sections using existing guards.
- **Tradeoff:** An explicit confirm step is justified by data consequences; don't remove it as friction.

Evidence: 062, 089, 116, 143, 224, 250.

### settings — KEEP

- **Primary goal:** Change supported application and appearance settings.
- **Attention priority:** Setting meaning, saved state and separate appearance axes.
- **Space without enough value:** Repeated generic section copy can shrink.
- **Navigation effort:** Preserve reachable Settings on mobile More and existing independent saves.
- **Interaction complexity:** Authentication/application configuration must not be conflated with a visual theme preset.
- **Removal/reorganization and layout decision:** Keep current scopes; share field/error/feedback grammar.
- **Tradeoff:** Moving utilities into More adds one navigation step but removes repeated chrome.

Evidence: 063, 090, 117, 144, 225, 251.

### plant-groups — REDESIGN

- **Primary goal:** Manage a coherent group without pretending it is individual records.
- **Attention priority:** Group identity, group quantity knowledge, location and lifecycle.
- **Space without enough value:** Same card/spacing issues as Plants; repeated labels can shrink.
- **Navigation effort:** Retain explicit Plants type filter, not an invented top-level destination.
- **Interaction complexity:** Group count/quantity cannot be summed as active individual Plants.
- **Removal/reorganization and layout decision:** Same operational table choice as Plants, type visibly labelled; quantity stays domain-specific.
- **Tradeoff:** A unified presentation still needs distinct group quantity and operation eligibility.

Evidence: 320, 379, 380, 381, 382, 383, 384.

### shell — REDESIGN

- **Primary goal:** Reach destinations and essential utilities with minimal chrome.
- **Attention priority:** Current location, task controls and content.
- **Space without enough value:** Duplicate utility/top-level bars push first useful content below the fold.
- **Navigation effort:** Keep existing macro groups; bottom primary destinations plus More contains all utilities.
- **Interaction complexity:** Menus must work with keyboard/Escape/focus; no function silently disappears.
- **Removal/reorganization and layout decision:** Compact mobile brand/menu and bottom navigation; desktop forest rail is separately reviewable.
- **Tradeoff:** Settings/Appearance/Sign out take one extra open; keyboard and focus contract must justify it.

Evidence: 340, 377, 378.

## Contextual detail and form decisions

**Identity hub — REFINE.** Keep Overview, Reference, Taxonomy, Maps, Media and History. These six sections reflect established distinct responsibilities. Remove redundant enclosing cards/headings; give collection footprint priority in Overview and keep precise active/total distinctions. Identity covers remain explicit. Existing per-section edit saves stay independent. Linked-record History must remain bounded to the existing authoritative projection; do not add an unsupported global exact-Identity filter.

**SeedLot / Plant detail — REFINE.** Keep the actual record's identity, quantitative context, location, acquisition and related operations. Group related facts in readable sections rather than decorating every fact as a card. Inspector is a preview, not a substitute for a directly addressable detail. Retain record-specific eligibility, source lineage, photo assignment and destructive boundaries.

**Create/Edit — REDESIGN.** Compare A single-active-section and B continuous anchored form. Recommend B for maintenance, where stock/date/source comparisons matter. Preserve unknown/approximate quantity and unit, PartialDate precision, explicit source relationships and server validation. The high-fidelity SeedLot example demonstrates both create and edit contexts. It does not pretend to implement all existing domain forms. Source-dependent sowing/harvest flows remain guided and independently saved Identity sections remain independent.

**Location full detail — KEEP.** The current full detail already has an appropriate direct/inclusive usage table. The hierarchy receives a targeted selected-context refinement; capture 297 cannot support a claim that the detail page is inherently empty.

**Order detail — REFINE.** Put transaction facts in one readable block and physical packet reconciliation next. Keep unknown Supplier/price, unallocated total price, link-existing behavior, no implicit acquisition fill and empty-only deletion. Don't invent delivery/payment status from the reference images.

## A/B choice criteria

Evaluate the same real long-label/unknown-stock examples in each pair. Compare first useful record position, useful facts visible, steps to Preview/detail/back, keyboard order, no-cover behavior and mobile action reach. Choose by task fit, not how many photographs are visible. The interactive review portal links each pair and recommends one; alternatives differ in column allocation, row representation or form content visibility rather than color.
