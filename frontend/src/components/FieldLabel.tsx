import type { ReactNode } from "react";
import "./field-label.css";

/** Caption only: controls expose their own native/ARIA required state. */
export function FieldLabel({
  children,
  required = false,
  as: Element = "label",
  htmlFor,
  id,
  className,
}: {
  children: ReactNode;
  required?: boolean;
  as?: "label" | "legend" | "span";
  htmlFor?: string;
  id?: string;
  className?: string;
}) {
  return (
    <Element
      htmlFor={htmlFor}
      id={id}
      className={className}
      data-required={required || undefined}
    >
      {children}
      {required && <span className="required-mark" aria-hidden="true" />}
    </Element>
  );
}
