# Feature worktrees, agents, delivery and retirement

> Summary: Feature worktree lifecycle, single-writer claims, handoff, parallel locking, delivery, finish, and worktree retirement.

This is the canonical environment and feature lifecycle contract for every agent and operator. It
validates feature context and runs environments from explicit source trees, and never moves the
primary checkout off `main`.

| Environment      | Source                                                      | Compose files                                | Project                                  | Browser                    | State                                                         |
| ---------------- | ----------------------------------------------------------- | -------------------------------------------- | ---------------------------------------- | -------------------------- | ------------------------------------------------------------- |
| DEV              | Primary checkout discovered through Git                     | `compose.dev.yaml`                           | `florabase`                              | `http://localhost:5173`    | Persistent DB, media, dependencies                            |
| Feature Review   | Current feature worktree, including dirty/untracked files   | DEV + review                                 | `florabase-feature-review`               | `http://localhost:15174`   | Persistent, isolated DB/media/dependencies                    |
| UAT Preview      | Owning feature source or clean delivered detached owner     | DEV + review + uat                           | `florabase-uat-preview`                  | `http://localhost:15174`   | Persistent isolated synthetic DB/media/dependencies           |
| Sourcing Preview | Current Sourcing worktree, including dirty/untracked files  | DEV + review + sourcing                      | `florabase-sourcing-preview`         | `http://localhost:15175`   | Persistent isolated synthetic DB/media/dependencies           |
| UAT instance     | Its owning linked feature worktree (one instance each)      | UAT Preview + uat-instance                   | `florabase-uat-branch-<branch>`      | `http://localhost:15180`–`15183` | Persistent isolated golden SMOKE/COMPREHENSIVE DB/media       |
| Stable Preview   | Clean detached checkout of fetched `origin/main` by default | DEV + production + preview                   | `florabase-preview`                      | `http://localhost:15173`   | Persistent isolated DB/media, immutable frontend dependencies |
| Quality checks   | Current feature worktree                                    | DEV + quality                                | `florabase-quality-<metadata-path-hash>` | None started               | Isolated volumes, no live DB, `network_mode: none` (`bridge` only via `--quality-network`) |
| Integration / CI | Current source / CI checkout                                | integration (standalone)                     | `florabase-integration-<random-run-id>`  | None                       | Disposable PostgreSQL tmpfs and test state                    |
| Production       | Selected deployable source/artifact                         | DEV + production                             | `florabase-prod`                         | Proxy port 8080 by default | Persistent DB/media                                           |

DEV is the tracked `compose.dev.yaml`; every other name in the Compose column is an override that
`scripts/compose_stacks.py` generates under the checkout's untracked Git directory
(`florabase-compose/<digest>/compose.<name>.yaml`) and loads after it (ADR 0008, WF-09). A revision
from before WF-09 keeps its own tracked overlays, which the helpers still load.

Migration verification (`florabase-feature-migration-<run-id>`), selected production verification
builds (`florabase-verification-build-<run-id>`) and unique smoke fixtures are also disposable.
Integration, migration and smoke register retirement before creating resources and verify zero owned
containers/networks/volumes after success, failure, partial creation and caught INT/TERM. A cleanup
failure fails the workflow. Images with exact ownership and no foreign tags/users retire; ambiguous
images and shared BuildKit cache remain and are reported. DEV, Review, UAT, Sourcing Preview, Stable
Preview and production never use this automatic retirement. The fixed `florabase-perf` benchmark is
explicitly operator-managed reusable test state, not a unique per-gate fixture; its manual stop
contract remains.

DEV deliberately retains the legacy explicit project name `florabase`. Renaming it to
`florabase-dev` would silently select an empty database instead of the operator's existing data.
Every helper passes an explicit project and project directory; none rely on the directory basename.
Compose prefixes DB, media, dependencies, networks, containers and development image tags with that
project. Review does not publish PostgreSQL/backend ports. Production has no Vite, source binds,
development port exposure or mutable dependency volume. Preview uses production builds and the
same-origin proxy with loopback cookie policy, not a Vite server.

## Feature worktrees and agents

