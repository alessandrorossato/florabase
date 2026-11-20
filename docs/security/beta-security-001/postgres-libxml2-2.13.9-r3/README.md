# BETA-SECURITY-001 — PostgreSQL libxml2 2.13.9-r3 (`18.6-alpine-florabase.3`)

Measured 2026-11-20. Branch `fix/beta-security-001-postgres-libxml2`, writer
`claude-beta-security-001-pg` (claim `75bb1b546100`), base `main`
`a625e8cab9a269bbf70efee65c727291c4a70e9c`. The operator authorized this PostgreSQL maintenance
on 2026-11-20. This is pre-commit evidence, not publication, host or gate approval. No finding is
suppressed and no VEX is used.

## Defect

The [PR #200 hosted rehearsal](https://github.com/alessandrorossato/florabase/actions/runs/44811753173)
on head `96ec8df` stopped at `SCAN/SMOKE: SECURITY GATE BLOCKED: postgresql`. The pinned
`18.6-alpine-florabase.2` identity had one HIGH finding, CVE-2026-86144, in `libxml2`
`2.13.9-r2`, fixed in `2.13.9-r3`. The backend and frontend images had none. The same identity
passed hosted rehearsals earlier that day, so the cause is the unpinned scanner database, not a
source change. [summary.json](summary.json) records the before report hash and finding.

Applicability (informational): the application issues no SQL XML functions or `xml` columns
(no matches in `backend/src` or `backend/alembic`). libxml2 is reachable only through SQL XML
features executed by an authenticated database role.

## Change

- `postgres/Dockerfile` adds `libxml2=2.13.9-r3` to the existing exact Alpine pin line, next to
  `zlib`, `krb5-libs` and `libxslt`, and sets the version label to `18.6-alpine-florabase.3`.
  The upstream base, gosu removal, user 70:70 and entrypoint guards are unchanged.
- `release/inputs.json` pins version `18.6-alpine-florabase.3`, index
  `sha256:2a50cabff7df4e5f108065b51585c2c202b92805f0b842dd3522aaf7e9158115` and linux/amd64
  manifest `sha256:d5d9db7f574c22797ef3be56f61b893dfa4b308c1f25b4d33dd71d312c56c053`.
  `upstream` and `source_date_epoch` are unchanged.

Three independent `scripts/beta_release.py postgres-identity` builds with the pinned BuildKit
produced these digests. The third ran with `--check` and printed `POSTGRES_IDENTITY_REPRODUCED`.
GHCR is not touched: neither the .2 nor the .3 identity is published.

Rejected: refreshing the upstream `postgres:18.6-alpine` base (a newer digest from
2026-11-05 exists), which would replace every upstream identity field for a one-package fix,
and any exception.

## Measured result

`make test-beta-images` passed 78 release and four tool-lock tests. `make test-beta-runtime`
passed 63 tests and 51 Python 3.8 controller tests. `scripts/build-beta-candidate.py
--security-dir` passed artifact-only smoke and cleanup. The pinned Trivy 0.69.3 found zero HIGH,
CRITICAL and secret findings in all three images. The PostgreSQL inventory records `libxml2`
`2.13.9-r3`, `libxslt` `1.1.43-r4`, `zlib` `1.4-r0` and `krb5-libs` `1.22.3-r0`.

The local candidate path builds PostgreSQL with a different index digest
(`sha256:08b756f1…`) than the deterministic pinned identity, from the same Dockerfile. The
authoritative scan of the pinned `.3` bytes is the hosted rehearsal on the exact fix commit.

## Open

Existing `.2` installations would need separately approved PostgreSQL maintenance with a paired
backup and restore before switching digests; none is known. The scanner vulnerability database
remains unpinned, so new advisories can block any SHA. Independent QA, canonical FULL, the
hosted rehearsal and operator delivery are pending.
