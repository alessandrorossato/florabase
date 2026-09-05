import type { EventResponse } from "../collection/api";
import { eventLabels, formatPartialDate, type EventFilter } from "./eventData";

export function EventFilters({
  selected,
  onSelect,
}: {
  selected: EventFilter;
  onSelect: (filter: EventFilter) => void;
}) {
  return (
    <div aria-label="Filter Events" className="filter-tabs" role="group">
      {(["all", "observations", "cultivation", "status"] as const).map(
        (filter) => (
          <button
            aria-pressed={selected === filter}
            className="filter-chip"
            key={filter}
            type="button"
            onClick={() => {
              onSelect(filter);
            }}
          >
            {filter[0].toUpperCase() + filter.slice(1)}
          </button>
        ),
      )}
    </div>
  );
}

export function EventFeed({
  events,
  compact = false,
}: {
  events: EventResponse[];
  compact?: boolean;
}) {
  return (
    <ol className={`event-feed${compact ? " event-feed--compact" : ""}`}>
      {events.map((event) => {
        const type = event.target.type === "plant" ? "Plant" : "Plant group";
        const name =
          event.target.label ?? event.target.botanical_identity.display_label;
        const href = `#/${event.target.type === "plant" ? "plants" : "plant-groups"}/${event.target.id}?tab=events`;
        return (
          <li key={event.id}>
            <article>
              <div className="event-feed-heading">
                <span className="event-kind">{eventLabels[event.kind]}</span>
                <time>{formatPartialDate(event.occurred_on)}</time>
              </div>
              <a className="event-target" href={href}>
                {name}
              </a>
              <span className="record-state">{type}</span>
              {event.destination_location && (
                <p>Moved to {event.destination_location.display_path}</p>
              )}
              {event.recipient && <p>Recipient: {event.recipient}</p>}
              {event.kind === "extraction" && event.resulting_plant && (
                <p>
                  1 individual extracted →{" "}
                  <a href={`#/plants/${event.resulting_plant.id}`}>
                    {event.resulting_plant.label ??
                      event.resulting_plant.botanical_identity.display_label}
                  </a>
                </p>
              )}
              {event.notes && <p className="preserve-lines">{event.notes}</p>}
            </article>
          </li>
        );
      })}
    </ol>
  );
}
