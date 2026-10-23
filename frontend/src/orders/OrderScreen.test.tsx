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
const supplier = {
  id: supplierId,
  name: "Nursery",
  kind: "nursery" as const,
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
};
function mount(initialId?: string, initialTab?: string) {
  return render(
    <AuthContext.Provider value={auth}>
      <OrderScreen initialId={initialId} initialTab={initialTab} />
    </AuthContext.Provider>,
  );
}
function orderRow() {
  return screen.findByRole("button", { name: /REF-1/ });
}
beforeEach(() => {
  window.history.replaceState(null, "", "#/orders");
  vi.mocked(listSuppliers).mockResolvedValue([supplier]);
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
  vi.restoreAllMocks();
  vi.clearAllMocks();
  window.history.replaceState(null, "", "#/dashboard");
});

test("directory exposes exact price, partial date, authoritative count and a hidden search label", async () => {
  const user = userEvent.setup();
  mount();
  const row = await orderRow();
  expect(row).toHaveAttribute("aria-pressed", "false");
  expect(screen.getByText("EUR 42.5000")).toBeVisible();
  expect(screen.getByText("2026-10 · Nursery")).toBeVisible();
  expect(screen.getByLabelText("Directory results")).toHaveTextContent(
    "1 record",
  );
  expect(screen.getByText("Search Orders", { selector: "label" })).toHaveClass(
    "sr-only",
  );

  await user.click(row);
  expect(row).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("link", { name: "Open details" })).toHaveAttribute(
    "href",
    `#/orders/${id}`,
  );

  fireEvent.change(screen.getByLabelText("Search Orders"), {
    target: { value: "ABC" },
  });
  await user.click(screen.getByRole("button", { name: "Filters" }));
  const filters = screen.getByRole("dialog", { name: "Orders filters" });
  const supplierControl = within(filters).getByRole("combobox", {
    name: "Supplier",
  });
  await user.click(supplierControl);
  await user.click(within(filters).getByRole("button", { name: "Nursery" }));
  await waitFor(() => {
    expect(listOrders).toHaveBeenLastCalledWith(
      "ABC",
      supplierId,
      0,
      expect.any(AbortSignal),
    );
  });
  expect(
    screen.getByRole("button", { name: "Remove supplier filter" }),
  ).toHaveTextContent("Supplier: Nursery");
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

test("new Order keeps unknown date and absent price, then sends the exact supplied pair", async () => {
  const user = userEvent.setup();
  mount();
  await orderRow();
  const create = screen.getByRole("button", { name: "New Order" });
  await user.click(create);
  const dialog = screen.getByRole("dialog", { name: "New Order" });
  expect(dialog.querySelector(".order-form__grid")).toBeInTheDocument();
  expect(
    within(dialog).getByText("Order date precision", { selector: "label" }),
  ).toHaveClass("sr-only");
  expect(within(dialog).queryByText("Precision")).not.toBeInTheDocument();
  expect(within(dialog).getByLabelText("Total price")).not.toBeRequired();
  expect(within(dialog).getByLabelText("Currency")).not.toBeRequired();
  expect(
    within(dialog).getByRole("combobox", { name: "Supplier" }),
  ).not.toBeRequired();
  expect(within(dialog).getByRole("button", { name: "Cancel" })).toBeVisible();
  await user.type(within(dialog).getByLabelText("Order reference"), "NEW");
  await user.type(
    within(dialog).getByLabelText("Total price"),
    "0.010000000000000001",
  );
  expect(within(dialog).getByLabelText("Currency")).toBeRequired();
  await user.type(within(dialog).getByLabelText("Currency"), "USD");
  expect(within(dialog).getByLabelText("Total price")).toBeRequired();
  await user.clear(within(dialog).getByLabelText("Currency"));
  expect(within(dialog).getByLabelText("Total price")).not.toBeRequired();
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
  await waitFor(() => {
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
  expect(screen.getByRole("status")).toHaveTextContent("Order created.");
});

test("pristine backdrop click closes New Order and restores focus without confirmation", async () => {
  const user = userEvent.setup();
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
  mount();
  await orderRow();
  const create = screen.getByRole("button", { name: "New Order" });
  await user.click(create);
  const dialog = screen.getByRole("dialog", { name: "New Order" });
  fireEvent.click(dialog, { clientX: 10, clientY: 10 });
  await waitFor(() => {
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
  expect(confirm).not.toHaveBeenCalled();
  expect(create).toHaveFocus();
  confirm.mockRestore();
});

test("dirty New Order protects backdrop, Escape and Cancel; inside clicks never dismiss", async () => {
  const user = userEvent.setup();
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  mount();
  await orderRow();
  await user.click(screen.getByRole("button", { name: "New Order" }));
  const dialog = screen.getByRole("dialog", { name: "New Order" });
  const reference = within(dialog).getByLabelText("Order reference");
  await user.type(reference, "DIRTY");
  fireEvent.click(reference);
  expect(screen.getByRole("dialog", { name: "New Order" })).toBeVisible();

  fireEvent.click(dialog, { clientX: 10, clientY: 10 });
  expect(confirm).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("dialog", { name: "New Order" })).toBeVisible();

  fireEvent.keyDown(dialog, { key: "Escape" });
  expect(confirm).toHaveBeenCalledTimes(2);
  expect(screen.getByRole("dialog", { name: "New Order" })).toBeVisible();

  await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
  expect(confirm).toHaveBeenCalledTimes(3);
  expect(screen.getByRole("dialog", { name: "New Order" })).toBeVisible();

  confirm.mockReturnValue(true);
  await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
  await waitFor(() => {
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
  confirm.mockRestore();
});

test("New Order dropdown clicks stay inside; Escape closes the picker before the dialog", async () => {
  const user = userEvent.setup();
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
  mount();
  await orderRow();
  await user.click(screen.getByRole("button", { name: "New Order" }));
  const dialog = screen.getByRole("dialog", { name: "New Order" });
  const supplierControl = within(dialog).getByRole("combobox", {
    name: "Supplier",
  });
  expect(supplierControl).toHaveAttribute("aria-expanded", "false");
  await user.click(supplierControl);
  await user.click(within(dialog).getByRole("button", { name: "Nursery" }));
  expect(dialog).toBeVisible();
  expect(supplierControl).toHaveValue("Nursery");

  await user.click(supplierControl);
  expect(within(dialog).getByRole("listbox")).toBeVisible();
  await user.keyboard("{Escape}");
  expect(within(dialog).queryByRole("listbox")).not.toBeInTheDocument();
  expect(dialog).toBeVisible();
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  confirm.mockRestore();
});

test("detail dashboard keeps partial dates, exact totals and independent seed lots", async () => {
  const user = userEvent.setup();
  mount(id);
  expect(await screen.findByRole("heading", { name: "REF-1" })).toBeVisible();
  expect(screen.getByText("2026-10")).toBeVisible();
  expect(screen.getByText("EUR 42.5000")).toBeVisible();
  expect(screen.getByRole("link", { name: "Nursery" })).toHaveAttribute(
    "href",
    `#/suppliers/${supplierId}`,
  );
  expect(screen.getByRole("link", { name: "Add seed lot" })).toHaveAttribute(
    "href",
    `#/seeds?action=create&order=${id}`,
  );
  expect(
    screen.getByRole("button", { name: "Link existing seed lot" }),
  ).toBeVisible();
  expect(screen.getByRole("button", { name: "Delete Order" })).toBeDisabled();
  expect(screen.getByText("Known purchase")).toBeVisible();

  await user.click(screen.getByRole("tab", { name: "Seed lots (2)" }));
  expect(await screen.findByRole("link", { name: "Packet A" })).toHaveAttribute(
    "href",
    `#/seeds/${detail.seed_lots[0]?.id ?? ""}`,
  );
  expect(screen.getByRole("link", { name: "Packet B" })).toBeVisible();
  expect(screen.getAllByText("Acquisition date unknown · Active")).toHaveLength(
    2,
  );
  expect(orderPrice({ total_price: null, currency: null })).toBe(
    "Price unknown",
  );
});

test("edit preserves values and reports domain conflicts inside the modal", async () => {
  const user = userEvent.setup();
  mount(id);
  const edit = await screen.findByRole("button", { name: "Edit Order" });
  await user.click(edit);
  expect(screen.getByLabelText("Total price")).toHaveValue("42.5000");
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
  await waitFor(() => {
    expect(screen.getByRole("heading", { name: "REF-1" })).toHaveFocus();
  });
});

test("direct edit route uses the inline fallback and returns focus to the detail heading", async () => {
  const user = userEvent.setup();
  window.history.replaceState(null, "", `#/orders/${id}?tab=edit`);
  mount(id, "edit");
  expect(
    await screen.findByRole("heading", { name: "Edit Order" }),
  ).toBeVisible();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(window.location.hash).toBe(`#/orders/${id}?tab=edit`);

  await user.click(screen.getByRole("button", { name: "Cancel" }));
  await waitFor(() => {
    expect(window.location.hash).toBe(`#/orders/${id}`);
  });
  await waitFor(() => {
    expect(screen.getByRole("heading", { name: "REF-1" })).toHaveFocus();
  });
});

test("leaving the direct edit URL closes the inline editor and restores its heading", async () => {
  const { rerender } = mount(id, "edit");
  expect(
    await screen.findByRole("heading", { name: "Edit Order" }),
  ).toBeVisible();
  rerender(
    <AuthContext.Provider value={auth}>
      <OrderScreen initialId={id} />
    </AuthContext.Provider>,
  );
  await waitFor(() => {
    expect(
      screen.queryByRole("heading", { name: "Edit Order" }),
    ).not.toBeInTheDocument();
  });
  const heading = await screen.findByRole("heading", { name: "REF-1" });
  await waitFor(() => {
    expect(heading).toHaveFocus();
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
    await screen.findByRole("button", { name: /Eligible packet/ }),
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

test("the explicit create route supports a real Order with all descriptive facts unknown", async () => {
  const user = userEvent.setup();
  render(
    <AuthContext.Provider value={auth}>
      <OrderScreen startCreating />
    </AuthContext.Provider>,
  );
  const dialog = await screen.findByRole("dialog", { name: "New Order" });
  expect(
    within(dialog).getByRole("group", { name: "Order date" }),
  ).toHaveTextContent("Unknown");
  expect(saveOrder).not.toHaveBeenCalled();
  await user.click(
    within(dialog).getByRole("button", { name: "Create Order" }),
  );
  await waitFor(() => {
    expect(saveOrder).toHaveBeenCalledWith(
      undefined,
      {
        supplier_id: null,
        ordered_on: null,
        order_reference: null,
        total_price: null,
        currency: null,
        notes: null,
      },
      "csrf",
    );
  });
});

test("Supplier filter popup stays anchored, wraps long names, and clears before closing the drawer", async () => {
  const longName =
    "Nursery-with-a-deliberately-long-name-that-must-wrap-without-overflowing";
  vi.mocked(listSuppliers).mockResolvedValue([{ ...supplier, name: longName }]);
  const user = userEvent.setup();
  window.history.replaceState(null, "", `#/orders?supplier_id=${supplierId}`);
  mount();
  await waitFor(() => {
    expect(listOrders).toHaveBeenCalledWith(
      "",
      supplierId,
      0,
      expect.any(AbortSignal),
    );
  });
  await waitFor(() => {
    expect(
      screen.getByRole("button", { name: "Remove supplier filter" }),
    ).toHaveTextContent(longName);
  });
  await user.click(screen.getByRole("button", { name: /^Filters/ }));
  const filters = screen.getByRole("dialog", { name: "Orders filters" });
  const control = within(filters).getByRole("combobox", {
    name: "Supplier",
  });
  expect(control).toHaveValue(longName);
  await user.click(control);
  const listbox = within(filters).getByRole("listbox");
  expect(listbox.closest(".reference-control")).toBeInTheDocument();
  expect(within(listbox).getByRole("button", { name: longName })).toBeVisible();
  await user.keyboard("{Escape}");
  expect(within(filters).queryByRole("listbox")).not.toBeInTheDocument();
  expect(filters).toBeVisible();
  await user.keyboard("{Escape}");
  expect(
    screen.queryByRole("dialog", { name: "Orders filters" }),
  ).not.toBeInTheDocument();
});

test("typing a multi-character search query keeps focus while results are in flight", async () => {
  vi.mocked(listOrders).mockResolvedValueOnce({
    items: [detail],
    total: 1,
    offset: 0,
    limit: 50,
  });
  vi.mocked(listOrders).mockReturnValue(new Promise(() => undefined));
  const user = userEvent.setup();
  mount();
  await orderRow();
  const search = screen.getByLabelText("Search Orders");
  await user.click(search);
  await user.type(search, "ABC");
  expect(search).toHaveValue("ABC");
  expect(search).toHaveFocus();
  await waitFor(() => {
    expect(listOrders).toHaveBeenLastCalledWith(
      "ABC",
      "",
      0,
      expect.any(AbortSignal),
    );
  });
});

test("a missing Supplier filter UUID stays exact and visible", async () => {
  const missing = "01900000-0000-7000-8000-000000000999";
  vi.mocked(listOrders).mockResolvedValue({
    items: [],
    total: 0,
    offset: 0,
    limit: 50,
  });
  const user = userEvent.setup();
  window.history.replaceState(null, "", `#/orders?supplier_id=${missing}`);
  mount();
  await waitFor(() => {
    expect(listOrders).toHaveBeenCalledWith(
      "",
      missing,
      0,
      expect.any(AbortSignal),
    );
  });
  const label = `Unavailable Supplier — ${missing}`;
  expect(
    screen.getByRole("button", { name: "Remove supplier filter" }),
  ).toHaveTextContent(label);
  await user.click(screen.getByRole("button", { name: /^Filters/ }));
  const filters = screen.getByRole("dialog", { name: "Orders filters" });
  const control = within(filters).getByRole("combobox", {
    name: "Supplier",
  });
  expect(control).toHaveValue(label);
  await user.click(control);
  expect(
    within(filters).getByRole("button", {
      name: `Unavailable Supplier — ${missing} (unavailable)`,
    }),
  ).toBeVisible();
});
