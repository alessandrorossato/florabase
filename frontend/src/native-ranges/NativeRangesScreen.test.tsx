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
import { getOccurrenceMapSummary } from "../occurrence-map/api";
import { createSavedView, listSavedViews } from "../saved-views/api";
import {
  getNativeOverview,
  getNativeComparison,
  getNativeSelection,
  listNativeIdentities,
  listTerritoryIdentities,
  type RangeIdentity,
  type RangePlace,
} from "./api";
import { loadGeometry } from "./geometry";
import geometry from "./data/world-110m.json";
import { NativeRangesScreen } from "./NativeRangesScreen";

vi.mock("./api", () => ({
  getNativeOverview: vi.fn(),
  getNativeComparison: vi.fn(),
  getNativeSelection: vi.fn(),
  listNativeIdentities: vi.fn(),
  listTerritoryIdentities: vi.fn(),
}));
vi.mock("./geometry", async (original) => ({
  ...(await original<typeof import("./geometry")>()),
  loadGeometry: vi.fn(),
}));
vi.mock("../occurrence-map/api", () => ({ getOccurrenceMapSummary: vi.fn() }));
vi.mock("../saved-views/api", () => ({
  createSavedView: vi.fn(),
  listSavedViews: vi.fn(),
  updateSavedView: vi.fn(),
  deleteSavedView: vi.fn(),
}));
const id = "01900000-0000-7000-8000-000000000911";
const other = "01900000-0000-7000-8000-000000000912";
const sessionExpired = vi.fn();
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
  sessionExpired,
  retryRestoration: vi.fn(),
  cancelLogout: vi.fn(),
};
const identity: RangeIdentity = {
  id,
  display_label: "Synthetic species ‘Long cultivar’",
  scientific_name: "Synthetic species",
  cultivar_name: "Long cultivar",
  common_name: "Example",
  representation: "living",
  retained_records: 3,
  current_records: 2,
  living_records: 1,
  matches_scope: true,
  matches_filters: true,
  native_range_count: 2,
};
const broad: RangePlace = {
  id: "broad",
  name: "South America",
  display_path: "World → Americas → South America",
  place_kind: "canonical",
  source_code_type: "un_m49",
  source_code: "005",
};
const precise: RangePlace = {
  id: "precise",
  name: "Brazil",
  display_path: "World → Americas → South America → Brazil",
  place_kind: "canonical",
  source_code_type: "iso_3166_1_alpha_2",
  source_code: "BR",
};
const territories = [
  { id: "BR", name: "Brazil", source_code: "BR", identity_count: 3 },
  { id: "AR", name: "Argentina", source_code: "AR", identity_count: 2 },
];
function show() {
  return render(
    <AuthContext.Provider value={auth}>
      <NativeRangesScreen />
    </AuthContext.Provider>,
  );
}
async function openChooser(user: ReturnType<typeof userEvent.setup>) {
  if (!screen.queryByRole("dialog", { name: "Choose represented species" }))
    await user.click(screen.getByRole("button", { name: "Choose species" }));
}
async function chooseSpecies(
  user: ReturnType<typeof userEvent.setup>,
  name: RegExp,
) {
  await openChooser(user);
  await user.click(await screen.findByRole("checkbox", { name }));
  await user.click(screen.getByRole("button", { name: "Done" }));
}
async function openFilters(user: ReturnType<typeof userEvent.setup>) {
  if (!screen.queryByRole("dialog", { name: "Native ranges filters" }))
    await user.click(screen.getByRole("button", { name: /^Filters/ }));
}
async function closeFilters(user: ReturnType<typeof userEvent.setup>) {
  await user.click(
    within(
      screen.getByRole("dialog", { name: "Native ranges filters" }),
    ).getByRole("button", { name: "Close" }),
  );
}
async function openDisclosure(
  user: ReturnType<typeof userEvent.setup>,
  name: RegExp,
) {
  if (name.source.includes("Selected species")) {
    await screen.findByRole("list", { name: "Comparison species and colors" });
    return;
  }
  if (name.source.includes("Territory map coverage")) {
    await screen.findByRole("complementary", { name: "Territory inspector" });
    return;
  }
  await user.click(
    await screen.findByRole("button", { name: /About this map/ }),
  );
  await screen.findByRole("dialog", { name: "Data and limitations" });
  await screen.findByRole("heading", { name });
}

