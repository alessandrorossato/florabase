import {
  type ReactNode,
  type MouseEventHandler,
  type RefObject,
  type ComponentPropsWithRef,
  useEffect,
  useRef,
  useCallback,
} from "react";
import { Tooltip } from "./Tooltip";
import { IconButton } from "./Action";
import { ActionButton } from "./Action";
import { Page } from "./WorkspaceUI";
import { TaskDialog } from "./TaskDialog";
import type { DirectoryView } from "./directoryPresentation";
import "../styles/directory.css";
import "../styles/directory-workspace.css";
import "../styles/directory-system.css";

/** Named layout slots only. The caller owns loading, URLs, filtering and mutations. */
export function DirectoryPage({
  titleId,
  header,
  toolbar,
  selection,
  content,
  pagination,
  feedback,
  inspector,
  className = "",
}: {
  titleId: string;
  header: ReactNode;
  toolbar?: ReactNode;
  selection?: ReactNode;
  content: ReactNode;
  pagination?: ReactNode;
  feedback?: ReactNode;
  inspector?: ReactNode;
  className?: string;
}) {
  return (
    <Page titleId={titleId} className={`ui-directory-page ${className}`}>
      {header}
      {toolbar}
      {selection}
      {feedback}
      <div
        className={`ui-directory-frame${inspector ? " ui-directory-frame--selected" : ""}`}
      >
        <div className="ui-directory-main">
          {content}
          {pagination}
        </div>
        {inspector}
      </div>
    </Page>
  );
}

export function DirectoryViewSwitcher({
  value,
  onChange,
}: {
  value: DirectoryView;
  onChange: (value: DirectoryView) => void;
}) {
  return (
    <div className="ui-view-switcher" role="group" aria-label="Directory view">
      {(["list", "gallery"] as const).map((view) => (
        <ActionButton
          key={view}
          variant="secondary"
          icon={view}
          aria-pressed={value === view}
          onClick={() => {
            onChange(view);
          }}
        >
          {view === "list" ? "List" : "Gallery"}
        </ActionButton>
      ))}
    </div>
  );
}

/** A native record surface; status description is shared with pointer and keyboard users. */
export function DirectoryTrigger({
  description = "Open Quick Preview",
  children,
  ...props
}: ComponentPropsWithRef<"button"> & { description?: string }) {
  return (
    <Tooltip content={description}>
      <button
        type="button"
        {...props}
        className={`ui-directory-trigger ${props.className ?? ""}`}
      >
        {children}
      </button>
    </Tooltip>
  );
}

export function DirectoryInspectorPlaceholder({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <aside
      className="ui-directory-inspector ui-directory-side-preview ui-inspector-placeholder"
      aria-label="Quick preview"
    >
      <h3>{title}</h3>
      <p>{children}</p>
    </aside>
  );
}

/** Shared directory grid: results span the records and inspector columns. */
export function DirectoryWorkspace({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`ui-directory-workspace ${className}`}>{children}</div>
  );
}

/** Presentation slots only; domain state, routes and operations stay with the caller. */
export function DirectoryRecordContent({
  visual,
  name,
  secondary,
  summary,
  status,
}: {
  visual: ReactNode;
  name: ReactNode;
  secondary?: ReactNode;
  summary?: ReactNode;
  status?: ReactNode;
}) {
  return (
    <span className="ui-record-content">
      <span className="ui-record-visual">{visual}</span>
      <span className="ui-record-identity">
        <span className="ui-record-title">
          <strong>{name}</strong>
          {status}
        </span>
        {secondary && <span className="ui-record-secondary">{secondary}</span>}
      </span>
      {summary != null && <span className="ui-record-summary">{summary}</span>}
    </span>
  );
}

interface RecordPresentation {
  label: string;
  name: ReactNode;
  href: string;
  visual?: ReactNode;
  metadata: ReactNode;
  status?: ReactNode;
  actions?: ReactNode;
  selected?: boolean;
  checked?: boolean;
  onCheck?: (checked: boolean) => void;
  onPreview: (trigger: HTMLButtonElement) => void;
  previewRef?: RefObject<HTMLButtonElement | null>;
}

/** Existing domains can supply their own complete interaction without nesting buttons. */
interface DirectoryRecordComposition {
  previewId?: string;
  children: ReactNode;
  onClick?: MouseEventHandler<HTMLLIElement>;
  selected?: boolean;
}

function RecordControls({
  label,
  checked,
  onCheck,
  actions,
  href,
}: RecordPresentation) {
  return (
    <div className="ui-directory-record-actions">
      {onCheck && (
        <label className="ui-record-selection">
          <input
            type="checkbox"
            checked={checked ?? false}
            onChange={(e) => {
              onCheck(e.currentTarget.checked);
            }}
          />
          <span className="sr-only">Select {label}</span>
        </label>
      )}
      <a className="button-link button--secondary" href={href}>
        Details {label}
      </a>
      {actions}
    </div>
  );
}

export function DirectoryRecords({
  view,
  label,
  children,
  listRef,
  photoTitles = false,
}: {
  view: DirectoryView;
  label: string;
  children: ReactNode;
  listRef?: RefObject<HTMLUListElement | null>;
  photoTitles?: boolean;
}) {
  return (
    <ul
      ref={listRef}
      tabIndex={listRef ? 0 : undefined}
      className={`ui-directory-records ui-directory-records--${view}${photoTitles ? " ui-directory-records--photo-titles" : ""}`}
      aria-label={label}
    >
      {children}
    </ul>
  );
}

