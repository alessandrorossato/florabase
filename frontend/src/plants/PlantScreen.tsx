import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
  type SyntheticEvent,
} from "react";

import {
  listBotanicalIdentities,
  type BotanicalIdentityResponse,
} from "../botanical-identities/api";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { useCreationDisclosure } from "../components/useCreationDisclosure";
import { EventJournal } from "../events/EventJournal";
import {
  listGeographicPlaces,
  type GeographicPlaceResponse,
} from "../geographic-places/api";
import { listLocations, type LocationResponse } from "../locations/api";
import { PartialDateField } from "../seed-lots/PartialDateField";
import { ReferencePicker } from "../seed-lots/ReferencePicker";
import { listSowings, type SowingResponse } from "../sowings/api";
import { listSuppliers, type SupplierResponse } from "../suppliers/api";
import {
  createPlant,
  createPlantGroup,
  extractPlantFromGroup,
  getPlant,
  getPlantGroup,
  listPlantGroups,
  listPlants,
  plantValidationMessages,
  updatePlant,
  updatePlantGroup,
  type DirectOriginKind,
  type PartialDate,
  type PlantCreate,
  type PlantGroupCreate,
  type PlantGroupLifecycle,
  type PlantGroupResponse,
  type PlantLifecycle,
  type PlantResponse,
} from "./api";

type RecordKind = "plant" | "group";
type PlantRecord =
  | { kind: "plant"; value: PlantResponse }
  | { kind: "group"; value: PlantGroupResponse };
type CollectionState =
  | { status: "loading" }
  | { status: "ready"; records: PlantRecord[] }
  | { status: "error" };
type DetailState =
  | { status: "idle" }
  | { status: "loading"; key: string }
  | { status: "ready"; record: PlantRecord }
  | { status: "error"; key: string };
type SaveState =
  | { status: "idle" }
  | { status: "saving" }
  | { status: "success"; message: string }
  | { status: "error"; messages: string[] };
type QuantityKind = "unknown" | "exact" | "approximate";
type OriginMode = "direct" | "sowing";

interface References {
  identities: BotanicalIdentityResponse[];
  sowings: SowingResponse[];
  suppliers: SupplierResponse[];
  places: GeographicPlaceResponse[];
  locations: LocationResponse[];
}

interface FormState {
  botanicalIdentityId: string;
  label: string;
  originMode: OriginMode;
  sowingId: string;
  directOriginKind: DirectOriginKind;
  directOriginDetail: string;
  supplierId: string;
  provenanceId: string;
  locationId: string;
  collectionEntryDate: PartialDate | null;
  lifecycle: PlantLifecycle | PlantGroupLifecycle;
  quantityKind: QuantityKind;
  quantityValue: string;
  notes: string;
}

const plantLifecycleLabels: Record<PlantLifecycle, string> = {
  active: "Active",
  dead: "Dead",
  lost: "Lost",
  discarded: "Discarded",
};
const groupLifecycleLabels: Record<PlantGroupLifecycle, string> = {
  active: "Active",
  completed: "Completed",
  dead: "Dead",
  lost: "Lost",
  discarded: "Discarded",
};
const originLabels: Record<DirectOriginKind, string> = {
  purchased: "Purchased",
  gift_exchange: "Gift / exchange",
  collection_produced: "Collection produced",
  other: "Other",
  unknown: "Unknown",
};

function recordKey(record: PlantRecord): string {
  return `${record.kind}:${record.value.id}`;
}

function blankForm(): FormState {
  return {
    botanicalIdentityId: "",
    label: "",
    originMode: "direct",
    sowingId: "",
    directOriginKind: "unknown",
    directOriginDetail: "",
    supplierId: "",
    provenanceId: "",
    locationId: "",
    collectionEntryDate: null,
    lifecycle: "active",
    quantityKind: "unknown",
    quantityValue: "",
    notes: "",
  };
}

function formFrom(record: PlantRecord): FormState {
  const value = record.value;
  const quantity = record.kind === "group" ? record.value.quantity : null;
  return {
    botanicalIdentityId: value.botanical_identity_id,
    label: value.label ?? "",
    originMode: value.originating_sowing_id ? "sowing" : "direct",
    sowingId: value.originating_sowing_id ?? "",
    directOriginKind: value.direct_origin_kind ?? "unknown",
    directOriginDetail: value.direct_origin_detail ?? "",
    supplierId: value.supplier_id ?? "",
    provenanceId: value.material_provenance_place_id ?? "",
    locationId: value.location_id ?? "",
    collectionEntryDate: value.collection_entry_date,
    lifecycle: value.lifecycle,
    quantityKind: quantity
      ? quantity.is_approximate
        ? "approximate"
        : "exact"
      : "unknown",
    quantityValue: quantity ? String(quantity.value) : "",
    notes: value.notes ?? "",
  };
}

function commonPayload(form: FormState) {
  const direct = form.originMode === "direct";
  return {
    botanical_identity_id: form.botanicalIdentityId,
    label: form.label || null,
    originating_sowing_id: direct ? null : form.sowingId || null,
    direct_origin_kind: direct ? form.directOriginKind : null,
    direct_origin_detail:
      direct && form.directOriginKind === "other"
        ? form.directOriginDetail || null
        : null,
    supplier_id: direct ? form.supplierId || null : null,
    material_provenance_place_id: direct ? form.provenanceId || null : null,
    location_id: form.locationId || null,
    collection_entry_date: form.collectionEntryDate,
    notes: form.notes || null,
  };
}

