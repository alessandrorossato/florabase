# FN-01 Cuttings source verification

Recorded 17 November 2026 in the CUTTING-owned worktree based on main
`ed5747c20d181c93b5cf78dab1656a24c576ba9b`. The application version was
`0.1.0-beta.6`. Tests used disposable PostgreSQL with synthetic fixtures and development builds.
The existing CUTTING migration is `20261110_0047`.

## Observed results

| Case | Reloaded lot start | Reloaded attempt outcome |
| --- | --- | --- |
| Complete | 4 | 4 rooted, completed |
| Partial | 4 | 2 rooted, completed |
| Failed | 4 | 0 rooted, failed |
| Pending | 4 | Unknown rooted count, active |
| Unknown input | Unknown | Unknown rooted count, active |

The tests created and then read the records through separate authenticated API requests. They
verified the observation projection for each outcome. The failed attempt case also verified a
year-precision observation, History search by “Rooting observation”, and a completed Check rooting
Schedule entry tied to the attempt. The clonal lineage cases exercised establishment of an
individual Plant and a PlantGroup, persisted origin links, traversal in both directions and
downstream-first reversal.

The Journal UI regression checked the source attempt link, notes, distinct zero and unknown
counts, and the absence of editing controls in the projected card. The Cuttings directory
regression covered both the initial empty collection and an empty filtered query.

## Checks and release disposition

- `./scripts/test-integration.sh backend/tests/integration/test_cuttings_api.py` passed 17 tests.
- Focused Vitest passed 37 tests across Journal, EventFeed, Cuttings and UX001.
- Backend Ruff and strict mypy, frontend Prettier, ESLint and type checks passed.
- `make api-check`, feature graph structure, offline document links and whitespace checks passed.

G-CORE step 12 remains pending on immutable release-candidate images. The source checks used
temporary test records and did not produce candidate image digests, candidate record IDs,
screenshots or browser traces. Record those fields and the step verdict in the
[G-CORE template](g-core-template.md) during the candidate run. FN-01 acceptance also requires
the delivered-tree canonical evidence and operator disposition.
