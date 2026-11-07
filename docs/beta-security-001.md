Draft-release P1 correction and targeted delta-QA handoff: [lookup correction](beta-security-001-lookup-correction.md).

# BETA-SECURITY-001 — security and release hardening candidate

Initial main: `f0d24224cf0eae32cc8670aeab54a67d53a2c723`.
Writer: `codex-beta-security-001`, authoritative branch `feat/beta-security-001`.
Status: candidate ready for independent QA; feature remains `in_progress`. Canonical FULL awaits QA authorization. No publication authorization.

## Plan and boundaries

Inventory the retained exact artifacts and measure compatible maintained runtime bases. Prefer
upstream digest-pinned refreshes and a smaller nginx runtime to ad-hoc package overlays. Keep Python
3.14/application dependency majors and PostgreSQL 18 unchanged. Preserve every PostgreSQL identity
field: its fixes require separately authorized maintenance. Retain original and new raw reports.

Harden executable tooling cache ownership, isolate bootstrap imports, verify complete scan reports,
bind protected checks to the expected CI workflow and exact source, and retain incomplete-publication
state. Preserve manifest schema v1 and every consumer field: BETA-RUNTIME-001 needs no interface
change. Do not touch its Compose, storage, controller or backups. No remote settings are changed.
No VEX is active or accepted. Any exception needs exact advisory/package/artifact applicability,
expiry and explicit operator acceptance, followed by a separately reviewed gate implementation.

## Supplied candidate-host evidence (not a publication prerequisite)

Operator instruction dated 2026-11-03 selects Synology DS224+, Linux/amd64, Docker Engine 24.0.2,
Compose 2.20.1; four cores, 9.6 GiB RAM, about 3.7 GiB available, low observed load and about 2.6 TB
free. This establishes preliminary selection/suitability; capacity, durability, recovery and runtime
security acceptance belong to BETA-RUNTIME-001. No remote host was probed here. Compatible amd64
Docker PCs/VPSs remain supported; application/images have no Synology-specific assumptions.

## Remediation outcome and artifact boundaries

[Complete retained evidence](security/beta-security-001/README.md) includes original report hashes,
every trial/new raw report, individual advisory/package inventories, exact final index/native/config
identities, build inputs, compatibility fixture/tool hashes and structured verification evidence. Counts are scanner records:

| Production image | Original CRITICAL / HIGH | Updated CRITICAL / HIGH | Secrets |
| --- | ---: | ---: | ---: |
| Backend | 2 / 36 | 0 / 0 | 0 |
| Frontend | 1 / 4 | 0 / 0 | 0 |
| PostgreSQL (unchanged) | 2 / 26 | 2 / 26 | 0 |

