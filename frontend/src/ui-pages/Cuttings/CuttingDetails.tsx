import { useState, type ReactNode } from "react";
import type { components } from "../../api/schema";
import { SpecimenPlate } from "../../components/CollectionUI";
import { setRecordRoute } from "../../components/recordNavigation";
import {
  FormActions,
  FormSection,
  PageHeader,
} from "../../components/ReferenceUI";
import { TaskDialog } from "../../components/TaskDialog";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  Page,
} from "../../components/WorkspaceUI";
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
  saveCutting,
  sourceLabels,
  useCuttingData,
  type Attempt,
  type AttemptDetail,
  type AttemptSummary,
  type AttemptWrite,
  type Lot,
  type LotDetail,
  type ReceiptEligibility,
  type RootingObservation,
} from "./api";

type Schema = components["schemas"];
type DetailTarget = "vegetative_lot" | "propagation_attempt";
type DialogMode =
  | { type: "edit" | "establish" }
  | { type: "observe"; observation?: RootingObservation }
  | { type: "undo"; receipt: string };

function CuttingPhotos({
  target,
  id,
  label,
  lot,
}: {
  target: DetailTarget;
  id: string;
  label: string;
  lot: Lot;
}) {
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
  const own = primary.state === "ready" ? primary.value : null;
  const inherited =
    (lotPhoto.state === "ready" ? lotPhoto.value : null) ??
    (motherPhoto.state === "ready" ? motherPhoto.value : null);
  return (
    <>
      <SpecimenPlate>
        <RecordVisual
          photo={own}
          fallbackPhoto={inherited}
          showSource
          kind="sowing"
          label={label}
          identity={{ id: lot.botanical_identity_id, display_label: label }}
        />
      </SpecimenPlate>
      <PhotosSection
        target={target}
        targetId={id}
        targetLabel={label}
        primaryPhoto={own}
        onPrimaryChanged={reloadPhoto}
      />
    </>
  );
}

