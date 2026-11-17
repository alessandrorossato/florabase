# SEARCH-001 — certification evidence map

Draft for Batch 03. Base `main` `554d74de88a278e2b9a392de9d105d3d62c35f91`. This record maps
committed evidence to each acceptance criterion. It does not certify the entry and does not
change its status (`implemented`); certification is a separate reviewed step.

| # | Criterion (exact text from features.json) | Committed evidence | Applies to the candidate because | State |
| --- | --- | --- | --- | --- |
| 1 | Filters reflect implemented structured fields and lifecycle states rather than speculative metadata | `backend/tests/test_search_api.py` `test_search_api_rejects_inapplicable_filter_combinations`, `test_search_api_rejects_lifecycle_outside_the_kind_vocabulary`; `backend/tests/integration/test_search.py` `test_search_combined_filters_use_recorded_semantics_and_stable_order`, `test_search_api_validates_filters_and_returns_typed_results`; `frontend/src/collection/DashboardSearch.test.tsx` "filters work without query text and active chips can be removed"; `docs/search.md` (filter paragraph) | Tests run in the canonical backend unit, integration and frontend suites; `docs/search.md` describes the current filters | Mapped |
| 2 | Botanical reference knowledge and collection observations remain distinguishable in results | `backend/tests/integration/test_search.py` `test_search_groups_relationships_filters_partial_dates_and_pagination` (profile text matches only `BOTANICAL_PROFILE`; Event observation text matches only `EVENT`); `backend/tests/test_search_service.py` `test_search_builds_typed_groups_and_uses_hierarchical_text_matches`, `test_search_reference_records_are_suppressed_by_collection_only_filters`; `frontend/src/collection/DashboardSearch.test.tsx` "Dashboard search replaces overview, groups results, and restores the normal route" (separate "Botany" region); `docs/search.md` "Groups remain distinct" | Tests run in the canonical suites | Mapped |
| 3 | Empty, partial, authorized, and large-result behavior is tested | `test_search.py` `test_search_is_authenticated_and_empty_request_does_not_scan`, `test_search_groups_relationships_filters_partial_dates_and_pagination`, `test_search_keeps_one_hit_per_record_and_minimizes_payloads`; `test_search_api.py` `test_search_api_trims_query_and_passes_bounded_paging`; `frontend/src/collection/DashboardSearch.test.tsx` "search error retries, and a large group loads a bounded next page" | Tests run in the canonical suites | Mapped |

Restatements: none.
Not counted: `docs/progress.md` SEARCH-001 entry stating the canonical gate "remains for later review" (prose; no committed gate record exists). Passing of the cited tests on the candidate is established only by the candidate gate run.
