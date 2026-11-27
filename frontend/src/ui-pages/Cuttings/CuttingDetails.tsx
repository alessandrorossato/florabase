import { useEffect, useRef, useState, type ReactNode } from "react";
import type { components } from "../../api/schema";
import {
  Breadcrumbs,
  DetailHeader,
  DetailPage,
  DetailTabs,
  RecordChildCard,
  RecordDescendants,
  RecordOverview,
  SpecimenLabel,
  SpecimenPlate,
} from "../../components/CollectionUI";
import { RecordAlmanac } from "../../timeline/RecordAlmanac";
import { setRecordRoute } from "../../components/recordNavigation";
import {
  FormActions,
  FormSection,
  OverflowMenu,
} from "../../components/ReferenceUI";
import { TaskDialog } from "../../components/TaskDialog";
import {
  EmptyState,
  ErrorState,
  LifecycleStatus,
  LoadingState,
  Page,
} from "../../components/WorkspaceUI";
import { LineageStrip } from "../../lineage/LineageStrip";
import { formatPartialDate } from "../../events/eventData";
import { LineagePanel } from "../../lineage/LineagePanel";
import { RecordVisual } from "../../photos/RecordVisual";
import { PhotosSection } from "../../photos/PhotosSection";
import type { PrimaryPhoto } from "../../photos/api";
import { PartialDateField } from "../../seed-lots/PartialDateField";
import {
  AttemptSetupFields,
  Choice,
  CountField,
  LocationField,
  LotFields,
  NotesField,
  QuantityField,
  TextField,
} from "./CuttingForm";
import {
  attempts,
  countLabel,
  cuttingError,
  lots,
  materialLabels,
  rootingLabel,
  useSaveCutting,
  sourceLabels,
  useCuttingData,
  type Attempt,
  type AttemptDetail,
  type AttemptSummary,
  type AttemptWrite,
  type Lot,
  type LotDetail,
  type LotWrite,
  type ReceiptEligibility,
  type RootingObservation,
} from "./api";

type Schema = components["schemas"];
type DetailTarget = "vegetative_lot" | "propagation_attempt";
type DialogMode =
  | { type: "edit" | "establish" }
  | { type: "observe"; observation?: RootingObservation }
  | { type: "undo"; receipt: string };

/** The record's own primary photo, with the lot's and the mother's as inherited fallbacks. */
function useCuttingPhotos(target: DetailTarget, id: string, lot: Lot) {
  const [primary, reloadPhoto] = useCuttingData<PrimaryPhoto | null>(
    `/api/v1/collection-records/${target}/${id}/primary-photo`,
  );
  const [lotPhoto] = useCuttingData<PrimaryPhoto | null>(
    target === "propagation_attempt"
      ? `/api/v1/collection-records/vegetative_lot/${lot.id}/primary-photo`
      : "",
  );
  const motherId = lot.mother_plant_id ?? lot.mother_plant_group_id;
  const motherKind = lot.mother_plant_id ? "plant" : "plant_group";
  const [motherPhoto] = useCuttingData<PrimaryPhoto | null>(
    motherId
      ? `/api/v1/collection-records/${motherKind}/${motherId}/primary-photo`
      : "",
  );
  return {
    own: primary.state === "ready" ? primary.value : null,
    inherited: [
      lotPhoto.state === "ready" ? lotPhoto.value : null,
      motherPhoto.state === "ready" ? motherPhoto.value : null,
    ],
    reloadPhoto,
  };
}

function CuttingPlate({
  photos,
  label,
  lot,
}: {
  photos: ReturnType<typeof useCuttingPhotos>;
  label: string;
  lot: Lot;
}) {
  return (
    <SpecimenPlate>
      <RecordVisual
        photo={photos.own}
        fallbackPhotos={photos.inherited}
        showSource
        kind="cutting"
        label={label}
        identity={{ id: lot.botanical_identity_id, display_label: label }}
      />
    </SpecimenPlate>
  );
}

const lifecycleLabels: Record<string, string> = {
  active: "Active",
  exhausted: "Exhausted",
  completed: "Completed",
  failed: "Failed",
  abandoned: "Abandoned",
  reversed: "Reversed",
};
function lifecycleLabel(state: string) {
  return (
    lifecycleLabels[state] ??
    state.charAt(0).toUpperCase() + state.slice(1).replaceAll("_", " ")
  );
}

/** Pages within a cutting record, kept in the route and synced on later route changes. */
function readRouteTab<T extends string>(tabs: readonly T[]): T {
  const param = new URLSearchParams(
    window.location.hash.split("?", 2)[1] ?? "",
  ).get("tab");
  return tabs.find((item) => item === param) ?? tabs[0];
}

function useRecordTab<T extends string>(base: string, tabs: readonly T[]) {
  const routeTab = readRouteTab(tabs);
  const routeKey = `${base}:${routeTab}`;
  const [tab, setTab] = useState<T>(routeTab);
  const [lastRouteKey, setLastRouteKey] = useState(routeKey);
  if (lastRouteKey !== routeKey) {
    setLastRouteKey(routeKey);
    setTab(routeTab);
  }
  useEffect(() => {
    const sync = () => {
      const next = readRouteTab(tabs);
      setLastRouteKey(`${base}:${next}`);
      setTab(next);
    };
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    return () => {
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("popstate", sync);
    };
  }, [base, tabs]);
  function select(next: T) {
    setTab(next);
    setLastRouteKey(`${base}:${next}`);
    window.history.replaceState(
      window.history.state,
      "",
      `${base}${next === tabs[0] ? "" : `?tab=${next}`}`,
    );
  }
  return [tab, select] as const;
}

