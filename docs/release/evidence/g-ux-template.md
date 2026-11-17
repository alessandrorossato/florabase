# G-UX record template

This is a template for gate G-UX of the [v1.0.0 release scope](../scope-v1.md#release-gates).
Copy it to `g-ux-<candidate>.md` for a recorded run. A copy counts as evidence only when every
field below is filled in from an actual run on the release-candidate images. This template is
not evidence.

## Run

| Field | Value |
| --- | --- |
| Candidate commit and version | |
| Images | backend and frontend digests from the release manifest |
| Page inventory version | 1, or the version recorded with this run |
| Dataset | empty database, then the populated dataset named here |
| Browsers and devices | |
| Themes evaluated | every shipped theme, light and dark, for contrast; one light and one dark for the other checks |
| Recorded by, date | |

Before the run, compare the [page inventory](../page-inventory-v1.md) with
`frontend/src/shell/navigation.ts` and `currentRoute()` at the candidate. Record any added or
removed entry as a new inventory version in the same change as this record. Settings → Account
is in the shell navigation and missing from inventory version 1, so it is added as version 2.

## Criteria

For each entry: **S** no horizontal page scroll at 390, 1024 and 1440 px; **K** every control is
operable by keyboard with visible focus; **D** dialogs trap focus and return it; **C** 4.5:1 text
contrast in every shipped theme; **Z** usable at 200 % zoom. Record Pass, Fail (with a defect
reference) or N/A (with the reason) for each, and for both the populated and the empty state
where the page has a list.

## Matrix

The last column names the certification rows that this entry supplies. Each evidence map under
[`certify/`](certify/README.md) names the exact part of this record that it relies on, and a
cell counts only for the rows that cite it.

| Entry | Route | S | K | D | C | Z | Empty | Supplies certification rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Today | `#/dashboard` | | | | | | | UX-TODAY-001; UI-SYSTEM-001 #3 (R16), #4 (R24: four photos, Plant links, labelled fallback, layout); UX-006 #3 (R14, proposed); THEMES-001; BRAND-01 #2 (mark in the shell) |
| Seeds and seed lot | `#/seeds`, `#/seeds/<id>` | | | | | | | UX-003; UI-SYSTEM-001; CONTROLS-001; UI-POLISH-001 #4 |
| Sowings and germination tab | `#/sowings`, `#/sowings/<id>` | | | | | | | GERMINATION-001; UX-003; UI-POLISH-001 #4 |
| Cuttings, lot and attempt | `#/cuttings`, `#/cuttings/lots/<id>`, `#/cuttings/attempts/<id>` | | | | | | | CUTTING-001 (writer's handoff); FABLE-FIX-CUTTINGS |
| Plants, Plant groups and Plant detail | `#/plants`, `#/plants?type=group`, `#/plants/<id>`, `#/plant-groups/<id>` | | | | | | | UX-003; MEASUREMENT-001 (height table and chart, both themes); PHENOLOGY-001; UI-POLISH-001 #4 |
| Harvests and Stored material | `#/harvests`, `?tab=stored-material`, `#/harvests/<id>` | | | | | | | HARVEST-001 #5 (R10), #4 (image fallback caption names its owner; R19 if confirmed); COLLECTION-VISUAL-002 #1 (R02), #8 (R23 if confirmed); UI-POLISH-001 #4 |
| Locations | `#/locations`, `#/locations/<id>` | | | | | | | LOCATION-002 #3; LOCATION-003 #3 (R25); COLLECTION-VISUAL-002 #4 (R03); UX-005 (R09) |
| Journal | `#/events` | | | | | | | UX-006; UX-DATE-001 |
| History | `#/history` | | | | | | | UX-006; UI-SYSTEM-WAVE2-001 |
| Schedule and Calendar | `#/schedule`, `?view=calendar` | | | | | | | UI-SYSTEM-WAVE2-001 |
| Botanical identities and identity detail | `#/identities`, `#/identities/<id>` | | | | | | | UX-004 #1; BOTANICAL-IDENTITIES-VISUAL-001 #1 (R05), #6 (R20 if confirmed: selection fill contrast) |
| Taxonomy | `#/taxonomy` | | | | | | | TAXONOMY-002 |
| Media and media asset | `#/media`, `#/media/<id>` | | | | | | | ATTACHMENT-005 #4; MEDIA-VISUAL-001 |
| Geography and sub-views | `#/geography`, `#/map`, `#/species-distribution`, `#/native-ranges`, `#/geography/<id>` | | | | | | | GEOGRAPHY-003; GEOGRAPHY-VISUAL-001 #1 (R04), #4 (no persistent tab strip); MAP-001 #6; UX-005 (R09) |
| Suppliers and supplier | `#/suppliers`, `#/suppliers/<id>` | | | | | | | UX-005 (R09); UI-SYSTEM-WAVE2-001 #3 (R06); UI-POLISH-001 #4 |
| Orders and order | `#/orders`, `#/orders/<id>` | | | | | | | UI-SYSTEM-WAVE2-001 #3 (R06); UI-POLISH-001 #4 |
| Settings: Theme | `#/settings` | | | | | | | THEMES-001 |
| Settings: Labels and the label composer | `#/labels`, `#/labels?kind=<kind>&record=<id>` | | | | | | | — |
| Settings: Import / Export | `#/import-export` | | | | | | | IMPORT-001 |
| Settings: Account (inventory version 2) | Account destination | | | | | | | ENG-01 |
| Material ancestry | `#/lineage/<kind>/<id>` | | | | | | | LINEAGE-003 |
| Shell surfaces | sign-in, command palette, create menu, record sheet, phone bottom bar, dialogs | | | | | | | CONTROLS-001 #3 (R11; R21 open); UI-REDESIGN-EXPLORATION-001 #4, #5; BRAND-01 (icons and logo); PWA-001 |

Creation and task routes, as listed in the inventory, are recorded as rows under their owning
entry.

## Defects

| ID | Entry | Criterion | Description | Severity | Resolution: commit, or disposition with reason |
| --- | --- | --- | --- | --- | --- |

## Outcome

G-UX passes when every entry has S, K, D, C and Z as Pass or a justified N/A, and every defect is
fixed or dispositioned. Recorded by: role, date.
