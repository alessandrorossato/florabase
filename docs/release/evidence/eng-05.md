# ENG-05 evidence: TAXONOMY-001 concurrency findings

22 November 2026 · Linux amd64 cloud host · `main` at
`1126c03a86ba5f203e859b1530f523c3475f981a`. The operator chose branch (a) of the
[ENG-05 acceptance criterion](../acceptance-v1.md) on 2026-11-22. No scope-change record is
needed, because branch (a) does not change scope.

## The two findings

| Finding | Before the fix | Fix |
| --- | --- | --- |
| 1. A duplicate-identity merge runs while a Plant, PlantGroup, SeedLot, VegetativeLot or Schedule write references the identity being retired | PostgreSQL could abort one transaction with a deadlock, or a stale session cache could write the retired identity's ID | #185 (`0bb1d6c`): the active-identity check reloads the row with `FOR SHARE`, and Schedule writes take `lock_lineage_writes` first, so every path takes locks in the same order and rejects a retired identity |
| 2. An identity is created, renamed or corrected while a merge is not yet committed | Lock-order deadlock, or a duplicate check that read the state before the merge | #185: `lock_identity_writes`, taken after `lock_lineage_writes`, and `find_duplicate(..., for_share=True)` re-evaluate `merged_into_id IS NULL` once the merge commits or rolls back; writes run in savepoints with bounded retry on unique-index races |

## Gate run

Command: `./scripts/test-integration.sh backend/tests/integration/test_taxonomy_concurrency.py`
(the integration stage, selected to this suite: disposable Compose project from
`compose.integration.yaml`, PostgreSQL 18.6, schema migrated to `20261110_0047`).

Result: **13 passed** (9 test functions, 4 of them run for both commit and rollback or both entry
points) in 4.06 s; `RESOURCE_CLEANUP_PASSED` with zero residual containers, networks and volumes.
Each scenario uses two real database sessions. The merge scenarios assert through
`_assert_no_records_point_to_retired_identity` that no Plant, PlantGroup, SeedLot, VegetativeLot or
Schedule row references the retired identity.

The `duplicate key value violates unique constraint "uq_botanical_identities_name_cultivar_ci"`
line in the database log is expected: it comes from
`test_correct_accepted_name_savepoint_rolls_back_synonym_cleanup_on_unique_error`, which forces
that violation and checks that the savepoint rolls back.

Host note: the cloud host reaches PyPI through a TLS-intercepting proxy. To build the test image,
its CA was added to the `development-builder` stage for this run only (`PIP_CERT`); the change was
not committed and does not affect what the tests run against.

## What this does not cover

- This run is focused. The full suite runs in every canonical FULL gate, which includes this
  file through `scripts/verification-impact.json`.
- TAXONOMY-001 status stays `verified`; this record closes the two open findings only.
