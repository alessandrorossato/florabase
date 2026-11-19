import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../auth/context";
import { getMedia, type MediaDetail } from "../media/api";
import { acquireTestAuth } from "../test/auth";
import { IdentityCoverMetadata } from "./IdentityCoverMetadata";
let auth: AuthContextValue;
vi.mock("../media/api", () => ({ getMedia: vi.fn() }));
beforeEach(async () => {
  auth = (await acquireTestAuth()).auth;
});
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
test("cover attribution uses the actual asset and preserves source and licence links", async () => {
  vi.mocked(getMedia).mockResolvedValue({
    title: "Layout illustration",
    attribution: "Original creator · resized derivative",
    licence_label: "CC-BY-3.0",
    licence_url: "https://creativecommons.org/licenses/by/3.0/",
    source_url: "https://commons.wikimedia.org/example",
  } as MediaDetail);
  render(
    <AuthContext.Provider value={auth}>
      <IdentityCoverMetadata id="asset" />
    </AuthContext.Provider>,
  );
  expect(
    await screen.findByText("Original creator · resized derivative"),
  ).toBeVisible();
  expect(screen.getByRole("link", { name: "CC-BY-3.0" })).toHaveAttribute(
    "href",
    "https://creativecommons.org/licenses/by/3.0/",
  );
  expect(
    screen.getByRole("link", { name: "Original image source" }),
  ).toHaveAttribute("href", "https://commons.wikimedia.org/example");
  expect(getMedia).toHaveBeenCalledWith(
    "asset",
    auth.capability,
    expect.any(AbortSignal),
  );
});
test("failed attribution is explicit and retryable", async () => {
  vi.mocked(getMedia)
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce({
      title: null,
      attribution: null,
      licence_label: null,
      licence_url: null,
      source_url: null,
    } as MediaDetail);
  const user = userEvent.setup();
  render(
    <AuthContext.Provider value={auth}>
      <IdentityCoverMetadata id="asset" />
    </AuthContext.Provider>,
  );
  expect(await screen.findByRole("alert")).toHaveTextContent("could not load");
  await user.click(
    screen.getByRole("button", { name: "Retry cover attribution" }),
  );
  expect(await screen.findByText("Attribution not recorded")).toBeVisible();
});
