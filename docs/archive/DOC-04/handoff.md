# DOC-04 Handoff — End-user guide and unassisted trial template

## 1. Branch, commits, and release scope

- **Feature ID**: `DOC-04` (`in_progress` in [`docs/features.json`](../../features.json); becomes
  `implemented` / `verified` after the unassisted non-developer trial runs on the release
  candidate).
- **Proposed release class in [`docs/release/scope-v1.json`](../../release/scope-v1.json)**:
  `"DOC-04": "release-work"` (added next to `DOC-01`, `DOC-03`, `DOC-05`).
- **Dependencies in `docs/features.json`**: `["RELEASE-SCOPE-001"]`.
- **Branch**: `docs/doc-04-user-guide`
- **Base commit (`origin/main`)**: `ddf5a1431453df6c6644fb1f2e9feeec6b120e16`
- **Final commit**: recorded in the delivery report and git log on `docs/doc-04-user-guide` (no
  pages were merged or split from the 10-page structure proposed in
  [`docs/release/scope-v1-handoff.md`](../../release/scope-v1-handoff.md) § DOC-04).
- **Verification tier**: `docs` (`make verification-plan FORMAT=json` and `make feature-verify`).

## 2. G-CORE coverage map

Every step of `G-CORE` 1–9 (plus step 12 Cuttings, and user-level parts of steps 10–11) in
[`docs/release/scope-v1.md`](../../release/scope-v1.md) § Core acceptance script is covered by the
user guide as follows:

| G-CORE step | Acceptance script summary | User guide page | Section heading(s) |
| --- | --- | --- | --- |
| **1** | Sign in on an empty database; see an intelligible zero-state `Today` and a clear path to the first record | [`docs/user-guide/README.md`](../../user-guide/README.md)<br>[`docs/user-guide/first-hour.md`](../../user-guide/first-hour.md) | `## Signing in`, `## How the app is laid out`<br>`## 1. Sign in and tour the empty Today screen` |
| **2** | Create a botanical identity, add a profile and a manual native range | [`docs/user-guide/first-hour.md`](../../user-guide/first-hour.md) | `## 2. Create a botanical identity, profile, and manual native range` (`### Create the botanical identity`, `### Add a botanical profile`, `### Record a manual native range`) |
| **3** | Create a supplier, an order, and a seed lot with partial and unknown values | [`docs/user-guide/concepts.md`](../../user-guide/concepts.md)<br>[`docs/user-guide/first-hour.md`](../../user-guide/first-hour.md) | `## Partial and unknown dates, and approximate quantities`<br>`## 3. Create a supplier, an order, and a seed lot` (`### Create a supplier`, `### Create an order`, `### Create a seed lot with partial or unknown values`) |
| **4** | Create a sowing from the seed lot, record a germination observation, create a plant and a plant group, extract a plant from the group, and perform a supported reversal | [`docs/user-guide/first-hour.md`](../../user-guide/first-hour.md) | `## 4. Sow the seeds, record germination, create plants, extract, and reverse` (`### Start a sowing from the seed lot`, `### Record a germination observation`, `### Create an individual Plant and a Plant group from the sowing`, `### Extract an individual Plant from the Plant group`, `### Perform a supported reversal`) |
| **5** | Record three journal entries on the plant or group: one keeping `Today` preselected, one with `Another date`, one with `Date unknown`; upload a photo and choose a primary photo | [`docs/user-guide/daily-use.md`](../../user-guide/daily-use.md) | `## Recording Journal entries on a Plant or Plant group` (`### Open the Journal and choose when it happened`)<br>`## Photos and choosing a primary photo` (`### Upload a photo to a Journal entry`, `### Upload photos to a record and set the primary photo`) |
| **6** | Move records in bulk to a location; prepare a label print preview and look up a record from its QR URL | [`docs/user-guide/daily-use.md`](../../user-guide/daily-use.md)<br>[`docs/user-guide/finding-things-and-labels.md`](../../user-guide/finding-things-and-labels.md) | `## Locations and moving records in bulk` (`### Create a Location (if you do not have one yet)`, `### Move records in bulk`)<br>`## 3. Prepare and print physical labels`, `## 4. Look up a record from a label QR code` |
| **7** | Schedule an activity, see `Today` reflect it, complete it, and see `Today` reflect the completion | [`docs/user-guide/daily-use.md`](../../user-guide/daily-use.md) | `## Scheduling and completing activities` (`### Schedule an activity`, `### See the scheduled activity on Today`, `### Complete the activity and check Today again`) |
| **8** | Record a harvest, track stored material, convert it to a new seed lot, and see the full chain (`Seed lot → Sowing → Plant/Plant group → harvested Seed lot`) in the lineage view | [`docs/user-guide/harvest-and-seed-saving.md`](../../user-guide/harvest-and-seed-saving.md) | `## 1. Record a harvest`<br>`## 2. Track collected material as Stored material`<br>`## 3. Convert stored seeds into a new Seed lot`<br>`## 4. Read the lineage chain` |
| **9** | Find the created records through global search, filters and a saved view; export CSV and run a CSV import preview | [`docs/user-guide/finding-things-and-labels.md`](../../user-guide/finding-things-and-labels.md)<br>[`docs/user-guide/your-data.md`](../../user-guide/your-data.md) | `## 1. Global search and filters`, `## 2. Save and reopen custom views (Saved views)`<br>`## 1. Export collection records to CSV`, `## 2. Validate and preview a CSV import` |
| **10–11** (user-level reference) | Session expiry during an edit (`Session expired — sign in again`) and server error during a save | [`docs/user-guide/troubleshooting.md`](../../user-guide/troubleshooting.md) | `## Signed out while editing a form`<br>`## "Nothing saved" or a server / connection error appears` |
| **12** | Cuttings: create a vegetative material lot, start a rooting attempt, log a rooting observation, establish a plant or plant group, and record a failed and an unknown-count attempt | [`docs/user-guide/cuttings.md`](../../user-guide/cuttings.md) | `## 1. Take or add a cuttings material lot`<br>`## 2. Start a rooting attempt from a material lot`<br>`## 3. Log rooting observations (including unknown or zero counts)`<br>`## 4. Establish a Plant or Plant group from a rooting attempt`<br>`## 5. Record failed or still-unknown attempts`<br>`## 6. Undo a cutting operation` |

