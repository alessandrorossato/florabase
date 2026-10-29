# Wave 1 final UX refinements — 29 October 2026

Operator-approved architecture and Proposal B remain. This candidate refines actual Dashboard,
Seeds and Plants only. The operator has now approved this framework subject to the final Plants
Gallery refinement. See [final Gallery and QA handoff](gallery-final.md) for the current phase;
the earlier unstaged-review restrictions below describe historical review evidence.

## Final contracts

- List hierarchy is record identity/scientific name, remaining quantity (groups only where meaningful),
  lifecycle, and three always-visible actions. Storage/source/provenance remain in Preview/Details.
  Individual Plants never acquire group quantities. Two-line bounded names cannot consume the
  independent quantity/actions columns; the complete identity is accessible in Preview/Details.
- Gallery uses approximately four columns at the 1440 baseline, three at intermediate widths and
  two on mobile. Image regions are 4:3, labels bounded, footers consistent. Small botanical
  placeholders retain full operation; primary/source/reference captions preserve visual provenance.
- `DirectoryRecordActions` reuses IconButton/Tooltip and typed Icon. Quick Preview, Details and Edit
  have separate domain callbacks; previews do not invoke editing. Details preserve canonical routes.
  Ordinary mobile record-body activation retains the existing full-detail affordance; the explicit
  Quick Preview action opens the overlay on every width.
- `DirectoryInspector` now always delegates to the existing native `TaskDialog`, centered/bounded
  on desktop and full-height on mobile. It neither reserves an inventory column nor creates a new
  dialog framework. Close/Escape, focus trap and connected-trigger/list fallback remain shared.
  Existing domain operations and nested edit confirmations remain owned by their original workflows.
- Modifier-selection extends `useBulkSelection`: Ctrl/Cmd record-body or row-background click enters
  selection and toggles eligible IDs. Subsequent ordinary body clicks and checkboxes toggle; actions,
  links and form controls are excluded. Select records remains the keyboard/touch entry and Exit
  selection remains explicit. All existing BULK-001 preview/apply behavior is retained.
- Dashboard's existing read endpoint samples at most eight active **individual Plant records** using
  PostgreSQL `ORDER BY random() LIMIT 8` over the full eligible relation, before any pagination.
  Five bounded queries resolve explicit primary links, active stored assets and identity references;
  no N+1 or provider access. The response uses Plant IDs and each card links to its Plant detail.
  Primary thumbnails are preferred; a broken/missing primary may use an explicitly labelled stored
  identity reference, then a botanical placeholder. Metadata for both candidates stays available.
  The client retains the sample for its mounted visit, including ordinary/day-driven refreshes.
  A fresh visit may sample differently; no duplicate Plant is added to fill eight positions.
- Quick add keeps all nine original destinations and visible labels, with nine distinct typed icons.

## Selection reset policy

The exact canonical domain filters plus loaded ordered visible typed IDs/eligibility form the scope.
A change clears active mode, IDs and any move dialog: search/type/lifecycle/identity changes,
visible membership removal/deletion, eligibility changes, edit/task scope, route changes and fresh
navigation (including reopening the same Saved View). Merely changing the List/Gallery `view`
parameter retains choices when all other scope inputs match, including Back/Forward. Storage
metadata refresh with the same eligible IDs does not itself invent a new scope; server expected
record/target revisions still reject stale moves. No hidden selection is retained across filters.
Maximum 100, active eligibility, target scope and atomic server Apply are unchanged.

## Product follow-ups — not implemented

[Cross-domain bulk proposal](bulk-operations.md) distinguishes supported contracts from candidates.
No bulk mutation, generalized delete, mass lifecycle API or new endpoint was introduced.

`DASHBOARD-CUSTOMIZATION-001` is planned: Settings-based widget visibility/order, optional preferred
photographic content and reset to defaults. Current named Dashboard components and one owning
query suffice; no drag-and-drop, persisted settings or speculative production registry was added.

## Integration and limits

Fetched `origin/main` remains `c77a1c5330de949168bf5f7c90d0f533af1bc320`, including Media #127 and
its test-inventory correction #128. The dirty Gate B/Wave 1 candidate is preserved in this worktree.
Dashboard OpenAPI/TypeScript artifacts are regenerated together; there is no schema migration.
Other directory families, Media, maps, taxonomy/tree and calendar retain their domain controls.
Review data, attachments, primary-photo assignments and covers are not reset or rewritten.

SQL random sampling scans the eligible population; it returns at most eight rows but is not a
large-library performance certification. Test seeding verifies repeatability without probabilistic
assertions. A huge collection may merit a measured sampling strategy in a separate increment.
Physical devices, assistive technology and true browser-zoom certification remain manual checks.
