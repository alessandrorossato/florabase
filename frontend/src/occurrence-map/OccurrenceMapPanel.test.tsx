import { cleanup, render, screen } from "@testing-library/react";
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

const authStub = vi.hoisted(() => ({
  state: { status: "authenticated", csrfToken: "csrf" },
  sessionExpired: vi.fn(),
}));
vi.mock("../auth/context", () => ({ useAuth: () => authStub }));
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
const generation = "01900000-0000-7000-8000-000000000001";
const saved = () => ({
  summary: summary(),
  generation,
  stale: false,
  provider_error: null,
  persisted: true,
});

test("cache miss performs only a local read, then explicit Load saves a generation", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      json({ summary: null, generation: null, stale: false, persisted: true }),
    )
    .mockResolvedValueOnce(json(saved()));
  const user = userEvent.setup();
  render(<OccurrenceMapPanel identityId={identityId} link={link} />);
  await user.click(
    await screen.findByRole("button", { name: "Load GBIF occurrence map" }),
  );
  expect(
    await screen.findByLabelText(
      "Interactive GBIF occurrence-record density map",
    ),
  ).toBeVisible();
  expect(fetch.mock.calls[0][0]).toMatch(/occurrence-map\/cache$/);
  expect(fetch.mock.calls[0][1]).not.toMatchObject({ method: "POST" });
  expect(fetch.mock.calls[1][1]).toMatchObject({ method: "POST" });
  await user.click(screen.getByText("Data details", { selector: "summary" }));
  expect(screen.getByText(/excludes records GBIF flags/)).toBeVisible();
  expect(screen.getByText(/do not share one blanket licence/)).toBeVisible();
  expect(screen.getByLabelText("Occurrence density legend")).toBeVisible();
});
test("cached and stale evidence restore locally across remount without a provider request", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(() =>
      Promise.resolve(json({ ...saved(), stale: true })),
    );
  const view = render(
    <OccurrenceMapPanel identityId={identityId} link={link} />,
  );
  expect(
    await screen.findByLabelText(
      "Interactive GBIF occurrence-record density map",
    ),
  ).toBeVisible();
  expect(screen.getByText(/potentially outdated/)).toBeVisible();
  view.unmount();
  render(<OccurrenceMapPanel identityId={identityId} link={link} />);
  await screen.findByLabelText(
    "Interactive GBIF occurrence-record density map",
  );
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(fetch.mock.calls.every(([, init]) => init?.method !== "POST")).toBe(
    true,
  );
});
test("failed refresh preserves cached evidence and explicit clearing unloads it", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(json(saved()))
    .mockResolvedValueOnce(
      json({ ...saved(), provider_error: "provider_unavailable" }),
    )
    .mockResolvedValueOnce(new Response(null, { status: 204 }));
  const user = userEvent.setup();
  render(<OccurrenceMapPanel identityId={identityId} link={link} />);
  await user.click(
    await screen.findByRole("button", { name: "Refresh from GBIF" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Previously saved evidence",
  );
  expect(
    screen.getByLabelText("Interactive GBIF occurrence-record density map"),
  ).toBeVisible();
  await user.click(
    screen.getByRole("button", {
      name: "Clear local evidence for linked taxon",
    }),
  );
  expect(
    await screen.findByRole("button", { name: "Load GBIF occurrence map" }),
  ).toBeVisible();
  expect(fetch.mock.calls[2][1]).toMatchObject({ method: "DELETE" });
});
test("no link makes no read; zero records and provider failure remain distinct", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      json({ ...saved(), summary: summary({ eligible_mapped_records: 0 }) }),
    )
    .mockResolvedValueOnce(json({ summary: null }))
    .mockResolvedValueOnce(json({}, 503));
  const user = userEvent.setup();
  const view = render(
    <OccurrenceMapPanel identityId={identityId} link={null} />,
  );
  expect(fetch).not.toHaveBeenCalled();
  view.unmount();
  const zero = render(
    <OccurrenceMapPanel identityId={identityId} link={link} />,
  );
  expect(await screen.findByText("No mapped occurrence records")).toBeVisible();
  zero.unmount();
  render(<OccurrenceMapPanel identityId={identityId} link={link} />);
  await user.click(
    await screen.findByRole("button", { name: "Load GBIF occurrence map" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "temporarily unavailable",
  );
});
