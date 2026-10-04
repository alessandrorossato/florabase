import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../auth/context";
import { ApiError } from "../auth/api";
import {
  StoredMaterialDirectory,
  StoredMaterialSection,
} from "./StoredMaterial";
import { InventoryDialog } from "./InventoryDialog";
import { type Harvest } from "./api";
import * as api from "./inventoryApi";
import { type Inventory } from "./inventoryApi";
vi.mock("./inventoryApi", async (original) => ({
  ...(await original<typeof import("./inventoryApi")>()),
  inventoryList: vi.fn(),
  saveInventory: vi.fn(),
  recordDisposition: vi.fn(),
  removeInventory: vi.fn(),
  dispositionHistory: vi.fn(),
}));
vi.mock("../locations/api", async (original) => ({
  ...(await original<typeof import("../locations/api")>()),
  listLocations: vi.fn(() =>
    Promise.resolve([
      {
        id: "storage",
        display_path: "Fridge → Long seed drawer",
        usage_scopes: ["harvest_inventory"],
        retired_at: null,
      },
    ]),
  ),
}));
const auth: AuthContextValue = {
  state: {
    status: "authenticated",
    csrfToken: "token",
    session: {
      user_id: "owner",
      login_name: "owner",
      display_name: null,
      owner: true,
      canonical_origin: "http://localhost",
    },
  },
  logIn: vi.fn(),
  logOut: vi.fn(),
  sessionExpired: vi.fn(),
  retryRestoration: vi.fn(),
  cancelLogout: vi.fn(),
};
const item: Harvest["items"][number] = {
  display_order: 0,
  description: null,
  id: "item",
  material_kind: "seed",
  quantity: {
    kind: "item_count",
    value: "10",
    unit: null,
    is_approximate: false,
  },
};
const source: Harvest["source"] = {
  id: "source",
  type: "plant",
  label: "Old coffee",
  display_name: "Old coffee",
  lifecycle: "dead",
  botanical_identity: { id: "identity", display_label: "Coffea arabica" },
};
const harvest: Harvest = {
  id: "harvest",
  plant_id: "source",
  plant_group_id: null,
  label: null,
  display_title: "Coffee seed harvest",
  source,
  occurred_on: null,
  notes: null,
  event_id: "event",
  items: [{ ...item, id: "item", display_order: 0, description: null }],
  created_at: "2026-10-03T00:00:00Z",
  updated_at: "2026-10-03T00:00:00Z",
};
const inventory: Inventory = {
  id: "inventory",
  harvest_item_id: "item",
  harvest_id: "harvest",
  harvest_title: harvest.display_title,
  source,
  material_kind: "seed",
  description: null,
  state: "active",
  quantity: item.quantity ?? null,
  location: null,
  has_dispositions: false,
  created_at: harvest.created_at,
  updated_at: harvest.updated_at,
};
function wrap(child: React.ReactNode) {
  return render(
    <AuthContext.Provider value={auth}>{child}</AuthContext.Provider>,
  );
}
beforeEach(() => {
  vi.mocked(api.inventoryList).mockResolvedValue([]);
  vi.mocked(api.saveInventory).mockResolvedValue(inventory);
  vi.mocked(api.recordDisposition).mockResolvedValue([]);
  vi.mocked(api.dispositionHistory).mockResolvedValue([]);
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
it("shows untracked opt-in separately from historical collection", async () => {
  wrap(<StoredMaterialSection harvest={harvest} />);
  expect(await screen.findByText("Not tracked")).toBeVisible();
  await userEvent.click(
    screen.getByRole("button", { name: "Track stored material" }),
  );
  const dialog = screen.getByRole("dialog", { name: "Track stored material" });
  expect(within(dialog).getByText("Collected:")).toBeVisible();
  expect(within(dialog).getByLabelText("Remaining now amount")).toHaveValue(
    "10",
  );
  expect(screen.queryByText(/Add to seed inventory/i)).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: /transfer|death|seedlot/i }),
  ).not.toBeInTheDocument();
});
it("confirms a smaller current amount with explicit Location selection", async () => {
  const saved = vi.fn();
  wrap(<InventoryDialog item={item} onClose={vi.fn()} onSaved={saved} />);
  await screen.findByLabelText("Storage Location");
  await userEvent.clear(screen.getByLabelText("Remaining now amount"));
  await userEvent.type(screen.getByLabelText("Remaining now amount"), "8");
  await userEvent.click(screen.getByLabelText("Storage Location"));
  await userEvent.click(
    within(
      screen.getByRole("option", { name: "Fridge → Long seed drawer" }),
    ).getByRole("button"),
  );
  await userEvent.click(
    screen.getByRole("button", { name: "Track stored material" }),
  );
  expect(api.saveInventory).toHaveBeenCalledWith(
    "item",
    undefined,
    {
      state: "active",
      quantity: { ...item.quantity, value: "8" },
      location_id: "storage",
    },
    "token",
  );
  expect(saved).toHaveBeenCalled();
});
it.each(api.dispositionKinds)(
  "records exact partial $label with no client-rounded arithmetic",
  async ({ id }) => {
    wrap(
      <InventoryDialog
        item={item}
        inventory={inventory}
        disposition
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );
    await userEvent.selectOptions(screen.getByLabelText("Disposition"), id);
    await userEvent.type(screen.getByLabelText("Amount used amount"), "3");
    expect(
      screen.getByText(/exact amount used will be subtracted/),
    ).toBeVisible();
    await userEvent.click(
      screen.getByRole("button", { name: "Record disposition" }),
    );
    expect(api.recordDisposition).toHaveBeenCalledWith(
      "inventory",
      expect.objectContaining({
        kind: id,
        mode: "partial",
        quantity: { ...item.quantity, value: "3" },
        resulting_quantity: null,
      }),
      "token",
    );
  },
);
it("requires confirmed approximate remainder and preserves weight units", async () => {
  const stock: Inventory = {
    ...inventory,
    quantity: { kind: "weight", unit: "g", value: "100", is_approximate: true },
  };
  wrap(
    <InventoryDialog
      item={item}
      inventory={stock}
      disposition
      onClose={vi.fn()}
      onSaved={vi.fn()}
    />,
  );
  expect(screen.getByText(/About 100 g/)).toBeVisible();
  await userEvent.selectOptions(
    screen.getByLabelText("Amount used precision"),
    "unknown",
  );
  await userEvent.type(
    screen.getByLabelText("Confirmed remaining now amount"),
    "60",
  );
  await userEvent.click(
    screen.getByRole("button", { name: "Record disposition" }),
  );
  expect(api.recordDisposition).toHaveBeenCalledWith(
    "inventory",
    expect.objectContaining({
      quantity: null,
      resulting_quantity: {
        kind: "weight",
        unit: "g",
        value: "60",
        is_approximate: true,
      },
    }),
    "token",
  );
});
it("unknown partial stock stays unknown and use-all is explicit", async () => {
  wrap(
    <InventoryDialog
      item={item}
      inventory={{ ...inventory, quantity: null }}
      disposition
      onClose={vi.fn()}
      onSaved={vi.fn()}
    />,
  );
  expect(screen.getByText("Remaining quantity stays unknown.")).toBeVisible();
  await userEvent.selectOptions(
    screen.getByLabelText("Material leaving stock"),
    "use_all",
  );
  expect(
    screen.queryByLabelText("Amount used precision"),
  ).not.toBeInTheDocument();
  expect(screen.getByText(/marks stored material depleted/)).toBeVisible();
  await userEvent.click(
    screen.getByRole("button", { name: "Record disposition" }),
  );
  expect(api.recordDisposition).toHaveBeenCalledWith(
    "inventory",
    expect.objectContaining({
      mode: "use_all",
      quantity: null,
      resulting_quantity: null,
    }),
    "token",
  );
});
it("retains disposition history, blocks removal and permits current correction", async () => {
  vi.mocked(api.inventoryList).mockResolvedValue([
    { ...inventory, state: "depleted", quantity: null, has_dispositions: true },
  ]);
  vi.mocked(api.dispositionHistory).mockResolvedValue([
    {
      id: "fact",
      inventory_id: "inventory",
      kind: "gifted",
      mode: "use_all",
      occurred_on: null,
      quantity: item.quantity ?? null,
      before: { state: "active", quantity: item.quantity ?? null },
      after: { state: "depleted", quantity: null },
      notes: "Given to a friend",
      created_at: harvest.created_at,
    },
  ]);
  wrap(<StoredMaterialSection harvest={harvest} />);
  await screen.findByRole("button", { name: "Edit stored material" });
  expect(
    screen.queryByRole("button", { name: "Record disposition" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Remove tracking" }),
  ).not.toBeInTheDocument();
  await userEvent.click(
    screen.getByRole("button", { name: "Show disposition history" }),
  );
  expect(await screen.findByText("Given to a friend")).toBeVisible();
  expect(screen.getByText("After: Depleted · no material held")).toBeVisible();
  await userEvent.click(
    screen.getByRole("button", { name: "Edit stored material" }),
  );
  await screen.findByLabelText("Storage Location");
  await userEvent.selectOptions(
    screen.getByLabelText("Inventory state"),
    "active",
  );
  await userEvent.click(
    within(
      screen.getByRole("dialog", { name: "Edit stored material" }),
    ).getByRole("button", { name: "Edit stored material" }),
  );
  expect(api.saveInventory).toHaveBeenCalledWith(
    "item",
    "inventory",
    expect.objectContaining({ state: "active", quantity: null }),
    "token",
  );
});
it("removes never-used tracking only after explicit confirmation", async () => {
  vi.mocked(api.inventoryList).mockResolvedValue([inventory]);
  wrap(<StoredMaterialSection harvest={harvest} />);
  await userEvent.click(
    await screen.findByRole("button", { name: "Remove tracking" }),
  );
  const dialog = screen.getByRole("dialog", {
    name: "Remove inventory tracking",
  });
  await userEvent.click(
    within(dialog).getByRole("button", { name: "Remove tracking" }),
  );
  expect(api.removeInventory).toHaveBeenCalledWith("inventory", "token");
});
it("directory defaults to active and retained depleted state remains reachable", async () => {
  vi.mocked(api.inventoryList).mockResolvedValue([
    inventory,
    { ...inventory, id: "depleted", state: "depleted", quantity: null },
  ]);
  wrap(<StoredMaterialDirectory />);
  expect(await screen.findByText("1 tracked material line")).toBeVisible();
  expect(
    screen.getByRole("link", { name: /Open source Harvest/ }),
  ).toHaveAttribute("href", "#/harvests/harvest");
  await userEvent.selectOptions(screen.getByLabelText("State"), "depleted");
  expect(screen.getByText(/Depleted · no material held/)).toBeVisible();
  expect(api.dispositionHistory).not.toHaveBeenCalled();
});
it("shows domain conflict, preserves entered data, and focuses the validation message", async () => {
  vi.mocked(api.recordDisposition).mockRejectedValue(
    new ApiError(409, null, {
      detail: {
        code: "inventory_quantity_exceeded",
        message: "Partial usage must be smaller than the exact balance",
      },
    }),
  );
  wrap(
    <InventoryDialog
      item={item}
      inventory={inventory}
      disposition
      onClose={vi.fn()}
      onSaved={vi.fn()}
    />,
  );
  await userEvent.type(screen.getByLabelText("Amount used amount"), "11");
  await userEvent.click(
    screen.getByRole("button", { name: "Record disposition" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Partial usage must be smaller",
  );
  expect(screen.getByLabelText("Amount used amount")).toHaveValue("11");
  await waitFor(() => {
    expect(screen.getByRole("alert")).toHaveFocus();
  });
});

it("filters stored material by exact source identity with state, material, Location and text", async () => {
  const stored: Inventory = {
    ...inventory,
    location: { id: "storage", display_path: "Fridge → Long seed drawer" },
  };
  const other: Inventory = {
    ...stored,
    id: "other-inventory",
    harvest_id: "other-harvest",
    harvest_title: "Coffea arabica misleading title",
    source: {
      ...source,
      type: "plant_group",
      botanical_identity: { id: "other", display_label: "Acer palmatum" },
    },
  };
  vi.mocked(api.inventoryList).mockResolvedValue([
    stored,
    other,
    { ...stored, id: "depleted", state: "depleted", quantity: null },
  ]);
  const user = userEvent.setup();
  wrap(<StoredMaterialDirectory />);
  await screen.findByText("2 tracked material lines");
  await user.type(
    screen.getByRole("combobox", { name: "Botanical identity" }),
    "Coffea",
  );
  await user.keyboard("{Enter}");
  expect(
    screen.queryByText("Coffea arabica misleading title"),
  ).not.toBeInTheDocument();
  expect(screen.getByText("1 tracked material line")).toBeVisible();
  await user.selectOptions(screen.getByLabelText("Material"), "fruit");
  expect(
    screen.getByText("No stored material matches these filters."),
  ).toBeVisible();
  await user.selectOptions(screen.getByLabelText("Material"), "seed");
  await user.selectOptions(
    screen.getByLabelText("Storage Location"),
    "storage",
  );
  await user.type(screen.getByLabelText("Search stored material"), "missing");
  expect(
    screen.getByText("No stored material matches these filters."),
  ).toBeVisible();
  await user.clear(screen.getByLabelText("Search stored material"));
  await user.selectOptions(screen.getByLabelText("State"), "");
  expect(screen.getByText("2 tracked material lines")).toBeVisible();
  await user.click(
    screen.getByRole("button", { name: "Clear botanical identity filter" }),
  );
  expect(screen.getByText("3 tracked material lines")).toBeVisible();
  expect(api.inventoryList).toHaveBeenCalledTimes(1);
});
