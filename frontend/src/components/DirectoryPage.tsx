import { type ReactNode, type MouseEventHandler, type RefObject } from "react";
import { IconButton } from "./Action";
import { ActionButton } from "./Action";
import { Page } from "./WorkspaceUI";
import { TaskDialog } from "./TaskDialog";
import type { DirectoryView } from "./directoryPresentation";
import "../styles/directory.css";

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
  children: ReactNode;
  onClick?: MouseEventHandler<HTMLLIElement>;
  selected?: boolean;
}

function RecordControls({
  label,
  checked,
  onCheck,
  selected,
  onPreview,
  previewRef,
  actions,
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
      <ActionButton
        ref={previewRef}
        variant="secondary"
        aria-label={`Quick preview ${label}`}
        aria-pressed={selected ?? false}
        onClick={(e) => {
          onPreview(e.currentTarget);
        }}
      >
        Preview
      </ActionButton>
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

export function DirectoryRow(
  props: RecordPresentation | DirectoryRecordComposition,
) {
  if ("children" in props)
    return (
      <li
        onClick={props.onClick}
        className="ui-directory-row ui-directory-row--composed"
        data-selected={props.selected ? true : undefined}
      >
        {props.children}
      </li>
    );
  return (
    <li
      className="ui-directory-row"
      data-selected={props.selected ? true : undefined}
    >
      <div className="ui-directory-thumbnail">{props.visual}</div>
      <div className="ui-directory-name">
        <a href={props.href}>{props.name}</a>
        {props.status}
      </div>
      <div className="ui-directory-metadata">{props.metadata}</div>
      <RecordControls {...props} />
    </li>
  );
}

export function DirectoryCard(
  props: RecordPresentation | DirectoryRecordComposition,
) {
  if ("children" in props)
    return (
      <li
        onClick={props.onClick}
        className="ui-directory-card ui-directory-card--composed"
        data-selected={props.selected ? true : undefined}
      >
        {props.children}
      </li>
    );
  return (
    <li
      className="ui-directory-card"
      data-selected={props.selected ? true : undefined}
    >
      <div className="ui-directory-visual">
        {props.visual ?? (
          <span className="ui-directory-no-image">
            No image for {props.label}
          </span>
        )}
      </div>
      <div className="ui-directory-card-body">
        <h3>
          <a href={props.href}>{props.name}</a>
        </h3>
        {props.status}
        <div className="ui-directory-metadata">{props.metadata}</div>
        <RecordControls {...props} />
      </div>
    </li>
  );
}

export function DirectoryInspector({
  title,
  children,
  onClose,
  returnFocusTo,
  fallbackFocusTo,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  returnFocusTo: RefObject<HTMLElement | null>;
  fallbackFocusTo: RefObject<HTMLElement | null>;
}) {
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

/** Three separate intentions; domain callers retain route and editor ownership. */
export function DirectoryRecordActions({
  label,
  onPreview,
  onDetails,
  onEdit,
}: {
  label: string;
  onPreview: (trigger: HTMLButtonElement) => void;
  onDetails: (trigger: HTMLButtonElement) => void;
  onEdit: (trigger: HTMLButtonElement) => void;
}) {
  return (
    <div
      className="ui-directory-record-actions"
      role="group"
      aria-label={`Actions for ${label}`}
    >
      <IconButton
        icon="eye"
        label={`Quick preview ${label}`}
        tooltip="Quick Preview"
        onClick={(e) => {
          onPreview(e.currentTarget);
        }}
      />
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
