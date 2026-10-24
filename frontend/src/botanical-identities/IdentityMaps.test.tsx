import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { IdentityMaps } from "./IdentityMaps";
import { listBotanicalNativeRanges } from "../botanical-profiles/api";
import { getExternalTaxonLink, type BotanicalIdentityResponse } from "./api";

import { getCollectionProvenanceMap } from "../provenance-map/api";
import { getCachedOccurrenceEvidence } from "../occurrence-map/api";
const auth = { sessionExpired: vi.fn() };
vi.mock("../auth/context", () => ({ useAuth: () => auth }));
vi.mock("../botanical-profiles/api", () => ({
  listBotanicalNativeRanges: vi.fn(),
}));
vi.mock("../provenance-map/api", () => ({
  getCollectionProvenanceMap: vi.fn(() => Promise.resolve({ sites: [] })),
}));
vi.mock("../occurrence-map/api", () => ({
  getCachedOccurrenceEvidence: vi.fn(),
}));
vi.mock("./api", () => ({ getExternalTaxonLink: vi.fn() }));
vi.mock("./IdentityNativeRange", () => ({
  IdentityNativeRange: () => <p>Native view mounted</p>,
}));
vi.mock("./IdentityOrigins", () => ({
  IdentityOrigins: () => <p>Origin view mounted</p>,
}));
vi.mock("./ExternalBotanicalDataPanel", () => ({
  ExternalBotanicalDataPanel: () => <p>Occurrence view mounted</p>,
}));
const identity = {
  id: "identity",
  scientific_name: "Salvia officinalis",
} as BotanicalIdentityResponse;
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
test("Maps reads local availability but mounts only the explicitly selected evidence type", async () => {
  vi.mocked(listBotanicalNativeRanges).mockResolvedValue([]);
  vi.mocked(getExternalTaxonLink).mockResolvedValue(null);
  const edit = vi.fn();
  const user = userEvent.setup();
  render(
    <IdentityMaps identity={identity} csrfToken="csrf" onEditRange={edit} />,
  );
  expect(
    await screen.findByText("0 structured entries recorded"),
  ).toBeVisible();
  expect(screen.getByText("No confirmed GBIF reference")).toBeVisible();
  expect(screen.queryByText(/view mounted/)).toBeNull();
  expect(
    screen.getByText("0 mapped sites · 0 direct record links"),
  ).toBeVisible();
  expect(getCachedOccurrenceEvidence).not.toHaveBeenCalled();
  expect(
    screen.getByRole("link", { name: "Open native ranges for this identity" }),
  ).toHaveAttribute("href", "#/native-ranges?mode=species&identity=identity");
  expect(
    screen.getByRole("link", {
      name: "Open occurrence evidence for this identity",
    }),
  ).toHaveAttribute("href", "#/species-distribution?identity=identity");
  expect(
    screen.getByRole("link", {
      name: "Open collection origins · all identities",
    }),
  ).toHaveAttribute("href", "#/map");
  await user.click(
    screen.getByRole("button", { name: "Inspect native range" }),
  );
  expect(await screen.findByText("Native view mounted")).toBeVisible();
  const inspection = screen.getByRole("region", {
    name: "Native range inspection",
  });
  await waitFor(() => {
    expect(
      within(inspection).getByRole("heading", { name: "Native range" }),
    ).toHaveFocus();
  });
  await user.click(screen.getByRole("button", { name: "Close inspection" }));
  expect(
    screen.getByRole("button", { name: "Inspect native range" }),
  ).toHaveFocus();
  expect(screen.queryByText("Native view mounted")).toBeNull();
  await user.click(
    screen.getByRole("button", { name: "Inspect occurrence evidence" }),
  );
  expect(await screen.findByText("Occurrence view mounted")).toBeVisible();
  expect(screen.queryByText("Native view mounted")).toBeNull();
  await user.click(
    screen.getByRole("button", { name: "Inspect collection origins" }),
  );
  expect(await screen.findByText("Origin view mounted")).toBeVisible();
  expect(screen.queryByText("Occurrence view mounted")).toBeNull();
  await user.click(
    screen.getByRole("button", { name: "Close collection origins" }),
  );
  expect(screen.queryByText(/view mounted/)).toBeNull();
  await user.click(screen.getByRole("button", { name: "Edit native range" }));
  expect(edit).toHaveBeenCalledOnce();
});
test("unknown availability remains an error and can be retried without falsely reporting absence", async () => {
  vi.mocked(listBotanicalNativeRanges).mockRejectedValue(new Error("offline"));
  vi.mocked(getExternalTaxonLink).mockResolvedValue(null);
  const user = userEvent.setup();
  render(
    <IdentityMaps identity={identity} csrfToken="csrf" onEditRange={vi.fn()} />,
  );
  expect(await screen.findByRole("alert")).toHaveTextContent("unavailable");
  expect(screen.queryByText("0 structured entries recorded")).toBeNull();
  vi.mocked(listBotanicalNativeRanges).mockResolvedValue([]);
  await user.click(
    screen.getByRole("button", { name: "Retry geographic summary" }),
  );
  expect(
    await screen.findByText("0 structured entries recorded"),
  ).toBeVisible();
  expect(screen.queryByRole("alert")).toBeNull();
});

test("summary uses only saved occurrence evidence and exact direct provenance membership", async () => {
  vi.mocked(listBotanicalNativeRanges).mockResolvedValue([]);
  vi.mocked(getExternalTaxonLink).mockResolvedValue({
    provider_display_name: "GBIF",
    scientific_name: "Salvia officinalis",
    stale: false,
  } as never);
  vi.mocked(getCachedOccurrenceEvidence).mockResolvedValue({
    stale: true,
    summary: { eligible_mapped_records: 123 },
  } as never);
  vi.mocked(getCollectionProvenanceMap).mockResolvedValue({
    sites: [
      {
        id: "site",
        records: [
          { botanical_identity: { id: "identity" }, record_type: "plant" },
          { botanical_identity: { id: "unrelated" }, record_type: "seed_lot" },
        ],
      },
    ],
  } as never);
  render(
    <IdentityMaps identity={identity} csrfToken="csrf" onEditRange={vi.fn()} />,
  );
  expect(
    await screen.findByText(
      "123 eligible mapped observations · cache needs review",
    ),
  ).toBeVisible();
  expect(
    screen.getByText("1 mapped site · 1 direct record links"),
  ).toBeVisible();
  expect(getCachedOccurrenceEvidence).toHaveBeenCalledWith(
    "identity",
    expect.any(AbortSignal),
  );
  expect(screen.queryByText(/view mounted/)).toBeNull();
});
