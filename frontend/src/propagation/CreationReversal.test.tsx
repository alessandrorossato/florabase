import {
  cleanup,
  render,
  screen,
  within,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/context";
import { CreationReversal } from "./CreationReversal";

const auth = {
  state: { status: "authenticated", csrfToken: "csrf-test", session: {} },
  sessionExpired: vi.fn(),
  logIn: vi.fn(),
  logOut: vi.fn(),
  retryRestoration: vi.fn(),
  cancelLogout: vi.fn(),
} as unknown as AuthContextValue;
const eligibility = {
  status: "safe",
  operation_receipt_id: "receipt",
  operation_status: "applied",
  source_id: "source",
  source_type: "sowing",
  reasons: [],
  retained_observation_ids: [],
};
function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
function show(
  kind: "sowing" | "plant" | "plant_group" = "plant",
  lifecycle = "active",
  inMoreMenu = false,
) {
  const onReversed = vi.fn();
  render(
    <AuthContext.Provider value={auth}>
      <CreationReversal
        inMoreMenu={inMoreMenu}
        kind={kind}
        id="result"
        lifecycle={lifecycle}
        revision="1"
        onReversed={onReversed}
      />
    </AuthContext.Provider>,
  );
  return onReversed;
}
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test("offers deep contextual help without starting a reversal", async () => {
  const fetch = vi.fn(() => Promise.resolve(json(eligibility)));
  vi.stubGlobal("fetch", fetch);
  show();
  const user = userEvent.setup();

  expect(fetch).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Undo creation" }));
  expect(await screen.findByText("Can undo")).toBeVisible();
  await user.click(screen.getByText("What undo preserves"));
  const dialog = screen.getByRole("dialog", { name: "Undo plant creation" });
  expect(dialog).toHaveTextContent(/source lifecycle and quantity snapshot/i);
  expect(dialog).toHaveTextContent(/not deleted/i);
  expect(fetch).toHaveBeenCalledTimes(1);
});

test.each(["sowing", "plant", "plant_group"] as const)(
  "SAFE %s reversal returns authoritative state with CSRF",
  async (kind) => {
    const result = {
      operation_status: "reversed",
      [kind]: { id: "result", lifecycle: "reversed" },
    };
    const fetch = vi.fn((_url: string, init?: RequestInit) =>
      Promise.resolve(json(init?.method === "POST" ? result : eligibility)),
    );
    vi.stubGlobal("fetch", fetch);
    const onReversed = show(kind);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Undo creation" }));
    await user.click(
      await screen.findByRole("button", { name: /Undo .* creation/ }),
    );
    expect(onReversed).toHaveBeenCalledWith(result);
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Creation reversed",
    );
    const mutation = fetch.mock.calls.find(
      ([, init]) => init?.method === "POST",
    );
    expect(mutation?.[0]).toContain("/reverse-creation");
    expect(new Headers(mutation?.[1]?.headers).get("X-CSRF-Token")).toBe(
      "csrf-test",
    );
    expect(
      screen.queryByRole("button", { name: /Undo .* creation/ }),
    ).not.toBeInTheDocument();
  },
);

test("retained observations require explicit confirmation and survive reversal", async () => {
  const fetch = vi.fn((_url: string, init?: RequestInit) =>
    Promise.resolve(
      json(
        init?.method === "POST"
          ? { plant: { lifecycle: "reversed" } }
          : {
              ...eligibility,
              status: "confirmation_required",
              retained_observation_ids: ["observation"],
            },
      ),
    ),
  );
  vi.stubGlobal("fetch", fetch);
  show();
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Undo creation" }));
  const button = await screen.findByRole("button", {
    name: "Undo plant creation",
  });
  expect(button).toBeDisabled();
  await user.click(screen.getByRole("checkbox", { name: /I confirm that 1/ }));
  expect(button).toBeEnabled();
  await user.click(button);
  expect(
    fetch.mock.calls.find(([, init]) => init?.method === "POST")?.[1]?.body,
  ).toBe(JSON.stringify({ confirm_retained_observations: true }));
  expect(
    await screen.findByText(/lineage and observations/),
  ).toBeInTheDocument();
});

