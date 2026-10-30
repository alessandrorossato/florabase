# Scheduled collection activities — SCHEDULE-001

Schedule (`#/schedule`, under Activity) stores explicit **future intention**. Journal stores
operator-recorded occurrences. History projects recorded facts. A due day passing is not an
occurrence, and completing an intention does not necessarily create an Event.

## Dates and statuses

Every activity has a complete date-only `due_on` day, a title, optional planning notes and one of
Repot, Water, Fertilize, Move / relocate, Check germination, Inspect, Harvest or General follow-up.
No PartialDate, time-of-day, operator timezone, background scheduler or automatic completion exists.
Inputs require `YYYY-MM-DD` dates; timestamp/epoch coercion is explicitly rejected.
The browser explicitly supplies its device's current calendar day for overdue and date buckets,
displays that day, and refreshes the projection when it changes. Grouping and the displayed day use
the same returned projection, including a request crossing midnight. API callers can supply `today`;
omitting it uses the UTC day. This affects only presentation, never stored lifecycle.

Canonical states are `planned`, `completed`, `cancelled`. Overdue is derived from planned +
`due_on < today`, never persisted. Today and next seven days (tomorrow through today + 7 inclusive)
are disjoint; Later follows that window. Past due active work remains planned. Past dates are valid
for explicit overdue work. Complete/cancel are terminal; correction of a closed intention requires
creating a new intention. No reopen or hard-delete endpoint exists.

## Targets and retention

An activity can refer to the whole collection or one exact BotanicalIdentity, SeedLot, Sowing,
Plant, PlantGroup or Location. Six narrow nullable restrictive foreign keys enforce at most one
reference. There is no polymorphic-reference engine. Existing record pickers are reused over a
bounded searchable/paged target API. Stored material and Harvest are deferred as direct targets:
plan Harvest against its Plant/PlantGroup; record actual Harvest/inventory in their existing workflows.

New assignments require a current record (or a botanical identity, which has no operational
lifecycle). Retirement, exhaustion, extraction, conversion, transfer, reversal and other lifecycle
changes do not cascade into Schedule. The actual target relationship and its current lifecycle remain
visible. An existing inactive target can be retained while editing/rescheduling and can be closed
without an Event; it cannot be newly assigned or receive a Schedule-created Event. Retargeting is an
explicit operator edit. BotanicalIdentity/Location deletion returns the established conflict response;
restrictive FKs protect every supported target in every status. Completed/cancelled planning evidence
therefore remains navigable. Referenced records and linked Events cannot be hard deleted.

## Completion and Events

Complete defaults to **Complete without a Journal Event**. The operator can explicitly choose
**Record what happened in Journal** only for a current Plant/PlantGroup and compatible kinds:

| Scheduled kind    | Existing Event kinds                |
| ----------------- | ----------------------------------- |
| Repot             | Repotting                           |
| Move / relocate   | Movement, with explicit destination |
| Inspect           | Observation                         |
| General follow-up | Observation or Other                |

The actual complete occurrence day and Event notes are entered independently from the due day and
planning notes. Movement explains and invokes the established current-Location effect. Water,
Fertilize, Check germination and Harvest complete without an Event here; their existing recording
workflows remain available. No invented Event kind mirrors Schedule kinds.

The Schedule row is locked; the expected version and current target are revalidated. The existing
Event service creates the Event and its normal effects in the same transaction as completion and
the durable one-to-one restrictive link. Failure rolls back all changes. A normalized completion
request fingerprint (including expected version and explicit Event fields) makes exact retries return
the same result, without another Event/version change. A changed retry conflicts. Cancel retries use
the original expected version and also return the existing cancellation. Other stale transitions and
all edits of terminal records conflict. Linked Event corrections retain the normal Journal correction
semantics; deletion is blocked to preserve the planning link.

Completed records now project a terminal **Completion recorded** fact in History at `completed_at`
(UTC), with navigation back to Schedule. This does not establish the actual work occurrence date.
Planned/overdue/cancelled records remain excluded. An explicit linked
Event appears through the existing Journal and History Event projection. Completion without Event
creates the terminal completion fact, without a botanical occurrence or operation receipt.

## API and persistence

Authenticated routes under `/api/v1/schedule` list/filter, retrieve, create, update/reschedule, cancel
and complete activities. Reads use normal sessions; writes require owner, exact Origin and CSRF.
Writes use `expected_version`; creation starts at version 1. List pages cap at 100 (default 50),
order by due day then ID and return bounded total/overdue/today counts. Search is literal title/notes,
never a related-record expansion. Filters support repeated status/activity-kind/target-kind values, a single date bucket,
exact typed target and search. Target choices cap at 100 and have an exact-target read route.

Migration `20261009_0041` follows delivered `0040`, adding only the scheduled-activities table,
constraints and indexes; no existing records are backfilled or mutated. A populated downgrade is
refused under an exclusive table lock to preserve planning evidence. Empty downgrade/re-upgrade
preserves unrelated collection data. UTC-aware created/updated/completed/cancelled timestamps
record explicit planning lifecycle transitions, not inferred horticultural occurrences.

## Workspace and integrations

