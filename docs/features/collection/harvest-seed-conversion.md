# HARVEST-003 — Create Seed lots from stored seeds

The approved product decision is guarded reversal with retained history. This is a narrow
conversion aggregate, not a new OperationReceipt kind or generic disposition undo system.

## Explicit conversion

Only an explicitly tracked, active seed HarvestItem can create a SeedLot. Harvest saving,
tracking, ordinary used-for-propagation dispositions and depletion never create lots.
An inventory can produce multiple independently recorded packets. One transaction records the
used_for_propagation disposition, changes source stock, creates a collection-produced SeedLot
and its unique HarvestSeedLotConversion. Failures roll back all four effects.

The result's one Plant or PlantGroup producer is the exact Harvest source. Existing lineage
serialization and cycle validation apply; no Harvest, item or inventory nodes enter the lineage
walker. The producer's current BotanicalIdentity defaults the form, but the operator may choose
another identity and correct it later. The exact PartialDate Harvest occurrence supplies the
harvest date; unknown stays unknown. No acquisition date, Supplier, provenance, notes, media,
Sowing or source Event is inferred. Target Location can be confirmed/changed independently of
remaining source storage. Its Seed lot eligibility scope is validated normally.

## Quantity contract

The existing SeedQuantity validator remains authoritative: count maps to seed_count, weight to
weight, unknown to absent quantity. Decimal strings and exact/approximate truth are preserved.
No unit or dimension conversion occurs. SeedLots support g/mg; stock recorded in kg requires an
explicit current measurement/correction in a supported unit before conversion.

| Source | Partial | Use all |
| --- | --- | --- |
| Exact | Positive exact compatible target strictly smaller than stock; derive exact remainder | Target equals the exact source quantity; source becomes depleted |
| Approximate | Explicit target measurement or unknown amount; confirm compatible approximate remainder | Explicit target measurement or unknown; source depleted |
| Unknown | Explicit target measurement or unknown; remainder stays unknown | Explicit target measurement or unknown; source depleted |

A measured target never manufactures a measured source remainder. Original disposition before/after
snapshots remain immutable and retain the original source precision even when a target was measured.
The conversion retains typed target quantity independently of later SeedLot correction.

## Persistence, correction and reversal

`harvest_seed_lot_conversions` has UUIDv7 ID, restrictive inventory/disposition/SeedLot FKs,
unique disposition and SeedLot references, typed target quantity, source correction version,
applied/reversed status, UTC created_at and reversed_at. Source before/after facts are obtained
through the exact immutable disposition, rather than duplicated. Database checks/triggers protect
quantity coherence, original conversion facts, status evidence and retained producer/source origin.

Converted SeedLot source_kind and producer references cannot change through ordinary edit. Once a
Harvest has any conversion, including reversed history, its source cannot be reassigned. Existing
tracking protections retain the item's seed material kind and block source deletion. Identity,
label, notes, Location, dates, viability and ordinary quantities remain correctable; corrections
never rewrite conversion snapshots or replay stock accounting.

Undo restores the captured inventory before-state and marks both conversion and SeedLot reversed
in one transaction. It retains Harvest/items, inventory, disposition, conversion, lot, producer
lineage and reversal time. Reversed lots remain readable and counted in lifecycle totals, but are
excluded from active holdings and cannot create new Sowings or be reactivated through correction.

Eligibility is safe or blocked. Source state/quantity must match its recorded after-state, and no
intervening quantity/state correction may have changed its correction version. Location-only
correction does not restore or alter source storage. Later standalone dispositions block undo even
when quantity remains unknown; later applied conversions must be undone newest-first. Reversed
later conversions are resolved history. Result lifecycle must still be active and quantity must
match its conversion snapshot; identity, Location, labels and notes do not block. Applied receipts
or Sowings without both reversed lifecycle and their explicit reversed seed-lot-to-sowing receipt
block. The existing downstream-first propagation reversal resolves those dependencies; nothing
cascades or deletes descendants. Original standalone HARVEST-002 dispositions remain non-reversible.

## Lock order and projections

Conversion and mutation-time reversal acquire the existing transaction-scoped lineage advisory lock
first, then Harvest owner, inventory, conversion (reversal), SeedLot and producer where applicable,
then existing Location validation locks. Stock-only writers never acquire the lineage lock; their
owner-first order remains compatible. Source and result rows are refreshed after locking. Existing
propagation reversal can hold receipt before SeedLot; conversion never locks dependent receipts.
Read-only eligibility is advisory and every rule is repeated under mutation locks.

SeedLot projection batches conversion IDs in one set-based query. Directories do not load history.
Conversion facts are joined in one query on demand in detail; there is no per-row Harvest/SeedLot
lookup. Authenticated reads and owner mutations reuse existing CSRF/Origin protection and stable
conflicts. UI uses native TaskDialog focus handling, exact source context, partial/all summaries,
precision controls and cross-links. Undo is secondary and confirms retained history and restoration.

## Migration and verification

Revision `20261004_0032` follows `20261003_0031`. It creates zero conversion rows for old data,
adds the source correction counter and SeedLot reversed lifecycle, and installs origin/history guards.
Empty downgrade/re-upgrade works. Populated conversion or reversed SeedLot history blocks downgrade
before destructive changes under table locks. Focused checks and implementation smoke are recorded
in [progress](progress.md). Operator UAT/visual acceptance is accepted; independent review found no
production defect and added unit coverage for creation, eligibility, reversal, history projection and
API paths. HARVEST-003 is `verified` pending the final canonical receipt and local commit.

HISTORY-001 also exposes these recorded facts through the read-only [operational History](operational-history.md).
Structured Harvests supersede their owned Events there; seed conversions supersede their linked
dispositions. Current inventory corrections and Location assignments do not fabricate occurrences.
The existing domain details and action controls remain authoritative.