beforeEach(() => {
  vi.resetAllMocks();
  Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
    configurable: true,
    value: vi.fn(),
  });
  window.history.replaceState(null, "", "#/native-ranges");
  vi.mocked(loadGeometry).mockResolvedValue(geometry);
  vi.mocked(listTerritoryIdentities).mockResolvedValue({
    items: [],
    total: 0,
    offset: 0,
    limit: 50,
  });
  vi.mocked(listNativeIdentities).mockResolvedValue({
    items: [
      identity,
      {
        ...identity,
        id: other,
        display_label: "Unranged species",
        native_range_count: 0,
      },
    ],
    total: 2,
    offset: 0,
    limit: 50,
  });
  vi.mocked(getNativeOverview).mockResolvedValue({
    represented: 4,
    with_range: 3,
    without_range: 1,
    territories,
    places: [
      { ...broad, identity_count: 2 },
      { ...precise, identity_count: 2 },
    ],
    places_total: 2,
    offset: 0,
    limit: 50,
  });
  vi.mocked(getNativeSelection).mockImplementation((selected) =>
    Promise.resolve({
      identity:
        selected === id
          ? identity
          : {
              ...identity,
              id: other,
              display_label: "Unranged species",
              native_range_count: 0,
            },
      ranges: selected === id ? [broad, precise] : [],
      territories:
        selected === id
          ? territories.map((v) => ({ ...v, identity_count: 1 }))
          : [],
      total: selected === id ? 2 : 0,
      offset: 0,
      limit: 50,
    }),
  );
  vi.mocked(listSavedViews).mockResolvedValue([]);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("overview exposes distinct coverage, exact places, meaning and local-only scope/search/filter", async () => {
  const user = userEvent.setup();
  show();
  expect(screen.getByRole("heading", { name: "Native ranges" })).toBeVisible();
  expect(
    screen.getByText(/distinct from occurrences and material origins/),
  ).toBeVisible();
  expect(
    await screen.findByRole("group", {
      name: /Collection recorded native-range coverage map/,
    }),
  ).toBeVisible();
  expect(
    screen.getByRole("group", { name: "Without structured range: 1" }),
  ).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Exact recorded places: 2" }),
  ).toBeVisible();
  await openDisclosure(user, /Territory map coverage/);
  const coverage = screen.getByRole("complementary", {
    name: "Territory inspector",
  });
  expect(within(coverage).getByText("3 identities")).toBeVisible();
  expect(screen.getByRole("link", { name: /Natural Earth/ })).toBeVisible();
  await openFilters(user);
  for (const value of ["living", "current", "historical", "all"]) {
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Collection representation" }),
      value,
    );
    expect(
      screen.getByRole("combobox", { name: "Collection representation" }),
    ).toHaveValue(value);
  }
  fireEvent.change(screen.getByLabelText("Search species"), {
    target: { value: "synthetic" },
  });
  await openFilters(user);
  await user.click(screen.getByLabelText("With native range only"));
  await waitFor(() => {
    expect(getNativeOverview).toHaveBeenLastCalledWith(
      { q: "synthetic", scope: "all", withRange: true, record: [] },
      0,
      expect.any(AbortSignal),
    );
  });
  expect(window.location.hash).toBe(
    "#/native-ranges?q=synthetic&withRange=true",
  );
  expect(getOccurrenceMapSummary).not.toHaveBeenCalled();
});

