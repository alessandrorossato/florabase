import { ActionButton } from "./Action";
import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { flushSync } from "react-dom";

export interface FormPanel {
  id: string;
  label: string;
  content: ReactNode;
}

// Panels remain mounted: controlled values and native FormData survive navigation.
export function FormSections({
  panels,
  submit,
  cancel,
  disabled = false,
  error,
  errorFields = [],
  label = "Form sections",
  mode = "create",
  initialPanelId,
}: {
  label?: string;
  initialPanelId?: string;
  mode?: "create" | "edit" | "page";
  panels: FormPanel[];
  submit: ReactNode;
  cancel: ReactNode;
  disabled?: boolean;
  error?: { messages: string[]; field?: string };
  errorFields?: { match: RegExp; selector: string }[];
}) {
  const prefix = useId();
  const root = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(() =>
    Math.max(
      0,
      panels.findIndex((panel) => panel.id === initialPanelId),
    ),
  );
  const index = Math.min(active, panels.length - 1);
  const reveal = useCallback((field: HTMLElement) => {
    let panel = field.closest<HTMLElement>("[data-form-panel]");
    while (panel && panel.parentElement !== root.current)
      panel =
        panel.parentElement?.closest<HTMLElement>("[data-form-panel]") ?? null;
    const next = Number(panel?.dataset.panelIndex ?? -1);
    if (next < 0) return;
    flushSync(() => {
      setActive(next);
    });
    field.focus();
  }, []);
  const errorSelector = (
    errorFields.find(({ match }) =>
      match.test(error?.field?.replaceAll("_", " ") ?? ""),
    ) ?? errorFields.find(({ match }) => match.test(error?.messages[0] ?? ""))
  )?.selector;
  useEffect(() => {
    if (!error) return;
    if (!errorSelector) return;
    const frame = requestAnimationFrame(() => {
      const field = root.current?.querySelector<HTMLElement>(errorSelector);
      if (field) reveal(field);
    });
    return () => {
      cancelAnimationFrame(frame);
    };
  }, [error, errorSelector, reveal]);
  function navigate(next: number, focusPanel = false) {
    flushSync(() => {
      setActive(next);
    });
    root.current
      ?.querySelector<HTMLElement>(
        focusPanel
          ? `[data-form-panel="${panels[next].id}"]`
          : `[role="tab"][data-index="${String(next)}"]`,
      )
      ?.focus();
  }

  return (
    <div
      className={`form-sections form-sections--${mode}`}
      ref={root}
      onInvalidCapture={(event) => {
        // Reveal the first native-invalid field before the browser tries to focus it.
        event.preventDefault();
        const scope =
          event.target instanceof Element
            ? (event.target.closest("form") ?? root.current)
            : root.current;
        const first = scope?.querySelector<HTMLElement>(
          "input:invalid, select:invalid, textarea:invalid",
        );
        if (first) reveal(first);
      }}
    >
      {mode !== "page" && (
        <div role="tablist" aria-label={label} className="form-section-tabs">
          {panels.map(({ id, label }, position) => (
            <button
              key={id}
              type="button"
              role="tab"
              id={`${prefix}-tab-${id}`}
              aria-controls={`${prefix}-panel-${id}`}
              aria-selected={position === index}
              tabIndex={position === index ? 0 : -1}
              data-index={position}
              disabled={disabled}
              onClick={() => {
                navigate(position);
              }}
              onKeyDown={(event) => {
                const next =
                  event.key === "ArrowRight"
                    ? (position + 1) % panels.length
                    : event.key === "ArrowLeft"
                      ? (position + panels.length - 1) % panels.length
                      : event.key === "Home"
                        ? 0
                        : event.key === "End"
                          ? panels.length - 1
                          : null;
                if (next !== null) {
                  event.preventDefault();
                  navigate(next);
                }
              }}
            >
              {label}
            </button>
          ))}
        </div>
      )}
      {panels.map(({ id, label: panelLabel, content }, position) => (
        <div
          key={id}
          role={mode === "page" ? "region" : "tabpanel"}
          id={`${prefix}-panel-${id}`}
          aria-labelledby={`${prefix}-${mode === "page" ? "heading" : "tab"}-${id}`}
          data-form-panel={id}
          data-panel-index={position}
          hidden={mode !== "page" && position !== index}
          tabIndex={-1}
          className="form-section-panel"
        >
          {mode === "page" && (
            <h3 id={`${prefix}-heading-${id}`}>{panelLabel}</h3>
          )}
          {mode === "page" && error && errorSelector && position === index && (
            <p className="notice notice--error">{error.messages[0]}</p>
          )}
          {content}
        </div>
      ))}
      <div className="form-section-footer">
        <div className="form-section-footer__return">
          {mode === "create" && index > 0 && (
            <ActionButton
              icon="back"
              type="button"
              className="button--secondary"
              disabled={disabled}
              onClick={() => {
                navigate(index - 1, true);
              }}
            >
              Back
            </ActionButton>
          )}
          {cancel}
        </div>
        {mode !== "create" || index === panels.length - 1 ? (
          <span key="submit" className="form-final-action">
            {submit}
          </span>
        ) : (
          <button
            key="next"
            type="button"
            disabled={disabled}
            onClick={() => {
              navigate(index + 1, true);
            }}
          >
            Next
          </button>
        )}
      </div>
    </div>
  );
}
