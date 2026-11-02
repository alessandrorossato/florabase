# TEST-DATA-002 comprehensive golden dataset

2 November 2026 · `feat/test-data-002` · extends [TEST-DATA-001](test-data-001-design.md), which still
defines the architecture, locking, guards and baseline contract. Awaiting independent QA.

Reviewed COMPREHENSIVE baseline: `d2db9e9b75fba58e15aa35801d75f2682b277bf67f810680f6828dadce4e98c7`
(schema `20261013_0042`, volume 420). SMOKE's baseline `70a1b1ae…f967` and plan pin did not change.

## Result of this increment

```bash
make golden-dataset-check                 # SMOKE: the default, lightweight path
make golden-dataset-comprehensive-check   # COMPREHENSIVE: manual, in its own disposable stack
```

Inside a disposable runner, every lifecycle action from TEST-DATA-001 takes `--profile comprehensive`:

```bash
python /review/golden_dataset.py create-copy --copy golden_a
python /review/golden_dataset.py generate --copy golden_a --profile comprehensive
python /review/golden_dataset.py verify-baseline --copy golden_a --profile comprehensive
```

STRESS still refuses. No lifecycle, Compose, CI, DEV, production or Dockhand configuration changed, and no
application module changed. Coverage: [COVERAGE.md](../scripts/fixtures/golden/COVERAGE.md).

## What the profile contains

3,183 plan nodes produce 3,973 domain records (3,982 rows less `application_settings`, `users` and the
provider cache), plus 289 canonical places from migrations and 34 media files.

| Area | Rows | Area | Rows |
| ---: | ---: | ---: | ---: |
| Sowings | 538 | Botanical identities | 114 |
| Seed lots | 428 | Harvests, lines, stock, dispositions, conversions | 205 |
| Germination observations | 390 | Scheduled activities | 69 |
| Events | 845 | Orders / Suppliers | 50 / 24 |
| Operation receipts | 650 | Media assets / links / primary photos | 37 / 34 / 7 |
| Plants / PlantGroups | 212 / 137 | Locations / sites / custom places | 34 / 24 / 7 |
| Profiles / native ranges / revisions | 28 / 32 / 28 | WFO / WCVP / GBIF links | 9 / 4 / 6 |
| Saved views | 20 | Proposals / applications | 3 / 2 |

Two kinds of scenario build this, kept separate so coverage never depends on random draws:

- **Named coverage scenarios** (all 14 SMOKE coverage scenarios, plus 18 new) create each state on purpose
  and assert it with field invariants. All 140 are checked on every validation.
- **`comprehensive-volume-mix`** adds 420 seeded collection journeys weighted by pathway: direct purchase,
  or a packet that stays stored or gets sown; repeated attempts, failure and abandonment; germination curves;
  derived Plants and trays; Events, harvests, stored material; endings; scheduled work. Favourite species
  recur (a squared draw) and the catalogue keeps a long tail, so counts are not uniform.

SMOKE's uniform `volume-background` is not part of this profile; the weighted mix replaces it.

## Decisions

- **Real services, including the refusals.** A `refused` node runs a forbidden operation inside a savepoint
  and fails the run unless the owning service raises exactly the named error. All 18 are exercised on every
  generation, and a test proves such a node fails when a rule stops refusing or refuses differently.
- **Rejected drafts stayed rejected.** The services refused a kilogram seed weight, an Order on a gift
  packet, a primary photo on a Sowing, and more. Each draft was corrected; no service was changed.
- **Synthetic reference indexes, real source code paths.** WFO and WCVP confirmation, proposal and application
  read local SQLite indexes. The plan carries their content, and the reviewed builders write them to a
  per-run temporary directory, never the media root. Validation rebuilds them to read the taxonomy tree. The
  service requires the reviewed release's metadata, so the stored evidence names WFO 2026-06 and WCVP v15/v16
  while the taxa are fabricated: **this evidence is structurally real and botanically meaningless**.
- **External copies use the real save path.** Only `fetch_image`, the one network call, is replaced with
  fixed bytes. `deny_network` stays on. Validation allows a copy only on an asset whose plan declares one.
- **Thumbnails are managed files.** A file under `.thumbnails/` is accepted only if named for an existing
  asset and its current attachment hash. Domain validation does not check those bytes; the baseline does.
