# Evidence, provenance and reference interpretation

## Inputs actually reviewed

All 270 selected prior audit JPEGs were hashed/read and visually reviewed through 17 contact sheets; all paired DOM captures were read (2,437,265 characters). `evidence-review.json` records page-to-capture IDs. The earlier package's actual route inventory, screenshots, proposals, consumer map and relevant feature handoffs inform this design. Current UI contract, roadmap, design proposals, shared components and current routes were inspected. This is a critical redesign study, not a claim that every historical screen is defective.

Baseline is delivered `ee34874` and synthetic Extended Botanical Review Dataset v5. Existing source semantics take precedence over idealized image-reference labels. Captures are screenshot evidence; prototype renders are design evidence. Never present one as the other.

**Evidence correction:** capture 297 shows a transient unselected Location state, not a settled full detail. The current detail source and usage state in capture 271 establish a real full-width detail. Its layout is not classified as broken on the strength of 297. WFO-unconfigured Taxonomy captures show legitimate local fallback, not a loaded source graph. Labels has no configured QR destination. Browser zoom/physical print/provider/AT certification is not implied by resized screenshots.

`build-data.py` extracts 124 fixture records and 8 licensed species photographs. Exact per-Identity active SeedLot/Plant coverage is copied from the rendered audit 049, including plain-species/cultivar distinction. Counts are record counts, never specimen totals or inferred mass. The illustration mapping is deliberately association-free: it is not a saved cover or actual primary photo. Tables include unknown/approximate stock, partial dates, long labels and unknown supplier/price.

## Four supplied visual references

| Direction taken                                                   | Why it fits                                                              | Reference detail deliberately not adopted                                     |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| Forest navigation, calm light canvas, compact border-led controls | Recognizable botanical identity; same content typography across palettes | Decorative gradients, dramatic rounded cards and top banners                  |
| Photography on Media/reference browsing                           | Useful recognition when actual assigned image exists                     | Species photo inferred as owned specimen/Identity cover                       |
| Compact tables/lists for operations                               | Stock/location/date scan before drill-down                               | Arbitrary Growing/Flowering/Fruiting/Dormant persisted Plant lifecycle        |
| Work-oriented Dashboard and compact mobile shell                  | Daily work and record access fit the product                             | Growth percentages, sparklines, flowering-now count, fake statistics          |
| Side filter / optional inspector                                  | On-demand width, preserved main context                                  | Invented filters/categories/cover toggles, Week calendar and unsupported tabs |
| Safe destructive confirmation                                     | Safe initial focus and explicit consequence                              | Undo/recoverable deletion promises without a product recovery contract        |

Reference image sidebars also depict Plant groups/Stored material/Tools destinations. This study retains the actual frozen macro categories and existing contextual paths, rather than silently adding those top-level links. The prototype navigation uses bounded specimen destinations; it is not a proposal to alter production route names. Settings/Sign out are visible-access design placeholders, not a functioning account environment.

## What works in the HTML study

Page/alternative navigation, six theme selectors, local example search, preview open/close/focus, mobile utility menu, Plant/group examples, dialog Escape/Cancel focus, Identity section switch/keyboard, local form required-field reveal and state specimens. The edit example retains the real Acer lot's 103 seeds, complete 2026-09-12 acquisition date and existing Supplier/Order/provenance links. No API/provider calls, persisted filters, Saved Views, mutations or authenticated session exist. Where an action requires a domain capability, the design preview states the boundary or links to the matching specimen; it never pretends to save/delete a real record.

## Reproducibility and limitations

Text/prototype source is durable in Git; images/fonts/renders are external task artifacts to avoid committing binary audit output. The local server uses an explicit artifact root and repository fixture root and rejects path traversal. This is intentionally a local review tool, not portable hosting infrastructure. Original audit assets and copied Source font files must be present to reproduce images exactly; absence yields a real 404. A future shared preview should package exact licensed assets with checksums and required font notices, not silently download substitutes.

Image credits are in credits.html, from the existing reviewed media-manifest. Font distribution notices remain under frontend/public/licenses. No new third-party imagery, CDN, package or design dependency was added.
