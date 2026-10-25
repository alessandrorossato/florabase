import {
  act,
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { App } from "../App";

// Route tests substitute only renderers; the real workspace, controls and state hooks stay mounted.
vi.mock("../native-ranges/NativeCoverageMap", () => ({
  NativeCoverageMap: () => <div aria-label="Native range renderer" />,
}));
vi.mock("../provenance-map/ProvenanceMap", () => ({
  ProvenanceMap: () => <div aria-label="Stored-coordinate renderer" />,
}));

function localApi() {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const path =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    let body: unknown;
    if (path.endsWith("/auth/session"))
      body = {
        user_id: "01900000-0000-7000-8000-000000000001",
        login_name: "owner",
        display_name: "Owner",
        owner: true,
        canonical_origin: "http://localhost",
      };
    else if (path.endsWith("/auth/csrf")) body = { csrf_token: "csrf" };
    else if (path.endsWith("/health")) body = { status: "ok" };
    else if (path === "/api/v1/provenance-sites/map")
      body = { sites: [], total_provenance_sites: 0, coordinate_less_sites: 0 };
    else if (path.includes("native-ranges/overview"))
      body = {
        represented: 0,
        with_range: 0,
        without_range: 0,
        places_total: 0,
        places: [],
        territories: [],
      };
    else if (
      path.includes("native-ranges/identities") ||
      path.includes("species-distribution/identities")
    )
      body = { items: [], total: 0, occurrence_ready: 0, offset: 0, limit: 50 };
    else throw new Error(`Unexpected provider or API request: ${path}`);
    return Promise.resolve(
      new Response(JSON.stringify(body), {
        headers: { "Content-Type": "application/json" },
      }),
    );
  });
}
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.history.replaceState(null, "", "#/dashboard");
});

