# Journal / History product pass — ACTIVITY-001

The final Activity-family visual/interaction layout and latest evidence are consolidated in the
[Activity refinement handoff](activity-family-refinement-handoff.md). The source/domain audit below
remains applicable; its earlier visual evidence is retained as historical candidate evidence.

Refined implementation candidate, 2026-10-13. Same `a165` worktree and
`feat/journal-history-product-pass` branch; base remains
`b99bb4af62efbb0c531e656009e0880559fb6f0f`. Unstaged/uncommitted; independent QA owns acceptance
and canonical verification. No migration, new domain or sidebar restructuring.

## PRODUCT MODEL

**Journal = recording hub + operator notebook fallback.**
**History = global read-only timeline of past facts.**
**Schedule = future intended work.**

If a structured concept already has a delivered workflow, the Record hub opens that canonical
workflow. Otherwise the operator uses the existing contextual Journal entry form. History owns
none of the records it displays; correction always belongs to the source.

The source audit remains unchanged: existing Plant/PlantGroup Events, propagation receipts,
germination observations, Harvests, material dispositions/conversions, and persisted Schedule
completion. Current fields, `updated_at`, ordinary creation timestamps, unknown acquisition and
unrecorded lifecycle transitions never manufacture operational facts. Existing Event models/API
and `events` route/Saved View identifiers remain internal contracts; operator copy uses Journal/entry.

## RECORD HUB

The header **+ Record** action uses shared `OverflowMenu`, with outside-click/Escape dismissal,
arrow-key navigation and focus return. The menu contains delivered actions only. The target chooser
appears after the menu closes; it reuses the existing bounded collection picker and shared modal.
No parallel action form, nested menu/modal flow, provider call or new Event/Activity domain is added.

`recordWorkflows` in `RecordLauncher.tsx` is the small extension point: add the canonical route of a
new delivered workflow when it exists. Target-dependent actions reuse that record's existing detail
route. Future Measurements, Phenology, Health, Cuttings/propagation and care workflows are examples
for that extension, not implemented actions.

## STRUCTURED ACTION ROUTING

| Record choice                               | Existing canonical destination   | Supported prefill / next step                                                                                                                     |
| ------------------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Record harvest                              | `#/harvests?action=create`       | Existing full Harvest form; choose its source there.                                                                                              |
| Record sowing                               | `#/sowings?action=create`        | Existing Sowing form and SeedLot selection.                                                                                                       |
| Move plants / groups                        | `#/plants`                       | Existing atomic bulk Location workflow: select visible records, Move selected, preview/apply. No invented bulk deep link or second movement form. |
| Complete scheduled work                     | `#/schedule`                     | Choose a planned activity and use its versioned completion action.                                                                                |
| Record germination                          | `#/sowings/<id>?tab=germination` | Choose the existing Sowing, then use its real dated-observation form.                                                                             |
| Add observation / note; Other journal entry | Plant/PlantGroup `?tab=events`   | Existing contextual Journal and Add entry form. Choose Observation/Other there.                                                                   |

Only supported target routing is reused. Due dates and hypothetical action prefill are never coupled
into those workflows. The original single-record movement/lifecycle entry workflows remain contextual
source workflows; the hub's multi-record move choice goes to the delivered bulk operation.

## JOURNAL FALLBACK

The notebook supports useful observations and contextual notes without requiring a future structured
domain. The global feed shows ordinary recorded entries and their full-note search matches. Structured
Harvest/operation backing records remain in their authoritative/contextual pages and History, rather
than repeating them as notebook entries. Bare movement/transfer/lifecycle/legacy Harvest actions with
no notes stay in History; annotated ones can contribute notebook context. No records are deleted or
rewritten by this presentation rule.

The compact chronology shows date, Journal source, entry type, target link, note excerpt and direct
context links. A target opens the existing record Journal for review/edit. No large per-row mutation
buttons are added globally. Plant/PlantGroup detail tab is now **Journal**, retaining its `events` URL.
The contextual editor's Add entry / Entry type terminology removes unnecessary Event wording.

Existing create/edit/date/content validation and current-state side effects remain authoritative.
Movement/lifecycle creation applies its existing transition; correction/deletion does not recompute
current state. Shared native dialogs preserve pristine Escape/backdrop dismissal, dirty confirmation,
pending-action protection, focus return and mobile fit. No structured Florabase form is copied.

