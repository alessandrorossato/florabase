# Wave 2 — independent QA intake

## Authorization and frozen scope

On 29 October 2026 the operator reported all six scenarios in the [primary handoff](README.md)
**PASSED** and approved local commit, independent QA, canonical FULL and later protected delivery.
The current task ends at the local commit. It does not push, create a PR, merge or finish the feature.
The operator explicitly authorized this implementation commit before QA/FULL. Do not reopen approved
design decisions or ask for another UAT unless an objective blocking defect requires it.

## Source identity

- Repository: `alessandrorossato/florabase`.
- Branch: `feat/ui-system-v1-wave2`.
- Worktree: `/home/alessandro/.codex/worktrees/bf7a/florabase`.
- Approved implementation base: `afcfbab334622d64cca2cdb2ea4c8f6a51ad957f` (Wave 1 #129).
- This document belongs to the local feature commit. Obtain its immutable commit and tree identities
  with `git log -1 --format='%H %T' -- docs/design/ui-system-v1/wave2/independent-qa.md`; the final
  operator report also supplies both full hashes. Confirm a clean worktree at intake.
- Before these acceptance/QA documentation updates, the complete candidate fingerprint matched the
  retained UAT snapshot exactly:
  `dc0c69259ad891bdf536cf82c5960e3f1726f4b5d61b6baf22e7b4ed533fd6b9`.
  No product source, tests or CSS changed during finalization.

## Current main and mandatory reconciliation

Freshly fetched `origin/main` is `5b2e2a1fadffa30de4e9129fe01750c71efb6d6c`, WCVP-VERSION-001
PR #130. It is one commit beyond the approved base and is not an ancestor of this feature candidate.
No reconciliation is performed in this local-commit task; primary `main` is not moved.

The only overlapping paths are `docs/features.json` and `docs/progress.md`. PR #130 inserts the WCVP
backlog entry near enrichment and prepends its progress milestone; Wave 2 appends its backlog entry
and progress milestones. Retain both sets of evidence/statuses. WCVP also has an equivalent JSON
Unicode escape change in an existing Maps acceptance criterion. No Activity, Sourcing, shared
composition or new Wave 2 stylesheet path overlaps. There is no Wave 2 API/schema/dependency/migration
change; #130's generated API updates belong to WCVP and must remain intact when reconciling.

QA must fetch again and deliberately reconcile current `origin/main` in this feature worktree before
canonical verification, preserving the approved UI and all incoming WCVP changes. Do not modify a
WCVP implementation worktree or primary checkout. The canonical helper refuses a feature that does
not contain fetched `origin/main`. Historical Wave 2 evidence predates this integration and does not
claim verification of the reconciled tree.

## Included and excluded content

Included: shared Activity composition/filter adapter; Journal, History and Schedule adoption;
Suppliers/Orders shared List/Gallery, explicit Preview/Details/Edit, responsive overlay previews,
selection/focus return; scoped Sourcing CSS; the three affected regression files; Wave 2 backlog,
UI contract, progress and review/QA documentation. Calendar navigation, chronology, Saved Views,
purchase/SeedLot reconciliation and existing domain workflows remain capability-owned.

Excluded: Review credentials and access files, synthetic database/media contents, screenshots and
contact sheets, local evidence HTML/JSON/logs/patches, temporary scripts, generated `frontend/dist`,
`.pnpm-store`, dependency caches, `.env` and all unrelated artifacts. No fixture implementation or
generated API artifact changed in Wave 2. Reuse the existing populated Review without reseeding,
resetting, rebuilding or stopping foreign environments as part of intake.

## Retained evidence and checks

- Operator UAT: six of six scenarios PASSED, reported directly by the operator.
- Untouched-base screen baseline: 97 tests passed in five files.
- Final focused regression boundary: 144 tests passed in 12 files, including four new Sourcing cases.
- Complete frontend lint (zero warnings), strict TypeScript, Prettier, production build and API drift:
  passed on the approved implementation. No product check was rerun solely for status-document edits.
- Current finalization checks: 120-feature graph valid; working/staged diff whitespace; approved
  candidate fingerprint match; all 154 retained capture SHA-256 digests revalidated.
- Visual evidence: 144 primary combinations across eight presentation states, three measured CSS
  widths (1440/1024/390), six themes, plus ten contextual captures. Raster dimensions remain separate.
- Review: <http://localhost:15174/#/suppliers>. Gallery: <http://localhost:15285/>. These existing
  processes are retained, not restarted. Availability is live process state, not a commit property.
- Evidence files remain outside Git under
  `/home/alessandro/.codex/visualizations/2026/10/29/01a1892e-29ef-7fb2-815a-684b0553e4d0/wave2-evidence/`.
  `source.json` describes the earlier approved dirty candidate, not the new commit or reconciled tree.
  Local credentials are outside the served evidence directory; do not copy them into QA reports/Git.

No canonical FULL receipt is claimed. The earlier broad `make check` attempt stopped at transient
implementation formatting and is not a FULL pass. Its subsequent focused/static passes are the
explicit evidence above.

## Independent QA sequence

1. Confirm the feature commit/tree, clean source, authorization and complete diff against its base.
2. Fetch and reconcile current main, preserving both documentation streams and generated WCVP contracts.
3. Independently review correctness/accessibility and domain preservation. Focus on presentation-only
   query/history/pagination, Saved Views exclusions, remounted preview/editor focus, filter semantics,
   calendar period/day behavior and independent Order/SeedLot relationships. Fix ordinary objective
   defects and run focused regressions only where new risk or a fix justifies them. Scope stays frozen.
4. Record QA evidence, freeze source **and index**, then run **one** `make feature-verify`. CI-004 selects
   FULL for `frontend/src/components/ActivityPage.tsx` and `frontend/src/styles/sourcing-directory.css`.
   FULL must include exhaustive quality/workflow/integration, both production builds and the real
   disposable base → head → base → head migration cycle, even with no Wave 2 migration.
   Do not chain a duplicate `verify-full` or manually repeat covered stages.
5. Only after the reconciled final tree passes, record the receipt and feature status honestly,
   commit any QA corrections/evidence, and validate receipt compatibility with the committed tree.
   Protected delivery is a later explicit boundary; this handoff authorizes no push or merge.

Physical devices/touch/soft keyboards, assistive technology, actual browser zoom, forced colors,
live failure injection and large-scale performance remain historical measurement limits. Operator
UAT acceptance is complete; these limits do not invent another acceptance or design gate.

`FLORABASE_UI_SYSTEM_V1_WAVE2_COMMITTED_READY_FOR_INDEPENDENT_QA`
