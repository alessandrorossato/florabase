import { cleanup, render, screen } from "@testing-library/react";
import { lazy, Suspense } from "react";
import { afterEach, expect, test, vi } from "vitest";

import { WorkspaceBoundary } from "./WorkspaceBoundary";
import { loadWorkspaceChunk } from "./workspaceChunk";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("failed chunk loading leaves a recovery action and the application shell usable", async () => {
  vi.spyOn(console, "error").mockImplementation(() => undefined);
  const FailedWorkspace = lazy(() =>
    loadWorkspaceChunk(() =>
      Promise.reject(
        new TypeError("Failed to fetch dynamically imported module"),
      ),
    ),
  );
  const { rerender } = render(
    <>
      <button>Sign out</button>
      <WorkspaceBoundary key="failed">
        <Suspense fallback={<p>Loading workspace…</p>}>
          <FailedWorkspace />
        </Suspense>
      </WorkspaceBoundary>
    </>,
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Florabase could not load this workspace.",
  );
  expect(screen.getByRole("button", { name: "Sign out" })).toBeEnabled();
  expect(
    screen.getByRole("button", { name: "Reload and try again" }),
  ).toBeEnabled();
  rerender(
    <>
      <button>Sign out</button>
      <WorkspaceBoundary key="other-route">
        <h2>Another workspace</h2>
      </WorkspaceBoundary>
    </>,
  );
  expect(
    screen.getByRole("heading", { name: "Another workspace" }),
  ).toBeInTheDocument();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

test("ordinary workspace render errors continue to surface", () => {
  vi.spyOn(console, "error").mockImplementation(() => undefined);
  function BrokenWorkspace(): never {
    throw new Error("Ordinary component failure");
  }

  expect(() =>
    render(
      <WorkspaceBoundary>
        <BrokenWorkspace />
      </WorkspaceBoundary>,
    ),
  ).toThrow("Ordinary component failure");
});

test("workspace module evaluation errors are not presented as download failures", async () => {
  const moduleError = new TypeError("Cannot read properties of undefined");
  await expect(
    loadWorkspaceChunk(() => Promise.reject(moduleError)),
  ).rejects.toBe(moduleError);
});
