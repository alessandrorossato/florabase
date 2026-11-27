# Purchase Orders — ORDER-001

An Order records one real purchase transaction. A Supplier is the reusable source party, and a
SeedLot is one physical lot. An Order can group zero or many SeedLots, including several separate
packets of the same BotanicalIdentity. Linking never combines lots or changes inventory.

## Recorded knowledge

Orders use UUIDv7 identifiers and UTC creation/update timestamps. Every descriptive field is
optional: Supplier, `ordered_on`, order reference, total price/currency and notes. An empty Order
is valid when its transaction details are unknown.

`ordered_on` reuses PartialDate (year, month or complete valid date). Null means unknown. It is
independent of a SeedLot's acquisition/receipt date. Copying Order date is a labelled optional action in the purchase preview, confirmed on Apply; it is never automatic.

Price means the known **total transaction price**, including only whatever total the operator
actually knows. Non-negative values are allowed, including an explicitly known zero. The API
accepts decimal text with at most 24 digits on each side of the decimal point. Unscaled PostgreSQL
Numeric retains the exact value and decimal scale; responses use decimal text without binary
floating-point arithmetic, rounding to two places or exponent notation. Currency and total price
must be supplied or cleared together. Currency is exactly three uppercase ASCII letters (ISO-style,
for example EUR/USD/GBP); this is syntax validation, without a currency catalogue or external service.
Negative, non-finite, exponent, binary float and numeric JSON input are rejected.

There are no currency conversions or cross-currency totals. No lot price, shipping/tax allocation,
accounting, payment details, line items, SKU catalogue or ordered-but-not-received inventory is inferred.

References trim surrounding whitespace, permit Unicode, reject control characters and have a
255-character bound. References need not be unique. Notes normalize line endings, trim surrounding
whitespace and permit newlines/tabs within 20,000 characters.

## Explicit SeedLot links and Supplier consistency

A SeedLot has zero or one `order_id`. Only `purchased` and `purchased_fruit` sources may link; an
incompatible source returns a typed 409 conflict. The operator must correct source knowledge
explicitly. Existing unlinked SeedLots of every source kind remain valid, with no migration backfill.

When both Supplier IDs are known, they must match. Either side may be null; no missing Supplier is
fabricated. Changing an Order Supplier checks every linked lot, including historical ones, and
rejects a contradiction. SeedLot creation/correction checks the same rule. Order row locks serialize
transaction edits/deletion with lot assignments so a concurrent edit cannot validate stale Supplier
knowledge. These are owning-service rules; cross-table equality is not claimed as a database CHECK.
The database additionally enforces purchase eligibility and restrictive foreign keys.

New Order Supplier assignments require an active Supplier. An unchanged historical Supplier link
remains editable and visible after retirement. The UI prefers active Suppliers and keeps the current
retired option for correction. Supplier retirement does not erase purchases.

## Shared purchase-context review

SeedLot → Order, Order → existing SeedLot and Order → new SeedLot use the same backend
`orders.reconciliation` preview/resolve contract. Selecting a transaction or physical lot is read-only.
The modal shows current/draft Source, proposed Source, current Supplier, Order Supplier and its action,
both dates, exact transaction total and fields outside this change. Saved acquisition context is also
shown when a draft differs. Cancel performs no mutation.

- Purchased and purchased-fruit retain their exact source. Unknown proposes Purchased; purchased-fruit
  is never inferred. Gift/exchange, self-collected, collection-produced and Other are conflicts. Save a
  valid explicit correction in normal SeedLot edit before linking. Harvest-conversion and reversed
  material protections still apply; the selector excludes incompatible and reversed lots.
- Blank Supplier proposes filling from a known Order Supplier, selected by default. Matching Suppliers
  stay unchanged. A known mismatch requires **Use Order supplier** before Apply can replace it.
  A cleared unsaved Supplier draft cannot conceal the stored conflict or erase known Supplier during
  linking. Correct/clear independent knowledge through normal saved SeedLot edit first. An unknown
  Order Supplier preserves known lot Supplier. Order Supplier editing refuses any known linked-lot
  mismatch; there is no implicit bulk synchronization. Correct/unlink affected lots first.
- Unknown acquisition date offers **Use Order date as acquisition date**, unchecked by default.
  Equal dates need no change. Different dates are preserved unless **Replace acquisition date with
  Order date** is explicitly checked. Copies retain exact year/month/day precision, never filling a
  missing day or month. Purchase and receipt remain separate facts.
- Apply on an existing SeedLot atomically saves the reviewed acquisition fields and link immediately.
  Other unsaved form fields remain drafts; stored identity, quantity, harvest date, Origin/provenance,
  Location, lifecycle and lineage are preserved. Both Order and SeedLot `updated_at` versions are
  checked under normal locks; a stale version returns typed 409 without any mutation. Refresh previews
  current stored acquisition fields before another Apply; independent form drafts remain available.
