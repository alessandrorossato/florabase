# Schedule UX — production candidate for operator UAT

30 October 2026. Branch `feat/schedule-ux`; fetched main remains `76c0911` (PR #131).
This branch preserves the approved concept commits through `b8d066f`; production changes are the
subsequent increment. Wave 3 remains active in `548f` at `13c3233` with dirty shared primitive work.
No Wave 3 source, shared component, primary main or existing Review resource was modified.

## Review access

Open **<http://localhost:25288/#/schedule>**, sign in with **preview / preview** (synthetic UAT only).
Project: `florabase-uat-preview-smoke-28ce00000001`, source `28ce`, database `florabase_uat` in its
own PostgreSQL volume/network; media and frontend dependencies are separately project-owned.
Backend/PostgreSQL are not published. Active Wave 3 Review stays on 15174; DEV stays on 5173.
The existing guarded UAT runtime built this candidate, migrated to existing code head
`20261013_0042`, and seeded the standard v4 synthetic dataset (66 references). No new migration exists.

This is a retained review instance, despite the existing helper's `-smoke-` project namespace.
Do not invoke ordinary `make uat-preview-*` for this instance: those use the fixed project/port.
The exact runner used is `/tmp/florabase-schedule-review.py`; `python3` plus that path accepts `status`,
`up`, `seed`, or `stop` from this worktree. `stop` preserves data. Do not reset/reseed for normal UAT.
If the temporary runner is lost, reconstruct the same reviewed adapter before managing this instance:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "scripts"))
from uat_preview import UATPreview
from workflow_environment import Repository
class ScheduleReview(UATPreview):
    def __init__(self):
        super().__init__(Repository(Path.cwd()))
        self.project = "florabase-uat-preview-smoke-28ce00000001"
        self.url = "http://localhost:25288"
    def environment(self):
        result = super().environment()
        result["FRONTEND_PORT"] = "25288"
        return result