test("selected species preserves broad plus precise records and has existing edit/occurrence links", async () => {
  const user = userEvent.setup();
  show();
  await chooseSpecies(user, /^Synthetic species/);
  expect(
    screen.getByRole("button", { name: /Compare species/ }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(
    await screen.findByRole("heading", { name: identity.display_label }),
  ).toBeVisible();
  expect(screen.getByRole("button", { name: /About this map/ })).toBeVisible();
  await openDisclosure(user, /Recorded native range · 2 places/);
  expect(screen.getByText(/Broad recorded range/)).toBeVisible();
  expect(screen.getByText(broad.display_path)).toBeVisible();
  expect(screen.getByText(precise.display_path)).toBeVisible();
  expect(
    screen.getByRole("link", { name: "Edit recorded range" }),
  ).toHaveAttribute("href", `#/identities/${id}?tab=native-range`);
  expect(
    screen.getByRole("link", { name: "View occurrence distribution" }),
  ).toHaveAttribute("href", `#/species-distribution?identity=${id}`);
  expect(window.location.hash).toBe(
    `#/native-ranges?mode=species&identity=${id}`,
  );
  expect(getOccurrenceMapSummary).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Done" }));
  await user.click(screen.getByRole("button", { name: "Clear selection" }));
  expect(screen.getByRole("button", { name: /Compare species/ })).toHaveFocus();
});

test("represented no-range identity stays visible and has actionable selected empty state", async () => {
  const user = userEvent.setup();
  show();
  await chooseSpecies(user, /^Unranged species/);
  expect(
    await screen.findByRole("heading", {
      name: "No structured native range recorded",
    }),
  ).toBeVisible();
  expect(
    screen.getByRole("link", { name: "Edit recorded range" }),
  ).toBeVisible();
  expect(document.querySelector(".native-map svg")).not.toBeInTheDocument();
});

test("custom/unmapped range remains authoritative without borrowing parent geometry", async () => {
  const user = userEvent.setup();
  window.history.replaceState(
    null,
    "",
    `#/native-ranges?mode=species&identity=${id}`,
  );
  vi.mocked(getNativeSelection).mockResolvedValue({
    identity,
    ranges: [
      {
        ...precise,
        name: "Very long custom place",
        display_path: "World → Brazil → Very long custom place",
        place_kind: "custom",
        source_code: null,
        source_code_type: null,
      },
    ],
    territories: [],
    total: 1,
    offset: 0,
    limit: 50,
  });
  show();
  await openDisclosure(user, /Recorded native range · 1 place/);
  expect(
    await screen.findByText("Custom recorded place · Map boundary unavailable"),
  ).toBeVisible();
  expect(
    screen.getByText(/No recorded range boundaries can be shown/),
  ).toBeVisible();
  expect(
    screen.getByText("World → Brazil → Very long custom place"),
  ).toBeVisible();
});

test("geometry failure preserves recorded lists and supports retry", async () => {
  const user = userEvent.setup();
  vi.mocked(loadGeometry).mockRejectedValueOnce(new Error("offline asset"));
  show();
  expect(
    await screen.findByText(/Map boundaries could not load/),
  ).toBeVisible();
  expect(
    screen.getByRole("group", { name: "Mapped territories: —" }),
  ).toHaveTextContent("Boundaries unavailable");
  await openDisclosure(user, /Exact recorded places/);
  expect(screen.getByText(broad.display_path)).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Done" }));
  await user.click(
    screen.getByRole("button", { name: "Retry map boundaries" }),
  );
  expect(
    await screen.findByRole("group", { name: /Collection recorded/ }),
  ).toBeVisible();
});

test("empty represented or no-range collection never presents a misleading blank map", async () => {
  vi.mocked(getNativeOverview).mockResolvedValue({
    represented: 2,
    with_range: 0,
    without_range: 2,
    territories: [],
    places: [],
    places_total: 0,
    offset: 0,
    limit: 50,
  });
  const shown = show();
  expect(
    await screen.findByText(/None of these represented identities/),
  ).toBeVisible();
  expect(document.querySelector(".native-map svg")).not.toBeInTheDocument();
  shown.unmount();
  vi.mocked(getNativeOverview).mockResolvedValue({
    represented: 0,
    with_range: 0,
    without_range: 0,
    territories: [],
    places: [],
    places_total: 0,
    offset: 0,
    limit: 50,
  });
  show();
  expect(
    await screen.findByText(
      /No represented identities match this collection view/,
    ),
  ).toBeVisible();
});

test("stale selection preserves its UUID and mismatch never substitutes another species", async () => {
  window.history.replaceState(
    null,
    "",
    `#/native-ranges?mode=species&scope=historical&identity=${id}`,
  );
  vi.mocked(getNativeSelection).mockResolvedValue({
    identity: { ...identity, matches_scope: false, matches_filters: false },
    ranges: [broad],
    territories,
    total: 1,
    offset: 0,
    limit: 50,
  });
  const shown = show();
  expect(
    await screen.findByText(/no longer matches these collection filters/),
  ).toBeVisible();
  expect(document.querySelector(".native-map svg")).not.toBeInTheDocument();
  shown.unmount();
  vi.mocked(getNativeSelection).mockRejectedValue(new ApiError(404, "missing"));
  show();
  expect(
    await screen.findByText(
      /selected identity is missing or no longer represented/,
    ),
  ).toBeVisible();
  expect(screen.getByText(`Selected identity: ${id}`)).toBeVisible();
  expect(screen.getByRole("button", { name: "Clear selection" })).toBeVisible();
});

test("Saved Views persist stable state, opening same view rebuilds at page one without providers", async () => {
  const user = userEvent.setup();
  window.history.replaceState(
    null,
    "",
    `#/native-ranges?q=synthetic&scope=living&mode=species&identity=${id}&withRange=true`,
  );
  const state = {
    q: "synthetic",
    scope: "living",
    mode: "species",
    identity: [id],
    withRange: true,
  };
  const saved = {
    id: other,
    name: "Living recorded ranges",
    surface: "native_ranges" as const,
    state_version: 1,
    state,
    compatibility: "supported" as const,
    created_at: "2026-10-08T00:00:00Z",
    updated_at: "2026-10-08T00:00:00Z",
  };
  vi.mocked(createSavedView).mockResolvedValue(saved);
  vi.mocked(listSavedViews).mockResolvedValue([saved]);
  vi.mocked(listNativeIdentities).mockResolvedValue({
    items: [identity],
    total: 55,
    offset: 0,
    limit: 50,
  });
  show();
  await screen.findByRole("heading", { name: identity.display_label });
  await user.click(screen.getByRole("button", { name: "Saved views" }));
  await user.click(screen.getByRole("button", { name: "Save view" }));
  await user.type(screen.getByLabelText("View name"), "Living recorded ranges");
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
        name: "Living recorded ranges",
        surface: "native_ranges",
        state_version: 1,
        state,
      },
      "csrf",
    );
  });
  await screen.findByRole("button", { name: "Open Living recorded ranges" });
  await user.click(screen.getByRole("button", { name: "Close" }));
  await openChooser(user);
  await screen.findByRole("navigation", { name: "Represented species pages" });
  await user.click(
    within(
      screen.getByRole("navigation", { name: "Represented species pages" }),
    ).getByRole("button", { name: "Next" }),
  );
  await waitFor(() => {
    expect(listNativeIdentities).toHaveBeenLastCalledWith(
      expect.any(Object),
      50,
      expect.any(AbortSignal),
    );
  });
  await user.click(screen.getByRole("button", { name: "Done" }));
  await user.click(screen.getByRole("button", { name: "Saved views" }));
  await user.click(
    await screen.findByRole("button", { name: "Open Living recorded ranges" }),
  );
  await openChooser(user);
  await waitFor(() => {
    expect(listNativeIdentities).toHaveBeenLastCalledWith(
      { q: "synthetic", scope: "living", withRange: true, record: [] },
      0,
      expect.any(AbortSignal),
    );
  });
  expect(window.location.hash).toBe(
    `#/native-ranges?q=synthetic&scope=living&mode=species&identity=${id}&withRange=true`,
  );
  expect(getOccurrenceMapSummary).not.toHaveBeenCalled();
});

