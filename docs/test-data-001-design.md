# TEST-DATA-001 deterministic golden dataset

2 November 2026 · `feat/test-data-001` · implementation candidate with independent QA corrections applied.

Reviewed SMOKE baseline: `70a1b1ae037cdfce7fa494096bbb557e266cfe7df5780183acda2c7d8dbef967` (schema `20261013_0042`, volume 12).

## Result of this increment

The SMOKE profile generates, validates and retires isolated synthetic copies from source. STRESS is
declared in the manifest and refuses until reviewed. [TEST-DATA-002](test-data-002-design.md) later made
COMPREHENSIVE executable and resolved some gaps listed below. No environment lifecycle or restore
workflow changed, and no Review, UAT, Sourcing, Preview, DEV or production command can reach this code.
Later, [MULTIBRANCH-UAT-001](development-workflow.md#uat-instances-parallel-per-worktree) added exactly one
persistent target, per-worktree UAT instances (`golden_uat`, workflow mode `uat-instance`); the copy
lifecycle and every other environment remain refused. That guard reads the workflow mode and project
from the environment; the host helper proves Docker identity first, and any other container would also
need a `golden_uat` database and user plus a mounted runtime, so a forged variable still fails closed.

```bash
make golden-dataset-check   # Disposable Compose project; proves generation, isolation and validation
```

Inside that disposable runner the operations are:

```bash
python /review/golden_dataset.py create-copy --copy golden_a   # New DB, Alembic head, own media root
python /review/golden_dataset.py generate --copy golden_a      # Idempotent; validates before success
python /review/golden_dataset.py validate --copy golden_a          # Domain validation only
python /review/golden_dataset.py verify-baseline --copy golden_a   # Domain + reviewed baseline
python /review/golden_dataset.py digest --copy golden_a            # Diagnostic: current digest
python /review/golden_dataset.py retire-copy --copy golden_a   # Drops the DB and removes its media
```

The coverage matrix is generated from the manifest: [COVERAGE.md](../scripts/fixtures/golden/COVERAGE.md).
It shows each scenario's runnable and still-planned profiles separately.

## Architecture

| Layer | File | Responsibility |
| --- | --- | --- |
| Manifest | `scripts/fixtures/golden/scenarios.json` | Seed, fixed anchor date, profiles, scenarios, invariants, reviewed pins |
| Plan | `scripts/golden_plan.py` | Pure and stdlib-only: scenario functions produce an ordered node list and its digest |
| Runtime | `scripts/golden_dataset.py` | Guards, copy lifecycle, node execution, validation and canonical digest |
| Executor | `review_dataset_v5.apply_node` | Existing node interpreter over owning services, extracted without behavior change |
| Evidence | `backend/tests/integration/test_golden_dataset.py` | Runs in the existing disposable integration workflow, so also in CI |

A copy is a dedicated database `golden_<name>` plus a dedicated media root
`/tmp/florabase-golden/golden_<name>` beside disposable test PostgreSQL. Its schema always comes from
Alembic and its data always comes from the plan. Nothing is cloned and no source is shared or mounted
writable: the plan is read-only input.

## Decisions

- **Reuse the owning services.** Every record goes through the same services and schemas as the API,
  so the domain rules apply. Several first drafts were rejected by those rules (a retired Supplier on a
  new Order, a stated remainder on exact stock) rather than producing unreachable states.
- **Reuse v5's plan shape** (`$ref` nodes, logical keys, ledger beside the media). v4 and v5 themselves are
  not imported as data: v4 anchors schedules to the seed day and both are tied to their environment guards.
- **Stable identifiers are scenario keys.** Each copy's ledger maps `seed:seed-quantity-states/unknown`
  to that copy's genuine UUIDv7, as ADR 0004 requires. Database ids and wall-clock timestamps differ per
  copy by design. Forcing ids would mean patching every model default for no current requirement.
- **Determinism is defined by a canonical digest.** See the baseline contract below for exactly what it
  normalizes. A UUID no table owns is counted rather than hidden. A test compares this digest's tables
  with `pg_tables`, so a new table cannot be missed.
- **Per-scenario randomness.** Each scenario seeds from `seed:scenario-id`, so adding a scenario moves no
  other scenario's values. Read checks pass the fixed `anchor_date` explicitly.
- **Generation has its own clock.** While generating, application modules read a plan-derived clock: node
  *n* runs at `anchor_date` 12:00:00 UTC plus *n* seconds. Services stay unchanged, and later nodes stay
  strictly later, which reversal eligibility and History depend on. Clock reads inside one node share an
  instant, so their internal order cannot matter. The real clock returns before final validation.
- **Atomic graph, then explicit finish.** A session guard refuses any commit during the graph phase, so a
  failure leaves an empty database and removes that run's media, and retry is allowed. Primary photos and
  external covers use services that always commit, so they run afterwards. A failure there leaves a
  `failed`, not clean, ledger that is never reported as ready and must be retired rather than repaired.
- **Fail closed on target.** Only `FLORABASE_ENVIRONMENT=test`, the disposable flag, no workflow mode, a
  `golden_` database, the exact matching media root, the connected database's real name and the code's
  Alembic head are accepted. A populated collection or foreign media is never adopted.
- **No provider dependency.** The taxon link uses the provider through a mock transport, as UAT v4 does.
  External media and covers use `example.invalid` and are never fetched. Real network calls are refused at
  runtime through httpx and `socket.create_connection`.

## Copy lifecycle locking

Every action (`create-copy`, `generate`, `validate`, `verify-baseline`, `digest`, `retire-copy`) takes one
exclusive, non-blocking `flock` on `/tmp/florabase-golden/.locks/<copy>.lock` and holds it for the whole
action, including `generate`'s final validation and `create-copy`'s Alembic child.

- The name is validated by `COPY_NAME`, and the configuration guard runs, before the lock file is created
  and before any database connection, so a refused target never reaches the lock directory.
- `.locks` cannot be a copy name and retirement removes only `<root>/<copy>`. The lock file is never deleted
  or replaced, so every action on a name contends on the same inode, including across retire and re-create.
- Each CLI process acquires it once, in one place, so nothing nests. A killed holder releases it through
  the kernel. The descriptor is not inherited by the Alembic child.
- A loser fails at once with exit 75 and changes nothing. Different names never contend. Reads are exclusive
  too: nothing needs concurrent reads of one copy yet, and one rule is easier to reason about.
- An action arriving after a completed retirement is an ordinary refusal (`media root is missing`, exit 1).
  A retirement interrupted between dropping the database and removing media is finished by rerunning it.

These locks protect against other golden actions only. They do not stop a direct SQL client, and retirement
still force-drops any such connection.

## Validation and baseline verification

These are two different claims, and only the second says a copy is the reviewed dataset.

| Command | Question | Exit codes |
| --- | --- | --- |
| `validate` | Is this copy internally valid? | 0 valid, 1 invalid |
| `verify-baseline` | Is it also exactly the reviewed baseline? | 0 `baseline-verified`, 1 `domain-invalid`, 3 `invariant-valid-baseline-modified`, 4 `baseline-unavailable` |
| `digest` | What does this copy contain now? | 0, even on a damaged copy; it claims nothing |

Any command can also exit 75 (busy) or 1 (refused). `validate` and `digest` report `"baseline": "not-checked"`.

**Domain validation** returns every problem it finds. It checks ledger state and plan identity, every managed
record, each scenario's invariants, attachment files by size and SHA-256, unmanaged files, external media
staying offline and unfetched, synthetic labels, pinned per-table counts, and pinned results from the real
read services (dashboard, directories, History, Media, Schedule, provenance map). It deliberately does not
pin every value, so a changed note can be valid.

**Baseline verification** compares the copy with `profiles.smoke.expected.baseline` in the version-controlled
manifest. The expected value is never computed from the target or written by any command. It applies only to
its recorded volume, plan digest and schema revision; anything else is `baseline-unavailable`, not a pass.

The digest covers all rows of every modelled table, including canonical geography and the provider cache;
the SHA-256 of every file under the media root, managed or not; and which logical row each scenario key names.

### Normalization contract

| Treatment | Field | Why |
| --- | --- | --- |
| Per-table ordinal (canonical places by source code) | UUIDs | Genuine per-copy UUIDv7 values; relationships survive as ordinals |
| Excluded | `users.password_hash` | Salted per copy |
| Excluded | `attachments.storage_key` | Random per copy; file bytes are hashed separately |
| Excluded | `auth_sessions`, `login_throttles` (all timestamps) | Session state; a test requires them to be empty |
| Excluded | `app_metadata.created_at` | Unmodelled migration default, the only wall-clock timestamp left; a test pins this as the whole list |

Nothing else is normalized. **Every other timestamp keeps its exact value**, as UTC, so copies compare equal
across timezones. There is no rule for `DateTime` columns as a type: a new column is retained by default, and
if it were not reproducible, copies would differ and the tests would fail.

### Timestamp classification

Audit of every timestamp column, read from PostgreSQL. All are retained.

| Group | Columns | Behaviour they drive |
| --- | --- | --- |
| Refresh | `external_taxon_links.last_refreshed_at`, `external_provider_cache.fetched_at` | Stale or fresh; provider cache TTL |
| Refresh record | `external_taxon_links.linked_at`, `.last_refresh_attempt_at`; `media_assets.fetched_at` | Shown in API responses; `fetched_at` also marks a fetched external asset |
| Transition | `suppliers`, `locations`, `geographic_places` `.retired_at`; `scheduled_activities.completed_at`, `.cancelled_at`; `harvest_seed_lot_conversions.reversed_at` | Availability rules and the History timeline |
| Confirmation | `wfo_links`, `wcvp_links` `.confirmed_at`; `native_range_applications.applied_at`; `users.password_changed_at` | Domain records; the first three are empty until those scenarios exist |
| Record time | `created_at` and `updated_at` across domain tables | See below |

`created_at` and `updated_at` are not merely technical here, so they are not on the allowlist. They provide the
History fallback time, list ordering, reversal eligibility (`plant.updated_at > receipt.created_at`) and
optimistic concurrency tokens.

Every stored timestamp comes from the plan except canonical geography, which has a fixed migration literal.

**Updating the pin.** A new migration or plan change makes `test_fresh_copies_match_the_reviewed_baseline`
fail, and its message prints the current digest. Review what changed and update the pin by hand in the same
change. This costs every migration one small manifest edit; that is the price of explicit schema compatibility.

## Performance and storage

Measured once on the development machine inside the disposable tmpfs PostgreSQL. Background volume is the
experimental `volume` parameter over SMOKE scenarios; it is not the COMPREHENSIVE profile.

| Volume | Nodes | Rows | Generate | Validate | Digest | Database | Media |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 12 (SMOKE) | 184 | 205 | 0.66 s | 0.25 s | 0.02 s | 12.56 MB | 948 B |
| 200 | 770 | 791 | 1.08 s | 0.16 s | 0.03 s | 12.79 MB | 948 B |
| 1000 | 3322 | 3343 | 3.50 s | 0.62 s | 0.08 s | 13.35 MB | 948 B |

Creating a copy takes 3.3–4.2 s, nearly all of it migrations and canonical geography, which also account
for almost all of the 12.5 MB baseline. Retiring takes about 2 s. These figures exclude real image volume, so
they do not predict the media cost of a representative COMPREHENSIVE profile.

### Test module runtime

Each CLI subprocess costs about 1.6 s importing the application, against 0.01 s for bare Python, and that
dominates the module. `--copy` used to re-exec and import twice; it now rebuilds settings in process. Losing
contenders and teardown run in parallel, and baseline negatives avoid repeating checks. Copies stay fully
independent and every assertion still goes through the real CLI.

| Measure | Before corrections | After corrections |
| --- | ---: | ---: |
| Whole module | 172 s, 17 tests (2 runs) | 260 s, 25 tests (2 runs) |
| With the timestamp tests, including v5 | — | 315–332 s, 32 tests (2 runs) |
| The 11 test phases present in both | 146 s | 133 s |
| `validate` | 3.70 s (1 sample) | 2.93 s (median of 5) |
| `digest` | 3.57 s (1 sample) | 2.43 s (median of 5) |
| `generate` on a ready copy | not measured | 2.80 s (median of 5) |

The module got longer overall because the concurrency and baseline tests are new; each needs real processes.

The "Before" and "After" columns predate the timestamp correction.

The remaining cost is one application import per process. Avoiding it means lazy imports across the runtime
or a long-lived runner that would stop testing the real CLI, so that refactor is deferred. Migrating each
copy is kept: a template database would be a clone, which this design rules out.

## Remaining gaps

- COMPREHENSIVE and STRESS are not generated. Their domain weighting needs review first: raw row count
  here came from one uniform background mix and says nothing about coverage.
- Planned scenarios are listed in the coverage matrix: WFO links (need the optional pinned index),
  WCVP proposals, local covers, media copies, bulk moves, import/export round trip, collection-produced
  packets outside conversion, and terminal Journal Events.
- Reads are checked through services, not over HTTP or in a browser.
- Timestamps are anchored in the past, so a link read today is stale on the real clock, as Schedule states
  already are relative to today. A future environment that needs a fresh copy must decide this explicitly.
- Clock reads in a module imported for the first time during generation would miss the generation clock. Today
  there are none; it would fail as differing copies rather than pass silently.
- The module's runtime, about 5 minutes, adds to CI integration time. Trimming it further needs the deferred import refactor.
- A corrupt ledger file makes `digest` and `validate` fail rather than report around it, which is closed but
  less useful as a diagnostic.
- Python's `random` and Pillow's PNG output are stable within the pinned image, but only tests compare them
  across copies. A base-image upgrade can legitimately change the plan pin or media bytes, which the pin
  reports for review.
- `uuid_labels` depends on UUIDv7 process monotonicity. A future parallel generator would need another key.

## Operator decisions needed

Adopting a copy in Feature Review, UAT or performance testing means a new environment lifecycle, so it was
deliberately not built here. Each of these needs your design review:

1. Whether copies get their own Compose project per copy, or a reset of existing Review/UAT.
2. Whether the Review, UAT or performance guards should accept a `golden` mode, since today's guard is
   TEST-and-disposable only and those environments are development-mode, persistent or both.
3. Whether a snapshot artifact is wanted at all. Generation from source takes seconds at these sizes, so I
   recommend not adding snapshots until a measured COMPREHENSIVE profile with real media justifies them.
