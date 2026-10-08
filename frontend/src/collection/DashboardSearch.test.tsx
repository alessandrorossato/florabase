import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { App } from "../App";

const id = "01900000-0000-7000-8000-000000000101";
const identity = {
  id,
  scientific_name: "Acmella oleracea",
  cultivar_name: null,
  common_name: "Toothache plant",
  display_label: "Acmella oleracea",
};
const dashboard = {
  counts: {
    active_seed_lots: 2,
    active_sowings: 1,
    active_plants: 3,
    active_plant_groups: 1,
    botanical_identities: 1,
    events: 0,
  },
  recent_events: [],
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function setup(
  search: (path: string) => Response,
  overview: unknown = dashboard,
) {
  const calls: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const path =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    calls.push(path);
    if (path.endsWith("/auth/session"))
      return Promise.resolve(
        json({
          user_id: id,
          login_name: "owner",
          display_name: "Owner",
          owner: true,
        }),
      );
    if (path.endsWith("/auth/csrf"))
      return Promise.resolve(json({ csrf_token: "csrf" }));
    if (path.endsWith("/health"))
      return Promise.resolve(json({ status: "ok" }));
    if (path === "/api/v1/dashboard") return Promise.resolve(json(overview));
    if (path === "/api/v1/botanical-identities")
      return Promise.resolve(json([identity]));
    if (
      /^\/api\/v1\/(locations|suppliers|geographic-places|provenance-sites)$/.test(
        path,
      )
    )
      return Promise.resolve(json([]));
    return Promise.resolve(search(path));
  });
  return calls;
}

