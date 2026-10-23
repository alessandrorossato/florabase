# CONTROLS-001 implementation handoff

23 October 2026. Combined candidate: `feat/themes-001` in
`/home/alessandro/.codex/worktrees/b64e/florabase`, currently at integration commit
`1a712ca7d01ee7705433f98622ae625cd228be82`. The operator approved one implementation branch,
combined visual review and one protected PR. THEMES-001 and CONTROLS-001 remain **implemented**;
canonical FULL verification and protected delivery are in progress.

[Live authenticated review](http://localhost:15174/#/settings) ·
[Product screenshot gallery](review/controls-001/gallery.html) ·
[Evidence notes](review/controls-001/README.md) · [Themes handoff](themes-001-handoff.md).

## Origins integration update

The local integration merge reconciles reviewed implementation `564f479ef2c6dc657fc213d2f9636ddac9ccd590`
(original base `b3f1de4693f50a12396344d251a16a0b4ded4b92`) with delivered main
`46ade479fb3955b1d020a321c8256211cd2af869` (MAPS-ORIGINS-001, PR #119).
See [integration evidence and checks](review/controls-001/origins-integration/README.md).
The original handoff below records the earlier implementation phase; its uncommitted/delivery-boundary
statements are historical. The integrated candidate is committed locally for renewed independent QA.
Both Themes and Controls remain implemented; the canonical FULL gate and delivery are pending.

## Shared architecture and action hierarchy

- `Icon.tsx`: one local, typed SVG action vocabulary, without another dependency. Decorative,
  nonfocusable 24-unit view boxes, 18px toolbar/20px shell size, 1.75 round strokes and `currentColor`.
  Search, funnel Filters, bookmark Saved views, add, edit, More, print, refresh, download, back,
  clear selection, layers, chevrons and appearance/navigation glyphs have canonical mappings.
- `Action.tsx`: native `ActionButton`, real-anchor `ActionLink` and labelled `IconButton`. Refs,
  disabled/busy states, native props, callbacks and modified-click link behavior survive adapters.
  Primary/secondary/quiet/danger presentation uses the existing semantic button roles. Leading and
  trailing icon slots align independently from the label; Quick add stays one 44px row.
- `controls.css`: minimum 44px targets, 8px icon/label gap, shared radius/type and theme colors.
  Icon-only secondary actions have accessible names and Tooltip. Visible labels return at ≤48rem
  and on coarse/no-hover devices; mobile Appearance is always labelled. No essential action is
  removed to fit a toolbar. Wrapping preserves the existing page layout.
- Creation, Save, destructive confirmation and domain-sensitive operations retain readable text.
  Filters and Saved views remain labelled at every width. Active-filter badges retain dimension
  counts; Dashboard now counts the selected kinds as one restricting dimension, without changing
  its selected kinds, query, persistence or filtering behavior.

Settings now uses a recognizable **horizontal sliders** glyph, distinct from funnel Filters and the
monitor/sun/moon Appearance control. Both Settings destinations retain their visible label, native
anchor, accessible name, focus and route behavior. The functioning THEMES preference store/cycler
is preserved; custom Tooltip replaces native title on the appearance trigger.

## Tooltip, overlays and keyboard behavior

`Tooltip.tsx` accepts one native trigger with its own accessible name and a concise text description.
A nonfocusable `display: contents` wrapper observes interaction without replacing child refs or event
handlers. No additional tab stop or interactive tooltip content is introduced.

- Fine-pointer hover opens after 500ms; keyboard focus-visible opens immediately. A 150ms leave
  window allows moving onto the tooltip. It stays while trigger or tooltip remains hovered/focused.
- Activation closes the tooltip before the native action. Escape closes and suppresses reopening
  until the next hover/focus cycle. Blur/leave, hidden/inert/disconnected or scrolled-out triggers
  dismiss without moving focus. Timers, observers and listeners are cleaned up.
- `role="tooltip"` and a stable ID supplement the trigger through `aria-describedby` while visible.
  Existing description IDs are retained and restored on dismissal. The actual trigger owns focus,
  visible focus styling and the action name; native disabled controls stay disabled.
- `controlLayers.ts` coordinates Escape: Tooltip, then menu, then dialog. Native `cancel` also checks
  child layers. Menu focus return and dialog dismissal guards remain in their existing owners.
- Native manual popover puts Tooltip above modal clipping without taking focus or light-dismissing
  another surface. The portal stays in the current dialog subtree. A dialog-local fixed overlay host
  supplies the fallback, outside inner scrollers; viewport placement flips/shifts with an 8px inset
  and visual-viewport resize/scroll tracking. Root controls use the corresponding root host.
- Touch activation performs the action once and does not require a first tap to reveal a description.
  Visible labels provide the no-hover alternative. Tooltips contain no essential-only information.
  There is no animation; existing reduced-motion policy and forced-colors system roles apply.

Browser fixture evidence separately proves native modal top-layer placement, a fallback tooltip
extending outside the modal boundary with a successful visible hit test, ordered Escape and scrolling
out dismissal. Unit tests cover fine-pointer delays/transfer, keyboard descriptions, refs and one-tap
activation. This is implementation evidence, not screen-reader or physical-touch certification.

## Consumer inventory and boundaries

| Surface | Shared adoption |
| --- | --- |
| PageHeader / DirectoryTools | Existing slots retained; labelled filter/bookmark/add tools, active chips, canonical close icons and drawer actions. |
| Search / Activity / Dashboard | One DirectorySearch presentation with search SVG; original labels, IDs, callbacks and existing limits retained. Dashboard Quick add remains a labelled chooser with a trailing chevron. |
| Saved Views | Labelled entry, existing compact dialog, native save/restore/delete workflows and explicit destructive text. |
| OverflowMenu | Canonical More secondary trigger; custom creation/bulk choosers keep visible labels. Original grouped actions, links, arrows and focus return remain. |
| Collection / Quick Preview / detail | Shared Edit, Back, Print and creation actions across Seeds, Sowings, Plants, Harvests, Stored material and Locations. Domain operations retain text and callbacks. |
| Activity / references / Sourcing / media | Journal, History, Schedule, identities, Suppliers, Orders, Geography and Media reuse the same actions/search/menus. |
| Dialogs / drawers / forms | Shared close/Done and labelled action adapters; layered dismissal integrated into TaskDialog without changing dirty/pending domain protection. |
| Settings / shell / mobile | Shared sliders, appearance and navigation glyphs; actual preference behavior retained; mobile labels and navigation destinations remain. |
| Maps / Labels / Import-Export | Labelled existing back/add/edit/print/download/refresh actions where present; native Leaflet zoom targets are 44px. Existing provider/evidence actions remain explicit. |

Not every SVG is an action icon: botanical/record placeholders, maps/geography/evidence graphics,
QR and physical label artwork retain their owning implementations. Leaflet's native plus/minus zoom
symbols remain renderer-owned. No invented map layer selector, provider request, raster recoloring,
record mutation, route change, schema/API/backend change, icon dependency or unrelated page layout
normalization is included. Existing THEMES sources, approved palettes and original 143 PNG review
artifacts are preserved. Remaining-page normalization follows this combined review.

## Six themes and responsive evidence

[113 authenticated product captures](review/controls-001/gallery.html) cover all six approved variants.
Seeds/Quick Preview and filter-drawer Tooltip each have six variants at actual 1440×844, 1024×844 and
390×844 layout viewports; mobile navigation has six phone variants. Desktop series cover Dashboard,
Saved Views, seed detail, botanical identities, Orders, Collection origins, Settings and supplier menu.
Mineral Dark spot checks cover the remaining Collection/Activity/Explore families, Labels and
Import/Export; additional Dashboard phone/tablet and labelled creation-menu captures are included.
Three clearly separated component-fixture images cover native/fallback modal and scroller behavior.

Measured canonical icons are 18/20px with 1.75 strokes; measured migrated actions meet 44px targets.
Captured roots have no horizontal viewport overflow. All 30 open product Tooltip measurements pass
text ≥4.5:1 and border ≥3:1 against their actual computed surfaces, and center-point hit tests confirm
visibility. Shared button, muted/icon and focus color pairs remain covered by the existing six-theme
production token tests. See [calculated checks](review/controls-001/evidence-check.json).

Measurements describe layout viewports, not necessarily exported image dimensions. The in-app
browser sometimes scales screenshot exports on scrolling pages; JSON and gallery captions record
bitmap dimensions separately. Images were not upscaled and are not browser-zoom proxies. Early
Controls captures precede the final Hide-navigation label and Quick-add alignment refinements;
new Dashboard and utility captures show the final source. Historical Themes captures remain historical.

A settled actual Settings reload retains Botanical/System and resolved Dark, including the checked
System radio and matching footer name. Earlier cross-tab captures exercise the same production
preference store. Browser evidence does not certify a throttled cold first-paint filmstrip.

## Verification and review status

- Before Controls: 13/13 focused baseline checks passed. The historical THEMES-only 850 result is
  preserved separately and is not claimed as Controls coverage.
- Complete combined frontend run: **859/859 tests in 75 files passed**, zero failures/skips. The
  preceding run exposed two obsolete test expectations/helpers, fixed without weakening behavior.
- Two later visual refinements added the Hide-navigation Tooltip and corrected the Quick-add trailing
  chevron slot. All **82 App cases** passed after the navigation refinement. A fresh final focused run
  passed **63/63** in ten files, including all **9 Controls** cases, Themes/Settings, Saved Views,
  DirectoryTools, menu interactions, Dashboard and external botanical data. The complete 859 run
  predates those two refinements; it is not an exact-final-tree canonical receipt.
- Final-source `pnpm typecheck`, full `pnpm lint` (zero warnings), `pnpm format:check` and
  `pnpm build` passed. Vite transformed **219 modules**; the built bootstrap precedes the module bundle.
  This is a frontend production build, not deployment or production-container certification.
- Feature graph: **110 valid**. `git diff --check` passed; index remains empty. Raw frontend reports
  are under ignored `frontend/coverage/controls-*.json` and `.log`; portable totals are in
  [test-results.json](review/controls-001/test-results.json). No assertions or timeouts were weakened.
- No backend/API/schema changes justify backend/integration reruns in this phase. Canonical
  `make feature-verify` / `make verify-full` were explicitly excluded and were not run. Neither feature
  is marked verified and no exact-tree receipt is claimed. Later authorized QA must gate the final tree.

## Review runtime and acceptance limits

Ownership was inspected before use/restoration. The earlier authorized data-preserving split remains:
current `b64e` frontend `florabase-themes-review-frontend` in its exact Quality project
`florabase-quality-ab1b459cfd98`, bound only to loopback 15174, proxies to retained `c902` Review
backend/database/media. Production backend source still matches the candidate base; no foreign
frontend/workflow edits were copied. At handoff the candidate frontend and retained backend/database
are running and healthy. The authenticated fixture session survives restoration.

The source-labelled volume checks in `scripts/workflow_environment.py` refuse another checkout's
Review ownership. `make feature-review-status` therefore still reports source mismatch. The current
helper has no non-destructive source-label transfer path; deleting data to satisfy it is unacceptable.
This split permits combined frontend visual review against a matching backend, **but does not pass a
supported full Review ownership handover or production-runtime smoke**. Keep this operational limit
explicit in acceptance and later canonical QA. No infrastructure workaround is delivered here.

After the runtime stopped between sessions, only the exact retained backend was started and this
candidate's isolated frontend runner restored/reconnected. Existing database/media were not deleted,
recreated, copied, reseeded or migrated; owner credentials were not changed. DEV, UAT, Stable Preview,
production, the primary checkout and other branches were not modified. Temporary review harness files
were removed before final lint/format/build; production routes do not expose a Controls specimen page.

Remaining acceptance: independent combined visual sign-off; real assistive technology and physical
coarse/touch devices; actual browser zoom 125%/150% and 320px reflow; OS forced-colors/reduced-motion
inspection; downloaded GBIF raster; throttled cold first-paint filmstrip; native print dialog, QR and
physical printer output. Synthetic GBIF IDs were not sent to providers for review. Appearance captures
retain Collection origins tile URLs (DOM evidence, not a traffic trace). Later MAPS-ORIGINS integration
still requires reconciliation. These pending checks have not been silently promoted to passing.

All implementation, design and review files remain unstaged and uncommitted for operator review.

`READY_FOR_THEMES_CONTROLS_VISUAL_REVIEW`