function PlanLink({ kind, id }: { kind: DetailTarget; id: string }) {
  return (
    <a
      className="button-link button--secondary"
      href={`#/schedule?target_kind=${kind}&target_id=${id}&action=create`}
    >
      Schedule a rooting check
    </a>
  );
}

function displayAttempt(attempt: Attempt) {
  return attempt.label ?? attempt.substrate ?? "Rooting attempt";
}

function LotFacts({ lot }: { lot: Lot }) {
  return (
    <dl className="record-facts">
      <div>
        <dt>Source</dt>
        <dd>
          {sourceLabels[lot.source_kind]}
          {lot.source_detail ? ` · ${lot.source_detail}` : ""}
        </dd>
      </div>
      <div>
        <dt>Initial quantity</dt>
        <dd>{countLabel(lot.initial_quantity)}</dd>
      </div>
      {lot.supplier_id && (
        <div>
          <dt>Supplier</dt>
          <dd>
            <a href={`#/suppliers/${lot.supplier_id}`}>Open supplier</a>
          </dd>
        </div>
      )}
      {lot.order_id && (
        <div>
          <dt>Purchase order</dt>
          <dd>
            <a href={`#/orders/${lot.order_id}`}>Open purchase order</a>
          </dd>
        </div>
      )}
      {lot.material_provenance_place_id && (
        <div>
          <dt>Geographic place</dt>
          <dd>
            <a href={`#/geography?place=${lot.material_provenance_place_id}`}>
              Open geographic place
            </a>
          </dd>
        </div>
      )}
      {lot.provenance_site_id && (
        <div>
          <dt>Provenance</dt>
          <dd>
            <a href={`#/geography/${lot.provenance_site_id}`}>
              Open collection site
            </a>
          </dd>
        </div>
      )}
      {lot.notes && (
        <div>
          <dt>Notes</dt>
          <dd>{lot.notes}</dd>
        </div>
      )}
    </dl>
  );
}

function IdentityLink({ id }: { id: string }) {
  const [data] = useCuttingData<Schema["BotanicalIdentityResponse"]>(
    `/api/v1/botanical-identities/${id}`,
  );
  return (
    <a href={`#/identities/${id}`}>
      {data.state === "ready"
        ? data.value.display_label
        : "Open botanical identity"}
    </a>
  );
}

/** Drops ?action=edit once the dialog closes, so a reload does not reopen it. */
function clearEditRequest() {
  if (!editRequested()) return;
  const [path, query = ""] = window.location.hash.split("?", 2);
  const params = new URLSearchParams(query);
  params.delete("action");
  const next = params.toString();
  window.history.replaceState(
    window.history.state,
    "",
    `${window.location.pathname}${window.location.search}${path}${next ? `?${next}` : ""}`,
  );
}

function editRequested() {
  return (
    new URLSearchParams(window.location.hash.split("?", 2)[1] ?? "").get(
      "action",
    ) === "edit"
  );
}

export function LotPage({ id, token }: { id: string; token: string }) {
  const [data, retry] = useCuttingData<LotDetail>(`${lots}/${id}`, true);
  // Directory rows open Edit through ?action=edit, like the other collection directories.
  const [dialog, setDialog] = useState<"start" | "edit" | undefined>(
    editRequested() ? "edit" : undefined,
  );
  const lot = data.state === "ready" ? data.value : undefined;
  return (
    <Page titleId="cutting-lot-title" className="cuttings-record">
      {data.state === "loading" && (
        <>
          <h2 id="cutting-lot-title" className="sr-only">
            Vegetative lot
          </h2>
          <LoadingState>Loading vegetative lot…</LoadingState>
        </>
      )}
      {data.state === "error" && (
        <>
          <h2 id="cutting-lot-title">Vegetative lot</h2>
          <ErrorState onRetry={retry}>{cuttingError(data.error)}</ErrorState>
        </>
      )}
      {lot && (
        <LotRecord
          lot={lot}
          id={id}
          onEdit={() => {
            setDialog("edit");
          }}
          onStart={() => {
            setDialog("start");
          }}
        />
      )}
      {lot && dialog === "edit" && lot.lifecycle !== "reversed" && (
        <LotEditDialog
          lot={lot}
          lifecycle={lot.lifecycle}
          token={token}
          close={() => {
            clearEditRequest();
            setDialog(undefined);
          }}
          refresh={retry}
        />
      )}
      {lot && dialog === "start" && (
        <StartDialog
          lot={lot}
          token={token}
          close={() => {
            setDialog(undefined);
          }}
        />
      )}
    </Page>
  );
}

const lotTabs = ["overview", "attempts", "photos", "lineage"] as const;