beforeEach(() => {
  window.history.replaceState(null, "", "#/dashboard");
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("Dashboard keeps its counts, actions, and chronological Event context", async () => {
  const event = {
    id,
    kind: "observation",
    occurred_on: { precision: "year", year: 2024 },
    created_at: "2024-06-01T00:00:00Z",
    updated_at: "2024-06-01T00:00:00Z",
    notes: "First growth",
    destination_location: null,
    destination_location_id: null,
    recipient: null,
    resulting_plant: null,
    resulting_plant_id: null,
    target: {
      id,
      type: "plant",
      label: "Acmella plant",
      lifecycle: "active",
      botanical_identity: { id, display_label: "Acmella oleracea" },
    },
  };
  setup(() => json({}), {
    ...dashboard,
    recent_events: [
      event,
      { ...event, id: `${id.slice(0, -1)}2`, notes: "Later growth" },
    ],
  });
  render(<App />);
  const snapshot = await screen.findByRole("region", {
    name: "Collection snapshot",
  });
  for (const [name, count] of [
    ["Seed lots", "2"],
    ["Sowings", "1"],
    ["Plants", "3"],
    ["Plant groups", "1"],
  ]) {
    expect(
      within(snapshot).getByRole("link", { name: `${name}: ${count}` }),
    ).toBeInTheDocument();
  }
  const actions = screen.getByRole("navigation", { name: "Quick actions" });
  expect(within(actions).getAllByRole("link")).toHaveLength(9);
  for (const [name, href] of [
    ["New seed lot", "#/seeds?action=create"],
    ["New sowing", "#/sowings?action=create"],
    ["New plant", "#/plants?action=create&kind=plant"],
    ["New plant group", "#/plants?action=create&kind=group"],
    ["Record harvest", "#/harvests?action=create"],
    ["New botanical identity", "#/identities?action=create"],
    ["New supplier", "#/suppliers?action=create"],
    ["New location", "#/locations?action=create"],
    ["New local place", "#/geography?action=create"],
  ]) {
    expect(within(actions).getByRole("link", { name })).toHaveAttribute(
      "href",
      href,
    );
  }
  const activity = screen.getByRole("region", { name: "Recent activity" });
  expect(
    within(activity).getByRole("link", { name: "Open Journal" }),
  ).toHaveAttribute("href", "#/events");
  expect(within(activity).getAllByRole("article")).toHaveLength(2);
  expect(within(activity).getAllByText("2024")).toHaveLength(2);
  expect(within(activity).getByText("First growth")).toBeInTheDocument();
  expect(within(activity).getByText("Later growth")).toBeInTheDocument();
  expect(
    within(activity).getAllByRole("link", { name: "Acmella oleracea" }),
  ).toHaveLength(2);
  expect(
    screen.getByRole("searchbox", { name: "Search your collection" }),
  ).toBeEnabled();
  expect(screen.getByRole("button", { name: "Filters" })).toBeEnabled();
});

test("Dashboard search replaces overview, groups results, and restores the normal route", async () => {
  const calls = setup((path) => {
    if (path.startsWith("/api/v1/search?"))
      return json({
        query: "acmella",
        total: 2,
        offset: 0,
        limit: 20,
        groups: [
          {
            kind: "seed_lot",
            total: 1,
            items: [
              {
                kind: "seed_lot",
                id,
                title: "Summer packet",
                context: "Acmella oleracea",
                href: `#/seeds/${id}`,
              },
            ],
          },
          {
            kind: "botanical_identity",
            total: 1,
            items: [
              {
                kind: "botanical_identity",
                id,
                title: "Acmella oleracea",
                context: "Toothache plant",
                href: `#/identities/${id}`,
              },
            ],
          },
        ],
      });
    return json({});
  });
  const user = userEvent.setup();
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: "Collection snapshot" }),
  ).toBeInTheDocument();
  const quickActions = screen.getByRole("navigation", {
    name: "Quick actions",
  });
  for (const [name, href] of [
    ["New seed lot", "#/seeds?action=create"],
    ["New sowing", "#/sowings?action=create"],
    ["New plant", "#/plants?action=create&kind=plant"],
    ["New plant group", "#/plants?action=create&kind=group"],
    ["Record harvest", "#/harvests?action=create"],
    ["New botanical identity", "#/identities?action=create"],
    ["New supplier", "#/suppliers?action=create"],
    ["New location", "#/locations?action=create"],
    ["New local place", "#/geography?action=create"],
  ]) {
    expect(within(quickActions).getByRole("link", { name })).toHaveAttribute(
      "href",
      href,
    );
    expect(within(quickActions).getByRole("link", { name })).toHaveClass(
      "button-link",
      "button--secondary",
    );
  }
  expect(screen.queryByRole("link", { name: "Browse Plants" })).toBeNull();
  await user.type(
    screen.getByRole("searchbox", { name: "Search your collection" }),
    "acmella",
  );
  expect(window.location.hash).toContain("q=acmella");
  expect(
    screen.queryByRole("heading", { name: "Collection snapshot" }),
  ).toBeNull();
  const results = screen.getByRole("region", { name: "Search results" });
  expect(
    await within(results).findByRole("link", { name: /Summer packet/ }),
  ).toHaveAttribute("href", `#/seeds/${id}`);
  expect(
    within(results).getByRole("heading", { name: "Seed lots · 1 result" }),
  ).toBeInTheDocument();
  expect(
    within(results).getByRole("heading", {
      name: "Botanical identities · 1 result",
    }),
  ).toBeInTheDocument();
  expect(
    within(
      within(results).getByRole("link", {
        name: "Botanical identity: Acmella oleracea. Toothache plant",
      }),
    ).getByText("Toothache plant"),
  ).toBeInTheDocument();
  expect(
    within(results).getByRole("region", { name: "Botany" }),
  ).toBeInTheDocument();
  expect(
    calls.filter((path) => path.startsWith("/api/v1/search?")).length,
  ).toBe(1);
  await user.click(screen.getByRole("button", { name: /Back to Dashboard/ }));
  expect(window.location.hash).toBe("#/dashboard");
  expect(
    await screen.findByRole("heading", { name: "Collection snapshot" }),
  ).toBeInTheDocument();
  window.history.back();
  await waitFor(() => {
    expect(window.location.hash).toContain("q=acmella");
  });
  expect(
    await within(
      await screen.findByRole("region", { name: "Search results" }),
    ).findByRole("link", { name: /Summer packet/ }),
  ).toBeInTheDocument();
  window.history.forward();
  await waitFor(() => {
    expect(window.location.hash).toBe("#/dashboard");
  });
  expect(
    await screen.findByRole("heading", { name: "Collection snapshot" }),
  ).toBeInTheDocument();
  window.history.replaceState(null, "", "#/dashboard?q=acmella");
  window.dispatchEvent(new PopStateEvent("popstate"));
  expect(
    await within(
      await screen.findByRole("region", { name: "Search results" }),
    ).findByRole("link", { name: /Summer packet/ }),
  ).toBeInTheDocument();
});