- **Add seed lot** from Order prepares only an Order/known-Supplier/Purchased draft using the shared
  service. Acquisition date stays unknown until explicitly copied or entered. Identity, quantity,
  harvest date, Origin/provenance, Location and lineage are never inferred. Apply in a new-lot modal
  prepares a draft only. Creation checks Order version and final confirmed acquisition fields again;
  changed acquisition fields require another preview. Each creation makes one distinct physical lot.
- Unlink removes only `order_id` on normal Save. Confirmed Source, Supplier and acquisition date stay
  independent SeedLot knowledge. There is no hidden rollback or copied-field provenance record.

Acquisition is one vertical flow: Source → Purchase Order/search → read-only transaction context →
Supplier → acquisition date. Origin is a separate tab. Known lot Supplier defaults Order search to
that exact Supplier, with an explicit **Show all Suppliers' Orders** choice for unknown/conflicting
Orders. Search uses truthful reference/Supplier/notes metadata. Order detail's bounded searchable
**Link existing seed lot** selector opens the same review and refreshes linked physical lots after
Apply. Multiple lots stay separate; exact navigation works in both directions.

The Order total is read-only transaction information, including currency, reference, date and
Supplier. It is not the price of this individual SeedLot. Nothing copies or divides it among lots. Confirmed Order versions refresh the contextual summary; failed transaction reads expose Retry.

Supplier and Order never establish biological/geographic provenance. A seller's country does not
populate material origin, a provenance site, native range or collection Location. SeedLot source,
Supplier, acquisition date, provenance, Location and lineage remain independent explicit fields.

## API, retention and directories

All endpoints require the existing owner session. Mutations retain exact Origin and CSRF protection:

- `GET /api/v1/orders`: `q` (200 characters), optional exact `supplier_id`, offset and limit.
- `POST /api/v1/orders`: create a transaction, returning 201 and its Location.
- `GET /api/v1/orders/{id}`: transaction plus bounded linked SeedLots; accepts `seed_lots_offset`
  and `seed_lots_limit`.
- `PATCH /api/v1/orders/{id}`: omitted fields remain unchanged; explicit null clears knowledge.
  The complete resulting state is validated, including the price/currency pair.
- `DELETE /api/v1/orders/{id}`: 204 only when no SeedLots reference it; otherwise typed 409.
- `POST /api/v1/orders/{id}/purchase-context/preview`: authenticated read-only acquisition preview;
  existing form drafts carry expected SeedLot version, reverse selection reads stored context.
- `POST /api/v1/orders/{id}/purchase-context/apply`: owner/Origin/CSRF-protected resolution;
  both expected versions and explicit Supplier/date choices. Existing lots persist atomically;
  a new-lot request returns confirmed draft context without creating anything.
- `POST /api/v1/orders/{id}/seed-lots`: create one physical lot with confirmed acquisition context,
  revalidating the Order version and final fields. No inferred material fields.
- `GET /api/v1/orders/{id}/seed-lot-choices`: eligible bounded literal search by lot label,
  BotanicalIdentity scientific name or direct Supplier name; UUID-ordered independent records.

Directory and linked-lot pages default to 50, maximum 100, with offsets bounded to 100000.
Directory order is known year/month/day descending, unknown date components last, then UUID
descending. This does not fill missing date precision. Literal, case-insensitive substring search
uses reference, direct Supplier name and notes; `%` and `_` are literal characters. Total and page
come from the same filtered projection. Linked lot count includes active and historical lots.

`#/orders` is a compact Sourcing directory with authoritative counts and read-first exact details.
Supplier detail provides exact filtered navigation, without financial analytics. SeedLot detail
shows an exact Order link beside its independent source context. Unreferenced deletion requires
confirmation; linked Orders explain why deletion is unavailable. There is no Order lifecycle.

Orders Saved Views use surface `orders`, v1 keys `q` and `supplier_id`. Opening uses the normal
canonical directory URL and starts on page one. Selection, forms, dialogs and offsets are excluded.
Missing Supplier filter UUIDs remain exact, visible and produce zero results.

Global Search adds `kind=order` under Sourcing beside Suppliers. Matches use only direct Order
reference, Supplier name and notes, with exact `#/orders/{id}` links and date/Supplier/price context.
Linked botanical names never confer a match. Existing collection-only structured filters retain
SEARCH-002 applicability and exclude Orders; use the Orders directory's Supplier filter for purchases.
Each searched kind keeps its two count/page queries; unrestricted text search is bounded to 30 SQL
statements across 14 kinds, including the two shared path queries.

Orders are deliberately absent from Activity History. Their date does not authorize a new History
category; purchase-history integration is a future candidate after actual use.

## Migration and boundaries

Migration `20261008_0036` adds Orders, nullable indexed SeedLot Order links, purchase-source and
money/date constraints, restrictive Supplier/Order foreign keys, and SavedView `orders` support.
Existing SeedLots remain unchanged and unlinked. Supplier/date/listing and SeedLot relationship
indexes support actual access paths. Downgrade locks affected tables and refuses while any Order or
Order Saved View exists. Explicit removal permits downgrade/re-upgrade without deleting old lots.

Plant/general purchases, order lines, FX, financial summaries and invoice files are deferred. The
approved navigation reorganization does not implement Species distribution, Native ranges or Schedule.
