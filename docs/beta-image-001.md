# BETA-IMAGE-001 — production image candidate

This increment prepares distribution for `0.1.0-beta.1`; it does not approve a host, publish a release,
deploy a stack or admit real collection use. TEST-DATA-002 is independent and is not consumed here.
Independent infrastructure QA and the exact-tree canonical FULL remain the next lifecycle steps.

## Platform screening and publication prerequisite

**Publication is blocked by missing host approval and the security findings in the
[QA handoff](beta-image-001-qa.md).** No intended beta host identity, OS/CPU measurement, Docker Engine/Compose
versions or operator selection was supplied. `release/platform.json` deliberately remains `pending`.
The Foundation's initial **linux/amd64** is a candidate, not host approval. Local native amd64 smoke
is development-machine evidence only. No Synology, Netcup or other persistent environment was accessed.

Before publication the operator records the intended host's identity/specification and evidence from:

```sh
uname -s
uname -m
docker version --format '{{.Server.Os}}/{{.Server.Arch}} {{.Server.Version}}'
docker compose version
```

For the current workflow, host evidence must establish Linux, native amd64, Docker Engine and supported
Compose v2 or newer. Commit the reviewed screening to `release/platform.json` with `status=approved`,
`candidate_platform=linux/amd64`, operator, screening date, nonempty evidence references and a `host`
object containing `identity`, `os=linux`, `architecture=amd64`, `runtime=docker`, `engine_version` and
`compose_version`. Keep secrets and sensitive network names out of public evidence. The screening
is a human-reviewed input, not a claim that this feature probes or qualifies the remote host.
If the selected initial host is ARM, this workflow must first be extended and independently tested
on native arm64, with matching pins and manifest platform identities. Emulation does not qualify it.
Capacity, durable storage, uptime and Dockhand release qualification belong to BETA-RUNTIME-001.

`python3 scripts/beta_release.py check --publication` fails closed while evidence is missing. A
successful non-publication `check` validates build inputs only and never grants publication authority.

## Build and production configuration

Existing independent `backend` and `frontend` build contexts/`runtime` targets remain compatible with
DEV, Quality and Preview. Production targets now pin the Dockerfile compiler and every base image
by immutable index digest; `release/inputs.json` also pins publication BuildKit, Trivy and SBOM
scanner inputs. Production Python requirements carry artifact hashes and exact transitive versions;
frontend uses the frozen integrity-bearing pnpm lock and pinned package manager. Publication supplies
`SOURCE_DATE_EPOCH` from the selected commit. This locks reviewed inputs; it is not evidence of a
bit-for-bit reproducibility comparison across machines or independently rebuilt provenance timestamps.
Tool/base/dependency updates require a new reviewed release, never silently refreshing old identities.

Backend runs as UID/GID 10001; pip is removed from both runtime Python environments. It includes
production Python dependencies, installed application,
Alembic revisions/configuration and the existing attachment artifact utility. It contains no test
runner, fixture generator, development server, owner, database or optional WFO/WCVP indices. Frontend
runs as nginx UID/GID 101, serving compiled static assets on 8080. Node/pnpm/Vite stay in build stages.
Both declare healthchecks and OCI version, revision, source and AGPL license labels. Both include the
repository license; dependency license files remain with Python distributions, and frontend notices
are assembled from installed dependency licenses. Matching source is retained with each release.

Version surfaces are `backend/pyproject.toml`, `florabase.__version__`/OpenAPI,
`frontend/package.json`, frontend `/release.json`, OCI labels and the manifest. API metadata changes
regenerate both generated artifacts; the TypeScript declaration can remain byte-identical when only
OpenAPI information changes. Local dirty candidates explicitly record `source.dirty=true` and are
never registry release evidence.

