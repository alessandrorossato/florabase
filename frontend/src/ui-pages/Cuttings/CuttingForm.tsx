import { useId, useState, type ReactNode, type SyntheticEvent } from "react";
import type { components } from "../../api/schema";
import type { BotanicalIdentityResponse } from "../../botanical-identities/api";
import {
  FormActions,
  FormSection,
  PageHeader,
} from "../../components/ReferenceUI";
import { ErrorState, LoadingState, Page } from "../../components/WorkspaceUI";
import {
  closeCollectionPage,
  setRecordRoute,
} from "../../components/recordNavigation";
import type { GeographicPlaceResponse } from "../../geographic-places/api";
import type { LocationResponse, LocationUsageScope } from "../../locations/api";
import { OrderPicker } from "../../orders/OrderPicker";
import type { PlantGroupResponse, PlantResponse } from "../../plants/api";
import type { ProvenanceSiteResponse } from "../../provenance-sites/api";
import { PartialDateField } from "../../seed-lots/PartialDateField";
import { ReferencePicker } from "../../seed-lots/ReferencePicker";
import type { SupplierListResponse } from "../../suppliers/api";
import {
  attempts,
  cuttingError,
  lots,
  materialLabels,
  useSaveCutting,
  sourceLabels,
  useCuttingData,
  type CuttingQuantity,
  type LotWrite,
} from "./api";

type Schema = components["schemas"];
type Setup = Schema["AttemptSetup"];
interface ChoiceItem {
  id: string;
  label: string;
}
type QtyMode = "unknown" | "exact" | "approximate";

export function Choice<T extends string>({
  label,
  value,
  items,
  onChange,
  disabled = false,
}: {
  label: string;
  value: T;
  items: readonly { id: T; label: string }[];
  onChange: (value: T) => void;
  disabled?: boolean;
}) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <select
        id={id}
        value={value}
        onChange={(event) => {
          onChange(event.currentTarget.value as T);
        }}
        disabled={disabled}
      >
        {items.map((item) => (
          <option key={item.id} value={item.id}>
            {item.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export function TextField({
  label,
  value,
  onChange,
  maxLength = 255,
}: {
  label: string;
  value?: string | null;
  onChange: (value: string) => void;
  maxLength?: number;
}) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        value={value ?? ""}
        maxLength={maxLength}
        onChange={(event) => {
          onChange(event.currentTarget.value);
        }}
      />
    </div>
  );
}

export function NotesField({
  value,
  onChange,
}: {
  value?: string | null;
  onChange: (value: string) => void;
}) {
  const id = useId();
  return (
    <div className="field field--full">
      <label htmlFor={id}>Notes</label>
      <textarea
        id={id}
        maxLength={20_000}
        value={value ?? ""}
        onChange={(event) => {
          onChange(event.currentTarget.value);
        }}
      />
    </div>
  );
}

export function CountField({
  label,
  value,
  onChange,
  minimum = 0,
}: {
  label: string;
  value?: number | null;
  onChange: (value: number | null) => void;
  minimum?: number;
}) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="number"
        min={minimum}
        max={2_147_483_647}
        step={1}
        value={value ?? ""}
        onChange={(event) => {
          const next = event.currentTarget.valueAsNumber;
          onChange(Number.isFinite(next) ? next : null);
        }}
      />
    </div>
  );
}

export function QuantityField({
  label,
  value,
  onChange,
  minimum = 1,
}: {
  label: string;
  value?: CuttingQuantity | null;
  onChange: (value: CuttingQuantity | null) => void;
  minimum?: number;
}) {
  const mode: QtyMode = value
    ? value.is_approximate
      ? "approximate"
      : "exact"
    : "unknown";
  return (
    <fieldset className="form-section">
      <legend>{label}</legend>
      <div className="form-grid">
        <Choice
          label={`${label} precision`}
          value={mode}
          items={[
            { id: "unknown", label: "Unknown" },
            { id: "exact", label: "Exact count" },
            { id: "approximate", label: "Approximate count" },
          ]}
          onChange={(next: QtyMode) => {
            onChange(
              next === "unknown"
                ? null
                : {
                    value: value?.value ?? Math.max(1, minimum),
                    is_approximate: next === "approximate",
                  },
            );
          }}
        />
        {value && (
          <CountField
            label={`${label} count`}
            minimum={minimum}
            value={value.value}
            onChange={(next) => {
              onChange({ ...value, value: next ?? 0 });
            }}
          />
        )}
      </div>
    </fieldset>
  );
}

