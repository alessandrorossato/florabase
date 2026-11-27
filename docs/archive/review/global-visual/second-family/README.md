# Dashboard / SeedLot second operator refinement

Source: `/home/alessandro/.codex/worktrees/996d/florabase`, branch `feat/global-visual-001`, HEAD
`cd63c185f7bcb0544cd9c3cff984b29564e6bc84` plus live dirty/uncommitted changes. Authenticated Review
at `http://localhost:15174` retains its existing owner, schema `20261013_0042` and v4/66 synthetic data.

## Responsive captures

Each of these states has six `.jpg` captures: `dashboard`, `seed-overview`, `seed-photos`,
`edit-from-details`, `edit-acquisition`, `edit-from-seeds`, `edit-direct-url`.

| Suffix           | Viewport | Scope                            |
| ---------------- | -------- | -------------------------------- |
| `1440-100`       | 1440×844 | Actual desktop viewport          |
| `1024-100`       | 1024×844 | Actual narrower desktop viewport |
| `390-100`        | 390×844  | Actual mobile viewport           |
| `1440-125-proxy` | 1152×675 | Effective-space proxy only       |
| `1440-150-proxy` | 960×563  | Effective-space proxy only       |
| `1024-125-proxy` | 819×675  | Effective-space proxy only       |

The proxy captures are **not actual browser zoom**. True 125%/150% zoom remains operator acceptance;
no unsupported zoom or page-style injection is used. No horizontal document overflow was observed in the saved probes.
`responsive-probes.json` retains 12 measurements for Dashboard and Seed Overview only; the remaining
30 states/sizes have screenshot evidence, not retained machine-readable geometry. These probes are
not full accessibility acceptance.
Temporary viewport overrides are reset at handoff.

At 1440×844, the first useful media card spans approximately y344–510, with entity header, tabs and
Photos controls above it. Its thumbnail/metadata/actions occupy about 166px height. Arbitrary media
volume and smaller effective viewports may scroll naturally. The new compact variant removes the
old 320px card-width limit locally; default Photos consumers retain their existing composition.

The edit modal is about 960×743 at 1440×844 and 390×844 on mobile. All captured modal action rows
remain within the viewport with 44px Save controls; long panels scroll internally. Mobile's native
top layer covers the inert bottom navigation. The direct full-page fallback uses normal document
scrolling where necessary.

## Interaction / accessibility evidence

`accessibility.json` confirms native `:modal`, explicit inert/aria-hidden background, body/workspace
scroll lock, focus inside the editor, Shift+Tab wrapping to Save and Tab wrapping to the first editor
link. Cancel restores `#/seeds?q=Basil`, search text, the same inspector and its Edit trigger.

`acquisition-scrolled.jpg` shows the intermediate acquisition section. A wheel scroll moved its
panel from 0 to 604px while document/workspace scroll positions stayed at 0. These Acquisition captures precede the final scoped checkbox alignment rule; browser control
subsequently refused the retained tab under its URL policy, so that styling change has no refreshed
screenshot. Known linked Supplier
is read-only; acquisition date remains Unknown independently of the recorded Order date.

`saved-to-photos-context.jpg` shows a normal authenticated save of the fixture's unchanged values,
returning to Photos with Edit focused. This normal save may update version/time metadata. No new
Order, media upload, primary change or unlink was performed in live Review. Existing ownership,
session behavior and fixture ledger were retained; no CSRF/session state was fabricated.

A live Save exposed event-order differences missed by the initial tests. Explicit completion now
closes the editor immediately and the parsed App route also owns Back closure; both hash/pop guards
remain for dirty departures. The actual invoking Edit button is passed to TaskDialog for reliable
focus return. Live Back now returns to the retained Photos tab with Edit focused. Additional tests
cover missing history events/click focus and guarded editor links. `returned-to-seeds-context.jpg`
records directory-context return. Direct edit URL captures have no fabricated modal background.

## Validation scope

Core suites cover SeedLot, Dashboard, Photos, purchase-context UI and Orders. Shared regressions
cover FormSections, TaskDialog/Reference interactions, bulk moves and Dashboard search. Final counts
and static/build results are recorded in the handoff; raw test reports are summarized without
credentials. Earlier normalization/first-family evidence is historical and does not prove this pass.

Review services stopped during an interruption. Recovery used only guarded `make feature-review-up`;
revision 0042 and the existing owner/dataset remain. No reset/remove/reseed or UAT operation ran.
No canonical `make feature-verify`, stage, commit, push or delivery is claimed.
