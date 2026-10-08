# Saved operator views — VIEW-001

Saved Views are private named shortcuts to existing operator search/filter state. PostgreSQL stores
that state, never result rows or counts. Reopening uses the normal application URL and queries the
current collection. Operator UAT and independent verification passed. The feature is verified.

## Supported surfaces and audit

All targeted directories had useful stable controls. Global Search already had a URL parser and
serializer (`collection/searchApi.ts`); other directories previously kept most controls locally.
VIEW-001 adds only small URL adapters for those controls (`saved-views/state.ts` and
`useDirectoryView.ts`). Existing default routes, matching predicates, ordering and domain rules stay
intact. Plants already supported `type`; Geography already addressed exact place/site selection,
which remains distinct from a reusable view.

| Surface ID             | Surface                     | Version 1 canonical keys                                                                                                                                        | Prior filter URL support   | Default omitted                              |
| ---------------------- | --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- | -------------------------------------------- |
| `global_search`        | Dashboard Global Search     | `q`, repeated `kind` array, `identity_id`, `lifecycle`, `location_id`, `supplier_id`, `provenance_place_id`, `provenance_site_id`, `event_kind`, numeric `year` | Yes, SEARCH-002            | Empty query/filters/kinds                    |
| `seed_lots`            | Seed lots                   | `q`, `lifecycle` (`active`, `history`, `all`)                                                                                                                   | No                         | `active`                                     |
| `sowings`              | Sowings                     | `q`, `lifecycle` (`active`, `completed`, `all`)                                                                                                                 | No                         | `active`                                     |
| `plants`               | Plants / PlantGroups        | `q`, `lifecycle` (`active`, `history`, `all`), `type` (`all`, `plant`, `group`)                                                                                 | Type only                  | `active`, `all`                              |
| `harvests`             | Harvest records             | `q`, `material`, `source_type`, `identity_id`                                                                                                                   | No                         | All materials/sources/identities             |
| `stored_material`      | Stored Harvest material     | `q`, `state` (`active`, `depleted`, `all`), `material`, `identity_id`, `location_id`                                                                            | `tab=stored-material` only | `active`, all materials/identities/Locations |
| `events`               | Global Journal              | `category` (`all`, `observations`, `cultivation`, `status`)                                                                                                     | No                         | `all`                                        |
| `media`                | Media Library               | `q`, `kind` (`local`, `external`), `association` (`all`, `linked`, `unlinked`), `target` (existing Collection/record types, including Supplier)                 | Exact detail only          | All kinds/associations/targets               |
| `botanical_identities` | BotanicalIdentity directory | `q`                                                                                                                                                             | No                         | Empty text                                   |
| `orders`               | Orders directory            | `q`, `supplier_id`                                                                                                                                              | Yes, ORDER-001             | Empty text, all Suppliers                    |
| `suppliers`            | Supplier directory          | `q`                                                                                                                                                             | No                         | Empty text                                   |
| `locations`            | Location directory          | `q`, `scope` (existing Location usage scopes or `all`)                                                                                                          | Exact detail only          | `all`                                        |
| `geography`            | Geography                   | `q`, `mode` (`places`, `sites`, `map`)                                                                                                                          | Exact place/site only      | `places`                                     |
| `provenance_map`       | Collection origins          | `q` (existing identity text), `seed_lots`, `plants` (booleans)                                                                                                  | No                         | Both record classes enabled                  |

No targeted directory was artificially excluded. Detail tabs, reference/profile editors, native
range and external-occurrence views, label sheets, imports, and operation wizards are intentionally
unsupported: their state is record/context selection, form input, or an explicit external-data
operation, rather than a reusable directory dataset. No additional filtering capability is introduced.
Geography's stored-coordinate Map mode remains its existing internal site view; collection-provenance
map controls remain separate. Map center, zoom, selected marker and popup are never saved.

## Canonical state and URLs

Each surface has an explicit allowlist, value types, defaults and version validation on the backend.
Directory UI adapters expose those same existing controls. Text is trimmed, blank/default values
omitted, UUID text lowercased, and repeated Global Search kinds deduplicated in the existing kind
order. Directory text is bounded to 200 characters; Global Search retains its existing 120-character
bound. There is no sort key because these screens expose no stable operator sort selector.

Global Search serialization and opening reuse `readSearchState`, `searchParams` and `searchHash`.
Its backend combination validation is shared with SEARCH-002's endpoint through `validate_filters`;
Saved View code does not implement matching or execute search while listing. The search query
semantics and error messages are preserved.

An example normal route is `#/plants?q=basil&lifecycle=history&type=group`. Stored material opens
`#/harvests?tab=stored-material&...`. Global Search keeps `#/dashboard?...` with repeated `kind` query keys.
Neither a SavedView ID nor an arbitrary stored route participates in the URL. Browser refresh and
Back/Forward use the ordinary parsers; changing controls updates their ordinary URL. Invalid known
values in a manually entered directory URL fall back to that control's default. Persisted state is
validated strictly; unknown or invalid saved keys never open as a broader view.

Pagination, loaded count, selection, detail/Quick Preview, creation/editing action, dialog/form state,
errors, loading, toasts, tree expansion, focus, scrolling and browser history position are excluded.
Opening starts at offset zero and closes transient selection on the directory. The URL has no
pagination or selected-record coupling. Manual changes never mutate a stored Saved View.

## Persistence, privacy and compatibility

