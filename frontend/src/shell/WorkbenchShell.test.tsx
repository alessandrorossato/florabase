import { readFileSync } from "node:fs";

import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";

import { WorkbenchShell } from "./WorkbenchShell";
import { allDestinations, workspaces } from "./navigation";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.removeItem("florabase.workbench.panel-collapsed.v1");
});

function searchResponse(q: string) {
  return {
    query: q,
    total: 2,
    offset: 0,
    limit: 5,
    groups: [
      {
        kind: "seed_lot",
        total: 1,
        items: [
          {
            kind: "seed_lot",
            id: "0190d2a8-0000-7000-8000-000000000001",
            title: "Basil counted packet",
            context: "Ocimum basilicum",
            href: "#/seeds/0190d2a8-0000-7000-8000-000000000001",
          },
        ],
      },
      {
        kind: "plant",
        total: 1,
        items: [
          {
            kind: "plant",
            id: "0190d2a8-0000-7000-8000-000000000002",
            title: "Basil mother plant",
            context: "Ocimum basilicum",
            href: "#/plants/0190d2a8-0000-7000-8000-000000000002",
          },
        ],
      },
    ],
  };
}

function renderShell(
  overrides: Partial<Parameters<typeof WorkbenchShell>[0]> = {},
) {
  const onNavigate = vi.fn();
  const onSignOut = vi.fn();
  const view = render(
    <WorkbenchShell
      section="dashboard"
      hash="#/dashboard"
      signedInAs="Test Owner"
      signingOut={false}
      onSignOut={onSignOut}
      onNavigate={onNavigate}
      {...overrides}
    >
      <section aria-label="Workspace content" className="app-content">
        <button type="button">Page action</button>
      </section>
    </WorkbenchShell>,
  );
  return { ...view, onNavigate, onSignOut };
}

test("the navigation model lists every former destination and Settings tool exactly once", () => {
  const sections = workspaces.flatMap((workspace) =>
    workspace.destinations.map((item) => item.section),
  );
  expect(new Set(sections).size).toBe(sections.length);
  expect([...sections].sort()).toEqual(
    [
      "dashboard",
      "seeds",
      "sowings",
      "cuttings",
      "plants",
      "harvests",
      "locations",
      "events",
      "history",
      "schedule",
      "identities",
      "taxonomy",
      "media",
      "geography",
      "suppliers",
      "orders",
      "settings",
      "labels",
      "import-export",
    ].sort(),
  );
  const hrefs = allDestinations().map((item) => item.href);
  for (const href of [
    "#/plants?type=group",
    "#/harvests?tab=stored-material",
    "#/schedule?view=calendar",
    "#/map",
    "#/species-distribution",
    "#/native-ranges",
  ])
    expect(hrefs).toContain(href);
});

