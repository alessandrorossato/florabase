import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { ApiError } from "../auth/api";
import { AuthContext, type AuthContextValue } from "../auth/context";
import {
  getCachedOccurrenceEvidence,
  refreshOccurrenceEvidence,
} from "../occurrence-map/api";
import { createSavedView, listSavedViews } from "../saved-views/api";
import { savedViewHash } from "../saved-views/state";
import {
  getRepresentedIdentity,
  listRepresentedIdentities,
  type RepresentedIdentity,
} from "./api";
import { SpeciesDistributionScreen } from "./SpeciesDistributionScreen";
vi.mock("./api", () => ({
  getRepresentedIdentity: vi.fn(),
  listRepresentedIdentities: vi.fn(),
}));
vi.mock("../occurrence-map/api", () => ({
  getCachedOccurrenceEvidence: vi.fn(),
  refreshOccurrenceEvidence: vi.fn(),
  clearOccurrenceEvidence: vi.fn(),
}));
vi.mock("../saved-views/api", () => ({
  createSavedView: vi.fn(),
  listSavedViews: vi.fn(),
  updateSavedView: vi.fn(),
  deleteSavedView: vi.fn(),
}));
vi.mock("../occurrence-map/OccurrenceDensityMap", () => ({
  OccurrenceDensityMap: () => <div>Shared density map</div>,
}));
const id = "01900000-0000-7000-8000-000000000911";
const otherId = "01900000-0000-7000-8000-000000000912";
const auth: AuthContextValue = {
  state: {
    status: "authenticated",
    csrfToken: "csrf",
    session: {
      user_id: id,
      login_name: "owner",
      display_name: "Owner",
      owner: true,
      canonical_origin: "http://localhost:15174",
    },
  },
  logIn: vi.fn(),
  logOut: vi.fn(),
  sessionExpired: vi.fn(),
  retryRestoration: vi.fn(),
  cancelLogout: vi.fn(),
};
const identity: RepresentedIdentity = {
  id,
  scientific_name: "Ocimum basilicum",
  display_label: "Ocimum basilicum ‘Long cultivar name’",
  cultivar_name: "Long cultivar name",
  common_name: "Basil",
  representation: "living",
  retained_records: 4,
  current_records: 3,
  living_records: 2,
  occurrence_eligibility: "available",
  external_taxon_id: "opaque-reviewed-id",
  matches_scope: true,
};
const unlinked: RepresentedIdentity = {
  ...identity,
  id: otherId,
  scientific_name: "Aloe vera",
  display_label: "Aloe vera",
  common_name: null,
  cultivar_name: null,
  representation: "historical",
  current_records: 0,
  living_records: 0,
  occurrence_eligibility: "not_linked",
  external_taxon_id: null,
};
const summary = {
  source: "GBIF occurrence records",
  provider: "gbif",
  external_taxon_id: "opaque-reviewed-id",
  taxon_scientific_name: "Ocimum basilicum",
  taxon_provider_url: "https://www.gbif.org",
  checklist_key: "7ddf754f-d193-4cc9-b351-99906754a03b",
  checklist_name: "Catalogue of Life eXtended Release",
  total_matching_records: 10,
  eligible_mapped_records: 8,
  retrieved_at: "2026-10-08T10:00:00Z",
  quality_policy: {
    occurrence_status: "PRESENT" as const,
    has_coordinate: true as const,
    has_geospatial_issue: false as const,
  },
  binning: "Hexagonal density",
  attribution: "GBIF.org and the contributing data publishers",
  provider_url: "https://www.gbif.org",
  licensing_url: "https://www.gbif.org/terms",
};
function show() {
  return render(
    <AuthContext.Provider value={auth}>
      <SpeciesDistributionScreen />
    </AuthContext.Provider>,
  );
}
beforeEach(() => {
  vi.resetAllMocks();
  window.history.replaceState(null, "", "#/species-distribution");
  vi.mocked(listRepresentedIdentities).mockResolvedValue({
    items: [identity, unlinked],
    total: 2,
    occurrence_ready: 1,
    offset: 0,
    limit: 50,
  });
  vi.mocked(getRepresentedIdentity).mockImplementation((selected) =>
    Promise.resolve(selected === id ? identity : unlinked),
  );
  vi.mocked(getCachedOccurrenceEvidence).mockResolvedValue({
    summary: null,
    generation: null,
    stale: false,
    persisted: true,
    provider_error: null,
  });
  vi.mocked(refreshOccurrenceEvidence).mockResolvedValue({
    summary,
    generation: id,
    stale: false,
    persisted: true,
    provider_error: null,
  });
  vi.mocked(listSavedViews).mockResolvedValue([]);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("local open, scope/search/select are provider-free; explicit Load reuses MAP-002", async () => {
  const user = userEvent.setup();
  show();
  expect(
    screen.getByRole("heading", { name: "Species distribution" }),
  ).toBeVisible();
  expect(
    screen.getByText(
      "Occurrence records show observed presence and do not establish native range.",
    ),
  ).toBeVisible();
  await screen.findByRole("button", { name: "2 Represented identities" });
  expect(refreshOccurrenceEvidence).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Filters" }));
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Collection representation" }),
    "living",
  );
  expect(
    screen.getByRole("combobox", { name: "Collection representation" }),
  ).toHaveValue("living");
  await user.click(screen.getByRole("button", { name: "Done" }));
  fireEvent.change(screen.getByLabelText("Search species"), {
    target: { value: "ocimum" },
  });
  await waitFor(() => {
    expect(listRepresentedIdentities).toHaveBeenLastCalledWith(
      "ocimum",
      "living",
      0,
      expect.any(AbortSignal),
    );
  });
  await user.click(screen.getByRole("button", { name: "Choose species" }));
  await user.click(
    await screen.findByRole("button", {
      name: /Ocimum basilicum ‘Long cultivar name’/,
    }),
  );
  const load = await screen.findByRole("button", {
    name: "Load GBIF occurrence map",
  });
  expect(window.location.hash).toBe(
    `#/species-distribution?q=ocimum&scope=living&identity=${id}`,
  );
  expect(refreshOccurrenceEvidence).not.toHaveBeenCalled();
  expect(
    screen.getByRole("link", { name: /Botanical identity details/ }),
  ).toHaveAttribute("href", `#/identities/${id}?tab=reference`);
  await user.click(load);
  expect(await screen.findByText("Shared density map")).toBeVisible();
  expect(refreshOccurrenceEvidence).toHaveBeenCalledExactlyOnceWith(id, "csrf");
  expect(screen.getByLabelText("Occurrence density legend")).toBeVisible();
  await user.click(screen.getByText("Data details", { selector: "summary" }));
  expect(screen.getByText(/Attribution: GBIF.org/)).toBeVisible();
  expect(
    screen.getByText(/PRESENT records with usable coordinates/),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Choose species" }));
  await user.click(screen.getByRole("button", { name: /Aloe vera/ }));
  expect(
    await screen.findByText(/Occurrence distribution is unavailable/),
  ).toBeVisible();
  expect(
    screen.getByRole("link", { name: "Link botanical source" }),
  ).toHaveAttribute("href", `#/identities/${otherId}?tab=source`);
  expect(screen.queryByText("Shared density map")).not.toBeInTheDocument();
  expect(refreshOccurrenceEvidence).toHaveBeenCalledTimes(1);
});

test("provider failure/retry and zero eligible records keep the directory usable", async () => {
  window.history.replaceState(
    null,
    "",
    `#/species-distribution?identity=${id}`,
  );
  vi.mocked(refreshOccurrenceEvidence)
    .mockRejectedValueOnce(new Error("provider"))
    .mockResolvedValueOnce({
      summary: { ...summary, eligible_mapped_records: 0 },
      generation: id,
      stale: false,
      persisted: true,
      provider_error: null,
    });
  const user = userEvent.setup();
  show();
  await user.click(
    await screen.findByRole("button", { name: "Load GBIF occurrence map" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "temporarily unavailable",
  );
  await user.click(screen.getByRole("button", { name: "Choose species" }));
  expect(
    await screen.findByRole("button", { name: /Aloe vera/ }),
  ).toBeEnabled();
  await user.click(screen.getByRole("button", { name: "Close" }));
  await user.click(
    screen.getByRole("button", { name: "Load GBIF occurrence map" }),
  );
  expect(await screen.findByText("No mapped occurrence records")).toBeVisible();
  expect(screen.queryByText("Shared density map")).not.toBeInTheDocument();
});

test("stale scope and missing identity remain explicit without substitution", async () => {
  window.history.replaceState(
    null,
    "",
    `#/species-distribution?scope=living&identity=${otherId}`,
  );
  vi.mocked(getRepresentedIdentity).mockResolvedValue({
    ...unlinked,
    matches_scope: false,
  });
  const user = userEvent.setup();
  show();
  expect(
    await screen.findByText(/no longer matches this collection scope/),
  ).toBeVisible();
  expect(
    screen.queryByRole("button", { name: /Load GBIF/ }),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Clear selection" }));
  expect(screen.getByText("Select a species")).toBeVisible();
  vi.mocked(getRepresentedIdentity).mockRejectedValue(new ApiError(404));
  window.history.pushState(null, "", `#/species-distribution?identity=${id}`);
  fireEvent(window, new PopStateEvent("popstate"));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "missing or no longer represented",
  );
  expect(screen.getByRole("button", { name: "Saved views" })).toBeEnabled();
  expect(window.location.hash).toContain(id);
});

test("refresh, back/forward and invalid URL defaults restore only local state", async () => {
  window.history.replaceState(
    null,
    "",
    `#/species-distribution?scope=invalid&identity=${id}`,
  );
  show();
  expect(
    await screen.findByRole("button", { name: "Load GBIF occurrence map" }),
  ).toBeVisible();
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Filters" }));
  expect(
    screen.getByRole("combobox", { name: "Collection representation" }),
  ).toHaveValue("all");
  await user.click(screen.getByRole("button", { name: "Done" }));
  expect(refreshOccurrenceEvidence).not.toHaveBeenCalled();
  window.history.pushState(
    null,
    "",
    `#/species-distribution?scope=historical&q=aloe&identity=${otherId}`,
  );
  fireEvent(window, new PopStateEvent("popstate"));
  expect(
    await screen.findByRole("heading", { name: "Aloe vera" }),
  ).toBeVisible();
  expect(screen.getByLabelText("Search species")).toHaveValue("aloe");
  window.history.replaceState(
    null,
    "",
    `#/species-distribution?scope=living&identity=${id}`,
  );
  fireEvent(window, new PopStateEvent("popstate"));
  expect(
    await screen.findByRole("button", { name: "Load GBIF occurrence map" }),
  ).toBeVisible();
  expect(refreshOccurrenceEvidence).not.toHaveBeenCalled();
});

test("Saved View create/open restores selection and cached evidence without another provider load", async () => {
  window.history.replaceState(
    null,
    "",
    `#/species-distribution?scope=living&identity=${id}`,
  );
  const saved = {
    id: otherId,
    owner_id: id,
    name: "Living basil",
    surface: "species_distribution" as const,
    state_version: 1,
    state: { scope: "living", identity: id },
    compatibility: "supported" as const,
    created_at: "2026-10-08T10:00:00Z",
    updated_at: "2026-10-08T10:00:00Z",
  };
  vi.mocked(createSavedView).mockResolvedValue(saved);
  vi.mocked(listRepresentedIdentities).mockResolvedValue({
    items: [identity],
    total: 60,
    occurrence_ready: 1,
    offset: 0,
    limit: 50,
  });
  const user = userEvent.setup();
  show();
  await user.click(
    await screen.findByRole("button", { name: "Load GBIF occurrence map" }),
  );
  await screen.findByText("Shared density map");
  await user.click(screen.getByRole("button", { name: "Choose species" }));
  await user.click(await screen.findByRole("button", { name: "Next" }));
  await waitFor(() => {
    expect(listRepresentedIdentities).toHaveBeenLastCalledWith(
      "",
      "living",
      50,
      expect.any(AbortSignal),
    );
  });
  await user.click(screen.getByRole("button", { name: "Close" }));
  await user.click(screen.getByRole("button", { name: "Saved views" }));
  await user.click(screen.getByRole("button", { name: "Save view" }));
  await user.type(screen.getByLabelText("View name"), "Living basil");
  vi.mocked(listSavedViews).mockResolvedValue([saved]);
  await user.click(
    within(screen.getByRole("dialog", { name: "Save view" })).getByRole(
      "button",
      {
        name: "Save view",
      },
    ),
  );
  await waitFor(() => {
    expect(createSavedView).toHaveBeenCalledWith(
      {
        name: "Living basil",
        surface: "species_distribution",
        state_version: 1,
        state: { scope: "living", identity: id },
      },
      "csrf",
    );
  });
  vi.mocked(getCachedOccurrenceEvidence).mockResolvedValue({
    summary,
    generation: id,
    stale: false,
    persisted: true,
    provider_error: null,
  });
  await user.click(
    await screen.findByRole("button", { name: "Open Living basil" }),
  );
  expect(await screen.findByText("Shared density map")).toBeVisible();
  expect(await screen.findByText("Locally available")).toBeVisible();
  expect(getCachedOccurrenceEvidence).toHaveBeenCalledTimes(2);
  expect(refreshOccurrenceEvidence).toHaveBeenCalledTimes(1);
  await waitFor(() => {
    expect(listRepresentedIdentities).toHaveBeenLastCalledWith(
      "",
      "living",
      0,
      expect.any(AbortSignal),
    );
  });
  expect(
    savedViewHash("species_distribution", 1, { scope: "living", identity: id }),
  ).toBe(`#/species-distribution?scope=living&identity=${id}`);
  expect(savedViewHash("species_distribution", 1, { loaded: true })).toBeNull();
});

test("chooser preview is transient and pane switching retains loaded evidence without provider reads", async () => {
  window.history.replaceState(
    null,
    "",
    `#/species-distribution?identity=${id}`,
  );
  const user = userEvent.setup();
  show();
  await user.click(
    await screen.findByRole("button", { name: "Load GBIF occurrence map" }),
  );
  const map = await screen.findByText("Shared density map");
  await user.click(screen.getByRole("button", { name: "Inspector" }));
  expect(screen.getByRole("button", { name: "Inspector" })).toHaveFocus();
  const disclosure = screen.getByText("Data details", { selector: "summary" });
  expect(
    screen.getAllByText("Data details", { selector: "summary" }),
  ).toHaveLength(1);
  await user.click(disclosure);
  expect(disclosure.parentElement).toHaveAttribute("open");
  expect(screen.getByText(/Counts and each viewed tile/)).toBeVisible();
  expect(screen.getByText("Shared density map")).toBe(map);
  await user.click(screen.getByRole("button", { name: "Map & evidence" }));
  expect(disclosure.parentElement).toHaveAttribute("open");
  expect(screen.getByText("Shared density map")).toBe(map);
  await user.click(screen.getByRole("button", { name: "Choose species" }));
  const aloe = await screen.findByRole("button", { name: /Aloe vera/ });
  await user.hover(aloe);
  expect(screen.getByLabelText("Species preview")).toHaveTextContent(
    "External taxon not linked",
  );
  expect(window.location.hash).toContain(id);
  aloe.focus();
  expect(screen.getByLabelText("Species preview")).toHaveTextContent(
    "Aloe vera",
  );
  await user.keyboard("{Escape}");
  expect(screen.getByRole("button", { name: "Choose species" })).toHaveFocus();
  expect(screen.getByText("Shared density map")).toBe(map);
  expect(refreshOccurrenceEvidence).toHaveBeenCalledTimes(1);
});

test("search resets explicit loading while retaining a selected identity excluded from results", async () => {
  window.history.replaceState(
    null,
    "",
    `#/species-distribution?identity=${id}`,
  );
  const user = userEvent.setup();
  show();
  await user.click(
    await screen.findByRole("button", { name: "Load GBIF occurrence map" }),
  );
  await screen.findByText("Shared density map");
  vi.mocked(listRepresentedIdentities).mockResolvedValue({
    items: [],
    total: 0,
    occurrence_ready: 0,
    offset: 0,
    limit: 50,
  });
  await user.type(screen.getByLabelText("Search species"), "no match");
  expect(
    await screen.findByRole("button", { name: "Load GBIF occurrence map" }),
  ).toBeVisible();
  expect(window.location.hash).toContain(id);
  expect(screen.queryByText("Shared density map")).not.toBeInTheDocument();
  expect(refreshOccurrenceEvidence).toHaveBeenCalledTimes(1);
});

test("unsupported local link and an empty directory never imply absence or request occurrences", async () => {
  window.history.replaceState(
    null,
    "",
    `#/species-distribution?identity=${id}`,
  );
  vi.mocked(getRepresentedIdentity).mockResolvedValue({
    ...identity,
    occurrence_eligibility: "incompatible",
  });
  vi.mocked(listRepresentedIdentities).mockResolvedValue({
    items: [],
    total: 0,
    occurrence_ready: 0,
    offset: 0,
    limit: 50,
  });
  const user = userEvent.setup();
  show();
  expect(
    await screen.findByRole("heading", {
      name: "External link unavailable/incompatible",
    }),
  ).toBeVisible();
  expect(
    screen.getByText(/does not mean the species has no occurrence records/),
  ).toBeVisible();
  expect(
    screen.getByRole("link", { name: "Link botanical source" }),
  ).toHaveAttribute("href", `#/identities/${id}?tab=source`);
  await user.click(screen.getByRole("button", { name: "Choose species" }));
  expect(
    await screen.findByText("No represented identities match these filters."),
  ).toBeVisible();
  expect(refreshOccurrenceEvidence).not.toHaveBeenCalled();
});

test("chooser dismissal restores the invoking readiness metric", async () => {
  const user = userEvent.setup();
  show();
  const metric = await screen.findByRole("button", {
    name: "2 Represented identities",
  });
  await user.click(metric);
  await user.keyboard("{Escape}");
  expect(metric).toHaveFocus();
  expect(refreshOccurrenceEvidence).not.toHaveBeenCalled();
});

test("backdrop dismisses without changing selection, while inner controls keep the chooser open", async () => {
  window.history.replaceState(
    null,
    "",
    `#/species-distribution?identity=${id}`,
  );
  const user = userEvent.setup();
  show();
  await user.click(
    await screen.findByRole("button", { name: "Choose species" }),
  );
  const dialog = screen.getByRole("dialog", { name: "Choose species" });
  await user.click(
    within(dialog).getByRole("heading", { name: "Choose one species" }),
  );
  expect(dialog).toBeVisible();
  fireEvent.click(dialog, { clientX: -1, clientY: -1 });
  expect(
    screen.queryByRole("dialog", { name: "Choose species" }),
  ).not.toBeInTheDocument();
  expect(window.location.hash).toContain(id);
  expect(screen.getByRole("button", { name: "Choose species" })).toHaveFocus();
  expect(refreshOccurrenceEvidence).not.toHaveBeenCalled();
});
