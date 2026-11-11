# VERIFICATION-EVIDENCE-001: reusable local stage evidence

The opt-in implementation is integrated into the pre-beta branch. This is Phase 2 of
[VERIFICATION-FAST-001](verification-fast-001-handoff.md). The operator requires all delivery
stages to run fresh and limits local stage evidence reuse to 24 hours.

## What changes

- `make feature-verify` and `make verify-full` accept three controls. With none of them, behaviour
  is unchanged: no evidence is read, written or deleted.

  | Control | Effect |
  |---|---|
  | `REUSE=1` | Quality and integration may be skipped when a valid record proves identical inputs. Every other stage runs. Fresh runs of those two stages record evidence. |
  | `REUSE=dry-run` | Every stage runs. For the two candidates the gate prints `would be reused` or `runs fresh: <reason>` and records new evidence. Use this during rollout to confirm the key is stable. |
  | `FRESH=1` | Every stage runs and existing records are ignored. Fresh records replace them. Wins over `REUSE`. |

  Any other value is refused. `make verification-evidence` (`REF=`) is a read-only dry-run of
  the gate's automatic plan without running any stage. Run it from the shell that will run the
  gate: the environment is part of the key, so another session or terminal reports
  `invalidated: environment: …` (a safe miss).
- Reuse is local only. The gate refuses an evidence mode under `GITHUB_ACTIONS=true`, and
  `ci-verify.py` never passes one. Every required GitHub check and its policy is unchanged.
- Only `quality` (`make check`) and `integration` (`make test-integration` or an exact affected
  selection) are candidates. Feature graph, the three whitespace checks, offline workflow suites,
  `workflow-check`, production builds and the real PostgreSQL migration cycle always execute.

## Evidence record

Location: `<absolute-git-dir>/florabase-stage-evidence/<stage>.json`, so each worktree has its own
records outside the source tree. Directories are mode 0700 and records 0600. The gate writes
records under the existing per-worktree verification lock. It writes a temporary file in the same
directory, fsyncs it, uses `os.replace`, then fsyncs the directory.

```json
{
  "kind": "florabase-stage-evidence",
  "schema": 1,
  "stage": "quality",
  "command": ["make", "check"],
  "worktree": "<absolute git dir>",
  "key": "<sha256 of [schema, stage, command, worktree, manifest]>",
  "manifest": {
    "compose": {"<model>": "<sha256 of the rendered model without labels and x-* fields>"},
    "mounts": {"<repo-relative source> (excluding <shadowed paths>)": "<tree sha256>"},
    "policy": {"scripts": "<tree sha256>", "top-level files": "<sha256>", "host symlinks": "<sha256>"},
    "environment": {"<NAME>": "<HMAC-SHA256(salt, NAME=value)>"},
    "env_files": {"<model>": "<sha256 of path and content>"},
    "volume_content": {"<model>/<volume>": "<content sha256> | absent"},
    "tools": {"docker": {}, "daemon": {}, "compose": "", "buildx": "", "python": "", "git": "", "make": ""},
    "images": {
      "<image reference>": "<content identity>",
      "built <model>/<service>": "rebuilt from the pinned build context"
    },
    "volumes": ["<model>/<service>: <volume> (<content digest | reconciliation>)"],
    "containers": ["<model>/<service>"]
  },
  "salt": "<random hex, per record>",
  "result": "passed",
  "exit_code": 0,
  "run_id": "<uuid hex>",
  "started_at": "<UTC ISO-8601>",
  "finished_at": "<UTC ISO-8601>",
  "digest": "<sha256 of every other field>"
}
```

Records never store environment values, env-file contents or container details. Variables are
salted HMACs, and env files and volumes appear only as digests.

## Input closure

The closure is derived from configuration and observed execution. No hand-maintained path list is
used.

1. **Rendered Compose.** `docker compose config --format json` runs through the stage's own helper:
   `workflow_environment.Environment(..., "quality")` for Quality, and
   `disposable_workflow.compose_invocation` with a fixed placeholder owner for integration.
   - **Removed before hashing.** Labels and top-level `x-*` extension fields are dropped. They are
     ownership metadata and anchors that carry the commit SHA and dirty flag, so keeping them would
     invalidate evidence on every commit. Compose ignores `x-*` at runtime.
   - **Added to the closure.** Every bind source and every build context of every service, plus
     any Dockerfile outside its context.
   - **Shadowed paths.** A bind source is digested minus paths shadowed by another mount or tmpfs in
     the same service, for example `frontend/node_modules`.
   - **Refused inputs:**
     - configs, secrets, `extends`, `env_file`, devices;
     - other build keys (`ssh`, `secrets`, `additional_contexts`, …);
     - mount types other than bind, volume or tmpfs;
     - sources outside the repository.