[`AGENTS.md`](../../../AGENTS.md) is the one instruction contract. Current Claude Code, Codex and OpenCode
each read it natively, so the repository has no `CLAUDE.md` or OpenCode configuration; a `CLAUDE.md`,
`CLAUDE.local.md` or `AGENTS.override.md` would displace it and must not be added. Claude Code before
v2.1.277 reads only `CLAUDE.md`; update it rather than duplicating the rules.

Every agent follows PLAN → IMPLEMENT → FOCUSED TESTS → REVIEW → INDEPENDENT QA → FREEZE → CANONICAL
VERIFY → OPERATOR DELIVERY → FINISH. The primary checkout stays on `main` for DEV.

```bash
# From the primary checkout: create or find a worktree
make feature-worktree BRANCH=feat/example-001   # ../florabase-worktrees/example-001 from fetched main
make feature-attach BRANCH=feat/example-001     # Read-only: path, SHAs, writer, receipt, resources

# Inside the worktree: inspect, then own it
make feature-context [BRANCH=feat/example-001] [FORMAT=json]
make feature-claim AGENT_ID=claude-code
make feature-verify AGENT_ID=claude-code

# Sequential handoff; dirty work is allowed because its exact digest is recorded
make feature-handoff AGENT_ID=claude-code TO=codex REPORT=/path/to/report.json
make feature-claim AGENT_ID=codex
```

Open any agent's session in the worktree path, for example `claude`, `codex` or `opencode` from that
directory. Tools that provide their own worktree use `make feature-init` there instead; claims work
identically. `AGENT_ID` is a free lowercase name (`codex`, `codex-2`), not a provider list.
`FLORABASE_WORKTREE_ROOT` overrides the managed root.

Creation refuses a primary off `main`, diverged local `main`, wrong origin, an invalid branch name, an
existing local or remote branch and an existing path. Attach and context refuse an unexpected branch
and unrelated history; a branch that is merely behind `origin/main` is reported, may be claimed and
is refused later by the canonical gate.

**Handoff.** `REPORT` is a JSON object with exactly `completed`, `tests` and `defects` (lists of
strings) and `next_action`. Everything else comes from Git: branch, HEAD, tree, worktree digest, base,
and on read, receipt validity and Docker ownership. It lives in the worktree's own Git metadata beside
the receipt (`info/florabase-agent-state.json`), is never committed and goes away with the worktree.
Keep secrets out of it. Claiming refuses another addressee and any change to HEAD or the exact file
digest since the handoff. It prints the report labelled as unverified and recomputes the receipt, so
no agent can pass on verification by assertion.

**One writer.** A claim holds until handed off or taken over; it never expires. A crashed session
therefore needs the operator, at an interactive terminal, to confirm that session is gone, read the id
from `make feature-context` and run `make feature-claim AGENT_ID=<new> TAKEOVER=<claim or handoff id>`.
A takeover also accepts a drifted handoff after inspection. Give each live session its own `AGENT_ID`
(`codex`, `codex-2`): reclaiming under the same name succeeds with a warning, because the helper has
no way to tell two sessions apart. Keep `REPORT` outside the worktree, where it cannot change the tree.
`feature-verify`, Review/Sourcing up/seed/remove and their mutating Compose passthrough refuse a pending handoff and any other or missing
`AGENT_ID` once a worktree is claimed. A never-claimed worktree behaves as before. `feature-deliver`,
`feature-finish`, `mark-finished` and `feature-retire` refuse any `AGENT_ID` except `operator`, a
pending handoff and an active verification gate (omitting `AGENT_ID` behaves like
`AGENT_ID=operator`, and `feature-retire` also requires explicit `CONFIRM_RETIRE=<id>`). **`AGENT_ID` and the local Git metadata enforce a cooperative protocol, not
authenticated security:** identity is declared, the state files are writable by any local process
and raw file edits are not intercepted. The claim coordinates cooperating agents and gates their
shared steps; it is not a sandbox. The terminal requirement for takeover and the identity checks at
delivery, finish and retirement stop a cooperating agent acting by mistake, not a determined one. Read-only reviewers use
`git worktree add --detach <path> <sha>` or a clean clone, in any number, and never hold a claim.

**Compose passthrough** (`workflow_environment.py <role> compose`, `make sourcing-preview-compose`)
classifies the subcommand before Docker is reached:

