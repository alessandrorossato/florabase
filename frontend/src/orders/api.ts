import type { components } from "../api/schema";
import { ApiError, requestJson } from "../auth/api";
export type Order = components["schemas"]["OrderResponse"];
export type OrderDetail = components["schemas"]["OrderDetailResponse"];
export type OrderPage = components["schemas"]["OrderPage"];
export type OrderCreate = components["schemas"]["OrderCreate"];

export function listOrders(
  q = "",
  supplierId = "",
  offset = 0,
  signal?: AbortSignal,
): Promise<OrderPage> {
  const params = new URLSearchParams({ offset: String(offset) });
  if (q.trim()) params.set("q", q.trim());
  if (supplierId) params.set("supplier_id", supplierId);
  return requestJson(`/api/v1/orders?${params}`, { signal });
}
export function getOrder(
  id: string,
  offset = 0,
  signal?: AbortSignal,
): Promise<OrderDetail> {
  return requestJson(
    `/api/v1/orders/${encodeURIComponent(id)}?seed_lots_offset=${String(offset)}`,
    { signal },
  );
}
export function saveOrder(
  id: string | undefined,
  payload: OrderCreate,
  csrf: string,
): Promise<Order> {
  return requestJson(
    `/api/v1/orders${id ? `/${encodeURIComponent(id)}` : ""}`,
    {
      method: id ? "PATCH" : "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
      body: JSON.stringify(payload),
    },
  );
}
export function deleteOrder(id: string, csrf: string): Promise<void> {
  return requestJson(`/api/v1/orders/${encodeURIComponent(id)}`, {
    method: "DELETE",
    headers: { "X-CSRF-Token": csrf },
  });
}
export function orderTitle(order: Pick<Order, "order_reference">): string {
  return order.order_reference ?? "Purchase order";
}
export function orderPrice(
  order: Pick<Order, "total_price" | "currency">,
): string {
  return order.total_price !== null
    ? `${order.currency ?? ""} ${order.total_price ?? ""}`
    : "Price unknown";
}
export function orderDate(date: Order["ordered_on"]): string {
  if (!date) return "Date unknown";
  const year = String(date.year).padStart(4, "0");
  if (date.precision === "year") return year;
  const month = String(date.month).padStart(2, "0");
  return date.precision === "month"
    ? `${year}-${month}`
    : `${year}-${month}-${String(date.day).padStart(2, "0")}`;
}
export function orderError(error: unknown): string {
  if (error instanceof ApiError) {
    const body = error.body as
      { detail?: { message?: string } | { msg: string }[] } | undefined;
    if (Array.isArray(body?.detail))
      return body.detail
        .map((item) => item.msg.replace(/^Value error, /, ""))
        .join(". ");
    if (body?.detail?.message) return body.detail.message;
    if (error.status === 403)
      return "Florabase could not authorize this change. Refresh the page and try again.";
  }
  return "Florabase could not complete this request. Check the connection and try again.";
}
