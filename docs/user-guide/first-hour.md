# Your first hour

This walkthrough takes you from a freshly installed, empty Florabase instance to a working
collection. You will sign in, explore **Today**, create a **Botanical identity** with a profile and
native range, add a **Supplier**, **Order**, and **Seed lot**, start a **Sowing**, log a
**Germination** check, create an individual **Plant** and a **Plant group**, extract a plant from
that group, and reverse an operation.

## 1. Sign in and tour the empty Today screen

1. Open your Florabase address in your browser.
2. Enter your owner **Login name** and **Password**, then click **Sign in**.
3. You land on **Today**, your daily workspace. On a brand-new database, every counter starts at
   `0`:
   - **Next work** shows **Overdue** (`0`), **Due today** (`0`), and **Next 7 days** (`0`), with the
     message: *"No planned activities. Schedule work when your collection needs it."*
   - **Recent activity** shows: *"No recent activity. Journal observations and recorded operations
     will appear here."*
   - **Record** lists quick shortcuts for daily tasks (**Add Journal entry**, **Record harvest**,
     **Record sowing**, **Take or add cuttings**, **Move plants / groups**, **Complete scheduled
     work**, and **Schedule activity**).
   - **Collection snapshot** shows `0` for **Individual Plants**, **Plant groups**, **Seed lots**,
     **Sowings**, and **Botanical identities**.
   - **To review** lists helpful follow-up checks (all `0` at the start) and links to **Sowings**,
     **Seeds**, and **Botanical identities**.
4. To create your first record, either click **Botanical identities** at the bottom of **To review**,
   click **+ New** → **New botanical identity** at the top of the left navigation panel, or select
   **Explore** → **Botanical identities** in the left rail.

<!-- TODO(DOC-04 screenshot): Today screen on a fresh database, zero state, highlight Collection snapshot, To review and + New menu -->

## 2. Create a botanical identity, profile, and manual native range

Every packet of seeds or living plant in your collection refers to a **Botanical identity**.

### Create the botanical identity

1. In **Explore** → **Botanical identities**, click **New botanical identity** (or choose **+ New** →
   **New botanical identity** from the left panel).
2. In the **Create a botanical identity** dialog, fill in the **Botanical name** section:
   - **Scientific name** (required): enter the botanical name, for example `Solanum lycopersicum`.
   - **Cultivar** (optional): enter a cultivar name without quotation marks, for example
     `San Marzano`.
   - **Common name** (optional): enter an everyday name, for example `Plum tomato`.
   > **Tip:** If the person who runs your server has installed the optional botanical reference data
   > (see [Optional reference data](reference-data.md)), typing at least two letters in
   > **Scientific name** shows matching names as suggestions. Pick one to fill in the
   > field, or keep typing your own name: any name is accepted, with or without a suggestion.
3. Click **Create botanical identity**.

Florabase opens the new identity's detail page on the **Overview** tab.

<!-- TODO(DOC-04 screenshot): Create a botanical identity dialog, filled in, highlight Scientific name, Cultivar, Common name, and Create botanical identity button -->

### Add a botanical profile

To store cultivation notes and reference details on this identity:

1. On the botanical identity's detail page, select the **Reference** tab.
2. In the **Botanical profile** panel, click **Add profile** (this opens the **Edit botanical
   identity** editor on the **Reference** tab, showing the **Add profile** form).
3. Use the three section tabs in the **Add profile** form to enter as much or as little as you need:
   - **Description & origin**: **Description** and **Origin & distribution**.
   - **Cultivation**: **Cultivation** notes (soil, light, hardiness, watering).
   - **Uses & warnings**: **Uses** and **Warnings** (such as toxicity or thorns).
4. Click **Save profile** (then click **Close editor** if you want to return to the read-only detail
   tabs).

### Record a manual native range

To record the geographic areas where this plant is native:

1. On the botanical identity's detail page, select the **Maps** tab and click **Edit native range**
   (or click **Edit botanical identity** at the top right and select the **Native range** tab).
