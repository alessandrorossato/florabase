# CERT-02 — frontend certification regressions

Branch `ci/cert-02-frontend-regressions`, writer `carbon-cert02`, created from post-Batch-02
`main` at `836bf80305a19fdd7f49845b8bc00ae423553a93`.

This change adds and extends focused frontend certification regressions for `UX-002`, `MAP-001`,
and `BOTANICAL-IDENTITIES-VISUAL-001`. No production defects were uncovered, so no production code
was modified. Shared feature-registry status updates (`docs/features.json`) and
`docs/release/scope-v1.json` are left untouched for WF-04 Batch 03 integration reconciliation.

## Acceptance criteria and regression coverage

| Item | Feature & criterion | Test file | Exact test name | Production code path exercised |
| --- | --- | --- | --- | --- |
| A1 | `UX-002` #1 (with #3 negative check): inline contextual help on ambiguous Sowing fields without adding `aria-describedby` chrome to self-explanatory Notes | [`frontend/src/sowings/SowingScreen.test.tsx`](../../../frontend/src/sowings/SowingScreen.test.tsx) | `layered help explains ambiguous Sowing fields without adding chrome to Notes` | [`frontend/src/sowings/SowingScreen.tsx`](../../../frontend/src/sowings/SowingScreen.tsx) (`#sowing-seed-lot` → `sowing-seed-lot-help`), [`frontend/src/sowings/SowingFormFields.tsx`](../../../frontend/src/sowings/SowingFormFields.tsx) (`Quantity sown` fieldset → `sowing-quantity-help`, `#sowing-location` → `sowing-location-help`, `#sowing-notes` without `aria-describedby`), [`frontend/src/components/ContextualHelp.tsx`](../../../frontend/src/components/ContextualHelp.tsx) (`FieldHelp`) |
| A1 | `UX-002` #1 (with #3 negative check): inline contextual help on Plant location, supplier, and material provenance without adding chrome to Notes | [`frontend/src/plants/PlantScreen.test.tsx`](../../../frontend/src/plants/PlantScreen.test.tsx) | `layered help explains Plant location, supplier and provenance` | [`frontend/src/plants/PlantFormFields.tsx`](../../../frontend/src/plants/PlantFormFields.tsx) (`#plant-location` → `plant-location-help`, `#plant-notes` without `aria-describedby`), [`frontend/src/plants/PlantScreen.tsx`](../../../frontend/src/plants/PlantScreen.tsx) (`#plant-supplier` → `plant-supplier-help`, `#plant-provenance` → `plant-provenance-help`), [`frontend/src/components/ContextualHelp.tsx`](../../../frontend/src/components/ContextualHelp.tsx) (`FieldHelp`) |
| A1 | `UX-002` #1 (with #3 negative check): inline contextual help on Journal phenological stage explaining recorded-only evidence | [`frontend/src/plants/PlantScreen.test.tsx`](../../../frontend/src/plants/PlantScreen.test.tsx) | `Journal phenology stage explains recorded-only evidence` | [`frontend/src/events/EventJournal.tsx`](../../../frontend/src/events/EventJournal.tsx) (`#event-stage-<targetId>` → `event-stage-help-<targetId>`, `#event-notes-<targetId>` without `aria-describedby`), [`frontend/src/components/ContextualHelp.tsx`](../../../frontend/src/components/ContextualHelp.tsx) (`FieldHelp`) |
| A2 | `MAP-001` #3: runtime configuration of OpenStreetMap-compatible tile URL, attribution, and online flag | [`frontend/src/provenance-map/config.test.ts`](../../../frontend/src/provenance-map/config.test.ts) | `runtime config tile URL and attribution are used when set, trimmed, and fall back when blank` | [`frontend/src/provenance-map/config.ts`](../../../frontend/src/provenance-map/config.ts) (`window.__FLORABASE_RUNTIME_CONFIG__`, `configured()`, `mapRuntimeConfig`) |
| A2 | `MAP-001` #3: configured tile URL and attribution passed to Leaflet `tileLayer` when Online basemap is enabled | [`frontend/src/provenance-map/ProvenanceMap.test.tsx`](../../../frontend/src/provenance-map/ProvenanceMap.test.tsx) | `configured tile URL and attribution reach Leaflet` | [`frontend/src/provenance-map/ProvenanceMap.tsx`](../../../frontend/src/provenance-map/ProvenanceMap.tsx) (`tileLayer(mapRuntimeConfig.tileUrl, { attribution: mapRuntimeConfig.attribution, referrerPolicy: "strict-origin-when-cross-origin" })`) |
| A3 | `BOTANICAL-IDENTITIES-VISUAL-001` #8: identity History tab renders linked recorded events once in API order, with Harvest and source links, preserved `PartialDate` precision, documented sowing/germination gaps, directory links, and empty state | [`frontend/src/botanical-identities/IdentityHistory.test.tsx`](../../../frontend/src/botanical-identities/IdentityHistory.test.tsx) | `identity History lists linked recorded events once, newest first, with Harvest links, precision and documented gaps` | [`frontend/src/botanical-identities/BotanicalIdentityScreen.tsx`](../../../frontend/src/botanical-identities/BotanicalIdentityScreen.tsx) (`#panel-history`, `Recorded history`, gap note, `identityDirectory("sowings" \| "harvests", identity.id)`, `EventFeed`), [`frontend/src/events/EventFeed.tsx`](../../../frontend/src/events/EventFeed.tsx), [`frontend/src/botanical-identities/identityNavigation.ts`](../../../frontend/src/botanical-identities/identityNavigation.ts) |
| A3 | `BOTANICAL-IDENTITIES-VISUAL-001` #5: Sowings and Plants botanical-identity directory filters survive browser Back and Forward navigation | [`frontend/src/sowings/SowingScreen.test.tsx`](../../../frontend/src/sowings/SowingScreen.test.tsx), [`frontend/src/plants/PlantScreen.test.tsx`](../../../frontend/src/plants/PlantScreen.test.tsx) | `identity-scoped Sowings uses the actual SeedLot identity and retains text search`, `identity scope composes with the Plants ownership model and separate group type` | [`frontend/src/saved-views/useDirectoryView.ts`](../../../frontend/src/saved-views/useDirectoryView.ts), [`frontend/src/saved-views/state.ts`](../../../frontend/src/saved-views/state.ts), [`frontend/src/sowings/SowingScreen.tsx`](../../../frontend/src/sowings/SowingScreen.tsx), [`frontend/src/plants/PlantScreen.tsx`](../../../frontend/src/plants/PlantScreen.tsx) |