2. **Named volumes.** Each named volume is digested by content, as type, mode, owner and bytes:
   - **When.** Before the stage, after it, and at reuse.
   - **How.** In a labelled, network-less, read-only `--rm` container of the stage's own built image.
     An absent volume is recorded as `absent`, and the digest container never creates one.
   - **Exception.** Only `frontend_node_modules` is classified instead. It holds pnpm, Vite and tsc
     caches that change on every run, and it is accepted only under `florabase-dev-entrypoint`,
     which reinstalls it with `pnpm install --frozen-lockfile` from the bound lockfile, or under the
     ownership-only `dev-state-init`.
   - **Disposable projects.** Named volumes of a disposable project refuse.
3. **Observed execution.** While the stage runs, a `docker events` stream sees every container
   created for this worktree.
   - **Attribution.** A container is attributed by source label, or by one of the stage's
     persistent built image names. The labelled digest containers are skipped.
   - **Checks while the container exists:**
     - every bind must match a rendered source after the same shadowing;
     - every volume must be digested or classified;
     - anonymous volumes refuse.
   - **Image identity.** Taken from the image the container actually pinned, as layer diff IDs,
     platform and runtime config without labels. Image IDs are not used. The real Quality runs
     showed that the containerd image store mints a new ID on every cached rebuild. `frontend` and
     `dev-state-init` also share one tag with different Compose labels. Neither changes what runs.
   - **Disposable integration image.** Identified by its build context, but only if every `FROM`,
     every `--from=`/`from=` source and the `syntax` directive are digest-pinned (any spelling),
     and no `ADD` fetches a URL.
   - **Refusals.** At least one container per model must be observed. A dead observer, an inspect
     failure or a container outside the rendered models leaves no record.

Tree digests cover every entry Docker would expose: path, type, mode, owner, content and symlink
target. That includes untracked and Git-ignored files. Sockets, FIFOs and unreadable entries
refuse. Build contexts are digested in full, a deliberate superset of what `.dockerignore`
sends. It can only cause extra misses, and it never requires reimplementing Docker's ignore
matcher.

Host-side programs are not sandboxed, so the following all count as inputs:

- **Verification policy.** The whole `scripts/` tree, minus CPython `__pycache__`, and every
  top-level file, including the Makefile, Compose files and `.env`. A host program symlink must
  resolve to a regular file already covered by that closure. The manifest includes the resolved
  targets, so changing an intermediate link invalidates evidence. An unresolved link or an
  unmeasured target refuses reuse.
- **Environment.** Every variable except `REUSE`, `FRESH`, `_`, `OLDPWD`, `PWD` and `SHLVL`.
  `MAKEFLAGS` and `MFLAGS` count with those controls stripped.
- **Tool identity.** Docker client and server, daemon ID, kernel and driver, Compose, Buildx,
  Python, Git and Make.

A record is written only if the stage exited 0 and every input class recomputed after the stage
equals its value before the stage. A stage that writes into its own closure is not recorded, for
example a first `pnpm install` that fills `frontend/.pnpm-store`.

## Reuse rule

`REUSE=1` skips a stage only if all of these hold:

- the record parses and its digest verifies;
- the kind and schema match;
- the worktree, stage and exact argv match;
- the result is `passed` with exit 0;
- the start and finish timestamps have UTC offsets, are ordered and are neither in the future
  nor malformed; the completion instant is at most 24 hours old;
- the key recomputes;
- every class recomputed from current state is equal.

Otherwise the stage runs and the log names the reason:

- `miss`
- `corrupt`
- `schema`
- `unknown: <why>`
- `invalidated: <class>: <entries>`, for example `invalidated: mounts: backend, backend/src` or
  `invalidated: environment: FLORABASE_EXAMPLE`
- `invalidated: record expired: completion is older than 24 hours (UTC)` in reuse and dry-run
  modes. The gate checks age before recomputing inputs and again before reuse.

Starting a fresh run of a stage deletes that stage's record first, so a failed or interrupted
stage leaves none.

## Receipt version 3

- **Writing.** Every gate writes the receipt fresh for the exact working tree, with a top-level
  `stage_evidence: {"mode", "reused"}`. A reused `completed` entry carries
  `reused_from: {run_id, key, finished_at}` and is otherwise identical to a fresh entry.
- **Validation.** `reused_from` is checked and then stripped:
  - only a reusable stage may carry it;
  - the reference must have exactly those three keys, a 64-hex key and a timezone-aware time;
  - the summary must name exactly the reused stages.
- **Version 2.** Version 2 receipts remain valid and can never contain reuse. Unknown versions are
  refused.
- **Delivery.** `feature-tree-fingerprint.py verify` without `--worktree`, which `feature-deliver`
  uses, always refuses any receipt with reused stages:
  `receipt reuses stage evidence (…), which is not delivery proof`.
  - The `--worktree` review check accepts it and names the reused stages.
  - `feature-context` reports it as review-only.
  - The consolidated delivery requires a fresh FULL on the clean, committed integration HEAD.
    Use `env -u REUSE FRESH=1 make verify-full AGENT_ID=<writer>` and confirm the resulting
    version 3 receipt contains `reused: []`.
