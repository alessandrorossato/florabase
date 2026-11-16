# REL-01 non-publishing rehearsal

Run on 2026-11-15 from clean local source commit
`de8bfaca54819350f6cf5cc3c00879e119db2949`, based on
`172e93fc8b7829f3e8d510049b9eb8d09a34c64d`. The rehearsal used a native Linux amd64 development
host with Docker Engine 29.9.3, Compose v5.7.1 and the workflow-pinned Buildx v0.38.1. The smoke
started from disposable empty PostgreSQL and media stores and created synthetic data for owner,
media, upgrade and recovery checks.

```bash
python3 scripts/release-tools.py scripts/rehearse-beta-release.py \
  --output /tmp/florabase-rel01-rc1.bCra4OPI/output
```

The run log is `/tmp/florabase-rel01-rc1.bCra4OPI/preflight.log`. The output directory contains
`assets/portable-compose.yaml`, `assets/release-manifest.json`,
`diagnostics/image-smoke.log`, `diagnostics/portable-smoke.log`,
`diagnostics/publication-state.json` and `diagnostics/scans/`.

The run reported `SCAN/SMOKE: PASS`, `VALIDATE ASSETS: PASS`, `PROMOTE: PASS` and
`BETA_RELEASE_REHEARSAL_PASSED`. The image smoke verified the runtime package and HTTP release
surface. The portable smoke passed fresh install, restart, schema refusal, failed upgrade and
restore. Promotion ran against the disposable loopback registry, and the attestation and Release
API records show input validation only.

| Surface | Verified value |
| --- | --- |
| Backend project and runtime module | `1.0.0-rc.1` |
| Installed Python package metadata | `1.0.0rc1` (PEP 440) |
| Frontend package and served `/release.json` | `1.0.0-rc.1` |
| Backend and frontend OCI version labels | `1.0.0-rc.1` |
| Manifest, locked build inputs and portable Compose header | `1.0.0-rc.1` |
| Intended Git tag | `v1.0.0-rc.1` |
| Image platform and Alembic head | `linux/amd64`, `20261110_0047` |

Portable Compose used loopback registry references with the following exact image index digests.

| Service | Index digest |
| --- | --- |
| Backend | `sha256:8f7f25d232cfbb5213c027b5ae58dd5cc92410fd0647090db75357e015c4c406` |
| Frontend | `sha256:3067bdd8f45be2897ceb32ae4ccaa186de52aba31559cdbfa96a369d1dcef53d` |
| PostgreSQL | `sha256:baf7806351b332422b6dff9f956f1080a2f3150eab87e4ee70565a8236591658` |

The verified SHA-256 for the Compose asset was
`84f5a40a5833f924e081e76c187cf9f3fe854a6575a21dc89a15ba823e53d476` and for the manifest was
`685337f7a7c87e50192669f2c84d31ed25e44df2a095d95bcf4a4fe8773c60e8`.
The release request's size and hash matched each asset. The source archive embedded the same
commit as the release manifest and the served release metadata.

Independent QA found and verified fixes for the protected remote-tag validator and stable draft
assertions. Those protected-path and regression-test corrections followed the local RC snapshot.
The independent stable-version snapshot `f03879303910d6ef14f4cabd61bc2f5e1bb17a8f` passed 60
release tests, 4 tool-lock tests and 62 controller tests. QA separately confirmed that hosted
rehearsal and protected publication refuse both v1 channels with the current beta-era feature
checker. Beta was exercised on the tooling branch by the same release, lock and controller suites.

The real-host gates, operator release approval and the DOC-02 checker integration remain tracked
under the [v1.0.0 release scope](../scope-v1.md). See the [REL-01 runbook](../rel-01-tooling.md) for
the release preparation procedure.
