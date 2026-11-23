# Optional reference data

Florabase is designed to work completely offline and without any external botanical datasets
installed. When you want richer botanical context, your instance operator can optionally provide
local reference snapshots or enable external lookups.

## What works without optional reference data

Every core feature in Florabase works out of the box on a fresh installation without any optional
reference files:

- Creating and editing **Botanical identities**, writing **Botanical profiles**, and recording
  manual **Native ranges** (using the built-in world countries and regions or your own local
  places).
- Managing **Suppliers**, **Orders**, **Seed lots**, **Sowings**, **Cuttings**, **Plants**, **Plant
  groups**, **Harvests**, **Stored material**, and **Locations**.
- Recording **Journal** entries, uploading **Photos**, scheduling work in **Schedule**, tracing
  **Lineage**, printing **Labels**, and using **Import / Export**.
- Viewing **Explore** → **Geography** → **Collection origins** and **Native ranges** on the built-in
  offline world basemap (Natural Earth boundaries).

## What optional reference data adds

When optional reference sources are available, they enrich **Botanical identities** and the pages
under **Explore**:

- **World Flora Online (WFO) local snapshot**: enables local taxonomy matching, accepted names, and
  classification browsing in **Explore** → **Taxonomy** and on the **Taxonomy** tab of a
  **Botanical identity**.
- **Kew WCVP local native-range index**: provides reviewable native-range proposals on a
  **Botanical identity** and in **Explore** → **Geography** → **Native ranges**.
- **GBIF online lookup**: lets you explicitly search and confirm a GBIF reference link on a
  **Botanical identity** and load occurrence density evidence for one species at a time in
  **Explore** → **Geography** → **Species distribution**.
- **OpenStreetMap tiles**: adds an optional street-level basemap when zooming in on provenance sites
  in **Explore** → **Geography** → **Collection origins**.

In every case, external or snapshot data is **proposal-based**: a reference source proposes a link or
range, and you decide whether to confirm it. Nothing overwrites your own collection records or manual
notes automatically.

## Checking which sources are used

To see the reference sources Florabase supports, what each one is used for, how it is reached, and
its licence, open **Settings** → **Data sources** in the left rail.

<!-- TODO(DOC-04 screenshot): Settings Data sources screen showing the Sources in use table -->

## Where the operator sets it up

Installing local reference snapshots (such as WFO and WCVP files) or enabling optional map tiles is
configured by the operator who runs the Florabase server. See the [Installation and operations
guide](../installation.md) for setup details.
<!-- TODO(DOC-04 after batch 12): Update this note once the operator setup for the WFO/WCVP reference data mount in docs/installation.md lands in batch 12. -->

Next, continue to **[Troubleshooting](troubleshooting.md)** for solutions to common everyday
questions.
