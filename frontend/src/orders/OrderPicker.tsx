import { ActionButton } from "../components/Action";
import { useEffect, useState, type ReactNode } from "react";
import { OrderTransaction } from "./PurchaseContext";
import { getOrder, listOrders, orderDate, orderTitle, type Order } from "./api";

/** Bounded, searchable transaction selection in the normal SeedLot editor. */
export function OrderPicker({
  value,
  onChange,
  disabled,
  supplierId = "",
  refreshKey = "",
  independentFields,
  retainedKnowledge,
  reviewAction,
}: {
  value: string;
  onChange: (id: string) => void;
  disabled: boolean;
  supplierId?: string;
  refreshKey?: string;
  independentFields?: ReactNode;
  retainedKnowledge?: ReactNode;
  reviewAction?: ReactNode;
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
    <fieldset
      className={`form-section${independentFields ? " acquisition-order" : ""}`}
    >
      <legend>Purchase Order</legend>
      {!independentFields && (
        <p className="field-help">
          Linking opens a review before changing recorded knowledge.
        </p>
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
      {selected?.id === value && !independentFields && (
        <OrderTransaction order={selected} />
      )}
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
      {loading && <p role="status">Loading Order choices…</p>}
      <div className="actions">
        {supplierId && (
          <label className="checkbox-field">
            <input
              type="checkbox"
              aria-label="Show all Suppliers’ Orders (including unknown or conflicting Suppliers)"
              checked={allSuppliers}
              disabled={disabled}
              onChange={(event) => {
                setAllSuppliers(event.currentTarget.checked);
                setOffset(0);
              }}
            />{" "}
            {independentFields
              ? "All Suppliers’ Orders"
              : "Show all Suppliers’ Orders (including unknown or conflicting Suppliers)"}
          </label>
        )}

        <a
          href="#/orders?action=create"
          target="_blank"
          rel="noopener noreferrer"
        >
          Create Order (new tab)
        </a>
        <ActionButton
          icon="refresh"
          type="button"
          disabled={disabled || loading}
          onClick={() => {
            setAttempt((current) => current + 1);
          }}
        >
          Refresh Order choices
        </ActionButton>
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
      {independentFields &&
        (!value ? (
          <div className="acquisition-independent">{independentFields}</div>
        ) : selected?.id === value ? (
          <section
            className="acquisition-linked"
            aria-label="Order transaction information"
          >
            <dl className="acquisition-transaction-facts">
              <div aria-label="Supplier from linked Order">
                <dt>Supplier</dt>
                <dd>
                  {selected.supplier ? (
                    <a href={`#/suppliers/${selected.supplier.id}`}>
                      {selected.supplier.name}
                    </a>
                  ) : (
                    "Not recorded"
                  )}
                </dd>
                <dd className="field-help">From linked Order</dd>
              </div>
              <div>
                <dt>Order date</dt>
                <dd>{orderDate(selected.ordered_on)}</dd>
                <dd className="field-help">From linked Order</dd>
              </div>
            </dl>
            {retainedKnowledge}
            <div className="acquisition-linked-actions">
              <a href={`#/orders/${selected.id}`}>{orderTitle(selected)}</a>
              {reviewAction}
              <p className="field-help">Unlink keeps recorded lot facts.</p>
            </div>
          </section>
        ) : null)}
    </fieldset>
  );
}
