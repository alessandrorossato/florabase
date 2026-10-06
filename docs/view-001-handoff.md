# VIEW-001 final verification handoff

Operator visual/product UAT passed, including the final responsive directory chrome cleanup.
Independent architecture, state, migration, API security, query and frontend interaction review
found no production defect. VIEW-001 is **verified**; the final canonical gate confirms the exact
reviewed tree before its authorized local commit and protected delivery.

## Worktree and scope

- Source: `/home/alessandro/.codex/worktrees/c5e8/florabase`.
- Branch: `feat/view-001-saved-views`, initialized with the supported `make feature-init`.
- Base and unchanged HEAD: `b6160b202e7fe665174e7144078fe7961b749ccf` (SEARCH-002, PR #72).
- Source is intentionally dirty/untracked and unstaged. Primary `main` remains clean at the base.
- Only VIEW-001 persistence, adapters, controls, tests and documentation are added. Existing search
  validation was extracted without changing its semantics. Two current-head integration assertions
  advance to the new migration head; earlier migrations are untouched.

## Domain, surfaces and state

See [the complete audited surface/key/default matrix](saved-views.md#supported-surfaces-and-audit).
Thirteen surfaces are supported: Global Search; Seed lots; Sowings; Plants/PlantGroups; Harvests;
Stored material; Events; Media Library; Botanical identities; Suppliers; Locations; Geography;
Collection Provenance map. All targeted useful directory controls were reused. Contextual details,
profile/native-range/external occurrence operations, labels, import forms and operation wizards are
intentionally unsupported for the reasons recorded there.

SavedView fields: UUIDv7 `id`, session User `owner_id`, trimmed nonempty Unicode `name` up to 120
characters, finite `surface`, explicit `state_version`, canonical JSONB `state`, UTC `created_at`
and `updated_at`. Names use PostgreSQL `lower(name)` uniqueness per owner/surface; same names on
other surfaces/owners remain valid. Version 1 is the only writable/openable contract.

Text/defaults/UUIDs/repeated kinds normalize deterministically. The original screen predicates still
own result matching. Stored state excludes pagination, loaded count, selections, details/previews,
forms/dialogs, actions, errors/loading, scrolling/focus, tree expansion, map position/popup and
browser-history position. Explicit opening starts a fresh ordinary directory task, including
page zero. Existing detail Back/history transitions retain their established selection/focus behavior. Manual filter controls use their local canonical URL updates without automatic writes.
Text bounds use Unicode character counts consistently across Python and TypeScript.

Stale exact UUIDs remain present. Global Search chips retain exact IDs; Harvest filters identify
unavailable identities; Stored material keeps an unavailable Location option. No filter is dropped,
substituted or broadened. Missing exact references return no matches through existing APIs/predicates.
Future versions and invalid persisted v1 state stay listable/renamable/deletable; Open explains their
incompatibility, and explicit same-surface Update may replace them with valid current v1 state.

## API, security and performance

- GET `/api/v1/saved-views`, optional typed `surface` and nonnegative bounded `offset`; 100 rows/page.
- POST `/api/v1/saved-views`, required name/surface/version/state.
- PATCH `/api/v1/saved-views/{id}`, rename and/or replace version/state together; surface immutable.
- DELETE `/api/v1/saved-views/{id}`, exact owner shortcut only.

Every operation scopes by the real session User UUID; foreign/missing IDs share typed 404 behavior.
Existing Origin/CSRF/session protections apply. Unknown keys/invalid values/empty defaults reject with
422; case-insensitive duplicate names return typed 409. Generated OpenAPI and declarations are
regenerated; no arbitrary route/URL/code/SQL or executable snapshot is accepted as state structure.

Each list page is one owner-scoped SavedView SELECT ordered by surface, lower(name), UUID. Its
unique index prefix covers owner and owner/surface lists. No target-name lookup, view execution,
counts/materialization, cache or JSON query index is added. Opening executes only normal target
requests; lists load on expansion and offer Show more. There is no browser-local product storage.

## Frontend

Shared compact controls use native TaskDialog focus/Escape/return handling, bounded names, conflict
feedback and wrapping responsive actions. Surface lists expose Open/Rename/Update with current
view/Delete; replace and delete are confirmed. Dashboard adds one all-surfaces entry. Open produces
ordinary canonical URLs without a SavedView ID. Existing Global Search parser/serializer and
filter combinations are reused. Directory adapters add the minimum refresh/history-safe URL state.

## Migration

Revision `20261006_0034`, predecessor `20261005_0033`: only `saved_views`, its FK/checks and one
owner/surface/lower(name) unique index. Upgrade preserves existing records. Populated downgrade
refuses before DDL; explicit view deletion permits empty downgrade and re-upgrade. Real PostgreSQL
coverage proves this cycle and retains unrelated User data.

## Initial implementation check evidence

- Baselines: SEARCH-002 API **10 tests**, Dashboard/search **8 tests**, passed before implementation.
- Backend focused state/API regressions: **84 passed**.
- PostgreSQL final focused matrix: **61 passed**, including second real login, owner isolation,
  JSONB/UUIDv7/UTC/timestamps, uniqueness, 100-row pages, surface API filtering, mutation protection,
  version/stale state, migration cycle, current-head/Supplier migration and SEARCH-001/002 regressions.
  Existing Alembic path_separator deprecation warnings remain; no warning/validation was weakened.
- Python whole-tree Ruff format/check and strict mypy **267 files** passed.
- Initial frontend Saved View adapters/product and Dashboard search: **57 passed**; corrected
  Plant/Global Search/adapters/product regression run: **98 passed**. Final frozen complete frontend
  suite: **435 passed in 43 files**, including Unicode bounds and detail-return URL restoration.
- Feature graph: **91 valid**. Production backend runtime image build passed.
- `make api-check` passed with no OpenAPI/declaration drift. Both production runtime images built.
- Final frontend zero-warning ESLint, strict TypeScript, production Vite build and whole-frontend
  Prettier check passed. `git diff --check` passed; the index remains empty, and all 53 intentional
  modified/untracked files remain unstaged. The primary checkout is clean at the unchanged base.

Only fresh passing runs are evidence. Earlier corrections included an existing Location enum import,
new-test typing/lint, normal Compose flag usage and hook declaration/dependency order.
The broader frontend run caught overbroad navigation remounts; explicit directory opens now request
a fresh task, while existing detail transitions and unchanged history states retain focus/selection.
Harvest and Stored Material tests now initialize their canonical default URLs between tests, because
the existing controls intentionally persist in those URLs; all original assertions remain intact. Docker checks
use the isolated per-worktree quality project. PostgreSQL used the unique disposable
`florabase-view001-integration-20261006` project with tmpfs DB; it was cleaned without deleting any
operator volume. Source `.env`, screenshots/logs, fixture DB/media and secrets are not tracked.

## Operator UAT layout correction

Plants had placed Saved Views inside its two-column search/filter grid, alongside Lifecycle.
Saved Views now occupies its own row directly below the directory heading and above search.
SeedLots and Sowings use the same ordering; Stored material places its row below the explanatory
subtitle. All other directory placements were already outside ordinary filter grids. The shared
Saved Views block does not shrink in bounded flex directories. No product controls or filter rules
were added or redesigned.

The review also found that the Stored material adapter generated `tab=stored`, while the existing
workspace requires `tab=stored-material`. The route and history guard now reuse that identifier;
an App-level Saved View Open/refresh regression checks the actual Stored material peer directory.
Normal synthetic UAT Save/Open/refresh also proved exact `q=Preview&state=all` restoration.
The resulting `Preview stored material` shortcut remains available for operator review.

At **1440×844, 1024×844 and 390×844**, all 13 supported surfaces were reviewed: 39 document/panel
bounds checks found no horizontal overflow; directory Saved Views blocks precede search/filter
controls and stay outside ordinary filter grids. Screenshots cover empty panels, expanded long
names and responsive action wrapping. Keyboard checks proved Save → Saved views → search order,
Enter activation, initial dialog focus, focus trapping, and Escape return to Save or the exact
Rename/Update/Delete trigger. Cancelling those dialogs preserved the stored Plants view; keyboard
Open restored its exact query/lifecycle/group state. Screenshots/measurements are saved outside Git
in `/tmp/florabase-view001-layout-review`.

Focused post-layout directory/UI tests: **90 passed**. Post-route Saved Views adapter/UI and Stored
material tests: **67 passed**. Targeted App open/refresh and keyboard peer-view tests: **3 passed**;
the Saved Views UI cases overlap between the first two runs. Final affected-file Prettier and
zero-warning ESLint, strict TypeScript and production Vite build passed. The final diff has 54
intentional modified/untracked files, an empty index, unchanged HEAD and a clean primary checkout.
UAT status reports healthy frontend/backend/DB, revision 0034 and the unchanged fixture v1 baseline.
The earlier 435-test whole-frontend run predates this correction; the canonical gate remains Luna's.

## Final operator UAT directory chrome polish

This follow-up is UI-only. Redundant inventory/collection/reference directory headings are visually
hidden through the existing `sr-only` convention, retaining the directory regions' accessible names.
The provenance Browse list also hides its redundant “Site directory” caption; map mode retains the
meaningful “Mapped sites” heading. Stored material and Provenance sites retain their distinct section
headings. Detail headings, forms and meaningful filter names are preserved.

Peer directory search captions now use a visually hidden, explicitly associated `<label>`. The shared
DirectorySearch component opts into this behavior only at the audited directories; pickers, linkers
and contextual searches keep their visible labels. SeedLots' “Show lots”, Sowings' “Show Sowings” and
Plants' “Lifecycle” legends are visually hidden, preserving their native fieldset group names. Plants'
“Record type”, specific select labels, and the map's linked-record filter legend still distinguish
controls and remain visible. Plants' desktop filter rows align without stretching lifecycle buttons.

The approved order remains heading/subtitle → Saved Views row → search → filters → results. There
are no route, filtering, search, Saved View state, API or domain changes in this follow-up.

Fresh review covered the twelve VIEW-001 directory surfaces plus Geography's Provenance sites
variant at **1440×844, 1024×844 and 390×844**. **78 collapsed/expanded document and panel bounds
checks** found no horizontal overflow. Saved Views precedes search and remains outside filter grids.
**39 keyboard checks** proved Save → Saved views → named search (or the existing first filter where
there is no search), with visible focus. Additional checks proved search → Active in all three
operational directories at all three sizes. Accessibility snapshots retain the exact search labels,
directory region names and hidden native legends; placeholders are not used as accessible names.
Save dialog initial focus, Shift-Tab trapping and Escape return passed at all three sizes. Mobile
Rename/Update/Delete cancellation returned focus to each exact trigger without changing stored views.

Focused frontend regressions: **225 passed in 13 files** (SeedLots, Sowings, Plants, Harvests, Stored
material, Media, Suppliers, collection map, Provenance sites, App, UX004, Saved Views and native
reference interactions). The narrow pre-edit baseline was **11 passed in 2 files**. Final
whole-frontend Prettier, zero-warning ESLint, strict TypeScript and production Vite build passed.
The UAT preview remains healthy with the existing operator edits preserved. Screenshots, accessibility
snapshots and measurements are retained outside Git in the task's visual artifacts folder:
`/home/alessandro/.codex/visualizations/2026/10/06/01a11123-8454-79f0-b44d-97ce86b1fafb/view-001-chrome`. At this operator-UAT checkpoint the source was still unstaged and uncommitted at the feature base.
Independent verification subsequently added focused service/API coverage after enforcing the existing
90% backend threshold; the final canonical gate records the final tree-specific result.

## Initial browser review evidence and limitation

At 1440×844, normal UI proved an empty Dashboard Saved Views list; Global Search Save with query
`Preview` plus Harvest/Media kinds; case-insensitive duplicate conflict; Escape; clear/reopen exact
canonical state; Plants query/lifecycle/type Save using the same name on another surface; rename to
a long valid name; manual edit/reopen proving no implicit write; explicit Update; reopen/refresh and
Back/Forward; and Media Library Save with local/linked/Collection filters. Views were created through
the normal product UI and remain available in synthetic UAT.

The in-app browser connection then disappeared (`Browser is not available: iab`; browser inventory
empty). Rebinding, creating a new UAT tab and reopening the app browser panel did not restore it.
A separate normal-API UAT smoke proved live results **1 → 0 → 1** across a temporary synthetic
Supplier name edit/restoration, then deleted only its disposable view and verified the Supplier
remained. The Supplier fields were restored through normal PUT (its normal updated timestamp advanced);
no baseline record was deleted.

The layout follow-up above completed the Reference-directory and responsive visual/overflow review.
The initial browser-session limitation was resolved by the later operator UAT pass. Live-result
record-edit and browser Delete/stale/future-state cases are covered by the documented normal-UI
UAT and focused automated product/database tests. Screenshots remain outside Git.

## UAT and roadmap

UAT uses `http://localhost:15174`, synthetic **preview / preview**, healthy from this dirty worktree after
supported guarded retirement of the proven `9f48` old owner. Standard `make uat-preview-up`,
`make uat-preview-seed` and `make uat-preview-status` passed; DB/code head is `20261006_0034`,
frontend/backend/DB are healthy, fixture v1 has 31 baseline records and the preview owner is initialized. Fixture v1 is unchanged; Saved Views
are created through normal operator UI for review, rather than adding seed records or bumping the
fixture. DEV, Stable Preview, Feature Review and production runtime/data are not modified.

Operator scenarios:

1. Dashboard query `Preview`, filter Harvests/Media, Save view, clear, reopen exact canonical state.
2. Plants: text `basil`, All lifecycle + Groups, save, clear and reopen from the first result page.
3. Media: choose existing kind/association/target controls and save; Geography: text + existing mode.
4. Rename, edit a filter without saving, reopen to confirm unchanged stored state, then explicitly
   Update with current view and reopen to confirm replacement.
5. Delete a shortcut and verify matched collection records remain. Try duplicate names on one
   surface and the same name on another. Refresh and Back/Forward through opened normal URLs.
6. Change an underlying synthetic record, reopen and confirm current results rather than snapshots.
7. Try retained unavailable UUID filters; inspect mobile wrapping, keyboard dialogs and long names.

Collection productivity v2 remains open. **Bulk operations next**, then justified unified operational
history, then Orders/Purchases. BOTANY-003's approved WFO/TLS blocker and later release sequencing
remain unchanged. Sharing/default views/favorites/materialized results are not implemented.
