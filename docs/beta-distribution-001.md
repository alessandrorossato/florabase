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

1. **Resolved (7 November 2026): PostgreSQL gosu.** Superseded by the Florabase PostgreSQL image
   (see the update below and
   [postgresql-image.md](security/beta-distribution-001/postgresql-image.md)). The official
   `postgres:18.6-alpine@sha256:123b1799…` reports 1 CRITICAL / 25 HIGH in gosu's Go 1.24.6 stdlib;
   the derived image's filesystem has no gosu, while its original bytes remain in an upstream layer.
2. **Approved (development and isolated verification only): PostgreSQL pin change** to
   `sha256:123b17998ccaf47e53b502e8c6a1e79afd8f579c6f3eec83c563da026f957395`; provenance,
   compatibility and recovery evidence recorded in the remediation evaluation.
3. **Frontend Alpine pins** go stale when Alpine supersedes them (the build then fails closed);
   remove them once the pinned base carries the fixes.
4. Fixed (`985437f`): readiness hung without an answer for 60 s against a paused database; it now
   uses an unpooled engine with `connect_timeout=3` and `statement_timeout=2000` and answers 503 in
   3.0 s. Stopped database: 503 in about 5 s (resolver timeout), unchanged.
5. Limitations: no owner password reset; HTTPS origin fixed at `init`; amd64 only (arm64 neither
   built nor tested); Dockhand workflow documented but not recorded on a real Dockhand, so no
   screenshots; real-host items in [beta-runtime-001.md](beta-runtime-001.md#outstanding-operator-evidence)
   remain.

## Mandatory for v0.1.0-beta.1 versus later

Mandatory and open: delta QA of the QA corrections, canonical FULL, the operator's decision on the
second-scanner sqlite-libs findings, protected publication with a clean registry-pull smoke of the
published images, then real-host acceptance (BETA-ACCEPTANCE-001).
Later: owner password reset/change, guided upgrade automation, arm64 images, configurable origin
and map tiles, request-path database timeouts, PostgreSQL major-upgrade tooling.

## Update, 7 November 2026: Florabase PostgreSQL image integrated

The operator approved integrating the gosu-free derived image for implementation and verification
(not publication). Full record: [postgresql-image.md](security/beta-distribution-001/postgresql-image.md).

- `postgres/` (Dockerfile, root guard, license) builds
  `ghcr.io/alessandrorossato/florabase-postgres:18.6-alpine-florabase.1` from the approved base
  `sha256:123b1799…`, removes gosu, pins zlib 1.4-r0, sets `USER 70:70`. Pinned and reproduced:
  index `sha256:e5855f0cc6118b2b6dcd8c36d933e9b350d04e1757dfacb26737de0298fb1cbb`, platform
  `sha256:e625e5878a90b4b0ae60824dd41b7960c56c033a07ceabae5852d573d2259a50`.
- Integrated into `release/inputs.json`, manifest schema v2, `beta_release.py` (validation,
  deterministic build, `postgres-identity [--check]`, SBOM, scan inventory), the protected publisher
  and workflow (one attestation step), the controller, the artifact smoke, the local candidate and
  the runtime smoke. Backend also pins zlib 1.4-r0.
- Superseded findings above: blocker 1 (gosu) is resolved at the filesystem level, with gosu's
  original bytes remaining in upstream layer 2 (documented, not physically eliminated).
- New finding: Grype reports 4 High in the backend's `sqlite-libs` 3.53.4-r0 with no Alpine fix
  that the release gate's Trivy does not report; assessed not reachable through Florabase code.
  Whether a second scanner should gate releases is an open operator decision.

Checks on `0d074e7` / this tree:
- `make workflow-check`: pass (release tests 30, runtime 60 + 48 on Python 3.8.20, strict mypy, Ruff).
- `beta_release.py postgres-identity --check`: reproduced the pins from fresh builders (repeatedly).
- Registry-level verification against a disposable registry: identity equal to the pins; release
  gate PASSED on the pulled bytes; Grype squashed and all-layers 0 Critical / 0 High; SBOM 54
  components without gosu.
- `build-beta-candidate.py --security-dir`: `LOCAL_BETA_CANDIDATE_PASSED`, Trivy gate passed for
  backend, frontend and PostgreSQL.
- Runtime smoke 22/22 from clean `0d074e7` in 858.2 s, zero owned residuals.
- Not run: actionlint (downloading the binary was declined), independent QA, canonical FULL,
  protected publication against GHCR.
