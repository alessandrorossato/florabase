# Finding things and printing labels

As your collection grows, Florabase gives you three fast ways to find records — global search and
filters, **Saved views**, and the **Search and commands** palette — plus printable physical labels
with QR codes that open straight to the matching record.

## 1. Global search and filters

### Search across your whole collection on Today

At the top of **Today**, the search bar searches across all of your records at once (**Botanical
identities**, **Seed lots**, **Sowings**, **Plants**, **Plant groups**, **Locations**, **Suppliers**,
**Geographic places**, **Provenance sites**, and **Journal** events):

1. Open **Today** in the left rail.
2. Type a scientific name, cultivar, common name, record label, supplier, or note into **Search your
   collection…**.
3. Matching records appear immediately below the toolbar, grouped with clear record-type badges.
   Click any result to open its detail page.
4. To narrow results by structured criteria (with or without a search word):
   - Click **Filters** next to the search box.
   - Choose one or more filters: **Record type**, **Botanical identity**, **Supplier**,
     **Collection location**, **Geographic provenance place**, **Provenance site**, **Lifecycle**,
     **Event kind**, or **Year**.
   - Click **Done**.
5. Active filters appear as removable chips below the toolbar. Click a chip's remove button or click
   **Reset** (in the **Filters** drawer) to clear all filters and return to the normal **Today**
   overview.

<!-- TODO(DOC-04 screenshot): Today screen with active search query and Filters drawer or active filter chips, highlight Search your collection, Filters button, and matching results -->

### Search within any directory

Every directory (**Seeds**, **Sowings**, **Cuttings**, **Plants**, **Harvests**, **Locations**,
**Journal**, **History**, **Schedule**, **Botanical identities**, **Suppliers**, **Orders**, and
**Geography**) has its own search box and **Filters** button at the top of the page.

By default, collection directories show your **Active** records first so historical or reversed
records do not clutter daily work. To inspect historical records in a directory, open **Filters** and
change **Lifecycle** (or **State**) to `All` or to the specific historical state you want.

### Jump anywhere with Search and commands

From any screen in Florabase, click **Search** in the left rail (or press `Ctrl K` / `⌘K`, or press
`/` when not typing in a text field) to open **Search and commands**:

- Type into **Search records, sections and actions** to jump directly to a record, switch to a
  workspace section, open a saved view, or trigger a creation action (such as **New seed lot** or
  **New plant**).

## 2. Save and reopen custom views (Saved views)

Whenever you set up a search query or combination of filters that you want to reuse — on **Today**
or in any directory — you can save it as a named **Saved view**:

### Save a view

1. On **Today** or in any directory (such as **Collection** → **Plants** or **Collection** →
   **Seeds**), enter a search term or apply one or more **Filters**.
2. Click **Saved views** in the toolbar.
3. In the **Saved views** dialog, click **Save view**.
4. Enter a **View name** (for example, `Tomatoes in Greenhouse` or `Active 2025 Sowings`) and click
   **Save view**.

<!-- TODO(DOC-04 screenshot): Saved views dialog showing Save view form and a list of saved views with Open, Rename, Update with current view, and Delete -->

### Reopen or manage a saved view

You can reopen a saved view in three ways:

- **From the left navigation panel**: saved views appear automatically as indented links directly
  underneath their section in the navigation panel (up to 5 per section, with a `Show all` link
  when you have more). Click any saved view name in the panel to open that section with your exact
  filters applied. <!-- TODO(DOC-04 verify): WorkbenchShell builds the overflow link dynamically as `Show all ${String(itemSavedViews.length)} saved views` (`frontend/src/shell/WorkbenchShell.tsx:582`). -->
- **From the toolbar**: on **Today** or in the directory, click **Saved views**, then click **Open**
  next to the view you want.
- **From Search and commands**: press `Ctrl K` / `⌘K`, type the view's name, and select it.

Inside the **Saved views** dialog, you can also click **Update with current view** (to overwrite a
saved view with your currently active filters), **Rename**, or **Delete**.

## 3. Prepare and print physical labels

Florabase can print pot stakes, packet labels and storage tags with QR codes for any **Seed lot**,
**Plant**, **Plant group**, or **Stored material** item.

### Configure your QR destination (one-time setup)

Before printing QR labels for the first time, tell Florabase the web address (origin) that your phone
or browser uses to reach your Florabase instance:

1. In the left rail, open **Settings** → **Labels** (on a phone, tap **Account and settings** at the
   top right, then **Labels**).
2. In the **QR destination** banner, click **Edit QR destination**.
3. In the **QR destination** dialog, enter your installation's address in **Public / QR base URL**
   (for example, `https://flora.example.org` or `http://192.168.1.50:8080` — use the `http://` or
   `https://` origin without a trailing path).
4. Click **Save**.

### Add records to a label batch and inspect Print preview

You can open a single record directly in the label preview by clicking the `⋯` menu (or header
actions) on a **Seed lot**, **Plant**, **Plant group**, or **Stored material** row and clicking
**Print label**, or you can build a multi-label batch in **Settings** → **Labels**:

1. Open **Settings** → **Labels**.
2. Choose a **Label size**:
   - **Small** (compact tag showing the QR code, title, scientific name, and record code)
   - **Medium** (adds source/origin and date)
   - **Large** (adds botanical common name and current location)
   - Optionally click **Set as default** to remember your preferred size on this browser.
3. Under **Add material**:
   - Select **Record type** (`Seed lot`, `Plant`, `Plant group`, or `Stored material`).
   - Pick the item in **Record**.
   - Click **Add record**.
4. In the **Selected material** list, adjust **Copies** (`1` to `50`) for each row or click
   **Remove** if you added a row by mistake.
5. Scroll down to **Print preview**:
   - Verify the rendered label cards and QR codes. Every card displays the exact fields that will be
     printed at your chosen size.
6. When ready to print on paper or label stock, click **Print** in the top right (and in your
   browser's print dialog, keep scale at `100%` and disable headers and footers for best alignment).

<!-- TODO(DOC-04 screenshot): Settings Labels screen showing QR destination configured, Label size options, Selected material, and Print preview with QR codes -->

## 4. Look up a record from a label QR code

When you scan a printed Florabase QR label with your phone's camera app, it opens a link ending in
`#/l/<type>/<id>`, which takes you straight to that **Seed lot**, **Plant**, **Plant group**, or
**Stored material** detail page (asking you to sign in first if you are not signed in yet).

You can also look up any label directly inside Florabase without leaving the app:

1. Click **Record** in the left rail (or in the bottom bar on a phone).
2. In the **Record** sheet, find the **Open a label** section:
   - Paste or type the label's full URL or `#/l/...` path into **Label link** and click **Open**.
   - Or, on a device with a camera and a browser that supports barcode scanning, click **Scan with
     camera** and point the camera at the QR code on the label.
3. Florabase resolves the label and opens the matching record's detail page immediately.

<!-- TODO(DOC-04 screenshot): Record sheet open, highlight Open a label section with Label link input, Open button, and Scan with camera -->

Next, continue to **[Your data: CSV import and export](your-data.md)** to learn how to export your
collection to CSV spreadsheets, preview CSV imports, and find backup and upgrade instructions.
