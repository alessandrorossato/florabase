# Specification: release targets in a scope manifest (DOC-02)

The operator approved, on 2026-11-15, storing release targets in a versioned manifest instead of
a field on each feature entry. This page specifies that manifest and the checker rules. Steps
1 and 2 below are implemented; step 3 is not.

## Decision

- Release targets are stored in `docs/release/scope-v1.json`, the release-scope manifest for
  v1.0.0. A later release gets its own manifest.
- Feature status stays exclusively in [`features.json`](../features.json). The manifest holds no
  status and `features.json` holds no release target.
- All eight classes of the [feature reconciliation](feature-reconciliation-v1.md) are kept:
  `baseline`, `certify`, `release-work`, `best-effort`, `tooling`, `record`, `internal` and
  `post-1.0`. Their meanings are those of the reconciliation.

The alternative that was not chosen is a `release_target` string on every entry of
`features.json`. Rationale recorded by the documentation, not stated by the operator: a target
is relative to one release, and `features.json` is edited by every feature branch.

The operator decided the manifest path, the eight classes, where status lives, the three steps
and their order, the rejection of missing, unknown and duplicate identifiers and of
inconsistent status and class combinations, and that adoption by open branches is deliberate.
The file format and the rule set below were this specification's proposal. The operator
approved them on 2026-11-15 as step 2 implements them, including the fixed order of `classes`,
ignoring top-level keys other than the four required ones, and delivering rule 8 with step 2.

## Why it is separate from the scope documents

