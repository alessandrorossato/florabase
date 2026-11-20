# PORTABLE-COMPOSE-001 portable smoke hardening

This remediation belongs to the disposable runtime smoke criterion of `PORTABLE-COMPOSE-001`
in the [feature registry](../../features.json). The entry remains `implemented` and `certify`.
The worktree was initialized at `origin/main` `fdc75e83fa8818cab791ed82cbba65f4f97db7ae`, claimed
as `terra-portable-smoke-hardening` (`75417096b4f5`), and fast-forwarded to the approved ENG-02
parent `48cc11ead7a6438e6c14015889d2653c4e450349` (tree
`909477f467a5a7ccd236367de64c288c8187972a`). The original hardening commit
`ca73d2d141b6fb74ba45582c64b8559c76817905` (tree `c6ae8e3c750ba004c5ad2ced9a456392c68a12b5`)
is a direct child of that commit and is the parent of the HTTP follow-up.

## Release path

[Protected publication](../../../.github/workflows/beta-images.yml) and
[hosted rehearsal](../../../.github/workflows/beta-release-rehearsal.yml) share the
[publisher](../../../scripts/publish-beta-images.py). Its `SCAN/SMOKE` stage checks the exact
candidate images, including version labels, the installed backend package and frontend
`release.json`, in the paired-image smoke. It then runs the
[portable smoke](../../../scripts/smoke-portable-compose.py) against the rendered Compose asset.
The publisher supplies all three candidate references and the manifest Alembic head independently
of the asset. Compose must resolve each reference on both stacks. The portable smoke tests
production settings through the loopback binding, readiness, effective canonical origin and
secure session behavior. The existing ENG-02 status, header and cache policy matrix still runs.

The child exit status remains mandatory before asset validation and promotion. The portable
success marker follows all runtime checks and cleanup. Exceptions report the failed operation
without dumping Compose stdout or stderr, response bodies, query parameters, credential values
or the actual contents of a mismatched header.

## Disposition of the 15 operational assertions

| Assertions in ENG-02 parent | Explicit checks in this correction |
| --- | --- |
| Service set and process UID (2) | Both rendered service sets and per-service references match the expected inputs. Each running UID is checked. |
| Initial and post-restart database head (2) | Require the exact image Alembic head and each SQL revision against the manifest. |
| Foreign revision refusal, failed-upgrade rollback revision and sentinel table (3) | Require the refusal statuses and diagnostics, preserved SQL revisions and unchanged sentinel table. Also check the head after recovery. |
| Access evidence and exclusion of logged secrets (2) | Each of frontend and backend must log both credential requests without the canary, passwords, CSRFs or session tokens. |
| Offline reset confirmation and exclusion of the reset password (2) | Require the commit confirmation and check both subprocess streams for the reset password. Login and revocation probes run after restart. |
| Original media after restart, after failed-upgrade recovery, in the restored stack and in the source after restore (4) | Compare bytes through authenticated HTTP on all four paths. Require the isolated restore's schema head too. |

Other false-PASS paths were implicit redirect following, empty or mistyped session fields,
unvalidated media paths, and zero or missing attachment verification evidence. The client now
checks the first HTTP response status and requires a JSON object, CSRF token and usable secure
cookie before accepting a session. The seeded media must have both expected local API URLs.
Backup requires custom-format `pg_dump` bytes, a media archive and exactly one verified file.
`pg_restore` and the attachment restore tooling still validate the payloads and must exit
successfully. The restored attachment count, digest verification and authenticated media retrieval
provide separate evidence. A required subprocess failure always propagates. An expected refusal
requires a failing application exit and the expected diagnostic marker.

## Original focused controls

`PortableSmokeEvidence` and the inherited `PortableSmokeHeaders` run via `make test-beta-images`,
which is a dependency of `workflow-check` in the canonical FULL plan. That target runs the focused
controls directly and relaunches them under both optimization modes. The tests use `unittest`
checks that remain active under optimization. The 13 focused tests passed with Python 3.14.4 in
all three invocations (`python3`, `python3 -O`, `PYTHONOPTIMIZE=1 python3`). They include valid
stack, HTTP, cookie and subprocess evidence and isolated negative cases for wrong services,
references, UIDs and revisions, authentication, log and reset evidence, lost media, empty or
invalid backup and restore evidence, unexpected HTTP including a redirect to success, missing
fields, failed subprocesses and publication propagation.

The offline targets also passed 75 release tests plus four tool-lock tests, and 63 beta
runtime tests on host Python plus 51 controller tests on Python 3.8.20. Ruff 0.17.4 lint and format,
strict mypy 2.4.1, the 168-entry feature graph, documentation links, disclosure and diff checks ran
without FULL. The graph still reports the eight pre-existing release candidate blockers.

## Historical disposable runtime

On 2026-11-20, before `ca73d2d` was committed, the publisher's `run_portable_smoke` launched the
original hardening worktree's executable code under `PYTHONOPTIMIZE=1` while holding the shared
verification capacity lock. The disposable build used the repository's runtime Dockerfiles. The
harness substituted its own local image tags into the rendered portable asset and inspected their
IDs. Registry digest and published-candidate acceptance remain pending.

