# Extended Botanical Review Dataset v5

2026-10-22 · candidate `c902` · `feat/maps-origins-001-candidate` · implemented, awaiting operator acceptance.

## Scope and evidence boundaries

This reusable, additive, **Review-only** resource extends the unchanged v4 fixture. The versioned
plan and licensed photos live in `scripts/fixtures/botanical-v5/`; the owning-domain service runner
is `scripts/review_dataset_v5.py`. It adds 248 creation nodes and records 252 relationship/row
references, including generated harvest items and the authoritative extraction event. It uses no
new schema or dependency and performs no network acquisition.

Recognizable species names are plausible layout examples, without new authority claims or invented
external taxon IDs. Every owned material label starts with Review v5; collection notes and botanical
profile/range descriptions explicitly identify fabricated review data. Coordinates are fabricated
WGS84 examples, never a user's real collecting sites. All new structured native ranges are deliberately
synthetic comparison assertions, **not scientifically verified native ranges**. The media are actual
licensed species illustrations; they do not depict any claimed owned specimen or verified cultivar.

## Exact live counts

The candidate-owned Review was seeded twice successfully with identical IDs/references/counts.
Original v4 retains its 80 managed references and byte-identical ledger; the enabled owner's
credential fingerprint is unchanged. Totals include the baseline:

| Entity | Total |
| --- | ---: |
| Botanical identities | 37 |
| Botanical reference profiles | 25 |
| Identities with structured native ranges | 24 |
| SeedLots | 43 |
| Individual Plants | 19 |
| PlantGroups | 7 |
| Sowings | 16 |
| Orders | 12 |
| Suppliers | 10 |
| ProvenanceSites | 14 |
| Locations | 18 |
| Harvests | 5 |
| Stored-material inventories | 4 |
| Journal/operation events | 13 |
| Scheduled activities | 27 |
| Media assets | 17 |
| Protected local images | 9 |
| External references | 8 |
| Record media links | 18 |
| Protected attachments | 9 |
| Germination observations | 2 |
| Harvest items | 8 |
| Custom GeographicPlaces | 6 |

The origins projection has **12 mapped sites, 2 without coordinates, 42 eligible directly linked
records and 22 distinct identities**. These are not stock quantities. 37 identities exist in the
directory; 36 are represented in the collection overview, preserving the pre-existing unrepresented
identity rather than fabricating material to make totals equal. History stays a read-only projection
of real dated facts and operation receipts; no History rows are inserted from current state.

## Completeness, uncertainty and relationships

| Acceptance case | Deterministic logical examples |
| --- | --- |
| Sparse identity / rich reference | 30 new identities across trees, herbs, vegetables, succulents, tropical plants and ornamentals; 20 new profiles, including long and sparse descriptions |
| Cultivars / long labels | Black Krim tomato, Cinnamon basil, Tricolor sage and an explicitly synthetic long Capsicum cultivar label |
| Missing acquisition/quantity | `seed:00`, `seed:28`; missing Location and no media on other lots |
| Approximate / year-only | `seed:01`: approximate 101 seeds, acquisition year 2025; no invented day/month |
| Exact / month-only | `seed:02`: exact 102 seeds, September 2026; no invented day |
| Historical material | `seed:26` exhausted exact zero; `seed:27` discarded; inactive/transferred direct Plants; retained retired Supplier |
| Acquisition grouping | Orders 00–08 have several lots; Orders 00/01 share Supplier 0; Order 09 has unknown Supplier; exact decimal totals/currencies and unknown totals |
| Independent knowledge | Order dates do not populate SeedLot acquisition dates; purchase does not assert biological provenance |
| Physical packets | Multiple Chamaerops SeedLots share identity/site; records remain distinct |
| Reconciliation | `seed:reconcile` has Supplier 1 and no Order. Attempt Order 00/Supplier 0 requires existing ORDER-001 reconciliation; no invalid relationship is precreated |
| Outside an Order | Purchased lots 27–29 and standalone examples retain nullable Order links |
| Sowings / germination | 12 new Sowings: active, completed, failed, abandoned; exact, partial and unknown sowing dates; null versus zero versus positive germination |
| Dated observations | Two observations on one Sowing record zero then two; observation evidence remains distinct from summary counts |
| Plants / groups | 15 new direct Plants, one Sowing-derived Plant, one service-extracted Plant; 6 groups with exact, approximate and unknown counts |
| Extraction / lineage | Group 0 starts with 12 and has 11 after legitimate extraction; generated operation event retained. Derived/extracted Plants have no independent site assertion |
| Collection produced | `seed:produced` has a real producer-Plant reference through the owning creation service |
| Harvest / Stored material | 3 new Harvests/items and 3 inventories: independent historical collected quantities and remaining stored stock, including depleted and unknown/approximate cases |
| Activity | 4 new Journal observations, extraction receipt, harvest events and 8 scheduled intentions; several activities target one Plant |
| Deep hierarchy | 7 new nested Locations and 4 custom GeographicPlaces; long paths remain explicit |
| Media links | 7 new local links, 6 external links, one new unlinked asset of each kind. New local linked SeedLots receive primary photos only on first completion |

