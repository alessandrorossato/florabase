import { FieldLabel } from "../components/FieldLabel";
import "../components/directory-preview.css";
import { useEditRoute } from "../components/useEditRoute";
import "./seed-refinement.css";
import { EditWorkspace } from "../components/EditWorkspace";
import { TaskDialog } from "../components/TaskDialog";
import {
  DirectoryTools,
  DirectoryFilterSelect,
} from "../components/DirectoryTools";
import { UpcomingActivities } from "../schedule/UpcomingActivities";
import { PurchaseContextDialog } from "../orders/PurchaseContext";
import {
  applyPurchase,
  previewPurchase,
  createPurchaseLot,
  type AcquisitionContext,
  type PurchaseApply,
} from "../orders/purchaseApi";
import { OrderPicker } from "../orders/OrderPicker";
import { getOrder, type OrderDetail } from "../orders/api";
import { DirectoryResults } from "../components/DirectoryResults";
import { BulkCheckbox, BulkSelect, BulkToolbar } from "../bulk/BulkLocation";
import { useBulkSelection } from "../bulk/useBulkSelection";
import { SavedViews } from "../saved-views/SavedViews";
import { useDirectoryView } from "../saved-views/useDirectoryView";
import { ConversionHistory } from "../harvests/ConversionHistory";
import { usePublishRecordIdentities } from "../components/recordPresentation";
import { useRecordName } from "../components/recordPresentation";
import { FormSections } from "../components/FormSections";
import { firstValidationField } from "../components/formValidation";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
  type MouseEventHandler,
  type RefObject,
  type SyntheticEvent,
} from "react";

import { ApiError } from "../auth/api";
import { labelComposerHref } from "../labels/labelData";
import { useAuth } from "../auth/context";
import { useCreationDisclosure } from "../components/useCreationDisclosure";
import {
  BotanicalName,
  DirectorySearch,
  QuickPreview,
} from "../components/ReferenceUI";
import { setRecordRoute } from "../components/recordNavigation";
import {
  Breadcrumbs,
  CollectionCard,
  DetailHeader,
  DetailContext,
  DetailTabs,
  WorkspaceIntro,
} from "../components/CollectionUI";
import { FieldHelp } from "../components/ContextualHelp";
import { LineagePanel } from "../lineage/LineagePanel";
import { PhotosSection } from "../photos/PhotosSection";
import { RecordVisual } from "../photos/RecordVisual";
import type { PrimaryPhoto } from "../photos/api";
import { listSowings, type SowingResponse } from "../sowings/api";
import {
  listProvenanceSites,
  type ProvenanceSiteResponse,
} from "../provenance-sites/api";
import {
  conflictExistingId,
  createBotanicalIdentity,
  getBotanicalIdentity,
  listBotanicalIdentities,
  validationMessages,
  type BotanicalIdentityResponse,
} from "../botanical-identities/api";
import {
  createGeographicPlace,
  geographyValidationMessages,
  listGeographicPlaces,
  type GeographicPlaceResponse,
} from "../geographic-places/api";
import {
  createLocation,
  listLocations,
  locationsForScope,
  locationValidationMessages,
  type LocationResponse,
} from "../locations/api";
import {
  createSupplier,
  listSuppliers,
  supplierValidationMessages,
  type SupplierResponse,
} from "../suppliers/api";
import {
  createSeedLot,
  listSeedLots,
  seedLotOrderError,
  seedLotValidationMessages,
  updateSeedLot,
  type PartialDate,
  type SeedLotCreate,
  type SeedLotLifecycle,
  type SeedLotResponse,
  type SeedLotSourceKind,
} from "./api";
import { PartialDateField } from "./PartialDateField";
import { ReferencePicker } from "./ReferencePicker";

type InventoryState =
  | { status: "loading" }
  | { status: "ready"; lots: SeedLotResponse[] }
  | { status: "error" };
interface References {
  identities: BotanicalIdentityResponse[];
  suppliers: SupplierResponse[];
  locations: LocationResponse[];
  places: GeographicPlaceResponse[];
  sites: ProvenanceSiteResponse[];
}
type SaveState =
  | { status: "idle" }
  | { status: "saving" }
  | { status: "success"; message: string }
  | { status: "error"; messages: string[]; field?: string };
type ContextKind = "identity" | "supplier" | "location" | "place";

interface FormState {
  botanicalIdentityId: string;
  label: string;
  quantityValue: string;
  quantityUnit: "seeds" | "g" | "mg";
  quantityApproximate: boolean;
  sourceKind: SeedLotSourceKind;
  sourceDetail: string;
  supplierId: string;
  orderId: string;
  locationId: string;
  materialProvenancePlaceId: string;
  provenanceSiteId: string;
  acquisitionDate: PartialDate | null;
  harvestDate: PartialDate | null;
  expectedViabilityUntil: PartialDate | null;
  lifecycle: SeedLotLifecycle;
  notes: string;
}

const sourceLabels: Record<SeedLotSourceKind, string> = {
  purchased: "Purchased",
  purchased_fruit: "From purchased fruit",
  self_collected: "Self-collected",
  collection_produced: "Produced from my collection",
  gift_exchange: "Gift / exchange",
  other: "Other",
  unknown: "Unknown",
};
const lifecycleLabels: Record<SeedLotLifecycle, string> = {
  active: "Active",
  exhausted: "Exhausted",
  discarded: "Discarded",
  lost: "Lost",
  reversed: "Reversed",
};

function blankForm(): FormState {
  return {
    botanicalIdentityId: "",
    label: "",
    quantityValue: "",
    quantityUnit: "seeds",
    quantityApproximate: false,
    sourceKind: "unknown",
    sourceDetail: "",
    supplierId: "",
    orderId: "",
    locationId: "",
    materialProvenancePlaceId: "",
    provenanceSiteId: "",
    acquisitionDate: null,
    harvestDate: null,
    expectedViabilityUntil: null,
    lifecycle: "active",
    notes: "",
  };
}

function formFrom(lot: SeedLotResponse): FormState {
  return {
    botanicalIdentityId: lot.botanical_identity_id,
    label: lot.label ?? "",
    quantityValue: lot.quantity?.value ?? "",
    quantityUnit:
      lot.quantity?.kind === "weight" ? (lot.quantity.unit ?? "g") : "seeds",
    quantityApproximate: lot.quantity?.is_approximate ?? false,
    sourceKind: lot.source_kind,
    sourceDetail: lot.source_detail ?? "",
    supplierId: lot.supplier_id ?? "",
    orderId: lot.order_id ?? "",
    locationId: lot.location_id ?? "",
    materialProvenancePlaceId: lot.material_provenance_place_id ?? "",
    provenanceSiteId: lot.provenance_site_id ?? "",
    acquisitionDate: lot.acquisition_date,
    harvestDate: lot.harvest_date,
    expectedViabilityUntil: lot.expected_viability_until,
    lifecycle: lot.lifecycle,
    notes: lot.notes ?? "",
  };
}

function payloadFrom(form: FormState): SeedLotCreate {
  return {
    botanical_identity_id: form.botanicalIdentityId,
    lifecycle: form.lifecycle,
    source_kind: form.sourceKind,
    label: form.label || null,
    quantity: form.quantityValue
      ? {
          value: form.quantityValue,
          kind: form.quantityUnit === "seeds" ? "seed_count" : "weight",
          unit: form.quantityUnit === "seeds" ? null : form.quantityUnit,
          is_approximate: form.quantityApproximate,
        }
      : null,
    source_detail:
      form.sourceKind === "other" ? form.sourceDetail || null : null,
    supplier_id: form.supplierId || null,
    order_id: form.orderId || null,
    location_id: form.locationId || null,
    material_provenance_place_id: form.materialProvenancePlaceId || null,
    provenance_site_id: form.provenanceSiteId || null,
    acquisition_date: form.acquisitionDate,
    harvest_date: form.harvestDate,
    expected_viability_until: form.expectedViabilityUntil,
    notes: form.notes || null,
  };
}

function quantityLabel(lot: SeedLotResponse): string {
  if (!lot.quantity) return "Quantity unknown";
  const unit = lot.quantity.kind === "seed_count" ? "seeds" : lot.quantity.unit;
  return `${lot.quantity.is_approximate ? "About " : ""}${lot.quantity.value} ${unit ?? ""}`;
}

