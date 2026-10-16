# First operator page-family refinement evidence

Authenticated, populated Feature Review on 2026-10-14. Source: worktree `996d`, branch
`feat/global-visual-001`, HEAD `cd63c185f7bcb0544cd9c3cff984b29564e6bc84` plus dirty changes.
Use `http://localhost:15174` with the existing Review `owner` credentials. DB revision is
`20261013_0042`; the preserved synthetic dataset is v4/66. No WFO snapshot is installed.

## Capture matrix and limitations

| Filename suffix  | Capture viewport | Meaning                          |
| ---------------- | ---------------- | -------------------------------- |
| `1440-100`       | 1440×844         | Normal desktop viewport          |
| `1024-100`       | 1024×844         | Normal narrower desktop viewport |
| `390-100`        | 390×844          | Mobile viewport                  |
| `1440-125-proxy` | 1152×675         | Effective-space proxy only       |
| `1440-150-proxy` | 960×563          | Effective-space proxy only       |
| `1024-125-proxy` | 819×675          | Effective-space proxy only       |

The proxy files are **not browser zoom evidence**. The enabled in-app browser did not apply the
requested shortcuts; a later shortcut probe stalled and required session recovery. Operator
125%/150% zoom acceptance remains pending. No horizontal document overflow was observed in the
captured states. Temporary viewport overrides are reset before handoff.

Each state below has six `.jpg` files using the suffixes above:

- `dashboard`: compact header, metrics, Upcoming and recent activity.
- `dashboard-filters`: default open drawer; at 1440×844 client/scroll height both 844px.
- `seeds-default`: result-count selection entry and ordinary browsing.
- `seeds-selection-zero`: explicit mode, disabled Actions, visible checkboxes.
- `seeds-selection-several`: three selected records.
- `seeds-inspector`: bounded desktop inspector; mobile uses the full detail workflow.
- `seed-edit-essentials`: direct tabs and Cancel/Save changes.
- `seed-edit-acquisition`: Save changes from an intermediate section.
- `seed-edit-long-section`: Seed details, safe short-viewport scrolling.
- `seed-detail-overview-empty`: compact empty Upcoming and grouped facts.
- `seed-detail-overview-populated`: Basil packet with photo, two Upcoming activities and facts.
- `seed-detail-photos-empty`: empty Photos and its existing media actions.

[responsive-probes.json](responsive-probes.json) contains DOM measurements saved after browser
session recovery. Earlier states retain screenshots but their in-memory measurements were lost;
no raw measurements are reconstructed. The unsuffixed Dashboard/drawer/Seeds images are earlier
iteration captures, not an original-source baseline or the final comparison. Scoped detail
heading/link-gap adjustments happened after the first empty detail/Photos capture; refreshed
Overview/Photos captures reflect those adjustments. Edit captures were refreshed after the final
desktop-only sticky-footer condition. `seed-edit-mobile-actions-reachable.jpg` shows the ordinary
mobile action row after scrolling: Save ends at about 723px above navigation at 780px, retaining 44px
height.

## Real interactions and shared consumers

[seed-save-from-acquisition.jpg](seed-save-from-acquisition.jpg) shows a successful normal
authenticated save of Aloe's existing values, with focus returned to its record heading. Ordinary
version/time metadata may change through that save. No fixture reset, synthetic CSRF/session or bulk
move was used. Selection tests in the real browser included zero/three, Select visible (seven),
Clear, Exit, and opening/cancelling the sole Actions operation. Unit tests additionally cover one,
scope resets and the 100-record limit.

Sibling captures cover Sowing edit, Plant/group selection and edit, Stored material selection,
Provenance Site edit and nested Botanical Profile edit. Their editors were inspected and cancelled
without saving. `regression-journal.jpg`, `regression-settings.jpg` and `regression-labels.jpg` record
read-only checks of accepted workspaces. Settings and print configuration remain unchanged.

## Focused validation

- Five first-family/shared primitive files: **65 tests passed**.
- Nine current consumer files: **118 tests passed**.
- Journal/History/Schedule/Settings/Labels: **129 tests passed**.
- Final SeedLot/FormSections/BulkLocation rerun: **48 tests passed**; final bulk focus assertion:
  **12 tests passed**. These reruns overlap the counts above.

TypeScript, targeted ESLint with zero warnings, source/document Prettier and Vite build passed.
Diff whitespace checks passed and the staged diff is empty. An interruption left Review frontend
and backend stopped; supported `make feature-review-up` recovered them with the DB revision,
owner/session and ready v4/66 dataset retained. No seed, reset or removal ran in this refinement.
No canonical gate or full-suite result for this refinement is claimed. Earlier normalization,
fixture and bundle evidence remains
in the parent directory with its original scope. Everything stays unstaged/uncommitted.
