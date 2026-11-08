# Florabase PostgreSQL image (`florabase-postgres`)

Status: integrated for implementation and verification (operator approval, 7 November 2026).
**Not published.** Publication, tags and real-host use remain separately authorized.

## What it is

`ghcr.io/alessandrorossato/florabase-postgres:18.6-alpine-florabase.1` is the official PostgreSQL
image the operator approved, with three changes and nothing else:

| Change | Why |
| --- | --- |
| `/usr/local/bin/gosu` removed | Its embedded Go 1.24.6 stdlib carries 1 CRITICAL / 25 HIGH advisories; no fixed official artifact exists (see [remediation evaluation](postgresql-gosu-remediation.md)) and Florabase never runs PostgreSQL as root |
| `zlib` 1.3.2-r1 → 1.4-r0 | CVE-2026-4738 (Critical), reported by Grype but not by the pinned Trivy; fixed in Alpine 3.24 |
| `USER 70:70`, the `florabase-postgres-entrypoint` guard and a root refusal on line 2 of the upstream `docker-entrypoint.sh` | Without gosu the upstream root branch cannot work. Root is refused (exit 64) before anything is created, chowned or initialized, through the image entrypoint and through an overridden `--entrypoint docker-entrypoint.sh` or `docker-ensure-initdb.sh`/`docker-enforce-initdb.sh` (which source it first) |

Inputs ([`postgres/`](../../../postgres/)): the base
`docker.io/library/postgres:18.6-alpine@sha256:123b17998ccaf47e53b502e8c6a1e79afd8f579c6f3eec83c563da026f957395`
(amd64 `sha256:300ebd02c6d4de9ee27ad7f6855d5d21b4d3a4a5117767c1197d284c635d9736`, docker-library
`e00e1bd`), the Dockerfile, the entrypoint and root-refusal scripts and the repository license. Labels record the base
name and digest, the image version and source; there is deliberately no per-commit label.

## Release contract

- **Pinned by content.** `release/inputs.json` `postgresql` holds the expected index
  `sha256:4edc079088c3f78b69fc8f9473e33881ebabea7fea2d82b3227b70a69ae3b7de` and platform manifest
  `sha256:55b1969a7fddad118ca07a15058a43a5916dec3e4dbab38029e671225b392b91`, the
  `source_date_epoch` (1762387200) and the exact `upstream` identity. `beta_release.py check`
  refuses a Dockerfile whose base, base-digest label or version differs, or that uses `ARG`.
- **Deterministic build.** The recorded `moby/buildkit:v0.34.2` image digest builds with `--no-cache`,
  `rewrite-timestamp`, the fixed epoch and no in-index provenance/SBOM (those embed build times);
  `/var/log/apk.log` is removed because it records install times. `imagetools create` then wraps the
  single amd64 manifest in a bare index. Two fresh local builders reproduced both pins. The beta.3
  GitHub publication used a different BuildKit image (0.33.1) and reported a different platform
  manifest and config. The old workflow retained no raw manifest/config or layer descriptors, so its
  first differing byte/component is not established. `release/inputs.json` is restored to the exact
  previously recorded 0.34.2 image, while the new GitHub-hosted rehearsal compares that toolchain
  with the failed run's exact 0.33.1 image and retains raw OCI documents and layer descriptor hashes.
  This change is a candidate correction until that hosted evidence passes. The workflow pins the
  Buildx client (`docker/setup-buildx-action` with `version: v0.38.1`) and BuildKit daemon image.
  The rehearsal also exercises shared application build, scan, manifest, smoke, asset and
  digest-preserving promotion helpers against an owned disposable registry. Remote GHCR writes,
  GitHub attestations and Release API finalization remain publication-only. The publisher continues
  to call `require_pinned_postgres` before copying any image to GHCR; it does not accept a new digest.
  Reproducibility deliberately does not run in every release's verify job, where a superseded Alpine
  pin would block application releases.
- **Same release manifest, same identity every release.** Manifest schema v2 records the derived
  image and its upstream base in `postgresql`. Every application release references the identical
  PostgreSQL index, so the controller's rule that `promote` never changes PostgreSQL still holds, and
  the pair plus PostgreSQL are bound to one manifest by immutable digests.
