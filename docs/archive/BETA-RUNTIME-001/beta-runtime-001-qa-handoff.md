# BETA-RUNTIME-001 — independent infrastructure QA handoff

Implementation claims below are the author's; QA treats them as claims and reproduces them. Scope,
design and operator procedures are in the [runbook](beta-runtime-001.md); the recorded disposable
run is [beta-runtime-001-evidence.json](beta-runtime-001-evidence.json).

## QA corrections (round 1, reviewed `e1a708f`)

| Finding | Correction | Regression |
| --- | --- | --- |
| R1 P0 schema gate reusable by plain Compose | One-shot `schema-gate` removed. The backend entrypoint guard checks image head = `.env` release head = database revision on every start and fails closed. Its healthcheck re-reads the revision and stops a backend whose schema changed. | `StackContract.test_schema_guard_runs_inside_every_backend_start`, `test_guard_refuses_missing_expected_head`; smoke step `schema-guard` (running change, plain `up -d`, `docker restart`, recreation, restore) |
| R2 P0 retention traversal | Set identity is proven from the directory (syntax, real non-symlink dir, ownership/mode, containment, exact artifacts, checksums, metadata identity); invalid entries are never eligible; the target is re-proven before `rmtree`; the policy is range-checked | `Retention.*` (traversal, absolute, symlink, mismatch, tampered/missing metadata, bad sums, writable, policy, last set, idempotence, dry run); smoke step `retention-boundary` |
| R3 P1 arbitrary bind address | IPv4 loopback only at `init`, `.env` rendering and acceptance (superseded in round 2 by a literal Compose address) | `BindAddress.*`; smoke refuses `0.0.0.0`, `::`, `192.0.2.10` |
| R4 P1 static privacy list | The scan derives paths from Git: the diff against the feature merge base (committed, staged, unstaged) plus untracked files. Only added lines are scanned; the only exemption is the marked synthetic-fixture block. | `Disclosure.test_no_infrastructure_or_secret_disclosure`, `test_scope_is_the_whole_feature_diff` |

Against the reviewed controller,
`FLORABASECTL_UNDER_TEST=<e1a708f florabasectl.py> python3 scripts/test-beta-runtime.py --controller-only`
fails every R2 and R3 test. Its retention printed `removing ../../victim` and an absolute path outside
the backup root (disposable temp directories only). The reviewed `compose.yaml` still has the
`service_completed_successfully` gate that `test_schema_guard_runs_inside_every_backend_start` rejects.

## QA corrections (round 2, reviewed `fcd25bc`)

