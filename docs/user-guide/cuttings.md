# Cuttings and vegetative propagation

Alongside seed propagation, Florabase tracks vegetative propagation in **Collection** → **Cuttings**.
You can record cuttings taken from a mother **Plant** or **Plant group** in your collection (or
brought in from outside), run one or more **Rooting attempts**, log rooting checks, establish rooted
**Plants** or **Plant groups**, and keep an accurate record of failed or uncounted attempts.

For a deeper reference on the vegetative propagation model, see the [Cuttings feature
guide](../cuttings.md).

## Material lots vs. rooting attempts

Florabase splits vegetative propagation into two linked records:

1. **Material lots** (the **Material lots** view in **Collection** → **Cuttings**): the physical
   batch of cuttings you took or acquired — `Stem cutting`, `Leaf cutting`, or `Root cutting`.
2. **Rooting attempts** (the **Rooting attempts** view in **Collection** → **Cuttings**): a specific
   rooting run started from a material lot, tracking substrate, hormone treatment, container,
   environment, temperatures, rooting checks, and status (`Active`, `Completed`, `Failed`, or
   `Abandoned`).

You can record a material lot and start its first rooting attempt in a single form, or record the
material lot first and start rooting attempts from it later.

## 1. Take or add a cuttings material lot

1. Open **Collection** → **Cuttings** and click **Take or add cuttings** (or open a mother **Plant**
   or **Plant group** detail page and click **Take cuttings** in the header).
2. In the **Take or add cuttings** (or **Take cuttings**) form, fill in the **Source and material**
   section:
   - **Material type**: choose `Stem cutting`, `Leaf cutting`, or `Root cutting`.
   - **Source**: choose `From the collection`, `Purchased`, `Gift or exchange`, `Self-collected`,
     `Other`, or `Unknown`.
     - If you chose `From the collection`, select **Mother record type** (`Plant` or `Plant group`)
       and pick the **Mother specimen**.
     - If you chose an external source, you can optionally pick a **Supplier**, **Purchase order**
       (when **Source** is `Purchased`), **Geographic place**, or **Provenance site**.
     - If you chose `Other`, enter a **Source detail**.
   - **Botanical identity**: prefilled automatically when a **Mother specimen** is selected;
     otherwise select the botanical identity.
   - **Material lot label** (optional): for example, `June softwood tips`.
   - **Taken or acquired on**: choose a **Precision** (`Unknown`, `Year`, `Year and month`, or
     `Complete date`).
   - **Initial lot quantity**: choose `Unknown`, `Exact count`, or `Approximate count` (and enter
     the piece count when exact or approximate is selected).
   - **Location** (optional): choose a holding location enabled for **Vegetative lots**.
   - **Notes** (optional).
3. In the **Rooting setup** section, decide whether to start rooting right away:
   - To stick the cuttings into substrate immediately, tick **Start rooting attempt immediately**:
     - Keep **Use all cuttings in this attempt** ticked to use the whole lot, or untick it to use
       only part of the lot (if the lot quantity is approximate, confirm the remainder under
       **Confirmed remaining quantity**).
     - Keep **Use the taken or acquired date** ticked, or untick it to enter a separate **Started
       on** date.
     - Fill in optional **Attempt label**, **Starting quantity** (shown when not using an exact
       whole-lot count), **Location** (enabled for **Rooting attempts**), **Substrate**, **Hormone
       treatment**, **Container**, **Environment**, and **Minimum** or **Maximum** temperature
       (`(°C)`).
       <!-- TODO(DOC-04 verify): AttemptSetupFields builds temperature labels dynamically as `{key === "temperature_min_c" ? "Minimum" : "Maximum"} temperature (°C)` (`frontend/src/ui-pages/Cuttings/CuttingForm.tsx:337-338`). -->
     - Click **Save cuttings**.
   - To save just the material lot first, leave **Start rooting attempt immediately** unticked and
     click **Save cuttings**.

<!-- TODO(DOC-04 screenshot): Take or add cuttings form, highlight Source and material fields and Start rooting attempt immediately checkbox -->

## 2. Start a rooting attempt from a material lot

If you saved a material lot without starting an attempt (or if you still have material left in an
active lot for a second batch):

1. Open the material lot from **Collection** → **Cuttings** (**Material lots**).
2. Click **Start rooting attempt** in the top action bar.
3. In the **Start rooting attempt** dialog:
   - Choose **Material use**:
     - `Use all cuttings`
     - `Use part of the lot` (if the lot quantity is approximate, confirm what stays behind in
       **Confirmed remaining quantity**)
     - `Leave stock unchanged`
   - Under **Rooting setup**, fill in optional **Attempt label**, **Started on** (`Unknown`, `Year`,
     `Year and month`, or `Complete date`), **Starting quantity** (`Unknown`, `Exact count`, or
     `Approximate count`, shown when not using an exact whole-lot count), **Location** (enabled for
     **Rooting attempts**), **Substrate**, **Hormone treatment**, **Container**, **Environment**,
     and **Minimum** or **Maximum** temperature (`(°C)`).
