import type { ReactNode } from "react";

/** The record and its sibling actions share one surface; branch controls stay outside. */
export function HierarchyRow({
  children,
  selected,
}: {
  children: ReactNode;
  selected?: boolean;
}) {
  return (
    <div
      className="ui-hierarchy-row"
      data-selected={selected ? true : undefined}
    >
      {children}
    </div>
  );
}