test("section links navigate through the guard; modified clicks keep native behaviour", async () => {
  const user = userEvent.setup();
  const { onNavigate } = renderShell({ section: "seeds", hash: "#/seeds" });
  const nav = screen.getByRole("navigation", { name: "Primary navigation" });
  expect(within(nav).getByRole("link", { name: "Seeds" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  await user.click(within(nav).getByRole("link", { name: "Plant groups" }));
  expect(onNavigate).toHaveBeenCalledWith("#/plants?type=group");
  onNavigate.mockClear();
  await user.keyboard("{Control>}");
  await user.click(within(nav).getByRole("link", { name: "Sowings" }));
  await user.keyboard("{/Control}");
  expect(onNavigate).not.toHaveBeenCalled();
});

test("sub-destinations, not their parent, are current on their own view", () => {
  renderShell({ section: "plants", hash: "#/plants?type=group" });
  const nav = screen.getByRole("navigation", { name: "Primary navigation" });
  expect(
    within(nav).getByRole("link", { name: "Plant groups" }),
  ).toHaveAttribute("aria-current", "page");
  expect(within(nav).getByRole("link", { name: "Plants" })).not.toHaveAttribute(
    "aria-current",
  );
});

test("the New menu lists every creation route", async () => {
  const user = userEvent.setup();
  const { onNavigate } = renderShell();
  await user.click(screen.getByRole("button", { name: "New record" }));
  const create = screen.getByRole("navigation", { name: "Create" });
  expect(within(create).getAllByRole("link")).toHaveLength(9);
  await user.click(within(create).getByRole("link", { name: "New sowing" }));
  expect(onNavigate).toHaveBeenCalledWith("#/sowings?action=create");
});

test("Ctrl+K opens the palette; sections and actions need no network", async () => {
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  const user = userEvent.setup();
  const { onNavigate } = renderShell();
  screen.getByRole("button", { name: "Page action" }).focus();
  await user.keyboard("{Control>}k{/Control}");
  const dialog = screen.getByRole("dialog", { name: "Search and commands" });
  const input = within(dialog).getByRole("combobox", {
    name: "Search records, sections and actions",
  });
  expect(input).toHaveFocus();
  expect(within(dialog).getByRole("option", { name: /Orders/ })).toBeVisible();
  expect(
    within(dialog).getByRole("option", { name: /New seed lot/ }),
  ).toBeVisible();
  expect(dialog).toHaveTextContent(
    "Jump to any section or start a new record.",
  );
  await user.type(input, "ord");
  const first = within(dialog).getAllByRole("option")[0];
  expect(input).toHaveAttribute("aria-activedescendant", first.id);
  await user.keyboard("{Enter}");
  expect(onNavigate).toHaveBeenCalledWith("#/orders");
  expect(
    screen.queryByRole("dialog", { name: "Search and commands" }),
  ).not.toBeInTheDocument();
  await waitFor(() => {
    expect(screen.getByRole("button", { name: "Page action" })).toHaveFocus();
  });
});

test("palette record search shows loading, results, keyboard choice and full search", async () => {
  const fetch = vi.fn((path: string) =>
    Promise.resolve(
      new Response(
        JSON.stringify(
          searchResponse(
            new URL(path, "http://test").searchParams.get("q") ?? "",
          ),
        ),
        { headers: { "Content-Type": "application/json" } },
      ),
    ),
  );
  vi.stubGlobal("fetch", fetch);
  const user = userEvent.setup();
  const { onNavigate } = renderShell();
  await user.click(screen.getByRole("button", { name: "Search" }));
  const dialog = screen.getByRole("dialog", { name: "Search and commands" });
  await user.type(within(dialog).getByRole("combobox"), "basil");
  expect(within(dialog).getByRole("status")).toHaveTextContent(
    "Searching records…",
  );
  expect(
    await within(dialog).findByRole("option", { name: /Basil counted packet/ }),
  ).toHaveTextContent("Seed lot · Ocimum basilicum");
  expect(within(dialog).getByRole("status")).toHaveTextContent(
    "2 matching records.",
  );
  expect(fetch).toHaveBeenCalledWith(
    "/api/v1/search?q=basil&limit=5",
    expect.objectContaining({ credentials: "same-origin" }),
  );
  await user.keyboard("{ArrowDown}");
  const options = within(dialog).getAllByRole("option");
  expect(options[1]).toHaveAttribute("aria-selected", "true");
  expect(
    within(dialog).getByRole("option", { name: /All results for “basil”/ }),
  ).toBeInTheDocument();
  await user.keyboard("{Enter}");
  expect(onNavigate).toHaveBeenCalledWith(
    "#/plants/0190d2a8-0000-7000-8000-000000000002",
  );
});

test("palette search failure keeps sections and actions usable", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.resolve(new Response("{}", { status: 500 }))),
  );
  const user = userEvent.setup();
  renderShell();
  await user.keyboard("/");
  const dialog = screen.getByRole("dialog", { name: "Search and commands" });
  await user.type(within(dialog).getByRole("combobox"), "seed");
  expect(
    await within(dialog).findByText(
      "Record search is unavailable right now. Sections and actions still work.",
    ),
  ).toBeInTheDocument();
  expect(within(dialog).getByRole("option", { name: /Seeds/ })).toBeVisible();
  await user.keyboard("{Escape}");
  expect(
    screen.queryByRole("dialog", { name: "Search and commands" }),
  ).not.toBeInTheDocument();
});

test("slash does not open the palette while typing in a field", async () => {
  const user = userEvent.setup();
  render(
    <WorkbenchShell
      section="dashboard"
      hash="#/dashboard"
      signedInAs="Test Owner"
      signingOut={false}
      onSignOut={vi.fn()}
      onNavigate={vi.fn()}
    >
      <section aria-label="Workspace content">
        <label>
          Notes <input />
        </label>
      </section>
    </WorkbenchShell>,
  );
  await user.click(screen.getByLabelText("Notes"));
  await user.keyboard("a/b");
  expect(screen.getByLabelText("Notes")).toHaveValue("a/b");
  expect(
    screen.queryByRole("dialog", { name: "Search and commands" }),
  ).not.toBeInTheDocument();
});

