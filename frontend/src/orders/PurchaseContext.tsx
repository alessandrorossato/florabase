import "./orders.css";
import { useEffect, useState } from "react";
import { TaskDialog } from "../components/TaskDialog";
import {
  orderDate,
  orderError,
  orderPrice,
  orderTitle,
  type Order,
} from "./api";
import {
  applyPurchase,
  previewPurchase,
  purchaseChoices,
  type AcquisitionContext,
  type PurchasePreview,
  type PurchaseResolution,
  type PurchaseSeedPage,
} from "./purchaseApi";

export function OrderTransaction({ order }: { order: Order }) {
  return (
    <section
      className="order-transaction"
      aria-label="Order transaction information"
    >
      <h4>Order transaction information</h4>
      <a href={`#/orders/${order.id}`}>{orderTitle(order)}</a>
      <dl>
        <div>
          <dt>Order Supplier</dt>
          <dd>{order.supplier?.name ?? "Supplier unknown"}</dd>
        </div>
        <div>
          <dt>Order date</dt>
          <dd>{orderDate(order.ordered_on)}</dd>
        </div>
        <div>
          <dt>Order total</dt>
          <dd>{orderPrice(order)}</dd>
        </div>
      </dl>
      <p className="field-help">
        Total transaction information only; this is not the price of this seed
        lot. No allocation or division between lots.
      </p>
    </section>
  );
}
const sourceName = (value: string) => value.replaceAll("_", " ");
export function PurchaseContextDialog({
  orderId,
  seedLotId,
  seedLotLabel,
  context,
  expectedSeedVersion,
  csrf,
  onApplied,
  onCancel,
}: {
  orderId: string;
  seedLotId?: string;
  seedLotLabel?: string;
  context?: AcquisitionContext;
  expectedSeedVersion?: string;
  csrf: string;
  onApplied: (result: PurchaseResolution) => void;
  onCancel: () => void;
}) {
  const [review, setReview] = useState<PurchasePreview | null>(null);
  const [useSupplier, setUseSupplier] = useState(false);
  const [useDate, setUseDate] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [attempt, setAttempt] = useState(0);
  // Capture the invocation draft. Refresh deliberately previews current stored acquisition fields.
  const [initial] = useState({
    context,
    seed_lot_id: seedLotId,
    expected_seed_lot_updated_at: expectedSeedVersion,
  });
  useEffect(() => {
    const controller = new AbortController();
    previewPurchase(
      orderId,
      attempt && seedLotId ? { seed_lot_id: seedLotId } : initial,
      controller.signal,
    )
      .then((result) => {
        if (controller.signal.aborted) return;
        setReview(result);
        setUseSupplier(result.supplier_action === "fill");
        setUseDate(false);
        setError("");
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setError(orderError(error));
      });
    return () => {
      controller.abort();
    };
  }, [orderId, seedLotId, attempt, initial]);
  async function apply() {
    if (!review || pending) return;
    setPending(true);
    setError("");
    try {
      const result = await applyPurchase(
        orderId,
        {
          seed_lot_id: review.seed_lot_id,
          context: review.current,
          expected_seed_lot_updated_at: review.seed_lot_updated_at,
          expected_order_updated_at: review.order.updated_at,
          use_order_supplier: useSupplier,
          use_order_date: useDate,
        },
        csrf,
      );
      onApplied(result);
    } catch (error: unknown) {
      setError(orderError(error));
    } finally {
      setPending(false);
    }
  }
  return (
    <TaskDialog
      title="Review purchase context"
      onClose={() => {
        if (!pending) onCancel();
      }}
    >
      <h3>Review purchase context</h3>
      {review ? (
        <>
          <p className="purchase-target">
            {seedLotId ? (
              <>
                Physical seed lot:{" "}
                <a href={`#/seeds/${seedLotId}`}>{seedLotLabel ?? seedLotId}</a>
              </>
            ) : (
              "New physical seed lot draft"
            )}
          </p>
          <OrderTransaction order={review.order} />
          {review.current.order_id && review.current.order_id !== orderId && (
            <p>
              This replaces the current Order link ({review.current.order_id}).
            </p>
          )}
          {review.stored &&
            (review.stored.source_kind !== review.current.source_kind ||
              review.stored.supplier_id !== review.current.supplier_id ||
              JSON.stringify(review.stored.acquisition_date) !==
                JSON.stringify(review.current.acquisition_date)) && (
              <p className="notice">
                Saved acquisition context:{" "}
                {sourceName(review.stored.source_kind)} ·{" "}
                {review.stored_supplier?.name ?? "Supplier unknown"} ·{" "}
                {orderDate(review.stored.acquisition_date)}. The changes below
                include your acquisition draft; Apply saves them now.
              </p>
            )}
          <dl className="purchase-changes">
            <div>
              <dt>Source</dt>
              <dd>
                {sourceName(review.current.source_kind)} →{" "}
                {sourceName(review.proposed_source)}
              </dd>
            </div>
            <div>
              <dt>SeedLot Supplier</dt>
              <dd>
                {review.current_supplier?.name ?? "Unknown"} →{" "}
                {useSupplier
                  ? review.order.supplier?.name
                  : (review.current_supplier?.name ?? "Unknown")}
              </dd>
            </div>
            <div>
              <dt>Acquisition date</dt>
              <dd>
                {orderDate(review.current.acquisition_date)} →{" "}
                {orderDate(
                  useDate
                    ? review.order.ordered_on
                    : review.current.acquisition_date,
                )}
              </dd>
            </div>
          </dl>
          {review.supplier_action !== "keep" && (
            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={useSupplier}
                disabled={pending}
                onChange={(event) => {
                  setUseSupplier(event.currentTarget.checked);
                }}
              />{" "}
              {review.supplier_action === "replace"
                ? "Replace known Supplier: use Order supplier"
                : "Fill unknown Supplier from Order"}
            </label>
          )}
          {review.date_action !== "keep" && (
            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={useDate}
                disabled={pending}
                onChange={(event) => {
                  setUseDate(event.currentTarget.checked);
                }}
              />{" "}
              {review.date_action === "replace"
                ? "Replace acquisition date with Order date"
                : "Use Order date as acquisition date"}{" "}
              (proposed copy; receipt may be later)
            </label>
          )}
          {review.conflict && (
            <p role="alert" className="notice notice--error">
              {review.conflict}
            </p>
          )}
          <p>
            Identity, quantity, Origin/provenance, Location, harvest date and
            lineage stay unchanged.
          </p>
          <p className="field-help">
            {seedLotId
              ? "Apply saves these acquisition fields now. Other form drafts remain unsaved."
              : "Apply prepares this draft. The SeedLot is saved only when you create it; Order changes are checked again then."}
          </p>
        </>
      ) : (
        <p role="status">Loading purchase preview…</p>
      )}
      {error && (
        <p role="alert" className="notice notice--error">
          {error}
        </p>
      )}
      <div className="actions">
        <button
          type="button"
          disabled={
            pending ||
            !review?.can_apply ||
            (review.supplier_action === "replace" && !useSupplier)
          }
          onClick={() => void apply()}
        >
          {pending ? "Applying…" : "Apply purchase context"}
        </button>
        <button
          type="button"
          className="button--secondary"
          disabled={pending}
          onClick={onCancel}
        >
          Cancel
        </button>
        {error && (
          <button
            type="button"
            disabled={pending}
            onClick={() => {
              setReview(null);
              setAttempt((value) => value + 1);
            }}
          >
            Refresh purchase preview
          </button>
        )}
      </div>
    </TaskDialog>
  );
}

