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
import { entryLabels, eventLabels, filteredEvents } from "../events/eventData";
import { EventJournal } from "../events/EventJournal";
import * as eventApi from "../events/api";
import { LocationScreen } from "../locations/LocationScreen";
import * as locationApi from "../locations/api";
import { readDirectoryState, savedViewHash } from "../saved-views/state";
import { acquireTestAuth } from "../test/auth";
import { BulkCheckbox, BulkSelect, BulkToolbar } from "./BulkLocation";
import { BulkCareDialog } from "./BulkCare";
import * as careApi from "./careApi";
import { formatBulkCareSummary } from "./careApi";
import { useBulkSelection, type BulkChoice } from "./useBulkSelection";

vi.mock("./careApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./careApi")>();
  return {
    ...actual,
    previewBulkCare: vi.fn(),
    applyBulkCare: vi.fn(),
    undoBulkCare: vi.fn(),
  };
});

vi.mock("../locations/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../locations/api")>();
  return {
    ...actual,
    listLocations: vi.fn(),
  };
});

vi.mock("../events/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../events/api")>();
  return {
    ...actual,
    listEvents: vi.fn(),
    createEvent: vi.fn(),
  };
});

let authValue: AuthContextValue;

function SelectionHarness({ choices }: { choices: BulkChoice[] }) {
  const selection = useBulkSelection("plants", choices);
  return (
    <AuthContext.Provider value={authValue}>
      <BulkSelect selection={selection} visible={choices} />
      <BulkToolbar
        selection={selection}
        visible={choices}
        onSuccess={() => undefined}
      />
      {choices.map((choice) => (
        <BulkCheckbox key={choice.id} selection={selection} choice={choice} />
      ))}
    </AuthContext.Provider>
  );
}

afterEach(cleanup);

beforeEach(async () => {
  vi.clearAllMocks();
  authValue = (await acquireTestAuth({ csrfToken: "csrf" })).auth;
  window.history.replaceState(null, "", "#/plants");
});

test("BulkToolbar shows Log care only when every selected item is a Plant or PlantGroup", async () => {
  const user = userEvent.setup();
  const mixedChoices: BulkChoice[] = [
    { kind: "plant", id: "p-1", label: "Hoya 1", eligible: true },
    { kind: "plant_group", id: "g-1", label: "Tray 1", eligible: true },
    { kind: "seed_lot", id: "s-1", label: "Seed lot 1", eligible: true },
  ];
  render(<SelectionHarness choices={mixedChoices} />);
  await user.click(screen.getByRole("button", { name: "Select records" }));

  // Select 1 plant + 1 plant group -> Log care is visible.
  await user.click(screen.getByRole("checkbox", { name: "Select Hoya 1" }));
  await user.click(screen.getByRole("checkbox", { name: "Select Tray 1" }));
  await user.click(screen.getByRole("button", { name: "Bulk actions" }));
  expect(screen.getByRole("button", { name: "Log care…" })).toBeVisible();

  // Add a seed lot -> Log care disappears.
  await user.click(screen.getByRole("button", { name: "Bulk actions" }));
  await user.click(screen.getByRole("checkbox", { name: "Select Seed lot 1" }));
  await user.click(screen.getByRole("button", { name: "Bulk actions" }));
  expect(
    screen.queryByRole("button", { name: "Log care…" }),
  ).not.toBeInTheDocument();
});

test("selection bulk care flow previews, logs, and undoes (with partial edit kept)", async () => {
  const user = userEvent.setup();
  vi.mocked(careApi.previewBulkCare).mockResolvedValue({
    kind: "watering",
    occurred_on: { precision: "day", year: 2026, month: 11, day: 25 },
    notes: "Rainwater",
    location_label: null,
    sublocation_count: 0,
    total_count: 4,
    log_count: 4,
    plant_count: 3,
    plant_group_count: 1,
    skipped_count: 0,
    can_apply: true,
    target_signature: "a".repeat(64),
    rows: [],
  });
  vi.mocked(careApi.applyBulkCare).mockResolvedValue({
    batch_id: "batch-123",
    kind: "watering",
    logged_count: 4,
    plant_count: 3,
    plant_group_count: 1,
    skipped_count: 0,
  });
  vi.mocked(careApi.undoBulkCare).mockResolvedValue({
    batch_id: "batch-123",
    deleted_count: 3,
    kept_count: 1,
    kept: [
      {
        id: "ev-1",
        target_kind: "plant",
        target_id: "p-1",
        label: "Hoya 1 · Hoya carnosa",
        reason: "Edited after batch creation",
      },
    ],
  });

  const choices: BulkChoice[] = [
    { kind: "plant", id: "p-1", label: "Hoya 1", eligible: true },
    { kind: "plant", id: "p-2", label: "Hoya 2", eligible: true },
    { kind: "plant", id: "p-3", label: "Hoya 3", eligible: true },
    { kind: "plant_group", id: "g-1", label: "Tray 1", eligible: true },
  ];
  render(<SelectionHarness choices={choices} />);
  await user.click(screen.getByRole("button", { name: "Select records" }));
  await user.click(screen.getByRole("button", { name: "Select visible" }));
  await user.click(screen.getByRole("button", { name: "Bulk actions" }));
  await user.click(screen.getByRole("button", { name: "Log care…" }));

  const dialog = screen.getByRole("dialog", {
    name: "Log care for 4 selected records",
  });
  await user.type(within(dialog).getByLabelText("Notes"), "Rainwater");
  await user.click(
    within(dialog).getByRole("button", { name: "Preview care log" }),
  );

  expect(
    await within(dialog).findByText(
      "Watering on 4 records (3 plants, 1 group)",
    ),
  ).toBeVisible();
  await user.click(within(dialog).getByRole("button", { name: "Log for 4" }));

  const status = await screen.findByText("Logged Watering for 4 records.");
  expect(status).toBeVisible();

  await user.click(screen.getByRole("button", { name: "Undo" }));
  expect(
    await screen.findByText(
      /Undone: 3 entries removed · 1 edited entry kept\./,
    ),
  ).toBeVisible();
  expect(
    screen.getByText("Hoya 1 · Hoya carnosa — Edited after batch creation"),
  ).toBeVisible();
});

