import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import {
  IdentityRecordMedia,
  type IdentityMediaRecord,
} from "./IdentityRecordMedia";
import { listPhotos } from "../photos/api";
import { getMedia } from "../media/api";
vi.mock("../auth/context", () => ({ useAuth: () => auth }));
const auth = { sessionExpired: vi.fn() };
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
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
test("real linked images retain captions, actual asset rights and source ownership", async () => {
  vi.mocked(listPhotos).mockResolvedValue([
    { id: "photo", media_asset_id: "asset", caption: "Young leaves" },
  ] as never);
  vi.mocked(getMedia).mockResolvedValue(asset);
  render(<IdentityRecordMedia records={records} />);
  expect(await screen.findByRole("img", { name: "Leaves" })).toHaveAttribute(
    "src",
    "/thumbnail",
  );
  expect(listPhotos).toHaveBeenCalledWith(
    "plant",
    "plant",
    expect.any(AbortSignal),
  );
  expect(screen.getByRole("link", { name: "Mother plant" })).toHaveAttribute(
    "href",
    records[0].href,
  );
  expect(
    screen.getByRole("link", { name: "Open media details for Young leaves" }),
  ).toHaveAttribute("href", "#/media/asset");
  expect(screen.getByText("Photographer")).toBeVisible();
  expect(screen.getByRole("link", { name: "CC BY 3.0" })).toHaveAttribute(
    "href",
    "https://creativecommons.org/licenses/by/3.0/",
  );
});
test("external references do not contact their image host and errors remain retryable", async () => {
  const user = userEvent.setup();
  vi.mocked(listPhotos).mockRejectedValueOnce(new Error("offline"));
  render(<IdentityRecordMedia records={records} />);
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
  render(<IdentityRecordMedia records={many} />);
  expect(await screen.findByText(/No images are attached/)).toBeVisible();
  expect(listPhotos).toHaveBeenCalledTimes(6);
  expect(getMedia).not.toHaveBeenCalled();
  await user.click(
    screen.getByRole("button", {
      name: "Show images from more linked records",
    }),
  );
  await waitFor(() => {
    expect(listPhotos).toHaveBeenCalledWith(
      "plant",
      "7",
      expect.any(AbortSignal),
    );
  });
  expect(screen.queryByRole("img")).toBeNull();
});

test("older photos with no asset reference remain source-record evidence rather than false absence", async () => {
  vi.mocked(listPhotos).mockResolvedValue([
    { id: "older-photo", media_asset_id: null },
  ] as never);
  render(<IdentityRecordMedia records={records} />);
  expect(await screen.findByText(/Some older photo entries/)).toBeVisible();
  expect(screen.queryByText(/No images are attached/)).toBeNull();
  expect(getMedia).not.toHaveBeenCalled();
});