- The wrong-head control initialized its fresh database, failed the exact Alembic head check,
  exited `1`, and emitted no portable success marker. It retired both
  `florabase-portable-09864485733a` projects and removed their temporary bind root.
- The valid control exited `0` after fresh install, bundled header/cache probes, credential
  rotation and offline reset, media and schema persistence, failed upgrade and recovery, and
  isolated PostgreSQL and media restore. It retired both `florabase-portable-27e2bdc2d20e`
  projects and removed their temporary bind root before success.
- Exact-project inventory confirmed zero containers, networks, volumes or images for all four
  projects. `florabase-verification-build-16b7265889b0` removed its three owned images and retained
  shared BuildKit cache. An earlier development run passed the same positive and negative paths
  under separate project prefixes. The identities above belong to the original, pre-commit smoke.

## HTTP client correction after independent QA

SOL accepted the operational checks, publisher contract, optimization-resistant validation and
cleanup behavior, and held the source on two HTTP client findings. The follow-up counts session
cookie definitions before parsing a single field. It rejects duplicates in separate or combined
fields, missing or malformed security attributes, and host-prefix domain attributes. It leaves
unrelated cookies alone and installs the session token and CSRF value only after validation.

HTTP protocol exceptions while opening or reading a response now produce a short diagnostic with
exception chaining suppressed. Deterministic fixtures exercised a malformed status line, a truncated
body, and a body-read exception containing a synthetic marker. All failed subprocesses exited
non-zero and their captured tracebacks omitted the marker. Expected HTTP errors still return their
body and headers, using status access compatible with Python 3.8.
The same fixtures reproduced both findings against the uncorrected parent.

All 16 focused tests passed with Python 3.14.4 in normal mode, with `-O`, and with
`PYTHONOPTIMIZE=1`. The existing optimized launcher discovered the new tests in both child runs.
`make test-beta-images` passed 78 release and four tool-lock tests. `make test-beta-runtime`
passed 63 host tests and 51 pinned Python 3.8.20 controller tests. The three new shared-client
regressions also passed directly on that Python 3.8.20 image. Ruff, strict mypy, disclosure,
documentation links and diff hygiene passed.

The historical runtime above predates the HTTP correction. SOL's focused confirmation is pending.
Independent Docker verification of the corrected client on the integrated candidate must still
exercise session issuance and the full portable smoke on the digest-bound assets. Canonical FULL,
formal acceptance and G-SEC remain pending.

## Strict session-cookie validation

Final independent QA accepted the HTTP protocol diagnostics and held only on session-cookie
attribute parsing. Both reported whitespace-separated assignments reproduced on `6361844`.
The follow-up validates the raw cookie once against the pinned backend serializer's output. It
requires an unquoted URL-safe token, both bare security flags, `Path=/`, `SameSite=strict`, and a
positive decimal `Max-Age`. Each complete semicolon-delimited field is validated, including its
boundaries and uniqueness, before the session and CSRF state changes. Attribute order, casing,
horizontal whitespace at field boundaries, and unrelated cookies remain supported.

The table-driven matrix checks both bypasses, reversed and duplicate assignments, malformed or
missing attributes, tabs and vertical whitespace, quoted values, and valid issuance. Every rejected
response preserves the previously installed credentials. All 16 focused tests passed with normal
Python, `-O`, and `PYTHONOPTIMIZE=1`, including the approved HTTP diagnostic cases. The existing
launcher passed, along with 78 release tests, four tool-lock tests, 63 host controller tests,
and 51 pinned Python 3.8.20 controller tests. Four shared HTTP client tests also passed directly
on Python 3.8.20. Ruff, strict mypy, links and diff checks passed.

SOL's cookie-only confirmation and independent Docker verification on the integrated candidate
remain pending. The prior runtime evidence retains its original provenance.

## Review and integration

The ENG-03 comparison used the requested `c4a222ecf7085aee5ad7b57080870fd67ecb542b`. The live ref
was also observed at `c43b4161275181b45e33ebc86dbe08794c405e34`, which adds a test-only correction.
The only changed-path overlap with this increment is `docs/progress.md`. Batch 07's certification
source and session recovery and mobile QA tips have no changed-path overlap. Its `PORTABLE-COMPOSE-001`
evidence map covers the same criterion and should reference this record when combined evidence is
assembled. The performance and Golden pin sources touch `docs/progress.md` as well.

After Batch 07, independently review this delta against ENG-02, then integrate ENG-02 before its
child and preserve their provenance in the integration record. If ENG-02 has already landed by
squash, bring forward only the corrective delta and verify the combined tree. ENG-03 needs its own
review and approval. Run fresh FULL and the exact-candidate hosted rehearsal after integration,
then complete formal release acceptance and G-SEC. Source publication and delivery are operator
actions.

Outside this remediation, the sibling image-only smoke retains an embedded `assert` for excluded
development tools and emits its marker before its cleanup context exits. Its exit status still
gates the publisher. The separate controller runtime smoke retains three optimization-sensitive
JSON shape assertions and a redirect-following HTTP status probe. Test loader invariants and
application assertions were outside the operational inventory.
