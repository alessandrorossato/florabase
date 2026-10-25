import { lazy, Suspense } from "react";
import { loadWorkspaceChunk } from "../components/workspaceChunk";
import type { GeographyView } from "./routes";

const NativeRanges = lazy(() =>
  loadWorkspaceChunk(async () => ({
    default: (await import("../native-ranges/NativeRangesScreen"))
      .NativeRangesScreen,
  })),
);
const Distribution = lazy(() =>
  loadWorkspaceChunk(async () => ({
    default: (await import("../species-distribution/SpeciesDistributionScreen"))
      .SpeciesDistributionScreen,
  })),
);
const Origins = lazy(() =>
  loadWorkspaceChunk(async () => ({
    default: (await import("../provenance-map/ProvenanceMapScreen"))
      .ProvenanceMapScreen,
  })),
);
const Management = lazy(() =>
  loadWorkspaceChunk(async () => ({
    default: (await import("../geographic-places/GeographyScreen"))
      .GeographyScreen,
  })),
);
const Overview = lazy(() =>
  loadWorkspaceChunk(async () => ({
    default: (await import("./GeographyOverview")).GeographyOverview,
  })),
);

export function GeographyWorkspace({
  view,
  siteId,
  placeId,
  startCreating,
}: {
  view: GeographyView;
  siteId?: string;
  placeId?: string;
  startCreating?: boolean;
}) {
  return (
    <Suspense fallback={<p role="status">Loading geography view…</p>}>
      {view === "overview" ? (
        <Overview />
      ) : view === "native-ranges" ? (
        <NativeRanges />
      ) : view === "species-distribution" ? (
        <Distribution />
      ) : view === "origins" ? (
        <Origins />
      ) : (
        <Management
          key={siteId ?? placeId ?? "directory"}
          initialSiteId={siteId}
          initialPlaceId={placeId}
          startCreating={startCreating}
        />
      )}
    </Suspense>
  );
}
