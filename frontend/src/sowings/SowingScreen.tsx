import { CreationReversal } from "../propagation/CreationReversal";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
  type SyntheticEvent,
} from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { useCreationDisclosure } from "../components/useCreationDisclosure";
import {
  Breadcrumbs,
  DetailHeader,
  DetailTabs,
} from "../components/CollectionUI";
import { listLocations, type LocationResponse } from "../locations/api";
import { PartialDateField } from "../seed-lots/PartialDateField";
import { listSeedLots, type SeedLotResponse } from "../seed-lots/api";
import { PropagationPath } from "../propagation/PropagationPath";
import {
  createSowing,
  getSowing,
  getSowingPropagationSummary,
  listSowings,
  sowingValidationMessages,
  updateSowing,
  type PartialDate,
  type SowingCreate,
  type SowingLifecycle,
  type SowingResponse,
  type SowingPropagationSummary,
} from "./api";

type CollectionState =
  | { status: "loading" }
  | { status: "ready"; sowings: SowingResponse[] }
  | { status: "error" };
type DetailState =
  | { status: "idle" }
  | { status: "loading"; id: string }
  | { status: "ready"; sowing: SowingResponse }
  | { status: "error"; id: string };
type SaveState =
  | { status: "idle" }
  | { status: "saving" }
  | { status: "success"; message: string }
  | { status: "error"; messages: string[] };
type QuantityKind = "unknown" | "seed_count" | "weight";

interface References {
  seedLots: SeedLotResponse[];
  locations: LocationResponse[];
}

interface FormState {
  seedLotId: string;
  label: string;
  sowingDate: PartialDate | null;
  quantityKind: QuantityKind;
  quantityValue: string;
  quantityUnit: "g" | "mg";
  quantityApproximate: boolean;
  germinatedCount: string;
  locationId: string;
  substrate: string;
  methodContainer: string;
  pretreatment: string;
  temperatureMinC: string;
  temperatureMaxC: string;
  environment: string;
  lifecycle: SowingLifecycle;
  notes: string;
}

const lifecycleLabels: Record<SowingLifecycle, string> = {
  active: "Active",
  reversed: "Reversed",
  completed: "Completed",
  failed: "Failed",
  abandoned: "Abandoned",
};

function blankForm(): FormState {
  return {
    seedLotId: "",
    label: "",
    sowingDate: null,
    quantityKind: "unknown",
    quantityValue: "",
    quantityUnit: "g",
    quantityApproximate: false,
    germinatedCount: "",
    locationId: "",
    substrate: "",
    methodContainer: "",
    pretreatment: "",
    temperatureMinC: "",
    temperatureMaxC: "",
    environment: "",
    lifecycle: "active",
    notes: "",
  };
}

function formFrom(sowing: SowingResponse): FormState {
  return {
    seedLotId: sowing.seed_lot_id,
    label: sowing.label ?? "",
    sowingDate: sowing.sowing_date,
    quantityKind: sowing.quantity?.kind ?? "unknown",
    quantityValue: sowing.quantity?.value ?? "",
    quantityUnit:
      sowing.quantity?.kind === "weight" ? (sowing.quantity.unit ?? "g") : "g",
    quantityApproximate: sowing.quantity?.is_approximate ?? false,
    germinatedCount:
      sowing.germinated_count === null ? "" : String(sowing.germinated_count),
    locationId: sowing.location_id ?? "",
    substrate: sowing.substrate ?? "",
    methodContainer: sowing.method_container ?? "",
    pretreatment: sowing.pretreatment ?? "",
    temperatureMinC: sowing.temperature_min_c ?? "",
    temperatureMaxC: sowing.temperature_max_c ?? "",
    environment: sowing.environment ?? "",
    lifecycle: sowing.lifecycle,
    notes: sowing.notes ?? "",
  };
}

function payloadFrom(form: FormState): SowingCreate {
  return {
    seed_lot_id: form.seedLotId,
    label: form.label || null,
    sowing_date: form.sowingDate,
    quantity:
      form.quantityKind === "unknown"
        ? null
        : {
            kind: form.quantityKind,
            value: form.quantityValue,
            unit: form.quantityKind === "weight" ? form.quantityUnit : null,
            is_approximate: form.quantityApproximate,
          },
    germinated_count:
      form.germinatedCount === "" ? null : Number(form.germinatedCount),
    location_id: form.locationId || null,
    substrate: form.substrate || null,
    method_container: form.methodContainer || null,
    pretreatment: form.pretreatment || null,
    temperature_min_c: form.temperatureMinC || null,
    temperature_max_c: form.temperatureMaxC || null,
    environment: form.environment || null,
    lifecycle: form.lifecycle,
    notes: form.notes || null,
  };
}

function dateLabel(date: PartialDate | null): string {
  if (!date) return "Not recorded";
  const year = String(date.year).padStart(4, "0");
  if (date.precision === "year") return year;
  const month = String(date.month).padStart(2, "0");
  if (date.precision === "month") return `${year}-${month}`;
  return `${year}-${month}-${String(date.day).padStart(2, "0")}`;
}

