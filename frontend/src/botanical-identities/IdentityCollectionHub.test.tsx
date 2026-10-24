import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import type { BotanicalIdentityCollectionResponse } from "../collection/api";
import { getIdentityCollection } from "../collection/api";
import { IdentityCollectionHub } from "./IdentityCollectionHub";
import { identityDirectory } from "./identityNavigation";

const auth = { sessionExpired: vi.fn() };
vi.mock("../auth/context", () => ({ useAuth: () => auth }));
vi.mock("../collection/api", () => ({ getIdentityCollection: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
const id = "01900000-0000-7000-8000-000000000099";
function fixture(total = 0) {
  return {
    identity: { id },
    seed_lots: Array.from({ length: total }, (_, index) => ({
      id: `lot-${String(index)}`,
      label: `Packet ${String(index)}`,
      lifecycle: index ? "exhausted" : "active",
    })),
    sowings: [
      {
        id: "sowing-1",
        label: "Tray",
        lifecycle: "active",
        seed_lot: { id: "lot-0", label: "Packet 0" },
      },
    ],
    plants: [],
    plant_groups: [],
    harvests: [],
  } as unknown as BotanicalIdentityCollectionResponse;
}
test("one Collection page bounds a large collection and links all original owners and exact directories", () => {
  render(<IdentityCollectionHub value={fixture(40)} />);
  const lots = screen.getByRole("region", { name: "Seed lots" });
  expect(within(lots).getByRole("heading")).toHaveTextContent("40 recorded");
  expect(within(lots).getAllByRole("listitem")).toHaveLength(4);
  expect(screen.queryByRole("link", { name: "Packet 4" })).toBeNull();
  for (const [kind, label] of [
    ["seeds", "Seed lots"],
    ["sowings", "Sowings"],
    ["plants", "Plants"],
    ["groups", "Plant groups"],
    ["harvests", "Harvests"],
  ] as const)
    expect(
      screen.getByRole("link", { name: `View all ${label} for this identity` }),
    ).toHaveAttribute("href", identityDirectory(kind, id));
  expect(screen.getByRole("link", { name: "Tray" })).toHaveAttribute(
    "href",
    "#/sowings/sowing-1",
  );
  expect(
    within(screen.getByRole("region", { name: "Sowings" })).getByRole("link", {
      name: "Packet 0",
    }),
  ).toHaveAttribute("href", "#/seeds/lot-0");
  expect(
    screen.getByRole("link", { name: "Create plant group from this sowing" }),
  ).toHaveAttribute(
    "href",
    "#/plants?action=from-sowing&sowing=sowing-1&kind=group",
  );
  expect(getIdentityCollection).not.toHaveBeenCalled();
});
test("Add group uses the existing task and keeps the identity hub as return context", async () => {
  window.history.replaceState(null, "", `#/identities/${id}?tab=collection`);
  render(<IdentityCollectionHub value={fixture()} />);
  const user = userEvent.setup();
  await user.click(screen.getByRole("link", { name: "Add plant group" }));
  expect(window.location.hash).toBe(
    `#/plants?action=create&identity=${id}&kind=group`,
  );
  expect(window.history.state).toMatchObject({
    collectionPageParent: `#/identities/${id}?tab=collection`,
  });
});
