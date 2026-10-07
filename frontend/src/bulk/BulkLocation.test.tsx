import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../auth/context";
import { ApiError } from "../auth/api";
import { openDirectoryRoute } from "../components/recordNavigation";
import { listLocations, type LocationResponse } from "../locations/api";
import { BulkCheckbox, BulkSelect, BulkToolbar } from "./BulkLocation";
import { applyLocation, previewLocation, type BulkPreview } from "./api";
import { useBulkSelection, type BulkChoice } from "./useBulkSelection";

vi.mock("../locations/api", () => ({ listLocations: vi.fn() }));
vi.mock("./api", () => ({ applyLocation: vi.fn(), previewLocation: vi.fn() }));
const auth: AuthContextValue = {
  state: {
    status: "authenticated",
    csrfToken: "csrf",
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
const choices: BulkChoice[] = [
  { kind: "plant", id: "plant", label: "Plant · Basil", eligible: true },
  {
    kind: "plant_group",
    id: "group",
    label: "Group · Basil tray",
    eligible: true,
  },
  { kind: "plant", id: "old", label: "Historical Basil", eligible: false },
];
const preview: BulkPreview = {
  target_location_id: "target",
  target_location: "Greenhouse → Bench",
  target_updated_at: "2026-10-06T00:00:00Z",
  selected_count: 2,
  move_count: 1,
  unchanged_count: 1,
  can_apply: true,
  rows: choices.slice(0, 2).map((row, index) => ({
    kind: row.kind,
    id: row.id,
    label: row.label,
    current_location_id: index ? "target" : "terrace",
    current_location: index ? "Greenhouse → Bench" : "Terrace",
    updated_at: "2026-10-06T00:00:00Z",
    status: index ? ("unchanged" as const) : ("move" as const),
    code: null,
    message: null,
  })),
};
const success = vi.fn();
function Harness({
  scope = "plants",
  rows = choices,
}: {
  scope?: string;
  rows?: BulkChoice[];
}) {
  const selection = useBulkSelection(scope, rows);
  return (
    <AuthContext.Provider value={auth}>
      <BulkSelect selection={selection} visible={rows} />
      <BulkToolbar selection={selection} visible={rows} onSuccess={success} />
      {rows.map((row) => (
        <BulkCheckbox
          key={`${row.kind}:${row.id}`}
          selection={selection}
          choice={row}
        />
      ))}
    </AuthContext.Provider>
  );
}
async function openMove() {
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Select" }));
  await user.click(screen.getByRole("button", { name: "Select visible" }));
  await user.click(screen.getByRole("button", { name: "Move to location" }));
  const dialog = screen.getByRole("dialog", { name: "Move to location" });
  await user.click(
    await within(dialog).findByRole("combobox", { name: "Target Location" }),
  );
  await user.click(
    await within(dialog).findByRole("button", {
      name: "Greenhouse → Bench",
    }),
  );
  return { user, dialog };
}
beforeEach(() => {
  window.history.replaceState(null, "", "#/plants");
  vi.mocked(listLocations).mockResolvedValue([
    {
      id: "target",
      display_path: "Greenhouse → Bench",
      retired_at: null,
      usage_scopes: ["plants", "seed_lots", "sowings", "harvest_inventory"],
    } as LocationResponse,
  ]);
  vi.mocked(previewLocation).mockResolvedValue(preview);
  vi.mocked(applyLocation).mockResolvedValue({
    moved_count: 1,
    unchanged_count: 1,
  });
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

test("selection is explicit, counts changes, excludes historical rows and clears/cancels", async () => {
  const user = userEvent.setup();
  render(<Harness />);
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Select" }));
  expect(screen.getByText("0 selected")).toBeVisible();
  const checkbox = screen.getByRole("checkbox", {
    name: "Select Plant · Basil",
  });
  await user.click(checkbox);
  expect(screen.getByText("1 selected")).toBeVisible();
  await user.click(checkbox);
  expect(screen.getByText("0 selected")).toBeVisible();
  expect(
    screen.getByRole("checkbox", { name: "Select Historical Basil" }),
  ).toBeDisabled();
  await user.click(screen.getByRole("button", { name: "Select visible" }));
  expect(screen.getByText("2 selected")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Clear selection" }));
  expect(screen.getByText("0 selected")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Done" }));
  await waitFor(() => {
    expect(screen.getByRole("button", { name: "Select" })).toHaveFocus();
  });
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
});

test("100-record bound never truncates Select visible and allows explicit individual selection", async () => {
  const user = userEvent.setup();
  const rows = Array.from({ length: 101 }, (_, index) => ({
    ...choices[0],
    id: String(index),
    label: `Plant ${String(index)}`,
  }));
  render(<Harness rows={rows} />);
  await user.click(screen.getByRole("button", { name: "Select" }));
  expect(screen.getByRole("button", { name: "Select visible" })).toBeDisabled();
  for (const checkbox of screen.getAllByRole("checkbox").slice(0, 100))
    await user.click(checkbox);
  expect(screen.getByText("100 selected")).toBeVisible();
  expect(
    screen.getByRole("checkbox", { name: "Select Plant 100" }),
  ).toBeDisabled();
  await user.click(screen.getByRole("checkbox", { name: "Select Plant 0" }));
  expect(
    screen.getByRole("checkbox", { name: "Select Plant 100" }),
  ).toBeEnabled();
});

test("filters, visible membership and reopening an identical Saved View reset selection", async () => {
  const user = userEvent.setup();
  const view = render(<Harness />);
  await user.click(screen.getByRole("button", { name: "Select" }));
  await user.click(screen.getByRole("button", { name: "Select visible" }));
  view.rerender(<Harness scope="plants?q=Basil" />);
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Select" }));
  view.rerender(<Harness scope="plants?q=Basil" rows={choices.slice(0, 1)} />);
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Select" }));
  act(() => {
    openDirectoryRoute("#/plants?q=Basil");
  });
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
});

test("typed mixed references survive preview, explicit apply clears selection and reports noops", async () => {
  render(<Harness />);
  const { user, dialog } = await openMove();
  expect(applyLocation).not.toHaveBeenCalled();
  await user.click(
    within(dialog).getByRole("button", { name: "Preview move" }),
  );
  expect(previewLocation).toHaveBeenCalledWith(
    [
      { kind: "plant", id: "plant" },
      { kind: "plant_group", id: "group" },
    ],
    "target",
    "csrf",
    expect.any(AbortSignal),
  );
  expect(
    await within(dialog).findByText(
      "1 will move · 1 already there · 2 selected",
    ),
  ).toBeVisible();
  expect(within(dialog).getByText("Already at this Location")).toBeVisible();
  expect(applyLocation).not.toHaveBeenCalled();
  await user.click(
    within(dialog).getByRole("button", { name: "Apply move (1)" }),
  );
  await waitFor(() => {
    expect(success).toHaveBeenCalledWith({
      moved_count: 1,
      unchanged_count: 1,
    });
  });
  expect(applyLocation).toHaveBeenCalledWith(preview, "csrf");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  expect(screen.getByText("1 moved · 1 already there.")).toBeVisible();
});

test("all-noop and domain conflicts cannot apply", async () => {
  vi.mocked(previewLocation).mockResolvedValue({
    ...preview,
    can_apply: false,
    move_count: 0,
    unchanged_count: 1,
    rows: [
      preview.rows[1],
      {
        ...preview.rows[0],
        status: "conflict",
        code: "record_not_active",
        message: "Only current active records can be moved.",
      },
    ],
  });
  render(<Harness />);
  const { user, dialog } = await openMove();
  await user.click(
    within(dialog).getByRole("button", { name: "Preview move" }),
  );
  expect(
    await within(dialog).findByText(
      "Only current active records can be moved.",
    ),
  ).toBeVisible();
  expect(
    within(dialog).getByRole("button", { name: "Apply move (0)" }),
  ).toBeDisabled();
  expect(applyLocation).not.toHaveBeenCalled();
});

test("stale conflict invalidates the preview, names affected records and requires refresh", async () => {
  vi.mocked(applyLocation).mockRejectedValueOnce(
    new ApiError(409, null, {
      detail: {
        code: "stale_preview",
        message: "No records moved. Preview again.",
        rows: [{ label: "Basil plant" }],
      },
    }),
  );
  render(<Harness />);
  const { user, dialog } = await openMove();
  await user.click(
    within(dialog).getByRole("button", { name: "Preview move" }),
  );
  await user.click(
    await within(dialog).findByRole("button", { name: "Apply move (1)" }),
  );
  expect(await within(dialog).findByRole("alert")).toHaveTextContent(
    "Basil plant — changed since preview",
  );
  expect(
    within(dialog).getByRole("button", { name: "Apply move" }),
  ).toBeDisabled();
  expect(success).not.toHaveBeenCalled();
  await user.click(
    within(dialog).getByRole("button", { name: "Preview move" }),
  );
  expect(
    await within(dialog).findByRole("button", { name: "Apply move (1)" }),
  ).toBeEnabled();
});

test("keyboard focus stays in dialog and Escape returns to Move trigger", async () => {
  render(<Harness />);
  const { user, dialog } = await openMove();
  const cancel = within(dialog).getByRole("button", { name: "Cancel" });
  cancel.focus();
  await user.tab();
  expect(within(dialog).getByRole("combobox")).toHaveFocus();
  await user.tab({ shift: true });
  expect(cancel).toHaveFocus();
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Move to location" }),
  ).toHaveFocus();
  expect(screen.getByText("2 selected")).toBeVisible();
});

test("Location failure can retry without applying and only shared eligible scopes appear", async () => {
  vi.mocked(listLocations).mockRejectedValueOnce(new Error("offline"));
  render(<Harness />);
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Select" }));
  await user.click(screen.getByRole("button", { name: "Select visible" }));
  await user.click(screen.getByRole("button", { name: "Move to location" }));
  await user.click(
    await screen.findByRole("button", { name: "Retry Locations" }),
  );
  await waitFor(() => {
    expect(
      screen.getByRole("combobox", { name: "Target Location" }),
    ).toBeEnabled();
  });
  expect(applyLocation).not.toHaveBeenCalled();
});

test("session protection refusal clears preview and asks for reload", async () => {
  vi.mocked(applyLocation).mockRejectedValue(new ApiError(403));
  render(<Harness />);
  const { user, dialog } = await openMove();
  await user.click(
    within(dialog).getByRole("button", { name: "Preview move" }),
  );
  await user.click(
    await within(dialog).findByRole("button", { name: "Apply move (1)" }),
  );
  expect(await within(dialog).findByRole("alert")).toHaveTextContent(
    "Reload the page before retrying",
  );
  expect(
    within(dialog).getByRole("button", { name: "Apply move" }),
  ).toBeDisabled();
  expect(success).not.toHaveBeenCalled();
});

test("target changes invalidate a successful preview and require a new server preview", async () => {
  vi.mocked(listLocations).mockResolvedValue([
    {
      id: "target",
      display_path: "Greenhouse → Bench",
      retired_at: null,
      usage_scopes: ["plants"],
    },
    {
      id: "second",
      display_path: "Outdoor → Terrace",
      retired_at: null,
      usage_scopes: ["plants"],
    },
  ] as LocationResponse[]);
  render(<Harness />);
  const { user, dialog } = await openMove();
  expect(
    within(dialog).getByRole("button", { name: "Apply move" }),
  ).toBeDisabled();
  await user.click(
    within(dialog).getByRole("button", { name: "Preview move" }),
  );
  expect(
    await within(dialog).findByRole("button", { name: "Apply move (1)" }),
  ).toBeEnabled();
  const chooser = within(dialog).getByRole("combobox", {
    name: "Target Location",
  });
  await user.clear(chooser);
  await user.click(
    await within(dialog).findByRole("button", { name: "Outdoor → Terrace" }),
  );
  expect(
    within(dialog).getByRole("button", { name: "Apply move" }),
  ).toBeDisabled();
  expect(
    within(dialog).queryByRole("region", { name: "Move preview" }),
  ).not.toBeInTheDocument();
  expect(applyLocation).not.toHaveBeenCalled();
  await user.click(
    within(dialog).getByRole("button", { name: "Preview move" }),
  );
  expect(previewLocation).toHaveBeenLastCalledWith(
    expect.any(Array),
    "second",
    "csrf",
    expect.any(AbortSignal),
  );
});

function bounds(dialog: HTMLElement) {
  vi.spyOn(dialog, "getBoundingClientRect").mockReturnValue({
    left: 100,
    top: 100,
    right: 700,
    bottom: 700,
  } as DOMRect);
}

test("only a direct backdrop click dismisses safely and restores the Move trigger", async () => {
  render(<Harness />);
  const { dialog } = await openMove();
  bounds(dialog);
  fireEvent.click(dialog, { clientX: 120, clientY: 120 });
  expect(dialog).toBeInTheDocument();
  fireEvent.click(within(dialog).getByRole("heading"), {
    clientX: 0,
    clientY: 0,
  });
  expect(dialog).toBeInTheDocument();
  fireEvent.click(dialog, { clientX: 10, clientY: 10 });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Move to location" }),
  ).toHaveFocus();
  expect(screen.getByText("2 selected")).toBeVisible();
  expect(applyLocation).not.toHaveBeenCalled();
});

test("backdrop, Escape and Cancel cannot dismiss an Apply in flight", async () => {
  let finish: (() => void) | undefined;
  vi.mocked(applyLocation).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = () => {
          resolve({ moved_count: 1, unchanged_count: 1 });
        };
      }),
  );
  render(<Harness />);
  const { user, dialog } = await openMove();
  bounds(dialog);
  await user.click(
    within(dialog).getByRole("button", { name: "Preview move" }),
  );
  await user.click(
    await within(dialog).findByRole("button", { name: "Apply move (1)" }),
  );
  expect(within(dialog).getByRole("button", { name: "Cancel" })).toBeDisabled();
  fireEvent.click(dialog, { clientX: 10, clientY: 10 });
  await user.keyboard("{Escape}");
  expect(dialog).toBeInTheDocument();
  expect(success).not.toHaveBeenCalled();
  act(() => {
    finish?.();
  });
  await waitFor(() => {
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
  expect(success).toHaveBeenCalledOnce();
});