function DetailNavigation({ children }: { children?: ReactNode }) {
  return (
    <div className="actions">
      <a className="button-link button--secondary" href="#/cuttings">
        All cuttings
      </a>
      {children}
    </div>
  );
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
        <dt>Botanical identity</dt>
        <dd>
          <IdentityLink id={lot.botanical_identity_id} />
        </dd>
      </div>
      <div>
        <dt>Material</dt>
        <dd>{materialLabels[lot.material_type]}</dd>
      </div>
      <div>
        <dt>Source</dt>
        <dd>
          {sourceLabels[lot.source_kind]}
          {lot.source_detail ? ` · ${lot.source_detail}` : ""}
        </dd>
      </div>
      <div>
        <dt>Taken or acquired on</dt>
        <dd>{formatPartialDate(lot.taken_on ?? null)}</dd>
      </div>
      <div>
        <dt>Initial quantity</dt>
        <dd>{countLabel(lot.initial_quantity)}</dd>
      </div>
      <div>
        <dt>Remaining quantity</dt>
        <dd>{countLabel(lot.quantity)}</dd>
      </div>
      <div>
        <dt>Status</dt>
        <dd>{lot.lifecycle}</dd>
      </div>
      {lot.location_id && (
        <div>
          <dt>Location</dt>
          <dd>
            <a href={`#/locations/${lot.location_id}`}>Open holding location</a>
          </dd>
        </div>
      )}
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

export function LotPage({ id, token }: { id: string; token: string }) {
  const [data, retry] = useCuttingData<LotDetail>(`${lots}/${id}`);
  const [start, setStart] = useState(false);
  const lot = data.state === "ready" ? data.value : undefined;
  return (
    <Page titleId="cutting-lot-title">
      <PageHeader
        titleId="cutting-lot-title"
        title={lot?.label ?? "Vegetative lot"}
        eyebrow="Cuttings"
        actions={
          <DetailNavigation>
            {lot?.lifecycle === "active" && (
              <>
                <button
                  type="button"
                  onClick={() => {
                    setStart(true);
                  }}
                >
                  Start rooting attempt
                </button>
                <PlanLink kind="vegetative_lot" id={id} />
              </>
            )}
          </DetailNavigation>
        }
      />
      {data.state === "loading" && (
        <LoadingState>Loading vegetative lot…</LoadingState>
      )}
      {data.state === "error" && (
        <ErrorState onRetry={retry}>{cuttingError(data.error)}</ErrorState>
      )}
      {lot && (
        <>
          <section aria-labelledby="cutting-lot-facts">
            <h3 id="cutting-lot-facts">Material and source</h3>
            <LotFacts lot={lot} />
          </section>
          <section aria-labelledby="cutting-lot-lineage">
            <h3 id="cutting-lot-lineage">Maternal lineage</h3>
            <LineagePanel kind="vegetative-lots" id={id} />
          </section>
          <section aria-labelledby="cutting-lot-attempts">
            <h3 id="cutting-lot-attempts">Rooting attempts</h3>
            {lot.attempts.length ? (
              <ul className="lineage-list">
                {lot.attempts.map((attempt) => (
                  <li key={attempt.id}>
                    <a href={`#/cuttings/attempts/${attempt.id}`}>
                      {displayAttempt(attempt)}
                    </a>{" "}
                    <span className="record-state">{attempt.lifecycle}</span>{" "}
                    {rootingLabel(attempt)}
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState>
                No attempts have been started for this lot.
              </EmptyState>
            )}
          </section>
          <CuttingPhotos
            target="vegetative_lot"
            lot={lot}
            id={id}
            label={lot.label ?? "vegetative lot"}
          />
          {start && (
            <StartDialog
              lot={lot}
              token={token}
              close={() => {
                setStart(false);
              }}
            />
          )}
        </>
      )}
    </Page>
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

function StartDialog({
  lot,
  token,
  close,
}: {
  lot: Lot;
  token: string;
  close: () => void;
}) {
  const [setup, setSetup] = useState<AttemptWrite["propagation_attempt"]>({
    started_on: lot.taken_on,
  });
  const [mode, setMode] =
    useState<AttemptWrite["source_adjustment"]["mode"]>("use_all");
  const [remainder, setRemainder] = useState<Lot["quantity"]>(null);
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
            propagation_attempt:
              mode === "use_all" ? { ...setup, quantity: lot.quantity } : setup,
          },
          token,
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
          showQuantity={mode !== "use_all"}
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
          token,
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
          token,
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
          token,
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
      await saveCutting(
        path,
        { confirm_retained_observations: confirmed },
        token,
      );
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

export function AttemptPage({ id, token }: { id: string; token: string }) {
  const [data, retry] = useCuttingData<AttemptDetail>(`${attempts}/${id}`);
  const [summary, retrySummary] = useCuttingData<AttemptSummary>(
    `${attempts}/${id}/propagation-summary`,
  );
  const [dialog, setDialog] = useState<DialogMode>();
  const attempt = data.state === "ready" ? data.value : undefined;
  const editable = attempt && attempt.lifecycle !== "reversed";
  const active = attempt?.lifecycle === "active";
  function close() {
    setDialog(undefined);
  }
  function refresh() {
    retry();
    retrySummary();
  }

  return (
    <Page titleId="cutting-attempt-title">
      <PageHeader
        titleId="cutting-attempt-title"
        title={attempt ? displayAttempt(attempt) : "Rooting attempt"}
        eyebrow="Cuttings"
        actions={
          <DetailNavigation>
            {active && (
              <>
                {attempt.rooted_count !== 0 && (
                  <button
                    type="button"
                    onClick={() => {
                      setDialog({ type: "establish" });
                    }}
                  >
                    Establish Plant or group
                  </button>
                )}
                <PlanLink kind="propagation_attempt" id={id} />
              </>
            )}
            {editable && (
              <button
                type="button"
                className="button--secondary"
                onClick={() => {
                  setDialog({ type: "edit" });
                }}
              >
                Edit attempt
              </button>
            )}
          </DetailNavigation>
        }
      />
      {data.state === "loading" && (
        <LoadingState>Loading rooting attempt…</LoadingState>
      )}
      {data.state === "error" && (
        <ErrorState onRetry={retry}>{cuttingError(data.error)}</ErrorState>
      )}
      {attempt && (
        <>
          <section aria-labelledby="rooting-overview">
            <h3 id="rooting-overview">Rooting overview</h3>
            <dl className="record-facts">
              <div>
                <dt>Status</dt>
                <dd>{attempt.lifecycle}</dd>
              </div>
              <div>
                <dt>Rooting outcome</dt>
                <dd>{rootingLabel(attempt)}</dd>
              </div>
              <div>
                <dt>Starting quantity</dt>
                <dd>{countLabel(attempt.quantity)}</dd>
              </div>
              <div>
                <dt>Material lot</dt>
                <dd>
                  <a href={`#/cuttings/lots/${attempt.vegetative_lot_id}`}>
                    {attempt.vegetative_lot.label ??
                      materialLabels[attempt.vegetative_lot.material_type]}
                  </a>
                </dd>
              </div>
              <div>
                <dt>Botanical identity</dt>
                <dd>
                  <IdentityLink
                    id={attempt.vegetative_lot.botanical_identity_id}
                  />
                </dd>
              </div>
              <div>
                <dt>Started on</dt>
                <dd>{formatPartialDate(attempt.started_on ?? null)}</dd>
              </div>
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
            )}
          </section>
          <section aria-labelledby="rooting-lineage">
            <h3 id="rooting-lineage">Maternal lineage</h3>
            <LineagePanel kind="propagation-attempts" id={id} />
          </section>
          <section aria-labelledby="rooting-timeline">
            <h3 id="rooting-timeline">Rooting observations</h3>
            {editable && (
              <button
                type="button"
                className="button--secondary"
                onClick={() => {
                  setDialog({ type: "observe" });
                }}
              >
                Log rooting observation
              </button>
            )}
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
                <ul className="lineage-list">
                  {summary.value.offspring.map((item) => (
                    <li key={item.id}>
                      <a
                        href={`#/${item.kind === "plant" ? "plants" : "plant-groups"}/${item.id}`}
                      >
                        {item.label ??
                          (item.kind === "plant" ? "Plant" : "Plant group")}
                      </a>{" "}
                      <span className="record-state">{item.lifecycle}</span>{" "}
                      {item.lifecycle !== "reversed" &&
                        item.operation_receipt_id && (
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
                        )}
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState>No established offspring.</EmptyState>
              ))}
          </section>
          <CuttingPhotos
            target="propagation_attempt"
            lot={attempt.vegetative_lot}
            id={id}
            label={displayAttempt(attempt)}
          />
          {dialog?.type === "edit" && (
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
              refresh={refresh}
            />
          )}
          {dialog?.type === "undo" && (
            <UndoDialog
              receipt={dialog.receipt}
              token={token}
              close={close}
              refresh={refresh}
            />
          )}
        </>
      )}
    </Page>
  );
}
