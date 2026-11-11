# PHENOLOGY-001 integration handoff

10 November 2026 · `feat/phenology-001` · writer `claude-phenology` · base `main`
`48f35ea0da3c70a0955fad6e5a9055a424142bdc`. Contract: [phenology](phenology.md).

Status: `implemented`, **READY_FOR_INTEGRATION**. Canonical FULL is intentionally deferred to the
operator's consolidated integration tree; no feature receipt exists, so `make feature-deliver`
(which requires a current receipt) cannot be used for this branch on its own.

## Integration facts

| Item | Value |
| --- | --- |
| Migration | `20261110_0046_event_phenology.py`, `revision = "20261110_0046"`, `down_revision = "20261109_0045"` (single head). CUTTING-001 must follow as `0047` with `down_revision = "20261110_0046"`. |
| Schema | `events.phenophase varchar(24) NULL`, `events.phenophase_date_is_approximate boolean NULL` |
| Constraint | New `ck_events_phenology`: both NULL, or flag NOT NULL, flag false unless a date is recorded, and stage within its kind (`observation`: bud_break, leaf_color_change, leaf_fall, dormancy_entry, dormancy_exit; `flowering`: flowering_onset/ongoing/end; `fruiting`: fruit_set, fruit_ripening, fruit_ripe). No existing constraint changed. Downgrade refuses while staged Events exist. |
| API | `Phenology {phase: Phenophase, date_is_approximate: bool = false}`; optional `phenology` on `EventCreate`, `EventUpdate`, `EventResponse`. No new route. `backend/openapi.json` and `frontend/src/api/schema.d.ts` regenerated; `make api-check` clean. |
| History | Event row context `Stage: <label>` (+ ` (approximate date)`); labels identical to the Journal. |
| Golden SMOKE | `schema_revision` `20261110_0046`, `canonical_sha256` `de25687b281866752bb689f2181c95363cdf80c325786be5e6ea710b77957fce`, `tables.events.sha256` `6933e7dab26ddbf5100b95500c0adf4efc9c95665506401ee0e8479bc4ad55db`. Nothing else changed. COMPREHENSIVE untouched (still `20261013_0042`). If CUTTING lands its schema after 0046, SMOKE must be re-pinned again on the consolidated tree. |

## Evidence (focused; not a canonical gate)

- Backend unit (`test_event_schemas`, `test_event_model`), ruff, ruff format, mypy: pass.
- PostgreSQL integration, 103 passed: `test_phenology_api` (scenarios: three flowering years,
  flowering without fruiting, two flowerings in one year, year/month/unknown and approximate dates,
  name correction, duplicate-identity merge, PlantGroup, correction/deletion, dead Plant,
  measurement coexistence, 401/403/422, DB constraint, downgrade/upgrade/re-upgrade with populated
  rows), `test_measurement_api`, `test_event_api`, `test_history`, `test_botanical_identity_api`,
  `test_autogenerate_checks`, `test_golden_dataset` (SMOKE).
- Earlier on the same code: `test_propagation_reversal`, `test_schedule` pass.
- Frontend typecheck, ESLint, Prettier; vitest `src/events` + `PlantScreen.test.tsx`: 89 passed.

## Independent QA

Two read-only reviews: no P1/P2 code defects. Fixed P3s: History labels aligned with the Journal,
approximate year wording, approximate flag reset on kind/stage change, per-year `role="group"`,
per-target heading id, mobile month label size, 24px mobile date targets, undated aria-labels,
approximate checkbox disabled without a date, phenology merge regression test.

## Visual review

UAT instance `florabase-uat-branch-feat-phenology-001` (port 15182, golden SMOKE plus 12 recorded
observations). Real authenticated headless-Chromium captures in
[`review/phenology-001/`](review/phenology-001/): `plant-history`, `record-dialog`,
`group-history` and `empty-state` at 1440, 768 and 390 px (dark), plus `plant-history-1440-light`
and `plant-history-390-light`. No horizontal overflow at any width. Keyboard activation of date
links is covered by tests. Not captured: a Journal with entries but no phenology (unit-tested).

## Risks

- Alembic ordering depends on CUTTING-001 re-parenting onto `20261110_0046`.
- Stage-less flowering/fruiting remains valid by design; there is no backfill.
- No phenology correction trail and no global-search stage terms (documented limits).
