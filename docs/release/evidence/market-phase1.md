# Market Phase 1 for beta.11 — QUICK-ADD-001, UX-ENTRY-002, BULK-002

Implemented on `claude/project-thread-sg3uco` from `origin/main` `c83d816` (writer: Claude, this
project thread), as the market-analysis Phase 1 slice for Batch 15. Phase 1 of the roadmap
proposal (O-07 to O-10, O-19a, O-21) was audited against main first: batch pot-on
(`PROPAGATION-BATCH-001`), multi-target care (`FN-03`, `CARE-BULK-001`), single-sheet import
(`IMPORT-002`) and default WFO/WCVP provisioning (`REF-SETUP-001`) already shipped in beta.10. This
slice closes the remaining O-07 quick-add gap and O-06 (dated bulk moves). arm64 images (O-21) and
QR quick actions (O-19a, `MOBILE-005`) are deferred. No migration.

## QUICK-ADD-001

- `POST /api/v1/quick-add/plant` (`quickAddPlant`, `backend/src/florabase/quick_add/`): `identity`
  is exactly one of `existing_id` or `new` (scientific name, cultivar, common name, optional
  `wfo.source_taxon_id`). A new identity goes through `create_botanical_identity`; an exact
  duplicate is reused and its taxonomy link is never changed. A picked WFO taxon is confirmed with
  the existing `taxonomy.service.confirm` only when its WFO name still equals the identity's
  scientific name (`422 wfo_name_mismatch` otherwise); the checksum is the local index's own.
  The Plant or PlantGroup (count required, at least 1) is built through `PlantCreate` /
  `PlantGroupCreate` and the existing create services. Everything runs in the request's single
  transaction, so a missing Location or Supplier, an unavailable index (`503
  taxonomy_unavailable`) or a mismatch leaves no identity, link or record behind.
- `#/quick-add` page (`frontend/src/quick-add/`), linked from Today's header, the **+ New** menu
  (last item) and the **Record** sheet.
- Tests: `backend/tests/test_quick_add.py` (schema), `backend/tests/integration/test_quick_add.py`
  (WFO link, reuse, groups, rollback for every failure, CSRF, unavailable index),
  `frontend/src/quick-add/QuickAddScreen.test.tsx`.

## UX-ENTRY-002

- Shared `frontend/src/botanical-identities/IdentityCreateDialog.tsx` (WFO name suggestions,
  portalled so it never nests in the opening form; a 409 duplicate resolves to the existing
  identity). Wired into the Plant form, `SowingDescendantWizard` and `PotOnDialog`. The empty
  Plants directory still requires an identity first (Quick add covers that case).
- Tests: `IdentityCreateDialog.test.tsx`, a pot-on test that creates an identity then pots on into it.

## BULK-002

- `BulkLocationApplyRequest.occurred_on` (PartialDate, optional) is passed to the Plant/PlantGroup
  Movement Events; the Move dialog shows the occurrence-date choice only for Plant/PlantGroup
  selections. `docs/bulk-operations.md` and the user guide describe it.
- Tests: unit and PostgreSQL integration (`tests/test_bulk_location.py`,
  `tests/integration/test_bulk_location.py`), `BulkLocation.test.tsx`, `api.test.ts`.

## Checks run in the cloud session

- Backend: `ruff check .`, `ruff format --check .`, `mypy` clean; focused pytest on PostgreSQL 16
  (local disposable cluster): quick add, bulk location (unit + integration) pass. OpenAPI and
  `schema.d.ts` regenerated.
- Frontend (Node 24): `tsc -b`, eslint on changed files, full `vitest run` 149 files / 1535 tests pass.
- Canonical gate (`make feature-verify`) is for the operator on the workstation.