## Focused checks

Run from the `ci/cert-02-frontend-regressions` worktree and its isolated Quality container:

- `pnpm vitest run src/provenance-map/config.test.ts src/provenance-map/ProvenanceMap.test.tsx src/botanical-identities/IdentityHistory.test.tsx src/sowings/SowingScreen.test.tsx src/plants/PlantScreen.test.tsx`: 5 test files, 130 tests passed (`config.test.ts` 1, `ProvenanceMap.test.tsx` 9, `IdentityHistory.test.tsx` 1, `SowingScreen.test.tsx` 39, `PlantScreen.test.tsx` 80).
- `make format-check`: ruff format check and `pnpm format:check` passed.
- `make lint`: ruff check and `pnpm lint` passed.
- `make typecheck`: mypy and `pnpm typecheck` passed.
- `make verification-plan`: exits 0; base `836bf80305a19fdd7f49845b8bc00ae423553a93`, tier `product` (changed scopes `identity`, `plants`, `sowings`; shared product paths under `frontend/src/provenance-map/`), static checks `feature-graph`, `whitespace`, `format-check`, `lint`, `typecheck`, `api-check`.
- `python3 scripts/check-features.py`: 163 valid feature entries.
- `python3 scripts/check-doc-links.py`: passed.
- `python3 scripts/test-beta-runtime.py Disclosure -q`: 63 disclosure tests passed.
- `git diff --check`: clean.

## Independent review

Independent read-only QA reviewer: `hydrogen-qa-cert02` (from an isolated scratch export, separate
from the writer).

| Reviewed commit | Verdict | Notes |
| --- | --- | --- |
| `cf5abaa2c0d5d9d1a82beb9caf63b7debda5576f` | PASS | Zero defects; all eight new and extended regression tests passed on the unmodified archive export and failed under targeted production mutations (A1 Sowing/Plant/Journal help descriptions, A2 `config.ts` trimming/fallback and `ProvenanceMap.tsx` `tileLayer` arguments, A3 `BotanicalIdentityScreen.tsx` History event ordering and `useDirectoryView.ts` `identity_id` navigation sync). |

The commit that records this verdict updates only `docs/release/evidence/cert-02.md` and
`docs/progress.md`; its delta QA verdict is provided with the frozen source tip.
