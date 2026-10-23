import { dismissDialogControlLayer } from "./controlLayers";
import { useEffect, useRef, type ReactNode, type RefObject } from "react";

function focusableControls(element: HTMLDialogElement | null) {
  return Array.from(
    element?.querySelectorAll<HTMLElement>(
      "a[href], button, input, select, textarea, [tabindex]",
    ) ?? [],
  ).filter(
    (control) =>
      control.tabIndex >= 0 &&
      !control.matches(":disabled, input[type='hidden']") &&
      !control.closest("[hidden], [inert], [aria-hidden='true']") &&
      getComputedStyle(control).display !== "none" &&
      getComputedStyle(control).visibility !== "hidden",
  );
}

/** Native modal focus handling, Escape, and return to the invoking control. */
export function TaskDialog({
  id,
  title,
  onClose,
  children,
  className,
  dismissOnBackdrop = false,
  returnFocusTo,
}: {
  id?: string;
  title: string;
  onClose: () => void;
  children: ReactNode;
  className?: string;
  dismissOnBackdrop?: boolean;
  returnFocusTo?: RefObject<HTMLElement | null>;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    returnFocus.current =
      returnFocusTo?.current ??
      (document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null);
    if (typeof element.showModal === "function") element.showModal();
    else element.setAttribute("open", "");
    focusableControls(element)[0]?.focus();
    return () => {
      if (typeof element.close === "function") element.close();
      else element.removeAttribute("open");
      returnFocus.current?.focus();
    };
  }, [returnFocusTo]);

  return (
    <dialog
      id={id}
      aria-label={title}
      className={`task-dialog${className ? ` ${className}` : ""}`}
      ref={dialog}
      onClick={(event) => {
        if (!dismissOnBackdrop || event.target !== event.currentTarget) return;
        const bounds = event.currentTarget.getBoundingClientRect();
        if (
          event.clientX < bounds.left ||
          event.clientX > bounds.right ||
          event.clientY < bounds.top ||
          event.clientY > bounds.bottom
        )
          onClose();
      }}
      onCancel={(event) => {
        event.preventDefault();
        if (!dismissDialogControlLayer(event.currentTarget)) onClose();
      }}
      onKeyDown={(event) => {
        if (event.defaultPrevented) return;
        if (event.key === "Escape") {
          event.preventDefault();
          onClose();
        }
        if (event.key !== "Tab") return;
        const focusable = focusableControls(dialog.current);
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
      {children}
      <div className="controls-overlay-host" data-controls-overlay-host="" />
    </dialog>
  );
}