function RecordSurface({
  previewRef,
  selected,
  onPreview,
  label,
  visual,
  name,
  status,
  metadata,
  gallery = false,
}: RecordPresentation & { gallery?: boolean }) {
  return (
    <DirectoryTrigger
      ref={previewRef}
      aria-label={`Quick preview ${label}`}
      aria-pressed={selected ?? false}
      onClick={(event) => {
        onPreview(event.currentTarget);
      }}
    >
      <span
        className={gallery ? "ui-directory-visual" : "ui-directory-thumbnail"}
      >
        {visual ?? (
          <span className="ui-directory-no-image">No image for {label}</span>
        )}
      </span>
      <span className="ui-directory-record-name">
        <strong>{name}</strong>
      </span>
      {status}
      <span className="ui-directory-metadata">{metadata}</span>
    </DirectoryTrigger>
  );
}
export function DirectoryRow(
  props: RecordPresentation | DirectoryRecordComposition,
) {
  return (
    <li
      data-preview-id={"children" in props ? props.previewId : undefined}
      onClick={"children" in props ? props.onClick : undefined}
      className="ui-directory-row ui-directory-row--composed"
      data-selected={props.selected ? true : undefined}
    >
      {"children" in props ? (
        props.children
      ) : (
        <>
          <RecordSurface {...props} />
          <RecordControls {...props} />
        </>
      )}
    </li>
  );
}
export function DirectoryCard(
  props: RecordPresentation | DirectoryRecordComposition,
) {
  return (
    <li
      data-preview-id={"children" in props ? props.previewId : undefined}
      onClick={"children" in props ? props.onClick : undefined}
      className="ui-directory-card ui-directory-card--composed"
      data-selected={props.selected ? true : undefined}
    >
      {"children" in props ? (
        props.children
      ) : (
        <>
          <RecordSurface {...props} gallery />
          <RecordControls {...props} />
        </>
      )}
    </li>
  );
}

export function DirectoryInspector({
  title,
  children,
  onClose,
  returnFocusTo,
  fallbackFocusTo,
  mode = "side",
  focusOnOpen = true,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  returnFocusTo: RefObject<HTMLElement | null>;
  fallbackFocusTo: RefObject<HTMLElement | null>;
  mode?: "modal" | "side";
  focusOnOpen?: boolean;
}) {
  if (mode === "side")
    return (
      <SideInspector
        focusOnOpen={focusOnOpen}
        title={title}
        onClose={onClose}
        returnFocusTo={returnFocusTo}
        fallbackFocusTo={fallbackFocusTo}
      >
        {children}
      </SideInspector>
    );
  return (
    <TaskDialog
      title={title}
      className="ui-directory-preview-overlay"
      onClose={onClose}
      returnFocusTo={returnFocusTo}
      fallbackFocusTo={fallbackFocusTo}
      dismissOnBackdrop
    >
      <div className="ui-inspector-heading">
        <h3>{title}</h3>
        <ActionButton icon="close" variant="quiet" onClick={onClose}>
          Close preview
        </ActionButton>
      </div>
      {children}
    </TaskDialog>
  );
}

/** Nonmodal Collection inspection; no backdrop, inert directory or focus trap. */
function SideInspector({
  focusOnOpen,
  title,
  children,
  onClose,
  returnFocusTo,
  fallbackFocusTo,
}: {
  focusOnOpen: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
  returnFocusTo: RefObject<HTMLElement | null>;
  fallbackFocusTo: RefObject<HTMLElement | null>;
}) {
  const closeButton = useRef<HTMLButtonElement>(null);
  const latest = useRef({ onClose, returnFocusTo, fallbackFocusTo });
  useEffect(() => {
    latest.current = { onClose, returnFocusTo, fallbackFocusTo };
  });
  const dismiss = useCallback(() => {
    const current = latest.current;
    current.onClose();
    const trigger = current.returnFocusTo.current;
    const fallback = current.fallbackFocusTo.current;
    (trigger?.isConnected
      ? trigger
      : fallback?.isConnected
        ? fallback
        : null
    )?.focus({ preventScroll: true });
  }, []);
  useEffect(() => {
    if (focusOnOpen) closeButton.current?.focus({ preventScroll: true });
    function escape(event: KeyboardEvent) {
      if (
        event.key !== "Escape" ||
        event.defaultPrevented ||
        document.querySelector("dialog[open]")
      )
        return;
      event.preventDefault();
      dismiss();
    }
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("keydown", escape);
    };
  }, [dismiss, focusOnOpen]);
  return (
    <aside
      className="ui-directory-inspector ui-directory-side-preview"
      aria-label={title}
    >
      <div className="ui-inspector-heading">
        <h3>{title}</h3>
        <ActionButton
          ref={closeButton}
          aria-label="Close preview"
          title="Close preview"
          icon="close"
          variant="quiet"
          onClick={dismiss}
        >
          Close preview
        </ActionButton>
      </div>
      <div className="ui-inspector-content">{children}</div>
    </aside>
  );
}

/** Domain actions plus direct Details and Edit actions for a directory record. */
export function DirectoryRecordActions({
  label,
  extraActions,
  onDetails,
  onEdit,
}: {
  label: string;
  extraActions?: ReactNode;
  onDetails: (trigger: HTMLButtonElement) => void;
  onEdit: (trigger: HTMLButtonElement) => void;
}) {
  return (
    <div
      className="ui-directory-record-actions"
      role="group"
      aria-label={`Actions for ${label}`}
    >
      {extraActions}
      <IconButton
        icon="document"
        label={`Details ${label}`}
        tooltip="Details"
        onClick={(e) => {
          onDetails(e.currentTarget);
        }}
      />
      <IconButton
        icon="edit"
        label={`Edit ${label}`}
        tooltip="Edit"
        onClick={(e) => {
          onEdit(e.currentTarget);
        }}
      />
    </div>
  );
}
