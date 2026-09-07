import { cleanup, render, screen } from "@testing-library/react";
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
) {
  const onReversed = vi.fn();
  render(
    <AuthContext.Provider value={auth}>
      <CreationReversal
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
    await user.click(
      await screen.findByRole("button", { name: /Undo .* creation/ }),
    );
    expect(onReversed).toHaveBeenCalledWith(result);
    expect(await screen.findByText(/Creation reversed/)).toBeInTheDocument();
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
  expect(await screen.findByText(/predates complete/)).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Open related record" }),
  ).toHaveAttribute("href", "#/plants/child");
  expect(
    screen.getByRole("button", { name: "Undo sowing creation" }),
  ).toBeDisabled();
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
    .click(await screen.findByRole("button", { name: "Undo plant creation" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("record changed");
  expect(
    screen.getByRole("button", { name: "Refresh eligibility" }),
  ).toBeInTheDocument();
  expect(onReversed).not.toHaveBeenCalled();
});

test("historical reversed detail never requests another reversal", () => {
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  show("plant_group", "reversed");
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
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "could not check reversal eligibility",
  );
  expect(
    screen.queryByRole("button", { name: "Undo plant creation" }),
  ).not.toBeInTheDocument();
});
