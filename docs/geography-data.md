# Canonical geography data

Florabase's canonical GeographicPlace hierarchy is a normalized extract of Unicode Common Locale
Data Repository (CLDR) JSON 48.2.1. Unicode published that stable package release on 2026-07-08.
The source files are maintained by the Unicode Consortium and CLDR's territory containment is based
on UN M.49 macro-regions.

## Source, attribution, and license

- Dataset: Unicode Common Locale Data Repository (CLDR)
- Pinned package release: 48.2.1
- Containment source:
  `cldr-json/cldr-core/supplemental/territoryContainment.json`
- English display-name source:
  `cldr-json/cldr-localenames-full/main/en/territories.json`
- Copyright: © 1991–2026 Unicode, Inc.
- License: Unicode License v3, SPDX `Unicode-3.0`; the redistributed notice is in
  `backend/alembic/data/UNICODE-LICENSE.txt`

The two verified upstream SHA-256 values are:

```text
9f7d2eed5278ebb7c302b7536e391708b237945c314d09a206c632c2fab45ee2  territoryContainment.json
158c1d575308f7e46912edbeda435c8fe2ef5dad280798231f3a432e406b1807  territories.json
```

## Reproducing the snapshot

Download only the two pinned official Unicode repository files outside normal application runtime:

```bash
curl -fsSLo /tmp/cldr-territoryContainment.json \
  https://raw.githubusercontent.com/unicode-org/cldr-json/48.2.1/cldr-json/cldr-core/supplemental/territoryContainment.json
curl -fsSLo /tmp/cldr-territories-en.json \
  https://raw.githubusercontent.com/unicode-org/cldr-json/48.2.1/cldr-json/cldr-localenames-full/main/en/territories.json
sha256sum /tmp/cldr-territoryContainment.json /tmp/cldr-territories-en.json
python3 scripts/generate_geographic_places.py \
  /tmp/cldr-territoryContainment.json \
  /tmp/cldr-territories-en.json \
  backend/alembic/data/geographic_places_cldr_48_2_1.json
```

The normalized snapshot has 287 records and SHA-256
`ecf0c2750a6a85d8c3e128323bb7c7dcf52bccb29697740acb53119a27d4fd6b`. The generator removes
deprecated and overlapping grouping-only CLDR containment entries, retains grouping code `419` to
preserve the applicable Latin America and Caribbean intermediate level in one coherent tree,
uses English display names (`World` capitalization and UN M.49's formal `Latin America and the
Caribbean` label are retained for the two corresponding region codes), assigns typed upstream
codes, and deterministically derives stable UUIDv7 identities. Its validation and backend tests
reject missing parents, multiple parents,
cycles, multiple roots, duplicate source identifiers, duplicate UUIDs, and missing representative
nodes.

The complete upstream repository is not vendored. The committed normalized JSON and license are the
only runtime inputs. Alembic revision `20260830_0007` seeds them during normal migration without
internet access; startup and API requests never fetch geography data.