export function LocationField({
  scope,
  value,
  onChange,
  disabled = false,
}: {
  scope: LocationUsageScope;
  value?: string | null;
  onChange: (value: string | null) => void;
  disabled?: boolean;
}) {
  const [locations, retry] =
    useCuttingData<LocationResponse[]>("/api/v1/locations");
  if (locations.state === "error")
    return <ErrorState onRetry={retry}>Could not load locations.</ErrorState>;
  return (
    <ReferencePicker
      label="Location"
      value={value ?? ""}
      disabled={disabled || locations.state === "loading"}
      choices={
        locations.state === "ready"
          ? locations.value
              .filter((item) => item.usage_scopes.includes(scope))
              .map((item) => ({
                id: item.id,
                label: item.display_path,
                retired: item.retired_at != null,
              }))
          : []
      }
      onChange={(next) => {
        onChange(next || null);
      }}
      help="Choose a location with the matching usage scope."
    />
  );
}

export function AttemptSetupFields({
  setup,
  onChange,
  disabled,
  sameDate = false,
  showQuantity = true,
}: {
  setup: Setup;
  onChange: (value: Setup) => void;
  disabled: boolean;
  sameDate?: boolean;
  showQuantity?: boolean;
}) {
  const id = useId();
  return (
    <>
      <TextField
        label="Attempt label"
        value={setup.label}
        onChange={(label) => {
          onChange({ ...setup, label });
        }}
      />
      {!sameDate && (
        <PartialDateField
          id={`${id}-started`}
          label="Started on"
          value={setup.started_on ?? null}
          disabled={disabled}
          onChange={(started_on) => {
            onChange({ ...setup, started_on });
          }}
        />
      )}
      {showQuantity && (
        <QuantityField
          label="Starting quantity"
          value={setup.quantity}
          onChange={(quantity) => {
            onChange({ ...setup, quantity });
          }}
        />
      )}
      <LocationField
        scope="propagation_attempts"
        value={setup.location_id}
        disabled={disabled}
        onChange={(location_id) => {
          onChange({ ...setup, location_id });
        }}
      />
      <TextField
        label="Substrate"
        maxLength={500}
        value={setup.substrate}
        onChange={(substrate) => {
          onChange({ ...setup, substrate });
        }}
      />
      <TextField
        label="Hormone treatment"
        maxLength={500}
        value={setup.hormone_treatment}
        onChange={(hormone_treatment) => {
          onChange({ ...setup, hormone_treatment });
        }}
      />
      <TextField
        label="Container"
        maxLength={500}
        value={setup.container}
        onChange={(container) => {
          onChange({ ...setup, container });
        }}
      />
      <TextField
        label="Environment"
        maxLength={500}
        value={setup.environment}
        onChange={(environment) => {
          onChange({ ...setup, environment });
        }}
      />
      {(["temperature_min_c", "temperature_max_c"] as const).map((key) => (
        <div key={key} className="field">
          <label htmlFor={`${id}-${key}`}>
            {key === "temperature_min_c" ? "Minimum" : "Maximum"} temperature
            (°C)
          </label>
          <input
            id={`${id}-${key}`}
            type="number"
            min={-50}
            max={70}
            step={0.01}
            value={setup[key] ?? ""}
            onChange={(event) => {
              onChange({ ...setup, [key]: event.currentTarget.value || null });
            }}
          />
        </div>
      ))}
    </>
  );
}

const choices = <T extends string>(labels: Record<T, string>) =>
  (Object.keys(labels) as T[]).map((id) => ({ id, label: labels[id] }));