function inventoryLabel(lot: SeedLotResponse): string {
  return lot.lifecycle === "active" ? "Remaining" : "Recorded quantity";
}

function SeedLotPreview({
  lot,
  onOpen,
  onEdit,
}: {
  lot: SeedLotResponse;
  onOpen: () => void;
  onEdit: MouseEventHandler<HTMLButtonElement>;
}) {
  const recordName = useRecordName();

  return (
    <QuickPreview>
      <RecordVisual
        photo={lot.primary_photo ?? null}
        label={recordName(lot, "Seed lot")}
        compact

        identity={lot.botanical_identity}
        kind={"seed"}
      />
      <p className="record-preview__type">Seed lot</p>
      <h3>{recordName(lot, "Unlabelled seed lot")}</h3>
      <p className="seed-preview__identity">
        <a href={`#/identities/${lot.botanical_identity.id}`}>
          {lot.botanical_identity.display_label}
        </a>
      </p>
      <div className="seed-preview__inventory">
        <span>{inventoryLabel(lot)}</span>
        <strong>{quantityLabel(lot)}</strong>
        {lot.lifecycle !== "active" && (
          <small>
            This lot is {lifecycleLabels[lot.lifecycle].toLowerCase()}.
          </small>
        )}
      </div>
      <dl className="record-preview__facts">
        <div>
          <dt>Status</dt>
          <dd>{lifecycleLabels[lot.lifecycle]}</dd>
        </div>
        <div>
          <dt>Storage</dt>
          <dd>
            {lot.location ? (
              <a href={`#/locations/${lot.location.id}`}>
                {lot.location.display_path}
              </a>
            ) : (
              "Not recorded"
            )}
          </dd>
        </div>
        <div>
          <dt>Supplier</dt>
          <dd>
            {lot.supplier ? (
              <a href={`#/suppliers/${lot.supplier.id}`}>{lot.supplier.name}</a>
            ) : (
              "Not recorded"
            )}
          </dd>
        </div>
      </dl>
      <div className="actions record-preview__actions seed-preview__actions">
        {lot.lifecycle === "active" && (
          <a
            className="button-link"
            href={`#/sowings?action=start&seedLot=${lot.id}`}
          >
            Start sowing
          </a>
        )}
        <button className="button--secondary" type="button" onClick={onOpen}>
          Open details
        </button>
        <button className="button--secondary" type="button" onClick={onEdit}>
          Edit
        </button>
      </div>
    </QuickPreview>
  );
}

function dateLabel(date: PartialDate | null): string {
  if (!date) return "Unknown";
  const year = String(date.year).padStart(4, "0");
  if (date.precision === "year") return year;
  const month = String(date.month).padStart(2, "0");
  if (date.precision === "month") return `${year}-${month}`;
  return `${year}-${month}-${String(date.day).padStart(2, "0")}`;
}

function ContextDialog({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <TaskDialog title={title} onClose={onClose} className="seed-context-dialog">
      <h3>{title}</h3>
      {children}
    </TaskDialog>
  );
}

function RelatedSowings({ seedLotId }: { seedLotId: string }) {
  const recordName = useRecordName();

  const [sowings, setSowings] = useState<SowingResponse[] | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    void listSowings(controller.signal)
      .then((items) => {
        setSowings(
          items.filter(({ seed_lot_id }) => seed_lot_id === seedLotId),
        );
      })
      .catch(() => {
        if (!controller.signal.aborted) setSowings([]);
      });
    return () => {
      controller.abort();
    };
  }, [seedLotId]);
  if (sowings === null) return <p role="status">Loading Sowings…</p>;
  if (!sowings.length)
    return (
      <div className="detail-empty-message">
        <p>No sowings use this seed lot yet.</p>
      </div>
    );
  return (
    <div className="card-grid">
      {sowings.map((sowing) => (
        <CollectionCard
          key={sowing.id}
          eyebrow={sowing.lifecycle}
          href={`#/sowings/${sowing.id}`}
          title={recordName(sowing, "Unlabelled Sowing")}
        >
          <p>{dateLabel(sowing.sowing_date)}</p>
          <p>
            {sowing.quantity
              ? `${sowing.quantity.is_approximate ? "~" : ""}${sowing.quantity.value} ${sowing.quantity.kind === "seed_count" ? "seeds used" : `${sowing.quantity.unit ?? "weight"} used`}`
              : "Quantity used not recorded"}
          </p>
          <p>
            {sowing.germinated_count === null
              ? "Germination not recorded"
              : `${String(sowing.germinated_count)} germinated`}
          </p>
          <p>{sowing.location?.display_path ?? "Location not recorded"}</p>
        </CollectionCard>
      ))}
    </div>
  );
}

