# v1.0.0 page inventory

This is the page inventory that gate G-UX of the [v1.0.0 release scope](scope-v1.md) evaluates.
It is version 1, derived from `main` at `947d77fc8bd2a757cdf49e28ec2e0f85b0374f1b`.

## Sources

The inventory is derived from two places in the frontend, and from nothing else:

- `workspaces` and `createActions` in `frontend/src/shell/navigation.ts`: every navigation
  destination, every subdestination and every creation entry point.
- `currentRoute()` in `frontend/src/App.tsx`: the record, detail and task routes.

## Freezing for a release candidate

1. At the candidate commit, compare those two sources with this page.
2. A destination, subdestination or record route that was added or removed is recorded as a new
   version of this page in the same change that records the gate. Nothing is dropped silently.
3. The G-UX record names the inventory version and the candidate commit. That pair is the frozen
   inventory for the candidate.

## Navigation destinations

| Workspace | Destination | Route | Subdestinations |
| --- | --- | --- | --- |
| Today | Today | `#/dashboard` | — |
| Collection | Seeds | `#/seeds` | — |
| Collection | Sowings | `#/sowings` | — |
| Collection | Cuttings | `#/cuttings` | — |
| Collection | Plants | `#/plants` | Plant groups `#/plants?type=group` |
| Collection | Harvests | `#/harvests` | Stored material `#/harvests?tab=stored-material` |
| Collection | Locations | `#/locations` | — |
| Activity | Journal | `#/events` | — |
| Activity | History | `#/history` | — |
| Activity | Schedule | `#/schedule` | Calendar `#/schedule?view=calendar` |
| Explore | Botanical identities | `#/identities` | — |
| Explore | Taxonomy | `#/taxonomy` | — |
| Explore | Media | `#/media` | — |
| Explore | Geography | `#/geography` | Collection origins `#/map`; Species distribution `#/species-distribution`; Native ranges `#/native-ranges` |
| Sourcing | Suppliers | `#/suppliers` | — |
| Sourcing | Orders | `#/orders` | — |
| Settings | Theme | `#/settings` | — |
| Settings | Labels | `#/labels` | — |
| Settings | Import / Export | `#/import-export` | — |

That is 19 destinations and 6 subdestinations.

## Record and detail routes

| Record | Route |
| --- | --- |
| Seed lot | `#/seeds/<id>` |
| Sowing | `#/sowings/<id>`, with the germination and lineage tabs |
| Plant | `#/plants/<id>` |
| Plant group | `#/plant-groups/<id>` |
| Cutting material lot | `#/cuttings/lots/<id>` |
| Rooting attempt | `#/cuttings/attempts/<id>` |
| Harvest | `#/harvests/<id>` |
| Location | `#/locations/<id>` |
| Botanical identity | `#/identities/<id>`, with the reference and edit tabs |
| Media asset | `#/media/<id>` |
| Provenance site | `#/geography/<id>` |
| Supplier | `#/suppliers/<id>` |
| Order | `#/orders/<id>` |
| Material ancestry | `#/lineage/<kind>/<id>` for seed lot, sowing, plant, plant group, vegetative lot and propagation attempt |
| Label composer for one record | `#/labels?kind=<kind>&record=<id>` |

## Creation and task routes

`#/seeds?action=create`, `#/sowings?action=create`, `#/sowings?action=start`,
`#/plants?action=create&kind=plant`, `#/plants?action=create&kind=group`,
`#/plants?action=from-sowing`, `#/plants?action=extract`, `#/cuttings/new`,
`#/harvests?action=create`, `#/identities?action=create`, `#/suppliers?action=create`,
`#/locations?action=create`, `#/geography?action=create`.

## Shell surfaces

Sign-in; the command palette; the create menu; the record sheet; the phone bottom bar; dialogs
and their dismissal.

## What is evaluated for each entry

- Viewports 390×844, 1024×844 and 1440×844, as in the [UI contract](../ui-contract.md).
- One light and one dark appearance of each shipped theme for contrast; one light and one dark
  appearance for the other checks.
- States: populated, and empty where the page has a list.
- The five G-UX criteria: no horizontal page scroll; keyboard operation with visible focus;
  dialog focus trapping and return; 4.5:1 text contrast; use at 200 % zoom.

A page that cannot show a state, such as an empty state for a detail route, is recorded as not
applicable with the reason.

## Limits of version 1

The record routes were read from `currentRoute()` and from the links the frontend builds. Tabs
inside a detail page other than those named above were not enumerated; they are evaluated as
part of their detail route. The freeze step above is where an omission is corrected.
