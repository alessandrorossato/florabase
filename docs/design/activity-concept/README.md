# Activity concept and Schedule UX study

Design/prototype candidate, **30 October 2026**. Source: freshly fetched `origin/main`
`76c0911dbf7ca5dc5f64b1a8d1de8c57c676c70e` (PR #131), clean at task entry.
Branch: `feat/activity-concept-schedule-prototype`, existing Codex worktree `28ce`.
Primary main and Wave 3 (`548f`) are untouched. No Docker command, Review takeover,
canonical gate, push, PR, merge or feature-finish belongs to this study.

**Recommendation:** keep three Activity destinations, with different primary jobs:
Journal captures operator meaning; History retrieves authoritative past facts; Schedule
organizes intended work by day. Approve Agenda-first Schedule separately from any new Journal
storage. Completed Wave 2 normalization remains accepted and is not reopened.

- [Actual-model audit and boundaries](#actual-model-audit)
- [Journal journeys and conceptual wireframes](journal.md)
- [Official-reference comparison](references.md)
- [Prototype, evidence, checks and operator decisions](handoff.md)
- [Runnable prototype source](../../../frontend/src/ui-pages/ScheduleUxPrototype/README.md)

## Current versus proposed information architecture

| Destination           | Current product                                                     | Proposed primary workspace                                                                     | Secondary content / boundary                                                                                      |
| --------------------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Journal `#/events`    | Record launcher above filtered Plant/PlantGroup Event notebook      | Prominent quick capture; exact optional subject/date; structured recording launcher            | Recent notebook entries below capture; proposed unscoped notes require a new model. No duplicated operation facts |
| History `#/history`   | Compact, paged read-only multi-source chronology                    | Retain compact chronological retrieval and source navigation                                   | Search, live filters, v1 Saved Views and pagination; no composer, create, edit or gallery                         |
| Schedule `#/schedule` | List buckets or Month; planned/completed/cancelled; versioned forms | Agenda first, compact date rail, contextual inspector; Month retained; optional date-only Week | Existing transitions and exact source links; no hours, recurrence, reminders or Schedule Saved Views              |

Global navigation membership and ordering remain unchanged. The prototype sidebar is reduced review
chrome, not a proposed replacement AppShell. This study does not merge Journal and History datasets.

## Actual-model audit

Read implementation and contracts together. Documentation is not proof that the central notebook
model exists. These are the controlling implementation paths:

- Journal: `frontend/src/events/{GlobalEventsScreen,RecordLauncher,EventJournal,EventFeed}.tsx`,
  `eventData.ts`; backend `events/{model,schemas,service,api}.py`.
- History: `frontend/src/history/{HistoryScreen.tsx,api.ts,state.ts,presentation.ts}`;
  backend `history/{service,schemas,api}.py`.
- Schedule: `frontend/src/schedule/{ScheduleScreen,ScheduleCalendar,ScheduleActivityRow,
ScheduleTargetPicker,ScheduleTargetLabel}.tsx`, `state.ts`, `calendar.ts`, `api.ts`;
  backend `schedule/{model,schemas,service,api}.py`.
- Media: backend `collection_photos/model.py`, especially `RecordMediaLink` and
  `CollectionPrimaryPhoto`; existing authenticated media UI owns linking/upload/attribution.
- Contracts: `docs/operational-history.md`, `docs/schedule.md`,
  `docs/activity-family-refinement-handoff.md`, `docs/design/ui-system-v1/wave2/README.md`,
  `docs/ui-contract.md`, Gate B implementation guidance and `docs/features.json`.

| Capability         | Actual implementation                                                                                                                                             | Consequence for the proposal                                                                                                                                         |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Free text today    | Event `notes`, nullable, max 20,000; occurrence PartialDate or null                                                                                               | Notes can be captured for an exact Plant/PlantGroup; not a standalone notebook note                                                                                  |
| Event subject      | Database requires **exactly one** Plant or PlantGroup FK                                                                                                          | An optional/no target, collection, Location, Sowing, SeedLot, identity or Harvest note is new domain work                                                            |
| Date uncertainty   | Event accepts year/month/day PartialDate or unknown; created_at is recorded time                                                                                  | Composer must not infer the occurrence date from capture, due day, photo metadata or parsing                                                                         |
| Recording actions  | Existing launcher routes to Harvest, Sowing, Plants, Schedule; contextual germination and Journal target chooser                                                  | Recompose entry points; keep business effects with canonical workflows                                                                                               |
| Notebook selection | `notebookEvents` excludes Harvest-owned, operation-owned, extraction/reintegration and unannotated state actions                                                  | Reuse ownership suppression. A note explaining an operation adds meaning, not another operation fact                                                                 |
| Journal query      | Global Event retrieval; notebook/category/search applied to returned collection in frontend                                                                       | This is not an existing server-paged central-notebook query. Define paging/search before scaling a new capture model                                                 |
| Provenance         | Event has recording/update instants, target and operation/Harvest ownership; no immutable author/source-note lineage                                              | Do not advertise authorship, original-source retention, revisions or promotion receipts as delivered                                                                 |
| Photos             | Media links support Event and several existing record targets; primary-photo and identity-cover contracts differ                                                  | Existing Event Photos can be reused contextually. A new JournalEntry needs its own reviewed media target/retention path; target thumbnail is not an Event attachment |
| Correction         | Ordinary Event updates/deletes affect the History projection; owned backing records route to authority                                                            | Journal is not immutable. Source-preserving note revision/correction relationships are new storage                                                                   |
| History authority  | SQL union across Events, operation receipts, germination, Harvests, dispositions, conversions and completed Schedule                                              | No History table. Suppress owned Event/conversion backing duplicates before filtering/paging                                                                         |
| History date       | Real occurrence PartialDate, otherwise labelled Recorded; Schedule uses completed_at labelled Completion recorded                                                 | Keep occurrence and recording semantics visible. Current lifecycle/updated_at cannot invent historical transitions                                                   |
| History query      | Authenticated bounded literal q, repeated category/subject types, year, stable SQL global order; limit 50/max100, offset ≤100,000                                 | Preserve canonical URL/Saved Views and page reset. Search precedes global count/page                                                                                 |
| Schedule target    | At most one of six restrictive FKs, or whole collection                                                                                                           | Exact existing references survive closure/lifecycle changes; Harvest/material direct targets remain deferred                                                         |
| Schedule lifecycle | Date-only due_on; planned/completed/cancelled; derived overdue; expected_version and locked transitions                                                           | Presentation can change without a migration. Terminal intentions cannot reopen or hard-delete                                                                        |
| Completion         | Default no Event; explicit compatible current Plant/PlantGroup Event is atomic with versioned completion; fingerprint makes identical completion retry idempotent | A checkmark is an intention closure, not proof of when botanical work occurred                                                                                       |
| Schedule search    | Server title/notes q, enum/date/target intersections, due-day/ID paging; device day projection in production                                                      | Do not claim botanical-target-label search, timezone scheduling or all-history client filtering                                                                      |

Registry context: `ACTIVITY-001`, `HISTORY-001`, `SCHEDULE-001` and attachment capabilities already
own the delivered contracts; `UI-SYSTEM-WAVE2-001` remains `implemented`. The new study registry item
tracks only this design/prototype deliverable, not production Journal or Schedule completion.

## History differentiation plan

Retain the existing grouped, compact log. The row hierarchy is:

```text
2026-10       [month precision]   HARVEST    Autumn basil harvest
                                         Source: Harvest #… → canonical detail
                                         Related: Basil group B → exact PlantGroup
                                         2 material lines
────────────────────────────────────────────────────────────────────────────
29 Oct 2026  Completion recorded  SCHEDULE  Scheduled work marked completed
             (UTC)                        Source: Scheduled activity #…
                                         Target: Lavender packet 07
```

Use the date/precision column, short fact/source label, source title, exact primary and bounded related
links, and concise factual context. A missing occurrence uses an explicit Recorded label; a month/year
never becomes the first of that period. A source record link is the correction path. No History row
mutation control is introduced. Current record labels can change after correction; they are not
historical name snapshots. Retained/reversed receipt states stay visible under existing rules.

Preserve `historyDateLabel`, `historyOrigin`, typed route derivation and exact inventory anchors.
Source Event links resolve to their actual target Events tab; do not invent a generic history-detail
route. Structured Harvest has one row even when it owns an Event or several material lines.
An ordinary Event appearing in Journal and History is the same authoritative record in two views.
A future **unstructured** notebook note should remain outside History until an explicit, separately
approved fact-projection policy exists. Promotion should project only the actual owning fact.

Keep search and category/primary record/year filters above the log; Saved Views save canonical
filters, not result snapshots, preview selection or page offsets. Preserve scalar-v1 read compatibility,
repeated-array canonicalization, page-one reset and deterministic typed-key tie-breakers. No production
History layout change is necessary in this task. Test future refinements against partial/unknown dates,
corrections/deletion, source deduplication and stable empty/out-of-range pages.
