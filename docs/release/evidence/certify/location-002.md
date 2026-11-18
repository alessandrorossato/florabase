# LOCATION-002 — certification evidence map

Prepared in Batch 07 (`docs/batch-07-functional-ux-certification`) against `main` `fdc75e83fa8818cab791ed82cbba65f4f97db7ae`, referencing frozen Batch 07 Workstream A (`173b9f6eed7979e4bc0793af88a55b4de7af1eeb`) and Workstream B (`39080cb84145e3e70b4ae38179169fb7af36d7ba`) where applicable. This record maps committed and frozen pre-RC evidence to each acceptance criterion. It does not certify the entry and does not change its status (`implemented`); certification is a separate reviewed step on the release-candidate images.

| # | Criterion (exact text from features.json) | Committed & frozen pre-RC evidence | Applies to the candidate because | State |
| --- | --- | --- | --- | --- |
| 1 | One shared Location concept remains authoritative while views can scope usage to Seeds, Sowings, or Plants without creating parallel location entities | Committed on `main`: `backend/src/florabase/locations/`, `backend/tests/integration/test_locations_api.py`, `frontend/src/locations/LocationScreen.test.tsx` (scope filtering for Seeds, Sowings, and Plants on one authoritative Location model). | Tests run in canonical integration and frontend suites | Mapped |
| 2 | A hierarchical collapsible presentation keeps roots, descendants, current paths, retirement state, and empty branches understandable | Committed on `main`: `frontend/src/locations/LocationScreen.tsx`, `frontend/src/components/HierarchyRow.test.tsx`, `frontend/src/locations/LocationScreen.test.tsx`. | Tests run in canonical frontend suite | Mapped |
| 3 | Desktop and mobile interactions remain accessible and link Location usage to the relevant supported records | Committed on `main`: `frontend/src/locations/LocationScreen.test.tsx`, `frontend/src/App.test.tsx`. Preliminary browser rehearsal: [`../g-core-pre-rc.md`](../g-core-pre-rc.md) Step 6 and [`../g-ux-pre-rc.md`](../g-ux-pre-rc.md) Row 7. | Tests run in canonical frontend suite; G-CORE step 6 and G-UX Locations entry verify on candidate images | Pending G-CORE step 6 / G-UX (Locations) |

Restatements: None (related `LOCATION-003 #3` is restated by confirmed `R25` in [`location-003.md`](location-003.md)).
Not counted: `docs/progress.md` prose.
