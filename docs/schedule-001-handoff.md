# SCHEDULE-001 implementation handoff

## WORKTREE

Implementation source: `/home/alessandro/.codex/worktrees/dcdf/florabase`, branch
`feat/schedule-001-collection-activities`, initialized through guarded `make feature-init` from
`8eece520408679579114677b3e2537e23f357b4b`. Independent source/domain/API/migration review and
Schedule-focused desktop/tablet/mobile UAT found no blocking product defect. Canonical
`make feature-verify` passed on this final reviewed source tree and its per-worktree receipt is current.

## DOMAIN DECISION

Schedule stores future intention; Journal stores operator-recorded occurrences; History projects
recorded facts. A narrow ScheduledActivity owns its title, kind, due day, optional notes, one optional
exact collection target and terminal planning outcome. It owns neither care automation nor inventory.
See [domain contract](schedule.md). No unresolved material domain decision remains.

## STATUS MODEL

`planned → completed` or `planned → cancelled`, through explicit operator actions. Terminal evidence
is retained and read-only. No reopen or hard deletion. A new intention expresses further work.

## DATE/TIME POLICY

Required complete date-only `due_on` in `YYYY-MM-DD` form; partial dates, timestamps and numeric epochs
are rejected for due/occurrence/projection days. Browser projection uses
its displayed device calendar day, refreshed when it changes. API `today` is explicit, with UTC day
as the default for callers that omit it. List grouping and the displayed day use the same returned
projection, including a fetch crossing midnight. Stored boundary timestamps are UTC aware. Actual Event day
is independently entered and never copied from the due date.

## TARGETS

Whole collection/no record, or one BotanicalIdentity, SeedLot, Sowing, Plant, PlantGroup or Location.
Six nullable restrictive FKs and an at-most-one check preserve concrete ownership. Existing
ReferencePicker is reused with bounded searchable/paged choices and exact target retrieval.
Harvest and stored material are deferred as direct targets; use their existing recording workflows.

## TARGET LIFECYCLE

New assignments require current records. Existing inactive references remain visible and may be
retained on edit/reschedule, completed without Event or cancelled. No lifecycle cascade, inferred
replacement, source synchronization or conversion occurs. Restrictive FKs preserve all referenced
records; BotanicalIdentity and Location deletion use their normal conflict responses.

## COMPLETION/EVENT POLICY

Default is completion without Event. Current Plant/PlantGroup can explicitly record compatible
Repotting, Movement, Observation or Other through the existing Event service. Movement requires an
explicit destination and applies its normal Location effect. Due date/planning notes and occurrence
date/Event notes remain independent. Completion and Event creation/link share one transaction.
Linked Event deletion is guarded; normal Journal correction semantics remain available. Planning
records are never History sources; only an explicitly created normal Event enters existing History.

## OVERDUE

Derived `status == planned && due_on < today`; overdue never means occurred. Today, tomorrow through
seven days inclusive and Later are disjoint. Passing time makes no persisted transition.

## API

Authenticated `/api/v1/schedule` CRUD-style planning reads/create/update and explicit complete/cancel
routes, without DELETE. Owner writes require normal Origin and CSRF protection. Typed filters,
literal title/notes search, deterministic `due_on,id` ordering, default 50/max 100 rows and bounded
counts. Target-choice APIs are paged, with exact lookup. OpenAPI and generated TypeScript declarations
are authoritative. Structural contract audit found only six new paths and ten new schemas; existing
paths and schemas are unchanged.

## MIGRATION

`20261009_0041_scheduled_activities`, parent `20261009_0040`, adds only planning persistence,
constraints, restrictive target/Event relationships and narrow query indexes. No backfill. Populated
downgrade refuses under an exclusive lock; empty downgrade/re-upgrade preserves unrelated data.
Both paths are exercised against real PostgreSQL.

## SAVED VIEWS

Explicitly deferred for this first increment, as permitted by the request. Existing VIEW-001
adapters are unchanged. Canonical URL filters restore views on refresh/Back/Forward; transient page,
dialog, search-input interaction and operation state are not saved preferences.

## DASHBOARD

Global overdue/today links and at most three active activities, linking to Schedule. No duplicate
history feed or collection-summary expansion.

## CONTEXTUAL UI

Plant/PlantGroup, SeedLot and Sowing full-detail overviews show at most three exact-target active
activities, View all and current-target Schedule activity. Context creation retrieves the exact
stored target; inactive details hide creation. Directory, quick preview and full detail remain
separate. Activity navigation contains Journal, History and Schedule, including mobile More.

