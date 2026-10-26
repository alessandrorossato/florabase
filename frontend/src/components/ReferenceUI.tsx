import { Icon } from "./Icon";
import { ActionButton, IconButton } from "./Action";
import { registerControlLayer } from "./controlLayers";
import {
  useEffect,
  useLayoutEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";
import { createPortal } from "react-dom";

/** Format only a structured scientific name; retain the operator-facing label verbatim. */
export function BotanicalName({
  label,
  scientificName,
}: {
  label: string;
  scientificName?: string;
}) {
  if (!scientificName || !label.startsWith(scientificName)) return <>{label}</>;
  return (
    <>
      <i className="scientific-name">{scientificName}</i>
      {label.slice(scientificName.length)}
    </>
  );
}

/** Small layout vocabulary, proven by the BotanicalIdentity reference. */
export function PageHeader({
  title,
  titleId,
  description,
  actions,
  tools,
  eyebrow = "Collection reference",
}: {
  title: string;
  titleId: string;
  description?: string;
  actions?: ReactNode;
  tools?: ReactNode;
  eyebrow?: string;
}) {
  return (
    <header className={`page-header${tools ? " page-header--with-tools" : ""}`}>
      <div className="page-identity">
        <p className="eyebrow">{eyebrow}</p>
        <h2 id={titleId}>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      {tools && <div className="page-tools">{tools}</div>}
      {actions && <div className="page-actions">{actions}</div>}
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
  maxLength,
}: {
  id: string;
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
  hideLabel?: boolean;
  maxLength?: number;
}) {
  return (
    <div className={`field directory-search ${className}`.trim()}>
      <label className={hideLabel ? "sr-only" : undefined} htmlFor={id}>
        {label}
      </label>
      <div className="search-control">
        <Icon name="search" />
        <input
          id={id}
          type="search"
          maxLength={maxLength}
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
  disabled = false,
  triggerRef,
  triggerContent,
  closeOnAction = true,
  popoverClassName = "",
}: {
  label?: string;
  ariaLabel?: string;
  children: ReactNode;
  disabled?: boolean;
  triggerRef?: RefObject<HTMLButtonElement | null>;
  triggerContent?: ReactNode;
  closeOnAction?: boolean;
  popoverClassName?: string;
}) {
  const id = useId();
  const internalTrigger = useRef<HTMLButtonElement>(null);
  const trigger = triggerRef ?? internalTrigger;
  const panel = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [portalHost, setPortalHost] = useState<HTMLElement | null>(null);
  const [position, setPosition] = useState({ left: 12, top: 12 });
  const close = (restore = false) => {
    setOpen(false);
    if (restore) trigger.current?.focus();
  };
  const show = () => {
    setPortalHost(trigger.current?.closest("dialog") ?? document.body);
    setOpen(true);
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
  }, [open, trigger]);
  useEffect(() => {
    if (!open) return;
    const dismiss = (event: Event) => {
      if (
        event.target instanceof Node &&
        !trigger.current?.contains(event.target) &&
        !panel.current?.contains(event.target)
      ) {
        setOpen(false);
        // A pointer dismissal restores focus before the clicked control takes it.
        // Focus-driven dismissal (for example Tab) keeps the chosen destination.
        if (event.type === "pointerdown") {
          trigger.current?.focus();
          requestAnimationFrame(() => {
            // Clicking a non-focusable surface can blur the trigger after pointerdown.
            if (document.activeElement === document.body)
              trigger.current?.focus();
          });
        }
      }
    };
    const unregister = panel.current
      ? registerControlLayer({
          element: panel.current,
          priority: 2,
          dismiss: () => {
            setOpen(false);
            trigger.current?.focus();
          },
        })
      : undefined;
    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("focusin", dismiss);

    return () => {
      document.removeEventListener("pointerdown", dismiss);
      document.removeEventListener("focusin", dismiss);
      unregister?.();
    };
  }, [open, trigger]);
  const triggerProps = {
    ref: trigger,
    type: "button" as const,
    disabled,
    "aria-expanded": open,
    "aria-controls": open ? id : undefined,
    className: "overflow-trigger button--secondary",
    onClick: () => {
      if (open) close();
      else show();
    },
    onKeyDown: (event: ReactKeyboardEvent<HTMLButtonElement>) => {
      if (event.key === "Escape" && open) {
        event.preventDefault();
        event.stopPropagation();
        close(true);
      }
      if (event.key === "ArrowDown") {
        event.preventDefault();
        show();
        requestAnimationFrame(() =>
          panel.current
            ?.querySelector<HTMLElement>("button:not(:disabled),a[href]")
            ?.focus(),
        );
      }
    },
  };
  return (
    <>
      {["More", "⋯", "…"].includes(label) ? (
        <IconButton
          {...triggerProps}
          icon="more"
          label={ariaLabel ?? "More actions"}
          visibleLabel="More"
          tooltip="More actions"
          tooltipDisabled={open}
        />
      ) : (
        <ActionButton
          {...triggerProps}
          trailingIcon={triggerContent ? undefined : "chevron-down"}
          aria-label={ariaLabel}
          icon={
            triggerContent
              ? undefined
              : label.startsWith("+") || label.startsWith("Quick add")
                ? "add"
                : "more"
          }
        >
          {triggerContent ?? label.replace(/^\+\s*|\s*▾$/g, "")}
        </ActionButton>
      )}
      {open &&
        createPortal(
          <div
            id={id}
            ref={panel}
            className={`overflow-popover ${popoverClassName}`}
            role="group"
            aria-label={`${ariaLabel ?? "More actions"} menu`}
            style={position}
            onClick={(event) => {
              if (
                event.target instanceof Element &&
                event.target.closest(
                  closeOnAction ? "button,a[href]" : "a[href]",
                )
              )
                close(true);
            }}
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                event.preventDefault();
                event.stopPropagation();
                close(true);
                return;
              }
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
          portalHost ?? document.body,
        )}
    </>
  );
}
