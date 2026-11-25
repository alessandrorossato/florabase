# DOC-04 — End-user guide

Status: `in_progress`. The guide and the trial template exist; DOC-04 is met only after an
unassisted non-developer trial on the release candidate, recorded from
[`doc-04-trial-template.md`](doc-04-trial-template.md).

## What exists

- Ten-page guide under [`docs/user-guide/`](../../user-guide/README.md), written from `ddf5a14`
  and updated for `v0.1.0-beta.9` after merging `origin/main` `b632c5c`.
- UI labels copied from `frontend/src` (non-test); labels built at run time carry a
  `TODO(DOC-04 verify)` comment (11), and planned screenshots a `TODO(DOC-04 screenshot)` comment
  (28). No `TODO(DOC-04 after batch 12)` markers remain.
- Writer handoff with the G-CORE coverage map, marker inventory and label provenance:
  [`docs/archive/DOC-04/handoff.md`](../../archive/DOC-04/handoff.md).

## Reviews

| Tree | Reviewer | Result |
| --- | --- | --- |
| `bb77239` | Claude, independent of the writer | FIX REQUIRED (Cuttings labels and four smaller label defects) |
| `408bad0` | Same reviewer | PASS |
| beta.9 update | Independent reviewer, pending | — |

## Acceptance mapping

| Criterion | Evidence |
| --- | --- |
| A non-developer completes G-CORE 1–9 with only the guide | Pending: unassisted trial on the release candidate |
| Trial record names role, date, candidate commit, per-step result and stopping points | [`doc-04-trial-template.md`](doc-04-trial-template.md) (template only) |
| All nine steps completed; every stopping point fixed or dispositioned | Pending: trial |

## Open before `verified`

- Screenshots from Golden DEV on the frozen candidate (replace the screenshot markers).
- Resolve or keep the verify markers after checking the running candidate.
- Document batch 13 and batch 14 features once they are on `main` (list in the handoff § 7).
- Run and record the unassisted trial.