## HISTORY

History remains read-only. Rows show a compact date column, rail/marker, concise source badge,
fact title, owning record link and bounded secondary context. Sources are Journal, Collection
operation, Propagation, Germination, Harvest, Stored material and Scheduled activity.
Persistent product explanations and repeated **Why this fact appears** disclosures are removed.
There are no mutation or creation controls on the timeline.

Date semantics remain visible where required: occurrence PartialDate retains year/month/day
precision; an unknown occurrence may show explicitly labelled **Recorded … (UTC)**; terminal
Schedule facts show **Completion recorded … (UTC)**. Completion time is not the work occurrence
date. Deterministic order, stable typed keys, source correction and bounded SQL pagination/count
remain unchanged. Search is applied before count and page in the existing one-statement projection.

## DUPLICATION

- Structured Harvest suppresses its backing Event in History; the global notebook excludes it.
- Event-backed operation receipt contributes one operation fact, retaining supported reversal status.
  Its backing entry does not independently populate the global notebook.
- Seed conversion suppresses its owned disposition; only persisted reversal instants justify a
  separate reversal fact.
- Bare movement/lifecycle facts stay in History; explanatory notes add operator meaning in the notebook.
- An ordinary Journal entry projected in History is the same source ID, not a duplicate stored record.
- Schedule completion and explicitly linked occurrence are distinct evidence: completion's recorded
  transition time versus the occurrence's explicitly chosen date. Retries do not add another fact.

## VISUAL FOUNDATION ALIGNMENT

Dashboard implementation and stylesheet were inspected directly. Activity uses the same flexible
Dashboard toolbar and native right-side filter drawer styling, shared Saved Views presentation,
PageHeader, StatusBadge, OverflowMenu and TaskDialog. Styles use the existing semantic tokens.
Activity now uses document scrolling and the available workspace width, with no trapped list pane.
No global visual normalization or Dashboard redesign is part of this refinement.

## PAGE HEADER

Both pages use the established Activity eyebrow/title. Journal's compact + Record action sits in
PageHeader's action area and wraps intrinsically. History has no create action. At the operator's
final request, concise subtitles are restored: Journal says "Record collection work and keep
observations and notes." History says "Past collection activity, with links to its source records."
Redundant orientation paragraphs and page-level explanatory disclosures remain removed.

## SEARCH / FILTERS / SAVED VIEWS

Both toolbars are **Search → Filters → Saved views**, with growing search and adjacent controls.
Filters live in Dashboard's shared drawer pattern, not a permanent button wall. Active summaries
are removable and Clear filters appears only for active filters; reset preserves the search text.

Journal searches existing loaded notebook entries: entry type, full notes, target label/botanical
identity, destination and recipient. History's authenticated bounded `q` search covers projected
title/context, primary/related display labels and visible source terminology; it is not global search.
Literal `%`/`_` characters are escaped. Source labels do not search UUIDs or implementation table names.
The API and Saved View search contract is bounded to 200 characters.

Journal retains category membership and `events` Saved View surface. History retains categories,
primary record type, timeline year, page-one reset and `history` surface. Optional `q` extends version-1
states backward-compatibly; old Saved Views still open. Search/filter changes are URL-addressable;
back/forward/refresh restore state, and manual changes never silently save a view.

## RESPONSIVE / ZOOM

Final screenshots and [machine layout evidence](review/journal-history/refined/zoom-evidence.json)
live in `docs/review/journal-history/refined/`: 71 screenshots and 21 page measurements.
Review matrix: 1440×844 at 80%, 100%, 125%, 150%; 1024×844 at 100%, 125%; 390×844 at 100%.
Dashboard is captured alongside Journal and History for direct grammar/density comparison.

Zoom uses actual Chrome `tabs.setZoom` in an isolated temporary extension/profile. It changes the
CSS viewport and device pixel ratio: at desktop 80/100/125/150%, widths are 1800/1440/1152/960 CSS px.
This is not CSS zoom or a device-scale-only simulation. The zoom capture harness activates the
normal DOM handlers because its native pointer/key targeting does not track browser zoom reliably;
normal-zoom native interaction and focused keyboard/focus tests are separate evidence.