- **No inheritance.** An old receipt is never copied. A new commit fails the HEAD-tree comparison
  as before.

## Real Docker evidence

The real stages ran in this worktree on 2026-11-10 and 2026-11-11 (Docker 29.9.3, Compose 5.7.0,
containerd snapshotter). Earlier runs exposed four real-world gaps, all fixed:

- a first `pnpm install` that grows `frontend/.pnpm-store` (correctly not recorded);
- the backend's `attachment_data` volume (now digested by content);
- per-rebuild image IDs (now content identity);
- the SHA-bearing `x-source` block (now stripped).

The final run with the final code:

- **Fresh recording.**
  - Quality took 355 s: 1048 backend unit tests passed and the full frontend suite ran.
  - Integration took 543 s: 818 passed, 29 skipped. It ran in a disposable project with verified
    retirement and no residual containers, networks or volumes.
- **What was recorded.**
  - Quality observed `backend`, `dev-state-init` and `frontend`, plus two images by content
    identity. `attachment_data` was content-digested and `node_modules` reconciled.
  - Integration observed `db` and `tests`. Postgres was identified by content and the tests image by
    its pinned context. No volumes were mounted.
- **`REUSE` pass.** Both stages were reused in 1.8 s.
- **Live probes.**
  - Editing `docs/development.md` reused both stages.
  - Editing `backend/src/florabase/__init__.py` invalidated both (`mounts: backend, backend/src`
    for Quality, `mounts: backend` for integration).
  - Editing `frontend/src/main.tsx` invalidated only Quality.
  - After reverting, both stages were reused again.
- **After the WIP commit.** The Quality record from the previous evening failed only on
  `environment`, because the session was new. Compose, mounts, images and volumes all still matched
  across the new commit.

## Accepted residual risks

- **Tampering.** The record digest detects corruption and partial writes. It does not defend
  against deliberate tampering by the same OS user, which matches the cooperative workflow
  protocol. The salt sits beside the HMACs, so a short secret in the environment could be guessed
  offline by someone who can already read the 0600 record.
- **Host reads.** Host scripts can read files outside the closure. Every script is part of the key,
  and the current Quality and integration helpers read only Git metadata, `.env` and Compose files.
  Bind digests assume Docker reads the same worktree files as the host. A remote daemon with a
  different filesystem at the same path falls outside this proof.
- **Dependency volume.** `frontend_node_modules` content is trusted to lockfile reconciliation and
  is not hashed.
- **Unhashed lock.** `backend/requirements-dev.lock` has no hashes. On a BuildKit cache miss, a
  rebuilt integration image relies on its version pins. A fresh run has the same exposure.
- **Clock skew.** The observer's start boundary uses host time. On a daemon with a skewed clock
  (Docker Desktop VM), early containers could be dropped or attributed wrongly. This would only
  refuse or miss a record, never widen reuse.
- **Spurious misses.** The environment is deliberately over-broad: `make -j` jobserver arguments,
  terminal variables and per-agent variables all enter the key. `scripts/__pycache__` written by host
  commands also invalidates integration. All of this is safe.
- **Intermittent test.** The source runs hit a pre-existing failure in
  `frontend/src/UX004.test.tsx` ("legacy collection deep links…"). The failed run left no record.
  Within the 24-hour local window, reuse can still skip a flaky test after an identical passing
  run. The consolidated delivery gate executes it fresh.

## Tests

`scripts/test-stage-evidence.py` (run by `make test-verification-impact`)
drives the real `feature-verify.sh`, gate and receipt helper in Git fixtures. A fake Docker
renders Compose with volatile labels and `x-*` fields, streams create events, answers volume,
inspect and version queries, and mints a fresh image ID and labels on every inspect. The suite
covers:

- a cache hit;
- changed Python, TypeScript, tests, migrations, OpenAPI and generated TypeScript;
- changed backend and frontend lockfiles, Dockerfile, file mode, symlink, untracked and Git-ignored
  bound files;
- changed Compose models, environment variable, env file, tool identity, image identity, volume
  content, a newly created volume, verification policy and Makefile;
- docs-only and new-commit label changes (both reused);
- truncated, empty, tampered, schema, failed-result, forged-key, foreign-worktree and
  changed-command records;
- failed, SIGINT-interrupted and self-mutating stages, both through files and through volumes;
- two concurrent gates in one worktree, and distinct worktrees;
- default, `REUSE=1`, `REUSE=dry-run`, `FRESH=1`, invalid values and the CI refusal;
- a new commit and index drift;
- receipt v3/v2 compatibility and nine malformed receipts;
- secrets absent from records;
- direct classification tests for unprovable mounts, volumes, images, Dockerfile sources, host
  symlinks and Compose inputs;
- atomic write failure.
