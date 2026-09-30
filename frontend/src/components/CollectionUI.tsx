import type { ReactNode, RefObject } from "react";

export interface TabItem<TabId extends string = string> {
  id: TabId;
  label: string;
}

export function WorkspaceIntro({
  eyebrow,
  title,
  titleId,
  description,
  actions,
  contextOnly = false,
  contextActions,
}: {
  eyebrow: string;
  title: string;
  titleId: string;
  description: string;
  actions?: ReactNode;
  contextOnly?: boolean;
  contextActions?: ReactNode;
}) {
  if (contextOnly)
    return (
      <>
        <h2 className="sr-only" id={titleId}>
          {title}
        </h2>
        {(Boolean(actions) || Boolean(contextActions)) && (
          <div className="workspace-context-actions">
            {contextActions}
            {actions}
          </div>
        )}
      </>
    );
  return (
    <header className="workspace-intro seed-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2 id={titleId}>{title}</h2>
        <p>{description}</p>
      </div>
      {actions}
    </header>
  );
}

export function Breadcrumbs({
  items,
}: {
  items: { label: string; href?: string }[];
}) {
  return (
    <nav aria-label="Breadcrumb" className="breadcrumbs">
      <ol>
        {items.map((item, index) => (
          <li key={`${item.label}:${String(index)}`}>
            {item.href ? <a href={item.href}>{item.label}</a> : item.label}
          </li>
        ))}
      </ol>
    </nav>
  );
}

export function DetailHeader({
  eyebrow,
  title,
  secondary,
  status,
  primaryActions,
  onEdit,
  editLabel = "Edit",
  overflow,
  headingRef,
  visual,
}: {
  eyebrow: string;
  title: string;
  secondary?: ReactNode;
  status?: ReactNode;
  primaryActions?: ReactNode;
  onEdit?: () => void;
  editLabel?: string;
  overflow?: ReactNode;
  headingRef?: RefObject<HTMLHeadingElement | null>;
  visual?: ReactNode;
}) {
  return (
    <header className="detail-header">
      <div className="detail-identity">
        {visual && <div className="detail-visual">{visual}</div>}
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h3 ref={headingRef} tabIndex={headingRef ? -1 : undefined}>
            {title}
          </h3>
          {secondary && <div className="detail-secondary">{secondary}</div>}
          {status && <div className="detail-status">{status}</div>}
        </div>
      </div>
      {(primaryActions ?? onEdit ?? overflow) && (
        <div className="actions detail-actions">
          {primaryActions}
          {onEdit && (
            <button
              className={primaryActions ? "button--secondary" : undefined}
              type="button"
              onClick={onEdit}
            >
              {editLabel}
            </button>
          )}
          {overflow}
        </div>
      )}
    </header>
  );
}

export function DetailContext({
  items,
}: {
  items: { label: string; value: ReactNode }[];
}) {
  return (
    <dl className="detail-context">
      {items.map(({ label, value }) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function DetailTabs<TabId extends string>({
  tabs,
  selected,
  onSelect,
  label = "Record sections",
}: {
  label?: string;
  tabs: TabItem<TabId>[];
  selected: TabId;
  onSelect: (id: TabId) => void;
}) {
  return (
    <div aria-label={label} className="detail-tabs" role="tablist">
      {tabs.map((tab) => (
        <button
          aria-selected={selected === tab.id}
          aria-controls={`panel-${tab.id}`}
          className="detail-tab"
          id={`tab-${tab.id}`}
          key={tab.id}
          role="tab"
          tabIndex={selected === tab.id ? 0 : -1}
          type="button"
          onClick={() => {
            onSelect(tab.id);
          }}
          onKeyDown={(event) => {
            if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key))
              return;
            event.preventDefault();
            const index = tabs.findIndex(({ id }) => id === selected);
            const next =
              event.key === "Home"
                ? 0
                : event.key === "End"
                  ? tabs.length - 1
                  : (index +
                      (event.key === "ArrowRight" ? 1 : -1) +
                      tabs.length) %
                    tabs.length;
            onSelect(tabs[next].id);
            const target = event.currentTarget.parentElement?.children[next];
            if (target instanceof HTMLElement)
              window.setTimeout(() => {
                target.focus();
              });
          }}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export function CollectionCard({
  title,
  eyebrow,
  href,
  children,
}: {
  title: string;
  eyebrow?: string;
  href?: string;
  children?: ReactNode;
}) {
  return (
    <article className="collection-card">
      {eyebrow && <p className="card-type">{eyebrow}</p>}
      <h3>{href ? <a href={href}>{title}</a> : title}</h3>
      {children}
    </article>
  );
}
