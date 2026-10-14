# Physical collection labels

Labels supports SeedLot, Plant, PlantGroup and managed Stored material. Contextual **Print label**
and **Settings → Tools → Labels** open the same temporary composer. Routes remain `#/labels` and
`#/labels?kind=<kind>&record=<uuid>`; contextual entry selects one exact record and one copy.
Location labels and untracked/raw Harvest items are outside this increment.

## Composition and application context

Choose Record type, search/select Record and Add record. Mixed batches retain typed exact sources,
merge duplicate additions into copies, and support positive integer copies up to **360 labels**.
Leaving or refreshing discards the batch. Label size changes only the current batch; **Default**
marks the saved preset and explicit **Set as default** persists it for future compositions.

The picker and Selected material list retain human stock names, source/type, quantity/acquisition,
Supplier/Location context where recorded. Common names are searchable where stored. Normal rows
omit UUIDs; exact IDs remain in source links and deliberate non-printing record details. Quantity
unknown/zero and PartialDate precision remain truthful in that application context.

## Final physical content

Only these elements appear on the screen sheet and printed label:

1. Exact-source QR, with a full quiet zone and optional tiny material-category glyph.
2. Scientific botanical name in the bundled botanical serif/italic treatment.
3. Cultivar, when recorded, in quotes and roman type on its own line.
4. Common name, when recorded, as a secondary roman line.

Common name comes from the existing BotanicalIdentity `common_name`; it is trimmed/omitted when
blank, never invented from scientific or stock names. Rank/uncertainty markers remain roman.
No family/order/kingdom/accepted lineage or taxonomy breadcrumb is printed. Stock display names,
material-type text, Location, source, quantity, acquisition and other operational lines are excluded
at every size. The QR supplies exact-record identity without printing technical IDs.

Name blocks wrap within the available physical area. Overflow warnings measure only rendered
scientific/cultivar/common-name content; removed application metadata cannot trigger them. The
Label content disclosure separates **Printed names** from **Record details (not printed)**.

## A4 presets and print safety

| Preset | Cell       | Grid / capacity | Horizontal / vertical margins | QR    | Scientific / cultivar / common type |
| ------ | ---------- | --------------- | ----------------------------- | ----- | ----------------------------------- |
| Small  | 40 × 20 mm | 5 × 13 / 65     | 5 / 18.5 mm                   | 16 mm | 8 / 7 / 7 pt                        |
| Medium | 50 × 30 mm | 4 × 9 / 36      | 5 / 13.5 mm                   | 24 mm | 10 / 8 / 8 pt                       |
| Large  | 70 × 40 mm | 2 × 7 / 14      | 35 / 8.5 mm                   | 32 mm | 12 / 10 / 10 pt                     |

Padding is 1 / 1.5 / 2 mm; text/QR gap is 0.75 / 1 / 1.5 mm. Names use the full interior height,
with no old bottom metadata band. Medium/Large QR grows into that freed space; Small keeps its
reliable 16 mm QR and prioritizes scientific name before optional names. Large uses two columns
rather than eliminating printer margins with three 70 mm columns. There are no cell gaps.

Preview scales the whole paper proportionally; print keeps physical millimetres/point typography.
Named page margins and absolute cell offsets avoid cumulative Chromium print-grid rounding.
Final blank cells remain blank and the last sheet has no extra trailing page. At the batch limit,
Small/Medium/Large produce 6 / 10 / 26 sheets.

Print at **100% / Actual size**, turn off Fit to page and browser headers/footers. Measure and scan a
trial print before adhesive stock. Browser raster/decoder QA does not certify a physical printer,
stock alignment, camera scanning or the native system print dialog. No PDF product feature exists.

## Shared public QR setting and contextual dialog

Settings → General remains canonical configuration for **Public / QR base URL**. The Labels
**QR destination → Edit** dialog edits that same persisted setting through the same save helper
and existing authenticated/CSRF API. No second composer URL setting exists.

The dialog populates the current address. Save preserves the latest persisted default size,
normalizes through the server, closes, regenerates QR immediately and retains selected material,
copies and temporary preset. Errors retain the draft; pending saves block dismissal. Pristine
Cancel/Escape/backdrop closes; dirty dismissal asks to Continue editing or Discard changes.
Focus returns to Edit. Clearing explicitly stores null and safely disables printing without clearing
the batch. General reloads the same saved value when opened.

Use an HTTP(S) origin with authority, maximum 200 characters, no credentials, path, query or
fragment, including empty query/fragment delimiters. Host case, default ports and a trailing slash
normalize safely. The root SPA introduces no subpath deployment. Backend validation remains
shared and authoritative; browser/login/preview host is never a fallback.

Migration `20261013_0042` creates installation preferences with Medium default and no QR origin.
Startup never migrates. Downgrade removes only preferences, which require reconfiguration after
re-upgrade. This UI correction adds no API/schema change and does not migrate/reset persistent UAT.

## QR destinations, glyphs and decoding

QR payload is solely saved public origin plus the existing source route:

- SeedLot: `/#/seeds/<id>`.
- Plant: `/#/plants/<id>`.
- PlantGroup: `/#/plant-groups/<id>`.
- Stored material: `/#/harvests/<harvest-id>?inventory=<inventory-id>`.

Stored material focuses the exact managed inventory record, including on an already-open Harvest.
No botanical/operational text, credentials, browser query strings or tokens enter the payload.
Normal authentication/authorization remains in force.

Local SVG uses pinned `qrcode-generator`, H correction, black/white contrast and a four-module
quiet zone. The tiny category glyph represents material type only. Medium/Large inset it only in
safe data regions away from functional patterns; Small uses a clean QR with an adjacent glyph.
There is no prominent printed material-type line. Unsafe insets fall back to an adjacent mark.
A module pitch below **0.22 mm** blocks printing and asks for a larger preset/shorter public URL.
An unconfigured/loading/failed setting blocks Print; browser-menu output shows a blocked explanation.

See [the current handoff](labels-navigation-ia-handoff.md) for focused tests, final resized-QR decoder
results, seven-boundary zoom review, dialog and footer evidence, and freeze readiness.
