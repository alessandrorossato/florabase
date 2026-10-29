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
  fallbackFocusTo,
  modal = true,
}: {
  id?: string;
  title: string;
  onClose: () => void;
  children: ReactNode;
  className?: string;
  dismissOnBackdrop?: boolean;
  returnFocusTo?: RefObject<HTMLElement | null>;
  fallbackFocusTo?: RefObject<HTMLElement | null>;
  modal?: boolean;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (returnFocusTo?.current) returnFocus.current = returnFocusTo.current;
  });

  useEffect(() => {
    const element = dialog.current;
    const fallback = fallbackFocusTo?.current;
    if (!element) return;
    if (!modal) {
      element.setAttribute("open", "");
      return;
    }
    if (element.open) element.removeAttribute("open");
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
      const target = returnFocus.current;
      (target?.isConnected
        ? target
        : fallback?.isConnected
          ? fallback
          : null
      )?.focus();
    };
  }, [returnFocusTo, fallbackFocusTo, modal]);

  return (
    <dialog
      id={id}
      aria-label={title}
      aria-modal={modal || undefined}
      role={modal ? "dialog" : "region"}
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
        if (!modal || event.defaultPrevented) return;
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
