# Unified operational history — HISTORY-001

History is a read-only projection of recorded collection activity. Journal remains the focused
Plant/PlantGroup Event journal at `#/events`; History is a separate Activity destination at `#/history`.
Corrections change the current projection, and deleting an ordinary Event removes its row. History
is neither an immutable audit log nor a schedule, and contains no synthetic persisted entries.

## Audited source matrix

| Source | Persisted fact | Authoritative date | Primary subject | Direct related records | Duplication risk | Deep link | Include / reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Event (all current kinds) | Journal occurrence | occurred_on PartialDate; otherwise created_at as Recorded | Plant / PlantGroup | Destination Location; resulting Plant | Structured Harvest; receipt-owned Event | Target Events tab | Yes, except Harvest-owned Events |
| OperationReceipt: SeedLot → Sowing | Applied propagation, retained status | created_at as Recorded | Resulting Sowing | Source SeedLot | Event link if present | Sowing detail | Yes, only without Event |
| OperationReceipt: Sowing → Plant / PlantGroup | Applied propagation, retained status | created_at as Recorded | Resulting Plant / PlantGroup | Source Sowing | Event link if present | Result detail | Yes, only without Event |
| OperationReceipt: extraction / transfer | Operation backing an Event | Event date | Event target | As Event | Always owns Event | Target Events tab | No independent row; Event represents operation, receipt supplies status |
| GerminationObservation | Dated incremental observation | observed_on exact day | Sowing | None | None | Sowing Germination tab | Yes |
| Harvest + HarvestItems | Structured collection occurrence with ordered material lines | Harvest occurred_on PartialDate; otherwise created_at as Recorded | Harvest | Source Plant / PlantGroup | Owned Event; multiple material lines | Harvest detail | Yes, one row per Harvest |
| HarvestMaterialDisposition | Immutable disposition, partial / use-all and amount | occurred_on PartialDate; otherwise created_at as Recorded | Inventory | Owning Harvest | Conversion-owned disposition | Owning Harvest's Stored material section, exact inventory anchor | Yes, except conversion-owned disposition |
| HarvestSeedLotConversion application | Applied seed conversion and status | created_at as Recorded | Resulting SeedLot | Source inventory | Owned used_for_propagation disposition | SeedLot detail; exact inventory link | Yes |
| HarvestSeedLotConversion reversal | Persisted reversal instant | reversed_at (UTC) | Resulting SeedLot | Source inventory | None | Same authoritative contexts | Yes, only with reversed_at |
| Current SeedLot / Sowing lifecycle | Current state only | No transition date | — | — | False history | — | No |
| Current Location, quantity, Supplier, provenance, updated_at | Current state / correction only | No occurrence evidence | — | — | False history | — | No |
| Creation of ordinary records / inventory tracking | Current records, no reviewed operational receipt | created_at alone does not establish an operational fact | — | — | False history | — | No |

Receipt result_date snapshots describe Sowing date or collection-entry date for safe reversal;
they are not a separately contracted propagation occurrence date. Receipt entries therefore use
Recorded consistently, including legacy receipts without snapshots. No current descendant field
is used as an operation date. Propagation reversals retain the original row with Reversed status;
there is no separate reversal row because these receipts have no reversal timestamp. Extraction's
separately stored reintegration Event is visible independently.

## Projection, dates and bounded queries

The normalized typed identity is `event:<id>`, `harvest:<id>`, `germination:<id>`,
`operation_receipt:<id>`, `disposition:<id>`, `conversion:<id>:applied` or
`conversion:<id>:reversed`. UUIDs identify existing facts; no History table is added.

An occurrence PartialDate keeps its year/month/day precision. Reversal instants use their UTC day
and retain the precise occurred_at value. Missing occurrence dates use created_at with an explicit
Recorded label. No updated_at participates. Timeline ordering uses displayed year descending,
known month descending (missing last), known day descending (missing last), precise reversal instant
or recording timestamp descending, then typed key ascending. Unknown dates sort last. Sorting never
fills missing rendered month/day. Timeline year means the displayed occurrence year, or UTC recorded
year for a Recorded row.

