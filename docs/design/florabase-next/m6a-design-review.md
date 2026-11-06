# Florabase Next M6A: creative design review

Status: **ready for operator review**. Design only: no frontend, backend, API, schema or auth
change was made in M6A.

- **New Claude Design canvas (M6A):** https://claude.ai/artifact/B3TWNaSJvnjxUz2GmdXRCx (private
  until shared from its Share menu).
- **Phase B artifact, preserved and unchanged:** https://claude.ai/artifact/GfbbqcoWQnULGwzagEfWX7
- **Studied implementation:** `e593c50` (M5) on UAT Preview, with the M2–M5 captures in
  `.florabase-next-evidence/` (manifests in `m2/` to `m5/`).
- **Design system:** Field Ledger as implemented (the tokens in `styles/tokens.css`, Instrument Sans,
  Newsreader, IBM Plex Mono). The account's earlier "Florabase UI System" was not applied, per
  the operator's instruction that it is a reference, not a constraint.

The canvas has four pages:

| Page | Artboards |
| ---- | --------- |
| Record detail: three directions | A Specimen Sheet (interactive: tabs, More menu; tweaks for the record and light/dark), B Research Workspace, C Ledger Folio |
| Responsive, sparse and states | A on a phone (interactive lineage disclosure; dark tweak); A on a tablet with a sparse record and a loading/error tweak |
| Daily work | Today; Seeds on a phone with a compact header (interactive); Record sheet; palette and confirm dialog (overlay tweak) |
| Before / after | Real M5 captures beside live imports of the direction A boards |

## 1. Critical visual audit of M5

What works: the Workbench rail, Field Ledger type, the honesty rules (planned against recorded,
partial dates, derived counts) and the lineage strip's restraint. What follows is what still
holds Florabase back.

| Area | Finding | Severity |
| ---- | ------- | -------- |
| Record detail | Still a management-app page: header, then tabs, then a grey "At a glance" band, then two columns of small fact lists. The specimen image is a 6rem thumbnail. Nothing makes a plant page feel different from an order page. | High |
| Record detail | Facts appear three times: header lines, At a glance, and "Origin and provenance", which repeats the lineage strip. | High |
| Record detail | The timeline is two text lists. Partial dates are correct but invisible as a concept; the reader cannot *see* that "2026-09" is a month, not a day. | Medium |
| Record detail | Six of ten types (Harvest, Stored material, Location, Identity, Supplier, Order) keep the old overview below the new header, so the product feels like two systems. | High (release) |
| Imagery | Plates are small and decorative. With no photo, the hatched placeholder is the strongest visual on many pages, which rewards missing data. | Medium |
| Today | Each task repeats "Plant · Preview — Nursery aloe" in full. The page is a list of tasks, not a view of the collection. Two search fields (panel and page) compete. | Medium |
| Directories (phone) | On Seeds, the first record starts about 580px down an 844px screen: title, search, List/Gallery, Filters, Saved views, New, chip, count, Select, per-page and pager all come first. | High (release) |
| Rail and panel | The rail is distinctive; the panel repeats the page title ("You are in Today / Today") and spends width on a single link for one-section workspaces. | Low |
| Record sheet | Functional but form-like: radios plus two picker fields ("Find collection record", "Target record"), and the label field has equal weight with frequent actions. | Medium |
| Palette | Text-only rows; records are hard to tell apart without identity or kind facts. | Low |
| Dark | Coherent, but leaves the same flat structure on a darker ground; image plates disappear. | Low |
| Copy | Many labels explain mechanics ("Recorded in the Journal and derived History, latest first"). Honest, but the page reads as text. The honesty should move into form (shape, position, precision) and leave fewer sentences. | Medium |

## 2. Alternatives (canvas page 1)

All three use the same real UAT record (Preview — Basil mother plant) and only facts that existing
endpoints return.

