# Harvest and seed saving

When your plants produce fruit, flowers, leaves, roots, or seeds, Florabase lets you record the
**Harvest**, track any material you keep in storage as **Stored material**, convert saved seeds into
a brand-new **Seed lot**, and trace the full **Lineage** chain from your original seed packet all
the way to the new one.

## 1. Record a harvest

You can start a harvest either from the plant or group you are harvesting from, or from the
**Harvests** directory.

1. Open the producing **Plant** or **Plant group** and click **Record harvest** in the top action
   bar (or go to **Collection** → **Harvests** and click **Record harvest**).
2. In the **Record harvest** dialog, work through the four section tabs:
   - **Source**:
     - If you opened the dialog from a plant or group, the source is already locked in.
     - Otherwise, choose **Source type** (`Plant` or `Plant group`) and select the producing specimen
       in **Harvest source**.
   - **Harvest**:
     - Optionally enter a **Label** (for example, `Late summer picking`).
     - Set the **Occurrence date** (`Complete date`, `Year and month`, `Year`, or `Unknown`).
   - **Materials collected**:
     - Every harvest includes at least one material line. To save seeds that you can later convert
       into a **Seed lot**, set **Material** to `Seeds` on a line (you can also click **Add material
       line** to record `Fruit`, `Flowers`, `Leaves`, `Roots`, `Stem / shoot`, `Whole plant`, or
       `Other` collected at the same time).
     - Set **Quantity** to `Not recorded`, `Item count`, or `Weight` (`g` or `kg`), and if you enter
       a count or weight, choose **Amount**, **Unit** (for weight), and **Precision** (`Exact` or
       `Approximate`).
     - Optionally add a short **Description** for that line (for example, `Dry cleaned seed from
       first truss`).
   - **Notes**:
     - Optionally enter general harvest **Notes**.
3. Click **Record Harvest**.

Florabase opens the new **Harvest** detail page and automatically logs a corresponding `Harvest`
entry in the producing plant or group's **Journal**.

<!-- TODO(DOC-04 screenshot): Record harvest dialog on Materials collected tab, showing a Seeds material line with Quantity and Precision, highlight Add material line and Record Harvest -->

## 2. Track collected material as Stored material

Recording a harvest records what you *gathered*. If you put a collected material line into a jar,
envelope, drying tray, or freezer to keep in stock, you promote that line to **Stored material**:

1. On the **Harvest** detail page, scroll to the **Stored material** section.
2. Find the collected material line (for example, your `Seeds` line, which initially says
   `Not tracked as stored material`) and click **Track stored material**.
3. In the **Track stored material** dialog:
   - Under **Remaining now**, confirm what is going into storage:
     - Choose `Exact`, `Approximate`, or `Unknown` (`Remaining now precision` is built from the
       **Remaining now** fieldset label). <!-- TODO(DOC-04 verify): InventoryDialog QuantityFields builds `${label} precision`, `${label} dimension`, `${label} amount`, and `${label} unit` dynamically from `label="Remaining now"` (`frontend/src/harvests/InventoryDialog.tsx:67-128`). -->
     - If `Exact` or `Approximate` is selected, choose `Item count` or `Weight`, enter the amount,
       and (for weight) select `mg`, `g`, or `kg`.
       > **Tip for seed saving:** If you plan to convert stored seeds by weight into a **Seed lot**,
       > record the weight in `g` or `mg` (`Seed lot` inventory uses `seeds`, `g`, or `mg`).
   - Under **Storage Location** (optional), select a location that has the **Stored material**
     scope enabled (or leave it blank, which displays as `Not recorded` under **Storage**).
4. Click **Track stored material**.

The line is now `Active` in your stored inventory. You can view and manage all stored harvest items
across your entire collection at any time by selecting **Collection** → **Harvests** → **Stored
material** in the left navigation panel.

<!-- TODO(DOC-04 screenshot): Harvest detail page Stored material section with an active tracked Seeds line, highlight Track stored material / Edit stored material and Create Seed lot buttons -->

> **Recording uses or disposal of stored material:** Whenever you consume, process, gift, or discard
> part of a stored line without creating a seed lot, click **Record disposition** on that line. In
> the **Record disposition** dialog, choose **Disposition** (`Consumed`, `Processed`, `Discarded`,
> `Gifted`, or `Used for propagation`), choose **Material leaving stock** (`Partial amount` to keep
> the line `Active`, or `Use all remaining` to mark it `Depleted`), enter **Amount used** (and
> **Confirmed remaining now** when the balance is approximate), optionally set **Disposition date**
> and **Notes**, and click **Record disposition**.

