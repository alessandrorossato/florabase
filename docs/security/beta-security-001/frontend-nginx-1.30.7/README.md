# BETA-SECURITY-001 — frontend nginx 1.30.7 base refresh

Measured 2026-11-20. Branch `fix/beta-security-001-frontend-nginx`, writer
`claude-beta-security-001-nginx` (claim `151629d90084`), base `main`
`fdc75e83fa8818cab791ed82cbba65f4f97db7ae` (tree `e179765b6ce213546437c0fe7c0969d8477e24f2`).
This is pre-commit dirty-source evidence, not publication, host or gate approval. No finding is
suppressed and no VEX is used.

## Defect

The [PR #197 hosted rehearsal](https://github.com/alessandrorossato/florabase/actions/runs/44765663940)
(head `af8935146e5aabcdfb15de6761e1e65053c0321f`) stopped at `SCAN/SMOKE: SECURITY GATE BLOCKED:
frontend`. Its artifact `beta-release-rehearsal-44765663940-1` has digest
`sha256:41d526bc99e763333cde05fcfa25bff59de37a86a0a0d8e7fd5402070de22aee`. Its frontend report
(SHA-256 `cb0d4e0d…346ff6`, summarized in [summary.json](summary.json)) lists six nginx
`1.30.6-r1` findings fixed in `1.30.7`: CRITICAL CVE-2026-113425, CVE-2026-121810, CVE-2026-123007,
CVE-2026-123633 and HIGH CVE-2026-118899, CVE-2026-123634. Backend and PostgreSQL had none.

The cause is the base, not the PR. `frontend/Dockerfile` is byte-identical on `main` and the PR
(blob `904c375c`). The pinned `nginxinc/nginx-unprivileged:stable-alpine-slim@sha256:5d8bb943…`
(nginx 1.30.6, built 2026-10-19) predates the nginx 1.30.7 security release of 18 November 2026.
The `main` rehearsal passed at 13:19Z that day, before the advisories reached the scanner database
at about 16:17Z. The scanner image is pinned, but its vulnerability database is not.

Applicability (informational, nothing is suppressed): `frontend/nginx.conf` listens on plain HTTP
8080 with no `http2`, QUIC, TLS or `mail` block. The resolver use-after-free CVE-2026-123634 is
plausibly reachable through `resolver 127.0.0.11` and the variable `proxy_pass` for `/api/`. The
other five need disabled features.

## Change

Upstream moved current Docker Hub releases from `nginxinc/` to `nginx/nginx-unprivileged`
([upstream README](https://github.com/nginx/docker-nginx-unprivileged#readme)). `nginxinc/` received
no 1.30.7 build. The operator approved the namespace change on 2026-11-20. `frontend/Dockerfile` and
`release/inputs.json` (`base_images.nginx`, which `scripts/beta_release.py` requires to match) now
pin:

`nginx/nginx-unprivileged:1.30.7-alpine3.24-slim@sha256:8432c57ac86f178741af2b89948bd9087cb9df1c415bc1ab4d23735c4f0e3e61`

- linux/amd64 manifest `sha256:64a2a533a92f64b868d5f6d262dbc8c9bdc0302154f631389170ac409761047a`.
  Created 2026-11-18T16:40Z with `NGINX_VERSION=1.30.7`, user 101, `8080/tcp`, `SIGQUIT` and
  `/docker-entrypoint.sh`.
- Revision label `95b8382efe669a2876f6736e9479667a1b509cee` is the upstream "Regenerated
  dockerfiles" commit. Signatures and attestations were not verified.
- The existing `apk add musl=1.2.6-r3 musl-utils=1.2.6-r3 zlib=1.4-r0` line is kept. The new base
  already carries musl `1.2.6-r3`, but its zlib `1.3.2-r1` is older than the pinned `1.4-r0`.

Rejected: mainline 1.31.7 (nginx.org lists it vulnerable until 1.31.9), an Alpine `nginx` overlay
(a different build and layout), and any exception (a fix exists).

## Measured result

`scripts/build-beta-candidate.py --security-dir` on the dirty tree built both production targets,
passed artifact-only smoke (migration, owner login, media, health) and cleaned up every resource.
It also scanned all three images with the pinned Trivy 0.69.3, using vulnerability and secret
scanning and `/dev/null` as the ignore file:

| Image | OS | HIGH / CRITICAL / secrets |
| --- | --- | --- |
| Frontend (report SHA-256 `54311164…823a4b`) | Alpine 3.24.4 | 0 / 0 / 0 |
| Backend | Alpine 3.24.3 | 0 / 0 / 0 |
| PostgreSQL 18.6-alpine-florabase.2 (pinned, unchanged) | Alpine 3.24.4 | 0 / 0 / 0 |

The frontend inventory records `nginx=1.30.7-r1`, `musl=1.2.6-r3`, `musl-utils=1.2.6-r3` and
`zlib=1.4-r0`. The local frontend identity is index `sha256:05f6ddef…bcf0db`, platform
`sha256:8c926eeb…0f637c` and config `sha256:9175c478…c18b34`. These are local dirty-tree digests,
not release identities.

[summary.json](summary.json) records both reports' hashes, identities, findings and key package
versions. Raw reports are not committed: their package metadata contains maintainer e-mail
addresses, which the repository disclosure gate rejects without exemption. The before report
remains in the archived CI artifact. The authoritative after report will be the hosted rehearsal
on the exact fix commit.

## Open

- Trivy reports no nginx finding on mainline 1.31.7, although nginx.org lists it as vulnerable.
  A clean scan does not prove that nginx is patched. Cross-checking the nginx version in the gate
  is a proposed follow-up and is not part of this change.
- The hosted rehearsal on the exact fix commit, independent QA, canonical FULL and operator
  delivery are pending. After merge, Batch 07 (`ci/batch-07`) must be re-integrated on the new
  `main`, and its FULL, candidate review and rehearsal redone.