function Detail({
  lot,
  onEdit,
  onPrimaryChanged,
  onConversionChanged,
  initialTab,
  headingRef,
  scientificName,
}: {
  lot: SeedLotResponse;
  onEdit: MouseEventHandler<HTMLButtonElement>;
  onPrimaryChanged?: (photo: PrimaryPhoto | null) => void;
  onConversionChanged?: () => void;
  initialTab?: string;
  headingRef?: RefObject<HTMLHeadingElement | null>;
  scientificName?: string;
}) {
  const recordName = useRecordName();
  const auth = useAuth();
  const [transaction, setTransaction] = useState<OrderDetail | null>(null);
  useEffect(() => {
    if (!lot.order_id) return;
    const controller = new AbortController();
    getOrder(lot.order_id, 0, controller.signal)
      .then((order) => {
        if (!controller.signal.aborted) setTransaction(order);
      })
      .catch((error: unknown) => {
        if (
          !controller.signal.aborted &&
          error instanceof ApiError &&
          error.status === 401
        )
          auth.sessionExpired();
      });
    return () => {
      controller.abort();
    };
  }, [lot.order_id, lot.updated_at, auth]);
  const linkedTransaction =
    transaction?.id === lot.order_id ? transaction : null;
  const summarySupplier = linkedTransaction?.supplier ?? lot.supplier;

  const [tab, setTab] = useState(
    initialTab &&
      ["overview", "sowings", "photos", "lineage"].includes(initialTab)
      ? initialTab
      : "overview",
  );
  return (
    <section
      className="seed-detail collection-detail"
      aria-label="Seed lot detail"
    >
      <Breadcrumbs
        items={[
          { label: "Collection", href: "#/dashboard" },
          { label: "Seeds", href: "#/seeds" },
        ]}
      />
      <DetailHeader
        headingRef={headingRef}
        visual={
          lot.primary_photo && (
            <div className="collection-primary-detail">
              <RecordVisual
                photo={lot.primary_photo}
                label={recordName(lot, "Seed lot")}
                identity={lot.botanical_identity}
                kind={"seed"}
              />
            </div>
          )
        }
        eyebrow="Seed lot"
        title={recordName(lot, "Unlabelled seed lot")}
        secondary={
          <a href={`#/identities/${lot.botanical_identity.id}`}>
            <BotanicalName
              label={lot.botanical_identity.display_label}
              scientificName={scientificName}
            />
          </a>
        }
        status={
          <>
            <span
              className={`lifecycle-badge lifecycle-badge--${lot.lifecycle}`}
            >
              {lifecycleLabels[lot.lifecycle]}
            </span>
            {lot.location && (
              <a href={`#/locations/${lot.location.id}`}>
                {lot.location.display_path}
              </a>
            )}
          </>
        }
        primaryActions={
          lot.lifecycle === "active" ? (
            <a
              className="button-link"
              href={`#/sowings?action=start&seedLot=${lot.id}`}
            >
              Start sowing
            </a>
          ) : undefined
        }
        editLabel="Edit seed lot"
        onEdit={onEdit}
        overflow={
          <a
            className="button-link button--secondary"
            href={labelComposerHref("seed-lot", lot.id)}
          >
            Print label
          </a>
        }
      />
      {lot.lifecycle !== "active" && (
        <div className="contextual-actions">
          <p className="field-help">
            This historical SeedLot remains available for review. Source
            adjustment requires an active lot.
          </p>
        </div>
      )}
      <DetailTabs
        tabs={[
          { id: "overview", label: "Overview" },
          { id: "sowings", label: "Sowings" },
          { id: "photos", label: "Photos" },
          { id: "lineage", label: "Lineage" },
        ]}
        selected={tab}
        onSelect={(next) => {
          setTab(next);
          window.history.replaceState(
            null,
            "",
            `#/seeds/${lot.id}?tab=${next}`,
          );
        }}
      />
      {tab === "overview" && (
        <div
          id="panel-overview"
          className="detail-tab-panel seed-overview"
          role="tabpanel"
          aria-labelledby="tab-overview"
        >
          <div className="seed-overview-facts">
            <h3>At a glance</h3>
            <dl className="seed-current-summary" aria-label="Current inventory">
              <div className="seed-summary-lifecycle">
                <dt>Lifecycle</dt>
                <dd>
                  <span
                    className={`lifecycle-badge lifecycle-badge--${lot.lifecycle}`}
                  >
                    {lifecycleLabels[lot.lifecycle]}
                  </span>
                </dd>
              </div>
              <div className="seed-summary-quantity">
                <dt>{inventoryLabel(lot)}</dt>
                <dd>{quantityLabel(lot)}</dd>
              </div>
              <div className="seed-summary-storage">
                <dt>Storage</dt>
                <dd>
                  {lot.location ? (
                    <a href={`#/locations/${lot.location.id}`}>
                      {lot.location.display_path}
                    </a>
                  ) : (
                    "Not recorded"
                  )}
                </dd>
              </div>
            </dl>
          </div>
          <div className="seed-overview-main seed-summary-sections">
            <section
              className="seed-fact-group"
              aria-labelledby="seed-overview-acquisition"
            >
              <h4 id="seed-overview-acquisition">Acquisition</h4>
              <p className="seed-fact-lead">
                {sourceLabels[lot.source_kind]}
                {lot.source_detail ? ` — ${lot.source_detail}` : ""}
              </p>
              <p>
                {summarySupplier ? (
                  <a href={`#/suppliers/${summarySupplier.id}`}>
                    {summarySupplier.name}
                  </a>
                ) : (
                  "Supplier not recorded"
                )}
              </p>
              {lot.order_id && (
                <small className="field-help">
                  {linkedTransaction?.supplier
                    ? "From linked Order"
                    : linkedTransaction
                      ? "Recorded on this seed lot; Order Supplier not recorded"
                      : "Recorded on this seed lot"}
                </small>
              )}
              <p className="seed-secondary-fact">
                Order:{" "}
                {lot.order ? (
                  <a href={`#/orders/${lot.order.id}`}>
                    {lot.order.order_reference ?? "Purchase order"}
                  </a>
                ) : (
                  "Not linked"
                )}
              </p>
            </section>
            <section
              className="seed-fact-group seed-origin"
              aria-labelledby="seed-overview-source"
            >
              <h4 id="seed-overview-source">Origin</h4>
              <p className="seed-fact-lead">
                {lot.provenance_site ? (
                  <a href={`#/geography/${lot.provenance_site.id}`}>
                    {lot.provenance_site.geographic_place_path
                      ? `${lot.provenance_site.geographic_place_path} → `
                      : ""}
                    {lot.provenance_site.name}
                  </a>
                ) : (
                  "Provenance site not recorded"
                )}
              </p>
              <p>
                {lot.material_provenance ? (
                  <a href={`#/geography?place=${lot.material_provenance.id}`}>
                    {lot.material_provenance.display_path}
                  </a>
                ) : (
                  "Material provenance not recorded"
                )}
              </p>
            </section>
            <section
              className="seed-fact-group seed-dates"
              aria-labelledby="seed-overview-dates"
            >
              <h4 id="seed-overview-dates">Dates &amp; condition</h4>
              <dl>
                <div>
                  <dt>Acquired</dt>
                  <dd>{dateLabel(lot.acquisition_date)}</dd>
                </div>
                <div>
                  <dt>Harvested</dt>
                  <dd>{dateLabel(lot.harvest_date)}</dd>
                </div>
                <div>
                  <dt>Expected viability</dt>
                  <dd>{dateLabel(lot.expected_viability_until)}</dd>
                </div>
              </dl>
            </section>
            <UpcomingActivities
              kind={"seed_lot"}
              id={lot.id}
              current={lot.lifecycle === "active"}
            />
            {lot.harvest_conversion_id && (
              <div className="seed-overview-conversion">
                <ConversionHistory
                  kind="seed_lot_id"
                  id={lot.id}
                  onChanged={onConversionChanged}
                />
              </div>
            )}
            {lot.notes && (
              <section
                aria-labelledby="seed-overview-notes"
                className="seed-fact-group seed-fact-group--notes"
              >
                <h4 id="seed-overview-notes">Notes</h4>
                <p className="preserve-lines">{lot.notes}</p>
              </section>
            )}
          </div>
        </div>
      )}
      {tab === "sowings" && (
        <div
          id="panel-sowings"
          className="detail-tab-panel"
          role="tabpanel"
          aria-labelledby="tab-sowings"
        >
          <RelatedSowings seedLotId={lot.id} />
        </div>
      )}
      {tab === "lineage" && (
        <div
          id="panel-lineage"
          className="detail-tab-panel"
          role="tabpanel"
          aria-labelledby="tab-lineage"
        >
          <LineagePanel kind="seed-lots" id={lot.id} />
        </div>
      )}
      {tab === "photos" && (
        <div
          id="panel-photos"
          className="detail-tab-panel"
          role="tabpanel"
          aria-labelledby="tab-photos"
        >
          <PhotosSection
            key={lot.id}
            presentation="compact"
            target="seed_lot"
            targetId={lot.id}
            targetLabel={recordName(lot, "Unlabelled seed lot")}
            primaryPhoto={lot.primary_photo}
            onPrimaryChanged={onPrimaryChanged}
          />
        </div>
      )}
    </section>
  );
}

const seedPage = {
  eyebrow: "Collection",
  title: "Seeds",
  titleId: "seeds-title",
  description: "Track seed lots from acquisition through sowing and history.",
};

