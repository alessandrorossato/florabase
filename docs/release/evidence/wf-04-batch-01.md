# WF-04 Batch 01 bootstrap evidence

The WF-04 implementation commit is `2645665eece2498186b9d7bd417f48e4e2f28bfe`, based on
`02519b99098305786f03ba5fba4af8eeb4bdead7`. The [batch manifest](batches/wf-04-batch-01.json)
records the four source tips, merge commits, conflict resolutions, and final reconciliations.

## Bootstrap validation

On 16 November 2026 the workflow writer used the Linux development host with Docker Engine
and a disposable Git repository, local bare remote, two synthetic feature sources, and a
simulated protected-squash GitHub response. There was no application dataset.

- `make smoke-feature-batch` passed using real Docker ownership and mount inspection. Both
  source tips became ancestors of the integration head. The supported helpers finished and
  retired both managed source worktrees following the simulated protected squash.
- `env -u AGENT_ID make smoke-workflow-resources` passed. Synthetic resources were retired and
  the observed identity of DEV, Review, UAT, Stable Preview and production resources remained
  unchanged.
- In a detached disposable checkout independent bootstrap QA passed the four batch delivery,
  CI and canonical receipt regressions in `scripts/test-feature-workflow.py` and the three batch
  regressions in `scripts/test-agent-workflow.py`. These exercise a fresh receipt for the exact
  approved head, rejection of missing, reused or stale evidence, strict up-to-date checks,
  missing CI event refusal, additive progress conflict resolution, finish resumption, and
  refusal of omitted or moved sources, wrong PR identity, incorrect squash, busy locks and
  protected resources.
- Live GitHub read-only review found active ruleset `22081847`, strict up-to-date
  `quality`, `integration` and `build` GitHub Actions checks, permitted squash, and no bypass actors.

## Source compatibility

An independent reviewer merged the four pinned source tips in a disposable clone for focused
QA. The 162-entry graph passed, the candidate gate refused DOC-05 and eight existing open items,
and directory-based WF-03 inventory passed before Docker. The REL-01 release suite passed 60
tests, the tool lock suite passed four, and the controller suite passed 63. DOC-05 delta QA
checked 39 documentation links and consistency of six version surfaces, and confirmed private
vulnerability reporting enabled. This candidate reconciles DOC-05's wording with REL-01's
enforcement. The [FN-06 record](fn-06.md) contains the owner-only browser run and both
operator-approved dispositions. Source QA and historical receipts retain their original
commit identities.
