# Batch 06 security baseline

Reviewed on 18 November 2026 for BETA-SECURITY-001 and G-SEC. The source was clean `main`
`c555baabe916e3fea1ef2c8f834c747ced5aa926`. The [17 November hosted rehearsal](https://github.com/alessandrorossato/florabase/actions/runs/44173878510)
ran on GitHub-hosted Ubuntu 24.04, native `linux/amd64`, with a disposable loopback registry and
disposable smoke data. Its manifest identifies `0.1.0-beta.6` and Alembic head `20261110_0047`.

## Exact image evidence

The [archived rehearsal artifact](https://github.com/alessandrorossato/florabase/actions/runs/44173878510/artifacts/14369406403)
has archive digest `sha256:8f85958e6d0fb4a283c1e3dd2268567de4b8826b533a6071a3b89be82025ad64`
as reported by GitHub. The release manifest and the Docker-save descriptors agree on each index
and platform digest. `validate_scan()` accepted each retained report against the corresponding
configuration digest and expected runtime inventory. The scan used Trivy 0.69.3 at the
[locked digest](../../../release/inputs.json), with vulnerability and secret scanning enabled
and `/dev/null` as the ignore file.

| Image | OCI index digest | HIGH / CRITICAL / secrets |
| --- | --- | --- |
| Backend beta.6 | `sha256:4304e1f241ddb2af8a3064e6122b14b95c94eccf207d10785f1acf2ae6921bee` | 0 / 0 / 0 |
| Frontend beta.6 | `sha256:18cf15f8dda4ebee0896c8db4eafa53129ccc2e2f75d0d42ac3e98157dedfa25` | 0 / 0 / 0 |
| PostgreSQL 18.6-alpine-florabase.2 | `sha256:baf7806351b332422b6dff9f956f1080a2f3150eab87e4ee70565a8236591658` | 0 / 0 / 0 |

Hashing the raw PostgreSQL index, platform manifest and configuration independently matched the
retained descriptor identities. The platform manifest is
`sha256:0a660365cb4cfb708fd5443bed32926ce01478107ff9a88c6b28b3e971c3a1e6` and records 13 layers.
The Trivy CycloneDX SBOM has 54 components and SHA-256
`bf991b32ef59798d61c4946fecc489edbabbaeb23bbec67233d471a8e1bcd189`. Both the scan package
inventory and SBOM record `krb5-libs=1.22.3-r0`, `libxslt=1.1.43-r4` and `zlib=1.4-r0`.
The earlier 18 HIGH findings belong to the [.1 rehearsal](../../security/beta-distribution-001/postgresql-image.md).
Artifact and portable smoke, asset validation and local digest-preserving promotion passed.

On 18 November, anonymous pull-only GHCR manifest requests returned definite absence for the .2
version tag and both .2 digests, and for the backend/frontend beta.6 and RC.1 version tags. The
hosted rehearsal validated attestation and Release API inputs. GitHub issuance and publication
remain separate protected operations. The latest published beta is
[v0.1.0-beta.5](https://github.com/alessandrorossato/florabase/releases/tag/v0.1.0-beta.5).
Its GitHub Release API metadata reports `immutable: false`. The published image content still
has digest identities. The operator needs to verify the immutability setting for future releases.

## Candidate evidence still required

- Build and scan the final RC pair by digest, using the exact pinned .2 image. Retain the raw
  reports, scanner and database identity or timestamp, descriptor and SBOM hashes, and artifact
  smoke per image. Disposition any remaining finding by advisory, package, digest, platform,
  fix availability and runtime applicability. An exception or VEX requires explicit operator
  acceptance and is subject to the existing fail-closed publication contract.
- On the disposable production stack, enumerate unauthenticated backend routes and check the
  frontend and backend surfaces separately. The backend's `FastAPI()` constructor leaves the
  generated documentation and schema routes enabled by default. The frontend proxies `/api/`.
  Test the backend directly inside the isolated network before closing the three-route G-SEC
  criterion. Record the second-host port probe, ENG-01 password change and recovery, reporting
  channel, and the ENG-02 header or deferral evidence.
- Treat a PostgreSQL digest switch as a separate operator-approved maintenance event. Record an
  independent reproducibility comparison and a paired restore rehearsal before that switch.
- Independently review and freeze the security increment, then run one fresh canonical FULL
  at the designated delivery boundary. The archived beta.6 reports describe the November 17
  rehearsal and the scanner data used in that run. Final RC scans, G-SEC, protected RC attestation, and
  operator acceptance are pending.
