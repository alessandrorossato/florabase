import { StatusBadge } from "../components/WorkspaceUI";
import { useRecordName } from "../components/recordPresentation";
import { EventTargetPhoto } from "./EventTargetPhoto";

import type { EventResponse } from "../collection/api";
import { eventLabels, eventSourceLabel, formatPartialDate } from "./eventData";

export function EventFeed({
  events,
  compact = false,
  showTargetPhoto = false,
  journal = false,
}: {
  events: EventResponse[];
  compact?: boolean;
  showTargetPhoto?: boolean;
  journal?: boolean;
}) {
  const recordName = useRecordName();

  return (
    <ol
      className={`event-feed${compact ? " event-feed--compact" : ""}${journal ? " journal-feed" : ""}`}
    >
      {events.map((event) => {
        const type = event.target.type === "plant" ? "Plant" : "Plant group";
        const name = recordName(
          event.target,
          event.target.type === "plant"
            ? "Unlabelled plant"
            : "Unlabelled plant group",
        );
        const href = `#/${event.target.type === "plant" ? "plants" : "plant-groups"}/${event.target.id}?tab=events`;
        const related = (
          <>
            <p>
              {journal && "Botanical identity: "}
              <a
                className="event-identity"
                href={`#/identities/${event.target.botanical_identity.id}?tab=events`}
              >
                {event.target.botanical_identity.display_label}
              </a>
            </p>
            {event.destination_location && (
              <p>
                Moved to{" "}
                <a href={`#/locations/${event.destination_location.id}`}>
                  {event.destination_location.display_path}
                </a>
              </p>
            )}
            {event.recipient && <p>Recipient: {event.recipient}</p>}
            {event.kind === "extraction" && event.resulting_plant && (
              <p>
                1 individual extracted →{" "}
                <a href={`#/plants/${event.resulting_plant.id}`}>
                  {recordName(event.resulting_plant, "Unlabelled plant")}
                </a>
              </p>
            )}
            {event.kind === "reintegration" && event.resulting_plant && (
              <p>
                Plant returned to this group →{" "}
                <a href={`#/plants/${event.resulting_plant.id}`}>
                  {recordName(event.resulting_plant, "Unlabelled plant")}
                </a>
              </p>
            )}
            {event.kind === "extraction" &&
              event.operation_status === "reversed" && (
                <p className="record-state">Reversed by reintegration</p>
              )}
            {event.harvest_id && (
              <p>
                <a href={`#/harvests/${event.harvest_id}`}>
                  {journal ? "Harvest: " : "Structured harvest · "}
                  {event.harvest_title}
                </a>
              </p>
            )}
          </>
        );
        if (journal)
          return (
            <li key={event.id}>
              <article>
                <time className="journal-date">
                  {event.occurred_on
                    ? formatPartialDate(event.occurred_on)
                    : `Recorded ${new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeZone: "UTC" }).format(new Date(event.created_at))} (UTC)`}
                </time>
                <div className="journal-content">
                  <div className="activity-row-heading">
                    <StatusBadge>{eventSourceLabel(event)}</StatusBadge>
                    <h3>{eventLabels[event.kind]}</h3>
                  </div>
                  <a className="event-target" href={href}>
                    {name}
                  </a>
                  <span className="journal-record-type">{type}</span>
                  {event.notes && (
                    <p className="journal-excerpt">
                      {event.notes.length > 240
                        ? `${event.notes.slice(0, 240).trimEnd()}…`
                        : event.notes}
                    </p>
                  )}
                  <div className="journal-related">{related}</div>
                </div>
              </article>
            </li>
          );
        return (
          <li key={event.id}>
            <article>
              {showTargetPhoto && (
                <EventTargetPhoto
                  photo={
                    event.harvest_id
                      ? event.harvest_primary_photo
                      : event.target.primary_photo
                  }
                  fallbackPhoto={
                    event.harvest_id ? event.target.primary_photo : null
                  }
                  identity={event.target.botanical_identity}
                  kind={
                    event.harvest_id
                      ? "harvest"
                      : event.target.type === "plant"
                        ? "plant"
                        : "group"
                  }
                  label={name}
                />
              )}
              <div className="event-feed-heading">
                <span className="event-kind">{eventLabels[event.kind]}</span>
                <time>{formatPartialDate(event.occurred_on)}</time>
              </div>
              <a className="event-target" href={href}>
                {name}
              </a>
              <span className="record-state">{type}</span>
              {related}
              {event.notes && <p className="preserve-lines">{event.notes}</p>}
            </article>
          </li>
        );
      })}
    </ol>
  );
}