getattr(ScheduleReview(), sys.argv[1])()
```

This uses the existing smoke-project allowance, fixed UAT credentials, source/volume/role guards,
configuration and fixture services; no identity guard was bypassed or changed. Do not copy this
adapter to another worktree or point it at a different project's existing volumes.

## Production versus prototype

| Aspect           | Approved prototype                        | Production candidate                                                                                                                                    |
| ---------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Persistence/auth | Memory fixture and synthetic auth context | Existing authenticated Schedule API, CSRF, PostgreSQL and real session restoration                                                                      |
| Presentations    | Agenda, optional Week, Month              | **Agenda default and Month only**; Week remains in the dev laboratory                                                                                   |
| URLs             | Prototype-only `ux=week`                  | Existing `view=list`/omitted and `view=calendar`; filters/month/date remain canonical; no new Saved Views surface                                       |
| Date navigation  | Common toolbar in the refined prototype   | Same separate Previous week/month, Today, Next week/month, Jump to date bar; Agenda's seven-day date rail                                               |
| Agenda data      | Selected day filtered from a loaded page  | Default continuous, ordered/paged collection; selected-day queries use server `due_from=due_to` before count/page; All dates clears only date selection |
| Attention        | Fixture overdue                           | API's collection-wide planned-overdue count links back to planned overdue Agenda with current other filters preserved                                   |
| Inspection       | Inline desktop / modal mobile simulator   | Existing accessible house activity dialog, exact live target/source links; existing row Complete and overflow edit/cancel workflows                     |
| Month            | Existing grid and simulated persistence   | Same bounded real API loader, overflow/day drawer/mobile day agenda; common navigation supplied by Schedule owner                                       |
| Completion       | Synthetic receipt only                    | Existing atomic/versioned completion; default no Event; only existing compatible explicit Event path                                                    |
| Sources          | Placeholder hashes with no real records   | Exact record links, historical targets, lifecycle eligibility, linked Journal context and restrictive retention unchanged                               |

The only extension to the frontend API adapter is an optional selected-day bound on `listSchedule`.
No backend API/schema/generated declaration changes are needed: both inclusive bounds already exist.
Search remains title/notes; statuses, eligibility, expected versions, error recovery and terminal states
stay with their existing services. Group counts refer to the current ordered page, not all matching
history. Selected dates intersect search/window/status/target filters; incompatible combinations may
truthfully produce no results. Month selection is navigation context; Agenda selection is an exact
query restriction. Returning to Agenda retains that date until All dates is selected.

No time of day, duration, recurrence, reminders, Event kinds, automatic completion, reopen or
hard-delete operation is introduced. Completing without an Event closes an intention only; it does
not establish a botanical occurrence. Journal and read-only source-derived History are unchanged.
Universal free-form/unscoped Journal entries still require a separately approved source-note model,
precision/provenance/correction/retention contract and later reviewed promotion receipt design;
see the [concept decision](../activity-concept/journal.md).

## Verification completed

- Untouched baseline: **75/75**, five Schedule/Activity suites.
- Final focused frontend: **76/76**, five suites (Schedule screen/calendar/API, Journal and History).
  Added a regression proving exact selected-day server bounds preserve query and pagination.
  Existing tests retain transitions, dirty handling, errors/auth expiry, target eligibility, versions,
  leap dates/year boundaries, overflow focus return, month navigation and URL/history/filter coverage.
- Complete ESLint, strict TypeScript, Prettier and default production build passed.
- Real authenticated API smoke in this database passed create/read/reschedule, stale-version 409,
  complete without Event and retained completed_at, terminal transition rejection, cancellation and
  subsequent read, and rejection of a timestamp where a date is required. [Result](evidence/server-smoke.json).
- Native browser saved **Schedule UI reload proof**, reloaded the app and inspected the persisted
  row. Native Month Next/Back/Today and selected-day Agenda reload were verified. Final browser error
  log was empty. The smoke records remain synthetic UAT records; no valuable data was changed.
- **36 settled primary captures**: Agenda/Month × 1440/1024/390 × six themes at 844 CSS pixel height.
  All document scroll widths fit their viewports. Actual raster dimensions/digests are separate in
  [captures.json](evidence/captures.json). [Agenda contact sheet](evidence/contact-agenda.jpg) and
  [Month contact sheet](evidence/contact-month.jpg) were visually reviewed. Two additional images
  show selected-day mobile reload and the desktop Month summary.
- Verification-impact planning selects **FULL**; [plan](evidence/verification-plan.txt) includes the
  inherited prototype paths as unclassified. No mapping was relaxed to obtain a lighter gate.
  Per operator direction, canonical FULL/feature-verify is **deferred until operator UAT**, not passed.
  PostgreSQL integration suites, migration cycling, API drift gate and protected delivery were not run.
  Live server/API checks above are focused checks, not a replacement claim for those gates.

Host frontend checks use Node 24.22.1 / available pnpm 11.25.0, against unchanged lockfile/dependencies;
repository declares pnpm 11.19.0. Physical devices, AT, actual browser zoom, exhaustive modal/theme
combinations, injected live network outages, midnight rollover and large-dataset load were not tested.
Error and focus regressions are component tests; real stale HTTP writes were separately exercised.
The operator reports all six Schedule UX UAT scenarios passed. Independent QA of the committed
implementation and evidence found no blocking defect; no corrective source change was required.
The retained Review was healthy at QA time (frontend/backend/PostgreSQL healthy, fixture v4 ready,
66 records, schema `20261013_0042`). Physical devices, assistive-technology testing, actual browser
zoom, exhaustive dialog/theme combinations, injected live network failures, midnight rollover and
large-collection performance remain unverified. These are recorded limitations, not acceptance
failures in the tested workflows.

## Operator UAT checklist

1. Open Agenda; inspect overdue/today/upcoming work and exact Plant, group, Sowing, SeedLot, identity,
   Location and whole-collection scopes. Follow a target and use Back to return.
2. Choose a day, search/filter and reload; verify exact results and no loss of scope. Use All dates;
   confirm the query/other filters remain. Check default continuous Agenda on mobile.
3. Switch to Month; use Previous/Next across October/November and December/January, Today and Jump
   to date. Check selected date, Back/Forward, overflow drawer and mobile selected-day agenda.
4. Create a synthetic task, edit/reschedule it, reload and inspect it. Cancel a separate task. Verify
   terminal rows do not offer invalid transitions. Check retained historical-target context.
5. Complete without Event; verify no botanical occurrence was created. Separately use the supported
   optional Journal Event flow on an active compatible Plant/PlantGroup, confirming actual date.
6. Use two views to produce a stale edit; confirm conflict, retained draft and explicit Reload current
   activity. Check pristine/dirty cancellation, keyboard Escape and return focus.
7. Inspect desktop/tablet/mobile and preferred themes. Confirm Month's common navigation refinement
   and the absence of production Week. The operator reports this UAT checklist passed across six
   scenarios; see the progress milestone for the authorized independent QA and delivery phase.

After UAT: independent review, freeze, one policy-selected FULL gate, then normal protected delivery.
The separate operator authorization for the delivery phase is recorded in the task handoff; its
actual gate, PR, merge and cleanup results are recorded only after they occur.
