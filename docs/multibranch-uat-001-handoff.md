# MULTIBRANCH-UAT-001 handoff — parallel per-worktree UAT instances

8 November 2026 · `feat/multibranch-uat-001` · writer `claude-code-mbuat` · base `4c845b1`.
Operator contract: [development workflow](development-workflow.md#uat-instances-parallel-per-worktree).

## Scope decision

The brief combined two capabilities with different runtimes. This increment delivers the first;
the second is a separate planned backlog entry.

| Capability | Runtime | This branch |
| --- | --- | --- |
| Independent UAT per feature worktree, golden SMOKE/COMPREHENSIVE data | Dev source runtime, same as UAT Preview | **Implemented** (MULTIBRANCH-UAT-001) |
| TUXEDO golden reference on the NAS's approved image digest pair | Image-only beta stack and `florabasectl` | **Planned** (GOLDEN-REFERENCE-001) |

The reference environment cannot reuse dev-source instances: it needs production images, the
controller's manifest verification, its own project (the controller fixes `florabase-prod`) and a
golden target guard for that identity. Building it here would have touched production-adjacent code
without its own review. Nothing in this branch changes production, the beta stack, publication or
release identities.

## TEST-DATA-001/002: evidence versus missing acceptance

| Feature | Status | Existing evidence (unchanged) | Still missing |
| --- | --- | --- | --- |
| TEST-DATA-001 | `in_progress` | SMOKE generation, identical digest across hash seeds/timezones/stacks, baseline `70a1b1ae…f967`, atomic failure, locks, damage detection, persistent targets refused | Ten planned scenarios, STRESS, independent QA delta, canonical FULL |
| TEST-DATA-002 | `implemented` | COMPREHENSIVE 3,183 nodes, baseline `cf423707…3a11`, two-stack reproduction | Independent delta QA, `import-export-roundtrip`, edit paths, CI schedule decision, canonical FULL |

This branch changes the golden runtime in two narrow places and adds tests for both:

1. `uat_instance_target` accepts exactly one persistent target (mode `uat-instance`, a
   `florabase-uat-branch-*` project, development and not disposable, `db:5432/golden_uat` as both
   database and user, standard media root). The disposable copy lifecycle, Review, Sourcing, the
   singleton UAT and DEV remain refused.
2. `table_counts` skips the session tables the digest already excluded. Generated copies must
   still have empty session tables (existing test); a sign-in no longer makes a copy invalid.

It settles TEST-DATA-002 decision 2 for instances only. Decisions 1, 3 and 4 stay open: there is no
snapshot reuse, the synthetic WFO/WCVP indexes are not provisioned for the running app, and the pinned anchor date is kept.
Neither TEST-DATA feature changes status here.

## Design summary

- `scripts/uat_instance.py` subclasses `UATPreview` and inherits every identity guard. The singleton
  was refactored only to read its project pattern, role label, workflow mode, database and
  confirmation variable names from class attributes; its behaviour and messages are unchanged.
- The allocation record is the immutable labels on the instance's own volumes. Port pool
  15180–15183 (four slots). Address-pool probe by exact name in `finally`.
- Capacity: `up`/`seed`/`reset` take `verification-full` with canonical FULL. Lock files now
  name the holder's purpose.
- Retirement: the inherited proven path plus exact image tags and proven one-off containers.

## Independent infrastructure QA

A read-only reviewer reported 3 P1, 4 P2 and 10 P3 findings. All P1 and P2 are fixed with regressions:

| Finding | Resolution |
| --- | --- |
| P1 Python 3.14-only `except A, B:` (ruff rewrite) would fail CI's 3.12 | Rewritten; a 3.12 `ast` parse test covers the three host-run modules |
| P1 lock test failed on detached checkouts (CI) | Test pins the repository identity |
| P1 `reset PROFILE=…` was impossible (refused at construction) | Mismatch refused only by `up`/`seed`; reset applies it after exact confirmation; tested |
| P2 capacity counted out-of-pool (smoke/leaked) instances | Only claims inside the pool count; tested |
| P2 probe network could leak | Removed by exact name in `finally` |
| P2 smoke ran heavy work outside the capacity lock | Smoke holds `verification-full` for its whole body |
| P2 interrupted seed one-off blocked remove/reset | Proven own one-offs removed after exact confirmation, all proven before any removal; tested |
| P3 context checked after allocation | `up` checks the source before any Docker probe |
| P3 validate exit 1 ambiguity, env-var trust, doc wording | Documented |

Accepted P3 limitations, documented: the record is read before the lock is taken (allocation re-reads
it); there are transient `docker inspect` races; a remove interrupted after its volumes are gone
leaves the image tags; some inherited messages name `uat-preview` commands; a detached owner whose
instance was never seeded can only remove it; there are extra git subprocesses per command.

## Checks

| Check | Result |
| --- | --- |
| `make test-uat-preview` (UAT 19, source 15, instance 14) | Pass |
| `test-workflow-resources`, `test-environment-workflow` (35), `test-agent-workflow` (63, 3 skipped) | Pass |
| `make golden-dataset-check` incl. the two new golden tests | 34 passed in 292 s |
| `scripts/check-features.py` | 144 features valid |
| Canonical `make feature-verify` (FULL, 17 stages) | Pass in 933 s; integration 809 passed, 29 skipped; rerun after this record |
| `make smoke-uat-instance` (run 6, after the QA fixes) | **Pass** in 195 s; zero residual containers, volumes, probe networks and branches |

Smoke history, kept for honesty: run 1 found that a failed sign-in made seeding fail (session-table
counts, fixed). Run 2 found that `TIME_WAIT` after `stop` blocked `up` (`SO_REUSEADDR`, fixed). Run 3
was refused because `origin/main` advanced (rebased). Run 4 failed the persistence check while a
foreign session was using Feature Review; the check now requires exact Docker and Git identity and
reports, rather than fails on, content changes to a live database owned by another session. Run 5
was correctly refused by the capacity lock while another worktree ran canonical FULL. Run 6 waited
for that lock and passed with no live-database notes.

**Delta QA (9 November).** All seven P1/P2 fixes passed. Its one new P2 came from run 6's log: after
stop and a rebuilding `up`, status printed `Dataset: unavailable` (line 1188) because the manifest
reader ran the retained container's image ID. With the containerd image store (Docker 29.9.3) a
rebuild replaces that manifest-list ID (`No such image`, line 1035), which would also have refused
detached owners. The reader now uses the project's current `<project>-backend-development` tag, and
the smoke asserts the manifest after restart. Run 7 passed in 224 s with the manifest read after
restart, no `No such image` and zero residual state. The P3 follow-up: reset and remove now prove the source before
one-off cleanup. The singleton UAT Preview's `marker_state` has the same pre-existing latent issue; it
is unchanged here and left as a follow-up.

Every run, failed ones included, retired all of its own containers, networks, volumes, images and
temporary branches. The singleton UAT Preview volumes (owner `florabase-ui-consistency-8e4313`,
created 4 November) were never touched; Docker reports no events for that project during this work.
