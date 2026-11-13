# Follow-up specification: `release_target` in the feature graph

This is a specification for a later increment. Nothing here is implemented, and
`scripts/check-features.py` is unchanged by the scope increment.

## Why it is separate

The scope increment is documentation only. Enforcing a release target needs a change to
`scripts/check-features.py`, and every path under `scripts/` selects the full canonical gate. The
checker also has no test of its own today, so a schema change made without one could weaken it.

## Current behaviour to keep

`scripts/check-features.py` requires `id`, `category`, `description`, `acceptance_criteria`,
`dependencies`, `priority` and `status` on every entry, rejects duplicate ids, unknown statuses,
missing dependencies and cycles, and ignores any other key. Every one of these checks stays.

## Proposed schema

- A top-level `allowed_release_targets` list: `baseline`, `certify`, `release-work`,
  `best-effort`, `tooling`, `record`, `internal`, `post-1.0`. The meanings are those in the
  [feature reconciliation](feature-reconciliation-v1.md).
- A `release_target` string on every entry.

## Proposed checker rules

1. `release_target` is present on every entry and is one of `allowed_release_targets`.
2. `baseline` requires status `verified`.
3. `post-1.0` requires a status other than `verified`.
4. With `--release-candidate`, no entry with target `certify` or `release-work` may be
   `planned` or `in_progress`. Without the flag this rule only reports, so ordinary development
   is not blocked while the certification work is open.

## Transition, in this order

1. Add an offline test for the checker covering its existing rules, with fixtures for each
   failure. This lands first and on its own, so that the existing behaviour is pinned.
2. Add the schema keys and rules 1–3, with tests, and populate `release_target` for all entries
   from the reconciliation matrix in the same change. The checker must pass on the populated file
   and fail on a fixture for each new rule.
3. Add rule 4 and wire `--release-candidate` into the release rehearsal.

Each step selects the full gate because it touches `scripts/`. Steps 1 and 2 can share one gate
if they are delivered together with other workflow changes.

## Acceptance

- The existing rules still fail on their fixtures.
- Removing `release_target` from one entry fails the checker.
- A `baseline` entry that is not `verified` fails the checker.
- The populated graph passes, and its targets equal the reconciliation matrix.

## Constraints from the scope

- Status and release target stay separate fields. No rule derives one from the other except the
  two consistency rules above, and no transition step promotes a status.
- `internal` is the internal-foundation class of the scope: exempt from user-facing completion
  certification, never exempt from the existing checks.
- The class of each task (mandatory, workflow enabler, optional, deferred) lives in the scope,
  not in the feature graph.

## Open points

A workflow planning review proposes a small versioned membership list, for example
`docs/release/scope-v1.json`, as the single machine authority instead of a per-entry field, with
targets `1.0` and `post-1.0` required for non-terminal entries. The operator chooses between that
and the per-entry field specified here before implementation.

Whether the watering and feeding kinds (scope decision 5) get their own entry before this lands
or with it. They are not EVENT-003, which is a broader post-1.0 entry.
