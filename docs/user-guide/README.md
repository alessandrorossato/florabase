# Florabase User Guide

Welcome to Florabase. This guide shows you how to record, follow, and care for a living plant
collection from day to day.

## Who this guide is for

This guide is written for home growers, seed savers, and small-collection keepers who already have
a running Florabase instance.

You do not need any programming, server, or database knowledge to use Florabase or follow this
guide. If Florabase is not installed yet, or if you need server administration instructions
(such as backups, upgrades, or resetting a forgotten owner password on the server), see the
[Installation and operations guide](../operate/installation.md).

## Signing in

When you open your Florabase web address in a browser, the sign-in screen appears:

1. Enter your **Login name**.
2. Enter your **Password**.
3. Click **Sign in**.

<!-- TODO(DOC-04 screenshot): Sign-in screen, empty form, highlight Login name, Password and Sign in button -->

Once signed in, Florabase opens on **Today**. Your session stays active in the browser until you
click **Sign out** in the bottom-left panel footer (or in **Account and settings** on a phone).

## How the app is laid out

Florabase uses a workspace layout called the **Workbench**:

- **Workspace rail (left side on desktop, bottom bar on phones and compact screens)**: switches
  between the main areas of the app. Choosing **Collection**, **Activity**, **Explore** or
  **Sourcing** opens its **Overview** page, with one tile per section, counts and first actions:
  - **Today** — your daily overview, global collection search, planned work due soon, recent
    activity, and review prompts.
  - **Collection** — your physical material and where it lives:
    - **Seeds** (seed lots)
    - **Sowings**
    - **Cuttings** (vegetative material lots and rooting attempts)
    - **Plants** (open **Plant groups** from the Plants page)
    - **Harvests** (open **Stored material** from the Harvests page)
    - **Locations** (your shelves, benches, beds, and storage boxes)
  - **Activity** — dated observations and planned work across your collection:
    - **Journal** (observations, movements, repotting, flowering, fruiting, measurements, and
      other events)
    - **History** (recorded propagation, extraction, and conversion operations)
    - **Schedule** and **Calendar** (planned activities and reminders)
  - **Explore** — botanical knowledge, ancestry, media, and maps across your collection:
    - **Botanical identities** (species, subspecies, varieties, and cultivars)
    - **Taxonomy**
    - **Lineage** (material ancestry from seed or cutting to descendant records)
    - **Media** (shared photos and illustrations)
    - **Geography** (**Collection origins**, **Species distribution**, **Native ranges**, plus
      **Places** and **Provenance sites**)
  - **Sourcing** — where acquired material came from:
    - **Suppliers**
    - **Orders**
  - **Settings** — personal and collection tools (in the left rail on desktop, or via the
    **Account and settings** button at the top right on mobile):
    - **Account** (change your password)
    - **Theme** (light, dark, or system appearance)
    - **Media** (defaults for saving local copies and for attribution and licence on your uploads)
    - **Labels** (printable plant and seed labels with QR codes)
    - **Import / Export** (CSV export and guided CSV import)
    - **Data sources** (status of optional external botanical references)
    - **Help**
- **Quick actions in the rail and panel**:
  - **Record** (in the rail on desktop and the bottom bar on mobile): opens a quick sheet to log a
    Journal entry, schedule work, complete due work, record a harvest or sowing, or open a printed
    label from its QR link.
  - **Search** (in the rail, or press `Ctrl K` / `⌘K` or `/`): opens **Search and commands** so you
    can jump straight to any record, section, saved view, or creation form.
  - **+ New** (at the top of the section panel): creates a **New seed lot**, **New sowing**,
    **New plant**, **New plant group**, **Record harvest**, **New botanical identity**,
    **New supplier**, **New location**, or **New local place** from anywhere.
- **Fields that point to your own records** (such as **Botanical identity**, **Supplier**,
  **SeedLot**, **Current location** or **Geographic place**) are searchable lists: click the field
  and start typing to narrow the list, use the arrow keys and Enter to pick an entry, or press
  Escape to close the list. Short fixed choices (such as **Kind** or **Precision**) stay ordinary
  drop-down lists.

<!-- TODO(DOC-04 screenshot): Workbench on Today, desktop layout, highlight left workspace rail, section panel with + New, Record button, and Search -->

## Reading order

If you are opening a fresh Florabase instance for the first time, read the first three pages in
order. After that, you can jump to whichever task you need.

1. **[Core concepts](concepts.md)** — How Florabase separates what a plant *is* (botanical
   identity) from what you *have* (seed lots, sowings, cuttings, plants, groups, harvests, and
   locations), and how partial dates and approximate quantities work.
2. **[Your first hour](first-hour.md)** — A step-by-step walkthrough from an empty database to your
   first botanical identity, supplier, order, seed lot, sowing, germination count, individual
   plant, plant group, extraction, and reversal.
3. **[Daily use](daily-use.md)** — Recording Journal entries (for today, a past date, or an unknown
   date), adding photos and picking a primary photo, scheduling and completing activities on
   **Today**, and moving records in bulk.
4. **[Harvest and seed saving](harvest-and-seed-saving.md)** — Recording a harvest from a plant or
   plant group, tracking stored material, converting saved seeds into a new seed lot, and reading
   the full lineage chain.
5. **[Cuttings and vegetative propagation](cuttings.md)** — Recording cuttings material lots,
   running rooting attempts, logging rooting checks, establishing rooted plants or groups, and
   recording failed or unknown-count attempts.
6. **[Finding things and printing labels](finding-things-and-labels.md)** — Using global search,
   filters, and **Saved views**, printing QR labels in **Small**, **Medium**, or **Large** format,
   and looking up a record from a label link or camera scan.
7. **[Your data: CSV import and export](your-data.md)** — Exporting your records to CSV, previewing
   and confirming a CSV import, and where to find backup, restore, and upgrade instructions.
8. **[Optional reference data](reference-data.md)** — What optional botanical reference snapshots
   (taxonomy, native ranges, species distribution) add, and what works out of the box without them.
9. **[Troubleshooting](troubleshooting.md)** — What to do if your session expires while editing,
   if a save fails, if you forget your password, if a list looks empty, or if you use Florabase on
   a phone.
