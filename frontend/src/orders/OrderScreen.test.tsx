import {
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
import { listSuppliers } from "../suppliers/api";
import {
  getOrder,
  listOrders,
  saveOrder,
  deleteOrder,
  orderPrice,
  type OrderDetail,
} from "./api";
import { previewPurchase, applyPurchase, purchaseChoices } from "./purchaseApi";
import { OrderScreen } from "./OrderScreen";
import { savedViewHash } from "../saved-views/state";

vi.mock("./purchaseApi", () => ({
  previewPurchase: vi.fn(),
  applyPurchase: vi.fn(),
  purchaseChoices: vi.fn(),
}));
vi.mock("../suppliers/api", () => ({ listSuppliers: vi.fn() }));
vi.mock("./api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./api")>()),
  getOrder: vi.fn(),
  listOrders: vi.fn(),
  saveOrder: vi.fn(),
  deleteOrder: vi.fn(),
}));
const id = "01900000-0000-7000-8000-000000000911";
const supplierId = "01900000-0000-7000-8000-000000000912";
const auth: AuthContextValue = {
  state: {
    status: "authenticated",
    csrfToken: "csrf",
    session: {
      user_id: id,
      login_name: "owner",
      display_name: "Owner",
      owner: true,
      canonical_origin: "http://localhost:15174",
    },
  },
  logIn: vi.fn(),
  logOut: vi.fn(),
  sessionExpired: vi.fn(),
  retryRestoration: vi.fn(),
  cancelLogout: vi.fn(),
};
const detail: OrderDetail = {
  id,
  supplier_id: supplierId,
  supplier: { id: supplierId, name: "Nursery" },
  ordered_on: { precision: "month", year: 2026, month: 10 },
  order_reference: "REF-1",
  total_price: "42.5000",
  currency: "EUR",
  notes: "Known purchase",
  seed_lot_count: 2,
  created_at: "2026-10-08T10:00:00Z",
  updated_at: "2026-10-08T10:00:00Z",
  seed_lots: [
    {
      id: "01900000-0000-7000-8000-000000000921",
      label: "Packet A",
      botanical_identity: { id, display_label: "Basil" },
      lifecycle: "active",
      acquisition_date: null,
    },
    {
      id: "01900000-0000-7000-8000-000000000922",
      label: "Packet B",
      botanical_identity: { id, display_label: "Basil" },
      lifecycle: "active",
      acquisition_date: null,
    },
  ],
  seed_lots_total: 2,
  seed_lots_offset: 0,
  seed_lots_limit: 50,
};
function mount(initialId?: string) {
  return render(
    <AuthContext.Provider value={auth}>
      <OrderScreen initialId={initialId} />
    </AuthContext.Provider>,
  );
}
beforeEach(() => {
  window.history.replaceState(null, "", "#/orders");
  vi.mocked(listSuppliers).mockResolvedValue([
    {
      id: supplierId,
      name: "Nursery",
      kind: "nursery",
      website: null,
      email: null,
      phone: null,
      notes: null,
      retired_at: null,
      created_at: detail.created_at,
      updated_at: detail.updated_at,
      usage_counts: {
        seed_lots_active: 0,
        seed_lots_total: 0,
        plants_active: 0,
        plants_total: 0,
        plant_groups_active: 0,
        plant_groups_total: 0,
        direct_records_active: 0,
        direct_records_total: 0,
      },
    },
  ]);
  vi.mocked(listOrders).mockResolvedValue({
    items: [detail],
    total: 1,
    offset: 0,
    limit: 50,
  });
  vi.mocked(getOrder).mockResolvedValue(detail);
  vi.mocked(saveOrder).mockResolvedValue(detail);
  vi.mocked(deleteOrder).mockResolvedValue(undefined);
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  window.history.replaceState(null, "", "#/dashboard");
});

