# BETA-FOUNDATION-001 — independent QA corrections B1–B4

Status: **QA_CORRECTIONS_READY**, awaiting independent delta QA. No canonical FULL run or delivery
receipt. Feature remains `implemented`. The operator explicitly requires delta QA before FULL.

Continued in the existing linked worktree on `feat/beta-foundation-001`; confirmed clean candidate
HEAD `3553a9c21837e3e122d692cd3c4fd4c785b505ad`, tree
`9d986e4bfe6d25e1755d6911911cffb13ba2f515` and retained writer
`codex-beta-foundation-001` through `make feature-context` and `make feature-claim`.
The corrected local HEAD/tree are reported in chat; they are not self-embedded here.

## B1 — sticky ownership on every child

The original preflight checked a directory's ownership against its parent, but not ownership of files
inside a sticky directory. A root-owned mode-1777 `frontend/node_modules` is writable by the operator,
but its root-owned file still cannot be unlinked by that operator. The check now applies the sticky
rule to every direct child with no-follow metadata, including regular files, FIFO/socket/device entries
and directories. Symlink refusal remains earlier; recursion and existing permission checks remain.

Real regression uses the cached Node image solely to create exact root-owned objects in a disposable
finished worktree. Regular file and FIFO are exercised independently. It asserts mode 1777/UID zero,
retirement refusal, retained Git registration, retained tracked source files and retained child
content/type. Cleanup removes only the exact fixture child and empty fixture directory as root;
there is no recursive chmod/chown or deletion fallback. The original empty-root-owned-directory
positive smoke still passes.

## B2 — running mounts outside host mountinfo

Retirement now lists **all** running container IDs without a Florabase label filter, projects only
ID/running state/mount metadata, resolves bind sources strictly and checks overlap in both directions.
Candidate, descendant, ancestor and symlink-alias sources refuse even if the bind is read-only or the
container has no Florabase labels. Thus a parent bind cannot conceal a nested container-only mount.
Host-visible `/proc/self/mountinfo` checks and existing labelled container/volume guards still run.

Missing/malformed IDs, inspection data, mount types or sources, unresolvable bind paths, Docker
failures and inventory changes refuse before Git removal. A second running-ID inventory detects
starts/stops during inspection. Default local volumes require matching daemon volume identity,
mountpoint and empty driver options; their Docker-managed paths need not be operator-readable.
Custom/unknown volume backing is conservatively refused because it cannot establish independence.
The guard itself only lists/inspects Docker; it never stops or changes a container.

The real regression starts an unlabelled disposable container with a bind of the **parent managed
worktree root** and nested tmpfs at the candidate's `frontend/node_modules`. It writes `live` inside
that mount, proves the host sees an empty directory, attempts retirement, then verifies registration,
source, live nested data and running container state are intact. Only that newly created container
is stopped/removed in cleanup; no real container is stopped, recreated or modified.

## Before/after evidence and the previously failing workflow test

Both real reproductions were rerun against the exact authoritative `3553a9c` helper, copied from Git
into disposable scripts. This isolated probe does not change the branch or any operator worktree:

| Case | Authoritative candidate before correction | Corrected behavior |
| --- | --- | --- |
| Root-owned sticky child | Retirement returned 1 with Git's `Operation not permitted`, but Git registration was already gone; an orphan tree remained. The observed `feature.txt` still existed; no claim that all original files survived is made. | Rejects with `sticky parent` before unregistering. Regular file and FIFO cases each retain registration and contents. |
| Unlabelled parent bind + hidden nested mount | Retirement returned 0, registration disappeared and the candidate/`feature.txt` were removed while the container was running. | Rejects with `running container`; registration, source and readable `live` nested data remain, and the fixture container is still running until scoped cleanup. |

Claude's throwaway patch itself is no longer present in its QA checkout, but the reported single
workflow failure was reproduced after adding the required Docker query: the existing
`test_linked_finish_then_explicit_retirement_preserves_environments` accepted only `ps -a --filter`
and `volume ls --filter`, so it failed on **`ps --quiet --no-trunc`**. This was a stale read-only command
expectation, not evidence of a Docker mutation. The assertion now permits that exact query and the
specific read-only container/volume inspect prefixes, while continuing to reject mutating commands.
The full suite passes with that assertion. Early new sticky fixtures also needed the existing
`node_modules/` ignored-cache rule; the final real reproductions include it and reach the defect.

## B3 / B4 and audit follow-ups

