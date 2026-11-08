# Isolated LINEAGE-003 Review

Open the root packet in this seeded instance,
**http://localhost:15176/#/lineage/seed_lot/01a1bcdb-8e91-7710-9466-46603a2fb7b8** (IDs are
per-seed; elsewhere use any record's **Lineage → Explore material ancestry**). Contract:
[lineage-explorer.md](../../lineage-explorer.md).

This Review runs beside Feature Review (15174) without touching it. It follows the precedent of the
taxonomy-visual-001 and wcvp-version-001 adapters: `review.py` subclasses the canonical
`workflow_environment.Environment` with process-local identities only, so build, migration,
ownership, seed and removal guards are the canonical ones.

| Identity | Value |
| --- | --- |
| Compose project | `florabase-lineage-003-review` (labels bind it to this worktree) |
| URL | `http://localhost:15176` (loopback only; backend/DB unpublished) |
| Database / user | `florabase_lineage_review` |
| Volumes | `florabase-lineage-003-review_{postgres_data,attachment_data,frontend_node_modules}` |
| Network | `florabase-lineage-003-review_internal` (Docker-allocated) |

```sh
AGENT_ID=claude-code python3 docs/review/lineage-003/review.py up      # build, migrate, wait healthy
AGENT_ID=claude-code python3 docs/review/lineage-003/review.py seed    # owner once + canonical fixture
python3 docs/review/lineage-003/review.py status
python3 docs/review/lineage-003/review.py stop                        # keeps all three volumes
CONFIRM_REMOVE_REVIEW=florabase-lineage-003-review \
  AGENT_ID=claude-code python3 docs/review/lineage-003/review.py remove  # deletes ONLY this project's volumes
python3 docs/review/lineage-003/test-review.py                        # Docker-free adapter checks
```

Mutating actions require the worktree writer (`AGENT_ID`) and take the project's machine lock. Seed
writes an identity-specialized copy of `scripts/uat_fixture.py` under the ignored
`.source-cache/florabase-lineage-003-review/` (it refuses if the canonical identity strings change),
creates the synthetic owner once with a generated password in `credentials.json` (mode 0600; never
publish it), then runs the canonical seed: the v4 baseline plus every additive extension, including
the review-only `lineage_explorer_extension` (127 manifest records). Repeat seed preserved all 127.

## Captures (authenticated, seeded synthetic data, 2026-11-08)

`captures/` — 1280×900 desktop unless named otherwise:

- `chain-<palette>-<light|dark>-1280.jpg`: upstream chain of the second-generation Plant in all eight
  supported themes (Field Ledger, Botanical, Herbarium, Mineral × light/dark).
- `tree-branching`, `tree-conversions`, `tree-reversed-flat`: root packet with progressive expansion —
  Plant group, extraction, directly recorded group producer, applied and reversed Harvest conversions,
  transferred sibling, reversed Plant.
- `paging-before` / `paging-after`: 27-Plant flat; first page of 25, then "Show 2 more" (focus moves
  to the first new record).
- Independent visual review (no blocking defects) led to a visible 1px `--lineage` rule on nested
  levels, the house touch query `(max-width: 48rem), (any-pointer: coarse)`, aligned "Show more" at
  every level and shorter wording; `tree-branching` and `paging-before` were recaptured afterwards.
  The other captures predate only those CSS/wording changes.
- `origin-orphan-producer`, `origin-unknown-independent`: produced lot without producer; same-identity
  independent Plant with unknown origin (no inferred parent).
- `phone-*-390`, `tablet-*-768`: phone 390×844 and tablet 768×1024 in light and dark; no horizontal
  overflow (`scrollWidth == clientWidth` measured at both).
- `entry-plant-lineage-tab-1280`: the Lineage tab entry link.
- `integration-golden-branch-{1280,768,390}`: after integration onto `48f35ea` (TAXONOMY-001 and
  MEASUREMENT-001, schema `0045`), this worktree's own UAT instance (golden SMOKE) with the branching
  root expanded; no horizontal overflow and 44 px touch targets at 390. The explorer UI code is
  identical to the reviewed commit, so the captures above still apply.

Viewport emulation was used in the desktop app's browser; physical devices and assistive
technology were not exercised.