`GET /api/v1/history` requires authentication. Filters: repeated `category` (event, propagation,
germination, harvest, material), `subject_kind` (plant, plant_group, sowing, harvest,
harvest_inventory, seed_lot), and `year` (1–9999). Default limit 50, maximum 100; offset 0–100000.
The response contains items, total, offset and limit. A normalized SQL UNION ALL suppresses owned
backing rows before filtering. SQL applies the global order and page. One SQL statement joins the
filtered count to the bounded page, including empty/out-of-range pages. Labels and at most two
related references are joined in SQL, with no per-row queries, external calls, media or full-history
Python download. Existing indexes are used; no speculative indexes or generic cache are added.

Record labels are current display labels, not historical name snapshots. Context is bounded and
uses directly stored facts (Event recipient, germination count, disposition mode/amount, Harvest
material-line count). Full notes remain on domain details. References are typed; the frontend derives
routes. Inventory references carry their owning Harvest ID and resolve to its existing Stored
material section with an exact inventory anchor. Event links use target Events tabs; germination
links use the Sowing Germination tab. No generic history-detail page exists.

## Saved Views and boundaries

History v1 saves only category, subject_kind and timeline year, omitting defaults. Category order is
canonical and duplicates collapse. URLs repeat category in the stable vocabulary order. Invalid URL
values are ignored; Saved View writes reject unsupported values and transient keys. Opening a view
starts at page one, including reopening the identical view. There is no local persistence or
result snapshot. Migration 20261007_0035 extends only the SavedView surface constraint. Downgrade
refuses while History SavedViews exist; explicit deletion permits downgrade without changing other
views.

Known gaps: legacy propagation without receipts; SeedLot/Sowing lifecycle corrections; direct
record creation; SeedLot/Sowing/inventory Location changes (including BULK-001); stock corrections
and tracking; Supplier/provenance corrections. Plant/PlantGroup bulk moves do have Movement Events.
Current fields and updated_at never fill these gaps. Ordinary corrections are not audit copies.
There are no History mutation, bulk, undo, scheduling, calendar or future-task controls.

## Activity UI and navigation

The global Event destination is **Journal**; the Event model, kinds, API, `#/events` route,
record-level Events tabs and Saved View `events` surface remain unchanged. Its permanent intro
explains observations/actions for Plants and Plant groups, with corrections through their existing
Event workflows. The correction/current-state disclosure remains secondary help. Journal rows show
occurrence or explicit Recorded date, kind, primary Plant/PlantGroup, a notes excerpt (up to 240
characters plus ellipsis), then smaller direct related links. Full notes remain on the record.

Journal's existing filters retain exactly their membership and URL/Saved View values:

| Display label | Internal category | Event kinds |
| --- | --- | --- |
| All entries | `all` | All kinds, including `other` |
| Observations | `observations` | observation, flowering, fruiting |
| Cultivation | `cultivation` | movement, repotting, pruning, treatment, harvest, extraction, reintegration |
| Lifecycle | `status` | transfer, death, loss, discarded |

History permanently explains its read-only collection-wide purpose, links to Journal, and acknowledges
recording gaps. Its compact filter bar uses named `aria-pressed` category chips: **All activity** is
selected for the empty category set; other categories support multiple selection. Primary record type,
Timeline year, explicit Apply year and Clear year preserve the existing state contract and page-one
reset. Clear year preserves other filters. The semantic ordered timeline has a subtle rail and markers,
product-facing action labels, distinct primary/secondary links, and visible PartialDate/Recorded labels.
No source inclusion, deduplication, date or persistence behavior changes with this presentation.

All six desktop sidebar groups have keyboard-operable disclosure buttons, visible focus, chevrons,
`aria-expanded` and controlled child navigation. First use expands every group. Collapsed group names
are stored only under `florabase.sidebar.collapsed-groups.v1` in localStorage as a browser presentation
preference. Invalid/unavailable storage falls back safely; only known groups are accepted. Activating
any route, including refresh/deep links and browser navigation, expands its group so the active
entry remains discoverable. An operator may collapse it again until the next activation. This
preference is neither domain data nor Saved View state. Mobile keeps its existing compact navigation
and More destinations, including separate Journal and History entries.
