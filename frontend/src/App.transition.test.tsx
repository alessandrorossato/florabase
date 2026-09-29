import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";

const seedGate = vi.hoisted(() => {
  let release: () => void = () => undefined;
  const pending = new Promise<void>((resolve) => {
    release = resolve;
  });
  return {
    pending,
    release: () => {
      release();
    },
  };
});

vi.mock("./collection/DashboardScreen", () => ({
  DashboardScreen: () => <h2>Dashboard workspace</h2>,
}));
vi.mock("./seed-lots/SeedLotScreen", async () => {
  await seedGate.pending;
  return { SeedLotScreen: () => <h2>Seeds workspace</h2> };
});

import { App } from "./App";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.history.replaceState(null, "", "/");
});

test("an unresolved route chunk shows a compact loading placeholder and one shell title", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const path =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    const body = path.endsWith("/auth/session")
      ? {
          user_id: "01900000-0000-7000-8000-000000000001",
          login_name: "owner",
          owner: true,
          canonical_origin: "http://localhost:5173",
        }
      : path.endsWith("/auth/csrf")
        ? { csrf_token: "test-token" }
        : { status: "ok" };
    return Promise.resolve(
      new Response(JSON.stringify(body), {
        headers: { "Content-Type": "application/json" },
      }),
    );
  });
  window.history.replaceState(null, "", "/#/dashboard");
  render(<App />);
  await screen.findByRole("heading", { name: "Dashboard workspace" });
  await userEvent.setup().click(screen.getByRole("button", { name: "Seeds" }));
  const loading = screen.getByRole("status");
  expect(loading).toHaveClass("workspace-route-loading");
  expect(loading).toHaveTextContent("Loading workspace…");
  expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  expect(screen.queryByRole("heading", { name: "Seeds workspace" })).toBeNull();

  await act(async () => {
    seedGate.release();
    await seedGate.pending;
  });
  expect(
    await screen.findByRole("heading", { name: "Seeds workspace" }),
  ).toBeInTheDocument();
  expect(screen.queryByText("Loading workspace…")).toBeNull();
});
