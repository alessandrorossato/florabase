import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../../auth/context";
import { Cuttings } from "./Cuttings";

const auth = {
  state: { status: "authenticated", csrfToken: "csrf-test", session: {} },
  sessionExpired: vi.fn(),
  logIn: vi.fn(),
  logOut: vi.fn(),
  retryRestoration: vi.fn(),
  cancelLogout: vi.fn(),
} as unknown as AuthContextValue;
const lot = {
  id: "lot",
  label: "Bench cuttings",
  botanical_identity_id: "identity",
  material_type: "stem_cutting",
  source_kind: "collection_produced",
  lifecycle: "exhausted",
  quantity: null,
  initial_quantity: null,
  updated_at: "2026-11-10T11:00:00Z",
};
const attempt = {
  id: "attempt",
  label: "Perlite trial",
  vegetative_lot_id: "lot",
  vegetative_lot: lot,
  lifecycle: "active",
  rooted_count: null,
  rooting_rate_percent: null,
  quantity: null,
  observations: [],
  operation_receipt_id: "receipt",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status });
}
function show(props: Parameters<typeof Cuttings>[0] = {}) {
  render(
    <AuthContext.Provider value={auth}>
      <Cuttings {...props} />
    </AuthContext.Provider>,
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.mocked(auth.sessionExpired).mockClear();
  window.history.replaceState(null, "", "/");
});

test.each([false, true])(
  "taking cuttings from a Plant preserves explicit count and start date overrides (%s)",
  async (override) => {
    const fetch = vi.fn((path: string) => {
      if (path === "/api/v1/plants")
        return Promise.resolve(
          json([
            {
              id: "mother",
              label: "Rosemary mother",
              lifecycle: "active",
              botanical_identity_id: "identity",
            },
          ]),
        );
      if (path === "/api/v1/botanical-identities")
        return Promise.resolve(
          json([
            {
              id: "identity",
              display_label: "Rosemary",
              scientific_name: "Salvia rosmarinus",
            },
          ]),
        );
      if (path === "/api/v1/propagation-attempts/fast-create")
        return Promise.resolve(
          json(
            {
              vegetative_lot: lot,
              propagation_attempt: attempt,
              operation_receipt_id: "receipt",
            },
            201,
          ),
        );
      return Promise.resolve(json([]));
    });
    vi.stubGlobal("fetch", fetch);
    show({
      route: "new",
      sourceId: "mother",
      sourceType: "plant",
      identityId: "identity",
    });
    const user = userEvent.setup();
    await waitFor(() => {
      expect(
        screen.getByRole("combobox", { name: "Mother specimen" }),
      ).toHaveValue("Rosemary mother");
    });
    expect(
      screen.getByRole("checkbox", {
        name: "Start rooting attempt immediately",
      }),
    ).toBeChecked();
    await user.selectOptions(screen.getByLabelText("Precision"), "year");
    await user.clear(screen.getByRole("spinbutton", { name: "Year" }));
    await user.type(screen.getByRole("spinbutton", { name: "Year" }), "2025");
    if (override) {
      await user.click(
        screen.getByRole("checkbox", {
          name: "Use the taken or acquired date",
        }),
      );
      await user.selectOptions(
        screen.getByLabelText("Starting quantity precision"),
        "exact",
      );
      const count = screen.getByLabelText("Starting quantity count");
      await user.clear(count);
      await user.type(count, "3");
    }
    await user.click(screen.getByRole("button", { name: "Save cuttings" }));
    await waitFor(() => {
      expect(window.location.hash).toBe("#/cuttings/attempts/attempt");
    });
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/propagation-attempts/fast-create",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"mother_plant_id":"mother"') as unknown,
      }),
    );
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/propagation-attempts/fast-create",
      expect.objectContaining({
        body: expect.stringContaining(
          override
            ? '"quantity":{"value":3,"is_approximate":false},"started_on":null'
            : '"started_on":{"precision":"year","year":2025},"quantity":null',
        ) as unknown,
      }),
    );
  },
);

