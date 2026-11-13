# v1.0.0 task acceptance criteria

This page is part of the [v1.0.0 release scope](scope-v1.md) and is authoritative for the
acceptance criteria of every task the scope names. The scope decides which tasks are mandatory;
this page says when each one is done.

Rules for every task:

- **Evidence is in the repository.** A task is accepted when its evidence is committed: tests in
  the tree, and a record of manual runs under `docs/release/evidence/` naming the commit, host,
  dataset, commands and result. A receipt that exists only in a worktree's Git metadata, or a
  statement in a chat or an external report, is not acceptance evidence.
- **Feature status is separate.** Meeting these criteria does not change a `features.json`
  status. A status changes only under the rules in the
  [feature reconciliation](feature-reconciliation-v1.md).
- **Optional tasks are conditional.** Their criteria apply only if the task is delivered. If it
  is not, the deferral is recorded in the scope-change table and the criteria do not apply.

## Mandatory release blockers

| ID | Acceptance criteria | Evidence |
| --- | --- | --- |
| ENG-01 | (1) An authenticated owner can change the password only by supplying the current one. (2) After a change the old password fails to sign in, the new one succeeds, and every other session of that user is rejected. (3) A command run without the application serving requests sets a new password for an existing owner and revokes all sessions. (4) Neither path logs or returns a password or token. | PostgreSQL integration tests for 1–4 in the canonical gate; G-CORE step 11 record. |
| ENG-05 | Exactly one of: **(a)** a PostgreSQL integration test using two real database sessions for each recorded finding (duplicate-identity merge against a concurrent Plant write; identity creation against an uncommitted merge) passes in the integration stage and shows no record left pointing at a retired identity; or **(b)** an operator-approved risk disposition is recorded in the scope-change table and in a document linked from the TAXONOMY-001 evidence, naming both findings, the conditions under which each occurs, the observable result, and the recovery. | (a) the test file path and the gate that ran it; or (b) the disposition document and the scope-change record. |
| ENG-07 | (1) The PERF-001 protocol is run on the release-candidate images with the Golden COMPREHENSIVE dataset. (2) The results are committed under `docs/performance/`. (3) The operator records thresholds and the supported collection size derived from those results in the scope-change table. (4) The candidate meets the recorded thresholds. | Results file; scope-change record; G-PERF record. |
| FN-01 | (1) Every CUTTING-001 acceptance criterion has recorded evidence, including a complete, a failed, a partial and a still-unknown rooting example with starting and outcome quantities retained. (2) Clonal edges appear in the lineage view in both directions. (3) The canonical gate passes on the delivered tree. (4) The operator's acceptance is recorded. | The Cuttings owner's handoff and tests; G-CORE step 12 record. Owned by the active Cuttings writer. |
| FN-05 | Decision D1 is approved: Today is preselected. (1) A new Journal entry opens with Today selected and can be saved without another date action. (2) Another date and Date unknown can each be chosen explicitly and are saved as chosen. (3) Opening an existing entry shows its stored date with its stored precision, and saving without touching the date leaves the stored value unchanged, including a year-only, a year-month and an unknown date. (4) A stored or drafted date does not change when the user navigates between records, switches the entry kind, cancels, or returns to a restored draft. (5) Height entries still require a date. (6) Frontend regression tests cover 1–5. Not implemented in the scope documentation change; assigned to the functional batch. | Test paths under `frontend/src/events/`; G-CORE step 5 record. |
| FN-06 | On a migrated database containing only the owner: (1) sign-in succeeds; (2) every page of the [page inventory](page-inventory-v1.md) that has a list renders its empty state with no error; (3) a first botanical identity, seed lot and plant can be created using only controls reachable from those empty states; (4) every defect found is fixed or has a recorded disposition. | Run record with the candidate commit and per-page result. |
| DOC-01 | The portable Compose guide contains: prerequisites; asset verification; configuration; first install; a reverse-proxy example including the headers the application does not send itself; upgrade; paired backup; isolated restore; troubleshooting for a wrong origin, a schema revision mismatch, an unhealthy container, bind-mount permissions and a lost password. `deployment.md` and `installation.md` each state their status (development; best-effort) in their first paragraph. | G-INSTALL, G-UPGRADE and G-RESTORE records state that no instruction outside the guide was used. |
| DOC-02 | (1) The feature reconciliation covers every entry and is regenerated for the candidate. (2) The checker's existing rules are pinned by a test before any schema change. (3) Release targets are stored and enforced as specified in the [schema follow-up](release-target-schema-followup.md). | The reconciliation; the checker test; `scripts/check-features.py` passing on the populated graph. |
| DOC-03 | Each statement in the list below is corrected, and a re-check against the candidate finds none of them. | A documentation change citing each row; the re-check recorded with the candidate commit. |
| DOC-04 | A person who did not develop Florabase, given only the published user guide and a freshly installed instance, completes G-CORE steps 1–9 without help from the author or from any agent. The record names the tester's role, the date, the candidate commit, the result of each step and every point where the tester stopped. Pass requires all nine steps completed and every stopping point either fixed in the guide or dispositioned. | Trial record under `docs/release/evidence/`. |
| DOC-05 | (1) `CHANGELOG.md` exists with an entry for the release. (2) A versioning page states the release line and the supported contracts. (3) `SECURITY.md` names a private reporting channel and the supported versions. | The three files at the candidate commit. |
| REL-01 | A non-publishing rehearsal produces `1.0.0-rc.N` assets in which the backend and frontend package versions, the image labels, `/release.json`, the release manifest and the tag name are equal. | Rehearsal log reference and the version values recorded. |
| REL-02 | The G-INSTALL, G-UPGRADE and G-RESTORE records exist for the candidate. | Those records. |
| REL-03 | Every mandatory gate in the scope has a record on one candidate commit, and G-SOAK has completed. | The gate records. |

