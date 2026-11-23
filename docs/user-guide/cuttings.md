# Cuttings and vegetative propagation

Alongside seed propagation, Florabase tracks vegetative propagation in **Collection** → **Cuttings**.
You can record cuttings taken from a mother **Plant** or **Plant group** in your collection (or
brought in from outside), run one or more **Rooting attempts**, log rooting checks, establish rooted
**Plants** or **Plant groups**, and keep an accurate record of failed or uncounted attempts.

For a deeper reference on the vegetative propagation model, see the [Cuttings feature
guide](../cuttings.md).

## Material lots vs. rooting attempts

Florabase splits vegetative propagation into two linked records:

1. **Material lot** (`Material lots` tab in **Collection** → **Cuttings**): the physical batch of
   vegetative pieces you took or acquired — `Cutting`, `Division`, `Scion`, `Offset / pup`, `Layer`,
   or `Other vegetative`.
2. **Rooting attempt** (`Rooting attempts` tab in **Collection** → **Cuttings**): a specific rooting
   run started from a material lot, tracking substrate, hormone treatment, container, environment,
   rooting checks, and outcome (`Active`, `Completed`, `Failed`, or `Abandoned`).

You can record a material lot and start its first rooting attempt in a single form, or record the
material lot first and start rooting attempts from it later.

## 1. Take or add a cuttings material lot

1. Open **Collection** → **Cuttings** and click **Take or add cuttings** (or open a mother **Plant**
   or **Plant group** detail page and click **Take cuttings** in the header).
2. In the **Take or add cuttings** form, fill in the **Material lot** section:
   - **Botanical identity** (required): prefilled if you started from a mother plant or group;
     otherwise select the botanical identity.
   - **Label** (optional): for example, `June softwood tips`.
   - **Material type**: choose `Cutting`, `Division`, `Scion`, `Offset / pup`, `Layer`, or
     `Other vegetative`.
   - **Collected or acquired on**: choose `Unknown`, `Year`, `Year and month`, or `Complete date`.
   - **Quantity**: choose `Unknown`, `Exact count`, or `Approximate count`. If you choose exact or
     approximate, enter the **Count** of pieces (for example, `6`).
   - **Location** (optional): choose a storage or holding location enabled for **Vegetative lots**.
   - **Origin**:
     - Choose `Mother Plant` or `Mother Plant group` if you took the cuttings from a specimen in your
       collection, and select the mother record.
     - Or choose `External / acquired` if the cuttings came from outside your collection (you can
       then optionally pick a **Supplier**, **Order**, **Geographic place**, or **Provenance site**).
   - **Notes** (optional).
3. Decide whether to start rooting right away:
   - To stick the cuttings into substrate immediately, tick **Start rooting attempt immediately**,
     fill in the **Rooting attempt** section (**Attempt label**, **Started on**, **Starting
     quantity**, **What happens to the source material lot?**, **Substrate**, **Hormone treatment**,
     **Container**, **Environment**, **Location**, **Attempt notes**), and click **Save cuttings**.
   - To save just the material lot first, leave **Start rooting attempt immediately** unticked and
     click **Save cuttings**.

<!-- TODO(DOC-04 screenshot): Take or add cuttings form, highlight Material type, Quantity, Origin (Mother Plant), and Start rooting attempt immediately checkbox -->

## 2. Start a rooting attempt from a material lot

If you saved a material lot without starting an attempt (or if you still have material left in an
active lot for a second batch):

1. Open the **Material lot** from **Collection** → **Cuttings** (`Material lots` tab).
2. Click **Start rooting attempt** in the top action bar.
3. In the **Start rooting attempt** dialog:
   - Under **Essentials**:
     - Optionally enter a **Label** (for example, `Perlite propagation box`).
     - Set **Started on** (`Complete date`, `Year and month`, `Year`, or `Unknown`).
     - Set **Starting quantity** (`Unknown`, `Exact count`, or `Approximate count`, plus **Count**).
     - Choose **What happens to the source material lot?**:
       - `Keep lot quantity unchanged`
       - `Use part of the lot` (and optionally enter the **Remaining lot quantity** if the lot has a
         known count)
       - `Use the whole lot (mark exhausted)`
   - Under **Rooting setup**, optionally record **Substrate**, **Hormone treatment**, **Container**,
     **Environment**, **Location** (a location enabled for **Rooting attempts**), and **Notes**.
4. Click **Start attempt**.

Florabase opens the new **Rooting attempt** detail page.

