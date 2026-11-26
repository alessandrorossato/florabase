# Core concepts

Before you add your first record, it helps to know how Florabase organises a living collection. Every
screen in the app follows a few simple ideas.

## Botanical identity vs. collection records

Florabase separates **what a plant is** from **what you physically have**.

### What a plant is: Botanical identity

A **Botanical identity** (`Explore` → `Botanical identities`) represents a kind of plant — a species,
subspecies, variety, or cultivar (for example, *Solanum lycopersicum* 'San Marzano' or *Lavandula
angustifolia*).

You create a botanical identity once. On that record you keep reference knowledge that applies to
every specimen of that kind:

- Its **Scientific name**, optional **Cultivar**, and **Common name**.
- A **Botanical profile** with notes on description, origin, cultivation, uses, and warnings.
- Its **Native range** (where the species occurs naturally in the wild).
- Optional taxonomy and distribution references.

### What you have: Collection records

Your physical packets, trays, pots, and beds live under **Collection**. Every collection record
points to a **Botanical identity**, and you can have many collection records for the same identity
over the years:

- **Seed lots** (`Collection` → `Seeds`): a packet, jar, or envelope of seeds you bought, received,
  collected, or harvested from your own plants.
- **Sowings** (`Collection` → `Sowings`): a specific sowing batch started from a seed lot (or
  recorded directly), where you track substrate, conditions, germination checks, and outcome.
- **Cuttings** (`Collection` → `Cuttings`): a **Vegetative lot** (stem, leaf, or root cuttings) and
  the **Rooting attempts** started from it.
- **Plants** (`Collection` → `Plants`): a single, individually tracked living specimen (such as a
  specimen tree, a mother plant, or a potted plant you observe on its own).
- **Plant groups** (`Collection` → `Plants` → `Plant groups`): a stand, flat, row, or bed of plants
  managed together as one unit. Whenever one plant in a group deserves individual tracking, you can
  **Extract plant** to turn it into an individual **Plant** without losing its history.
- **Harvests** and **Stored material** (`Collection` → `Harvests` and `Stored material`): fruit,
  flowers, leaves, roots, or seeds gathered from a **Plant** or **Plant group**. Collected lines can
  be tracked in storage as **Stored material**, and stored seeds can be converted into a new
  **Seed lot**.
- **Locations** (`Collection` → `Locations`): the places on your property where your material is kept
  (for example, `Greenhouse → Bench 2` or `Seed Fridge → Top Drawer`). Each location lists which
  record types it is **Used for** (`Plants`, `Sowings`, `Seed lots`, `Stored material`,
  `Vegetative lots`, `Rooting attempts`).

> **Note:** Your **Locations** are where your material currently sits in your home or garden. Where
> wild or acquired material originally came from in the world is recorded separately as
> **Material provenance** and **Precise provenance site** under `Explore` → `Geography`.

## Suppliers and Orders

Under **Sourcing**, you can record who provided your material and how it arrived:

- **Suppliers** (`Sourcing` → `Suppliers`): nurseries, seed companies, exchanges, markets, or
  people (`Seller`, `Nursery`, `Supermarket`, `Person`, `Exchange`, `Other`).
- **Orders** (`Sourcing` → `Orders`): a specific purchase or shipment from a supplier, with an optional
  **Order date**, **Order reference**, and **Total price** / **Currency**. Linking a **Seed lot** to
  an **Order** lets you reuse the supplier and order date with one click.

## Journal, History, and Schedule

Under **Activity** (and on individual records), Florabase keeps three distinct timelines:

- **Journal** (`Activity` → `Journal`, or the **Journal** tab on a **Plant** or **Plant group**):
  what happened to your plants — observations, movements, repotting, flowering, fruiting, pruning,
  treatments, measurements, transfers, or losses.
- **History** (`Activity` → `History`): structural collection operations, such as starting a sowing
  from a seed lot, creating plants from a sowing, extracting a plant from a group, or converting
  stored harvest seeds into a seed lot.
