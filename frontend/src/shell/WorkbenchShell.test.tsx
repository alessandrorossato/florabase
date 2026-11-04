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
