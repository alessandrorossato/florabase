# GERMINATION-001 — certification evidence map

Draft for Batch 03. Base `main` `554d74de88a278e2b9a392de9d105d3d62c35f91`. This record maps
committed evidence to each acceptance criterion. It does not certify the entry and does not
change its status (`implemented`); certification is a separate reviewed step.

| # | Criterion (exact text from features.json) | Committed evidence | Applies to the candidate because | State |
| --- | --- | --- | --- | --- |
| 1 | Optional dated observations can coexist with simple germination totals | `backend/tests/test_germination.py` `test_summary_uses_incremental_observations_and_exact_seed_threshold`, `test_create_observation_rejects_conflicts_and_persists_valid_input`; `backend/tests/integration/test_germination.py` `test_observation_bound_and_sowing_edit_use_same_parent_lock`; `frontend/src/sowings/SowingScreen.test.tsx` "germination tab keeps simple and dated totals distinct and supports correction" | Tests run in the canonical backend, integration and frontend suites | Mapped |
| 2 | Percentage, first germination, timing, cumulative germination, and T50 are derived only when sufficient data exists | `backend/tests/test_germination.py` `test_t50_uses_exact_sown_seed_threshold_and_linear_interpolation`, `test_timing_and_percentage_are_unavailable_without_exact_inputs` (non-day dates, non-seed-count or approximate quantities, no observations → `None`); `frontend/src/sowings/SowingScreen.test.tsx` "germination progress uses only an exact positive seed-count denominator" | Tests run in the canonical backend and frontend suites | Mapped |
| 3 | Missing observations never prevent basic Sowing use | `backend/tests/test_germination.py` `test_timing_and_percentage_are_unavailable_without_exact_inputs` (`has_observations=False` still returns a detail); `frontend/src/sowings/SowingScreen.test.tsx` "minimal creation requires only an understandable SeedLot choice" (Sowing recorded with no observation) | Tests run in the canonical backend and frontend suites | Mapped |

Restatements: none.
Not counted: canonical gate pass and independent QA recorded only as `docs/progress.md` prose (reconciliation cites progress 3456 and 3670–3683). The Sowing germination tab is in the page inventory and G-UX will cover it, but no criterion requires a visual check.
