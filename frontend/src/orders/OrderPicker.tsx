import { useEffect, useState } from "react";
import { OrderTransaction } from "./PurchaseContext";
import { getOrder, listOrders, orderDate, orderTitle, type Order } from "./api";

/** Bounded, searchable transaction selection in the normal SeedLot editor. */
export function OrderPicker({
  value,
  onChange,
  disabled,
  supplierId = "",
  refreshKey = "",
}: {
  value: string;
  onChange: (id: string) => void;
  disabled: boolean;
  supplierId?: string;
  refreshKey?: string;
}) {
  const [allSuppliers, setAllSuppliers] = useState(false);
  const supplierFilter = allSuppliers ? "" : supplierId;
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [items, setItems] = useState<Order[]>([]);
  const [selected, setSelected] = useState<Order | null>(null);
  const [contextError, setContextError] = useState("");
  const [total, setTotal] = useState(0);
  const [loadedKey, setLoadedKey] = useState("");
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const requestKey = `${query}:${supplierFilter}:${String(offset)}:${String(attempt)}`;
  const loading = loadedKey !== requestKey;
  useEffect(() => {
    const controller = new AbortController();
    listOrders(query, supplierFilter, offset, controller.signal)
      .then((page) => {
        if (controller.signal.aborted) return;
        setItems(page.items);
        setTotal(page.total);
        setLoadedKey(requestKey);
        setError(false);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setError(true);
          setLoadedKey(requestKey);
        }
      });
    return () => {
      controller.abort();
    };
  }, [query, supplierFilter, offset, attempt, requestKey]);
  useEffect(() => {
    if (!value) return;
    const controller = new AbortController();
    getOrder(value, 0, controller.signal)
      .then((order) => {
        if (!controller.signal.aborted) {
          setSelected(order);
          setContextError("");
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setSelected(null);
          setContextError(value);
        }
      });
    return () => {
      controller.abort();
    };
  }, [value, refreshKey, attempt]);
  const currentItems = loading ? [] : items;
  const choices =
    selected?.id === value &&
    !currentItems.some((item) => item.id === selected.id)
      ? [selected, ...currentItems]
      : currentItems;
  return (
    <fieldset className="form-section">
      <legend>Purchase Order (optional)</legend>
      <p className="field-help">
        Selection opens a purchase-context review. Unknown sources may become
        Purchased; known incompatible sources require explicit correction first.
      </p>
      {supplierId && (
        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={allSuppliers}
            disabled={disabled}
            onChange={(event) => {
              setAllSuppliers(event.currentTarget.checked);
              setOffset(0);
            }}
          />{" "}
          Show all Suppliers’ Orders (including unknown or conflicting
          Suppliers)
        </label>
      )}
      <div className="field">
        <label htmlFor="seed-order-search">Find an Order</label>
        <input
          id="seed-order-search"
          type="search"
          maxLength={200}
          placeholder="Reference, Supplier or notes"
          value={query}
          disabled={disabled}
          onChange={(event) => {
            setQuery(event.currentTarget.value);
            setOffset(0);
          }}
        />
      </div>
      {error && (
        <div role="alert">
          Could not load Orders.{" "}
          <button
            type="button"
            onClick={() => {
              setAttempt((value) => value + 1);
            }}
          >
            Retry Order choices
          </button>
        </div>
      )}
      <div className="field">
        <label htmlFor="seed-order">Order</label>
        <select
          id="seed-order"
          value={value}
          disabled={disabled}
          onChange={(event) => {
            onChange(event.currentTarget.value);
          }}
        >
          <option value="">No Order</option>
          {value && !choices.some((item) => item.id === value) && (
            <option value={value}>Linked Order — {value}</option>
          )}
          {choices.map((item) => (
            <option value={item.id} key={item.id}>
              {orderTitle(item)} · {orderDate(item.ordered_on)} ·{" "}
              {item.supplier?.name ?? "Supplier unknown"}
            </option>
          ))}
        </select>
      </div>
      {selected?.id === value && <OrderTransaction order={selected} />}
      {value &&
        selected?.id !== value &&
        (contextError === value ? (
          <div role="alert">
            Could not load Order transaction information.{" "}
            <button
              type="button"
              disabled={disabled}
              onClick={() => {
                setAttempt((current) => current + 1);
              }}
            >
              Retry transaction information
            </button>
          </div>
        ) : (
          <p role="status">Loading Order transaction information…</p>
        ))}
      {value && (
        <p className="field-help">
          Unlinking removes only the Order relationship when saved. Confirmed
          Source, Supplier and acquisition date remain.
        </p>
      )}
      {loading && <p role="status">Loading Order choices…</p>}
      <div className="actions">
        {offset > 0 && (
          <button
            type="button"
            disabled={disabled || loading}
            onClick={() => {
              setOffset((value) => Math.max(0, value - 50));
            }}
          >
            Previous Order choices
          </button>
        )}
        {offset + items.length < total && (
          <button
            type="button"
            disabled={disabled || loading}
            onClick={() => {
              setOffset((value) => value + 50);
            }}
          >
            Next Order choices
          </button>
        )}
      </div>
    </fieldset>
  );
}