| Class | Subcommands | Review, Sourcing | DEV | Quality, production |
| --- | --- | --- | --- | --- |
| Read-only | `config events images logs ls port ps stats top version volumes` | Available to anyone | Available | Available |
| Mutating | `attach bridge build commit cp create down exec export kill pause publish pull push restart rm run scale start stop unpause up wait watch` | Writer claim and lifecycle lock | `build exec pull run` take the lifecycle lock; the rest are refused | Available; Quality refuses `down kill rm stop` |
| Unknown or flag first | Anything else | Refused | Refused | Refused |

`config -o`/`--output` writes a host file and counts as mutating. Flags are matched by Compose's own
grammar (`--x`, `--x=v`, `-x`, `-x=v`, clusters such as `-fx` and `-xt5`), conservatively, so an
explicit false value also refuses. `down` or `rm` with a volume flag is refused on every role: Review
and Sourcing keep their confirmed remove action, UAT and Stable Preview expose no Compose passthrough,
and production has no passthrough for deleting data. Any future production deletion must be a separately
designed operation. `up --renew-anon-volumes` is refused everywhere. On every role, `cp` refuses
relative container paths, any path that contains or sits inside PostgreSQL, media or dependency
storage in either direction, `-L`/`--follow-link` and `-` tar streams. `make sourcing-preview-compose` permits only read-only
subcommands. A mutating `exec` or `watch` holds the lock until it exits, so it blocks other lifecycle
commands meanwhile.

This protects against mistakes through the passthrough, and only there. It does not resolve symlinks
already inside a container, so a plain `cp` to a path that is itself such a symlink is not detected.
`run` (including `run -v`), `exec` and direct `docker` access remain able to change or delete data, and
production `exec` and `run` stay available because backup and restore depend on them.

**Parallel features** use separate worktrees and need no coordination apart from these shared resources:

| Resource | Concurrent features | Guard |
| ------------------------------------------- | --------------------------------------- | ---------------------------------------------------- |
| Quality project, integration, migration, build | Parallel; project is unique per worktree/run | Existing exact ownership labels |
| Feature Review, Sourcing Preview | One owner per project; others refused | Owner labels plus machine lock on lifecycle commands |
| UAT Preview | One owner; shares port 15174 with Review | Owner labels plus machine and per-owner locks |
| UAT instances | One per worktree, at most four; ports 15180-15183 | Volume-label allocation, per-instance locks, FULL capacity lock for up/seed/reset |
| CPU, shared BuildKit, Docker address pools | Exhausted by concurrent FULL | Machine FULL lock |
| Same worktree's gate and receipt | One at a time | Per-worktree verification lock |
| Same worktree's retirement | One at a time | Per-target retirement lock in Git common metadata plus target verification lock |

