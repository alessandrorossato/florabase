import { useEffect, useRef, useState, type SyntheticEvent } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { DirectoryResults } from "../components/DirectoryResults";
import { DirectorySearch, PageHeader } from "../components/ReferenceUI";
import { TaskDialog } from "../components/TaskDialog";
import { PartialDateField } from "../seed-lots/PartialDateField";
import { ReferencePicker } from "../seed-lots/ReferencePicker";
import { SavedViews } from "../saved-views/SavedViews";
import { useDirectoryView } from "../saved-views/useDirectoryView";
import { listSuppliers, type SupplierListResponse } from "../suppliers/api";
import {
  deleteOrder,
  getOrder,
  listOrders,
  orderDate,
  orderError,
  orderPrice,
  orderTitle,
  saveOrder,
  type OrderCreate,
  type OrderDetail,
  type OrderPage,
} from "./api";
import { LinkExistingSeedLot } from "./PurchaseContext";
import "./orders.css";

function OrderForm({
  initial,
  suppliers,
  pending,
  onSave,
  onCancel,
}: {
  initial?: OrderDetail;
  suppliers: SupplierListResponse[];
  pending: boolean;
  onSave: (payload: OrderCreate) => void;
  onCancel: () => void;
}) {
  const [supplier, setSupplier] = useState(initial?.supplier_id ?? "");
  const [date, setDate] = useState(initial?.ordered_on ?? null);
  const [dirty, setDirty] = useState(false);
  function cancel() {
    if (!dirty || window.confirm("Discard unsaved Order changes?")) onCancel();
  }
  function submit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (pending) return;
    const data = new FormData(event.currentTarget);
    const field = (name: string) => {
      const value = data.get(name);
      return typeof value === "string" ? value : "";
    };
    const price = field("price").trim();
    onSave({
      supplier_id: supplier || null,
      ordered_on: date,
      order_reference: field("reference") || null,
      total_price: price || null,
      currency: field("currency") || null,
      notes: field("notes") || null,
    });
  }
  return (
    <form
      onSubmit={submit}
      onChange={() => {
        setDirty(true);
      }}
    >
      <fieldset disabled={pending} className="form-section">
        <legend>{initial ? "Edit Order" : "New Order"}</legend>
        <p>
          Record one purchase transaction. Physical seed lots are added
          separately.
        </p>
        <ReferencePicker
          label="Supplier (optional)"
          choices={suppliers.map((item) => ({
            id: item.id,
            label: item.name,
            retired: Boolean(item.retired_at),
          }))}
          value={supplier}
          onChange={(id) => {
            setSupplier(id);
            setDirty(true);
          }}
        />
        <PartialDateField
          id="order-date"
          label="Order date"
          value={date}
          disabled={pending}
          onChange={(value) => {
            setDate(value);
            setDirty(true);
          }}
        />
        <div className="field">
          <label htmlFor="order-reference">Order reference (optional)</label>
          <input
            id="order-reference"
            name="reference"
            maxLength={255}
            defaultValue={initial?.order_reference ?? ""}
          />
        </div>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="order-price">Total price (optional)</label>
            <input
              id="order-price"
              name="price"
              type="text"
              inputMode="decimal"
              pattern="[0-9]{1,24}(\.[0-9]{1,24})?"
              defaultValue={initial?.total_price ?? ""}
              aria-describedby="order-price-help"
            />
          </div>
          <div className="field">
            <label htmlFor="order-currency">Currency</label>
            <input
              id="order-currency"
              name="currency"
              maxLength={3}
              pattern="[A-Z]{3}"
              placeholder="EUR"
              defaultValue={initial?.currency ?? ""}
              aria-describedby="order-price-help"
            />
          </div>
        </div>
        <p id="order-price-help" className="field-help">
          Use an exact amount and a three-letter uppercase currency together, or
          leave both blank. This is the total transaction price.
        </p>
        <div className="field">
          <label htmlFor="order-notes">Notes (optional)</label>
          <textarea
            id="order-notes"
            name="notes"
            maxLength={20000}
            defaultValue={initial?.notes ?? ""}
            rows={4}
          />
        </div>
      </fieldset>
      <div className="actions form-actions">
        <button type="submit" disabled={pending}>
          {pending ? "Saving…" : initial ? "Save changes" : "Create Order"}
        </button>
        <button
          className="button--secondary"
          type="button"
          disabled={pending}
          onClick={cancel}
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

export function OrderScreen({ initialId }: { initialId?: string } = {}) {
  const auth = useAuth();
  const [offset, setOffset] = useState(0);
  const [lotOffset, setLotOffset] = useState(0);
  const view = useDirectoryView("orders", () => {
    setOffset(0);
  });
  const [storedPage, setPage] = useState<OrderPage | null>(null);
  const [storedDetail, setDetail] = useState<OrderDetail | null>(null);
  const [suppliers, setSuppliers] = useState<SupplierListResponse[] | null>(
    null,
  );
  const [loadError, setLoadError] = useState("");
  const [suppliersError, setSuppliersError] = useState("");
  const [loadedKey, setLoadedKey] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [linking, setLinking] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [attempt, setAttempt] = useState(0);
  const requestKey = `${initialId ?? ""}:${view.state.q}:${view.state.supplier_id}:${String(offset)}:${String(lotOffset)}:${String(attempt)}`;
  const page = loadedKey === requestKey ? storedPage : null;
  const detail = loadedKey === requestKey ? storedDetail : null;
  const visibleLoadError =
    suppliersError || (loadedKey === requestKey ? loadError : "");
  const feedback = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (error) feedback.current?.focus();
  }, [error]);
  useEffect(() => {
    const controller = new AbortController();
    listSuppliers(controller.signal)
      .then((items) => {
        if (!controller.signal.aborted) {
          setSuppliers(items);
          setSuppliersError("");
        }
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          if (error instanceof ApiError && error.status === 401)
            auth.sessionExpired();
          else setSuppliersError("Florabase could not load Suppliers.");
        }
      });
    return () => {
      controller.abort();
    };
  }, [auth, attempt]);
  useEffect(() => {
    const controller = new AbortController();
    const request = initialId
      ? getOrder(initialId, lotOffset, controller.signal).then((item) => {
          if (!controller.signal.aborted) setDetail(item);
        })
      : listOrders(
          view.state.q,
          view.state.supplier_id,
          offset,
          controller.signal,
        ).then((item) => {
          if (!controller.signal.aborted) setPage(item);
        });
    request
      .then(() => {
        if (!controller.signal.aborted) {
          setLoadError("");
          setLoadedKey(requestKey);
        }
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else {
          setLoadedKey(requestKey);
          setLoadError(
            error instanceof ApiError && error.status === 404
              ? "Order not found."
              : "Florabase could not load Orders.",
          );
        }
      });
    return () => {
      controller.abort();
    };
  }, [
    auth,
    initialId,
    view.state.q,
    view.state.supplier_id,
    offset,
    lotOffset,
    attempt,
    requestKey,
  ]);
  if (
    auth.state.status !== "authenticated" &&
    auth.state.status !== "logging-out" &&
    auth.state.status !== "logout-failed"
  )
    return null;
  const csrf = auth.state.csrfToken;
  async function save(payload: OrderCreate) {
    setPending(true);
    setError("");
    try {
      const result = await saveOrder(initialId, payload, csrf);
      setFormOpen(false);
      setSuccess(initialId ? "Order updated." : "Order created.");
      if (initialId) setAttempt((value) => value + 1);
      else window.location.hash = `#/orders/${result.id}`;
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else setError(orderError(error));
    } finally {
      setPending(false);
    }
  }
  async function remove() {
    if (!initialId || pending) return;
    setPending(true);
    setError("");
    try {
      await deleteOrder(initialId, csrf);
      window.location.hash = "#/orders";
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else setError(orderError(error));
    } finally {
      setPending(false);
    }
  }
  return (
    <section className="workspace orders-page" aria-labelledby="orders-title">
      <PageHeader
        eyebrow="Sourcing"
        title={initialId ? (detail ? orderTitle(detail) : "Order") : "Orders"}
        titleId="orders-title"
        description="Track purchase transactions and the physical seed lots acquired through them."
        actions={
          initialId ? (
            <a href="#/orders">All Orders</a>
          ) : (
            <button
              type="button"
              disabled={!suppliers}
              onClick={() => {
                setError("");
                setFormOpen(true);
              }}
            >
              + New Order
            </button>
          )
        }
      />
      {success && (
        <p className="notice notice--success" role="status">
          {success}
        </p>
      )}
      {visibleLoadError ? (
        <div role="alert" className="notice notice--error">
          <p>{visibleLoadError}</p>
          <button
            type="button"
            onClick={() => {
              setAttempt((value) => value + 1);
            }}
          >
            Retry Orders
          </button>
          {initialId && <a href="#/orders">Return to Orders</a>}
        </div>
      ) : initialId ? (
        detail ? (
          <>
            <div className="actions">
              <a
                className="button-link"
                href={`#/seeds?action=create&order=${detail.id}`}
              >
                Add seed lot
              </a>
              <button
                type="button"
                className="button--secondary"
                onClick={() => {
                  setLinking(true);
                }}
              >
                Link existing seed lot
              </button>
              <button
                className="button--secondary"
                type="button"
                disabled={!suppliers}
                onClick={() => {
                  setError("");
                  setFormOpen(true);
                }}
              >
                Edit Order
              </button>
              <button
                className="button--secondary"
                type="button"
                disabled={detail.seed_lot_count > 0}
                aria-describedby="order-delete-help"
                onClick={() => {
                  setError("");
                  setDeleting(true);
                }}
              >
                Delete Order
              </button>
            </div>
            <p id="order-delete-help" className="field-help">
              {detail.seed_lot_count
                ? "Linked seed lots retain this transaction. Unlink them in Seed lot edit before deleting."
                : "Only Orders without linked seed lots can be deleted."}
            </p>
            <dl className="order-facts">
              <div>
                <dt>Supplier</dt>
                <dd>
                  {detail.supplier ? (
                    <a href={`#/suppliers/${detail.supplier.id}`}>
                      {detail.supplier.name}
                    </a>
                  ) : (
                    "Supplier unknown"
                  )}
                </dd>
              </div>
              <div>
                <dt>Order date</dt>
                <dd>{orderDate(detail.ordered_on)}</dd>
              </div>
              <div>
                <dt>Reference</dt>
                <dd>{detail.order_reference ?? "Not recorded"}</dd>
              </div>
              <div>
                <dt>Total price</dt>
                <dd>{orderPrice(detail)}</dd>
              </div>
            </dl>
            {detail.notes && (
              <section className="record-section">
                <h3>Notes</h3>
                <p className="preserve-lines">{detail.notes}</p>
              </section>
            )}
            <section
              className="record-section"
              aria-labelledby="order-lots-title"
            >
              <h3 id="order-lots-title">
                Physical seed lots ({detail.seed_lots_total})
              </h3>
              <p className="field-help">
                Each lot remains independent. Link here or from SeedLot
                Acquisition; unlink in SeedLot edit.
              </p>
              {detail.seed_lots_total === 0 ? (
                <p className="empty-state">No seed lots linked yet.</p>
              ) : (
                <ul className="order-list">
                  {detail.seed_lots.map((lot) => (
                    <li key={lot.id}>
                      <a href={`#/seeds/${lot.id}`}>
                        {lot.label ?? lot.botanical_identity.display_label}
                      </a>
                      <span>
                        {lot.botanical_identity.display_label} · {lot.lifecycle}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              <div className="actions">
                {lotOffset > 0 && (
                  <button
                    type="button"
                    onClick={() => {
                      setLotOffset((value) =>
                        Math.max(0, value - detail.seed_lots_limit),
                      );
                    }}
                  >
                    Previous seed lots
                  </button>
                )}
                {lotOffset + detail.seed_lots.length <
                  detail.seed_lots_total && (
                  <button
                    type="button"
                    onClick={() => {
                      setLotOffset((value) => value + detail.seed_lots_limit);
                    }}
                  >
                    Next seed lots
                  </button>
                )}
              </div>
            </section>
          </>
        ) : (
          <p role="status">Loading Order…</p>
        )
      ) : (
        <>
          <SavedViews surface="orders" state={view.savedState} />
          <div className="order-controls">
            <DirectorySearch
              id="order-search"
              label="Search Orders"
              placeholder="Reference, Supplier or notes"
              value={view.state.q}
              onChange={(value) => {
                view.update("q", value);
                setOffset(0);
              }}
            />
            <div className="field">
              <label htmlFor="orders-supplier">Supplier</label>
              <select
                id="orders-supplier"
                value={view.state.supplier_id}
                onChange={(event) => {
                  view.update("supplier_id", event.currentTarget.value);
                  setOffset(0);
                }}
              >
                <option value="">All Suppliers</option>
                {view.state.supplier_id &&
                  !suppliers?.some(
                    (item) => item.id === view.state.supplier_id,
                  ) && (
                    <option value={view.state.supplier_id}>
                      Unavailable Supplier — {view.state.supplier_id}
                    </option>
                  )}
                {suppliers?.map((item) => (
                  <option value={item.id} key={item.id}>
                    {item.name}
                    {item.retired_at ? " (retired)" : ""}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {!page ? (
            <p role="status">Loading Orders…</p>
          ) : (
            <>
              <DirectoryResults count={page.items.length} total={page.total} />
              {page.total === 0 ? (
                <div className="empty-state">
                  <h3>No Orders found</h3>
                  <p>
                    {view.state.q || view.state.supplier_id
                      ? "Try another search or Supplier."
                      : "Record a purchase, then add or link its physical seed lots."}
                  </p>
                </div>
              ) : (
                <ul className="order-list">
                  {page.items.map((order) => (
                    <li key={order.id}>
                      <div>
                        <a href={`#/orders/${order.id}`}>{orderTitle(order)}</a>
                        <span>
                          {orderDate(order.ordered_on)} ·{" "}
                          {order.supplier?.name ?? "Supplier unknown"}
                        </span>
                      </div>
                      <div>
                        <strong>{orderPrice(order)}</strong>
                        <span>
                          {order.seed_lot_count} seed{" "}
                          {order.seed_lot_count === 1 ? "lot" : "lots"}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
              <div className="actions">
                {offset > 0 && (
                  <button
                    type="button"
                    onClick={() => {
                      setOffset((value) => Math.max(0, value - page.limit));
                    }}
                  >
                    Previous Orders
                  </button>
                )}
                {offset + page.items.length < page.total && (
                  <button
                    type="button"
                    onClick={() => {
                      setOffset((value) => value + page.limit);
                    }}
                  >
                    Next Orders
                  </button>
                )}
              </div>
            </>
          )}
        </>
      )}
      {linking && initialId && (
        <LinkExistingSeedLot
          orderId={initialId}
          csrf={csrf}
          onCancel={() => {
            setLinking(false);
          }}
          onApplied={() => {
            setLinking(false);
            setAttempt((value) => value + 1);
            setSuccess("SeedLot purchase context linked.");
          }}
        />
      )}
      {formOpen && suppliers && (
        <TaskDialog
          title={initialId ? "Edit Order" : "New Order"}
          onClose={() => {
            if (!pending && window.confirm("Discard unsaved Order changes?"))
              setFormOpen(false);
          }}
        >
          <OrderForm
            initial={detail ?? undefined}
            suppliers={suppliers}
            pending={pending}
            onSave={(payload) => void save(payload)}
            onCancel={() => {
              setFormOpen(false);
            }}
          />
          {error && (
            <div
              ref={feedback}
              role="alert"
              tabIndex={-1}
              className="notice notice--error"
            >
              {error}
            </div>
          )}
        </TaskDialog>
      )}
      {deleting && (
        <TaskDialog
          title="Delete Order"
          onClose={() => {
            if (!pending) setDeleting(false);
          }}
        >
          <h3>Delete this Order?</h3>
          <p>
            This removes the transaction permanently. Linked Orders cannot be
            deleted.
          </p>
          {error && (
            <div ref={feedback} role="alert" tabIndex={-1}>
              {error}
            </div>
          )}
          <div className="actions">
            <button
              type="button"
              disabled={pending}
              onClick={() => void remove()}
            >
              {pending ? "Deleting…" : "Confirm delete"}
            </button>
            <button
              className="button--secondary"
              type="button"
              disabled={pending}
              onClick={() => {
                setDeleting(false);
              }}
            >
              Cancel
            </button>
          </div>
        </TaskDialog>
      )}
    </section>
  );
}
