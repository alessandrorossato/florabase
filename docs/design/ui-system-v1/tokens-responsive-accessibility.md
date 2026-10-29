# Token, responsive and accessibility proposal

## Foundation retained

`frontend/src/styles/tokens.css` is the only source for the six theme combinations: Botanical, Herbarium and Mineral × Light/Dark. The prototype serves that exact file at `/tokens.css`; it does not duplicate the palette definitions. Appearance and palette remain independent axes. Auto appearance in the product keeps its existing operating-system behavior; prototype selectors deliberately show explicit states only.

Use `background`, `surface`, `surface-subtle`, `surface-hover`, `text`, `text-muted`, `border`, `border-strong`, `primary`, `primary-hover`, `primary-subtle`, `on-primary`, `success`, `warning`, `warning-text`, `warning-subtle`, `danger`, `danger-subtle`, `info`, `focus-ring`, `overlay-backdrop` and `elevation-overlay`. Never use pale border color as the only form-control boundary or color as the only status cue.

Source Sans 3 is UI/body; Source Serif 4 italic is botanical naming. Cultivar names remain distinguishable and are not silently italicized as species epithets. Existing type roles: body 15px/22px; small 13px/18px; headings 17/22/32px; large 40px only when warranted. Metadata uses small text without hiding core facts. Existing spacing is 4/8/12/16/24/32/48/64px. Prototype gaps outside this scale are composition exploration, not new tokens to copy.

Small/normal/large radii remain 6/10/14px. Use small for controls/rows, normal for bounded panels, large sparingly. Borders carry grouping; elevation is for overlays only. No gradients, glass, ornamental KPI cards or invented chart ink.

## Proposed navigation roles, pending acceptance

The dark forest rail visible in the supplied direction is expressed only inside the design prototype with four proposed roles: `nav-surface #16231b`, `nav-ink #ecf1ec`, `nav-muted #b7c8bd`, `nav-active #254333`; selected edge #a8cbb4. It is intentionally consistent across the three palettes in this candidate, with existing semantic colors inside content. This is a visual proposal, not an approved seventh theme. Gate B either promotes a reviewed navigation role matrix for all six combinations or retains the existing themed rail. Do not scatter these literals into product styles. Text contrast is measured in validation; all controls still need browser/AT verification at Gate B.

## Responsive rules

| Width / context                 | Proposed behavior                                                                                                       | Evidence acceptance                                                           |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| 1440×900 desktop                | 220px rail; intrinsic two-column header; full inventory until selection; optional 310px inspector                       | First records visible without scrolling through empty chrome; long names wrap |
| 1024×900 tablet                 | Same readable rail; toolbar wraps by available width; inspector becomes modal if useful content is too narrow           | No 256px/608px flex-basis heights; no body horizontal overflow                |
| 390×844 mobile                  | Compact brand/menu, primary bottom destinations; one-column content, labelled inventory records; modal selected preview | All essential facts/actions retained; footer above bottom navigation          |
| 320 CSS px and actual 200% zoom | Same reading order, no hidden controls; allow necessary specialist canvas/table scroll with textual equivalent          | Gate B/manual evidence still required; resized viewport is not real zoom      |

Use container/available-width behavior for the header, not an enormous min-height budget. On mobile the proposed order is title → purpose → search → filter/view actions → create → content. Essential actions remain labelled. Toolbar should not become a second fixed mobile bar. Studio review controls and design disclaimers are outside product chrome and excluded from canvas captures.

Inventory rows grow naturally for real long cultivar/lot labels. A compact density target is roughly 60–80px for short two-line rows, never a hard fixed height. On mobile compare essential facts without sideways scrolling by using labelled record blocks. Analytical tables that require column comparison may retain bounded scrolling with a named region, not body overflow.

## Interaction and focus rules

- House target size remains 44px for controls. Inline text links keep natural reading behavior; don't turn every link into a filled button.
- Every dialog has a title, focus containment, safe initial focus and return target. Destructive dialogs choose Cancel. Pending/error behavior stays domain-owned. Native HTML dialogs are a design interaction specimen only.
- Tabs get labelled panels, selected state, roving focus, Arrow/Home/End behavior; tab order must not contain six equivalent selected-section stops.
- Show errors both near the field and in a focusable summary; reveal the relevant section before focus. Errors cannot rely on red alone.
- Filters preserve query and use the current live/apply semantics. Saved Views stay page-private and serialize only supported dimensions.
- Mobile More preserves Settings, Appearance and Sign out, plus all macro-category destinations. Escape/dismiss returns to More. Authentication state is never moved into a new privileged route.
- Reduced-motion preference suppresses nonessential transitions. Forced colors and browser high contrast need manual validation; photographs and maps must still have useful text equivalents.
- Avoid nesting landmarks or heading levels for style. Product h1 remains the shell brand convention, page headings h2, sections h3; the prototype has a separate hidden design title and does not change production semantics.

## Scientific and physical exceptions

Do not recolor provider map imagery, QR payloads, print geometry or botanical photographs to mimic the chrome. Map evidence legends and comparison hues retain their semantics. Labels continue physical CSS geometry and authenticated destination configuration, not screen-as-print assumptions. Placeholder imagery is never scientific observation or a claimed record primary photo.
