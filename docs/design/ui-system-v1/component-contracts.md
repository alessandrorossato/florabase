# Component contracts and ownership

The old audit's [actual component inventory](../../review/release-visual-audit-001/component-inventory.md) and [consumer map](../../review/release-visual-audit-001/component-consumers.json) remain authoritative for existing code. The following is the proposed consolidation ledger. Gate B begins by checking each current export/prop rather than creating aliases for all names.

| Contract           | Current owner / reuse                      | Proposed responsibility and acceptance                                                                                                       |
| ------------------ | ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| PageHeader         | WorkspaceUI                                | Intrinsic grid/wrapping tools; no flex-basis becoming block height; one title, description and labelled actions                              |
| PageToolbar        | DirectoryTools                             | Controlled query, actions, filters and Saved Views in predictable order; compact intrinsic sizes                                             |
| Breadcrumbs        | WorkspaceUI/current route pages            | Semantic navigation/list, current item, exact back context; no new route taxonomy                                                            |
| Search             | existing SearchField / DirectoryTools      | Visible or programmatic label, clear action, Escape behavior, preserved query and result announcement; no placeholder-only name              |
| FilterDrawer       | DirectoryTools                             | Domain supplies fields, live/apply semantics and counts; labelled close, initial focus and return focus; no invented common filter schema    |
| ViewSwitcher       | current specialist/segmented controls      | Existing representations only; aria-pressed or real tabs, labels and URL state owned by page                                                 |
| Saved Views        | existing SavedView menu                    | Only supported page families/dimensions; preserve private ownership and current URL serialization                                            |
| Buttons / overflow | house controls and Icon                    | Essential verbs visibly labelled, secondary familiar icon with accessible name; menu never hides the sole primary action                     |
| Popovers           | existing house menu/popover pattern        | Anchored placement, Escape/outside dismissal, roving/menu keyboard where appropriate, focus return                                           |
| Dialog             | TaskDialog / ConfirmDialog                 | Proposed `initialFocusRef` or equivalent safe-target API; default destructive confirmations to Cancel; pending/error stays open              |
| Form fields        | current house form controls                | Label/control/help/error IDs, required text, fieldset legend, error summary points to actual control                                         |
| Reference pickers  | ReferencePicker                            | Reuse async combobox, loading/no-match/error, keyboard selection and collection-local identity; no replacement native datalist in production |
| Record row         | CollectionUI / directory domain rows       | Stable identity, one primary open action, separately labelled preview/selection; no nested button/link collisions                            |
| Card               | collection / Identity / Media-owned cards  | Actual assigned image or truthful placeholder, consistent media geometry, long name wrapping, no inferred cover                              |
| Table              | existing table patterns                    | Caption/name, scoped headers, preserved units/values; mobile labelled record blocks or bounded table scroll for genuine comparison           |
| StatusBadge        | WorkspaceUI                                | Text plus semantic color, lifecycle vocabulary owned by domain; Flowering/Fruiting are Journal occurrences here                              |
| KPI summary        | WorkspaceUI MetricCard / dashboard summary | One compact facts strip, denominator/time/source context; no trend from snapshots or group-to-individual sum                                 |
| Pagination         | DirectoryTools/current pages               | Actual page/offset/count, disabled edges, current page, retains query/filter; no prototype sample count posed as a server page               |
| Inspector          | current preview panels                     | Optional selection-only allocation; stable heading, labelled close, responsive modal and row focus recovery                                  |
| Empty state        | WorkspaceUI                                | No records vs no matches vs no selection differ; one useful action, concise explanatory copy                                                 |
| Loading state      | WorkspaceUI                                | Preserve useful context, aria-busy/status, no fake metrics or destructive focus jump                                                         |
| Error state        | WorkspaceUI                                | Specific retry/recovery, retained query/draft, role alert for new failure, no fabricated empty success                                       |

## API extensions worth making

1. Fix PageHeader geometry at its owner once. Add no page-level min-height overrides. Existing Media's scoped fix can remain until this migration is accepted.
2. Add an explicit initial-focus target to the house dialog without changing other modal semantics. Consume it in destructive flows after independent regression review; don't globally choose the first button by DOM accident.
3. Express optional inspector layout as composition. Do not add fetch/URL/record-type props to DirectoryPage.
4. Share error-summary-to-section-to-field focus through FormSections, preserving current domain field mapping and asynchronous timing.

## Do / don't

Use `QuantityValue`/PartialDate display behavior already present; do not concatenate missing date parts or replace unknown stock with zero. Keep harvested quantity and stored remainder separate. Link to the actual target record; an Identity hub is not a SeedLot detail route. Keep unrelated reference geography, provenance, location and supplier distinct.

The HTML design specimen uses small native interactions to test a composition. Its helper functions are intentionally not a new component API and must not be copied as production replacements for existing pickers/dialogs. React reuse, controlled state, translated error keys and component test contracts belong to Gate B.

## Gate B focused reusable checks

- Header: long title + search + filters + Saved Views + create at 1024px; compare actual bounds and first content position. Test wrapping and keyboard order, not CSS strings.
- Dialog: initial Cancel, Tab/Shift-Tab containment, Escape return, pending submit lock and failure retained. Include two mounted dialogs and a disappearing trigger.
- Inspector: absent when unselected; selected row opens; close returns focus; mobile same information; preserve search/page/selected key through detail/back.
- Form: async server validation reveals hidden section then focuses exact field; independent Identity sections do not submit each other's drafts.
- Theme: contrast roles and focus across six variants; image/QR/map roles remain specialized.
- Use existing Testing Library/Vitest and browser harness. Avoid a test for every trivial wrapper or snapshot of every CSS declaration.
