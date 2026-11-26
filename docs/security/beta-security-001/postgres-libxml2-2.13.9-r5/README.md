# BETA-SECURITY-001 — PostgreSQL libxml2 2.13.9-r5 (`18.6-alpine-florabase.6`)

Measured 2026-11-26. Branch `fix/postgres-libxml2-r5`, writer `claude-pg-pin` (claim
`c8b870d1ccb5`), base `main` `08ff2f92d6f9b5496c04ed3b0ae5828451e35269`. This is pre-commit
evidence, not publication, host or gate approval. No finding is suppressed and no VEX is used.

## Defect

The PR #228 (batch 14) hosted `rehearse` check failed building `postgres/Dockerfile` at the exact
Alpine pin line: `unable to select packages: libxml2-2.13.9-r2 breaks world[libxml2=2.13.9-r3]`.
`apk policy` in the unchanged pinned base (`postgres:18.6-alpine@sha256:123b1799…`, Alpine 3.24.4)
now offers `libxml2` `2.13.9-r5` only; `r3` was withdrawn from `v3.24/main`. `zlib` `1.4-r0`,
`krb5-libs` `1.22.3-r0` and `libxslt` `1.1.43-r4` are still offered. Exact pins fail the build when
superseded by design, so the cause is the repository change, not a source change.

## Change

- `postgres/Dockerfile` pins `libxml2=2.13.9-r5` on the existing exact Alpine pin line and sets
  the version label to `18.6-alpine-florabase.6`. Upstream base, other pins, gosu removal, user
  70:70, health check and entrypoint guards are unchanged.
- `release/inputs.json` pins version `18.6-alpine-florabase.6`, index
  `sha256:fa3d79573aca9e4558876fd82337d6892ebaa8ce3219444c793f481ddf88de9b` and linux/amd64
  manifest `sha256:b61292b44712e5d8c695486d62c17cf58af99939535721d7be9e710fc65f1a3d`.
  `upstream` and `source_date_epoch` are unchanged.

Two independent `scripts/beta_release.py postgres-identity` builds with the pinned BuildKit
(`--no-cache`) produced these digests; the second ran with `--check`. GHCR is not touched.

Rejected: refreshing the upstream base for a one-package pin, and unpinning `libxml2`.

## Open

The scanner vulnerability database and the Alpine repository remain moving inputs, so a later
package withdrawal or advisory can block any SHA again. The authoritative scan of the pinned `.6`
bytes is the hosted rehearsal on the exact fix commit. Independent QA, canonical FULL and operator
delivery are pending.
