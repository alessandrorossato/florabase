import type { ReactNode } from "react";
import { Page } from "./WorkspaceUI";

/** Source labels and occurrence/recorded-time semantics stay in the supplied chronology. */
export function ActivityPage({
  titleId,
  className = "",
  header,
  toolbar,
  chronology,
  feedback,
  pagination,
}: {
  titleId: string;
  className?: string;
  header: ReactNode;
  toolbar?: ReactNode;
  chronology: ReactNode;
  feedback?: ReactNode;
  pagination?: ReactNode;
}) {
  return (
    <Page titleId={titleId} className={className}>
      {header}
      {toolbar}
      {feedback}
      {chronology}
      {pagination}
    </Page>
  );
}