- **Protected publication only; built once, re-verified always.** When the pinned version is not yet
  published, the existing manual, environment-approved workflow builds it in a disposable loopback
  registry, `require_pinned_postgres` refuses anything that does not reproduce the pins, and only
  then copies those exact bytes (`imagetools create --prefer-index=false`) to a GHCR candidate tag;
  nothing unverified reaches GHCR. When `18.6-alpine-florabase.1` already exists it must point at the
  pinned index (registry manifest digest, verified against the returned bytes; anything other than a
  definite `MANIFEST_UNKNOWN`/`NAME_UNKNOWN` 404 refuses), and it is not rebuilt.
  Either way every release re-verifies the published bytes: registry identity, the unchanged
  fail-closed scan gate, SBOM (pinned Trivy CycloneDX, release asset `postgresql-sbom.cdx.json`),
  artifact smoke with the pair and `actions/attest-build-provenance`; the version tag is written only
  on first publication.
- **Consumers verify it.** The controller requires the Florabase repository, the recorded upstream
  base, a reference tag equal to the version, user `70:70`, the guard entrypoint and the base-digest
  and version labels on the pulled image, and checks the platform digest; the artifact smoke
  additionally checks gosu absence and root refusal through every entry point.

## Verification evidence

[`postgresql-image/registry-verification.json`](postgresql-image/registry-verification.json):
built with the pinned BuildKit into a disposable loopback registry, pulled by the pinned index
digest, then:

| Check | Result |
| --- | --- |
| Registry identity | index `4edc0790…` holding exactly the amd64 manifest `55b1969a…`; equal to the pins |
| Release gate (pinned Trivy 0.69.3, vuln+secret, HIGH/CRITICAL, no ignore file) on the pulled bytes | PASSED: 0 / 0, 0 secrets; Alpine 3.24 package inventory present; no gosu target |
| Grype v0.121.1, squashed filesystem | 0 Critical / 0 High; 3 Medium (busybox CVE-2025-60876, no fix) |
| Grype v0.121.1, `--scope all-layers` | identical: 3 Medium, no gosu or Go stdlib findings |
| SBOM | 54 components, none is gosu |
| Root start | exit 64 with an explicit message before any directory or data change |

**Runtime smoke** ([evidence](../../beta-distribution-001-evidence.json)) runs on an image built from
`postgres/` with the local builder and served from the nested test registry, so its digest differs
from the pins; it proves behavior, not the pinned identity: fresh install, persistence, daemon
restart, backup, isolated and replacement restore, explicit-migration upgrade, failure drills, and
the `postgres-image` step (uid 70, gosu absent, root refused with exit 64 through the default,
`docker-entrypoint.sh` and `docker-ensure-initdb.sh` entry points with the live data directory
byte-identical, previous official-pin data directory opens).

The local candidate (`build-beta-candidate.py`) likewise builds the image with the local builder; it is not
authoritative for the pinned identity, which only `beta_release.py postgres-identity --check` and
the protected publisher prove.

## Residual: gosu's bytes remain in an upstream layer

The removal is **runtime removal, not physical elimination.** Layer 2 of the image (upstream,
`sha256:63677b2e…`) still contains `usr/local/bin/gosu` (1,769,900 bytes, sha256
`52c8749d0142edd234e9d6bd5237dff2d81e71f43537e2f4f66f75dd4b243dd0`, the official gosu 1.19 release
binary). Layer 12 (Florabase) contains the whiteout `usr/local/bin/.wh.gosu`. No container started
from the image can see or execute the file.

Assessment:

- **Runtime:** none. The file is absent from every container filesystem; nothing in the image or
  the stack references it after the guard; the stack also drops all capabilities and sets
  `no-new-privileges`.
- **Extraction:** anyone who pulls the image can extract the binary from the layer tarball. They
  obtain only the unmodified, publicly released gosu 1.19 that Docker Hub already distributes in the
  same layer; it gives no access to Florabase data and would have to be run deliberately outside the
  image.
