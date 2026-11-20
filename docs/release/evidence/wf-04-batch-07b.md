# WF-04 Batch 07b integration evidence

Pinned main is `0784ce63c1e035343cc09a0eb53193e9dcad2c00`, which adds the
BETA-SECURITY-001 frontend nginx 1.30.7 base (PR #198) to the original Batch 07 base
`fdc75e83fa8818cab791ed82cbba65f4f97db7ae`. The integration writer is
`claude-batch07b-integration` with claim `66afff7dd108`. The
[manifest](batches/batch-07b.json) records the exact commits, bases, original
source claims, reviewers and merge order.

Candidate 07b supersedes `ci/batch-07` at `af8935146e5aabcdfb15de6761e1e65053c0321f`
(PR #197). The changed base requires a new reviewed candidate. The five source
tips, their approvals and the merge order are unchanged. The evidence recorded for
`af89351` (canonical FULL, candidate review, external combined checks, hosted
rehearsal) is historical and certifies nothing about this candidate.

| Source | Frozen tip | Source approval provenance |
| --- | --- | --- |
| FRONTEND-002 | `08c0bb353d98ac752a5828fe8f207fe44ad789cd` | Opus technical PASS, `BATCH07_AUTH_PRIVATE_ISSUANCE_INDEPENDENT_QA`. SOL security PASS, `BATCH07_AUTH_PRIVATE_ISSUANCE_FINAL_APPROVAL`. Both reports are archived. |
| UI-SYSTEM-001 | `39080cb84145e3e70b4ae38179169fb7af36d7ba` | Argon PASS, `BATCH07_MOBILE_UX_INDEPENDENT_QA`, archived. The original `c555baa` base is recorded in the manifest. |
| TEST-DATA-002 | `81848389b93204fb13dabf020aa5061c4d869072` | Opus PASS, `BATCH07_GOLDEN_COMPREHENSIVE_PIN_INDEPENDENT_QA`, archived. Opus reproduced the diagnosis on the base and attributed the exact-tip integration run to the source writer. |
| PERF-001 | `143bbc8ad69d07a47551f01976017c6218ff9a3b` | Sonnet PASS, `BATCH07_PERFORMANCE_HARNESS_FINAL_INDEPENDENT_QA`, archived. The preliminary performance rehearsal retains its original provenance. |
| CERT-01 | `00ec17c5a69ec4b2617b3237ab7355f8426d0386` | Sonnet's prior comprehensive review is retained in the review record. SOL PASS on the three-file RC-SEQ-01 correction, `BATCH07_FUNCTIONAL_UX_CERTIFICATION_FINAL_APPROVAL`, was supplied by the orchestrator for tree `17c4acf6eb8eb5a1bc8084e4388ad9b4820a23cb`. The original final SOL artifact awaits archival. |

The five source merges replay the original order. The only conflict is the additive
`docs/progress.md` append on the base, which preparation resolves by keeping both
sections. Apart from `docs/progress.md`, the merged tree differs from the original
`80968c6` merge result only by the PR #198 diff. The
Orders and Cuttings test suites retain the AUTH harness and add the Mobile UX
directory heading, layout and preview assertions. Both provenance milestones
remain in [progress](../../progress.md).

The only source delta since `af89351` is the frontend runtime base and its evidence.
Combined checks are recorded externally against the exact candidate identity. They
include the dedicated Golden COMPREHENSIVE check and the strict performance rehearsal,
whose chunk-recovery stage exercises the production nginx fallback on the new base,
plus the exact-commit independent review and a fresh canonical FULL. The focused
frontend regressions are Node/Vitest suites with no nginx dependency, and FULL
repeats them. The three deferred Chromium cases passed on `af89351` and are not
repeated: they cover session restoration and mobile layout, the application code
and `nginx.conf` behind them are unchanged, and the hosted rehearsal smoke covers
the new runtime base.

The CERT-01 approval covers documentation. The eight release-candidate blockers
and RC-SEQ-01 remain open, and formal G-CORE, G-UX and G-PERF acceptance remains
pending. Feature statuses, acceptance requirements and release membership
are unchanged.
