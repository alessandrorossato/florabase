# Schedule references and adaptation matrix

Official pages consulted **30 October 2026**. This is a functional pattern analysis, not a visual
clone. No vendor artwork, font, brand asset or proprietary component is used by the prototype.
“Not established” means the linked documentation does not substantiate the behavior; it does not
claim the product lacks it. Keyboard shortcuts alone do not establish screen-reader conformance.

Sources:

- **T:** [Todoist Upcoming](https://www.todoist.com/it/help/todoist/get-started/plan-your-week-with-the-upcoming-view-OKOg1mR8).
- **TK:** [Todoist keyboard shortcuts](https://www.todoist.com/help/todoist/features/use-keyboard-shortcuts-in-todoist-Wyovn2).
- **N:** [Notion Calendar](https://www.notion.com/product/calendar).
- **NM:** [Notion Calendar apps](https://www.notion.com/help/notion-calendar-apps).
- **NK:** [Notion Calendar keyboard shortcuts](https://www.notion.com/en-gb/help/notion-calendar-keyboard-shortcuts).
- **S:** [Sunsama timeboxing](https://www.sunsama.com/features/timeboxing).

| Pattern                 | Todoist evidence (T/TK)                             | Notion evidence (N/NM/NK)                                       | Sunsama evidence (S)                     | Florabase adaptation / boundary                                                                                |
| ----------------------- | --------------------------------------------------- | --------------------------------------------------------------- | ---------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Agenda / Upcoming       | Future tasks organized by date                      | Deadlines alongside calendar events                             | Daily task planning alongside meetings   | Agenda is primary; due-day groups and exact botanical targets; dates express intention                         |
| Week / Month            | Calendar alternative to task list                   | Grid and calendar navigation; mobile has different view choices | Calendar-based daily time allocation     | Retain existing Month; optional seven **date** columns, no hourly grid                                         |
| Day navigation          | Date picker and busy-day indicators                 | At-a-glance calendar context                                    | Today-focused plan                       | Compact Monday–Sunday rail, explicit Today/Previous/Next and date input; cross-month dates keep ISO day        |
| Overdue attention       | Overdue rescheduling tools                          | Not established on cited product page                           | Not established on cited feature page    | Quiet persistent attention; inspect each intention, no bulk automatic roll-forward                             |
| Completion / reschedule | Date change via drag or date picker; task shortcuts | Dragging edits database item dates                              | Completion can display actual time spent | Reuse explicit versioned edit/complete/cancel. No gesture-only write, reopen, duration or inferred actual work |
| Context inspection      | Task/date interactions                              | Connected documents provide context                             | Tasks and calendar shown together        | Lightweight record inspector; exact target, due day, lifecycle, notes and optional linked Event                |
| Dense / sparse days     | Occupied dates indicated                            | Combined commitments visible                                    | Projections help identify overload       | Show activity counts and truthful empty dates; no capacity-hours, duration estimate or “free time” claim       |
| Responsive/mobile       | Date navigation and task rescheduling               | Mobile apps and quick-access widgets                            | Mobile calendar example shown            | Selected-day agenda and native modal inspection; no seven cramped task columns or hidden overflow              |
| Keyboard                | Documented task/navigation shortcuts                | Searchable shortcut list                                        | Not established by feature page          | Native links/buttons, Tab/Enter/Space, Escape, focus return; drag is unnecessary. Custom shortcuts deferred    |

Selection rationale is Florabase-specific: precise target navigation and explicit completion matter
more than reserving time. Sunsama's realistic daily review suggests checking the number and content
of intentions before rescheduling; **counts are not effort estimates**. Notion suggests retaining
context while inspecting, rather than navigating away for every task. Todoist supplies the strongest
basis for Agenda-first discovery and an explicit date-based reschedule alternative.

Do not copy time-of-day, task duration, external-calendar busy slots, shutdown time, AI estimates,
recurrence or reminders into a date-only Schedule. Those need separately approved models/API contracts.
The prototype deliberately offers no disabled or fake controls for these deferred domains.

The cited sources do not establish a complete accessibility audit, every responsive breakpoint,
all completion semantics or comparative performance. A vendor interaction demonstration is a reference,
not validation that the same interaction is appropriate for botanical records.
