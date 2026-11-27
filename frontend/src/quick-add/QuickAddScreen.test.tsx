import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { ApiError } from "../auth/api";
import { AuthContext, type AuthContextValue } from "../auth/context";
import {
  listBotanicalIdentities,
  type BotanicalIdentityResponse,
} from "../botanical-identities/api";
import { listLocations, type LocationResponse } from "../locations/api";
import { localDay } from "../schedule/calendar";
import { listSuppliers } from "../suppliers/api";
import { searchNames, type Candidate } from "../taxonomy/api";
import { acquireTestAuth } from "../test/auth";
import { quickAddPlant } from "./api";
import { QuickAddScreen } from "./QuickAddScreen";

vi.mock("../botanical-identities/api", () => ({
  listBotanicalIdentities: vi.fn(),
}));
vi.mock("../locations/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../locations/api")>()),
  listLocations: vi.fn(),
}));
vi.mock("../suppliers/api", () => ({ listSuppliers: vi.fn() }));
vi.mock("../taxonomy/api", () => ({ searchNames: vi.fn() }));
vi.mock("./api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./api")>()),
  quickAddPlant: vi.fn(),
}));

let auth: AuthContextValue;
const basil = {
  id: "basil",
  scientific_name: "Ocimum basilicum",
  display_label: "Ocimum basilicum",
  common_name: "Basil",
} as BotanicalIdentityResponse;
const taxon = (id: string, name: string, status = "accepted") =>
  ({
    taxon: {
      source_taxon_id: id,
      parent_source_taxon_id: null,
      scientific_name: name,
      authorship: "Schltr.",
      rank: "species",
      taxonomic_status: status,
      accepted_source_taxon_id: null,
    },
    classification: [
      {
        source_taxon_id: "wfo-7000000001",
        parent_source_taxon_id: null,
        scientific_name: "Apocynaceae",
        authorship: "",
        rank: "family",
        taxonomic_status: "accepted",
        accepted_source_taxon_id: null,
      },
    ],
  }) as Candidate;
const [year, month, day] = localDay().split("-").map(Number);

