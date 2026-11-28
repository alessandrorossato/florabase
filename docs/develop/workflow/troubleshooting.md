# Workflow troubleshooting and acceptance evidence

> Summary: Common environment troubleshooting checks and acceptance evidence recording.

## Troubleshooting and acceptance evidence

- `DB CURRENT IS AHEAD OF OR INCOMPATIBLE WITH CODE`: use the checkout containing that revision or
  update primary `main` after delivery. Never force a downgrade to make the old code fit.
- DEV `belongs to <source>`: use `make dev-stop`, then `make dev-up` after primary is updated and
  DB/code compatible. No old source files or volume deletion are required.
- Review `belongs to <source>`: run stop/remove from its owning source before starting another Review.
- `GitHub CLI gh ... not found in PATH`: install `gh` on the operator host; authenticate with
  `gh auth login` before delivery. Verification does not require GitHub authentication.
- Primary staged changes during finish: preserve/resolve the operator changes deliberately; do not
  reset the index or check out the feature into primary.
- Migration or startup failure: use the environment's status command. Preserve its volumes while
  resolving code/revision compatibility; stop is not remove.

`make test-environment-workflow` models primary 0029 and a dirty untracked linked-worktree 0030,
configuration fallback, project boundaries, ahead-of-code refusal and destructive scope.
`make smoke-environment-workflow` requires an already linked worktree and fresh unique synthetic Review/Preview projects; existing operator Review is preserved.
It creates an untracked no-op migration, starts real Review, proves non-root/noninteractive fresh
bootstrap, repairs an intentionally root-owned `.bin` fixture through normal startup, checks
changed dependency/lockfile bootstrap and DB/media/dependency stop/restart persistence, builds a separate `origin/main` archive Preview and
validates production/integration topology. DEV container/mount/Git/revision snapshots are compared
before and after. Only fresh resources bearing exact registered-run labels are retired and verified; no operator data is deleted
and no additional real Git worktree is created.

`make smoke-dev-recovery` uses a unique disposable DEV fixture with a vanished old source. It proves
legacy tmpfs and durable media, DB rows and dependency files survive stop and primary recreation,
repeated stop is safe, and ahead-of-code state refuses application startup/upgrade without downgrade.
Before/after snapshots verify operator DEV, Review, Preview, production and primary Git are unchanged.
