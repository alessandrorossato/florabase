import { ActionButton } from "../components/Action";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type MouseEventHandler,
  type RefObject,
  type SyntheticEvent,
} from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { DetailEmptyState } from "../components/DetailEmptyState";
import { DirectoryResults } from "../components/DirectoryResults";
import { DirectoryTools } from "../components/DirectoryTools";
import { EditWorkspace } from "../components/EditWorkspace";
import { FieldLabel } from "../components/FieldLabel";
import { DirectorySearch, RecordPreview } from "../components/ReferenceUI";
import { TaskDialog } from "../components/TaskDialog";
import { useCollectionPageReturnFocus } from "../components/useCollectionPageReturnFocus";
import { useEditRoute } from "../components/useEditRoute";
import {
  Breadcrumbs,
  CollectionCard,
  DetailHeader,
  DetailTabs,
  WorkspaceIntro,
} from "../components/CollectionUI";
import {
  closeCollectionPage,
  openCollectionPage,
  setRecordRoute,
} from "../components/recordNavigation";
import { RecordVisual } from "../photos/RecordVisual";
import { SavedViews } from "../saved-views/SavedViews";
import { useDirectoryView } from "../saved-views/useDirectoryView";
import { PartialDateField } from "../seed-lots/PartialDateField";
import { ReferencePicker } from "../seed-lots/ReferencePicker";
import type { PartialDate } from "../seed-lots/api";
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
  type Order,
  type OrderCreate,
  type OrderDetail,
  type OrderPage,
} from "./api";
import { LinkExistingSeedLot } from "./PurchaseContext";
import "./orders.css";

type OrderRecord = Order | OrderDetail;
type OrderTab = "overview" | "seed-lots";

const orderPage = {
  eyebrow: "Sourcing",
  title: "Orders",
  titleId: "orders-title",
  description:
    "Track purchase transactions and the physical seed lots acquired through them.",
};

const lifecycleLabels: Record<string, string> = {
  active: "Active",
  exhausted: "Exhausted",
  discarded: "Discarded",
  lost: "Lost",
  transferred: "Transferred",
  completed: "Completed",
  dead: "Dead",
  reversed: "Reversed",
  reintegrated: "Reintegrated",
};

interface OrderFormValues {
  supplier: string;
  orderedOn: PartialDate | null;
  reference: string;
  price: string;
  currency: string;
  notes: string;
}

function orderFormValues(initial?: OrderRecord): OrderFormValues {
  return {
    supplier: initial?.supplier_id ?? "",
    orderedOn: initial?.ordered_on ?? null,
    reference: initial?.order_reference ?? "",
    price: initial?.total_price ?? "",
    currency: initial?.currency ?? "",
    notes: initial?.notes ?? "",
  };
}

function orderPayload(values: OrderFormValues): OrderCreate {
  return {
    supplier_id: values.supplier || null,
    ordered_on: values.orderedOn,
    order_reference: values.reference || null,
    total_price: values.price.trim() || null,
    currency: values.currency || null,
    notes: values.notes || null,
  };
}

function seedLotTitle(lot: {
  label: string | null;
  botanical_identity: { display_label: string };
}): string {
  return lot.label ?? lot.botanical_identity.display_label;
}

