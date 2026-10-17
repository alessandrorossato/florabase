import type { ReactNode } from "react";
import "./detail-empty-state.css";

export function DetailEmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="detail-empty-message detail-empty-state">
      <p>{children}</p>
    </div>
  );
}
