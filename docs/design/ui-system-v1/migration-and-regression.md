# Migration and verification plan

## Integration ownership

Base fetched and inspected: `origin/main ee3487412fe458cbdf7145154c54a58b66132cae` (delivered Taxonomy PR #126). Candidate branch `docs/ui-system-v1-design`, same Codex-managed bc88 worktree. The preceding RELEASE-VISUAL-AUDIT-001 dirty documentation remains intact; this design is a separate directory/feature record, not a production implementation hidden inside the audit.

Media workstream: chat **Audit Media workspace visuals**, worktree 1d44, separately approved photographic implementation. Explicit operator authorization permits coordination. Latest workstream report says local wrapping-header and Cancel-first PhotoDialog fixes, 31 real captures, 122 tests and a later affected 40-test run plus lint/build; these are owner-reported, not rerun by this design task. Header owner measurements: 98px at 1440, 186px at 1024/880, 212px mobile; gallery 4/3/2/2 columns. URL/offset/card-focus corrections remain Media-owned. No copying their code, environment takeover, authentication-cookie replacement or merging their work is part of Gate A.

| Shared issue                       | Current ownership                                                                  | Proposed system prevention                           | Integration requirement                                                                                                       |
| ---------------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| F09: tablet page-header height     | Global shared issue unresolved; Media has local scoped correction                  | Intrinsic grid/wrapping, no axis-changing flex basis | Inspect delivered Media diff first; shared fix must preserve gallery and compact metrics before removing any local workaround |
| F01: Delete receives initial focus | Media has local Cancel-first correction; global dialog contract extension proposed | Explicit safe initial target in house dialog         | Verify Media and non-Media consumers independently; don't replace correct local behavior by DOM-order guessing                |
| Taxonomy                           | Delivered accepted graph architecture                                              | Surrounding header/state convergence only            | Preserve graph/camera/fullscreen/keyboard semantics; missing WFO does not justify fake graph fixtures as source validation    |
| Maps                               | Accepted Geography workspaces and evidence contracts                               | Same shared control grammar, map-dominant content    | No provider load on open/search/selection/restore; separate occurrence/range/origin evidence                                  |

## Migration waves after Gate A acceptance

1. **Foundation, bounded Gate B:** reconcile latest delivered main and Media; implement shared header/dialog focus and minimum composed archetypes; add scaffold/lab; demonstrate Directory and Activity with real house components. No broad page migration. Update UI contract/AGENTS only for accepted responsibilities.
2. **Inventory:** migrate accepted Seeds table or list, selected-only inspector and Plants/groups representation. Preserve URL/saved queries, bulk visible-only eligibility, quantity/date contracts, source chooser and edit drafts. Evaluate first-page/body geometry before adding imagery.
3. **Reference and Dashboard:** accepted Identity index/hub framing and Dashboard approach. Ship a useful no-cover state; photos never substitute for assignments. Six-section hub and independent save boundaries remain intact.
4. **Activity and sourcing:** Journal/History density, Schedule list framing, Supplier directory, Orders table/detail. Keep calendar state, completion, transaction/packet separation and destructive guards.
5. **Specialized framing / remaining forms:** Locations outline/detail, labels/import/settings controls and map/tree surroundings only after each acceptance. No migration of a good canvas to a generic card page.

Each wave is independently reviewable/deliverable with a behavior-preserving rollback. Old and new compositions coexist through the same primitive exports. Do not implement all seven templates before the first real consumer demonstrates a need.

## CI-004 regression strategy

During Gate A run syntax/assertions, data provenance/link/asset checks, feature graph, diff hygiene and browser design checks. No repeated FULL exploration gates, backend tests or API regeneration for files that do not change application code.

Gate B shared components/styles affect many consumers and conservatively select canonical FULL under existing policy. Use focused tests while developing, independent domain/UI/implementation review, freeze tree, then one `make feature-verify` on the final exact source. Never manually repeat its covered stages. A source/test change after receipt invalidates it. No skipped-success wrappers or weakened protected suites.

For later isolated page migrations, use the policy-selected impact profile plus affected behavior/focus tests and representative screenshots. Header/dialog/inspector contract tests are reused; don't run a 27-page six-theme matrix for every small label edit. Unknown scope, infra, config, dependencies, security and workflow changes still escalate FULL.

## Review acceptance before Gate B

Record choices A/B per Dashboard, Seeds, Plants, Identities and forms; approve/reject forest rail independently; confirm selected-only inspector and compact mobile utilities. Review at least one long-name/unknown-date/unknown-stock state, 1024px header and 390px form/preview. Approve bounded system implementation separately from migrating those product pages. The mockups are concrete enough for this review; actual React acceptance, assistive technology and device evidence remain pending.