The production configuration contract remains the existing baseline: backend/DB private on the
container network; only frontend exposed via a loopback proxy; `/api/` goes to `backend:8000` without
stripping the prefix; Docker DNS is re-resolved so a replaced backend is not cached indefinitely. Configure backend `FLORABASE_ENVIRONMENT=production`, an explicit HTTPS
`FLORABASE_CANONICAL_ORIGIN`, `FLORABASE_COOKIE_MODE=secure`, empty CORS, database URL and writable
backend-only media storage. No URL/secret is compiled into the frontend. Optional nonsecret map
configuration uses the existing `runtime-config.js` mechanism. Do not use DEV overlays for releases.
The frontend healthcheck covers nginx; backend readiness covers DB connectivity. Neither replaces
explicit Alembic-head comparison, owner acceptance, media validation or later real-HTTPS testing.
Application startup never migrates or bootstraps an owner.

## Protected publication and registry access

`.github/workflows/beta-images.yml` has **only workflow_dispatch**. A feature push, PR or version-tag
push cannot publish. Existing `quality`, `integration`, `build`, delivery and merge protections are
unchanged. The manually selected main workflow commit must equal `source_sha`, the clean build
checkout and a pre-existing protected `v<version>` tag. The exact main commit must already have all
three successful GitHub Actions checks. The workflow repeats exhaustive CI and migration cycling.
The separate `publish` job is serialized without cancellation and needs successful verification.

Repository/operator prerequisites, deliberately not configured by this feature:

1. Protect main and `v*` tags, preserving existing required reviews/checks. Restrict tag creation.
2. Create the `beta-release` environment, allow only main, require an independent reviewer, prevent
   self-review and administrative bypass. Confirm protection support on the repository's GitHub plan.
3. Set environment secret `RELEASE_APPROVED_SHA` to the exact accepted 40-character source commit.
   A missing/auto-created environment has no such secret and fails before package writes. Update this
   value only after independent QA, canonical FULL and explicit publication authorization.
4. Approve/commit intended-host screening, deliver the implementation through normal protected
   feature delivery, then select the release commit/tag. This agent does not push or create the tag.
5. Grant the workflow access to GHCR packages `florabase-backend` and `florabase-frontend`; enable
   immutable GitHub Releases and retention of versioned images/attestations/source. Restrict package
   administration/deletion. The workflow refuses existing release/version identities; GHCR tags alone
   are not an immutability control. Digest references are authoritative.

Only the publication job receives package/content write and OIDC/attestation permissions; other
jobs have read-only contents. Checkout credentials are not persisted. Registry login uses the
short-lived GITHUB_TOKEN through stdin and is removed in finally. New packages normally inherit
repository access through OCI source labels; verify visibility and access explicitly. Private pulls
use an appropriately scoped read-only credential via `docker login --password-stdin`; do not put
credentials in Compose, manifests, build arguments, source archives or command arguments.

Publication builds both targets at one accepted SHA and pushes **run-specific candidates** with
maximal BuildKit provenance and SBOM attestations. It scans the exact candidate/backend/frontend and
pinned PostgreSQL bytes with Trivy vulnerability+secret scanners; any HIGH/CRITICAL finding, database
update/network/scanner error or smoke failure stops version promotion. There is no ignore-unfixed or
blanket vulnerability suppression. Reports retain findings and scanner metadata; vulnerability DBs
are deliberately current, so later scans can change verdicts for identical images.
Native amd64 smoke pulls by digest and executes outside the checkout. Only after it succeeds are
version tags added to those exact indexes, without rebuilding or rewriting their attestations. The
manifest is attested by the workflow and retained with source, security reports, build metadata and
smoke tools/log. A new GitHub prerelease attaches these artifacts using the pre-existing tag.

No `latest` application tag is published. Previous prereleases/tags/digests are never edited or deleted.
The process cannot atomically promote two registry tags and a GitHub Release: failure partway through
may leave candidates or a partial version pair. No manifest-bearing GitHub prerelease is created
before all gates. Treat any orphan candidates/version tags as unpublished, retain evidence, and
investigate explicitly; do not retry by overwriting them. Use a new reviewed beta version when a
version was partly consumed. A GitHub upload/attestation failure may require operator disposition;
there is no automatic destructive cleanup. Runner-local BuildKit is removed; shared local builder
cache and registry artifacts are never pruned by this feature.

