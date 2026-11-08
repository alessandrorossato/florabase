# Beta publication preflight

On a clean committed checkout, run:

```sh
make release-preflight-local
```

Use the default local Docker socket on native Linux/amd64 with Compose and Buildx **v0.38.1**.
The command prints a new temporary evidence directory. It uses the hash-locked Python tooling,
pinned BuildKit, Dockerfile frontend, registry, Syft and Trivy. The first run needs network access
for pinned images and dependencies, Alpine and Trivy databases. A warm hash-locked Python cache
supports `FLORABASE_RELEASE_OFFLINE=1` for tooling bootstrap. The builds and scanner still have
their normal network requirements.

The local preflight and hosted rehearsal call the same publisher function as protected publication.
Each uses a fresh, uniquely owned loopback registry and explicitly selected builder. They build
PostgreSQL in a separate scratch registry, compare the exact index and platform digests to the
release pins and copy the index to a candidate tag in the destination. This exercises first
publication even when GHCR already holds the pinned PostgreSQL tag. The protected publisher reuses
that tag only when it matches the pin. The earlier double-build and previous-toolchain comparison
are historical diagnostic experiments. The normal rehearsal performs the one build and copy that
the first-time publisher performs.

## Output and checkpoints

| Stage | Evidence and refusal behavior |
| --- | --- |
| PREPARE | Version, platform and tool pins, exact clean checkout and native local daemon |
| VALIDATE | Definite application-tag absence and pinned or absent PostgreSQL tag. Protected runs also recheck the selected Git tag and GitHub Release absence |
| CANDIDATES | Digest references, BuildKit metadata and first-time PostgreSQL raw OCI evidence under `diagnostics/postgres-reproducibility/` |
| SCAN/SMOKE | Pinned Trivy vulnerability and secret verdicts, configuration and layer identities, BuildKit SBOMs and PostgreSQL CycloneDX, artifact-only migration, owner login and media smoke |
| VALIDATE ASSETS | Exact seven-file inventory with sizes and SHA-256 digests, manifest-bound installation bundle, exact attestation subjects, draft request and upload verification, and a fresh version-absence check |
| PROMOTE | Verify each newly written version tag by digest and record each successful write. A running or failed write may have reached the registry |
| ATTEST | Protected Actions issues provenance for the tested image indexes, manifest and bundle files. The runner records the action outcomes |
| RELEASE | Create a private draft using the exact validated file list, verify its identity and uploaded asset digests, then mark it public as a prerelease |

`output/assets/` is the only distribution directory. It holds the manifest, three installation
files, source archive, release notes and PostgreSQL SBOM. Internal diagnostics and stage state are
retained separately, including incomplete output on failure. `output/diagnostics/publication-state.json`
records stage outcomes, validated subjects and asset digests. The workflow uploads both directories
for investigation. The release request uploads the exact validated filenames.

The failed beta.4 workflow ([run 42508727559](https://github.com/alessandrorossato/florabase/actions/runs/42508727559))
left `publication-state.json` at `smoke_passed` and contained two files nested under
`postgres-reproducibility/` beside the release assets. The archive, notes and bundle had already
been generated when `prepare_release_assets()` called `release_asset_inventory()`. Putting that
directory in the asset directory reproduces the rejection in the focused suite. Run
`make test-beta-images` independently to test this boundary, malformed and changed assets,
security and smoke failures, a tag appearing during preparation, partial promotion and draft
digest mismatch.

## Verification coverage

| Gate | Before | After |
| --- | --- | --- |
| Local canonical FULL | Workflow checks, product static checks and unit suites, API drift, both production builds, PostgreSQL integration and forced migration cycle | Same, including the focused release regressions |
| PR CI | Exact PR merge SHA, impact policy, complete product suites and builds for product changes, workflow checks for high-risk changes | Same, plus the publisher-compatible rehearsal in its existing separate workflow |
| Main push CI | Exact main SHA, full workflow and product checks, integration and both production builds | Same plus a forced migration cycle against the preceding main SHA |
| Hosted rehearsal | Read-only GHCR probe, registry build/scan/smoke and a separately assembled output layout | Read-only GHCR probe and the actual publisher pipeline, on PR and exact main push SHA. No exhaustive application suite |
| Protected publication | Exact main CI evidence, then another `make ci` and forced migration cycle before protected publisher | Require successful exact-SHA main CI and main-push rehearsal, including the named migration job. Reuse this evidence during publication retries |

Main CI evidence comes from a successful platform workflow run and its latest completed jobs.
Successful jobs from the same run and SHA can be reused when only failed jobs are rerun. A PR merge revision, prior SHA, another workflow, a missing job or an incomplete run
cannot authorize publication. Main CI and local FULL remain distinct trust boundaries. The image
build and scanner inside protected publication still run on the bytes actually being published.

## Remote boundaries and retry policy

The local command simulates promotion only in the disposable registry. Hosted rehearsal adds GHCR
read-only credential and version checks. Protected-only operations include the approved-SHA
environment secret, package write policy, GitHub-issued attestations and actual draft creation,
asset upload and finalization. The protected run needs the exact main commit, its matching immutable
version tag, successful main CI, successful hosted rehearsal and separate environment approval.

Before PROMOTE, correct the failed stage and rerun preflight. An unchanged source can reuse its
successful CI evidence. After any PROMOTE write starts, inspect the retained journal and the
registry before taking action. A partial promotion, attestation or draft requires operator review.
The publisher refuses an occupied application version, an existing release/draft or reused
checkpoint. Use a new version for new source and leave existing Git tags, digests, attestations and
releases intact. The registry API has no conditional tag creation in this path. Protected workflow
concurrency serializes this publisher, and release package write permissions must remain exclusive
to it while publishing.
