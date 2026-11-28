# v0.1.0-beta.10 publication record

Published on 2026-11-27 through the protected
[Protected Florabase release](https://github.com/alessandrorossato/florabase/actions/runs/45962728106)
workflow (run `45962728106`, attempt 1, succeeded). The operator created the annotated tag
`v0.1.0-beta.10` (object `09160014dcfcbaf28a052cd7789f3f58b1ed7612`, 2026-11-27T08:03:10Z) on
`main` `4111ed8eed08e5d4286e84d4bbdc5b0634239bb2` and dispatched the workflow. Before tagging,
`ci.yml` ([run `45960533164`](https://github.com/alessandrorossato/florabase/actions/runs/45960533164))
and the non-publishing rehearsal
([run `45960533337`](https://github.com/alessandrorossato/florabase/actions/runs/45960533337)) had
succeeded on that exact commit.

This record was written on 2026-11-28, after publication, from the Release API, the GHCR registry
and the GitHub attestations API.

## Release

[GitHub Release `v0.1.0-beta.10`](https://github.com/alessandrorossato/florabase/releases/tag/v0.1.0-beta.10):
prerelease, not a draft, published 2026-11-27T08:27:16Z. The Release API reports
`immutable: false`, as for earlier betas. `compose.yaml` is taken from the release tag in Git; its
SHA-256 `29c7cd863e851d908cbbc3ed8b0dd04a3eef40a23b33368af3e2c1081f6755d7` equals the
`compose_template` field of `release-manifest.json`.

| Asset | SHA-256 |
| --- | --- |
| `release-manifest.json` | `96abea32840add093ce26d3ec810157f66da862b67017d553d520c6401c2a58c` |
| `RELEASE.md` | `6b93be37686d7d91b236145caea22600318886836acc9e6af12223555c8212bc` |
| `postgresql-sbom.cdx.json` | `304d8cabd818fd38d2d4db5cbf17b987b2cb1f4405035a48479d19d1ad72976f` |
| `florabase-0.1.0-beta.10-source.tar.gz` | `9f3cfe5df428c504af373883498ed5c725e94c2dd23177863b92cea35750f4cf` |
| `florabase-0.1.0-beta.10.apk` | `34be19dd155ec9efc6efaf3dffd3b143cfb896167eecfc907e1a46f0b670ab08` |
| `florabase-0.1.0-beta.10.apk.sha256` | `24858f0388184054d2c45a823993ae86d2e1c80f25cabb170cf6d2d5071770d6` |

The downloaded `release-manifest.json`, `RELEASE.md` and `.apk.sha256` files hash to the Release
API asset digests, and the `.apk.sha256` file names the APK digest above.

## Images

`release-manifest.json` (schema version 3) names version `0.1.0-beta.10`, source revision
`4111ed8eed08e5d4286e84d4bbdc5b0634239bb2` (clean), platform `linux/amd64`, Alembic head
`20261125_0050`, and workflow run `45962728106` attempt 1. On 2026-11-28 each GHCR tag and
`:latest` resolved to the manifest's index digest:

| Image | Tags | Index digest | Platform digest (`linux/amd64`) |
| --- | --- | --- | --- |
| `ghcr.io/alessandrorossato/florabase-backend` | `0.1.0-beta.10`, `latest` | `sha256:a5a06121b8f06973bc3cbc69fa2312d864ef0bef9bd3ffa54f6446e643324861` | `sha256:52b9b8282d3b2450e69e8c84bd6255463cde0318cd398037cbd0e78fa589d415` |
| `ghcr.io/alessandrorossato/florabase-frontend` | `0.1.0-beta.10`, `latest` | `sha256:afe8ab16a3bbc7022602d04dcaa0e11bd82124c081374a45710f1529b1d71d3e` | `sha256:c11ff6b981654e5012faf7524b14b8df112eed8f5fda321c7e2c92c838385fd0` |
| `ghcr.io/alessandrorossato/florabase-postgres` | `18.6-alpine-florabase.6`, `latest` | `sha256:fa3d79573aca9e4558876fd82337d6892ebaa8ce3219444c793f481ddf88de9b` | `sha256:b61292b44712e5d8c695486d62c17cf58af99939535721d7be9e710fc65f1a3d` |

The PostgreSQL index equals the `18.6-alpine-florabase.6` pin in `release/inputs.json` at
`4111ed8`, built from `docker.io/library/postgres:18.6-alpine@sha256:123b17998ccaf47e53b502e8c6a1e79afd8f579c6f3eec83c563da026f957395`.

## Attestations

The GitHub attestations API returns one SLSA provenance v1 attestation for `release-manifest.json`
and for each of the three image index digests. Each statement names workflow
`.github/workflows/beta-images.yml` at `refs/heads/main` of `alessandrorossato/florabase` and
source commit `4111ed8eed08e5d4286e84d4bbdc5b0634239bb2`. This record reads the statements; it
does not repeat the cryptographic `gh attestation verify` check, which the operator can run as
documented in
[Install Florabase — Verify the release provenance](../../installation.md#verify-the-release-provenance-optional-digest-pinning)
with `sha=4111ed8eed08e5d4286e84d4bbdc5b0634239bb2` and the digests above.

## Android APK

The automatic [Mobile Android release APK](https://github.com/alessandrorossato/florabase/actions/runs/45965802666)
run that followed the protected release failed, and two manual re-dispatches from `aeaa9b0` also
failed. The causes, Corepack resolving the wrong pnpm from the repository root and the
`apksigner` 37 certificate output format, were fixed on `main` in #231 and #232. The re-dispatch from `main` `c83d816`
([run `45990452476`](https://github.com/alessandrorossato/florabase/actions/runs/45990452476),
2026-11-27T11:26Z, input tag `v0.1.0-beta.10`) succeeded: it built the APK from the tag's
sources with `main`'s workflow file and attached the signed `florabase-0.1.0-beta.10.apk`
(`versionCode` `100310`) and its `.sha256` to the Release at 2026-11-27T11:28:50Z. Obtainium
installs it from this prerelease when "Include prereleases" is on.

## Scope

This record provides remote evidence for the publication criteria of BETA-IMAGE-001 for
`v0.1.0-beta.10`. It changes no feature status. Host installation with the release
`compose.yaml`, real-data onboarding and the beta soak remain BETA-DATA-001 and
BETA-ACCEPTANCE-001.
