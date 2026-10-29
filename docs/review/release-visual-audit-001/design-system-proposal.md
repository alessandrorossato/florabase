# UI Foundation v0.1 release consolidation — proposed

The delivered [UI Foundation](../../ui-contract.md) remains authoritative. This document requires
operator acceptance before production work. Keep its semantic tokens, typography, scales, six theme
sets and compatible aliases. No new UI dependency, token hierarchy or universal overlay is justified.

## Shared grammar

`App shell → breadcrumb context → PageHeader → optional context/filters → content → optional inspector`.
Use PageHeader's existing `title`, `titleId`, `eyebrow`, `description`, `tools`, `actions` slots.
WorkspaceIntro remains an adapter. PageToolbar is a documented composition of existing tools; do not
create a React component solely to give that composition a name.

| Variant             | Identity / tools / content contract                                                                                                                                                                                                                                                                                                     | Narrow layout                                                                                                                              |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Directory           | Title + short factual description; DirectoryTools in header, top aligned when the title and controls share a line. Search → Filters if supported → Saved views if supported → one creation action. Context and removable dimension chips occupy their own wrapping region. Results/selection controls belong immediately above content. | Identity first, search full row, labelled controls wrap, primary action reachable. Never clip a group or use horizontal toolbar scrolling. |
| Detail              | Canonical breadcrumb; DetailHeader with identity/current status, labelled Edit, meaningful primary operation, secondary overflow; DetailTabs only where an existing section contract exists.                                                                                                                                            | Identity wraps; actions keep their names. Mobile detail is a real page/intentional inspector, never an accidental offscreen desktop rail.  |
| Activity / Timeline | ActivityPageHeader and chronological source/date semantics. Journal's Record menu, History read-only, Schedule creation remain different.                                                                                                                                                                                               | Date/source and content read together. Keep source/unknown date text; chronological order unchanged.                                       |
| Map                 | GeographyHeader context + compact directory controls, then map and inspectable evidence rail/legend. Three evidence types remain separate. Map title can stay Geography with explicit breadcrumb/subview identity.                                                                                                                      | Use existing List/Map or stacked arrangement, reachable textual alternatives/attribution. Provider loading stays explicit.                 |
| Tree                | Existing Taxonomy header: search, List/Tree, Filters; source evidence outside ordinary action cluster; graph retains camera, hierarchy and selection.                                                                                                                                                                                   | Existing compact inspector/fallback and fullscreen model. Do not turn graph nodes into directory cards or alter accepted interaction.      |
| Calendar            | Activity header, then separate month identity + List/Calendar and period navigation. This local view row is intentional.                                                                                                                                                                                                                | Readable agenda/day selection; same intent/status semantics and source targets.                                                            |
| Utility / Settings  | Focused title + operation; configuration/input/result regions. Labels Print lives at header level with clear disabled reason. Appearance remains independent of server settings.                                                                                                                                                        | Controls stack; physical print page remains mm-based and white/black in every theme.                                                       |

## Surface hierarchy

Use a page background, a single grouped content surface where useful and ruled semantic sections.
Reserve a raised surface for an actual overlay. Selection requires the existing semantic edge/fill
plus text/ARIA; hover is not selection. Rich photographic cards belong to Media's separate design.
Empty unselected context should be a concise hint; retaining a large blank inspector is a deliberate
page-family choice, not a mandatory pattern.

Body/UI uses Source Sans 3; structured scientific names use Source Serif 4 and semantic italic.
Cultivar, common name, authority and operator label remain appropriately roman. Preserve 44px house
controls; do not introduce a second compact scale. Rows may grow for real content instead of hiding
names, uncertain quantities or dates. A narrow row can move metadata below identity before shrinking
its reading column.

## Interaction ownership

| Surface                      | Size/layout recommendation                                                                                                  | Dismissal/focus contract                                                                                                                                                                                                                                                    |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Small popover / action group | Content-sized, viewport-clamped; existing OverflowMenu and controlLayers                                                    | Nonmodal; Escape closes innermost layer, outside click preserves new intentional focus, action/Escape returns as appropriate. Use existing group semantics; do not claim arrow-key menu semantics without implementing/tests.                                               |
| Filter drawer                | Existing native TaskDialog right drawer, field-width controls, bounded scroll, title/Close and Reset/Done                   | Live filters; reset preserves search. No extra Apply model. Escape/backdrop safe and returns focus.                                                                                                                                                                         |
| Confirmation                 | Short, content-sized native TaskDialog; explicit consequence and Cancel/destructive action                                  | **Proposed extension:** optional `initialFocusTo` ref distinct from existing `returnFocusTo`. Dangerous confirmations select Cancel; callers retain pending/dirty guards. Test default callers as well. Inspect an equally small existing mechanism before adding this API. |
| Small atomic form            | TaskDialog with bounded fields and actions                                                                                  | Labelled fields; appropriate first input; safe cancel/pending behavior.                                                                                                                                                                                                     |
| Contextual editor            | Existing EditWorkspace with mounted background, meaningful title/tabs, internally scrollable form and available Cancel/Save | Caller owns route/draft/dirty/pending. Direct reload uses same content full page; no invented background. Identity retains its four independently saved sections.                                                                                                           |
| Full-page creation           | Existing semantic form canvas, current step/section model, one-column mobile                                                | Preserve prerequisites, PartialDate precision and field validation/focus. Do not convert every task into a wizard.                                                                                                                                                          |
| Detail inspector             | Existing QuickPreview/RecordPreview, domain inspector or Media's contained on-demand preview                                | Desktop rail and narrow presentation are explicit variants; keep selection synchronized and links meaningful.                                                                                                                                                               |

## Tokens and compatibility

Reuse surface/surface-subtle/surface-hover, text/text-muted, border/border-strong, primary/subtle,
focus-ring, danger/subtle, warning-text/subtle, overlay-backdrop/elevation-overlay. Keep the existing
spacing, type and radius tokens. Do not repurpose primary as a scientific data ramp. Retain native
range comparison slots, numeric/striped equivalents and provider imagery; themes must not request
new external data or invert photos. Labels retains black QR/white paper and physical geometry.

## Operator decision choices

1. **Recommended:** approve grammar plus F01/F02 priorities, then authorize a narrowly scoped shared-controls implementation wave. Accept the rest as a ranked migration backlog, with Media independently approved and WFO/print/zoom checks still open.
2. Approve only F01 safe destructive focus first; retain current layouts while the remaining evidence gaps are completed.
3. Request revisions to named proposal examples before any implementation.

Acceptance of these documents does not authorize staging, delivery, data/schema changes, IA changes,
a broad CSS pass or canonical FULL verification in this phase. Later shared UI infrastructure work
must receive repository-selected **FULL** verification after independent/operator review and freeze.