test("mobile workspace and account sheets navigate, theme and sign out", async () => {
  const user = userEvent.setup();
  const { onNavigate, onSignOut } = renderShell({
    section: "orders",
    hash: "#/orders",
  });
  const mobile = screen.getByRole("navigation", {
    name: "Mobile primary navigation",
  });
  expect(
    within(mobile).getByRole("button", { name: "Sourcing" }),
  ).toHaveAttribute("aria-current", "true");
  await user.click(within(mobile).getByRole("button", { name: "Collection" }));
  const sheet = screen.getByRole("dialog", { name: "Collection" });
  await user.click(
    within(sheet).getByRole("link", { name: "Stored material" }),
  );
  expect(onNavigate).toHaveBeenCalledWith("#/harvests?tab=stored-material");
  expect(screen.queryByRole("dialog", { name: "Collection" })).toBeNull();

  await user.click(
    screen.getByRole("button", { name: "Account and settings" }),
  );
  const account = screen.getByRole("dialog", { name: "Account and settings" });
  expect(account).toHaveTextContent("Signed in as Test Owner");
  expect(
    within(account).getByRole("button", { name: /Appearance:/ }),
  ).toBeInTheDocument();
  await user.click(within(account).getByRole("button", { name: "Sign out" }));
  expect(onSignOut).toHaveBeenCalledTimes(1);
  await user.click(
    within(account).getByRole("link", { name: "Import / Export" }),
  );
  expect(onNavigate).toHaveBeenCalledWith("#/import-export");
});

test("signing out disables the panel action with a visible busy label", () => {
  renderShell({ signingOut: true });
  expect(screen.getByRole("button", { name: "Signing out…" })).toBeDisabled();
});

function savedViewsFetch(views: unknown[]) {
  return vi.fn((path: string) =>
    Promise.resolve(
      new Response(
        JSON.stringify(path.startsWith("/api/v1/saved-views") ? views : []),
        { headers: { "Content-Type": "application/json" } },
      ),
    ),
  );
}
const view = (
  id: string,
  name: string,
  surface: string,
  state: object,
  compatibility = "supported",
) => ({
  id,
  name,
  surface,
  state,
  state_version: 1,
  compatibility,
  created_at: "2026-11-01T00:00:00Z",
  updated_at: "2026-11-01T00:00:00Z",
});

test("supported Saved Views open as their ordinary directory URLs in the owning workspace, Today and the palette", async () => {
  const fetch = savedViewsFetch([
    view("0190d2a8-0000-7000-8000-00000000000a", "Basil lots", "seed_lots", {
      q: "basil",
    }),
    view(
      "0190d2a8-0000-7000-8000-00000000000b",
      "Broken",
      "plants",
      { q: "x" },
      "invalid_state",
    ),
  ]);
  vi.stubGlobal("fetch", fetch);
  const user = userEvent.setup();
  const { onNavigate } = renderShell({ section: "seeds", hash: "#/seeds" });
  const saved = await screen.findByRole("navigation", { name: "Saved views" });
  expect(
    within(saved).getByRole("link", { name: /Basil lots/ }),
  ).toHaveAttribute("href", "#/seeds?q=basil");
  expect(within(saved).queryByText("Broken")).toBeNull();
  await user.click(within(saved).getByRole("link", { name: /Basil lots/ }));
  expect(onNavigate).toHaveBeenCalledWith("#/seeds?q=basil");
  await user.click(screen.getByRole("tab", { name: /^Sourcing/ }));
  expect(screen.queryByRole("navigation", { name: "Saved views" })).toBeNull();
  await user.click(screen.getByRole("tab", { name: /^Today/ }));
  expect(
    within(screen.getByRole("navigation", { name: "Saved views" })).getByRole(
      "link",
      { name: /Basil lots/ },
    ),
  ).toBeInTheDocument();
  await user.keyboard("{Control>}k{/Control}");
  expect(
    within(
      screen.getByRole("dialog", { name: "Search and commands" }),
    ).getByRole("option", { name: /Basil lots/ }),
  ).toHaveTextContent("Saved view · Seed lots");
  expect(fetch).toHaveBeenCalledTimes(1);
  await user.keyboard("{Escape}");
  window.dispatchEvent(new Event("florabase:saved-views-changed"));
  await waitFor(() => {
    expect(fetch).toHaveBeenCalledTimes(2);
  });
});

test("Saved View listing failure leaves the panel usable without the group", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.resolve(new Response("{}", { status: 500 }))),
  );
  renderShell({ section: "seeds", hash: "#/seeds" });
  expect(
    screen.getByRole("navigation", { name: "Primary navigation" }),
  ).toBeInTheDocument();
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(screen.queryByRole("navigation", { name: "Saved views" })).toBeNull();
});