### DOC-03 statement list

| File | Statement at the baseline | Fact at the baseline |
| --- | --- | --- |
| `docs/architecture.md`, "Deliberately deferred" | Supplier media, saved views, bulk operations, PWA installability and taxonomy reconciliation are backlog | All are on `main` |
| `docs/architecture.md`, "Implemented domain modules" | Omits Orders, Schedule, Saved Views, Taxonomy, Explore, Cuttings, Measurements and Import/Export | All have routers in `backend/src/florabase/api/router.py` |
| `docs/development.md` | "Version 2 receipts" | Receipts are version 3 (`development-workflow.md`) |
| `docs/development.md` | "Codex-managed feature worktree", "existing Codex worktree" | The workflow is provider-neutral (`AGENTS.md`) |
| `docs/development.md` | "`quality` runs `make check`" | The job runs `scripts/ci-verify.py quality` (`.github/workflows/ci.yml`) |
| `docs/security.md`, implementation table | "nginx provides the separate source-address limit" | `frontend/nginx.conf` has no rate limit; the operator's proxy owns it |
| `docs/portable-installation.md`, `docs/installation.md` | Name `v0.1.0-beta.6` as the release | Not tagged or published; the last published beta is `v0.1.0-beta.5` |
| `features.json`, UI-REDESIGN-EXPLORATION-001 description | "experimental only" | Delivered as the production shell in `fec0398` |

The list is closed for this scope. A stale statement found later is added by a scope-change
record or corrected as ordinary documentation work; it does not reopen DOC-03.

## Required workflow enablers

These do not change the product. They are required because the mandatory work is delivered
through them. Their detailed design belongs to their implementers; the criteria below are the
outcomes the scope requires.