References: [GitHub environment protection](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments),
[Docker attestations](https://docs.docker.com/build/ci/github-actions/attestations/),
[GitHub artifact verification](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations).

## Manifest contract and consumption

`release/manifest.schema.json` defines public manifest v1. `scripts/beta_release.py` constructs and
validates cross-field consistency; consumers must also verify the registry descriptors and provenance.

| Field | Contract |
| --- | --- |
| `schema_version`, `distribution`, `version` | v1, registry-candidate, explicit beta version; local-candidate is deliberately outside the public schema |
| `source` | Repository URL, exact shared source commit, `dirty=false` |
| `platforms` | Currently only native `linux/amd64` |
| `images.backend`, `images.frontend` | GHCR digest reference, index digest, resolved platform digest, platform |
| `postgresql` | Exact repository/version/reference/index digest/platform digest/platform; copied from reviewed inputs |
| `alembic_head` | Single code migration head, checked against the actual backend image and migrated disposable DB |
| `build_inputs`, `workflow` | Reviewed immutable inputs, workflow run ID and attempt |

PostgreSQL is selected as `docker.io/library/postgres:18.6-alpine` at the index and native manifest
recorded in `release/inputs.json`. The tag is descriptive only. Application refreshes must preserve
**all** PostgreSQL identity fields; a minor/rebuild/major digest change needs separate explicit
maintenance review and compatibility/restore rehearsal. This feature does not change the existing
DEV/preview production-oriented Compose PostgreSQL selection or implement a runtime updater.

Consumers obtain the matching release-manifest and source from the versioned prerelease, verify
its artifact attestation (for example `gh attestation verify release-manifest.json --repo
alessandrorossato/florabase`), verify OCI/provenance source/revision and index/platform identities,
then pull the two exact `images.*.reference` values. Never derive a pair from independent mutable tags.
An artifact attestation proves its producer; acceptance still requires the expected protected workflow,
source, successful checks and release identity. Retain the manifest and matching source with recovery
records. BETA-RUNTIME-001 will own the versioned image-only Dockhand Compose and stable data volumes;
no persistent stack/controller is implemented here.

## Focused image-only acceptance

```sh
make test-beta-images
make smoke-beta-images
# Artifact-only reproduction, after downloading the matching release tools and manifest:
python3 smoke-beta-images.py --manifest release-manifest.json
```

Local `make smoke-beta-images` builds unique positively labelled image outputs, records a
`local-candidate` manifest in `/tmp/florabase-beta-candidate.json`, copies only smoke tools/evidence
to a fresh temporary artifact directory and executes there. Local evidence cannot claim a GHCR pull.
Production targets need no source mounts or local installation. The registry path explicitly pulls
all three immutable references and validates the actual runtime architecture and OCI identities.

The smoke registers cleanup before resource creation, uses unique project/network ownership labels,
PostgreSQL tmpfs, a dedicated media volume, random ephemeral passwords, no external volumes and only
an ephemeral frontend loopback port. It reads no `.env` and contacts no existing application/database.
It proves explicit empty → head migration, exact revision, repeated already-current migration, health,
same-origin routing, no baked owner, stdin owner bootstrap, secure-cookie settings, login/session,
Origin/CSRF refusal, authenticated original upload/download, private binary denial, non-root runtime,
no host/source binds, DB/session/media persistence across backend+frontend recreation, logout and
readiness failure on database loss. DB tmpfs is intentionally not restart-persistent. Cleanup verifies
zero owned containers/networks/volumes after success/failure/caught INT/TERM, using existing ownership
helpers; ambiguous/shared images are retained and reported. SIGKILL/daemon loss still require exact-run
recovery from the printed owner/project/source, never global prune or volume deletion.

The isolated transport is HTTP with an explicit replay of the secure cookie to test server policy;
real HTTPS/browser cookie handling and durable-host restart/reboot remain BETA-RUNTIME-001 acceptance.
No canonical FULL is run before independent QA; publication, registry-pull evidence and real-host
acceptance are not fabricated when their prerequisites are unavailable.
