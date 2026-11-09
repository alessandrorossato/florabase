import type { EventResponse } from "./api";
import { formatPartialDate } from "./eventData";

type Measurement = NonNullable<EventResponse["measurement"]>;
type Dated = EventResponse & {
  measurement: Measurement;
  occurred_on: NonNullable<EventResponse["occurred_on"]>;
};

const MILLIMETRES: Record<Measurement["unit"], number> = {
  mm: 1,
  cm: 10,
  m: 1000,
};
const DAY = 86_400_000;
const W = 320; // W and H match the SVG viewBox.
const H = 160;
const LEFT = 44;
const RIGHT = 12;
const TOP = 12;
const BOTTOM = 28;
const INSET = 10; // Keeps the first and last marks off the axes.

/** The whole recorded period in UTC days: a month or year is never narrowed to one day. */
function period(date: Dated["occurred_on"]): [number, number] {
  const month = (date.month ?? 1) - 1;
  if (date.precision === "day")
    return Array(2).fill(Date.UTC(date.year, month, date.day ?? 1) / DAY) as [
      number,
      number,
    ];
  if (date.precision === "month")
    return [
      Date.UTC(date.year, month, 1) / DAY,
      Date.UTC(date.year, month + 1, 0) / DAY,
    ];
  return [Date.UTC(date.year, 0, 1) / DAY, Date.UTC(date.year, 11, 31) / DAY];
}

function round(value: number): string {
  return String(Number(value.toFixed(3)));
}

export function HeightHistory({ events }: { events: EventResponse[] }) {
  const heights = events.filter(
    (event): event is Dated =>
      event.measurement?.quantity === "height" && event.occurred_on !== null,
  );
  if (heights.length === 0) return null;
  const chronological = heights
    .map((event) => ({ event, span: period(event.occurred_on) }))
    .sort((a, b) => a.span[0] - b.span[0] || a.span[1] - b.span[1]);
  // Plot in the unit last recorded; mm/cm/m is exact same-dimension scaling.
  const unit = chronological[chronological.length - 1].event.measurement.unit;
  const plotted = chronological.map(({ event, span }) => ({
    event,
    span,
    value:
      (Number(event.measurement.value) * MILLIMETRES[event.measurement.unit]) /
      MILLIMETRES[unit],
  }));
  const start = Math.min(...plotted.map((item) => item.span[0]));
  const end = Math.max(...plotted.map((item) => item.span[1]));
  const top = Math.max(...plotted.map((item) => item.value)) * 1.1;
  const x = (day: number) =>
    LEFT +
    INSET +
    ((day - start) / Math.max(end - start, 1)) * (W - LEFT - RIGHT - 2 * INSET);
  const y = (value: number) => TOP + (1 - value / top) * (H - TOP - BOTTOM);
  const first = chronological[0].event.occurred_on;
  const last = (
    plotted.find((item) => item.span[1] === end) ?? plotted[plotted.length - 1]
  ).event.occurred_on;

  return (
    <section className="height-history" aria-labelledby="height-history-title">
      <h5 id="height-history-title">Height history</h5>
      {plotted.length > 1 && (
        <figure>
          <svg
            viewBox="0 0 320 160"
            role="img"
            aria-label={`Height in ${unit} from ${formatPartialDate(first)} to ${formatPartialDate(last)}, ${String(plotted.length)} measurements`}
          >
            <line
              className="height-axis"
              x1={LEFT}
              x2={W - RIGHT}
              y1={y(0)}
              y2={y(0)}
            />
            <line
              className="height-axis"
              x1={LEFT}
              x2={LEFT}
              y1={TOP}
              y2={y(0)}
            />
            <text x={LEFT - 6} y={y(0)} textAnchor="end">
              0
            </text>
            <text x={LEFT - 6} y={TOP + 8} textAnchor="end">
              {round(top)}
            </text>
            <text x={4} y={TOP + 8}>
              {unit}
            </text>
            <text x={LEFT} y={H - 8}>
              {formatPartialDate(first)}
            </text>
            <text x={W - RIGHT} y={H - 8} textAnchor="end">
              {formatPartialDate(last)}
            </text>
            {plotted.map(({ event, span, value }) => {
              const hollow = event.measurement.is_approximate;
              return span[0] === span[1] ? (
                <circle
                  key={event.id}
                  className={`height-mark${hollow ? " height-mark--approximate" : ""}`}
                  cx={x(span[0])}
                  cy={y(value)}
                  r={4}
                />
              ) : (
                <line
                  key={event.id}
                  className={`height-span${hollow ? " height-mark--approximate" : ""}`}
                  x1={x(span[0])}
                  x2={x(span[1])}
                  y1={y(value)}
                  y2={y(value)}
                />
              );
            })}
          </svg>
          <figcaption className="field-help">
            Dots are dated to the day. Bars cover a month or year recorded
            without a day. Dashed or hollow marks are approximate. Values are
            plotted in {unit}; the table keeps each recorded unit.
          </figcaption>
        </figure>
      )}
      <table className="germination-history">
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th scope="col">Height</th>
            <th scope="col">Basis</th>
          </tr>
        </thead>
        <tbody>
          {heights.map((event) => (
            <tr key={event.id}>
              <th scope="row" data-label="Date">
                {formatPartialDate(event.occurred_on)}
              </th>
              <td data-label="Height">
                {event.measurement.value} {event.measurement.unit}
              </td>
              <td data-label="Basis">
                {event.measurement.is_approximate ? "Approximate" : "Measured"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
