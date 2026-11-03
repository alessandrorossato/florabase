# BETA-IMAGE-001 final reliability corrections

Second independent QA supplied by the operator reviewed `d661200` / tree
`f6da0e824349e254a05875d5344c6212f5c925de`: CONDITIONAL PASS; D2/D4 accepted.
This document supersedes earlier operational verdicts, preserving their historical evidence.
Feature remains `in_progress`. Publication and production deployment remain blocked.

## D1: identity and quiescence

Container inventory now requests full IDs. Failed inspection performs a successful fresh full-ID
listing, with conservative prefix matching for legacy short IDs; an existing container or unavailable
existence evidence refuses cleanup. Final residual inventory uses the same checks, so inspection
failure cannot become a false zero-resource success. A realistic short-ID regression fails against
`d661200` with `ResourceError not raised` and passes on the correction.

Release smoke Compose calls now run through `Disposable.run`, in an owned process group. On
interruption it marks quiescence unproved, sends SIGTERM, waits at most 30 seconds, and checks the
process group is gone before inventory/deletion. Timeout uses bounded kill/wait and explicitly refuses
automatic resource cleanup, preserving exact-run manual recovery. It never adopts a resource merely
because it uses an owned network. Ordinary success, foreign-user refusal and repeated cleanup remain
covered. This coordinates the release smoke's Compose calls; it is not a Docker-wide process killer.

Real probe `scripts/test-beta-lifecycle.py`: timed SIGTERM during a real Compose run; its owned
wrapper deliberately creates another exactly labelled container during shutdown. The final run
`florabase-workflow-smoke-2678fd1e30cf` removed **2 containers, 1 network, 1 media volume**, verified
zero residuals, passed repeated cleanup, and compared equal before/after foreign container inventories.
Initial probe versions exposed a reentrant Python wait in the probe wrapper; corrected to polling
outside the signal handler before the final passing run. Their owned resources were retired too.
The timeout/refusal regression leaves resources untouched, then proves exact recovery and repetition.

## Self-contained dependencies and D3

`make test-beta-images` calls `scripts/release-tools.py`. It creates a project-managed, interpreter-
specific venv **without ensurepip**, bootstraps pip 25.3 from its SHA-256-verified wheel, and installs
all five pinned validation packages/transitives with `--require-hashes --only-binary`, using a managed
wheelhouse. System Python and system packages are not modified. The existing Ubuntu host has neither
pip nor ensurepip; the requested target still passes without PYTHONPATH configuration.

Cache defaults to `/tmp/florabase-release-tools-<uid>-<contract/interpreter hash>`; set
`FLORABASE_RELEASE_CACHE` to another writable cache root for durable reuse. Preparation holds a lock.
Online preparation downloads only pinned, hash-checked wheels. Set `FLORABASE_RELEASE_OFFLINE=1`
to use only the verified cached bootstrap/wheelhouse; a missing cache fails explicitly. A fresh venv
from copied wheelhouse passed offline, while an empty offline cache refused. The cache is disposable;
there is no system pip installation or PEP 668 override. Hosted CI uses the same Make target, and the
privileged publication job uses the same launcher/environment. Artifact bundles include launcher,
bootstrap hash, requirements, schema and trusted inputs. No unverified dependency fallback exists.

Manifest tests now use genuinely distinct component digests. Complete validation rejects duplicate
index **or** platform digests as well as duplicate/foreign references, and compares build_inputs with
the trusted approved source's release/inputs.json (distributed inputs.json for artifact tools).
Consumers must obtain that trusted contract from the independently verified source/release, not from
an arbitrary unverified manifest. Existing schema/provenance/platform/source/PostgreSQL checks remain.

## Executed focused verification

- `make test-beta-images`: **12/12 pass**, without custom PYTHONPATH; warm offline and fresh offline
  environments also 12/12. Empty offline cache refuses rather than skipping checks.
- Resource regressions: **19/19 pass**, including realistic short IDs, vanished resources, unknown
  metadata, shutdown timeout refusal, exact recovery, repeats and foreign ownership/user protection.
- Real Compose SIGTERM/late-create probe: PASS as above. No Docker-wide prune.
- `make workflow-check AGENT_ID=codex-beta-image-001`: PASS, including repository workflow policy,
  Ruff/format and strict mypy for the new launcher/lifecycle helpers. Existing CI job/step protections
  remain intact; the earlier global pip installation step is removed.
- Actionlint on existing CI and beta publication YAML: PASS (shellcheck integration disabled).
- Version-asserted patched Pillow 13.0.0/certifi 2026.10.18 compatibility: **102/102 pass** across
  uploads/storage, remote media, provider/service, occurrence cache and tile API tests.
- Official unchanged acceptance path on intended pinned inputs: PASS, with normal registry pulls and
  descriptor checks, no Docker shim, offline override or relaxed assertion. Final scan-bound run
  `florabase-workflow-smoke-933229091268` retired 3 containers/1 network/1 media volume; exact owned
  image outputs were retired by its build owner. Health, migrations, authentication, private media,
  non-root and setuid/setgid checks remain part of the official smoke.
- Scans execute with the same HIGH/CRITICAL+secret policy and correctly fail promotion. Their scan
  owners report zero residual containers/networks/volumes. Shared upstream images/cache are retained.

Logs are `/tmp/beta-reliability-*.log`; source checks and staged whitespace are verified before commit.
No canonical FULL, push, PR, merge, publication, feature-finish or persistent deployment was run.
Independent focused delta QA must clear correctness before canonical FULL.

## Exact-artifact security and remaining acceptance

[Preserved raw reports, exact identities and individual advisory inventory](security/beta-image-001-reliability/README.md)
record fresh measurements matching the reviewer's reported counts:

| Image | CRITICAL | HIGH | Secret findings |
| --- | ---: | ---: | ---: |
| Backend | 2 | 36 | 0 |
| Frontend | 1 | 4 | 0 |
| PostgreSQL | 2 | 26 | 0 |

Reports are bound to actual saved-image configuration digests, native manifests and index digests.
Docker inspect identifiers may identify an index rather than a config; these are recorded separately.
The index is backed by BuildKit export metadata; native/config exports are cross-checked against the
retained raw scan configuration identities and recorded build-log hash. PostgreSQL uses the exact
selected immutable index/native descriptor, checked by official smoke. Local application artifacts
are dirty-source audit candidates, never approved GHCR release identities; a clean accepted commit
must be rebuilt for publication. Original scans and earlier batch evidence remain unchanged.

Fixed versions advertised by scanners are listed individually. Compatible rebuilt/pinned bases or
reviewed component patches remain required; runtime package presence alone does not prove or disprove
exploitability. PostgreSQL image maintenance remains separate from application refreshes. No base or
dependency was changed in this reliability correction. Per-advisory/package draft VEX assessments
expire on 2026-12-03 or any artifact change, whichever occurs first. All require explicit operator
approval; none is active or supplied to the scanner. The Debian zlib/MiniZip proposal still requires
exact binary confirmation; all other unfixed entries remain under investigation and blocking.

Synology DS224+ / Linux amd64 selection is retained. Actual runtime/capacity acceptance, protected
publication configuration, explicit release authorization, independent delta QA and canonical FULL
remain pending. Compose portability to compatible Linux PCs/VPSs is retained; Dockhand remains
optional. No Synology or other persistent environment was accessed.
