# Daily use

Once your collection is set up, most of your time in Florabase goes into four everyday tasks:
checking **Today**, recording **Journal** entries, adding **Photos** (and picking a primary photo),
scheduling and completing work in **Schedule**, and moving records between **Locations**.

## Checking Today

Whenever you sign in or click **Today** in the left rail, you get an immediate summary of your
collection:

- **Next work** counts scheduled activities that are **Overdue**, **Due today**, or coming up in the
  **Next 7 days**, and lists the next due items with a link to **Open Schedule**.
- **Recent activity** shows your latest **Journal** observations and collection **History**
  operations side by side.
- **Record** gives you one-click buttons for **Add Journal entry**, **Record harvest**, **Record
  sowing**, **Take or add cuttings**, **Move plants / groups**, **Complete scheduled work**, and
  **Schedule activity**.
- **To review** highlights active sowings waiting for germination counts, purchased seed lots without
  an order link, and botanical identities you can enrich.

## Recording Journal entries on a Plant or Plant group

The **Journal** records observations and care events on an individual **Plant** or a **Plant group**.

### Open the Journal and choose when it happened

1. Open a **Plant** or **Plant group** from **Collection** → **Plants** (note that **Collection** →
   **Plants** lists your specimens and groups; see **Filters** to narrow the view).
   <!-- TODO(DOC-04 after batch 12): Once the Plants directory card-height layout fix lands, check whether any directory view note is needed. -->
2. On the record's detail page, select the **Journal** tab.
3. Click **Add entry** (or **Add the first entry** if the journal is empty).
   > **Shortcut:** You can also click **Record** in the left rail (or on **Today**) and choose **Add
   > Journal entry** to pick a **Plant** or **Plant group** and open its **Add entry** dialog from
   > anywhere.
4. Select an **Entry type**:
   - `Observation`, `Movement`, `Repotting`, `Flowering`, `Fruiting`, `Pruning`, `Treatment`,
     `Harvest`, `Transfer`, `Death`, `Loss`, `Discarded`, `Measurement` (for an individual
     **Plant**), or `Other`.
5. Under **When did it happen?**, choose one of the three date options:
   - **Today, YYYY-MM-DD** — **preselected by default** every time you open **Add entry**. If the
     event happened today, you do not need to touch the date controls at all.
   - **Another date** — select this to record an event from the past (or a specific date). An
     **Occurrence date** box appears where you can choose **Precision** as `Complete date`
     (**Year**, **Month**, **Day**), `Year and month` (**Year**, **Month**), or `Year` (**Year**).
   - **Date unknown** — select this when you know something happened (for example, the plant was
     repotted or flowered before you started keeping records) but do not know when. (Note:
     `Measurement` entries require a date of at least a year or month, so **Date unknown** is
     disabled for `Measurement`.)
6. Fill in **Notes** (plus any fields specific to that entry type, such as **Destination Location**
   for `Movement`, **Height** **Value** and **Unit** for `Measurement`, or **Phenological stage**
   for `Observation`, `Flowering`, and `Fruiting`).
7. Click **Add entry**.

<!-- TODO(DOC-04 screenshot): Add entry dialog on a Plant Journal tab, highlight Entry type, When did it happen radio buttons with Today preselected, Another date, and Date unknown -->

Try recording three entries in a row on the same plant or group:

1. An `Observation` keeping **Today, YYYY-MM-DD** preselected.
2. A `Repotting` or `Flowering` entry choosing **Another date** (with a complete or partial date).
3. An `Observation` or `Pruning` entry choosing **Date unknown**.

All three appear in the record's **Journal** tab (and in **Activity** → **Journal** across your
whole collection), clearly showing each entry's exact, partial, or unknown date.

## Photos and choosing a primary photo

You can attach photos both to individual **Journal** entries (to document how a plant looked on a
particular day) and directly to a record's **Photos** tab (where you can choose its **Primary**
photo).

### Upload a photo to a Journal entry

1. On a **Plant** or **Plant group** detail page, open the **Journal** tab.
2. Find the Journal entry you want to illustrate and click **Photos** on that entry's row.
3. In the entry's photos dialog, click **Add new media**.
4. Under **Image file**, choose a JPEG, PNG, or WebP image from your device.
5. Optionally enter a **Caption** and **Attribution (shared media)**.
6. Click **Save**.

The photo is now attached to that Journal entry (and also appears in the plant's **Photos** tab so
you can see all photos of that plant in one place).

### Upload photos to a record and set the primary photo

Every **Plant**, **Plant group**, **Seed lot**, **Harvest**, **Cuttings** record, and **Supplier**
can hold photos, and you can pick one photo as the record's **Primary** image (shown on its overview
header and directory card):

1. Open the record (for example, your **Plant** or **Plant group**) and select the **Photos** tab.
2. If you want to upload another image directly to the record, click **Add media** (or **Add new
   media**), choose an **Image file** (JPEG, PNG, or WebP), add an optional **Caption**, and click
   **Save**. (You can also click **Link existing** / **Link existing media** to attach an image that
   is already in your Florabase media library.)
3. To make a photo the record's main image, open the **`⋯`** (**Actions for ...**) menu on that
   photo card (or find the action buttons on the card) and click **Set as primary**.

The photo card displays a **Primary** badge, and the image immediately appears at the top of the
record's detail page. You can switch the primary photo to another image at any time by clicking
**Set as primary** on the other photo, or clear it with **Remove primary**.

<!-- TODO(DOC-04 screenshot): Plant Photos tab with uploaded photos, highlight Primary badge and Set as primary action in the photo card menu -->

