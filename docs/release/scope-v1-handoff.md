# RELEASE-SCOPE-001 handoff

Documentation-only increment on `docs/release-scope-v1`, base
`947d77fc8bd2a757cdf49e28ec2e0f85b0374f1b`, writer `claude-scope-v1`.

## Delivered

- [scope-v1.md](scope-v1.md): the release contract with the eight approved decisions, gates, work
  required before the release, exclusions and the scope-change procedure.
- [feature-reconciliation-v1.md](feature-reconciliation-v1.md): all 156 baseline entries with
  status, proposed release target, existing evidence and gap.
- `features.json`: three status changes (below) and the entry for this increment.
- `product-roadmap.md`: reduced to a pointer, the version line and the post-1.0 themes. The
  previous text is preserved, with only relative links adjusted, in
  [history/product-roadmap-2026-11-11.md](history/product-roadmap-2026-11-11.md).
- `README.md`: release line, official installation path, delivered capabilities and the misplaced
  Harvest paragraph.
- [release-target-schema-followup.md](release-target-schema-followup.md): specification for the
  later `release_target` schema and checker change. No script was modified.
- [acceptance-v1.md](acceptance-v1.md) and [page-inventory-v1.md](page-inventory-v1.md), added by
  the corrective commit described below.

## Status changes and their evidence

| ID | Change | Evidence |
| --- | --- | --- |
| ATTACHMENT-004 | `implemented` → `verified` | `progress.md` 2026-09-26 and 2026-09-27 entries: canonical gate passed, independent QA with a concurrency regression, operator manual review passed; `attachment-004-review.md` |
| FABLE-FIX-CUTTINGS | `in_progress` → `implemented` | On `main` in `947d77f` (#177); batch browser QA in the "UX closeout batch" entry |
| UI-REDESIGN-EXPLORATION-001 | `in_progress` → `implemented` | Workbench shell on `main` since `fec0398` (#147) |

No other status was changed. GERMINATION-001 and MULTIBRANCH-UAT-001 are named as promotion
candidates and left as they were.

## Not done here, and why

- **`release_target` in `features.json`.** Deferred to the schema follow-up; the targets are
  proposed in the reconciliation matrix only.
- **CUTTING-001 status and `docs/cuttings.md`.** An active writer (`codex-cutting-31a6`, branch
  `feat/cutting-001-implementation`) holds uncommitted changes to `docs/cuttings.md`,
  `docs/progress.md` and lineage code. CUTTING-001 was left `in_progress` and no Cuttings
  document was edited.
- **`docs/progress.md`.** One entry was added at the top of the file. The active Cuttings writer
  also has an uncommitted change to this file; a textual conflict is possible when that work is
  integrated and is resolved by keeping both entries.
- **Independent review.** Not performed by the writer. The frozen commit awaits a reviewer in a
  separate read-only checkout.
- **Draft pull request.** Not opened. `AGENTS.md` reserves push and pull-request creation for the
  operator's `make feature-deliver`.

## Remaining documentation work

### DOC-01 — one official installation guide

- `portable-installation.md` becomes the primary guide: add a reverse-proxy example, a
  troubleshooting section and the host notes (Synology, VPS) that exist only in `installation.md`.
- Label `deployment.md` as development-only and `installation.md` as best-effort at the top of
  each file. The README already says so.
- `backup-restore.md` describes the source-build procedure; the official path's backup is inside
  `portable-installation.md`. Decide which page owns backup and restore for the official path.
- `portable-installation.md` and `installation.md` name `v0.1.0-beta.6`, which is not tagged or
  published (latest tag and GitHub release: `v0.1.0-beta.5`). Left unchanged: the statement
  is conditional ("once it is published") and the release owner should correct it at publication.

### DOC-03 — stale statements still present

The closed list of statements, with the fact for each, is in the
[task acceptance criteria](acceptance-v1.md#doc-03-statement-list).

### DOC-04 — end-user guide

Nothing exists. Proposed pages: concepts; first hour; daily use; harvest and seed saving;
cuttings; finding things and labels; your data (CSV, backup, restore, upgrade); optional
reference data; troubleshooting. Write against the frozen candidate with screenshots from Golden
DEV.

### DOC-05 — changelog, versioning policy, security contact

- No `CHANGELOG` exists; release notes live only in GitHub release bodies.
- The version line is now stated in `product-roadmap.md` and `scope-v1.md`; a short standalone
  versioning page is still wanted.
- `SECURITY.md` publishes no private reporting address and no supported-versions statement.

## QA remediation after `c7440bf`

The independent review of `c7440bf` returned `SCOPE_QA_FAIL`. The corrective commit on top of it:

- Restores the scope classification: mandatory blockers, required workflow enablers, optional
  improvements, POST-1.0 deferrals and non-deliverable classes. WF-08 is deferred. ENG-02, FN-02,
  FN-04 and DOC-06 are optional.
- Adds [acceptance-v1.md](acceptance-v1.md) with measurable, repository-accessible criteria for
  every task, and [page-inventory-v1.md](page-inventory-v1.md) as the frozen input of G-UX.
- Rewrites the gates so that no mandatory gate requires an optional task; each conditional
  clause states what applies on deferral.
- Makes internal foundation an explicit class with a certification policy (BOTANICAL-MATCH-1A).
- Recomputes the verified-on-unverified dependency count from the graph: 12, including
  ATTACHMENT-004 on ATTACHMENT-003 and UX-006.
- Tracks the legacy beta references of RELEASE-001, BETA-IMAGE-001 and BETA-ACCEPTANCE-001
  without rewriting them, names `v0.1.0-beta.5` as the current upgrade baseline, excludes
  GOLDEN-REFERENCE-001 explicitly, and states that the beta's seven-day soak proposal does not
  affect the 14-day release-candidate soak.
- Records the operator's D1 decision (Today preselected) as mandatory task FN-05 for the
  functional batch. No interface code was changed.

The full text of the review report was not available in the repository or the review folders
when this was written; the corrections follow the findings as relayed by the orchestrator.

## Outstanding questions for the operator

1. **Optional class of ENG-03, ENG-04, ENG-06 and FN-07.** The operator ruled on ENG-02, FN-02,
   FN-04 and DOC-06. These four are classed optional on the audit's recommendation; confirm.
2. **Promotion candidates.** Record operator acceptance for GERMINATION-001 (visual review) and
   MULTIBRANCH-UAT-001 (operator UAT), or leave them for the release certification?
3. **ENG-05.** Which branch: the two-session regression, or a documented risk disposition?
   TAXONOMY-001 stays `verified` meanwhile.
4. **DASHBOARD-001.** Its verified layout was reversed by UX-TODAY-001. Re-verify under
   UX-TODAY-001, or annotate the entry?
5. **UI-SYSTEM-001.** Close at the delivered state, or keep open?
6. **Historical records.** May RELEASE-VISUAL-AUDIT-001, ACTIVITY-CONCEPT-001 and
   BETA-FOUNDATION-001 be closed without certification, as the matrix proposes?
7. **Care kinds.** Which identifier carries the watering and feeding kinds (decision 5)?
8. **Machine-readable scope.** The workflow planning review suggests a small
   `docs/release/scope-v1.json` membership list instead of a per-entry field. Decide before the
   schema follow-up is implemented.