test("filters work without query text and active chips can be removed", async () => {
  const calls = setup((path) =>
    path.startsWith("/api/v1/search?")
      ? json({ query: "", total: 0, offset: 0, limit: 20, groups: [] })
      : json({}),
  );
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { name: "Collection snapshot" });
  await user.click(screen.getByRole("button", { name: "Filters" }));
  const panel = screen.getByRole("region", { name: "Search filters" });
  await user.click(within(panel).getByRole("checkbox", { name: "Plants" }));
  await user.selectOptions(
    within(panel).getByRole("combobox", { name: "Plants lifecycle" }),
    "active",
  );
  expect(window.location.hash).toContain("kind=plant");
  expect(window.location.hash).toContain("lifecycle=active");
  expect(
    await screen.findByText("No records match this search and its filters."),
  ).toBeInTheDocument();
  expect(calls.some((path) => path.includes("kind=plant"))).toBe(true);
  const storedHash = window.location.hash;
  cleanup();
  window.history.replaceState(null, "", storedHash);
  render(<App />);
  expect(
    await screen.findByText("No records match this search and its filters."),
  ).toBeInTheDocument();
  expect(
    calls.some(
      (path) =>
        path.includes("kind=plant") && path.includes("lifecycle=active"),
    ),
  ).toBe(true);
  await user.click(screen.getByRole("button", { name: /Remove Plants/ }));
  expect(window.location.hash).toBe("#/dashboard");
  expect(
    await screen.findByRole("heading", { name: "Collection snapshot" }),
  ).toBeInTheDocument();
});

test("search error retries, and a large group loads a bounded next page", async () => {
  let fail = true;
  const calls = setup((path) => {
    if (!path.startsWith("/api/v1/search?")) return json({});
    if (fail) {
      fail = false;
      return json({ detail: "error" }, 500);
    }
    const offset = Number(
      new URL(path, "https://florabase.test").searchParams.get("offset"),
    );
    const size = offset ? 5 : 20;
    return json({
      query: "packet",
      total: 25,
      offset,
      limit: 20,
      groups: [
        {
          kind: "seed_lot",
          total: 25,
          items: Array.from({ length: size }, (_, index) => ({
            kind: "seed_lot",
            id: `${id.slice(0, -3)}${String(offset + index).padStart(3, "0")}`,
            title: `Packet ${String(offset + index)}`,
            context: "Acmella oleracea",
            href: `#/seeds/${id}`,
          })),
        },
      ],
    });
  });
  window.history.replaceState(null, "", "#/dashboard?q=packet");
  const user = userEvent.setup();
  render(<App />);
  expect(
    await screen.findByRole("button", { name: "Retry search" }),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Retry search" }));
  expect(
    await screen.findByRole("heading", {
      name: "Seed lots · showing 20 of 25",
    }),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Show more results" }));
  expect(
    await screen.findByRole("heading", { name: "Seed lots · 25 results" }),
  ).toBeInTheDocument();
  expect(
    calls.filter((path) => path.startsWith("/api/v1/search?")).length,
  ).toBe(3);
});

test("a slower response for an old query cannot replace the current results", async () => {
  let resolveA: ((response: Response) => void) | undefined;
  let resolveB: ((response: Response) => void) | undefined;
  const calls: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const path =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    calls.push(path);
    if (path.endsWith("/auth/session"))
      return Promise.resolve(
        json({
          user_id: id,
          login_name: "owner",
          display_name: "Owner",
          owner: true,
        }),
      );
    if (path.endsWith("/auth/csrf"))
      return Promise.resolve(json({ csrf_token: "csrf" }));
    if (path.endsWith("/health"))
      return Promise.resolve(json({ status: "ok" }));
    if (path === "/api/v1/dashboard") return Promise.resolve(json(dashboard));
    if (path === "/api/v1/botanical-identities")
      return Promise.resolve(json([identity]));
    if (
      /^\/api\/v1\/(locations|suppliers|geographic-places|provenance-sites)$/.test(
        path,
      )
    )
      return Promise.resolve(json([]));
    const query = new URL(path, "https://florabase.test").searchParams.get("q");
    if (query === "a")
      return new Promise<Response>((resolve) => (resolveA = resolve));
    if (query === "ab")
      return new Promise<Response>((resolve) => (resolveB = resolve));
    return Promise.resolve(
      json({ query, total: 0, offset: 0, limit: 20, groups: [] }),
    );
  });

  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { name: "Collection snapshot" });
  const input = screen.getByRole("searchbox", {
    name: "Search your collection",
  });
  await user.type(input, "a");
  await waitFor(() => {
    expect(resolveA).toBeDefined();
  });
  await user.type(input, "b");
  await waitFor(() => {
    expect(resolveB).toBeDefined();
  });

  const result = (query: string, title: string) =>
    json({
      query,
      total: 1,
      offset: 0,
      limit: 20,
      groups: [
        {
          kind: "seed_lot",
          total: 1,
          items: [
            {
              kind: "seed_lot",
              id,
              title,
              context: "Acmella oleracea",
              href: `#/seeds/${id}`,
            },
          ],
        },
      ],
    });
  resolveB?.(result("ab", "Current result"));
  expect(
    await screen.findByRole("link", { name: /Current result/ }),
  ).toBeInTheDocument();
  resolveA?.(result("a", "Stale result"));
  await waitFor(() => {
    expect(calls.some((path) => path.includes("q=a"))).toBe(true);
  });
  expect(screen.queryByRole("link", { name: /Stale result/ })).toBeNull();
  expect(
    screen.getByRole("link", { name: /Current result/ }),
  ).toBeInTheDocument();
});