> **Note on botanical identity and shared media:** A **Botanical identity** can also have reference
> images on its **Media** tab, and **Explore** → **Media** provides a shared media library across
> the app.
<!-- TODO(DOC-04 after batch 12): Expand the botanical identity Media tab and Explore Media asset flow once the batch 12 media redesign lands. -->

## Scheduling and completing activities

Use **Schedule** (`Activity` → **Schedule**) to plan upcoming care tasks and reminders.

### Schedule an activity

1. Open **Activity** → **Schedule** in the left rail (or click **Schedule activity** on **Today**, or
   click **Schedule activity** on a record's **Overview** tab).
2. Click **+ Schedule activity**.
3. In the **Schedule activity** dialog:
   - **Title** (required): enter a short description, for example `Check roots and pot on`.
   - **Activity kind**: choose `Repot`, `Water`, `Fertilize`, `Move / relocate`,
     `Check germination`, `Check rooting`, `Inspect`, `Harvest`, or `General follow-up`.
   - **Due date** (required): enter the date the task is due (`YYYY-MM-DD`). Pick today's date (or
     a date within the next 7 days) so you can see it immediately on **Today**.
   - **Target type**: keep `Whole collection / no specific record` for a general chore, or choose
     `Botanical identity`, `Seed lot`, `Sowing`, `Plant`, `Plant group`, `Location`,
     `Vegetative lot`, or `Rooting attempt` and select the target record.
   - **Planning notes** (optional): add any extra instructions.
4. Click **Save activity**.

<!-- TODO(DOC-04 screenshot): Schedule activity dialog, filled in with Title, Activity kind, Due date and a target Plant, highlight Save activity -->

### See the scheduled activity on Today

1. Click **Today** in the left rail.
2. Look at the **Next work** panel:
   - The counter for **Due today** (or **Overdue** / **Next 7 days**, depending on the due date you
     chose) has increased.
   - Your planned activity is listed directly under **Next work**, showing its title, kind, due
     status, and target record link.

> **Tip:** In **Activity** → **Schedule**, you can switch between the list view and the monthly grid
> at any time by clicking **Calendar** (or **Agenda** to return to the list), or open **Activity** →
> **Calendar** directly from the left navigation panel.

### Complete the activity and check Today again

1. From **Today**, click **Open Schedule** in the **Next work** panel (or click **Complete scheduled
   work** under **Record**).
2. On the row for your scheduled activity, click **Complete**.
3. In the **Complete activity** dialog, choose how to finish the task:
   - **Complete without a Journal Event**: marks the scheduled item `Completed` right away (click
     **Complete without Event**).
   - **Record what happened in Journal** (available when the target is an active **Plant** or
     **Plant group** and the activity kind maps to a Journal event such as `Repot`,
     `Move / relocate`, `Inspect`, or `General follow-up`): records a linked Journal entry at the
     same time. Confirm the **Event kind**, **Actual occurrence date** (and destination **Location**
     if it is a movement), add optional **Event notes**, and click **Complete and record Event**.
4. Click **Today** in the left rail:
   - In **Next work**, the due counter decreases and the completed item is no longer listed as due.
   - If you chose **Record what happened in Journal**, the new entry appears under **Recent
     activity**.

<!-- TODO(DOC-04 screenshot): Complete activity dialog showing Complete without a Journal Event and Record what happened in Journal options -->

## Locations and moving records in bulk

When you rearrange shelves, move seedlings out to a cold frame, or reorganize seed packets, you can
move up to 100 active records to a target **Location** in one step.

### Create a Location (if you do not have one yet)

1. In the left rail, open **Collection** → **Locations**, then click **New location** (or choose
   **+ New** → **New location**).
2. In the **New location** dialog (**Create a location**):
   - Enter a **Name** (required), for example `Greenhouse Bench 1` or `Cold Frame`.
   - Choose a **Parent location** (or keep `No parent (root location)`).
   - Under **Used for**, keep the checkboxes ticked for the record types that can live at this
     location (`Plants`, `Sowings`, `Seed lots`, `Stored material`, `Vegetative lots`,
     `Rooting attempts`). By default, all six are ticked for a new location.
   - Click **Create location**.

### Move records in bulk

Bulk move is available in **Collection** → **Seeds**, **Sowings**, **Plants** (covering both
individual plants and plant groups), and **Harvests** → **Stored material**.

1. Open the directory for the records you want to move — for example, **Collection** → **Plants**
   (or **Collection** → **Seeds**).
2. In the directory results bar above the list, click **Select records**.
3. Tick the checkbox on each active record you want to move (or click **Select visible** to select
   every eligible active record currently shown).
4. Open the **Actions ▾** menu in the selection bar and click **Move to location**.
5. In the **Move to location** dialog:
   - Under **Target Location**, choose the destination location (only active locations that have the
     matching **Used for** scope enabled are offered).
   - Click **Preview move**.
6. Review the preview table:
   - Florabase shows how many records **Will move** and whether any are **Already at this
     Location**.
7. Click **Apply move (N)** to confirm.

Every moved record now shows the new **Location** on its overview and directory card. When you move
**Plants** or **Plant groups**, Florabase also records a `Movement` entry in each moved specimen's
**Journal**.

<!-- TODO(DOC-04 screenshot): Move to location dialog at Preview move step, highlight Target Location, Will move summary, and Apply move button -->

Next, continue to **[Harvest and seed saving](harvest-and-seed-saving.md)** to learn how to harvest
from a plant or group, store seeds, convert them into a new seed lot, and trace the full lineage.
