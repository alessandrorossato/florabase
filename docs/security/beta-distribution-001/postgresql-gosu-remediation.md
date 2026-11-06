# PostgreSQL gosu findings: remediation evaluation (6 November 2026)

## Decision 1: approved development pin (recorded)

The operator approved this pin for continued beta development and isolated verification only. It
does not authorize publication, bypass the vulnerability gate or touch production data.

| Field | Value |
| --- | --- |
| Reference | `docker.io/library/postgres:18.6-alpine@sha256:123b17998ccaf47e53b502e8c6a1e79afd8f579c6f3eec83c563da026f957395` |
| linux/amd64 manifest | `sha256:300ebd02c6d4de9ee27ad7f6855d5d21b4d3a4a5117767c1197d284c635d9736` |
| Configuration | `sha256:38b9ffe2d4c13d7c445b66306be6763dfa6f503689ea0c5b9f84544ccf3ca8e4` |
| Provenance | Docker Official Image, `org.opencontainers.image.source` `https://github.com/docker-library/postgres.git#e00e1bd34ec5c8a8e7ad89b273b3d42efaf6d5bc:18/alpine3.24`, created 2026-11-05T19:06:10Z, version `18.6-alpine3.24`, Alpine 3.24.4 |
| Replaces | `sha256:10a5c69a…` (same source revision, built 2026-10-21) |
| Compatibility | Data directory initialized by the previous pin opens with its rows; PostgreSQL 18.6 on both |
| Recovery tests | Two full disposable runtime smokes on this pin: backup, tamper detection, isolated restore, restic export/import, replacement restore, compatible/failed/interrupted upgrades ([evidence](../../beta-distribution-001-evidence.json)) |
| Scan | 1 CRITICAL / 25 HIGH, all `stdlib` v1.24.6 in `/usr/local/bin/gosu`; 0 secrets ([summary](postgresql-18.6-rebuild/summary.json)) |

## Option 1: a newer official PostgreSQL or gosu artifact

Not available.

- Every PostgreSQL 18 Dockerfile in `docker-library/postgres` `master` (`alpine3.24`, `trixie`,
  `bookworm`) sets `GOSU_VERSION 1.19`, and the newest upstream commit touching 18 is the
  18.6 update (`e00e1bd`, 2026-08-13). `18-alpine`, `18.6-alpine` and `18.6-alpine3.24` all
  resolve to the pinned index; there is no `18.7-alpine`.
- gosu `1.20` (2026-10-25) exists, but its release notes state it is **built on Go 1.24.6**, the
  same toolchain the findings name. Its only security change is GO-2026-6686 in a dependency.
  Swapping gosu therefore removes none of the 26 findings.
- The Debian variants carry the same gosu, so changing distribution does not help either.

## Option 2: a derived image without gosu

Prototype ([Dockerfile](postgresql-derived-prototype/Dockerfile.prototype)):

```dockerfile
FROM docker.io/library/postgres:18.6-alpine@sha256:123b17998ccaf47e53b502e8c6a1e79afd8f579c6f3eec83c563da026f957395
RUN rm /usr/local/bin/gosu
USER 70:70
```

Entrypoint, command, stop signal, environment and every other file are the upstream ones. Only
`docker-entrypoint.sh` references gosu, and only on its root branch (`exec gosu postgres …`).

| Check | Result |
| --- | --- |
| Reproducibility | Two `--no-cache` BuildKit 0.34.2 builds with `SOURCE_DATE_EPOCH=1762387200` and `rewrite-timestamp=true`: identical manifest `sha256:b242b556fe8be30beaa5b19ebe2e1f56378c22c4460081b388675980fbe4e369` |
| Scan (pinned Trivy 0.69.3, same flags and empty ignore file as the gate) | **0 CRITICAL / 0 HIGH / 0 secrets**, exit 0 ([reduced report](postgresql-derived-prototype/postgresql-security.json)) |
| Fresh init as 70:70, read-only root, tmpfs, `cap_drop ALL`, `no-new-privileges`, on a 70:70 0700 bind directory (the stack's shape) | Initializes, serves, `current_user` florabase; gosu absent |
| Restart and recreation on the same directory | Data intact |
| `pg_dump` in the container (backup path) and `pg_restore --list` via `--entrypoint` (`validate_artifacts` path) | Work; dump lists table data |
| `pg_restore` into a fresh database (replacement-restore path) | Rows restored |
| Data directory created by the official `10a5c69a…` image | Opens with its rows |
| Default invocation without `--user` | Runs as uid 70 and initializes |
| **Unsupported root invocation on existing data** | Exit 127 `exec: gosu: not found` before `initdb` or server start; ownership, modes, sizes and file list byte-identical before/after |
| Unsupported root invocation on an empty directory | Exit 127; leaves only the empty `18/docker` directory (70:0 0700) the upstream entrypoint creates; no database, and a later correct start initializes normally |

Every supported Florabase path (stack `user: "70:70"`, `compose exec db` for dump/restore/psql,
`--entrypoint pg_restore` for validation, isolated and replacement restore projects) never reaches
the root branch. A mistaken root start fails loudly instead of running PostgreSQL as root or
corrupting data.

**Residual:** `rm` in a new layer is a whiteout. The gosu bytes still exist in the unchanged
upstream layer that the image references. They are unreachable in any container filesystem, and
the scanner correctly evaluates the merged filesystem, but they are distributed. Removing them would
mean flattening the image, which discards upstream layer identity and deduplication. The prototype
keeps the upstream layers, so provenance stays checkable against the official digest.

## Option 3: maintenance and supply-chain comparison

| | Official image (current) | Derived image |
| --- | --- | --- |
| Gate | Blocks (26 findings) until upstream moves to a fixed Go toolchain; no date, and gosu's maintainer does not rebuild for unreachable stdlib advisories | Passes today |
| What Florabase publishes | Nothing; users pull from Docker Hub | A third GHCR package, `florabase-postgres`, with attestation, SBOM, scan and retention like the pair |
| Rebuild trigger | None | Every upstream PostgreSQL rebuild or security update: bump the base digest, rebuild, scan, smoke. Each is a PostgreSQL identity change under the existing separate-maintenance rule |
| Release identity | Unchanged by application releases | Reproducible from the pinned base and a fixed epoch, so application releases can rebuild byte-identical platform manifests and assert the expected digest, preserving PostgreSQL identity |
| Licenses | Docker Hub's redistribution | Florabase redistributes Alpine/PostgreSQL binaries; source obligations as already handled for the application images |
| Architectures | Upstream multi-arch | linux/amd64 only, matching the pair |
| Code changes to adopt | — | `release/inputs.json` (base + expected digest), publish script and protected workflow (build, scan, attest, promote), manifest PostgreSQL repository, controller manifest checks, runtime smoke, docs; no runtime or controller behavior change |

## Option 4: VEX

Not proposed. The derived image removes the component instead of asserting non-applicability. A VEX
path would remain a separate security review and operator approval.

## Recommendation

Adopt option 2. It is the only remediation that passes the unchanged fail-closed gate now, it
preserves upstream provenance and PostgreSQL 18.6 data compatibility, and every supported
initialization, backup, restore and migration path is shown working without gosu. The cost is owning
a third published image and its rebuild cadence. Integrating it changes the protected publication
workflow and adds a new GHCR package, so it awaits explicit operator approval. Until then the release
remains BETA-BLOCKED.