- **Deliberate deletions leave the ledger.** A node may name the earlier record it removes (`removes`), as
  an unlink does. Validation then expects that key to be absent rather than reporting it missing.
- **Reads kept apart.** `comprehensive_projections` holds this profile's pinned reads (taxonomy tree, lineage,
  search, lifecycle counts, History by category) so SMOKE's reviewed projection pin is unchanged.
- **One file.** The new scenarios stay in `golden_plan.py`, now about 3,200 lines, because it runs both as
  a script and an import and a split would register scenarios in a second module instance. Worth revisiting
  when STRESS arrives.

## Baseline contract: what changed

The contract in the TEST-DATA-001 design holds. Two additions, each visible only where this profile has data:

| Treatment | Field | Why |
| --- | --- | --- |
| Per-table ordinal, like an id | `wfo_links.version`, `wcvp_links.version` | Random per copy; a proposal's frozen evidence refers to it, and the relationship must survive |
| Fixed placeholder | `scheduled_activities.completion_fingerprint`, only where the linked Event has a destination | A SHA-256 of the request, which names a per-copy Location id |

The second was found by the digest itself: two copies differed in one row. Completing a `move` activity is the
real product path, so it stays in the plan. A test proves the exception is exactly one row wide and that every
other completion hash remains content. **Limitation:** tampering with that one hash is not detected.

**Updating the pin.** A new migration turns COMPREHENSIVE into `baseline-unavailable` (exit 4), never a false pass,
and does not break CI because this module does not run there. To re-pin, delete
`profiles.comprehensive.expected`, run `generate`, `validate` and `digest`, review what changed, and write the
values by hand. No command writes them. The plan pin itself is still checked by `make golden-dataset-check`, which
needs no generation, so an accidental plan change is caught in CI.

## Independent verification

Each run below is its own Compose project with its own tmpfs PostgreSQL. The first produced the pin.

| Evidence | Result |
| --- | --- |
| Copies in one stack: `PYTHONHASHSEED=1, TZ=UTC` and `PYTHONHASHSEED=2, TZ=Asia/Tokyo` | Identical digest; different UUIDs |
| Separate stacks, each verifying both copies against the pin | `baseline-verified` every time |
| SMOKE baseline beside a COMPREHENSIVE copy | `baseline-verified` |

Negative tests in [test_golden_comprehensive.py](../backend/tests/integration/test_golden_comprehensive.py)
all go through the real CLI unless noted:

| Damage | Detected as |
| --- | --- |
| WFO or proposal evidence, site notes, view name, harvest notes | Baseline, naming the table |
| Two Plants swap Locations (every count and field stays valid) | Baseline `table plants` only |
| Retirement cleared on a Location | `domain-invalid`: invariant and projection |
| Identity edited after confirmation | `domain-invalid`: the synonym projection changes |
| Stray thumbnail / altered thumbnail bytes | Unmanaged file / baseline `media_sha256` |
| Undeclared external copy (in process; a constraint stops doing it by SQL) | `external asset was fetched` |
| Timestamps only this profile populates (7 columns, in process) | Digest changes |
| SMOKE arguments on a COMPREHENSIVE copy, and the reverse | Refused; never adopted |
| Failure late in the atomic graph | Empty database, no objects, retry allowed |
| Failure in the committing phase | `failed`, not clean, never ready; must be retired |
| Contention during a held validation | Exit 75 at once for four other actions |

## Performance and resources

Two independent stacks of the final tree (one sample each), on the development machine, tmpfs PostgreSQL:

| Measure | Stack A | Stack B |
| --- | ---: | ---: |
| `generate` work, including its final validation | 8.9 s | 9.8 s |
| Whole `generate` process, with application import | 12.1 s | 12.8 s |
| `create-copy` (migrations and geography) | 4.5 s | 4.5 s |
| `validate` process | 6.0 s | 5.9 s |
| `digest` process | 2.7 s | 2.8 s |
| `verify-baseline` process | 5.0 s | 5.1 s |
| Peak RSS of `generate` | 214 MB | 214 MB |
| Database size | 14.3 MB | 14.3 MB |
| Media | 2.1 MB, 34 files | 2.1 MB, 34 files |
| Dedicated test module | 22 tests, 258 s | 22 tests, 266 s |

