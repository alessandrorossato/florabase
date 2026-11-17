# CERT-05 — release evidence for the beta distribution entries

Branch `docs/cert-05-release-evidence`, writer `sol-cert05`, from `main`
`b088a94eef82418b033ae42391726cabe5f4f0c5` (after Batch 03, #193). Documentation only. It was
checked on 2026-11-17 against the repository at that commit and against read-only GitHub run, PR
and release metadata. No release asset was downloaded.

This record evaluates every acceptance criterion of BETA-IMAGE-001 and beta-postgres-repro-001.
It changes no status. Both entries stay `in_progress` until the operator rules on the
recommendations at the end.

Verdicts:

- **Met**: committed or protected-run evidence covers the whole criterion.
- **Superseded**: the criterion names a historical target that later delivery replaced. Needs
  operator acceptance.
- **Gap**: evidence is missing or does not cover the whole criterion.

## BETA-IMAGE-001

Title: "Publish a paired immutable GHCR production-image release for v0.1.0-beta.1".

| # | Criterion (short) | Evidence | Verdict |
| --- | --- | --- | --- |
| 1 | Supported platform recorded before publication, with no specific host approval | [`release/platform.json`](../../../release/platform.json): `candidate_platform` `linux/amd64`, `host_approval_required: false`; host acceptance is a separate `pending` deployment gate. | Met |
| 2 | Protected workflow, same source revision, minimal registry permissions, coherent version, OCI source/revision/version labels, licences; no PR publication | [`beta-images.yml`](../../../.github/workflows/beta-images.yml): `workflow_dispatch` only, both jobs `if: github.ref == 'refs/heads/main'`; `source_sha` must equal `GITHUB_SHA` and the commit of the `v<version>` tag from `release/inputs.json`. Workflow permissions are `contents: read`, `actions: read`; only the `publish` job, under environment `beta-release` with an exact-commit approval step, adds `contents`, `packages`, `id-token` and `attestations` write. Labels `org.opencontainers.image.{title,version,revision,source,licenses}` in [`backend/Dockerfile`](../../../backend/Dockerfile) and [`frontend/Dockerfile`](../../../frontend/Dockerfile); PostgreSQL labels checked by `scripts/beta_release.py` and `scripts/smoke-beta-images.py`. `LICENSE` is copied into the backend, frontend and PostgreSQL images; the frontend adds `THIRD_PARTY_NOTICES.txt`. Protected run 42520884360 (`4c845b1`, 2026-11-08) succeeded in both jobs. | Met |
| 3 | Versioned manifest with digests, architectures, source commit and Alembic head; earlier artifacts kept; no secrets or development dependencies; immutable PostgreSQL reference | [`release/manifest.schema.json`](../../../release/manifest.schema.json) requires `version`, `source`, `platforms`, `alembic_head`, `postgresql`, `images`, `build_inputs`. Release `v0.1.0-beta.5` (prerelease, target `4c845b1`) lists `release-manifest.json` and `postgresql-sbom.cdx.json` among seven assets. Run 42520884360 rechecked the validated assets and attested the backend, frontend and PostgreSQL indexes, the install bundle and the manifest. The beta.1 to beta.4 tags remain. The images exclude test and development tooling, operator data and optional WFO/WCVP indices ([`beta-image-001.md`](../../beta-image-001.md)); scans and secret checks run in the publisher ([preflight](../../security/beta-distribution-001/release-publication-preflight.md)). The manifest content was not downloaded for this record. | Met |
| 4 | Clean registry-pull smoke on each native architecture: non-root, same-origin proxy, Alembic, owner bootstrap, health, media persistence | Run 42520884360 step "Build, scan and smoke immutable candidates; promote only the tested pair" succeeded. [`scripts/smoke-beta-images.py`](../../../scripts/smoke-beta-images.py) refuses images without a non-root user, checks `alembic heads`/`upgrade head`, `florabase.auth.bootstrap`, `/healthz` and the media volume. Only `linux/amd64` is supported. | Met |
| 5 | Registry access, reproducible inputs, artifact verification and stack use documented; API artifacts regenerated, `api-check` passes | [`beta-image-001.md`](../../beta-image-001.md), [`installation.md`](../../installation.md), [release preflight](../../security/beta-distribution-001/release-publication-preflight.md). `make api-check` is part of every canonical FULL, including #158's. | Met |
| 6 | Independent infrastructure QA and exact-tree canonical FULL before operator delivery; publication separately authorized | Original delivery #142 (head `c6d5b96`) went through the receipt-gated `feature-deliver`. Its body sentence "Local canonical verification completed before this reviewed commit" is that command's template, emitted only after `feature-tree-fingerprint.py verify` accepted a receipt for the exact head tree and the policy plan, which was FULL because the change touched `.github/` and `Makefile`. That receipt is local and not committed. No committed independent QA covers `c6d5b96`: the last verdict is CONDITIONAL PASS on `d661200`, one commit earlier ([final reliability](../../beta-image-001-final-reliability.md)). The publication path actually used was redelivered by #158 (head `484d2d1`): its body records independent QA of the frozen candidate and canonical `make feature-verify` on `484d2d1`. Publication was a separate protected dispatch with environment approval (run 42520884360). | Gap for #142 (QA); remediated by #158, needs operator acceptance |
| — | Title target `v0.1.0-beta.1` | beta.1 to beta.4 are tags without a GitHub Release ([`CHANGELOG.md`](../../../CHANGELOG.md)). The only published paired release is `v0.1.0-beta.5`, published 2026-11-08 from `4c845b1`. | Superseded, needs operator acceptance |

## beta-postgres-repro-001

| # | Criterion (short) | Evidence | Verdict |
| --- | --- | --- | --- |
| 1 | Local command and non-publishing ubuntu-24.04 workflow share the protected publisher and pinned inputs with owned registries | [`beta-release-rehearsal.yml`](../../../.github/workflows/beta-release-rehearsal.yml) (`ubuntu-24.04`, `packages: read`) and `scripts/rehearse-beta-release.py`, delivered in #155; [rehearsal contract](../../security/beta-distribution-001/beta-release-rehearsal.md). | Met |
| 2 | Two independent clean PostgreSQL builds match the pins; descriptors retained | Hosted runs 42482904548 (`c65b725`) and 42485751305 (`8b006b1`): both builds matched index `4edc0790…` and platform `55b1969a…`, all 13 layers equal, evidence uploaded as an artifact. Both runs failed later at registry-evidence stages, which #155 then fixed ([progress](../../progress.md), "BETA-RELEASE-REHEARSAL — reproducibility hotfix candidate"). | Met |
| 3 | Builds, digest pull, manifest, scans, SBOM, artifact smoke, asset inventory and local promotion all pass | Hosted rehearsal 42494565435 on #155's final head `7e73762` ran 15:23–15:26Z and succeeded, before the 15:48Z merge. Later full passes: 42517706427 (#158 head `484d2d1`) and 44042306847 (`main` `b088a94`). | Met |
| 4 | GHCR checked read-only; GHCR writes, attestations and Release API finalization labelled remote-only and untested | The rehearsal contract separates the read-only GHCR check from protected-only stages and records attestations and Release API operations as not run. | Met |
| 5 | Publication needs exact-main CI with forced migration and exact-main hosted rehearsal; asset allowlist; no automatic resume after partial promotion | [Release preflight](../../security/beta-distribution-001/release-publication-preflight.md) (#158): exact seven-file inventory, exact-SHA main CI with a forced migration cycle, main-push rehearsal, and operator review after a partial promotion; the publisher refuses a reused checkpoint. | Met |
| 6 | beta.3 first differing OCI byte established or bounded; no digest changed | Established: layer 12 (`COPY LICENSE`) and `rootfs.diff_ids[11]` differed because the checkout mode was 0644, not 0664. Forcing each mode reproduced each digest; the build now normalizes the mode. No pin changed. | Met |
| 7 | Focused regressions and canonical FULL on the exact final tree, with a valid receipt, before protected delivery | #155's body names FULL on `c12af84`. Its head `7e73762` has five later commits (five files, +322/−77: the release scripts, tests, rehearsal document and `docs/progress.md`), and no FULL on `7e73762` is recorded. Mitigation: hosted rehearsal passed on `7e73762`, and #158's FULL on `484d2d1` covers a tree that contains those commits. | Gap; mitigated, needs operator acceptance |

## Risk carried forward

BETA-SECURITY-001 stays `in_progress`; its PostgreSQL scan findings and approvals are recorded as
open ([feature reconciliation](../feature-reconciliation-v1.md)). The published beta.5 PostgreSQL
image is affected by them. This record covers the distribution pipeline, not that risk.

## Recommendations requiring operator acceptance

Nothing below is applied.

1. **Supersession of `v0.1.0-beta.1` by `v0.1.0-beta.5`** for BETA-IMAGE-001: accept beta.5 as
   the first paired immutable release that met every stage.
2. **BETA-IMAGE-001 #6**: accept #158's independent QA and exact-head FULL, followed by the
   separately approved protected run, as satisfying the criterion for the pipeline that published.
3. **beta-postgres-repro-001 #7**: accept the passing hosted rehearsal on `7e73762` and #158's
   later FULL as covering the commits after `c12af84`, or require a recorded exception.
4. If 1 and 2 are accepted, BETA-IMAGE-001 may move to `implemented`. If 3 is accepted,
   beta-postgres-repro-001 may move to `implemented`. Neither becomes `verified`.
5. Either move would remove that entry from the release-candidate blockers, 8 to 6 if both move.
   RELEASE-001 and BETA-ACCEPTANCE-001 still need their own decisions; CUTTING-001,
   UI-SYSTEM-001, BETA-SECURITY-001 and BETA-DATA-001 stay open.

## Effect of this source

- Adds CERT-05 (`tooling`) to `docs/features.json` and `docs/release/scope-v1.json`, and records
  CERT-05 and the WF-07 workflow enabler in [`scope-v1.md`](../scope-v1.md).
- No other entry, criterion, class or checker changes. The release-candidate blockers stay the
  same eight.