function MotherPicker({
  lot,
  change,
  disabled,
}: {
  lot: LotWrite;
  change: (lot: LotWrite) => void;
  disabled: boolean;
}) {
  const [kind, setKind] = useState<"plant" | "plant_group">(
    lot.mother_plant_group_id ? "plant_group" : "plant",
  );
  const [data, retry] = useCuttingData<(PlantResponse | PlantGroupResponse)[]>(
    kind === "plant" ? "/api/v1/plants" : "/api/v1/plant-groups",
  );
  return (
    <>
      <Choice
        label="Mother record type"
        value={kind}
        items={[
          { id: "plant", label: "Plant" },
          { id: "plant_group", label: "Plant group" },
        ]}
        disabled={disabled}
        onChange={(next: "plant" | "plant_group") => {
          setKind(next);
          change({
            ...lot,
            mother_plant_id: null,
            mother_plant_group_id: null,
          });
        }}
      />
      {data.state === "error" && (
        <ErrorState onRetry={retry}>
          Could not load mother specimens.
        </ErrorState>
      )}
      <ReferencePicker
        label="Mother specimen"
        disabled={disabled || data.state !== "ready"}
        value={
          (kind === "plant"
            ? lot.mother_plant_id
            : lot.mother_plant_group_id) ?? ""
        }
        choices={
          data.state === "ready"
            ? data.value
                .filter(
                  (item) =>
                    !["reversed", "reintegrated"].includes(item.lifecycle),
                )
                .map((item) => ({
                  id: item.id,
                  label: item.label ?? item.botanical_identity.display_label,
                }))
            : []
        }
        onChange={(id) => {
          const mother =
            data.state === "ready"
              ? data.value.find((item) => item.id === id)
              : undefined;
          change({
            ...lot,
            mother_plant_id: kind === "plant" ? id || null : null,
            mother_plant_group_id: kind === "plant_group" ? id || null : null,
            botanical_identity_id:
              mother?.botanical_identity_id ?? lot.botanical_identity_id,
          });
        }}
      />
    </>
  );
}

function ExternalOriginFields({
  lot,
  change,
  disabled,
}: {
  lot: LotWrite;
  change: (lot: LotWrite) => void;
  disabled: boolean;
}) {
  const [suppliers, retrySuppliers] =
    useCuttingData<SupplierListResponse[]>("/api/v1/suppliers");
  const [places, retryPlaces] = useCuttingData<GeographicPlaceResponse[]>(
    "/api/v1/geographic-places",
  );
  const [sites, retrySites] = useCuttingData<ProvenanceSiteResponse[]>(
    "/api/v1/provenance-sites",
  );
  function picker(
    label: string,
    items: ChoiceItem[],
    key: "supplier_id" | "material_provenance_place_id" | "provenance_site_id",
  ) {
    return (
      <ReferencePicker
        label={label}
        choices={items}
        value={lot[key] ?? ""}
        onChange={(value) => {
          change({ ...lot, [key]: value || null });
        }}
        disabled={disabled}
      />
    );
  }
  return (
    <>
      {suppliers.state === "error" && (
        <ErrorState onRetry={retrySuppliers}>
          Could not load suppliers.
        </ErrorState>
      )}
      {picker(
        "Supplier",
        suppliers.state === "ready"
          ? suppliers.value.map((item) => ({ id: item.id, label: item.name }))
          : [],
        "supplier_id",
      )}
      {lot.source_kind === "purchased" && (
        <OrderPicker
          value={lot.order_id ?? ""}
          disabled={disabled}
          supplierId={lot.supplier_id ?? ""}
          onChange={(orderId) => {
            change({ ...lot, order_id: orderId || null });
          }}
          independentFields={
            <p className="field-help">
              Link the purchase transaction for this lot.
            </p>
          }
        />
      )}
      {places.state === "error" && (
        <ErrorState onRetry={retryPlaces}>
          Could not load geographic places.
        </ErrorState>
      )}
      {picker(
        "Geographic place",
        places.state === "ready"
          ? places.value.map((item) => ({
              id: item.id,
              label: item.display_path,
            }))
          : [],
        "material_provenance_place_id",
      )}
      {sites.state === "error" && (
        <ErrorState onRetry={retrySites}>
          Could not load provenance sites.
        </ErrorState>
      )}
      {picker(
        "Provenance site",
        sites.state === "ready"
          ? sites.value.map((item) => ({ id: item.id, label: item.name }))
          : [],
        "provenance_site_id",
      )}
    </>
  );
}

