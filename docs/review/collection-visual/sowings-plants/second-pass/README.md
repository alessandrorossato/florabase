# COLLECTION-VISUAL-001 — second-pass evidence

This is historical second-pass evidence, superseded by the [third-pass index](../third-pass/README.md).
The operator did not accept this pass. Its checks and hashes do not verify the current source. See the [current handoff](../../../../collection-visual-001-handoff.md).

Candidate: `ef73`, `feat/collection-visual-001`, base `1e3df6a` plus unstaged source.
Review: [localhost:15174](http://localhost:15174), existing fixture v4/66, revision 20261013_0042.
No reset/reseed, collection writes, reversal submission or persistent-environment operation occurred.

[Responsive matrix](responsive-matrix.json): **90 unique state/viewport checks**, no measured page or
visible-control horizontal overflow. Create/Edit include 1440×844, 1024×844, 390×844 and effective
1152×675 / 960×563 / 819×675 zoom proxies. These do not certify actual 125%/150% browser zoom.
Directory, selection and canonical Overview/Lineage checks include all three unscaled sizes.
Representative screenshots are viewport captures, so long mobile pages may extend beyond the image.

The normal 1440 Origin editors fit without inner scrolling; reduced heights retain internal scroll
and stable actions. Desktop Sowing Overview ends near 789px, Plant near 702px, PlantGroup near 861px.
Sowing preview pairs match at 196×44px (1440) and 114×62px (1024). Plant preview media uses the
Botanical Identity 12rem container and scale-down to avoid enlarging small protected thumbnails.
The blocked reversal dialog restores its trigger's focus. Eligible/confirmation behavior is tested
with authoritative-shaped responses; v4 records shown live have no reversible creation receipt.

Final focused tests: **223 / 13 files passed**. From `frontend/`:

```sh
node node_modules/vitest/vitest.mjs run --configLoader runner src/seed-lots/SeedLotScreen.test.tsx --maxWorkers=1
node node_modules/vitest/vitest.mjs run --configLoader runner src/plants/PlantScreen.test.tsx --maxWorkers=1
node node_modules/vitest/vitest.mjs run --configLoader runner src/sowings/SowingScreen.test.tsx src/propagation/CreationReversal.test.tsx src/propagation/GuidedForms.test.tsx --maxWorkers=1
node node_modules/vitest/vitest.mjs run --configLoader runner src/photos/PhotosSection.test.tsx src/photos/RecordVisual.test.tsx src/lineage/LineagePanel.test.tsx src/media/MediaScreen.test.tsx src/bulk/BulkLocation.test.tsx src/components/FormSections.test.tsx src/seed-lots/ReferencePicker.test.tsx src/seed-lots/PartialDateField.test.tsx --maxWorkers=1
npm run build
```

Counts: SeedLot 49, Plant 52, core Sowing/reversal/guided 44, shared 78. Existing payload, validation,
seed-usage review, reversal CSRF/confirmation/409/history and direct-link assertions remain. Initial
failures identified obsolete row-context/create-tab expectations; those tests now assert the same
facts in Preview or page sections. No timeout, backend assertion or validation was weakened.

Static checks use all modified/untracked frontend TS/TSX/CSS files, discovered with `git diff
--name-only` plus `git ls-files --others --exclude-standard`: Prettier check on that exact set,
ESLint `--max-warnings 0` on its TS/TSX subset. Production build includes strict `tsc -b` and Vite.
A typed test query and void-handler lint issues were corrected before final passes. Feature graph:
`python3 scripts/check-features.py` reports 105 valid; `git diff --check` passes. Whitespace-normalized
comparison against HEAD confirms Sowing/Plant payload/validation, germination denominator logic and
the CreationReversal submit function are unchanged. No backend/API/migration/dependency edits or
corresponding gates. Canonical `make feature-verify` was not run; this is not a delivery receipt.

## Screenshots

- [group create 1440 100](group-create-1440-100.jpg)
- [group create 390 100](group-create-390-100.jpg)
- [group edit 1440 100](group-edit-1440-100.jpg)
- [group edit 390 100](group-edit-390-100.jpg)
- [group lineage 1440 100](group-lineage-1440-100.jpg)
- [group lineage 390 100](group-lineage-390-100.jpg)
- [group overview 1440 100](group-overview-1440-100.jpg)
- [group overview 390 100](group-overview-390-100.jpg)
- [group preview 1024 100](group-preview-1024-100.jpg)
- [group preview 1440 100](group-preview-1440-100.jpg)
- [plant create 1440 100](plant-create-1440-100.jpg)
- [plant create 390 100](plant-create-390-100.jpg)
- [plant edit 1440 100](plant-edit-1440-100.jpg)
- [plant edit 390 100](plant-edit-390-100.jpg)
- [plant from sowing lineage 1440 100](plant-from-sowing-lineage-1440-100.jpg)
- [plant from sowing lineage 390 100](plant-from-sowing-lineage-390-100.jpg)
- [plant lineage 1440 100](plant-lineage-1440-100.jpg)
- [plant lineage 390 100](plant-lineage-390-100.jpg)
- [plant overview 1440 100](plant-overview-1440-100.jpg)
- [plant overview 390 100](plant-overview-390-100.jpg)
- [plant preview 1024 100](plant-preview-1024-100.jpg)
- [plant preview 1440 100](plant-preview-1440-100.jpg)
- [plant primary photo preview 1440 100](plant-primary-photo-preview-1440-100.jpg)
- [plants directory 1024 100](plants-directory-1024-100.jpg)
- [plants directory 1440 100](plants-directory-1440-100.jpg)
- [plants directory 390 100](plants-directory-390-100.jpg)
- [plants selection 390 100](plants-selection-390-100.jpg)
- [reversal blocked 1024 100](reversal-blocked-1024-100.jpg)
- [reversal blocked 1440 100](reversal-blocked-1440-100.jpg)
- [reversal blocked 390 100](reversal-blocked-390-100.jpg)
- [seed lineage empty 1440 100](seed-lineage-empty-1440-100.jpg)
- [seed photos empty 1440 100](seed-photos-empty-1440-100.jpg)
- [seed sowings empty 1440 100](seed-sowings-empty-1440-100.jpg)
- [seeds directory 1024 100](seeds-directory-1024-100.jpg)
- [seeds directory 1440 100](seeds-directory-1440-100.jpg)
- [seeds directory 390 100](seeds-directory-390-100.jpg)
- [seeds selection 390 100](seeds-selection-390-100.jpg)
- [sowing create 1440 100](sowing-create-1440-100.jpg)
- [sowing create 390 100](sowing-create-390-100.jpg)
- [sowing edit 1440 100](sowing-edit-1440-100.jpg)
- [sowing edit 390 100](sowing-edit-390-100.jpg)
- [sowing lineage 1440 100](sowing-lineage-1440-100.jpg)
- [sowing lineage 390 100](sowing-lineage-390-100.jpg)
- [sowing overview 1440 100](sowing-overview-1440-100.jpg)
- [sowing overview 390 100](sowing-overview-390-100.jpg)
- [sowing photos empty 1440 100](sowing-photos-empty-1440-100.jpg)
- [sowing photos empty 390 100](sowing-photos-empty-390-100.jpg)
- [sowing preview 1024 100](sowing-preview-1024-100.jpg)
- [sowing preview 1440 100](sowing-preview-1440-100.jpg)
- [sowings directory 1024 100](sowings-directory-1024-100.jpg)
- [sowings directory 1440 100](sowings-directory-1440-100.jpg)
- [sowings directory 390 100](sowings-directory-390-100.jpg)
- [sowings selection 390 100](sowings-selection-390-100.jpg)
