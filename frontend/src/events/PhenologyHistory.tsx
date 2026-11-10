import type { EventResponse } from "./api";
import { phenologyStage, phenophaseLabels, type Phenophase } from "./eventData";

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];
// Seasonal reading order; stage-less flowering/fruiting entries follow their family.
const ORDER: string[] = [
  "dormancy_exit",
  "bud_break",
  "flowering_onset",
  "flowering_ongoing",
  "flowering_end",
  "flowering",
  "fruit_set",
  "fruit_ripening",
  "fruit_ripe",
  "fruiting",
  "leaf_color_change",
  "leaf_fall",
  "dormancy_entry",
];

const stageKey = (event: EventResponse) => event.phenology?.phase ?? event.kind;
const family = (event: EventResponse) =>
  event.kind === "observation" ? "growth" : event.kind;

/** Date inside its year group: a month or year is never narrowed to a day. */
function withinYear(event: EventResponse): string {
  const date = event.occurred_on;
  if (!date) return "date not recorded";
  const about = event.phenology?.date_is_approximate ? "about " : "";
  if (date.precision === "year")
    return `month not recorded${about ? " (approximate year)" : ""}`;
  const month = MONTHS[(date.month ?? 1) - 1];
  return date.precision === "month"
    ? `${about}${month}`
    : `${about}${String(date.day)} ${month}`;
}

function chronological(a: EventResponse, b: EventResponse): number {
  // Year-only dates sort after dated months within their year; nothing invents a month.
  const month = (event: EventResponse) => event.occurred_on?.month ?? 13;
  return (
    month(a) - month(b) ||
    (a.occurred_on?.day ?? 0) - (b.occurred_on?.day ?? 0) ||
    a.created_at.localeCompare(b.created_at)
  );
}

/**
 * Year-by-year phenology from recorded Journal entries only (docs/phenology.md). A stage seen in
 * another year but not this one reads "No … observation recorded", never "did not happen".
 */
export function PhenologyHistory({
  targetId,
  events,
  onRecord,
  onShow,
}: {
  targetId: string;
  events: EventResponse[];
  onRecord: () => void;
  onShow: (event: EventResponse) => void;
}) {
  const entries = events.filter((event) => phenologyStage(event) !== null);
  const years = new Map<number | null, EventResponse[]>();
  for (const event of entries) {
    const year = event.occurred_on?.year ?? null;
    years.set(year, [...(years.get(year) ?? []), event]);
  }
  const ordered = [...years.keys()].sort(
    (a, b) => (b ?? -Infinity) - (a ?? -Infinity),
  );
  const staged = ORDER.filter((key) =>
    entries.some((event) => event.phenology?.phase === key),
  ) as Phenophase[];

  return (
    <section className="phenology" aria-labelledby={`phenology-${targetId}`}>
      <div className="event-heading">
        <h5 id={`phenology-${targetId}`}>Phenology</h5>
        <button type="button" className="button--secondary" onClick={onRecord}>
          Record phenology
        </button>
      </div>
      {entries.length === 0 ? (
        <p className="field-help">
          No phenology observations recorded yet. Record bud break, flowering,
          fruiting, leaf change or dormancy as you see it.
        </p>
      ) : (
        <>
          <p className="field-help">
            Recorded observations only, by year. A missing stage means nothing
            was recorded, not that it did not happen.
          </p>
          <div className="phenology-legend" aria-hidden="true">
            <span className="phenology-mark phenology-mark--growth" /> Leaves
            and growth
            <span className="phenology-mark phenology-mark--flowering" />{" "}
            Flowering
            <span className="phenology-mark phenology-mark--fruiting" />{" "}
            Fruiting
            <span className="phenology-mark phenology-mark--approximate" />{" "}
            Approximate date
          </div>
          {ordered.map((year) => {
            const recorded = [...(years.get(year) ?? [])].sort(chronological);
            const heading = year === null ? "Date not recorded" : String(year);
            const groups = ORDER.map((key) => ({
              key,
              items: recorded.filter((event) => stageKey(event) === key),
            })).filter((group) => group.items.length > 0);
            const missing =
              year === null
                ? []
                : staged.filter(
                    (phase) =>
                      !recorded.some(
                        (event) => event.phenology?.phase === phase,
                      ),
                  );
            return (
              <div
                role="group"
                className="phenology-year"
                key={heading}
                aria-label={heading}
              >
                <h6>{heading}</h6>
                {year !== null && (
                  <ol className="phenology-months" aria-hidden="true">
                    {MONTHS.map((month, index) => (
                      <li key={month}>
                        <span className="phenology-month">{month}</span>
                        {recorded
                          .filter(
                            (event) =>
                              event.occurred_on?.precision !== "year" &&
                              event.occurred_on?.month === index + 1,
                          )
                          .map((event) => (
                            <span
                              key={event.id}
                              title={phenologyStage(event) ?? undefined}
                              className={`phenology-mark phenology-mark--${family(event)}${event.phenology?.date_is_approximate ? " phenology-mark--approximate" : ""}${event.occurred_on?.precision === "month" ? " phenology-mark--month" : ""}`}
                            />
                          ))}
                      </li>
                    ))}
                  </ol>
                )}
                <ul className="phenology-stages">
                  {groups.map(({ key, items }) => (
                    <li key={key}>
                      <strong>
                        {key in phenophaseLabels
                          ? phenophaseLabels[key as Phenophase]
                          : phenologyStage(items[0])}
                        :
                      </strong>{" "}
                      {items.map((event, index) => (
                        <span key={event.id}>
                          {index > 0 && ", "}
                          <button
                            type="button"
                            aria-label={`${phenologyStage(event) ?? ""}, ${withinYear(event)} ${heading}: show Journal entry`}
                            onClick={() => {
                              onShow(event);
                            }}
                          >
                            {withinYear(event)}
                          </button>
                        </span>
                      ))}
                    </li>
                  ))}
                  {missing.map((phase) => (
                    <li key={phase} className="phenology-missing">
                      No “{phenophaseLabels[phase]}” observation recorded
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </>
      )}
    </section>
  );
}