The final matrix passes: no horizontal document/main overflow, full-width toolbar growth, clean
wrapping, readable date/content columns and fitted drawers/dialogs. Long editor/drawer content
uses its normal modal scroll; page content uses document scrolling. Native normal-zoom checks pass
for launcher keyboard/outside-click/Escape/focus, filter/Saved View dismissal, notebook/germination
chooser routing, pristine editor Escape/backdrop/focus, dirty discard/continue, and each structured
source destination. Mobile create/edit/search/month precision/delete passes; its temporary note was
removed through the source UI. Compare [Journal desktop](review/journal-history/refined/events-1440-100.png),
[History desktop](review/journal-history/refined/history-1440-100.png) and
[Dashboard desktop](review/journal-history/refined/dashboard-1440-100.png).
Full screen-reader acceptance and global page review remain independent QA.

## SCHEDULE RELATIONSHIP

Completed ScheduledActivity projects one stable terminal fact at persisted `completed_at` (UTC).
Planned/overdue/cancelled activities do not enter completed History. Completion without entry adds
no botanical occurrence; optional compatible creation stays explicit/atomic/idempotent and retains
its own actual date. Schedule detail and target links remain canonical. Schedule UI is not redesigned.

## DASHBOARD REGRESSION

Dashboard still reuses History's shared source/date presentation. Ordinary notebook entries are
Journal; operation-backed facts and completions are History. Recent activity remains bounded at six.
Only shared source labels are simplified; no Dashboard layout, metric, search or sidebar redesign.
Existing search behavior and mixed-source recent-activity regressions are retained.

## UAT

Implementation uses a unique positively owned disposable preview, with the existing synthetic v4
fixture and normal `preview / preview` login. Repeated seed preserves row/media/manifest state.
The existing observations, Harvest, repot completion with explicit occurrence, inspection completion
without occurrence and cancelled follow-up are sufficient. No fixture extension or persistent UAT
reset/reseed/ownership change is needed. Temporary operator test notes are removed through the normal
workflow. Final disposable project `florabase-uat-preview-smoke-6f992cfb07eb` was retired after checks:
four containers, two owned images, one network and three volumes removed; zero residual owned
containers/networks/volumes. Protected operator Git/container/volume/database snapshots are unchanged.
The interrupted preview and an EOF-ended setup were also retired through positive-ownership cleanup.

## TESTS

Focused checks only; no canonical `make feature-verify`:

- Baseline: 92 backend History/Saved View tests and 11 Journal/History frontend tests passed.
- Backend final: 147 focused History, Saved View, Schedule, Event and schema tests; Ruff lint/format;
  strict mypy across 339 files.
- PostgreSQL: 57 focused tests for History, History Saved Views, Schedule, Dashboard and Event API,
  including literal text search before count/page and the preserved source/dedup/date/completion rules.
  Guarded disposable cleanup reports zero residual containers/networks/volumes.
- Frontend: 194 focused checks across the affected selection, including launcher/route/dismissal/focus, notebook suppression/search,
  drawer/filter reset, Saved View compatibility, contextual Journal, Schedule, Dashboard and existing
  UX regressions. The 42-test contextual Plant/Journal suite was rerun successfully after the final
  error-copy assertion correction. ESLint, strict TypeScript, scoped Prettier and production build pass.
- API artifacts regenerated for optional History `q`; `make api-check` reports no drift.
- Browser: requested real zoom/viewport matrix, direct Dashboard comparison and native normal-zoom
  interactions; final evidence linked above. No new fixture/guard code is changed.

No migration cycle, full release gate or global visual acceptance is claimed.

## SIDEBAR IA NOTES

No macro-category or ordering change. Defer the question of whether a cross-domain recording hub
belongs in Activity despite routing to Collection operations; whether Explore versus Maps is intuitive;
where Labels/Import/Export belong; and whether future Propagation affects Collection structure.
A dedicated pre-v0.1 navigation/IA review should resolve daily-workflow ordering before the freeze.

## DEFERRED

Labels; global visual review/normalization; sidebar IA changes; universal contextual timeline;
Material Lineage; Measurements; Phenology; Health; Cuttings; recurring care; QR/mobile capture;
new generic Event/Activity models; historical author/source fields; additional facts without persisted
operational evidence. Future domains join Record only after their real workflow is delivered.

Handoff boundary: **READY_FOR_VISUAL_REVIEW**. Candidate remains unstaged/uncommitted.
