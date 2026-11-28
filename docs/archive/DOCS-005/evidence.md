# DOCS-005 — Implementation Evidence & Batch-15 Handoff

- **Branch**: `docs/docs-005-structure` (base `origin/main` `c83d816`)
- **Writer**: `antigravity-docs-005`
- **Feature ID**: `DOCS-005` (registered after `DOCS-001` in `docs/features.json` and as `"best-effort"` in `docs/release/scope-v1.json`)
- **Commit structure**:
  1. Pure `git mv` commit (`0390c760`): 2,718 files renamed at 100% similarity, 0 insertions, 0 deletions.
  2. Links, hard-coded paths, tombstones, guide splits, and regenerated OpenAPI/TS schema (`c6832a4f`).
  3. Agent reading path (`docs/agent-map.md`, `AGENTS.md`), folder `README.md` indexes, `make feature-show` / `make feature-list`, drift checks + tests, and `DOCS-005` backlog/progress/evidence.

## 1. Measured Agent Start-Path Context Savings

Measured honestly against base `c83d816` (note: per Phase 1 ruling #4, `docs/progress.md` is not rotated in this diff; the saving comes from `AGENTS.md` step 4 instructing agents to read only the top milestone of `docs/progress.md`, use `make feature-show`, and open only the targeted section from `docs/agent-map.md`):

| Item | Before (`c83d816`) | After (`DOCS-005`) |
| --- | ---: | ---: |
| `AGENTS.md` | 9,923 B (135 lines) | 10,077 B (135 lines) |
| `docs/agent-map.md` | — | 6,711 B (39 lines) |
| `docs/progress.md` | 101,121 B (full file) | 2,032 B (latest milestone only) |
| `docs/features.json` / `make feature-show` | 258,581 B (full file) | 1,345 B (one entry: `DOCS-005`) |
| **Total read at task start** | **369,625 B (361.0 KB)** | **20,165 B (19.7 KB)** |
| **Reduction** | — | **−349,460 B (−94.5%)** |

## 2. `make feature-show` / `make feature-list` Sample Outputs

```text
$ make feature-show ID=MOBILE-003
MOBILE-003 [implemented | post-1.0 | P2 | mobile]
  Usable Android release app: Florabase branding and deterministic asset generator, native file export/share and full-screen photo viewer, Android PrintManager label printing, server-driven map runtime config via /api/v1/system/info, native update banner, monotonic SemVer versionCode, env-only release signing, and opt-in GitHub Release APK workflow for Obtainium while keeping PWA unchanged
  deps: MOBILE-002, MOBILE-001
  criteria:
    - PWA remains unchanged ...
```

```text
$ make feature-show ID=MOBILE-
MOBILE-001 [implemented | post-1.0 | P2 | mobile] ...
MOBILE-002 [implemented | post-1.0 | P2 | mobile] ...
MOBILE-003 [implemented | post-1.0 | P2 | mobile] ...
```

## 3. Grep Proof (No Stale Non-Tombstone `docs/<old>` Paths Outside History)

Running `git grep -n -E 'docs/(<all 55 moved filenames>)'` excluding `docs/`, `CHANGELOG.md` (released entries), `compose.yaml` (untouched per ADR 0009), `postgres/florabase-postgres-entrypoint.sh` (untouched per Ruling #5), and synthetic paths in `scripts/test-verification-impact.py` returns **only**:
- `scripts/check-doc-links.py` & `scripts/test-doc-links.py`: explicit `TOMBSTONES` list & tombstone tests.
- `scripts/smoke-portable-compose.py` (db checks), `scripts/test-beta-images.py` (L1476), `scripts/test-beta-runtime.py` (L346 `compose.yaml`, L435 `florabase-postgres-entrypoint.sh`): intentional assertions against untouched shipped artifacts covered by the `docs/installation.md` tombstone.

## 4. Paths Other Batch-15 Branches Touch (Integration Checklist)

`DOCS-005` is scheduled to merge **last** in Batch 15:
- `docs/progress.md`: touched by all Batch-15 branches (`UI-POLISH-006`, `UAT-INSTANCE-002`, `MOBILE-004`, `DEMO-001`). `DOCS-005` only prepends at top (no rotation), so `feature_batch.py`'s `additive_progress()` merges it cleanly.
- `docs/features.json` & `docs/release/scope-v1.json`: `DOCS-005` is inserted right after `DOCS-001` (not the tail) to avoid tail conflicts with Batch-15 additions.
- `docs/README.md`: any Batch-15 branch adding a new top-level doc (e.g. `docs/demo-mode.md` from `DEMO-001`) should be moved into its subfolder (`docs/operate/demo-mode.md`), given a `> Summary:` line, and linked from `docs/operate/README.md` during Batch-15 integration.
- `docs/mobile.md` → `docs/operate/mobile.md`: `MOBILE-004` edits `docs/mobile.md` (Commit 1 is pure `git mv` for rename detection).
- `docs/development-workflow.md` → `docs/develop/workflow/review-and-uat.md`: `UAT-INSTANCE-002` edits `## UAT instances (parallel, per worktree)`.
- `docs/ui-contract.md` → `docs/develop/ui-contract.md`: `UI-POLISH-006` edits `docs/ui-contract.md` (kept whole, pure `git mv` in Commit 1).
- `backend/openapi.json` & `frontend/src/api/schema.d.ts`: 1-line docstring update from `backend/src/florabase/events/schemas.py` (`docs/features/activity/phenology.md`); if `DEMO-001` also updates OpenAPI, resolve by running `make api-generate`.

## 5. Fix Round (M1 Batch Merge & Case-Insensitive Lookup)

- **M1 reproduction**: `d7dc7e59` rewrote 7 links deeper in `docs/progress.md` in addition to prepending at the top. Merging `common=c83d816`, `ours=common + prepended sibling milestone`, `theirs=d7dc7e59` failed in `scripts/feature_batch.py` (`_additive_progress()`), which previously only handled deep edits on `ours` when `theirs` was a pure top prepend.
- **M1 fix**: added the symmetric branch in `_additive_progress()` when `ours` is a pure top prepend (`ours.endswith(common)` and `ours.count(common) == 1`) and `theirs` carries deep edits below the 3-line anchor, preserving the refusal when both sides edit deeper than the top. Verified against the exact `c83d816` / `d7dc7e59` reproduction (`merged=103,267 B`) and covered by `test_batch_additive_progress_preserves_incoming_deep_edit_and_refuses_both_deep` in `scripts/test-agent-workflow.py`.
- **Nit**: `scripts/feature-show.py` now matches IDs and prefixes case-insensitively (`make feature-show ID=docs-005` finds `DOCS-005`), covered in `scripts/test-check-features.py`.