Owner labels exist only after creation, so two sources starting Review together could both pass that
check; the lock closes the window. FULL runs share no fixed name or port, so its lock protects capacity
rather than identity, and affected gates stay parallel. All locks are kernel `flock`s in
`$FLORABASE_LOCK_DIR` (default `.local/state/florabase/locks` in the account's home), so they cover separate clones,
never block, and release on any exit including SIGKILL. Children do not inherit them. After SIGKILL,
stages may briefly outlive the released lock; use the failed run's recovery command as described below.
Remote CI and direct `make ci` take no lock. Parallel Review ports are deliberately not provided.

**Retirement.** After a linked finish succeeds, `make feature-finish` (and `make feature-batch-finish`
for each finished batch source) automatically attempts best-effort retirement of a managed worktree
directly under `florabase-worktrees/` by reusing the exact same retirement checks below, confirmed
implicitly by the finish proof just written. Pass `KEEP_WORKTREE=1` to skip auto-retirement and keep
the detached worktree. Provider-managed worktrees (without the managed marker or outside
`florabase-worktrees/`) are never touched and are retained for their provider tool. If any safety
guard refuses (owned Review/UAT/Preview resources, running bind mount, Docker unavailable, ignored
`.env` or backups, locks, etc.), finish still succeeds and prints the refusal reason, follow-up
command, and final `WORKTREE: RETAINED <path> (<reason>)` line; resolve the condition and then from
the primary checkout run:

```bash
make feature-retire FEATURE=example-001 CONFIRM_RETIRE=example-001
```

It is an operator-only step: any declared agent `AGENT_ID` (anything other than unset, empty, or
`operator`) or invalid `AGENT_ID` is refused before any target worktree lookup, lock, Docker query or
filesystem change. It removes one worktree directly under the managed root that
`make feature-worktree` created, and only with valid linked-worktree metadata, no pending handoff
or writer state, no active verification gate (the target verification lock is held from preflight
through `git worktree remove`), finish's proof at the same HEAD, a merge on cached `origin/main`,
a deleted branch, clean status and no Docker containers or volumes labelled with that source
(Docker unavailable refuses). Missing, prunable, locked, cross-wired or symlinked worktree
metadata refuse before removal. Ignored files other than regenerable caches, such as `.env` or backups, refuse for a decision, and so does any directory it
could not delete. The removal preflight permits a readable empty directory without child write
permission when its parent permits removal (including sticky-directory ownership checks). Nonempty
directories still require write/search permission; sticky-parent ownership is checked for files and
other direct children as well as directories. Every running Docker container is inspected regardless
of labels: a bind source equal to, inside or above the candidate refuses after path resolution.
Missing/changing Docker evidence and unsupported custom volume backing refuse before removal.
Symlinks and any host-visible mounted path within the candidate are refused. Linux
`/proc/self/mountinfo` is required to detect same-device bind mounts; missing or unreadable
traversal/mount evidence fails closed before Git removal. No ownership/permission changes
or recursive deletion fallback are performed. A non-blocking per-target `flock` in shared Git
common metadata serializes concurrent `feature-retire` invocations for the same worktree while
allowing independent worktrees to retire in parallel. Remaining cooperative concurrency limits:
`AGENT_ID` is cooperative convention rather than authenticated security (omitted `AGENT_ID` is
treated as operator and direct `git`/`docker`/shell commands bypass the CLI); advisory `flock`s
coordinate local helper invocations on the same host and release on exit or SIGKILL, but preflight
checks and `git worktree remove` remain non-atomic against external non-locking writers, mount
changes or newly started containers, so operators must stop external source and Docker writers
before retirement. It uses `git worktree remove` without force, so worktrees from agent tools, clones,
branches and all volumes are out of its reach.
A branch-less worktree with no proof, or an abandoned feature, stays for the operator to decide.

### Worktrees provided by an agent tool

```bash
make feature-init
# Only when the tool left a clean detached HEAD at origin/main:
make feature-init BRANCH=ci/example
```

Initialization validates repository identity, branch naming, source path and the cached `origin/main`
base. It prints branch, SHA, dirty state, primary path and common metadata without revealing secrets.
It is idempotent on an existing compatible feature branch, including dirty source. It never fetches
implicitly or discards changes. Fetch `origin/main` deliberately before initial setup when needed.
Detached attachment requires a clean tree exactly at `origin/main`; an existing branch must contain
that base. Unsupported states receive a refusal rather than a reset, stash or branch rewrite.

Manual development can still use `make feature-start BRANCH=feat/example`. In a primary checkout it
fetches, fast-forwards clean `main`, then creates the branch as before. In a linked worktree it fetches
and delegates to initialization in that worktree, without attempting to switch shared `main`.

**After delivery: remove your worktree.** Florabase never deletes provider-managed worktrees:

1. Stop at `READY_FOR_DELIVERY`; the operator runs `make feature-deliver` and `make feature-finish`
   (or `make feature-batch-finish`).
2. When the operator tells the agent the PR is merged and finished, from a directory **outside** the
   worktree verify `git -C <worktree> status --porcelain` is empty and
   `git -C <worktree> branch --show-current` is empty (detached after finish), and verify
   `make feature-context` / `make workflow-resources` from that worktree show no owned Review/UAT
   resources, then remove the worktree **through the agent's own tool** (Antigravity: its
   worktree/workspace removal; plain fallback: `git worktree remove <path>` without `--force`). Never
   use `--force`, never `rm -rf`, and never remove a worktree that is dirty, still on a branch, owns
   Review/UAT resources, or belongs to another agent.
3. If anything refuses, report the path and reason to the operator and stop.
