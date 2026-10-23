import { ActionButton } from "../components/Action";
import { ScheduleTargetLabel } from "./ScheduleTargetLabel";
import { OverflowMenu } from "../components/ReferenceUI";
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
          <strong>
            {activityState(item, today).replace("Planned · ", "")}
          </strong>
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
            {item.notes.length > 160
              ? `${item.notes.slice(0, 160)}…`
              : item.notes}
          </p>
        )}
        {item.linked_event_id && item.target && (
          <a href={`${targetHref(item.target)}?tab=events`}>
            Linked Journal entry
          </a>
        )}
        {item.status === "completed" && !item.linked_event_id && (
          <p className="schedule-row-context">
            Completed without a Journal entry
          </p>
        )}
      </div>
      {owner && item.status === "planned" && (
        <div className="schedule-row-actions">
          <button
            className="button--secondary"
            onClick={() => {
              onAction("complete", item);
            }}
          >
            Complete
          </button>
          <OverflowMenu label="⋯" ariaLabel={`Actions for ${item.title}`}>
            <nav
              className="schedule-row-menu"
              aria-label={`Activity actions for ${item.title}`}
            >
              <ActionButton
                icon="edit"
                type="button"
                onClick={() => {
                  onAction("edit", item);
                }}
              >
                Edit / reschedule
              </ActionButton>
              <button
                type="button"
                className="schedule-cancel-action"
                onClick={() => {
                  onAction("cancel", item);
                }}
              >
                Cancel activity
              </button>
            </nav>
          </OverflowMenu>
        </div>
      )}
    </div>
  );
}