test("Recent lists previously opened sections, not records or the current page", () => {
  vi.stubGlobal("fetch", savedViewsFetch([]));
  const props = {
    signedInAs: "Test Owner",
    signingOut: false,
    onSignOut: vi.fn(),
    onNavigate: vi.fn(),
  };
  const content = <section aria-label="Workspace content" />;
  const { rerender } = render(
    <WorkbenchShell section="seeds" hash="#/seeds" {...props}>
      {content}
    </WorkbenchShell>,
  );
  rerender(
    <WorkbenchShell
      section="plants"
      hash="#/plants/0190d2a8-0000-7000-8000-000000000001"
      {...props}
    >
      {content}
    </WorkbenchShell>,
  );
  rerender(
    <WorkbenchShell section="orders" hash="#/orders" {...props}>
      {content}
    </WorkbenchShell>,
  );
  const recent = screen.getByRole("navigation", { name: "Recent" });
  expect(
    within(recent)
      .getAllByRole("link")
      .map((link) => link.getAttribute("href")),
  ).toEqual(["#/seeds"]);
});

test("many Saved Views stay reachable: five shown, the rest behind a disclosure and in the palette", async () => {
  const views = Array.from({ length: 12 }, (_, index) =>
    view(
      `0190d2a8-0000-7000-8000-0000000001${String(index).padStart(2, "0")}`,
      `Lots view ${String(index + 1)}`,
      "seed_lots",
      { q: `q${String(index)}` },
    ),
  );
  vi.stubGlobal("fetch", savedViewsFetch(views));
  const user = userEvent.setup();
  renderShell({ section: "seeds", hash: "#/seeds" });
  const saved = await screen.findByRole("navigation", { name: "Saved views" });
  expect(within(saved).getAllByRole("link")).toHaveLength(5);
  const more = within(saved).getByRole("button", {
    name: "Show all 12 saved views",
  });
  expect(more).toHaveAttribute("aria-expanded", "false");
  await user.click(more);
  expect(within(saved).getAllByRole("link")).toHaveLength(12);
  expect(more).toHaveAttribute("aria-expanded", "true");
  await user.click(within(saved).getByRole("button", { name: "Show fewer" }));
  expect(within(saved).getAllByRole("link")).toHaveLength(5);
  await user.keyboard("{Control>}k{/Control}");
  await user.keyboard("view 12");
  expect(
    screen.getByRole("option", { name: /Lots view 12/ }),
  ).toBeInTheDocument();
});

test("collapsing the active workspace removes the panel from layout and focus, and reopening restores it", async () => {
  vi.stubGlobal("fetch", savedViewsFetch([]));
  // Load the real shell stylesheet so the cascade, not a class name, is under test (M8 P1:
  // a same-specificity base rule after the collapsed rule kept the panel displayed). jsdom
  // ignores media conditions, so only the unconditional (desktop) rules are loaded; the phone
  // strip is covered by browser captures.
  const style = document.createElement("style");
  style.textContent = withoutMediaBlocks(
    readFileSync("src/shell/workbench.css", "utf8"),
  );
  document.head.append(style);
  try {
    const user = userEvent.setup();
    renderShell({ section: "seeds", hash: "#/seeds" });
    const tab = screen.getByRole("tab", { name: /Collection/ });
    const panel = screen.getByRole("tabpanel", { hidden: true });
    expect(panel).toHaveAttribute("id", "wb-panel");
    expect(getComputedStyle(panel).display).toBe("flex");
    expect(tab).toHaveAttribute("aria-selected", "true");

    await user.click(tab);
    expect(getComputedStyle(panel).display).toBe("none");
    expect(tab).toHaveAttribute("aria-selected", "false");
    expect(localStorage.getItem("florabase.workbench.panel-collapsed.v1")).toBe(
      "true",
    );

    await user.click(tab);
    expect(getComputedStyle(panel).display).toBe("flex");
    expect(tab).toHaveAttribute("aria-selected", "true");
    expect(tab).toHaveFocus();
    expect(within(panel).getByRole("link", { name: "Seeds" })).toBeVisible();
  } finally {
    style.remove();
  }
});

function withoutMediaBlocks(css: string) {
  let out = "";
  let index = 0;
  while (index < css.length) {
    const start = css.indexOf("@media", index);
    if (start === -1) return out + css.slice(index);
    out += css.slice(index, start);
    let depth = 0;
    let cursor = css.indexOf("{", start);
    for (; cursor < css.length; cursor += 1) {
      if (css[cursor] === "{") depth += 1;
      if (css[cursor] === "}") depth -= 1;
      if (depth === 0) break;
    }
    index = cursor + 1;
  }
  return out;
}