| Direction | Idea | Strengths | Costs |
| --------- | ---- | --------- | ----- |
| **A. Specimen Sheet** | A herbarium sheet: large portrait plate (400×500) with a ruled specimen label below it; the name and scientific name set large; lineage drawn as a sequence of recorded steps with relation verbs; an **Almanac** that places entries on a month axis, with month-only and year-only dates drawn as spans and undated entries in their own tray. | Most memorable and most botanical. Partial dates become visible as shape. One label block replaces three repeated fact groups. Scales down to a phone naturally (plate becomes a banner). | Taller page; the plate needs a good fallback; the Almanac needs a careful accessible list twin (it has one). |
| **B. Research Workspace** | Three panes: related-records outline, a dense fact grid with a merged Journal/Schedule table, and an inspector with the lineage stem, photo and next plan. | Fastest for scanning many facts; best use of 1440+ screens. | Weakest botanical identity; image is secondary; hardest to collapse to tablet and phone; closest to generic tooling. |
| **C. Ledger Folio** | Typography-led folio: very large serif name, a genealogy rule for lineage, ledger rows with dotted leaders, a Journal grouped by recorded precision ("September 2026 · day not recorded"), marginalia for facts and photo. | Calm, distinctive, excellent for dates and precision; prints beautifully. | Imagery secondary; actions quieter; weaker for quick phone work. |

## 3. Recommendation: direction A, borrowing from C

Adopt **A Specimen Sheet** as the record-detail grammar for all ten types, and borrow C's
precision grouping for the full Journal tab. Reasons:

1. It is the only direction where the specimen is the subject: plate, label and name carry the
   botanical identity the operator asked for.
2. It removes duplication structurally. The specimen label is the single fact block, the lineage
   sequence is the single provenance statement, and the Almanac replaces both "Upcoming" and the
   recorded list on Overview.
3. Honesty moves from prose into form. Hollow means planned, solid means recorded, a span means
   month or year precision, and the undated tray means no date. Text shrinks without losing
   meaning.
4. It degrades well. Tablet keeps two columns with a smaller plate; on a phone the plate is a
   banner, lineage is a disclosure, and the Almanac becomes a list with a thumb-reach action dock.
5. For sparse records it reads as "not recorded" rather than as a broken page (see the tablet
   board, with the real Aloe unknown stock).

B's merged Journal/Schedule **table** is worth keeping as an optional dense view in the Journal
tab for power users (M6B stretch, not required).

## 4. M6B component and layout proposal

Frontend only, on the existing CollectionUI contract. Domain code keeps API, validation and save
ownership.

| Component | Replaces / extends | Notes |
| --------- | ------------------ | ----- |
| `SpecimenSheet` (layout) | `DetailPage` + `DetailHeader` | Two columns ≥ 75rem (plate column 25rem); two columns on a tablet with a 16rem plate; phone banner. Slots: `plate`, `label`, `identity`, `actions`, `lineage`, `sections`. |
| `SpecimenPlate` | `RecordVisual` in headers | Portrait 4:5; real photo, else the identity reference with its source caption, else a quiet fallback with "Add photo". Never makes missing data the loudest element. |
| `SpecimenLabel` | `DetailSummary`, header facts, part of `DetailContext` | One ruled `dl`; unknown values in italic "Not recorded" or "Unknown", never "—" or 0. Each domain supplies its rows. |
| `LineageSequence` | `LineageStrip` (keeps `useRecordedLineage`) | Cards per recorded step with relation verbs derived only from kind pairs (Seed lot→Sowing "sown as", Sowing→Plant "grown into", Group→Plant "extracted", Plant→Seed lot "produced"). Phone: disclosure. |
| `Almanac` | `RecordTimeline` (keeps its data hooks) | Month axis (visual, `aria-hidden`) plus the existing two-lane lists as the accessible structure; partial-date spans; undated tray; today marker. |
| `ActionDock` (phone) | Header actions on ≤ 48rem | Sticky above the bottom bar: primary action plus up to two, rest in More. |
| `DirectoryHeader` compact mode (phone) | `PageHeader` + `DirectoryTools` on ≤ 48rem | Title row (count, New), search plus one "View, filters and saved views" button with a badge, removable chips; pagination and Select move to the end or the sheet. **Target: first record at or above 240px** (now about 580px). |
| `TodayByRecord` | Today "Next work" list | Groups the existing `upcoming` items by target with one plate and name per record; counts in a header ledger. Same `/api/v1/dashboard` data. |
| Record sheet v2 | `RecordSheet` | Large tiles for the open record; one search across Plant, Plant group and Sowing via the existing `/api/v1/search` (filtered client-side by kind); recent records from the existing session Recent; label row with Scan only where supported. |
| Palette rows | `CommandPalette` | Plate and second-line facts only from fields the search result already returns. |

