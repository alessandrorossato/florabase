import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { AuthContext } from "../auth/context";
import { acquireTestAuth } from "../test/auth";
import { DataSourcesScreen } from "./DataSourcesScreen";
import { HelpScreen } from "./HelpScreen";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("Help explains key ideas and links every workspace destination", () => {
  render(<HelpScreen />);
  expect(screen.getByRole("heading", { name: "Help", level: 2 })).toBeVisible();
  const explore = screen.getByRole("region", { name: "Explore" });
  expect(
    within(explore).getByRole("link", { name: "Lineage" }),
  ).toHaveAttribute("href", "#/lineage");
  expect(screen.getByText("Botanical identity")).toBeInTheDocument();
});

test("Data sources lists each external reference with its access rule and the planned standard", () => {
  render(<DataSourcesScreen />);
  const table = screen.getByRole("table");
  expect(
    within(table).getByRole("link", { name: "World Flora Online (WFO)" }),
  ).toHaveAttribute("href", "#/taxonomy");
  expect(within(table).getAllByRole("row")).toHaveLength(7);
  expect(
    screen.getByRole("heading", { name: "Integration standard (planned)" }),
  ).toBeVisible();
});

test("Data sources renders read-only reference index status when authenticated", async () => {
  const { auth } = await acquireTestAuth();
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        mode: "auto",
        wfo: {
          state: "preparing",
          status: "preparing",
          reason: null,
          available: false,
        },
        wcvp_v16: {
          state: "failed",
          status: "failed: disk",
          reason: "disk",
          available: false,
        },
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ),
  );

  render(
    <AuthContext.Provider value={auth}>
      <DataSourcesScreen />
    </AuthContext.Provider>,
  );

  const statusRegion = screen.getByRole("region", {
    name: "Reference index status",
  });
  expect(await within(statusRegion).findByText("preparing")).toBeVisible();
  expect(within(statusRegion).getByText("failed: disk")).toBeVisible();
  expect(within(statusRegion).getByText("enabled")).toBeVisible();
  // Read-only: no action buttons ("start now", etc.).
  expect(within(statusRegion).queryAllByRole("button")).toHaveLength(0);
});

test("Data sources reports ready (setup off) and error states cleanly", async () => {
  const { auth } = await acquireTestAuth();
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
    new Response(
      JSON.stringify({
        mode: "off",
        wfo: {
          state: "ready",
          status: "ready (setup off)",
          reason: null,
          available: true,
        },
        wcvp_v16: {
          state: "manual",
          status: "manual",
          reason: null,
          available: true,
        },
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ),
  );

  const { unmount } = render(
    <AuthContext.Provider value={auth}>
      <DataSourcesScreen />
    </AuthContext.Provider>,
  );

  const statusRegion = screen.getByRole("region", {
    name: "Reference index status",
  });
  expect(
    await within(statusRegion).findByText("ready (setup off)"),
  ).toBeVisible();
  expect(within(statusRegion).getByText("manual")).toBeVisible();
  expect(within(statusRegion).getByText("off")).toBeVisible();
  unmount();

  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
    new Response("error", { status: 503 }),
  );
  render(
    <AuthContext.Provider value={auth}>
      <DataSourcesScreen />
    </AuthContext.Provider>,
  );
  expect(
    await screen.findByText("Could not load reference index status."),
  ).toBeVisible();
});
