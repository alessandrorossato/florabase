# Detail empty states and required labels

Candidate: `/home/alessandro/.codex/worktrees/996d/florabase`, branch
`feat/global-visual-001`, base HEAD `cd63c185f7bcb0544cd9c3cff984b29564e6bc84` plus current
dirty/uncommitted source. Authenticated Feature Review: http://localhost:15174.

## Live visual evidence

At **1440×844, 1024×844 and 390×844**, all at 100% / visual viewport scale 1:

- `sowings-*`, `lineage-*`: normal gutter, border 0, minimum height 0, natural 54px message area.
- `photos-*`: restrained 72.25px bordered gallery placeholder; all three media actions retained.
- `create-top-*`, `create-acquisition-*`, `create-actions-*`, `create-full-*`: full-page form,
  identity marked required, optional captions plain, final actions reachable. Full captures supplement
  the actual 844px viewport screenshots; they do not substitute a different viewport size.
- `edit-essentials-*`: identity retains required semantics after selection.
- `edit-acquisition-*`: nullable Supplier/date and defaulted Source remain unmarked. The mobile
  linked Order case and unlinked draft are both captured.
- `edit-partial-date-*`: selected Month precision requires Year and Month, with no invented Day.
  `edit-partial-date-fields-390` shows both parts after scrolling the modal panel.

`observations.json` records geometry, caption states, native/ARIA requirements and marker styling.
There are **29 observations**, with no horizontal document overflow. Markers are muted semantic-token
12px captions. Underlying inert Details nodes may appear in the DOM probe while Edit is open; actual
screenshots and the accessibility tree identify the active modal. A 15px native vertical scrollbar
may reduce full-page screenshot width; no horizontal overflow is implied.

No create/save/media/Order-context operation was submitted. Only unsaved inspection values changed.
Native draft cancellation stalled browser control once; the operator dismissed it, and the remaining
Create matrix then completed. This does not certify automated native discard-prompt handling.
Temporary viewport overrides were reset.

## Validation

`required-audit.json` confirms all **54 native/reference required expressions unchanged** against the
before-pass audit. Actual backend schemas were checked for nullable/defaulted SeedLot fields, Order
price/currency pairing, required references/names, movement destination and selected date/quantity
parts. No backend, API schema, migration or environment workflow changed during this pass.

`test-summary.json` records **448 unique passing frontend tests across 27 files**, plus the final
15-test Location rerun. New coverage includes native/ARIA required semantics, selected ReferencePicker
state, nullable SeedLot fields (including Purchased Supplier), conditional PartialDate/quantity and
price/currency states, unchanged payloads, plain Sowings/Lineage and retained Photos workspace.
Shared keyboard/focus and accessible description regressions pass. This is focused browser/DOM
accessibility evidence, not a screen-reader certification.

`static-checks.json` records strict TypeScript, targeted zero-warning ESLint, 47-file Prettier check,
production build and whitespace results. Production bundles: SeedLot 45.14 kB / 12.40 kB gzip; main
228.15 kB / 70.92 kB gzip. `review-status.txt` records supported environment health and ownership. Existing Review
owner, schema and managed dataset are preserved. Canonical feature-verify, staging, commit, push and
delivery were not run. UAT, DEV, Stable Preview and production were not operated on.
