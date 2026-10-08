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
import { PurchaseContextDialog, LinkExistingSeedLot } from "./PurchaseContext";
import {
  previewPurchase,
  applyPurchase,
  purchaseChoices,
  type PurchasePreview,
} from "./purchaseApi";

vi.mock("./purchaseApi", () => ({
  previewPurchase: vi.fn(),
  applyPurchase: vi.fn(),
  purchaseChoices: vi.fn(),
}));
const orderId = "01900000-0000-7000-8000-000000000911";
const seedId = "01900000-0000-7000-8000-000000000912";
const version = "2026-10-08T10:00:00Z";
const review: PurchasePreview = {
  order: {
    id: orderId,
    supplier_id: orderId,
    supplier: { id: orderId, name: "Nursery A" },
    ordered_on: { precision: "month", year: 2026, month: 10 },
    total_price: "32.500000000000000001",
    currency: "EUR",
    order_reference: "PO-1",
    notes: null,
    created_at: version,
    updated_at: version,
    seed_lot_count: 0,
  },
  seed_lot_id: seedId,
  seed_lot_updated_at: version,
  current: {
    source_kind: "unknown",
    supplier_id: null,
    acquisition_date: null,
    order_id: null,
  },
  current_supplier: null,
  proposed_source: "purchased",
  supplier_action: "fill",
  date_action: "copy",
  can_apply: true,
  conflict: null,
};
const onApplied = vi.fn();
const onCancel = vi.fn();
function mount(value = review) {
  vi.mocked(previewPurchase).mockResolvedValue(value);
  return render(
    <PurchaseContextDialog
      orderId={orderId}
      seedLotId={seedId}
      csrf="csrf"
      onApplied={onApplied}
      onCancel={onCancel}
    />,
  );
}
beforeEach(() => {
  vi.mocked(previewPurchase).mockResolvedValue(review);
  vi.mocked(applyPurchase).mockResolvedValue({
    order: review.order,
    context: {
      source_kind: "purchased",
      supplier_id: orderId,
      order_id: orderId,
      acquisition_date: null,
    },
    confirmation: {
      context: review.current,
      expected_order_updated_at: version,
      use_order_supplier: true,
      use_order_date: false,
    },
    seed_lot: null,
  });
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

test("preview is read only, cancellation never applies, and exact total is transaction context", async () => {
  mount();
  expect(await screen.findByText("EUR 32.500000000000000001")).toBeVisible();
  expect(screen.getByText(/not the price of this seed lot/)).toBeVisible();
  expect(screen.getByLabelText(/Fill unknown Supplier/)).toBeChecked();
  expect(
    screen.getByLabelText(/Use Order date as acquisition date/),
  ).not.toBeChecked();
  expect(applyPurchase).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(onCancel).toHaveBeenCalledOnce();
  expect(applyPurchase).not.toHaveBeenCalled();
});
test("Apply sends server context and both versions with explicit date choice", async () => {
  mount();
  await screen.findByText("PO-1");
  await userEvent.click(
    screen.getByLabelText(/Use Order date as acquisition date/),
  );
  await userEvent.click(
    screen.getByRole("button", { name: "Apply purchase context" }),
  );
  await waitFor(() => {
    expect(onApplied).toHaveBeenCalledOnce();
  });
  expect(applyPurchase).toHaveBeenCalledWith(
    orderId,
    {
      seed_lot_id: seedId,
      context: review.current,
      expected_seed_lot_updated_at: version,
      expected_order_updated_at: version,
      use_order_supplier: true,
      use_order_date: true,
    },
    "csrf",
  );
});
test("known Supplier conflict cannot Apply until replacement is confirmed; differing date stays", async () => {
  mount({
    ...review,
    current: {
      source_kind: "purchased_fruit",
      supplier_id: seedId,
      acquisition_date: { precision: "year", year: 2025 },
    },
    current_supplier: { id: seedId, name: "Garden exchange" },
    supplier_action: "replace",
    date_action: "replace",
    proposed_source: "purchased_fruit",
  });
  await screen.findByText(/Garden exchange → Garden exchange/);
  expect(
    screen.getByRole("button", { name: "Apply purchase context" }),
  ).toBeDisabled();
  expect(screen.getByLabelText(/Replace acquisition date/)).not.toBeChecked();
  await userEvent.click(screen.getByLabelText(/Replace known Supplier/));
  await userEvent.click(
    screen.getByRole("button", { name: "Apply purchase context" }),
  );
  expect(applyPurchase).toHaveBeenCalledWith(
    orderId,
    expect.objectContaining({
      use_order_supplier: true,
      use_order_date: false,
      context: {
        source_kind: "purchased_fruit",
        supplier_id: seedId,
        acquisition_date: { precision: "year", year: 2025 },
      },
    }),
    "csrf",
  );
});
test("incompatible source displays server explanation and blocks Apply", async () => {
  mount({
    ...review,
    can_apply: false,
    conflict: "Correct its source explicitly in normal SeedLot edit first.",
    current: { source_kind: "self_collected" },
    proposed_source: "self_collected",
  });
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Correct its source",
  );
  expect(
    screen.getByRole("button", { name: "Apply purchase context" }),
  ).toBeDisabled();
  expect(applyPurchase).not.toHaveBeenCalled();
});
test("matching Supplier/date offers no replacement controls", async () => {
  mount({
    ...review,
    supplier_action: "keep",
    date_action: "keep",
    current: {
      source_kind: "purchased",
      supplier_id: orderId,
      acquisition_date: review.order.ordered_on,
    },
  });
  await screen.findByText("PO-1");
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
});
test("stale Apply exposes conflict and refreshes authoritative acquisition before another Apply", async () => {
  vi.mocked(applyPurchase).mockRejectedValueOnce(
    new ApiError(409, null, {
      detail: {
        code: "stale_purchase_context",
        message:
          "Order or SeedLot changed. Nothing applied; refresh and preview again.",
      },
    }),
  );
  mount();
  await screen.findByText("PO-1");
  await userEvent.click(
    screen.getByRole("button", { name: "Apply purchase context" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent("Nothing applied");
  expect(onApplied).not.toHaveBeenCalled();
  await userEvent.click(
    screen.getByRole("button", { name: "Refresh purchase preview" }),
  );
  await waitFor(() => {
    expect(previewPurchase).toHaveBeenLastCalledWith(
      orderId,
      { seed_lot_id: seedId },
      expect.any(AbortSignal),
    );
  });
});
test("Order reverse selector searches bounded choices then opens the same preview without applying", async () => {
  vi.mocked(purchaseChoices).mockResolvedValue({
    items: [
      {
        id: seedId,
        label: "Physical packet",
        source_kind: "unknown",
        supplier: null,
        order_id: null,
      },
    ],
    total: 51,
    offset: 0,
    limit: 50,
  });
  render(
    <LinkExistingSeedLot
      orderId={orderId}
      csrf="csrf"
      onApplied={onApplied}
      onCancel={onCancel}
    />,
  );
  await userEvent.click(
    await screen.findByRole("button", { name: "Next seed choices" }),
  );
  await waitFor(() => {
    expect(purchaseChoices).toHaveBeenLastCalledWith(
      orderId,
      "",
      50,
      expect.any(AbortSignal),
    );
  });
  await userEvent.type(
    screen.getByRole("searchbox", { name: "Find a seed lot" }),
    "packet",
  );
  await waitFor(() => {
    expect(purchaseChoices).toHaveBeenLastCalledWith(
      orderId,
      "packet",
      0,
      expect.any(AbortSignal),
    );
  });
  await userEvent.click(
    await screen.findByRole("button", { name: "Physical packet" }),
  );
  const dialog = await screen.findByRole("dialog", {
    name: "Review purchase context",
  });
  expect(await within(dialog).findByText("PO-1")).toBeVisible();
  expect(
    within(dialog).getByRole("link", { name: "Physical packet" }),
  ).toHaveAttribute("href", `#/seeds/${seedId}`);
  expect(previewPurchase).toHaveBeenLastCalledWith(
    orderId,
    expect.objectContaining({ seed_lot_id: seedId }),
    expect.any(AbortSignal),
  );
  expect(applyPurchase).not.toHaveBeenCalled();
});
