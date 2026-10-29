> Gate B is approved. The current production handoff is [Wave 1](wave1/README.md); this document retains the earlier design/prototype evidence.

> **Operator update, 27 October 2026:** Proposal B is selected with refinements.
> [Gate B working candidate, state contract and verification](gate-b/README.md).
> The Gate A record below is preserved history; its pending-acceptance statements
> describe that earlier phase, not the current implementation scope.

# Florabase UI System v1 — Gate A

**Product direction candidate, 26 October 2026.** Review at <http://localhost:15283/>.
Start with the five A/B comparisons, then the page-family specimens. This is a design-only HTML prototype, using current semantic tokens and approved synthetic Review fixtures. It is not a second React component library or a production component showcase.

## Decisions requested

| Decision        | Recommendation                                                          | Alternative / cost                                                                   |
| --------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Dashboard       | A: work first, one factual holdings strip                               | B: collection portrait, slower access to daily work                                  |
| Seeds           | A: full-width inventory table; selected inspector only                  | B: richer rows, easier visual recognition but fewer records per screen               |
| Plants / groups | A: operation table, explicit type filter                                | B: photographic cards, useful browsing but weak without assigned photos              |
| Identities      | A: visual reference index with truthful coverage and image availability | B: analytical index, most efficient when covers are absent                           |
| Create / Edit   | B: continuous sections with anchor navigation, sticky actions           | A: one active section, stronger guidance but hides context                           |
| Mobile          | One compact brand/menu, existing bottom destinations, utilities in More | Removes duplicate utility chrome; More adds one step to Settings/Appearance/Sign out |
| Shared system   | Seven composed archetypes, existing house primitives                    | No business rules inside a universal page component                                  |

Identities opens the hub directly because the index already shows name and collection coverage. Seeds/Plants retain a selected-only preview for operational context.

Choose page directions independently; accepting a palette does not accept workflow changes. The visual index must use actual explicit Identity covers in the product. Reference photographs in this candidate illustrate the design only. The real captured dataset currently has no assigned covers; the analytical alternative stays useful without imagery.

## Package

- [Complete UX critique and archetype matrix](ux-critique.md): 27 audited families plus contextual forms/detail/mobile decisions.
- [Architecture and named slots](architecture.md).
- [Component contracts and ownership](component-contracts.md).
- [Tokens, responsive and accessibility rules](tokens-responsive-accessibility.md).
- [Gate B scaffolding and living showcase proposal](scaffolding-and-showcase.md).
- [Migration, checks and integration boundaries](migration-and-regression.md).
- [Evidence, reference interpretation and limitations](evidence-and-references.md).
- [Interactive comparisons](compare.html), [prototype](prototype.html), [image attribution](credits.html).
- [Capture/interaction verification](validation.json), [reviewed evidence manifest](evidence-review.json).

## Reopen locally

From the repository root: `python3 docs/design/ui-system-v1/serve.py`, then <http://localhost:15283/>. The read-only server binds 127.0.0.1. No authentication, database, API, provider, Docker startup or collection edits are needed. `build-data.py` rebuilds examples from repository fixtures and captured DOM; it requires the preceding audit artifacts at their recorded local location. Fonts and rendered screenshots remain in the task's external visualization directory, not Git. See evidence documentation for the asset manifest and portable limitations.

## Gate boundary

Gate A proposes architecture and shows working **design interactions**. Gate B remains pending operator acceptance: production React templates, the actual scaffold command, dev-only React laboratory, focused shared tests and two real archetype integrations. No production routes, navigation, shared components, tokens, AGENTS.md or UI contract are changed in this candidate. `UI-SYSTEM-001` remains `in_progress`; no implementation/verification claim covers Gate B.

No staging, commit, push, PR or canonical FULL gate was performed for this design candidate.

`FLORABASE_UI_SYSTEM_V1_DESIGN_READY_FOR_REVIEW`