| Finding | Correction | Regression |
| --- | --- | --- |
| R3 P1 `FLORABASE_BIND_ADDRESS` interpolation | Literal `127.0.0.1` in `compose.yaml`; only the port is variable. The `--bind-address` option and rendered variable are removed; acceptance requires exactly 127.0.0.1. | `StackContract.test_hostile_bind_variables_cannot_widen_publication` (ambient, `.env`, `::`, hostile port, Compose 2.20.1 too); `BindAddress.*`; smoke `hostile-bind-environment` |
| R4 P1 staged-content bypass | The scanner reads Git objects: added lines of `base..HEAD`, `--cached` (index blobs), unstaged worktree vs index, and untracked files. It uses rename detection, skips deletions and refuses on any Git error. There is no exemption: patterns and samples are assembled so their own source never matches. | `Disclosure.test_staged_blob_is_scanned_even_when_worktree_is_clean` (Codex's exact case), `test_unstaged_worktree_is_scanned_when_index_is_safe`, `test_committed_untracked_rename_and_deletion`, `test_failed_git_reads_refuse`, `test_patterns_detect_synthetic_samples_and_not_their_source` |
| R2 retention TOCTOU | `remove_set`: no-follow root fd (controller-owned 0700), no-follow set fd, validation, identity check, rename to a tombstone inside the root fd, re-check, fd-based `rmtree`. The residual limit is documented in the runbook. | `Retention.test_directory_substitution_after_validation_fails_closed`, `test_symlink_substitution_after_validation_fails_closed`, `test_unprotected_backup_root_refuses_deletion` |

Against `fcd25bc`:
- `FLORABASE_BIND_ADDRESS=0.0.0.0` makes Compose 2.20.1 render `host_ip 0.0.0.0`; the corrected stack renders `127.0.0.1`.
- The reviewed scanner returns `[]` for a staged sensitive blob behind a safe worktree copy; the corrected one reports `staged notes.md:1`.
- The reviewed controller fails the directory-substitution, unprotected-root and bind tests.

Real-host blocker added: Engine < 28 loopback publication may be reachable from the same L2 segment.
An independent LAN reachability test and DSM protections are required before deployment.

## Reproduce

```bash
make test-beta-runtime
make smoke-beta-runtime
make workflow-check
```

`test-beta-runtime` runs the offline stack contract, controller rules and disclosure scan under the
host Python. It also runs the controller rules under the pinned Python 3.8.20 image; that image has
no Git, so the disclosure scan reports skipped there and the host run is the authoritative one. `smoke-beta-runtime` needs native linux/amd64
Docker with privileged containers, about 8 minutes and network access for the first image builds and
for the checksum-verified Compose 2.20.1 download (cached under `~/.cache/florabase`). It must end
with `BETA_RUNTIME_SMOKE_PASSED` and `RESOURCE_CLEANUP_PASSED … residual_containers_networks_volumes=0`.

Isolated procedure for a reviewer without access to the operator's Docker socket. Do not change
socket permissions or grant broad privileges; use a disposable machine or VM that you control.

1. Provision a clean linux/amd64 VM with any current Docker Engine, then add your account to its
   `docker` group. All tested runtime versions are nested: `docker:24.0.2-dind` and Compose 2.20.1
   run inside it.
2. `git clone` the repository and `git checkout <candidate commit>`; confirm `git status` is clean.
3. Run `make test-beta-runtime` and `make smoke-beta-runtime`. The smoke creates only resources
   labelled with its own run ID and removes them. Nothing touches other projects; it checks that
   host `florabase-prod` resources are unchanged.
4. The evidence written to `/tmp/florabase-beta-runtime-smoke.json` records `source.commit`, `tree`
   and `clean`; a run from a dirty tree prints a warning and is not evidence for a commit.

## Review focus

- Startup can never migrate: Compose schema-gate, maintenance-only `migrate`/`tools`, a fresh gate
  run per controller start.
- Promotion state machine: phases, journal, refusal rules (lock, drift, foreign volumes, PostgreSQL
  identity, unknown/ahead schema, unconfirmed migration), failure handling with writers kept stopped,
  `resume`/`abort`/`--after-failed`, and the interrupted replacement-restore guard.
- Recovery sets: quiescence, checksums, metadata, validation with recorded images, retention
  selection, restic export verified by restore, isolated restore never mounting live data,
  replacement restore preserving the failed data.
- Python 3.8 compatibility of `florabasectl.py` (DSM 7.2) and the Compose 2.20.1 feature set.
- Clean-host portability: the stack and controller must work on any unrelated linux/amd64 Docker
  host. No path, hostname, network or service outside the operator-chosen `--root` is assumed.

## Privacy and sanitization check (mandatory)

Florabase is public and portable, so nothing committed may describe a real installation. QA confirms,
for every new and modified file in the diff (`git status --short --untracked-files=all`):

1. `make test-beta-runtime` (host run) passes `Disclosure.test_no_infrastructure_or_secret_disclosure`.
   It derives the scope from Git: every path changed against the feature merge base (committed,
   staged, unstaged) plus untracked candidates, including `Makefile`, `.gitignore` and modified docs.
   It looks for private/CGNAT IPv4 addresses, concrete `*.ts.net` names, personal home paths, email
   addresses, private keys, access tokens and literal credentials. The only exemption is the marked
   synthetic-fixture block in the test itself. `FLORABASE_DISCLOSURE_BASE=<sha>` scans another range.
2. A manual read of the diff finds none of the following:
   - real LAN/Tailscale addresses, hostnames or domains;
   - names of the operator's other containers, stacks, networks or services;
   - usernames or machine-specific paths;
   - credentials, keys, certificates or backup destinations;
   - NAS hardware/resource inventories or container statistics;
   - logs or test artifacts from a real host.

   Paths such as `/volume1/docker/florabase` or `/srv/florabase` appear only as labelled, configurable
   examples. Origins are placeholders (`<node>.<tailnet>.ts.net`, `*.example.invalid`).
3. `docs/beta-runtime-001-evidence.json` holds only disposable-run facts: synthetic IDs, loopback
   registry digests, pinned public images, timings and booleans. It has no workstation capacity,
   kernel, user or path outside the disposable `/srv/florabase-runtime-smoke` volume. `preflight`
   output from real hosts stays on the host; commit only reviewed, sanitized screening.
4. Host configuration lives outside the repository under `--root`. The repository carries only the
   sanitized `deploy/beta/florabase.env.example`, and `.gitignore` excludes `deploy/beta/.env`,
   `reference.env`, `*.local.*`, `secrets/` and `state/`.
5. The public repository URL `github.com/alessandrorossato/florabase` and its GHCR package names are
   the project's published identity (already in `release/`), not private infrastructure.

## Known limits (not defects of this increment)

- There is no real-host evidence yet: OS/Python versions, the pinned Dockhand behavior, Tailscale
  Serve, a real reboot, the off-host destination and RPO/RTO. These belong to the operator before
  BETA-ACCEPTANCE-001.
- The default restic image is a new runtime-owned pin awaiting BETA-SECURITY-001 scanning.
- `restore-replace` and `restore-isolated` need the recorded image digests to stay pullable.