test("Back/Forward restores mode/scope and selection independent of search results", async () => {
  const user = userEvent.setup();
  show();
  await chooseSpecies(user, /^Synthetic species/);
  await openFilters(user);
  fireEvent.change(screen.getByLabelText("Search species"), {
    target: { value: "unmatched" },
  });
  await screen.findByRole("heading", { name: identity.display_label });
  window.history.replaceState(
    null,
    "",
    `#/native-ranges?scope=current&mode=species&identity=${id}`,
  );
  fireEvent.popState(window);
  await waitFor(() => {
    expect(getNativeSelection).toHaveBeenLastCalledWith(
      id,
      { q: "", scope: "current", withRange: false, record: [] },
      0,
      expect.any(AbortSignal),
    );
  });
  expect(
    screen.getByRole("combobox", { name: "Collection representation" }),
  ).toHaveValue("current");
  expect(screen.getByLabelText("Search species")).toHaveValue("");
});

test("API failures remain retryable and authentication expiry uses the session boundary", async () => {
  const user = userEvent.setup();
  vi.mocked(getNativeOverview).mockRejectedValueOnce(new Error("offline"));
  vi.mocked(listNativeIdentities).mockRejectedValueOnce(new Error("offline"));
  show();
  await user.click(
    await screen.findByRole("button", { name: "Retry collection overview" }),
  );
  await openChooser(user);
  await user.click(
    await screen.findByRole("button", { name: "Retry represented species" }),
  );
  expect(
    await screen.findByRole("group", { name: /Collection recorded/ }),
  ).toBeVisible();
  await chooseSpecies(user, /^Synthetic species/);
  await screen.findByRole("heading", { name: identity.display_label });
  vi.mocked(listNativeIdentities).mockRejectedValueOnce(
    new ApiError(401, "expired"),
  );
  await openFilters(user);
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Collection representation" }),
    "living",
  );
  await closeFilters(user);
  await openChooser(user);
  await waitFor(() => {
    expect(sessionExpired).toHaveBeenCalled();
  });
});