Active work is grouped into Overdue, Today, Next 7 days and Later within compact white list surfaces.
Schedule shares the Activity PageIdentity/PageTools header: short subtitle, visible Search, Filters,
and owner-only creation. Filters use the shared Dashboard-style native drawer; completed/cancelled
use actual stored statuses. Search uses the existing server-side literal title/notes query, capped at 200 characters,
with filtering before count/page; it applies identically in List and the bounded visible Calendar month.
Clear filters preserves search and the current view/month/day. The default planned Status is an active dimension; removing it includes all stored statuses.
Active dimensions have removable summaries. URL keys are `status`, `window`, `activity_kind`, `target_kind`, `target_id`, `q`;
values are encoded in deterministic enum order; empty kind/target restrictions are omitted. Legacy omitted Status remains planned; unrestricted Status repeats all three real values. Refresh, Back and Forward restore filters; page state and
forms are transient. `#/schedule/<id>` opens retained evidence; contextual `action=create` uses an
exact target. Search typing replaces the current URL to avoid one history step per keystroke.
List/Calendar sits in the local count/month heading, alongside temporal navigation in Calendar. Planned owner rows expose Complete plus an accessible
overflow menu for Edit/reschedule and Cancel, retaining confirmation, expected versions and reload.
Terminal/non-owner records expose inspection/source navigation only. Calendar day-drawer menus render
within the modal's interactive subtree; Escape closes the menu before the drawer and restores focus.
Full notes remain in inspection; compact row excerpts keep synthetic fixture notes unobtrusive.

Dashboard shows global overdue/today counts and at most three active records, linking to Schedule.
Plant/PlantGroup, SeedLot and Sowing full-detail overviews show at most three active records and
View all / Schedule activity with target preselection. Inactive details retain upcoming visibility and
View all; new contextual creation is hidden. Directory rows and quick previews remain unchanged.

Schedule Saved Views are explicitly deferred: adding and reviewing another persistence/surface
adapter is beyond this first planning increment. Existing VIEW-001 surfaces and semantics are
unchanged. Calendar is the complementary Month presentation described below; List remains the default operational view.

## Synthetic UAT and exclusions

Guarded UAT Preview is `http://localhost:15174`, local UAT-only owner `preview / preview`.
Explicit seed creates eleven synthetic schedule examples spanning all six target kinds, overdue,
today, this week, later, completed/cancelled, no-Event completion and explicit linked repotting Event.
Repeating seed preserves operator edits and dates; time passing naturally changes derived buckets.

Operator review should create from Schedule and Plant/Sowing/SeedLot detail, reschedule, complete
without Event, explicitly record actual repotting or movement, retry the same completion through the
API, inspect Journal/History boundaries, cancel, reopen terminal evidence and use 390×844 mobile.
See [handoff](schedule-001-handoff.md) for checks and visual-review readiness.

Recurrence, notifications/reminders, assignees/teams, subtasks, priority matrices, attachments,
workflow engines, kanban and broad visual redesign remain outside this increment.

## Calendar presentation (SCHEDULE-002)

Calendar uses the same ScheduledActivity records and filters. Open
`#/schedule?view=calendar&month=2026-10`; optional `date=2026-10-12` selects a day.
List remains the default. View links and period/day navigation create browser-history entries;
search continues to replace the current entry. Back/Forward restore URL state. Month is the only
calendar mode. Previous / Today / Next use local calendar components; placement always uses the
concrete `due_on`, without time or timezone conversion.

Desktop and tablet show a Monday-first semantic month table with two summaries per day and a
“more” action. Selecting a day opens a context-preserving native-modal drawer for every matching
activity on that date. It reuses the existing inspect/edit/reschedule/cancel/complete paths and their
optimistic versions. Add activity prefills the selected date in the existing creation form.
At ≤48rem, compact date buttons and counts replace cell summaries, and a selected-day list exposes
all work and actions without horizontal scrolling. Selected date is deep-linkable; drawer visibility
is transient. Current/selected dates and terminal/overdue states have explicit accessible/text cues.

Calendar intersects existing Schedule filters with inclusive API `due_from` / `due_to` bounds for
the visible month. The existing list endpoint retains its auth, capped pagination, due-day/ID order
and batched target resolution. It rejects reversed bounds. Month loading retrieves all its matching
pages and aborts superseded requests; selecting a day uses the loaded month. A request fixes the
local `today` across pages and the screen refreshes at midnight. PartialDate is not involved.

Explicit synthetic seed adds seven Calendar examples (including five same-day activities, month
end and next month) once, preserving original Schedule examples and operator edits. The independent
review handoff and focused evidence are in [SCHEDULE-002 handoff](schedule-002-handoff.md).
Week, drag/drop, recurrence, reminders, assignments, priorities, external sync/export, Schedule
Saved Views and global visual migration remain deferred.

The Activity filter drawer applies live. Status, Activity kind and Target type use checkbox fieldsets;
Date window is a single select. No selection includes all values. API enum lists are bounded at 3/8/6,
union within each dimension and intersect across dimensions before count/page. Exact target IDs
require exactly one type. Overdue still requires planned status and a due day before today, even
when combined with terminal statuses. Filters count dimensions, and each summary removes a complete
dimension. Reset/Done is the sole footer. List URLs retain month/day for reversible view switching.

## Agenda / Month UX candidate

The production UX candidate names the existing List presentation **Agenda** (default) and Calendar
**Month**, retaining their canonical URLs. Both share the approved explicit period/Today/date-jump
navigation. Agenda is continuous by default; choosing a day sends exact inclusive server bounds
before count/page, and All dates clears that date while retaining filters/search. Counts within
chronological groups describe the current ordered page. The collection-wide planned-overdue link
remains available outside the displayed month/day and preserves other active filters.
Existing dialogs, ownership, terminal transitions and actual Event contracts are unchanged.
Week remains a development-only prototype. [Operator UAT handoff](design/schedule-ux/README.md)
records real persistence checks, isolated Review access, visual evidence and the pending FULL gate.
