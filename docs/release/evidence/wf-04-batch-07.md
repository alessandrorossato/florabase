# WF-04 Batch 07 integration evidence

Pinned main is `fdc75e83fa8818cab791ed82cbba65f4f97db7ae`. The integration
writer is `codex-batch07-integration` with claim `133d5925280f`. The
[manifest](batches/batch-07.json) records the exact commits, bases, original
source claims, reviewers and merge order.

| Source | Frozen tip | Source approval provenance |
| --- | --- | --- |
| FRONTEND-002 | `08c0bb353d98ac752a5828fe8f207fe44ad789cd` | Opus technical PASS, `BATCH07_AUTH_PRIVATE_ISSUANCE_INDEPENDENT_QA`. SOL security PASS, `BATCH07_AUTH_PRIVATE_ISSUANCE_FINAL_APPROVAL`. Both reports are archived. |
| UI-SYSTEM-001 | `39080cb84145e3e70b4ae38179169fb7af36d7ba` | Argon PASS, `BATCH07_MOBILE_UX_INDEPENDENT_QA`, archived. The original `c555baa` base is recorded in the manifest. |
| TEST-DATA-002 | `81848389b93204fb13dabf020aa5061c4d869072` | Opus PASS, `BATCH07_GOLDEN_COMPREHENSIVE_PIN_INDEPENDENT_QA`, archived. Opus reproduced the diagnosis on the base and attributed the exact-tip integration run to the source writer. |
| PERF-001 | `143bbc8ad69d07a47551f01976017c6218ff9a3b` | Sonnet PASS, `BATCH07_PERFORMANCE_HARNESS_FINAL_INDEPENDENT_QA`, archived. The preliminary performance rehearsal retains its original provenance. |
| CERT-01 | `00ec17c5a69ec4b2617b3237ab7355f8426d0386` | Sonnet's prior comprehensive review is retained in the review record. SOL PASS on the three-file RC-SEQ-01 correction, `BATCH07_FUNCTIONAL_UX_CERTIFICATION_FINAL_APPROVAL`, was supplied by the orchestrator for tree `17c4acf6eb8eb5a1bc8084e4388ad9b4820a23cb`. The original final SOL artifact awaits archival. |

All five source merges are reproducible without conflict resolution. The
Orders and Cuttings test suites retain the AUTH harness and add the Mobile UX
directory heading, layout and preview assertions. Both provenance milestones
remain in [progress](../../progress.md).

Combined checks are recorded externally against the exact candidate identity.
They include the focused frontend regressions, three deferred Chromium cases,
the dedicated Golden COMPREHENSIVE check and strict performance rehearsal.
Independent candidate review and the fresh canonical FULL follow separately.

The CERT-01 approval covers documentation. The eight release-candidate blockers
and RC-SEQ-01 remain open, and formal G-CORE, G-UX and G-PERF acceptance remains
pending. Feature statuses, acceptance requirements and release membership
are unchanged.