test.each([
  [
    "#/native-ranges?q=basil&scope=current",
    "Native ranges",
    "Search species",
    "basil",
  ],
  [
    "#/geography/native-ranges?q=basil&scope=current",
    "Native ranges",
    "Search species",
    "basil",
  ],
  [
    "#/species-distribution?q=Salvia&scope=historical",
    "Species distribution",
    "Search species",
    "Salvia",
  ],
  [
    "#/geography/species-distribution?q=Salvia&scope=historical",
    "Species distribution",
    "Search species",
    "Salvia",
  ],
  [
    "#/map?q=Ocimum&plants=false",
    "Collection origins",
    "Botanical identity",
    "Ocimum",
  ],
  [
    "#/geography/origins?q=Ocimum&plants=false",
    "Collection origins",
    "Botanical identity",
    "Ocimum",
  ],
])(
  "%s mounts the full workspace under Geography with restored controls",
  async (hash, label, search, value) => {
    localApi();
    window.history.replaceState(null, "", hash);
    render(<App />);
    // Cold entry loads the Geography workspace and then the selected map chunk.
    await screen.findByRole(
      "heading",
      { name: "Geography", level: 2 },
      { timeout: 5000 },
    );
    expect(
      within(
        screen.getByRole("region", { name: "Workspace content" }),
      ).getAllByRole("heading", { level: 2 }),
    ).toHaveLength(1);
    const sidebar = screen.getByRole("navigation", {
      name: "Primary navigation",
    });
    expect(
      within(sidebar).getByRole("link", { name: "Geography" }),
    ).toHaveAttribute("aria-current", "page");
    for (const name of [
      "Maps",
      "Native ranges",
      "Species distribution",
      "Collection origins",
    ])
      expect(within(sidebar).queryByText(name)).not.toBeInTheDocument();
    const breadcrumbs = screen.getByRole("navigation", { name: "Breadcrumb" });
    expect(
      within(breadcrumbs).getByRole("link", { name: "Geography" }),
    ).toHaveAttribute("href", "#/geography/overview");
    expect(
      within(breadcrumbs)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toEqual(["Explore", "Geography", label]);
    expect(
      screen.queryByRole("navigation", { name: "Geography views" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("searchbox", { name: search })).toHaveValue(value);
    expect(screen.getByRole("button", { name: /Filters/ })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Saved views" }),
    ).toBeInTheDocument();
    if (label === "Native ranges")
      expect(
        screen.getByRole("button", { name: "Compare species (0)" }),
      ).toBeInTheDocument();
    if (label === "Species distribution")
      expect(
        screen.getByRole("button", { name: "Choose species" }),
      ).toBeInTheDocument();
  },
);

test("internal map navigation uses canonical anchors and history restores the complete legacy state", async () => {
  const fetch = localApi();
  window.history.replaceState(
    null,
    "",
    "#/map?q=basil&plants=false&future=keep",
  );
  render(<App />);
  await screen.findByRole("searchbox", { name: "Botanical identity" });
  const user = userEvent.setup();
  await user.click(
    within(screen.getByRole("navigation", { name: "Breadcrumb" })).getByRole(
      "link",
      { name: "Geography" },
    ),
  );
  await screen.findByRole("heading", { name: "Geographic overview" });
  await user.click(screen.getByRole("link", { name: "Explore native ranges" }));
  await screen.findByRole("button", { name: "Compare species (0)" });
  expect(window.location.hash).toBe("#/geography/native-ranges");
  act(() => {
    window.history.replaceState(
      null,
      "",
      "#/map?q=basil&plants=false&future=keep",
    );
    window.dispatchEvent(new PopStateEvent("popstate"));
  });
  expect(
    await screen.findByRole("searchbox", { name: "Botanical identity" }),
  ).toHaveValue("basil");
  await user.click(screen.getByRole("button", { name: /Filters/ }));
  expect(
    screen.getByRole("checkbox", { name: "Plants and plant groups" }),
  ).not.toBeChecked();
  expect(window.location.hash).toContain("future=keep");
  expect(
    fetch.mock.calls.every(
      ([input]) => typeof input === "string" && input.startsWith("/api/v1/"),
    ),
  ).toBe(true);
  await waitFor(() => {
    expect(
      screen.queryByRole("heading", { name: "Native ranges" }),
    ).not.toBeInTheDocument();
  });
});

test("same-view Collection origins query navigation restores the visible search", async () => {
  localApi();
  window.history.replaceState(null, "", "#/geography/origins?q=Ocimum");
  render(<App />);
  expect(
    await screen.findByRole("searchbox", { name: "Botanical identity" }),
  ).toHaveValue("Ocimum");
  act(() => {
    window.location.hash = "#/geography/origins?q=Salvia";
  });
  await waitFor(() => {
    expect(
      screen.getByRole("searchbox", { name: "Botanical identity" }),
    ).toHaveValue("Salvia");
  });
  act(() => {
    window.location.hash = "#/map?q=Ocimum&plants=false";
  });
  await waitFor(() => {
    expect(
      screen.getByRole("searchbox", { name: "Botanical identity" }),
    ).toHaveValue("Ocimum");
  });
});

test("Geography breadcrumb opens canonical Overview from a legacy map and history restores its view", async () => {
  localApi();
  window.history.replaceState(null, "", "#/native-ranges?q=Salvia");
  render(<App />);
  const breadcrumb = await screen.findByRole("navigation", {
    name: "Breadcrumb",
  });
  const user = userEvent.setup();
  await user.click(within(breadcrumb).getByRole("link", { name: "Geography" }));
  await screen.findByRole("heading", { name: "Geographic overview" });
  expect(window.location.hash).toBe("#/geography/overview");
  act(() => {
    window.history.replaceState(null, "", "#/native-ranges?q=Salvia");
    window.dispatchEvent(new PopStateEvent("popstate"));
  });
  expect(
    await screen.findByRole("searchbox", { name: "Search species" }),
  ).toHaveValue("Salvia");
  expect(
    screen.getByRole("navigation", { name: "Breadcrumb" }),
  ).toHaveTextContent("Native ranges");
});
