# Structured Plant measurements (MEASUREMENT-001)

Roadmap theme 4, "Measurements / growth history". This increment records and browses real
longitudinal **height** measurements for individual Plants. Other quantities are proposed below and
are not implemented.

## Domain contract

A measurement is a Journal Event of kind `measurement` with one typed payload. It is not a separate
event system, table or timeline: it shares the Event identity, PartialDate occurrence date, notes,
photos, ordering, correction and deletion rules from [domain model § Event](domain-model.md#event),
and History projects it like every other Event.

| Concern | Decision |
| --- | --- |
| Subject | Exactly one individual **Plant**. PlantGroup measurements are refused (`measurement_requires_plant`): a group value needs sample size, aggregation (mean, range, representative individual) and member-count semantics that are not yet decided. |
| Quantity | Controlled vocabulary. This slice accepts only `height`: vertical extent from the growing medium surface to the highest living tissue, measured as found (not stretched). |
| Value | Positive exact decimal, sent and returned as a JSON string. Stored in unscaled PostgreSQL `numeric`, so `12`, `12.0` and `12.50` keep the resolution the operator recorded. At most 3 fractional digits; values above 200 m are refused as implausible typos. |
| Unit | Required and stored exactly as recorded. Height accepts `mm`, `cm`, `m`. No conversion is persisted. Quantity/unit compatibility is enforced in both Pydantic and a database CHECK, so a mass unit can never be attached to height. |
| Uncertainty | Two explicit signals: recorded resolution (preserved decimal places) and `is_approximate` for an estimate rather than an instrument reading. A ± tolerance is deferred until real use needs it. |
| Date | An occurrence PartialDate is **required** for a measurement (any precision: year, month or day). An undated value has no longitudinal meaning; record it as an Observation note instead. Month or year precision is never converted to a day. |
| Correction | `PUT /api/v1/events/{id}` updates the same Event in place and advances `updated_at`; Florabase is not event-sourced, so the Event always holds the current value. Before a correction changes the value (including its recorded resolution), unit, approximation or date, the stored measurement is copied to an append-only `event_measurement_corrections` row with its PartialDate precision and the UTC `replaced_at` instant. Notes-only edits add no row. Changing the kind away from `measurement` clears the payload but keeps the trail. Explicitly deleting the Event deletes its trail with it, matching History, which drops deleted Events. |
| Retention | Measurements never write current state. Plant has no "current height" column; the latest value is derived from history. Restrictive Event foreign keys keep measurements when the Plant becomes dead, lost, transferred, discarded, reintegrated or reversed. Measurements may still be recorded for inactive Plants. Like observation, flowering and fruiting, a measurement is a retainable observation: it neither blocks reintegration nor propagation reversal, and it is listed in their confirmation step. |
| Ownership | The `events` capability owns validation and persistence. History only projects (`Measurement` title, `Height: 42.5 cm (approximate)` context). |

### Storage

Four nullable generic columns on `events`, populated only for `kind = 'measurement'`:
`measurement_quantity`, `measurement_value`, `measurement_unit`, `measurement_is_approximate`.
They are generic over quantities, not one column per botanical trait, and Plant gains no columns.
`ck_events_measurement` makes the payload all-or-nothing, requires a Plant target and an occurrence
date, and restricts units per quantity. Migration 0043 extends `ck_events_kind`; downgrade refuses
while measurement Events exist instead of silently deleting them.

### Correction trail

No existing infrastructure keeps durable revisions: History is a read-only projection that is
explicitly not an audit log, and OperationReceipts snapshot reversible operations one-to-one. The
trail is therefore one small append-only table owned by the `events` capability (migration 0044),
written only in the correction path under a row lock. It holds no current state, so lineage,
reintegration and propagation reversal are unchanged. Corrections are not History occurrences.

### API

`EventWrite` and `EventResponse` gain `measurement: {quantity, value, unit, is_approximate} | null`.
`EventResponse.measurement_corrections` lists the replaced values oldest first, each with
`measurement`, `occurred_on` and `replaced_at`.
`measurement` is required exactly when `kind = "measurement"`. Existing endpoints carry it; no new
route is added.

## Display

The Plant detail Journal shows a **Height history** panel when the Plant has height measurements:

- a table of every recorded value with its own unit, date at its recorded precision and an
  "approximate" marker;
- a small SVG chart in one display unit (the unit of the most recent measurement). Conversion
  between `mm`, `cm` and `m` is exact scaling within the same dimension and is for plotting only;
  the axis states the unit;
- day-precision values are dots; month- or year-precision values are drawn as a horizontal span
  over the whole recorded period, never as an invented day. Approximate values are hollow;
- with fewer than two dated values the chart is omitted and the table remains;
- chart and table use only the current value. The Journal card of a corrected measurement has a
  "Corrected N times" disclosure listing each replaced value, its date and when it was replaced.

Measurements appear in the Journal under the Observations filter and in the collection Journal and
History with their value and unit.

## Proposed next quantities (not implemented)

Propose after the height slice is used on real data:

| Quantity | Units | Notes |
| --- | --- | --- |
| `stem_diameter` | `mm`, `cm` | Needs a measuring-height convention (e.g. caliper at 15 cm, DBH at 1.3 m), probably a controlled `method` field. |
| `canopy_width` | `cm`, `m` | Widest spread vs. mean of two perpendicular spans must be decided. |
| `weight` | `g`, `kg` | Mostly meaningful for whole potted Plants or tubers; clarify with/without container. |
| custom | operator-defined label + unit | Needs a controlled unit catalogue so `cm` and `CM` or `in` and `cm` are never silently mixed. |

Each is a migration widening `ck_events_measurement` and `ck_event_measurement_corrections_value`
plus vocabulary, not a new table. Multi-value
sessions (height and canopy on one visit) are separate Events for now.
