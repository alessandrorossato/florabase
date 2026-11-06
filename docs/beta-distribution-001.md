# BETA-DISTRIBUTION-001 — installable beta distribution: implementation and QA handoff

Branch `feat/beta-distribution-001`, writer `claude-beta`, base `fec0398`, `origin/main` `da80dc6`
merged without rewriting. Status `in_progress`: independent infrastructure QA and the canonical
gate have not run; nothing was pushed, published, tagged or deployed.

## Decisions (operator, 6 November 2026)

- Keep the existing backend/frontend image pair plus PostgreSQL; no combined image and no parallel
  distribution mechanism. Extend `deploy/beta`, `florabasectl.py`, the manifest and GHCR workflow.
- Migrations stay explicit: nothing migrates on `up`, restart or image update.
- Version `0.1.0-beta.1`, tag `v0.1.0-beta.1`; no `latest` from a prerelease.

## Gap assessment against the brief

Already on main and reused unchanged: paired, digest-pinned, non-root, read-only images with health
checks and OCI labels; protected manual GHCR workflow with scans, SBOM/provenance, attestations and
new-prerelease-only publication; the image-only `deploy/beta` stack (loopback-only frontend, no
published database/backend, bind-backed volumes that never fall back to an empty database,
`dockhand.update=false`); the controller's init/install/owner bootstrap/acceptance, paired recovery
sets, isolated and replacement restore, restic export, journaled `promote` with explicit migration;
the single-owner bootstrap (no default credentials, password ≥ 12 characters, never an argument).

Gaps closed here:

| Gap | Change |
| --- | --- |
| Release assets did not carry the install files; installing needed the source archive | `publish-beta-images.py` attaches `compose.yaml`, `florabasectl.py`, `florabase.env.example` (byte-bound like every asset); RELEASE.md points to the guide and states no `latest` |
| Guard refusals were not actionable; invalid settings surfaced as "database revision unavailable (ValidationError)" | Guard validates settings first (field names and messages only, never values) and names the action for invalid configuration, mismatched image, unavailable database, empty, pending and newer/foreign schema |
| Acceptance did not prove the SPA shell or API routing | `http_acceptance` checks the shell, every referenced script (served as JavaScript) and a JSON 404 for an unknown API path, on every base URL |
| No reverse-proxy or failure-mode acceptance | Smoke drills: pending migration refused, missing secret, PostgreSQL stopped, HTTP origin, TLS nginx proxy with hostile `X-Forwarded-Host`/`Forwarded` |
| PostgreSQL 2 CRITICAL / 26 HIGH blocker | Pin moved to the upstream same-version rebuild; remaining gosu findings stay a blocker (below) |
| Frontend base newly flagged (3 HIGH, fixes available, no upstream rebuild) | Exact Alpine package pins in the runtime stage |
| No end-user guide | [installation.md](installation.md), linked from README and deployment.md |

## Changed files

- `deploy/beta/compose.yaml` (guard), `deploy/beta/florabasectl.py` (acceptance)
- `scripts/publish-beta-images.py`, `scripts/test-beta-images.py`, `scripts/test-beta-runtime.py`,
  `scripts/smoke-beta-runtime.py`
- `release/inputs.json` (PostgreSQL identity), `frontend/Dockerfile` (security-owned; runtime
  stage only)
- `docs/installation.md`, `docs/beta-distribution-001.md`, `docs/beta-distribution-001-evidence.json`,
  `docs/security/beta-distribution-001/`, `docs/beta-runtime-001.md`, `docs/deployment.md`,
  `README.md`, `docs/features.json`, `docs/progress.md`

