import type { ReactNode, RefObject } from "react";
import { TaskDialog } from "./TaskDialog";
import "./edit-workspace.css";
/** Reuses the native task dialog; the caller owns routes, dirty state and entity data. */
export function EditWorkspace({
  modal,
  title,
  onClose,
  children,
  returnFocusTo,
}: {
  modal: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  returnFocusTo?: RefObject<HTMLElement | null>;
}) {
  return modal ? (
    <TaskDialog
      title={title}
      className="edit-workspace-modal"
      onClose={onClose}
      dismissOnBackdrop
      returnFocusTo={returnFocusTo}
    >
      {children}
    </TaskDialog>
  ) : (
    <div className="edit-workspace-fallback">{children}</div>
  );
}
