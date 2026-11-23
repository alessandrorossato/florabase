import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../auth/context";
import {
  IdentityRecordMedia,
  type IdentityMediaRecord,
} from "./IdentityRecordMedia";
import { listPhotos } from "../photos/api";
import { getMedia } from "../media/api";
import { acquireTestAuth } from "../test/auth";
let auth: AuthContextValue;
vi.mock("../photos/api", () => ({ listPhotos: vi.fn() }));
vi.mock("../media/api", () => ({ getMedia: vi.fn() }));
const records: IdentityMediaRecord[] = [
  {
    id: "plant",
    target: "plant",
    kind: "Plant",
    label: "Mother plant",
    href: "#/plants/plant?tab=photos",
  },
];
const asset = {
  id: "asset",
  kind: "local",
  title: "Leaves",
  attribution: "Photographer",
  licence_label: "CC BY 3.0",
  licence_url: "https://creativecommons.org/licenses/by/3.0/",
  source_url: "https://example.org/image",
  content_url: "/content",
  thumbnail_url: "/thumbnail",
  deletion_pending: false,
} as never;
beforeEach(async () => {
  auth = (await acquireTestAuth()).auth;
});
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  vi.restoreAllMocks();
});
test("real linked images retain captions, actual asset rights and source ownership", async () => {
  vi.mocked(listPhotos).mockResolvedValue([
    { id: "photo", media_asset_id: "asset", caption: "Young leaves" },
  ] as never);
  vi.mocked(getMedia).mockResolvedValue(asset);
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(new Blob(["img"], { type: "image/png" }), { status: 200 }),
  );
  render(
    <AuthContext.Provider value={auth}>
      <IdentityRecordMedia records={records} />
    </AuthContext.Provider>,
  );
  const img = await screen.findByRole("img", { name: "Leaves" });
  expect(img.getAttribute("src")).toMatch(/^blob:/);
  expect(listPhotos).toHaveBeenCalledWith(
    "plant",
    "plant",
    auth.capability,
    expect.any(AbortSignal),
  );
  expect(
    screen.getByRole("link", { name: "Plant · Mother plant" }),
  ).toHaveAttribute("href", records[0].href);
  expect(
    screen.getByRole("link", { name: "Open media details for Young leaves" }),
  ).toHaveAttribute("href", "#/media/asset");
  expect(screen.getByText(/Photographer/)).toBeVisible();
  expect(screen.getByRole("link", { name: "Image source" })).toHaveAttribute(
    "href",
    "https://example.org/image",
  );
  expect(screen.getByRole("link", { name: "CC BY 3.0" })).toHaveAttribute(
    "href",
    "https://creativecommons.org/licenses/by/3.0/",
  );
});
test("external references do not contact their image host and errors remain retryable", async () => {
  const user = userEvent.setup();
  vi.mocked(listPhotos).mockRejectedValueOnce(new Error("offline"));
  render(
    <AuthContext.Provider value={auth}>
      <IdentityRecordMedia records={records} />
    </AuthContext.Provider>,
  );
  expect(await screen.findByRole("alert")).toHaveTextContent("could not load");
  vi.mocked(listPhotos).mockResolvedValue([
    { id: "photo", media_asset_id: "asset", caption: null },
  ] as never);
  vi.mocked(getMedia).mockResolvedValue({
    ...(asset as object),
    kind: "external",
    content_url: null,
    thumbnail_url: null,
    image_url: "https://remote.example/image.jpg",
  } as never);
  await user.click(screen.getByRole("button", { name: "Retry linked images" }));
  expect(await screen.findByText("Not stored locally")).toBeVisible();
  expect(screen.queryByRole("img")).toBeNull();
  expect(screen.queryByText("Preview once")).toBeNull();
});
test("empty and bounded record batches do not invent images or load the whole collection", async () => {
  const user = userEvent.setup();
  vi.mocked(listPhotos).mockResolvedValue([]);
  const many = Array.from({ length: 8 }, (_, n) => ({
    ...records[0],
    id: String(n),
  }));
  render(
    <AuthContext.Provider value={auth}>
      <IdentityRecordMedia records={many} />
    </AuthContext.Provider>,
  );
  expect(await screen.findByText(/No photos on the records/)).toBeVisible();
  expect(listPhotos).toHaveBeenCalledTimes(6);
  expect(getMedia).not.toHaveBeenCalled();
  await user.click(
    screen.getByRole("button", {
      name: "Show photos from more records",
    }),
  );
  await waitFor(() => {
    expect(listPhotos).toHaveBeenCalledWith(
      "plant",
      "7",
      auth.capability,
      expect.any(AbortSignal),
    );
  });
  expect(screen.queryByRole("img")).toBeNull();
});

test("older photos with no asset reference remain source-record evidence rather than false absence", async () => {
  vi.mocked(listPhotos).mockResolvedValue([
    { id: "older-photo", media_asset_id: null },
  ] as never);
  render(
    <AuthContext.Provider value={auth}>
      <IdentityRecordMedia records={records} />
    </AuthContext.Provider>,
  );
  expect(await screen.findByText(/Some older photo entries/)).toBeVisible();
  expect(screen.queryByText(/No photos on the records/)).toBeNull();
  expect(getMedia).not.toHaveBeenCalled();
});
