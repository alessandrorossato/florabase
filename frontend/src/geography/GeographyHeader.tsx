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
          { label: "Explore" },
          { label: "Geography", href: geographyHref("overview") },
          { label },
        ]}
      />
      <PageHeader
        title="Geography"
        titleId="geography-title"
        eyebrow=""
        description={description}
        tools={tools}
        actions={actions}
      />
      <h3 className="sr-only" id={`geography-${view}-title`}>
        {label}
      </h3>
    </>
  );
}
