# SeedLot dashboard, compact Photos and connected pickers

Candidate: `/home/alessandro/.codex/worktrees/996d/florabase`, branch `feat/global-visual-001`,
base HEAD `cd63c185f7bcb0544cd9c3cff984b29564e6bc84` plus current dirty/uncommitted source.
Authenticated Feature Review: http://localhost:15174.

## Live evidence

The required matrix uses actual **1440×844, 1024×844 and 390×844**, all at 100% / scale 1.
`observations.json` records **30 observations**, all without horizontal document overflow. Full-page
supplemental screenshots retain the requested viewport width; they are not alternate viewport sizes.

| Cases | Coverage |
| --- | --- |
| `overview-populated-*` | Basil: exact stock, linked Order/Supplier, populated activities, notes; all three widths, mobile lower section and full-page supplements |
| `overview-long-origin-*` | Lavender: approximate stock, Gift/exchange, complete long origin path, empty activities, notes; all widths and mobile origin/lower context |
| `photos-populated-*` | Protected local Basil media at all widths, no visible duplicate heading or global helper, right-aligned actions |
| `photos-external-privacy-*` | Existing Lavender external tile at all widths; host/privacy/Preview once retained; no remote img loaded |
| `photos-empty-*` | Genovese gallery placeholder/actions at all widths |
| `picker-identity-*`, `picker-storage-*`, `picker-supplier-*` | All three SeedLot inputs at each requested width: 4px gap, equal control/popup width, bounded menu and internal scroll |
| `order-native-search-390` | Existing searchable native Order choices; query restored without selecting an Order |
| `picker-plant-identity-1440` | Shared picker in the unchanged Plant create flow: 4px gap and aligned width |
| `consumer-sowing-native-1440` | Existing native SeedLot/location controls inspected; no shared popup to change |
| `picker-short-viewport-390x400` | Additional menu-fitting probe only: above-input placement at 4px, menu inside the short viewport |

`picker-before.png` preserves the original 45.984px gap caused by the entire field/help grid serving
as the popup containing block. The shared control-only wrapper fixes the cause. Menu measurement is
live geometry evidence, not a pixel-based regression test. `live-keyboard.json` records Supplier
selection after Arrow/Enter, collapsed state, cleared active descendant and retained input focus.
The temporary selected Supplier was cleared. No product record or media was saved/linked/removed.
No remote image host was contacted. Native date precision, required labeling and full-page Create
remain unchanged. Plant/Sowing forms were inspected only for picker compatibility, not redesigned.

The final viewport override is reset. `operator-ready.png` shows authenticated Lavender Overview at
normal 1280×720. Normal manual login is `owner` with the unchanged Review password.

## Validation

- Baseline: 21 ReferencePicker/Photos tests pass.
- Final: **247 unique tests across 13 files** pass; `test-summary.json` indexes the suites. This includes
  SeedLot facts/links/actions, Photos/Media privacy and failure behavior, shared picker focus/keyboard/
  ARIA state, Order and representative Plant/Sowing/Bulk/Labels consumers.
- One intermediate date whitespace assertion was replaced with individual semantic term/value checks.
  The final SeedLot and ReferencePicker suites pass; no weaker validation or timeout was introduced.
- Strict TypeScript, zero-warning targeted ESLint, eight-file Prettier check, production build and
  whitespace checks pass. `static-checks.json` records their scope. No backend/API/schema change.
- Production JS: SeedLot 45.38 kB / 12.42 kB gzip; main 228.15 kB / 70.91 kB gzip.
- `review-status.txt`: candidate owner, frontend/backend/DB healthy, schema `20261013_0042`, existing
  managed v4/66 ready dataset. No reset/remove/reseed, UAT/DEV/Stable/production operation, canonical
  verification, staging, commit, push or delivery. Candidate remains in_progress and dirty.