test("explicit multiple selection shows contributors, filter exclusions, removal, and clear", async () => {
  const user = userEvent.setup();
  vi.mocked(getNativeComparison).mockResolvedValue({
    identities: [
      identity,
      {
        ...identity,
        id: other,
        display_label: "Unranged species",
        matches_filters: false,
      },
    ],
    missing_ids: [],
    territories: [{ ...territories[0], identity_count: 1, identity_ids: [id] }],
  });
  show();
  await chooseSpecies(user, /^Synthetic species/);
  await screen.findByRole("heading", { name: identity.display_label });
  await chooseSpecies(user, /^Unranged species/);
  expect(
    await screen.findByRole("heading", { name: "Selected species comparison" }),
  ).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Compare species (2)" }),
  ).toHaveAttribute("aria-pressed", "true");
  await openDisclosure(user, /Territory map coverage/);
  await openDisclosure(user, /Selected species · 2/);
  expect(
    screen.getByRole("list", { name: "Comparison species and colors" }),
  ).toHaveTextContent(identity.display_label);
  expect(screen.getByText(/Excluded by active filters/)).toBeVisible();
  expect(window.location.hash).toContain(`identity=${id}&identity=${other}`);
  await openFilters(user);
  await user.click(screen.getByLabelText("Plants"));
  await user.click(screen.getByLabelText("Seeds"));
  await waitFor(() => {
    expect(getNativeComparison).toHaveBeenLastCalledWith(
      [id, other],
      { q: "", scope: "all", withRange: false, record: ["seed_lot", "plant"] },
      expect.any(AbortSignal),
    );
  });
  expect(window.location.hash).toContain("record=seed_lot&record=plant");
  await closeFilters(user);
  await screen.findByRole("heading", { name: "Selected species comparison" });
  await openDisclosure(user, /Selected species · 2/);
  await user.click(
    screen.getByRole("button", { name: "Remove Unranged species" }),
  );
  expect(
    await screen.findByRole("heading", { name: identity.display_label }),
  ).toBeVisible();
  await chooseSpecies(user, /^Synthetic species/);
  expect(
    screen.getByRole("button", { name: "Compare species (0)" }),
  ).toBeVisible();
  expect(
    screen.getByRole("heading", { name: "Select a species" }),
  ).toBeVisible();
});

test("20 selection limit keeps deselection available and invalid URL never truncates silently", async () => {
  const ids = Array.from(
    { length: 20 },
    (_, i) => `01900000-0000-7000-8000-${String(i).padStart(12, "0")}`,
  );
  window.history.replaceState(
    null,
    "",
    `#/native-ranges?${ids.map((value) => `identity=${value}`).join("&")}`,
  );
  vi.mocked(listNativeIdentities).mockResolvedValue({
    items: [
      { ...identity, id: ids[0] },
      { ...identity, id: other, display_label: "Extra species" },
    ],
    total: 2,
    offset: 0,
    limit: 50,
  });
  const user = userEvent.setup();
  const shown = show();
  await openChooser(user);
  expect(
    await screen.findByRole("checkbox", { name: /Extra species/ }),
  ).toBeDisabled();
  expect(
    screen.getByRole("checkbox", { name: /Synthetic species/ }),
  ).not.toBeDisabled();
  expect(screen.getByText(/Selection limit reached/)).toBeVisible();
  shown.unmount();
  window.history.replaceState(
    null,
    "",
    `#/native-ranges?identity=${id}&identity=invalid`,
  );
  show();
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Selection could not be restored",
  );
  expect(
    screen.getByRole("button", { name: "Compare species (0)" }),
  ).toBeVisible();
});

test("comparison keeps stale UUIDs explicit and restorable from repeated URL parameters", async () => {
  window.history.replaceState(
    null,
    "",
    `#/native-ranges?mode=species&identity=${other}&identity=${id}&identity=${id.toUpperCase()}`,
  );
  vi.mocked(getNativeComparison).mockResolvedValue({
    identities: [identity],
    missing_ids: [other],
    territories: [],
  });
  const user = userEvent.setup();
  show();
  await openDisclosure(user, /Selected species · 2/);
  expect(
    await screen.findByText(`Missing or no longer represented: ${other}`),
  ).toBeVisible();
  expect(getNativeComparison).toHaveBeenCalledWith(
    [id, other],
    expect.any(Object),
    expect.any(AbortSignal),
  );
  expect(
    screen.getByRole("button", { name: "Compare species (2)" }),
  ).toBeVisible();
});

test("opening a multi-species Saved View restores its exact set and category filters", async () => {
  const user = userEvent.setup();
  const state = {
    identity: [other, id],
    record: ["plant", "seed_lot"],
    mode: "species",
    scope: "current",
    withRange: true,
  };
  vi.mocked(listSavedViews).mockResolvedValue([
    {
      id: other,
      name: "Compared species",
      surface: "native_ranges",
      state_version: 1,
      state,
      compatibility: "supported",
      created_at: "2026-10-08T00:00:00Z",
      updated_at: "2026-10-08T00:00:00Z",
    },
  ]);
  vi.mocked(getNativeComparison).mockResolvedValue({
    identities: [
      identity,
      { ...identity, id: other, display_label: "Unranged species" },
    ],
    missing_ids: [],
    territories: [],
  });
  show();
  await user.click(screen.getByRole("button", { name: "Saved views" }));
  await user.click(
    await screen.findByRole("button", { name: "Open Compared species" }),
  );
  expect(
    await screen.findByRole("heading", { name: "Selected species comparison" }),
  ).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Compare species (2)" }),
  ).toHaveAttribute("aria-pressed", "true");
  await openFilters(user);
  expect(screen.getByLabelText("Plants")).toBeChecked();
  expect(screen.getByLabelText("Seeds")).toBeChecked();
  expect(getNativeComparison).toHaveBeenLastCalledWith(
    [id, other],
    { q: "", scope: "current", withRange: true, record: ["seed_lot", "plant"] },
    expect.any(AbortSignal),
  );
  window.history.replaceState(
    null,
    "",
    `#/native-ranges?mode=species&identity=${other}&identity=${id}&scope=living&record=plant`,
  );
  fireEvent.popState(window);
  await waitFor(() => {
    expect(getNativeComparison).toHaveBeenLastCalledWith(
      [id, other],
      { q: "", scope: "living", withRange: false, record: ["plant"] },
      expect.any(AbortSignal),
    );
  });
});