test("Harvest and Media URL kinds render compact groups and page together without images", async () => {
  window.history.replaceState(
    null,
    "",
    "#/dashboard?q=summer&kind=harvest&kind=media_asset",
  );
  const calls = setup((path) => {
    const params = new URL(path, "https://florabase.test").searchParams;
    const offset = Number(params.get("offset"));
    return json({
      query: "summer",
      total: 3,
      offset,
      limit: 1,
      groups: [
        {
          kind: "harvest",
          total: 1,
          items: offset
            ? []
            : [
                {
                  kind: "harvest",
                  id,
                  title: "Summer basket",
                  context: "Plant: North plant · 2026 · Leaves",
                  href: `#/harvests/${id}`,
                },
              ],
        },
        {
          kind: "media_asset",
          total: 2,
          items: [
            {
              kind: "media_asset",
              id: offset ? `${id.slice(0, -1)}2` : id,
              title: offset ? "Summer remote image" : "Summer local image",
              context: offset ? "External image" : "Local image",
              href: `#/media/${offset ? `${id.slice(0, -1)}2` : id}`,
            },
          ],
        },
      ],
    });
  });
  const user = userEvent.setup();
  render(<App />);
  const result = await screen.findByRole("region", { name: "Search results" });
  expect(
    await within(result).findByRole("link", { name: /Summer basket/ }),
  ).toHaveAttribute("href", `#/harvests/${id}`);
  expect(
    within(result).getByRole("link", { name: /Summer local image/ }),
  ).toHaveAttribute("href", `#/media/${id}`);
  expect(
    within(result)
      .getAllByRole("heading", { level: 4 })
      .map((h) => h.textContent),
  ).toEqual(["Collection", "Media"]);
  expect(
    within(result).getByText("Harvest · Plant: North plant · 2026 · Leaves"),
  ).toBeInTheDocument();
  expect(within(result).queryAllByRole("img")).toHaveLength(0);
  await user.click(screen.getByRole("button", { name: "Show more results" }));
  expect(
    await within(result).findByRole("link", { name: /Summer remote image/ }),
  ).toBeInTheDocument();
  expect(within(result).getAllByRole("link")).toHaveLength(3);
  expect(
    calls
      .filter((p) => p.startsWith("/api/v1/search?"))
      .every((p) => p.includes("kind=harvest&kind=media_asset")),
  ).toBe(true);
  expect(calls.some((p) => /thumbnail|\/content|https:\/\//.test(p))).toBe(
    false,
  );
});

test("Harvest kind offers occurrence year and restores mixed kinds through browser history", async () => {
  const calls = setup(() =>
    json({ query: "", total: 0, offset: 0, limit: 20, groups: [] }),
  );
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { name: "Collection snapshot" });
  await user.click(screen.getByRole("button", { name: "Filters" }));
  const panel = screen.getByRole("region", { name: "Search filters" });
  await user.click(within(panel).getByRole("checkbox", { name: "Harvests" }));
  const year = within(panel).getByRole("spinbutton", { name: "Occurred year" });
  await user.type(year, "2026");
  expect(
    within(panel).queryByRole("combobox", { name: /lifecycle/ }),
  ).toBeNull();
  expect(
    within(panel).queryByRole("combobox", { name: "Event kind" }),
  ).toBeNull();
  await waitFor(() => {
    expect(
      calls.some((p) => p.includes("kind=harvest") && p.includes("year=2026")),
    ).toBe(true);
  });
  expect(
    await screen.findByText("No records match this search and its filters."),
  ).toBeInTheDocument();
  await user.click(within(panel).getByRole("checkbox", { name: "Media" }));
  expect(window.location.hash).toContain("kind=harvest&kind=media_asset");
  expect(window.location.hash).not.toContain("year=");
  window.history.back();
  await waitFor(() => {
    expect(
      within(panel).getByRole("spinbutton", { name: "Occurred year" }),
    ).toHaveValue(2026);
    expect(
      within(panel).getByRole("checkbox", { name: "Media" }),
    ).not.toBeChecked();
  });
  expect(
    within(panel).getByRole("checkbox", { name: "Media" }),
  ).not.toBeChecked();
  window.history.forward();
  await waitFor(() => {
    expect(
      within(panel).getByRole("checkbox", { name: "Media" }),
    ).toBeChecked();
  });
  // Escape returns keyboard focus to the existing filter toggle.
  within(panel).getByRole("checkbox", { name: "Media" }).focus();
  await user.keyboard("{Escape}");
  expect(screen.getByRole("button", { name: "Filters (2)" })).toHaveFocus();
});

