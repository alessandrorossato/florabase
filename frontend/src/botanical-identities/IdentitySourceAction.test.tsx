import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import {
  getIdentityCollection,
  type BotanicalIdentityCollectionResponse,
} from "../collection/api";
import { IdentitySourceAction } from "./IdentitySourceAction";

const expired = vi.hoisted(() => vi.fn());
const auth = { sessionExpired: expired };
vi.mock("../auth/context", () => ({ useAuth: () => auth }));
vi.mock("../collection/api", () => ({ getIdentityCollection: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
function collection({
  lots = [],
  plants = [],
  groups = [],
}: { lots?: string[]; plants?: string[]; groups?: string[] } = {}) {
  return {
    seed_lots: lots.map((lifecycle, index) => ({
      id: `lot-${String(index)}`,
      label: `Packet ${String(index + 1)}`,
      lifecycle,
      location: null,
    })),
    plants: plants.map((lifecycle, index) => ({
      id: `plant-${String(index)}`,
      label: `Plant ${String(index + 1)}`,
      lifecycle,
      location: null,
      botanical_identity: { display_label: "Ocimum basilicum" },
    })),
    plant_groups: groups.map((lifecycle, index) => ({
      id: `group-${String(index)}`,
      label: `Group ${String(index + 1)}`,
      lifecycle,
      location: null,
      botanical_identity: { display_label: "Ocimum basilicum" },
    })),
  } as unknown as BotanicalIdentityCollectionResponse;
}
test("sowing source selection is explicit, limited to active lots and preserves the source URL", async () => {
  vi.mocked(getIdentityCollection).mockResolvedValue(
    collection({
      lots: ["active", "exhausted", "discarded", "lost", "reversed", "active"],
    }),
  );
  const user = userEvent.setup();
  render(<IdentitySourceAction identityId="identity-a" kind="sowing" />);
  expect(getIdentityCollection).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Start sowing" }));
  expect(await screen.findByRole("link", { name: "Packet 1" })).toHaveAttribute(
    "href",
    "#/sowings?action=start&seedLot=lot-0",
  );
  expect(screen.getByRole("link", { name: "Packet 6" })).toBeInTheDocument();
  expect(
    screen.queryByRole("link", { name: "Packet 2" }),
  ).not.toBeInTheDocument();
  expect(screen.getAllByRole("link")).toHaveLength(2);
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Start sowing" })).toHaveFocus();
});
test("one eligible lot still shows its source before launch and returns to the identity context", async () => {
  window.history.replaceState(null, "", "#/identities/identity-a?tab=sowings");
  vi.mocked(getIdentityCollection).mockResolvedValue(
    collection({ lots: ["active"] }),
  );
  const user = userEvent.setup();
  render(<IdentitySourceAction identityId="identity-a" kind="sowing" />);
  await user.click(screen.getByRole("button", { name: "Start sowing" }));
  await user.click(await screen.findByRole("link", { name: "Packet 1" }));
  expect(window.location.hash).toBe("#/sowings?action=start&seedLot=lot-0");
  expect(window.history.state).toMatchObject({
    collectionPageParent: "#/identities/identity-a?tab=sowings",
  });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
test("no active seed material explains the prerequisite and offers identity-prefilled creation", async () => {
  vi.mocked(getIdentityCollection).mockResolvedValue(
    collection({ lots: ["exhausted"] }),
  );
  const user = userEvent.setup();
  render(<IdentitySourceAction identityId="identity-a" kind="sowing" />);
  await user.click(screen.getByRole("button", { name: "Start sowing" }));
  expect(await screen.findByText(/No active seed lots/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Create seed lot" })).toHaveAttribute(
    "href",
    "#/seeds?action=create&identity=identity-a",
  );
});
test("harvest offers actual Plants and groups including historical/inactive sources", async () => {
  vi.mocked(getIdentityCollection).mockResolvedValue(
    collection({ plants: ["active", "dead"], groups: ["inactive"] }),
  );
  const user = userEvent.setup();
  render(<IdentitySourceAction identityId="identity-a" kind="harvest" />);
  await user.click(screen.getByRole("button", { name: "Record harvest" }));
  expect(await screen.findByRole("link", { name: "Plant 1" })).toHaveAttribute(
    "href",
    "#/harvests?action=create&sourceType=plant&source=plant-0",
  );
  expect(screen.getByRole("link", { name: "Plant 2" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Group 1" })).toHaveAttribute(
    "href",
    "#/harvests?action=create&sourceType=plant_group&source=group-0",
  );
});
test("no harvest source explains the prerequisite and offers both existing creation flows", async () => {
  vi.mocked(getIdentityCollection).mockResolvedValue(collection());
  const user = userEvent.setup();
  render(<IdentitySourceAction identityId="identity-a" kind="harvest" />);
  await user.click(screen.getByRole("button", { name: "Record harvest" }));
  expect(
    await screen.findByText(/No Plants or Plant groups/),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Add source plant" }),
  ).toHaveAttribute(
    "href",
    "#/plants?action=create&identity=identity-a&kind=plant",
  );
  expect(
    screen.getByRole("link", { name: "Add source plant group" }),
  ).toHaveAttribute(
    "href",
    "#/plants?action=create&identity=identity-a&kind=group",
  );
});
test("source errors have retry and cancellation aborts an outstanding request", async () => {
  vi.mocked(getIdentityCollection)
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce(collection());
  const user = userEvent.setup();
  render(<IdentitySourceAction identityId="identity-a" kind="harvest" />);
  await user.click(screen.getByRole("button", { name: "Record harvest" }));
  await user.click(
    await screen.findByRole("button", { name: "Retry sources" }),
  );
  await screen.findByText(/No Plants or Plant groups/);
  expect(getIdentityCollection).toHaveBeenCalledTimes(2);
  const signal = vi.mocked(getIdentityCollection).mock.calls[1][1];
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  await waitFor(() => {
    expect(signal?.aborted).toBe(true);
  });
});
