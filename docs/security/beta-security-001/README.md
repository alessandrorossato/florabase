# BETA-SECURITY-001 retained security evidence

Measured 2026-11-03 with the unchanged pinned Trivy 0.69.3 vulnerability+secret policy.
This is local dirty-source evidence, not publication/host approval. No finding is suppressed.
Build/diagnostic logs remain in /tmp with hashes in verification-evidence.json; they are not committed build output.

- [All scan inventories](all-scan-inventories.json): original and every measured update/base trial,
  per advisory/package/version/target/fix availability, report hashes, identities, severity and prerequisites.
- [Final exact identity summary](summary.json); [final raw reports and hash-checked OCI descriptors](candidate-c/).
- [Original unchanged raw evidence](../beta-image-001-reliability/README.md); its report hashes are
  included in the inventory. Original reports were not edited.
- [First application remediation batch](candidate-a/) and the evaluated
  [Debian trixie/nginx slim bases](base-debian-trixie-and-nginx-slim/),
  [Python Alpine base](base-python-alpine/). Base pip-vendored findings are absent from the final runtime
  because pip is removed; final runtime reports independently prove this, without ignoring findings.
- [PostgreSQL per-advisory applicability](postgresql-applicability.json),
  [binary/package/entrypoint inspection](postgresql-runtime-inspection.json),
  [actual OAuth curl/Brotli linkage](postgresql-runtime-inspection.json),
  [exact upstream gosu binary match](gosu-upstream.json).
- [26 advisory-specific VEX drafts](vex-drafts.json): **UNAPPROVED**, no scanner ingestion,
  expire 2026-12-03T00:00:00Z or artifact/platform change. No exception proposed for curl/Brotli.
- [Compatibility probe](compatibility-probe.py), [test-tool wheel hashes](compatibility-test-inputs.json),
  [verification results and local diagnostic log hashes](verification-evidence.json).

The probe wraps official artifact smoke only to append separate read-only test/tool mounts against
its exact backend artifact. Those mounts are not part of artifact-only smoke or production images.
The probe recreates ephemeral test tools under /tmp and requires the trusted source checkout,
release-tools launcher and explicit Docker access. Its final overall exit is nonzero because
PostgreSQL blocks, after smoke and 103 tests succeed. Candidate A lacks exported native descriptors;
final Candidate C adds hash-checked native/index/config retention and supersedes its identity evidence.
One intervening probe failed to import pytest due to host-private fixture permissions; it did not
reach scanning and retired every owned resource. No application defect or test assertion was bypassed.

| Final image | CRITICAL | HIGH | Secrets | Configuration digest |
| --- | ---: | ---: | ---: | --- |
| backend | 0 | 0 | 0 | `sha256:325f0efd273bd6869a3522962dac449edc5216d89826b4c98833da0d38ea5b0c` |
| frontend | 0 | 0 | 0 | `sha256:52d670a1396cee3c1e75f44b3db1e33d9e6746626a9faba91d671bb03c92537b` |
| postgresql | 2 | 26 | 0 | `sha256:57b23a0326ee442e83b3d3fa027c5a148be0a392d7c91d1ca4e1e70131ee859a` |

Complete native/index digests are in summary.json and each descriptor record. Config IDs are checked
against the raw Trivy ImageID; exported descriptor blobs were SHA-256 checked before retention.
Docker inspect IDs can be indexes, so they are never mislabeled as configuration identities.
Local image labels include disposable ownership; a clean authorized release commit must be rebuilt.
Scan CreatedAt/version metadata is retained. Vulnerability databases are current online Trivy inputs,
so future counts may change for the same image. No offline/stale-DB override was used.

The same-version upstream PostgreSQL descriptor still equals the selected immutable index. Any
PostgreSQL image/library/gosu refresh is a separate explicit maintenance decision, with compatibility
and paired recovery evidence. These application updates do not alter that contract or its identity.

[Operator requirements and QA handoff](../../beta-security-001.md) lists every remaining approval.
