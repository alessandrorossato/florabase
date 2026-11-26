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
import {
  ApiError,
  AuthRequestLockedError,
  StaleAuthEpochError,
} from "../auth/api";
import {
  AuthContext,
  type AuthContextValue,
  type AuthState,
} from "../auth/context";
import { acquireTestAuth } from "../test/auth";
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
let auth: AuthContextValue;
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
beforeEach(async () => {
  vi.resetAllMocks();
  auth = (
    await acquireTestAuth({
      session: {
        user_id: id,
        display_name: "Owner",
        canonical_origin: "http://localhost:15174",
      },
      csrfToken: "csrf",
    })
  ).auth;
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
function findMetric() {
  return screen.findByText("Represented identities", {
    exact: false,
    selector: ".distribution-overview__metric",
  });
}
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
  const metric = await findMetric();
  await waitFor(() => {
    expect(metric).toHaveTextContent("2 Represented identities");
  });
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
      auth.capability,
      expect.any(AbortSignal),
    );
  });
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
  // The species list stays inline beside the map and marks the selection.
  expect(
    screen.getByRole("button", {
      name: /Ocimum basilicum ‘Long cultivar name’/,
    }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(refreshOccurrenceEvidence).not.toHaveBeenCalled();
  expect(
    screen.getByRole("link", { name: /Botanical identity details/ }),
  ).toHaveAttribute("href", `#/identities/${id}?tab=reference`);
  await user.click(load);
  expect(await screen.findByText("Shared density map")).toBeVisible();
  expect(refreshOccurrenceEvidence).toHaveBeenCalledExactlyOnceWith(
    id,
    "csrf",
    auth.capability,
  );
  expect(screen.getByLabelText("Occurrence density legend")).toBeVisible();
  await user.click(screen.getByText("Data details", { selector: "summary" }));
  expect(screen.getByText(/Attribution: GBIF.org/)).toBeVisible();
  expect(
    screen.getByText(/PRESENT records with usable coordinates/),
  ).toBeVisible();
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
  expect(
    await screen.findByRole("button", { name: /Aloe vera/ }),
  ).toBeEnabled();
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
  await user.click(await screen.findByRole("button", { name: "Next" }));
  await waitFor(() => {
    expect(listRepresentedIdentities).toHaveBeenLastCalledWith(
      "",
      "living",
      50,
      auth.capability,
      expect.any(AbortSignal),
    );
  });
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
      auth.capability,
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
      auth.capability,
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
  const aloe = await screen.findByRole("button", { name: /Aloe vera/ });
  expect(aloe).toHaveTextContent("External taxon not linked");
  expect(aloe).toHaveAttribute("aria-pressed", "false");
  expect(window.location.hash).toContain(id);
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
  expect(
    await screen.findByText("No represented identities match these filters."),
  ).toBeVisible();
  expect(refreshOccurrenceEvidence).not.toHaveBeenCalled();
});