test("directory preserves exact price, partial date and authoritative count with searchable Supplier state", async () => {
  mount();
  expect(await screen.findByRole("link", { name: "REF-1" })).toHaveAttribute(
    "href",
    `#/orders/${id}`,
  );
  expect(screen.getByText("EUR 42.5000")).toBeVisible();
  expect(screen.getByText("2026-10 · Nursery")).toBeVisible();
  expect(screen.getByLabelText("Directory results")).toHaveTextContent(
    "1 record",
  );
  fireEvent.change(screen.getByLabelText("Search Orders"), {
    target: { value: "ABC" },
  });
  fireEvent.change(screen.getByLabelText("Supplier", { selector: "select" }), {
    target: { value: supplierId },
  });
  await waitFor(() => {
    expect(listOrders).toHaveBeenLastCalledWith(
      "ABC",
      supplierId,
      0,
      expect.any(AbortSignal),
    );
  });
  expect(
    savedViewHash("orders", 1, { q: "ABC", supplier_id: supplierId }),
  ).toBe(`#/orders?q=ABC&supplier_id=${supplierId}`);
});

test("empty, loading and error states are actionable", async () => {
  vi.mocked(listOrders).mockReturnValueOnce(new Promise(() => undefined));
  const view = mount();
  expect(screen.getByText("Loading Orders…")).toBeVisible();
  view.unmount();
  vi.mocked(listOrders).mockRejectedValueOnce(new ApiError(500));
  mount();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "could not load Orders",
  );
  vi.mocked(listOrders).mockResolvedValue({
    items: [],
    total: 0,
    offset: 0,
    limit: 50,
  });
  await userEvent.click(screen.getByRole("button", { name: "Retry Orders" }));
  expect(
    await screen.findByRole("heading", { name: "No Orders found" }),
  ).toBeVisible();
});

test("create keeps unknown date and price absent, sends exact text when supplied", async () => {
  const user = userEvent.setup();
  mount();
  await screen.findByRole("link", { name: "REF-1" });
  await user.click(screen.getByRole("button", { name: "+ New Order" }));
  const dialog = screen.getByRole("dialog", { name: "New Order" });
  await user.type(
    within(dialog).getByLabelText("Order reference (optional)"),
    "NEW",
  );
  await user.type(
    within(dialog).getByLabelText("Total price (optional)"),
    "0.010000000000000001",
  );
  await user.type(within(dialog).getByLabelText("Currency"), "USD");
  await user.click(
    within(dialog).getByRole("button", { name: "Create Order" }),
  );
  await waitFor(() => {
    expect(saveOrder).toHaveBeenCalledWith(
      undefined,
      expect.objectContaining({
        ordered_on: null,
        supplier_id: null,
        total_price: "0.010000000000000001",
        currency: "USD",
        order_reference: "NEW",
      }),
      "csrf",
    );
  });
});

test("detail exposes independent seed lots, truthful transaction and Add seed lot context", async () => {
  mount(id);
  expect(await screen.findByRole("link", { name: "Packet A" })).toHaveAttribute(
    "href",
    `#/seeds/${detail.seed_lots[0]?.id ?? ""}`,
  );
  expect(screen.getByRole("link", { name: "Packet B" })).toBeVisible();
  expect(screen.getByRole("link", { name: "Add seed lot" })).toHaveAttribute(
    "href",
    `#/seeds?action=create&order=${id}`,
  );
  expect(screen.getByRole("link", { name: "Nursery" })).toHaveAttribute(
    "href",
    `#/suppliers/${supplierId}`,
  );
  expect(screen.getByRole("button", { name: "Delete Order" })).toBeDisabled();
  expect(screen.getByText("2026-10")).toBeVisible();
  expect(orderPrice({ total_price: null, currency: null })).toBe(
    "Price unknown",
  );
});

