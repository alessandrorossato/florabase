Current reliability correction and fresh official smoke/security evidence: [final reliability handoff](beta-image-001-final-reliability.md).

# BETA-IMAGE-001 QA corrections

Independent findings supplied by the operator for reviewed commit `3b9401d` / tree
`2356c7e6ffa8a8ceacbd72fe286eadf81e5c12b0`: CONDITIONAL PASS with D1–D4.

- D1: container inspection disappearance requires a fresh successful all-container inventory before being treated as removed. Other inspection failures fail closed. Remaining exact-label networks/media retire; repeats are safe. Recovery accepts a recorded missing source only as one of four required matching ownership labels, with foreign-user refusal intact.
- D2: repository, exact beta-images signer workflow, main source ref, authorized source commit and hosted-runner policy are now mandatory in the verification runbook. Official checksum-verified gh 2.103.3 exposes all flags; local 2.46.0 does not. Workflow checks actual flag support before publication. Consumers must also compare authorized version/tag, index and native digests against the signed manifest.
- D3: the published Draft 2020-12 JSON schema is enforced using pinned host-only jsonschema tooling, distributed with artifact tools. Fixed overescaped schema patterns; restricted each image to its exact expected GHCR repository, enforced required run identities, immutable base/tool references and complete fields, while preserving cross-field source/platform/PostgreSQL/digest checks. Foreign owners, identical pair references, missing/null run IDs, mutable inputs and missing fields have negative regressions.
- D4: fetched and locally merged `origin/main` at `1e44c3fb6c8d1274d172a9895261737b65fb1648` without rewriting. Resolved progress conflict by retaining both sections. Main adds TEST-DATA-002 fixture/planner/integration-test code, registry/docs and Make targets; no runtime application, Dockerfile or release implementation came from main. The feature did not edit or execute another environment.

## Focused evidence

Release tests 11/11; resource tests 17/17. Real Docker race/repeat fixture passed with unchanged foreign container inventory and zero owned residual resources. A first inventory-comparison attempt observed concurrent smoke activity and failed its global equality assertion; its exact owned cleanup still completed. A second quiet fixture passed. Real recovery CLI on a deleted temporary source refused a forged source, cleaned exact labelled network/media with the correct source and passed a repeat.

Workflow Ruff/format/strict mypy PASS after fixing the findings exposed during iteration. Media compatibility: 86 passed across attachment storage, remote-media fetch/copies and external-botany provider/service tests. No TLS verification bypass was added. A separate SSLContext check loaded the updated certifi CA bundle with CERT_REQUIRED and hostname verification enabled; no live remote TLS endpoint acceptance is claimed. Artifact-only smoke and security batch results are recorded below. No canonical FULL, push, PR, remote merge, registry publication or deployment.

## Security batch and remaining acceptance

Reviewed the original scanner evidence and Pillow 13 release notes before changing pins. Pillow handles untrusted attachment/media decoding and tile validation; all retain validation and decompression limits. certifi supplies outbound TLS trust through httpx; no custom trust-store edits or disabled verification. Upgraded Pillow 12.3.0 → 13.0.0 and certifi 2026.7.22 → 2026.10.18 in production/dev locks with exact artifact hashes. Removed application-image setuid/setgid bits, retaining non-root runtime.

Original evidence remains unchanged in `beta-image-001-local-evidence.json` and `/tmp/beta-image-001-security-final/`. Fresh reports in `/tmp/beta-qa-security/`: backend 5 CRITICAL/43 HIGH (previously 11/66), frontend 3/61 and PostgreSQL 2/26. All reports have zero secret findings. Remaining backend critical packages are SQLite, Perl and zlib; frontend brotli/OpenSSL; PostgreSQL brotli/Go stdlib. The scanner gate still fails and promotion is prohibited. No blanket suppression, ignore-unfixed or severity reduction.

