# Activity concept and Schedule UX review handoff

**Ready for concept/prototype review, not delivery.** Branch `feat/activity-concept-schedule-prototype`
in worktree `28ce`, base `76c0911` (freshly fetched main / PR #131). The study receives a reviewed
local commit after focused checks; no canonical verification receipt or production feature acceptance
is claimed.
`ACTIVITY-CONCEPT-001` is `implemented` for this bounded study, not `verified`.

## Review entry points

- [Current/proposed IA and actual-model audit](README.md).
- [Journal journeys, wireframes, data-contract risks and phases](journal.md).
- [Official-reference Schedule comparison](references.md).
- **[Isolated runnable Schedule prototype](http://127.0.0.1:15286/activity-lab/#/schedule?month=2026-10&date=2026-10-30)**.
- [Setup, functional boundaries and source reuse](../../../frontend/src/ui-pages/ScheduleUxPrototype/README.md).
- [Evidence gallery](evidence/index.html), [capture manifest](evidence/captures.json),
  [source identity](evidence/source.json).

The loopback Vite server serves only this worktree on 15286. It does not use Docker or the shared
15174 Review port. No live authentication, database, media or provider connection is required.
Reload deliberately resets synthetic changes. Its fixed presentation day is **30 October 2026**;
this is a fixture convention, not a proposed replacement for production's local-day rollover.

## What works and what is a proposal

| Scope                                                                                               | Status in this task                                                                                                                   |
| --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Central Journal, optional/no subject, provenance, templates, original-source corrections, promotion | **Design only**; journeys and wireframes distinguish existing Event workflows from new JournalEntry contracts                         |
| Compact differentiated History                                                                      | **Recommendation preserving current implementation**; no History source, API, SQL, mutation or layout change                          |
| Agenda, date rail, optional Week, Month, inspector                                                  | **Functional frontend on synthetic fixtures**, using actual shared components and Schedule rows/calendar                              |
| Create/edit/reschedule, target picker, complete/cancel, dirty guard and conflict reload             | **Actual existing ActivityDialog**, exported unchanged for reuse; transport and persistence are simulated                             |
| Optional supported Event completion                                                                 | Actual compatible form and deliberate choice; only an **in-memory synthetic receipt**, no botanical effect or real Event service call |
| Exact targets and linked Journal contexts                                                           | Canonical exact hashes retained; record-detail/History destinations are outside the fixture and are explicitly labelled unavailable   |
| Auth/concurrency/idempotency                                                                        | Synthetic context and simulator demonstrate states; no auth enforcement, SQL lock, transaction or multi-client proof                  |
| Date/filter/URL/paging                                                                              | Current Schedule parsers/serializers and API adapters reused; `ux=week` is prototype-only, not a new production URL contract          |
| API/schema/migrations/Saved Views                                                                   | Unchanged. Schedule still has no Saved Views; Journal/History existing v1 contracts remain unchanged                                  |

The simulator does not claim domain validation equivalence. In particular it does not apply Movement
Location effects, implement media retention, immutable source notes or real transactional promotion.
These remain the responsibility of the existing service or separately approved future work.
Unknown fixture API requests fail closed instead of forwarding to a backend. The real App/AuthProvider
is never mounted by this development entry.

## Visual and interaction evidence

**54 primary full-page captures:** Agenda / Week / Month × 1440 / 1024 / 390 CSS pixels ×
Botanical / Herbarium / Mineral × Light / Dark, each with an **844 CSS pixel viewport height**.
Actual raster dimensions and SHA-256 digests are recorded separately in the manifest.
Every capture records its route, palette, effective appearance, viewport and document scroll width.
All 54 primary captures have no horizontal document overflow. Full-page images include the review
chrome and below-fold content; they are not claims that every task fits in the initial viewport.

All three contact sheets were visually inspected:
[Agenda](evidence/contact-agenda.jpg), [Week](evidence/contact-week.jpg),
[Month](evidence/contact-month.jpg). Native desktop/mobile screenshots were also inspected during
interaction review. Six supplemental captures show:

- Mobile inspection and exact target context.
- Mobile completion with **without Event selected by default**.
- Mobile terminal result: unchanged due date, labelled UTC completion time and no Journal Event.
- Mobile filter drawer.
- Desktop inline inspection.
- Desktop explicit compatible Event choice with independently entered occurrence fields.

Browser smoke used the actual UI to inspect, select completion mode, complete a synthetic task without
Event, close inspection, open/close filters, discard a dirty explicit-Event draft and restore the
initial fixture. The terminal inspector explicitly displayed “Completed without a Journal Event” and
“Completion recorded”, with the original due day retained. Final browser error log was empty. The
viewport override was reset and the prototype tab retained for review. A browser-handle interruption
after the user's retry was resolved by resetting the automation session; previously saved captures
were retained, not recreated or represented as new acquisitions.

Native screen-reader/AT, physical devices, actual browser zoom, forced colors, real backend failures,
large collections, live midnight rollover and cross-client races were **not tested**. Viewport resizing
is not browser zoom. Keyboard/focus and history cases were tested in component tests, not a complete
native keyboard-only browser audit. Supplemental states are Botanical Light samples, not a six-theme
modal matrix.

## Focused verification

| Check                                                                            | Result                                                                                                |
| -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Untouched-source baseline: Schedule calendar/API/screen, global Journal, History | **75/75** tests across five suites                                                                    |
| Final: same suites plus ScheduleUxPrototype                                      | **86/86**, six suites; **11 new** prototype/fixture tests                                             |
| Complete frontend ESLint, zero warnings                                          | Passed                                                                                                |
| Complete frontend Prettier check                                                 | Passed                                                                                                |
| Strict TypeScript                                                                | Passed directly; also passed as part of production build                                              |
| Default Vite production build                                                    | Passed                                                                                                |
| Existing `python3 scripts/check_ui_lab_build.py`                                 | Passed                                                                                                |
| Additional production exclusion scan                                             | No Activity lab entry, fixture text, class markers or simulator in **125** emitted HTML/CSS/JS assets |
| `python3 scripts/check-features.py`                                              | **122 features valid**                                                                                |
| `git diff --check` and local document-link / image-manifest checks               | Passed                                                                                                |

Final frontend test command:

```bash
cd frontend
pnpm test src/ui-pages/ScheduleUxPrototype/ScheduleUxPrototype.test.tsx \
  src/schedule/ScheduleScreen.test.tsx src/schedule/calendar.test.ts \
  src/schedule/api.test.ts src/events/GlobalEventsScreen.test.tsx \
  src/history/HistoryScreen.test.tsx
pnpm lint
pnpm format:check
pnpm build
```

Tests exercise no-Event default, historical target closure, incompatible Event rejection, exact source
links, version-conflict draft retention/reload, failed save and dirty dismissal, idempotent synthetic
completion, terminal cancellation, cross-month inclusive Week bounds, URL state restoration, inline
Escape/focus return, empty search, load retry and fail-closed fixture requests. Existing Schedule tests
continue covering canonical forms/transitions/calendar behavior. These do not substitute for database
integration or operator acceptance.

Host toolchain: Node **24.22.1**, available pnpm **11.25.0** (repository declares **11.19.0**);
lockfile/dependencies are unchanged. Initial sandbox DNS/store/socket restrictions were resolved with
authorized dependency installation and loopback Vite startup; no foreign environment was used.
Canonical FULL/`make feature-verify`, PostgreSQL integration, migration cycling, API regeneration/drift,
Docker builds and stack health were not run: backend/contracts are unchanged and this task explicitly
excludes canonical FULL and protected delivery. The frontend production build is a focused check,
not a claim that the whole stack passed a release gate.

## Correctness review and remaining design limits

A separate source/diff pass checked authority/date boundaries, absence of real network forwarding,
unchanged shared primitives and the single production export. It corrected inspector restoration on
browser navigation, inactive picker choices and test assumptions about the existing radio completion
controls. The final diff pass also excluded an exhaustive Activity-kind selection from the active
filter count, preserving the canonical restriction semantics. That correction does not change any
pictured default-filter state; capture-time and final source digests are retained separately. Final
tests/static checks cover the corrected candidate. No external independent QA agent or
operator acceptance is claimed.

- Agenda retains the existing globally ordered page of 50 and qualifies group counts **on this page**.
  Mobile shows selected day, overdue and terminal groups from that page. A selected day beyond that
  page is not proven empty. Before production, use existing date bounds for a selected-day query plus
  independently bounded overdue results; keep filter intersections and stable pagination explicit.
- Week is deliberately optional. Six tasks on one day produce a much taller column than sparse days;
  seven columns should not be shipped as the primary operational surface. At tablet/mobile widths the
  prototype uses a selected-day agenda. Decide whether compact summaries plus inspection justify Week.
- The mobile toolbar/date rail consume substantial initial vertical space. Review actual task access
  and compact header priorities before production integration; screenshot reflow is not usability approval.
- Week/Month limit their datasets to the visible period and therefore do not carry off-period overdue
  work into their grids. A production period view should expose a separately scoped overdue attention
  link/count rather than silently treating out-of-period work as absent or moving its date.
- Date-only ISO days remain intact. No controls suggest hours, duration, recurrence, reminders,
  automatic completion, unscheduling or reopen. Search is title/notes only. No fake capacity metric exists.
- Exact target and lifecycle retention, historical source links, terminal behavior and schema downgrade
  behavior are unchanged in production. The development-only Week URL must not leak into Saved Views.

## Recommended implementation sequence and operator decisions

1. **Approve Activity responsibilities and Journal scope.** Keep all three destinations. Decide whether
   the first Journal increment is a target-required composer over existing Events, or whether unscoped
   source notes are essential immediately. The latter requires the separate model/API review in journal.md.
2. **Approve a bounded Schedule integration.** Recommend Agenda + compact date navigation + context
   inspector, retaining Month. Decide mobile selected-day versus continuous Upcoming defaults, how overdue
   attention stays visible across periods, and whether Week merits inclusion. Resolve scoped paging and
   mobile density before treating the prototype as production-ready. Agree canonical presentation URLs
   and compatibility for existing List/Calendar links. Integrate after reconciling Wave 3; shared component
   changes, if any, belong to their owning approved increment, not this concurrent study.
3. **Approve the source-note contract before new Journal persistence.** Decide exact supported subject
   types/cardinality, author/source assertions, occurrence precision, correction/version/deletion policy,
   attachment retention, existing Event coexistence and paged search. Review migration safety/downgrade,
   permissions, errors and concurrency; then implement that one increment with its required FULL gate.
4. **Add media and one reviewed promotion journey only after source notes exist.** Choose the first
   canonical operation, one-to-many result policy and durable idempotent receipt/correction semantics.
   Preserve original sources and require explicit confirmation before every authoritative mutation.
5. **Independent review and verification precede delivery.** Operator visual acceptance and correctness
   QA apply to the separately selected production increment. Only that later authorized task freezes the
   tree and runs its canonical gate. This study does not push, create PRs, merge or run feature-finish.

The review boundary is **FLORABASE_ACTIVITY_CONCEPT_AND_SCHEDULE_UX_REVIEW_READY**.
