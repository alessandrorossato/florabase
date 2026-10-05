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
import { ConversionDialog } from "./ConversionDialog";
import { ConversionHistory } from "./ConversionHistory";
import {
  StoredMaterialDirectory,
  StoredMaterialSection,
} from "./StoredMaterial";
import type { Inventory } from "./inventoryApi";
import type { Harvest } from "./api";
import * as conversionApi from "./conversionApi";
import * as inventoryApi from "./inventoryApi";
vi.mock("./conversionApi", () => ({
  convertSeeds: vi.fn(),
  listConversions: vi.fn(),
  reversalEligibility: vi.fn(),
  reverseConversion: vi.fn(),
}));
vi.mock("./inventoryApi", async (original) => ({
  ...(await original<typeof import("./inventoryApi")>()),
  inventoryList: vi.fn(),
}));
vi.mock("../botanical-identities/api", () => ({
  listBotanicalIdentities: vi.fn(() =>
    Promise.resolve([
      { id: "identity", display_label: "Coffee" },
      { id: "offspring", display_label: "Offspring identity" },
    ]),
  ),
}));
vi.mock("../locations/api", async (original) => ({
  ...(await original<typeof import("../locations/api")>()),
  listLocations: vi.fn(() =>
    Promise.resolve([
      {
        id: "fridge",
        display_path: "Fridge",
        retired_at: null,
        usage_scopes: ["seed_lots", "harvest_inventory"],
      },
      {
        id: "drawer",
        display_path: "Drawer",
        retired_at: null,
        usage_scopes: ["seed_lots"],
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
const source: Harvest["source"] = {
  id: "plant",
  type: "plant",
  label: "Mother plant",
  display_name: "Mother plant",
  lifecycle: "active",
  botanical_identity: { id: "identity", display_label: "Coffee" },
};
const harvest: Harvest = {
  id: "harvest",
  plant_id: "plant",
  plant_group_id: null,
  label: "Seeds collected",
  display_title: "Seeds collected",
  source,
  occurred_on: { precision: "year", year: 2026 },
  notes: null,
  items: [
    {
      id: "item",
      display_order: 0,
      material_kind: "seed",
      description: null,
      quantity: null,
    },
  ],
  event_id: "event",
  created_at: "2026-10-04T00:00:00Z",
  updated_at: "2026-10-04T00:00:00Z",
};
const inventory: Inventory = {
  id: "stock",
  harvest_item_id: "item",
  harvest_id: "harvest",
  harvest_title: "Seeds collected",
  source,
  material_kind: "seed",
  description: null,
  state: "active",
  quantity: {
    kind: "item_count",
    value: "10",
    unit: null,
    is_approximate: false,
  },
  location: { id: "fridge", display_path: "Fridge" },
  has_dispositions: false,
  created_at: harvest.created_at,
  updated_at: harvest.updated_at,
};
const conversion: conversionApi.Conversion = {
  id: "conversion",
  inventory_id: "stock",
  harvest_id: "harvest",
  harvest_item_id: "item",
  disposition_id: "disposition",
  seed_lot_id: "lot",
  seed_lot_label: "Packet",
  status: "applied",
  quantity: {
    kind: "seed_count",
    value: "3",
    unit: null,
    is_approximate: false,
  },
  before: { state: "active", quantity: inventory.quantity },
  after: {
    state: "active",
    quantity: {
      kind: "item_count",
      value: "7",
      unit: null,
      is_approximate: false,
    },
  },
  created_at: harvest.created_at,
  reversed_at: null,
};
function wrap(child: React.ReactNode) {
  return render(
    <AuthContext.Provider value={auth}>{child}</AuthContext.Provider>,
  );
}
beforeEach(() => {
  vi.mocked(inventoryApi.inventoryList).mockResolvedValue([inventory]);
  vi.mocked(conversionApi.convertSeeds).mockResolvedValue(conversion);
  vi.mocked(conversionApi.listConversions).mockResolvedValue([conversion]);
  vi.mocked(conversionApi.reversalEligibility).mockResolvedValue({
    status: "safe",
    reasons: [],
  });
  vi.mocked(conversionApi.reverseConversion).mockResolvedValue({
    ...conversion,
    status: "reversed",
  });
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
it("shows eligibility request failure inside Undo and keeps confirmation disabled", async () => {
  vi.mocked(conversionApi.reversalEligibility).mockRejectedValueOnce(
    new Error("Network unavailable"),
  );
  const user = userEvent.setup();
  wrap(<ConversionHistory kind="seed_lot_id" id="lot" />);
  await user.click(
    await screen.findByRole("button", { name: "Undo Seed lot creation" }),
  );
  const dialog = within(screen.getByRole("dialog"));
  expect(await dialog.findByRole("alert")).toHaveTextContent(
    "Could not check undo eligibility. Close and retry.",
  );
  expect(dialog.getByRole("button", { name: "Confirm undo" })).toBeDisabled();
  expect(dialog.queryByRole("status")).not.toBeInTheDocument();
  expect(conversionApi.reverseConversion).not.toHaveBeenCalled();
});
it("exposes creation only on tracked active seed material", async () => {
  const view = wrap(<StoredMaterialDirectory />);
  expect(
    await screen.findByRole("button", { name: "Create Seed lot" }),
  ).toBeEnabled();
  view.unmount();
  for (const row of [
    { ...inventory, material_kind: "fruit" as const },
    { ...inventory, state: "depleted" as const },
  ]) {
    vi.mocked(inventoryApi.inventoryList).mockResolvedValue([row]);
    const v = wrap(<StoredMaterialDirectory />);
    if (row.state === "depleted")
      await userEvent
        .setup()
        .selectOptions(screen.getByLabelText("State"), "depleted");
    await screen.findByText("1 tracked material line");
    expect(
      screen.queryByRole("button", { name: "Create Seed lot" }),
    ).not.toBeInTheDocument();
    v.unmount();
  }
  vi.mocked(inventoryApi.inventoryList).mockResolvedValue([]);
  wrap(<StoredMaterialSection harvest={harvest} />);
  expect(
    await screen.findByRole("button", { name: "Track stored material" }),
  ).toBeEnabled();
  expect(
    screen.queryByRole("button", { name: "Create Seed lot" }),
  ).not.toBeInTheDocument();
});
it("shows producer, date, identity and Location context and creates an exact partial lot", async () => {
  const user = userEvent.setup();
  const saved = vi.fn();
  wrap(
    <ConversionDialog
      inventory={inventory}
      harvest={harvest}
      onClose={vi.fn()}
      onSaved={saved}
    />,
  );
  expect(
    await screen.findByRole("combobox", { name: "Botanical identity" }),
  ).toHaveValue("Coffee");
  expect(
    screen.getByText(/Producer: Plant · Mother plant/),
  ).toBeInTheDocument();
  expect(screen.getByText(/Harvest date: 2026/)).toBeInTheDocument();
  expect(
    screen.getByRole("combobox", { name: "Seed lot Location" }),
  ).toHaveValue("Fridge");
  await user.type(screen.getByLabelText("Seed lot quantity amount"), "3");
  await user.type(screen.getByLabelText("Seed lot label"), "Packet");
  await user.click(screen.getByRole("button", { name: "Create Seed lot" }));
  await waitFor(() => {
    expect(saved).toHaveBeenCalledWith(conversion);
  });
  expect(conversionApi.convertSeeds).toHaveBeenCalledWith(
    "stock",
    expect.objectContaining({
      mode: "partial",
      botanical_identity_id: "identity",
      location_id: "fridge",
      quantity: {
        kind: "seed_count",
        value: "3",
        unit: null,
        is_approximate: false,
      },
    }),
    "token",
  );
});
it("use all exact stock preserves exact target and depletes the source", async () => {
  const user = userEvent.setup();
  wrap(
    <ConversionDialog
      inventory={inventory}
      harvest={harvest}
      onClose={vi.fn()}
      onSaved={vi.fn()}
    />,
  );
  await screen.findByRole("combobox", { name: "Botanical identity" });
  await user.selectOptions(
    screen.getByLabelText("Material leaving stock"),
    "use_all",
  );
  expect(screen.getByLabelText("Seed lot quantity amount")).toHaveValue("10");
  expect(screen.getByLabelText("Seed lot quantity amount")).toBeDisabled();
  expect(
    screen.getByText(/All remaining source material will be depleted/),
  ).toBeInTheDocument();
});
it("allows explicit identity and target Location choices for a Plant group", async () => {
  const user = userEvent.setup();
  wrap(
    <ConversionDialog
      inventory={{ ...inventory, source: { ...source, type: "plant_group" } }}
      harvest={harvest}
      onClose={vi.fn()}
      onSaved={vi.fn()}
    />,
  );
  const identity = await screen.findByRole("combobox", {
    name: "Botanical identity",
  });
  expect(screen.getByText(/Producer: Plant group/)).toBeInTheDocument();
  await user.clear(identity);
  await user.type(identity, "Offspring");
  await user.click(
    await screen.findByRole("button", {
      name: "Offspring identity",
    }),
  );
  const location = screen.getByRole("combobox", { name: "Seed lot Location" });
  await user.clear(location);
  await user.type(location, "Drawer");
  await user.click(await screen.findByRole("button", { name: "Drawer" }));
  await user.type(screen.getByLabelText("Seed lot quantity amount"), "3");
  await user.click(screen.getByRole("button", { name: "Create Seed lot" }));
  await waitFor(() => {
    expect(conversionApi.convertSeeds).toHaveBeenCalledWith(
      "stock",
      expect.objectContaining({
        botanical_identity_id: "offspring",
        location_id: "drawer",
      }),
      "token",
    );
  });
});
it("requires approximate remainder while an unknown source stays unknown", async () => {
  const approximate = {
    ...inventory,
    quantity: {
      kind: "item_count" as const,
      value: "10",
      unit: null,
      is_approximate: true,
    },
  };
  const v = wrap(
    <ConversionDialog
      inventory={approximate}
      harvest={harvest}
      onClose={vi.fn()}
      onSaved={vi.fn()}
    />,
  );
  await screen.findByRole("combobox", { name: "Botanical identity" });
  expect(
    screen.getByLabelText("Confirmed remaining now precision"),
  ).toHaveValue("approximate");
  v.unmount();
  wrap(
    <ConversionDialog
      inventory={{ ...inventory, quantity: null }}
      harvest={harvest}
      onClose={vi.fn()}
      onSaved={vi.fn()}
    />,
  );
  await screen.findByRole("combobox", { name: "Botanical identity" });
  expect(screen.getByLabelText("Seed lot quantity precision")).toHaveValue(
    "unknown",
  );
  expect(
    screen.getByText(/source remainder stays unknown/),
  ).toBeInTheDocument();
  expect(
    screen.queryByLabelText("Confirmed remaining now precision"),
  ).not.toBeInTheDocument();
});
it("shows source/result cross-links and guarded undo with retained history", async () => {
  const user = userEvent.setup();
  const changed = vi.fn();
  wrap(<ConversionHistory kind="seed_lot_id" id="lot" onChanged={changed} />);
  expect(
    await screen.findByRole("link", { name: /originating Harvest/ }),
  ).toHaveAttribute("href", "#/harvests/harvest");
  expect(screen.getByRole("link", { name: "Packet" })).toHaveAttribute(
    "href",
    "#/seeds/lot",
  );
  await user.click(
    screen.getByRole("button", { name: "Undo Seed lot creation" }),
  );
  const dialog = screen.getByRole("dialog");
  expect(
    within(dialog).getByText(/remain in history as Reversed/),
  ).toBeInTheDocument();
  await waitFor(() => {
    expect(
      within(dialog).getByRole("button", { name: "Confirm undo" }),
    ).toBeEnabled();
  });
  await user.click(
    within(dialog).getByRole("button", { name: "Confirm undo" }),
  );
  await waitFor(() => {
    expect(changed).toHaveBeenCalled();
  });
});
it("explains ineligible undo and server conflicts without permitting confirmation", async () => {
  const user = userEvent.setup();
  vi.mocked(conversionApi.reversalEligibility).mockResolvedValue({
    status: "blocked",
    reasons: ["Source inventory changed after this conversion."],
  });
  wrap(<ConversionHistory kind="seed_lot_id" id="lot" />);
  await user.click(
    await screen.findByRole("button", { name: "Undo Seed lot creation" }),
  );
  expect(
    await screen.findByText("Source inventory changed after this conversion."),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Confirm undo" })).toBeDisabled();
});
it("retains a conversion dialog on conflict and moves focus to the explanation", async () => {
  const user = userEvent.setup();
  vi.mocked(conversionApi.convertSeeds).mockRejectedValue(
    new ApiError(409, null, {
      detail: { message: "Stock changed. Refresh and retry." },
    }),
  );
  wrap(
    <ConversionDialog
      inventory={inventory}
      harvest={harvest}
      onClose={vi.fn()}
      onSaved={vi.fn()}
    />,
  );
  await screen.findByRole("combobox", { name: "Botanical identity" });
  await user.type(screen.getByLabelText("Seed lot quantity amount"), "3");
  await user.click(screen.getByRole("button", { name: "Create Seed lot" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Stock changed. Refresh and retry.",
  );
  expect(screen.getByRole("dialog")).toBeInTheDocument();
});
