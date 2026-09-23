import { useEffect, useRef, type ReactNode } from "react";

/** Small layout vocabulary, proven by the BotanicalIdentity reference. */
export function PageHeader({
  title,
  titleId,
  description,
  actions,
}: {
  title: string;
  titleId: string;
  description: string;
  actions: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <p className="eyebrow">Collection reference</p>
        <h2 id={titleId}>{title}</h2>
        <p>{description}</p>
      </div>
      {actions}
    </header>
  );
}

export function DirectorySearch({
  id,
  label,
  placeholder,
  value,
  onChange,
  disabled = false,
  className = "",
}: {
  id: string;
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <div className={`field directory-search ${className}`.trim()}>
      <label htmlFor={id}>{label}</label>
      <div className="search-control">
        <span aria-hidden="true">⌕</span>
        <input
          id={id}
          type="search"
          placeholder={placeholder}
          value={value}
          disabled={disabled}
          onChange={(event) => {
            onChange(event.currentTarget.value);
          }}
        />
      </div>
    </div>
  );
}

export function FormSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <fieldset className="form-section">
      <legend>{title}</legend>
      <div className="form-grid">{children}</div>
    </fieldset>
  );
}

export function FormActions({ children }: { children: ReactNode }) {
  return <div className="actions form-actions">{children}</div>;
}

export function StatStrip({
  items,
  label = "Active collection records",
}: {
  items: { label: string; value: number }[];
  label?: string;
}) {
  return (
    <dl className="stat-strip" aria-label={label}>
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function QuickPreview({ children }: { children: ReactNode }) {
  return (
    <aside className="quick-preview" aria-label="Quick preview">
      <p className="eyebrow">Quick preview</p>
      {children}
    </aside>
  );
}

export function OverflowMenu({
  label = "More",
  ariaLabel,
  children,
}: {
  label?: string;
  ariaLabel?: string;
  children: ReactNode;
}) {
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const triggerRef = useRef<HTMLElement>(null);
  const close = (restoreFocus = false) => {
    const details = detailsRef.current;
    if (!details?.open) return;
    details.open = false;
    if (restoreFocus) triggerRef.current?.focus();
  };

  useEffect(() => {
    const details = detailsRef.current;
    if (!details) return;
    const dismissOutside = (event: Event) => {
      if (
        details.open &&
        event.target instanceof Node &&
        !details.contains(event.target)
      ) {
        details.open = false;
      }
    };
    const closePeers = () => {
      if (!details.open) return;
      for (const peer of document.querySelectorAll<HTMLDetailsElement>(
        "details.overflow-menu[open]",
      )) {
        if (peer !== details) peer.open = false;
      }
    };
    document.addEventListener("pointerdown", dismissOutside);
    document.addEventListener("focusin", dismissOutside);
    details.addEventListener("toggle", closePeers);
    return () => {
      document.removeEventListener("pointerdown", dismissOutside);
      document.removeEventListener("focusin", dismissOutside);
      details.removeEventListener("toggle", closePeers);
    };
  }, []);

  return (
    <details
      className={`overflow-menu${label === "More" ? " overflow-menu--text" : ""}`}
      ref={detailsRef}
      onKeyDown={(event) => {
        if (event.key !== "Escape" || !detailsRef.current?.open) return;
        event.preventDefault();
        event.stopPropagation();
        close(true);
      }}
    >
      <summary ref={triggerRef} aria-label={ariaLabel}>
        {label}
      </summary>
      <div
        className="overflow-menu__panel"
        onClick={(event) => {
          if (event.target instanceof Element && event.target.closest("button"))
            close(true);
        }}
      >
        {children}
      </div>
    </details>
  );
}
