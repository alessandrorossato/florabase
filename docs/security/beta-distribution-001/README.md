# BETA-DISTRIBUTION-001 security evidence (6 November 2026)

Scanner: the pinned `aquasec/trivy:0.69.3` from `release/inputs.json`, run through
`scripts/beta_release.py::scan_images` (HIGH/CRITICAL vulnerabilities and secrets, no ignore file,
fail closed). The committed `*-security.json` files are reduced reports: every finding, secret
result and image identity, plus the SHA-256 and size of the raw Trivy JSON they came from. The raw
reports embed public package-maintainer addresses, which the repository disclosure check refuses,
so they stayed outside Git; re-running the same scan reproduces them.

| Image | Before | After |
| --- | --- | --- |
| Backend runtime (current tree) | 0 CRITICAL / 0 HIGH / 0 secrets | unchanged |
| Frontend runtime (current tree) | 0 / 3 HIGH: musl, musl-utils 1.2.6-r2 (CVE-2026-107891), zlib 1.3.2-r0 (CVE-2026-85091) | 0 / 0 / 0 after pinning musl/musl-utils 1.2.6-r3 and zlib 1.4-r0 in the runtime stage |
| PostgreSQL `18.6-alpine` | `10a5c69a…`: 2 CRITICAL / 26 HIGH (BETA-SECURITY-001) | upstream same-version rebuild `123b1799…` (amd64 `300ebd02…`): 1 CRITICAL / 25 HIGH, all Go 1.24.6 stdlib inside `/usr/local/bin/gosu`; brotli and libcurl findings resolved |

- `application/before`, `application/after`: frontend/backend reports and identities. The images
  are local builds of this branch, not published artifacts; publication re-scans the exact pushed
  bytes.
- `postgresql-18.6-rebuild/`: identity, descriptors, raw report and `summary.json` with advisories,
  gosu applicability and the data-directory compatibility check.

**Release blocker.** The fail-closed gate still blocks publication on the 26 gosu findings. gosu
is not executed by this stack (the entrypoint calls it only as root; the stack runs PostgreSQL as
70:70 with all capabilities dropped and no-new-privileges), but that is applicability evidence, not
a scanner pass. Resolving it needs an operator decision: wait for an upstream image built with a
fixed Go toolchain, publish a Florabase-built PostgreSQL image without gosu, or accept narrowly
scoped expiring VEX statements, which also need a reviewed scanner VEX input path.