function LotRecord({
  lot,
  id,
  onEdit,
  onStart,
}: {
  lot: LotDetail;
  id: string;
  onEdit: () => void;
  onStart: () => void;
}) {
  const [tab, setTab] = useRecordTab(`#/cuttings/lots/${id}`, lotTabs);
  const label = lot.label ?? "Unlabelled vegetative lot";
  const photos = useCuttingPhotos("vegetative_lot", id, lot);
  return (
    <DetailPage as="div" className="cutting-detail">
      <Breadcrumbs
        items={[
          { label: "Collection", href: "#/dashboard" },
          { label: "Cuttings", href: "#/cuttings" },
          { label },
        ]}
      />
      <DetailHeader
        headingLevel={2}
        titleId="cutting-lot-title"
        eyebrow="Vegetative lot"
        title={label}
        plate={<CuttingPlate photos={photos} label={label} lot={lot} />}
        label={
          <SpecimenLabel
            kind="Cuttings"
            name="Current material"
            rows={[
              {
                label: "Remaining",
                value: countLabel(lot.quantity),
                emphasis: true,
              },
              { label: "Material", value: materialLabels[lot.material_type] },
              {
                label: "Taken on",
                value: formatPartialDate(lot.taken_on ?? null),
              },
              {
                label: "Location",
                wide: true,
                value: lot.location_id ? (
                  <a href={`#/locations/${lot.location_id}`}>
                    Open holding location
                  </a>
                ) : (
                  "Not recorded"
                ),
              },
            ]}
          />
        }
        secondary={<IdentityLink id={lot.botanical_identity_id} />}
        status={
          <LifecycleStatus state={lot.lifecycle}>
            {lifecycleLabel(lot.lifecycle)}
          </LifecycleStatus>
        }
        lineage={
          <LineageStrip
            key={lot.updated_at}
            kind="vegetative-lots"
            id={id}
            current="This Vegetative lot"
            currentKind="vegetative_lot"
            fullHref={`#/cuttings/lots/${id}?tab=lineage`}
            onLineageTab={tab === "lineage"}
            onFull={(event) => {
              event.preventDefault();
              setTab("lineage");
            }}
          />
        }
        primaryActions={
          lot.lifecycle === "active" ? (
            <button type="button" onClick={onStart}>
              Start rooting attempt
            </button>
          ) : undefined
        }
        editLabel="Edit vegetative lot"
        onEdit={lot.lifecycle !== "reversed" ? onEdit : undefined}
        overflow={
          lot.lifecycle === "active" ? (
            <OverflowMenu ariaLabel="More vegetative lot actions">
              <PlanLink kind="vegetative_lot" id={id} />
            </OverflowMenu>
          ) : undefined
        }
      />
      <DetailTabs
        tabs={[
          { id: "overview", label: "Overview" },
          { id: "attempts", label: "Rooting attempts" },
          { id: "photos", label: "Photos" },
          { id: "lineage", label: "Lineage" },
        ]}
        selected={tab}
        onSelect={setTab}
      />
      {tab === "overview" && (
        <div
          id="panel-overview"
          role="tabpanel"
          aria-labelledby="tab-overview"
          className="detail-tab-panel"
        >
          <RecordOverview
            facts={
              <>
                <section aria-labelledby="cutting-lot-facts">
                  <h3 id="cutting-lot-facts">Material and source</h3>
                  <LotFacts lot={lot} />
                </section>
                <RecordDescendants
                  headingId="cutting-lot-descendants"
                  items={[
                    {
                      label: `${String(lot.attempts.length)} ${lot.attempts.length === 1 ? "rooting attempt" : "rooting attempts"}`,
                      href: `#/cuttings/lots/${id}?tab=attempts`,
                      onClick: (event) => {
                        event.preventDefault();
                        setTab("attempts");
                      },
                    },
                  ]}
                  lineageHref={`#/cuttings/lots/${id}?tab=lineage`}
                  onOpenLineage={(event) => {
                    event.preventDefault();
                    setTab("lineage");
                  }}
                />
              </>
            }
            almanac={
              <RecordAlmanac
                kind="vegetative_lot"
                id={id}
                current={lot.lifecycle === "active"}
                recordedElsewhere={
                  <>
                    {lot.attempts.length > 0
                      ? `${String(lot.attempts.length)} ${lot.attempts.length === 1 ? "rooting attempt" : "rooting attempts"} recorded. `
                      : "No rooting attempts recorded yet. "}
                    <a
                      href={`#/cuttings/lots/${id}?tab=attempts`}
                      onClick={(event) => {
                        event.preventDefault();
                        setTab("attempts");
                      }}
                    >
                      Open Rooting attempts
                    </a>
                  </>
                }
              />
            }
          />
        </div>
      )}
      {tab === "attempts" && (
        <div
          id="panel-attempts"
          role="tabpanel"
          aria-labelledby="tab-attempts"
          className="detail-tab-panel"
        >
          <section aria-labelledby="cutting-lot-attempts">
            <h3 id="cutting-lot-attempts">Rooting attempts</h3>
            {lot.attempts.length ? (
              <div className="record-child-grid">
                {lot.attempts.map((attempt) => (
                  <RecordChildCard
                    key={attempt.id}
                    kind="Rooting attempt"
                    href={`#/cuttings/attempts/${attempt.id}`}
                    title={displayAttempt(attempt)}
                    status={attempt.lifecycle}
                    statusLabel={lifecycleLabel(attempt.lifecycle)}
                    meta={<p>{rootingLabel(attempt)}</p>}
                  />
                ))}
              </div>
            ) : (
              <EmptyState>
                No attempts have been started for this lot.
              </EmptyState>
            )}
          </section>
        </div>
      )}
      {tab === "photos" && (
        <div
          id="panel-photos"
          role="tabpanel"
          aria-labelledby="tab-photos"
          className="detail-tab-panel"
        >
          <PhotosSection
            target="vegetative_lot"
            targetId={id}
            targetLabel={label}
            primaryPhoto={photos.own}
            onPrimaryChanged={photos.reloadPhoto}
          />
        </div>
      )}
      {tab === "lineage" && (
        <div
          id="panel-lineage"
          role="tabpanel"
          aria-labelledby="tab-lineage"
          className="detail-tab-panel"
        >
          <LineagePanel kind="vegetative-lots" id={id} />
        </div>
      )}
    </DetailPage>
  );
}