export function LotFields({
  lot,
  change,
  disabled,
  children,
}: {
  lot: LotWrite;
  change: (lot: LotWrite) => void;
  disabled: boolean;
  children: ReactNode;
}) {
  const [identities, retryIdentities] = useCuttingData<
    BotanicalIdentityResponse[]
  >("/api/v1/botanical-identities");
  const knownMother = Boolean(lot.mother_plant_id ?? lot.mother_plant_group_id);

  return (
    <>
      {identities.state === "loading" && (
        <LoadingState>Loading botanical identities…</LoadingState>
      )}
      {identities.state === "error" && (
        <ErrorState onRetry={retryIdentities}>
          Could not load botanical identities.
        </ErrorState>
      )}
      <FormSection title="Source and material">
        <Choice
          label="Material type"
          items={choices(materialLabels)}
          value={lot.material_type}
          onChange={(material_type) => {
            change({ ...lot, material_type });
          }}
        />
        <Choice
          label="Source"
          items={choices(sourceLabels)}
          value={lot.source_kind}
          onChange={(source_kind) => {
            change({
              ...lot,
              source_kind,
              source_detail: null,
              mother_plant_id: null,
              mother_plant_group_id: null,
              supplier_id: null,
              order_id: null,
              material_provenance_place_id: null,
              provenance_site_id: null,
            });
          }}
        />
        {lot.source_kind === "collection_produced" ? (
          <MotherPicker lot={lot} change={change} disabled={disabled} />
        ) : (
          <ExternalOriginFields lot={lot} change={change} disabled={disabled} />
        )}
        {lot.source_kind === "other" && (
          <TextField
            label="Source detail"
            value={lot.source_detail}
            onChange={(source_detail) => {
              change({ ...lot, source_detail });
            }}
          />
        )}
        <ReferencePicker
          label="Botanical identity"
          required={!knownMother}
          value={lot.botanical_identity_id ?? ""}
          disabled={disabled || identities.state !== "ready"}
          choices={
            identities.state === "ready"
              ? identities.value.map((item) => ({
                  id: item.id,
                  label: item.display_label,
                  scientificName: item.scientific_name,
                }))
              : []
          }
          onChange={(value) => {
            change({ ...lot, botanical_identity_id: value || null });
          }}
          help={
            knownMother && !lot.botanical_identity_id
              ? "Defaults to the mother specimen’s identity."
              : undefined
          }
        />
        <TextField
          label="Material lot label"
          value={lot.label}
          onChange={(label) => {
            change({ ...lot, label });
          }}
        />
        <PartialDateField
          id="cuttings-taken"
          label="Taken or acquired on"
          value={lot.taken_on ?? null}
          disabled={disabled}
          onChange={(taken_on) => {
            change({ ...lot, taken_on });
          }}
        />
        {children}
        <LocationField
          scope="vegetative_lots"
          value={lot.location_id}
          disabled={disabled}
          onChange={(location_id) => {
            change({ ...lot, location_id });
          }}
        />
        <NotesField
          value={lot.notes}
          onChange={(notes) => {
            change({ ...lot, notes });
          }}
        />
      </FormSection>
    </>
  );
}

