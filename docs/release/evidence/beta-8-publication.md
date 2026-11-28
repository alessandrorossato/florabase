# v0.1.0-beta.8 publication record

Published on 2026-11-23 through the protected
[Protected Florabase release](https://github.com/alessandrorossato/florabase/actions/runs/45124950700)
workflow (run `45124950700`, attempt 1; `verify` and `publish` succeeded). The operator created
the annotated tag `v0.1.0-beta.8` (object `3a6dc331ed0770cf24b171b4af650dbadda0585f`) on
`main` `c4ffd63004bf4448af902ffb9a012f5d53f965bd`, set the `beta-release` environment approval to
that commit, dispatched the workflow and approved the environment. Before tagging, `ci.yml`
(quality, integration, build, release-migration) and the non-publishing rehearsal had succeeded on
that exact commit.

## Release

[GitHub Release `v0.1.0-beta.8`](https://github.com/alessandrorossato/florabase/releases/tag/v0.1.0-beta.8):
prerelease, not a draft, published 2026-11-23T06:49:28Z. The Release API reports
`immutable: false`, as for beta.7. The immutability setting for future releases remains an
operator decision. It is the first release published under the deployable `:latest`
`compose.yaml` contract ([ADR 0009](../../decisions/0009-minimal-production-compose.md),
[ADR 0010](../../decisions/0010-deployable-latest-compose.md)): `compose.yaml` is taken directly
from the release tag in Git (and its SHA-256 `0c01356f0365bb13a601a8661fb9fdfc32ce24f1ea7a91515fdfb78bc2d62088`
is bound in `release-manifest.json`'s `compose_template` field) rather than uploaded as a separate
rendered release asset.

| Asset | SHA-256 |
| --- | --- |
| `release-manifest.json` | `32138ffea752d328c81c1cbd261c1ecd73064bd369436ffa2cbc1067a02c6b1c` |
| `RELEASE.md` | `2c3d2093afa30a2bb36c836395ff038a5813e2bd98ba9fc5549cfbde8217120f` |
| `postgresql-sbom.cdx.json` | `6bdc3abf3c571f91d40723cb932b2bf8b2857fef5452aa9b0e271fd902539129` |
| `florabase-0.1.0-beta.8-source.tar.gz` | `a82b1f343b31d62d7665ed4a1fcd79873925075980f2b3019194f30be5c84f00` |

The downloaded files' SHA-256 values equal the Release API asset digests.

## Images

`release-manifest.json` (schema version 3) names version `0.1.0-beta.8`, source revision
`c4ffd63004bf4448af902ffb9a012f5d53f965bd` (clean), Alembic head `20261110_0047`,
`compose_template.compose.yaml`
`sha256:0c01356f0365bb13a601a8661fb9fdfc32ce24f1ea7a91515fdfb78bc2d62088`, and workflow run
`45124950700` attempt 1. Each GHCR tag (and promoted `:latest` at publication) resolves to the
manifest's index digest:

| Image | Reference in `release-manifest.json` | Index digest | Platform digest (`linux/amd64`) |
| --- | --- | --- | --- |
| Backend | `ghcr.io/alessandrorossato/florabase-backend@sha256:1b63b75730cb11c5099f0280834ac974ac93db952c7ee1e6f676d09affc120ee` (tag `0.1.0-beta.8` and `:latest`) | `sha256:1b63b75730cb11c5099f0280834ac974ac93db952c7ee1e6f676d09affc120ee` | `sha256:e8fc8acd7a319cb2fa38648ceec4085dcc0533026984ac775b093bae1783c2c5` |
| Frontend | `ghcr.io/alessandrorossato/florabase-frontend@sha256:15153404fd13a9db9a06e7401c751d63ff447a6a97ee9c7bab2b9214172290d8` (tag `0.1.0-beta.8` and `:latest`) | `sha256:15153404fd13a9db9a06e7401c751d63ff447a6a97ee9c7bab2b9214172290d8` | `sha256:7bb8229966f45bee5c7f6d2c6e59dbf819c9fb5e758aec80f065ba56f327495d` |
| PostgreSQL | `ghcr.io/alessandrorossato/florabase-postgres:18.6-alpine-florabase.4@sha256:2d843bd2ac7e9cebc4b4aaed2d24bb6f7717261fa27e798fe1f28583e853d625` (tag `18.6-alpine-florabase.4` and `:latest`) | `sha256:2d843bd2ac7e9cebc4b4aaed2d24bb6f7717261fa27e798fe1f28583e853d625` | `sha256:c677e9e20e56d6c32c2d359f66b44b66e2ead27d51fcaa64528f78a88299589d` |

The PostgreSQL index equals the reproduced `18.6-alpine-florabase.4` pin in `release/inputs.json`
at commit `c4ffd63`.

## Attestations

`gh attestation verify` (GitHub CLI 2.105.0) succeeded for `release-manifest.json` and for each of
the three OCI image indexes as documented in
[Install Florabase — Verify the release provenance](../../operate/installation.md#verify-the-release-provenance-optional-digest-pinning):

```bash
repo=alessandrorossato/florabase
sha=c4ffd63004bf4448af902ffb9a012f5d53f965bd

gh attestation verify release-manifest.json --repo "$repo" \
  --signer-workflow "$repo/.github/workflows/beta-images.yml" \
  --source-ref refs/heads/main --source-digest "$sha" \
  --deny-self-hosted-runners

gh attestation verify \
  oci://ghcr.io/alessandrorossato/florabase-backend@sha256:1b63b75730cb11c5099f0280834ac974ac93db952c7ee1e6f676d09affc120ee \
  --repo "$repo" \
  --signer-workflow "$repo/.github/workflows/beta-images.yml" \
  --source-ref refs/heads/main --source-digest "$sha" \
  --deny-self-hosted-runners

gh attestation verify \
  oci://ghcr.io/alessandrorossato/florabase-frontend@sha256:15153404fd13a9db9a06e7401c751d63ff447a6a97ee9c7bab2b9214172290d8 \
  --repo "$repo" \
  --signer-workflow "$repo/.github/workflows/beta-images.yml" \
  --source-ref refs/heads/main --source-digest "$sha" \
  --deny-self-hosted-runners

gh attestation verify \
  oci://ghcr.io/alessandrorossato/florabase-postgres:18.6-alpine-florabase.4@sha256:2d843bd2ac7e9cebc4b4aaed2d24bb6f7717261fa27e798fe1f28583e853d625 \
  --repo "$repo" \
  --signer-workflow "$repo/.github/workflows/beta-images.yml" \
  --source-ref refs/heads/main --source-digest "$sha" \
  --deny-self-hosted-runners
```

Recorded verification results:

- `release-manifest.json`: `Loaded digest sha256:32138ffea752d328c81c1cbd261c1ecd73064bd369436ffa2cbc1067a02c6b1c for file://release-manifest.json` — `Loaded 1 attestation from GitHub API` — `✓ Verification succeeded!` (`Build workflow: .github/workflows/beta-images.yml@refs/heads/main`, `Signer workflow: .github/workflows/beta-images.yml@refs/heads/main`).
- `florabase-backend`: `Loaded digest sha256:1b63b75730cb11c5099f0280834ac974ac93db952c7ee1e6f676d09affc120ee for oci://ghcr.io/alessandrorossato/florabase-backend@sha256:1b63b75730cb11c5099f0280834ac974ac93db952c7ee1e6f676d09affc120ee` — `Loaded 1 attestation from GitHub API` — `✓ Verification succeeded!`.
- `florabase-frontend`: `Loaded digest sha256:15153404fd13a9db9a06e7401c751d63ff447a6a97ee9c7bab2b9214172290d8 for oci://ghcr.io/alessandrorossato/florabase-frontend@sha256:15153404fd13a9db9a06e7401c751d63ff447a6a97ee9c7bab2b9214172290d8` — `Loaded 1 attestation from GitHub API` — `✓ Verification succeeded!`.
- `florabase-postgres`: `Loaded digest sha256:2d843bd2ac7e9cebc4b4aaed2d24bb6f7717261fa27e798fe1f28583e853d625 for oci://ghcr.io/alessandrorossato/florabase-postgres:18.6-alpine-florabase.4@sha256:2d843bd2ac7e9cebc4b4aaed2d24bb6f7717261fa27e798fe1f28583e853d625` — `Loaded 1 attestation from GitHub API` — `✓ Verification succeeded!`.

## Scope

This record provides remote evidence for the publication criteria of BETA-IMAGE-001 and the
remote-only GHCR, attestation and Release API stages of beta-postgres-repro-001 for
`v0.1.0-beta.8` (`18.6-alpine-florabase.4`). It changes no feature status. Host installation with
the release `compose.yaml`, real-data onboarding and the beta soak remain BETA-DATA-001 and
BETA-ACCEPTANCE-001.