export function SeedLotScreen({
  initialId,
  initialTab,
  initialIdentityId,
  initialOrderId,
  startCreating = false,
}: {
  initialId?: string;
  initialTab?: string;
  initialIdentityId?: string;
  initialOrderId?: string;
  startCreating?: boolean;
} = {}) {
  const recordName = useRecordName();

  const auth = useAuth();
  const [inventory, setInventory] = useState<InventoryState>({
    status: "loading",
  });
  const [references, setReferences] = useState<References | null>(null);
  const scientificNames = useMemo(
    () =>
      new Map<string, string>(
        references?.identities.map((identity) => [
          identity.id,
          identity.scientific_name,
        ]) ?? [],
      ),
    [references],
  );
  usePublishRecordIdentities(references?.identities);
  const [attempt, setAttempt] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(
    initialId ?? null,
  );
  const [detailOpen, setDetailOpen] = useState(Boolean(initialId));
  const detailHeading = useRef<HTMLHeadingElement>(null);
  const view = useDirectoryView("seed_lots", () => {
    setSelectedId(null);
    setDetailOpen(false);
  });
  const filter = view.state.lifecycle;
  const setFilter = (value: "active" | "history" | "all") => {
    view.update("lifecycle", value);
  };
  const search = view.state.q;
  const setSearch = (value: string) => {
    view.update("q", value);
  };

  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<FormState>(blankForm);
  const [save, setSave] = useState<SaveState>({ status: "idle" });
  const [context, setContext] = useState<{
    kind: ContextKind;
    query: string;
  } | null>(null);
  const [contextError, setContextError] = useState<string | null>(null);
  const [contextSaving, setContextSaving] = useState(false);
  const feedback = useRef<HTMLDivElement>(null);
  const contextTrigger = useRef<HTMLElement | null>(null);
  const contextualCreationStarted = useRef(false);
  const [candidateOrderId, setCandidateOrderId] = useState("");
  const [purchaseConfirmation, setPurchaseConfirmation] =
    useState<PurchaseApply | null>(null);
  const [creationPurchaseContext, setCreationPurchaseContext] =
    useState<AcquisitionContext | null>(null);
  const creationCsrf =
    "csrfToken" in auth.state ? auth.state.csrfToken : undefined;
  const [orderContext, setOrderContext] = useState<OrderDetail | null>(null);
  const [orderContextError, setOrderContextError] = useState(false);
  const editBaseline = useRef("");
  const editTrigger = useRef<HTMLButtonElement | null>(null);
  const directEditHandled = useRef(false);
  const edit = useEditRoute({
    routeIsEdit: initialTab === "edit",
    canDismiss: () => {
      if (
        save.status === "saving" ||
        contextSaving ||
        context ||
        candidateOrderId
      )
        return false;
      return (
        JSON.stringify(form) === editBaseline.current ||
        window.confirm("Discard unsaved seed lot changes?")
      );
    },
    onDismiss: () => {
      setEditing(false);
      setSave((current) =>
        current.status === "success" ? current : { status: "idle" },
      );
      if (!edit.modal && selectedId)
        setRecordRoute(`#/seeds/${selectedId}`, true);
    },
  });
  const lastRouteId = useRef(initialId);
  useEffect(() => {
    if (lastRouteId.current === initialId) return;
    lastRouteId.current = initialId;
    if (edit.modal) return;
    const timeout = window.setTimeout(() => {
      if (initialId) setSelectedId(initialId);
      setDetailOpen(Boolean(initialId));
    }, 0);
    return () => {
      window.clearTimeout(timeout);
    };
  }, [initialId, edit.modal]);

  useEffect(() => {
    if (!initialOrderId || !startCreating || !creationCsrf) return;
    const controller = new AbortController();
    getOrder(initialOrderId, 0, controller.signal)
      .then(async (order) => {
        const review = await previewPurchase(
          initialOrderId,
          {},
          controller.signal,
        );
        if (controller.signal.aborted) return;
        const result = await applyPurchase(
          initialOrderId,
          {
            context: review.current,
            expected_order_updated_at: review.order.updated_at,
            use_order_supplier: true,
            use_order_date: false,
          },
          creationCsrf,
          controller.signal,
        );
        // applyPurchase carries the same AbortSignal through the draft-only request.
        controller.signal.throwIfAborted();
        setOrderContext(order);
        setCreationPurchaseContext(result.context);
        setPurchaseConfirmation(result.confirmation);
        setOrderContextError(false);
      })
      .catch(() => {
        if (!controller.signal.aborted) setOrderContextError(true);
      });
    return () => {
      controller.abort();
    };
  }, [initialOrderId, startCreating, attempt, creationCsrf]);
  const {
    expanded: creationExpanded,
    triggerRef: creationTriggerRef,
    panelRef: creationPanelRef,
    open: openCreation,
    close: closeCreation,
    focusFirst: focusCreation,
  } = useCreationDisclosure();

  useEffect(() => {
    if (
      !startCreating ||
      !references ||
      (initialOrderId && (!orderContext || !creationPurchaseContext)) ||
      contextualCreationStarted.current
    )
      return;
    contextualCreationStarted.current = true;
    setSelectedId(null);
    setEditing(true);
    setDetailOpen(true);
    setForm({
      ...blankForm(),
      botanicalIdentityId: initialIdentityId ?? "",
      ...(creationPurchaseContext
        ? {
            orderId: creationPurchaseContext.order_id ?? "",
            supplierId: creationPurchaseContext.supplier_id ?? "",
            sourceKind: creationPurchaseContext.source_kind,
            acquisitionDate: creationPurchaseContext.acquisition_date ?? null,
          }
        : {}),
    });
    setSave({ status: "idle" });
    openCreation();
  }, [
    initialIdentityId,
    initialOrderId,
    orderContext,
    creationPurchaseContext,
    openCreation,
    references,
    startCreating,
  ]);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      listSeedLots(controller.signal),
      listBotanicalIdentities(controller.signal),
      listSuppliers(controller.signal),
      listLocations(controller.signal),
      listGeographicPlaces(controller.signal),
      listProvenanceSites(controller.signal),
    ])
      .then(([lots, identities, suppliers, locations, places, sites]) => {
        setInventory({ status: "ready", lots });
        setReferences({ identities, suppliers, locations, places, sites });
        setSelectedId((current) =>
          current && lots.some(({ id }) => id === current) ? current : null,
        );
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else setInventory({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [auth, attempt]);

  useEffect(() => {
    if (save.status === "error") feedback.current?.focus();
  }, [save]);

  const lots = useMemo(
    () => (inventory.status === "ready" ? inventory.lots : []),
    [inventory],
  );
  const selected = lots.find(({ id }) => id === selectedId) ?? null;
  useEffect(() => {
    if (initialTab !== "edit") {
      directEditHandled.current = false;
      return;
    }
    if (edit.modal) {
      // This edit entry already belongs to the contextual workspace. Closing it
      // must not reopen the fallback while the browser processes history.back().
      directEditHandled.current = true;
      return;
    }
    if (directEditHandled.current || !selected) return;
    directEditHandled.current = true;
    const timeout = window.setTimeout(() => {
      const values = formFrom(selected);
      editBaseline.current = JSON.stringify(values);
      setForm(values);
      setEditing(true);
      setDetailOpen(true);
    }, 0);
    return () => {
      window.clearTimeout(timeout);
    };
  }, [initialTab, edit.modal, selected]);

  const visible = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return lots.filter((lot) => {
      const lifecycleMatch =
        filter === "all" ||
        (filter === "active"
          ? lot.lifecycle === "active"
          : lot.lifecycle !== "active");
      const textMatch =
        !query ||
        [
          lot.botanical_identity.display_label,
          lot.label,
          lot.supplier?.name,
          lot.location?.display_path,
          lot.material_provenance?.display_path,
        ].some((value) => value?.toLocaleLowerCase().includes(query));
      return lifecycleMatch && textMatch;
    });
  }, [filter, lots, search]);

  const bulkChoices = visible.map((lot) => ({
    kind: "seed_lot" as const,
    id: lot.id,
    label: `Seed Lot · ${recordName(lot, "Unlabelled seed lot")}`,
    eligible: lot.lifecycle === "active",
  }));
  const bulk = useBulkSelection(
    JSON.stringify(view.state) + String(initialId) + String(editing),
    bulkChoices,
  );
  if (!references && inventory.status === "loading") {
    return (
      <section
        className="workspace seeds-workspace"
        aria-labelledby="seeds-title"
      >
        <WorkspaceIntro {...seedPage} />
        <p role="status">Loading seed inventory…</p>
      </section>
    );
  }
  if (inventory.status === "error" || !references) {
    return (
      <section
        className="workspace seeds-workspace"
        aria-labelledby="seeds-title"
      >
        <WorkspaceIntro {...seedPage} />
        <div className="notice notice--error" role="alert">
          <p>
            Florabase could not load the seed inventory or its reference
            choices.
          </p>
          <button
            type="button"
            onClick={() => {
              setAttempt((value) => value + 1);
            }}
          >
            Retry
          </button>
        </div>
      </section>
    );
  }
  if (
    auth.state.status !== "authenticated" &&
    auth.state.status !== "logging-out" &&
    auth.state.status !== "logout-failed"
  )
    return null;
  const csrfToken = auth.state.csrfToken;
  const pending = save.status === "saving";

  function startCreate() {
    setPurchaseConfirmation(null);
    setCandidateOrderId("");
    setSelectedId(null);
    setEditing(true);
    setDetailOpen(true);
    setForm(blankForm());
    setSave({ status: "idle" });
    openCreation();
  }
  function startEdit(lot: SeedLotResponse, trigger: HTMLButtonElement) {
    editTrigger.current = trigger;
    directEditHandled.current = true;
    setPurchaseConfirmation(null);
    setCandidateOrderId("");
    if (creationExpanded) closeCreation({ returnFocus: false });
    setSelectedId(lot.id);
    setEditing(true);
    const values = formFrom(lot);
    editBaseline.current = JSON.stringify(values);
    setForm(values);
    edit.open(`#/seeds/${lot.id}?tab=edit`);
    setSave({ status: "idle" });
  }
  function openContext(kind: ContextKind, query: string) {
    contextTrigger.current = document.activeElement as HTMLElement | null;
    setContext({ kind, query });
    setContextError(null);
  }
  function closeContext() {
    setContext(null);
    setContextError(null);
    window.setTimeout(() => contextTrigger.current?.focus(), 0);
  }

  async function refreshLots(authoritative: SeedLotResponse) {
    setInventory((current) => {
      if (current.status !== "ready") return current;
      const exists = current.lots.some(({ id }) => id === authoritative.id);
      return {
        status: "ready",
        lots: exists
          ? current.lots.map((lot) =>
              lot.id === authoritative.id ? authoritative : lot,
            )
          : [...current.lots, authoritative],
      };
    });
    const refreshed = await listSeedLots();
    setInventory({ status: "ready", lots: refreshed });
    setSelectedId(authoritative.id);
  }

  async function submit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (pending) return;
    const quantity = Number(form.quantityValue);
    const errors: string[] = [];
    if (!form.botanicalIdentityId) errors.push("Choose a botanical identity.");
    if (form.quantityValue && (!Number.isFinite(quantity) || quantity < 0))
      errors.push("Enter a non-negative quantity.");
    if (
      form.quantityValue &&
      quantity === 0 &&
      (form.lifecycle !== "exhausted" || form.quantityApproximate)
    )
      errors.push(
        "A known zero quantity is only valid for an exhausted lot, and it must be exact.",
      );
    if (
      form.quantityUnit === "seeds" &&
      form.quantityValue &&
      !Number.isInteger(quantity)
    )
      errors.push("Seed count must be a whole number.");
    if (errors.length) {
      setSave({ status: "error", messages: errors });
      return;
    }
    if (!selected && form.orderId && !purchaseConfirmation) {
      setCandidateOrderId(form.orderId);
      setSave({
        status: "error",
        field: "order_id",
        messages: [
          "Review purchase context before creating this linked SeedLot.",
        ],
      });
      return;
    }
    const wasCreating = !selected;
    setSave({ status: "saving" });
    try {
      const payload = payloadFrom(form);
      if (selected?.harvest_conversion_id) {
        payload.producer_plant_id = selected.producer_plant_id;
        payload.producer_plant_group_id = selected.producer_plant_group_id;
      }
      const lot = selected
        ? await updateSeedLot(selected.id, payload, csrfToken)
        : form.orderId && purchaseConfirmation
          ? await createPurchaseLot(
              form.orderId,
              payload,
              purchaseConfirmation,
              csrfToken,
            )
          : await createSeedLot(payload, csrfToken);
      await refreshLots(lot);
      if (edit.modal) edit.close(true);
      else {
        setEditing(false);
        setDetailOpen(true);
        if (initialTab === "edit") setRecordRoute(`#/seeds/${lot.id}`, true);
      }
      if (wasCreating) closeCreation({ returnFocus: false });
      setSave({
        status: "success",
        message: selected
          ? "Seed lot changes were saved."
          : "Seed lot was added to the collection.",
      });
      if (wasCreating) setRecordRoute(`#/seeds/${lot.id}`);
      if (!edit.modal)
        window.setTimeout(() => detailHeading.current?.focus(), 0);
    } catch (error: unknown) {
      const orderError =
        error instanceof ApiError ? seedLotOrderError(error) : undefined;
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else if (error instanceof ApiError && error.status === 422) {
        setSave({
          status: "error",
          messages: seedLotValidationMessages(error),
          field: firstValidationField(error),
        });
      } else if (orderError)
        setSave({ status: "error", messages: [orderError], field: "order_id" });
      else if (error instanceof ApiError && error.status === 403)
        setSave({
          status: "error",
          messages: [
            "Florabase could not authorize this change. Refresh the page and try again.",
          ],
        });
      else
        setSave({
          status: "error",
          messages: [
            "Florabase could not save or refresh this seed lot. Check the connection and try again.",
          ],
        });
    }
  }

  async function submitContext(
    event: SyntheticEvent<HTMLFormElement, SubmitEvent>,
  ) {
    event.preventDefault();
    if (!context || contextSaving) return;
    const data = new FormData(event.currentTarget);
    const value = (name: string) => {
      const item = data.get(name);
      return typeof item === "string" ? item : "";
    };
    setContextSaving(true);
    setContextError(null);
    try {
      if (context.kind === "identity") {
        const identity = await createBotanicalIdentity(
          {
            scientific_name: value("scientific_name"),
            cultivar_name: value("cultivar_name") || null,
            common_name: value("common_name") || null,
          },
          csrfToken,
        );
        const identities = await listBotanicalIdentities();
        setReferences((current) => current && { ...current, identities });
        setForm((current) => ({
          ...current,
          botanicalIdentityId: identity.id,
        }));
      } else if (context.kind === "supplier") {
        const supplier = await createSupplier(
          {
            name: value("name"),
            kind: value("kind") as
              | "seller"
              | "nursery"
              | "supermarket"
              | "person"
              | "exchange"
              | "other",
          },
          csrfToken,
        );
        const suppliers = await listSuppliers();
        setReferences((current) => current && { ...current, suppliers });
        setForm((current) => ({ ...current, supplierId: supplier.id }));
      } else if (context.kind === "location") {
        const location = await createLocation(
          { name: value("name"), parent_id: value("parent_id") || null },
          csrfToken,
        );
        const locations = await listLocations();
        setReferences((current) => current && { ...current, locations });
        setForm((current) => ({ ...current, locationId: location.id }));
      } else {
        const place = await createGeographicPlace(
          {
            name: value("name"),
            parent_id: value("parent_id"),
            place_type: "other_named_area",
          },
          csrfToken,
        );
        const places = await listGeographicPlaces();
        setReferences((current) => current && { ...current, places });
        setForm((current) => ({
          ...current,
          materialProvenancePlaceId: place.id,
        }));
      }
      closeContext();
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else if (
        context.kind === "identity" &&
        error instanceof ApiError &&
        error.status === 409
      ) {
        const id = conflictExistingId(error);
        if (id) {
          try {
            const identity = await getBotanicalIdentity(id);
            setReferences(
              (current) =>
                current && {
                  ...current,
                  identities: [
                    ...current.identities.filter((item) => item.id !== id),
                    identity,
                  ],
                },
            );
            setForm((current) => ({ ...current, botanicalIdentityId: id }));
            closeContext();
          } catch {
            setContextError(
              "That botanical identity already exists, but Florabase could not load it.",
            );
          }
        } else
          setContextError(
            "That botanical identity already exists. Search the existing choices and select it.",
          );
      } else if (error instanceof ApiError && error.status === 422) {
        const messages =
          context.kind === "identity"
            ? validationMessages(error)
            : context.kind === "supplier"
              ? supplierValidationMessages(error)
              : context.kind === "location"
                ? locationValidationMessages(error)
                : geographyValidationMessages(error);
        setContextError(messages.join(" "));
      } else if (error instanceof ApiError && error.status === 403)
        setContextError(
          "Florabase could not authorize this reference change. Refresh and try again.",
        );
      else
        setContextError(
          "Florabase could not create this reference. Your seed lot details are still here.",
        );
    } finally {
      setContextSaving(false);
    }
  }

  const lifecycleField = (
    <div className="field">
      <label htmlFor="lifecycle">Lifecycle</label>
      <select
        id="lifecycle"
        value={form.lifecycle}
        disabled={pending || selected?.lifecycle === "reversed"}
        onChange={(event) => {
          const lifecycle = event.currentTarget.value as SeedLotLifecycle;
          setForm((current) => ({
            ...current,
            lifecycle,
          }));
        }}
      >
        {Object.entries(lifecycleLabels)
          .filter(
            ([value]) =>
              value !== "reversed" || selected?.lifecycle === "reversed",
          )
          .map(([value, label]) => (
            <option value={value} key={value}>
              {label}
            </option>
          ))}
      </select>
      <small>
        Use Exhausted for an exact known zero quantity. Historical lots remain
        editable.
      </small>
    </div>
  );

  const editor = editing ? (
    <EditWorkspace
      returnFocusTo={editTrigger}
      modal={edit.modal && Boolean(selected)}
      title={
        selected ? `Edit ${recordName(selected, "seed lot")}` : "Add seed lot"
      }
      onClose={() => {
        edit.close();
      }}
    >
      <form
        className="seed-form collection-form"
        onClickCapture={(event) => {
          if (!selected || !(event.target instanceof Element)) return;
          const link = event.target.closest<HTMLAnchorElement>('a[href^="#"]');
          if (
            link &&
            link.target !== "_blank" &&
            link.hash !== window.location.hash &&
            !edit.prepareDeparture()
          )
            event.preventDefault();
        }}
        onSubmit={(event) => void submit(event)}
        noValidate
      >
        <Breadcrumbs
          items={[
            ...(!selected
              ? [{ label: "Collection", href: "#/dashboard" }]
              : []),
            { label: "Seeds", href: "#/seeds" },
            { label: selected ? "Edit seed lot" : "New" },
          ]}
        />
        <DetailHeader
          eyebrow="Seed lot"
          title={
            selected
              ? `Edit ${recordName(selected, "seed lot")}`
              : "Add seed lot"
          }
          secondary={
            selected && (
              <DetailContext
                items={[
                  {
                    label: "Botanical identity",
                    value: selected.botanical_identity.display_label,
                  },
                ]}
              />
            )
          }
        />
        {!selected && (
          <p className="seed-create-description">
            Record a physical seed lot in the collection.
          </p>
        )}
        {save.status === "error" && (
          <div
            className="notice notice--error"
            role="alert"
            tabIndex={-1}
            ref={feedback}
          >
            <ul>
              {save.messages.map((message) => (
                <li key={message}>{message}</li>
              ))}
            </ul>
          </div>
        )}
        <FormSections
          mode={selected ? "edit" : "page"}
          disabled={pending}
          error={save.status === "error" ? save : undefined}
          errorFields={[
            { match: /order/i, selector: "#seed-order" },
            {
              match: /location|storage/i,
              selector: '[data-form-panel="inventory"] [role="combobox"]',
            },
            {
              match: /supplier/i,
              selector: '[data-form-panel="acquisition"] [role="combobox"]',
            },
            {
              match: /provenance site/i,
              selector:
                '[data-form-panel="origin"] .field:last-child [role="combobox"]',
            },
            {
              match: /provenance/i,
              selector: '[data-form-panel="origin"] [role="combobox"]',
            },
            { match: /identity/i, selector: '[role="combobox"]' },
            {
              match: /quantity|seed count/i,
              selector: '[aria-label="Quantity value"]',
            },
            { match: /label/i, selector: "#lot-label" },
            { match: /source detail/i, selector: "#source-detail" },
            { match: /source/i, selector: "#source-kind" },
            { match: /acquisition/i, selector: "#acquisition-year" },
            { match: /harvest/i, selector: "#harvest-year" },
            { match: /viability/i, selector: "#viability-year" },
            { match: /notes/i, selector: "#seed-notes" },
            { match: /lifecycle/i, selector: "#lifecycle" },
          ]}
          panels={[
            {
              id: "essentials",
              label: selected ? "Essentials" : "Identity",
              content: (
                <>
                  <ReferencePicker
                    label="Botanical identity"
                    help="A shared botanical identity keeps the botanical name consistent across records; it does not establish lineage."
                    required
                    disabled={pending}
                    choices={references.identities.map((item) => ({
                      id: item.id,
                      label: item.display_label,
                      scientificName: item.scientific_name,
                    }))}
                    value={form.botanicalIdentityId}
                    onChange={(id) => {
                      setForm((current) => ({
                        ...current,
                        botanicalIdentityId: id,
                      }));
                    }}
                    onCreate={(query) => {
                      openContext("identity", query);
                    }}
                    createLabel="Create identity"
                  />
                  {!selected && (
                    <p className="field-help seed-task-hint">
                      One seed lot represents one physical packet or bag. Add
                      another record for a separate packet, even of the same
                      taxon.
                    </p>
                  )}

                  <div className="field">
                    <label htmlFor="lot-label">Lot label</label>
                    <input
                      id="lot-label"
                      value={form.label}
                      disabled={pending}
                      onChange={(event) => {
                        const value = event.currentTarget.value;
                        setForm((current) => ({
                          ...current,
                          label: value,
                        }));
                      }}
                    />
                  </div>
                  {selected && lifecycleField}
                </>
              ),
            },
            {
              id: "inventory",
              label: "Inventory",
              content: (
                <>
                  <fieldset
                    aria-describedby="seed-quantity-help"
                    className="quantity-field"
                  >
                    <legend>Quantity</legend>
                    <div className="quantity-controls">
                      <input
                        aria-label="Quantity value"
                        inputMode="decimal"
                        value={form.quantityValue}
                        disabled={pending}
                        onChange={(event) => {
                          const value = event.currentTarget.value;
                          setForm((current) => ({
                            ...current,
                            quantityValue: value,
                          }));
                        }}
                      />
                      <select
                        aria-label="Quantity unit"
                        value={form.quantityUnit}
                        disabled={pending}
                        onChange={(event) => {
                          const value = event.currentTarget
                            .value as FormState["quantityUnit"];
                          setForm((current) => ({
                            ...current,
                            quantityUnit: value,
                          }));
                        }}
                      >
                        <option value="seeds">seeds</option>
                        <option value="g">g</option>
                        <option value="mg">mg</option>
                      </select>
                      <label className="checkbox-label">
                        <input
                          type="checkbox"
                          checked={form.quantityApproximate}
                          disabled={pending || !form.quantityValue}
                          onChange={(event) => {
                            const checked = event.currentTarget.checked;
                            setForm((current) => ({
                              ...current,
                              quantityApproximate: checked,
                            }));
                          }}
                        />
                        Approximately
                      </label>
                    </div>
                    <FieldHelp id="seed-quantity-help">
                      Enter a value only when known, mark estimates as
                      approximate, and leave the quantity empty rather than
                      guessing.
                    </FieldHelp>
                  </fieldset>

                  {!selected && lifecycleField}
                  <ReferencePicker
                    label="Storage location"
                    help="Where this SeedLot is currently kept in your collection, not where it originated."
                    disabled={pending}
                    choices={locationsForScope(
                      references.locations,
                      "seed_lots",
                    ).map((item) => ({
                      id: item.id,
                      label: item.display_path,
                      retired: Boolean(item.retired_at),
                    }))}
                    value={form.locationId}
                    onChange={(id) => {
                      setForm((current) => ({
                        ...current,
                        locationId: id,
                      }));
                    }}
                    onCreate={(query) => {
                      openContext("location", query);
                    }}
                    createLabel="Create location"
                  />
                </>
              ),
            },
            {
              id: "acquisition",
              label: "Acquisition",
              content: (
                <>
                  <div className="field">
                    <label htmlFor="source-kind">Source</label>
                    <select
                      id="source-kind"
                      value={form.sourceKind}
                      disabled={
                        pending || Boolean(selected?.harvest_conversion_id)
                      }
                      onChange={(event) => {
                        setPurchaseConfirmation(null);
                        const value = event.currentTarget
                          .value as SeedLotSourceKind;
                        setForm((current) => ({
                          ...current,
                          sourceKind: value,
                          sourceDetail:
                            value === "other" ? current.sourceDetail : "",
                        }));
                      }}
                    >
                      {Object.entries(sourceLabels).map(([value, label]) => (
                        <option value={value} key={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </div>
                  {form.sourceKind === "other" && (
                    <div className="field">
                      <label htmlFor="source-detail">Source detail </label>
                      <input
                        id="source-detail"
                        value={form.sourceDetail}
                        disabled={pending}
                        onChange={(event) => {
                          const value = event.currentTarget.value;
                          setForm((current) => ({
                            ...current,
                            sourceDetail: value,
                          }));
                        }}
                      />
                    </div>
                  )}
                  <OrderPicker
                    independentFields={
                      <>
                        <ReferencePicker
                          label="Supplier"
                          help="Supplier does not establish its biological origin."
                          disabled={pending}
                          choices={references.suppliers.map((item) => ({
                            id: item.id,
                            label: item.name,
                            retired: Boolean(item.retired_at),
                          }))}
                          value={form.supplierId}
                          onChange={(id) => {
                            setForm((current) => ({
                              ...current,
                              supplierId: id,
                            }));
                            setPurchaseConfirmation(null);
                          }}
                          onCreate={(query) => {
                            openContext("supplier", query);
                          }}
                          createLabel="Create supplier"
                        />
                        <div className="acquisition-date-slot">
                          <PartialDateField
                            id="acquisition"
                            label="Acquisition date"
                            helpText="Do not invent a missing month or day."
                            value={form.acquisitionDate}
                            onChange={(value) => {
                              setForm((current) => ({
                                ...current,
                                acquisitionDate: value,
                              }));
                              setPurchaseConfirmation(null);
                            }}
                            disabled={pending}
                          />
                        </div>
                      </>
                    }
                    retainedKnowledge={
                      <div
                        className="acquisition-retained"
                        aria-label="Recorded seed lot knowledge"
                      >
                        <strong>Recorded on this seed lot</strong>
                        <p>
                          Supplier:{" "}
                          {references.suppliers.find(
                            (item) => item.id === form.supplierId,
                          )?.name ??
                            (form.supplierId
                              ? ((selected?.supplier_id === form.supplierId
                                  ? selected.supplier?.name
                                  : null) ?? "Recorded Supplier")
                              : "Not recorded")}{" "}
                          · Acquisition date: {dateLabel(form.acquisitionDate)}
                        </p>
                      </div>
                    }
                    reviewAction={
                      <button
                        type="button"
                        className="button--secondary"
                        disabled={pending}
                        onClick={() => {
                          setCandidateOrderId(form.orderId);
                        }}
                      >
                        Review purchase context / use Order date
                      </button>
                    }
                    value={form.orderId}
                    supplierId={form.supplierId}
                    refreshKey={purchaseConfirmation?.expected_order_updated_at}
                    disabled={pending}
                    onChange={(id) => {
                      if (id) setCandidateOrderId(id);
                      else {
                        setForm((current) => ({
                          ...current,
                          orderId: "",
                        }));
                        setPurchaseConfirmation(null);
                      }
                    }}
                  />
                </>
              ),
            },
            {
              id: "origin",
              label: "Origin",
              content: (
                <>
                  <ReferencePicker
                    label="Material provenance"
                    help="Where the biological material originated, not its Supplier or current storage location."
                    disabled={pending}
                    choices={references.places.map((item) => ({
                      id: item.id,
                      label: item.display_path,
                      retired: Boolean(item.retired_at),
                    }))}
                    value={form.materialProvenancePlaceId}
                    onChange={(id) => {
                      setForm((current) => ({
                        ...current,
                        materialProvenancePlaceId: id,
                      }));
                    }}
                    onCreate={(query) => {
                      openContext("place", query);
                    }}
                    createLabel="Create local place"
                  />
                  <ReferencePicker
                    label="Precise provenance site"
                    disabled={pending}
                    choices={references.sites.map((site) => ({
                      id: site.id,
                      label: `${site.geographic_place_path ? `${site.geographic_place_path} → ` : ""}${site.name}`,
                    }))}
                    value={form.provenanceSiteId}
                    onChange={(id) => {
                      setForm((current) => ({
                        ...current,
                        provenanceSiteId: id,
                      }));
                    }}
                  />
                </>
              ),
            },
            {
              id: "details",
              label: "Seed details",
              content: (
                <>
                  <div className="partial-date-grid">
                    <PartialDateField
                      id="harvest"
                      label="Harvest date"
                      showHelp={false}
                      value={form.harvestDate}
                      onChange={(value) => {
                        setForm((current) => ({
                          ...current,
                          harvestDate: value,
                        }));
                      }}
                      disabled={pending}
                    />
                    <PartialDateField
                      id="viability"
                      label="Expected viability until"
                      showHelp={false}
                      value={form.expectedViabilityUntil}
                      onChange={(value) => {
                        setForm((current) => ({
                          ...current,
                          expectedViabilityUntil: value,
                        }));
                      }}
                      disabled={pending}
                    />
                  </div>

                  <div className="field">
                    <label htmlFor="seed-notes">Notes</label>
                    <textarea
                      id="seed-notes"
                      rows={4}
                      value={form.notes}
                      disabled={pending}
                      onChange={(event) => {
                        const value = event.currentTarget.value;
                        setForm((current) => ({
                          ...current,
                          notes: value,
                        }));
                      }}
                    />
                  </div>
                </>
              ),
            },
          ]}
          submit={
            <button type="submit" disabled={pending}>
              {pending ? "Saving…" : selected ? "Save changes" : "Add seed lot"}
            </button>
          }
          cancel={
            <button
              type="button"
              className="button--secondary"
              onClick={() => {
                if (selected) {
                  edit.close();
                  return;
                }
                setEditing(false);
                setSave({ status: "idle" });
                setForm(blankForm());
                closeCreation();
                setDetailOpen(false);
              }}
            >
              Cancel
            </button>
          }
        />
      </form>
    </EditWorkspace>
  ) : null;

  return (
    <section
      className="workspace seeds-workspace"
      aria-labelledby="seeds-title"
    >
      <div
        className="seed-context-page"
        inert={edit.modal}
        aria-hidden={edit.modal || undefined}
      >
        <WorkspaceIntro
          contextOnly={detailOpen || (editing && !edit.modal)}
          {...seedPage}
          tools={
            !(detailOpen || (editing && !edit.modal)) && (
              <DirectoryTools
                onReset={() => {
                  setFilter("all");
                }}
                name="Seeds"
                search={
                  <DirectorySearch
                    hideLabel
                    id="seed-search"
                    label="Search seed inventory"
                    placeholder="Search lots, identity or location"
                    value={search}
                    onChange={setSearch}
                  />
                }
                savedViews={
                  <SavedViews
                    presentation="dialog"
                    surface="seed_lots"
                    state={view.savedState}
                  />
                }
                filters={
                  <>
                    <DirectoryFilterSelect
                      label="Lifecycle"
                      value={filter}
                      onChange={setFilter}
                      options={[
                        { value: "active", label: "Active" },
                        { value: "history", label: "History" },
                        { value: "all", label: "All" },
                      ]}
                    />
                  </>
                }
                activeFilters={[
                  ...(filter !== "all"
                    ? [
                        {
                          label: "Lifecycle",
                          value: filter === "active" ? "Active" : "History",
                          onRemove: () => {
                            setFilter("all");
                          },
                        },
                      ]
                    : []),
                ]}
                actions={
                  <button
                    type="button"
                    ref={creationTriggerRef}
                    aria-expanded={creationExpanded}
                    aria-controls="new-seed-lot-panel"
                    onClick={() => {
                      if (creationExpanded) focusCreation();
                      else startCreate();
                    }}
                  >
                    + New seed lot
                  </button>
                }
              />
            )
          }
        />
        {orderContextError && (
          <div role="alert" className="notice notice--error">
            <p>
              Could not load the Order context. No seed lot has been created.
            </p>
            <button
              type="button"
              onClick={() => {
                setAttempt((value) => value + 1);
              }}
            >
              Retry Order context
            </button>
          </div>
        )}
        {initialOrderId &&
          startCreating &&
          !orderContext &&
          !orderContextError && <p role="status">Loading Order context…</p>}
        <div
          className={`seed-master-detail operational-layout directory-preview-layout${detailOpen || (editing && !edit.modal) ? " is-detail-view" : ""}`}
        >
          <section
            className="seed-master"
            aria-labelledby="seed-inventory-title"
          >
            <h3 className="sr-only" id="seed-inventory-title">
              Seed lot inventory
            </h3>
            <BulkToolbar
              selection={bulk}
              visible={bulkChoices}
              onSuccess={() => {
                setSelectedId(null);
                setDetailOpen(false);
                setAttempt((value) => value + 1);
              }}
            />
            {inventory.status === "ready" && (
              <DirectoryResults
                count={visible.length}
                actions={
                  <BulkSelect
                    selection={bulk}
                    visible={bulkChoices}
                    onStart={() => {
                      setSelectedId(null);
                      setDetailOpen(false);
                    }}
                  />
                }
              />
            )}
            {lots.length === 0 ? (
              <div className="empty-state">
                <h3>No seeds recorded yet</h3>
                <p>
                  Add a seed lot with only its botanical identity; everything
                  unknown can remain unknown.
                </p>
              </div>
            ) : visible.length === 0 ? (
              <div className="empty-state">
                <h3>No matching seed lots</h3>
                <p>
                  Try another search or lifecycle view. Historical records
                  remain available under History or All.
                </p>
              </div>
            ) : (
              <ul
                className="seed-list"
                aria-label="Seed inventory"
                tabIndex={0}
              >
                {visible.map((lot, bulkIndex) => (
                  <li
                    key={lot.id}
                    className={bulk.active ? "bulk-selection-row" : undefined}
                    data-selected={
                      bulk.checked({ kind: "seed_lot", id: lot.id }) ||
                      undefined
                    }
                  >
                    <BulkCheckbox
                      selection={bulk}
                      choice={bulkChoices[bulkIndex]}
                    />
                    <button
                      type="button"
                      className="seed-row"
                      aria-pressed={selectedId === lot.id}
                      onClick={() => {
                        if (bulk.active) {
                          bulk.toggle(bulkChoices[bulkIndex]);
                          return;
                        }
                        if (creationExpanded)
                          closeCreation({ returnFocus: false });
                        setSelectedId(lot.id);
                        const isMobile =
                          window.matchMedia("(max-width: 48rem)").matches;
                        setDetailOpen(isMobile);
                        if (isMobile) setRecordRoute(`#/seeds/${lot.id}`);
                        setEditing(false);
                        setSave({ status: "idle" });
                      }}
                    >
                      <span className="seed-primary">
                        <RecordVisual
                          photo={lot.primary_photo ?? null}
                          label={recordName(lot, "Seed lot")}
                          compact

                          identity={lot.botanical_identity}
                          kind={"seed"}
                        />
                        <span className="seed-primary__text">
                          <strong>
                            {recordName(lot, "Unlabelled seed lot")}
                          </strong>
                          <small>
                            <BotanicalName
                              label={lot.botanical_identity.display_label}
                              scientificName={scientificNames.get(
                                lot.botanical_identity_id,
                              )}
                            />
                          </small>
                        </span>
                      </span>
                      <span className="seed-quantity">
                        <strong>
                          {quantityLabel(lot)}
                          {lot.quantity && lot.lifecycle === "active"
                            ? " remaining"
                            : ""}
                        </strong>
                        {lot.lifecycle !== "active" && (
                          <small>Recorded quantity</small>
                        )}
                      </span>
                      <span className="seed-location">
                        {lot.location?.display_path ?? "Storage not recorded"}
                      </span>
                      <span
                        className={`lifecycle-badge lifecycle-badge--${lot.lifecycle}`}
                      >
                        {lifecycleLabels[lot.lifecycle]}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section
            id={creationExpanded ? "new-seed-lot-panel" : undefined}
            className={
              creationExpanded
                ? "seed-detail-pane seed-creation-panel"
                : "seed-detail-pane"
            }
            ref={creationExpanded ? creationPanelRef : undefined}
            aria-label="Seed lot detail and editor"
          >
            {save.status === "success" && (
              <div className="notice notice--success" role="status">
                {save.message}
              </div>
            )}
            {editing && !edit.modal ? (
              editor
            ) : selected ? (
              detailOpen ? (
                <div className="selected-seed">
                  <Detail
                    lot={selected}
                    headingRef={detailHeading}
                    scientificName={scientificNames.get(
                      selected.botanical_identity_id,
                    )}
                    onConversionChanged={() => {
                      void listSeedLots()
                        .then((lots) => {
                          setInventory({ status: "ready", lots });
                        })
                        .catch((failure: unknown) => {
                          if (
                            failure instanceof ApiError &&
                            failure.status === 401
                          )
                            auth.sessionExpired();
                          else setInventory({ status: "error" });
                        });
                    }}
                    initialTab={initialTab}
                    onPrimaryChanged={(photo) => {
                      setInventory((current) =>
                        current.status === "ready"
                          ? {
                              status: "ready",
                              lots: current.lots.map((lot) =>
                                lot.id === selected.id
                                  ? { ...lot, primary_photo: photo }
                                  : lot,
                              ),
                            }
                          : current,
                      );
                    }}
                    onEdit={(event) => {
                      startEdit(selected, event.currentTarget);
                    }}
                  />
                </div>
              ) : (
                <SeedLotPreview
                  lot={selected}
                  onOpen={() => {
                    setDetailOpen(true);
                    setRecordRoute(`#/seeds/${selected.id}`);
                  }}
                  onEdit={(event) => {
                    startEdit(selected, event.currentTarget);
                  }}
                />
              )
            ) : (
              <div className="empty-state seed-detail-empty">
                <h3>Select a seed lot</h3>
                <p>
                  Choose a lot from the inventory to inspect or edit it without
                  losing your place in the list.
                </p>
              </div>
            )}
          </section>
        </div>
      </div>
      {edit.modal && editor}
      {candidateOrderId && (
        <PurchaseContextDialog
          orderId={candidateOrderId}
          seedLotId={selected?.id}
          seedLotLabel={
            selected?.label ?? selected?.botanical_identity.display_label
          }
          expectedSeedVersion={selected?.updated_at}
          context={{
            source_kind: form.sourceKind,
            supplier_id: form.supplierId || null,
            acquisition_date: form.acquisitionDate,
            order_id: form.orderId || null,
          }}
          csrf={csrfToken}
          onCancel={() => {
            setCandidateOrderId("");
          }}
          onApplied={(result) => {
            setForm((current) => ({
              ...current,
              orderId: result.context.order_id ?? "",
              sourceKind: result.context.source_kind,
              supplierId: result.context.supplier_id ?? "",
              acquisitionDate: result.context.acquisition_date ?? null,
            }));
            setPurchaseConfirmation(result.confirmation);
            if (result.seed_lot) {
              const authoritative = result.seed_lot;
              editBaseline.current = JSON.stringify(formFrom(authoritative));
              setInventory((current) =>
                current.status === "ready"
                  ? {
                      ...current,
                      lots: current.lots.map((lot) =>
                        lot.id === authoritative.id ? authoritative : lot,
                      ),
                    }
                  : current,
              );
            }
            setSave({
              status: "success",
              message: result.seed_lot
                ? "Reviewed acquisition fields were saved. Other form drafts remain unsaved."
                : "Purchase context applied to this draft. Create the SeedLot to save it.",
            });
            setCandidateOrderId("");
          }}
        />
      )}
      {context && (
        <ContextDialog
          title={
            context.kind === "identity"
              ? "Create botanical identity"
              : context.kind === "supplier"
                ? "Create supplier"
                : context.kind === "location"
                  ? "Create storage location"
                  : "Create local geographic place"
          }
          onClose={closeContext}
        >
          <form onSubmit={(event) => void submitContext(event)}>
            {context.kind === "identity" ? (
              <>
                <div className="field">
                  <FieldLabel required htmlFor="context-scientific-name">
                    Scientific name
                  </FieldLabel>
                  <input
                    id="context-scientific-name"
                    name="scientific_name"
                    required
                    defaultValue={context.query}
                  />
                </div>
                <div className="field">
                  <label htmlFor="context-cultivar">Cultivar</label>
                  <input id="context-cultivar" name="cultivar_name" />
                </div>
                <div className="field">
                  <label htmlFor="context-common">Common name</label>
                  <input id="context-common" name="common_name" />
                </div>
              </>
            ) : context.kind === "supplier" ? (
              <>
                <div className="field">
                  <FieldLabel required htmlFor="context-name">
                    Name
                  </FieldLabel>
                  <input
                    id="context-name"
                    name="name"
                    required
                    defaultValue={context.query}
                  />
                </div>
                <div className="field">
                  <label htmlFor="context-kind">Kind</label>
                  <select id="context-kind" name="kind" defaultValue="seller">
                    <option value="seller">Seller</option>
                    <option value="nursery">Nursery</option>
                    <option value="supermarket">Supermarket</option>
                    <option value="person">Person</option>
                    <option value="exchange">Exchange</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </>
            ) : (
              <>
                <div className="field">
                  <label htmlFor="context-name">Name</label>
                  <input
                    id="context-name"
                    name="name"
                    required
                    defaultValue={context.query}
                  />
                </div>
                <ReferencePicker
                  label={"Parent"}
                  required={context.kind === "place"}
                  choices={
                    context.kind === "location"
                      ? locationsForScope(
                          references.locations,
                          "seed_lots",
                        ).map((item) => ({
                          id: item.id,
                          label: item.display_path,
                          retired: Boolean(item.retired_at),
                        }))
                      : references.places.map((item) => ({
                          id: item.id,
                          label: item.display_path,
                          retired: Boolean(item.retired_at),
                        }))
                  }
                  value=""
                  onChange={(id) => {
                    const hidden =
                      document.querySelector<HTMLInputElement>(
                        "#context-parent-id",
                      );
                    if (hidden) hidden.value = id;
                  }}
                />
                <input type="hidden" id="context-parent-id" name="parent_id" />
              </>
            )}
            {contextError && (
              <div className="notice notice--error" role="alert">
                {contextError}
              </div>
            )}
            <div className="actions">
              <button type="submit" disabled={contextSaving}>
                {contextSaving ? "Creating…" : "Create and select"}
              </button>
              <button
                type="button"
                className="button--secondary"
                onClick={closeContext}
              >
                Cancel
              </button>
            </div>
          </form>
        </ContextDialog>
      )}
    </section>
  );
}
