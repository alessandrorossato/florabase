import type { ComponentPropsWithRef, ReactNode } from "react";
import { Icon, type IconName } from "./Icon";
import { Tooltip } from "./Tooltip";

interface ActionStyle {
  icon?: IconName;
  trailingIcon?: IconName;
  variant?: "primary" | "secondary" | "quiet" | "danger";
}
export function ActionButton({
  icon,
  trailingIcon,
  variant,
  children,
  className = "",
  ...props
}: ComponentPropsWithRef<"button"> & ActionStyle) {
  return (
    <button
      type="button"
      {...props}
      className={`control-action${variant && variant !== "primary" ? ` button--${variant}` : ""} ${className}`.trim()}
    >
      {icon && <Icon name={icon} />}
      <span>{children}</span>
      {trailingIcon && <Icon name={trailingIcon} />}
    </button>
  );
}
export function ActionLink({
  icon,
  children,
  className = "",
  ...props
}: ComponentPropsWithRef<"a"> & { icon?: IconName }) {
  return (
    <a {...props} className={`control-action ${className}`.trim()}>
      {icon && <Icon name={icon} />}
      <span>{children}</span>
    </a>
  );
}
export function IconButton({
  icon,
  label,
  tooltip,
  visibleLabel = label,
  tooltipDisabled = false,
  shell = false,
  className = "",
  ...props
}: Omit<
  ComponentPropsWithRef<"button">,
  "children" | "aria-label" | "title"
> & {
  icon: IconName;
  label: string;
  tooltip: string;
  visibleLabel?: ReactNode;
  tooltipDisabled?: boolean;
  shell?: boolean;
}) {
  return (
    <Tooltip content={tooltip} disabled={tooltipDisabled}>
      <button
        type="button"
        {...props}
        aria-label={label}
        className={`control-icon-button button--secondary ${className}`.trim()}
      >
        <Icon name={icon} shell={shell} />
        <span className="control-icon-button__label">{visibleLabel}</span>
      </button>
    </Tooltip>
  );
}
