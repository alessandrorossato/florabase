# Florabase Next: independent review package (M7)

**Status:** experimental branch, ready for independent review. **Not** approved for merge,
release, canonical FULL, push or delivery. The reviewer reads and verifies; the reviewer does
not modify repository files. If Codex is used as reviewer, it is review-only and only with the
operator's explicit authorization.

## 1. Exact revisions

| What | Value |
| ---- | ----- |
| Branch | `feat/ui-redesign-exploration-001` (local only, not pushed) |
| Base / comparison main | `d94f275` (`origin/main` checked read-only during M7: still `d94f275`; main is 0 commits ahead of the merge base) |
| Last code commit | `4571f03` (the M7 checkpoint commit adds documentation only; `git rev-parse HEAD HEAD^{tree}` gives the exact head and tree, reported in the M7 checkpoint) |
| Scope | Frontend only. `git diff --stat d94f275 HEAD -- backend` is empty: no API, schema, migration or auth change |

Milestone commits (oldest first): M0 `c2ed8ec`; M1 `8ce52fa` `b39fa50` `ecadaf3` `436bbf0`;
M2 `307611b` `66479bf`; M3 `b59a21c` `dd846c2`; M4 `94a1675` `bfb23b4` `380e6f4` `9dba8a1`;
M5 `e593c50` `07b6274`; M6A `5462ee4`; M6B `81ba6b9` `85b726a` `659e053` `70810bb` `353ea39`
`0db5bc5`; M6 final `b8d6e63`; M7 `2d95552` `4571f03` and the M7 checkpoint commit (docs).

## 2. Verification commands

Run from the feature worktree. Frontend checks use the per-worktree isolated quality project:

```bash
python3 ./scripts/workflow_environment.py quality compose -- run --rm --no-deps -T frontend sh -c 'pnpm format:check && pnpm typecheck && pnpm lint && pnpm exec vitest run && pnpm build'
```

```bash
git diff --stat d94f275 HEAD -- backend
```

```bash
make api-check
```

Expected: format, typecheck, lint (0 warnings) and build pass; the suite runs 1207 tests;
`backend` diff empty; no API drift. Known intermittents are listed in §8.

## 3. Comparison environments

| Environment | Source | Data | Notes |
| ----------- | ------ | ---- | ----- |
| Florabase Next | UAT Preview, Compose project `florabase-uat-preview`, `http://localhost:15174`, serving this worktree (`make uat-preview-up AGENT_ID=<id>`; `make uat-preview-status`) | Synthetic fixture v4 plus one synthetic Plant extracted in M6B for lineage | Writable, isolated; never a production database or volume |
| Original Florabase (main `d94f275`) | Baseline evidence `.florabase-next-evidence/baseline-main-d94f275/` (149 captures; manifest `docs/design/florabase-next/baseline-main-d94f275.manifest.json`) taken at M0 from the isolated synthetic environment | Synthetic fixture | For a live side-by-side: UAT Preview serves one source at a time; stop it (`make uat-preview-stop`), start it from a detached checkout of `d94f275`, review, then restore this worktree. Data volumes are preserved |

Production infrastructure and main were never modified.

## 4. Review login

Only the synthetic UAT fixture owner: `preview` / `preview` (UAT Preview only; seeded by
`make uat-preview-seed`). No personal or production credentials are used or needed.

## 5. Representative routes and workflows

| Area | Route | What to check |
| ---- | ----- | ------------- |
| Shell | any page | Rail workspaces preview without navigating; panel sections, Saved views (5 + "Show all"), Recent; Ctrl/⌘K palette with "This record" actions; phone bottom bar (Record first) |
| Today | `#/dashboard` | Summary from counts only; Next work grouped by record; Data quality collapsed and neutral |
| Plant (dense) | Plants → "Preview — Basil mother plant" | Specimen plate and label, two-step lineage with relationship text, Almanac (month span, day dot, undated entry listed), Journal periods |
| Plant (three-step lineage) | "Preview — Basil seedling (extracted for M6B lineage check)" | Seed lot → Sowing → Plant group → Plant |
| Seed lot (sparse) | Seeds → "Preview — Aloe unknown stock" | "Quantity unknown", "No recorded source material", no axis for sparse dates |
| Sowing | Sowings → "Preview — Spring basil tray" | Germination, lineage from its Seed lot, legacy `?tab=propagation` opens Lineage |
| Botanical identity | Explore → Botanical identities → "Aloe vera" | Reference sheet within the hub |
| Directories (phone 390) | Seeds, Plants, Sowings, Harvests | First record near the top; icon tools; pagination after the list; bottom bar fully visible |
| Capture | Record button → search "basil" → a Sowing | Opens the record's own germination form (`entry=new`), address cleaned |
| Labels | Record → Label link | Only label-shaped Florabase links open; foreign links refused |

