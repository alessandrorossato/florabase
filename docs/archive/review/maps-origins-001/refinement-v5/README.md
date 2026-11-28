# Authenticated Review — Origins corrections and Botanical Dataset v5

2026-10-22 · c902 · `feat/maps-origins-001-candidate` · live Review
[Collection origins](http://localhost:15174/#/map). All collection/native-range responses in these
captures come from the real persisted synthetic Review database after owner UI sign-in.

- `browser-report.json`: real origins KPIs (12 mapped / 42 direct records / 22 identities / 2 without
  coordinates), exact marker/inspector selection, local geography with external traffic blocked,
  no horizontal overflow and compact 44px Filters rows at 1440×844, 1024×844 and 390×844.
- `extended-browser-report.json`: five chosen species, BR5/TH4/IT3/US2/AU1 coverage, keyboard territory
  selection, real collection directories, no automatic external media contact, isolated optional
  basemap refusal. Tile refusal is a local test double, not a fresh public OSM outage.
- `links-media-report.json`: KPI drill-downs, actual origin→SeedLot→Photos navigation, protected image
  decoding/attribution and unauthenticated 401, Harvest→Stored material, no automatic remote photo
  contact, exactly one explicitly requested no-referrer Preview once against an intercepted refusal.
  Responsive inspector/Close/backdrop checks preserve shared apply-as-chosen behavior.
- `preservation.json`: original v4 ledger/references and owner credentials unchanged, two seeds equal,
  every pre-existing foreign project inventory unchanged, measured disk footprint. No hashes of
  credentials or secrets are included.
- `environment-status.txt` and `dataset-status.json`: final guarded source/health/revision/v4/v5 status.
- `verification.json`: completed automated checks; no canonical verification receipt.

Representative screenshots are named by viewport and surface. `1440-selected.png` shows a site with
13 direct records and 6 identities; `*-filters.png` documents the corrected checkbox layout.
`*-map.png` and `*-inspector.png` show responsive panes. `native-five-species.png` shows comparison and
territory inspection; `native-recorded-places.png` retains broad, exact, custom and boundary-unavailable
cases. `protected-local-photo.png` and `external-reference-private.png` distinguish actual protected
content from metadata-only external references. `injected-online-403.png` is explicitly a mock failure.

The eight licensed photographs are species illustrations for synthetic records, not claimed specimens.
See the [dataset document](../../extended-botanical-dataset-v5.md) and checked-in media source/licence
manifest. Neither seeding nor acceptance launches real tile prefetch or GBIF occurrence downloads.

The adjacent capture scripts are optional reproducible browser harnesses, not application dependencies.
They require Playwright/Chromium already installed, the live candidate-owned Review, and
`REVIEW_PASSWORD_FILE` pointing to the existing mode-0600 owner credential file. Set `NODE_PATH` to an
installed Playwright node_modules directory, and `PLAYWRIGHT_BROWSERS_PATH` if appropriate. Run each
script with Node; they sign in through the UI and write evidence beside themselves. They make no
collection writes. Provider-failure routes are intercepted and explicitly labelled. Password content
is read only into the login interaction and is never logged, saved or included in reports.

Viewport resizing is **not actual browser zoom**. 125%/150% zoom, screen reader, physical touch and
operator visual acceptance remain unverified. Natural Earth is generalized 1:110m context, not detailed
offline street cartography. Arbitrary HTTP-200 provider policy artwork cannot reliably be recognized
by an image error callback; online detail stays deployment-disabled until permission is resolved.

Older parent/sibling captures are historical synthetic/v4 evidence and do not describe current online
basemap defaults or current dataset volume. This evidence supersedes those limits.
