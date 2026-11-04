# Decisions D1–D6 (open, deferred without decision)

**Status: OPEN, DEFERRED WITHOUT DECISION.** UI-DESIGN-001 closed on 4 November 2026 with all six
decisions undecided. The operator chose to explore a more radical redesign (Florabase Next) instead.
The mockups and the design artifact illustrate the reviewer's **proposed** option only so it could be
judged visually. That is not a recommendation adopted or a decision made. Any future increment that
revives one of these items must obtain its decision first.

| ID | Question | Option A — keep current (EXISTING) | Option B — PROPOSAL illustrated in the mockups | Affects | Blocks |
| --- | --- | --- | --- | --- | --- |
| D1 | Sidebar at tablet widths (≤64rem) | Full labelled sidebar until 48rem | Icon rail with labels as accessible names and tooltips; records gain ≈170 px | `App.tsx` shell, `foundation.css` | Optional; independent of all phases |
| D2 | Gallery placeholder when a record has no photo | Compact 3rem placeholder (intentional Wave 3 treatment) | The same 4:3 frame as a photo, with the icon centered | `DirectoryCard`, `directory-system.css` (F-15) | Phase 5 gallery work |
| D3 | Casing of record types in UI copy | Mixed, as today ("Edit Plant", "Edit seed lot") | Sentence case: "Edit plant", "Create plant group", "Delete order", "Loading sowings…" | Labels across owners; tests asserting button names (F-12) | Phase 3 label changes |
| D4 | The context row above Plant/Sowing Details (C5) | Keep "← Back to …" and "New …" above the breadcrumb | Remove it. The breadcrumb is the return route; creation stays in the directory and header actions | `PlantScreen`, `SowingScreen` `WorkspaceIntro contextActions` (F-03); closes the UI-FLICKER-001 C5 offset | Phase 3 |
| D5 | Facts repeated in the header and DetailSummary | Keep both (deferred content item) | Lifecycle and location stay in the header; the summary drops them and shows origin, entry date and kind/quantity | Plant, Sowing and Seed lot summaries | Phase 3 summary change |
| D6 | Primary creation action on phones | Visible "New plant or group" in the tool lane | A header button labeled "New"; accessible name "New plant or group"; per-page select leaves the compact results bar | `DirectoryTools`, `PageHeader` compact slot (F-01) | Phase 4 |

No phase of the [implementation plan](implementation-plan.md) is approved, including phases 0–2, which
do not depend on these decisions.

## Decision record

| ID | Decision | Decided by | Date |
| --- | --- | --- | --- |
| D1 | — open (deferred at closure, 4 Nov 2026) — | | |
| D2 | — open (deferred at closure, 4 Nov 2026) — | | |
| D3 | — open (deferred at closure, 4 Nov 2026) — | | |
| D4 | — open (deferred at closure, 4 Nov 2026) — | | |
| D5 | — open (deferred at closure, 4 Nov 2026) — | | |
| D6 | — open (deferred at closure, 4 Nov 2026) — | | |