test("actual Back and Forward restore selection and filters without persisting territory inspection", async () => {
  const user = userEvent.setup();
  show();
  await chooseSpecies(user, /^Synthetic species/);
  await screen.findByRole("heading", { name: identity.display_label });
  const selectedHash = window.location.hash;
  await openFilters(user);
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Collection representation" }),
    "current",
  );
  await waitFor(() => {
    expect(getNativeSelection).toHaveBeenLastCalledWith(
      id,
      { q: "", scope: "current", withRange: false, record: [] },
      0,
      expect.any(AbortSignal),
    );
  });
  const filteredHash = window.location.hash;
  const map = await screen.findByRole("group", {
    name: /Recorded native-range map for selected species/,
  });
  await user.click(within(map).getByRole("button", { name: /Brazil/ }));
  expect(window.location.hash).toBe(filteredHash);
  window.history.back();
  await waitFor(() => {
    expect(window.location.hash).toBe(selectedHash);
  });
  await waitFor(() => {
    expect(
      screen.getByRole("combobox", { name: "Collection representation" }),
    ).toHaveValue("all");
  });
  expect(
    await screen.findByRole("heading", { name: identity.display_label }),
  ).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "Clear territory inspection" }),
  ).not.toBeInTheDocument();
  window.history.forward();
  await waitFor(() => {
    expect(
      screen.getByRole("combobox", { name: "Collection representation" }),
    ).toHaveValue("current");
  });
  await screen.findByRole("heading", { name: identity.display_label });
  expect(window.location.hash).toBe(filteredHash);
  expect(getOccurrenceMapSummary).not.toHaveBeenCalled();
});

test("reset filters preserves search and explicit selection while restoring unrestricted dimensions", async () => {
  const user = userEvent.setup();
  window.history.replaceState(
    null,
    "",
    `#/native-ranges?q=synthetic&scope=current&record=plant&withRange=true&mode=species&identity=${id}`,
  );
  show();
  await screen.findByRole("heading", { name: identity.display_label });
  await openFilters(user);
  await user.click(screen.getByRole("button", { name: "Reset filters" }));
  await waitFor(() => {
    expect(getNativeSelection).toHaveBeenLastCalledWith(
      id,
      { q: "synthetic", scope: "all", withRange: false, record: [] },
      0,
      expect.any(AbortSignal),
    );
  });
  expect(screen.getByLabelText("Search species")).toHaveValue("synthetic");
  expect(window.location.hash).toContain(`identity=${id}`);
  expect(window.location.hash).not.toMatch(/scope=|record=|withRange=/);
});

test("KPI drill-down reveals exact evidence or opens bounded species selection with stable focus", async () => {
  const user = userEvent.setup();
  show();
  const exact = await screen.findByRole("button", {
    name: "Exact recorded places: 2",
  });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(listNativeIdentities).not.toHaveBeenCalled();
  const before = window.location.hash;
  await user.click(exact);
  expect(
    screen.getByRole("dialog", { name: "Data and limitations" }),
  ).toBeVisible();
  expect(await screen.findByText(broad.display_path)).toBeVisible();
  expect(window.location.hash).toBe(before);
  await user.click(screen.getByRole("button", { name: "Done" }));
  expect(exact).toHaveFocus();
  await user.click(
    screen.getByRole("button", { name: "Mapped territories: 2" }),
  );
  expect(
    screen.getByRole("complementary", { name: "Territory inspector" })
      .parentElement,
  ).toHaveFocus();
  const represented = screen.getByRole("button", {
    name: "Represented identities: 4",
  });
  await user.click(represented);
  await screen.findByRole("checkbox", { name: /^Synthetic species/ });
  await user.keyboard("{Escape}");
  expect(
    screen.queryByRole("dialog", { name: "Choose represented species" }),
  ).not.toBeInTheDocument();
  expect(represented).toHaveFocus();
  await user.click(
    screen.getByRole("button", { name: "With recorded native range: 3" }),
  );
  await screen.findByRole("checkbox", { name: /^Synthetic species/ });
  expect(listNativeIdentities).toHaveBeenLastCalledWith(
    { q: "", scope: "all", withRange: true, record: [] },
    0,
    expect.any(AbortSignal),
  );
  await user.click(screen.getByRole("button", { name: "Done" }));
  await waitFor(() => {
    expect(
      screen.getByRole("button", { name: "Choose species" }),
    ).toHaveFocus();
  });
  expect(window.location.hash).toBe("#/native-ranges?withRange=true");
});

