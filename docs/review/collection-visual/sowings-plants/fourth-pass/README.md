# COLLECTION-VISUAL-001 — fourth-pass evidence

Current candidate `ef73`, `feat/collection-visual-001`, HEAD/base `1e3df6a` plus unstaged source.
Operator visual acceptance is pending. Prior passes are historical, not current-source verification.
[Handoff](../../../../collection-visual-001-handoff.md) · [checks and source hashes](checks.json).

[Feature Review](http://localhost:15174) is healthy with the same owner, DB/code `20261013_0042` and
v4 / ready / 66 records. On resumption the frontend/backend were stopped; supported
`make feature-review-up` restored this exact source while preserving DB/media. No reset, removal,
reseed, collection write or persistent-environment operation. [Final status](review-status.txt).

## Responsive forms and bottom edges

[Matrix](responsive-matrix.json): **30 unique checks**, five forms at 1440×844, 1024×844, 390×844
and effective 1152×675, 960×563 and 819×675 viewport proxies. No measured page/control horizontal
overflow. All form/footer backgrounds are transparent, footer positions static and edges aligned.
All five mobile footer bottoms clear the [shared mobile navigation geometry](mobile-navigation.json).
Every requested form has bottom-edge captures at every size, plus desktop/mobile top views.
Actual 125%/150% browser zoom remains untested; proxies do not certify actual zoom.

Observed real 1440×844 / 100% default fixture pages:

| Form               | Page height | Footer bottom |
| ------------------ | ----------: | ------------: |
| New Plant          |       844px |         790px |
| New Plant group    |       844px |         803px |
| New Sowing         |       844px |         817px |
| Guided Plant       |       844px |         808px |
| Guided Plant group |       846px |         822px |

Guided group is two pixels taller than the viewport; its footer remains visible. Conditional fields,
completion outcome, validation and smaller/zoom-proxy screens may scroll. Text and controls were not
shrunk. Sowing SeedLot/label and quantity/location have identical measured control tops; Substrate/
Method and Pretreatment/temperature parts also align. Notes/Environment use coherent textarea heights.

[Three Origin editors](edit-matrix.json) cover Plant, group and direct-origin Plant at real 1440×844;
all fit without internal panel scrolling and keep the footer visible. Caption cleanup retains native
accessible names and groups. [Live More checks](actions.json) verify Transfer placement, keyboard entry,
Escape and Transfer-dialog focus return for both menu owners; blocked Undo remains accessible.
[Navigation](navigation.json) records both live guided Cancel returns to the exact source Lineage tab.
Real-history unit tests cover Back/Cancel for both source tabs. A live browser Back reached the source,
but its browser tool wait stalled; a complete live Back matrix is not claimed. No mutation was submitted.

## Focused verification

From `frontend/`:

```sh
node node_modules/vitest/vitest.mjs run --configLoader runner src/plants/PlantScreen.test.tsx src/sowings/SowingScreen.test.tsx src/propagation/GuidedForms.test.tsx src/seed-lots/PartialDateField.test.tsx src/components/recordNavigation.test.ts src/propagation/CreationReversal.test.tsx src/components/CollectionUI.test.tsx src/components/FormSections.test.tsx src/seed-lots/SeedLotScreen.test.tsx src/App.transition.test.tsx src/App.lazy.test.tsx --maxWorkers=1
node node_modules/vitest/vitest.mjs run --configLoader runner src/plants/PlantScreen.test.tsx --maxWorkers=1
npm run build
```

**178 distinct tests / 11 files passed** across bounded runs. The combined attempt had 175 passes and
three Plant failures; its ten clean files contribute 120 cases. Corrected an overbroad test-label edit
that affected an unrelated Journal date query and awaited required scheduled menu focus. The final
complete Plant repeat passed **58**. One interrupted repeat exited 143 without results and is not
counted. No timeout, payload/quantity/CSRF/conflict assertion or validation was weakened.

Touched TS/TSX/CSS paths come from `git diff --name-only` plus `git ls-files --others --exclude-standard`.
Prettier check passes that exact set; ESLint checks its TS/TSX subset with `--max-warnings 0`.
The production build includes strict `tsc -b` and Vite. Test-only typing and void-arrow style issues
were corrected before final checks. `python3 scripts/check-features.py`: **105 valid**;
`git diff --check`: clean. Nine whitespace-normalized domain/payload/reversal helpers match HEAD;
guided write payloads and atomic calls are unchanged. No backend/API/schema/migration/dependency edits.

Canonical `make feature-verify` was not run. No staging, commit, push or delivery; no receipt is claimed.
Status stays implemented. Fourth-pass acceptance, actual browser zoom and later independent QA remain.

## Captures

- [direct plant edit origin 1440 100](direct-plant-edit-origin-1440-100.png)
- [group edit origin 1440 100](group-edit-origin-1440-100.png)
- [group more 1440 100](group-more-1440-100.png)
- [guided group 1024 100 bottom](guided-group-1024-100-bottom.png)
- [guided group 1024 125 proxy bottom](guided-group-1024-125-proxy-bottom.png)
- [guided group 1440 100 bottom](guided-group-1440-100-bottom.png)
- [guided group 1440 100 top](guided-group-1440-100-top.png)
- [guided group 1440 125 proxy bottom](guided-group-1440-125-proxy-bottom.png)
- [guided group 1440 150 proxy bottom](guided-group-1440-150-proxy-bottom.png)
- [guided group 390 100 bottom](guided-group-390-100-bottom.png)
- [guided group 390 100 top](guided-group-390-100-top.png)
- [guided plant 1024 100 bottom](guided-plant-1024-100-bottom.png)
- [guided plant 1024 125 proxy bottom](guided-plant-1024-125-proxy-bottom.png)
- [guided plant 1440 100 bottom](guided-plant-1440-100-bottom.png)
- [guided plant 1440 100 top](guided-plant-1440-100-top.png)
- [guided plant 1440 125 proxy bottom](guided-plant-1440-125-proxy-bottom.png)
- [guided plant 1440 150 proxy bottom](guided-plant-1440-150-proxy-bottom.png)
- [guided plant 390 100 bottom](guided-plant-390-100-bottom.png)
- [guided plant 390 100 top](guided-plant-390-100-top.png)
- [new group 1024 100 bottom](new-group-1024-100-bottom.png)
- [new group 1024 125 proxy bottom](new-group-1024-125-proxy-bottom.png)
- [new group 1440 100 bottom](new-group-1440-100-bottom.png)
- [new group 1440 100 top](new-group-1440-100-top.png)
- [new group 1440 125 proxy bottom](new-group-1440-125-proxy-bottom.png)
- [new group 1440 150 proxy bottom](new-group-1440-150-proxy-bottom.png)
- [new group 390 100 bottom](new-group-390-100-bottom.png)
- [new group 390 100 top](new-group-390-100-top.png)
- [new plant 1024 100 bottom](new-plant-1024-100-bottom.png)
- [new plant 1024 125 proxy bottom](new-plant-1024-125-proxy-bottom.png)
- [new plant 1440 100 bottom](new-plant-1440-100-bottom.png)
- [new plant 1440 100 top](new-plant-1440-100-top.png)
- [new plant 1440 125 proxy bottom](new-plant-1440-125-proxy-bottom.png)
- [new plant 1440 150 proxy bottom](new-plant-1440-150-proxy-bottom.png)
- [new plant 390 100 bottom](new-plant-390-100-bottom.png)
- [new plant 390 100 top](new-plant-390-100-top.png)
- [new sowing 1024 100 bottom](new-sowing-1024-100-bottom.png)
- [new sowing 1024 125 proxy bottom](new-sowing-1024-125-proxy-bottom.png)
- [new sowing 1440 100 bottom](new-sowing-1440-100-bottom.png)
- [new sowing 1440 100 top](new-sowing-1440-100-top.png)
- [new sowing 1440 125 proxy bottom](new-sowing-1440-125-proxy-bottom.png)
- [new sowing 1440 150 proxy bottom](new-sowing-1440-150-proxy-bottom.png)
- [new sowing 390 100 bottom](new-sowing-390-100-bottom.png)
- [new sowing 390 100 top](new-sowing-390-100-top.png)
- [plant edit origin 1440 100](plant-edit-origin-1440-100.png)
- [plant more 1440 100](plant-more-1440-100.png)
