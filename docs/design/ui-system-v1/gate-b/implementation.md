# Reusable composition and presentation contract

## Reuse map

| Need                   | Implementation                                                              | Ownership                                                                                                    |
| ---------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Directory structure    | `frontend/src/components/DirectoryPage.tsx`                                 | Named header, toolbar, selection, feedback, content, pagination, optional inspector slots                    |
| Heading/search/filters | Existing PageHeader, DirectoryTools, DirectorySearch, DirectoryFilterSelect | No competing page header or drawer                                                                           |
| Presentation           | DirectoryViewSwitcher + `directoryPresentation.ts`                          | Controlled List/Gallery; native buttons with names and aria-pressed                                          |
| Record list/gallery    | DirectoryRecords, DirectoryRow, DirectoryCard                               | Caller supplies stable key, label, formatted name, href, visual, metadata/status, selection, preview/actions |
| Optional preview       | DirectoryInspector                                                          | Inline above 75rem; TaskDialog below; Close first; explicit trigger and connected fallback                   |
| Chronology             | `ActivityPage.tsx`                                                          | Header/tools/feedback/chronology/pagination composition; owning capability supplies ordered evidence         |
| Photographs            | Existing PrimaryPhotoVisual supplied as the visual slot                     | Existing authenticated local thumbnails/external opt-in and broken-image behavior remain authoritative       |
| Navigation             | `navigationIcons.ts` + existing typed Icon                                  | CurrentColor, unified strokes, decorative SVGs; text supplies accessible names                               |
| Colors/type/spacing    | Existing semantic Foundation CSS                                            | New directory CSS consumes existing tokens; forest sidebar proposal is scoped to the dev lab                 |

DirectoryPage does not fetch, sort, infer permissions, invent actions or interpret
domain fields. Use stable record IDs as React keys. The **same filtered authoritative
page** renders in either mode; do not request a second dataset or silently reset scope,
query, pagination or checked/preview selection on a view toggle. Provide BotanicalName
with structured scientificName so cultivar text remains upright. Use existing quantity
and partial-date formatters for real domain integrations. Row thumbnails reserve an
aligned slot; Gallery images occupy a 4:3 frame using object-fit: cover, never stretch.
Missing photos remain explicit and carry the record's accessible name.

PageHeader already separates identity and tools. The existing normalization rule now
explicitly sets `flex-direction: row` alongside its wrapping flex bases, preventing
the legacy column axis from turning a width basis into an 880px vertical header.
There is no fixed heading height. Mobile content, metadata and long names wrap and
scroll. Desktop previews cannot reduce the record list to an empty permanent panel.

Inline preview Close restores focus to the currently mounted row's trigger, or a
connected page fallback if the trigger disappeared. Filtering which removes the
selected record must close the preview without pulling focus away from the search.
Compact preview uses native modal containment/Escape and the same focus fallback.
The caller supplies refs; it must reconnect the selected trigger after changing row
representation. TaskDialog's optional fallback is backward compatible with callers
which omit it. Do not replace domain-specific Media Quick Preview with this generic
record inspector.

## URL, history and browser preference

`DirectoryView = "list" | "gallery"`. For an explicitly supported presentation
surface, the precedence is:

1. Valid `view=list|gallery` in the existing hash query.
2. Valid browser preference `florabase.directory-view.v1.<surface>`.
3. Defaults: SeedLots/Sowings/Suppliers/Orders List; Plants/Botanical identities Gallery.

The value is a browser presentation preference, shared by users of that browser,
not an owner record, permission or server default. Store only the mode, never record
IDs, names, filters, credentials or data. Storage denial safely falls back to URL/state.
Mount/key the hook per directory surface. It does not synchronize separate browser
tabs; URL/history restoration within the page is supported.

Selecting a mode pushes only `view`, preserving existing history.state and all other
query dimensions. Repeated selection of the same URL creates no duplicate history
entry. `popstate`/`hashchange` restore presentation. Existing `useDirectoryView` owns
canonical filters and retains unknown presentation query parameters when updating
supported filters. Do not rename a canonical parameter or add it to an API request.

**Saved Views v1 stays unchanged:** save only the delivered validated canonical filter
state. It excludes mode, selection, dialogs, focus and offsets. Reopening a saved view
uses the ordinary canonical URL/page-one semantics and current browser presentation
preference/default; an explicit shared URL can override with `view`. No state-version
bump, schema migration, new surface registration or local SavedView persistence.
Maps, taxonomy, schedule and timelines never acquire this List/Gallery parameter.

## Safe page scaffold

```
make ui-page NAME=SeedLotReview ARCHETYPE=directory
make ui-page NAME=RecordedWork ARCHETYPE=activity
python3 scripts/ui_page.py --name SeedLotReview --archetype directory --dry-run
```

The Python standard-library generator accepts a PascalCase identifier of at most
64 characters and exactly the two implemented archetypes. It resolves output inside
`frontend/src/ui-pages/<Name>/`, rejects escaping symlinks/paths and existing folders,
uses exclusive file creation and rolls back only its own partial files on failure.
Make passes arguments through environment values rather than interpolating shell code.

It creates three files: a typed composition using real exports, a Vitest skeleton
with explicit `test.todo` domain acceptance (no placeholder passing claim), and a README
with integration/accessibility/state obligations. It adds no route, navigation item,
API, dependency or migration. Replace TODOs, reuse existing owning data/filter/formatters,
implement meaningful tests, integrate deliberately, then run CI-004-selected verification.

Working examples are in `frontend/src/ui-lab/Lab.tsx`: bounded SeedLot/Plant/Sowing/Identity
directories and ActivityPage with three captured Journal entries. The scaffold itself
does not claim those entry facts or implement a generic history service.

## Development-only showcase

`make ui-lab` uses the installed Vite and serves the separate `frontend/ui-lab/index.html`
entry at `http://localhost:15284/ui-lab/`. That entry imports only in DEV. The default
production build uses the original index and App routes, with no lab import, build
input, fixture photographs or privileged review route. After a normal build run:

```
python3 scripts/check_ui_lab_build.py
```

The lab reuses actual styles, fonts, appearance store, controls, dialogs and canonical
filter adapters. It has no API requests/login or domain mutations. The top review bar
is development chrome included in the captures; it is not proposed product navigation.
Only the Dashboard baseline fits within 844px by design; other records and mobile
layouts retain natural page scrolling. Keep the external Gate A studies as historical
references; do not interpret the lab's placeholder links as new application routes.
