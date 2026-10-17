> **Historical third-pass evidence.** The [fourth-pass index](../fourth-pass/README.md) supersedes form/workflow conclusions and source hashes. Operator acceptance remains pending.

# COLLECTION-VISUAL-001 — third-pass evidence

Current candidate: `ef73`, branch `feat/collection-visual-001`, base/HEAD `1e3df6a` plus unstaged source.
The first and second passes are historical and were not operator-accepted. This index supersedes
those visual conclusions. See the [handoff](../../../../collection-visual-001-handoff.md).

[Feature Review](http://localhost:15174) remains healthy, owned by this candidate, with its existing
v4 / ready / 66-record fixture and DB/code revision `20261013_0042`.
The final [read-only status](review-status.txt) confirms identity and health. No reset, removal,
reseed, collection writes, reversal submission or persistent-environment operation occurred.

## Responsive and interaction evidence

[Check summary and source hashes](checks.json) · [Layout matrix](responsive-matrix.json): **67 unique state/viewport checks**, no measured page or
visible-control horizontal overflow. Three directories, direct record creation, extraction, four
Lineage variants, three Details action groups and their More menus are covered. Source-based creation
has four additional desktop/mobile checks. Full-page form backgrounds measure transparent.
Directory identities use the expected serif/normal weight and scientific-name italics while actions
and operational metadata retain sans. The Plant harvest primary link uses readable on-primary text.

Direct create/extract cover 1440×844, 1024×844, 390×844 and effective 1152×675, 960×563 and 819×675
viewport proxies. Directories, Lineage and action groups/More cover the three unscaled sizes.
**Actual 125%/150% browser zoom is not certified**: that control is unavailable in this browser tool.
Mobile Lineage has viewport and supplemental full-page captures so the complete ordered path is visible.

[Navigation observations](navigation.json) cover Dashboard Quick add Back to each category, extraction
Back/Cancel to the exact source Lineage tab with Extract focus, source-operation Cancel, menu keyboard
navigation/Escape and the existing blocked reversal dialog/focus return. No real mutation was submitted.
The preserved fixture has no extracted individual Plant; the explicit four-node extracted path is
covered by authoritative-shaped unit fixtures, not claimed as live fixture evidence.

## Focused checks

From `frontend/`, using the existing Vitest configuration and timeouts:

```sh
node node_modules/vitest/vitest.mjs run --configLoader runner src/sowings/SowingScreen.test.tsx src/lineage/LineagePanel.test.tsx src/propagation/CreationReversal.test.tsx src/components/CollectionUI.test.tsx --maxWorkers=1
node node_modules/vitest/vitest.mjs run --configLoader runner src/App.test.tsx src/App.lazy.test.tsx src/App.transition.test.tsx src/propagation/GuidedForms.test.tsx src/components/recordNavigation.test.ts --maxWorkers=1
node node_modules/vitest/vitest.mjs run --configLoader runner src/seed-lots/SeedLotScreen.test.tsx src/plants/PlantScreen.test.tsx src/photos/PhotosSection.test.tsx src/photos/RecordVisual.test.tsx src/media/MediaScreen.test.tsx src/bulk/BulkLocation.test.tsx src/components/FormSections.test.tsx src/seed-lots/ReferencePicker.test.tsx src/seed-lots/PartialDateField.test.tsx --maxWorkers=1
node node_modules/vitest/vitest.mjs run --configLoader runner src/plants/PlantScreen.test.tsx --maxWorkers=1
npm run build
```

Final distinct result: **318 tests / 18 files passed** across bounded runs: core 49 / 4 files,
App/navigation/guided 89 / 5, eight clean regression files 124, and final isolated Plant 56.
The nine-file regression attempt initially had one immediate-focus assertion fail in Plant; all eight
other files passed. A later Plant run caught a duplicate inactive-source alert after a server conflict
and a second opening's focus race. The extra route-level alert is now limited to unopened extraction;
focus tests wait for the required existing heading focus before editing. Final Plant repeats the whole
file. Assertions for payloads, exact quantities, 409 preservation, confirmation and CSRF remain.
An earlier Seed run terminated under load and is not counted; its isolated full-file repeat passed 50.
No timeout or validation was weakened. Final ESLint caught two void-arrow style issues in the new
focus waits; automatic brace formatting corrected them, then the file passed lint and Prettier.

All modified/untracked frontend TS/TSX/CSS paths are discovered with `git diff --name-only` plus
`git ls-files --others --exclude-standard`. Prettier checks that exact set; ESLint checks its TS/TSX
subset with `--max-warnings 0`. The production build includes strict `tsc -b` and Vite. Feature graph:
`python3 scripts/check-features.py` reports **105 valid**. `git diff --check` is clean.
Nine whitespace-normalized payload/validation/germination/extraction-summary/reversal-submit helpers
match HEAD. No backend/API/schema/migration/dependency changes or corresponding gates.

Canonical `make feature-verify` was intentionally not run. This is visual-review evidence, not a
delivery receipt. Status stays implemented; operator acceptance and actual browser zoom remain.
All work is unstaged/uncommitted; Review is left running.

## Captures

- [direct plant lineage 1440 100](direct-plant-lineage-1440-100.jpg)
- [direct plant lineage 390 100](direct-plant-lineage-390-100.jpg)
- [direct plant lineage 390 full](direct-plant-lineage-390-full.jpg)
- [extract plant 1440 100](extract-plant-1440-100.jpg)
- [extract plant 390 100](extract-plant-390-100.jpg)
- [group actions 1440 100](group-actions-1440-100.jpg)
- [group actions 390 100](group-actions-390-100.jpg)
- [group create 1440 100](group-create-1440-100.jpg)
- [group create 390 100](group-create-390-100.jpg)
- [group lineage 1440 100](group-lineage-1440-100.jpg)
- [group lineage 390 100](group-lineage-390-100.jpg)
- [group lineage 390 full](group-lineage-390-full.jpg)
- [group more 1440 100](group-more-1440-100.jpg)
- [group more 390 100](group-more-390-100.jpg)
- [plant actions 1440 100](plant-actions-1440-100.jpg)
- [plant actions 390 100](plant-actions-390-100.jpg)
- [plant create 1440 100](plant-create-1440-100.jpg)
- [plant create 390 100](plant-create-390-100.jpg)
- [plant from sowing 1440 100](plant-from-sowing-1440-100.jpg)
- [plant from sowing 390 100](plant-from-sowing-390-100.jpg)
- [plant lineage 1440 100](plant-lineage-1440-100.jpg)
- [plant lineage 390 100](plant-lineage-390-100.jpg)
- [plant lineage 390 full](plant-lineage-390-full.jpg)
- [plant more 1440 100](plant-more-1440-100.jpg)
- [plant more 390 100](plant-more-390-100.jpg)
- [plants directory 1024 100](plants-directory-1024-100.jpg)
- [plants directory 1440 100](plants-directory-1440-100.jpg)
- [plants directory 390 100](plants-directory-390-100.jpg)
- [seeds directory 1024 100](seeds-directory-1024-100.jpg)
- [seeds directory 1440 100](seeds-directory-1440-100.jpg)
- [seeds directory 390 100](seeds-directory-390-100.jpg)
- [sowing actions 1440 100](sowing-actions-1440-100.jpg)
- [sowing actions 390 100](sowing-actions-390-100.jpg)
- [sowing create 1440 100](sowing-create-1440-100.jpg)
- [sowing create 390 100](sowing-create-390-100.jpg)
- [sowing from seed 1440 100](sowing-from-seed-1440-100.jpg)
- [sowing from seed 390 100](sowing-from-seed-390-100.jpg)
- [sowing lineage 1440 100](sowing-lineage-1440-100.jpg)
- [sowing lineage 390 100](sowing-lineage-390-100.jpg)
- [sowing lineage 390 full](sowing-lineage-390-full.jpg)
- [sowing more 1440 100](sowing-more-1440-100.jpg)
- [sowing more 390 100](sowing-more-390-100.jpg)
- [sowings directory 1024 100](sowings-directory-1024-100.jpg)
- [sowings directory 1440 100](sowings-directory-1440-100.jpg)
- [sowings directory 390 100](sowings-directory-390-100.jpg)
