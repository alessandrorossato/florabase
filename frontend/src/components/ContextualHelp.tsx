import { useEffect, useId, useRef, useState, type ReactNode } from "react";

export function FieldHelp({
  id,
  children,
}: {
  id: string;
  children: ReactNode;
}) {
  return (
    <small className="field-help" id={id}>
      {children}
    </small>
  );
}

export function InfoDisclosure({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const triggerId = useId();
  const trigger = useRef<HTMLButtonElement>(null);

  function close() {
    setOpen(false);
    window.setTimeout(() => trigger.current?.focus(), 0);
  }

  return (
    <div
      className="info-disclosure"
      onKeyDown={(event) => {
        if (event.key === "Escape" && open) {
          event.preventDefault();
          close();
        }
      }}
    >
      <button
        aria-controls={panelId}
        aria-expanded={open}
        className="info-disclosure__trigger"
        id={triggerId}
        ref={trigger}
        type="button"
        onClick={() => {
          setOpen((value) => !value);
        }}
      >
        {label}
      </button>
      <div
        aria-labelledby={triggerId}
        className="info-disclosure__panel"
        hidden={!open}
        id={panelId}
        role="region"
      >
        {children}
      </div>
    </div>
  );
}

export function ContextHelpDialog({
  buttonLabel,
  title,
  children,
}: {
  buttonLabel: string;
  title: string;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const titleId = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const dialog = useRef<HTMLDivElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) closeButton.current?.focus();
  }, [open]);

  function close() {
    setOpen(false);
    window.setTimeout(() => trigger.current?.focus(), 0);
  }

  return (
    <>
      <button
        className="button--secondary context-help-trigger"
        ref={trigger}
        type="button"
        onClick={() => {
          setOpen(true);
        }}
      >
        {buttonLabel}
      </button>
      {open && (
        <div
          className="dialog-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) close();
          }}
        >
          <div
            aria-labelledby={titleId}
            aria-modal="true"
            className="context-dialog context-help-dialog"
            ref={dialog}
            role="dialog"
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                event.preventDefault();
                close();
                return;
              }
              if (event.key !== "Tab" || !dialog.current) return;
              const focusable = Array.from(
                dialog.current.querySelectorAll<HTMLElement>(
                  "button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled])",
                ),
              );
              const first = focusable.at(0);
              const last = focusable.at(-1);
              if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last?.focus();
              } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first?.focus();
              }
            }}
          >
            <h3 id={titleId}>{title}</h3>
            <div className="context-help-dialog__content">{children}</div>
            <button
              className="button--secondary"
              ref={closeButton}
              type="button"
              onClick={close}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </>
  );
}
