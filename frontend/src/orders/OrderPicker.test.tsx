import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { getOrder, listOrders, type OrderDetail } from "./api";
import { OrderPicker } from "./OrderPicker";
vi.mock("./api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./api")>()),
  getOrder: vi.fn(),
  listOrders: vi.fn(),
}));
const order: OrderDetail = {
  id: "01900000-0000-7000-8000-000000000911",
  order_reference: "PO-OLD",
  supplier_id: null,
  supplier: null,
  ordered_on: null,
  total_price: null,
  currency: null,
  notes: null,
  created_at: "2026-10-08T00:00:00Z",
  updated_at: "2026-10-08T00:00:00Z",
  seed_lot_count: 0,
  seed_lots: [],
  seed_lots_total: 0,
  seed_lots_offset: 0,
  seed_lots_limit: 50,
};
function Editor() {
  const [value, setValue] = useState(order.id);
  return (
    <>
      <OrderPicker value={value} onChange={setValue} disabled={false} />
      <output>{value || "Unlinked"}</output>
    </>
  );
}
beforeEach(() => {
  vi.mocked(getOrder).mockResolvedValue(order);
  vi.mocked(listOrders).mockResolvedValue({
    items: [],
    total: 0,
    offset: 0,
    limit: 50,
  });
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
test("existing Order outside the page stays selectable through search, unlink and relink", async () => {
  const user = userEvent.setup();
  render(<Editor />);
  await screen.findByRole("option", { name: /PO-OLD/ });
  await user.type(
    screen.getByRole("searchbox", { name: "Find an Order" }),
    "missing",
  );
  await waitFor(() => {
    expect(listOrders).toHaveBeenLastCalledWith(
      "missing",
      "",
      0,
      expect.any(AbortSignal),
    );
  });
  expect(screen.getByLabelText("Order", { selector: "select" })).toHaveValue(
    order.id,
  );
  await user.selectOptions(
    screen.getByLabelText("Order", { selector: "select" }),
    "",
  );
  expect(screen.getByText("Unlinked")).toBeVisible();
  vi.mocked(listOrders).mockResolvedValue({
    items: [order],
    total: 1,
    offset: 0,
    limit: 50,
  });
  await user.clear(screen.getByRole("searchbox", { name: "Find an Order" }));
  await screen.findByRole("option", { name: /PO-OLD/ });
  await user.selectOptions(
    screen.getByLabelText("Order", { selector: "select" }),
    order.id,
  );
  expect(screen.getByRole("status")).toHaveTextContent(order.id);
});
test("failed Order choices can be retried and large directories are paged", async () => {
  vi.mocked(listOrders).mockRejectedValueOnce(new Error("offline"));
  render(<Editor />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Could not load Orders",
  );
  vi.mocked(listOrders).mockResolvedValue({
    items: [order],
    total: 51,
    offset: 0,
    limit: 50,
  });
  await userEvent.click(
    screen.getByRole("button", { name: "Retry Order choices" }),
  );
  await userEvent.click(
    await screen.findByRole("button", { name: "Next Order choices" }),
  );
  await waitFor(() => {
    expect(listOrders).toHaveBeenLastCalledWith(
      "",
      "",
      50,
      expect.any(AbortSignal),
    );
  });
});

test("known Supplier filters Orders first with a deliberate all-Suppliers escape", async () => {
  render(
    <OrderPicker
      value=""
      onChange={vi.fn()}
      disabled={false}
      supplierId="supplier-a"
    />,
  );
  await waitFor(() => {
    expect(listOrders).toHaveBeenLastCalledWith(
      "",
      "supplier-a",
      0,
      expect.any(AbortSignal),
    );
  });
  await userEvent.click(screen.getByLabelText(/Show all Suppliers/));
  await waitFor(() => {
    expect(listOrders).toHaveBeenLastCalledWith(
      "",
      "",
      0,
      expect.any(AbortSignal),
    );
  });
});

test("confirmed Order version refreshes transaction context and failed context can be retried", async () => {
  vi.mocked(getOrder).mockRejectedValueOnce(new Error("offline"));
  const view = render(
    <OrderPicker
      value={order.id}
      onChange={vi.fn()}
      disabled={false}
      refreshKey="old"
    />,
  );
  await userEvent.click(
    await screen.findByRole("button", {
      name: "Retry transaction information",
    }),
  );
  await screen.findByRole("region", { name: "Order transaction information" });
  vi.mocked(getOrder).mockResolvedValue({
    ...order,
    total_price: "12.340000000000000001",
    currency: "EUR",
  });
  view.rerender(
    <OrderPicker
      value={order.id}
      onChange={vi.fn()}
      disabled={false}
      refreshKey="new"
    />,
  );
  expect(await screen.findByText("EUR 12.340000000000000001")).toBeVisible();
});
