# WF-04 Batch 13 integration evidence

The Batch 13 integration branch is `ci/batch-13`, based on pinned `origin/main` at
`b632c5c734fdab55e62230cdee99938ae34ece7e` (PR #226). The integration writer is `claude-batch-13`.
The [manifest](batches/batch-13.json) records the exact source tips, merge commits, additive
`docs/progress.md` resolutions and post-merge reconciliations.

## Source provenance and exact-tip readiness

Each source was frozen in its own clean, claimed worktree with no pending handoff and reviewed
independently by Claude before integration:

| ID | Branch | Frozen tip | Writer | Source QA | Committed evidence |
| --- | --- | --- | --- | --- | --- |
| DOCS-004 | `docs/docs-004-batch12-followups` | `40e204bf058d16261f55189f8b301e02bd941632` | `claude-batch13` | `claude-docs004-source-qa` | [`docs-004.md`](docs-004.md) |
| PROPAGATION-BATCH-001 | `feat/propagation-batch-001` | `7022f8e504d670eed300840d1a98ad897aaf28ff` | `neon-propagation-batch-001` | `claude-propagation-batch001-source-qa` | [`propagation-batch-001.md`](propagation-batch-001.md) |
| CARE-BULK-001 (with FN-03) | `feat/care-bulk-001` | `3490d18ff3fd8c9b4f86af3625ed8611e41d646f` | `neon` | `claude-care-bulk001-source-qa` | [`care-bulk-001.md`](care-bulk-001.md) |
| UX-SORT-001 | `feat/fn-05-directory-sort` | `760283a6ed05f9b65111b5c25720dfd6bb13c02c` | `claude-batch13` | `claude-ux-sort001-source-qa` | [`ux-sort-001.md`](ux-sort-001.md) |
| MEDIA-FETCH-001 | `fix/media-fetch-001` | `d2321c17814a1c98159c40e08b441fb2ee5c79da` | `claude-media-fetch` | `claude-media-fetch001-source-qa` | [`media-fetch-001.md`](media-fetch-001.md) |

PROPAGATION-BATCH-001 is based on the older `main` `1a78476`; the planner accepted it without a
rebase and its frozen tip remains an ancestor of the integration head.

## Integration conflict and cross-branch checks

- **Pre-check:** `git merge-tree --write-tree` chained over the tips in merge order reported
  conflicts only in `docs/progress.md` (sources 2 to 5). `backend/openapi.json`,
  `frontend/src/api/schema.d.ts`, `docs/features.json` and `docs/release/scope-v1.json` auto-merged.
- **Conflict resolution:** `feature-batch-prepare` resolved `docs/progress.md` additively. Because
  PROPAGATION-BATCH-001 predates the MOBILE-002 and beta.9 milestones on `main`, its milestone
  landed below them; the reconciliation moves it back into merge order (no line added or removed
  other than the Batch 13 milestone).
- **Shared source files:** PROPAGATION-BATCH-001 and CARE-BULK-001 both touch
  `backend/src/florabase/plants/schemas.py` and `plants/service.py`; UX-SORT-001 and CARE-BULK-001
  both touch `backend/src/florabase/saved_views/state.py` and `frontend/src/saved-views/state.ts`.
  All merged without textual conflict and are covered by `make check` on the integrated tree.
- **Migration:** CARE-BULK-001 adds `20261125_0049_event_care_kinds` on `20261123_0048`; it is the
  single Alembic head of the integrated tree. Delivery therefore reports a migration and the
  operator runs `make dev-upgrade` after finish.
- **Generated API:** `make api-generate` on the integrated tree produced no drift.
- **Reconciliation:** prepended the Batch 13 integration milestone to
  [`docs/progress.md`](../../progress.md), restored merge order there and recorded this
  provenance document.
- **Summary:** the request summary was shortened to the 72-character limit as
  "Tray potting, bulk watering and feeding, directory sort, Wikipedia fix".
- **Proposed release classes (for operator confirmation):** `DOCS-004`, `PROPAGATION-BATCH-001`,
  `CARE-BULK-001`, `FN-03`, `UX-SORT-001`, `MEDIA-FETCH-001` (`best-effort`), all `implemented`.
