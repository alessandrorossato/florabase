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

Planned/overdue/completed/cancelled records are never added as History sources. An explicit linked
Event appears through the existing Journal and History Event projection. Completion without Event
creates no botanical occurrence, operation receipt or History item.

## API and persistence

Authenticated routes under `/api/v1/schedule` list/filter, retrieve, create, update/reschedule, cancel
and complete activities. Reads use normal sessions; writes require owner, exact Origin and CSRF.
Writes use `expected_version`; creation starts at version 1. List pages cap at 100 (default 50),
order by due day then ID and return bounded total/overdue/today counts. Search is literal title/notes,
never a related-record expansion. Filters support status, date bucket, activity kind, target kind,
exact typed target and search. Target choices cap at 100 and have an exact-target read route.

Migration `20261009_0041` follows delivered `0040`, adding only the scheduled-activities table,
constraints and indexes; no existing records are backfilled or mutated. A populated downgrade is
refused under an exclusive table lock to preserve planning evidence. Empty downgrade/re-upgrade
preserves unrelated collection data. UTC-aware created/updated/completed/cancelled timestamps
record explicit planning lifecycle transitions, not inferred horticultural occurrences.

## Workspace and integrations

Active work is grouped into Overdue, Today, Next 7 days and Later. Filters open through an accessible
disclosure and the current view remains visible; completed/cancelled filters
remain secondary. URL keys are `status`, `window`, `activity_kind`, `target_kind`, `target_id`, `q`; default
values are omitted in deterministic order. Refresh, Back and Forward restore filters; page state and
forms are transient. `#/schedule/<id>` opens retained evidence; contextual `action=create` uses an
exact target. Search typing replaces the current URL to avoid one history step per keystroke.

Dashboard shows global overdue/today counts and at most three active records, linking to Schedule.
Plant/PlantGroup, SeedLot and Sowing full-detail overviews show at most three active records and
View all / Schedule activity with target preselection. Inactive details retain upcoming visibility and
View all; new contextual creation is hidden. Directory rows and quick previews remain unchanged.

Schedule Saved Views are explicitly deferred: adding and reviewing another persistence/surface
adapter is beyond this first planning increment. Existing VIEW-001 surfaces and semantics are
unchanged. A calendar is also deferred; the accessible list is the initial presentation.

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