function plantPayload(form: FormState): PlantCreate {
  return {
    ...commonPayload(form),
    lifecycle: form.lifecycle as PlantLifecycle,
  };
}

function groupPayload(form: FormState): PlantGroupCreate {
  return {
    ...commonPayload(form),
    lifecycle: form.lifecycle,
    quantity:
      form.quantityKind === "unknown"
        ? null
        : {
            value: Number(form.quantityValue),
            is_approximate: form.quantityKind === "approximate",
          },
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

function quantityLabel(record: PlantRecord): string | null {
  if (record.kind === "plant") return null;
  const quantity = record.value.quantity;
  if (!quantity) return "Quantity unknown";
  return `${quantity.is_approximate ? "~" : ""}${String(quantity.value)} plants`;
}

function extractionQuantityExplanation(group: PlantGroupResponse): string {
  if (group.lifecycle !== "active")
    return "This group is no longer active. Extraction cannot continue.";
  if (!group.quantity)
    return "Group quantity is unknown and will remain unknown.";
  if (group.quantity.is_approximate)
    return "Approximate group quantity will remain unchanged.";
  if (group.quantity.value === 1)
    return "This is the last exact member. The group will become Completed.";
  return `Group count: ${String(group.quantity.value)} → ${String(group.quantity.value - 1)}`;
}

function originSummary(record: PlantRecord): string {
  const value = record.value;
  const originatingGroup =
    record.kind === "plant" ? record.value.originating_plant_group : null;
  if (originatingGroup)
    return `Extracted from group · ${originatingGroup.label ?? originatingGroup.botanical_identity.display_label}`;
  if (value.originating_sowing)
    return `From sowing${value.originating_sowing.label ? ` · ${value.originating_sowing.label}` : ""}`;
  const kind = value.direct_origin_kind ?? "unknown";
  if (kind === "purchased" && value.supplier)
    return `Purchased · ${value.supplier.name}`;
  return kind === "unknown" ? "Origin unknown" : originLabels[kind];
}

function lifecycleLabel(record: PlantRecord): string {
  return record.kind === "plant"
    ? plantLifecycleLabels[record.value.lifecycle]
    : groupLifecycleLabels[record.value.lifecycle];
}

function sowingChoice(sowing: SowingResponse): string {
  const label = sowing.label ? ` · ${sowing.label}` : "";
  const lot = sowing.seed_lot.label ? ` · lot ${sowing.seed_lot.label}` : "";
  return `${sowing.seed_lot.botanical_identity_display_label}${label}${lot} · ${sowing.lifecycle}`;
}

function Detail({
  record,
  sowings,
  locations,
  headingRef,
  onEventTargetRefresh,
}: {
  record: PlantRecord;
  sowings: SowingResponse[];
  locations: LocationResponse[];
  headingRef: RefObject<HTMLHeadingElement | null>;
  onEventTargetRefresh: () => Promise<void>;
}) {
  const value = record.value;
  const sowing = value.originating_sowing_id
    ? sowings.find(({ id }) => id === value.originating_sowing_id)
    : undefined;
  const hasDirectOrigin = !value.originating_sowing_id;
  const originatingGroup =
    record.kind === "plant" ? record.value.originating_plant_group : null;
  return (
    <article className="plant-detail">
      <section aria-labelledby="plant-record-title">
        <p className="eyebrow">
          {record.kind === "plant" ? "Plant" : "Plant group"}
        </p>
        <h3 id="plant-record-title" tabIndex={-1} ref={headingRef}>
          {value.botanical_identity.display_label}
        </h3>
        {value.label && <p className="seed-label">{value.label}</p>}
        <dl>
          <div>
            <dt>Lifecycle</dt>
            <dd>{lifecycleLabel(record)}</dd>
          </div>
          <div>
            <dt>Collection entry</dt>
            <dd>{dateLabel(value.collection_entry_date)}</dd>
          </div>
          <div>
            <dt>Current location</dt>
            <dd>{value.location?.display_path ?? "Not recorded"}</dd>
          </div>
        </dl>
      </section>
      {record.kind === "group" && (
        <section aria-labelledby="plant-group-title">
          <h4 id="plant-group-title">Group</h4>
          <dl>
            <div>
              <dt>Quantity</dt>
              <dd>{quantityLabel(record)}</dd>
            </div>
          </dl>
        </section>
      )}
      <section aria-labelledby="plant-origin-title">
        <h4 id="plant-origin-title">Origin</h4>
        {originatingGroup ? (
          <dl>
            <div>
              <dt>Extracted from group</dt>
              <dd>
                {originatingGroup.label ??
                  originatingGroup.botanical_identity.display_label}
              </dd>
            </div>
            <div>
              <dt>Group botanical context</dt>
              <dd>{originatingGroup.botanical_identity.display_label}</dd>
            </div>
          </dl>
        ) : value.originating_sowing ? (
          <dl>
            <div>
              <dt>Origin Sowing</dt>
              <dd>{value.originating_sowing.label ?? "Unlabelled Sowing"}</dd>
            </div>
            <div>
              <dt>Sowing lifecycle</dt>
              <dd>{value.originating_sowing.lifecycle}</dd>
            </div>
            <div>
              <dt>Upstream botanical context</dt>
              <dd>
                {value.originating_sowing.botanical_identity_display_label}
              </dd>
            </div>
            <div>
              <dt>Seed lot</dt>
              <dd>
                {sowing?.seed_lot.label ?? value.originating_sowing.seed_lot_id}
              </dd>
            </div>
          </dl>
        ) : (
          <dl>
            <div>
              <dt>Direct origin</dt>
              <dd>{originLabels[value.direct_origin_kind ?? "unknown"]}</dd>
            </div>
            {value.direct_origin_kind === "other" &&
              value.direct_origin_detail && (
                <div>
                  <dt>Origin detail</dt>
                  <dd>{value.direct_origin_detail}</dd>
                </div>
              )}
            {value.supplier && (
              <div>
                <dt>Supplier</dt>
                <dd>{value.supplier.name}</dd>
              </div>
            )}
            {value.material_provenance && (
              <div>
                <dt>Material provenance</dt>
                <dd>{value.material_provenance.display_path}</dd>
              </div>
            )}
          </dl>
        )}
        {!hasDirectOrigin && !originatingGroup && (
          <p className="field-help">
            The upstream botanical context describes the origin Sowing; the
            identity above belongs to this record.
          </p>
        )}
      </section>
      {value.notes && (
        <section aria-labelledby="plant-notes-title">
          <h4 id="plant-notes-title">Notes</h4>
          <p className="preserve-lines">{value.notes}</p>
        </section>
      )}
      <EventJournal
        key={`${record.kind}:${value.id}`}
        targetKind={record.kind}
        targetId={value.id}
        targetLabel={value.label ?? value.botanical_identity.display_label}
        locations={locations}
        onTargetRefresh={onEventTargetRefresh}
      />
    </article>
  );
}

export function PlantScreen() {
  const auth = useAuth();
  const [collection, setCollection] = useState<CollectionState>({
    status: "loading",
  });
  const [references, setReferences] = useState<References | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [detailAttempt, setDetailAttempt] = useState(0);
  const [detail, setDetail] = useState<DetailState>({ status: "idle" });
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [lifecycleFilter, setLifecycleFilter] = useState<
    "active" | "history" | "all"
  >("active");
  const [typeFilter, setTypeFilter] = useState<"all" | RecordKind>("all");
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState(false);
  const [creationKind, setCreationKind] = useState<RecordKind | null>(null);
  const [mobileDetail, setMobileDetail] = useState(false);
  const [form, setForm] = useState<FormState>(blankForm);
  const [moreDetails, setMoreDetails] = useState(false);
  const [save, setSave] = useState<SaveState>({ status: "idle" });
  const [extractionSource, setExtractionSource] =
    useState<PlantGroupResponse | null>(null);
  const feedback = useRef<HTMLDivElement>(null);
  const detailHeading = useRef<HTMLHeadingElement>(null);
  const extractionHeading = useRef<HTMLHeadingElement>(null);
  const extractionTrigger = useRef<HTMLButtonElement | null>(null);
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
    if (editing && extractionSource) extractionHeading.current?.focus();
  }, [editing, extractionSource]);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      listPlants(controller.signal),
      listPlantGroups(controller.signal),
      listBotanicalIdentities(controller.signal),
      listSowings(controller.signal),
      listSuppliers(controller.signal),
      listGeographicPlaces(controller.signal),
      listLocations(controller.signal),
    ])
      .then(
        ([
          plants,
          groups,
          identities,
          sowings,
          suppliers,
          places,
          locations,
        ]) => {
          const records: PlantRecord[] = [
            ...plants.map((value): PlantRecord => ({ kind: "plant", value })),
            ...groups.map((value): PlantRecord => ({ kind: "group", value })),
          ];
          setCollection({ status: "ready", records });
          setReferences({ identities, sowings, suppliers, places, locations });
          setSelectedKey((current) =>
            current && records.some((record) => recordKey(record) === current)
              ? current
              : null,
          );
        },
      )
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
    if (!selectedKey) return;
    if (detail.status === "ready" && recordKey(detail.record) === selectedKey)
      return;
    const [kind, id] = selectedKey.split(":", 2) as [RecordKind, string];
    const controller = new AbortController();
    const request =
      kind === "plant"
        ? getPlant(id, controller.signal)
        : getPlantGroup(id, controller.signal);
    void request
      .then((value) => {
        setDetail({ status: "ready", record: { kind, value } as PlantRecord });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else setDetail({ status: "error", key: selectedKey });
      });
    return () => {
      controller.abort();
    };
  }, [auth, detail, detailAttempt, selectedKey]);

  useEffect(() => {
    if (save.status === "error") feedback.current?.focus();
  }, [save]);

  useEffect(() => {
    if (mobileDetail && detail.status === "ready" && !editing)
      detailHeading.current?.focus();
  }, [detail, editing, mobileDetail]);

  const records = useMemo(
    () => (collection.status === "ready" ? collection.records : []),
    [collection],
  );
  const visible = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return records.filter((record) => {
      const value = record.value;
      const lifecycleMatch =
        lifecycleFilter === "all" ||
        (lifecycleFilter === "active"
          ? value.lifecycle === "active"
          : value.lifecycle !== "active");
      const typeMatch = typeFilter === "all" || record.kind === typeFilter;
      const sowing = value.originating_sowing_id
        ? references?.sowings.find(
            ({ id }) => id === value.originating_sowing_id,
          )
        : undefined;
      const originatingGroup =
        record.kind === "plant" ? record.value.originating_plant_group : null;
      const textMatch =
        !query ||
        [
          value.botanical_identity.display_label,
          value.label,
          value.location?.display_path,
          value.supplier?.name,
          value.originating_sowing?.label,
          value.originating_sowing?.botanical_identity_display_label,
          originatingGroup?.label,
          originatingGroup?.botanical_identity.display_label,
          sowing?.seed_lot.label,
        ].some((item) => item?.toLocaleLowerCase().includes(query));
      return lifecycleMatch && typeMatch && textMatch;
    });
  }, [lifecycleFilter, records, references, search, typeFilter]);

  if (!references && collection.status === "loading")
    return (
      <section className="workspace" aria-labelledby="plants-title">
        <h2 id="plants-title">Plants</h2>
        <p role="status">Loading Plants…</p>
      </section>
    );
  if (collection.status === "error" || !references)
    return (
      <section className="workspace" aria-labelledby="plants-title">
        <h2 id="plants-title">Plants</h2>
        <div className="notice notice--error" role="alert">
          <p>Florabase could not load the Plant collection or its choices.</p>
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
  if (
    auth.state.status !== "authenticated" &&
    auth.state.status !== "logging-out" &&
    auth.state.status !== "logout-failed"
  )
    return null;
  const csrfToken = auth.state.csrfToken;
  const pending = save.status === "saving";
  const selected =
    detail.status === "ready" && recordKey(detail.record) === selectedKey
      ? detail.record
      : null;
  const formKind = extractionSource
    ? "plant"
    : (selected?.kind ?? creationKind);
  const extractedEdit =
    !extractionSource &&
    selected?.kind === "plant" &&
    Boolean(selected.value.originating_plant_group_id);

  function startCreate() {
    setExtractionSource(null);
    setSelectedKey(null);
    setDetail({ status: "idle" });
    setCreationKind(null);
    setEditing(true);
    setMobileDetail(true);
    setForm(blankForm());
    setMoreDetails(false);
    setSave({ status: "idle" });
    openCreation();
  }

  function chooseCreationKind(kind: RecordKind) {
    setCreationKind(kind);
    setForm(blankForm());
    setMoreDetails(false);
    setSave({ status: "idle" });
  }

  function startEdit(record: PlantRecord) {
    setExtractionSource(null);
    if (creationExpanded) closeCreation({ returnFocus: false });
    setCreationKind(null);
    setForm(formFrom(record));
    setMoreDetails(true);
    setEditing(true);
    setSave({ status: "idle" });
  }

  function selectRecord(record: PlantRecord, trigger: HTMLButtonElement) {
    setExtractionSource(null);
    if (creationExpanded) closeCreation({ returnFocus: false });
    const key = recordKey(record);
    selectedTrigger.current = trigger;
    setDetail({ status: "loading", key });
    setSelectedKey(key);
    setMobileDetail(true);
    setEditing(false);
    setCreationKind(null);
    setSave({ status: "idle" });
  }

  function returnToList() {
    setMobileDetail(false);
    setEditing(false);
    window.setTimeout(() => selectedTrigger.current?.focus(), 0);
  }

  function startExtraction(group: PlantGroupResponse) {
    setExtractionSource(group);
    setForm({
      ...blankForm(),
      botanicalIdentityId: group.botanical_identity_id,
      locationId: group.location_id ?? "",
    });
    setMoreDetails(true);
    setEditing(true);
    setSave({ status: "idle" });
  }

  function updateForm<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function refreshEventTarget(kind: RecordKind, id: string) {
    const [target, plants, groups] = await Promise.all([
      kind === "plant" ? getPlant(id) : getPlantGroup(id),
      listPlants(),
      listPlantGroups(),
    ]);
    const authoritative = {
      kind,
      value: target,
    } as PlantRecord;
    setDetail({ status: "ready", record: authoritative });
    setCollection({
      status: "ready",
      records: [
        ...plants.map((value): PlantRecord => ({ kind: "plant", value })),
        ...groups.map((value): PlantRecord => ({ kind: "group", value })),
      ],
    });
  }

  function validate(): string[] {
    const errors: string[] = [];
    if (!form.botanicalIdentityId) errors.push("Choose a Botanical identity.");
    if (form.originMode === "sowing" && !form.sowingId)
      errors.push("Choose an originating Sowing.");
    if (
      form.directOriginKind === "other" &&
      form.originMode === "direct" &&
      !form.directOriginDetail.trim()
    )
      errors.push("Describe the other direct origin.");
    if (formKind === "group" && form.quantityKind !== "unknown") {
      const quantity = Number(form.quantityValue);
      if (
        form.quantityValue === "" ||
        !Number.isInteger(quantity) ||
        quantity < 0
      )
        errors.push("Group count must be zero or a positive whole number.");
      else if (form.quantityKind === "approximate" && quantity === 0)
        errors.push("Approximate group count must be greater than zero.");
      else if (
        quantity === 0 &&
        !["completed", "dead", "discarded"].includes(form.lifecycle)
      )
        errors.push(
          "Exact zero is only valid for completed, dead, or discarded groups.",
        );
    }
    return errors;
  }

  async function submit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (pending || !formKind) return;
    const errors = validate();
    if (errors.length) {
      setSave({ status: "error", messages: errors });
      return;
    }
    const wasCreating = !selected;
    setSave({ status: "saving" });
    try {
      let authoritative: PlantRecord;
      if (extractionSource) {
        const result = await extractPlantFromGroup(
          extractionSource.id,
          {
            botanical_identity_id: form.botanicalIdentityId,
            location_id: form.locationId || null,
            label: form.label || null,
            collection_entry_date: form.collectionEntryDate,
            notes: form.notes || null,
          },
          csrfToken,
        );
        authoritative = { kind: "plant", value: result.plant };
        setCollection((current) => ({
          status: "ready",
          records:
            current.status === "ready"
              ? [
                  authoritative,
                  ...current.records
                    .filter(
                      (record) =>
                        recordKey(record) !== recordKey(authoritative),
                    )
                    .map((record) =>
                      record.kind === "group" &&
                      record.value.id === result.plant_group.id
                        ? ({
                            kind: "group",
                            value: result.plant_group,
                          } satisfies PlantRecord)
                        : record,
                    ),
                ]
              : [
                  authoritative,
                  {
                    kind: "group",
                    value: result.plant_group,
                  } satisfies PlantRecord,
                ],
        }));
        setSelectedKey(recordKey(authoritative));
        setDetail({ status: "ready", record: authoritative });
        setEditing(false);
        setExtractionSource(null);
        setSave({
          status: "success",
          message: "Plant was extracted from the group.",
        });
        return;
      } else if (formKind === "plant") {
        const value = selected
          ? await updatePlant(
              selected.value.id,
              extractedEdit
                ? {
                    botanical_identity_id: form.botanicalIdentityId,
                    label: form.label || null,
                    collection_entry_date: form.collectionEntryDate,
                    location_id: form.locationId || null,
                    lifecycle: form.lifecycle as PlantLifecycle,
                    notes: form.notes || null,
                  }
                : plantPayload(form),
              csrfToken,
            )
          : await createPlant(plantPayload(form), csrfToken);
        authoritative = { kind: "plant", value };
      } else {
        const value = selected
          ? await updatePlantGroup(
              selected.value.id,
              groupPayload(form),
              csrfToken,
            )
          : await createPlantGroup(groupPayload(form), csrfToken);
        authoritative = { kind: "group", value };
      }
      const [plants, groups] = await Promise.all([
        listPlants(),
        listPlantGroups(),
      ]);
      setCollection({
        status: "ready",
        records: [
          ...plants.map((value): PlantRecord => ({ kind: "plant", value })),
          ...groups.map((value): PlantRecord => ({ kind: "group", value })),
        ],
      });
      setSelectedKey(recordKey(authoritative));
      setDetail({ status: "ready", record: authoritative });
      setEditing(false);
      setCreationKind(null);
      if (wasCreating) closeCreation();
      setSave({
        status: "success",
        message: wasCreating
          ? `${formKind === "plant" ? "Plant" : "Plant group"} was added to the collection.`
          : `${formKind === "plant" ? "Plant" : "Plant group"} changes were saved.`,
      });
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else if (error instanceof ApiError && error.status === 422)
        setSave({ status: "error", messages: plantValidationMessages(error) });
      else if (
        extractionSource &&
        error instanceof ApiError &&
        error.status === 409
      ) {
        try {
          const refreshed = await getPlantGroup(extractionSource.id);
          setExtractionSource(refreshed);
          setCollection((current) => ({
            status: "ready",
            records:
              current.status === "ready"
                ? current.records.map((record) =>
                    record.kind === "group" && record.value.id === refreshed.id
                      ? { kind: "group", value: refreshed }
                      : record,
                  )
                : [{ kind: "group", value: refreshed }],
          }));
        } finally {
          setSave({
            status: "error",
            messages: [
              "The Plant group changed before extraction. Its current state has been refreshed; review it and try again.",
            ],
          });
        }
      } else if (error instanceof ApiError && error.status === 403)
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
            "Florabase could not save or refresh this record. Check the connection and try again.",
          ],
        });
    }
  }

  return (
    <section
      className="workspace plants-workspace"
      aria-labelledby="plants-title"
    >
      <div className="workspace-intro seed-heading">
        <div>
          <p className="eyebrow">Living collection</p>
          <h2 id="plants-title">Plants</h2>
          <p>
            Manage individual specimens and groups together without losing their
            origin.
          </p>
        </div>
        <button
          type="button"
          ref={creationTriggerRef}
          aria-expanded={creationExpanded}
          aria-controls="new-plant-panel"
          disabled={references.identities.length === 0}
          onClick={() => {
            if (creationExpanded) focusCreation();
            else startCreate();
          }}
        >
          + New
        </button>
      </div>
      {references.identities.length === 0 && (
        <div className="notice" role="status">
          <p>
            A Botanical identity is required before you can record a Plant or
            Plant group. Add one from Botanical identities first.
          </p>
        </div>
      )}
      <div
        className={`plant-master-detail${mobileDetail ? " is-detail-view" : ""}`}
      >
        <section
          className="seed-master plant-master"
          aria-labelledby="plant-list-title"
        >
          <h3 id="plant-list-title">Plants collection</h3>
          <div className="seed-controls">
            <div className="field">
              <label htmlFor="plant-search">Search Plants</label>
              <input
                id="plant-search"
                type="search"
                value={search}
                onChange={(event) => {
                  setSearch(event.currentTarget.value);
                }}
              />
            </div>
            <fieldset className="lifecycle-filter">
              <legend>Lifecycle</legend>
              {(["active", "history", "all"] as const).map((item) => (
                <button
                  key={item}
                  type="button"
                  aria-pressed={lifecycleFilter === item}
                  onClick={() => {
                    setLifecycleFilter(item);
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
            <fieldset className="lifecycle-filter">
              <legend>Record type</legend>
              {(["all", "plant", "group"] as const).map((item) => (
                <button
                  key={item}
                  type="button"
                  aria-pressed={typeFilter === item}
                  onClick={() => {
                    setTypeFilter(item);
                  }}
                >
                  {item === "all"
                    ? "All"
                    : item === "plant"
                      ? "Plants"
                      : "Groups"}
                </button>
              ))}
            </fieldset>
          </div>
          {records.length === 0 ? (
            <div className="profile-empty">
              <h4>No Plants recorded yet</h4>
              <p>Use + New to record the first Plant or Plant group.</p>
            </div>
          ) : visible.length === 0 ? (
            <p>No Plants match this search and filter view.</p>
          ) : (
            <ul className="seed-list" aria-label="Plants collection">
              {visible.map((record) => {
                const value = record.value;
                return (
                  <li key={recordKey(record)}>
                    <button
                      type="button"
                      className="seed-row plant-row"
                      aria-pressed={selectedKey === recordKey(record)}
                      onClick={(event) => {
                        selectRecord(record, event.currentTarget);
                      }}
                    >
                      <span className="seed-primary">
                        <strong>
                          {value.botanical_identity.display_label}
                        </strong>
                        {value.label && <small>{value.label}</small>}
                      </span>
                      <span className="record-type-badge">
                        {record.kind === "plant" ? "Plant" : "Group"}
                      </span>
                      <span>
                        {value.location?.display_path ??
                          "Location not recorded"}
                      </span>
                      <span>{originSummary(record)}</span>
                      {quantityLabel(record) && (
                        <span>{quantityLabel(record)}</span>
                      )}
                      <span
                        className={`lifecycle-badge lifecycle-badge--${value.lifecycle}`}
                      >
                        {lifecycleLabel(record)}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
        <section
          id={creationExpanded ? "new-plant-panel" : undefined}
          className={`seed-detail-pane plant-detail-pane${creationExpanded ? " seed-creation-panel" : ""}`}
          ref={creationExpanded ? creationPanelRef : undefined}
          aria-label="Plant detail and editor"
        >
          <button
            type="button"
            className="plant-back button--secondary"
            onClick={returnToList}
          >
            ← Back to Plants
          </button>
          {save.status === "success" && (
            <div className="notice notice--success" role="status">
              {save.message}
            </div>
          )}
          {editing ? (
            creationExpanded && !creationKind ? (
              <div className="plant-kind-choice">
                <div className="seed-form-heading">
                  <div>
                    <p className="eyebrow">New collection record</p>
                    <h3>What are you tracking?</h3>
                  </div>
                  <button
                    type="button"
                    className="button--secondary"
                    onClick={() => {
                      setEditing(false);
                      setMobileDetail(false);
                      closeCreation();
                    }}
                  >
                    Cancel
                  </button>
                </div>
                <p>
                  Choose individual tracking for one specimen or group tracking
                  for multiple individuals managed together.
                </p>
                <div className="plant-kind-actions">
                  <button
                    type="button"
                    data-creation-focus
                    onClick={() => {
                      chooseCreationKind("plant");
                    }}
                  >
                    <strong>Plant</strong>
                    <span>One individually tracked specimen</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      chooseCreationKind("group");
                    }}
                  >
                    <strong>Plant group</strong>
                    <span>Multiple individuals managed as one record</span>
                  </button>
                </div>
              </div>
            ) : formKind ? (
              <form
                className="seed-form plant-form"
                onSubmit={(event) => void submit(event)}
                noValidate
              >
                <div className="seed-form-heading">
                  <div>
                    <p className="eyebrow">
                      {extractionSource
                        ? "PlantGroup extraction"
                        : selected
                          ? "Correct record"
                          : "Fast entry"}
                    </p>
                    <h3
                      ref={extractionSource ? extractionHeading : undefined}
                      tabIndex={extractionSource ? -1 : undefined}
                    >
                      {extractionSource
                        ? "Extract plant"
                        : selected
                          ? `Edit ${formKind === "plant" ? "Plant" : "Plant group"}`
                          : `Record ${formKind === "plant" ? "Plant" : "Plant group"}`}
                    </h3>
                  </div>
                  <button
                    type="button"
                    className="button--secondary"
                    onClick={() => {
                      const wasExtraction = extractionSource !== null;
                      setEditing(false);
                      setExtractionSource(null);
                      setSave({ status: "idle" });
                      if (!selected) {
                        setCreationKind(null);
                        setMobileDetail(false);
                        closeCreation();
                      } else if (wasExtraction) {
                        window.setTimeout(
                          () => extractionTrigger.current?.focus(),
                          0,
                        );
                      }
                    }}
                  >
                    Cancel
                  </button>
                </div>
                <ReferencePicker
                  key={`${selectedKey ?? "new"}-${formKind}-identity`}
                  label="Botanical identity"
                  required
                  disabled={pending}
                  value={form.botanicalIdentityId}
                  onChange={(value) => {
                    updateForm("botanicalIdentityId", value);
                  }}
                  choices={references.identities.map((identity) => ({
                    id: identity.id,
                    label: identity.display_label,
                  }))}
                />
                <div className="field">
                  <label htmlFor="plant-label">
                    Label <span className="optional">(optional)</span>
                  </label>
                  <input
                    id="plant-label"
                    value={form.label}
                    disabled={pending}
                    onChange={(event) => {
                      updateForm("label", event.currentTarget.value);
                    }}
                  />
                </div>
                {formKind === "group" && (
                  <fieldset className="quantity-field">
                    <legend>
                      Quantity <span className="optional">(optional)</span>
                    </legend>
                    <div className="field">
                      <label htmlFor="plant-quantity-kind">Kind</label>
                      <select
                        id="plant-quantity-kind"
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
                        <option value="exact">Exact count</option>
                        <option value="approximate">Approximate count</option>
                      </select>
                    </div>
                    {form.quantityKind !== "unknown" && (
                      <div className="field">
                        <label htmlFor="plant-quantity-value">Count</label>
                        <input
                          id="plant-quantity-value"
                          inputMode="numeric"
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
                    )}
                  </fieldset>
                )}
                {extractionSource && (
                  <div className="notice" role="status">
                    <p>
                      Origin: {extractionSource.label ?? "this Plant group"}.
                    </p>
                    <p>{extractionQuantityExplanation(extractionSource)}</p>
                  </div>
                )}
                {!extractionSource && (
                  <button
                    type="button"
                    className="button--secondary disclosure-button"
                    aria-expanded={moreDetails}
                    aria-controls="plant-advanced-fields"
                    onClick={() => {
                      setMoreDetails((value) => !value);
                    }}
                  >
                    {moreDetails ? "Fewer details" : "More details"}
                  </button>
                )}
                {moreDetails && (
                  <div
                    id="plant-advanced-fields"
                    className="advanced-fields plant-advanced-fields"
                  >
                    {!extractionSource && !extractedEdit ? (
                      <>
                        <fieldset className="origin-mode-field field--full">
                          <legend>Origin</legend>
                          <label className="checkbox-label">
                            <input
                              type="radio"
                              name="origin-mode"
                              checked={form.originMode === "direct"}
                              disabled={pending}
                              onChange={() => {
                                setForm((current) => ({
                                  ...current,
                                  originMode: "direct",
                                  sowingId: "",
                                }));
                              }}
                            />
                            Direct / origin not tracked through a Sowing
                          </label>
                          <label className="checkbox-label">
                            <input
                              type="radio"
                              name="origin-mode"
                              checked={form.originMode === "sowing"}
                              disabled={pending}
                              onChange={() => {
                                setForm((current) => ({
                                  ...current,
                                  originMode: "sowing",
                                  directOriginKind: "unknown",
                                  directOriginDetail: "",
                                  supplierId: "",
                                  provenanceId: "",
                                }));
                              }}
                            />
                            Known Sowing
                          </label>
                        </fieldset>
                        {form.originMode === "sowing" ? (
                          <div className="field--full">
                            <ReferencePicker
                              key={`${selectedKey ?? "new"}-${formKind}-sowing`}
                              label="Originating Sowing"
                              required
                              disabled={pending}
                              value={form.sowingId}
                              onChange={(value) => {
                                updateForm("sowingId", value);
                              }}
                              choices={references.sowings.map((sowing) => ({
                                id: sowing.id,
                                label: sowingChoice(sowing),
                              }))}
                            />
                            <small>
                              Active and historical Sowings are available.
                              Choosing one never changes this record's Botanical
                              identity.
                            </small>
                          </div>
                        ) : (
                          <>
                            <div className="field">
                              <label htmlFor="plant-direct-origin">
                                Direct origin
                              </label>
                              <select
                                id="plant-direct-origin"
                                value={form.directOriginKind}
                                disabled={pending}
                                onChange={(event) => {
                                  const directOriginKind = event.currentTarget
                                    .value as DirectOriginKind;
                                  setForm((current) => ({
                                    ...current,
                                    directOriginKind,
                                    directOriginDetail:
                                      directOriginKind === "other"
                                        ? current.directOriginDetail
                                        : "",
                                  }));
                                }}
                              >
                                {(
                                  Object.keys(
                                    originLabels,
                                  ) as DirectOriginKind[]
                                ).map((kind) => (
                                  <option key={kind} value={kind}>
                                    {originLabels[kind]}
                                  </option>
                                ))}
                              </select>
                            </div>
                            {form.directOriginKind === "other" && (
                              <div className="field">
                                <label htmlFor="plant-origin-detail">
                                  Other origin detail
                                </label>
                                <input
                                  id="plant-origin-detail"
                                  value={form.directOriginDetail}
                                  disabled={pending}
                                  onChange={(event) => {
                                    updateForm(
                                      "directOriginDetail",
                                      event.currentTarget.value,
                                    );
                                  }}
                                />
                              </div>
                            )}
                            <div className="field">
                              <label htmlFor="plant-supplier">
                                Supplier{" "}
                                <span className="optional">(optional)</span>
                              </label>
                              <select
                                id="plant-supplier"
                                value={form.supplierId}
                                disabled={pending}
                                onChange={(event) => {
                                  updateForm(
                                    "supplierId",
                                    event.currentTarget.value,
                                  );
                                }}
                              >
                                <option value="">Not recorded</option>
                                {references.suppliers.map((supplier) => (
                                  <option
                                    key={supplier.id}
                                    value={supplier.id}
                                    disabled={
                                      Boolean(supplier.retired_at) &&
                                      supplier.id !== form.supplierId
                                    }
                                  >
                                    {supplier.name}
                                    {supplier.retired_at ? " (retired)" : ""}
                                  </option>
                                ))}
                              </select>
                              <small>
                                Selecting a Supplier does not change the
                                direct-origin kind.
                              </small>
                            </div>
                            <div className="field">
                              <label htmlFor="plant-provenance">
                                Material provenance{" "}
                                <span className="optional">(optional)</span>
                              </label>
                              <select
                                id="plant-provenance"
                                value={form.provenanceId}
                                disabled={pending}
                                onChange={(event) => {
                                  updateForm(
                                    "provenanceId",
                                    event.currentTarget.value,
                                  );
                                }}
                              >
                                <option value="">Not recorded</option>
                                {references.places.map((place) => (
                                  <option
                                    key={place.id}
                                    value={place.id}
                                    disabled={
                                      Boolean(place.retired_at) &&
                                      place.id !== form.provenanceId
                                    }
                                  >
                                    {place.display_path}
                                    {place.retired_at ? " (retired)" : ""}
                                  </option>
                                ))}
                              </select>
                              <small>
                                Where the biological material originated or was
                                collected, when known.
                              </small>
                            </div>
                          </>
                        )}
                      </>
                    ) : (
                      <div className="field--full notice">
                        <strong>Origin is read-only.</strong>{" "}
                        {extractionSource
                          ? `This Plant will be extracted from ${extractionSource.label ?? extractionSource.botanical_identity.display_label}.`
                          : `This Plant was extracted from ${selected?.kind === "plant" ? (selected.value.originating_plant_group?.label ?? selected.value.originating_plant_group?.botanical_identity.display_label ?? "its Plant group") : "its Plant group"}.`}
                      </div>
                    )}
                    <PartialDateField
                      id="plant-entry-date"
                      label="Collection-entry date (optional)"
                      value={form.collectionEntryDate}
                      disabled={pending}
                      onChange={(value) => {
                        updateForm("collectionEntryDate", value);
                      }}
                    />
                    <div className="field">
                      <label htmlFor="plant-location">
                        Current location{" "}
                        <span className="optional">(optional)</span>
                      </label>
                      <select
                        id="plant-location"
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
                      <small>
                        The record's current physical collection position.
                      </small>
                    </div>
                    {!extractionSource && (
                      <div className="field">
                        <label htmlFor="plant-lifecycle">Lifecycle</label>
                        <select
                          id="plant-lifecycle"
                          value={form.lifecycle}
                          disabled={pending}
                          onChange={(event) => {
                            updateForm(
                              "lifecycle",
                              event.currentTarget
                                .value as FormState["lifecycle"],
                            );
                          }}
                        >
                          {Object.entries(
                            formKind === "plant"
                              ? plantLifecycleLabels
                              : groupLifecycleLabels,
                          ).map(([value, label]) => (
                            <option key={value} value={value}>
                              {label}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                    <div className="field field--full">
                      <label htmlFor="plant-notes">
                        Notes <span className="optional">(optional)</span>
                      </label>
                      <textarea
                        id="plant-notes"
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
                  <button
                    type="submit"
                    disabled={
                      pending ||
                      (extractionSource !== null &&
                        extractionSource.lifecycle !== "active")
                    }
                  >
                    {pending
                      ? "Saving…"
                      : extractionSource
                        ? "Extract plant"
                        : selected
                          ? "Save changes"
                          : `Record ${formKind === "plant" ? "Plant" : "Plant group"}`}
                  </button>
                </div>
              </form>
            ) : null
          ) : detail.status === "loading" ? (
            <p role="status">Loading Plant detail…</p>
          ) : detail.status === "error" ? (
            <div className="notice notice--error" role="alert">
              <p>Florabase could not load this record.</p>
              <button
                type="button"
                onClick={() => {
                  if (selectedKey)
                    setDetail({ status: "loading", key: selectedKey });
                  setDetailAttempt((value) => value + 1);
                }}
              >
                Retry detail
              </button>
            </div>
          ) : selected ? (
            <div className="selected-seed selected-plant">
              <Detail
                record={selected}
                sowings={references.sowings}
                locations={references.locations}
                headingRef={detailHeading}
                onEventTargetRefresh={() =>
                  refreshEventTarget(selected.kind, selected.value.id)
                }
              />
              <div className="actions">
                {selected.kind === "group" &&
                  (selected.value.lifecycle === "active" ? (
                    <button
                      type="button"
                      onClick={(event) => {
                        extractionTrigger.current = event.currentTarget;
                        startExtraction(selected.value);
                      }}
                    >
                      Extract plant
                    </button>
                  ) : (
                    <p className="field-help">
                      Plants can only be extracted from an active group.
                    </p>
                  ))}
                <button
                  type="button"
                  onClick={() => {
                    startEdit(selected);
                  }}
                >
                  Edit {selected.kind === "plant" ? "Plant" : "Plant group"}
                </button>
              </div>
            </div>
          ) : (
            <div className="selected-seed seed-detail-empty">
              <h3>Select a Plant or group</h3>
              <p>Choose a compact row to see its full record.</p>
            </div>
          )}
        </section>
      </div>
    </section>
  );
}
