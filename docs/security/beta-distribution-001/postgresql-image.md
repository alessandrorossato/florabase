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
| `USER 70:70` and the `florabase-postgres-entrypoint` guard | Without gosu the upstream root branch cannot work; the guard refuses root before the upstream entrypoint creates, chowns or initializes anything (exit 64) |

Inputs ([`postgres/`](../../../postgres/)): the base
`docker.io/library/postgres:18.6-alpine@sha256:123b17998ccaf47e53b502e8c6a1e79afd8f579c6f3eec83c563da026f957395`
(amd64 `sha256:300ebd02c6d4de9ee27ad7f6855d5d21b4d3a4a5117767c1197d284c635d9736`, docker-library
`e00e1bd`), the Dockerfile, the four-line guard and the repository license. Labels record the base
name and digest, the image version and source; there is deliberately no per-commit label.

## Release contract

- **Pinned by content.** `release/inputs.json` `postgresql` holds the expected index
  `sha256:e5855f0cc6118b2b6dcd8c36d933e9b350d04e1757dfacb26737de0298fb1cbb` and platform manifest
  `sha256:e625e5878a90b4b0ae60824dd41b7960c56c033a07ceabae5852d573d2259a50`, the
  `source_date_epoch` (1762387200) and the exact `upstream` identity. `beta_release.py check`
  refuses a Dockerfile whose base, base-digest label or version differs, or that uses `ARG`.
- **Deterministic build.** The pinned BuildKit builds with `--no-cache`, `rewrite-timestamp`, the
  fixed epoch and no in-index provenance/SBOM (those embed build times); `/var/log/apk.log` is
  removed because it records install times. `imagetools create` then wraps the single amd64 manifest
  in a bare index. Fresh builders reproduced both digests on every run.
- **Same release manifest, same identity every release.** Manifest schema v2 records the derived
  image and its upstream base in `postgresql`. Because the build is reproducible, every application
  release references the identical PostgreSQL index, so the controller's rule that `promote` never
  changes PostgreSQL still holds, and the pair plus PostgreSQL are bound to one manifest by
  immutable digests.
- **Protected publication only.** The existing manual, environment-approved workflow builds it
  first; `require_pinned_postgres` refuses any build that does not reproduce the pins. It is pushed
  as a candidate, scanned by the unchanged fail-closed gate, SBOM'd (pinned Trivy CycloneDX, release
  asset `postgresql-sbom.cdx.json`), smoked with the pair, attested with
  `actions/attest-build-provenance` and only then tagged. An existing `18.6-alpine-florabase.1` tag
  is accepted only if it already points at the pinned index.
- **Consumers verify it.** The controller requires the Florabase repository, the recorded upstream
  base, user `70:70`, the guard entrypoint and the base-digest label on the pulled image, and checks
  the platform digest; the artifact smoke additionally checks gosu absence and root refusal.

## Verification evidence

[`postgresql-image/registry-verification.json`](postgresql-image/registry-verification.json):
built with the pinned BuildKit into a disposable loopback registry, pulled by the pinned index
digest, then:

| Check | Result |
| --- | --- |
| Registry identity | index `e5855f0c…` holding exactly the amd64 manifest `e625e587…`; equal to the pins |
| Release gate (pinned Trivy 0.69.3, vuln+secret, HIGH/CRITICAL, no ignore file) on the pulled bytes | PASSED: 0 / 0, 0 secrets; Alpine 3.24 package inventory present; no gosu target |
| Grype v0.121.1, squashed filesystem | 0 Critical / 0 High; 3 Medium (busybox CVE-2025-60876, no fix) |
| Grype v0.121.1, `--scope all-layers` | identical: 3 Medium, no gosu or Go stdlib findings |
| SBOM | 54 components, none is gosu |
| Root start | exit 64 with an explicit message before any directory or data change |
| Runtime smoke 22/22 from clean `0d074e7` (Engine 24.0.2, Compose 2.20.1): fresh install, persistence, daemon restart, backup, isolated and replacement restore, explicit-migration upgrade, failure drills | pass; `postgres-image` step: uid 70, gosu absent, root exit 64 with the live data directory byte-identical, previous official-pin data directory opens ([evidence](../../beta-distribution-001-evidence.json)) |

The local candidate (`build-beta-candidate.py`) builds the image with the local builder; it is not
authoritative for the pinned identity, which only `beta_release.py postgres-identity --check` and
the protected publisher prove.

## Residual: gosu's bytes remain in an upstream layer

The removal is **runtime removal, not physical elimination.** Layer 2 of the image (upstream,
`sha256:63677b2e…`) still contains `usr/local/bin/gosu` (1,769,900 bytes, sha256
`52c8749d0142edd234e9d6bd5237dff2d81e71f43537e2f4f66f75dd4b243dd0`, the official gosu 1.19 release
binary). Layer 11 (Florabase) contains the whiteout `usr/local/bin/.wh.gosu`. No container started
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
uses. Florabase opens SQLite only for its own optional WFO/WCVP reference indexes, read-only, which
the operator provisions with SHA-256 verification. They are not reachable through Florabase's code
paths, but they are unfixed, and the release gate (Trivy) does not see them. Reduced reports:
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
3. **Expect forced rebuilds:** the exact `zlib=1.4-r0` pin fails the build once Alpine supersedes
   it. That is intentional (fail closed) but makes the next release a PostgreSQL identity change.
4. **Keep the record:** retain the build/scan/SBOM evidence and this document's digests for every
   published version; never delete or overwrite a published PostgreSQL version.

## Owner-facing implications

- Installations pull PostgreSQL from GHCR (`florabase-postgres`) instead of Docker Hub.
- The database still runs PostgreSQL 18.6 as 70:70 with the same data layout; a data directory
  written by the previously pinned official image opens unchanged.
- Starting the database container as root is no longer possible; it stops with an explicit message.
- Application upgrades never change the PostgreSQL image. A new `florabase-postgres` version is a
  separately announced database maintenance step with its own backup.
