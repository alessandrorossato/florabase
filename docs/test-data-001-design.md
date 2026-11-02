# TEST-DATA-001 deterministic golden dataset

2 November 2026 · `feat/test-data-001` · implementation candidate awaiting operator review.

## Result of this increment

The SMOKE profile generates, validates and retires isolated synthetic copies from source. COMPREHENSIVE
and STRESS are declared in the manifest and refuse until reviewed. No environment lifecycle or restore
workflow changed, and no Review, UAT, Sourcing, Preview, DEV or production command can reach this code.

```bash
make golden-dataset-check   # Disposable Compose project; proves generation, isolation and validation
```

Inside that disposable runner the operations are:

```bash
python /review/golden_dataset.py create-copy --copy golden_a   # New DB, Alembic head, own media root
python /review/golden_dataset.py generate --copy golden_a      # Idempotent; validates before success
python /review/golden_dataset.py validate --copy golden_a
python /review/golden_dataset.py digest --copy golden_a
python /review/golden_dataset.py retire-copy --copy golden_a   # Drops the DB and removes its media
```

The coverage matrix is generated from the manifest: [COVERAGE.md](../scripts/fixtures/golden/COVERAGE.md).

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
- **Determinism is defined by a canonical digest.** Every table is hashed with UUIDs replaced by a table
  ordinal (UUIDv7 is monotonic within the generating process), timestamps reduced to present or absent,
  and secrets, session state and provider-cache timing excluded. A UUID no table owns is counted rather
  than hidden. A test compares this digest's tables with `pg_tables`, so a new table cannot be missed.
- **Per-scenario randomness.** Each scenario seeds from `seed:scenario-id`, so adding a scenario moves no
  other scenario's values. Time is the fixed `anchor_date`; read checks pass that date explicitly.
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

## Validation

`validate` returns every problem it finds, and any problem fails the run. It checks ledger state and plan
identity, every managed record, each scenario's invariants, attachment files by size and SHA-256, unmanaged
files, external media staying offline and unfetched, synthetic labels, pinned per-table counts, and pinned
results from the real read services (dashboard, directories, History, Media, Schedule, provenance map).

## Performance and storage

Measured once on the development machine inside the disposable tmpfs PostgreSQL. Background volume is the
experimental `volume` parameter over SMOKE scenarios; it is not the COMPREHENSIVE profile.

| Volume | Nodes | Rows | Generate | Validate | Digest | Database | Media |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 12 (SMOKE) | 184 | 205 | 0.66 s | 0.25 s | 0.02 s | 12.56 MB | 948 B |
| 200 | 770 | 791 | 1.08 s | 0.16 s | 0.03 s | 12.79 MB | 948 B |
| 1000 | 3322 | 3343 | 3.50 s | 0.62 s | 0.08 s | 13.35 MB | 948 B |

Creating a copy takes 3.3–4.2 s, nearly all of it migrations and canonical geography, which also account
for almost all of the 12.5 MB baseline. Retiring takes about 2 s. The test module itself takes minutes
because each subprocess imports the application. These figures exclude real image volume, so they do not
predict the media cost of a representative COMPREHENSIVE profile.

## Remaining gaps

- COMPREHENSIVE and STRESS are not generated. Their domain weighting needs review first: raw row count
  here came from one uniform background mix and says nothing about coverage.
- Planned scenarios are listed in the coverage matrix: WFO links (need the optional pinned index),
  WCVP proposals, local covers, media copies, bulk moves, import/export round trip, collection-produced
  packets outside conversion, and terminal Journal Events.
- Reads are checked through services, not over HTTP or in a browser.
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
