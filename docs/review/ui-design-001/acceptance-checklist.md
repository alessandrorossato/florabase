# Visual acceptance and public screenshots

**Status: PROPOSED / AWAITING DESIGN APPROVAL.** This checklist applies to future implementation phases and the release screenshot set. Nothing here has been checked against an implementation yet. Items that depend on D1–D6 apply only once those are decided.

## Per page (every phase)

- [ ] Breadcrumb, then title (`h2`, `type-h1`; 22px below 48rem), then one-sentence subtitle. No row above the breadcrumb.
- [ ] Exactly one filled primary visible per surface. Edit is secondary with the icon. Danger appears only inside a confirmation.
- [ ] Action labels are sentence case, verb + object. No typed `←`/`→` in labels.
- [ ] Every lifecycle state is a `LifecycleStatus` chip with its exact word. No pills on controls or chips.
- [ ] Text uses only the nine type styles; no weight 700.
- [ ] Radii are 6/10/14px only. No shadow outside dialogs, drawers, popovers and tooltips.
- [ ] Botanical names: italic serif on the scientific part only; cultivar roman in quotes.
- [ ] Unknown, approximate, zero and partial-date values render honestly. Nothing is fabricated while loading.

## Keyboard and accessibility

- [ ] Tab order follows the visual order. Every focus ring is a 3px solid `focus-ring`, 3px out, or −3px inside scrollports, and is never clipped.
- [ ] A record row's Enter opens Details. Details and Edit are reachable siblings. Back restores focus to the opened row (UI-POLISH-001 owners; EXISTING behavior to preserve).
- [ ] Every dialog: initial focus on the safe control; Escape keeps the draft; focus returns to the trigger; a pending state blocks dismissal.
- [ ] Heading outline: shell `h1`, page or record `h2`, sections `h3`, no skips (QA-8 covered).
- [ ] Touch targets are ≥44px. Icon-only buttons have names and show labels on touch.
- [ ] Re-measure contrast on rendered pixels for text-muted on surface-subtle and border-strong on surface in all six themes.
- [ ] Manual (operator): real 125%/150% browser zoom, VoiceOver or NVDA pass on Plants directory → Details → Edit, a physical phone, and forced colors.

## Responsive

- [ ] 1440, 1024, 768 and 390 CSS px: no page-level horizontal overflow, and long names, paths and cultivars wrap.
- [ ] 390×844: first Plants record in the top half of the viewport; bottom navigation doesn't cover the last row's actions.
- [ ] 1024: Details actions wrap under the title, not beside a squeezed title.
- [ ] UI-FLICKER-001: direct-load and Back/Forward between Plants and Details hold title position (±0 px at 1440 and 1024; the documented breadcrumb-wrap exception at 390).

## Public screenshot set

The design mockups in [mockups/](mockups/README.md) are **never** part of this set; they are not product screenshots.

Capture from a fresh synthetic Review on the delivered main (fixture v4 + Extended v5, labels free of "Review v5 —" prefixes if the operator approves a presentation fixture). Never use owner data, real locations or credentials. Hide review chrome. Use the CSS viewport sizes exactly and record the raster size.

| # | Screen | Viewport | Theme | State shown |
| --- | --- | --- | --- | --- |
| 1 | Dashboard | 1440×900 | Botanical Light | Populated summary and recent facts |
| 2 | Plants directory (List) | 1440×900 | Botanical Light | Active filter chip, mixed lifecycle chips |
| 3 | Plants gallery | 1440×900 | Botanical Dark | Mix of own photos and placeholders |
| 4 | Plant details, Overview | 1440×900 | Botanical Light | Header actions, summary, sections |
| 5 | Plant edit | 1440×900 | Herbarium Light | Grouped sections, one validation error |
| 6 | Discard-changes confirmation | 1440×900 | Botanical Dark | ConfirmDialog over the editor |
| 7 | Seeds directory | 1024×844 | Mineral Light | Exact, approximate and unknown quantities |
| 8 | Journal / History | 1440×900 | Botanical Light | Source labels and partial dates |
| 9 | Taxonomy tree or map workspace | 1440×900 | Botanical Dark | Specialized workspace in house grammar |
| 10 | Plants directory | 390×844 | Botanical Light | Compact toolbar, first records visible |
| 11 | Plant details | 390×844 | Botanical Dark | Wrapped actions, tabs |
| 12 | Theme settings | 1024×844 | Mineral Dark | Six-theme picker |

- [ ] Each image is listed in a manifest with route, commit SHA, fixture version, viewport, raster size, theme and timestamp.
- [ ] No loading skeleton, toast or focus ring is caught mid-transition unless that state is the subject.
- [ ] The independent reviewer signs off on the set before publication.