A narrowly scoped **draft VEX proposal**, not approved or consumed by scanners, concerns only CVE-2023-45853 against Debian bookworm zlib1g `1:1.2.13.dfsg-1` in the exact backend candidate. Debian's tracker says vulnerable contrib/minizip was not built in that source version. Proposed assessment: not affected through this binary, subject to independent confirmation of the exact SBOM/binary contents, absence of bundled pyminizip and explicit operator approval. Expires 2026-12-03 or immediately on image/dependency change. The attempted post-cleanup runtime file listing failed because the disposable image had already been retired; it is not evidence of absence. No other advisory receives this disposition. Keep the gate failing until approved per-advisory policy and all other findings are resolved.

Sources: [Pillow release notes](https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html), [certifi exact metadata](https://pypi.org/pypi/certifi/2026.10.18/json), [Debian advisory applicability](https://security-tracker.debian.org/tracker/CVE-2023-45853), [gh verification policy](https://cli.github.com/manual/gh_attestation_verify).

## Host and operational boundaries

Operator selected Synology DS224+, Linux/amd64. This is selection evidence, not fabricated on-host runtime/capacity acceptance. Docker Engine/Compose measurements, RAM/disk/IO/uptime and real-host acceptance remain pending. Compatible Linux/amd64 PCs/VPSs must work with Compose alone; Dockhand is optional control plane. Arm64 remains a bounded later extension. No NAS was accessed. Publication protections, explicit approval, registry-pull acceptance and canonical FULL remain outstanding.

## Second base-image batch — blocked, not accepted

Rechecked the original descriptive tags: all still selected original digests. Maintained Python 3.14/bookworm and nginx stable/alpine streams supplied new immutable candidates, now pinned in release/inputs.json and Dockerfiles. PostgreSQL 18-alpine resolves to the existing 18.6 digest, retained unchanged. Both new production builds passed. The updated-base smoke then failed **before application startup**, while registry inspection of PostgreSQL returned HTTP 429 Too Many Requests at `registry-1.docker.io/v2/library/postgres/manifests/sha256:84abaff33a0bbc646ae9b1492a05168d4b09814ca49ff2a2839b0969b59f60a0`, explicitly reporting the unauthenticated pull limit. Owned build outputs were retired with zero container/network/volume residuals. No registry-limit bypass or credential changes were attempted.

**Current base pins have no completed runtime smoke or security scan.** The 5/43, 3/61, 2/26 counts above belong only to the completed dependency/setuid batch on the previous bases. They cannot certify the current images. Rebuild, artifact-only smoke and rescan the current exact pins after registry access recovers; this remains a delivery/publication blocker in addition to independent delta QA and canonical FULL. The VEX draft above cannot carry across this image change without a new exact-artifact assessment. Original scanner evidence remains unchanged.

After reconciliation, a separate artifact-only smoke of batch A passed, with zero residual owned resources. An additional 16/16 tile-cache/API tests passed (occurrence cache and external-botany API), bringing dependency compatibility coverage to 102 tests. Updated snapshot/report hashes and explicit unknown batch-B security state are in [correction evidence](beta-image-001-qa-correction-evidence.json).

CI retains the existing unconditional quality/integration/build names and protections; only the quality job gains installation of pinned host validation dependencies. Both new and existing workflow YAML pass actionlint. A final source/index/commit check will leave the feature clean, with full SHA/tree reported by Git at handoff.

Final compatibility clarification: reusable Quality initially retained old installed packages despite changed lockfiles. Those first runs alone were not dependency-upgrade evidence. The final isolated run installed the exact patched packages under /tmp, asserted Pillow 13.0.0 and certifi 2026.10.18 before execution, loaded the patched CA bundle with CERT_REQUIRED/hostname checking, and passed all 102 selected tests (`/tmp/beta-qa-patched-compat.log`). Final workflow-check and actionlint pass. No full product/integration suite or canonical FULL is claimed.