Shell: hide the context panel's duplicate title on one-section workspaces. On phones, consider
Record · Today · Collection · Activity · More (Explore, Sourcing and Settings under More),
pending operator review.

Motion: 150–200 ms opacity and translate for sheets, the menu and the lineage disclosure only,
disabled under `prefers-reduced-motion`. No decorative animation.

Implementation order (each one reviewable): 1. `SpecimenSheet` + `SpecimenLabel` +
`SpecimenPlate` on Plant/Group; 2. `LineageSequence` + `Almanac`; 3. Seed lot and Sowing;
4. the remaining six types; 5. phone `ActionDock` and compact `DirectoryHeader`; 6. Today by
record; 7. Record sheet v2 and palette rows; 8. dark pass, captures, accessibility pass.

## 5. Prototype against implemented

| Shown on the canvas | Status |
| ------------------- | ------ |
| Lineage data, Journal entries, Schedule items, counts, seed lot names, quantities, locations | IMPLEMENTED data (UAT fixture v4) |
| "Basil seedling no. 4" (three-step chain through a Plant group) | **Illustrative**; not in UAT. Real three-step data is an M6B test task. |
| Specimen sheet, Almanac, compact phone header, Today by record, Record sheet v2, palette plates, phone action dock | PROTOTYPE |
| Data quality disclosure, Saved views, Record sheet v1, entry deep links, focus modality | IMPLEMENTED (M4–M5) |
| Per-record History lane | PROPOSAL (backend filter; not built) |

## 6. Register of unresolved functional and accessibility issues

These are M6 release requirements; none is closed by M6A.

| # | Issue | Type | Plan |
| - | ----- | ---- | ---- |
| R1 | Consistent Details across all ten record types (six still have old overviews) | Functional/visual | M6B steps 1–4 |
| R2 | Plant Journal requested twice (Overview timeline and Journal tab) | Performance | M6B: one fetch per record version, shared by `Almanac` and the Journal tab, invalidated by Journal mutations; no API change |
| R3 | Plant provenance repeats lineage | Visual | Resolved by `SpecimenLabel` + `LineageSequence` (Origin row keeps only non-lineage origin: purchase, supplier, provenance site) |
| R4 | Mobile directory header height | Usability | Compact `DirectoryHeader`, target first record ≤ 240px, measured in captures |
| R5 | Realistic multi-step lineage | Test | Create a Plant extracted from "Preview — Basil seedlings" in isolated UAT through existing APIs; capture the three-step chain; keep unit cases for reversed/unlabelled/missing |
| R6 | MediaScreen "detail return preserves filters…" intermittent | Test | Investigate like StoredMaterial (mechanism first, repeated runs, then a fix or a documented cause) |
| R7 | Real-device QR camera acceptance | Device | Operator test on an Android phone over HTTPS (or localhost) with a printed label; record result |
| R8 | Almanac accessibility | A11y | Axis `aria-hidden`; lists remain the semantic structure; spans carry text equivalents ("month only") |
| R9 | Phone action dock overlapping content | A11y | Content padding equals dock height; dock respects safe area; focus never hidden under it |
| R10 | Contrast of muted text on plates and lineage tint in dark | A11y | Verify 4.5:1 for every muted-on-tint pair in both appearances before acceptance |
| R11 | Screen reader, real zoom and forced-colour checks of the new layout | A11y | Manual pass at M6B end (not covered by automated probes) |
| R12 | Preserve functionality, APIs, permissions and the six themes | Constraint | Same as M1–M5: domain code untouched; the six palette blocks stay pinned |
| R13 | Six themes on the new layout | Visual | Specimen components use tokens only; the M6B captures include Botanical |