2. In the **Native range** panel, click **Manage native range**.
3. In the **Geographic place** picker (**Choose an exact named area**), type or select a place (such
   as a country, region, or local place) and click **Add place**.
   > **Tip:** Florabase comes pre-loaded with standard world countries and regions. If you ever need
   > a custom town, valley, or local area that is not in the list, open **Explore** → **Geography**,
   > click **Places** under **Geographic records**, and click **New local place** to add one under
   > any parent region.
4. Repeat **Add place** if the species is native to more than one area, then click **Done**.
5. Close the edit dialog if it is open, then view the **Maps** or **Overview** tab on the botanical
   identity to see the recorded native range.

<!-- TODO(DOC-04 screenshot): Botanical identity Maps or Native range dialog, with a native range place added, highlight Manage native range and Add place -->

## 3. Create a supplier, an order, and a seed lot

Next, record where a packet of seeds came from and add it to your collection, using partial dates and
approximate or unknown quantities (see [Core concepts: Partial and unknown dates, and approximate
quantities](concepts.md#partial-and-unknown-dates-and-approximate-quantities)).

### Create a supplier

1. In the left rail, select **Sourcing** → **Suppliers**, then click **New supplier** (or use
   **+ New** → **New supplier**).
2. On the **Essentials** tab of the **Add supplier** dialog:
   - Enter the supplier **Name** (required), for example `Alpine Seed Exchange`.
   - Select the **Kind** (required): `Seller`, `Nursery`, `Supermarket`, `Person`, `Exchange`, or
     `Other`.
3. Optionally switch to the **Contact and notes** tab to fill in **Website**, **Email**, **Phone**,
   or **Notes**.
4. Click **Add supplier**.

### Create an order

1. In the left rail, select **Sourcing** → **Orders**, then click **New Order**.
2. Under **Order context**:
   - In **Supplier**, select the supplier you just created.
   - In **Order date**, choose a **Precision** (`Unknown`, `Year`, `Year and month`, or
     `Complete date`). For example, choose `Year and month` and enter `2025` for **Year** and `2`
     for **Month**.
   - Optionally enter an **Order reference** (such as an invoice or order number).
3. Under **Transaction and notes**:
   - Optionally enter **Total price** and a three-letter **Currency** code (such as `EUR` or `USD`),
     or leave both blank.
   - Optionally add **Notes**.
4. Click **Create Order**.

### Create a seed lot with partial or unknown values

From the saved **Order** detail page, you can create a linked seed lot directly:

1. On the **Order** detail page, click **Add seed lot** (or go to **Collection** → **Seeds** and
   click **New seed lot**).
2. In the **Add seed lot** dialog, work through the section tabs:
   - **Identity**:
     - Select your **Botanical identity** (required).
     - Optionally enter a **Lot label** (for example, `2025 packet A`).
   - **Inventory**:
     - Under **Quantity**, you can either record an approximate amount (enter `50` in
       **Quantity value**, choose `seeds` in **Quantity unit**, and tick **Approximately**) or leave
       **Quantity value** empty to record an unknown quantity.
     - Leave **Lifecycle** set to `Active`.
     - Optionally pick a **Storage location** (or click **Create location** inline to add one, such
       as `Seed Box`).
   - **Acquisition**:
     - Set **Source** to `Purchased`.
     - If you started from the **Order** page, **Purchase order** and **Supplier** are already
       filled in. If you started from **Collection** → **Seeds**, select the order in **Purchase
       order**, then click **Review purchase context / use Order date** and click **Apply purchase
       context** to copy the order's supplier and date automatically.
     - In **Acquisition date**, you can keep the partial date copied from the order (such as
       `Year and month`), change **Precision** to `Year` or `Unknown`, or enter a `Complete date`.
   - **Origin** and **Seed details** (optional):
     - On **Origin**, you can select a **Material provenance** place or **Precise provenance site**.
     - On **Seed details**, you can set a partial or complete **Harvest date** and
       **Expected viability until** date, plus **Notes**.
3. Click **Add seed lot**.

   > **Tip:** To enter several packets in a row, click **Save and add another** instead. Florabase
   > saves the seed lot and keeps the form open with a fresh draft that keeps only the **Botanical
   > identity**. The **Sowings**, **Plants** and **Plant groups** creation forms have the same
   > button (a new sowing keeps its **SeedLot**; a new plant or group keeps its **Botanical
   > identity**).

<!-- TODO(DOC-04 screenshot): Add seed lot dialog on Inventory or Acquisition tab, showing Approximately quantity and partial Acquisition date -->

## 4. Sow the seeds, record germination, create plants, extract, and reverse

Now follow your seeds through germination into living plants.

### Start a sowing from the seed lot

1. On your new **Seed lot** detail page, click **Start sowing** in the top action bar.
2. In Step 1 (**Sowing details**) of the **Start sowing** dialog:
   - On the **Essentials** tab, **Source SeedLot** is locked to your seed lot. Optionally add a
     **Sowing label** (for example, `Spring Tray 1`) and choose a **Sowing date** (`Complete date`,
     `Year and month`, `Year`, or `Unknown`).
   - On the **Material & location** tab, choose **Quantity sown** (`Unknown`, `Seed count`, or
     `Weight`). If you choose `Seed count`, enter an **Amount** (for example, `12`) and optionally
     tick **Approximate**. You can also pick a **Current location**.
   - Optionally fill in the **Cultivation** tab (**Substrate**, **Method / container**,
     **Pretreatment**, **Minimum °C**, **Maximum °C**, **Environment / conditions**) and the
     **Notes** tab.
   - Click **Review seed usage**.
3. In Step 2 (**Seed usage**), choose **What happens to the source seed lot?**:
   - **Keep inventory unchanged**: leaves the seed lot quantity and `Active` status as they are.
   - **Use part of the lot** (or **Record partial use; quantity stays unknown** when the seed lot
     quantity is unknown): keeps the seed lot `Active` and updates its remaining quantity if you
     enter one.
   - **Use the whole lot**: marks the seed lot `Exhausted` (and sets remaining quantity to `0` if a
     quantity was tracked).
4. Click **Start sowing**.

Florabase opens the new **Sowing** detail page.

<!-- TODO(DOC-04 screenshot): Start sowing wizard on Step 2 Seed usage, highlight What happens to the source seed lot options and Start sowing button -->

### Record a germination observation

When seedlings appear (or when you check the tray and see none yet):

1. On the **Sowing** detail page, click **Record germination** in the header (or select the
   **Germination** tab and click **Add observation**).
2. In the **Add germination observation** dialog:
   - Enter the exact **Date** of your check (`YYYY-MM-DD`).
   - Enter **Newly germinated** as a whole number (for example, `8`; enter `0` if you checked the
     tray and saw no new seedlings today).
3. Click **Save observation**.

The sowing's total germinated count and observation list update immediately.

### Create an individual Plant and a Plant group from the sowing

Once seedlings are ready to pot on or plant out, you can promote them into an individual **Plant**, a
**Plant group**, or both:

1. On the **Sowing** detail page, click **Create Plant**.
2. On the **Create Plant** page (showing `From <sowing>` under the heading):
   - On **Essentials**, **Botanical identity** is prefilled from the sowing. Optionally enter a
     **Label** (for example, `Specimen #1`) and pick a **Current location**.
   - On **Origin**, optionally set the **Collection-entry date**.
   - On **Lifecycle & notes**, optionally add **Notes**.
   - On **Sowing after creation**, keep **Keep active** selected so you can also create a plant
     group from the remaining seedlings.
   - Click **Create Plant**.
3. On the new plant's detail page, click the sowing link next to **Source sowing** in the header
   summary (or in the header lineage strip) to return to your **Sowing** detail page.
4. Click **Create Plant group**.
5. On the **Create Plant group** page (showing `From <sowing>` under the heading):
   - On **Essentials**, optionally enter a **Label** (for example, `Bed A row`), set **Quantity** to
     `Exact count` (or `Approximate count` / `Unknown`) and enter a **Count** (for example, `6`).
   - On **Sowing after creation**, choose **Keep active** (if more seedlings remain in the tray) or
     **Complete Sowing** (if you have potted up everything from this sowing).
   - Click **Create Plant group**.

### Extract an individual Plant from the Plant group

If one plant in your **Plant group** stands out and you want to track it individually:

1. On the **Plant group** detail page, click **Extract plant** in the top action bar.
2. In the **Extract plant** dialog:
   - On **Essentials**, optionally give the extracted plant a **Label** (for example, `Selected
     early fruiter`) and confirm its **Current location**.
   - Optionally set a **Collection-entry date** on **Origin** or **Notes** on **Lifecycle & notes**.
3. Click **Extract plant**.

Florabase creates the new individual **Plant** and opens its detail page. If the **Plant group** had
an exact count greater than `1`, its count automatically decreases by `1`. The new plant's
**Overview** displays an **Original Plant group** panel linking back to the group it came from.

<!-- TODO(DOC-04 screenshot): Extracted Plant Overview page, highlight Original Plant group panel and Reintegrate into group button -->

### Perform a supported reversal

Florabase lets you reverse guided propagation and extraction steps if you made a mistake. Reversing
an action restores the parent record's prior count and status while keeping the reversed record in
history (marked `Reintegrated` or `Reversed`) so your audit trail stays intact.

Here are the supported reversals in the product and how to run one right now:

- **Reintegrate an extracted Plant back into its Plant group** (fastest to try right after
  extraction):
  1. On the extracted **Plant** detail page (**Overview** tab), find the **Original Plant group**
     panel.
  2. Click **Reintegrate into group**.
  3. In the **Reintegrate into original group?** dialog, click **Reintegrate Plant** (if you had
     already logged observations on the plant, click **Confirm and reintegrate**).
  4. The plant is marked `Reintegrated`, and the **Plant group** gets its previous count and
     `Active` state back.
- **Undo a Plant or Plant group created from a Sowing**:
  1. Open the **Plant** or **Plant group** that was created from a sowing.
  2. Click the `⋯` (**More record actions**) button in the top right of the detail header and
     choose **Undo creation**.
  3. In the `Undo plant creation` (or `Undo plant group creation`) dialog, click the confirm button
     (`Undo plant creation` or `Undo plant group creation`). The sowing is restored to its
     pre-creation state, and the reversed plant or group remains in history as `Reversed`.
     <!-- TODO(DOC-04 verify): CreationReversal builds the dialog title and confirm button dynamically as `Undo ${labels[kind]} creation` where `labels` maps to `"sowing"`, `"plant"`, and `"plant group"` (`frontend/src/propagation/CreationReversal.tsx:33,204,211,348`). -->
- **Undo a Sowing started from a Seed lot**:
  1. If the sowing has any active descendant plants or plant groups, undo their creation first
     (newest first).
  2. On the **Sowing** detail page, click **Undo creation** in the top action bar, then confirm
     `Undo sowing creation` in the dialog. The source **Seed lot** gets its previous quantity and
     `Active` status back.

> **Note:** Two other workflows also support one-click reversal in the same way: **Undo Seed lot creation** on a seed lot converted from stored harvest seeds (covered in [Harvest and seed
> saving](harvest-and-seed-saving.md)) and **Undo starting attempt** / **Undo establishment** on
> cuttings (covered in [Cuttings and vegetative propagation](cuttings.md)).

You now have your first botanical identity, supplier, order, seed lot, sowing, germination record,
plant, and plant group. Continue to **[Daily use](daily-use.md)** to learn how to record journal
observations, upload photos, schedule activities, and move records in bulk.
