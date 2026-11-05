# Florabase Next M8: extended review environment and optional WFO (recommendation only)

**Status:** investigation only. Nothing was started, seeded, imported, reset, downloaded or
deleted. The UAT Preview, its volumes and the writer claim are unchanged.

## What the repository already supports

| Capability | Supported mechanism | Source |
| ---------- | ------------------- | ------ |
| Small manual-review dataset | UAT Preview, project `florabase-uat-preview`, fixture v4 plus additive extensions (66 managed records, 68 with WFO) | `make uat-preview-*`, `docs/development-workflow.md` |
| Isolated writable review environment | Feature Review, project `florabase-feature-review`, own DB `florabase_review`, own media and dependency volumes, owned by one worktree | `make feature-review-*` |
| Extended synthetic dataset | **Extended Botanical Review Dataset v5**: additive on v4 in Review only (248 creation nodes; totals include 43 SeedLots, 19 Plants, 7 PlantGroups, 16 Sowings, 37 identities, 18 Locations, 12 Orders, 10 Suppliers, 5 Harvests, 27 scheduled activities, 17 media assets; roughly 300–350 rows across the listed entities with v4). It refuses UAT, DEV, Sourcing, Stable Preview and production, makes no network request and uses a separate ledger | `make feature-review-extended-seed`, `docs/review/extended-botanical-dataset-v5.md` |
| WFO taxonomy source | Optional pinned WFO 2026-06 SQLite index in the worktree's ignored `backend/src/.source-cache/wfo-2026-06.sqlite` plus `.sha256` seal (394 MiB), provisioned explicitly from the pinned archive (132.6 MB, SHA-256 `75f1ad1f…1987`, CC0) by `florabase.taxonomy.snapshot` | `docs/taxonomy-003-handoff.md`, `backend/src/florabase/taxonomy/snapshot.py` |

## Constraints found

1. **Feature Review and UAT Preview both publish `127.0.0.1:15174`** (`PORTS` in
   `scripts/workflow_environment.py`). They cannot run at the same time. Running Review means
   stopping UAT first with `make uat-preview-stop`, which preserves UAT's database, media and
   dependency volumes.
2. **WFO is wired only into UAT.** `compose.uat.yaml` sets `FLORABASE_WFO_SNAPSHOT_PATH` (and the
   WCVP v15 path); `compose.review.yaml` sets neither, and the operator `.env` does not define it.
   The v5 dataset is Review-only. Today, **no supported environment combines v5 and WFO.**
3. **No WFO index exists on this machine** (no `.source-cache` in any checkout). Provisioning needs a
   download of the pinned archive, which needs your explicit approval.
4. **Review needs an owner** created interactively by you (`make feature-review-bootstrap-owner
   LOGIN=owner`, choosing a Review-only password). Seeding refuses without exactly one enabled owner.
   I will not create or use a personal password.
5. No Review volumes exist yet, and no other worktree owns Review.

## Recommendation

**Two steps; the second needs separate approval because it is an infrastructure change.**

### Step 1: extended dataset now, without WFO (fully supported, no code change)

From this worktree, after your approval:

```bash
make uat-preview-stop
```

```bash
make feature-review-up
```

```bash
make feature-review-bootstrap-owner LOGIN=owner
```

```bash
make feature-review-seed
```

```bash
make feature-review-extended-seed
```

```bash
make feature-review-extended-status
```

Review is then at http://localhost:15174 with v4 plus v5 (roughly 300–350 records). Taxonomy shows its
truthful "source not available" state. To return to the small UAT: `make feature-review-stop`, then
`make uat-preview-up`. Both keep their volumes; neither touches DEV.

### Step 2: WFO in Review (needs approval of an infrastructure change and FULL)

- Download the pinned archive (132.6 MB from the Zenodo URL in `taxonomy/source.py`) into a new
  empty directory, verify its SHA-256, and provision the index into this worktree's ignored cache:
  `python3 ./scripts/workflow_environment.py review compose -- run --rm backend python -m florabase.taxonomy.snapshot <archive> /app/src/.source-cache/wfo-2026-06.sqlite --retrieved-at <UTC timestamp>`.
- Add one line to `compose.review.yaml` passing `FLORABASE_WFO_SNAPSHOT_PATH` (read-only index;
  no schema or data change). Under AGENTS.md this is infrastructure and needs FULL, so it belongs in
  its own `ci/` or `infra/` branch, not in this UI branch.
- WCVP stays at the existing v15 wiring; no version replacement.

**Alternative without an infrastructure change:** provision the same WFO index and use it in UAT,
which is already wired. That only reaches the small v4 dataset, and the taxonomy extension adds 2
UAT records (a Holy basil identity and packet) when `make uat-preview-seed` next runs.

## Expected resources

Measured on the running UAT as a proxy for Review: about 0.65 GiB memory (frontend 394 MiB, backend
201 MiB, PostgreSQL 61 MiB) and about 250 MB of volumes (dependencies 179 MB, database 70 MB). v5
adds 648 KB of packaged photos and a modest database increase. The WFO index adds 394 MiB of disk
(ignored, per worktree) and the archive 132.6 MB (deletable after provisioning). Host: 24 CPUs,
60 GiB RAM, 438 GB free.