function SaveDialog({
  title,
  label,
  onSave,
  close,
  children,
}: {
  title: string;
  label: string;
  onSave: () => Promise<void>;
  close: () => void;
  children: ReactNode;
}) {
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState("");
  function dismiss() {
    if (!busy && (!dirty || window.confirm("Discard unsaved changes?")))
      close();
  }
  return (
    <TaskDialog title={title} onClose={dismiss}>
      <h3>{title}</h3>
      <form
        onChange={() => {
          setDirty(true);
        }}
        onKeyDownCapture={(event) => {
          if (
            event.key === "Enter" &&
            event.target instanceof Element &&
            event.target.matches('input[role="combobox"][aria-expanded="true"]')
          )
            setDirty(true);
        }}
        onClickCapture={(event) => {
          if (
            event.target instanceof Element &&
            event.target.closest("[role='option']")
          )
            setDirty(true);
        }}
        onSubmit={(event) => {
          event.preventDefault();
          if (busy) return;
          setBusy(true);
          setError("");
          void onSave()
            .then(close, (reason: unknown) => {
              setError(cuttingError(reason));
            })
            .finally(() => {
              setBusy(false);
            });
        }}
      >
        <FormActions>
          <button
            type="button"
            className="button--secondary"
            onClick={dismiss}
            disabled={busy}
          >
            Cancel
          </button>
          <button type="submit" disabled={busy}>
            {busy ? "Saving…" : label}
          </button>
        </FormActions>
        <fieldset disabled={busy} className="form-section">
          {children}
        </fieldset>
        {error && (
          <p role="alert" className="notice notice--error">
            {error}
          </p>
        )}
      </form>
    </TaskDialog>
  );
}

function LotEditDialog({
  lot,
  lifecycle,
  token,
  close,
  refresh,
}: {
  lot: Lot;
  lifecycle: Schema["VegetativeLotUpdate"]["lifecycle"];
  token: string;
  close: () => void;
  refresh: () => void;
}) {
  const saveCutting = useSaveCutting(token);
  const [details, setDetails] = useState<LotWrite>({
    botanical_identity_id: lot.botanical_identity_id,
    label: lot.label,
    material_type: lot.material_type,
    source_kind: lot.source_kind,
    source_detail: lot.source_detail,
    mother_plant_id: lot.mother_plant_id,
    mother_plant_group_id: lot.mother_plant_group_id,
    supplier_id: lot.supplier_id,
    order_id: lot.order_id,
    material_provenance_place_id: lot.material_provenance_place_id,
    provenance_site_id: lot.provenance_site_id,
    location_id: lot.location_id,
    taken_on: lot.taken_on,
    notes: lot.notes,
  });
  const [status, setStatus] = useState(lifecycle);
  const [quantity, setQuantity] = useState(lot.quantity);
  return (
    <SaveDialog
      title="Edit vegetative lot"
      label="Save lot"
      close={close}
      onSave={async () => {
        const payload: Schema["VegetativeLotUpdate"] = {
          ...details,
          expected_updated_at: lot.updated_at,
          lifecycle: status,
          quantity,
        };
        await saveCutting(`${lots}/${lot.id}`, payload, "PUT");
        refresh();
      }}
    >
      <LotFields lot={details} change={setDetails} disabled={false}>
        <Choice
          label="Lot status"
          value={status}
          onChange={setStatus}
          items={[
            { id: "active", label: "Active" },
            { id: "exhausted", label: "Exhausted" },
            { id: "discarded", label: "Discarded" },
            { id: "lost", label: "Lost" },
          ]}
        />
        <QuantityField
          label="Remaining quantity"
          value={quantity}
          onChange={setQuantity}
          minimum={status === "exhausted" ? 0 : 1}
        />
      </LotFields>
    </SaveDialog>
  );
}

function StartDialog({
  lot,
  token,
  close,
}: {
  lot: Lot;
  token: string;
  close: () => void;
}) {
  const saveCutting = useSaveCutting(token);
  const [setup, setSetup] = useState<AttemptWrite["propagation_attempt"]>({
    started_on: lot.taken_on,
  });
  const [mode, setMode] =
    useState<AttemptWrite["source_adjustment"]["mode"]>("use_all");
  const [remainder, setRemainder] = useState<Lot["quantity"]>(null);
  const useExactLotCount =
    mode === "use_all" && lot.quantity?.is_approximate === false;
  return (
    <SaveDialog
      title="Start rooting attempt"
      label="Start attempt"
      close={close}
      onSave={async () => {
        const result = await saveCutting<Schema["AttemptTransitionResponse"]>(
          `${lots}/${lot.id}/propagation-attempts`,
          {
            source_adjustment: {
              mode,
              ...(mode === "partial" ? { resulting_quantity: remainder } : {}),
            },
            propagation_attempt: {
              ...setup,
              quantity: useExactLotCount
                ? lot.quantity
                : (setup.quantity ?? null),
            },
          },
        );
        setRecordRoute(`#/cuttings/attempts/${result.propagation_attempt.id}`);
      }}
    >
      <Choice
        label="Material use"
        value={mode}
        items={[
          { id: "use_all", label: "Use all cuttings" },
          { id: "partial", label: "Use part of the lot" },
          { id: "none", label: "Leave stock unchanged" },
        ]}
        onChange={setMode}
      />
      {mode === "partial" && lot.quantity?.is_approximate && (
        <QuantityField
          label="Confirmed remaining quantity"
          value={remainder}
          onChange={setRemainder}
        />
      )}
      <FormSection title="Rooting setup">
        <AttemptSetupFields
          setup={setup}
          onChange={setSetup}
          disabled={false}
          showQuantity={!useExactLotCount}
        />
      </FormSection>
    </SaveDialog>
  );
}

