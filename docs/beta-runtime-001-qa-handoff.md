# BETA-RUNTIME-001 — independent infrastructure QA handoff

Implementation claims below are the author's; QA treats them as claims and reproduces them. Scope,
design and operator procedures are in the [runbook](beta-runtime-001.md); the recorded disposable
run is [beta-runtime-001-evidence.json](beta-runtime-001-evidence.json).

## Reproduce

```bash
make test-beta-runtime
make smoke-beta-runtime
make workflow-check
```

`test-beta-runtime` runs the offline stack contract, controller rules and disclosure scan under the
host Python and under the pinned Python 3.8.20 image. `smoke-beta-runtime` needs native linux/amd64
Docker with privileged containers, about 8 minutes and network access for the first image builds and
for the checksum-verified Compose 2.20.1 download (cached under `~/.cache/florabase`). It must end
with `BETA_RUNTIME_SMOKE_PASSED` and `RESOURCE_CLEANUP_PASSED … residual_containers_networks_volumes=0`.

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

1. `make test-beta-runtime` passes `Disclosure.test_no_infrastructure_or_secret_disclosure`.
   It scans for private/CGNAT IPv4 addresses, concrete `*.ts.net` names, personal home paths, email
   addresses, private keys, access tokens and literal credentials.
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