test("record pages start with the panel collapsed; the rail opens it there without changing the saved preference", async () => {
  vi.stubGlobal("fetch", savedViewsFetch([]));
  const user = userEvent.setup();
  const record = "#/plants/0190d2a8-0000-7000-8000-000000000002";
  const { container, rerender } = renderShell({
    section: "plants",
    hash: record,
  });
  const shell = container.querySelector(".wb-shell");
  expect(shell).toHaveClass("wb-shell--collapsed");
  const tab = screen.getByRole("tab", { name: /Collection/ });
  expect(tab).toHaveAttribute("aria-selected", "false");

  await user.click(tab);
  expect(shell).not.toHaveClass("wb-shell--collapsed");
  expect(tab).toHaveAttribute("aria-selected", "true");
  expect(localStorage.getItem("florabase.workbench.panel-collapsed.v1")).toBe(
    "false",
  );

  const props = {
    signedInAs: "Test Owner",
    signingOut: false,
    onSignOut: vi.fn(),
    onNavigate: vi.fn(),
  };
  rerender(
    <WorkbenchShell
      section="plants"
      hash="#/plants/0190d2a8-0000-7000-8000-000000000003"
      {...props}
    >
      <section aria-label="Workspace content" className="app-content" />
    </WorkbenchShell>,
  );
  expect(shell).toHaveClass("wb-shell--collapsed");
  rerender(
    <WorkbenchShell section="plants" hash="#/plants" {...props}>
      <section aria-label="Workspace content" className="app-content" />
    </WorkbenchShell>,
  );
  expect(shell).not.toHaveClass("wb-shell--collapsed");
});

/** Lays out the shell as a browser would; jsdom has no layout. */
function layout(
  viewport: { innerWidth: number; clientWidth: number; clientHeight: number },
  sidebar: Partial<DOMRect>,
  bottombar: Partial<DOMRect> | null,
) {
  vi.stubGlobal("innerWidth", viewport.innerWidth);
  const root = document.documentElement;
  Object.defineProperty(root, "clientWidth", {
    configurable: true,
    value: viewport.clientWidth,
  });
  Object.defineProperty(root, "clientHeight", {
    configurable: true,
    value: viewport.clientHeight,
  });
  const original = window.getComputedStyle.bind(window);
  const pinned = (style: CSSStyleDeclaration, position: string) =>
    new Proxy(style, {
      get: (target, key): unknown =>
        key === "position" ? position : Reflect.get(target, key, target),
    });
  vi.spyOn(window, "getComputedStyle").mockImplementation((element) => {
    const style = original(element);
    if (element.classList.contains("wb-sidebar"))
      return pinned(style, "sticky");
    if (element.classList.contains("wb-bottombar"))
      return pinned(style, bottombar ? "fixed" : "static");
    return style;
  });
  const box = (rect: Partial<DOMRect>) =>
    ({
      left: 0,
      top: 0,
      right: 0,
      bottom: 0,
      width: 0,
      height: 0,
      ...rect,
    }) as DOMRect;
  vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(
    function (this: Element) {
      if (this.classList.contains("wb-sidebar")) return box(sidebar);
      if (this.classList.contains("wb-bottombar") && bottombar)
        return box(bottombar);
      return box({});
    },
  );
}

test.each([
  ["a classic scrollbar (layout viewport 375 of a 390 window)", 390, 375],
  ["overlay scrollbars (layout viewport equals the window)", 390, 390],
])(
  "pinned phone header and bottom bar are published as scroll-padding with %s",
  (_mode, innerWidth, clientWidth) => {
    layout(
      { innerWidth, clientWidth, clientHeight: 844 },
      { right: clientWidth, width: clientWidth, bottom: 116.6, height: 116.6 },
      { top: 779.6, bottom: 844, height: 64.4, right: clientWidth },
    );
    try {
      renderShell();
      const root = document.documentElement.style;
      expect(root.getPropertyValue("--wb-obscured-top")).toBe("117px");
      expect(root.getPropertyValue("--wb-obscured-bottom")).toBe("65px");
    } finally {
      vi.restoreAllMocks();
    }
  },
);

test("a desktop side rail is not published as a pinned top header", () => {
  layout(
    { innerWidth: 1440, clientWidth: 1425, clientHeight: 844 },
    { right: 80, width: 80, bottom: 844, height: 844 },
    null,
  );
  try {
    renderShell();
    const root = document.documentElement.style;
    expect(root.getPropertyValue("--wb-obscured-top")).toBe("0px");
    expect(root.getPropertyValue("--wb-obscured-bottom")).toBe("0px");
  } finally {
    vi.restoreAllMocks();
  }
});
