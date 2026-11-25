# FN-02, FN-04, UX-ENTRY-001 — directory sort, searchable pickers, Save and add another

Implemented on `feat/fn-02-fn-04-list-ux` from `origin/main` at
`ddf5a1431453df6c6644fb1f2e9feeec6b120e16` (writer `claude-pkg-b`). No database migration; the
saved-view state is JSON validated by Pydantic, so the new optional `sort` field needs none.
PWA behaviour is unchanged; only the `UpdateNotice` test fixtures moved to the current beta.

## FN-02 — sort Seeds, Sowings and Plants

- [`frontend/src/components/directorySort.ts`](../../../frontend/src/components/directorySort.ts):
  `sortDirectory` orders an already filtered list (stable copy, never mutates) by the displayed
  record name (`localeCompare`, numeric, case-insensitive) or by a partial date compared by its
  known parts, undated records last in both directions. Empty sort keeps the API order.
- [`frontend/src/components/DirectorySort.tsx`](../../../frontend/src/components/DirectorySort.tsx):
  the toolbar `Sort by` select (new optional `sort` slot of `DirectoryTools`).
- Dates: Seeds `acquisition_date ?? harvest_date`, Sowings `sowing_date`, Plants and Plant groups
  `collection_entry_date`. Sorting happens before `useDirectoryPagination`, whose scope key
  includes the sort, so the order survives page changes and a new sort returns to page 1.
- `sort` is a canonical URL and Saved View field: frontend
  [`saved-views/state.ts`](../../../frontend/src/saved-views/state.ts) and backend
  [`saved_views/state.py`](../../../backend/src/florabase/saved_views/state.py)
  (`Literal["name", "name_desc", "newest", "oldest"] | None`, unknown values rejected).

## FN-04 — searchable reference pickers

Every reference `<select>` whose options come from user data was replaced by the existing
[`ReferencePicker`](../../../frontend/src/seed-lots/ReferencePicker.tsx) combobox (type to filter,
ArrowUp/ArrowDown, Enter, Escape): Plant Current location, Supplier, Material provenance and
Precise provenance site; Sowing SeedLot and Current location; Journal movement Destination
Location; Sowing descendant Botanical identity; Provenance site Geographic place; native range
Geographic place; Geography create and edit Parent geographic place; Location create Parent
location; Stored material Storage Location filter. Bounded enumerations stay native selects; the
Order picker already has server-side search. `ReferencePicker` gained optional `id` (keeps the
validation-focus selectors), `name` (hidden input for uncontrolled forms) and `describedBy`.
Dialog pickers use `openOnFocus={false}` so Escape still closes the dialog first.

## UX-ENTRY-001 — Save and add another

Seeds, Sowings and Plants/Plant groups create forms show **Save and add another** beside the
primary save (never when editing or extracting). It runs the same submit, refreshes the
directory, stays on the create form with a fresh draft that keeps only the main reference
(botanical identity; the SeedLot for a Sowing), announces success and focuses the first field.

## Small backlog items

- `compose.yaml` header now carries the one-time folder and owner block from
  `docs/installation.md` step 1 (49 lines, within the 50-line contract).
- `frontend/src/pwa/UpdateNotice.test.tsx` fixtures use `0.1.0-beta.8` → `0.1.0-beta.9`.

## Acceptance mapping

| Item | Coverage |
| --- | --- |
| FN-02 order rules | `frontend/src/components/directorySort.test.ts` |
| FN-02 Seeds, incl. pagination and URL | `SeedLotScreen.test.tsx` (`FN-02 Seeds sort by name and date survives pagination and the URL`) |
| FN-02 Sowings / Plants | `SowingScreen.test.tsx`, `PlantScreen.test.tsx` (`FN-02 …`) |
| FN-02 saved view contract | `saved-views/state.test.ts`, `backend/tests/test_saved_views.py` |
| FN-04 long list by typing and keyboard | `PlantScreen.test.tsx` (`FN-04 a long Supplier list is searchable by typing and keyboard`) and the updated picker flows in App, Plants, Sowings, Geography, Locations, Provenance sites, Stored material and guided forms |
| UX-ENTRY-001 | `SeedLotScreen.test.tsx`, `SowingScreen.test.tsx`, `PlantScreen.test.tsx` (`UX-ENTRY-001 …`) |
