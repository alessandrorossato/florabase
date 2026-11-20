import type { ReactElement } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/context";
import { acquireTestAuth } from "../test/auth";
import { PrimaryPhotoVisual } from "./PrimaryPhotoVisual";

let auth: AuthContextValue;
function renderVisual(ui: ReactElement) {
  return render(<AuthContext.Provider value={auth}>{ui}</AuthContext.Provider>);
}
function mockImageFetch() {
  return vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(
      new Response(new Blob(["img"], { type: "image/png" }), { status: 200 }),
    );
}
beforeEach(async () => {
  auth = (await acquireTestAuth()).auth;
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("local primary uses only its fixed protected thumbnail and falls back on failure", async () => {
  const url = "/api/v1/collection-photos/local/photo-1/thumbnail";
  const fetch = mockImageFetch();
  renderVisual(
    <PrimaryPhotoVisual
      photo={{ kind: "local", photo_id: "photo-1", thumbnail_url: url }}
      label="Seed lot A"
      compact
    />,
  );
  const image = await screen.findByRole("img", {
    name: "Primary photo for Seed lot A",
  });
  expect(image.getAttribute("src")).toMatch(/^blob:/);
  expect(fetch).toHaveBeenCalledWith(
    url,
    expect.objectContaining({ credentials: "same-origin" }),
  );
  expect(image).toHaveAttribute("loading", "lazy");
  fireEvent.error(image);
  expect(screen.getByText("Primary photo unavailable")).toBeVisible();
});

test("external primary remains a neutral indicator with no remote request", () => {
  renderVisual(
    <PrimaryPhotoVisual
      photo={{ kind: "external", photo_id: "photo-2", thumbnail_url: null }}
      label="Plant B"
    />,
  );
  expect(screen.getByText("External primary photo")).toBeVisible();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});

test("no primary has no image or inferred fallback", () => {
  const { container } = renderVisual(
    <PrimaryPhotoVisual photo={null} label="Group C" />,
  );
  expect(container).toBeEmptyDOMElement();
});

test.each([
  null,
  { kind: "external" as const, photo_id: "external", thumbnail_url: null },
])(
  "neutral directory slot never loads an absent or external image",
  (photo) => {
    const { container } = renderVisual(
      <PrimaryPhotoVisual
        photo={photo}
        label="Record"
        compact
        fallback="neutral"
      />,
    );
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(container.querySelector("[aria-hidden=true]")).toBeInTheDocument();
    expect(container).not.toHaveTextContent("External primary photo");
  },
);

test("failed local directory thumbnail keeps its neutral slot", async () => {
  mockImageFetch();
  const { container } = renderVisual(
    <PrimaryPhotoVisual
      photo={{
        kind: "local",
        photo_id: "local",
        thumbnail_url: "/api/v1/photos/local/thumbnail",
      }}
      label="Record"
      compact
      fallback="neutral"
    />,
  );
  fireEvent.error(await screen.findByRole("img"));
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  expect(container.querySelector("[aria-hidden=true]")).toBeInTheDocument();
});

test("saved external primary uses its protected snapshot for activity visuals", async () => {
  const fetch = mockImageFetch();
  renderVisual(
    <PrimaryPhotoVisual
      label="Plant"
      photo={{
        kind: "external",
        photo_id: "external",
        thumbnail_url: "/api/v1/media-assets/external/thumbnail?v=1",
      }}
    />,
  );
  const img = await screen.findByRole("img");
  expect(img.getAttribute("src")).toMatch(/^blob:/);
  expect(fetch).toHaveBeenCalledWith(
    "/api/v1/media-assets/external/thumbnail?v=1",
    expect.objectContaining({ credentials: "same-origin" }),
  );
});
