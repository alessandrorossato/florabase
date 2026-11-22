# v0.1.0-beta.7 publication record

Published on 2026-11-21 through the protected
[Protected Florabase release](https://github.com/alessandrorossato/florabase/actions/runs/44949666442)
workflow (run `44949666442`; `verify` and `publish` succeeded on attempt 2). On the operator's
instruction, the master orchestrator created the annotated tag `v0.1.0-beta.7` (object
`db56c532fca706a613fa684bd17765268764f629`) on `main` `1126c03a86ba5f203e859b1530f523c3475f981a`
and dispatched the workflow. Before tagging, `ci.yml` (quality, integration, build,
release-migration) and the non-publishing rehearsal had succeeded on that exact commit.

Attempt 1 stopped at its first `publish` step, before any package write, because the
`beta-release` environment secret `RELEASE_APPROVED_SHA` still named the beta.6 commit. The
operator set it to `1126c03`, reran the failed job and approved the environment.

## Release

[GitHub Release `v0.1.0-beta.7`](https://github.com/alessandrorossato/florabase/releases/tag/v0.1.0-beta.7):
prerelease, not a draft, published 2026-11-21T21:19:51Z. The Release API reports
`immutable: false`, as for beta.6. The immutability setting for future releases remains an
operator decision. It is the first release with the single self-initializing `compose.yaml`
([ADR 0008](../../decisions/0008-self-initializing-single-compose.md)).

| Asset | SHA-256 |
| --- | --- |
| `compose.yaml` | `89107dd61164b77fba8def9eed3b7bd4e473d0e1f72fb0749876bee2fa0e8120` |
| `release-manifest.json` | `8a23124d1f92c1db7f27d5f86bbeab1bad1f13e72195d14f1941fec1df8270ae` |
| `RELEASE.md` | `865afaaba8e1b64bd664498831ba5168de8982f3c61a0c760e52e19b261624e0` |
| `postgresql-sbom.cdx.json` | `90553338d3af5f5286f41011ef4bdc5068f973132ade84a8e7805b62e27e28df` |
| `florabase-0.1.0-beta.7-source.tar.gz` | `35fcc3ea1735d206e3fc7a882acae92a0dc8f79cda25fa9612037524f12e1701` |

The downloaded files' SHA-256 values equal the Release API asset digests.

## Images

`release-manifest.json` (schema version 3) names version `0.1.0-beta.7`, source revision
`1126c03` (clean), Alembic head `20261110_0047` and workflow run `44949666442` attempt 2. Each
GHCR tag resolves to the manifest's index digest:

| Image | Tag | Index digest |
| --- | --- | --- |
| Backend | `ghcr.io/alessandrorossato/florabase-backend:0.1.0-beta.7` | `sha256:cd55d768a1d17028d74f4e00294344a2508daa86bdb341864d190cd48422a041` |
| Frontend | `ghcr.io/alessandrorossato/florabase-frontend:0.1.0-beta.7` | `sha256:fae4a3b1b1b7a81d28729612f76467b10c19223f18c421c88acbfe48c0744099` |
| PostgreSQL | `ghcr.io/alessandrorossato/florabase-postgres:18.6-alpine-florabase.3` | `sha256:2a50cabff7df4e5f108065b51585c2c202b92805f0b842dd3522aaf7e9158115` |

The PostgreSQL index is unchanged from beta.6 and equals the pin in
[release inputs](../../../release/inputs.json).

## Attestations

`gh attestation verify` (GitHub CLI 2.105.0) succeeded with
`--signer-workflow alessandrorossato/florabase/.github/workflows/beta-images.yml` for:

- the three image indexes above;
- `compose.yaml` and `release-manifest.json`, additionally bound with
  `--source-digest 1126c03a86ba5f203e859b1530f523c3475f981a`. Each certificate names run
  `44949666442` attempt 2.

## Scope

This record provides remote evidence for the publication criteria of BETA-IMAGE-001 and the
remote-only GHCR, attestation and Release API stages of beta-postgres-repro-001. It changes no
feature status. Host installation with the release `compose.yaml`, real-data onboarding and the
beta soak remain BETA-DATA-001 and BETA-ACCEPTANCE-001.
