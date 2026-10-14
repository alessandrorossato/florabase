import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";

const { loaded } = vi.hoisted(() => ({ loaded: [] as string[] }));
vi.mock("./collection/DashboardScreen", () => {
  loaded.push("dashboard");
  return { DashboardScreen: () => <h2>Dashboard workspace</h2> };
});
vi.mock("./labels/LabelsScreen", () => {
  loaded.push("labels");
  return { LabelsScreen: () => <h2>Labels workspace</h2> };
});
vi.mock("./seed-lots/SeedLotScreen", () => {
  loaded.push("seeds");
  return { SeedLotScreen: () => <h2>Seeds workspace</h2> };
});

import { App } from "./App";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.history.replaceState(null, "", "/");
});

test("restoration defers workspaces and navigation loads only the selected workspace", async () => {
  let restore: ((response: Response) => void) | undefined;
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const path =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    if (path.endsWith("/auth/session"))
      return new Promise<Response>((resolve) => {
        restore = resolve;
      });
    return Promise.resolve(
      new Response(
        JSON.stringify(
          path.endsWith("/auth/csrf")
            ? { csrf_token: "test-token" }
            : { status: "ok" },
        ),
        { headers: { "Content-Type": "application/json" } },
      ),
    );
  });
  window.history.replaceState(null, "", "/#/dashboard");
  render(<App />);
  expect(screen.getByText(/restoring your session/i)).toBeInTheDocument();
  expect(loaded).toEqual([]);
  restore?.(
    new Response(
      JSON.stringify({
        user_id: "01900000-0000-7000-8000-000000000001",
        login_name: "owner",
        display_name: "Owner",
        owner: true,
        canonical_origin: "http://localhost:5173",
      }),
      { headers: { "Content-Type": "application/json" } },
    ),
  );
  await screen.findByRole(
    "heading",
    { name: "Dashboard workspace" },
    { timeout: 5000 },
  );
  expect(loaded).toEqual(["dashboard"]);
  const user = userEvent.setup();
  await user.click(screen.getByRole("link", { name: "Settings" }));
  await screen.findByRole("heading", { name: "Settings" }, { timeout: 5000 });
  await user.click(await screen.findByRole("link", { name: "Labels" }));
  await screen.findByRole(
    "heading",
    { name: "Labels workspace" },
    { timeout: 5000 },
  );
  expect(loaded).toEqual(["dashboard", "labels"]);
  await user.click(
    within(
      screen.getByRole("navigation", { name: "Primary navigation" }),
    ).getByRole("link", { name: "Seeds" }),
  );
  await screen.findByRole(
    "heading",
    { name: "Seeds workspace" },
    { timeout: 5000 },
  );
  expect(loaded).toEqual(["dashboard", "labels", "seeds"]);
  await user.click(screen.getByRole("link", { name: "Dashboard" }));
  await screen.findByRole(
    "heading",
    { name: "Dashboard workspace" },
    { timeout: 5000 },
  );
  expect(loaded).toEqual(["dashboard", "labels", "seeds"]);
});
