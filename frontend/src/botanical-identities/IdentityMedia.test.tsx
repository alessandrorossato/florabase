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
test("identity cover and related-record photo destinations retain separate ownership without claiming photos exist", () => {
  const identity = {
    id: "identity",
    display_label: "Salvia officinalis",
  } as BotanicalIdentityResponse;
  const collection = {
    identity,
    seed_lots: [{ id: "lot", label: "Packet" }],
    sowings: [{ id: "tray", label: "Tray" }],
    plants: [{ id: "plant", label: "Mother" }],
    plant_groups: [{ id: "group", label: "Seedlings" }],
    harvests: [{ id: "harvest", display_title: "Collected leaves" }],
    events: [],
  } as unknown as BotanicalIdentityCollectionResponse;
  render(
    <IdentityMedia
      identity={identity}
      csrfToken="csrf"
      collection={collection}
    />,
  );
  expect(screen.getByText("Cover for identity")).toBeVisible();
  for (const [name, href] of [
    ["Packet", "#/seeds/lot?tab=photos"],
    ["Tray", "#/sowings/tray?tab=photos"],
    ["Mother", "#/plants/plant?tab=photos"],
    ["Seedlings", "#/plant-groups/group?tab=photos"],
    ["Collected leaves", "#/harvests/harvest"],
  ])
    expect(screen.getByRole("link", { name })).toHaveAttribute("href", href);
  expect(
    screen.getByText(/These remain collection-record media/),
  ).toBeVisible();
  expect(
    screen.getByText(/one cover, not arbitrary direct attachments/),
  ).toBeVisible();
});
