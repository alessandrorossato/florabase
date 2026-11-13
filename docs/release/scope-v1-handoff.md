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

| File | Statement | Fact at the baseline |
| --- | --- | --- |
| `docs/architecture.md` "Deliberately deferred" | Supplier media, saved views, bulk operations, PWA installability and taxonomy reconciliation are backlog | All are on `main` |
| `docs/architecture.md` "Implemented domain modules" | Omits Orders, Schedule, Saved Views, Taxonomy, Explore, Cuttings, Measurements, Import/Export | All have routers in `api/router.py` |
| `docs/development.md` | "Version 2 receipts"; "Codex-managed feature worktree"; "`quality` runs `make check`" | Receipts are version 3; the workflow is provider-neutral; the job runs `scripts/ci-verify.py quality` |
| `docs/security.md` table | "nginx provides the separate source-address limit" | The bundled `nginx.conf` has no rate limit; the operator's proxy owns it |
| `docs/beta-foundation-001.md`, BETA-* entries | Written for `v0.1.0-beta.1` | Tags reach beta.5; sources say beta.6 |
| `features.json` RELEASE-001 | "first distributable Florabase 0.1.0 release"; "application version 0.1.0" | Superseded by decision 1; re-scope with the schema follow-up |
| `features.json` UI-REDESIGN-EXPLORATION-001 description | "experimental only" | Delivered as the production shell |

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

## Outstanding questions for the operator

1. **UX-DATE-001 D1.** Keep (a) nothing selected, or switch to (b) Today preselected? The
   alternatives and their source are in `scope-v1.md`.
2. **Promotion candidates.** Record operator acceptance for GERMINATION-001 (visual review) and
   MULTIBRANCH-UAT-001 (operator UAT), or leave them for the release certification?
3. **TAXONOMY-001.** Fix the two concurrency findings, or record them as accepted risk? It stays
   `verified` meanwhile.
4. **DASHBOARD-001.** Its verified layout was reversed by UX-TODAY-001. Re-verify under
   UX-TODAY-001, or annotate the entry?
5. **UI-SYSTEM-001.** Close at the delivered state, or keep open?
6. **Historical records.** May RELEASE-VISUAL-AUDIT-001, ACTIVITY-CONCEPT-001 and
   BETA-FOUNDATION-001 be closed without certification, as the matrix proposes?
7. **Certification method.** 38 entries are "PRE-1.0 certify". Certify each against its own
   criteria on the release candidate, or accept the G-CORE and G-UX records as their evidence
   where the criteria overlap?
8. **Care kinds.** Which identifier carries the watering and feeding kinds (decision 5)?