test("edit preserves values, reports domain conflicts inside the modal", async () => {
  const user = userEvent.setup();
  mount(id);
  await user.click(await screen.findByRole("button", { name: "Edit Order" }));
  expect(screen.getByLabelText("Total price (optional)")).toHaveValue(
    "42.5000",
  );
  vi.mocked(saveOrder).mockRejectedValueOnce(
    new ApiError(409, null, {
      detail: { message: "Supplier conflicts with a linked SeedLot" },
    }),
  );
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Supplier conflicts",
  );
  expect(screen.getByRole("dialog", { name: "Edit Order" })).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  await waitFor(() => {
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

test("unreferenced Order deletion requires explicit confirmation; server refusal remains visible", async () => {
  vi.mocked(getOrder).mockResolvedValue({
    ...detail,
    seed_lot_count: 0,
    seed_lots: [],
    seed_lots_total: 0,
    ordered_on: null,
    supplier: null,
    supplier_id: null,
    total_price: null,
    currency: null,
  });
  const user = userEvent.setup();
  mount(id);
  expect(await screen.findByText("Price unknown")).toBeVisible();
  expect(screen.getByText("Date unknown")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Delete Order" }));
  expect(deleteOrder).not.toHaveBeenCalled();
  vi.mocked(deleteOrder).mockRejectedValueOnce(
    new ApiError(409, null, {
      detail: { message: "This Order has linked SeedLots" },
    }),
  );
  await user.click(screen.getByRole("button", { name: "Confirm delete" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("linked SeedLots");
  await user.click(screen.getByRole("button", { name: "Confirm delete" }));
  await waitFor(() => {
    expect(window.location.hash).toBe("#/orders");
  });
});

test("opening an Orders Saved View resets pagination", async () => {
  vi.mocked(listOrders).mockResolvedValue({
    items: [detail],
    total: 51,
    offset: 0,
    limit: 50,
  });
  const user = userEvent.setup();
  mount();
  await user.click(await screen.findByRole("button", { name: "Next Orders" }));
  await waitFor(() => {
    expect(listOrders).toHaveBeenLastCalledWith(
      "",
      "",
      50,
      expect.any(AbortSignal),
    );
  });
  window.history.pushState(null, "", "#/orders?q=REF");
  window.dispatchEvent(new PopStateEvent("popstate"));
  await waitFor(() => {
    expect(listOrders).toHaveBeenLastCalledWith(
      "REF",
      "",
      0,
      expect.any(AbortSignal),
    );
  });
});

test("Order detail links an existing physical lot through shared preview and refreshes after Apply", async () => {
  vi.mocked(purchaseChoices).mockResolvedValue({
    items: [
      {
        id: supplierId,
        label: "Eligible packet",
        source_kind: "unknown",
        supplier: null,
        order_id: null,
      },
    ],
    total: 1,
    offset: 0,
    limit: 50,
  });
  vi.mocked(previewPurchase).mockResolvedValue({
    order: detail,
    seed_lot_id: supplierId,
    seed_lot_updated_at: detail.updated_at,
    current: { source_kind: "unknown" },
    current_supplier: null,
    proposed_source: "purchased",
    supplier_action: "fill",
    date_action: "copy",
    can_apply: true,
    conflict: null,
  });
  vi.mocked(applyPurchase).mockResolvedValue({
    order: detail,
    context: {
      source_kind: "purchased",
      order_id: id,
      supplier_id: supplierId,
    },
    confirmation: {
      context: { source_kind: "unknown" },
      expected_order_updated_at: detail.updated_at,
      use_order_supplier: true,
      use_order_date: false,
    },
    seed_lot: null,
  });
  mount(id);
  await userEvent.click(
    await screen.findByRole("button", { name: "Link existing seed lot" }),
  );
  await userEvent.click(
    await screen.findByRole("button", { name: "Eligible packet" }),
  );
  await screen.findByRole("dialog", { name: "Review purchase context" });
  expect(applyPurchase).not.toHaveBeenCalled();
  const calls = vi.mocked(getOrder).mock.calls.length;
  await userEvent.click(
    await screen.findByRole("button", { name: "Apply purchase context" }),
  );
  await waitFor(() => {
    expect(vi.mocked(getOrder).mock.calls.length).toBeGreaterThan(calls);
  });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
