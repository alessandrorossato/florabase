# Third-party notices and data sources

Florabase itself is licensed under `AGPL-3.0-or-later` (see [LICENSE](LICENSE)). Bundled
third-party assets, operator-installed reference snapshots, and optional runtime data sources keep
their own licences and attribution terms, summarized below from the repository's committed notices
and [`frontend/src/settings/DataSourcesScreen.tsx`](frontend/src/settings/DataSourcesScreen.tsx).

| Asset or data source | Distribution / access | Licence | Full notice / documentation |
| --- | --- | --- | --- |
| **IBM Plex Mono**, **Instrument Sans**, **Newsreader**, **Source Sans 3**, **Source Serif 4** (typefaces) | Bundled with frontend | SIL Open Font License 1.1 (`OFL-1.1`) | [`frontend/public/licenses/ibm-plex-mono.txt`](frontend/public/licenses/ibm-plex-mono.txt), [`instrument-sans.txt`](frontend/public/licenses/instrument-sans.txt), [`newsreader.txt`](frontend/public/licenses/newsreader.txt), [`source-sans-3.txt`](frontend/public/licenses/source-sans-3.txt), [`source-serif-4.txt`](frontend/public/licenses/source-serif-4.txt) |
| **qrcode-generator** (2.0.4, Kazuhiko Arase) | Bundled with frontend | MIT | [`frontend/public/qrcode-generator-LICENSE.txt`](frontend/public/qrcode-generator-LICENSE.txt) |
| **Natural Earth** (1:110m Admin 0 map units 5.1.1 / v5.1.2 presentation geometry) | Bundled with frontend (offline) | Public Domain (attribution optional) | [`frontend/src/native-ranges/data/NATURAL-EARTH-NOTICE.md`](frontend/src/native-ranges/data/NATURAL-EARTH-NOTICE.md), [`docs/features/explore/native-ranges-explore.md`](docs/features/explore/native-ranges-explore.md) |
| **Unicode CLDR** (v48.2.1 canonical territory seed data and territory mapping) | Bundled with backend and frontend | Unicode License v3 (`Unicode-3.0`) | [`backend/alembic/data/UNICODE-LICENSE.txt`](backend/alembic/data/UNICODE-LICENSE.txt), [`frontend/src/native-ranges/data/UNICODE-LICENSE.txt`](frontend/src/native-ranges/data/UNICODE-LICENSE.txt), [`docs/architecture/geography-data.md`](docs/architecture/geography-data.md) |
| **Botanical Review / UI Lab synthetic fixture photos** (8 Wikimedia Commons JPEG derivatives) | Development / UI Lab fixtures only (not application collection media) | Per-file CC0 / CC BY (see adjacent manifest) | [`frontend/src/ui-lab/assets/NOTICE.md`](frontend/src/ui-lab/assets/NOTICE.md), [`scripts/fixtures/botanical-v5/NOTICE.md`](scripts/fixtures/botanical-v5/NOTICE.md) |
| **World Flora Online (WFO) Plant List** (reviewed snapshot, e.g. 2026-06) | Operator-installed local snapshot; **not distributed** with Florabase and never fetched at run time | CC0 (acknowledge WFO; retain release DOI, retrieval date and checksum) | [`docs/features/explore/collection-taxonomy.md`](docs/features/explore/collection-taxonomy.md), [`docs/archive/TAXONOMY-003/taxonomy-003-source.md`](docs/archive/TAXONOMY-003/taxonomy-003-source.md) |
| **Kew World Checklist of Vascular Plants (WCVP)** (v15 / v16; TDWG WGSRPD level-3 crosswalk) | Operator-installed sealed local index; **not distributed** with Florabase | CC BY 3.0 Unported (retain Kew citation, release version and licence with proposals/applications) | [`docs/features/explore/native-range-enrichment.md`](docs/features/explore/native-range-enrichment.md), [`docs/archive/ENRICHMENT-001/native-range-enrichment-source-v15.md`](docs/archive/ENRICHMENT-001/native-range-enrichment-source-v15.md), [`docs/archive/WCVP-VERSION-001/wcvp-version-001.md`](docs/archive/WCVP-VERSION-001/wcvp-version-001.md) |
| **GBIF** (taxon reference search and species occurrence density) | Fetched on demand only when the operator searches, confirms/refreshes a link, or loads occurrence data | Per-dataset licences; cite the published dataset and preserve publisher attribution | [`docs/features/explore/species-distribution.md`](docs/features/explore/species-distribution.md) |
| **OpenStreetMap tiles** (optional street-level basemap) | Fetched at run time **only** when explicitly enabled by the operator in `runtime-config.js` (off by default) | ODbL + tile provider usage policy and attribution | [`docs/operate/deployment.md`](docs/operate/deployment.md) |

## Third-party software dependencies

Third-party Python (PyPI) and JavaScript/TypeScript (npm) software dependencies declared in
`backend/pyproject.toml`, `backend/requirements*.lock`, `frontend/package.json`, and
`frontend/pnpm-lock.yaml` keep their own licences. All production dependencies must remain
compatible with `AGPL-3.0-or-later`. Frontend production builds collect npm dependency notices via
`frontend/build-notices.mjs`, and `make license-check` audits installed PyPI and npm dependency
licences locally.