function OrderForm({
  initial,
  suppliers,
  pending,
  error,
  errorRef,
  onSave,
  onCancel,
  onDirtyChange,
}: {
  initial?: OrderRecord;
  suppliers: SupplierListResponse[];
  pending: boolean;
  error: string;
  errorRef: RefObject<HTMLDivElement | null>;
  onSave: (payload: OrderCreate) => void;
  onCancel: () => void;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const [values, setValues] = useState<OrderFormValues>(() =>
    orderFormValues(initial),
  );
  const baseline = useRef(JSON.stringify(orderFormValues(initial)));
  const hasPrice = Boolean(values.price.trim());
  const hasCurrency = Boolean(values.currency);
  const supplierChoices = useMemo(() => {
    const choices = suppliers.map((supplier) => ({
      id: supplier.id,
      label: supplier.name,
      retired: Boolean(supplier.retired_at),
      inactiveLabel: "retired",
    }));
    if (
      initial?.supplier_id &&
      !choices.some(({ id }) => id === initial.supplier_id)
    )
      choices.push({
        id: initial.supplier_id,
        label: initial.supplier?.name ?? "Unavailable Supplier",
        retired: true,
        inactiveLabel: "unavailable",
      });
    return choices;
  }, [initial, suppliers]);

  function change(patch: Partial<OrderFormValues>) {
    const next = { ...values, ...patch };
    setValues(next);
    onDirtyChange(JSON.stringify(next) !== baseline.current);
  }

  function submit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (pending) return;
    onSave(orderPayload(values));
  }

  return (
    <form className="order-form collection-form" onSubmit={submit}>
      <header className="order-form__header">
        <p className="eyebrow">
          {initial ? "Purchase transaction" : "New purchase transaction"}
        </p>
        <h3>{initial ? "Edit Order" : "New Order"}</h3>
        <p>
          Record the transaction first. Physical seed lots stay independent and
          are added or linked separately.
        </p>
      </header>
      {error && (
        <div
          className="notice notice--error"
          ref={errorRef}
          role="alert"
          tabIndex={-1}
        >
          {error}
        </div>
      )}
      <div className="order-form__grid">
        <section className="order-form__column" aria-labelledby="order-context">
          <h4 id="order-context">Order context</h4>
          <ReferencePicker
            label="Supplier"
            choices={supplierChoices}
            value={values.supplier}
            onChange={(supplier) => {
              change({ supplier });
            }}
            disabled={pending}
            placeholder="No Supplier selected"
            openOnFocus={false}
          />
          <PartialDateField
            id="order-date"
            label="Order date"
            value={values.orderedOn}
            disabled={pending}
            showHelp={false}
            hidePrecisionLabel
            onChange={(orderedOn) => {
              change({ orderedOn });
            }}
          />
          <div className="field">
            <label htmlFor="order-reference">Order reference</label>
            <input
              id="order-reference"
              name="reference"
              maxLength={255}
              disabled={pending}
              value={values.reference}
              onChange={(event) => {
                change({ reference: event.currentTarget.value });
              }}
            />
          </div>
        </section>
        <section
          className="order-form__column"
          aria-labelledby="order-transaction-fields"
        >
          <h4 id="order-transaction-fields">Transaction and notes</h4>
          <div className="order-form__pair">
            <div className="field">
              <FieldLabel htmlFor="order-price" required={hasCurrency}>
                Total price
              </FieldLabel>
              <input
                id="order-price"
                aria-required={hasCurrency || undefined}
                aria-describedby="order-price-help"
                name="price"
                type="text"
                inputMode="decimal"
                pattern="[0-9]{1,24}(\.[0-9]{1,24})?"
                disabled={pending}
                value={values.price}
                onChange={(event) => {
                  change({ price: event.currentTarget.value });
                }}
              />
            </div>
            <div className="field">
              <FieldLabel htmlFor="order-currency" required={hasPrice}>
                Currency
              </FieldLabel>
              <input
                id="order-currency"
                aria-required={hasPrice || undefined}
                aria-describedby="order-price-help"
                name="currency"
                maxLength={3}
                pattern="[A-Z]{3}"
                placeholder="EUR"
                disabled={pending}
                value={values.currency}
                onChange={(event) => {
                  change({ currency: event.currentTarget.value });
                }}
              />
            </div>
          </div>
          <p id="order-price-help" className="field-help">
            Exact amount and three-letter currency together, or leave both
            blank. This is the total transaction price, never a per-lot price.
          </p>
          <div className="field">
            <label htmlFor="order-notes">Notes</label>
            <textarea
              id="order-notes"
              name="notes"
              maxLength={20000}
              rows={3}
              disabled={pending}
              value={values.notes}
              onChange={(event) => {
                change({ notes: event.currentTarget.value });
              }}
            />
          </div>
        </section>
      </div>
      <div className="order-form__footer">
        <button
          className="button--secondary"
          type="button"
          disabled={pending}
          onClick={onCancel}
        >
          Cancel
        </button>
        <button type="submit" disabled={pending}>
          {pending ? "Saving…" : initial ? "Save changes" : "Create Order"}
        </button>
      </div>
    </form>
  );
}

function OrderPreview({
  order,
  onOpen,
  onEdit,
}: {
  order: Order;
  onOpen: () => void;
  onEdit: MouseEventHandler<HTMLButtonElement>;
}) {
  return (
    <RecordPreview
      visual={
        <RecordVisual
          photo={null}
          label={orderTitle(order)}
          kind="order"
          className="quick-preview-media"
        />
      }
      type="Purchase order"
      title={orderTitle(order)}
      secondary={order.supplier?.name ?? "Supplier unknown"}
      facts={[
        { label: "Order date", value: orderDate(order.ordered_on) },
        { label: "Total price", value: orderPrice(order) },
        {
          label: "Physical seed lots",
          value: String(order.seed_lot_count),
        },
      ]}
      actions={
        <>
          <a
            className="button-link"
            href={`#/orders/${order.id}`}
            onClick={onOpen}
          >
            Open details
          </a>
          <div
            className="preview-action-group"
            role="group"
            aria-label="Order actions"
          >
            <ActionButton
              icon="edit"
              className="button--secondary"
              type="button"
              data-order-preview-edit
              onClick={onEdit}
            >
              Edit
            </ActionButton>
          </div>
        </>
      }
    />
  );
}