## CONCURRENCY

Row locks plus required expected versions protect edits/transitions. Current targets are locked and
revalidated for new assignment/Event recording. Exact normalized completion retries return the same
Event and version; changed retries conflict. Cancellation retries are also idempotent. Real two-session
races cover edit/edit, edit/complete, cancel/complete, completion/completion and Event/Event,
plus target retirement/deletion racing an edit. Failure leaves no partial Event or target movement.

## ACCESSIBILITY

Semantic headings/lists, visible status text, labelled controls, loading/empty/error/retry states,
accessible filter disclosure, and existing TaskDialog focus trap, Escape and focus restoration.
Mobile rows stack actions and wrap notes; filters are collapsed initially to keep activities reachable.
Conflict errors preserve entries and expose explicit reload. Initial URL synchronization preserves
identical filters, avoiding duplicate reads that could mask a loading failure. Browser checks at
1440×844, 1024×844 and 390×844 found no horizontal overflow. Native keyboard date editing persists
rescheduling; completion/cancellation confirmations are usable, Escape restores the triggering
record, and the existing focus trap contains keyboard navigation. Final visual approval belongs to Luna.

## TESTS

- Backend: **93 passed**, `pytest --no-cov -m "not integration"`, covering Schedule, Event/schema,
  History, Saved Views, Location and BotanicalIdentity service/API. Ruff format/lint and strict mypy
  (**336 files**) pass. UAT fixture scoped Ruff and strict mypy (**1 file**) pass.
- PostgreSQL: **52 passed**, Schedule **12** plus Event API, History and Saved Views. A unique
  disposable integration project uses the canonical script's tmpfs DB and exact cleanup pattern,
  current backend source read-only and an existing dependency image. Completion, race, retention,
  security, date boundaries and both guarded/empty migration paths pass.
- Frontend: **197 passed across 9 files**, Schedule/App/lazy App/Plant/Sowing/SeedLot/Journal/History/
  Saved Views. Full strict TypeScript, ESLint, affected formatting and asset build pass. The final
  lifecycle-label correction then passes **20 tests** (Schedule **16**, ReferencePicker **4**),
  strict typing, focused lint/format and another asset build. Original reference-picker wording
  remains the default; Schedule supplies the actual inactive lifecycle label.
- Workflow: UAT Preview **19 passed**, environment workflow **29 passed**. Actual guarded
  up/seed/status and repeated seed succeed. API generation/drift and final backend export check
  pass; feature graph **99 valid**, production backend/frontend images and `git diff --check` pass.

See [progress](progress.md) for consolidated evidence. Initial fixture/mock/test-expectation issues
and load timeouts under simultaneous builds were resolved; the final UI run was sequential, without
weakened assertions or timeouts. The final canonical receipt matches this source tree. No staged
changes or commit exist.

## UAT

Isolated Preview: <http://localhost:15174>, UAT-only owner `preview / preview`, source `dcdf`, schema
`20261009_0041`. Existing `748b` UAT ownership was retired through the exact owning guarded remove
command explicitly authorized in request section 24. No generic Docker cleanup was used.

Explicit additive seed installs eleven synthetic Schedule examples with six target kinds, overdue,
today/week/later, completed/cancelled, completion without Event and a linked repotting Event.
Repeating seed preserves existing dates and operator edits. Day changes naturally age fixtures;
operator review added then explicitly cancelled a 2026-10-10 collection intention, rescheduled the
original watering intention to that day, completed a SeedLot inspection without Event, and completed
a new November repot intention with an independently entered October Event. The durable link opens
the Plant Journal showing actual `2026-10-10`, independently of due `2026-11-10`. Plant, PlantGroup,
SeedLot and Sowing detail context/preselection and mobile More navigation were reviewed. Repeating
guarded seed preserved these edits. UAT baseline manifest
contains 53 records; additional operator review records are not silently absorbed into the manifest.
DEV, Stable Preview and production services/data are unchanged.

## ROADMAP

The base roadmap named SCHEDULE-001 but the 98-entry machine graph omitted its record. Exactly one
canonical SCHEDULE-001 entry reconciles this discrepancy; no duplicate or substitute ID was created.
SCHEDULE-001 is verified. PHYLOGENY-001 remains planned
and SOURCE_BLOCKED; TAXONOMY-003 remains verified; BOTANY-003/004 and ENRICHMENT-002 remain planned.
No recurrence, notifications, attachments, calendar, assignees, teams or generic task engine.
