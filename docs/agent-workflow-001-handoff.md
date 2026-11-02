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

## Compose passthrough classification

Independent QA found the first guard was a denylist that missed `cp` and `watch`. It is now an allowlist over every
Compose v5.6.1 verb that refuses unknown verbs; the policy table is in the workflow contract. The same review found
`make sourcing-preview-compose` was labelled read-only but was not, and Sourcing make targets had no writer check.
DEV gained a lifecycle lock around its up, stop, upgrade and supported mutating passthrough.

A further QA pass found production passthrough still allowed `down -v`, and that `cp -L` escaped path checks. Probing
the real parser with `--dry-run` on an empty project showed Compose also accepts `-v=true`, `-v=1`, `-vt5` and
`rm -vf=true`, which the earlier Review and Sourcing regex missed too. Flags now follow that grammar on every role.

## Tradeoffs and compatibility

- `AGENT_ID` and local Git metadata enforce a cooperative protocol, not authenticated security: identity is declared,
  state files are locally writable and raw file edits are not intercepted. Guards bind cooperating agents at gates;
  they do not sandbox a hostile one, and direct `docker` commands are outside them. An agent omitting `AGENT_ID` at deliver is treated as the operator, and an
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
- Agents in a claimed worktree are not writer-gated on DEV passthrough such as `make dev-bootstrap-owner`, because DEV
  has no feature writer. `run`, `exec` and direct Docker can still change or delete data, and a plain `cp` to a path
  that is already a symlink inside the container is not detected.
- A long `exec` or `watch` on Review holds its lock, so two concurrent `review compose exec` commands now refuse.
- A worktree created before this helper, including this branch's own, has no marker. Remove those deliberately.
- Interruption between finish's proof and branch deletion leaves retirement refusing until the operator deletes that ref.
