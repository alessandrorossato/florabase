import { useState } from "react";
import { OverflowMenu } from "../components/ReferenceUI";
import { TaskDialog } from "../components/TaskDialog";
import { ScheduleTargetPicker } from "../schedule/ScheduleTargetPicker";

// Add a delivered canonical route here when another recording workflow is ready.
// Target-dependent workflows reuse their own detail route, never a small copy of their form.
const recordWorkflows = [
  { label: "Record harvest", href: "#/harvests?action=create" },
  { label: "Record sowing", href: "#/sowings?action=create" },
  { label: "Move plants / groups", href: "#/plants" },
  { label: "Complete scheduled work", href: "#/schedule" },
] as const;

type NotebookTarget = "plant" | "plant_group";
export function RecordLauncher() {
  const [task, setTask] = useState<"journal" | "germination" | null>(null);
  const [kind, setKind] = useState<NotebookTarget>("plant");
  const [targetId, setTargetId] = useState("");
  const targetKind = task === "germination" ? "sowing" : kind;
  const title =
    task === "germination" ? "Record germination" : "Record a Journal entry";
  const targetHref =
    task === "germination"
      ? `#/sowings/${targetId}?tab=germination`
      : `#/${kind === "plant" ? "plants" : "plant-groups"}/${targetId}?tab=events`;
  function choose(next: "journal" | "germination") {
    setTargetId("");
    setTask(next);
  }
  return (
    <>
      <OverflowMenu label="+ Record" ariaLabel="Record">
        <nav className="dashboard-quick-add" aria-label="Record choices">
          <button
            type="button"
            onClick={() => {
              choose("journal");
            }}
          >
            Add observation / note
          </button>
          {recordWorkflows.map(({ label, href }) => (
            <a key={href} href={href}>
              {label}
            </a>
          ))}
          <button
            type="button"
            onClick={() => {
              choose("germination");
            }}
          >
            Record germination
          </button>
          <button
            type="button"
            onClick={() => {
              choose("journal");
            }}
          >
            Other journal entry
          </button>
        </nav>
      </OverflowMenu>
      {task && (
        <TaskDialog
          title={title}
          className="journal-entry-dialog"
          dismissOnBackdrop
          onClose={() => {
            setTask(null);
          }}
        >
          <h3>{title}</h3>
          {task === "journal" ? (
            <label className="field">
              Record type
              <select
                value={kind}
                onChange={(event) => {
                  setKind(event.target.value as NotebookTarget);
                  setTargetId("");
                }}
              >
                <option value="plant">Plant</option>
                <option value="plant_group">Plant group</option>
              </select>
            </label>
          ) : (
            <p>Choose the Sowing to open its germination observations.</p>
          )}
          <ScheduleTargetPicker
            key={targetKind}
            allowInactive
            kind={targetKind}
            value={targetId}
            selected={null}
            onChange={setTargetId}
          />
          <div className="actions">
            {targetId && (
              <a
                className="button-link"
                href={targetHref}
                onClick={() => {
                  setTask(null);
                }}
              >
                {task === "journal"
                  ? "Continue to Journal"
                  : "Open germination observations"}
              </a>
            )}
            <button
              className="button--secondary"
              type="button"
              onClick={() => {
                setTask(null);
              }}
            >
              Cancel
            </button>
          </div>
        </TaskDialog>
      )}
    </>
  );
}