test("location bulk care dialog handles sub-locations, empty scope, and stale preview", async () => {
  const user = userEvent.setup();
  vi.mocked(careApi.previewBulkCare)
    .mockResolvedValueOnce({
      kind: "feeding",
      occurred_on: { precision: "day", year: 2026, month: 11, day: 25 },
      notes: null,
      location_label: "Greenhouse → Bench 2",
      sublocation_count: 2,
      total_count: 3,
      log_count: 2,
      plant_count: 1,
      plant_group_count: 1,
      skipped_count: 1,
      can_apply: true,
      target_signature: "b".repeat(64),
      rows: [
        {
          kind: "plant",
          id: "p-dead",
          label: "Dead cactus · Mammillaria",
          status: "skipped",
          reason: "Inactive (dead)",
        },
      ],
    })
    .mockResolvedValueOnce({
      kind: "feeding",
      occurred_on: { precision: "day", year: 2026, month: 11, day: 25 },
      notes: null,
      location_label: "Greenhouse → Bench 2",
      sublocation_count: 0,
      total_count: 0,
      log_count: 0,
      plant_count: 0,
      plant_group_count: 0,
      skipped_count: 0,
      can_apply: false,
      target_signature: "c".repeat(64),
      rows: [],
    });

  vi.mocked(careApi.applyBulkCare).mockRejectedValueOnce(
    new ApiError(409, null, {
      detail: {
        code: "stale_preview",
        message: "Records changed since preview; preview again.",
      },
    }),
  );

  render(
    <AuthContext.Provider value={authValue}>
      <BulkCareDialog
        targets={{
          mode: "location",
          locationId: "loc-1",
          locationLabel: "Greenhouse → Bench 2",
        }}
        onClose={() => undefined}
        onSuccess={() => undefined}
      />
    </AuthContext.Provider>,
  );

  const subCheckbox = screen.getByRole("checkbox", {
    name: "Include sub-locations",
  });
  expect(subCheckbox).toBeChecked();
  await user.selectOptions(screen.getByLabelText("Care type"), "feeding");
  await user.click(screen.getByRole("button", { name: "Preview care log" }));

  expect(
    await screen.findByText(
      "Feeding on 2 records (1 plant, 1 group) in Greenhouse → Bench 2 and 2 sub-locations",
    ),
  ).toBeVisible();
  expect(screen.getByText("1 skipped record")).toBeVisible();

  // Trigger 409 stale_preview -> displays alert and Refresh preview button.
  await user.click(screen.getByRole("button", { name: "Log for 2" }));
  expect(
    await screen.findByText("Records changed since preview; preview again."),
  ).toBeVisible();
  expect(screen.getByRole("button", { name: "Refresh preview" })).toBeVisible();

  // Unchecking sub-locations and re-previewing empty location disables apply.
  await user.click(subCheckbox);
  await user.click(screen.getByRole("button", { name: "Preview care log" }));
  expect(await screen.findByText(/Nothing to log/)).toBeVisible();
  expect(screen.getByRole("button", { name: "Log for 0" })).toBeDisabled();
});