Backend uses official digest-pinned Python 3.14 Alpine (actual Python 3.14.10, SQLite 3.53.4),
with production hash-locked binary wheels, no compiler/pip in runtime, UID/GID 10001 and no
setuid/setgid executables. The unchanged Debian development builder remains separate to preserve
development/Quality compatibility; it is not a production image. No Python application dependency or
PostgreSQL major was changed. Frontend uses digest-pinned stable nginx unprivileged Alpine **slim**,
UID/GID 101, without the unnecessary curl/Brotli/expat runtime packages. License/notices remain.
Scanner-reported uncompressed size fell from 228.3 to 152.8 MiB for backend and 63.7 to 23.7 MiB
for frontend; detected OS package counts fell from 97 to 30 and 70 to 21 respectively.
The evaluated trixie base eliminated the two CRITICAL findings but left 45 OS HIGH findings plus five
pip-vendored HIGH findings before pip removal; it was rejected. Python Alpine had only the five
pip-vendored findings, eliminated by the existing runtime pip removal. Raw trials remain available.
Upstream base rationale: [official Python variants](https://hub.docker.com/_/python) and
[maintained unprivileged nginx images](https://github.com/nginx/docker-nginx-unprivileged).

Two official application build/artifact-smoke/scan batches passed application smoke and reached the
expected **blocking** PostgreSQL verdict. The final descriptor-bound batch also passed 103 focused
media/provider/cache/SQLite taxonomy/geography tests against its exact production backend bytes,
with patched Pillow 13.0.0/certifi 2026.10.18 and CA verification asserted. This compatibility probe
mounts read-only tests/tools separately, after official artifact-only smoke; no test/tool is added to
production layers. Its initial attempt failed because the test fixture was private to host UID 1000;
only disposable fixture read permissions were corrected for container UID 10001, then all 103 passed.
All owned image/smoke/scan/probe resources retired; shared upstream images/BuildKit cache remain.
The candidate carries dirty-source local OCI labels at the initial main SHA. It is audit evidence,
not a clean accepted source build or a GHCR artifact. Publication must rebuild the final authorized
clean commit and repeat every gate. The DS224+ has not run these images in this task.

## PostgreSQL maintenance and proposed exceptions

Every PostgreSQL identity field in release/inputs.json is byte-equivalent to the initial main input.
A read-only query of the current `18.6-alpine` tag resolves to the **same selected index**, so there is
no freshly rebuilt same-version upstream image to select from this measurement. Do not silently
upgrade PostgreSQL, patch its live container, or let application promotion alter its digest.

The two library findings remain potentially applicable: brotli-libs 1.2.0-r1 / CVE-2026-111497
(advertised fix 1.2.1-r0), libcurl 8.22.0-r0 / CVE-2026-92392 (8.23.0-r0). Exact-image ldd evidence
shows the optional libpq-oauth-18.so loads curl and Brotli. A hostile compressed HTTP response or an
HTTP/2 upload/RST_STREAM is required respectively. Ordinary Florabase SCRAM use does not configure
OAuth, but client utilities/extensions/operator actions have not been excluded by an accepted runtime
policy. No exception is proposed for these libraries. See
[PostgreSQL's optional OAuth client contract](https://www.postgresql.org/docs/18/libpq-oauth.html).

The remaining 26 findings identify Go 1.24.6 in `/usr/local/bin/gosu`, not PostgreSQL's server.
The exact binary SHA-256 matches the official gosu 1.19 release. Reviewed main/setup-user code does
local account parsing, privilege change and exec; negative symbol-prefix inspection supports absence
of affected TLS/X509, HTTP/URL/mail, MIME, ASN1/XML/template and os.Root code. The Windows-only
Dial/LookupPort advisory also conflicts with the pinned Linux platform. The
[per-advisory assessments](security/beta-security-001/postgresql-applicability.json) retain each
exploit prerequisite, fixed versions, target and exact image identity. These support **draft** narrowly
scoped not-affected VEX proposals, expiring 2026-12-03T00:00:00Z or any artifact/platform change.
Negative strings alone are not proof; independent review must check the combined binary/source
reasoning. The exact binary match proves release correspondence, not an independent reproducible build.

No VEX is accepted, emitted as scanner input or applied. Accepting a draft does not make this gate
pass: the code has no VEX ingestion path, and the two library findings still block. Prefer separately
authorized PostgreSQL maintenance: select/review a maintained fixed image or a controlled same-version
rebuild with pinned patched libraries and reviewed gosu/Go toolchain, then perform compatibility and
paired restore rehearsals under BETA-RUNTIME-001 before changing its identity. Any release-gate VEX
support is a separately reviewed change requiring explicit operator acceptance of each exact
advisory/component/artifact/expiry. There is no blanket unfixed exemption.

## Release security changes

- Publication has read-only contents/actions at workflow scope. Only the protected publish job has
  contents/packages/attestations/OIDC write. All publication actions stay SHA-pinned, checkout
  credentials are not persisted, and credentials travel through stdin/environment only.
- Exact source approval is checked again inside the publisher **before registry login**: official
  repository, manual main dispatch, protected workflow ref, hosted runner, clean source and approved
  SHA. Protected checks now come from a successful canonical ci.yml **push to main**, matching source
  and repository, with all three successful jobs from one run attempt. A similarly named external or
  different workflow cannot substitute. API pagination and errors remain fail-closed.
- Scan success needs a fresh report, exact config digest, OS inventory and expected Python/nginx/gosu
  inventories. Existing reports refuse overwrite. Suppressed findings are displayed; the ignore file
  is explicitly /dev/null. Scanner errors, secrets, HIGH/CRITICAL findings and incomplete reports block.
  Saved OCI index/native descriptor bytes are hash-checked and tied to the saved config and inspect ID.
  Classic Docker registry exports obtain index/native bytes by immutable registry reference and
  hash-check both against the saved config; a real pinned PostgreSQL lookup and adversarial fixtures
  pass. Local-only native-descriptor retention requires an OCI-capable image store; production
  consumers need only digest pulls, so the selected Engine 24 host is not required to build/scan.
- Artifact smoke now runs both application services with read-only rootfs, all capabilities dropped,
  no-new-privileges and bounded noexec/nosuid tmpfs. Registry application descriptors are compared
  with the manifest as well as the existing PostgreSQL check.
- Release Python tooling creates an owned 0700 cache under trusted non-symlink ancestors, rejects
  foreign/shared or unsafe nested entries before touching a lock/executable, and permits only bounded
  internal/expected interpreter links. Cache contract v2 does not reuse the old unsafe namespace.
  Pip bootstrap is hash-checked and runs with isolated imports; the final interpreter ignores Python
  environment/user-site injection. Dependencies remain hash-locked binary wheels in a venv, with no
  system pip installation. Other UIDs are excluded; same-UID processes remain trusted like source.
  FLORABASE_RELEASE_CACHE must have safe ancestry; unsafe caches are refused, never repaired in place.
  Offline reuse works; missing verified bootstrap/wheels refuses. Host Docker/gh remain prerequisites,
  not packages installed into the application; incompatible gh attestation flags refuse preflight.
- Individual OCI index attestations now bind both image digests to this protected workflow, alongside
  maximal BuildKit provenance/SBOM and the signed release manifest. They are stored with GitHub
  attestations; no additional registry-referrer upload is claimed. The public manifest v1 is unchanged.
- publication-state.json records candidate digests and completed phases before promotion. It is
  diagnostic evidence, never permission to resume/retry. Security/smoke failure cannot promote tags.
  A complete pair still requires all image/manifest attestations before release creation. Assets first
  upload to a **draft**; exact asset names, byte sizes and GitHub-reported SHA-256 digests must match
  every local file before the draft is published. A partial draft is not an accepted release.

## Operator configuration and exact approvals still required

No remote repository setting, environment, tag, package, release or persistent host was changed.

1. Independent infrastructure/security QA must review this diff, retained raw reports and the draft
   applicability evidence. Only after QA explicitly authorizes it, freeze source/index and run one
   `make feature-verify AGENT_ID=<receiving-claim-owner>`; security selects FULL. This implementation
   has **not** run canonical FULL and has no delivery receipt. Follow the writer handoff protocol.
2. Resolve PostgreSQL's 28 blocking records through separate explicit maintenance authorization; or
   independently review and explicitly accept each defensible expiring VEX draft, then authorize a
   narrowly tested ingestion policy. Library fixes remain required. Do not interpret this handoff as
   a security exception, PostgreSQL maintenance approval or beta admission.
3. Host acceptance is no longer a publication prerequisite (`release/platform.json` records the supported
   linux/amd64 platform; the DS224+ measurements are a candidate-target note). Runtime capacity,
   persistent IO, reboot/recovery, HTTPS and Engine 24.0.2 / Compose 2.20.1 operational acceptance remain
   separate post-publication BETA-RUNTIME-001 deployment gates on the actual host.
4. Protect main and v* tags with required reviews/checks; restrict tag creation to the release operator.
   Configure **beta-release** environment with an explicit **main-only branch rule**, independent
   required reviewer, prevent self-review and no administrative bypass. Confirm the repository plan
   actually supports these protections. Never rely on an automatically created/unprotected environment.
   [GitHub protection semantics](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments).
5. Keep RELEASE_APPROVED_SHA **only as an environment secret**, never a repository/organization secret
   fallback. Set it to the exact clean accepted main commit only after QA, canonical FULL and explicit
   publication authorization; remove/rotate stale approvals after each attempt. Create a protected
   version tag pointing to that same commit. An existing version/release is never overwritten.
6. Grant the repository's short-lived GITHUB_TOKEN access to only the two GHCR packages and GitHub
   attestations/releases. Enable immutable Releases and restrict package tag/deletion administration;
   retain old digests, matching source and attestations. GHCR tag mutation is not cryptographically
   prevented by this code: operator/package access controls matter; digests are authoritative.
   Hosted permission/protection/registry-pull/attestation behavior has not been executed locally.
7. Only after all gates are clear, the operator may separately authorize protected workflow dispatch
   and environment approval for that exact source. This task does not push, create a PR/tag, deliver,
   publish or deploy. New GHCR artifacts and the actual protected workflow require subsequent evidence.

Publication cannot atomically commit two registry tags plus GitHub assets. On interruption/failure,
retain run-specific candidates, checkpoints, build metadata and artifacts; do not treat a workflow
artifact, draft release, one promoted tag or a manifest by itself as acceptance. SIGKILL/runner loss
may prevent final logs/upload; inspect the exact run/candidate names and remote read-only state.
A failed upload/attestation/draft-finalization needs operator diagnosis. Never overwrite an identity,
blindly retry, delete remote evidence or infer absence from an API failure. Use a new reviewed beta
version if a version identity was partly consumed. No automatic destructive registry cleanup exists.

Consumers require a published nondraft release, the authorized protected tag/commit, exact manifest
schema/inputs and all three expected attestations. Verify manifest and each `oci://<digest-reference>`
with `gh attestation verify`, adding `--repo alessandrorossato/florabase`,
`--signer-workflow alessandrorossato/florabase/.github/workflows/beta-images.yml`,
`--source-ref refs/heads/main --source-digest "$AUTHORIZED_COMMIT" --deny-self-hosted-runners`.
Obtain AUTHORIZED_COMMIT independently of unverified assets. Verify native/index descriptors and OCI
labels against the signed manifest, then pull by digest. Do not execute downloaded tools before
verifying their asset digests against the accepted release. Runtime manifest schema/fields remain
unchanged, so no BETA-RUNTIME-001 interface adjustment is required.

## Focused validation and QA boundary

- Baseline `make test-beta-images`: 12/12 before changes.
- Updated `make test-beta-images`: 21/21, including unsafe cache, spoofed CI/source, incomplete/suppressed
  scan, native/config descriptor, partial draft and security/smoke-failure publication regressions.
- `make workflow-check AGENT_ID=codex-beta-security-001`: PASS (policy, Ruff/format, strict mypy).
- Checksum-verified actionlint 1.7.12 on CI/publication YAML: PASS (shellcheck integration disabled).
- Resource ownership/lifecycle regressions: 19/19. Final official artifact-only smoke and 103 exact
  Alpine runtime compatibility tests: PASS. All scan batches preserve blocking PostgreSQL results;
  a nonzero overall scan command is expected and must not be reported as release security PASS.
- Offline isolated release-tool tests: final 21/21 warm offline, 20/20 in a fresh wheelhouse-only
  venv before the classic-store test was added; empty cache refuses. `make api-check`: PASS with no drift; environment boundary
  regressions: 35/35. Real Compose SIGTERM with late creation: PASS, two containers/network/media
  retired, repeated cleanup and unchanged foreign inventory proven. Feature graph: 134 valid; whitespace
  checked before commit. Structured results and local log hashes are in verification-evidence.json.

Canonical FULL, full product/integration/migration-cycle suites, actual GHCR publication/pulls,
hosted environment enforcement, real-host runtime/security acceptance and beta admission remain
unexecuted. The ordinary image smoke does test disposable empty-to-head and repeated migration;
it is not the canonical full upgrade/downgrade cycle. No local commit claims a verification receipt.
