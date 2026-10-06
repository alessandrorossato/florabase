import {
  act,
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState, type ReactNode } from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { ApiError } from "../auth/api";
import { AuthContext, type AuthContextValue } from "../auth/context";
import { BotanicalIdentityFilter } from "../harvests/BotanicalIdentityFilter";
import { setRecordRoute } from "../components/recordNavigation";
import { SavedViews } from "./SavedViews";
import * as api from "./api";
import { useDirectoryView } from "./useDirectoryView";

const id = "01900000-0000-7000-8000-000000000001";
const auth: AuthContextValue = {
  state: {
    status: "authenticated",
    session: {
      user_id: id,
      login_name: "owner",
      display_name: null,
      owner: true,
      canonical_origin: "http://localhost",
    },
    csrfToken: "csrf",
  },
  logIn: vi.fn(),
  logOut: vi.fn(),
  sessionExpired: vi.fn(),
  retryRestoration: vi.fn(),
  cancelLogout: vi.fn(),
};
function view(overrides: Partial<api.SavedView> = {}): api.SavedView {
  return {
    id,
    name: "Basil view",
    surface: "seed_lots",
    state_version: 1,
    state: { q: "basil", lifecycle: "history" },
    created_at: "2026-10-06T10:00:00Z",
    updated_at: "2026-10-06T10:00:00Z",
    compatibility: "supported",
    ...overrides,
  };
}
function wrap(content: ReactNode) {
  return render(
    <AuthContext.Provider value={auth}>{content}</AuthContext.Provider>,
  );
}
function Directory() {
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState(false);
  const state = useDirectoryView("seed_lots", () => {
    setPage(0);
    setSelected(false);
  });
  return (
    <>
      <label>
        Search seeds
        <input
          value={state.state.q}
          onChange={(event) => {
            state.update("q", event.currentTarget.value);
          }}
        />
      </label>
      <button
        onClick={() => {
          state.update("lifecycle", "history");
        }}
      >
        History
      </button>
      <button
        onClick={() => {
          state.replace({ q: "", lifecycle: "active" });
        }}
      >
        Clear filters
      </button>
      <button
        onClick={() => {
          setPage(80);
          setSelected(true);
        }}
      >
        Next page and select
      </button>
      <p>
        Offset {page} · {selected ? "Selected" : "No selection"}
      </p>
      <SavedViews surface="seed_lots" state={state.savedState} />
    </>
  );
}
beforeEach(() => {
  window.history.replaceState(null, "", "#/seeds");
  vi.spyOn(api, "listSavedViews").mockResolvedValue([]);
  vi.spyOn(api, "createSavedView").mockResolvedValue(view());
  vi.spyOn(api, "updateSavedView").mockResolvedValue(view());
  vi.spyOn(api, "deleteSavedView").mockResolvedValue(undefined);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("default directory has compact access and only meaningful state allows Save", async () => {
  const user = userEvent.setup();
  wrap(<Directory />);
  expect(
    screen.queryByRole("button", { name: "Save view" }),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Saved views" }));
  expect(await screen.findByText(/No Saved Views yet/)).toBeVisible();
  await user.type(
    screen.getByRole("textbox", { name: "Search seeds" }),
    "basil",
  );
  await user.click(screen.getByRole("button", { name: "Save view" }));
  const dialog = screen.getByRole("dialog", { name: "Save view" });
  expect(within(dialog).getByLabelText("View name")).toHaveFocus();
  await user.click(within(dialog).getByRole("button", { name: "Save view" }));
  expect(await within(dialog).findByRole("alert")).toHaveTextContent(
    "Enter a name",
  );
  await user.type(within(dialog).getByLabelText("View name"), "Basil view");
  vi.mocked(api.listSavedViews).mockResolvedValue([
    view({ state: { q: "basil" } }),
  ]);
  await user.click(within(dialog).getByRole("button", { name: "Save view" }));
  expect(api.createSavedView).toHaveBeenCalledWith(
    {
      name: "Basil view",
      surface: "seed_lots",
      state_version: 1,
      state: { q: "basil" },
    },
    "csrf",
  );
  expect(
    await screen.findByRole("button", { name: "Open Basil view" }),
  ).toBeVisible();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

test("conflict feedback stays in focused dialog and Escape returns focus", async () => {
  const user = userEvent.setup();
  window.history.replaceState(null, "", "#/seeds?q=basil");
  vi.mocked(api.createSavedView).mockRejectedValue(
    new ApiError(409, null, { detail: "conflict" }),
  );
  wrap(<Directory />);
  const trigger = screen.getByRole("button", { name: "Save view" });
  await user.click(trigger);
  const dialog = screen.getByRole("dialog");
  await user.type(within(dialog).getByLabelText("View name"), "Basil view");
  await user.click(within(dialog).getByRole("button", { name: "Save view" }));
  expect(await within(dialog).findByRole("alert")).toHaveTextContent(
    "already exists",
  );
  await user.keyboard("{Escape}");
  expect(trigger).toHaveFocus();
});

test("opening uses normal canonical URL, resets page and selection, refresh/history restore filters", async () => {
  const user = userEvent.setup();
  vi.mocked(api.listSavedViews).mockResolvedValue([view()]);
  const rendered = wrap(<Directory />);
  await user.click(
    screen.getByRole("button", { name: "Next page and select" }),
  );
  await user.click(screen.getByRole("button", { name: "Saved views" }));
  await user.click(
    await screen.findByRole("button", { name: "Open Basil view" }),
  );
  expect(window.location.hash).toBe("#/seeds?q=basil&lifecycle=history");
  expect(screen.getByRole("textbox", { name: "Search seeds" })).toHaveValue(
    "basil",
  );
  expect(screen.getByText("Offset 0 · No selection")).toBeVisible();
  expect(api.updateSavedView).not.toHaveBeenCalled();
  rendered.unmount();
  wrap(<Directory />); // Browser refresh re-enters the ordinary parser.
  expect(screen.getByRole("textbox", { name: "Search seeds" })).toHaveValue(
    "basil",
  );
  act(() => {
    window.history.back();
  });
  await waitFor(() => {
    expect(screen.getByRole("textbox", { name: "Search seeds" })).toHaveValue(
      "",
    );
  });
  act(() => {
    window.history.forward();
  });
  await waitFor(() => {
    expect(screen.getByRole("textbox", { name: "Search seeds" })).toHaveValue(
      "basil",
    );
  });
});

test("manual edits never auto-save; explicit rename and update preserve view identity", async () => {
  const user = userEvent.setup();
  window.history.replaceState(null, "", "#/seeds?q=basil");
  vi.mocked(api.listSavedViews).mockResolvedValue([view()]);
  wrap(<Directory />);
  await user.clear(screen.getByRole("textbox", { name: "Search seeds" }));
  await user.type(
    screen.getByRole("textbox", { name: "Search seeds" }),
    "mint",
  );
  expect(api.updateSavedView).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Saved views" }));
  await user.click(
    await screen.findByRole("button", { name: "Rename Basil view" }),
  );
  let dialog = screen.getByRole("dialog");
  await user.clear(within(dialog).getByLabelText("View name"));
  await user.type(within(dialog).getByLabelText("View name"), "Fresh mint");
  await user.click(
    within(dialog).getByRole("button", { name: "Rename Saved View" }),
  );
  await waitFor(() => {
    expect(api.updateSavedView).toHaveBeenCalledWith(
      id,
      { name: "Fresh mint" },
      "csrf",
    );
  });
  await user.click(
    await screen.findByRole("button", {
      name: "Update Basil view with current view",
    }),
  );
  dialog = screen.getByRole("dialog");
  expect(within(dialog).getByText(/Replace the saved filters/)).toBeVisible();
  await user.click(
    within(dialog).getByRole("button", { name: "Update Saved View" }),
  );
  await waitFor(() => {
    expect(api.updateSavedView).toHaveBeenCalledWith(
      id,
      { state_version: 1, state: { q: "mint" } },
      "csrf",
    );
  });
});

test("delete asks confirmation, removes only the shortcut, and permits future-state management", async () => {
  const user = userEvent.setup();
  vi.mocked(api.listSavedViews).mockResolvedValue([
    view({ state_version: 9, compatibility: "unsupported_version" }),
  ]);
  wrap(<Directory />);
  await user.click(screen.getByRole("button", { name: "Saved views" }));
  await user.click(
    await screen.findByRole("button", { name: "Open Basil view" }),
  );
  expect(await screen.findByRole("status")).toHaveTextContent(
    "unsupported or incompatible",
  );
  expect(window.location.hash).toBe("#/seeds");
  await user.click(screen.getByRole("button", { name: "Delete Basil view" }));
  expect(api.deleteSavedView).not.toHaveBeenCalled();
  const dialog = screen.getByRole("dialog");
  expect(
    within(dialog).getByText(/Collection and reference records are kept/),
  ).toBeVisible();
  vi.mocked(api.listSavedViews).mockResolvedValue([]);
  await user.click(
    within(dialog).getByRole("button", { name: "Delete Saved View" }),
  );
  expect(await screen.findByText(/No Saved Views yet/)).toBeVisible();
  expect(api.deleteSavedView).toHaveBeenCalledWith(id, "csrf");
  expect(
    screen.queryByRole("button", { name: "Open Basil view" }),
  ).not.toBeInTheDocument();
});

test("Dashboard access lists multiple surfaces and opens another ordinary route", async () => {
  const user = userEvent.setup();
  window.history.replaceState(null, "", "#/dashboard");
  vi.mocked(api.listSavedViews).mockResolvedValue([
    view(),
    view({
      id: "other",
      name: "Basil view",
      surface: "media",
      state: { q: "leaf", target: "supplier" },
    }),
  ]);
  wrap(<SavedViews surface="global_search" state={{}} allSurfaces />);
  await user.click(
    screen.getByRole("button", { name: "Saved views · all surfaces" }),
  );
  const panel = await screen.findByRole("region", { name: "All Saved Views" });
  expect(api.listSavedViews).toHaveBeenCalledWith(
    undefined,
    expect.any(AbortSignal),
    0,
  );
  expect(within(panel).getByText("Media Library")).toBeVisible();
  await user.click(
    within(panel).getAllByRole("button", { name: "Open Basil view" })[1],
  );
  expect(window.location.hash).toBe("#/media?q=leaf&target=supplier");
  expect(
    screen.queryByRole("button", { name: /Update.*current view/ }),
  ).not.toBeInTheDocument();
});

test("stale exact identity remains visible and clearable", () => {
  wrap(<BotanicalIdentityFilter choices={[]} value={id} onChange={vi.fn()} />);
  expect(
    screen.getByRole("combobox", { name: "Botanical identity" }),
  ).toHaveValue(`Unavailable botanical identity · ${id}`);
  expect(
    screen.getByRole("button", { name: "Clear botanical identity filter" }),
  ).toBeVisible();
});

test("bounded pages append on request and a failed page retries without skipping rows", async () => {
  const user = userEvent.setup();
  const first = Array.from({ length: 100 }, (_, index) =>
    view({
      id: `01900000-0000-7000-8000-${String(index).padStart(12, "0")}`,
      name: `View ${String(index)}`,
    }),
  );
  vi.mocked(api.listSavedViews)
    .mockResolvedValueOnce(first)
    .mockRejectedValueOnce(new Error("Temporary failure"))
    .mockResolvedValueOnce([
      view({
        id: "01900000-0000-7000-8000-000000000100",
        name: "Last view",
      }),
    ]);
  wrap(<Directory />);
  await user.click(screen.getByRole("button", { name: "Saved views" }));
  const more = await screen.findByRole("button", {
    name: "Show more Saved Views",
  });
  await user.click(more);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Could not load Saved Views",
  );
  expect(more).toBeDisabled();
  await user.click(screen.getByRole("button", { name: "Retry Saved Views" }));
  expect(
    await screen.findByRole("button", { name: "Open Last view" }),
  ).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Open View 0" }),
  ).toBeInTheDocument();
  expect(api.listSavedViews).toHaveBeenNthCalledWith(
    2,
    "seed_lots",
    expect.any(AbortSignal),
    100,
  );
  expect(api.listSavedViews).toHaveBeenNthCalledWith(
    3,
    "seed_lots",
    expect.any(AbortSignal),
    100,
  );
  expect(
    screen.queryByRole("button", { name: "Show more Saved Views" }),
  ).not.toBeInTheDocument();
});

test("detail return preserves directory filters, task state, and refreshable URL", async () => {
  const user = userEvent.setup();
  window.history.replaceState(null, "", "#/seeds?q=basil&lifecycle=history");
  const rendered = wrap(<Directory />);
  await user.click(
    screen.getByRole("button", { name: "Next page and select" }),
  );
  act(() => {
    setRecordRoute(`#/seeds/${id}`);
  });
  act(() => {
    setRecordRoute("#/seeds", true);
  });
  expect(window.location.hash).toBe("#/seeds?q=basil&lifecycle=history");
  expect(screen.getByText("Offset 80 · Selected")).toBeVisible();
  rendered.unmount();
  wrap(<Directory />);
  expect(screen.getByRole("textbox", { name: "Search seeds" })).toHaveValue(
    "basil",
  );
});
