# Consolidated SeedLot / Dashboard refinement

Source: `/home/alessandro/.codex/worktrees/996d/florabase`, branch `feat/global-visual-001`, base HEAD
`cd63c185f7bcb0544cd9c3cff984b29564e6bc84` plus dirty/uncommitted live source. Review is
http://localhost:15174, with the existing owner/session, revision `20261013_0042` and managed fixture
v4/66 ready. Existing operator-created records remain present.

## Live responsive evidence

The matrix has ten states, each at six CSS viewport sizes: `dashboard`, `seeds-preview`,
`edit-from-preview`, `acquisition-linked`, `acquisition-no-order`, `seed-overview`, `seed-gallery`,
`edit-from-details-focus`, `edit-first-tab-focus`, `seed-lineage-root`.

| File suffix    | CSS viewport | Meaning                    |
| -------------- | ------------ | -------------------------- |
| 1440-100       | 1440x844     | Normal desktop             |
| 1440-125-proxy | 1152x675     | Effective-space proxy only |
| 1440-150-proxy | 960x563      | Effective-space proxy only |
| 1024-100       | 1024x844     | Narrower desktop           |
| 1024-125-proxy | 819x675      | Effective-space proxy only |
| 390-100        | 390x844      | Mobile                     |

These are **not actual browser zoom captures**. Actual 125%/150% zoom remains operator acceptance.
The browser may omit scrollbars/scale its screenshot canvas; `responsive-probes.json` records the
actual requested CSS viewport and layout geometry. The app's existing responsive sidebar behavior
also adapts while resizing. Temporary viewport overrides were reset.

The 60 retained probes have no horizontal document overflow. Repeated pre-fix measurements were
replaced with the latest observation per state/viewport; missing data was not reconstructed.
At 1440x844, the linked and no-Order panels have equal client/scroll heights of 414px. Earlier
inherited fieldset/legend/action spacing caused avoidable scrolling; scoped fixes remove it. Shorter
viewports scroll panels with actions visible. The no-Order captures use the existing purchased lot
without an Order; an earlier unsaved unlink separately demonstrated retained Supplier knowledge.

Dashboard shows all high-value sections and its populated wide filter drawer fits at normal desktop.
Seeds and the read-only Sowings reference share the 1.3fr/0.8fr split. Details uses the available width
and normal gutters; Overview retains natural-height primary context beside one facts surface.
The first gallery tile spans approximately y344-627 at 1440x844, with entity header/tabs/tools above.
Mobile naturally scrolls to the gallery; its action menu remains inside the usable viewport.

## Interaction evidence

- `interaction-probes.json`: native modal, inert background, body scroll lock, Shift+Tab to Save,
  Tab back to the first editor link, clean Back to the retained Photos tab with Edit focused.
- `edit-from-details-focus-*` and `edit-first-tab-focus-*`: selected first/last editor navigation,
  visible focus rings, wrapped mobile tabs and persistent action rows.
- `pristine-backdrop-return.jpg`: immediate pristine close and return to the directory preview.
  Dirty backdrop produced the discard prompt; its rejection outcome was not captured live. Unit
  tests cover rejection/acceptance and operator confirmation remains appropriate.
- `gallery-keyboard-focus.jpg`, `gallery-keyboard-actions.jpg`, `gallery-mobile-actions.jpg`:
  non-hover access to named overflow, Open, primary, metadata and confirmed-unlink actions.
  Metadata editing was opened and cancelled; no media/primary/unlink operation persisted.
- `gallery-image-details-route.jpg`: image activation opens the exact shared media asset and retained
  metadata. Browser Back returns to Photos.
- `direct-edit-fallback-1440-100.jpg`: fresh authenticated Edit URL is a full-page fallback, no modal.
- `saved-to-gallery-context.jpg`: normal save of unchanged Basil values succeeds, returns to Photos
  and focuses Edit. No fallback reopens. Version/time metadata may update.

After the temporary direct-link tab, the first save met normal CSRF rejection. Cancelling and
reloading the main tab through the ordinary auth flow resolved it. No session/CSRF state was fabricated.
A final missing-history-event regression exposed a contextual-close/fallback timing window; the
entry is now marked handled, and the test also checks that no fallback reopens.

## Siblings and fixture limits

Read-only desktop screenshots cover Sowings directory/preview, History, Settings and Labels. No
Sowings/Plants visual redesign began. QR destination is still unconfigured; printing was not tested.

The reviewed SeedLot has one gallery item and no recorded producer. The seeded external asset is
linked to a Plant. Multi-item/external gallery and producer SeedLot paths have focused tests, not
fresh live captures in this family. No new fixture, media link or inferred ancestry was created to
fill these gaps, and no remote Preview once request was made in live Review.

## Validation and boundaries

`validation.json` records exact suite counts and static checks. Source TypeScript, targeted ESLint,
Prettier, production build and whitespace checks are separate from operator visual acceptance.
The final SeedLot JS chunk is 45.88 kB / 12.31 kB gzip, and main is 227.83 kB / 70.83 kB gzip.
Backend/API/schema code is unchanged in this UI refinement; no new PostgreSQL/migration/API-drift
verification is claimed.

Review remains running. No reset/remove/reseed, persistent UAT/DEV/Stable/production operation,
stage, commit, push, delivery or canonical feature-verify. Feature status remains in_progress.