test("typed blockers explain legacy metadata and link a dependent result", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve(
        json({
          ...eligibility,
          status: "blocked",
          reasons: [
            {
              code: "legacy_receipt_missing_result_snapshot",
              message:
                "This operation predates complete automatic-reversal metadata.",
            },
            {
              code: "active_downstream_operation",
              message: "Undo the descendant first.",
              entity_type: "plant",
              entity_id: "child",
            },
          ],
        }),
      ),
    ),
  );
  show("sowing");
  const user = userEvent.setup();
  const trigger = screen.getByRole("button", { name: "Undo creation" });
  expect(trigger).toBeEnabled();
  await user.click(trigger);
  expect(await screen.findByText(/predates complete/)).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Open related record" }),
  ).toHaveAttribute("href", "#/plants/child");
  const dialog = screen.getByRole("dialog", { name: "Undo sowing creation" });
  expect(
    within(dialog).queryByRole("button", { name: "Undo sowing creation" }),
  ).not.toBeInTheDocument();
  expect(dialog).toHaveTextContent("Cannot undo");
  await user.click(within(dialog).getByRole("button", { name: "Close" }));
  expect(trigger).toHaveFocus();
});

test("stale reversal requires refreshed eligibility and never silently succeeds", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((_url: string, init?: RequestInit) =>
      Promise.resolve(
        init?.method === "POST"
          ? json({ detail: { code: "source_quantity_changed" } }, 409)
          : json(eligibility),
      ),
    ),
  );
  const onReversed = show();
  await userEvent
    .setup()
    .click(screen.getByRole("button", { name: "Undo creation" }));
  await userEvent
    .setup()
    .click(await screen.findByRole("button", { name: "Undo plant creation" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("record changed");
  expect(
    screen.getByRole("button", { name: "Refresh eligibility" }),
  ).toBeInTheDocument();
  expect(onReversed).not.toHaveBeenCalled();
});

test("historical reversed detail never requests another reversal", async () => {
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  show("plant_group", "reversed");
  await userEvent
    .setup()
    .click(screen.getByRole("button", { name: "Creation reversed" }));
  expect(screen.getByRole("status")).toHaveTextContent(
    "Repeating the forward action creates a new record",
  );
  expect(fetch).not.toHaveBeenCalled();
});

test("malformed eligibility fails visibly instead of enabling reversal", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.resolve(json({}))),
  );
  show();
  await userEvent
    .setup()
    .click(screen.getByRole("button", { name: "Undo creation" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "could not check reversal eligibility",
  );
  expect(
    screen.queryByRole("button", { name: "Undo plant creation" }),
  ).not.toBeInTheDocument();
});

test("dialog loads eligibility only on demand, traps focus and rechecks after closing", async () => {
  const fetch = vi.fn(() => Promise.resolve(json(eligibility)));
  vi.stubGlobal("fetch", fetch);
  show();
  const user = userEvent.setup();
  const trigger = screen.getByRole("button", { name: "Undo creation" });
  expect(
    screen.queryByText(/Creation operation|Dependency state/),
  ).not.toBeInTheDocument();
  expect(fetch).not.toHaveBeenCalled();
  await user.click(trigger);
  await screen.findByText("Can undo");
  const dialog = screen.getByRole("dialog", { name: "Undo plant creation" });
  within(dialog).getByRole("button", { name: "Undo plant creation" }).focus();
  await user.tab();
  expect(within(dialog).getByRole("button", { name: "Cancel" })).toHaveFocus();
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
  await user.click(trigger);
  await screen.findByText("Can undo");
  expect(fetch).toHaveBeenCalledTimes(2);
});

test("Details More entry uses the established menu and returns focus after reversal inspection", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.resolve(json(eligibility))),
  );
  show("sowing", "active", true);
  const user = userEvent.setup();
  const more = screen.getByRole("button", { name: "More record actions" });
  more.focus();
  await user.keyboard("{ArrowDown}");
  const undo = await screen.findByRole("button", { name: "Undo creation" });
  await waitFor(() => {
    expect(undo).toHaveFocus();
  });
  await user.keyboard("{Escape}");
  expect(more).toHaveFocus();
  expect(
    screen.queryByRole("button", { name: "Undo creation" }),
  ).not.toBeInTheDocument();
  await user.click(more);
  await user.click(screen.getByRole("button", { name: "Undo creation" }));
  const dialog = await screen.findByRole("dialog", {
    name: "Undo sowing creation",
  });
  await within(dialog).findByText("Can undo");
  await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
  expect(more).toHaveFocus();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  await user.click(more);
  await user.click(document.body);
  expect(
    screen.queryByRole("button", { name: "Undo creation" }),
  ).not.toBeInTheDocument();
});
