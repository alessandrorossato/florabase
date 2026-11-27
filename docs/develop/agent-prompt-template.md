# Agent prompt template — post-delivery cleanup

Copy this block into feature briefs for agents working in provider-managed worktrees (see
[AGENTS.md](../AGENTS.md#after-delivery-remove-your-worktree) and
[docs/development-workflow.md](development-workflow.md#worktrees-provided-by-an-agent-tool)).

## Final step (after delivery and finish)

1. Stop at `READY_FOR_DELIVERY`; the operator runs `make feature-deliver` and `make feature-finish`
   (or `make feature-batch-finish`).
2. Once the operator confirms the PR is merged and finished, from a directory **outside** your
   worktree check `git -C <worktree> status --porcelain` (must be empty),
   `git -C <worktree> branch --show-current` (must be empty / detached), and
   `make feature-context` / `make workflow-resources` (no owned Review/UAT resources), then remove
   your worktree through your own tool (plain fallback: `git worktree remove <path>`, never
   `--force`, never `rm -rf`, never touch dirty/branched/other-agent worktrees).
3. If anything refuses, report the path and reason to the operator and stop.