export function LinkExistingSeedLot({
  orderId,
  csrf,
  onApplied,
  onCancel,
}: {
  orderId: string;
  csrf: string;
  onApplied: () => void;
  onCancel: () => void;
}) {
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<PurchaseSeedPage | null>(null);
  const [loaded, setLoaded] = useState("");
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [seedId, setSeedId] = useState("");
  const [seedLabel, setSeedLabel] = useState("");
  const key = `${q}:${String(offset)}:${String(attempt)}`;
  useEffect(() => {
    const controller = new AbortController();
    purchaseChoices(orderId, q, offset, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) {
          setPage(result);
          setLoaded(key);
          setError("");
        }
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setError(orderError(error));
          setLoaded(key);
        }
      });
    return () => {
      controller.abort();
    };
  }, [orderId, q, offset, attempt, key]);
  if (seedId)
    return (
      <PurchaseContextDialog
        orderId={orderId}
        seedLotId={seedId}
        seedLotLabel={seedLabel}
        csrf={csrf}
        onApplied={onApplied}
        onCancel={() => {
          setSeedId("");
        }}
      />
    );
  const current = loaded === key ? page : null;
  return (
    <TaskDialog title="Link existing seed lot" onClose={onCancel}>
      <h3>Link existing seed lot</h3>
      <p>
        Purchased, purchased-fruit and Unknown sources are eligible for review.
        Other sources must be corrected explicitly in SeedLot edit first.
      </p>
      <label htmlFor="purchase-seed-search">Find a seed lot</label>
      <input
        id="purchase-seed-search"
        type="search"
        maxLength={200}
        value={q}
        onChange={(event) => {
          setQ(event.currentTarget.value);
          setOffset(0);
        }}
      />
      {error ? (
        <div role="alert">
          {error}
          <button
            type="button"
            onClick={() => {
              setAttempt((value) => value + 1);
            }}
          >
            Retry seed lots
          </button>
        </div>
      ) : !current ? (
        <p role="status">Loading seed lots…</p>
      ) : (
        <>
          <p>{current.total} eligible physical seed lots</p>
          <ul className="order-list">
            {current.items.map((lot) => (
              <li key={lot.id}>
                <button
                  type="button"
                  onClick={() => {
                    setSeedLabel(lot.label);
                    setSeedId(lot.id);
                  }}
                >
                  {lot.label}
                </button>
                <span>
                  {sourceName(lot.source_kind)} ·{" "}
                  {lot.supplier?.name ?? "Supplier unknown"}
                  {lot.order_id ? " · Already linked to an Order" : ""}
                </span>
              </li>
            ))}
          </ul>
          <div className="actions">
            {offset > 0 && (
              <button
                type="button"
                onClick={() => {
                  setOffset((value) => Math.max(0, value - 50));
                }}
              >
                Previous seed choices
              </button>
            )}
            {offset + current.items.length < current.total && (
              <button
                type="button"
                onClick={() => {
                  setOffset((value) => value + 50);
                }}
              >
                Next seed choices
              </button>
            )}
          </div>
        </>
      )}
      <button type="button" className="button--secondary" onClick={onCancel}>
        Cancel
      </button>
    </TaskDialog>
  );
}