Enforcing the manifest needs a change to `scripts/check-features.py`, and every path under
`scripts/` selects the full canonical gate. The checker also had no test of its own, so a
schema change made without one could weaken it; step 1 added that test
(`scripts/test-check-features.py`, #181).

## Current behaviour to keep

`scripts/check-features.py` requires `id`, `category`, `description`, `acceptance_criteria`,
`dependencies`, `priority` and `status` on every entry, rejects duplicate ids, unknown statuses,
missing dependencies and cycles, and ignores any other key. It also rejects an
`allowed_statuses` that is missing or not a list of strings, a `features` value that is not a
list, an entry that is not an object, an empty or non-string `id`, `dependencies` that are not
a list of strings, and `acceptance_criteria` that is not a non-empty list. Every one of these checks stays.

## Manifest

Format, as implemented in step 2:

```json
{
  "version": 1,
  "release": "1.0.0",
  "classes": ["baseline", "certify", "release-work", "best-effort", "tooling", "record", "internal", "post-1.0"],
  "membership": {
    "FOUNDATION-001": "baseline"
  }
}
```

`membership` maps each feature identifier to exactly one class. By convention keys follow the
order of `features.json`; the checker does not enforce order.

The reconciliation matrix labels map to the class tokens as follows: 1.0 baseline is
`baseline`; PRE-1.0 certify is `certify`; PRE-1.0 release work is `release-work`; best-effort
(not certified) is `best-effort`; tooling (not a release deliverable) is `tooling`; historical
record is `record`; internal foundation (exempt) is `internal`; POST-1.0 is `post-1.0`.

## Checker rules

1. The manifest is readable, has `version` 1 and `release` `1.0.0`, and its `classes` are
   exactly the eight above.
2. Every identifier in `features.json` is a key of `membership`. A missing identifier fails.
3. Every key of `membership` is an identifier in `features.json`. An unknown identifier fails.
4. No key appears twice in `membership`. A duplicate fails: the checker parses with an
   `object_pairs_hook` that rejects a repeated key in any object of the manifest, because the
   default parser silently keeps the last value.
5. Every value is one of `classes`.
6. `baseline` requires status `verified`.
7. `post-1.0` requires a status other than `verified`.
8. With `--release-candidate`, no entry classed `certify` or `release-work` may be `planned` or
   `in_progress`. Without the flag this rule only reports, so ordinary development is not
   blocked while the certification work is open.

A manifest that cannot be read, or that breaks any of rules 1 to 7, fails the checker; nothing
is skipped when the manifest is absent. `classes` must list the eight tokens in the order
above. Top-level keys other than the four are ignored; the four are required and validated.

Rules 6 and 7 are the inconsistent status and class combinations this specification defines;
the operator approved the set on 2026-11-15. No rule changes a status, and no rule
derives a class from a status or a status from a class other than those two.

An entry classed `post-1.0` that reaches `verified` needs a scope-change record
re-classing it (for example to `baseline`), proposed in the same change and approved by the
operator before delivery; otherwise rule 7 fails.

After step 2 the manifest is the machine authority for class. Changing an existing
identifier's class is a re-class under [Changing this scope](scope-v1.md#changing-this-scope)
and needs an approved record. The reconciliation matrix is the evidence record and is
regenerated for the candidate.

## Transition, in this order

1. Add an offline test for the checker covering its existing rules, with fixtures for each
   failure. This lands first and on its own, so that the existing behaviour is pinned.
   Delivered in #181.
2. Add the manifest with complete membership taken from the reconciliation matrix, and rules
   1–7 with a failing fixture for each. The checker must pass on the populated manifest.
   With the operator's approval of 2026-11-15, step 2 also adds rule 8 to the checker, with
   fixtures. This intentionally changes the original split, which put rule 8 in step 3. The
   flag `scripts/check-features.py --release-candidate` is opt-in: no gate, CI job or release
   tool passes it, so ordinary verification is unchanged.
3. Wire `--release-candidate` into the release rehearsal, coordinated with REL-01, which owns
   the release tooling.

Each step selects the full gate because it touches `scripts/`.

## Adoption by open branches

From the moment step 2 is on `main`, pull-request CI, which checks the merge commit, fails for
any branch that adds, removes or renames a feature identifier until `membership` matches. The
local canonical gate detects this only after the branch merges `main`. This is deliberate.

- Step 2 re-derives membership from current `main` before its final verification, so that an
  identifier merged in the meantime does not fail step 2's own merge commit.
- Before step 2 is delivered, its handoff lists every open branch that changes the set of
  identifiers, found from worktrees, claims and open pull requests, and each of those writers
  is told.
- A branch updates by merging `main` and adding, removing or renaming one line per changed
  identifier, before its final
  canonical verification. It writes the class it proposes and names it in its handoff; the
  operator approves it before delivery.
- The class of a new identifier follows the scope: a task the scope names takes the class the
  operator approves for it, and work that is not in the scope is `post-1.0`
  ([Changing this scope](scope-v1.md#changing-this-scope), rule 4).
- Identifiers that are in `features.json` and not in the reconciliation matrix when step 2 is
  prepared are listed in its handoff with a proposed class, for the operator to approve.
- The operator approved these classes on 2026-11-15: ENG-01 is `certify`, because it is an
  implemented, user-facing feature on `main` whose certification must verify its acceptance
  criteria and recorded evidence, including the applicable G-CORE check; RELEASE-SCOPE-001,
  DOC-01, DOC-03 and DOC-05 are `release-work`; BRAND-01, which the scope did not name, is
  `certify`. A task that is not yet in `features.json`
  takes its class when it is added. No status changes with them, and
  the class does not promote ENG-01 to `verified`; it reaches `verified` only through its
  certification.

## Acceptance

- The existing rules still fail on their fixtures.
- Removing one identifier from `membership`, adding an unknown one, and repeating one each fail
  the checker.
- A `baseline` entry that is not `verified`, and a `post-1.0` entry that is, each fail.
- With `--release-candidate`, a `certify` or `release-work` entry that is `planned` or
  `in_progress` fails; without the flag it is reported and the checker passes.
- The populated manifest passes, and its classes equal the reconciliation matrix for every
  entry the matrix covers.

## Constraints from the scope

- Status and release target stay separate, in separate files. No transition step promotes a
  status.
- `internal` is the internal-foundation class of the scope: exempt from user-facing completion
  certification, never exempt from the existing checks.
- The class of each task (mandatory, workflow enabler, optional, deferred) lives in the scope,
  not in the manifest.

## Open point

The watering and feeding kinds (scope decision 5) have no entry of their own, and step 2 does
not add one. If FN-03 is delivered, its branch adds the identifier and its manifest line under
the adoption rules above. They are not EVENT-003, which is a broader post-1.0 entry.
