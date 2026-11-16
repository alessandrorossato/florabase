# G-CORE record template

This is a template for gate G-CORE, which runs the
[core acceptance script](../scope-v1.md#core-acceptance-script-g-core) on the release-candidate
images starting from an empty database. Copy it to `g-core-<candidate>.md` for a recorded run.
A copy counts as evidence only when filled in from an actual run. This template is not evidence
and is separate from the DOC-04 unassisted trial, which uses only G-CORE steps 1–9.

## Run

| Field | Value |
| --- | --- |
| Candidate commit and version | |
| Images | backend and frontend digests from the release manifest |
| Host, browser, viewport | |
| Starting state | migrated empty database with only the bootstrapped owner |
| Recorded by, date | |

## Steps

The last column names the certification rows that the step supplies. Each evidence map under
[`certify/`](certify/README.md) cites the step and the observation it relies on, and a step
counts only for the rows that cite it.

| Step | Script | Result | Observations | Defects | Supplies certification rows |
| --- | --- | --- | --- | --- | --- |
| 1 | Empty database: sign in, see a usable empty Today, follow the path to a first record | | | | FN-06; UX-TODAY-001; UI-SYSTEM-001 #4 (R24: no image gives one line) |
| 2 | Botanical identity, profile and a manual native range | | | | UX-004; BOTANICAL-IDENTITIES-VISUAL-001 |
| 3 | Supplier, order and a seed lot with partial and unknown values | | | | UX-005; UX-DATE-001 (partial dates) |
| 4 | Sowing, germination observation, plant and plant group, extraction and a supported reversal | | | | GERMINATION-001; LINEAGE-003 |
| 5 | Journal entry: a new entry opens with Today selected; one entry each with Today, Another date and Date unknown; photo upload; primary photo | | | | FN-05; UX-DATE-001 #3 (R01); ATTACHMENT-003; ATTACHMENT-005 |
| 6 | Bulk move; label print preview and QR lookup | | | | LOCATION-002; UI-REDESIGN-EXPLORATION-001 #3 (QR lookup) |
| 7 | Schedule an activity, complete it, and see Today reflect it | | | | UX-TODAY-001; UX-006 #3 (R14, proposed) |
| 8 | Harvest, stored material and a new seed lot; the lineage view shows the chain | | | | HARVEST-001; LINEAGE-003 |
| 9 | Search, filters and a Saved View; CSV export and import preview | | | | SEARCH-001; IMPORT-001; CONTROLS-001 #4 |
| 10 | Session expiry during an edit and a server stop during a save: an error is shown and nothing is lost | | | | — |
| 11 | Change the password and sign in with the new one | | | | ENG-01 #1, #2 |
| 12 | Cuttings: a material lot through rooting to an established plant, including a failed and a still-unknown attempt | | | | FN-01; CUTTING-001 (writer's handoff); FABLE-FIX-CUTTINGS |

## Defects

| ID | Step | Description | Severity (critical, high, medium, low) | Resolution: commit, or disposition with reason |
| --- | --- | --- | --- | --- |

## Outcome

G-CORE passes when all twelve steps pass on the candidate images and no critical or high
functional defect is open. Recorded by: role, date.
