import { useId, type ReactNode } from "react";

/** UI Foundation v0.1. PageHeader remains in ReferenceUI for existing consumers. */
export function Page({
  titleId,
  children,
  className = "",
}: {
  titleId: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      aria-labelledby={titleId}
      className={`workspace ui-page ${className}`}
    >
      {children}
    </section>
  );
}
export function SectionHeader({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="ui-section-header">
      <h3 id={id}>{title}</h3>
      {children}
    </div>
  );
}
export function Metric({
  label,
  value,
  context,
  href,
}: {
  label: string;
  value: number;
  context: string;
  href: string;
}) {
  const contextId = useId();
  return (
    <a
      className="ui-metric"
      href={href}
      aria-label={`${label}: ${String(value)}`}
      aria-describedby={contextId}
    >
      <span className="ui-metric__label">{label}</span>
      <strong className="ui-metric__value">{value}</strong>
      <span id={contextId} className="ui-metric__context">
        {context}
      </span>
    </a>
  );
}
export function StatusBadge({
  children,
  attention = false,
}: {
  children: ReactNode;
  attention?: boolean;
}) {
  return (
    <span className={`ui-badge${attention ? " ui-badge--attention" : ""}`}>
      {children}
    </span>
  );
}
export function EmptyState({ children }: { children: ReactNode }) {
  return <p className="ui-state">{children}</p>;
}
export function LoadingState({ children }: { children: ReactNode }) {
  return (
    <p className="ui-state" role="status">
      {children}
    </p>
  );
}
export function ErrorState({
  children,
  onRetry,
}: {
  children: ReactNode;
  onRetry: () => void;
}) {
  return (
    <div className="ui-state ui-state--error" role="alert">
      <p>{children}</p>
      <button type="button" onClick={onRetry}>
        Retry
      </button>
    </div>
  );
}
