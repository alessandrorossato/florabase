# Decisions awaiting approval (D1–D6)

**Status: DECISION PENDING for every item.** None of these has been decided. The mockups and the
design artifact illustrate the reviewer's **proposed** option so it can be judged visually. That is
not a recommendation already adopted. Record each answer here, or in the follow-up implementation
increment, before work that depends on it begins.

| ID | Question | Option A — keep current (EXISTING) | Option B — PROPOSAL illustrated in the mockups | Affects | Blocks |
| --- | --- | --- | --- | --- | --- |
| D1 | Sidebar at tablet widths (≤64rem) | Full labelled sidebar until 48rem | Icon rail with labels as accessible names and tooltips; records gain ≈170 px | `App.tsx` shell, `foundation.css` | Optional; independent of all phases |
| D2 | Gallery placeholder when a record has no photo | Compact 3rem placeholder (intentional Wave 3 treatment) | The same 4:3 frame as a photo, with the icon centered | `DirectoryCard`, `directory-system.css` (F-15) | Phase 5 gallery work |
| D3 | Casing of record types in UI copy | Mixed, as today ("Edit Plant", "Edit seed lot") | Sentence case: "Edit plant", "Create plant group", "Delete order", "Loading sowings…" | Labels across owners; tests asserting button names (F-12) | Phase 3 label changes |
| D4 | The context row above Plant/Sowing Details (C5) | Keep "← Back to …" and "New …" above the breadcrumb | Remove it. The breadcrumb is the return route; creation stays in the directory and header actions | `PlantScreen`, `SowingScreen` `WorkspaceIntro contextActions` (F-03); closes the UI-FLICKER-001 C5 offset | Phase 3 |
| D5 | Facts repeated in the header and DetailSummary | Keep both (deferred content item) | Lifecycle and location stay in the header; the summary drops them and shows origin, entry date and kind/quantity | Plant, Sowing and Seed lot summaries | Phase 3 summary change |
| D6 | Primary creation action on phones | Visible "New plant or group" in the tool lane | A header button labeled "New"; accessible name "New plant or group"; per-page select leaves the compact results bar | `DirectoryTools`, `PageHeader` compact slot (F-01) | Phase 4 |

Phases 0, 1 and 2 of the [implementation plan](implementation-plan.md) do not depend on any of these
decisions.

## Decision record

| ID | Decision | Decided by | Date |
| --- | --- | --- | --- |
| D1 | — pending — | | |
| D2 | — pending — | | |
| D3 | — pending — | | |
| D4 | — pending — | | |
| D5 | — pending — | | |
| D6 | — pending — | | |
