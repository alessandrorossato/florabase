# Proposed UI System architecture

This is the Gate A implementation contract. Type names and signatures below are proposals, not shipped exports. Reuse UI Foundation v0.1 and its actual components before creating any wrapper.

## Composition boundary

A page owns API requests, query/URL restoration, mutations, permissions, validation, scientific evidence and domain-specific actions. A template owns landmarks, layout slots, responsive flow and presentational state placement. A template never fetches data, infers status, counts entities, invents filters, resets selection or writes URLs.

Existing `PageHeader`/`WorkspacePage` in `WorkspaceUI.tsx`, `DirectoryTools`, `EditWorkspace`, `FormSections`, `CollectionUI`, `TaskDialog`, `ConfirmDialog`, `ReferencePicker`, Saved Views and specialist controls are the starting implementation. The existing consumer map in `../../review/release-visual-audit-001/component-consumers.json` is the migration inventory. Do not rename every consumer to make the diagrams look uniform.

## Archetype matrix and named slots

| Proposed composition | Named slots                                                                            | Owns                                                                                       | Explicit boundary / first example                                       |
| -------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| DirectoryPage        | header, toolbar, activeFilters, selectionBar, content, pagination, inspector, feedback | Full width without selection; selected inspector at adequate width, modal equivalent below | Seeds; domain supplies eligible selection and server page results       |
| DetailPage           | breadcrumbs, identity, actions, sections, related, dangerZone, feedback                | Heading hierarchy and readable sections, optional on-demand context                        | SeedLot detail; no mandatory hero/photo or universal tabs               |
| FormWorkspace        | context, heading, sectionNav, errorSummary, fields, footer, feedback                   | Stable mounted draft, sticky safe footer, section focus/reveal                             | SeedLot create/edit; keep Identity's independent save boundaries        |
| ActivityPage         | header, toolbar, periodSummary, chronology, pagination, feedback                       | Time-column alignment, source labels, mobile chronology                                    | Journal / read-only History remain separate renderers                   |
| MediaWorkspace       | header, toolbar, selectionBar, gallery, pagination, preview, feedback                  | Integration contract with approved Media workspace                                         | Media owner supplies photographic layout, URL/offset and focus behavior |
| SpatialWorkspace     | header, toolbar, legend, canvas, results, inspector, feedback                          | Map-dominant allocation, fullscreen/selection frame and textual equivalent                 | Native ranges and occurrences retain separate semantics                 |
| CalendarWorkspace    | header, toolbar, period, calendar, agenda, inspector, feedback                         | Monthly grid / mobile agenda, period/focus region                                          | Schedule keeps explicit intended work and domain completion             |

```tsx
// Proposed API shape only. Domain data and effects stay at the call site.
<DirectoryPage
  header={<PageHeader /* current house API, plus approved layout fix */ />}
  toolbar={<DirectoryTools /* controlled query/filter/save state */ />}
  content={<SeedLotInventory rows={rows} onPreview={setSelected} />}
  selectionBar={
    selection.visible ? <BulkLocationActions {...selection} /> : null
  }
  inspector={selected ? <SeedLotPreview record={selected} /> : null}
  pagination={<SeedLotPagination {...page} />}
  feedback={<DirectoryFeedback state={state} />}
/>
```

Do not implement a slot just to match this diagram if current composition already provides it. The smallest Gate B can add missing layout behavior to the existing primitive and export a documented composition recipe. Slots accept ReactNode; conditional actions, not an `entityType` switch, distinguish domains.

## Selection and navigation persistence

The initial directory uses the full content width. A labelled Preview action selects a record; the selected row retains a visible border/background and a stable key. At desktop the inspector consumes approximately 310px only while open. If the remaining inventory cannot show its essential facts, the same preview becomes a modal/drawer instead. Closing returns focus to the invoking row; deleted/filtered-out rows use a predictable heading/result fallback. The prototype exercises the row-present case; Gate B must test the disappearing-row case.

Opening details must retain the exact prior query, page, sort, Saved View and selected key through the current route state. Browser Back restores the result context without a refetch that discards it. The prototype demonstrates selection/full-width recovery and a bounded Back link; it does not simulate server pagination or production URL restoration.

For Identities, recommend opening the hub directly: name and collection coverage are already present in the index, so another preview adds a step without enough new information. The optional inspector recipe is useful for inventory, not mandatory for every directory.

No second empty preview title or enclosing directory title duplicates the page heading. Initial focus does not automatically move to a newly loaded directory or selected record while a user is typing. Announce result changes politely, not the entire table.

## Form choice

Recommend continuous sections (B) for collection maintenance: users compare stock, date precision and acquisition without switching hidden panels. Anchor navigation is a compact outline, not a second wizard. One-panel A is retained as a meaningful guided alternative, especially for narrow step-dependent creation. It must reveal the section containing a validation error before focusing the field and keep all draft values mounted.

Keep current source choosers for sowing/harvest eligibility and the existing per-section Identity edit saves. Do not turn every create workflow into one universal seed form. The mockup's seed form shows hierarchy, not complete domain validation. React Gate B must reuse the existing control implementations, server-error mapping and `setValidationField(errors[0])` asynchronous focus behavior.

## Intentional variation

Inventory prioritizes quantities, units, exact/approximate/unknown, storage and lifecycle. Reference directories prioritize botanical name, cultivar and actual collection coverage. Activity prioritizes occurrence versus recorded time. Maps, Taxonomy and Calendar keep their specialist canvas models. These are different compositions of the same grammar, not design debt to flatten into cards.