- **Scanners:** neither the pinned Trivy (filesystem scan) nor Grype in `all-layers` mode reported
  it. Other tools that inspect each layer independently may still report the 26 Go stdlib
  advisories against this image; such a report is accurate about the bytes and should be answered
  with this record, not suppressed.
- **Alternative not taken:** flattening the image would remove the bytes but discard the upstream
  layer identity that lets anyone verify the image against the official digest.

The image is therefore **not** "vulnerability-free": it passes the release gate and Grype at
HIGH/CRITICAL on its filesystem, retains unreachable upstream bytes, and carries Medium findings
without fixes.

## Image and vulnerability report (all three images, 7 November 2026)

| Image | Trivy gate (HIGH/CRITICAL, secrets) | Grype v0.121.1 |
| --- | --- | --- |
| Backend | 0 / 0 / 0 | **4 High in `sqlite-libs` 3.53.4-r0, no Alpine fix** (CVE-2026-119373, -119374, -119379, -119586); 12 Medium, 2 Low. The zlib Critical is fixed by the new `zlib=1.4-r0` pin |
| Frontend | 0 / 0 / 0 | 0 Critical / 0 High; 3 Medium (busybox) |
| PostgreSQL (derived) | 0 / 0 / 0 | 0 Critical / 0 High; 3 Medium (busybox) |

SQLite applicability: -119586 concerns the `sqlite3` shell's `.recover`, which `sqlite-libs` does
not contain; -119373/-119374 need FTS5 and -119379 the session extension, neither of which Florabase
uses. Florabase opens SQLite only for its own optional WFO/WCVP reference indexes, read-only. They
are unfixed, and the release gate (Trivy) does not see them. Case-by-case triage and the reference
index hardening that closes the crafted-index path QA demonstrated:
[sqlite-reference-indexes.md](sqlite-reference-indexes.md). Reduced reports:
[`postgresql-image/second-scanner.json`](postgresql-image/second-scanner.json).

## Maintenance responsibility (new)

Florabase now owns a third published image. The owner of the release process must:

1. **Monitor upstream:** docker-library/postgres 18 updates (new `18.6-alpine*` rebuilds, 18.x
   minor releases), Alpine 3.24 security fixes for the packages listed in the release SBOM, gosu
   releases, and both scanners' findings on the published digest.
2. **Rebuild only deliberately:** when the base or a pinned package must change:
   - update `FROM`, the base-name/base-digest labels and `release/inputs.json` `postgresql.upstream`;
     bump `org.opencontainers.image.version` and `postgresql.version` to the next
     `18.6-alpine-florabase.N` (never reuse a tag);
   - run `python3 scripts/release-tools.py scripts/beta_release.py postgres-identity`, record the
     printed digests as the new pins, and confirm with `--check` from a second fresh run;
   - rerun the scans, `make test-beta-images`, `make test-beta-runtime` and the runtime smoke;
   - treat it as PostgreSQL maintenance under the BETA-RUNTIME-001 rule: a new PostgreSQL identity
     needs reviewed compatibility, a paired backup/restore rehearsal and operator approval; it never
     rides on an application release.
3. **Superseded pins:** the exact `zlib=1.4-r0` pin fails a *rebuild* once Alpine supersedes it.
   Application releases do not rebuild an already-published PostgreSQL version, so they are not
   blocked; the next PostgreSQL identity simply needs the current package version. The backend and
   frontend carry the same kind of exact pins and are rebuilt for every release, so a superseded pin
   there does block application releases until the pin is updated (fail closed, by design).
4. **Keep the record:** retain the build/scan/SBOM evidence and this document's digests for every
   published version; never delete or overwrite a published PostgreSQL version.

## Owner-facing implications

- Installations pull PostgreSQL from GHCR (`florabase-postgres`) instead of Docker Hub.
- The database still runs PostgreSQL 18.6 as 70:70 with the same data layout; a data directory
  written by the previously pinned official image opens unchanged.
- Starting the database container as root is no longer possible; it stops with an explicit message.
- Application upgrades never change the PostgreSQL image. A new `florabase-postgres` version is a
  separately announced database maintenance step with its own backup.
