# CERT-03 · Harvest regression evidence

Base `836bf80305a19fdd7f49845b8bc00ae423553a93`. Source
`ci/cert-03-harvest-regressions`, writer `sol-batch03-c121`.

## HARVEST-001 criterion 6

`test_harvest_without_stored_material_is_not_current_holding` in
`backend/tests/integration/test_dashboard.py` records a seed Harvest from a dead Plant through
`harvests.service.write_harvest` without creating stored-material inventory. It snapshots
`collection_views.service.dashboard` before and after. The non-Event counts stay equal,
`overview.current_identities` stays at zero, the Event count increases by one, and the sole
recent Harvest Event is the Harvest's linked Event.

## HARVEST-001 criterion 4

`Harvest fallback image is labelled with its actual owner` in
`frontend/src/harvests/HarvestScreen.test.tsx` renders a compact Harvest row against a local
identity-cover fixture and a second row with its own primary photo. It checks the fallback
thumbnail, alt text and visible reference label, checks the owned thumbnail and label, and
excludes the source Plant photo. This exercises the existing HarvestScreen and RecordVisual
ownership semantics. R19 remains pending an operator decision.

## Focused verification

- `./scripts/test-integration.sh backend/tests/integration/test_dashboard.py`
  passed 9 tests in disposable PostgreSQL (baseline 8). Exact cleanup passed.
- `pnpm vitest run src/harvests/HarvestScreen.test.tsx` passed 20 tests in Quality
  (baseline 19).
- `make lint`, `make typecheck`, scoped backend Ruff formatting, scoped frontend Prettier and
  `git diff --check` passed.
- `make verification-plan` selected affected, with the Dashboard integration and Harvest
  frontend files in its inventory.

The independent QA record in the Batch 03 coordination package identifies the exact frozen Git
commit. Canonical verification and registry reconciliation are integration work.
