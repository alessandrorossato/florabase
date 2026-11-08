# Beta release rehearsal and beta.3 OCI mismatch

Status: implementation candidate; hosted rehearsal pending. No GHCR write, GitHub Release,
publication dispatch or public tag was created.

## beta.3 failure evidence

Workflow `42421453830` passed verification and protected authorization, then stopped in
`require_pinned_postgres` before any GHCR candidate push. The build reported index
`sha256:e514d64b47dc14141baa8cb773e7fca128a7a1784d63738f87ebc384c45a85e8`, while the pin is
`sha256:4edc079088c3f78b69fc8f9473e33881ebabea7fea2d82b3227b70a69ae3b7de`. The reported platform
manifest was `sha256:72cb11d596f44a88deaf0156e2aa90a75a54e85f812bc05d1d0968e05f1f7c02` rather than
`sha256:55b1969a7fddad118ca07a15058a43a5916dec3e4dbab38029e671225b392b91`; configs were respectively
`sha256:e01ce338509b32bb61f9527bfc830dd793e5ceed148adbf51adb494c319705c9` and
`sha256:ef74e207ea99325724ca33a7d80cef4d0bb4e58854781636185f274c3e18e02a`.

The retained publication artifact is only the 293-byte `publication-state.json`; the verification
artifact is the job log. Neither contains the old image's raw OCI platform manifest, config bytes or
layer descriptors. The committed pin evidence records the expected index, platform manifest, config
and layer count, but not its raw platform manifest or layer descriptor list. Consequently, no
byte-level historical first difference can be asserted from the failed run's retained artifacts.
The old job log shows the same pinned Dockerfile frontend, PostgreSQL base index/platform, zlib
version, fixed `SOURCE_DATE_EPOCH`, and `rewrite-timestamp` export setting. Its locked
`buildx-stable-1` BuildKit image ran BuildKit 0.33.1; the committed reproduction record names
BuildKit 0.34.2. That builder change is the leading testable cause, not a proven explanation by
itself: both versions reproduced the pin in separate local trials, so the GitHub-hosted comparison
must decide it.

The candidate correction restores the exact immutable BuildKit 0.34.2 input already named in the
successful reproduction evidence. It leaves the PostgreSQL source/base/package pins, expected
digests, exact identity check and non-root hardening unchanged. The rehearsal also rebuilds once
with the exact previous beta.3 BuildKit image as a diagnostic. It retains hash-checked raw index,
platform-manifest and config bytes plus descriptor-level layer digests for both builders.

## Local rehearsal result (not hosted acceptance)

On the TUXEDO, the corrected rehearsal completed against its owned loopback registry. Two independent
clean BuildKit 0.34.2 builds and the exact previous BuildKit image all produced the pinned PostgreSQL
index `sha256:4edc079088c3f78b69fc8f9473e33881ebabea7fea2d82b3227b70a69ae3b7de` and platform manifest
`sha256:55b1969a7fddad118ca07a15058a43a5916dec3e4dbab38029e671225b392b91`. Their config digest was
`sha256:ef74e207ea99325724ca33a7d80cef4d0bb4e58854781636185f274c3e18e02a`; all 13 layer descriptors
matched. The index, platform manifest and config raw bytes also matched their respective digests.
The two BuildKit versions were byte-identical at these OCI boundaries on this host. This falsifies
BuildKit version alone as a sufficient local explanation and does not explain beta.3's GitHub-built
index `sha256:e514d64b47dc14141baa8cb773e7fca128a7a1784d63738f87ebc384c45a85e8`. The failed run's
historical raw documents were not retained, so its first differing byte is still unknown. The
GitHub-hosted old-versus-pinned builder comparison must determine whether the runner environment or
another build input caused that output; until then, the builder pin change is only a candidate fix.

The local report is marked `github_hosted: false`; it did not run the GHCR read-only check. Backend,
frontend and PostgreSQL production builds, manifest validation, digest pulls, Trivy 0.69.3
vulnerability/secret scans (zero findings in each report), PostgreSQL SBOM, artifact-only migration,
login and media smoke, install bundle hashes, local version-tag promotion and release/attestation
input validation all passed. Disposable digests were backend
`sha256:0de1169003643c7185071f71ffc0d9b28c3559cceb4c5f9fa09426c98ed2680c`, frontend
`sha256:9bc8f3a1aade313fb454ce12c57de489eddbb1432b7b205529721d996df7a23f`, and PostgreSQL as above.
The run used synthetic local workflow metadata, created no GitHub attestations or Release API request,
and is not proof of GitHub-hosted equivalence. The final retained machine-readable report and OCI
documents are in `/tmp/florabase-beta-release-rehearsal-local-final` on the development host only.

## Non-publishing rehearsal

`.github/workflows/beta-release-rehearsal.yml` runs on `ubuntu-24.04`, using the protected workflow's
checkout and Buildx action revisions and Buildx 0.38.1. It gets package `read` only. It verifies GHCR
auth and release-tag absence through the same registry-manifest preflight helper, then drives the
protected build, manifest, scan, SBOM, image-only smoke, install-asset preparation and digest
promotion helpers against a labeled loopback `registry:2.8.3` instance. PostgreSQL is rebuilt twice
with independent no-cache builders from the same locked input. A third build with the previous
BuildKit input is diagnostic and cannot change which digest the gate accepts.

The hosted registry rehearsal proves only actions executed against the disposable registry. GHCR
authentication and tag absence are directly checked with pull scope. GHCR image writes, generated
GitHub attestations and draft/final Release API operations are recorded as not run and remain subject
to the protected live publication gate. The rehearsal never invokes that workflow or API.

The workflow always uploads its report, raw OCI evidence, image build metadata, scan reports, SBOM,
smoke log, manifest and asset hashes for 90 days. The root `rehearsal-report.json` distinguishes
passed checks from remote-only boundaries. A failed stage leaves prior evidence available as an
artifact and never counts as a successful release rehearsal.