test("session expiry keeps loaded map and directory intact, ignores lock cancellation, and clears obsolete failedQuery on restore", async () => {
  window.history.replaceState(
    null,
    "",
    `#/species-distribution?identity=${id}`,
  );
  vi.mocked(getCachedOccurrenceEvidence).mockResolvedValue({
    summary,
    generation: id,
    stale: false,
    persisted: true,
    provider_error: null,
  });

  // 1. Trigger a genuine initial directory error first (failedQuery set), while SelectedIdentity loads map cleanly.
  vi.mocked(listRepresentedIdentities).mockRejectedValueOnce(new Error("down"));
  const sessionExpired = vi.fn();
  const makeAuth = (state: AuthState): AuthContextValue => ({
    ...auth,
    state,
    sessionExpired,
  });
  const authenticatedState = auth.state;
  const lockedState: AuthState = {
    status: "unauthenticated",
    retainedIdentity: {
      user_id: id,
      login_name: "owner",
      display_name: "Owner",
    },
    message: "Your session expired.",
  };

  const view = render(
    <AuthContext.Provider value={makeAuth(authenticatedState)}>
      <SpeciesDistributionScreen />
    </AuthContext.Provider>,
  );

  expect(await screen.findByText("Shared density map")).toBeVisible();
  expect(
    await screen.findByText(/Could not load represented identities/),
  ).toBeVisible();

  // 2. Same-owner restoration refreshes cleanly AND clears obsolete failedQuery for the unchanged queryKey.
  vi.mocked(listRepresentedIdentities).mockResolvedValue({
    items: [identity, unlinked],
    total: 2,
    occurrence_ready: 1,
    offset: 0,
    limit: 50,
  });
  view.rerender(
    <AuthContext.Provider value={makeAuth(lockedState)}>
      <SpeciesDistributionScreen />
    </AuthContext.Provider>,
  );
  view.rerender(
    <AuthContext.Provider value={makeAuth(authenticatedState)}>
      <SpeciesDistributionScreen />
    </AuthContext.Provider>,
  );
  await waitFor(() => {
    expect(
      screen.getByText("Represented identities", {
        exact: false,
        selector: ".distribution-overview__metric",
      }),
    ).toHaveTextContent("2 Represented identities");
  });
  expect(
    screen.queryByText(/Could not load represented identities/),
  ).toBeNull();
  expect(screen.getByText("Shared density map")).toBeVisible();

  // 3. Entering locked recovery suspends protected effects without unmounting the map or producing false errors.
  const listCallsBeforeLock = vi.mocked(listRepresentedIdentities).mock.calls
    .length;
  const identityCallsBeforeLock = vi.mocked(getRepresentedIdentity).mock.calls
    .length;

  view.rerender(
    <AuthContext.Provider value={makeAuth(lockedState)}>
      <SpeciesDistributionScreen />
    </AuthContext.Provider>,
  );
  await new Promise((r) => setTimeout(r, 200));

  expect(vi.mocked(listRepresentedIdentities).mock.calls.length).toBe(
    listCallsBeforeLock,
  );
  expect(vi.mocked(getRepresentedIdentity).mock.calls.length).toBe(
    identityCallsBeforeLock,
  );
  expect(screen.getByText("Shared density map")).toBeVisible();
  expect(screen.queryByRole("alert")).toBeNull();
  expect(
    screen.queryByText(/Could not load represented identities/),
  ).toBeNull();
  expect(screen.queryByText(/Could not load the selected identity/)).toBeNull();

  // 4. Local AuthRequestLockedError / StaleAuthEpochError rejections never become false error alerts or failedQuery.
  vi.mocked(listRepresentedIdentities).mockRejectedValueOnce(
    new AuthRequestLockedError(),
  );
  vi.mocked(getRepresentedIdentity).mockRejectedValueOnce(
    new StaleAuthEpochError(),
  );
  view.rerender(
    <AuthContext.Provider value={makeAuth(authenticatedState)}>
      <SpeciesDistributionScreen />
    </AuthContext.Provider>,
  );
  await waitFor(() => {
    expect(vi.mocked(getRepresentedIdentity).mock.calls.length).toBe(
      identityCallsBeforeLock + 1,
    );
  });
  await new Promise((r) => setTimeout(r, 200));
  expect(screen.queryByRole("alert")).toBeNull();
  expect(
    screen.queryByText(/Could not load represented identities/),
  ).toBeNull();
  expect(screen.queryByText(/Could not load the selected identity/)).toBeNull();
  expect(screen.getByText("Shared density map")).toBeVisible();

  // 5. Genuine network error behavior remains intact when authenticated.
  vi.mocked(listRepresentedIdentities).mockRejectedValueOnce(new Error("net"));
  fireEvent.change(screen.getByLabelText("Search species"), {
    target: { value: "salvia" },
  });
  expect(
    await screen.findByText(/Could not load represented identities/),
  ).toBeVisible();
});
