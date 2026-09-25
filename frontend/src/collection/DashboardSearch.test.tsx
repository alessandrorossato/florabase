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

function setup(search: (path: string) => Response) {
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
    ["Add seed lot", "#/seeds?action=create"],
    ["Add plant", "#/plants?action=create&kind=plant"],
    ["Add plant group", "#/plants?action=create&kind=group"],
    ["Import / Export", "#/import-export"],
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
