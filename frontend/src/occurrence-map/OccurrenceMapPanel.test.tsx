import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";

import type { ExternalTaxonLinkResponse } from "../botanical-identities/api";
import type { OccurrenceMapSummary } from "./api";
import { OccurrenceMapPanel } from "./OccurrenceMapPanel";

vi.mock("./OccurrenceDensityMap", () => ({
  OccurrenceDensityMap: ({ identityId }: { identityId: string }) => (
    <div aria-label="Interactive GBIF occurrence-record density map">
      Density map for {identityId}
    </div>
  ),
}));

const identityId = "01900000-0000-7000-8000-000000000099";
const link: ExternalTaxonLinkResponse = {
  provider: "gbif",
  provider_display_name: "GBIF",
  external_id: "Q2M4",
  provider_url: "https://www.gbif.org/species/Q2M4",
  scientific_name: "Calopteryx splendens",
  canonical_name: "Calopteryx splendens",
  authorship: "(Harris, 1780)",
  rank: "SPECIES",
  taxonomic_status: "ACCEPTED",
  accepted_external_id: null,
  accepted_name: null,
  kingdom: "Animalia",
  phylum: "Arthropoda",
  class_name: "Insecta",
  order_name: "Odonata",
  family: "Calopterygidae",
  genus: "Calopteryx",
  linked_at: "2026-09-12T08:00:00Z",
  last_refreshed_at: "2026-09-12T08:00:00Z",
  last_refresh_attempt_at: "2026-09-12T08:00:00Z",
  refresh_error: null,
  stale: false,
};

function summary(
  overrides: Partial<OccurrenceMapSummary> = {},
): OccurrenceMapSummary {
  return {
    source: "GBIF occurrence records",
    provider: "gbif",
    external_taxon_id: "Q2M4",
    taxon_scientific_name: "Calopteryx splendens",
    taxon_provider_url: "https://www.gbif.org/species/Q2M4",
    checklist_key: "7ddf754f-d193-4cc9-b351-99906754a03b",
    checklist_name: "Catalogue of Life eXtended Release",
    total_matching_records: 20,
    eligible_mapped_records: 17,
    retrieved_at: "2026-09-12T10:00:00Z",
    quality_policy: {
      occurrence_status: "PRESENT",
      has_coordinate: true,
      has_geospatial_issue: false,
    },
    binning: "Zoom-appropriate hexagonal occurrence-record density",
    attribution: "GBIF.org and the contributing data publishers",
    provider_url: "https://www.gbif.org",
    licensing_url: "https://www.gbif.org/terms",
    ...overrides,
  };
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("does not contact GBIF without a confirmed link or deliberate load", () => {
  const fetch = vi.spyOn(globalThis, "fetch");
  const { rerender } = render(
    <OccurrenceMapPanel identityId={identityId} link={null} />,
  );
  expect(screen.getByText(/Confirm a GBIF taxon link above/i)).toBeVisible();
  expect(fetch).not.toHaveBeenCalled();

  rerender(<OccurrenceMapPanel identityId={identityId} link={link} />);
  expect(
    screen.getByRole("button", { name: "Load GBIF occurrence map" }),
  ).toBeVisible();
  expect(fetch).not.toHaveBeenCalled();
});

test("loads exact summary and exposes accessible evidence, privacy, quality, and licensing context", async () => {
  Object.defineProperties(window, {
    innerWidth: { configurable: true, value: 390 },
    innerHeight: { configurable: true, value: 844 },
  });
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(json(summary()));
  const user = userEvent.setup();
  render(<OccurrenceMapPanel identityId={identityId} link={link} />);

  expect(
    screen.getByText("GBIF occurrence data · not native-range data"),
  ).toBeVisible();
  await user.click(
    screen.getByRole("button", { name: "Occurrence evidence and privacy" }),
  );
  expect(
    screen.getByText(/Collection records, notes, account identity/i),
  ).toBeVisible();
  await user.click(
    screen.getByRole("button", { name: "Load GBIF occurrence map" }),
  );

  expect(
    await screen.findByLabelText(
      "Interactive GBIF occurrence-record density map",
    ),
  ).toBeVisible();
  expect(screen.getByText("17")).toBeVisible();
  expect(screen.getByText("20")).toBeVisible();
  expect(screen.getByText(/excludes records GBIF flags/i)).toBeVisible();
  expect(screen.getByText(/does not mean the taxon is native/i)).toBeVisible();
  expect(screen.getByText(/not biological abundance/i)).toBeVisible();
  expect(screen.getByText(/do not share one blanket licence/i)).toBeVisible();
  expect(screen.getByLabelText("Occurrence density legend")).toBeVisible();
  expect(fetch).toHaveBeenCalledWith(
    `/api/v1/botanical-identities/${identityId}/occurrence-map/summary`,
    expect.objectContaining({ credentials: "same-origin", signal: undefined }),
  );
});

test("supports zero occurrences and external-service failure without losing context", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      json(summary({ total_matching_records: 0, eligible_mapped_records: 0 })),
    )
    .mockResolvedValueOnce(
      json({ detail: { code: "provider_unavailable" } }, 503),
    )
    .mockResolvedValueOnce(json(summary()));
  const user = userEvent.setup();
  const { rerender } = render(
    <OccurrenceMapPanel identityId={identityId} link={link} />,
  );
  await user.click(
    screen.getByRole("button", { name: "Load GBIF occurrence map" }),
  );
  expect(await screen.findByText("No mapped occurrence records")).toBeVisible();
  expect(
    screen.queryByLabelText("Interactive GBIF occurrence-record density map"),
  ).not.toBeInTheDocument();

  rerender(
    <OccurrenceMapPanel
      key="second-link"
      identityId="01900000-0000-7000-8000-000000000100"
      link={{ ...link, external_id: "BSJCX" }}
    />,
  );
  await user.click(
    screen.getByRole("button", { name: "Load GBIF occurrence map" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /botanical and collection data remain available/i,
  );
  await user.click(screen.getByRole("button", { name: "Retry" }));
  await waitFor(() => {
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

test("does not invent a negative excluded count when live GBIF counts change", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    json(summary({ total_matching_records: 17, eligible_mapped_records: 20 })),
  );
  const user = userEvent.setup();
  render(<OccurrenceMapPanel identityId={identityId} link={link} />);

  await user.click(
    screen.getByRole("button", { name: "Load GBIF occurrence map" }),
  );

  expect(
    await screen.findByText(
      /two live counts changed while GBIF processed them/i,
    ),
  ).toBeVisible();
  expect(screen.queryByText(/-3 matching records/i)).not.toBeInTheDocument();
});
