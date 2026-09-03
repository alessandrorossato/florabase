import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
  type SyntheticEvent,
} from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { useCreationDisclosure } from "../components/useCreationDisclosure";
import {
  Breadcrumbs,
  CollectionCard,
  DetailHeader,
  DetailTabs,
} from "../components/CollectionUI";
import { LineagePanel } from "../lineage/LineagePanel";
import { listSowings, type SowingResponse } from "../sowings/api";
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
}
type SaveState =
  | { status: "idle" }
  | { status: "saving" }
  | { status: "success"; message: string }
  | { status: "error"; messages: string[] };
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
  locationId: string;
  materialProvenancePlaceId: string;
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
    locationId: "",
    materialProvenancePlaceId: "",
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
    locationId: lot.location_id ?? "",
    materialProvenancePlaceId: lot.material_provenance_place_id ?? "",
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
    location_id: form.locationId || null,
    material_provenance_place_id: form.materialProvenancePlaceId || null,
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
  const dialog = useRef<HTMLDivElement>(null);
  useEffect(() => {
    dialog.current
      ?.querySelector<HTMLElement>("input, select, button")
      ?.focus();
  }, []);
  return (
    <div
      className="dialog-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className="context-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="context-dialog-title"
        ref={dialog}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            onClose();
            return;
          }
          if (event.key !== "Tab" || !dialog.current) return;
          const focusable = Array.from(
            dialog.current.querySelectorAll<HTMLElement>(
              "button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])",
            ),
          );
          const first = focusable.at(0);
          const last = focusable.at(-1);
          if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last?.focus();
          } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first?.focus();
          }
        }}
      >
        <h3 id="context-dialog-title">{title}</h3>
        {children}
      </div>
    </div>
  );
}

function RelatedSowings({ seedLotId }: { seedLotId: string }) {
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
      <div className="empty-state">
        <p>No Sowings use this SeedLot.</p>
      </div>
    );
  return (
    <div className="card-grid">
      {sowings.map((sowing) => (
        <CollectionCard
          key={sowing.id}
          eyebrow={sowing.lifecycle}
          href={`#/sowings/${sowing.id}`}
          title={sowing.label ?? "Unlabelled Sowing"}
        >
          <p>{dateLabel(sowing.sowing_date)}</p>
          <p>{sowing.location?.display_path ?? "Location not recorded"}</p>
        </CollectionCard>
      ))}
    </div>
  );
}

function Detail({
  lot,
  onEdit,
  initialTab,
}: {
  lot: SeedLotResponse;
  onEdit: () => void;
  initialTab?: string;
}) {
  const [tab, setTab] = useState(
    initialTab && ["overview", "sowings", "lineage"].includes(initialTab)
      ? initialTab
      : "overview",
  );
  return (
    <section className="seed-detail" aria-labelledby="seed-detail-title">
      <Breadcrumbs
        items={[
          { label: "Seeds", href: "#/seeds" },
          { label: lot.label ?? lot.botanical_identity.display_label },
        ]}
      />
      <DetailHeader
        eyebrow="Seed lot"
        title={lot.label ?? lot.botanical_identity.display_label}
        secondary={
          <a href={`#/identities/${lot.botanical_identity.id}`}>
            {lot.botanical_identity.display_label}
          </a>
        }
        status={
          <>
            <span
              className={`lifecycle-badge lifecycle-badge--${lot.lifecycle}`}
            >
              {lifecycleLabels[lot.lifecycle]}
            </span>
            {lot.location && <span>{lot.location.display_path}</span>}
          </>
        }
        editLabel="Edit seed lot"
        onEdit={onEdit}
      />
      <DetailTabs
        tabs={[
          { id: "overview", label: "Overview" },
          { id: "sowings", label: "Sowings" },
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
        <div className="detail-tab-panel overview-grid">
          <p className="eyebrow">Selected seed lot</p>
          <h3 id="seed-detail-title">{lot.botanical_identity.display_label}</h3>
          {lot.label && <p className="seed-label">{lot.label}</p>}
          <dl>
            <div>
              <dt>Lifecycle</dt>
              <dd>{lifecycleLabels[lot.lifecycle]}</dd>
            </div>
            <div>
              <dt>Quantity</dt>
              <dd>{quantityLabel(lot)}</dd>
            </div>
            <div>
              <dt>Source</dt>
              <dd>
                {sourceLabels[lot.source_kind]}
                {lot.source_detail ? ` — ${lot.source_detail}` : ""}
              </dd>
            </div>
            <div>
              <dt>Supplier</dt>
              <dd>{lot.supplier?.name ?? "Not recorded"}</dd>
            </div>
            <div>
              <dt>Storage</dt>
              <dd>{lot.location?.display_path ?? "Not recorded"}</dd>
            </div>
            <div>
              <dt>Material provenance</dt>
              <dd>{lot.material_provenance?.display_path ?? "Not recorded"}</dd>
            </div>
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
            <div>
              <dt>Notes</dt>
              <dd className="preserve-lines">{lot.notes ?? "Not recorded"}</dd>
            </div>
          </dl>
        </div>
      )}
      {tab === "sowings" && (
        <div
          className="detail-tab-panel"
          role="tabpanel"
          aria-labelledby="tab-sowings"
        >
          <RelatedSowings seedLotId={lot.id} />
        </div>
      )}
      {tab === "lineage" && (
        <div
          className="detail-tab-panel"
          role="tabpanel"
          aria-labelledby="tab-lineage"
        >
          <LineagePanel kind="seed-lots" id={lot.id} />
        </div>
      )}
    </section>
  );
}