test("a Media search hit opens its exact asset and browser history restores search", async () => {
  window.history.replaceState(
    null,
    "",
    "#/dashboard?q=remote&kind=media_asset",
  );
  const mediaDetail = {
    id,
    kind: "external",
    title: "Remote illustration",
    attribution: "Author",
    licence_label: null,
    licence_url: null,
    image_url: "https://example.invalid/image.png",
    source_url: "https://example.invalid/source",
    original_filename: null,
    media_type: null,
    byte_size: null,
    width: null,
    height: null,
    fetched_at: null,
    local_copy_cleanup_pending: false,
    deletion_pending: false,
    content_url: null,
    thumbnail_url: null,
    collection_link_count: 0,
    cover_reference_count: 0,
    can_delete: true,
    created_at: "2026-10-06T00:00:00Z",
    updated_at: "2026-10-06T00:00:00Z",
    links: [],
    covers: [],
  };
  const calls = setup((path) =>
    path === `/api/v1/media-assets/${id}`
      ? json(mediaDetail)
      : json({
          query: "remote",
          total: 1,
          offset: 0,
          limit: 20,
          groups: [
            {
              kind: "media_asset",
              total: 1,
              items: [
                {
                  kind: "media_asset",
                  id,
                  title: "Remote illustration",
                  context: "External image",
                  href: `#/media/${id}`,
                },
              ],
            },
          ],
        }),
  );
  const user = userEvent.setup();
  const view = render(<App />);
  await user.click(
    await screen.findByRole("link", { name: /Remote illustration/ }),
  );
  expect(
    await screen.findByRole("heading", { name: "Remote illustration" }),
  ).toBeInTheDocument();
  expect(window.location.hash).toBe(`#/media/${id}`);
  expect(calls).toContain(`/api/v1/media-assets/${id}`);
  expect(calls.some((path) => path.startsWith("https://example.invalid"))).toBe(
    false,
  );
  // Remounting on the exact URL models refresh, without losing the asset selection.
  view.unmount();
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: "Remote illustration" }),
  ).toBeInTheDocument();
  window.history.back();
  expect(
    await screen.findByRole("region", { name: "Search results" }),
  ).toBeInTheDocument();
  await waitFor(() => {
    expect(
      screen.getByRole("searchbox", { name: "Search your collection" }),
    ).toHaveValue("remote");
  });
  window.history.forward();
  expect(
    await screen.findByRole("heading", { name: "Remote illustration" }),
  ).toBeInTheDocument();
});

test("Orders and Suppliers share Sourcing search with exact Order deep links", async () => {
  setup((path) => {
    if (path.startsWith("/api/v1/search?"))
      return json({
        query: "PO-1",
        total: 1,
        offset: 0,
        limit: 20,
        groups: [
          {
            kind: "order",
            total: 1,
            items: [
              {
                kind: "order",
                id,
                title: "PO-1",
                context: "2026-10 · Nursery · EUR 42.50",
                href: `#/orders/${id}`,
              },
            ],
          },
        ],
      });
    return json({});
  });
  render(<App />);
  const input = await screen.findByRole("searchbox", {
    name: "Search your collection",
  });
  await userEvent.type(input, "PO-1");
  const result = await screen.findByRole("link", { name: /PO-1/ });
  expect(result).toHaveAttribute("href", `#/orders/${id}`);
  expect(
    screen.getByRole("heading", { name: "Sourcing", level: 4 }),
  ).toBeVisible();
  expect(result).toHaveTextContent("2026-10 · Nursery · EUR 42.50");
});