function ObservationDialog({
  attempt,
  observation,
  token,
  close,
  refresh,
}: {
  attempt: AttemptDetail;
  observation?: RootingObservation;
  token: string;
  close: () => void;
  refresh: () => void;
}) {
  const saveCutting = useSaveCutting(token);
  const [values, setValues] = useState<Schema["RootingObservationWrite"]>({
    stage: observation?.stage ?? "inspection",
    observed_on: observation?.observed_on,
    rooted_count: observation?.rooted_count,
    notes: observation?.notes,
  });
  return (
    <SaveDialog
      title={
        observation ? "Correct rooting observation" : "Log rooting observation"
      }
      label="Save observation"
      close={close}
      onSave={async () => {
        const path = `${attempts}/${attempt.id}/observations`;
        await saveCutting(
          observation ? `${path}/${observation.id}` : path,
          values,
          observation ? "PUT" : "POST",
        );
        refresh();
      }}
    >
      <FormSection title="Rooting check">
        <Choice
          label="Stage"
          value={values.stage}
          items={[
            { id: "inspection", label: "Inspection" },
            { id: "callus", label: "Callus" },
            { id: "root_initials", label: "Root initials" },
            { id: "rooted", label: "Rooted" },
            { id: "loss", label: "Loss" },
          ]}
          onChange={(stage) => {
            setValues({ ...values, stage });
          }}
        />
        <PartialDateField
          id="rooting-observed"
          label="Observed on"
          value={values.observed_on ?? null}
          disabled={false}
          onChange={(observed_on) => {
            setValues({ ...values, observed_on });
          }}
        />
        <CountField
          label="Observed rooted count"
          value={values.rooted_count}
          onChange={(rooted_count) => {
            setValues({ ...values, rooted_count });
          }}
        />
        <NotesField
          value={values.notes}
          onChange={(notes) => {
            setValues({ ...values, notes });
          }}
        />
      </FormSection>
    </SaveDialog>
  );
}

function EstablishDialog({
  attempt,
  token,
  close,
  refresh,
}: {
  attempt: AttemptDetail;
  token: string;
  close: () => void;
  refresh: () => void;
}) {
  const saveCutting = useSaveCutting(token);
  const [kind, setKind] = useState<"plant" | "plant_group">("plant");
  const [values, setValues] = useState<Schema["EstablishPlantGroup"]>({
    resulting_attempt_lifecycle: "active",
  });
  return (
    <SaveDialog
      title="Establish Plant or Plant group"
      label="Establish"
      close={close}
      onSave={async () => {
        const { quantity, ...plant } = values;
        await saveCutting(
          `${attempts}/${attempt.id}/${kind === "plant" ? "plants" : "plant-groups"}`,
          kind === "plant" ? plant : { ...plant, quantity },
        );
        refresh();
      }}
    >
      <FormSection title="Established specimen">
        <Choice
          label="Result"
          value={kind}
          items={[
            { id: "plant", label: "Individual Plant" },
            { id: "plant_group", label: "Plant group" },
          ]}
          onChange={setKind}
        />
        <TextField
          label="Label"
          value={values.label}
          onChange={(label) => {
            setValues({ ...values, label });
          }}
        />
        {kind === "plant_group" && (
          <QuantityField
            label="Group quantity"
            value={values.quantity}
            onChange={(quantity) => {
              setValues({ ...values, quantity });
            }}
          />
        )}
        <PartialDateField
          id="cutting-established"
          label="Collection entry date"
          value={values.collection_entry_date ?? null}
          disabled={false}
          onChange={(collection_entry_date) => {
            setValues({ ...values, collection_entry_date });
          }}
        />
        <LocationField
          scope="plants"
          value={values.location_id}
          onChange={(location_id) => {
            setValues({ ...values, location_id });
          }}
        />
        <Choice
          label="Attempt after establishment"
          value={values.resulting_attempt_lifecycle}
          items={[
            { id: "active", label: "Keep attempt active" },
            { id: "completed", label: "Mark completed" },
            { id: "abandoned", label: "Mark abandoned" },
          ]}
          onChange={(resulting_attempt_lifecycle) => {
            setValues({ ...values, resulting_attempt_lifecycle });
          }}
        />
        <NotesField
          value={values.notes}
          onChange={(notes) => {
            setValues({ ...values, notes });
          }}
        />
      </FormSection>
    </SaveDialog>
  );
}

function AttemptEditDialog({
  attempt,
  token,
  close,
  refresh,
}: {
  attempt: AttemptDetail;
  token: string;
  close: () => void;
  refresh: () => void;
}) {
  const saveCutting = useSaveCutting(token);
  const [setup, setSetup] = useState<Schema["AttemptSetup"]>({
    label: attempt.label,
    quantity: attempt.quantity,
    started_on: attempt.started_on,
    location_id: attempt.location_id,
    substrate: attempt.substrate,
    hormone_treatment: attempt.hormone_treatment,
    container: attempt.container,
    environment: attempt.environment,
    notes: attempt.notes,
    temperature_min_c: attempt.temperature_min_c,
    temperature_max_c: attempt.temperature_max_c,
  });
  const [lifecycle, setLifecycle] = useState<
    Schema["PropagationAttemptUpdate"]["lifecycle"]
  >(attempt.lifecycle === "reversed" ? "active" : attempt.lifecycle);
  const [rooted, setRooted] = useState(attempt.rooted_count ?? null);
  const [ended, setEnded] = useState(attempt.ended_on ?? null);
  return (
    <SaveDialog
      title="Edit rooting attempt"
      label="Save attempt"
      close={close}
      onSave={async () => {
        await saveCutting(
          `${attempts}/${attempt.id}`,
          {
            ...setup,
            lifecycle,
            rooted_count: rooted,
            ended_on: ended,
            expected_updated_at: attempt.updated_at,
          },
          "PUT",
        );
        refresh();
      }}
    >
      <FormSection title="Outcome">
        <Choice
          label="Status"
          value={lifecycle}
          items={[
            { id: "active", label: "Active" },
            { id: "completed", label: "Completed" },
            { id: "failed", label: "Failed" },
            { id: "abandoned", label: "Abandoned" },
          ]}
          onChange={setLifecycle}
        />
        <CountField label="Rooted count" value={rooted} onChange={setRooted} />
        <PartialDateField
          id="cutting-ended"
          label="Ended on"
          value={ended}
          disabled={false}
          onChange={setEnded}
        />
      </FormSection>
      <FormSection title="Rooting setup">
        <AttemptSetupFields
          setup={setup}
          onChange={setSetup}
          disabled={false}
        />
        <NotesField
          value={setup.notes}
          onChange={(notes) => {
            setSetup({ ...setup, notes });
          }}
        />
      </FormSection>
    </SaveDialog>
  );
}