- BETA-IMAGE-001 begins with intended-host architecture/runtime screening **before publication**.
  Initial `linux/amd64` requires native intended-host support. An initial arm64 host requires
  `linux/arm64` and native smoke before publication. Additional architectures can follow in separate
  verified releases without blocking an agreed amd64 beta. Host capacity remains unmeasured and is
  qualified in BETA-RUNTIME-001. No dependency cycle or image/runtime reverse dependency was added.
- The release manifest must record PostgreSQL's exact immutable image identity (version, platform
  and manifest/resolved digests). Application refresh must preserve it. Major/minor/rebuilt-image
  changes require separate explicit maintenance, reviewed compatibility and paired backup/recovery
  evidence; application image refresh cannot silently update PostgreSQL.
- Verified the current [Dockhand label documentation](https://dockhand.pro/manual/#container-labels-available)
  and [environment update policy](https://dockhand.pro/manual/#checking-for-updates). Require
  `dockhand.update=false` on frontend, backend and PostgreSQL, inspect actual deployed labels, and
  check the selected environment's **Automatically update containers** toggle as well as per-container/
  stack policy. Keep Git auto-sync/unguarded webhooks off; labels are not a general stack-deploy lock.
  The chosen pinned runtime version still needs live acceptance in BETA-RUNTIME-001. No current
  Dockhand environment was changed. Excluded-container checks/badges may be suppressed, so release
  notification comes from the separate manifest workflow.
- Recorded pending COLLECTION-VISUAL-002 operator acceptance, planned stable RELEASE-001, and exact
  search/map/label IDs/statuses in the audit. No existing feature status was promoted.
- Recorded AGENTS.md's retirement `AGENT_ID` enforcement discrepancy as separate planned
  WORKFLOW-RETIRE-AUTH-001. B1–B4 do not change that authorization boundary.

## Verification and resource preservation

| Command/check | Result |
| --- | --- |
| Initial unchanged-source empty-directory and unsafe-state baseline | 2 passed |
| Focused B1/B2/original empty-directory, path/evidence/volume and lifecycle probes | 7 passed; then full suite exercises the final independent file/FIFO cases |
| `FLORABASE_RETIRE_DOCKER_SMOKE=1 make test-agent-workflow` | 60 passed, **no skips**, including all 3 real Docker smoke methods |
| `make test-feature-workflow test-workflow-helpers test-workflow-resources test-environment-workflow` | 46 lifecycle + 14 resource + 35 environment tests passed; shell helper checks all passed |
| `make workflow-check AGENT_ID=codex-beta-foundation-001` | Passed policy checks, Ruff lint/format (30 files), strict mypy (19 + 5 files) |
| Feature graph, local documentation links, retained statuses and whitespace | 132 valid features; non-beta existing entries/statuses unchanged; local links and whitespace pass |
| Resource snapshots before/after the full smoke-enabled suite | Exactly **6 containers / 8 networks / 17 volumes** unchanged; existing container image/running/start/restart/mount fingerprints unchanged; zero retirement smoke containers remain |
| `make verification-plan FORMAT=json` | FULL required; diagnostic plan only, **not executed** |

Non-secret local logs/probes are ephemeral under `/tmp`: `beta-qa-red-real.log`,
`beta-qa-compatibility-failure.log`, `beta-qa-targeted.log`, `beta-qa-agent-suite.log`,
`beta-qa-adjacent.log`, `beta-qa-workflow-check.log`, `beta-qa-resources-before.json` and
`beta-qa-verification-plan.json`. Snapshot checks and targeted results were also returned in chat.
Real probes use `--pull=never`, `--network=none`, no persistent test volumes and exact cleanup targets.
No broad Docker cleanup, production environment change, source permission rewrite or schema/API change.

Known limits: Linux mountinfo and the local Docker filesystem model remain required; unknown custom
volume backing and unavailable evidence refuse conservatively. Docker inspection and Git deletion
are not one atomic transaction: operators must coordinate external writers, mount changes and container
starts after inspection. The documented retirement identity discrepancy is intentionally a separate
follow-up. Architecture/capacity, data onboarding, deployed Dockhand behavior, PostgreSQL pin selection,
backup/restore and release automation are future acceptance work, not claimed completed here.

Next: independent delta QA on this corrected tree. Only after it passes may the appropriate QA session
freeze source/index and run the policy-selected canonical gate. Do not push, open a PR, deliver, merge
or run real feature-finish from this request. No `verified` promotion or release approval is implied.

## Additional accepted limitations

Docker mount Source is path-based; stale or deliberately retargeted paths cannot always be detected.
Linux immutable files can still cause failed Git removal with orphaned directory state in exceptional
privileged environments. These limits do not change the accepted safeguards or the separate planned
WORKFLOW-RETIRE-AUTH-001 follow-up.