SMOKE's database is 12.6 MB by comparison.

The module runs 4 full generations: the two compared copies, one full graph for the atomic failure and one for
the committing failure. Everything else shares those copies or restores them after damaging them.

**Media cost is understated.** The largest fixture is a 1600×1200 JPEG with a smooth gradient texture, which
compresses far better than a photograph. These numbers do not predict a collection of real images.

## CI recommendation

Do nothing to required CI. `pytest -m integration` names no file, so the module skips itself. A test in the SMOKE
module runs that same kind of selection and fails if it ever stops skipping. Required integration gains that test
(one extra pytest collection) and plan-level checks with no database. That addition was not timed on its own: the
SMOKE module took 350 s in this run, and its earlier recorded runs vary too much to isolate the difference.

**Proposal for your approval, not implemented:** a separate `golden-comprehensive` job in `ci.yml`, triggered by
`workflow_dispatch` and a weekly `schedule`, calling `make golden-dataset-comprehensive-check`. It would never be a
required check. At about 4.5 minutes per run including stack setup, it catches dependency or base-image drift that changes bytes between
reviewed runs. Until then, run it by hand after any change to the plan, the digest, a migration or an owning
service's write path.

## Domain observations for review

Neither is changed here, and neither is pinned as a promise.

1. **Retired Locations accept new records through the owning service.** `require_location_for_scope` checks usage
   scope but not `retired_at`, so `create_seed_lot` accepted one in a draft of this plan. New Orders at a retired
   Supplier are refused, so this looks inconsistent. Not checked over HTTP or in the UI, which may filter them.
2. **A movement Event on a dead Plant is accepted.** Only reintegrated and reversed records refuse current-state
   Events. Transfer of a dead Plant is refused. This may be intended, for correcting a record.

## Coverage gaps and limitations

- **`import-export-roundtrip`** is still planned. It was not in this increment's scope and has no coverage here.
- **Editing paths are thin.** Records are created in their final state, or moved by Events and operations. Identity,
  Schedule and external-link updates are the only corrections exercised, so few rows have `updated_at` far from
  `created_at`. `update_seed_lot`, `update_sowing`, `update_plant` and Event edits are not used.
- **`media-corrupted-copies` became `media-external-copies`.** A failed fetch stores nothing, so there is no
  persistent state to represent. Corruption is covered by the media negatives instead.
- **Runtime-only unavailability is not stored data.** "Taxonomy source unavailable" and a missing index depend on
  the deployment, not the copy. Interrupted copy cleanup, a pending-delete attachment, also needs a crash to reach.
- **WCVP and WFO taxa are fabricated** behind real release metadata, as above, and the Schedule `move` fingerprint is
  normalized. An enrichment demo on a copy would show those names.
- **Reads go through services**, not HTTP or a browser. Nothing here says a page renders 3,000 records well.
- **Observed on one calendar date and machine.** Timestamps are anchored in the past, so links read as stale on the
  real clock, as TEST-DATA-001 records. A Pillow or base-image upgrade can change media bytes and needs a re-pin.
- **Real species names** appear in the catalogue for realism. All profiles, ranges and provenance about them are
  synthetic, and no identity label check enforces a `Golden` prefix, because scientific names are not labels.

## Next step, separately: Review and UAT

COMPREHENSIVE is deliberately not wired into any shared lifecycle. The operator decisions in the TEST-DATA-001
design still stand, and this work informs them:

1. **Snapshots stay unjustified at this size.** Create and generate together take about 16 s, so generating from
   source is still cheaper to reason about. Re-measure with real image volume before reconsidering.
2. **A guard decision is required.** Today's guard accepts only `FLORABASE_ENVIRONMENT=test` with the disposable
   flag, while Review and UAT are development-mode, persistent or both. Accepting a `golden` mode is a new lifecycle.
3. **Synthetic indexes would need thought there.** Generation builds them per run and discards them. A long-lived
   environment reading the taxonomy tree would need the same index provisioned, or those links read as unavailable.
4. **Fresh timestamps.** Whether a copy for humans should be anchored near today needs deciding; the pinned anchor
   makes all Schedule states and link freshness read as old.