Trial record template:
[`docs/release/evidence/doc-04-trial-template.md`](../../release/evidence/doc-04-trial-template.md).

## 3. Marker inventory (`TODO(DOC-04 ...)`)

### `TODO(DOC-04 verify)` markers

None (`0`). Every UI navigation name, button label, tab title, and field label in the user guide was
verified directly against the frontend TypeScript/React source on base commit `ddf5a1431453`.

### `TODO(DOC-04 after batch 12)` markers (4)

| File:line | Area | Marker text |
| --- | --- | --- |
| `docs/user-guide/first-hour.md:45` | Creating a botanical identity (WFO autocomplete) | `<!-- TODO(DOC-04 after batch 12): Note the local WFO name suggestion step in the Create a botanical identity form once batch 12 lands. -->` |
| `docs/user-guide/daily-use.md:30` | Plants directory layout | `<!-- TODO(DOC-04 after batch 12): Once the Plants directory card-height layout fix lands, check whether any directory view note is needed. -->` |
| `docs/user-guide/daily-use.md:107` | Botanical identity Media tab & Explore Media library | `<!-- TODO(DOC-04 after batch 12): Expand the botanical identity Media tab and Explore Media asset flow once the batch 12 media redesign lands. -->` |
| `docs/user-guide/reference-data.md:54` | Optional reference data mount in `docs/installation.md` | `<!-- TODO(DOC-04 after batch 12): Update this note once the operator setup for the WFO/WCVP reference data mount in docs/installation.md lands in batch 12. -->` |

### `TODO(DOC-04 screenshot)` markers (27)

