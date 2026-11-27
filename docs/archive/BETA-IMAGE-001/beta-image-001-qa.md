Historical initial handoff; superseded for current decisions by [QA corrections](beta-image-001-qa-corrections.md). Original scan evidence is preserved.

> **Superseded in part (RELEASE-PLATFORM-DECOUPLE):** publication no longer requires approval of a specific host. `release/platform.json` records the supported linux/amd64 platform; host capacity, Docker/Compose, HTTPS, persistence and recovery acceptance are separate post-publication deployment gates (BETA-RUNTIME-001). See [BETA-IMAGE-001](beta-image-001.md#platform-policy-and-publication-prerequisite). The text below is preserved as historical record and is not rewritten.

# BETA-IMAGE-001 — independent QA handoff

Candidate prepared on `feat/beta-image-001` from verified cached main
`f637539e5f3cad80695a875029a97287a37e46c0`, writer `codex-beta-image-001`.
This is a local implementation checkpoint, **not READY_FOR_DELIVERY, a verified feature, publication
approval or a production-qualified image pair**. Feature registry remains `in_progress` because
publication, host screening, security acceptance, independent QA and canonical FULL are outstanding.
The reviewed local commit carries the final implementation identity. No push, PR, merge,
feature-finish, persistent deployment or TEST-DATA-002 mutation occurred.

## Implementation boundary

- Production Dockerfile targets, immutable upstream/tool pins, production dependency hashes,
  non-root users, embedded healthchecks, minimal runtime contents, coherent beta versions/OCI labels,
  frontend release surface, Docker DNS re-resolution, licenses and bundled dependency notices.
- Protected manual-main workflow, exact source/tag/check identities, environment SHA approval,
  run-scoped candidate pushes, provenance/SBOM, scans, clean digest pulls and native image-only smoke,
  version promotion of the same tested indexes, manifest attestation/source retention/prerelease.
- Manifest v1 schema and validator; explicit PostgreSQL index/platform identities. Existing feature
  delivery/CI protections remain unchanged. No persistent runtime Compose, deployment, data import,
  upgrade automation or backup controller was added.
- [Configuration, operator prerequisites and manifest contract](beta-image-001.md).

## Checks actually executed on 3 November 2026

| Check | Result and limits |
| --- | --- |
| Initial `make check AGENT_ID=codex-beta-image-001` | Backend 985 passed, 2 skipped, 90.06% coverage; frontend 1144 passed / 1 failed. Failure: Sowing historical `?tab=propagation` → Lineage URL assertion at line 1375. Broad run is **not PASS**. Static stages preceding tests passed; API stage was not reached in this command. |
| Single failing Sowing test, then full Sowing owner suite | 1/1 targeted and 35/35 owner tests passed. No UI/test relaxation was made; broad-suite intermittency remains for canonical QA. |
| `make api-generate`, `make api-check` | PASS. Both generators ran. Only OpenAPI info.version changes bytes; TypeScript declaration remains identical. |
| `make workflow-check AGENT_ID=codex-beta-image-001` | PASS including all workflow Ruff/format/strict mypy and new release-contract tests. Earlier combined typing found a variable-name conflict, fixed before the final run. |
| `python3 scripts/test-beta-images.py` | 9/9 PASS, with negative subcases for host evidence/unsupported platforms, mutable/mismatched image and PostgreSQL identities, dirty/inconsistent source metadata, local-vs-registry evidence, required source checks and manual/environment trigger boundaries, plus a real SIGTERM controller/child cleanup probe. |
| Official actionlint 1.7.12, checksum verified | PASS on `.github/workflows/beta-images.yml`; shellcheck integration disabled because this tool invocation did not install shellcheck. Hosted environment/package permissions were not exercised. |
| Frontend build-notices Prettier | PASS; production frontend TypeScript/Vite build passed in the final runtime image build. |
| Dependency pins / hash verification | All 33 production versions unchanged; 690 artifact SHA-256 values resolved from exact PyPI version metadata. Both the production and isolated development builds installed successfully using the hash-enforcing production lock. Slow whole-distribution pip-compile hashing was stopped on its exact owned container; no version refresh or dependency upgrade occurred. |
| Final `build-beta-candidate.py --evidence /tmp/beta-image-001-candidate.json --security-dir /tmp/beta-image-001-security-final` | Both production builds and the complete artifact-only runtime smoke PASS; the overall command correctly **FAILS** on the security gate below. |
| Feature graph / whitespace | 132 valid features; `git diff --check` PASS. Staged whitespace checked before commit. |
| Actual missing-host publication preflight | Refused with `PUBLICATION BLOCKED`; no registry write attempted. |

Local runtime: native Linux/amd64, Docker Engine 29.9.2, Compose 5.7.0, buildx 0.38.1.
This is development-machine evidence, not the intended host's screening.

Image-only smoke ran from a new temporary artifact directory with no local checkout, no source/host
binds in application containers, no `.env`, random credentials and ephemeral loopback exposure.
It passed explicit empty-DB migration/head verification/idempotence, non-root runtime and absence of
pytest/ruff/mypy/pip, frontend/backend routing/version/licenses, health and readiness, no baked owner,
stdin bootstrap, secure cookie attributes, owner login/session, Origin/CSRF refusal, authenticated
original media and anonymous denial, application recreation with DB/session/media retained, logout,
and DB-loss readiness failure. It did not claim real HTTPS, durable-host recovery or registry pulls.

Exact final smoke resources:

- `florabase-workflow-smoke-b84e52ad8d9d`: retired 3 containers, 1 network, 1 media volume; zero residuals.
- `florabase-workflow-smoke-c45ccdeb2bb5`: scanner lifecycle; zero residual containers/networks/volumes.
- `florabase-verification-build-0124952cb232`: retired both exclusively owned runtime image outputs;
  zero residual containers/networks/volumes. Shared upstream images/BuildKit cache were retained.

Staged review also found that subprocess.run could kill an artifact child before its cleanup on
parent interruption. The shared runner now sends SIGTERM and waits for child cleanup; a real
controller/child signal regression passes. Runtime images were unchanged by this helper correction.

Earlier failing synthetic PNG and tmpfs-restart probes also retired their exact resources; PNG was
corrected and DB-loss testing moved after logout because stopping PostgreSQL tmpfs intentionally
discards the disposable cluster. No assertion was weakened to accept an application failure.

Logs remain under `/tmp/beta-image-001-*.log`. Local candidate identities, full report paths/hashes,
raw scanner counts and critical package summaries are in
[local evidence](beta-image-001-local-evidence.json). Local image IDs are not GHCR manifest digests;
labels use the pre-commit HEAD with explicit `dirty=true`. A release must rebuild the clean final
accepted commit, never relabel this dirty candidate as published evidence.

## Blocking findings and publication prerequisites

The final Trivy 0.69.3 vulnerability+secret scan returned:

| Image | CRITICAL | HIGH | Secret findings |
| --- | ---: | ---: | ---: |
| Backend | 11 | 66 | 0 |
| Frontend | 3 | 61 | 0 |
| PostgreSQL | 2 | 26 | 0 |

These are raw scanner findings, including potentially repeated packages; exploitability and vendor
advisory disposition have not been independently triaged. No waiver, ignore-unfixed flag, severity
reduction or suppression was introduced. Backend critical packages include Pillow 12.3.0 and certifi
2026.7.22 (scanner advertises fixes 13.0.0 and 2026.10.18), plus Debian libraries. Frontend critical
packages include brotli/libcrypto/libssl; PostgreSQL includes brotli and a Go stdlib component.
Pip was removed as unnecessary runtime tooling, but the remaining findings still block publication.
Security remediation requires reviewed dependency/base updates and fresh compatibility/security
checks before calling these images production-qualified. The selected PostgreSQL candidate is not
yet a deployed database identity; any change still needs explicit review, never a silent app refresh.

There is also **no intended-host/operator selection**. `release/platform.json` stays pending and
`linux/amd64` remains conditional. Required environment protection, exact SHA secret, protected tag,
GHCR package permissions/retention and immutable-release settings are documented but were not
configured or inspected on GitHub. Actual hosted publication, registry provenance/attestation
verification and clean GHCR-pull smoke remain unexecuted. No publication authorization was inferred.

## Next session

Independently review the infrastructure diff and failure paths, including no-write host refusal,
exact commit/tag/environment gates, partial publication behavior, digest-preserving promotion,
scanner failure/cleanup, source/license retention and artifact-only isolation. Triage/remediate the
security findings and obtain intended-host evidence before publication. Real registry tests require
separate explicit authorization and configured protections; no persistent host deployment is in scope.
Then freeze source/index and run one policy-selected canonical FULL with `make feature-verify`,
using the machine-wide existing lock and **never concurrently with another FULL**. No canonical
FULL or receipt was claimed here; this handoff intentionally stops at independent QA. Do not promote
the registry entry to verified or deliver based on the local smoke alone.
