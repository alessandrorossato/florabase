# COLLECTION-VISUAL-001 — accepted visual review and independent verification

Same candidate: `/home/alessandro/.codex/worktrees/ef73/florabase`, branch
`feat/collection-visual-001`, HEAD/base `1e3df6adf9afdfd4a213396666b336f6d1b5136c` plus unstaged source.
The operator accepted the fourth pass and authorized independent review, canonical verification,
commit, protected delivery and finish. Review fixed outdated presentation assertions without
weakening domain checks. The first canonical FULL gate passed; the final documented tree is being
verified now before staging and commit.

[Feature Review](http://localhost:15174) uses the existing candidate-owned database/media and fixture
v4/66. On resumption its frontend/backend were stopped; supported `feature-review-up` reused the
existing state. No reset, removal, reseed or collection mutation. Persistent environments untouched.
See the [fourth-pass evidence index](review/collection-visual/sowings-plants/fourth-pass/README.md).

## FULL-PAGE FOOTER FIX

Overlapping sibling form rules supplied a separate surface and inconsistent spacing. Full-page
Collection forms now share one footer definition in collection-page.css: the Add SeedLot gutters,
single top border, 12px vertical padding and normal document flow, with a transparent background that
continues the canvas. This shared surface correction includes Add SeedLot itself; its form layout
and behavior are retained. Contextual Edit keeps its bounded dialog footer.

Full-page footers have no stickiness, shadow, detached surface or extra margin. Their widths match
the form grid; normal workspace bottom spacing keeps mobile navigation clear. The last 80px and
footer bounds are included in the responsive review rather than inferred from top-of-page captures.

## REDUNDANT FORM LABEL REMOVAL

Plant/group create and Edit hide the nested Origin legend visually while retaining the named fieldset
and both radios. Collection-entry date hides the nested Precision caption through an opt-in shared
PartialDate prop; its select is named “Collection-entry date precision”. Sowing date uses the same
mechanism. Existing SeedLot PartialDate captions retain their original default rendering.

Sowing “Kind” becomes a hidden “Quantity sown kind” label. Group “Kind” becomes hidden “Quantity kind”.
The Notes section avoids a second visible Notes caption. Temperature keeps visible Minimum °C and
Maximum °C labels, with the overall group name hidden visually. Conditional controls, required markers,
date precision, count/weight/approximate/unknown semantics and validation remain.

## NEW PLANT / PLANTGROUP

The desktop workspace keeps Essentials and Lifecycle & notes on the left, Origin and collection-entry
facts on the right. Section tops align and the footer spans the same grid. Group Quantity remains a
real group-specific field, alongside Current location when wide. Individual Plants have no quantity.
The same shared field components normalize create, extraction, direct Edit and contextual Edit.

## NEW SOWING

The desktop grid deliberately pairs Essentials with Material & location, then Outcome & status with
Cultivation; Notes follows on the left. SeedLot and label share an aligned row, date sits beneath.
Quantity/location are peers; Substrate/Method align, as do Pretreatment and temperature parts.
Notes and Environment use coherent 5rem minimum textareas without reducing control or text size.
Concise helper copy retains meaningful uncertainty and historical-entry guidance.

## GUIDED CREATE PLANT

One Sowing page identity replaces stacked propagation/result headings. A compact Creating from
SeedLot/Sowing summary retains actual links; the graphical path is removed only from creation.
Botanical identity is preselected and remains editable as before, with concise truthful helper copy.
Origin reads as a plain explicit source link. Essentials/notes and Origin/Sowing-after-creation use
the available workspace, with the shared full-page footer.

## GUIDED CREATE PLANTGROUP

Uses the same compact guided layout, retaining group Quantity and exact/approximate/unknown meaning.
Both kinds keep their existing atomic endpoint, payload, collection-entry PartialDate, lifecycle,
notes and source relationships. No write request occurs until explicit submission. Back and Cancel
return to the same source Sowing Details tab; direct links use a safe source fallback.

## COMPACT SOWING-STATE CONTROL

Four native named radios retain Keep active, Complete Sowing, Mark failed and Abandon Sowing. They
form a compact two-by-two desktop group with a 44px interaction height. One live description explains
the selected consequence; no permanently repeated card explanations or duplicate confirmation text.
Existing final-outcome facts still appear when Complete is selected, including honest uncertainty.

## DETAIL ACTION / TRANSFER

Eligible individual Plants keep Record harvest primary and Edit visible. Eligible groups keep Extract
plant primary and Edit visible; the existing group Harvest link remains available. Transfer/Transfer
group now live in the existing More menu with Print label and supported Undo creation. Eligibility,
transfer request and lifecycle behavior are unchanged. Transfer and reversal dialogs return to the
stable More trigger after menu content unmounts; keyboard/Escape behavior is covered.

## PARTIALDATE LABEL NORMALIZATION

The shared PartialDate opt-in changes only label rendering and accessible naming. Unknown stays null;
year/month/day precision still controls which required parts exist, and narrowing precision removes
unknown finer components. Shared tests exercise both visible and hidden-caption modes while retaining
adjacent values. Transfer date and unrelated date families retain their existing presentation.

## RESPONSIVE / VIEWPORT

**30 unique form/viewport checks** cover all five requested forms at 1440×844, 1024×844,
390×844 and effective 1152×675, 960×563 and 819×675 viewport proxies. No measured horizontal
page/control overflow. Every measured footer is static, transparent and aligned to its form edges;
all five mobile bottom captures clear the shared navigation bar. Three ordinary Origin editors
(individual, group and direct-origin Plant) fit at real 1440×844 without internal panel scrolling.

At real 1440×844 / 100%, default New Plant, group and Sowing pages are 844px high, with footer bottoms
at approximately 790px, 803px and 817px. Guided Plant is 844px with footer at 808px. Guided group is
846px high (2px beyond the viewport), with its footer at 822px. These observed fixture/default states
support the fit statements; conditional controls, completion facts, validation and narrower screens
may scroll. Actual browser zoom is unavailable; 125%/150% are explicitly viewport proxies.

Live menus verified keyboard entry, Escape and Transfer-dialog return to More for both kinds; the
blocked Undo entry remains. Both guided Cancel actions returned to the exact source Lineage tab.
Real-history Back has focused unit evidence for both source tab contexts. A live browser Back reached
the source, but the browser tool wait stalled; no complete live Back matrix is claimed.

## TESTS

**178 distinct tests / 11 files passed** across bounded runs: ten clean files from the combined
run contribute 120 cases; the final isolated complete Plant run contributes 58. Coverage includes
Sowing, Plant/group, guided creation, both PartialDate label modes, FormSections/contextual Edit,
Details actions/More/reversal, real-history source/category navigation, SeedLot and App transitions.
Existing source/identity/quantity/lifecycle/payload/CSRF/conflict assertions remain.

The initial combined run exposed one overbroad test-label replacement affecting an unrelated Journal
date and two immediate menu-focus assertions. Restored the Journal label query and awaited the same
required menu focus. An interrupted Plant repeat was not counted; the final complete repeat passed.
No timeout, validation or business assertion was weakened. Strict TypeScript/production build,
targeted zero-warning ESLint, touched-source formatting, **105-feature** graph and whitespace checks
pass. Type/lint checks also caught and corrected test-only typing/void-arrow issues.

Nine payload/validation/germination/extraction-summary/reversal-submit helpers match HEAD after
whitespace normalization. Guided descendant API calls and atomic payloads are unchanged. No backend,
API/schema, migration or dependency change; those gates did not run. This is visual-review evidence,
not a canonical verification receipt.

## INDEPENDENT REVIEW AND CANONICAL GATE

Operator acceptance is complete. The independent review confirmed the candidate stays limited to
Collection visual normalization and its UI documentation/evidence: no backend, API, schema, migration
or dependency changes. `Propagation002.test.tsx` now checks the all-visible page sections and current
accessible quantity labels, follows the explicit View lineage action, and retains the source-adjustment,
quantity, conflict, and lifecycle assertions. Supplier's shared Photos empty-state expectation matches
the accepted concise copy. Focused repro passed **19 tests / 2 files**.

The final canonical `make feature-verify` selected **FULL** against base
`1e3df6adf9afdfd4a213396666b336f6d1b5136c` and passed with a working-tree receipt: feature graph **105
valid**; workflow and environment suites; repository formatting, zero-warning frontend lint, strict
mypy (**346 files**), TypeScript and API drift; backend **939 passed / 90.22% coverage**; frontend
**755 passed / 68 files**; PostgreSQL integration **735 passed**; backend/frontend production builds;
full migration cycle and exact-tree receipt. Migration revision remains `20261013_0042`; this feature
adds none. Disposable integration and migration resources reported clean exact-owner cleanup.

One earlier final-gate attempt exposed a timing-sensitive Stored Material focus assertion; the exact
test passed in isolation and again in the complete final frontend suite (**755/68**). The final full
gate passed without source changes and recorded the receipt for this candidate tree.

Actual browser zoom remains unverified. The 125%/150% evidence is labelled viewport proxies; the
measured 846px guided-group page at 844px viewport and the stalled live browser-Back observation retain
their stated limits. Feature Review is healthy at revision `0042`, fixture v4/66. The read-only
inventory identifies persistent UAT as owned by worktree `4ff7`; the guarded UAT status command refused
this checkout, and no UAT operation was made. Its volumes remain retained. After the gate, exact-owner
`feature-review-up` restored Review's stopped application services while retaining DB/media, owner and
fixture v4/66; final Review status is healthy at `20261013_0042`.

PR #112 CI passed integration and production build, but its independent quality job exposed that the
guided Sowing local validation set the error message without selecting the quantity error field. The
candidate now supplies that field to the existing FormSections focus mapping, and the regression waits
for its documented animation-frame focus. This is a bounded accessibility correction; the follow-up
canonical gate and protected delivery are required before completion.

READY_FOR_DELIVERY