export function SeedLotScreen({
  initialId,
  initialTab,
}: {
  initialId?: string;
  initialTab?: string;
} = {}) {
  const auth = useAuth();
  const [inventory, setInventory] = useState<InventoryState>({
    status: "loading",
  });
  const [references, setReferences] = useState<References | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [filter, setFilter] = useState<"active" | "history" | "all">("active");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(
    initialId ?? null,
  );
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<FormState>(blankForm);
  const [moreDetails, setMoreDetails] = useState(false);
  const [save, setSave] = useState<SaveState>({ status: "idle" });
  const [context, setContext] = useState<{
    kind: ContextKind;
    query: string;
  } | null>(null);
  const [contextError, setContextError] = useState<string | null>(null);
  const [contextSaving, setContextSaving] = useState(false);
  const feedback = useRef<HTMLDivElement>(null);
  const contextTrigger = useRef<HTMLElement | null>(null);
  const {
    expanded: creationExpanded,
    triggerRef: creationTriggerRef,
    panelRef: creationPanelRef,
    open: openCreation,
    close: closeCreation,
    focusFirst: focusCreation,
  } = useCreationDisclosure();

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      listSeedLots(controller.signal),
      listBotanicalIdentities(controller.signal),
      listSuppliers(controller.signal),
      listLocations(controller.signal),
      listGeographicPlaces(controller.signal),
    ])
      .then(([lots, identities, suppliers, locations, places]) => {
        setInventory({ status: "ready", lots });
        setReferences({ identities, suppliers, locations, places });
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

  if (!references && inventory.status === "loading") {
    return (
      <section className="workspace" aria-labelledby="seeds-title">
        <h2 id="seeds-title">Seeds</h2>
        <p role="status">Loading seed inventory…</p>
      </section>
    );
  }
  if (inventory.status === "error" || !references) {
    return (
      <section className="workspace" aria-labelledby="seeds-title">
        <h2 id="seeds-title">Seeds</h2>
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
    setSelectedId(null);
    setEditing(true);
    setForm(blankForm());
    setMoreDetails(false);
    setSave({ status: "idle" });
    openCreation();
  }
  function startEdit(lot: SeedLotResponse) {
    if (creationExpanded) closeCreation({ returnFocus: false });
    setSelectedId(lot.id);
    setEditing(true);
    setForm(formFrom(lot));
    setMoreDetails(true);
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
    const wasCreating = !selected;
    setSave({ status: "saving" });
    try {
      const payload = payloadFrom(form);
      const lot = selected
        ? await updateSeedLot(selected.id, payload, csrfToken)
        : await createSeedLot(payload, csrfToken);
      await refreshLots(lot);
      setEditing(false);
      if (wasCreating) closeCreation();
      setSave({
        status: "success",
        message: selected
          ? "Seed lot changes were saved."
          : "Seed lot was added to the collection.",
      });
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else if (error instanceof ApiError && error.status === 422)
        setSave({
          status: "error",
          messages: seedLotValidationMessages(error),
        });
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
          { name: value("name"), parent_id: value("parent_id") },
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

  return (
    <section
      className="workspace seeds-workspace"
      aria-labelledby="seeds-title"
    >
      <div className="workspace-intro seed-heading">
        <div>
          <p className="eyebrow">Collection inventory</p>
          <h2 id="seeds-title">Seeds</h2>
          <p>
            See what is available, record newly obtained material, and retain
            exhausted, discarded, or lost lots.
          </p>
        </div>
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
      </div>
      <div className="seed-master-detail">
        <section className="seed-master" aria-labelledby="seed-inventory-title">
          <h3 id="seed-inventory-title">Seed lot inventory</h3>
          <div className="seed-controls">
            <div className="field">
              <label htmlFor="seed-search">Search seed inventory</label>
              <input
                id="seed-search"
                type="search"
                value={search}
                onChange={(event) => {
                  setSearch(event.currentTarget.value);
                }}
              />
            </div>
            <fieldset className="lifecycle-filter">
              <legend>Show lots</legend>
              {(["active", "history", "all"] as const).map((item) => (
                <button
                  type="button"
                  aria-pressed={filter === item}
                  key={item}
                  onClick={() => {
                    setFilter(item);
                  }}
                >
                  {item === "active"
                    ? "Active"
                    : item === "history"
                      ? "History"
                      : "All"}
                </button>
              ))}
            </fieldset>
          </div>
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
                Try another search or lifecycle view. Historical records remain
                available under History or All.
              </p>
            </div>
          ) : (
            <ul className="seed-list" aria-label="Seed inventory">
              {visible.map((lot) => (
                <li key={lot.id}>
                  <button
                    type="button"
                    className="seed-row"
                    aria-pressed={selectedId === lot.id}
                    onClick={() => {
                      if (creationExpanded)
                        closeCreation({ returnFocus: false });
                      setSelectedId(lot.id);
                      setEditing(false);
                      setSave({ status: "idle" });
                    }}
                  >
                    <span className="seed-primary">
                      <strong>{lot.botanical_identity.display_label}</strong>
                      {lot.label && <small>{lot.label}</small>}
                    </span>
                    <span>{quantityLabel(lot)}</span>
                    <span>
                      {lot.location?.display_path ?? "Location unknown"}
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
          {editing ? (
            <form
              className="seed-form"
              onSubmit={(event) => void submit(event)}
              noValidate
            >
              <div className="seed-form-heading">
                <div>
                  <p className="eyebrow">
                    {selected ? "Correct seed lot" : "Fast entry"}
                  </p>
                  <h3>
                    {selected
                      ? `Edit ${selected.botanical_identity.display_label}`
                      : "Add seed lot"}
                  </h3>
                </div>
                <button
                  type="button"
                  className="button--secondary"
                  onClick={() => {
                    setEditing(false);
                    if (!selected) {
                      setForm(blankForm());
                      setMoreDetails(false);
                      setSave({ status: "idle" });
                      closeCreation();
                    }
                  }}
                >
                  Cancel
                </button>
              </div>
              <ReferencePicker
                label="Botanical identity"
                required
                disabled={pending}
                choices={references.identities.map((item) => ({
                  id: item.id,
                  label: item.display_label,
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
              <div className="seed-primary-fields">
                <div className="field">
                  <label htmlFor="lot-label">
                    Lot label <span className="optional">(optional)</span>
                  </label>
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
                <fieldset className="quantity-field">
                  <legend>
                    Quantity <span className="optional">(optional)</span>
                  </legend>
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
                  <small>Leave empty when quantity is unknown.</small>
                </fieldset>
                <div className="field">
                  <label htmlFor="source-kind">Source</label>
                  <select
                    id="source-kind"
                    value={form.sourceKind}
                    disabled={pending}
                    onChange={(event) => {
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
                    <label htmlFor="source-detail">
                      Source detail <span className="optional">(optional)</span>
                    </label>
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
                <ReferencePicker
                  label="Supplier (optional)"
                  disabled={pending}
                  choices={references.suppliers.map((item) => ({
                    id: item.id,
                    label: item.name,
                    retired: Boolean(item.retired_at),
                  }))}
                  value={form.supplierId}
                  onChange={(id) => {
                    setForm((current) => ({ ...current, supplierId: id }));
                  }}
                  onCreate={(query) => {
                    openContext("supplier", query);
                  }}
                  createLabel="Create supplier"
                />
                <ReferencePicker
                  label="Storage location (optional)"
                  disabled={pending}
                  choices={references.locations.map((item) => ({
                    id: item.id,
                    label: item.display_path,
                    retired: Boolean(item.retired_at),
                  }))}
                  value={form.locationId}
                  onChange={(id) => {
                    setForm((current) => ({ ...current, locationId: id }));
                  }}
                  onCreate={(query) => {
                    openContext("location", query);
                  }}
                  createLabel="Create location"
                />
              </div>
              <button
                type="button"
                className="button--secondary disclosure-button"
                aria-expanded={moreDetails}
                onClick={() => {
                  setMoreDetails((value) => !value);
                }}
              >
                {moreDetails ? "Fewer details" : "More details"}
              </button>
              {moreDetails && (
                <div className="advanced-fields">
                  <ReferencePicker
                    label="Material provenance (optional)"
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
                  <div className="partial-date-grid">
                    <PartialDateField
                      id="acquisition"
                      label="Acquisition date"
                      value={form.acquisitionDate}
                      onChange={(value) => {
                        setForm((current) => ({
                          ...current,
                          acquisitionDate: value,
                        }));
                      }}
                      disabled={pending}
                    />
                    <PartialDateField
                      id="harvest"
                      label="Harvest date"
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
                    <label htmlFor="lifecycle">Lifecycle</label>
                    <select
                      id="lifecycle"
                      value={form.lifecycle}
                      disabled={pending}
                      onChange={(event) => {
                        const value = event.currentTarget
                          .value as SeedLotLifecycle;
                        setForm((current) => ({
                          ...current,
                          lifecycle: value,
                        }));
                      }}
                    >
                      {Object.entries(lifecycleLabels).map(([value, label]) => (
                        <option value={value} key={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                    <small>
                      Use Exhausted for an exact known zero quantity. Historical
                      lots remain editable.
                    </small>
                  </div>
                  <div className="field">
                    <label htmlFor="seed-notes">
                      Notes <span className="optional">(optional)</span>
                    </label>
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
                </div>
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
              <button type="submit" disabled={pending}>
                {pending
                  ? "Saving…"
                  : selected
                    ? "Save changes"
                    : "Add to collection"}
              </button>
            </form>
          ) : selected ? (
            <div className="selected-seed">
              <Detail
                lot={selected}
                initialTab={initialTab}
                onEdit={() => {
                  startEdit(selected);
                }}
              />
            </div>
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
                  <label htmlFor="context-scientific-name">
                    Scientific name
                  </label>
                  <input
                    id="context-scientific-name"
                    name="scientific_name"
                    required
                    defaultValue={context.query}
                  />
                </div>
                <div className="field">
                  <label htmlFor="context-cultivar">
                    Cultivar <span className="optional">(optional)</span>
                  </label>
                  <input id="context-cultivar" name="cultivar_name" />
                </div>
                <div className="field">
                  <label htmlFor="context-common">
                    Common name <span className="optional">(optional)</span>
                  </label>
                  <input id="context-common" name="common_name" />
                </div>
              </>
            ) : context.kind === "supplier" ? (
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
                  label={
                    context.kind === "location" ? "Parent (optional)" : "Parent"
                  }
                  required={context.kind === "place"}
                  choices={
                    context.kind === "location"
                      ? references.locations.map((item) => ({
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