beforeEach(async () => {
  auth = (await acquireTestAuth({ csrfToken: "csrf" })).auth;
  window.location.hash = "#/quick-add";
  vi.mocked(listBotanicalIdentities).mockResolvedValue([basil]);
  vi.mocked(listLocations).mockResolvedValue([
    {
      id: "bench",
      display_path: "Greenhouse → Bench",
      retired_at: null,
      usage_scopes: ["plants"],
    } as LocationResponse,
  ]);
  vi.mocked(listSuppliers).mockResolvedValue([
    { id: "nursery", name: "Hoya nursery" } as Awaited<
      ReturnType<typeof listSuppliers>
    >[number],
  ]);
  vi.mocked(searchNames).mockResolvedValue([
    taxon("wfo-0000000001", "Hoya kerrii"),
    taxon("wfo-0000000002", "Hoya kerrii var. variegata", "synonym"),
  ]);
  vi.mocked(quickAddPlant).mockResolvedValue({
    record_kind: "plant",
    record_id: "plant-1",
    identity_id: "new-identity",
    identity_display_label: "Hoya kerrii",
    identity_created: true,
    wfo_linked: true,
  });
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function renderScreen() {
  render(
    <AuthContext.Provider value={auth}>
      <QuickAddScreen />
    </AuthContext.Provider>,
  );
}

test("a picked WFO name creates the identity, its link and the plant in one request", async () => {
  renderScreen();
  const user = userEvent.setup();
  const name = await screen.findByRole("combobox", { name: /Scientific name/ });
  await user.type(name, "Hoya k");
  const option = await screen.findByRole("option", {
    name: /Hoya kerrii Schltr\./,
  });
  expect(option).toHaveTextContent("WFO · accepted · Apocynaceae");
  await user.click(option);
  expect(name).toHaveValue("Hoya kerrii");
  expect(
    screen.getByText(/New identity linked to WFO Hoya kerrii/),
  ).toBeVisible();
  await user.click(screen.getByRole("combobox", { name: "Supplier" }));
  await user.click(await screen.findByRole("button", { name: "Hoya nursery" }));
  expect(screen.getByLabelText("Origin")).toHaveValue("purchased");
  await user.click(screen.getByRole("button", { name: "Add and open" }));
  await waitFor(() => {
    expect(window.location.hash).toBe("#/plants/plant-1");
  });
  expect(quickAddPlant).toHaveBeenCalledWith(
    {
      identity: {
        new: {
          scientific_name: "Hoya kerrii",
          cultivar_name: null,
          common_name: null,
          wfo: { source_taxon_id: "wfo-0000000001" },
        },
      },
      material: "plant",
      quantity: null,
      label: null,
      location_id: null,
      supplier_id: "nursery",
      direct_origin_kind: "purchased",
      collection_entry_date: { precision: "day", year, month, day },
      notes: null,
    },
    "csrf",
    auth.capability,
  );
});

test("an existing identity is reused and editing the name drops a WFO pick", async () => {
  renderScreen();
  const user = userEvent.setup();
  const name = await screen.findByRole("combobox", { name: /Scientific name/ });
  await user.type(name, "basil");
  await user.click(
    await screen.findByRole("option", { name: /In your collection/ }),
  );
  expect(
    screen.getByText("Uses your identity Ocimum basilicum."),
  ).toBeVisible();
  expect(screen.queryByLabelText("Cultivar")).not.toBeInTheDocument();
  await user.type(name, "x");
  expect(screen.getByText(/saved as typed, without a WFO link/)).toBeVisible();
  await user.clear(name);
  await user.type(name, "Ocimum");
  await user.keyboard("{ArrowDown}{Enter}");
  await user.click(screen.getByRole("radio", { name: "A group of plants" }));
  await user.click(screen.getByRole("button", { name: "Add and add another" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Enter how many plants the group holds",
  );
  expect(quickAddPlant).not.toHaveBeenCalled();
  await user.type(screen.getByLabelText(/How many/), "12");
  await user.click(screen.getByLabelText("Approximate count"));
  await user.click(screen.getByRole("combobox", { name: "Location" }));
  await user.click(
    await screen.findByRole("button", { name: "Greenhouse → Bench" }),
  );
  vi.mocked(quickAddPlant).mockResolvedValueOnce({
    record_kind: "plant_group",
    record_id: "group-1",
    identity_id: "basil",
    identity_display_label: "Ocimum basilicum",
    identity_created: false,
    wfo_linked: false,
  });
  await user.click(screen.getByRole("button", { name: "Add and add another" }));
  const status = await screen.findByText(/Added plant group of/);
  expect(
    within(status).getByRole("link", { name: "Ocimum basilicum" }),
  ).toHaveAttribute("href", "#/plant-groups/group-1");
  expect(vi.mocked(quickAddPlant).mock.calls[0]?.[0]).toMatchObject({
    identity: { existing_id: "basil" },
    material: "plant_group",
    quantity: { value: 12, is_approximate: true },
    location_id: "bench",
  });
  // Add another keeps the place and clears the name for the next plant.
  expect(name).toHaveValue("");
  expect(name).toHaveFocus();
  expect(window.location.hash).toBe("#/quick-add");
});

test("free text without suggestions and a server refusal keep the form", async () => {
  vi.mocked(searchNames).mockRejectedValue(new Error("offline"));
  vi.mocked(quickAddPlant).mockRejectedValue(
    new ApiError(422, null, {
      detail: {
        code: "wfo_name_mismatch",
        message:
          "The scientific name no longer matches the WFO name you picked. Pick it again.",
      },
    }),
  );
  renderScreen();
  const user = userEvent.setup();
  const name = await screen.findByRole("combobox", { name: /Scientific name/ });
  await user.type(name, "Mystery plant");
  expect(
    await screen.findByText(/WFO suggestions are unavailable/),
  ).toBeVisible();
  await user.type(screen.getByLabelText("Cultivar"), "Red");
  await user.click(screen.getByRole("button", { name: "Add and open" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Pick it again.");
  expect(vi.mocked(quickAddPlant).mock.calls[0]?.[0].identity).toEqual({
    new: {
      scientific_name: "Mystery plant",
      cultivar_name: "Red",
      common_name: null,
      wfo: null,
    },
  });
  expect(name).toHaveValue("Mystery plant");
  expect(window.location.hash).toBe("#/quick-add");
});