Workflow smoke performed in M7 (Playwright, synthetic UAT, results in §7).

## 6. Critical domain invariants (expected behaviour)

1. **Lineage is only explicit.** Steps come from `/lineage` endpoints (or a Sowing's recorded
   Seed lot). A shared Botanical identity never implies lineage; no descendants are inferred.
2. **Planned is never done.** Schedule items read Planned / Due today / "Overdue · not recorded
   as done"; nothing planned appears in the Recorded lane.
3. **Date precision is preserved.** Year-only shows `2024`, month-only `2025-04`, undated
   "Date not recorded"; the Almanac draws month/year as spans and never draws undated entries.
4. **Unknown is not zero.** "Quantity unknown", "Not recorded", "Unknown" — never `0` or `—`.
5. **Derived is labelled.** Today's counts and Data quality state that they are derived.
6. **No form copies.** Capture opens the record's existing form; validation, permissions,
   unsaved-change protection and history behaviour are the existing ones.
7. **Label links cannot leave the app or trigger actions.** Only `#/seeds|plants|plant-groups/<uuid>`
   and `#/harvests/<uuid>?inventory=<uuid>` are accepted.
8. **Backend contracts unchanged.** No API, schema, auth or permission change.
9. **Six original themes preserved.** Their token blocks are pinned by test; Field Ledger is the
   branch default only.

## 7. Evidence index

| Evidence | Location |
| -------- | -------- |
| Milestone records | `docs/design/florabase-next/README.md` (M0–M7), `docs/progress.md` |
| Before (main) | `baseline-main-d94f275/` (149) |
| After, all routes, desktop/tablet/phone, light and dark | `m7-4571f03-field-ledger-light/`, `m7-4571f03-field-ledger-dark/` (118 each, incl. shell interactions) |
| Final visual review set | `m6-final-review/` (16, numbered) |
| Before/after composites | `m7-before-after/` (10, main vs M7), `m2-`, `m3-`, `m4-before-after/` |
| Manifests (hashes, probes) | `docs/design/florabase-next/{m1…m7,m6b,m6-final}/` |
| Design | M6A canvas https://claude.ai/artifact/B3TWNaSJvnjxUz2GmdXRCx (private; share to reviewer) |

**Image quality note:** specimen plates show the API's *thumbnail* rendition enlarged. Softness
or pixelation in plates is an image-source limitation, not the layout; the display-rendition
proposal is in the M6 section of the README.

## 8. Known limitations and outstanding issues

| # | Issue | Classification | Blocking for adoption? |
| - | ----- | -------------- | ---------------------- |
| 1 | Manual screen reader (NVDA/VoiceOver), real browser zoom, Windows High Contrast, physical touch devices | **Not performed** (automated evidence only) | Yes: a manual pass is required |
| 2 | Real-device QR camera scanning | **Pending operator test on Android** (HTTPS or localhost, printed label); feature-detected, absent where unsupported | No for adoption of the UI; yes before claiming camera scanning |
| 3 | App "identity section keyboard navigation retains browser Back and Forward boundaries" intermittent | Observed once (M6 final run). Not reproduced in 10 later full runs or 20 isolated runs. Instrumented runs measured its steps at 1–13 ms against a 1000 ms wait, which refutes the load-timeout hypothesis. A remaining, **unproven** hypothesis is jsdom history carried over from an earlier test in the same file. Tracked, unclassified; the branch does not change identity behaviour | Needs classification by the reviewer |
| 4 | MediaScreen "detail return…" intermittent | Final focus assertion hardened for a passive-effect race; not reproduced before or after | No (tracked) |
| 5 | Specimen plates use the API thumbnail enlarged | Image-source limitation (soft or pixelated), not layout; additive `display_url` rendition proposed (backend change, not authorised) | No, but high-priority product quality |
| 6 | Main JS 251.5 → 285.0 kB (gzip 78.1 → 87.8 kB) vs main | Cost of the shell, Saved Views serializer, Specimen Sheet, Almanac, capture and search | No; review whether to split chunks |
| 7 | Botanical and other original themes keep 40px controls at touch widths in a few places | Same as main (original geometry) | No |
| 8 | Botanical identity keeps its hub layout (reference sheet, not a specimen sheet) | Deliberate | No |
| 9 | Phone action dock, Today thumbnails, recent-record chips | Evaluated, not built (reasons in README) | No |