function quantityLabel(sowing: SowingResponse): string {
  const quantity = sowing.quantity;
  const germinated = sowing.germinated_count;
  if (!quantity)
    return germinated === null
      ? "Quantity not recorded"
      : `${String(germinated)} germinated`;
  const prefix = quantity.is_approximate ? "~" : "";
  if (quantity.kind === "seed_count") {
    const sown = `${prefix}${quantity.value} sown`;
    return germinated === null
      ? sown
      : `${String(germinated)} germinated / ${sown}`;
  }
  const sown = `${prefix}${quantity.value} ${quantity.unit ?? "g"} sown`;
  return germinated === null
    ? sown
    : `${String(germinated)} germinated · ${sown}`;
}

function seedLotLabel(lot: SeedLotResponse): string {
  const detail = lot.label ? ` · ${lot.label}` : "";
  const lifecycle = lot.lifecycle === "active" ? "" : ` · ${lot.lifecycle}`;
  return `${lot.botanical_identity.display_label}${detail}${lifecycle}`;
}

function Detail({
  sowing,
  headingRef,
  onEdit,
  initialTab,
}: {
  sowing: SowingResponse;
  headingRef: RefObject<HTMLHeadingElement | null>;
  onEdit: () => void;
  initialTab?: string;
}) {
  const [summary, setSummary] = useState<
    | { status: "loading" }
    | { status: "ready"; value: SowingPropagationSummary }
    | { status: "error" }
  >({ status: "loading" });
  useEffect(() => {
    const controller = new AbortController();
    void getSowingPropagationSummary(sowing.id, controller.signal)
      .then((value) => {
        if (!Array.isArray(value.plants) || !Array.isArray(value.plant_groups))
          throw new Error("Invalid propagation summary");
        setSummary({ status: "ready", value });
      })
      .catch(() => {
        if (!controller.signal.aborted) setSummary({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [sowing.id]);
  const [tab, setTab] = useState(
    initialTab === "lineage" ? "lineage" : "overview",
  );
  const hasCultivation = Boolean(
    sowing.substrate ??
    sowing.method_container ??
    sowing.pretreatment ??
    sowing.temperature_min_c ??
    sowing.temperature_max_c ??
    sowing.environment,
  );
  const temperature =
    sowing.temperature_min_c && sowing.temperature_max_c
      ? `${sowing.temperature_min_c}–${sowing.temperature_max_c} °C`
      : sowing.temperature_min_c
        ? `Minimum ${sowing.temperature_min_c} °C`
        : sowing.temperature_max_c
          ? `Maximum ${sowing.temperature_max_c} °C`
          : null;
  return (
    <article className="sowing-detail">
      <Breadcrumbs
        items={[
          { label: "Sowings", href: "#/sowings" },
          {
            label:
              sowing.label ?? sowing.seed_lot.botanical_identity_display_label,
          },
        ]}
      />
      <DetailHeader
        eyebrow="Sowing"
        title={sowing.label ?? sowing.seed_lot.botanical_identity_display_label}
        secondary={
          <>
            <a href={`#/identities/${sowing.seed_lot.botanical_identity_id}`}>
              {sowing.seed_lot.botanical_identity_display_label}
            </a>{" "}
            ·{" "}
            <a href={`#/seeds/${sowing.seed_lot.id}`}>
              {sowing.seed_lot.label ?? "Unlabelled SeedLot"}
            </a>
          </>
        }
        status={
          <>
            <span
              className={`lifecycle-badge lifecycle-badge--${sowing.lifecycle}`}
            >
              {lifecycleLabels[sowing.lifecycle]}
            </span>
            {sowing.location && <span>{sowing.location.display_path}</span>}
          </>
        }
        editLabel="Edit Sowing"
        onEdit={onEdit}
      />
      {sowing.lifecycle !== "reversed" && (
        <div className="actions contextual-actions">
          <a
            className="button-link"
            href={`#/plants?action=from-sowing&sowing=${sowing.id}&kind=plant`}
          >
            Create Plant
          </a>
          <a
            className="button-link button--secondary"
            href={`#/plants?action=from-sowing&sowing=${sowing.id}&kind=group`}
          >
            Create PlantGroup
          </a>
        </div>
      )}
      <DetailTabs
        tabs={[
          { id: "overview", label: "Overview" },
          { id: "lineage", label: "Propagation" },
        ]}
        selected={tab}
        onSelect={(next) => {
          setTab(next);
          window.history.replaceState(
            null,
            "",
            `#/sowings/${sowing.id}?tab=${next}`,
          );
        }}
      />
      {tab === "overview" && (
        <div className="detail-tab-panel overview-grid">
          <section aria-labelledby="sowing-origin-title">
            <p className="eyebrow">Source</p>
            <h3 id="sowing-origin-title" tabIndex={-1} ref={headingRef}>
              {sowing.seed_lot.botanical_identity_display_label}
            </h3>
            {sowing.label && <p className="seed-label">{sowing.label}</p>}
            <dl>
              <div>
                <dt>Lifecycle</dt>
                <dd>{lifecycleLabels[sowing.lifecycle]}</dd>
              </div>
              <div>
                <dt>Seed lot</dt>
                <dd>
                  <a href={`#/seeds/${sowing.seed_lot.id}`}>
                    {sowing.seed_lot.label ?? "Unlabelled lot"}
                  </a>{" "}
                  · {sowing.seed_lot.lifecycle}
                </dd>
              </div>
            </dl>
          </section>
          <section className="field--full" aria-labelledby="descendants-title">
            <h4 id="descendants-title">Tracked descendants</h4>
            {summary.status === "loading" && (
              <p role="status">Loading propagation summary…</p>
            )}
            {summary.status === "error" && (
              <p className="notice notice--error">
                Florabase could not load the propagation summary.
              </p>
            )}
            {summary.status === "ready" && (
              <>
                <p className="descendant-total">
                  <strong>
                    {summary.value.exact_descendant_count} exact{" "}
                    {summary.value.exact_descendant_count === 1
                      ? "individual"
                      : "individuals"}
                  </strong>
                </p>
                {summary.value.approximate_plant_group_count > 0 && (
                  <p>
                    + {summary.value.approximate_plant_group_count} approximate
                    Plant{" "}
                    {summary.value.approximate_plant_group_count === 1
                      ? "group"
                      : "groups"}
                  </p>
                )}
                {summary.value.unknown_plant_group_count > 0 && (
                  <p>
                    + {summary.value.unknown_plant_group_count} Plant{" "}
                    {summary.value.unknown_plant_group_count === 1
                      ? "group"
                      : "groups"}{" "}
                    with unknown quantity
                  </p>
                )}
                {summary.value.plants.length +
                  summary.value.plant_groups.length ===
                  0 && (
                  <p>No directly originating Plants or Plant groups yet.</p>
                )}
                <PropagationPath
                  title="Propagation path"
                  stages={[
                    [
                      {
                        type: "Source SeedLot",
                        label: sowing.seed_lot.label ?? "Unlabelled SeedLot",
                        href: `#/seeds/${sowing.seed_lot.id}`,
                        state: sowing.seed_lot.lifecycle,
                      },
                    ],
                    [
                      {
                        type: "Current Sowing",
                        label: sowing.label ?? "Unlabelled Sowing",
                        href: `#/sowings/${sowing.id}`,
                        state: sowing.lifecycle,
                      },
                    ],
                    [
                      ...summary.value.plants.map((plant) => ({
                        type: "Plant",
                        label: plant.label ?? "Unlabelled Plant",
                        href: `#/plants/${plant.id}`,
                        state: plant.lifecycle,
                      })),
                      ...summary.value.plant_groups.map((group) => ({
                        type: "Plant group",
                        label: group.label ?? "Unlabelled Plant group",
                        href: `#/plant-groups/${group.id}`,
                        state: group.quantity
                          ? `${group.quantity.is_approximate ? "~" : ""}${String(group.quantity.value)} · ${group.lifecycle}`
                          : `quantity unknown · ${group.lifecycle}`,
                      })),
                    ],
                  ]}
                />
              </>
            )}
          </section>
          <section aria-labelledby="sowing-facts-title">
            <h4 id="sowing-facts-title">Sowing</h4>
            <dl>
              <div>
                <dt>Sowing date</dt>
                <dd>{dateLabel(sowing.sowing_date)}</dd>
              </div>
              <div>
                <dt>Result</dt>
                <dd>{quantityLabel(sowing)}</dd>
              </div>
              <div>
                <dt>Current location</dt>
                <dd>{sowing.location?.display_path ?? "Not recorded"}</dd>
              </div>
            </dl>
          </section>
          {hasCultivation && (
            <section aria-labelledby="sowing-cultivation-title">
              <h4 id="sowing-cultivation-title">Cultivation</h4>
              <dl>
                {sowing.substrate && (
                  <div>
                    <dt>Substrate</dt>
                    <dd>{sowing.substrate}</dd>
                  </div>
                )}
                {sowing.method_container && (
                  <div>
                    <dt>Method / container</dt>
                    <dd>{sowing.method_container}</dd>
                  </div>
                )}
                {sowing.pretreatment && (
                  <div>
                    <dt>Pretreatment</dt>
                    <dd>{sowing.pretreatment}</dd>
                  </div>
                )}
                {temperature && (
                  <div>
                    <dt>Temperature</dt>
                    <dd>{temperature}</dd>
                  </div>
                )}
                {sowing.environment && (
                  <div>
                    <dt>Environment</dt>
                    <dd>{sowing.environment}</dd>
                  </div>
                )}
              </dl>
            </section>
          )}
          {sowing.notes && (
            <section aria-labelledby="sowing-notes-title">
              <h4 id="sowing-notes-title">Notes</h4>
              <p className="preserve-lines">{sowing.notes}</p>
            </section>
          )}
        </div>
      )}
      {tab === "lineage" && (
        <div
          className="detail-tab-panel"
          role="tabpanel"
          aria-labelledby="tab-lineage"
        >
          {summary.status === "loading" && (
            <p role="status">Loading propagation summary…</p>
          )}
          {summary.status === "error" && (
            <p className="notice notice--error">
              Florabase could not load the propagation summary.
            </p>
          )}
          {summary.status === "ready" && (
            <PropagationPath
              title="Recorded propagation"
              stages={[
                [
                  {
                    type: "Source SeedLot",
                    label: sowing.seed_lot.label ?? "Unlabelled SeedLot",
                    href: `#/seeds/${sowing.seed_lot.id}`,
                    state: sowing.seed_lot.lifecycle,
                  },
                ],
                [
                  {
                    type: "Current Sowing",
                    label: sowing.label ?? "Unlabelled Sowing",
                    href: `#/sowings/${sowing.id}`,
                    state: sowing.lifecycle,
                  },
                ],
                [
                  ...summary.value.plants.map((plant) => ({
                    type: "Plant",
                    label: plant.label ?? "Unlabelled Plant",
                    href: `#/plants/${plant.id}`,
                    state: plant.lifecycle,
                  })),
                  ...summary.value.plant_groups.map((group) => ({
                    type: "Plant group",
                    label: group.label ?? "Unlabelled Plant group",
                    href: `#/plant-groups/${group.id}`,
                    state: group.quantity
                      ? `${group.quantity.is_approximate ? "~" : ""}${String(group.quantity.value)} · ${group.lifecycle}`
                      : `quantity unknown · ${group.lifecycle}`,
                  })),
                ],
              ]}
            />
          )}
        </div>
      )}
    </article>
  );
}

export function SowingScreen({
  initialId,
  initialTab,
}: {
  initialId?: string;
  initialTab?: string;
} = {}) {
  const auth = useAuth();
  const [collection, setCollection] = useState<CollectionState>({
    status: "loading",
  });
  const [references, setReferences] = useState<References | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [detailAttempt, setDetailAttempt] = useState(0);
  const [detail, setDetail] = useState<DetailState>({ status: "idle" });
  const [selectedId, setSelectedId] = useState<string | null>(
    initialId ?? null,
  );
  const [filter, setFilter] = useState<"active" | "completed" | "all">(
    "active",
  );
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState(false);
  const [mobileDetail, setMobileDetail] = useState(Boolean(initialId));
  const [form, setForm] = useState<FormState>(blankForm);
  const [moreDetails, setMoreDetails] = useState(false);
  const [save, setSave] = useState<SaveState>({ status: "idle" });
  const feedback = useRef<HTMLDivElement>(null);
  const detailHeading = useRef<HTMLHeadingElement>(null);
  const selectedTrigger = useRef<HTMLButtonElement | null>(null);
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
      listSowings(controller.signal),
      listSeedLots(controller.signal),
      listLocations(controller.signal),
    ])
      .then(([sowings, seedLots, locations]) => {
        setCollection({ status: "ready", sowings });
        setReferences({ seedLots, locations });
        setSelectedId((current) =>
          current && sowings.some(({ id }) => id === current) ? current : null,
        );
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else setCollection({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [auth, attempt]);

  useEffect(() => {
    if (!selectedId) return;
    const controller = new AbortController();
    void getSowing(selectedId, controller.signal)
      .then((sowing) => {
        setDetail({ status: "ready", sowing });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else setDetail({ status: "error", id: selectedId });
      });
    return () => {
      controller.abort();
    };
  }, [auth, detailAttempt, selectedId]);

  useEffect(() => {
    if (save.status === "error") feedback.current?.focus();
  }, [save]);

  useEffect(() => {
    if (mobileDetail && detail.status === "ready" && !editing)
      detailHeading.current?.focus();
  }, [detail, editing, mobileDetail]);

  const sowings = useMemo(
    () => (collection.status === "ready" ? collection.sowings : []),
    [collection],
  );
  const visible = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return sowings.filter((sowing) => {
      const lifecycleMatch =
        filter === "all" ||
        (filter === "active"
          ? sowing.lifecycle === "active"
          : sowing.lifecycle === "completed");
      const textMatch =
        !query ||
        [
          sowing.seed_lot.botanical_identity_display_label,
          sowing.label,
          sowing.location?.display_path,
          sowing.seed_lot.label,
        ].some((value) => value?.toLocaleLowerCase().includes(query));
      return lifecycleMatch && textMatch;
    });
  }, [filter, search, sowings]);

  if (!references && collection.status === "loading") {
    return (
      <section className="workspace" aria-labelledby="sowings-title">
        <h2 id="sowings-title">Sowings</h2>
        <p role="status">Loading Sowings…</p>
      </section>
    );
  }
  if (collection.status === "error" || !references) {
    return (
      <section className="workspace" aria-labelledby="sowings-title">
        <h2 id="sowings-title">Sowings</h2>
        <div className="notice notice--error" role="alert">
          <p>Florabase could not load the Sowing collection or its choices.</p>
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
  const selected =
    detail.status === "ready" && detail.sowing.id === selectedId
      ? detail.sowing
      : null;

  function startCreate() {
    setSelectedId(null);
    setDetail({ status: "idle" });
    setEditing(true);
    setMobileDetail(true);
    setForm(blankForm());
    setMoreDetails(false);
    setSave({ status: "idle" });
    openCreation();
  }

  function startEdit(sowing: SowingResponse) {
    if (creationExpanded) closeCreation({ returnFocus: false });
    setForm(formFrom(sowing));
    setMoreDetails(true);
    setEditing(true);
    setSave({ status: "idle" });
  }

  function selectSowing(id: string, trigger: HTMLButtonElement) {
    if (creationExpanded) closeCreation({ returnFocus: false });
    selectedTrigger.current = trigger;
    setDetail({ status: "loading", id });
    setSelectedId(id);
    setMobileDetail(true);
    setEditing(false);
    setSave({ status: "idle" });
  }

  function returnToList() {
    setMobileDetail(false);
    setEditing(false);
    window.setTimeout(() => selectedTrigger.current?.focus(), 0);
  }

  function updateForm<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function validate(): string[] {
    const errors: string[] = [];
    const quantity = Number(form.quantityValue);
    const germinated = Number(form.germinatedCount);
    if (!form.seedLotId) errors.push("Choose a SeedLot.");
    if (form.quantityKind !== "unknown") {
      if (!form.quantityValue || !Number.isFinite(quantity) || quantity <= 0)
        errors.push("Quantity sown must be greater than zero.");
      else if (
        form.quantityKind === "seed_count" &&
        !Number.isInteger(quantity)
      )
        errors.push("Seed count must be a whole number.");
    }
    if (
      form.germinatedCount !== "" &&
      (!Number.isInteger(germinated) || germinated < 0)
    )
      errors.push("Germinated count must be zero or a positive whole number.");
    if (
      form.germinatedCount !== "" &&
      form.quantityKind === "seed_count" &&
      !form.quantityApproximate &&
      Number.isFinite(quantity) &&
      germinated > quantity
    )
      errors.push("Germinated count cannot exceed an exact seed count.");
    const minimum = Number(form.temperatureMinC);
    const maximum = Number(form.temperatureMaxC);
    if (form.temperatureMinC !== "" && !Number.isFinite(minimum))
      errors.push("Enter a valid minimum temperature.");
    if (form.temperatureMaxC !== "" && !Number.isFinite(maximum))
      errors.push("Enter a valid maximum temperature.");
    if (
      form.temperatureMinC !== "" &&
      form.temperatureMaxC !== "" &&
      Number.isFinite(minimum) &&
      Number.isFinite(maximum) &&
      minimum > maximum
    )
      errors.push(
        "Minimum temperature cannot be greater than maximum temperature.",
      );
    return errors;
  }

  async function submit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (pending) return;
    const errors = validate();
    if (errors.length) {
      setSave({ status: "error", messages: errors });
      return;
    }
    const wasCreating = !selected;
    setSave({ status: "saving" });
    try {
      const payload = payloadFrom(form);
      const authoritative = selected
        ? await updateSowing(selected.id, payload, csrfToken)
        : await createSowing(payload, csrfToken);
      setCollection((current) => {
        if (current.status !== "ready") return current;
        const exists = current.sowings.some(
          ({ id }) => id === authoritative.id,
        );
        return {
          status: "ready",
          sowings: exists
            ? current.sowings.map((item) =>
                item.id === authoritative.id ? authoritative : item,
              )
            : [...current.sowings, authoritative],
        };
      });
      const refreshed = await listSowings();
      setCollection({ status: "ready", sowings: refreshed });
      setSelectedId(authoritative.id);
      setDetail({ status: "ready", sowing: authoritative });
      setEditing(false);
      if (wasCreating) closeCreation();
      setSave({
        status: "success",
        message: wasCreating
          ? "Sowing was recorded."
          : "Sowing changes were saved.",
      });
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else if (error instanceof ApiError && error.status === 422)
        setSave({ status: "error", messages: sowingValidationMessages(error) });
      else if (error instanceof ApiError && error.status === 403)
        setSave({
          status: "error",
          messages: [
            "Florabase could not authorize this change. Refresh and try again.",
          ],
        });
      else
        setSave({
          status: "error",
          messages: [
            "Florabase could not save or refresh this Sowing. Check the connection and try again.",
          ],
        });
    }
  }

  const activeSeedLots = references.seedLots.filter(
    (lot) => lot.lifecycle === "active",
  );
  const inactiveSeedLots = references.seedLots.filter(
    (lot) => lot.lifecycle !== "active",
  );

  return (
    <section
      className="workspace sowings-workspace"
      aria-labelledby="sowings-title"
    >
      <div className="workspace-intro seed-heading">
        <div>
          <p className="eyebrow">Propagation records</p>
          <h2 id="sowings-title">Sowings</h2>
          <p>
            Record a simple attempt quickly, then retain cultivation details and
            outcomes.
          </p>
        </div>
        <button
          type="button"
          ref={creationTriggerRef}
          aria-expanded={creationExpanded}
          aria-controls="new-sowing-panel"
          disabled={references.seedLots.length === 0}
          onClick={() => {
            if (creationExpanded) focusCreation();
            else startCreate();
          }}
        >
          + New Sowing
        </button>
      </div>
      {references.seedLots.length === 0 && (
        <div className="notice" role="status">
          <p>
            A SeedLot is required before you can record a Sowing. Add one from
            Seeds first.
          </p>
        </div>
      )}
      <div
        className={`sowing-master-detail${mobileDetail ? " is-detail-view" : ""}`}
      >
        <section
          className="seed-master sowing-master"
          aria-labelledby="sowing-list-title"
        >
          <h3 id="sowing-list-title">Sowing collection</h3>
          <div className="seed-controls">
            <div className="field">
              <label htmlFor="sowing-search">Search Sowings</label>
              <input
                id="sowing-search"
                type="search"
                value={search}
                onChange={(event) => {
                  setSearch(event.currentTarget.value);
                }}
              />
            </div>
            <fieldset className="lifecycle-filter">
              <legend>Show Sowings</legend>
              {(["active", "completed", "all"] as const).map((item) => (
                <button
                  key={item}
                  type="button"
                  aria-pressed={filter === item}
                  onClick={() => {
                    setFilter(item);
                  }}
                >
                  {item === "active"
                    ? "Active"
                    : item === "completed"
                      ? "Completed"
                      : "All"}
                </button>
              ))}
            </fieldset>
          </div>
          {sowings.length === 0 ? (
            <div className="profile-empty">
              <h4>No Sowings recorded yet</h4>
              <p>
                {references.seedLots.length
                  ? "Use + New Sowing to record the first attempt."
                  : "Create a SeedLot from Seeds first."}
              </p>
            </div>
          ) : visible.length === 0 ? (
            <p>No Sowings match this search and lifecycle view.</p>
          ) : (
            <ul className="seed-list" aria-label="Sowing collection">
              {visible.map((sowing) => (
                <li key={sowing.id}>
                  <button
                    type="button"
                    className="seed-row sowing-row"
                    aria-pressed={selectedId === sowing.id}
                    onClick={(event) => {
                      selectSowing(sowing.id, event.currentTarget);
                    }}
                  >
                    <span className="seed-primary">
                      <strong>
                        {sowing.seed_lot.botanical_identity_display_label}
                      </strong>
                      {sowing.label && <small>{sowing.label}</small>}
                    </span>
                    <span>{dateLabel(sowing.sowing_date)}</span>
                    <span>{quantityLabel(sowing)}</span>
                    <span>
                      {sowing.location?.display_path ?? "Location not recorded"}
                    </span>
                    <span
                      className={`lifecycle-badge lifecycle-badge--${sowing.lifecycle}`}
                    >
                      {lifecycleLabels[sowing.lifecycle]}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section
          id={creationExpanded ? "new-sowing-panel" : undefined}
          className={`seed-detail-pane sowing-detail-pane${creationExpanded ? " seed-creation-panel" : ""}`}
          ref={creationExpanded ? creationPanelRef : undefined}
          aria-label="Sowing detail and editor"
        >
          <button
            type="button"
            className="sowing-back button--secondary"
            onClick={returnToList}
          >
            ← Back to Sowings
          </button>
          {save.status === "success" && (
            <div className="notice notice--success" role="status">
              {save.message}
            </div>
          )}
          {editing ? (
            <form
              className="seed-form sowing-form"
              onSubmit={(event) => void submit(event)}
              noValidate
            >
              <div className="seed-form-heading">
                <div>
                  <p className="eyebrow">
                    {selected ? "Correct Sowing" : "Fast entry"}
                  </p>
                  <h3>{selected ? "Edit Sowing" : "Record Sowing"}</h3>
                </div>
                <button
                  type="button"
                  className="button--secondary"
                  onClick={() => {
                    setEditing(false);
                    setSave({ status: "idle" });
                    if (!selected) {
                      setMobileDetail(false);
                      closeCreation();
                    }
                  }}
                >
                  Cancel
                </button>
              </div>
              <div className="field">
                <label htmlFor="sowing-seed-lot">SeedLot</label>
                <select
                  id="sowing-seed-lot"
                  required
                  value={form.seedLotId}
                  disabled={pending}
                  onChange={(event) => {
                    updateForm("seedLotId", event.currentTarget.value);
                  }}
                >
                  <option value="">Choose a SeedLot</option>
                  {activeSeedLots.length > 0 && (
                    <optgroup label="Active SeedLots">
                      {activeSeedLots.map((lot) => (
                        <option key={lot.id} value={lot.id}>
                          {seedLotLabel(lot)}
                        </option>
                      ))}
                    </optgroup>
                  )}
                  {inactiveSeedLots.length > 0 && (
                    <optgroup label="Historical SeedLots">
                      {inactiveSeedLots.map((lot) => (
                        <option key={lot.id} value={lot.id}>
                          {seedLotLabel(lot)}
                        </option>
                      ))}
                    </optgroup>
                  )}
                </select>
                <small>
                  Historical SeedLots remain available for historical entry.
                </small>
              </div>
              <div className="sowing-fast-fields">
                <div className="field">
                  <label htmlFor="sowing-label">
                    Sowing label <span className="optional">(optional)</span>
                  </label>
                  <input
                    id="sowing-label"
                    value={form.label}
                    disabled={pending}
                    onChange={(event) => {
                      updateForm("label", event.currentTarget.value);
                    }}
                  />
                </div>
                <PartialDateField
                  id="sowing-date"
                  label="Sowing date (optional)"
                  value={form.sowingDate}
                  disabled={pending}
                  onChange={(value) => {
                    setForm((current) => ({ ...current, sowingDate: value }));
                  }}
                />
                <fieldset className="quantity-field">
                  <legend>
                    Quantity sown <span className="optional">(optional)</span>
                  </legend>
                  <div className="field">
                    <label htmlFor="sowing-quantity-kind">Kind</label>
                    <select
                      id="sowing-quantity-kind"
                      value={form.quantityKind}
                      disabled={pending}
                      onChange={(event) => {
                        const quantityKind = event.currentTarget
                          .value as QuantityKind;
                        setForm((current) => ({
                          ...current,
                          quantityKind,
                          quantityValue:
                            quantityKind === "unknown"
                              ? ""
                              : current.quantityValue,
                        }));
                      }}
                    >
                      <option value="unknown">Unknown</option>
                      <option value="seed_count">Seed count</option>
                      <option value="weight">Weight</option>
                    </select>
                  </div>
                  {form.quantityKind !== "unknown" && (
                    <div className="quantity-controls sowing-quantity-controls">
                      <div className="field">
                        <label htmlFor="sowing-quantity-value">Amount</label>
                        <input
                          id="sowing-quantity-value"
                          inputMode="decimal"
                          value={form.quantityValue}
                          disabled={pending}
                          onChange={(event) => {
                            updateForm(
                              "quantityValue",
                              event.currentTarget.value,
                            );
                          }}
                        />
                      </div>
                      {form.quantityKind === "weight" && (
                        <div className="field">
                          <label htmlFor="sowing-quantity-unit">Unit</label>
                          <select
                            id="sowing-quantity-unit"
                            value={form.quantityUnit}
                            disabled={pending}
                            onChange={(event) => {
                              updateForm(
                                "quantityUnit",
                                event.currentTarget.value as "g" | "mg",
                              );
                            }}
                          >
                            <option value="g">g</option>
                            <option value="mg">mg</option>
                          </select>
                        </div>
                      )}
                      <label className="checkbox-label">
                        <input
                          type="checkbox"
                          checked={form.quantityApproximate}
                          disabled={pending}
                          onChange={(event) => {
                            updateForm(
                              "quantityApproximate",
                              event.currentTarget.checked,
                            );
                          }}
                        />
                        Approximate
                      </label>
                    </div>
                  )}
                </fieldset>
              </div>
              <button
                type="button"
                className="button--secondary disclosure-button"
                aria-expanded={moreDetails}
                aria-controls="sowing-advanced-fields"
                onClick={() => {
                  setMoreDetails((value) => !value);
                }}
              >
                {moreDetails ? "Fewer details" : "More details"}
              </button>
              {moreDetails && (
                <div
                  id="sowing-advanced-fields"
                  className="advanced-fields sowing-advanced-fields"
                >
                  <div className="field">
                    <label htmlFor="germinated-count">
                      Germinated count{" "}
                      <span className="optional">(optional)</span>
                    </label>
                    <input
                      id="germinated-count"
                      inputMode="numeric"
                      value={form.germinatedCount}
                      disabled={pending}
                      onChange={(event) => {
                        updateForm(
                          "germinatedCount",
                          event.currentTarget.value,
                        );
                      }}
                    />
                    <small>
                      Use 0 when none germinated; leave empty when unknown.
                    </small>
                  </div>
                  <div className="field">
                    <label htmlFor="sowing-location">
                      Current location{" "}
                      <span className="optional">(optional)</span>
                    </label>
                    <select
                      id="sowing-location"
                      value={form.locationId}
                      disabled={pending}
                      onChange={(event) => {
                        updateForm("locationId", event.currentTarget.value);
                      }}
                    >
                      <option value="">Not recorded</option>
                      {references.locations.map((location) => (
                        <option
                          key={location.id}
                          value={location.id}
                          disabled={
                            Boolean(location.retired_at) &&
                            location.id !== form.locationId
                          }
                        >
                          {location.display_path}
                          {location.retired_at ? " (retired)" : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="sowing-substrate">
                      Substrate <span className="optional">(optional)</span>
                    </label>
                    <input
                      id="sowing-substrate"
                      value={form.substrate}
                      disabled={pending}
                      onChange={(event) => {
                        updateForm("substrate", event.currentTarget.value);
                      }}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="sowing-method">
                      Method / container{" "}
                      <span className="optional">(optional)</span>
                    </label>
                    <input
                      id="sowing-method"
                      value={form.methodContainer}
                      disabled={pending}
                      onChange={(event) => {
                        updateForm(
                          "methodContainer",
                          event.currentTarget.value,
                        );
                      }}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="sowing-pretreatment">
                      Pretreatment <span className="optional">(optional)</span>
                    </label>
                    <input
                      id="sowing-pretreatment"
                      value={form.pretreatment}
                      disabled={pending}
                      onChange={(event) => {
                        updateForm("pretreatment", event.currentTarget.value);
                      }}
                    />
                  </div>
                  <fieldset className="temperature-field">
                    <legend>
                      Temperature{" "}
                      <span className="optional">(optional, °C)</span>
                    </legend>
                    <div className="temperature-controls">
                      <div className="field">
                        <label htmlFor="temperature-min">Minimum °C</label>
                        <input
                          id="temperature-min"
                          inputMode="decimal"
                          value={form.temperatureMinC}
                          disabled={pending}
                          onChange={(event) => {
                            updateForm(
                              "temperatureMinC",
                              event.currentTarget.value,
                            );
                          }}
                        />
                      </div>
                      <div className="field">
                        <label htmlFor="temperature-max">Maximum °C</label>
                        <input
                          id="temperature-max"
                          inputMode="decimal"
                          value={form.temperatureMaxC}
                          disabled={pending}
                          onChange={(event) => {
                            updateForm(
                              "temperatureMaxC",
                              event.currentTarget.value,
                            );
                          }}
                        />
                      </div>
                    </div>
                  </fieldset>
                  <div className="field field--full">
                    <label htmlFor="sowing-environment">
                      Environment / conditions{" "}
                      <span className="optional">(optional)</span>
                    </label>
                    <textarea
                      id="sowing-environment"
                      value={form.environment}
                      disabled={pending}
                      onChange={(event) => {
                        updateForm("environment", event.currentTarget.value);
                      }}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="sowing-lifecycle">Lifecycle</label>
                    <select
                      id="sowing-lifecycle"
                      value={form.lifecycle}
                      disabled={pending}
                      onChange={(event) => {
                        updateForm(
                          "lifecycle",
                          event.currentTarget.value as SowingLifecycle,
                        );
                      }}
                    >
                      {(Object.keys(lifecycleLabels) as SowingLifecycle[])
                        .filter(
                          (value) =>
                            value !== "reversed" ||
                            selected?.lifecycle === "reversed",
                        )
                        .map((value) => (
                          <option key={value} value={value}>
                            {lifecycleLabels[value]}
                          </option>
                        ))}
                    </select>
                  </div>
                  {form.lifecycle === "completed" && (
                    <div
                      className="completion-outcome field--full"
                      aria-live="polite"
                    >
                      <h4>Final Sowing outcome</h4>
                      {form.quantityKind === "seed_count" &&
                      !form.quantityApproximate &&
                      form.quantityValue !== "" &&
                      form.germinatedCount !== "" &&
                      Number(form.germinatedCount) <=
                        Number(form.quantityValue) ? (
                        <dl>
                          <div>
                            <dt>Sown</dt>
                            <dd>{form.quantityValue}</dd>
                          </div>
                          <div>
                            <dt>Germinated</dt>
                            <dd>{form.germinatedCount}</dd>
                          </div>
                          <div>
                            <dt>Not germinated</dt>
                            <dd>
                              {String(
                                Number(form.quantityValue) -
                                  Number(form.germinatedCount),
                              )}
                            </dd>
                          </div>
                        </dl>
                      ) : (
                        <p>
                          The exact non-germinated remainder cannot be derived
                          from the available quantity precision. You may still
                          complete this Sowing.
                        </p>
                      )}
                      <p className="field-help">
                        Review the germinated count above before saving. No
                        separate remainder is persisted.
                      </p>
                    </div>
                  )}
                  <div className="field field--full">
                    <label htmlFor="sowing-notes">
                      Notes <span className="optional">(optional)</span>
                    </label>
                    <textarea
                      id="sowing-notes"
                      value={form.notes}
                      disabled={pending}
                      onChange={(event) => {
                        updateForm("notes", event.currentTarget.value);
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
              <div className="actions">
                <button type="submit" disabled={pending}>
                  {pending
                    ? "Saving…"
                    : selected
                      ? "Save changes"
                      : "Record Sowing"}
                </button>
              </div>
            </form>
          ) : detail.status === "loading" ? (
            <p role="status">Loading Sowing detail…</p>
          ) : detail.status === "error" ? (
            <div className="notice notice--error" role="alert">
              <p>Florabase could not load this Sowing.</p>
              <button
                type="button"
                onClick={() => {
                  if (selectedId)
                    setDetail({ status: "loading", id: selectedId });
                  setDetailAttempt((value) => value + 1);
                }}
              >
                Retry detail
              </button>
            </div>
          ) : selected ? (
            <div className="selected-seed selected-sowing">
              <CreationReversal
                key={`reversal:${selected.id}:${selected.updated_at}`}
                kind="sowing"
                id={selected.id}
                lifecycle={selected.lifecycle}
                revision={selected.updated_at}
                onReversed={(result) => {
                  if (!("seed_lot" in result)) return;
                  setDetail({ status: "ready", sowing: result.sowing });
                  setCollection((current) =>
                    current.status === "ready"
                      ? {
                          ...current,
                          sowings: current.sowings.map((value) =>
                            value.id === result.sowing.id
                              ? result.sowing
                              : value,
                          ),
                        }
                      : current,
                  );
                  setReferences((current) =>
                    current
                      ? {
                          ...current,
                          seedLots: current.seedLots.map((value) =>
                            value.id === result.seed_lot.id
                              ? result.seed_lot
                              : value,
                          ),
                        }
                      : current,
                  );
                }}
              />
              <Detail
                key={selected.updated_at}
                sowing={selected}
                headingRef={detailHeading}
                initialTab={initialTab}
                onEdit={() => {
                  startEdit(selected);
                }}
              />
            </div>
          ) : (
            <div className="selected-seed seed-detail-empty">
              <h3>Select a Sowing</h3>
              <p>Choose a compact row to see its full record.</p>
            </div>
          )}
        </section>
      </div>
    </section>
  );
}
