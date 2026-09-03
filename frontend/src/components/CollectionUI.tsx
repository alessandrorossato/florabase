import type { ReactNode } from "react";

export interface TabItem<TabId extends string = string> {
  id: TabId;
  label: string;
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
  onEdit,
  editLabel = "Edit",
  overflow,
}: {
  eyebrow: string;
  title: string;
  secondary?: ReactNode;
  status?: ReactNode;
  onEdit?: () => void;
  editLabel?: string;
  overflow?: ReactNode;
}) {
  return (
    <header className="detail-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h3>{title}</h3>
        {secondary && <div className="detail-secondary">{secondary}</div>}
        {status && <div className="detail-status">{status}</div>}
      </div>
      {(onEdit ?? overflow) && (
        <div className="actions detail-actions">
          {onEdit && (
            <button type="button" onClick={onEdit}>
              {editLabel}
            </button>
          )}
          {overflow}
        </div>
      )}
    </header>
  );
}

export function DetailTabs<TabId extends string>({
  tabs,
  selected,
  onSelect,
}: {
  tabs: TabItem<TabId>[];
  selected: TabId;
  onSelect: (id: TabId) => void;
}) {
  return (
    <div aria-label="Record sections" className="detail-tabs" role="tablist">
      {tabs.map((tab) => (
        <button
          aria-selected={selected === tab.id}
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
