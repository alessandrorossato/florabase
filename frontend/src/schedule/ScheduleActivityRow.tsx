import { ScheduleTargetLabel } from "./ScheduleTargetLabel";
import type { Activity } from "./api";
import {
  activityLabels,
  activityState,
  localDay,
  targetHref,
  targetLabels,
} from "./state";

export type ActivityAction = "inspect" | "edit" | "complete" | "cancel";
export function ScheduleActivityRow({
  item,
  owner,
  onAction,
  today = localDay(),
}: {
  item: Activity;
  owner: boolean;
  today?: string;
  onAction: (action: ActivityAction, item: Activity) => void;
}) {
  return (
    <div className="schedule-row">
      <div>
        <button
          className="link-button schedule-title"
          onClick={() => {
            onAction("inspect", item);
          }}
        >
          {item.title}
        </button>
        <p>
          <time dateTime={item.due_on}>{item.due_on}</time> ·{" "}
          {activityLabels[item.activity_kind]} ·{" "}
          <strong>{activityState(item, today)}</strong>
        </p>
        {item.target ? (
          <p>
            {targetLabels[item.target.kind]}:{" "}
            <a href={targetHref(item.target)}>
              <ScheduleTargetLabel target={item.target} />
            </a>
            {item.target.lifecycle &&
              item.target.lifecycle !== "active" &&
              ` (${item.target.lifecycle})`}
          </p>
        ) : (
          <p>Whole collection</p>
        )}
        {item.notes && (
          <p className="schedule-notes">
            {item.notes.length > 240
              ? `${item.notes.slice(0, 240)}…`
              : item.notes}
          </p>
        )}
        {item.linked_event_id && item.target && (
          <a href={`${targetHref(item.target)}?tab=events`}>
            Linked Journal Event
          </a>
        )}
        {item.status === "completed" && !item.linked_event_id && (
          <p>Completed without a Journal Event</p>
        )}
      </div>
      {owner && item.status === "planned" && (
        <div className="button-row">
          <button
            className="button--secondary"
            onClick={() => {
              onAction("edit", item);
            }}
          >
            Edit / reschedule
          </button>
          <button
            className="button--secondary"
            onClick={() => {
              onAction("complete", item);
            }}
          >
            Complete
          </button>
          <button
            className="button--secondary"
            onClick={() => {
              onAction("cancel", item);
            }}
          >
            Cancel activity
          </button>
        </div>
      )}
    </div>
  );
}
