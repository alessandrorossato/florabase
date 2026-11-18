# WF-04 Batch 06 security integration

Pinned main `c555baabe916e3fea1ef2c8f834c747ced5aa926`. Writer
`sol-batch06-integration`, claim `a6d4ba62b170`. WF-04 accepted both clean
source tips and merged them in order without conflicts. Both source tips
are ancestors of the integrated candidate.

| Source | Frozen tip | Frozen tree | Source QA |
| --- | --- | --- | --- |
| [BETA-SECURITY-001](batch-06-hydrogen-security-remediation.md) | `800b43292493219103676c5a074385187ac6f401` | `77b94d3c030c2af8572dd3af2bf1be1ded6da8d1` | PASS, `sol-batch06-source-qa` |
| [CERT-05](batch-06-security-baseline.md) | `579aa5c559062d2c9d1639153afdec4aaf8b181a` | `a43dbeda5f381b2f16a3274cfbfae43241082f84` | Independent PASS supplied by Gemini 4 Hydrogen, Antigravity session `9f693eb5-de39-47ea-bb0f-121a9655b5c4` |

The Hydrogen delta review confirmed that the only change after independently
reviewed implementation `347bc9b8c4d6f5cba4d0b7f78c7daba38d97d807` was its
committed Markdown evidence. The prior live production QA verified backend GET
and HEAD return 404 on all four documentation paths, nginx serves the SPA fallback,
and real login, Origin, CSRF and session controls work. The integrated runtime
and workflow files match those reviewed bytes.

## Scanner provenance

The historical PostgreSQL .1 record used Grype 0.121.1 with database build
`2026-11-07T06:18:48Z` against index
`sha256:4edc079088c3f78b69fc8f9473e33881ebabea7fea2d82b3227b70a69ae3b7de`.
The squashed and all-layers reports each recorded zero HIGH/CRITICAL and three
MEDIUM matches. The [historical reduced app reports](../../security/beta-distribution-001/postgresql-image/second-scanner.json)
retain scanner and DB metadata and report hashes. Their Grype records do not
carry image digests, so they remain historical summaries with unverified digest
binding. The separate [PostgreSQL registry evidence](../../security/beta-distribution-001/postgresql-image/registry-verification.json)
records the historical .1 identity.

The 18 November reconnaissance reran Grype 0.121.1 using database build
`2026-11-18T06:21:08Z`. Each report's image configuration digest matches
the corresponding archive descriptor. The table records index digests and
full-report checksums. Numbers count matches, including package-level repeats.

| Scan set | Image | OCI index digest | HIGH / CRITICAL matches | Grype JSON SHA-256 |
| --- | --- | --- | --- | --- |
| Published beta.5 | backend | `sha256:b02344284a9fdd53698e21c708736ee899edb5eb5b9e55eb5030524a55029492` | 13 / 0 | `bffa86bf45a610b2255c30927557bb909fee828247d8a38459a797d4a495439f` |
| Published beta.5 | frontend | `sha256:4f8615acfa07a62ddf5a07d1b989d59fed6aee750c16a7641cec5369023881b2` | 8 / 0 | `f5360b62a716e3d9deb0b22965200ae4722dbd0abcbb1a730660ad4d01184418` |
| Published beta.5 | PostgreSQL .1 | `sha256:4edc079088c3f78b69fc8f9473e33881ebabea7fea2d82b3227b70a69ae3b7de` | 20 / 0 | `1aa2d4ba66e0a2d72068a34b65dad28f7b7ef28d0bd17078a25bdcee9cb898be` |
| Unpublished local beta.6 rehearsal | backend | `sha256:69e2f577a63c69324143e6723eae92904fec633c63c8b6d388fe1924015500f1` | 13 / 0 | `5fe62afcd70d273f6d74049a3fa627e5eccf4fb25d29b0135688c81a981b5844` |
| Unpublished local beta.6 rehearsal | frontend | `sha256:72637d43ea9a6def7e91dcdc0968f949a49eec81e89d75ac3bf69f08e0d95959` | 8 / 0 | `b913bdb0d941af72123d60983a9098de27adba6d8c848df86914a73c77c67ba1` |
| Unpublished local beta.6 rehearsal | PostgreSQL .2 | `sha256:baf7806351b332422b6dff9f956f1080a2f3150eab87e4ee70565a8236591658` | 8 / 0 | `55511f323ab858985dd1215c3c32d08432fb9f7c322ebae5f40d3fc1e3f1ec84` |

The local beta.6 app pair in this table has its own digests. The app digests
from the [hosted Trivy rehearsal](batch-06-security-baseline.md) differ.
Both rehearsals reproduced the same pinned PostgreSQL .2 identity. PostgreSQL
.2 updated `krb5-libs` and `libxslt` and retained `zlib=1.4-r0`. The Trivy
gate and Grype results cover different scanner inventories. The 18 November
Grype findings and runtime applicability assessments remain pending operator
review. No VEX or advisory exception was applied.

## Integrated focused verification

- 54 backend infrastructure, auth API, health, readiness and configuration tests
  passed. They exercised production GET/HEAD absence, development docs, offline
  OpenAPI, and the exact production unauthenticated route inventory.
- The offline backend schema export and frontend declaration check passed with
  zero drift. CI jobs, permissions, triggers and upload behavior were verified
  by comparing the workflow with main after reversing the eight SHA changes.
- Release workflow regressions passed 61 tests, pinned-tool lock checks passed
  four, and feature workflow regressions passed 55.
- Local artifact-only production smoke rebuilt the runtime images and passed
  with an empty disposable PostgreSQL database, Alembic `20261110_0047`,
  production health and login, and version checks. The launcher initially
  encountered the shared release tool lock and the serial retry passed.
  Both smoke and build projects reported zero residual owned resources.
  This verifies the local runtime artifact flow. It neither exercises the
  protected publisher nor certifies final RC image digests.
- The 168-entry feature graph passed. The RC checker still reports the same
  eight blockers. Backlog statuses, release classes, release inputs and
  PostgreSQL sources and pins remain unchanged.

Independent combined QA of the final commit and tree is pending. Remaining
release decisions include the separate Grype dispositions and any VEX, final
digest-bound RC scans, protected attestations, release immutability, and any
operator-approved PostgreSQL maintenance with a paired restore rehearsal.
