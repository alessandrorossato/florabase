# Schedule UX prototype (development only)

Run the existing frontend toolchain, without Docker, auth or a database:

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm exec vite --host 127.0.0.1 --port 15286 --strictPort
```

Open <http://127.0.0.1:15286/activity-lab/#/schedule?month=2026-10&date=2026-10-30>.
Do not use the normal application root for this fixture. Its frozen projection day is 30 October 2026.
The explicit month/day URL makes this deterministic on later review dates. Reload resets all changes.

`main.tsx` imports `mount.tsx` only in Vite DEV. The normal production entry/router/build inputs are
unchanged. This entry mounts only the prototype and a synthetic auth **context**, never the real
AuthProvider/session restoration. `FixtureSchedule.fetch` replaces fetch only in this entry; unknown
requests return a synthetic failure and never forward to network. No secret or credential is required.
Native Vite module/font/style loading still uses the local development server.

Reuse: ActivityPage, ActivityPageHeader/DirectoryTools, ActivityChoices, ScheduleActivityRow,
ScheduleTargetLabel, ScheduleCalendar, TaskDialog and the exact current ActivityDialog. The only
production-source edit is exporting ActivityDialog from ScheduleScreen, without changing its behavior.
All new styles are scoped to the prototype. Shared primitives and Wave 3 files are unchanged.

Functional on fixture data: Agenda, Week, existing Month; previous/next/Today/date selection; canonical
search and multi-filters, exact target scope in incoming URLs; browser history; stable list pagination;
inspection and focus return; canonical create/edit/target picker, dirty-discard guard, reload-on-conflict,
complete/cancel and opt-in supported Event forms. Review chrome can inject the next request failure or
write conflict. Six-theme selectors use the real appearance store (a browser appearance preference).

Simulator limits: no database, authorization enforcement, locks, transaction isolation, real occurrence
side effects, media, migration, concurrency between clients, live local-day rollover or real idempotency
storage. An explicit Event is saved as an in-memory receipt only; Movement does not update a Location.
It demonstrates the distinction from completion, not domain-service correctness. Unknown source routes
show their exact canonical hash and an explicit unavailable-detail notice instead of mounting App.
Synthetic public IDs do not identify actual records. Never treat these links as live collection data.

Agenda groups the existing ordered page of 50; date-group counts explicitly say “on this page”. On
mobile it displays Overdue, the selected day and terminal groups. A selected day beyond the current
page is not proven empty: its message says “on this page”. A production selected-day agenda should use
the existing due_from/due_to bounds plus a separately bounded overdue query, preserving pagination and
window intersections; this scaling integration is a handoff requirement, not simulated with hidden data.
Week uses inclusive day bounds and capped pages; Month reuses the existing bounded calendar loader.
No time-of-day, duration, recurrence, reminders, automatic completion or new Event kinds are offered.

`ux=week` is a prototype-only presentation parameter; Agenda preserves canonical `view=list` (omitted
by serializer), Month preserves `view=calendar`. Month/date, repeated filters and exact target ID use
the current parser/serializer unchanged. Schedule has no Saved Views. A production Week URL/preference
contract is an explicit decision; no v1 Saved Views schema is changed here.

Targeted checks:

```bash
pnpm test src/ui-pages/ScheduleUxPrototype/ScheduleUxPrototype.test.tsx \
  src/schedule/ScheduleScreen.test.tsx src/schedule/calendar.test.ts \
  src/schedule/api.test.ts src/events/GlobalEventsScreen.test.tsx \
  src/history/HistoryScreen.test.tsx
pnpm lint
pnpm format:check
pnpm build
```

See the [study handoff](../../../../docs/design/activity-concept/handoff.md) for actual results,
visual evidence and limitations. A functional synthetic prototype is not production implementation
or independent operator acceptance. No canonical verification or protected delivery was authorized.
