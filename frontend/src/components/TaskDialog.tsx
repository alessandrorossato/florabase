import { useEffect, useRef, type ReactNode } from "react";

/** Native modal focus handling, Escape, and return to the invoking control. */
export function TaskDialog({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    returnFocus.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    if (typeof element.showModal === "function") element.showModal();
    else element.setAttribute("open", "");
    element
      .querySelector<HTMLElement>("input, select, textarea, button")
      ?.focus();
    return () => {
      if (typeof element.close === "function") element.close();
      else element.removeAttribute("open");
      returnFocus.current?.focus();
    };
  }, []);

  return (
    <dialog
      aria-label={title}
      className="task-dialog"
      ref={dialog}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.preventDefault();
          onClose();
        }
        if (event.key !== "Tab") return;
        const focusable = Array.from(
          dialog.current?.querySelectorAll<HTMLElement>(
            "button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])",
          ) ?? [],
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
      {children}
    </dialog>
  );
}
