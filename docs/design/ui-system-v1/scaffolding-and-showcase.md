# Gate B — scaffolding and living UI laboratory

**Not implemented during Gate A.** The user explicitly puts implementation after product-direction acceptance. This plan makes the proposed command and examples concrete without registering unsupported production pages.

## Lightweight scaffold

Proposed repository entry: `make ui-page NAME=SeedLotReview ARCHETYPE=directory`. A small Python standard-library generator under `scripts/` validates a PascalCase component name, one of seven explicit archetypes and a resolved output within a designated frontend page folder. Refuse existing files, path separators, traversal, unknown archetype and partial output; no shell interpolation. Support `--check` or dry-run to review paths. Keep command arguments consistent with the current Make workflow.

Generate exactly three files:

1. Typed TSX page composition using existing approved exports, named content slots and explicit TODO regions. No API read, mock persistence, invented permissions or unsupported actions.
2. Vitest/Testing Library skeleton that checks meaningful landmark/name/control expectations and marks domain acceptance work clearly. Do not generate a passing test that only asserts its own placeholder string.
3. Short README with intended archetype, route integration performed manually, URL/query ownership, responsive expectations, loading/empty/error cases, keyboard/focus checklist and narrow verification command.

No route registration, sidebar edit, backend endpoint, data migration or dependency installation. Initially generate DirectoryPage and ActivityPage examples only; additional archetype recipes can be documented compositions until a real consumer needs code.

## Two working React examples after acceptance

| Example                             | Real components                                                                                                  | Demonstrates                                                                                | Acceptance                                                                 |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| SeedLot inventory specimen          | PageHeader, DirectoryTools, QuantityValue, PartialDate, Saved Views, existing SeedLot preview / reference fields | Full-width list, selected inspector, query preservation, precise/approximate/unknown values | Reuses real exports; controlled in-memory fixture; no server mutation      |
| Journal / History activity specimen | PageHeader, actual filters, chronology and shared states                                                         | Occurrence vs recorded timestamp, read-only source facts, long labels, error retry          | No History fabricated from current state; no Journal mutation from History |

These examples live in the dev lab first. Migrate a real page only with the accepted page-direction decision and its existing behavior tests. React examples must compile with strict TypeScript, use actual public exports and receive a focused test; static HTML is not accepted as completion of Gate B.

## Development-only laboratory

Prefer Vite already in the repository, not Storybook or a new component library. Provide an explicit local lab launcher (`make ui-lab`) using a dedicated dev root/entry, fixtures and current CSS. The production `index.html`, production routes, App navigation and build input stay unchanged. The lab entry must fail closed outside DEV; a production build artifact assertion confirms no lab entry, fixture or privileged UI route is emitted. Do not rely solely on hiding a navigation link.

Specimens cover every contract in component-contracts.md, supported variants, six themes, overflow/long labels, empty/loading/error, dialogs, filters, selection and the seven archetypes. Use current controlled fixture helpers and explicit local state; no real owner login, credential or provider API. Controls for viewport width/appearance belong to lab chrome, not product workflows. Include meaningful keyboard exercises and a copyable example beside the rendered component.

## Proposed agent guidance, to apply only with Gate B

> New UI starts from an approved archetype or its documented composition recipe. Reuse existing semantic tokens, DirectoryTools, house dialog and form primitives. Domain code owns API, URLs, validation and scientific meaning. Show desktop/tablet/mobile and keyboard evidence for structural changes; use the impact-selected verification profile. Do not introduce a competing page header, empty inspector or icon-only essential action.

This wording is proposed here only. AGENTS.md and the accepted UI contract remain untouched until the implementation scope is approved.