Schedule dates use fixed October 2026 anchors for repeatability; overdue/due presentation naturally
changes with the clock. External-provider error/unavailable evidence remains isolated in tests, not
persisted as fake observations.

## Native-range comparison matrix

Choose **Chamaerops humilis, Ficus carica, Quercus robur, Acer palmatum, Pinus pinea** in that order
(or any order). The selected set yields Brazil 5, Thailand 4, Italy 3, United States 2 and Australia 1.
These are synthetic test assertions, even where a name/geography pair happens to be plausible.

Ginkgo biloba records broad South America plus exact Brazil, exercising union without double count.
Other identities have disconnected countries, broad coverage, Vatican City without available boundary,
and deeply nested custom places without renderable polygons. Identities 20–29 have no new structured
range. The real canonical hierarchy supplies country/region relationships; no centroid or replacement
polygon is invented for missing boundaries.

## Provenance-site matrix

| New site | Coordinates / accuracy | Purpose |
| --- | --- | --- |
| site:00 · Review v5 synthetic origin 01 — a deliberately long recorded locality name | 38.1600, 13.3500; 25m | Synthetic review site |
| site:01 · Review v5 synthetic origin 02 | 38.1602, 13.3502; accuracy unknown | Synthetic review site |
| site:02 · Review v5 synthetic origin 03 | 38.1600, 13.3500; 150m | Synthetic review site |
| site:03 · Review v5 synthetic origin 04 | 18.8000, 98.9200; 1000m | Synthetic review site |
| site:04 · Review v5 synthetic origin 05 | -22.9000, -43.2000; accuracy unknown | Synthetic review site |
| site:05 · Review v5 synthetic origin 06 | 37.7700, -122.4200; 50m | Synthetic review site |
| site:06 · Review v5 synthetic origin 07 | -33.8600, 151.2000; 500m | Synthetic review site |
| site:07 · Review v5 synthetic origin 08 | -33.9200, 18.4200; accuracy unknown | Synthetic review site |
| site:08 · Review v5 synthetic origin 09 | 35.6800, 139.7600; 75m | Synthetic review site |
| site:09 · Review v5 synthetic origin 10 | 43.6000, 3.8700; 5m | Synthetic review site |
| site:10 · Review v5 synthetic origin 11 | No coordinates | Synthetic review site |
| site:11 · Review v5 synthetic origin 12 | No coordinates | Synthetic review site |
| site:12 · Review v5 synthetic origin 13 — no linked material | -41.2800, 174.7700; accuracy unknown | Synthetic review site |

Sites 00–02 exercise close/coincident Italian markers, several identities, several physical packets
and a deep geographic path. Sites span multiple continents; site 12 has zero eligible direct records.
Two coordinate-less sites remain Geography records and the unfiltered missing-coordinate KPI. Eligible
records include both Seeds and direct Plants/groups, with historical rows retained. Descendants do
not acquire markers from lineage, supplier, storage Location, native range, taxonomy or GBIF. Botanical
identity search and category exclusions produce truthful zero-result states without changing data.

## Media source and licence manifest

Each image was inspected on its individual Commons description page on 2026-10-22. Derivatives are
max 640px JPEG, recompressed, with EXIF removed. The checked-in machine-readable
[manifest](../../scripts/fixtures/botanical-v5/media-manifest.json) records source/preview URL, creator,
licence URL, dimensions, modification notice, byte size and SHA-256. Its adjacent NOTICE retains reuse
terms. These independent photo licences are not replaced by the application's licence.

