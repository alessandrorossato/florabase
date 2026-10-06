import {
  useEffect,
  useLayoutEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";

/** Small layout vocabulary, proven by the BotanicalIdentity reference. */
export function PageHeader({
  title,
  titleId,
  description,
  actions,
  eyebrow = "Collection reference",
}: {
  title: string;
  titleId: string;
  description: string;
  actions: ReactNode;
  eyebrow?: string;
}) {
  return (
    <header className="page-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
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
  hideLabel = false,
}: {
  id: string;
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
  hideLabel?: boolean;
}) {
  return (
    <div className={`field directory-search ${className}`.trim()}>
      <label className={hideLabel ? "sr-only" : undefined} htmlFor={id}>
        {label}
      </label>
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

/** Compact record inspection shared by the operational directories. */
export function RecordPreview({
  title,
  type,
  secondary,
  facts,
  actions,
  visual,
}: {
  title: string;
  type: string;
  secondary?: ReactNode;
  visual?: ReactNode;
  facts: { label: string; value: ReactNode }[];
  actions: ReactNode;
}) {
  return (
    <QuickPreview>
      {visual}
      <p className="record-preview__type">{type}</p>
      <h3>{title}</h3>
      {secondary && <p>{secondary}</p>}
      <dl className="record-preview__facts">
        {facts.map(({ label, value }) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <div className="actions record-preview__actions">{actions}</div>
    </QuickPreview>
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
  const id = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({ left: 12, top: 12 });
  const close = (restore = false) => {
    setOpen(false);
    if (restore) trigger.current?.focus();
  };
  useLayoutEffect(() => {
    if (!open) return;
    const place = () => {
      const anchor = trigger.current?.getBoundingClientRect();
      const box = panel.current?.getBoundingClientRect();
      if (!anchor || !box) return;
      const left = Math.max(
        12,
        Math.min(anchor.right - box.width, window.innerWidth - box.width - 12),
      );
      const below = anchor.bottom + 8;
      const top = Math.max(
        12,
        Math.min(
          below + box.height <= window.innerHeight - 12
            ? below
            : anchor.top - box.height - 8,
          window.innerHeight - box.height - 12,
        ),
      );
      setPosition((current) =>
        current.left === left && current.top === top ? current : { left, top },
      );
    };
    place();
    const observer =
      typeof ResizeObserver === "undefined"
        ? undefined
        : new ResizeObserver(place);
    if (panel.current) observer?.observe(panel.current);
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      observer?.disconnect();
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [open]);
  useEffect(() => {
    if (!open) return;
    const dismiss = (event: Event) => {
      if (
        event.target instanceof Node &&
        !trigger.current?.contains(event.target) &&
        !panel.current?.contains(event.target)
      )
        setOpen(false);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
        trigger.current?.focus();
      }
    };
    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("focusin", dismiss);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", dismiss);
      document.removeEventListener("focusin", dismiss);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);
  return (
    <>
      <button
        className="overflow-trigger button--secondary"
        ref={trigger}
        type="button"
        aria-label={ariaLabel}
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        onClick={() => {
          setOpen((current) => !current);
        }}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setOpen(true);
            requestAnimationFrame(() =>
              panel.current
                ?.querySelector<HTMLElement>("button:not(:disabled),a[href]")
                ?.focus(),
            );
          }
        }}
      >
        {label}
      </button>
      {open &&
        createPortal(
          <div
            id={id}
            ref={panel}
            className="overflow-popover"
            role="group"
            aria-label={`${ariaLabel ?? "More actions"} menu`}
            style={position}
            onClick={(event) => {
              if (
                event.target instanceof Element &&
                event.target.closest("button,a[href]")
              )
                close(true);
            }}
            onKeyDown={(event) => {
              const items = Array.from(
                panel.current?.querySelectorAll<HTMLElement>(
                  "button:not(:disabled),a[href]",
                ) ?? [],
              );
              const index = items.indexOf(
                document.activeElement as HTMLElement,
              );
              const next =
                event.key === "ArrowDown"
                  ? (index + 1) % items.length
                  : event.key === "ArrowUp"
                    ? (index - 1 + items.length) % items.length
                    : event.key === "Home"
                      ? 0
                      : event.key === "End"
                        ? items.length - 1
                        : null;
              if (next !== null) {
                event.preventDefault();
                items[next]?.focus();
              }
            }}
          >
            {children}
          </div>,
          document.body,
        )}
    </>
  );
}