| ID | Acceptance criteria | Evidence |
| --- | --- | --- |
| WF-01 | (1) After `make lint`, `make typecheck` and `make test` in a worktree with no prior Quality state, `docker network ls` shows no network belonging to that worktree's Quality project. (2) Those three commands still pass. (3) Quality volumes and their ownership labels are unchanged in kind. | A disposable smoke asserting 1 and 3, run in the canonical gate; the gate result for 2. |
| WF-02 | `make verification-plan FORMAT=json` selects: (1) for a change only under a shared interface path such as `frontend/src/components/`, every backend and frontend suite, all static checks, API drift, both production builds and integration, and no workflow or release suite; (2) for a change under `scripts/`, `Makefile`, `compose*`, `.github/`, a Dockerfile or a lockfile, everything in 1 plus the workflow and release suites and the forced migration cycle; (3) for an unclassified path, the same as 2. (4) Delivery refuses a receipt whose tier is lower than the recomputed plan. (5) No product check that runs today for a path stops running for that path. | Cases for 1–4 in `scripts/test-verification-impact.py`; a before/after plan comparison for 5 in the handoff. |
| WF-03 | (1) A new test file placed in a directory owned by a scope is selected with that scope without editing the impact map. (2) A test file owned by no scope makes `make verification-plan` exit non-zero and name the file, without starting Docker. | Cases in `scripts/test-verification-impact.py`. |
| WF-04 | On a disposable fixture with at least two source branches: (1) one integration branch is produced with a record of each source branch and commit; (2) the delivery title and body list every feature identifier and source commit; (3) each source branch is finished and its worktree retired by supported commands, with proof that all its commits are contained in the merge; (4) a source branch with a commit not contained in the merge is refused and left intact. | Cases in `scripts/test-feature-workflow.py` and `scripts/test-agent-workflow.py`. |
| WF-06 | On synthetic Docker state: (1) the report lists each class of leftover (disposable resources of an ended run, Quality projects of a missing or merged source, UAT instances of a merged or missing source); (2) without the confirmation token nothing is changed; (3) with it, only disposable resources and confirmed Quality projects are removed, and UAT instances are stopped with their volumes retained; (4) the container identifiers, volume names and labels of DEV, UAT Preview, Stable Preview and production fixtures are identical before and after. | A real disposable smoke asserting 1–4. |

## Optional PRE-1.0 improvements

Each row applies only if the task is delivered for 1.0. None is required by a mandatory gate.
If a task is not delivered, its deferral is recorded and nothing else follows.

| ID | Acceptance criteria if delivered | If deferred |
| --- | --- | --- |
| ENG-02 | (1) A response for `/` from the bundled nginx carries `X-Content-Type-Options: nosniff`, a `Referrer-Policy`, a frame restriction (`frame-ancestors` or `X-Frame-Options`) and a `Content-Security-Policy`. (2) With those headers, every page of the page inventory loads without a console policy violation in a light and a dark theme, including an external image and, where configured, online map tiles. | The DOC-01 proxy example carries these headers; G-SEC records the deferral. |
| ENG-03 | A test enumerates the application's routes and fails when any route other than sign-in, health and readiness lacks the authentication dependency. | G-SEC uses the recorded route review instead. |
| ENG-04 | (1) Every response carries a request identifier header. (2) An unhandled error writes one structured log entry containing that identifier and no credential. (3) The error view shows the identifier. | G-DIAG's logging clause does not apply. |
| ENG-06 | One real-browser test covers G-CORE steps 1–8 against the production images, headless, with no network access beyond the stack, and runs in the top verification tier. | G-CORE is recorded from the operator's pass alone. |
| FN-02 | The Seeds, Sowings and Plants directories can be ordered by at least name and date, the order survives pagination, and a component test covers each directory. | No effect on any gate. |
| FN-03 | Journal entries can be recorded with a watering kind and a feeding kind for a Plant and a Plant group; they appear in Journal and History; the migration passes the migration cycle with existing events present. Dropped if implementation or migration risk threatens the release (decision 5). | No effect on any gate. |
| FN-04 | Every reference select that can exceed 50 options is searchable by typing, operable by keyboard, and covered by a component test. | No effect on any gate. |
| FN-07 | Installation, launch and sign-in are recorded on one physical Android device and one physical iOS device. | The README and `docs/pwa.md` state that installation is experimental; PWA-001 stays `implemented`. |
| DOC-06 | The documentation is reorganised without a broken relative link, and every moved file that a script reads is updated in the same change. | No effect on any gate. |

## Deferred

| ID | State | Reopening condition |
| --- | --- | --- |
| WF-08 | Deferred. The existing post-merge jobs and release safeguards stay as they are. | Evidence that a replacement gives equal or stronger exact-main coverage, reviewed separately and approved by the operator. |
