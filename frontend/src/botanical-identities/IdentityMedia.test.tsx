import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import type { BotanicalIdentityResponse } from "./api";
import type { BotanicalIdentityCollectionResponse } from "../collection/api";
import { IdentityMedia } from "./IdentityMedia";
vi.mock("../photos/BotanicalIdentityCover", () => ({
  BotanicalIdentityCover: ({ identityId }: { identityId: string }) => (
    <p>Cover for {identityId}</p>
  ),
}));
vi.mock("./IdentityRecordMedia", () => ({
  IdentityRecordMedia: () => <p>Actual linked image gallery</p>,
}));
afterEach(cleanup);
test("identity media shows the cover and record photos without technical explanations", () => {
  const identity = {
    id: "identity",
    display_label: "Salvia officinalis",
  } as BotanicalIdentityResponse;
  const collection = {
    identity,
    seed_lots: [{ id: "lot", label: "Packet" }],
    sowings: [],
    plants: [],
    plant_groups: [],
    harvests: [],
    events: [],
  } as unknown as BotanicalIdentityCollectionResponse;
  const { rerender } = render(
    <IdentityMedia
      identity={identity}
      csrfToken="csrf"
      collection={collection}
    />,
  );
  expect(screen.getByText("Cover for identity")).toBeVisible();
  expect(screen.getByText("Actual linked image gallery")).toBeVisible();
  expect(
    screen.getByRole("heading", { name: "Collection record photos" }),
  ).toBeVisible();
  expect(screen.queryByText(/identity-level media contract/)).toBeNull();
  rerender(
    <IdentityMedia
      identity={identity}
      csrfToken="csrf"
      collection={{ ...collection, seed_lots: [] }}
    />,
  );
  expect(
    screen.getByText("No collection records use this identity yet."),
  ).toBeVisible();
  expect(screen.queryByText("Actual linked image gallery")).toBeNull();
});
