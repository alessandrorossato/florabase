# Proposed component and token changes

**Status: COMPLETE — DOCUMENTED DESIGN REVIEW · NO IMPLEMENTATION APPROVED.** Everything in this document is a PROPOSAL unless it is labeled EXISTING. Labels follow the [package legend](README.md#how-to-read-this-package).

Ten reusable rules, not per-screen redesigns. None of these tokens or components exists in the product yet, except where a row says EXISTING. Nothing here changes an API, the schema, domain rules, routes, filters or saved-view state.

## The ten rules

1. **One primary per surface.** A filled `primary` action appears at most once per header, dialog or form footer.
2. **The action owns its prominence.** The same verb looks the same on every record kind.
3. **Breadcrumb is the back route.** No context row above it. History-return buttons use the `back` icon and read "Back to <area>".
4. **Sentence case** for every label. Record types are common nouns (**D3**, DECISION PENDING).
5. **Nine type styles only.** Three weights: 400, 600, 650.
6. **Three radii, one shadow.** `radius-round` only for map marks. `elevation-overlay` only for overlays.
7. **One focus ring.** 3px `focus-ring`, 3px offset, −3px inset inside scrollports.
8. **Three breakpoints.** 48, 64 and 75rem.
9. **One status chip.** `LifecycleStatus` text in tone; `Badge` for neutral facts.
10. **One confirmation.** `ConfirmDialog`: Cancel first and focused, consequence stated, outlined danger.

## Token changes

| Token | Change | Value | Replaces |
| --- | --- | --- | --- |
| `focus-ring-width` | add | 3px | literal 2px/3px outlines |
| `focus-ring-offset` | add | 3px | 2px ×16, 3px ×6 |
| `focus-ring-inset` | add | −3px | −2px ×10, −3px ×13, −6px ×1 inside scrollports |
| `radius-round` | add | 999px | pills on markers and scales only |
| `bp-compact`, `bp-medium`, `bp-wide` | add (documented constants; CSS custom properties can't drive `@media`, so they're mirrored in a comment block and a lint check) | 48 / 64 / 75rem | 12 one-off queries |
| `record-visual`, `detail-visual`, `inspector-width` | add | 3rem / 4.5rem / 25rem | literals in `directory-system.css` and `detail-page.css` |
| colors, type, spacing, radius small/normal/large, `elevation-overlay` | **unchanged (EXISTING)** | — | — |

No color value changes. All six themes keep their exact measured values.

### Legacy type mapping (F-06)

| Legacy `font-size` in `styles.css` | Becomes |
| --- | --- |
| 0.65–0.72rem | `type-eyebrow` if uppercase, otherwise `type-label` |
| 0.75–0.78rem | `type-label` |
| 0.8–0.88rem | `type-small` |
| 0.9–1.05rem | `type-body` / `type-strong` |
| 1.1–1.25rem | `type-h3` |
| 1.4–1.75rem | `type-h2` |
| 2rem | `type-h1` / `type-metric` |
| weight 700 | 600 (`type-strong`) or 650 (headings) |

### Legacy radius mapping (F-10)

0.4–0.55rem → `radius-small`; 0.6–0.7rem → `radius-normal`; 0.75–1.25rem → `radius-large` on dialogs, otherwise `radius-normal`. 999px stays only on `.provenance-map-marker`, `.occurrence-density-scale` and map legend marks (→ `radius-round`). `.location-scope`, `.record-type-badge`, `.lifecycle-badge`, `.dashboard-filter-chips button` and `.primary-photo-badge` → `radius-small`.

## Component changes

| Component (file) | Change | Consumers | Risk |
| --- | --- | --- | --- |
| `TaskDialog` (`components/TaskDialog.tsx`) | Optional `initialFocus` ref; default unchanged (first focusable) | 32 files; backward compatible | Low |
| **`ConfirmDialog`** (new, beside TaskDialog) | `title`, `body`, `confirmLabel`, `cancelLabel`, `tone`, `pending`, `error`; Cancel first and focused | Replaces 21 `window.confirm` (F-02); later Harvest/Order/Inventory/Cover/Reversal confirmations | Medium: dirty-guard semantics are async instead of sync |
| `DetailHeader` (`components/CollectionUI.tsx`) | Default `headingLevel` 2; actions slot documented as primary → Edit → More | 10 Details families | Low/medium: heading-focus tests |
| `WorkspaceIntro` `contextActions` | Not rendered on Details (**D4**, DECISION PENDING) | Plants, Sowings | Medium: mobile return path must stay reachable |
| `DetailSummary` | Callers drop facts shown in the header (**D5**, DECISION PENDING) | Plant, Sowing, Seed lot | Low, content only |
| `DirectoryTools` + `DirectoryViewSwitcher` | Segmented presentation control; `compact` layout at `bp-compact` | 8 directories | Medium: `aria-pressed` and URL `view` precedence must hold |
| `PageHeader` (`ReferenceUI.tsx`) | Optional compact action slot | Directories only | Low |
| `LifecycleStatus` | Sole lifecycle chip; `OriginInspector` adopts it | 1 caller | Low |
| `Icon` | No new shapes; `back` replaces `←` | 8 labels | Low |
| `FieldLabel` | No API change; adopted when an editor is touched | Opportunistic | Low |
| CSS: `styles.css` | Delete legacy focus rules (`:427–431`) and dead `.record-type-badge`, `.ui-status-indicator`, `.seed-overview-facts`; token-map the selectors listed above | Global | Medium: broad cascade |

## Explicitly out of scope

- Map, tree and calendar controls keep their specialized workspaces (AGENTS UI boundary).
- Media's density and preview stay with MEDIA-VISUAL-001.
- No inspector or Quick Preview comes back. No new route, filter, saved-view field or API.
- No change to color values, fonts or the six-theme matrix.