| Illustration | Creator | Licence | Source | Packaged bytes |
| --- | --- | --- | --- | ---: |
| Aloe vera | Merstel007 | [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/) | [Commons description](https://commons.wikimedia.org/wiki/File:Aloe_Vera%2C.jpg) | 79579 |
| Lavandula angustifolia | Daria Sitnikova | [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) | [Commons description](https://commons.wikimedia.org/wiki/File:Field_Lavandula_angustifolia.jpg) | 97588 |
| Salvia officinalis | Caroline Léna Becker | [CC-BY-3.0](https://creativecommons.org/licenses/by/3.0/) | [Commons description](https://commons.wikimedia.org/wiki/File:Sauge_officinale.JPG) | 47830 |
| Ficus carica | Homoarborea | [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/) | [Commons description](https://commons.wikimedia.org/wiki/File:Ficus_carica_%281%29.jpg) | 92045 |
| Ocimum basilicum | Cliff Hutson | [CC-BY-2.0](https://creativecommons.org/licenses/by/2.0/) | [Commons description](https://commons.wikimedia.org/wiki/File:Basil_%28Ocimum_basilicum%29.jpg) | 37790 |
| Echinacea purpurea | Lena Jaginyan | [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) | [Commons description](https://commons.wikimedia.org/wiki/File:Echinacea_purpurea_plant.jpg) | 34395 |
| Helianthus annuus | AnRo0002 | [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/) | [Commons description](https://commons.wikimedia.org/wiki/File:20240826Helianthus_annuus2.jpg) | 78421 |
| Solanum lycopersicum | AnRo0002 | [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/) | [Commons description](https://commons.wikimedia.org/wiki/File:20240906Solanum_lycopersicum.jpg) | 41107 |

Measured live Review storage after seeding: **798,099 bytes across 61 media-root files**
(including metadata, manifests and derived images); PostgreSQL reports **12,605,119 bytes** for the
whole Review database. These are point-in-time measurements including baseline/operator state,
not incremental disk quotas.

Total packaged images: **508,755 bytes** (about 0.5 MiB). They are outside production
backend/frontend build contexts; the fixture mounts read-only into Review and disposable integration.
Runtime protected ingestion creates 8 new local assets using decoder/size validation, metadata and
owner-only storage. Seven external references persist HTTPS URLs and attribution only; seeding does
not fetch them. Lists do not contact third parties. Preview once remains explicit and uses the
existing no-referrer photo contract; saving a copy remains a separate supported operation. No GBIF
observation photographs are used. The eighth local photo and seventh external reference are deliberately
unlinked acceptance cases.

## GBIF-ready cases

The baseline's authoritative Ocimum basilicum link is retained (CoL XR usage `48GBK`, confirmed through
the existing GBIF match contract). It is ready for explicit Load; no occurrences or occurrence counts
are manufactured. All new identities have no external link. Baseline optional WFO availability remains
unchanged. Unsupported/unavailable provider states are covered by existing explicit test doubles;
there is no seeded downloaded GBIF occurrence cache. Seeding performs no occurrence or tile downloads.

## Guards, manifest and repeatability

From this candidate use `make feature-review-extended-seed` and
`make feature-review-extended-status`. The host calls the existing exact Review seed guard: source,
project, healthy services, revision, network, database and media/dependency-volume ownership. Runtime
checks repeat Review mode/project/source identity, connected DB/user, loopback auth and media-root
marker validation, ready v4 and exactly one enabled owner. Wrong roles refuse before mutation.

Logical keys and relationship references are deterministic. Owning services issue legitimate UUIDv7
IDs on the first run; the separate protected ledger preserves those actual IDs on every repeat.
IDs are not forced from production constants and are not promised identical across independent new
environments. The plan/media digest prevents silently interpreting a changed plan as the same fixture.
Ready reruns validate row/media existence and hashes, preserving operator fields, primary designations,
credentials and baseline references. They neither create duplicates nor synchronize edits to defaults.

Graph creation uses domain services in one transaction, including media ingestion with commit=False.
The ledger moves building → prepared → ready; primary designation runs after the graph commit. A
prepared graph can finish after interruption only if every reference/content validation succeeds.
Failure rolls back uncommitted DB rows, records diagnostics and never claims ready. New upload files
from a failed transaction may remain as explicitly listed orphans; inspect rather than deleting shared
media or attempting an automatic reset. A failed/incomplete manifest refuses ordinary repeat seeding.
The same Review lock serializes v4/v5 seed operations.

There is **no v5 destructive cleanup command**. Keep operator edits and the live Review; do not reset,
drop, wipe or recreate it. Any eventual removal requires separate explicit authorization and the exact
owning-worktree guarded environment command. DEV, UAT, Stable Preview, Sourcing and production retain
their own resources and baseline semantics.

## Live acceptance and limits

[Browser evidence](maps-origins-001/refinement-v5/README.md) includes authenticated real-database
screenshots and machine-readable reports at 1440×844, 1024×844 and 390×844. Origins KPIs match the API,
all 12 markers exist, keyboard selection opens the multi-identity inspector, and compact Filters rows
are clickable at all widths. Five-species comparison verifies the 1–5 overlap matrix; live collection
directories, media/privacy and an isolated local provider-refusal test are covered. Provider refusal
is explicitly injected, not a claim of a fresh real OSM outage.

The public OSM policy requires a browser Referer. The previous no-referrer tile setting violated that
requirement; outgoing requests were inspected and aborted before transmission. Collection origins now
uses local Natural Earth by default; optional online detail is configuration-gated, sends only the app
origin cross-origin and latches image errors without retry. HTTP-200 policy artwork cannot reliably be
detected by an image error handler; operators must resolve provider permission before enabling it.
Actual browser 125%/150% zoom, physical touch and screen-reader certification remain operator checks;
viewport resizing is reported separately and is not zoom evidence.

Validation details and remaining scope are recorded in the MAPS-ORIGINS-001 handoff. No canonical
feature verification, staging, commit, push or delivery was performed.
