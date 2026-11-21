# v0.1.0-beta.6 publication record

Published on 2026-11-21 by the operator through the protected
[Protected Florabase release](https://github.com/alessandrorossato/florabase/actions/runs/44888816590)
workflow (run `44888816590`, attempt 1; `verify` and `publish` succeeded). The operator created
the annotated tag `v0.1.0-beta.6` (object `1be504a310d3af8e6e795ffd02939a02c02e081b`) on
`main` `3552b3d9f8be4832c9b6f3ba8dab29f6437ee6cc`, set the `beta-release` environment approval to
that commit, dispatched the workflow and approved the environment. Before tagging, `ci.yml`
(quality, integration, build, release-migration) and the non-publishing rehearsal had succeeded
on that exact commit.

## Release

[GitHub Release `v0.1.0-beta.6`](https://github.com/alessandrorossato/florabase/releases/tag/v0.1.0-beta.6):
prerelease, not a draft, published 2026-11-21T09:24:28Z. The Release API reports
`immutable: false`, as for beta.5. The immutability setting for future releases remains an
operator decision.

| Asset | SHA-256 |
| --- | --- |
| `portable-compose.yaml` | `c0bea140a7f0686a6ef8ef76b43058c4a396b9087e644c2c406de5630ec8b1bf` |
| `compose.yaml` | `e32ed997385044e721009d50afb2067c226422778724c752064d71432c508f1e` |
| `florabasectl.py` | `52775253b94b611f5b3bd3befa30d17741e298fa5f04bcfe0a3dc15cd264dcaa` |
| `florabase.env.example` | `26b2d05cb1c53193d895609872b3bed5aeb5b42fa734582c8ad3b35e367e55a7` |
| `release-manifest.json` | `3c06e7b0b63eac228d290f1b5327f89b690ec6e160d8566901c4f264d72cc39b` |
| `RELEASE.md` | `8165bd9ae973ce3703713fc9f930b13979828ce65a415fced79ea0bc6419b19f` |
| `postgresql-sbom.cdx.json` | `300d5cb3c8939a275c6a0f35e6963c484539467143030caaa2c9bb22d6fed75a` |
| `florabase-0.1.0-beta.6-source.tar.gz` | `6f673883c840647f1da91854cdc09407c4fb40fa7fce92f6c5a1e566e273c879` |

The downloaded files' SHA-256 values equal the Release API asset digests.

## Images

`release-manifest.json` names version `0.1.0-beta.6`, source revision `3552b3d` (clean) and
Alembic head `20261110_0047`. Each GHCR version tag resolves to the manifest's index digest:

| Image | Tag | Index digest |
| --- | --- | --- |
| Backend | `ghcr.io/alessandrorossato/florabase-backend:0.1.0-beta.6` | `sha256:26cef79884456a79da77da2147ed27a7980944147d13a031c1f02f4707e1d647` |
| Frontend | `ghcr.io/alessandrorossato/florabase-frontend:0.1.0-beta.6` | `sha256:96043d9bb63a0c74b8a068421c0a5e57904c038a877ed6f82c67f65e40413cb6` |
| PostgreSQL | `ghcr.io/alessandrorossato/florabase-postgres:18.6-alpine-florabase.3` | `sha256:2a50cabff7df4e5f108065b51585c2c202b92805f0b842dd3522aaf7e9158115` |

The PostgreSQL index equals the reproduced pin in [release inputs](../../../release/inputs.json).
This is the first GHCR publication of `18.6-alpine-florabase.3`.

## Attestations

`gh attestation verify` (GitHub CLI 2.105.0) succeeded for all eight subjects, with
`--signer-workflow alessandrorossato/florabase/.github/workflows/beta-images.yml`. The policy
enforced SLSA provenance v1, the GitHub Actions OIDC issuer, the `alessandrorossato/florabase`
source repository and signer `beta-images.yml@refs/heads/main`.

- The three image indexes above (operator run).
- `compose.yaml`, `portable-compose.yaml`, `florabasectl.py`, `florabase.env.example` and
  `release-manifest.json`, additionally bound with `--source-digest 3552b3d9f8be4832c9b6f3ba8dab29f6437ee6cc`.
  Each certificate names run `44888816590` attempt 1.

## Scope

This record provides remote evidence for the publication criteria of BETA-IMAGE-001 and the
remote-only GHCR, attestation and Release API stages of beta-postgres-repro-001. It changes no
feature status. Host deployment, HTTPS, persistence and recovery acceptance remain
BETA-RUNTIME-001. Real-data onboarding and the beta soak remain BETA-DATA-001 and
BETA-ACCEPTANCE-001.