function UndoDialog({
  receipt,
  token,
  close,
  refresh,
}: {
  receipt: string;
  token: string;
  close: () => void;
  refresh: () => void;
}) {
  const saveCutting = useSaveCutting(token);
  const path = `/api/v1/cutting-operations/${receipt}/reversal`;
  const [eligibility, retry] = useCuttingData<ReceiptEligibility>(path);
  const [confirmed, setConfirmed] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const current = eligibility.state === "ready" ? eligibility.value : undefined;
  async function undo() {
    if (
      pending ||
      !current ||
      current.status === "blocked" ||
      (current.status === "confirmation_required" && !confirmed)
    )
      return;
    setError("");
    setPending(true);
    try {
      await saveCutting(path, { confirm_retained_observations: confirmed });
      refresh();
      close();
    } catch (reason) {
      setError(cuttingError(reason));
      setConfirmed(false);
      retry();
    } finally {
      setPending(false);
    }
  }
  return (
    <TaskDialog
      title="Undo cutting operation"
      onClose={() => {
        if (!pending) close();
      }}
    >
      <h3>Undo cutting operation</h3>
      <p>
        This restores the source’s recorded pre-operation state and keeps the
        result in history.
      </p>
      {eligibility.state === "loading" && (
        <LoadingState>Checking eligibility…</LoadingState>
      )}
      {eligibility.state === "error" && (
        <ErrorState onRetry={retry}>
          Could not check reversal eligibility.
        </ErrorState>
      )}
      {error && (
        <p role="alert" className="notice notice--error">
          {error}
        </p>
      )}
      {current?.status === "blocked" && (
        <ul>
          {current.reasons.map((reason) => (
            <li key={`${reason.code}:${reason.entity_id ?? ""}`}>
              {reason.message}
            </li>
          ))}
        </ul>
      )}
      <FormActions>
        <button
          type="button"
          className="button--secondary"
          disabled={pending}
          onClick={close}
        >
          Cancel
        </button>
        {current && current.status !== "blocked" && (
          <button
            type="button"
            className="button--danger"
            disabled={
              pending ||
              (current.status === "confirmation_required" && !confirmed)
            }
            onClick={() => {
              void undo();
            }}
          >
            {pending ? "Reversing…" : "Confirm undo"}
          </button>
        )}
      </FormActions>
      {current?.status === "confirmation_required" && (
        <label>
          <input
            type="checkbox"
            checked={confirmed}
            disabled={pending}
            onChange={(event) => {
              setConfirmed(event.currentTarget.checked);
            }}
          />
          Keep recorded observations on the reversed result
        </label>
      )}
    </TaskDialog>
  );
}

const attemptTabs = [
  "overview",
  "observations",
  "offspring",
  "photos",
  "lineage",
] as const;
type AttemptTab = (typeof attemptTabs)[number];

function AttemptRecord({
  attempt,
  id,
  label,
  tab,
  setTab,
  primaryActions,
  secondaryActions,
  onEdit,
  overflow,
  children,
}: {
  attempt: AttemptDetail;
  id: string;
  label: string;
  tab: AttemptTab;
  setTab: (tab: AttemptTab) => void;
  primaryActions?: ReactNode;
  secondaryActions?: ReactNode;
  onEdit?: () => void;
  overflow?: ReactNode;
  children: ReactNode;
}) {
  const lot = attempt.vegetative_lot;
  const photos = useCuttingPhotos("propagation_attempt", id, lot);
  return (
    <DetailPage as="div" className="cutting-detail">
      <Breadcrumbs
        items={[
          { label: "Collection", href: "#/dashboard" },
          { label: "Cuttings", href: "#/cuttings" },
          { label },
        ]}
      />
      <DetailHeader
        headingLevel={2}
        titleId="cutting-attempt-title"
        eyebrow="Rooting attempt"
        title={label}
        plate={<CuttingPlate photos={photos} label={label} lot={lot} />}
        label={
          <SpecimenLabel
            kind="Rooting attempt"
            name="Current rooting state"
            rows={[
              {
                label: "Rooting",
                value: rootingLabel(attempt),
                emphasis: true,
              },
              { label: "Started with", value: countLabel(attempt.quantity) },
              {
                label: "Started on",
                value: formatPartialDate(attempt.started_on ?? null),
              },
              {
                label: "Material lot",
                wide: true,
                value: (
                  <a href={`#/cuttings/lots/${attempt.vegetative_lot_id}`}>
                    {lot.label ?? materialLabels[lot.material_type]}
                  </a>
                ),
              },
            ]}
          />
        }
        secondary={<IdentityLink id={lot.botanical_identity_id} />}
        status={
          <LifecycleStatus state={attempt.lifecycle}>
            {lifecycleLabel(attempt.lifecycle)}
          </LifecycleStatus>
        }
        lineage={
          <LineageStrip
            key={attempt.updated_at}
            kind="propagation-attempts"
            id={id}
            current="This Rooting attempt"
            currentKind="propagation_attempt"
            fullHref={`#/cuttings/attempts/${id}?tab=lineage`}
            onLineageTab={tab === "lineage"}
            onFull={(event) => {
              event.preventDefault();
              setTab("lineage");
            }}
          />
        }
        primaryActions={primaryActions}
        secondaryActions={secondaryActions}
        editLabel="Edit attempt"
        onEdit={onEdit}
        overflow={overflow}
      />
      <DetailTabs
        tabs={[
          { id: "overview", label: "Overview" },
          { id: "observations", label: "Observations" },
          { id: "offspring", label: "Offspring" },
          { id: "photos", label: "Photos" },
          { id: "lineage", label: "Lineage" },
        ]}
        selected={tab}
        onSelect={setTab}
      />
      {children}
      {tab === "photos" && (
        <div
          id="panel-photos"
          role="tabpanel"
          aria-labelledby="tab-photos"
          className="detail-tab-panel"
        >
          <PhotosSection
            target="propagation_attempt"
            targetId={id}
            targetLabel={label}
            primaryPhoto={photos.own}
            onPrimaryChanged={photos.reloadPhoto}
          />
        </div>
      )}
      {tab === "lineage" && (
        <div
          id="panel-lineage"
          role="tabpanel"
          aria-labelledby="tab-lineage"
          className="detail-tab-panel"
        >
          <LineagePanel kind="propagation-attempts" id={id} />
        </div>
      )}
    </DetailPage>
  );
}