test("LocationScreen detail launches Log care for everything here", async () => {
  const user = userEvent.setup();
  const emptyCount = { active: 0, total: 0 };
  const usage = {
    plants: { active: 2, total: 2 },
    plant_groups: emptyCount,
    sowings: emptyCount,
    seed_lots: emptyCount,
    harvest_inventory: emptyCount,
    vegetative_lots: emptyCount,
    propagation_attempts: emptyCount,
  };
  vi.mocked(locationApi.listLocations).mockResolvedValue([
    {
      id: "loc-bench",
      name: "Bench 2",
      parent_id: null,
      usage_scopes: ["plants"],
      usage: {
        plants: { active: 2, total: 2 },
        sowings: emptyCount,
        seed_lots: emptyCount,
        harvest_inventory: emptyCount,
        vegetative_lots: emptyCount,
        propagation_attempts: emptyCount,
      },
      direct_usage: usage,
      usage_including_descendants: usage,
      display_path: "Bench 2",
      retired_at: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ]);

  render(
    <AuthContext.Provider value={authValue}>
      <LocationScreen initialId="loc-bench" />
    </AuthContext.Provider>,
  );

  const launcher = await screen.findByRole("button", {
    name: "Log care for everything here…",
  });
  await user.click(launcher);
  expect(
    await screen.findByRole("dialog", { name: "Log care in Bench 2" }),
  ).toBeVisible();
});

test("single EventJournal supports Watering and Feeding and filters under Care (FN-03)", async () => {
  const user = userEvent.setup();
  vi.mocked(eventApi.listEvents).mockResolvedValue([
    {
      id: "ev-water",
      target: {
        type: "plant",
        id: "p-1",
        label: "Hoya 1",
        lifecycle: "active",
        botanical_identity: {
          id: "id-1",
          display_label: "Hoya carnosa",
        },
      },
      kind: "watering",
      occurred_on: { precision: "day", year: 2026, month: 11, day: 25 },
      notes: "Morning soak",
      destination_location_id: null,
      destination_location: null,
      recipient: null,
      resulting_plant_id: null,
      resulting_plant: null,
      measurement_corrections: [],
      created_at: "2026-11-25T08:00:00Z",
      updated_at: "2026-11-25T08:00:00Z",
    },
  ]);

  // Verify eventData labels and Care filter group.
  expect(entryLabels.care).toBe("Care");
  expect(eventLabels.watering).toBe("Watering");
  expect(eventLabels.feeding).toBe("Feeding");
  expect(
    filteredEvents(
      [
        {
          id: "1",
          kind: "watering",
        } as unknown as eventApi.EventResponse,
        {
          id: "2",
          kind: "feeding",
        } as unknown as eventApi.EventResponse,
        {
          id: "3",
          kind: "repotting",
        } as unknown as eventApi.EventResponse,
      ],
      "care",
    ).map((e) => e.kind),
  ).toEqual(["watering", "feeding"]);

  // Verify EventJournal shows Care filter and Watering/Feeding in Entry type picker.
  render(
    <AuthContext.Provider value={authValue}>
      <EventJournal
        targetKind="plant"
        targetId="p-1"
        targetLabel="Hoya 1"
        locations={[]}
        onTargetRefresh={() => Promise.resolve()}
      />
    </AuthContext.Provider>,
  );

  await waitFor(() => {
    expect(screen.getByText("Morning soak")).toBeVisible();
  });
  await user.click(screen.getByRole("button", { name: "Care" }));
  expect(screen.getByText("Morning soak")).toBeVisible();

  await user.click(screen.getByRole("button", { name: "Add entry" }));
  const select = screen.getByLabelText("Entry type");
  expect(within(select).getByRole("option", { name: "Watering" })).toBeTruthy();
  expect(within(select).getByRole("option", { name: "Feeding" })).toBeTruthy();

  // Verify formatBulkCareSummary helper directly.
  expect(
    formatBulkCareSummary({
      kind: "watering",
      occurred_on: null,
      notes: null,
      location_label: "Greenhouse → Bench 2",
      sublocation_count: 1,
      total_count: 1,
      log_count: 1,
      plant_count: 1,
      plant_group_count: 0,
      skipped_count: 0,
      can_apply: true,
      target_signature: "d".repeat(64),
      rows: [],
    }),
  ).toBe(
    "Watering on 1 record (1 plant) in Greenhouse → Bench 2 and 1 sub-location",
  );
});

test("events Saved Views accept care category and keep existing three categories unchanged", () => {
  expect(savedViewHash("events", 1, { category: ["care"] })).toBe(
    "#/events?category=care",
  );
  expect(readDirectoryState("events", "#/events?category=care")).toEqual({
    q: "",
    category: ["care"],
  });
  expect(
    savedViewHash("events", 1, {
      category: ["observations", "cultivation", "status"],
    }),
  ).toBe("#/events?category=observations&category=cultivation&category=status");
  expect(
    readDirectoryState(
      "events",
      "#/events?category=observations&category=cultivation&category=status",
    ),
  ).toEqual({
    q: "",
    category: ["observations", "cultivation", "status"],
  });
  expect(
    savedViewHash("events", 1, {
      category: ["status", "care", "observations", "cultivation"],
    }),
  ).toBe(
    "#/events?category=care&category=observations&category=cultivation&category=status",
  );
});
