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
beforeEach(() => {
  vi.resetAllMocks();
  window.history.replaceState(null, "", "#/native-ranges");
  vi.mocked(loadGeometry).mockResolvedValue(geometry);
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
    screen.getByText(
      /distinct from occurrence records and from the recorded origins/,
    ),
  ).toBeVisible();
  expect(
    await screen.findByRole("img", {
      name: /Collection recorded native-range coverage map/,
    }),
  ).toBeVisible();
  expect(
    screen.getByLabelText("Native-range coverage summary"),
  ).toHaveTextContent("Without structured range1");
  expect(screen.getByText("Exact recorded places · 2")).toBeVisible();
  expect(
    screen.getByText(/One identity counts at most once per unit/),
  ).toBeVisible();
  const coverage = screen.getByText(/Territory map coverage/).parentElement;
  if (!coverage) throw new Error("Coverage list is missing");
  expect(within(coverage).getByText("3 identities")).toBeVisible();
  expect(screen.getByRole("link", { name: /Natural Earth/ })).toBeVisible();
  for (const label of ["Living", "Current", "Historical", "All represented"]) {
    await user.click(screen.getByRole("button", { name: label }));
    expect(screen.getByRole("button", { name: label })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  }
  fireEvent.change(screen.getByLabelText("Search species"), {
    target: { value: "synthetic" },
  });
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
  await user.click(
    await screen.findByRole("checkbox", { name: /Synthetic species/ }),
  );
  expect(
    screen.getByRole("button", { name: /Selected species/ }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(
    await screen.findByRole("heading", { name: identity.display_label }),
  ).toBeVisible();
  expect(screen.getByText("Recorded native range · 2 places")).toBeVisible();
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
  await user.click(screen.getByRole("button", { name: "Clear selection" }));
  expect(
    screen.getByRole("button", { name: /Selected species/ }),
  ).toHaveFocus();
});

test("represented no-range identity stays visible and has actionable selected empty state", async () => {
  const user = userEvent.setup();
  show();
  await user.click(
    await screen.findByRole("checkbox", { name: /Unranged species/ }),
  );
  expect(
    await screen.findByRole("heading", {
      name: "No structured native range recorded",
    }),
  ).toBeVisible();
  expect(
    screen.getByRole("link", { name: "Edit recorded range" }),
  ).toBeVisible();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});

test("custom/unmapped range remains authoritative without borrowing parent geometry", async () => {
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
  expect(screen.getByText(broad.display_path)).toBeVisible();
  await user.click(
    screen.getByRole("button", { name: "Retry map boundaries" }),
  );
  expect(
    await screen.findByRole("img", { name: /Collection recorded/ }),
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
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
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
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
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
  await user.click(screen.getByRole("button", { name: "Save view" }));
  await user.type(screen.getByLabelText("View name"), "Living recorded ranges");
  await user.click(
    within(screen.getByRole("dialog")).getByRole("button", {
      name: "Save view",
    }),
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
  await user.click(
    await screen.findByRole("button", { name: "Open Living recorded ranges" }),
  );
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
  await user.click(
    await screen.findByRole("checkbox", { name: /Synthetic species/ }),
  );
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
  expect(screen.getByRole("button", { name: "Current" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
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
  await user.click(
    await screen.findByRole("button", { name: "Retry represented species" }),
  );
  expect(
    await screen.findByRole("img", { name: /Collection recorded/ }),
  ).toBeVisible();
  await user.click(
    await screen.findByRole("checkbox", { name: /Synthetic species/ }),
  );
  await screen.findByRole("heading", { name: identity.display_label });
  vi.mocked(listNativeIdentities).mockRejectedValueOnce(
    new ApiError(401, "expired"),
  );
  await user.click(screen.getByRole("button", { name: "Living" }));
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
  await user.click(
    await screen.findByRole("checkbox", { name: /Synthetic species/ }),
  );
  await screen.findByRole("heading", { name: identity.display_label });
  await user.click(screen.getByRole("checkbox", { name: /Unranged species/ }));
  expect(
    await screen.findByRole("heading", { name: "Selected species comparison" }),
  ).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Selected species (2)" }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(
    screen.getByText(/Contributing species: Synthetic species/),
  ).toBeVisible();
  expect(screen.getByText(/Excluded by current filters/)).toBeVisible();
  expect(window.location.hash).toContain(`identity=${id}&identity=${other}`);
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
  await screen.findByRole("heading", { name: "Selected species comparison" });
  await user.click(
    screen.getByRole("button", { name: "Remove Unranged species" }),
  );
  expect(
    await screen.findByRole("heading", { name: identity.display_label }),
  ).toBeVisible();
  await user.click(screen.getByRole("checkbox", { name: /Synthetic species/ }));
  expect(
    screen.getByRole("button", { name: "Selected species (0)" }),
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
  const shown = show();
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
    screen.getByRole("button", { name: "Selected species (0)" }),
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
  show();
  expect(
    await screen.findByText(`Missing or no longer represented: ${other}`),
  ).toBeVisible();
  expect(getNativeComparison).toHaveBeenCalledWith(
    [id, other],
    expect.any(Object),
    expect.any(AbortSignal),
  );
  expect(
    screen.getByRole("button", { name: "Selected species (2)" }),
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
    screen.getByRole("button", { name: "Selected species (2)" }),
  ).toHaveAttribute("aria-pressed", "true");
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