| File:line | Marker text |
| --- | --- |
| `docs/user-guide/README.md:24` | `<!-- TODO(DOC-04 screenshot): Sign-in screen, empty form, highlight Login name, Password and Sign in button -->` |
| `docs/user-guide/README.md:77` | `<!-- TODO(DOC-04 screenshot): Workbench on Today, desktop layout, highlight left workspace rail, section panel with + New, Record button, and Search -->` |
| `docs/user-guide/first-hour.md:30` | `<!-- TODO(DOC-04 screenshot): Today screen on a fresh database, zero state, highlight Collection snapshot, To review and + New menu -->` |
| `docs/user-guide/first-hour.md:50` | `<!-- TODO(DOC-04 screenshot): Create a botanical identity dialog, filled in, highlight Scientific name, Cultivar, Common name, and Create botanical identity button -->` |
| `docs/user-guide/first-hour.md:82` | `<!-- TODO(DOC-04 screenshot): Botanical identity Maps or Native range dialog, with a native range place added, highlight Manage native range and Add place -->` |
| `docs/user-guide/first-hour.md:148` | `<!-- TODO(DOC-04 screenshot): Add seed lot dialog on Inventory or Acquisition tab, showing Approximately quantity and partial Acquisition date -->` |
| `docs/user-guide/first-hour.md:179` | `<!-- TODO(DOC-04 screenshot): Start sowing wizard on Step 2 Seed usage, highlight What happens to the source seed lot options and Start sowing button -->` |
| `docs/user-guide/first-hour.md:234` | `<!-- TODO(DOC-04 screenshot): Extracted Plant Overview page, highlight Original Plant group panel and Reintegrate into group button -->` |
| `docs/user-guide/daily-use.md:55` | `<!-- TODO(DOC-04 screenshot): Add entry dialog on a Plant Journal tab, highlight Entry type, When did it happen radio buttons with Today preselected, Another date, and Date unknown -->` |
| `docs/user-guide/daily-use.md:102` | `<!-- TODO(DOC-04 screenshot): Plant Photos tab with uploaded photos, highlight Primary badge and Set as primary action in the photo card menu -->` |
| `docs/user-guide/daily-use.md:130` | `<!-- TODO(DOC-04 screenshot): Schedule activity dialog, filled in with Title, Activity kind, Due date and a target Plant, highlight Save activity -->` |
| `docs/user-guide/daily-use.md:163` | `<!-- TODO(DOC-04 screenshot): Complete activity dialog showing Complete without a Journal Event and Record what happened in Journal options -->` |
| `docs/user-guide/daily-use.md:206` | `<!-- TODO(DOC-04 screenshot): Move to location dialog at Preview move step, highlight Target Location, Will move summary, and Apply move button -->` |
| `docs/user-guide/harvest-and-seed-saving.md:40` | `<!-- TODO(DOC-04 screenshot): Record harvest dialog on Materials collected tab, showing a Seeds material line with Quantity and Precision, highlight Add material line and Record Harvest -->` |
| `docs/user-guide/harvest-and-seed-saving.md:66` | `<!-- TODO(DOC-04 screenshot): Harvest detail page Stored material section with an active tracked Seeds line, highlight Track stored material / Edit stored material and Create Seed lot buttons -->` |
| `docs/user-guide/harvest-and-seed-saving.md:105` | `<!-- TODO(DOC-04 screenshot): Create Seed lot from stored seeds dialog, highlight Material leaving stock, Resulting Seed lot label, Seed lot quantity, and Create Seed lot button -->` |
| `docs/user-guide/harvest-and-seed-saving.md:141` | `<!-- TODO(DOC-04 screenshot): Seed lot Lineage tab or Explore Lineage view showing the multi-step chain from original Seed lot through Sowing and Plant/Plant group to the converted Seed lot -->` |
| `docs/user-guide/cuttings.md:53` | `<!-- TODO(DOC-04 screenshot): Take or add cuttings form, highlight Material type, Quantity, Origin (Mother Plant), and Start rooting attempt immediately checkbox -->` |
| `docs/user-guide/cuttings.md:101` | `<!-- TODO(DOC-04 screenshot): Rooting attempt detail page with Rooting observations and Log rooting observation dialog -->` |
| `docs/user-guide/cuttings.md:133` | `<!-- TODO(DOC-04 screenshot): Establish Plant or Plant group dialog on a Rooting attempt, highlight Create (Plant / Plant group) and Attempt after establishment -->` |
| `docs/user-guide/finding-things-and-labels.md:30` | `<!-- TODO(DOC-04 screenshot): Today screen with active search query and Filters drawer or active filter chips, highlight Search your collection, Filters button, and matching results -->` |
| `docs/user-guide/finding-things-and-labels.md:65` | `<!-- TODO(DOC-04 screenshot): Saved views dialog showing Save view form and a list of saved views with Open, Rename, Update with current view, and Delete -->` |
| `docs/user-guide/finding-things-and-labels.md:124` | `<!-- TODO(DOC-04 screenshot): Settings Labels screen showing QR destination configured, Label size options, Selected material, and Print preview with QR codes -->` |
| `docs/user-guide/finding-things-and-labels.md:141` | `<!-- TODO(DOC-04 screenshot): Record sheet open, highlight Open a label section with Label link input, Open button, and Scan with camera -->` |
| `docs/user-guide/your-data.md:64` | `<!-- TODO(DOC-04 screenshot): Settings Import / Export screen showing Download CSV, Blank template, Example CSV, Validate and preview, and the Preview table with Ready rows and Confirm import / Cancel preview buttons -->` |
| `docs/user-guide/reference-data.md:47` | `<!-- TODO(DOC-04 screenshot): Settings Data sources screen showing the Sources in use table -->` |
| `docs/user-guide/troubleshooting.md:23` | `<!-- TODO(DOC-04 screenshot): Session expired — sign in again dialog over an open form, highlight Login name, Password, Sign in, and Discard unsaved changes and sign out -->` |