test.each([
  [null, "Rooting pending"],
  [0, "0 rooted · starting count unknown"],
  [2, "2 rooted · starting count unknown"],
])("attempt overview distinguishes rooted count %s", async (count, message) => {
  vi.stubGlobal(
    "fetch",
    vi.fn((path: string) => {
      if (path === "/api/v1/propagation-attempts/attempt")
        return Promise.resolve(json({ ...attempt, rooted_count: count }));
      if (path.endsWith("/propagation-summary"))
        return Promise.resolve(json({ offspring: [] }));
      if (path.endsWith("/lineage"))
        return Promise.resolve(json({ ancestors: [] }));
      if (path.endsWith("/primary-photo")) return Promise.resolve(json(null));
      return Promise.resolve(json([]));
    }),
  );
  show({ route: "attempts", id: "attempt" });
  expect(await screen.findByText(message)).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "Establish Plant or group" }) !== null,
  ).toBe(count !== 0);
});

test("undo retains rooting observations only after confirmation", async () => {
  const fetch = vi.fn((path: string, options?: RequestInit) => {
    if (path === "/api/v1/propagation-attempts/attempt")
      return Promise.resolve(json(attempt));
    if (path.endsWith("/propagation-summary"))
      return Promise.resolve(json({ offspring: [] }));
    if (path.endsWith("/lineage"))
      return Promise.resolve(json({ ancestors: [] }));
    if (path.endsWith("/primary-photo")) return Promise.resolve(json(null));
    if (path.endsWith("/reversal"))
      return Promise.resolve(
        options?.method === "POST"
          ? new Response(null, { status: 204 })
          : json({
              status: "confirmation_required",
              retained_observation_ids: ["observation"],
              reasons: [],
            }),
      );
    return Promise.resolve(json([]));
  });
  vi.stubGlobal("fetch", fetch);
  show({ route: "attempts", id: "attempt" });
  const user = userEvent.setup();
  await user.click(
    await screen.findByRole("button", { name: "Undo starting attempt" }),
  );
  const dialog = within(
    screen.getByRole("dialog", { name: "Undo cutting operation" }),
  );
  const confirmation = await dialog.findByRole("button", {
    name: "Confirm undo",
  });
  expect(confirmation).toBeDisabled();
  await user.click(
    dialog.getByRole("checkbox", {
      name: "Keep recorded observations on the reversed result",
    }),
  );
  await user.click(confirmation);
  expect(fetch).toHaveBeenCalledWith(
    "/api/v1/cutting-operations/receipt/reversal",
    expect.objectContaining({
      method: "POST",
      body: '{"confirm_retained_observations":true}',
    }),
  );
  await waitFor(() => {
    expect(
      screen.queryByRole("dialog", { name: "Undo cutting operation" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Rooting overview" }),
    ).toHaveFocus();
  });
});

test("cuttings session expiry returns to the sign-in flow", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.resolve(json({}, 401))),
  );
  show();
  await waitFor(() => {
    expect(auth.sessionExpired).toHaveBeenCalled();
  });
});

test("lot details save corrections with the version of the displayed lot", async () => {
  const fetch = vi.fn((path: string, options?: RequestInit) => {
    if (path === "/api/v1/vegetative-lots/lot") {
      if (options?.method === "PUT") return Promise.resolve(json(lot));
      return Promise.resolve(
        json({ ...lot, source_kind: "unknown", attempts: [] }),
      );
    }
    if (path.endsWith("/lineage"))
      return Promise.resolve(json({ ancestors: [] }));
    if (path.endsWith("/primary-photo")) return Promise.resolve(json(null));
    return Promise.resolve(json([]));
  });
  vi.stubGlobal("fetch", fetch);
  show({ route: "lots", id: "lot" });
  const user = userEvent.setup();
  await user.click(
    await screen.findByRole("button", { name: "Edit vegetative lot" }),
  );
  const dialog = within(
    screen.getByRole("dialog", { name: "Edit vegetative lot" }),
  );
  await user.selectOptions(dialog.getByLabelText("Lot status"), "active");
  await user.click(dialog.getByRole("button", { name: "Save lot" }));
  const request = fetch.mock.calls.find(
    ([, options]) => options?.method === "PUT",
  );
  expect(request?.[0]).toBe("/api/v1/vegetative-lots/lot");
  const body = request?.[1]?.body;
  expect(
    typeof body === "string" ? (JSON.parse(body) as unknown) : body,
  ).toMatchObject({
    botanical_identity_id: lot.botanical_identity_id,
    expected_updated_at: lot.updated_at,
    lifecycle: "active",
    quantity: null,
  });
  await waitFor(() => {
    expect(
      screen.getByRole("button", { name: "Edit vegetative lot" }),
    ).toHaveFocus();
  });
});