test("chooser returns focus, preserves inspection, and keeps selected IDs through search and closing", async () => {
  const user = userEvent.setup();
  show();
  const map = await screen.findByRole("group", { name: /Collection recorded/ });
  await user.click(within(map).getByRole("button", { name: /Brazil/ }));
  const trigger = screen.getByRole("button", {
    name: "Choose species",
  });
  await user.click(trigger);
  await screen.findByRole("checkbox", { name: /^Synthetic species/ });
  await user.keyboard("{Escape}");
  expect(trigger).toHaveFocus();
  expect(within(map).getByRole("button", { name: /Brazil/ })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await openChooser(user);
  await user.click(
    await screen.findByRole("checkbox", { name: /^Synthetic species/ }),
  );
  await user.type(
    screen.getByRole("searchbox", { name: "Find represented species" }),
    "cultivar",
  );
  await waitFor(() => {
    expect(listNativeIdentities).toHaveBeenLastCalledWith(
      { q: "cultivar", scope: "all", withRange: false, record: [] },
      0,
      expect.any(AbortSignal),
    );
  });
  await user.click(screen.getByRole("button", { name: "Done" }));
  await waitFor(() => {
    expect(trigger).toHaveFocus();
  });
  expect(
    screen.getByRole("button", { name: "Compare species (1)" }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(window.location.hash).toContain(`identity=${id}`);
  expect(window.location.hash).toContain("q=cultivar");
  expect(
    screen.queryByRole("checkbox", { name: /^Synthetic species/ }),
  ).not.toBeInTheDocument();
});

test("five-species comparison disables a sixth choice, preserves colors, and keeps old saved selections intact", async () => {
  const user = userEvent.setup();
  const ids = Array.from(
    { length: 6 },
    (_, index) =>
      `01900000-0000-7000-8000-${String(index + 100).padStart(12, "0")}`,
  );
  const rows = ids.map((key, index) => ({
    ...identity,
    id: key,
    display_label: `Comparison species ${String(index + 1)}`,
  }));
  window.history.replaceState(
    null,
    "",
    `#/native-ranges?mode=species&${ids
      .slice(0, 5)
      .map((key) => `identity=${key}`)
      .join("&")}`,
  );
  vi.mocked(listNativeIdentities).mockResolvedValue({
    items: rows,
    total: 6,
    offset: 0,
    limit: 50,
  });
  vi.mocked(getNativeComparison).mockImplementation((selected) =>
    Promise.resolve({
      identities: rows.filter((row) => selected.includes(row.id)),
      missing_ids: [],
      territories: [
        {
          ...territories[0],
          identity_count: selected.length,
          identity_ids: selected,
        },
      ],
    }),
  );
  const rendered = show();
  const legend = await screen.findByRole("list", {
    name: "Comparison species and colors",
  });
  expect(within(legend).getAllByRole("listitem")).toHaveLength(5);
  const colors = [
    ...legend.querySelectorAll<HTMLElement>(".native-color-key"),
  ].map((element) => element.style.background);
  expect(new Set(colors).size).toBe(5);
  await openChooser(user);
  expect(
    await screen.findByRole("checkbox", { name: /^Comparison species 6/ }),
  ).toBeDisabled();
  expect(
    screen.getByRole("checkbox", { name: /^Comparison species 1/ }),
  ).toBeEnabled();
  await user.click(screen.getByRole("button", { name: "Done" }));
  await user.click(
    screen.getByRole("button", { name: "Remove Comparison species 2" }),
  );
  const reduced = await screen.findByRole("list", {
    name: "Comparison species and colors",
  });
  await waitFor(() => {
    expect(within(reduced).getAllByRole("listitem")).toHaveLength(4);
  });
  expect(
    [...reduced.querySelectorAll<HTMLElement>(".native-color-key")].map(
      (element) => element.style.background,
    ),
  ).toEqual(colors.filter((_, index) => index !== 1));
  rendered.unmount();
  window.history.replaceState(
    null,
    "",
    `#/native-ranges?mode=species&${ids.map((key) => `identity=${key}`).join("&")}`,
  );
  show();
  expect(
    await screen.findByText(/All are preserved in count-based coverage/),
  ).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Compare species (6)" }),
  ).toBeVisible();
  expect(window.location.hash.match(/identity=/g)).toHaveLength(6);
  expect(document.querySelector("pattern")).not.toBeInTheDocument();
});

test("Explore all inspector uses full scoped collection while Compare passes only explicit IDs", async () => {
  const user = userEvent.setup();
  vi.mocked(listTerritoryIdentities).mockResolvedValue({
    items: [
      {
        ...identity,
        matching_territories: [
          {
            source_code: "BR",
            name: "Brazil",
            exact_recorded: false,
            broad_recorded_places: ["South America"],
          },
        ],
      },
    ],
    total: 1,
    offset: 0,
    limit: 50,
  });
  show();
  const map = await screen.findByRole("group", { name: /Collection recorded/ });
  await user.click(within(map).getByRole("button", { name: /Brazil/ }));
  await waitFor(() => {
    expect(listTerritoryIdentities).toHaveBeenLastCalledWith(
      { q: "", scope: "all", withRange: false, record: [] },
      ["BR"],
      "any",
      undefined,
      0,
      expect.any(AbortSignal),
    );
  });
  expect(
    await screen.findByText(
      /Brazil: drawing coverage only · broad record: South America/,
    ),
  ).toBeVisible();
  await user.click(within(map).getByRole("button", { name: /Argentina/ }));
  await waitFor(() => {
    expect(listTerritoryIdentities).toHaveBeenLastCalledWith(
      expect.any(Object),
      ["BR", "AR"],
      "any",
      undefined,
      0,
      expect.any(AbortSignal),
    );
  });
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Match territories" }),
    "all",
  );
  await waitFor(() => {
    expect(listTerritoryIdentities).toHaveBeenLastCalledWith(
      expect.any(Object),
      ["BR", "AR"],
      "all",
      undefined,
      0,
      expect.any(AbortSignal),
    );
  });
  await chooseSpecies(user, /^Synthetic species/);
  const comparison = await screen.findByRole("group", {
    name: /Recorded native-range map for selected species/,
  });
  expect(
    within(comparison).getByRole("button", { name: /Brazil/ }),
  ).toHaveAttribute("aria-pressed", "true");
  await waitFor(() => {
    expect(listTerritoryIdentities).toHaveBeenLastCalledWith(
      expect.any(Object),
      ["BR", "AR"],
      "any",
      [id],
      0,
      expect.any(AbortSignal),
    );
  });
  expect(window.location.hash).toContain(`identity=${id}`);
  expect(window.location.hash).not.toContain("territory");
});

test("inspector failures retry and expire authentication without changing comparison IDs", async () => {
  const user = userEvent.setup();
  vi.mocked(listTerritoryIdentities).mockRejectedValueOnce(
    new Error("offline"),
  );
  show();
  const map = await screen.findByRole("group", { name: /Collection recorded/ });
  await user.click(within(map).getByRole("button", { name: /Brazil/ }));
  expect(
    await screen.findByText("Could not load territory identities."),
  ).toBeVisible();
  vi.mocked(listTerritoryIdentities).mockResolvedValueOnce({
    items: [],
    total: 0,
    offset: 0,
    limit: 50,
  });
  await user.click(
    screen.getByRole("button", { name: "Retry territory identities" }),
  );
  expect(
    await screen.findByText(/No matching identities in these results/),
  ).toBeVisible();
  vi.mocked(listTerritoryIdentities).mockRejectedValueOnce(
    new ApiError(401, "expired", "Expired"),
  );
  await user.click(within(map).getByRole("button", { name: /Argentina/ }));
  await waitFor(() => {
    expect(sessionExpired).toHaveBeenCalled();
  });
});

test("paging exact recorded evidence retains the dialog and committed map territory", async () => {
  const user = userEvent.setup();
  vi.mocked(getNativeOverview).mockImplementation((_filters, offset) =>
    Promise.resolve({
      represented: 4,
      with_range: 3,
      without_range: 1,
      territories,
      places: [{ ...broad, identity_count: 2 }],
      places_total: 51,
      offset,
      limit: 50,
    }),
  );
  show();
  const map = await screen.findByRole("group", { name: /Collection recorded/ });
  await user.click(within(map).getByRole("button", { name: /Brazil/ }));
  await user.click(
    screen.getByRole("button", { name: "Exact recorded places: 51" }),
  );
  await screen.findByText(broad.display_path);
  await user.click(screen.getByRole("button", { name: "Next" }));
  await waitFor(() => {
    expect(getNativeOverview).toHaveBeenLastCalledWith(
      expect.any(Object),
      50,
      expect.any(AbortSignal),
    );
  });
  expect(await screen.findByText("Page 2")).toBeVisible();
  expect(
    screen.getByRole("dialog", { name: "Data and limitations" }),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Done" }));
  expect(within(map).getByRole("button", { name: /Brazil/ })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});