## 4. Disagreements found between existing feature docs and the code

Per the prompt rule (*"check claims against the code when the two disagree, and report any
disagreement in the handoff instead of fixing the other doc"*), the user guide follows the code on
`ddf5a1431453`, and the following differences in existing `docs/*.md` files were identified:

| Existing feature doc | What the existing doc says | What the code on `main` (`ddf5a1431453`) actually does |
| --- | --- | --- |
| `docs/schedule.md` (§ Dates and statuses, § Targets and retention) | Lists **eight** activity kinds (`Repot`, `Water`, `Fertilize`, `Move / relocate`, `Check germination`, `Inspect`, `Harvest`, `General follow-up`) and **six** target types (`BotanicalIdentity`, `SeedLot`, `Sowing`, `Plant`, `PlantGroup`, `Location`). | `frontend/src/schedule/state.ts` defines **nine** activity kinds (adding `Check rooting` / `check_rooting`) and **eight** target types (adding `Vegetative lot` / `vegetative_lot` and `Rooting attempt` / `propagation_attempt`). |
| `docs/schedule.md` (§ Agenda / Month UX candidate) | States that the view switcher names the views `Agenda` and `Month`. | `frontend/src/schedule/ScheduleScreen.tsx` (line 796) renders a single toggle button labelled `Calendar` when in list view and `Agenda` when in calendar view (matching the navigation sub-item `Calendar` in `frontend/src/shell/navigation.ts`). |
| `docs/saved-views.md` (§ Supported surfaces, § API and operator flows) | Lists **16** supported surfaces and describes separate `Save view` and `Saved views` controls in a dedicated row below directory filters. | `frontend/src/saved-views/state.ts` lists **17** surfaces (including `cuttings`). After `UI-REVIEW-001`, directories use `<SavedViews presentation="dialog" />` inside `DirectoryTools`, so the toolbar exposes a single `Saved views` button opening a dialog that contains the `Save view` action; moreover, `frontend/src/shell/WorkbenchShell.tsx` surfaces up to 5 saved views per section directly in the left navigation panel. |
| `docs/bulk-operations.md` (§ Explicit transient selection, § Navigation and later work) | States that directories expose a `Select` button, that the active bar has `Move to location`, `Select visible`, `Clear selection`, and `Done`, and lists legacy macroareas (`Overview (Dashboard)`, `Collection`, `Activity`, `Places`, `Reference`, `Tools`). | `frontend/src/bulk/BulkLocation.tsx` labels the entry button `Select records`, and the active selection bar has `Select visible`, `Clear`, `Actions ▾` → `Move to location`, and `Exit selection`. `frontend/src/shell/navigation.ts` defines the six workspaces `Today`, `Collection`, `Activity`, `Explore`, `Sourcing`, and `Settings`. |
| `docs/labels.md` (§ User workflow, § QR links and base URL setting) | Refers to `Settings → Tools → Labels`, `Settings → General` for **Public / QR base URL**, and `QR destination → Edit`. | `frontend/src/shell/navigation.ts` places `Labels` directly under `Settings` (`Settings` → `Labels`). There is no `Settings → General` page (`#/settings?tab=general` redirects to `#/labels?qr=edit`), and `frontend/src/labels/LabelsScreen.tsx` labels the button `Edit QR destination` (opening `QrDestinationDialog.tsx` with field `Public / QR base URL` and button `Save`). |
| `docs/import-export.md` (§ Guided operator flow) | Refers to `Tools → Import / Export`. | `frontend/src/shell/navigation.ts` places `Import / Export` under `Settings` (`Settings` → `Import / Export`). |
| `docs/search.md` (§ Using global search) | Refers to `Dashboard` and `Dashboard Quick actions` (`Add seed lot`, `Add plant`, `Add plant group`, `Import / Export`). | `frontend/src/collection/DashboardScreen.tsx` titles the page `Today`. Its `Record` panel (`frontend/src/events/recordWorkflows.ts`) lists `Add Journal entry`, `Record harvest`, `Record sowing`, `Take or add cuttings`, `Move plants / groups`, `Complete scheduled work`, and `Schedule activity`, while creation actions live in the shell's `+ New` (`New record`) menu (`frontend/src/shell/navigation.ts`). |

## 5. Source provenance of UI labels (Navigation and G-CORE 1–4 forms)

Every UI label used in the guide was taken verbatim from the read-only frontend source files below:

### Main navigation & shell controls

| UI area / flow | Exact labels used in the guide | Source file(s) |
| --- | --- | --- |
| Sign-in & session expiry | `Login name`, `Password`, `Sign in`, `Session expired — sign in again`, `Discard unsaved changes and sign out` | `frontend/src/auth/LoginForm.tsx`<br>`frontend/src/App.tsx` |
| Workspaces & sections | **Today**: `Today`<br>**Collection**: `Seeds`, `Sowings`, `Cuttings`, `Plants` (sub-item `Plant groups`), `Harvests` (sub-item `Stored material`), `Locations`<br>**Activity**: `Journal`, `History`, `Schedule` (sub-item `Calendar`)<br>**Explore**: `Botanical identities`, `Taxonomy`, `Lineage`, `Media`, `Geography` (sub-items `Collection origins`, `Species distribution`, `Native ranges`)<br>**Sourcing**: `Suppliers`, `Orders`<br>**Settings**: `Account`, `Theme`, `Labels`, `Import / Export`, `Data sources`, `Help` | `frontend/src/shell/navigation.ts`<br>`frontend/src/shell/WorkbenchShell.tsx` |
| Shell quick actions | `+ New` (`New record`: `New seed lot`, `New sowing`, `New plant`, `New plant group`, `Record harvest`, `New botanical identity`, `New supplier`, `New location`, `New local place`), `Record`, `Search` (`Search and commands`, `Search records, sections and actions`), `Account and settings`, `Hide panel`, `Sign out` | `frontend/src/shell/navigation.ts`<br>`frontend/src/shell/WorkbenchShell.tsx`<br>`frontend/src/shell/RecordSheet.tsx`<br>`frontend/src/shell/CommandPalette.tsx` |
| Today zero-state & panels (G-CORE 1) | `Today`, `Search your collection…`, `Filters`, `Saved views`, `Next work` (`Open Schedule`, `Overdue`, `Due today`, `Next 7 days`, `No planned activities. Schedule work when your collection needs it.`), `Recent activity` (`Open Journal`, `Open History`, `No recent activity. Journal observations and recorded operations will appear here.`), `Record` (`Add Journal entry`, `Record harvest`, `Record sowing`, `Take or add cuttings`, `Move plants / groups`, `Complete scheduled work`, `Schedule activity`), `Collection snapshot` (`Individual Plants`, `Plant groups`, `Seed lots`, `Sowings`, `Botanical identities`), `To review` | `frontend/src/collection/DashboardScreen.tsx`<br>`frontend/src/collection/DashboardSearch.tsx`<br>`frontend/src/events/recordWorkflows.ts` |

### Create forms and action flows for G-CORE 2–4 (and 5–9, 12)

| G-CORE step & workflow | Exact labels used in the guide | Source file(s) |
| --- | --- | --- |
| **G-CORE 2**: Create botanical identity | `New botanical identity`, dialog `Create a botanical identity`, section `Botanical name`, fields `Scientific name`, `Cultivar`, `Common name`, buttons `Cancel`, `Create botanical identity`, detail tabs `Overview`, `Reference`, `Taxonomy`, `Maps`, `Media`, `History`, button `Edit botanical identity` | `frontend/src/botanical-identities/BotanicalIdentityScreen.tsx`<br>`frontend/src/botanical-identities/identitySections.ts` |
| **G-CORE 2**: Add botanical profile | `Reference` tab → `Add profile`, dialog `Add botanical profile`, tabs `Description & origin` (`Description`, `Origin & distribution`), `Cultivation` (`Cultivation`), `Uses & warnings` (`Uses`, `Warnings`), button `Save profile` | `frontend/src/botanical-profiles/BotanicalProfilePanel.tsx`<br>`frontend/src/botanical-identities/BotanicalIdentityScreen.tsx` |
| **G-CORE 2**: Record manual native range | `Maps` tab → `Edit native range` (or `Edit botanical identity` → `Native range` tab), `Manage native range`, `Geographic place` (`Choose an exact named area`), `Add place`, `Done` (plus `Explore` → `Geography` → `Places` → `New local place`) | `frontend/src/botanical-identities/IdentityMaps.tsx`<br>`frontend/src/botanical-profiles/BotanicalNativeRangeManager.tsx`<br>`frontend/src/geography/GeographyOverview.tsx`<br>`frontend/src/geographic-places/GeographyScreen.tsx` |
| **G-CORE 3**: Create supplier | `Sourcing` → `Suppliers` → `New supplier`, dialog `Add supplier`, tabs `Essentials` (`Name`, `Kind`: `Seller`, `Nursery`, `Supermarket`, `Person`, `Exchange`, `Other`) and `Contact and notes` (`Website`, `Email`, `Phone`, `Notes`), button `Add supplier` | `frontend/src/suppliers/SupplierScreen.tsx` |
| **G-CORE 3**: Create order | `Sourcing` → `Orders` → `New Order`, sections `Order context` (`Supplier`, `Order date`, `Order reference`) and `Transaction and notes` (`Total price`, `Currency`, `Notes`), button `Create Order`, detail action `Add seed lot` | `frontend/src/orders/OrderScreen.tsx` |
| **G-CORE 3**: Partial dates & Create seed lot | `Precision` (`Unknown`, `Year`, `Year and month`, `Complete date`, plus `Year`, `Month`, `Day`); `Collection` → `Seeds` → `New seed lot`, dialog `Add seed lot`, tabs `Identity` (`Botanical identity`, `Lot label`), `Inventory` (`Quantity`, `Quantity value`, `Quantity unit`: `seeds`, `g`, `mg`, `Approximately`, `Lifecycle`: `Active`, `Storage location`, `Create location`), `Acquisition` (`Source`: `Purchased`, `Purchase order`, `Review purchase context / use Order date`, `Apply purchase context`, `Supplier`, `Acquisition date`), `Origin` (`Material provenance`, `Precise provenance site`), `Seed details` (`Harvest date`, `Expected viability until`, `Notes`), button `Add seed lot` | `frontend/src/seed-lots/PartialDateField.tsx`<br>`frontend/src/seed-lots/SeedLotScreen.tsx`<br>`frontend/src/orders/PurchaseContext.tsx` |
| **G-CORE 4**: Start sowing from seed lot | `Start sowing`, Step 1 `Sowing details` with tabs `Essentials` (`Source SeedLot`, `Sowing label`, `Sowing date`), `Material & location` (`Quantity sown`: `Unknown`, `Seed count`, `Weight`, `Amount`, `Approximate`, `Current location`), `Cultivation` (`Substrate`, `Method / container`, `Pretreatment`, `Minimum °C`, `Maximum °C`, `Environment / conditions`), `Notes`, button `Review seed usage`; Step 2 `Seed usage` (`What happens to the source seed lot?`: `Keep inventory unchanged`, `Use part of the lot`, `Record partial use; quantity stays unknown`, `Use the whole lot`), button `Start sowing` | `frontend/src/seed-lots/SeedLotScreen.tsx`<br>`frontend/src/propagation/SeedLotSowingWizard.tsx`<br>`frontend/src/sowings/SowingFormFields.tsx` |
| **G-CORE 4**: Germination observation | `Record germination` (or `Germination` tab → `Add observation`), dialog `Add germination observation`, fields `Date`, `Newly germinated`, button `Save observation` | `frontend/src/sowings/SowingScreen.tsx`<br>`frontend/src/sowings/GerminationSection.tsx` |
| **G-CORE 4**: Create Plant and Plant group from Sowing | `Create Plant`, `Create Plant group`, dialogs `Create Plant from Sowing` / `Create Plant group from Sowing`, tabs `Essentials` (`Botanical identity`, `Label`, `Quantity`: `Unknown`, `Exact count`, `Approximate count`, `Count`, `Current location`), `Origin` (`Collection-entry date`), `Lifecycle & notes` (`Notes`), section `Sowing after creation` (`Keep active`, `Complete Sowing`, `Mark failed`, `Abandon Sowing`), buttons `Create Plant`, `Create Plant group` | `frontend/src/sowings/SowingScreen.tsx`<br>`frontend/src/propagation/SowingDescendantWizard.tsx`<br>`frontend/src/plants/PlantFormFields.tsx` |
| **G-CORE 4**: Extract Plant & Supported reversals | `Extract plant`; `Original Plant group` → `Reintegrate into group` → `Reintegrate into original group?` → `Reintegrate Plant` / `Confirm and reintegrate`; `⋯` (`More record actions`) → `Undo creation` → `Undo plant creation` / `Undo plant group creation` / `Undo sowing creation` | `frontend/src/plants/PlantScreen.tsx`<br>`frontend/src/propagation/CreationReversal.tsx` |
| **G-CORE 5**: Journal entries & Photos | `Journal` tab → `Add entry` / `Add the first entry`, `Entry type`, `When did it happen?` (`Today, YYYY-MM-DD`, `Another date`, `Date unknown`), `Occurrence date`; entry `Photos` → `Add new media` → `Image file`, `Caption`, `Attribution (shared media)`, `Save`; record `Photos` tab → `Add media` / `Add new media` / `Link existing`, `⋯` → `Set as primary`, `Primary`, `Remove primary` | `frontend/src/events/EventJournal.tsx`<br>`frontend/src/events/OccurrenceDateChoice.tsx`<br>`frontend/src/photos/PhotosSection.tsx` |
| **G-CORE 6–9 & 12**: Locations, Bulk move, Schedule, Harvest, Cuttings, Labels, Saved views, CSV | Verified in `LocationScreen.tsx`, `BulkLocation.tsx`, `ScheduleScreen.tsx`, `HarvestScreen.tsx`, `HarvestForm.tsx`, `StoredMaterial.tsx`, `ConversionDialog.tsx`, `LineagePanel.tsx`, `AncestryExplorer.tsx`, `Cuttings.tsx`, `CuttingForm.tsx`, `CuttingDetails.tsx`, `LabelsScreen.tsx`, `QrDestinationDialog.tsx`, `SavedViews.tsx`, `ImportExportScreen.tsx` | See respective screen components under `frontend/src/` |