function OrderDetailView({
  order,
  initialTab,
  headingRef,
  onEdit,
  onLink,
  onDelete,
  onLotOffset,
}: {
  order: OrderDetail;
  initialTab?: string;
  headingRef: RefObject<HTMLHeadingElement | null>;
  onEdit: MouseEventHandler<HTMLButtonElement>;
  onLink: () => void;
  onDelete: () => void;
  onLotOffset: (offset: number) => void;
}) {
  const [tab, setTab] = useState<OrderTab>(
    initialTab === "seed-lots" ? "seed-lots" : "overview",
  );
  const hasLinkedLots = order.seed_lots_total > 0;
  const lotOffset = order.seed_lots_offset;

  function selectTab(next: OrderTab) {
    setTab(next);
    window.history.replaceState(null, "", `#/orders/${order.id}?tab=${next}`);
  }

  return (
    <article
      aria-label="Order detail"
      className="order-detail collection-detail"
    >
      <Breadcrumbs
        items={[
          { label: "Sourcing", href: "#/dashboard" },
          { label: "Orders", href: "#/orders" },
          { label: orderTitle(order) },
        ]}
      />
      <DetailHeader
        headingRef={headingRef}
        visual={
          <div className="collection-primary-detail">
            <RecordVisual kind="order" label={orderTitle(order)} photo={null} />
          </div>
        }
        eyebrow="Purchase order"
        title={orderTitle(order)}
        secondary={
          order.supplier ? (
            <a href={`#/suppliers/${order.supplier.id}`}>
              {order.supplier.name}
            </a>
          ) : (
            <span>Supplier unknown</span>
          )
        }
        status={
          <span className="order-count">
            {order.seed_lots_total} physical seed{" "}
            {order.seed_lots_total === 1 ? "lot" : "lots"}
          </span>
        }
        primaryActions={
          <>
            <a
              className="button-link"
              href={`#/seeds?action=create&order=${order.id}`}
            >
              Add seed lot
            </a>
            <button
              className="button--secondary"
              type="button"
              onClick={onLink}
            >
              Link existing seed lot
            </button>
          </>
        }
        editLabel="Edit Order"
        onEdit={onEdit}
      />
      <DetailTabs
        tabs={[
          { id: "overview", label: "Overview" },
          {
            id: "seed-lots",
            label: `Seed lots (${String(order.seed_lots_total)})`,
          },
        ]}
        selected={tab}
        onSelect={selectTab}
      />
      {tab === "overview" && (
        <div
          id="panel-overview"
          className="detail-tab-panel order-overview collection-overview"
          role="tabpanel"
          aria-labelledby="tab-overview"
        >
          <section
            className="collection-summary"
            aria-labelledby="order-summary-title"
          >
            <h4 id="order-summary-title">At a glance</h4>
            <dl aria-label="Current Order state">
              <div>
                <dt>Order date</dt>
                <dd>{orderDate(order.ordered_on)}</dd>
              </div>
              <div>
                <dt>Total price</dt>
                <dd>{orderPrice(order)}</dd>
              </div>
              <div>
                <dt>Physical seed lots</dt>
                <dd>{order.seed_lots_total}</dd>
              </div>
            </dl>
            <p className="field-help">
              The total transaction price is never divided or allocated between
              seed lots.
            </p>
          </section>
          <section
            className="order-fact-group"
            aria-labelledby="order-transaction-title"
          >
            <h4 id="order-transaction-title">Transaction details</h4>
            <dl>
              <div>
                <dt>Reference</dt>
                <dd>{order.order_reference ?? "Not recorded"}</dd>
              </div>
              <div>
                <dt>Notes</dt>
                <dd className="preserve-lines">
                  {order.notes ?? "No notes recorded."}
                </dd>
              </div>
            </dl>
            <p className="field-help">
              Supplier is optional. The Order date is independent from each
              SeedLot acquisition date.
            </p>
          </section>
          <section
            className="order-fact-group"
            aria-labelledby="order-lots-summary-title"
          >
            <h4 id="order-lots-summary-title">Physical seed lots</h4>
            <p>
              {hasLinkedLots
                ? `${String(order.seed_lots_total)} distinct ${
                    order.seed_lots_total === 1 ? "lot remains" : "lots remain"
                  } independent, each with its own acquisition context.`
                : "No physical seed lots are linked to this Order yet."}
            </p>
            {hasLinkedLots && (
              <p>
                <button
                  className="button--quiet"
                  type="button"
                  onClick={() => {
                    selectTab("seed-lots");
                  }}
                >
                  View physical seed lots
                </button>
              </p>
            )}
            <p className="field-help">
              Unlink in SeedLot edit. That removes only the Order association
              and never the physical lot.
            </p>
          </section>
          <section
            className="order-fact-group order-overview-wide order-danger"
            aria-labelledby="order-delete-title"
          >
            <h4 id="order-delete-title">Remove this Order</h4>
            <p>
              {hasLinkedLots
                ? "Unlink every physical seed lot before deleting this transaction."
                : "This removes the purchase transaction permanently."}
            </p>
            <button
              className="button--secondary order-danger__button"
              type="button"
              disabled={hasLinkedLots}
              aria-describedby="order-delete-help"
              onClick={onDelete}
            >
              Delete Order
            </button>
            <p id="order-delete-help" className="field-help">
              {hasLinkedLots
                ? "Linked seed lots retain this transaction. Unlink them in Seed lot edit first."
                : "Only Orders without linked seed lots can be deleted."}
            </p>
          </section>
        </div>
      )}
      {tab === "seed-lots" && (
        <div
          id="panel-seed-lots"
          className="detail-tab-panel order-seed-lots"
          role="tabpanel"
          aria-labelledby="tab-seed-lots"
        >
          <section
            className="order-fact-group"
            aria-labelledby="order-lots-title"
          >
            <h4 id="order-lots-title">
              Physical seed lots ({order.seed_lots_total})
            </h4>
            <p className="field-help">
              Each lot remains independent. Link here or from SeedLot
              Acquisition; unlink in SeedLot edit.
            </p>
            {order.seed_lots_total === 0 ? (
              <DetailEmptyState>No seed lots linked yet.</DetailEmptyState>
            ) : (
              <>
                <div className="card-grid">
                  {order.seed_lots.map((lot) => (
                    <CollectionCard
                      key={lot.id}
                      eyebrow="SeedLot"
                      title={seedLotTitle(lot)}
                      href={`#/seeds/${lot.id}`}
                    >
                      <p>
                        <a href={`#/identities/${lot.botanical_identity.id}`}>
                          {seedLotTitle(lot) ===
                          lot.botanical_identity.display_label
                            ? "View botanical identity"
                            : lot.botanical_identity.display_label}
                        </a>
                      </p>
                      <p>
                        {lot.acquisition_date
                          ? `Acquired ${orderDate(lot.acquisition_date)}`
                          : "Acquisition date unknown"}{" "}
                        · {lifecycleLabels[lot.lifecycle] ?? lot.lifecycle}
                      </p>
                    </CollectionCard>
                  ))}
                </div>
                <div className="actions">
                  {lotOffset > 0 && (
                    <button
                      type="button"
                      onClick={() => {
                        onLotOffset(
                          Math.max(0, lotOffset - order.seed_lots_limit),
                        );
                      }}
                    >
                      Previous seed lots
                    </button>
                  )}
                  {lotOffset + order.seed_lots.length <
                    order.seed_lots_total && (
                    <button
                      type="button"
                      onClick={() => {
                        onLotOffset(lotOffset + order.seed_lots_limit);
                      }}
                    >
                      Next seed lots
                    </button>
                  )}
                </div>
              </>
            )}
          </section>
        </div>
      )}
    </article>
  );
}