No Makefile, CI workflow, shared verification script, backend application or migration change.
The merged main commit (#149) touched only verification-workflow files.

## Evidence

- `make test-beta-runtime`: 60 tests (Python 3.14.4, host Compose) and 48 (Python 3.8.20).
  New: `HttpAcceptance` (healthy shell, SPA fallback for `/api` refused, missing shell/asset
  refused) and guard contract strings, including no echo of submitted values.
- `make test-beta-images`: 26 tests (new: bundle attached before inventory and promotion, files
  exist, only the exact version tag).
- `make workflow-check`: Ruff, format, strict mypy, policy, both suites: pass.
- `scripts/check-features.py`: 138 features valid.
- Guard in the real production backend image (network none): unreachable database, HTTP origin
  and missing database URL each give the actionable message; a planted password never appears.
- `make smoke-beta-runtime` equivalent (`scripts/smoke-beta-runtime.py`) twice from clean commits:
  `872f076` (830.6 s) and `fd4fc76` / tree `372b97dd…` (841.4 s), 21/21 steps, zero owned
  residuals, host `florabase-prod` and the unrelated nested workload unchanged. Final evidence:
  [beta-distribution-001-evidence.json](beta-distribution-001-evidence.json). The tree after it
  differs only in `docs/` (reduced scan reports, docs) and main's verification-workflow files.
- PostgreSQL rebuild: data directory initialized by the old pin opened under the new image with
  its rows intact. All smoke backup/restore/upgrade drills ran on the new pin.
- Scans with the pinned Trivy through `scan_images`: [security evidence](security/beta-distribution-001/README.md).

Acceptance-test mapping (brief items 1–10): 1 bundle-only controller, registry pull by digest
(`preflight`, `install`); 2 `install`/`acceptance` health; 3 `bootstrap-owner` + owner login;
4 seeded records, shell/assets/API 404, owner session; 5 uploads, shared/unlinked/saved originals
and SHA-256 identity across recreation and daemon restart; 6 `persistence`; 7 `promote-compatible`
with an explicit migration, plus failed/interrupted upgrades; 8 `backup`, `restore-isolated`,
`offhost-export`, `restore-replace`; 9 `https-reverse-proxy`; 10 `failure-modes`,
`pending-migration-refused`, `schema-guard`, `refuse-ahead-schema`.

## Security findings and blockers

1. **Blocking: PostgreSQL gosu.** `postgres:18.6-alpine@sha256:123b1799…` still reports 1 CRITICAL /
   25 HIGH, all Go 1.24.6 stdlib in `/usr/local/bin/gosu`. The stack never executes gosu (non-root
   70:70, no capabilities), which is applicability evidence only; the fail-closed gate blocks
   publication. Operator choice needed: wait for an upstream rebuild with a fixed Go toolchain,
   publish a Florabase-built PostgreSQL image without gosu (a new supply-chain artifact), or accept
   narrowly scoped expiring VEX (also needs a reviewed VEX input path in the gate).
2. **Approval needed: PostgreSQL pin change.** BETA-RUNTIME-001 requires operator approval for a
   rebuilt digest. Compatibility and paired backup/restore rehearsals are recorded above; no
   installation uses the old pin.
3. **Frontend Alpine pins** go stale when Alpine supersedes them (the build then fails closed);
   remove them once the pinned base carries the fixes.
4. Observation: `/api/v1/ready` has no database connect timeout; with PostgreSQL stopped and the
   name unresolvable it may answer only after the client gives up. Failure is still controlled.
5. Limitations: no owner password reset; HTTPS origin fixed at `init`; amd64 only (arm64 neither
   built nor tested); Dockhand workflow documented but not recorded on a real Dockhand, so no
   screenshots; real-host items in [beta-runtime-001.md](beta-runtime-001.md#outstanding-operator-evidence)
   remain.

## Mandatory for v0.1.0-beta.1 versus later

Mandatory and open: blocker 1, approval 2, independent QA, canonical FULL, protected publication
and a clean registry-pull smoke of the published pair, then real-host acceptance (BETA-ACCEPTANCE-001).
Later: owner password reset/change, guided upgrade automation, arm64 images, configurable origin
and map tiles, readiness connect timeout, PostgreSQL major-upgrade tooling.