- **Schedule** (`Activity` → `Schedule` and `Calendar`): future work you plan to do (`Repot`,
  `Water`, `Fertilize`, `Move / relocate`, `Check germination`, `Check rooting`, `Inspect`,
  `Harvest`, `General follow-up`). Items due soon appear automatically on **Today** under **Next
  work**. When you complete a scheduled activity, you can optionally record the corresponding
  **Journal** entry in the same step.

## Lineage: where something came from

**Lineage** tracks the real physical chain of propagation in your collection — for example:

`Seed lot` → `Sowing` → `Plant` (or `Plant group`) → `Harvest` (stored seeds) → new `Seed lot`

Or for vegetative propagation:

Mother `Plant` (or `Plant group`) → `Vegetative lot` → `Rooting attempt` → new `Plant` (or `Plant
group`)

Florabase only shows lineage links that you explicitly recorded. Two plants that merely share the
same **Botanical identity** are never assumed to be parent and offspring unless they are connected by
a recorded sowing, extraction, harvest seed conversion, or cutting.

When you make a mistake in a guided propagation step — such as starting a sowing from the wrong seed
lot, creating a plant from a sowing, extracting a plant from a group, or converting stored seeds into
a seed lot — Florabase provides a supported **Undo** (or **Reintegrate into group**). Reversing an
operation restores the parent record's previous quantity and status while keeping the reversed record
in history so your audit trail is never silently erased.

## Partial and unknown dates, and approximate quantities

In a real collection, you rarely know every date or exact seed count. You might find an old seed
packet marked only "Autumn 2023", recall that a shrub was planted "sometime in 2021", or buy a packet
that holds roughly 50 seeds.

Florabase never forces you to invent a fake `"1 January"` date or a guessed `"0"` quantity.

### Partial and unknown dates

Many date fields (such as **Order date**, **Acquisition date**, **Harvest date**,
**Collection-entry date**, and **Journal** entry dates) let you choose the exact level of certainty
you have:

- **Unknown** (or **Date unknown** in the Journal): you do not know when it happened.
- **Year**: you know only the year (for example, `2024`).
- **Year and month**: you know the year and month (for example, `2024-03`), without guessing a day.
- **Complete date**: you know the exact year, month, and day (for example, `2024-03-15`).

In the **Journal**, **Today** is preselected by default so daily notes take one click, while
**Another date** and **Date unknown** are right next to it for backdated or undated notes.

### Unknown and approximate quantities

Quantity fields across Florabase distinguish between `"zero"`, `"approximate"`, and `"not counted"`:

- **Seed lots**: enter a **Quantity value** and choose a **Quantity unit** (`seeds`, `g`, or `mg`).
  Tick **Approximately** if the amount is an estimate. Leave **Quantity value** blank if the amount
  is unknown.
- **Sowings**: choose **Quantity sown** as **Unknown**, **Seed count**, or **Weight** (`g` or `mg`),
  and tick **Approximate** when estimating.
- **Plant groups**: choose **Quantity** as **Unknown**, **Exact count**, or **Approximate count**.
- **Harvests** and **Stored material**: choose whether a quantity is `Not recorded` / `Unknown`, an
  `Exact` count or weight, or an `Approximate` count or weight.

## Explore vs. a record's own tabs

You can look at your collection from two angles:

- **A record's own tabs**: when you open a specific **Botanical identity**, **Seed lot**, **Sowing**,
  **Plant**, **Plant group**, or **Harvest**, the tabs along the top (`Overview`, `Journal`,
  `Germination`, `Photos`, `Lineage`, `Reference`, `Maps`, `History`, and so on) show only data for
  that single record.
- **Explore** (`Explore` in the left rail): lets you browse across your whole collection at once —
  all **Botanical identities**, the **Taxonomy** tree, the collection-wide **Lineage** explorer, the
  shared **Media** library, and the **Geography** maps (**Collection origins**, **Species
  distribution**, and **Native ranges**).

Next, continue to **[Your first hour](first-hour.md)** to walk through creating your first records step by
step.
