import type { ReactNode } from "react";
import "./geography.css";
import { Breadcrumbs } from "../components/CollectionUI";
import { PageHeader } from "../components/ReferenceUI";
import { geographyHref, geographyViews, type GeographyView } from "./routes";

export function GeographyHeader({
  view,
  description,
  tools,
  actions,
}: {
  view: GeographyView;
  description: string;
  tools?: ReactNode;
  actions?: ReactNode;
}) {
  const label = geographyViews.find(([id]) => id === view)?.[1] ?? view;
  return (
    <>
      <Breadcrumbs
        items={[
          { label: "Explore", href: "#/explore" },
          { label: "Geography", href: geographyHref("overview") },
          { label },
        ]}
      />
      <PageHeader
        // The page title is the menu entry the person chose, like every other section.
        title={view === "overview" ? "Geography" : label}
        titleId={
          view === "overview" ? "geography-title" : `geography-${view}-title`
        }
        eyebrow=""
        description={description}
        tools={tools}
        actions={actions}
      />
      {view === "overview" && (
        <h3 className="sr-only" id={`geography-${view}-title`}>
          {label}
        </h3>
      )}
    </>
  );
}