`SavedView` contains an application UUIDv7, `owner_id` referencing the authenticated User, human
`name`, finite `surface`, integer `state_version`, validated JSONB `state`, and UTC creation/update
timestamps. Initial state version is **1**. Names are trimmed, nonempty, Unicode, free of control
characters, and at most 120 characters. A PostgreSQL unique index on owner, surface and `lower(name)`
prevents case-insensitive duplicates on that surface, including racing writes. The same name may be
used by another owner or on another surface. PostgreSQL's normal `lower` behavior follows the
existing identity-name convention; this is not transliteration or fuzzy equivalence.

Every read/write includes the actual session User UUID. A foreign ID returns the same typed 404 as a
missing ID; every mutation uses existing Origin and CSRF protections. No sharing or visibility model
changes the single-owner auth architecture. User removal cascades only that user's private views.
The unique index's owner/surface prefix serves the list access paths; no JSONB GIN index is needed.
Listing is one SavedView SELECT per bounded 100-row page, deterministically ordered by surface, lowercased name and UUID;
it never executes views or resolves referenced records. Controls load the list only when expanded and offer Show more Saved Views to access later pages.

Creation and state replacement accept only v1 and reject invalid/unknown keys, enums, UUIDs, types,
combinations, transient fields and empty/default state. PATCH surface is immutable. Rename does not
validate/reinterpret old state. Future versions and invalid persisted v1 state remain listable with
explicit compatibility, renamable and deletable; Open explains incompatibility and does not navigate.
An explicit Update with current view may replace old state with a valid v1 state on the same surface.

Filter UUIDs are saved as exact values, with no foreign-key relationship to the filtered records.
Deleting a referenced record never drops or substitutes its filter. Global Search retains the exact
UUID in active chips; Harvest identity controls show “Unavailable botanical identity” plus its UUID,
and Stored material preserves an unavailable Location option. Existing exact-filter APIs/predicates
return zero matching records when references are missing. Those views remain manageable.

## API and operator flows

- `GET /api/v1/saved-views`: current user's views, optionally filtered by typed `surface`, with bounded 100-row pages and an `offset`.
- `POST /api/v1/saved-views`: name, surface, version and canonical state; 201 on creation.
- `PATCH /api/v1/saved-views/{id}`: rename, or replace `state` and `state_version` together.
- `DELETE /api/v1/saved-views/{id}`: exact owner shortcut only; 204 on success.

A duplicate name returns typed `saved_view_name_conflict` (409). Missing/foreign views return
`saved_view_not_found` (404). Invalid writes return 422. There is no execution endpoint or arbitrary
path input. Generated OpenAPI and TypeScript declarations remain backend-authoritative.

Supported directories have compact Save view and Saved views controls; Save appears only with
meaningful valid state. The name dialog identifies the surface and reports validation/conflicts.
Directory Saved Views controls occupy their own row below the heading/subtitle and above the search
or filter area, outside ordinary filter grids; expanded panels remain separate from those filters.
Redundant peer directory headings, search captions and lifecycle legends are visually hidden using
the existing `sr-only` convention. Explicit associated search labels, named directory regions and
native filter-group names remain accessible; meaningful section/filter headings remain visible.
Saved views offers Open, Rename, Update with current view on the same surface, and Delete. Both
replace-state and delete ask for explicit confirmation. Dashboard provides an all-surfaces entry
without another navigation destination. Existing native modal focus/Escape/return handling is reused.
Actions wrap on small screens and long names wrap inside their panel.

Migration `20261006_0034` adds only `saved_views` and its constraints/index. Upgrade preserves all
existing data. Downgrade refuses before DDL while any Saved Views remain, following existing
populated-history safety conventions; after explicit deletion it removes only this persistence.
Database backup/restore naturally includes Saved Views.

Collection productivity v2 remains open. BULK-001 operator UAT and independent final verification
passed. Justified unified operational history follows bulk moves, then Orders/Purchases. Sharing,
favorites, defaults, execution history,
notifications, materialized results, browser-local persistence and BOTANY-003 work remain deferred.

## BULK-001 interaction

BULK-001 selection mode, typed selected IDs, target and move preview are transient local interaction state. They never enter a Saved View or URL. Opening any Saved View, including the identical current view, clears selection; changing filters, rendered membership or navigating also clears it. See [bulk operations](bulk-operations.md).

## History extension — HISTORY-001

The fourteenth surface, `history`, has an explicit v1 contract: repeated `category` in the stable
Events / Propagation / Germination / Harvests / Stored material order, optional `subject_kind`, and
optional integer `year` (1–9999). Empty/default controls are omitted. Example:
`#/history?category=event&category=harvest&year=2026`. Timeline year follows the date shown, including
explicit Recorded fallback. Invalid URL values fall back consistently; invalid persisted values,
unknown keys and transient pagination/selection are rejected. Opening resets to page one even when
reopening the identical view. Normal rename/update/delete and owner/CSRF protections are reused.
The original thirteen adapters are unchanged. Migration `20261007_0035` extends only the surface
check; downgrade preserves other views and refuses until History views are explicitly deleted.
See [History contract](operational-history.md).

The global `events` surface is displayed as **Journal** and continues to open `#/events` with the
same category values. Sidebar collapsed groups are a separate browser presentation preference,
never Saved View state. History's empty category set is visibly **All activity**; category chips and
year clearing preserve the existing History v1 state and page-one opening behavior.
