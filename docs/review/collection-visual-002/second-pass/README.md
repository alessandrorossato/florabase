# Second visual refinement — COLLECTION-VISUAL-002

Same candidate, HEAD `a36c6cffb938c5ed20f93942e1eac1070897962c`, branch `feat/collection-visual-002`.
[Review](http://localhost:15174) remains candidate-owned, fixture v4/80, revision `20261013_0042`.
No reset/reseed or domain write was submitted in this pass. See the
[handoff](../../../collection-visual-002-handoff.md) for semantics, filter audit and acceptance limits.

## Visual evidence

These **31 viewport captures** supersede the first-pass images for the refined states. They are
viewport screenshots, not full-document screenshots. [Measurements](measurements.json) record actual
viewport dimensions, document width, panel client/scroll heights and selected content widths.

| State                      | 1440×844                                                                               | 1024×844                                                                               | 390×844                                             |
| -------------------------- | -------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | --------------------------------------------------- |
| Harvest directory/preview  | [Selected + preview](1440-harvest-directory-preview.jpg)                               | [Directory](1024-harvest-directory.jpg)                                                | [Directory](390-harvest-directory.jpg)              |
| Harvest Details            | [One-line](1440-harvest-details.jpg)                                                   | [Details](1024-harvest-details.jpg)                                                    | [Details](390-harvest-details.jpg)                  |
| Contextual Edit            | [Details](1440-harvest-edit-details.jpg), [Materials](1440-harvest-edit-materials.jpg) | [Details](1024-harvest-edit-details.jpg), [Materials](1024-harvest-edit-materials.jpg) | [Stacked Materials](390-harvest-edit-materials.jpg) |
| Conversion                 | [Dialog](1440-seed-conversion.jpg)                                                     | [Dialog](1024-seed-conversion.jpg)                                                     | [Scrollable dialog/footer](390-seed-conversion.jpg) |
| Stored material            | [Directory](1440-stored-directory.jpg)                                                 | [Directory](1024-stored-directory.jpg)                                                 | [Readable row](390-stored-directory.jpg)            |
| Location directory/preview | [Selected + preview](1440-location-directory-preview.jpg)                              | [Directory](1024-location-directory.jpg)                                               | [Directory](390-location-directory.jpg)             |
| Deep Location tree         | First-pass full-path evidence remains                                                  | [Tree](1024-location-deep-tree.jpg)                                                    | [Tree](390-location-deep-tree.jpg)                  |
| Location Details           | [Root dashboard](1440-location-details.jpg)                                            | [Details](1024-location-details.jpg)                                                   | [Details](390-location-details.jpg)                 |

All document widths are at or below the tested viewport width. Stored-material identity widths are
914px at desktop, 498px at tablet and 264px at mobile: the few-character column defect is resolved.
At desktop, Harvest's high-value Notes/History row ends at 766px; Photos continues below. Root Location
Details ends at 803px and the document fits 844px. One-line edit panels measure client=scroll=465px;
ordinary conversion and its form measure client=scroll=741px. Native scroll fallback remains for small
screens, many materials, errors and zoom. The final conversion fieldset border polish followed its
capture; field order, control sizing and quantity behavior remain as pictured.

## Zoom proxies

Browser capabilities expose viewport resizing, not true browser zoom. These are honest proxies for a
1440×844 desktop at 125%/150%, not zoom certification:

| State            | 1152×675 (125% proxy)                        | 960×563 (150% proxy)                         |
| ---------------- | -------------------------------------------- | -------------------------------------------- |
| Harvest Details  | [125% proxy](125-proxy-harvest-details.jpg)  | [150% proxy](150-proxy-harvest-details.jpg)  |
| Stored material  | [125% proxy](125-proxy-stored-directory.jpg) | [150% proxy](150-proxy-stored-directory.jpg) |
| Location Details | [125% proxy](125-proxy-location-details.jpg) | [150% proxy](150-proxy-location-details.jpg) |

A native dirty-Escape attempt stalled the browser input channel and exposed no controllable JavaScript
dialog. A fresh candidate tab was opened for read-only evidence and left for review, with its viewport
override reset. Later live keyboard/Back/Save checks are not claimed. Automated tests cover dirty
Escape/backdrop/Cancel, dirty Back refusal and acceptance, Save focus, tab/error reveal, material-line
focus and per-item More dialog return focus. Operator native-confirmation and true zoom checks remain.

## Focused checks

Run inside the existing candidate-owned frontend, without recreating Review:

```text
python3 scripts/workflow_environment.py review compose -- exec -T frontend pnpm test <files>
python3 scripts/workflow_environment.py review compose -- exec -T frontend pnpm exec eslint <changed TS/TSX files> --max-warnings 0
python3 scripts/workflow_environment.py review compose -- exec -T frontend pnpm exec prettier --check <changed frontend files>
python3 scripts/workflow_environment.py review compose -- exec -T frontend pnpm build
python3 scripts/check-features.py
git diff --check
```

Successful focused suites cover **316 distinct tests across 15 files**:
App 78; HarvestScreen 15; StoredMaterial 20; Conversion 9; PlantScreen 58; SeedLotScreen 50;
SowingScreen 31; DashboardScreen, SavedViews, BulkLocation, ReferenceInteractions, FormSections,
DirectoryTools, PartialDateField and recordNavigation 55 combined. The long shared invocation exited
143 after its three page-family suites passed; its eight remaining suites passed in a separate run.
Build includes strict TypeScript and Vite production output. Final lint/format/TypeScript/feature graph
and whitespace checks are recorded in [verification](verification.txt).

No backend application/API/schema/migration/dependency changes. No PostgreSQL or canonical
`make feature-verify`, staging, commit, push or delivery. Persistent UAT remains untouched.
