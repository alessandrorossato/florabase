import type { ReactElement } from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../auth/context";
import { acquireTestAuth } from "../test/auth";
import { EventTargetPhoto } from "./EventTargetPhoto";

let auth: AuthContextValue;
function renderWithAuth(ui: ReactElement) {
  return render(<AuthContext.Provider value={auth}>{ui}</AuthContext.Provider>);
}
beforeEach(async () => {
  auth = (await acquireTestAuth()).auth;
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
const identity = { id: "identity", display_label: "Species" };

test("Dashboard and Events target imagery uses a saved external primary locally", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(
      new Response(new Blob(["img"], { type: "image/png" }), { status: 200 }),
    );
  renderWithAuth(
    <EventTargetPhoto
      kind="plant"
      label="Plant"
      identity={identity}
      photo={{
        kind: "external",
        photo_id: "link",
        thumbnail_url: "/api/v1/media-assets/snapshot/thumbnail?v=1",
      }}
    />,
  );
  const img = await screen.findByRole("img");
  expect(img.getAttribute("src")).toMatch(/^blob:/);
  expect(fetch).toHaveBeenCalledWith(
    "/api/v1/media-assets/snapshot/thumbnail?v=1",
    expect.objectContaining({ credentials: "same-origin" }),
  );
});

test("reference-only activity target stays a placeholder without remote loading", () => {
  renderWithAuth(
    <EventTargetPhoto
      kind="plant"
      label="Plant"
      identity={identity}
      photo={{ kind: "external", photo_id: "link", thumbnail_url: null }}
    />,
  );
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});

test("activity retains its explicitly supplied source-photo evidence", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(
      new Response(new Blob(["img"], { type: "image/png" }), { status: 200 }),
    );
  renderWithAuth(
    <EventTargetPhoto
      kind="harvest"
      label="Harvest Event"
      identity={identity}
      photo={null}
      fallbackPhoto={{
        kind: "local",
        photo_id: "source",
        thumbnail_url: "/source-evidence",
      }}
    />,
  );
  const img = await screen.findByRole("img", {
    name: "Source primary photo for Harvest Event",
  });
  expect(img.getAttribute("src")).toMatch(/^blob:/);
  expect(fetch).toHaveBeenCalledWith(
    "/source-evidence",
    expect.objectContaining({ credentials: "same-origin" }),
  );
});