export function AttemptPage({ id, token }: { id: string; token: string }) {
  const [data, retry] = useCuttingData<AttemptDetail>(
    `${attempts}/${id}`,
    true,
  );
  const [summary, retrySummary] = useCuttingData<AttemptSummary>(
    `${attempts}/${id}/propagation-summary`,
  );
  const [dialog, setDialog] = useState<DialogMode | undefined>(
    editRequested() ? { type: "edit" } : undefined,
  );
  const overview = useRef<HTMLHeadingElement>(null);
  const [tab, setTab] = useRecordTab(`#/cuttings/attempts/${id}`, attemptTabs);
  const attempt = data.state === "ready" ? data.value : undefined;
  const editable = attempt && attempt.lifecycle !== "reversed";
  const active = attempt?.lifecycle === "active";
  function close() {
    clearEditRequest();
    setDialog(undefined);
  }
  function refresh() {
    retry();
    retrySummary();
  }
  function refreshAfterTransition() {
    refresh();
    setTab("overview");
    requestAnimationFrame(() => overview.current?.focus());
  }

  const label = attempt ? displayAttempt(attempt) : "Rooting attempt";
  return (
    <Page titleId="cutting-attempt-title" className="cuttings-record">
      {data.state === "loading" && (
        <>
          <h2 id="cutting-attempt-title" className="sr-only">
            Rooting attempt
          </h2>
          <LoadingState>Loading rooting attempt…</LoadingState>
        </>
      )}
      {data.state === "error" && (
        <>
          <h2 id="cutting-attempt-title">Rooting attempt</h2>
          <ErrorState onRetry={retry}>{cuttingError(data.error)}</ErrorState>
        </>
      )}
      {attempt && (
        <AttemptRecord
          attempt={attempt}
          id={id}
          label={label}
          tab={tab}
          setTab={setTab}
          primaryActions={
            active && attempt.rooted_count !== 0 ? (
              <button
                type="button"
                onClick={() => {
                  setDialog({ type: "establish" });
                }}
              >
                Establish Plant or group
              </button>
            ) : undefined
          }
          secondaryActions={
            editable ? (
              <button
                type="button"
                className="button--secondary"
                onClick={() => {
                  setDialog({ type: "observe" });
                }}
              >
                Log rooting observation
              </button>
            ) : undefined
          }
          onEdit={
            editable
              ? () => {
                  setDialog({ type: "edit" });
                }
              : undefined
          }
          overflow={
            active ? (
              <OverflowMenu ariaLabel="More rooting attempt actions">
                <PlanLink kind="propagation_attempt" id={id} />
              </OverflowMenu>
            ) : undefined
          }
        >
          {tab === "overview" && (
            <div
              id="panel-overview"
              role="tabpanel"
              aria-labelledby="tab-overview"
              className="detail-tab-panel"
            >
              <RecordOverview
                facts={
                  <>
                    <section aria-labelledby="rooting-overview">
                      <h3 id="rooting-overview" ref={overview} tabIndex={-1}>
                        Rooting overview
                      </h3>
                      <dl className="record-facts">
                        {attempt.ended_on && (
                          <div>
                            <dt>Ended on</dt>
                            <dd>{formatPartialDate(attempt.ended_on)}</dd>
                          </div>
                        )}
                        {attempt.substrate && (
                          <div>
                            <dt>Substrate</dt>
                            <dd>{attempt.substrate}</dd>
                          </div>
                        )}
                        {attempt.hormone_treatment && (
                          <div>
                            <dt>Hormone treatment</dt>
                            <dd>{attempt.hormone_treatment}</dd>
                          </div>
                        )}
                        {attempt.container && (
                          <div>
                            <dt>Container</dt>
                            <dd>{attempt.container}</dd>
                          </div>
                        )}
                        {attempt.environment && (
                          <div>
                            <dt>Environment</dt>
                            <dd>{attempt.environment}</dd>
                          </div>
                        )}
                        {attempt.location_id && (
                          <div>
                            <dt>Location</dt>
                            <dd>
                              <a href={`#/locations/${attempt.location_id}`}>
                                Open rooting location
                              </a>
                            </dd>
                          </div>
                        )}
                        {attempt.notes && (
                          <div>
                            <dt>Notes</dt>
                            <dd>{attempt.notes}</dd>
                          </div>
                        )}
                      </dl>
                      {editable && attempt.operation_receipt_id && (
                        <p>
                          <button
                            type="button"
                            className="button--secondary"
                            onClick={() => {
                              if (attempt.operation_receipt_id)
                                setDialog({
                                  type: "undo",
                                  receipt: attempt.operation_receipt_id,
                                });
                            }}
                          >
                            Undo starting attempt
                          </button>
                        </p>
                      )}
                    </section>
                    <RecordDescendants
                      headingId="rooting-descendants"
                      loading={summary.state === "loading"}
                      error={summary.state === "error"}
                      items={
                        summary.state === "ready"
                          ? [
                              {
                                label: `${String(summary.value.offspring.length)} established offspring`,
                                href: `#/cuttings/attempts/${id}?tab=offspring`,
                                onClick: (event) => {
                                  event.preventDefault();
                                  setTab("offspring");
                                },
                              },
                            ]
                          : []
                      }
                      lineageHref={`#/cuttings/attempts/${id}?tab=lineage`}
                      onOpenLineage={(event) => {
                        event.preventDefault();
                        setTab("lineage");
                      }}
                    />
                  </>
                }
                almanac={
                  <RecordAlmanac
                    kind="propagation_attempt"
                    id={id}
                    current={active}
                    recordedElsewhere={
                      <>
                        {attempt.observations.length > 0
                          ? `${String(attempt.observations.length)} rooting ${attempt.observations.length === 1 ? "observation" : "observations"} recorded. `
                          : "No rooting observations recorded yet. "}
                        <a
                          href={`#/cuttings/attempts/${id}?tab=observations`}
                          onClick={(event) => {
                            event.preventDefault();
                            setTab("observations");
                          }}
                        >
                          Open Observations
                        </a>
                      </>
                    }
                  />
                }
              />
            </div>
          )}
          {tab === "observations" && (
            <div
              id="panel-observations"
              role="tabpanel"
              aria-labelledby="tab-observations"
              className="detail-tab-panel"
            >
              <section aria-labelledby="rooting-timeline">
                <h3 id="rooting-timeline">Rooting observations</h3>
                {attempt.observations.length ? (
                  <ol className="lineage-list">
                    {attempt.observations.map((item) => (
                      <li key={item.id}>
                        <strong>{item.stage.replaceAll("_", " ")}</strong>
                        {" · "}
                        {formatPartialDate(item.observed_on ?? null)}
                        {item.rooted_count != null &&
                          ` · ${String(item.rooted_count)} rooted`}
                        {item.notes && <p>{item.notes}</p>}
                        {editable && (
                          <button
                            type="button"
                            className="button--quiet"
                            onClick={() => {
                              setDialog({ type: "observe", observation: item });
                            }}
                          >
                            Correct observation
                          </button>
                        )}
                      </li>
                    ))}
                  </ol>
                ) : (
                  <EmptyState>No rooting observations recorded.</EmptyState>
                )}
              </section>
            </div>
          )}
          {tab === "offspring" && (
            <div
              id="panel-offspring"
              role="tabpanel"
              aria-labelledby="tab-offspring"
              className="detail-tab-panel"
            >
              <section aria-labelledby="rooting-offspring">
                <h3 id="rooting-offspring">Established offspring</h3>
                {summary.state === "loading" && (
                  <LoadingState>Loading offspring…</LoadingState>
                )}
                {summary.state === "error" && (
                  <ErrorState onRetry={retrySummary}>
                    Could not load offspring.
                  </ErrorState>
                )}
                {summary.state === "ready" &&
                  (summary.value.offspring.length ? (
                    <div className="record-child-grid">
                      {summary.value.offspring.map((item) => (
                        <RecordChildCard
                          key={item.id}
                          kind={item.kind === "plant" ? "Plant" : "Plant group"}
                          href={`#/${item.kind === "plant" ? "plants" : "plant-groups"}/${item.id}`}
                          title={
                            item.label ??
                            (item.kind === "plant" ? "Plant" : "Plant group")
                          }
                          status={item.lifecycle}
                          statusLabel={lifecycleLabel(item.lifecycle)}
                          actions={
                            item.lifecycle !== "reversed" &&
                            item.operation_receipt_id ? (
                              <button
                                type="button"
                                className="button--secondary"
                                onClick={() => {
                                  if (item.operation_receipt_id)
                                    setDialog({
                                      type: "undo",
                                      receipt: item.operation_receipt_id,
                                    });
                                }}
                              >
                                Undo establishment
                              </button>
                            ) : undefined
                          }
                        />
                      ))}
                    </div>
                  ) : (
                    <EmptyState>No established offspring.</EmptyState>
                  ))}
              </section>
            </div>
          )}
        </AttemptRecord>
      )}
      {attempt && (
        <>
          {dialog?.type === "edit" && editable && (
            <AttemptEditDialog
              attempt={attempt}
              token={token}
              close={close}
              refresh={refresh}
            />
          )}
          {dialog?.type === "observe" && (
            <ObservationDialog
              attempt={attempt}
              observation={dialog.observation}
              token={token}
              close={close}
              refresh={refresh}
            />
          )}
          {dialog?.type === "establish" && (
            <EstablishDialog
              attempt={attempt}
              token={token}
              close={close}
              refresh={refreshAfterTransition}
            />
          )}
          {dialog?.type === "undo" && (
            <UndoDialog
              receipt={dialog.receipt}
              token={token}
              close={close}
              refresh={refreshAfterTransition}
            />
          )}
        </>
      )}
    </Page>
  );
}
