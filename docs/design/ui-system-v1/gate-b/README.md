> Gate B is approved. The current production handoff is [Wave 1](../wave1/README.md); this document retains the earlier design/prototype evidence.

# Gate B — Proposal B refined, working React candidate

Operator decision: **B**, including dual directory views, semantic navigation icons,
a prominent KPI strip and eight photographs. This bounded implementation is ready
for layout/template review before production page migration. Gate A research,
alternatives and its original evidence remain historical and unchanged.

- [Working Dashboard and directory prototype](http://localhost:15284/ui-lab/#/dashboard).
- [Before/after and responsive gallery](http://localhost:15283/gate-b/index.html).
- [Development component showcase](http://localhost:15284/ui-lab/#/components).
- [Template/state/scaffolding contract](implementation.md).
- [Focused verification and limits](verification.md).

Run from this worktree: `python3 docs/design/ui-system-v1/serve.py` for the review
portal on loopback 15283; `make ui-lab` for Vite on loopback 15284. Both are local
processes, independent of DEV/UAT/Review, with no database or authentication.
If the computer/app restarts, rerun these commands. Stop only those processes.
The gallery's large JPEG files live in the task's external visualization directory;
their manifest is in this folder. A fresh clone needs those review artifacts to
reproduce the screenshot gallery; the React lab uses repository fixtures directly.

## Exact changes from the original B

| Area               | Original Gate A B                                  | Refined B                                                                                                                                |
| ------------------ | -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Dashboard          | Collection portrait composition                    | One strong four-metric strip; eight distinct 4:3 reference photographs in 4×2; useful adjacent Next work; explicit History/Journal links |
| Directories        | Independent rich-row/photo/analytical alternatives | One controlled List/Gallery pattern; the same records, names, filters and selection; compact aligned thumbnails and photographic cards   |
| Defaults           | Page-specific static alternatives                  | Seeds/Sowings List; Plants/Identities Gallery; URL and browser preference contract                                                       |
| Inspector          | Design interaction                                 | Real shared responsive inspector; inline desktop, house modal at ≤75rem; tested focus return when rows remount/disappear                 |
| Navigation         | Repeated/generic pictograms                        | Existing typed Icon vocabulary and semantic destination map; visible labels, frozen groups and routes                                    |
| Header             | Gate A layout recipes                              | Real PageHeader + DirectoryTools; intrinsic wrapping; shared axis/basis defect corrected at its existing CSS rule                        |
| Developer workflow | Proposed scaffold/lab                              | Two actual React archetypes; validated `make ui-page`; dev-only Vite entry with production exclusion check                               |

The 1440×844 measured CSS viewport contains the header, strip, eight loaded photos
and Next work without document scrolling. Browser DPR and visual scale were 1;
this is the baseline viewport test, not a claim of exercising browser zoom controls.
The strip is factual synthetic Review data: **17 individual Plant records, 7
PlantGroup records, 40 SeedLots, 12 active Sowings**. Plant groups never become a
new sidebar destination or an individual-plant quantity. All-Plant scope counts
24 records; it does not claim 24 individual plants.

The eight photographs already exist in the v5 fixture media manifest. They are
explicitly attributed **botanical reference illustrations**, with stable order,
identity-search links and no invented specimen, primary-photo or cover assignment.
The lab does not contact external image providers. Production integration must
prefer the existing protected/local primary-photo contract and preserve external
opt-in and honest missing/broken-image states. Some representative directory
records therefore intentionally have no image. See the lab's Attribution page.

The synthetic snapshot is dated **26 October 2026**. Today/Overdue values describe
that captured state, rather than the current operator date.

## Bounded behavior

The lab demonstrates four directory families and a separate Journal chronology
using captured synthetic facts. Search is applied before the ten-record display
excerpt. Plants supports the existing type scope; other domain filters are shown
as page-owned boundaries rather than implemented fictitious controls. It is not
a replacement API, full dataset, pagination contract or backend integration.
Unsupported lab destinations lead to preserved Gate A studies; detail/create
links are explicitly specimens. Production routes and directory implementations
are not migrated. The Saved Views exercise runs the delivered v1 canonical adapter
in memory; it neither creates nor persists owner SavedView records.

Production-reachable changes are limited to decorative destination icons,
the shared header flex-axis correction and an optional TaskDialog focus fallback.
No shared tokens, API/schema, domain state, media code or environment is changed.

## Proposed migration waves — operator review first

1. **Review this candidate.** Approve Dashboard composition, dual views, density,
   navigation and optional inspector. Keep the tree unstaged/uncommitted. No FULL.
2. **Seeds/Sowings pilot.** One directory at a time, List default; use the exact
   existing API, quantity/PartialDate, filter, Saved View and Quick Preview contracts.
   Confirm selection/pagination/recovery and keyboard behavior against the real page.
3. **Plants/Identities.** Gallery defaults, local group mode, reference versus owned
   photography and missing covers, full existing identity hub semantics. No new lifecycle
   statuses such as Growing/Flowering are inferred from the visual reference.
4. **Remaining directories and Dashboard.** Suppliers/Orders start List for workflow
   comparison. Dashboard gets its own reviewed aggregate/photo integration; fixture
   metrics never become a live source. ActivityPage composes actual chronology, never
   derives History from current state or `updated_at`.
5. **Specialized workspaces/forms.** Maps/tree/calendar/timelines keep their own
   representation controls. Reuse header/tokens only where appropriate. Each existing
   form retains its owning validation, save boundary and navigation behavior.

Media delivered independently as [PR #127](https://github.com/alessandrorossato/florabase/pull/127),
merge `69814bba`, after this candidate's `ee34874` base. Its clean worktree and changed
paths were inspected: no shared-file overlap. No Media files were copied, replaced or
rebased here. Before delivery, synchronize the candidate with then-current main,
preserve both documentation milestones and rerun the appropriate tests. CI-004 chooses
the final canonical profile then; this review candidate has no verification receipt.