4. Click **Start attempt**.

Florabase opens the new **Rooting attempt** detail page.

## 3. Log rooting observations (including unknown or zero counts)

While an attempt is rooting, you can log periodic checks without having to establish a plant yet:

1. On the **Rooting attempt** detail page, click **Log rooting observation** in the top action
   bar.
2. In the **Log rooting observation** dialog, under **Rooting check**:
   - Choose the **Stage**:
     - `Inspection` (general check)
     - `Callus` (callus tissue forming)
     - `Root initials` (first root bumps visible)
     - `Rooted` (roots formed)
     - `Loss` (some or all pieces lost to rot or drying)
   - Set **Observed on** (`Unknown`, `Year`, `Year and month`, or `Complete date`).
   - In **Observed rooted count** (optional):
     - Enter a whole number (such as `4`, or `0` if you checked and none have rooted yet), or leave
       it blank if you did not count or cannot tell without disturbing the substrate.
   - Optionally enter **Notes**.
3. Click **Save observation**.

If you need to fix a typo in an observation later, open the attempt's **Observations** tab and click
**Correct observation** next to that entry in the **Rooting observations** list.

<!-- TODO(DOC-04 screenshot): Rooting attempt detail page with Rooting observations and Log rooting observation dialog -->

## 4. Establish a Plant or Plant group from a rooting attempt

Once one or more cuttings have rooted and you pot them up as living collection specimens:

1. On the active **Rooting attempt** detail page, click **Establish Plant or group** in the top
   action bar.
2. In the **Establish Plant or Plant group** dialog, under **Established specimen**:
   - Choose **Result** as either `Individual Plant` (a single individually tracked specimen) or
     `Plant group` (a batch of rooted cuttings managed together).
   - Optionally enter a **Label**.
   - If you chose `Plant group`, set **Group quantity** (`Unknown`, `Exact count`, or
     `Approximate count`).
   - Set **Collection entry date** (`Unknown`, `Year`, `Year and month`, or `Complete date`).
   - Select an optional **Location** (enabled for **Plants**).
   - Choose **Attempt after establishment**:
     - `Keep attempt active` (if other cuttings in the same attempt are still rooting)
     - `Mark completed` (if the rooting run is finished)
     - `Mark abandoned` (if you are abandoning the unrooted remainder)
   - Optionally enter **Notes**.
3. Click **Establish**.

The newly established **Plant** or **Plant group** appears under **Established offspring** on the
rooting attempt's **Offspring** tab. When you open that plant or group and check its **Lineage**
tab, you will see the full vegetative chain:

Mother `Plant` (or `Plant group`) → *Taken as vegetative material* → `Vegetative lot` → *Started
rooting attempt* → `Rooting attempt` → *Established from rooting attempt* → new `Plant` (or `Plant
group`).

<!-- TODO(DOC-04 screenshot): Establish Plant or Plant group dialog on a Rooting attempt, highlight Result (Individual Plant / Plant group) and Attempt after establishment -->

## 5. Record failed or still-unknown attempts

Not every batch of cuttings roots, and you do not always know the exact rooted count:

- **Attempts where the rooted count is still unknown**: leave **Observed rooted count** (in **Log
  rooting observation**) and **Rooted count** (in **Edit rooting attempt**) empty. In the attempt's
  header, **Rooting** displays `Rooting pending` while the attempt is active (or
  `Rooted count unrecorded` once ended), and you can still click **Establish Plant or group**
  whenever at least one cutting is ready.
- **Failed or abandoned attempts**: if none of the cuttings survived:
  1. On the **Rooting attempt** detail page, click **Edit attempt**.
  2. In the **Edit rooting attempt** dialog, under **Outcome**, change **Status** to `Failed` (or
     `Abandoned`).
  3. Set **Rooted count** to `0` (or leave it empty if uncounted) and optionally set **Ended on**.
  4. Click **Save attempt**.
  When **Rooted count** is `0` or the attempt is no longer `Active`, Florabase hides the **Establish
  Plant or group** button while keeping the failed attempt and its observations in your history so you
  can learn which substrates, hormones, or seasons worked and which did not.

## 6. Undo a cutting operation

Just like seed propagation, guided cutting transitions can be reversed if you made a mistake:

- To undo establishing a plant or group from a rooting attempt, open the **Rooting attempt** detail
  page, open its **Offspring** tab, find the offspring under **Established offspring**, click
  **Undo establishment**, and in the **Undo cutting operation** dialog click **Confirm undo**.
- To undo starting a rooting attempt from a material lot (once any established offspring have been
  undone first), click **Undo starting attempt** under **Rooting overview** on the attempt's
  **Overview** tab, and click **Confirm undo**.

Next, continue to **[Finding things and printing labels](finding-things-and-labels.md)** to learn how
to search, filter, save custom views, print QR labels, and scan or paste a label link.
