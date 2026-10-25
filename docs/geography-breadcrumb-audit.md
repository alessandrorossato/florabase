# Geography operator corrections: breadcrumb audit

Source: `feat/geography-visual-001`, base `e7ade78`, with Botanical Identities #121 (`5778da7`)
integrated by merge. Both histories and the separate IA-NAV worktree are preserved.

## Shared convention

`Breadcrumbs` is now a standalone shared component, re-exported through CollectionUI for existing
callers. Group names without a landing page are plain text; the old Collection/Sourcing links to
Dashboard are removed. Supported directory/record links retain their exact hrefs and identifiers.
The last non-linked item has `aria-current="page"`. Paths wrap on small screens.

PageHeader uses the same component for ordinary root workspaces, using its existing owning group and
title. It does not generate another path on record or `action=` task routes. Dashboard has no added
breadcrumb because it has no meaningful parent. Geography supplies its explicit three-item canonical
path and no persistent tabs. No sidebar group, route owner, macrocategory or Saved View schema changed.

| Representative destination | Result |
| --- | --- |
| Dashboard | Root: no redundant path |
| Seeds | Collection / Seeds; full detail appends the existing record name |
| Sowings | Collection / Sowings; full detail appends its existing title |
| Plants / PlantGroups | Collection / Plants; full detail appends the exact existing plant/group title |
| Harvests | Collection / Harvests; existing named detail path gains Collection |
| Locations | Collection / Locations; existing exact location detail gains Collection |
| Journal, History, Schedule | Activity / current workspace; calendar/filter state unchanged |
| Botanical identities | Explore / Botanical identities; existing exact identity detail gains Explore |
| Taxonomy | Explore / Collection taxonomy, matching the current supported page title |
| Media | Explore / Media; existing named media detail gains Explore |
| Geography, all six routes | Explore / linked Geography Overview / current view; aliases remain supported |
| Suppliers, Orders | Sourcing / current workspace; existing named detail paths retained |
| Settings | Application / Settings, using its existing owner label |
| Labels, Import/Export | Tools / current workspace |

Only straightforward title additions were made to SeedLot, Sowing and Plant/PlantGroup full details.
No domain form or modal route lifecycle was rewritten. Shared breadcrumb tests cover directory groups,
record/task exclusions, current semantics and exact query-bearing href preservation. The full frontend
run exercises the existing workflows as well as new Geography regressions.

## Dedicated follow-up: contextual task paths

Keep contextual create/edit wizards and embedded Reference modules on their established explicit
breadcrumbs for this increment. Their parent may be a filtered collection, source material or an
identity module; normalizing every operation to a universal path requires agreeing that contextual
return contract first. Loading/error placeholders may retain their existing short path until their
record is available. This is a bounded follow-up, not an invitation to redesign the sidebar.

The merge retained main #121's identity hub, Collection media/context changes and identity-scoped
Saved View additions alongside Geography's route adapter. Main's `IdentityMaps` links still use
`#/native-ranges?mode=species&identity=<id>`, `#/species-distribution?identity=<id>` and `#/map`;
all remain supported. Focused integrated checks and the canonical gate are recorded in the current
handoff. The separate IA-NAV-001 design worktree remains untouched.