## 3. Convert stored seeds into a new Seed lot

When an active **Stored material** line has **Material** set to `Seeds`, you can convert all or part
of it into a new **Seed lot** ready for sowing:

1. On the **Harvest** detail page (under **Stored material**) or in **Collection** → **Harvests** →
   **Stored material**, find your active `Seeds` line and click **Create Seed lot**.
2. In the **Create Seed lot from stored seeds** dialog, fill in the three sections:
   - **Source stored material**:
     - Under **Material leaving stock**, choose either **Partial amount** (if some seeds remain in
       harvest storage) or **Use all remaining** (if you are putting all of the stored seeds into the
       new seed lot; this marks the stored material line `Depleted`).
   - **Resulting Seed lot**:
     - **Botanical identity** is locked to the producing plant or group's botanical identity so
       lineage stays consistent.
     - Optionally select a **Seed lot Location** (a location enabled for **Seed lots**).
     - Optionally enter a **Seed lot label** (for example, `2025 Home-saved F1`), an **Expected
       viability until** date, and **Seed lot notes**.
   - **Conversion quantities**:
     - Under **Seed lot quantity**, choose `Unknown`, `Exact`, or `Approximate`. If you choose
       `Exact` or `Approximate`, select `Item count` (for seed count) or `Weight`, enter the amount,
       and (for weight) choose `g` or `mg`.
     - If you chose **Partial amount** from an approximate stored line, confirm what stays behind
       under **Confirmed remaining now**.
3. Click **Create Seed lot**.
4. In the confirmation banner that appears (`Seed lot created.`), click **Open Seed lot** (or open
   the new lot from **Collection** → **Seeds**).

The new **Seed lot** has its **Source** automatically set to `Produced from my collection` and its
**Harvest date** populated from the harvest's occurrence date.

<!-- TODO(DOC-04 screenshot): Create Seed lot from stored seeds dialog, highlight Material leaving stock, Resulting Seed lot label, Seed lot quantity, and Create Seed lot button -->

### Undoing a seed lot conversion

If you converted the wrong amount or chose the wrong stored line:

1. On the new **Seed lot** detail page (under **Harvested seed origin**) or on the **Harvest** detail
   page (under **Stored material**, after clicking `Show` `Seed lot conversions`), click **Undo Seed
   lot creation**. <!-- TODO(DOC-04 verify): ConversionHistory builds the toggle button label dynamically as `{open ? "Hide" : "Show"} Seed lot conversions` (`frontend/src/harvests/ConversionHistory.tsx:126`). -->
2. In the **Undo Seed lot creation** dialog, click **Confirm undo**.

As long as no sowings have been started from the converted seed lot yet, Florabase marks the seed
lot `Reversed` in history and restores the stored material line's previous remaining quantity and
`Active` state.

## 4. Read the lineage chain

Now that you have converted harvested seeds into a new **Seed lot**, you can inspect the complete
multi-generation chain (`Seed lot` → `Sowing` → `Plant` / `Plant group` → harvested new `Seed lot`):

1. Open your newly converted **Seed lot** detail page.
2. On the **Overview** tab, look at the **Harvested seed origin** section: it shows the transferred
   quantity and an **Open originating Harvest and stored material** link back to the harvest.
3. Select the **Lineage** tab on the **Seed lot** detail page:
   - Under **Recorded upstream path**, Florabase displays the step-by-step chain leading to this
     seed lot, showing each ancestor record and the relationship between them (for example,
     `Seed lot` → *Sown from seed lot* → `Sowing` → *Propagated from sowing* → `Plant` / `Plant
     group` → *Converted from harvested material* → your new `Seed lot`).
4. For the full interactive graph across generations, click **Explore material ancestry** in the
   **Lineage** tab (or select **Explore** → **Lineage** in the left rail and pick your new **Seed
   lot**):
   - You can see the **Current record**, `Generation` `1` (the producing plant or group), and
     `Generation` `2` (the sowing and original seed lot), with the harvest and conversion evidence
     shown on the connecting edge. <!-- TODO(DOC-04 verify): AncestryExplorer builds generation column headings dynamically as `Generation ${String(generation.depth)}` (`frontend/src/lineage/AncestryExplorer.tsx:480`). -->
   - Click any record in the chain to jump straight to it.

<!-- TODO(DOC-04 screenshot): Seed lot Lineage tab or Explore Lineage view showing the multi-step chain from original Seed lot through Sowing and Plant/Plant group to the converted Seed lot -->

Next, continue to **[Cuttings and vegetative propagation](cuttings.md)** to learn how to propagate
plants from cuttings, divisions, and other vegetative material.
