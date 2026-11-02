# AGENT-WORKFLOW-001 handoff

The operator runbook and contract are in
[development-workflow.md](development-workflow.md#feature-worktrees-and-agents).

## Design decisions

- **Extension, not a second lifecycle.** `feature_worktree.py` adds only what was missing: creating and finding
  worktrees, one writer, one handoff, one retirement. `feature-init`, `start`, `verify`, `deliver` and `finish`
  keep their contracts and a never-claimed worktree behaves as before.
- **Git and Docker stay authoritative.** Added state is one per-worktree file beside the receipt plus finish's
  proof. Reported work is labelled as a report; receipt and ownership are always recomputed.
- **Kernel locks instead of lock files with expiry.** They need no stale-lock recovery and survive SIGKILL safely.
- **No TTL on claims.** Expiry could silently hand a live session's worktree to another writer. Takeover needs the
  exact id at an interactive terminal, and refusals do not reveal it.
- **Machine scope outside Git metadata**, because separate clones have separate metadata.

## Collision investigation

Quality derives its project from the worktree metadata path; integration, migration and verification builds use
random projects; `run` publishes no ports. FULL therefore has no identity collision, only CPU, BuildKit and Docker
address-pool contention, so only FULL takes the machine lock. Review's real gap was a check-then-create race:
owner labels do not exist until creation, so two sources could both pass `require_owner`. Lifecycle commands now
hold a machine lock. Review and UAT share port 15174, which fails loudly at bind and keeps separate volumes.

## Tradeoffs and compatibility

- `AGENT_ID` is declared, not authenticated, and raw file edits are not intercepted. Guards bind cooperating agents at
  gates; they do not sandbox a hostile one. An agent omitting `AGENT_ID` at deliver is treated as the operator, and an
  agent with a pseudo-terminal could reach takeover. Two live sessions sharing one name both pass, with a warning.
- After SIGKILL the lock is released while a Docker stage may briefly continue, which can overlap a new FULL. Unique
  projects keep this a capacity matter; the failed-run recovery command still applies.
- A refused gate still invalidates that worktree's earlier receipt when it loses at the lock stage, as any gate start does.
- Claude Code before v2.1.277, or with a `CLAUDE.local.md`/parent `CLAUDE.md`, does not read `AGENTS.md`. Update it or
  use its `claude-md-and-agents-md` setting; a repository `CLAUDE.md` was not added because installed versions do not need it.
- `Repository.require_origin` now reads the configured URL rather than the `insteadOf`-expanded one, so a local
  rewrite no longer causes refusal. Delivery keeps its own stricter expanded check.
- Existing Codex worktrees, 28ce, 548f, bf7a and `florabase-claude` are unaffected: retirement requires a marker only
  `make feature-worktree` writes.
- A worktree created before this helper, including this branch's own, has no marker. Remove those deliberately.
- Interruption between finish's proof and branch deletion leaves retirement refusing until the operator deletes that ref.
