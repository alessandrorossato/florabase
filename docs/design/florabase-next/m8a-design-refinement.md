# Florabase Next M8 Stage A: design refinement proposal

**Status:** design only, awaiting operator approval. No frontend, backend, test or
configuration file was changed in Stage A. Main is untouched; the branch stays experimental.

- **Canvas (Claude Design, private):** https://claude.ai/artifact/EZkPPeaXAXm151sJmbUPCq
- **Input:** independent audit by Codex Luna of `35f9eb2` (Functional QA: pass with findings;
  Design and UX acceptance: fail), the M6A canvas
  (https://claude.ai/artifact/B3TWNaSJvnjxUz2GmdXRCx), the Phase B Workbench prototype
  (https://claude.ai/artifact/GfbbqcoWQnULGwzagEfWX7) and the M7 captures.
- **Look:** Field Ledger tokens (Instrument Sans, Newsreader, IBM Plex Mono; the existing light and
  dark colour blocks) on the Florabase UI System spacing, radii, 44px touch targets and copy rules.
  The design system's `tokens.json` is installed on the canvas.
- **Data:** synthetic UAT fixture v4 and the M6B extracted seedling. The plate image marked
  "UAT thumbnail" is the real fixture file (96 × 96 px WebP). The image marked "Illustrative" is a
  drawing standing in for a future display rendition; it is not a photograph and not available
  today.

## Canvas map

| Page | Before (real M7 capture) | After (proposal) |
| ---- | ------------------------ | ---------------- |
| 1 Specimen Sheet | Basil mother plant, desktop; Nursery aloe, tablet | **R1 Herbarium Mount** (recommended, interactive: 4 record/image states, dark, panel); R2 Folio Spread (alternative); R1 at tablet (interactive) |
| 2 Today | Today desktop; Today phone | **T1 Collection Bench** (recommended, interactive work filter, dark); T2 Week Ledger (alternative); T1 phone |
| 3 Phone | Extracted seedling detail; Seeds; Botanical identity | Record detail (identity row or banner, lineage disclosure); Seeds (measured, filter sheet); identity tabs (grid or scroll-with-cue) |
| 4 System | Command palette | Missing-photo and small-image system (M7 vs M8, light and dark); palette with record identification |

Five M7 captures were taken fresh from UAT at `35f9eb2` because the archived M7 set shows the
photo-less Aloe only: Basil mother plant (desktop and phone) and the extracted seedling (desktop and
phone). They are kept outside the repository with the other evidence.

## Recommended direction

**R1 Herbarium Mount + T1 Collection Bench**, with the phone identity row, the wrapping identity
tab grid and the quiet mat placeholder.

The record page becomes one botanical object: a herbarium sheet that holds the mounted photograph
and the specimen label together, beside a large serif record title and italic scientific name.
Lineage becomes a quiet stem line instead of a band of cards. The workspace panel stays out of the
way on record pages. Images are never enlarged beyond twice their natural size, so a 320px API
thumbnail looks deliberate rather than soft, and the same rule lets a future display rendition fill
the sheet at full quality.

Today becomes a collection bench: the date and a serif "Today", one derived ledger line of counts,
the active Plants as small herbarium sheets, then Next work as the primary column with a
four-way filter. Today has one search: its existing collection search (with Filters and Saved
views); the shell's own search entry is hidden on Today.

### Why not the alternatives

- **R2 Folio Spread** is the most editorial, but it doubles the plate area. Without a display
  rendition every record shows a soft or tiny image, and Planned/Recorded fall below the first
  screen at 1440 × 900.
- **T2 Week Ledger** suits a busy Schedule, but most days are empty in a small collection, record
  grouping is lost (one aloe appears in three columns), and it collapses to a list on phones.
- **Phone banner variant** shows the image larger, but a 96–320px thumbnail as a full-width banner
  is soft, and it costs about 200px before the title. The identity row shows the image beside the
  title at no more than 1× on most screens.

## Audit findings mapped to the proposal

| Luna finding | Priority | Proposed solution | Board | Dependency |
| ------------ | -------- | ----------------- | ----- | ---------- |
| Specimen detail: weak focal point, modest title, plate and label read as side cards, soft enlarged imagery | P1 | Herbarium sheet (photo mount + label in one object, ruled header with record kind and short id); 60px Newsreader title (46px for long labels); 30px italic scientific name; status and location as one quiet line; lineage as a stem line; panel collapsed by default on record pages, search moves to the top bar when the panel is closed; "New plant or group" leaves the record header (global New stays) | Main, Tablet | Frontend. Full-quality large images need the display rendition (backend proposal) |
| Missing-photo striped placeholders dominate | P1 | Flat mat tone (`surface-subtle`), inset hairline at detail size, 22–32px line mark in `border-strong`, "No photograph" in muted text and a text "Add photo" link only at detail size; mark only at card, row and palette sizes | Placeholders, all boards | Frontend |
| Today: generic, text-forward, two search entry points, four-metric strip | P1 | Keep Today's collection search (it is the full grouped search with Filters, Saved views and history, not a duplicate) as the single search; hide the shell's search entry on Today (panel search on desktop, app-bar icon on phone; Ctrl/⌘K still opens the palette); counts become one ledger line labelled "Counted from active records" with a Data quality link; the active Plants appear as a bench of small herbarium sheets using the photo each Plant already has; Next work is the primary column with All / Overdue / Due today / Next 7 days | Today, TodayPhone | Frontend; no new requests |
| Phone record: lineage cards fill the first screen, image below the fold | P1 | Detail pages replace the workspace strip and "Back to Plants" button with one 48px context bar ("‹ Plants"); 96 × 120 mounted image beside the title; actions in one 44px row (primary, Edit, More icon with label); lineage folds to one 60px disclosure row ("Recorded lineage · 3 steps", kinds summary) that expands to the vertical sequence | PhoneDetail | Frontend |
| Phone directories miss 240px | P1 | Two 44px control rows: search + Filters (badge shows the active filter count; chips move into the filter sheet), then layout toggle + Saved views + New. First record at 224px (measured on the board) | SeedsPhone | Frontend |
| Plant lineage capture identical to Plant detail | P1 | Stage B: find the cause, fix it, and make capture fail unless the URL and selected tab match the requested route | — | Capture tooling |
| Identity tabs clipped on phone | P2 | Six tabs wrap into a 3 × 2 grid at phone width (recommended); alternative keeps the scroll row with a fade and "n of 6" cue | IdentityPhone | Frontend |
| Command palette rows text-only | P2 | Kind glyph tile per record kind, title, italic identity line from the existing search `context`, group headers per kind with the totals the search response already returns, kind filter buttons using the existing `kind` parameter | Palette | Frontend; thumbnails would need the backend |
| Sparse Almanac axis looks unfinished | P2 | Twelve-month season strip (month cells: recorded dot, month-only tint, planned dashed ring), hidden from assistive technology, with the grouped lists as the record | Main | Frontend |
| Manual screen reader, zoom, high contrast, touch | P1 (release) | Not a design item. Stays open; required before release acceptance | — | Manual QA |

### Note on the fresh captures

The fresh M7 captures show a focus ring on the record title. This is correct behaviour, not a
defect: the capture script signed in by pressing Enter, which records keyboard modality, and
`foundation.css` shows the heading ring only after keyboard use. Stage B captures will sign in with
a pointer action so evidence reflects a pointer user, and keyboard evidence stays a separate set.

## Concrete component and layout changes for Stage B

| Area | Files (expected) | Change |
| ---- | ---------------- | ------ |
| Specimen sheet | `components/CollectionUI.tsx`, `components/specimen.css` | `SpecimenPlate` and `SpecimenLabel` move into one `SpecimenSheet` figure; ruled header; label anchored bottom-right at desktop; `DetailHeader` title scale and scientific line |
| Image mount | new `components/MountedImage.tsx` | Reads the loaded image's natural size; renders uncropped at no more than 2× natural size on the mat; no extra request |
| Missing photo | new `components/NoPhotograph.tsx` | Sizes: sheet, card, row, glyph; replaces the striped backgrounds everywhere they occur |
| Lineage | `lineage/LineageStrip.tsx`, `lineage/lineage-strip.css` | Desktop stem line (no cards); phone disclosure (button with `aria-expanded`), vertical sequence when open |
| Almanac | `timeline/RecordTimeline.tsx`, `timeline/almanac.ts` | Season strip for sparse records; axis only with enough dated activity |
| Shell | `shell/WorkbenchShell.tsx` and shell CSS | Panel collapsed by default on record pages and single-destination workspaces; top-bar search when collapsed; phone context bar on detail pages |
| Today | `collection/DashboardScreen.tsx`, `today.css`, shell | Collection search stays as the only visible search; shell search entry hidden on Today; ledger counts; bench; work filter segments |
| Directories (phone) | `styles/directory-system.css`, directory tools | Two control rows; filter count badge; chips inside the filter sheet |
| Identity tabs | `botanical-identities/botanical-identities.css` | 3 × 2 tab grid at ≤ 40rem |
| Palette | `shell/CommandPalette.tsx` | Kind glyphs, identity line, per-kind groups and totals, kind filter |

Every API, route, permission, form and domain rule stays as it is. No backend change.

## Tradeoffs

- **Habit changes:** on Today the shell's search entry is hidden (the page's collection search
  and Ctrl/⌘K remain); "New plant or group" leaves the record header (global New remains); on phone record pages the
  workspace strip gives way to a context bar (the Collection sheet in the bottom bar still lists
  every workspace); row actions on phone directories become Edit and More (Details is the row
  title link and stays in More).
- **Smaller images by design:** without a display rendition, plates show thumbnails smaller but
  sharper. The sheet looks deliberate; it does not look photographic.
- **Panel default:** collapsing the panel on record pages gives the specimen room but hides
  Recent and Saved views until the panel is opened.
- **Bundle:** two small components replace CSS backgrounds; no new dependency.

## Backend-dependent limitations (not authorised, separate proposals)

1. **Display rendition** (`display_url`, bounded long edge, for example 1280px): needed for large,
  sharp plates and for R2. The M6 proposal stands. Originals are never downloaded in lists.
2. **Thumbnails in search hits:** would allow plates in palette rows.
3. **Per-record History filter:** unchanged from M6A.

## Stage B plan (after approval only)

1. Fix the plant lineage capture: verify the requested route and selected tab, repair the cause,
   and make capture assert URL and selected-tab state before hashing.
2. Investigate the Botanical identity Back/Forward intermittent in an isolated writable test
   environment; classify it with evidence, without loosening the test.
3. Build `MountedImage` and `NoPhotograph`; replace striped placeholders.
4. Specimen sheet, title hierarchy, lineage stem, season strip (desktop and tablet).
5. Phone record: context bar, identity row, lineage disclosure.
6. Today: bench, ledger counts, work filter, one visible search (existing Dashboard search tests
   stay green unchanged).
7. Phone directories (two rows, filter badge) and identity tab grid.
8. Palette record identification.
9. Focused tests per change, full frontend suite, accessibility checks (contrast, keyboard, zoom,
   forced colours), authentic UAT captures with state assertions, before/after composites.
10. Stop for final visual and functional acceptance. No canonical FULL, push, delivery or merge.
