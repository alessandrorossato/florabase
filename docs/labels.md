# Physical lookup labels

LABEL-001 prints labels for **SeedLot, Plant, and PlantGroup**. Open **Print label** in an existing
record detail, or open **Tools → Labels** (mobile: **More → Labels**). The detail action prepares one
copy of that record. The composer can add other supported records through the existing searchable
record picker, change copy counts, remove entries, and preview up to 36 labels on one A4 sheet.
Identical record selections increase copies. The picker shows the existing UUID to distinguish
otherwise identical records; it does not assign a new inventory or accession number.

The sheet is temporary browser state. Leaving Labels or refreshing discards edits to the sheet. A
detail-action URL includes the one initial record, so refreshing that URL starts again with that
record's single copy. Nothing is written to PostgreSQL or browser storage. Already selected labels
are a snapshot of the names loaded by the composer; reopen it after correcting a record's name.

## Content and QR lookup

Each label has the current BotanicalIdentity `display_label` as its strongest text, **Seed lot**,
**Plant**, or **Plant group**, the record's existing optional label, a small Florabase wordmark, and
a locally generated black-and-white SVG QR. Seed lot follows the existing detail terminology.
Cultivar and partial names retain the identity API's display semantics. An absent optional record
label is omitted. A defensively blank identity display is marked unavailable, never inferred.
Botanical text wraps within four lines and optional context within two; exceptionally long names
may truncate. The QR never shrinks to accommodate text. Labels contain no photos, Supplier,
provenance, Location, quantities, dates, lifecycle, or notes.

The QR contains only an absolute URL built afresh from the authenticated session's configured
canonical origin, the existing root/hash record route, and the exact validated UUID. The session
response uses `FLORABASE_CANONICAL_ORIGIN`; the browser Host, proxy aliases, current path, and
forwarded headers do not choose the public address:

- `https://your-florabase.example/#/seeds/<UUID>`
- `https://your-florabase.example/#/plants/<UUID>`
- `https://your-florabase.example/#/plant-groups/<UUID>`

This uses Florabase's existing canonical-origin setting, without another public-URL setting or
trusting request Host/forwarded headers. Production requires HTTPS. Development can use its
configured loopback origin (`http://localhost:5173`); that address is not portable to a phone.
Print from the normal operator-facing Florabase address. The scanning device must reach that address.
Origins with credentials, paths, query strings, or fragments are rejected; a missing origin stops
label creation.

Current URL queries, hashes, session cookies, bearer tokens, API keys, CSRF tokens, and temporary
credentials are never copied into QR data. UUIDs are identifiers, not credentials. Opening the URL
uses the existing detail and normal owner login flow; the hash survives login. Existing protected
record APIs retain their authorization, malformed-UUID validation, and not-found behavior. There
are no public record endpoints or QR-specific record pages.

Creation and printing perform no external QR or image requests. QR codes use four white modules on
each edge, medium error correction, square black modules, and a fixed 22 × 22 mm SVG including the
quiet zone. No logos or decorations modify them.

## Printing and physical checks

Use a fresh A4 portrait sheet. The fixed layout starts at the top left of its print area and fills
left to right: **4 columns × 9 rows**, at most 36 labels. There are no gutters. Each border-box is
exactly **50 mm wide × 30 mm high**, including 1.5 mm internal padding. The grid occupies 200 × 270 mm;
A4's 210 × 297 mm leaves **5 mm left/right** and **13.5 mm top/bottom** margins. Labels cannot split
across pages. Only the sheet prints; app navigation, controls, helper text, and record-detail UI are
hidden. Preview columns adapt to screen width; print columns remain fixed.

In the browser print dialog:

1. Choose A4 portrait and **100% / Actual size**.
2. Disable **Fit to page** and other scaling; retain the stylesheet's margins.
3. Disable browser headers and footers.
4. On a plain-paper trial, check the first and last row/column alignment against your chosen sheet,
   measure the 50 × 30 mm cell pitch, and scan representative Seed lot, Plant, and Plant group QRs.

Printers and drivers can override scale and margins. Confirm physical size and scanability before
printing adhesive stock, especially with long names or long installation hostnames. An A4 stock
with different pitch, gutters, or margins will not match this fixed layout. Partially used sheets,
custom sizes/layouts, thermal protocols, template editing, persistent print jobs, and server PDF
generation are outside LABEL-001. The browser's ordinary Save as PDF remains available.

## Dependency

`qrcode-generator` **2.0.4** is a small, dependency-free QR encoder with maintained upstream JavaScript
and TypeScript declarations. Only its module matrix API is used; React constructs SVG elements
without injecting generated HTML. Its [MIT license](https://github.com/kazuhikoarase/qrcode-generator/blob/master/LICENSE)
permits inclusion in Florabase's AGPL-3.0-or-later application while retaining the upstream copyright
and license notice in `frontend/public/qrcode-generator-LICENSE.txt`, shipped with the production
assets. The exact dependency and integrity are pinned in the frontend manifest and lockfile. No UI
framework or runtime decoder is added.