## 3. Log rooting observations (including unknown or zero counts)

While an attempt is rooting, you can log periodic checks without having to establish a plant yet:

1. On the **Rooting attempt** detail page, under **Rooting observations**, click **Log rooting
   observation**.
2. In the **Log rooting observation** dialog:
   - Choose the **Stage**:
     - `Inspection` (general check)
     - `Callus` (callus tissue forming)
     - `Root initials` (first root bumps visible)
     - `Rooted` (roots formed)
     - `Loss` (some or all pieces lost to rot or drying)
   - Set **Observed on** (`Complete date`, `Year and month`, `Year`, or `Unknown`).
   - In **Rooted count** (optional):
     - Enter a whole number (such as `4`, or `0` if you checked and none have rooted yet), or leave
       it blank if you did not count or cannot tell without disturbing the substrate.
   - Optionally enter **Notes**.
3. Click **Save observation**.

If you need to fix a typo in an observation later, click **Correct observation** next to that entry
in the **Rooting observations** list.

<!-- TODO(DOC-04 screenshot): Rooting attempt detail page with Rooting observations and Log rooting observation dialog -->

## 4. Establish a Plant or Plant group from a rooting attempt

Once one or more cuttings have rooted and you pot them up as living collection specimens:

1. On the active **Rooting attempt** detail page, click **Establish Plant or group** in the top
   action bar.
2. In the **Establish Plant or Plant group** dialog:
   - Under **Resulting record**:
     - Choose **Create** as either `Plant` (a single individually tracked specimen) or `Plant group`
       (a batch of rooted cuttings managed together).
     - Optionally enter a **Label** and select a **Current location** (enabled for **Plants**).
     - Set **Collection-entry date** (`Complete date`, `Year and month`, `Year`, or `Unknown`).
     - If you chose `Plant group`, set **Group quantity** (`Unknown`, `Exact count`, or
       `Approximate count`, plus **Count**).
   - Under **Attempt outcome**:
     - Choose **Attempt after establishment**:
       - `Keep active` (if other cuttings in the same attempt are still rooting)
       - `Complete attempt` (if the rooting run is finished)
       - `Abandon remaining` (if you are discarding the unrooted remainder)
     - Optionally update **Rooted count** and **Notes**.
3. Click **Establish**.

The newly established **Plant** or **Plant group** appears under **Established offspring** on the
rooting attempt page. When you open that plant or group and check its **Lineage** tab, you will see
the full vegetative chain:

Mother `Plant` (or `Plant group`) → *Taken as vegetative material* → `Material lot` → *Started
rooting attempt* → `Rooting attempt` → *Established from rooting attempt* → new `Plant` (or `Plant
group`).

<!-- TODO(DOC-04 screenshot): Establish Plant or Plant group dialog on a Rooting attempt, highlight Create (Plant / Plant group) and Attempt after establishment -->

## 5. Record failed or still-unknown attempts

Not every batch of cuttings roots, and you do not always know the exact rooted count:

- **Attempts where the rooted count is still unknown**: leave **Rooted count** empty when logging
  observations or editing the attempt. Florabase shows the rooting outcome as `Rooted count unknown`
  (never a false `0 rooted`), and you can still click **Establish Plant or group** whenever at least
  one cutting is ready.
- **Failed or abandoned attempts**: if none of the cuttings survived:
  1. On the **Rooting attempt** detail page, click **Edit attempt**.
  2. Under **Outcome**, change **Status** to `Failed` (or `Abandoned`).
  3. Set **Rooted count** to `0` (or leave it empty if uncounted) and optionally set **Ended on**.
  4. Click **Save attempt**.
  When **Rooted count** is `0` or the attempt is no longer `Active`, Florabase hides the **Establish
  Plant or group** button while keeping the failed attempt and its observations in your history so you
  can learn which substrates, hormones, or seasons worked and which did not.

## 6. Undo a cutting operation

Just like seed propagation, guided cutting transitions can be reversed if you made a mistake:

- To undo establishing a plant or group from a rooting attempt, open the **Rooting attempt** detail
  page, find the offspring under **Established offspring**, click **Undo establishment**, and click
  **Confirm undo**.
- To undo starting a rooting attempt from a material lot (once any established offspring have been
  undone first), click **Undo starting attempt** under **Rooting overview** on the attempt page, and
  click **Confirm undo**.

Next, continue to **[Finding things and printing labels](finding-things-and-labels.md)** to learn how
to search, filter, save custom views, print QR labels, and scan or paste a label link.
