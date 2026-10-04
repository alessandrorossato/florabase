import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../auth/context";
import { ApiError } from "../auth/api";
import { HarvestScreen } from "./HarvestScreen";
import { HarvestForm } from "./HarvestForm";
import type { Harvest } from "./api";
import * as api from "./api";
vi.mock("./api", async (original) => ({
  ...(await original<typeof import("./api")>()),
  listHarvests: vi.fn(),
  getHarvest: vi.fn(),
  saveHarvest: vi.fn(),
  deleteHarvest: vi.fn(),
}));
vi.mock("./inventoryApi", async (original) => ({
  ...(await original<typeof import("./inventoryApi")>()),
  inventoryList: vi.fn(() => Promise.resolve([])),
}));
vi.mock("../plants/api", () => ({
  listPlants: vi.fn(() =>
    Promise.resolve([
      {
        id: "plant-1",
        label: "Coffee",
        lifecycle: "dead",
        botanical_identity: {
          id: "identity-1",
          display_label: "Coffea arabica",
        },
      },
    ]),
  ),
  listPlantGroups: vi.fn(() =>
    Promise.resolve([
      {
        id: "group-1",
        label: "Okra Burgundy",
        lifecycle: "active",
        botanical_identity: {
          id: "identity-1",
          display_label: "Abelmoschus esculentus",
        },
      },
    ]),
  ),
}));
vi.mock("../photos/PhotosSection", () => ({
  PhotosSection: ({
    target,
    onPrimaryChanged,
  }: {
    target: string;
    onPrimaryChanged: (photo: unknown) => void;
  }) => (
    <section aria-label="Harvest media">
      <span>{target} media</span>
      <button
        onClick={() => {
          onPrimaryChanged({
            kind: "local",
            photo_id: "photo-1",
            thumbnail_url: "/safe-harvest.jpg",
          });
        }}
      >
        Set primary test image
      </button>
    </section>
  ),
}));
const auth: AuthContextValue = {
  state: {
    status: "authenticated",
    csrfToken: "token",
    session: {
      user_id: "owner-id",
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
const harvest: Harvest = {
  id: "harvest-1",
  plant_id: "plant-1",
  plant_group_id: null,
  label: null,
  display_title: "Coffee — Fruit harvest",
  source: {
    id: "plant-1",
    type: "plant",
    display_name: "Coffee",
    label: "Coffee",
    lifecycle: "dead",
    botanical_identity: { id: "identity-1", display_label: "Coffea arabica" },
    primary_photo: {
      kind: "local",
      photo_id: "source-photo",
      thumbnail_url: "/source.jpg",
    },
  },
  occurred_on: { precision: "month", year: 2026, month: 8 },
  notes: "Picked ripe fruit",
  event_id: "event-1",
  primary_photo: null,
  items: [
    {
      id: "item-1",
      display_order: 0,
      material_kind: "fruit",
      description: null,
      quantity: {
        kind: "item_count",
        value: "12",
        unit: null,
        is_approximate: false,
      },
    },
  ],
  created_at: "2026-08-21T12:00:00Z",
  updated_at: "2026-08-21T12:00:00Z",
};
function wrap(children: React.ReactNode) {
  return render(
    <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>,
  );
}
afterEach(() => {
  cleanup();
});
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.listHarvests).mockResolvedValue([harvest]);
  vi.mocked(api.getHarvest).mockResolvedValue(harvest);
  vi.mocked(api.saveHarvest).mockResolvedValue(harvest);
});
describe("Harvest directory and detail", () => {
  it("shows source, materials and quantity in accessible directory and preview", async () => {
    const user = userEvent.setup();
    wrap(<HarvestScreen />);
    const row = await screen.findByRole("button", {
      name: /Coffee — Fruit harvest/,
    });
    expect(row).toHaveTextContent("12 items");
    await user.click(row);
    const preview = screen.getByRole("complementary", {
      name: "Quick preview",
    });
    expect(
      within(preview).getByRole("link", { name: "Open details" }),
    ).toHaveAttribute("href", "#/harvests/harvest-1");
    expect(within(preview).getByText("Coffee")).toBeVisible();
    await user.selectOptions(screen.getByLabelText("Material"), "leaf");
    expect(screen.getByText("No Harvests match these filters.")).toBeVisible();
    await user.selectOptions(screen.getByLabelText("Material"), "");
    await user.type(screen.getByLabelText("Search Harvests"), "missing");
    expect(screen.getByText("No Harvests match these filters.")).toBeVisible();
  });
  it("renders compact detail, notes, owned Event and shared media/primary updates", async () => {
    const user = userEvent.setup();
    wrap(<HarvestScreen initialId="harvest-1" />);
    expect(
      await screen.findByRole("heading", { name: harvest.display_title }),
    ).toBeVisible();
    expect(
      screen.getByRole("link", { name: /View owned harvest Event/ }),
    ).toHaveAttribute("href", "#/plants/plant-1?tab=events&event=event-1");
    expect(screen.getByText("Picked ripe fruit")).toBeVisible();
    expect(screen.getByRole("img")).toHaveAttribute("src", "/source.jpg");
    await user.click(
      screen.getByRole("button", { name: "Set primary test image" }),
    );
    expect(screen.getByRole("img")).toHaveAttribute("src", "/safe-harvest.jpg");
    await user.click(screen.getByRole("button", { name: "Delete harvest" }));
    expect(
      screen.getByRole("dialog", { name: "Delete harvest" }),
    ).toHaveTextContent("Linked media remain in the Media library");
  });
  it("allows retry after a directory failure", async () => {
    vi.mocked(api.listHarvests).mockRejectedValueOnce(new ApiError(503));
    const user = userEvent.setup();
    wrap(<HarvestScreen />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not load Harvests",
    );
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(
      await screen.findByRole("button", { name: /Coffee — Fruit harvest/ }),
    ).toBeVisible();
  });
});
describe("Atomic Harvest form", () => {
  it("submits preselected inactive Plant with partial date and exact count", async () => {
    const user = userEvent.setup();
    const onSaved = vi.fn();
    wrap(
      <HarvestForm sourceId="plant-1" onClose={vi.fn()} onSaved={onSaved} />,
    );
    await screen.findByRole("combobox", { name: "Harvest source" });
    await user.selectOptions(
      screen.getByLabelText("Quantity type 1"),
      "item_count",
    );
    await user.clear(screen.getByLabelText("Quantity 1"));
    await user.type(screen.getByLabelText("Quantity 1"), "12");
    await user.selectOptions(screen.getByLabelText("Precision"), "month");
    await user.clear(screen.getByLabelText("Year"));
    await user.type(screen.getByLabelText("Year"), "2026");
    await user.clear(screen.getByLabelText("Month"));
    await user.type(screen.getByLabelText("Month"), "8");
    await user.click(screen.getByRole("button", { name: "Save harvest" }));
    await waitFor(() => {
      expect(api.saveHarvest).toHaveBeenCalledWith(
        null,
        expect.objectContaining({
          plant_id: "plant-1",
          plant_group_id: null,
          occurred_on: { precision: "month", year: 2026, month: 8 },
          items: [
            expect.objectContaining({
              material_kind: "fruit",
              quantity: {
                kind: "item_count",
                value: "12",
                unit: null,
                is_approximate: false,
              },
            }),
          ],
        }),
        "token",
      );
    });
    expect(onSaved).toHaveBeenCalledWith(harvest);
  });
  it("adds keyboard material lines, approximate weight, unknown quantity and focus after removal", async () => {
    const user = userEvent.setup();
    wrap(
      <HarvestForm
        sourceType="plant_group"
        sourceId="group-1"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );
    await screen.findByRole("combobox", { name: "Harvest source" });
    screen.getByRole("button", { name: "Add material line" }).focus();
    await user.keyboard("{Enter}");
    await waitFor(() => {
      expect(screen.getByLabelText("Material 2")).toHaveFocus();
    });
    await user.selectOptions(screen.getByLabelText("Material 2"), "seed");
    await user.selectOptions(
      screen.getByLabelText("Quantity type 2"),
      "weight",
    );
    await user.clear(screen.getByLabelText("Quantity 2"));
    await user.type(screen.getByLabelText("Quantity 2"), "0.0000000001");
    expect(screen.getByLabelText("Quantity 2")).toBeValid();
    await user.selectOptions(screen.getByLabelText("Weight unit 2"), "kg");
    await user.selectOptions(
      screen.getByLabelText("Quantity precision 2"),
      "approximate",
    );
    await user.click(screen.getByRole("button", { name: "Save harvest" }));
    await waitFor(() => {
      expect(api.saveHarvest).toHaveBeenCalledWith(
        null,
        expect.objectContaining({
          plant_id: null,
          plant_group_id: "group-1",
          occurred_on: null,
          items: [
            expect.objectContaining({ quantity: null }),
            expect.objectContaining({
              material_kind: "seed",
              quantity: {
                kind: "weight",
                value: "1e-10",
                unit: "kg",
                is_approximate: true,
              },
            }),
          ],
        }),
        "token",
      );
    });
    await user.click(
      screen.getByRole("button", { name: "Remove material line 1" }),
    );
    await waitFor(() => {
      expect(screen.getByLabelText("Material 1")).toHaveFocus();
    });
    expect(
      screen.getByRole("button", { name: "Remove material line 1" }),
    ).toBeDisabled();
  });
  it("edits source type while retaining item UUID and identifies row errors", async () => {
    vi.mocked(api.saveHarvest).mockRejectedValue(
      new ApiError(422, null, {
        detail: [
          {
            loc: ["body", "items", 0, "quantity"],
            msg: "Quantity must be positive",
          },
        ],
      }),
    );
    const user = userEvent.setup();
    wrap(<HarvestForm harvest={harvest} onClose={vi.fn()} onSaved={vi.fn()} />);
    await screen.findByRole("combobox", { name: "Harvest source" });
    await user.selectOptions(
      screen.getByLabelText("Source type"),
      "plant_group",
    );
    const picker = await screen.findByRole("combobox", {
      name: "Harvest source",
    });
    await user.click(picker);
    await user.click(
      await screen.findByRole("button", { name: /Okra Burgundy/ }),
    );
    await user.click(screen.getByRole("button", { name: "Save harvest" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Material line 1: Quantity must be positive",
    );
    expect(api.saveHarvest).toHaveBeenCalledWith(
      "harvest-1",
      expect.objectContaining({
        plant_group_id: "group-1",
        items: [expect.objectContaining({ id: "item-1" })],
      }),
      "token",
    );
  });
  it("requires a selected source rather than accepting typed search text", async () => {
    wrap(<HarvestForm onClose={vi.fn()} onSaved={vi.fn()} />);
    await screen.findByRole("combobox", { name: "Harvest source" });
    fireEvent.submit(
      screen.getByRole("button", { name: "Save harvest" }).closest("form") ??
        document.createElement("form"),
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Choose a source");
    expect(api.saveHarvest).not.toHaveBeenCalled();
  });
});

it("filters exact source identity across Plants and groups and composes search/material/source", async () => {
  const group: Harvest = {
    ...harvest,
    id: "group-harvest",
    display_title: "Group collection",
    source: { ...harvest.source, id: "group", type: "plant_group" },
    items: [{ ...harvest.items[0], material_kind: "seed" }],
  };
  const other: Harvest = {
    ...harvest,
    id: "other-harvest",
    display_title: "Coffea arabica misleading title",
    source: {
      ...harvest.source,
      botanical_identity: { id: "identity-2", display_label: "Acer palmatum" },
    },
  };
  const rows = [harvest, group, other];
  vi.mocked(api.listHarvests).mockImplementation((_signal, identity) =>
    Promise.resolve(
      rows.filter(
        (row) => !identity || row.source.botanical_identity.id === identity,
      ),
    ),
  );
  const user = userEvent.setup();
  wrap(<HarvestScreen />);
  await screen.findByRole("button", { name: /misleading title/ });
  const picker = screen.getByRole("combobox", { name: "Botanical identity" });
  expect(picker).toHaveAttribute("placeholder", "All botanical identities");
  await user.type(picker, "Coffea");
  await user.keyboard("{Enter}");
  await waitFor(() => {
    expect(api.listHarvests).toHaveBeenLastCalledWith(
      expect.any(AbortSignal),
      "identity-1",
    );
  });
  expect(
    screen.queryByRole("button", { name: /misleading title/ }),
  ).not.toBeInTheDocument();
  expect(screen.getByText("2 harvests")).toBeVisible();
  await user.selectOptions(screen.getByLabelText("Material"), "seed");
  expect(screen.getByText("1 harvest")).toBeVisible();
  await user.selectOptions(screen.getByLabelText("Source type"), "plant");
  expect(screen.getByText("No Harvests match these filters.")).toBeVisible();
  await user.selectOptions(screen.getByLabelText("Source type"), "plant_group");
  await user.type(screen.getByLabelText("Search Harvests"), "missing");
  expect(screen.getByText("No Harvests match these filters.")).toBeVisible();
  await user.clear(screen.getByLabelText("Search Harvests"));
  expect(screen.getByText("1 harvest")).toBeVisible();
  await user.click(
    screen.getByRole("button", { name: "Clear botanical identity filter" }),
  );
  const cleared = screen.getByRole("combobox", { name: "Botanical identity" });
  expect(cleared).toHaveValue("");
  expect(cleared).toHaveFocus();
  await user.keyboard("{Escape}");
  await user.selectOptions(screen.getByLabelText("Material"), "");
  await user.selectOptions(screen.getByLabelText("Source type"), "");
  await screen.findByRole("button", { name: /misleading title/ });
});

it("distinguishes an empty collection from an empty identity result and retains choices", async () => {
  vi.mocked(api.listHarvests)
    .mockResolvedValueOnce([harvest])
    .mockResolvedValue([]);
  const user = userEvent.setup();
  const view = wrap(<HarvestScreen />);
  await screen.findByRole("button", { name: /Coffee — Fruit harvest/ });
  await user.type(
    screen.getByRole("combobox", { name: "Botanical identity" }),
    "Coffea",
  );
  await user.keyboard("{Enter}");
  expect(
    await screen.findByText("No Harvests match these filters."),
  ).toBeVisible();
  view.unmount();
  wrap(<HarvestScreen />);
  expect(await screen.findByText(/No Harvests recorded yet/)).toBeVisible();
});
