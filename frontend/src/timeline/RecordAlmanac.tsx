import { useId, type ReactNode } from "react";

import type { components } from "../api/schema";
import { formatPartialDate } from "../events/eventData";
import { historyHash } from "../history/state";
import type { EventTargetKind } from "../events/api";
import type { TargetKind } from "../schedule/state";
import { NextUp, RecordTimeline } from "./RecordTimeline";
import "./record-timeline.css";

type PartialDate = components["schemas"]["PartialDate"];

export type RecordAlmanacProps =
  | {
      kind: TargetKind;
      id: string;
      current?: boolean;
      journal?: { target: EventTargetKind; href: string; onOpen?: () => void };
      recordedElsewhere?: ReactNode;
      className?: string;
    }
  | {
      kind: "harvest";
      id: string;
      occurredOn: PartialDate | null;
      eventId?: string;
      sourceHref: string;
      sourceLabel?: string;
      sourceScheduleHref?: string;
      className?: string;
    };

/**
 * Shared Almanac block for every Collection record Overview: Planned (Schedule) + Recorded
 * (Journal or record-specific observations) + "Edits and collection operations are kept in History."
 */
export function RecordAlmanac(props: RecordAlmanacProps) {
  const titleId = useId();
  if (props.kind !== "harvest") {
    return (
      <RecordTimeline
        kind={props.kind}
        id={props.id}
        current={props.current}
        journal={props.journal}
        recordedElsewhere={props.recordedElsewhere}
        className={props.className}
      />
    );
  }
  const history = historyHash({
    q: "",
    category: [],
    subject_kind: ["harvest"],
    year: "",
  });
  return (
    <section
      className={`record-timeline ${props.className ?? ""}`.trim()}
      aria-labelledby={titleId}
    >
      <h4 id={titleId}>Almanac</h4>
      <NextUp
        scheduleHref={props.sourceScheduleHref ?? "#/schedule"}
        emptyText="Plans are kept on the source record"
        scheduleLabel="Open in Schedule"
      />
      <div className="record-timeline__lanes">
        <section
          className="record-timeline__lane record-timeline__lane--planned"
          aria-label="Planned"
        >
          <p className="record-timeline__lane-title" aria-hidden="true">
            Planned <span>in Schedule, not yet done</span>
          </p>
          <p className="record-timeline__note">
            Harvests are completed events; schedule follow-up on the source
            record.
          </p>
          <p className="record-timeline__links">
            <a href={props.sourceScheduleHref ?? "#/schedule"}>
              View source in Schedule
            </a>
          </p>
        </section>

        <section
          className="record-timeline__lane record-timeline__lane--recorded"
          aria-label="Recorded"
        >
          <p className="record-timeline__lane-title" aria-hidden="true">
            Recorded <span>in source Journal</span>
          </p>
          <ol className="record-timeline__list">
            <li className="record-timeline__item">
              {props.occurredOn ? (
                <time>{formatPartialDate(props.occurredOn)}</time>
              ) : (
                <span className="record-timeline__undated">
                  Date not recorded
                </span>
              )}
              <div>
                <strong>Harvest</strong>
                <p>
                  {props.sourceLabel
                    ? `Recorded on ${props.sourceLabel}`
                    : "Owned harvest event"}
                </p>
              </div>
            </li>
          </ol>
          <p className="record-timeline__links">
            {props.eventId && (
              <a href={`${props.sourceHref}?tab=events&event=${props.eventId}`}>
                View owned harvest Event in source history
              </a>
            )}
            <a href="#/events">Journal</a>
          </p>
        </section>
      </div>
      <p className="record-timeline__footnote">
        Edits and collection operations are kept in{" "}
        <a href={history}>History</a>.
      </p>
    </section>
  );
}