export function CuttingForm({
  token,
  identityId,
  sourceId,
  sourceType,
}: {
  token: string;
  identityId?: string;
  sourceId?: string;
  sourceType?: "plant" | "plant_group";
}) {
  const [lot, setLot] = useState<LotWrite>({
    botanical_identity_id: identityId,
    material_type: "stem_cutting",
    source_kind: sourceId ? "collection_produced" : "unknown",
    mother_plant_id: sourceType === "plant" ? sourceId : undefined,
    mother_plant_group_id: sourceType === "plant_group" ? sourceId : undefined,
  });
  const [immediate, setImmediate] = useState(Boolean(sourceId));
  const [sameDate, setSameDate] = useState(true);
  const [useAll, setUseAll] = useState(true);
  const [setup, setSetup] = useState<Setup>({});
  const [remainder, setRemainder] = useState<CuttingQuantity | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const saveCutting = useSaveCutting(token);
  const knownMother = Boolean(lot.mother_plant_id ?? lot.mother_plant_group_id);
  const useExactLotCount =
    useAll && lot.initial_quantity?.is_approximate === false;

  async function submit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (pending) return;
    if (!lot.botanical_identity_id && !knownMother) {
      setError("Select a botanical identity or a mother specimen.");
      return;
    }
    setPending(true);
    setError("");
    try {
      if (immediate) {
        const result = await saveCutting<Schema["AttemptTransitionResponse"]>(
          `${attempts}/fast-create`,
          {
            vegetative_lot: lot,
            source_adjustment: useAll
              ? { mode: "use_all" }
              : { mode: "partial", resulting_quantity: remainder },
            propagation_attempt: {
              ...setup,
              started_on: sameDate
                ? (lot.taken_on ?? null)
                : (setup.started_on ?? null),
              quantity: useExactLotCount
                ? lot.initial_quantity
                : (setup.quantity ?? null),
            },
          },
        );
        setRecordRoute(
          `#/cuttings/attempts/${result.propagation_attempt.id}`,
          true,
        );
      } else {
        const result = await saveCutting<Schema["VegetativeLotResponse"]>(
          lots,
          lot,
        );
        setRecordRoute(`#/cuttings/lots/${result.id}`, true);
      }
    } catch (reason) {
      setError(cuttingError(reason));
    } finally {
      setPending(false);
    }
  }
  return (
    <Page titleId="cuttings-create-title">
      <PageHeader
        titleId="cuttings-create-title"
        title={sourceId ? "Take cuttings" : "Take or add cuttings"}
        eyebrow="Cuttings"
      />
      <form
        onSubmit={(event) => {
          void submit(event);
        }}
      >
        <fieldset disabled={pending} className="form-section">
          <LotFields lot={lot} change={setLot} disabled={pending}>
            <QuantityField
              label="Initial lot quantity"
              value={lot.initial_quantity}
              onChange={(initial_quantity) => {
                setLot({ ...lot, initial_quantity });
              }}
            />
          </LotFields>
          <FormSection title="Rooting setup">
            <label>
              <input
                type="checkbox"
                checked={immediate}
                onChange={(event) => {
                  setImmediate(event.currentTarget.checked);
                }}
              />{" "}
              Start rooting attempt immediately
            </label>
            {immediate && (
              <>
                <label>
                  <input
                    type="checkbox"
                    checked={useAll}
                    onChange={(event) => {
                      setUseAll(event.currentTarget.checked);
                    }}
                  />{" "}
                  Use all cuttings in this attempt
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={sameDate}
                    onChange={(event) => {
                      setSameDate(event.currentTarget.checked);
                    }}
                  />{" "}
                  Use the taken or acquired date
                </label>
                {!useAll && lot.initial_quantity?.is_approximate && (
                  <QuantityField
                    label="Confirmed remaining quantity"
                    value={remainder}
                    onChange={setRemainder}
                  />
                )}
                <AttemptSetupFields
                  setup={setup}
                  showQuantity={!useExactLotCount}
                  onChange={setSetup}
                  disabled={pending}
                  sameDate={sameDate}
                />
              </>
            )}
          </FormSection>
        </fieldset>
        {error && (
          <p className="notice notice--error" role="alert">
            {error}
          </p>
        )}
        <FormActions>
          <button
            className="button--secondary"
            type="button"
            disabled={pending}
            onClick={() => {
              if (
                window.confirm("Leave this form and discard unsaved changes?")
              )
                closeCollectionPage("#/cuttings");
            }}
          >
            Cancel
          </button>
          <button type="submit" disabled={pending}>
            {pending ? "Saving…" : "Save cuttings"}
          </button>
        </FormActions>
      </form>
    </Page>
  );
}