export function OrderScreen({
  initialId,
  initialTab,
  startCreating = false,
}: {
  initialId?: string;
  initialTab?: string;
  startCreating?: boolean;
} = {}) {
  const auth = useAuth();
  const [offset, setOffset] = useState(0);
  const [lotOffsetState, setLotOffsetState] = useState({
    id: initialId ?? "",
    offset: 0,
  });
  const [storedPage, setStoredPage] = useState<OrderPage | null>(null);
  const [storedDetail, setStoredDetail] = useState<OrderDetail | null>(null);
  const [pageLoadedKey, setPageLoadedKey] = useState("");
  const [detailLoadedKey, setDetailLoadedKey] = useState("");
  const [storedPageError, setStoredPageError] = useState("");
  const [pageErrorKey, setPageErrorKey] = useState("");
  const [storedDetailError, setStoredDetailError] = useState("");
  const [detailErrorKey, setDetailErrorKey] = useState("");
  const [suppliers, setSuppliers] = useState<SupplierListResponse[] | null>(
    null,
  );
  const [suppliersError, setSuppliersError] = useState("");
  const [supplierAttempt, setSupplierAttempt] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(
    initialId ?? null,
  );
  const [target, setTarget] = useState<OrderRecord | null>(null);
  const [editing, setEditing] = useState(false);
  const [formOpen, setFormOpen] = useState(startCreating);
  const [formDirty, setFormDirty] = useState(false);
  const [formError, setFormError] = useState("");
  const [savePending, setSavePending] = useState(false);
  const [success, setSuccess] = useState("");
  const [linking, setLinking] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deletePending, setDeletePending] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const view = useDirectoryView("orders", () => {
    setOffset(0);
  });
  const lotOffset =
    lotOffsetState.id === (initialId ?? "") ? lotOffsetState.offset : 0;
  const pageRequestKey = `${view.state.q}:${view.state.supplier_id}:${String(
    offset,
  )}:${String(attempt)}`;
  const detailRequestKey = `${initialId ?? ""}:${String(lotOffset)}:${String(
    attempt,
  )}`;
  const page = pageLoadedKey === pageRequestKey ? storedPage : null;
  const detail =
    initialId && detailLoadedKey === detailRequestKey ? storedDetail : null;
  const pageError = pageErrorKey === pageRequestKey ? storedPageError : "";
  const detailError =
    initialId && detailErrorKey === detailRequestKey ? storedDetailError : "";
  const setLotOffset = (offset: number) => {
    setLotOffsetState({ id: initialId ?? "", offset });
  };
  const detailFeedback = useRef<HTMLDivElement>(null);
  const formFeedback = useRef<HTMLDivElement>(null);
  const deleteFeedback = useRef<HTMLDivElement>(null);
  const detailHeading = useRef<HTMLHeadingElement>(null);
  const createTrigger = useRef<HTMLButtonElement>(null);
  const editTrigger = useRef<HTMLButtonElement>(null);
  const directEditHandled = useRef(false);
  const restorePreviewEdit = useRef(false);
  const restoreDetailHeading = useRef(false);
  const previousCreateRoute = useRef(startCreating);

  const edit = useEditRoute({
    routeIsEdit: initialTab === "edit",
    canDismiss: () => {
      if (savePending) return false;
      return !formDirty || window.confirm("Discard unsaved Order changes?");
    },
    onDismiss: () => {
      setEditing(false);
      setTarget(null);
      setFormDirty(false);
      setFormError("");
      if (!edit.modal && initialId) {
        restoreDetailHeading.current = true;
        setRecordRoute(`#/orders/${initialId}`, true);
      }
    },
  });

  useEffect(() => {
    const controller = new AbortController();
    void listSuppliers(controller.signal)
      .then((items) => {
        if (controller.signal.aborted) return;
        setSuppliers(items);
        setSuppliersError("");
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else setSuppliersError("Florabase could not load Suppliers.");
      });
    return () => {
      controller.abort();
    };
  }, [auth, supplierAttempt]);

  useEffect(() => {
    const controller = new AbortController();
    void listOrders(
      view.state.q,
      view.state.supplier_id,
      offset,
      controller.signal,
    )
      .then((item) => {
        if (controller.signal.aborted) return;
        setStoredPage(item);
        setStoredPageError("");
        setPageLoadedKey(pageRequestKey);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401) {
          auth.sessionExpired();
          return;
        }
        setStoredPageError("Florabase could not load Orders.");
        setPageErrorKey(pageRequestKey);
        setPageLoadedKey(pageRequestKey);
      });
    return () => {
      controller.abort();
    };
  }, [
    auth,
    attempt,
    offset,
    pageRequestKey,
    view.state.q,
    view.state.supplier_id,
  ]);

  useEffect(() => {
    if (!initialId) return;
    const controller = new AbortController();
    void getOrder(initialId, lotOffset, controller.signal)
      .then((item) => {
        if (controller.signal.aborted) return;
        setStoredDetail(item);
        setStoredDetailError("");
        setDetailLoadedKey(detailRequestKey);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401) {
          auth.sessionExpired();
          return;
        }
        setStoredDetailError(
          error instanceof ApiError && error.status === 404
            ? "Order not found."
            : "Florabase could not load this Order.",
        );
        setDetailErrorKey(detailRequestKey);
        setDetailLoadedKey(detailRequestKey);
      });
    return () => {
      controller.abort();
    };
  }, [auth, attempt, detailRequestKey, initialId, lotOffset]);

  useEffect(() => {
    if (startCreating === previousCreateRoute.current) return;
    previousCreateRoute.current = startCreating;
    const timeout = window.setTimeout(() => {
      if (startCreating) {
        setEditing(false);
        setTarget(null);
        setFormOpen(true);
        setFormDirty(false);
        setFormError("");
        return;
      }
      setFormOpen(false);
      setFormDirty(false);
      setFormError("");
    }, 0);
    return () => {
      window.clearTimeout(timeout);
    };
  }, [startCreating]);

  useEffect(() => {
    if (initialTab !== "edit") {
      directEditHandled.current = false;
      return;
    }
    if (edit.modal) {
      directEditHandled.current = true;
      return;
    }
    if (directEditHandled.current) return;
    const source =
      detail && detail.id === initialId
        ? detail
        : (page?.items.find(({ id }) => id === initialId) ?? null);
    if (!source) return;
    directEditHandled.current = true;
    const timeout = window.setTimeout(() => {
      setTarget(source);
      setFormDirty(false);
      setFormError("");
      setEditing(true);
    }, 0);
    return () => {
      window.clearTimeout(timeout);
    };
  }, [detail, edit.modal, initialId, initialTab, page]);

  // Browser Back out of a direct edit URL closes the inline fallback instead of
  // leaving an editor mounted under a non-edit route.
  useEffect(() => {
    if (initialTab === "edit" || edit.modal || !editing) return;
    const timeout = window.setTimeout(() => {
      setEditing(false);
      setTarget(null);
      setFormDirty(false);
      setFormError("");
      if (initialId) restoreDetailHeading.current = true;
    }, 0);
    return () => {
      window.clearTimeout(timeout);
    };
  }, [edit.modal, editing, initialId, initialTab]);

  useCollectionPageReturnFocus(!initialId && !formOpen && !editing);

  useEffect(() => {
    if (formError) formFeedback.current?.focus();
  }, [formError]);

  useEffect(() => {
    if (detailError) detailFeedback.current?.focus();
  }, [detailError]);

  useEffect(() => {
    if (deleteError) deleteFeedback.current?.focus();
  }, [deleteError]);

  const visible = useMemo(() => page?.items ?? [], [page]);
  const selected = useMemo(() => {
    const inPage = visible.find(({ id }) => id === selectedId);
    if (inPage) return inPage;
    if (detail?.id === selectedId) return detail;
    return null;
  }, [detail, selectedId, visible]);
  const supplierChoices = useMemo(() => {
    const choices = (suppliers ?? []).map((supplier) => ({
      id: supplier.id,
      label: supplier.name,
      retired: Boolean(supplier.retired_at),
      inactiveLabel: "retired",
    }));
    if (
      view.state.supplier_id &&
      !choices.some(({ id }) => id === view.state.supplier_id)
    )
      choices.push({
        id: view.state.supplier_id,
        label: `Unavailable Supplier — ${view.state.supplier_id}`,
        retired: true,
        inactiveLabel: "unavailable",
      });
    return choices;
  }, [suppliers, view.state.supplier_id]);
  const activeSupplierName =
    suppliers?.find(({ id }) => id === view.state.supplier_id)?.name ??
    `Unavailable Supplier — ${view.state.supplier_id}`;

  // A saved edit refreshes the detail, so move focus to the record heading
  // instead of the detached Edit button from the replaced render.
  useEffect(() => {
    if (!restoreDetailHeading.current || !detail || editing || edit.modal)
      return;
    restoreDetailHeading.current = false;
    const frame = requestAnimationFrame(() => {
      detailHeading.current?.focus();
    });
    return () => {
      cancelAnimationFrame(frame);
    };
  }, [detail, edit.modal, editing]);

  // Editing from Quick Preview changes the route, so restore focus once the
  // directory and its preview have rendered again.
  useEffect(() => {
    if (
      initialId ||
      editing ||
      edit.modal ||
      !restorePreviewEdit.current ||
      !selected
    )
      return;
    restorePreviewEdit.current = false;
    const frame = requestAnimationFrame(() => {
      document.querySelector<HTMLElement>("[data-order-preview-edit]")?.focus();
    });
    return () => {
      cancelAnimationFrame(frame);
    };
  }, [edit.modal, editing, initialId, selected]);

  if (
    auth.state.status !== "authenticated" &&
    auth.state.status !== "logging-out" &&
    auth.state.status !== "logout-failed"
  )
    return null;
  const csrf = auth.state.csrfToken;

  async function save(payload: OrderCreate) {
    if (savePending) return;
    const existing = target;
    setSavePending(true);
    setFormError("");
    try {
      const result = await saveOrder(existing?.id, payload, csrf);
      setFormOpen(false);
      setEditing(false);
      setTarget(null);
      setFormDirty(false);
      setSelectedId(result.id);
      setSuccess(existing ? "Order updated." : "Order created.");
      if (existing && initialId && !restorePreviewEdit.current)
        restoreDetailHeading.current = true;
      setAttempt((value) => value + 1);
      if (existing) {
        if (edit.modal) edit.close(true);
        else if (initialId) setRecordRoute(`#/orders/${initialId}`, true);
      } else {
        closeCollectionPage("#/orders");
      }
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else setFormError(orderError(error));
    } finally {
      setSavePending(false);
    }
  }

  async function remove() {
    if (!initialId || deletePending) return;
    setDeletePending(true);
    setDeleteError("");
    try {
      await deleteOrder(initialId, csrf);
      setDeleting(false);
      setSelectedId(null);
      setSuccess("Order deleted.");
      setAttempt((value) => value + 1);
      if (window.location.hash !== "#/orders")
        window.location.hash = "#/orders";
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else setDeleteError(orderError(error));
    } finally {
      setDeletePending(false);
    }
  }

  function startCreate() {
    setEditing(false);
    setTarget(null);
    setFormOpen(true);
    setFormDirty(false);
    setFormError("");
    setSuccess("");
    openCollectionPage("#/orders?action=create");
  }

  function startEdit(record: OrderRecord, trigger: HTMLButtonElement | null) {
    editTrigger.current = trigger;
    directEditHandled.current = true;
    restorePreviewEdit.current = !initialId;
    setFormOpen(false);
    setTarget(record);
    setEditing(true);
    setFormDirty(false);
    setFormError("");
    setSuccess("");
    edit.open(`#/orders/${record.id}?tab=edit`);
  }

  function requestCreateClose() {
    if (savePending) return;
    if (formDirty && !window.confirm("Discard unsaved Order changes?")) return;
    setFormOpen(false);
    setFormDirty(false);
    setFormError("");
    closeCollectionPage("#/orders");
  }

  function requestEditClose() {
    if (savePending) return;
    if (formDirty && !window.confirm("Discard unsaved Order changes?")) return;
    if (edit.modal) {
      edit.close(true);
      return;
    }
    setEditing(false);
    setTarget(null);
    setFormDirty(false);
    setFormError("");
    if (initialId) {
      restoreDetailHeading.current = true;
      setRecordRoute(`#/orders/${initialId}`, true);
    }
  }

  const editor = (initial?: OrderRecord) => (
    <EditWorkspace
      returnFocusTo={initial ? editTrigger : createTrigger}
      modal={initial ? edit.modal : true}
      title={initial ? "Edit Order" : "New Order"}
      onClose={initial ? requestEditClose : requestCreateClose}
    >
      <OrderForm
        key={initial?.id ?? "new"}
        initial={initial}
        suppliers={suppliers ?? []}
        pending={savePending}
        error={formError}
        errorRef={formFeedback}
        onSave={(payload) => {
          void save(payload);
        }}
        onCancel={initial ? requestEditClose : requestCreateClose}
        onDirtyChange={setFormDirty}
      />
    </EditWorkspace>
  );

  if (initialId)
    return (
      <section
        aria-labelledby="orders-title"
        className="workspace orders-workspace"
      >
        <div
          className="collection-context-page"
          inert={edit.modal || formOpen}
          aria-hidden={edit.modal || formOpen || undefined}
        >
          <WorkspaceIntro contextOnly {...orderPage} />
          {suppliersError && (
            <div className="notice notice--error" role="alert">
              <p>{suppliersError}</p>
              <button
                type="button"
                onClick={() => {
                  setSuppliers(null);
                  setSuppliersError("");
                  setSupplierAttempt((value) => value + 1);
                }}
              >
                Retry Suppliers
              </button>
            </div>
          )}
          {detailError ? (
            <div
              className="notice notice--error"
              role="alert"
              ref={detailFeedback}
              tabIndex={-1}
            >
              <p>{detailError}</p>
              <button
                type="button"
                onClick={() => {
                  setAttempt((value) => value + 1);
                }}
              >
                Retry Order
              </button>
              <a href="#/orders">Return to Orders</a>
            </div>
          ) : detail ? (
            editing && !edit.modal ? (
              editor(detail)
            ) : (
              <OrderDetailView
                key={detail.id}
                order={detail}
                initialTab={initialTab}
                headingRef={detailHeading}
                onEdit={(event) => {
                  startEdit(detail, event.currentTarget);
                }}
                onLink={() => {
                  setLinking(true);
                }}
                onDelete={() => {
                  setDeleteError("");
                  setDeleting(true);
                }}
                onLotOffset={setLotOffset}
              />
            )
          ) : (
            <p role="status">Loading Order…</p>
          )}
          <div aria-live="polite">
            {success && (
              <p className="notice notice--success" role="status">
                {success}
              </p>
            )}
          </div>
        </div>
        {edit.modal && editing && target && editor(target)}
        {formOpen && suppliers && editor()}
        {linking && detail && (
          <LinkExistingSeedLot
            orderId={detail.id}
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
        {deleting && (
          <TaskDialog
            title="Delete Order"
            dismissOnBackdrop
            onClose={() => {
              if (!deletePending) setDeleting(false);
            }}
          >
            <h3>Delete this Order?</h3>
            <p>
              This removes the transaction permanently. Orders with linked seed
              lots cannot be deleted.
            </p>
            {deleteError && (
              <div
                className="notice notice--error"
                ref={deleteFeedback}
                role="alert"
                tabIndex={-1}
              >
                {deleteError}
              </div>
            )}
            <div className="actions">
              <button
                type="button"
                disabled={deletePending}
                onClick={() => void remove()}
              >
                {deletePending ? "Deleting…" : "Confirm delete"}
              </button>
              <button
                className="button--secondary"
                type="button"
                disabled={deletePending}
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

  return (
    <section
      aria-labelledby="orders-title"
      className="workspace orders-workspace"
    >
      <div
        className="collection-context-page"
        inert={formOpen}
        aria-hidden={formOpen || undefined}
      >
        <WorkspaceIntro
          {...orderPage}
          tools={
            <DirectoryTools
              onReset={() => {
                view.update("supplier_id", "");
                setOffset(0);
              }}
              name="Orders"
              search={
                <DirectorySearch
                  hideLabel
                  id="order-search"
                  label="Search Orders"
                  placeholder="Reference, Supplier or notes"
                  value={view.state.q}
                  onChange={(value) => {
                    view.update("q", value);
                    setOffset(0);
                  }}
                />
              }
              savedViews={
                <SavedViews
                  presentation="dialog"
                  surface="orders"
                  state={view.savedState}
                />
              }
              actions={
                <ActionButton
                  icon="add"
                  type="button"
                  ref={createTrigger}
                  data-collection-return="create"
                  disabled={!suppliers}
                  onClick={startCreate}
                >
                  New Order
                </ActionButton>
              }
              filters={
                <div className="order-supplier-filter">
                  <ReferencePicker
                    label="Supplier"
                    choices={supplierChoices}
                    value={view.state.supplier_id}
                    onChange={(supplierId) => {
                      view.update("supplier_id", supplierId);
                      setOffset(0);
                    }}
                    disabled={!suppliers}
                    placeholder="All Suppliers"
                    help="Optional. Narrow the directory to one recorded Supplier."
                    openOnFocus={false}
                  />
                </div>
              }
              activeFilters={
                view.state.supplier_id
                  ? [
                      {
                        label: "Supplier",
                        value: activeSupplierName,
                        onRemove: () => {
                          view.update("supplier_id", "");
                          setOffset(0);
                        },
                      },
                    ]
                  : []
              }
            />
          }
        />
        {suppliersError && (
          <div className="notice notice--error" role="alert">
            <p>{suppliersError}</p>
            <button
              type="button"
              onClick={() => {
                setSuppliers(null);
                setSuppliersError("");
                setSupplierAttempt((value) => value + 1);
              }}
            >
              Retry Suppliers
            </button>
          </div>
        )}
        <div className="order-master-detail operational-layout directory-preview-layout">
          <section
            className="seed-master order-master"
            aria-labelledby="order-directory-title"
          >
            <h3 className="sr-only" id="order-directory-title">
              Order directory
            </h3>
            {page && (
              <DirectoryResults count={page.items.length} total={page.total} />
            )}
            {!page && !pageError && (
              <p aria-live="polite" className="notice">
                Loading Orders…
              </p>
            )}
            {pageError && (
              <div className="notice notice--error" role="alert">
                <p>{pageError}</p>
                <button
                  type="button"
                  onClick={() => {
                    setAttempt((value) => value + 1);
                  }}
                >
                  Retry Orders
                </button>
              </div>
            )}
            {page?.total === 0 && (
              <div className="empty-state">
                <h3>No Orders found</h3>
                <p>
                  {view.state.q || view.state.supplier_id
                    ? "Try another search or Supplier."
                    : "Record a purchase, then add or link its physical seed lots."}
                </p>
              </div>
            )}
            {page && page.total > 0 && page.items.length === 0 && (
              <p className="notice" role="status">
                No Orders on this page. Go to the previous page.
              </p>
            )}
            {visible.length > 0 && (
              <ul
                className="seed-list order-list-directory"
                aria-label="Orders"
                tabIndex={0}
              >
                {visible.map((order) => (
                  <li key={order.id}>
                    <button
                      type="button"
                      className="seed-row order-row"
                      aria-pressed={selectedId === order.id}
                      onClick={() => {
                        setSelectedId(order.id);
                        setSuccess("");
                        if (window.matchMedia("(max-width: 48rem)").matches)
                          setRecordRoute(`#/orders/${order.id}`);
                      }}
                    >
                      <span className="seed-primary">
                        <RecordVisual
                          kind="order"
                          label={orderTitle(order)}
                          photo={null}
                          compact
                        />
                        <span className="order-row__identity">
                          <strong>{orderTitle(order)}</strong>
                          <small>
                            {orderDate(order.ordered_on)} ·{" "}
                            {order.supplier?.name ?? "Supplier unknown"}
                          </small>
                        </span>
                      </span>
                      <span className="order-row__amount">
                        <strong>{orderPrice(order)}</strong>
                        <small>
                          {order.seed_lot_count} seed{" "}
                          {order.seed_lot_count === 1 ? "lot" : "lots"}
                        </small>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {page && (
              <div className="actions order-pagination">
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
            )}
          </section>
          <section
            className="seed-detail-pane order-detail-pane"
            aria-label="Order detail and quick preview"
          >
            {selected ? (
              <OrderPreview
                order={selected}
                onOpen={() => {
                  setSuccess("");
                }}
                onEdit={(event) => {
                  startEdit(selected, event.currentTarget);
                }}
              />
            ) : (
              <div className="empty-state seed-detail-empty">
                <h3>Select an Order</h3>
                <p>
                  Choose a purchase for a Quick Preview, then open details to
                  inspect its transaction and linked physical seed lots.
                </p>
              </div>
            )}
          </section>
        </div>
        <div aria-live="polite">
          {success && (
            <p className="notice notice--success" role="status">
              {success}
            </p>
          )}
        </div>
      </div>
      {formOpen && suppliers && editor()}
    </section>
  );
}
