import { firstValidationField } from "../components/formValidation";
import { useMemo } from "react";
import { FormSections } from "../components/FormSections";
import {
  PlantEssentialsFields,
  PlantEntryDateField,
  PlantNotesField,
  type PlantFieldsState,
} from "../plants/PlantFormFields";
import {
  useRecordName,
  usePublishRecordIdentities,
} from "../components/recordPresentation";
import { useEffect, useRef, useState, type SyntheticEvent } from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { Breadcrumbs } from "../components/CollectionUI";
import { FieldHelp } from "../components/ContextualHelp";
import {
  listBotanicalIdentities,
  type BotanicalIdentityResponse,
} from "../botanical-identities/api";
import { listLocations, type LocationResponse } from "../locations/api";
import {
  createPlantFromSowing,
  createPlantGroupFromSowing,
  getSowing,
  type SowingLifecycle,
  type SowingResponse,
} from "../sowings/api";
import { PropagationPath } from "./PropagationPath";

type Kind = "plant" | "group";

const sowingLifecycleLabels: Record<
  Exclude<SowingLifecycle, "reversed">,
  string
> = {
  active: "Keep active",
  completed: "Complete Sowing",
  failed: "Mark failed",
  abandoned: "Abandon Sowing",
};

export function SowingDescendantWizard({
  sowingId,
  kind,
}: {
  sowingId: string;
  kind: Kind;
}) {
  const auth = useAuth();
  const recordName = useRecordName();
  const [data, setData] = useState<
    | { status: "loading" }
    | { status: "error" }
    | {
        status: "ready";
        sowing: SowingResponse;
        identities: BotanicalIdentityResponse[];
        locations: LocationResponse[];
      }
  >({ status: "loading" });
  const [identityId, setIdentityId] = useState("");
  const [form, setForm] = useState<PlantFieldsState>({
    label: "",
    locationId: "",
    collectionEntryDate: null,
    notes: "",
    quantityKind: "unknown",
    quantityValue: "",
  });
  const {
    label,
    locationId,
    collectionEntryDate: entryDate,
    notes,
    quantityKind,
    quantityValue,
  } = form;
  const updateForm = <K extends keyof PlantFieldsState>(
    key: K,
    value: PlantFieldsState[K],
  ) => {
    setForm((current) => ({ ...current, [key]: value }));
  };
  const [resultingLifecycle, setResultingLifecycle] =
    useState<SowingLifecycle>("active");
  const [pending, setPending] = useState(false);
  const [messages, setMessages] = useState<string[]>([]);
  const [validationField, setValidationField] = useState<string | undefined>();
  const feedback = useRef<HTMLDivElement>(null);
  usePublishRecordIdentities(
    data.status === "ready" ? data.identities : undefined,
  );
  const sectionError = useMemo(
    () => (messages.length ? { messages, field: validationField } : undefined),
    [messages, validationField],
  );

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      getSowing(sowingId, controller.signal),
      listBotanicalIdentities(controller.signal),
      listLocations(controller.signal),
    ])
      .then(([sowing, identities, locations]) => {
        setData({ status: "ready", sowing, identities, locations });
        setIdentityId(sowing.seed_lot.botanical_identity_id);
        setForm((current) => ({
          ...current,
          locationId: sowing.location_id ?? "",
        }));
      })
      .catch(() => {
        if (!controller.signal.aborted) setData({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [sowingId]);

  if (data.status === "loading")
    return (
      <section className="workspace">
        <p role="status">Loading propagation workflow…</p>
      </section>
    );
  if (data.status === "error")
    return (
      <section className="workspace">
        <div className="notice notice--error" role="alert">
          Florabase could not load the source Sowing.
        </div>
      </section>
    );
  const { sowing, identities, locations } = data;
  if (sowing.lifecycle === "reversed")
    return (
      <section className="workspace">
        <p role="alert">
          This Sowing is Reversed and cannot create new descendants.
        </p>
        <a href={`#/sowings/${sowing.id}`}>View historical Sowing</a>
      </section>
    );

  const completionOutcome = (() => {
    if (resultingLifecycle !== "completed") return null;
    const quantity = sowing.quantity;
    if (
      quantity?.kind === "seed_count" &&
      !quantity.is_approximate &&
      sowing.germinated_count !== null
    ) {
      const notGerminated = Number(quantity.value) - sowing.germinated_count;
      return (
        <div className="completion-outcome" aria-live="polite">
          <h4>Final Sowing outcome</h4>
          <dl>
            <div>
              <dt>Sown</dt>
              <dd>{quantity.value}</dd>
            </div>
            <div>
              <dt>Germinated</dt>
              <dd>{sowing.germinated_count}</dd>
            </div>
            <div>
              <dt>Not germinated</dt>
              <dd>{String(Math.max(0, notGerminated))}</dd>
            </div>
          </dl>
          <p className="field-help">
            Review or correct the final germinated count from the Sowing editor
            before completing if needed.
          </p>
        </div>
      );
    }
    return (
      <div className="completion-outcome">
        <h4>Final Sowing outcome</h4>
        <p>
          The exact non-germinated remainder cannot be derived from the recorded{" "}
          {quantity?.kind === "weight"
            ? "weight"
            : quantity?.is_approximate
              ? "approximate quantity"
              : "unknown quantity"}
          . You may still complete the Sowing.
        </p>
      </div>
    );
  })();

  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    setValidationField(undefined);
    const errors: string[] = [];
    if (!identityId) errors.push("Choose a Botanical identity.");
    if (kind === "group" && quantityKind !== "unknown") {
      const value = Number(quantityValue);
      if (!quantityValue || !Number.isInteger(value) || value <= 0)
        errors.push("Plant group quantity must be a positive whole number.");
    }
    if (errors.length) {
      setMessages(errors);
      return;
    }
    const common = {
      botanical_identity_id: identityId,
      label: label || null,
      collection_entry_date: entryDate,
      location_id: locationId || null,
      lifecycle: "active" as const,
      notes: notes || null,
    };
    const csrfToken =
      auth.state.status === "authenticated" ||
      auth.state.status === "logging-out" ||
      auth.state.status === "logout-failed"
        ? auth.state.csrfToken
        : "";
    setPending(true);
    setMessages([]);
    setValidationField(undefined);
    try {
      if (kind === "plant") {
        const result = await createPlantFromSowing(
          sowing.id,
          { plant: common, resulting_sowing_lifecycle: resultingLifecycle },
          csrfToken,
        );
        window.location.hash = `/plants/${result.plant.id}`;
      } else {
        const result = await createPlantGroupFromSowing(
          sowing.id,
          {
            plant_group: {
              ...common,
              quantity:
                quantityKind === "unknown"
                  ? null
                  : {
                      value: Number(quantityValue),
                      is_approximate: quantityKind === "approximate",
                    },
            },
            resulting_sowing_lifecycle: resultingLifecycle,
          },
          csrfToken,
        );
        window.location.hash = `/plant-groups/${result.plant_group.id}`;
      }
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 422) {
        setValidationField(firstValidationField(error));
      }

      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else if (error instanceof ApiError && error.status === 409)
        setMessages([
          "The source Sowing changed before submission. Review its current lifecycle and try again.",
        ]);
      else
        setMessages([
          `Florabase could not create the ${kind === "plant" ? "Plant" : "Plant group"}. Your details are still here.`,
        ]);
      setPending(false);
      window.setTimeout(() => feedback.current?.focus(), 0);
    }
  }

  return (
    <section
      className="workspace propagation-workspace"
      aria-labelledby="descendant-title"
    >
      <Breadcrumbs
        items={[
          {
            label: sowing.seed_lot.botanical_identity_display_label,
            href: `#/identities/${sowing.seed_lot.botanical_identity_id}?tab=plants`,
          },
          {
            label: recordName(sowing, "Sowing"),
            href: `#/sowings/${sowing.id}`,
          },
          { label: kind === "plant" ? "Create Plant" : "Create Plant group" },
        ]}
      />
      <div className="workspace-intro">
        <div>
          <p className="eyebrow">Guided propagation</p>
          <h2 id="descendant-title">
            Create {kind === "plant" ? "Plant" : "Plant group"}
          </h2>
          <p>
            From <strong>{recordName(sowing, "Unlabelled Sowing")}</strong>. The
            originating Sowing is stored explicitly.
          </p>
        </div>
      </div>
      <PropagationPath
        stages={[
          [
            {
              type: "Source SeedLot",
              label: recordName(
                {
                  label: sowing.seed_lot.label,
                  botanical_identity_id: sowing.seed_lot.botanical_identity_id,
                  botanical_identity_display_label:
                    sowing.seed_lot.botanical_identity_display_label,
                },
                "Unlabelled SeedLot",
              ),
              href: `#/seeds/${sowing.seed_lot.id}`,
              state: sowing.seed_lot.lifecycle,
            },
          ],
          [
            {
              type: "Current Sowing",
              label: recordName(sowing, "Unlabelled Sowing"),
              href: `#/sowings/${sowing.id}`,
              state: sowing.lifecycle,
            },
          ],
        ]}
      />
      <form
        className="propagation-form"
        onSubmit={(event) => void submit(event)}
        noValidate
      >
        <p className="eyebrow">Result</p>
        <h3>New {kind === "plant" ? "Plant" : "Plant group"} details</h3>
        <FormSections
          disabled={pending}
          error={sectionError}
          errorFields={[
            { match: /identity/i, selector: "#descendant-identity" },
            {
              match: /quantity|whole number/i,
              selector: "#plant-quantity-value",
            },
            {
              match: /collection entry/i,
              selector: "#plant-entry-date-precision",
            },
            { match: /notes/i, selector: "#plant-notes" },
          ]}
          panels={[
            {
              id: "essentials",
              label: "Essentials",
              content: (
                <>
                  <div className="field">
                    <label htmlFor="descendant-identity">
                      Botanical identity
                    </label>
                    <select
                      aria-describedby="descendant-identity-help"
                      id="descendant-identity"
                      value={identityId}
                      onChange={(event) => {
                        setIdentityId(event.currentTarget.value);
                      }}
                    >
                      {identities.map((identity) => (
                        <option key={identity.id} value={identity.id}>
                          {identity.display_label}
                        </option>
                      ))}
                    </select>
                    <FieldHelp id="descendant-identity-help">
                      The source identity is preselected, but a valid changed
                      identity may be chosen. Sharing an identity does not
                      establish lineage.
                    </FieldHelp>
                  </div>
                  <PlantEssentialsFields
                    form={form}
                    updateForm={updateForm}
                    pending={pending}
                    kind={kind}
                    locations={locations}
                  />
                </>
              ),
            },
            {
              id: "origin",
              label: "Origin",
              content: (
                <>
                  <div className="notice field--full">
                    Originating Sowing:{" "}
                    <strong>{recordName(sowing, "Sowing")}</strong>. This
                    explicit link is created with the result.
                  </div>
                  <PlantEntryDateField
                    form={form}
                    updateForm={updateForm}
                    pending={pending}
                  />
                </>
              ),
            },
            {
              id: "lifecycle",
              label: "Lifecycle & notes",
              content: (
                <>
                  <PlantNotesField
                    form={form}
                    updateForm={updateForm}
                    pending={pending}
                  />
                  <div className="field--full">
                    {" "}
                    <p className="eyebrow">Sowing state after creation</p>
                    <fieldset className="choice-cards">
                      <legend>Resulting Sowing lifecycle</legend>
                      {(
                        Object.keys(sowingLifecycleLabels) as Exclude<
                          SowingLifecycle,
                          "reversed"
                        >[]
                      ).map((value) => (
                        <label key={value}>
                          <input
                            type="radio"
                            name="resulting-lifecycle"
                            checked={resultingLifecycle === value}
                            onChange={() => {
                              setResultingLifecycle(value);
                            }}
                          />
                          <span>
                            <strong>{sowingLifecycleLabels[value]}</strong>
                            <small>
                              {value === "active"
                                ? "Default. Descendant counts never complete a Sowing automatically."
                                : `The Sowing will be marked ${value} in the same atomic operation.`}
                            </small>
                          </span>
                        </label>
                      ))}
                    </fieldset>
                    {completionOutcome}
                    <p className="field-help">
                      Confirm to create the{" "}
                      {kind === "plant" ? "Plant" : "Plant group"} with an
                      explicit link to this Sowing. The Sowing will{" "}
                      {resultingLifecycle === "active"
                        ? "remain active"
                        : `be marked ${resultingLifecycle}`}
                      .
                    </p>
                  </div>
                </>
              ),
            },
          ]}
          submit={
            <button type="submit" disabled={pending}>
              {pending
                ? "Creating…"
                : `Create ${kind === "plant" ? "Plant" : "Plant group"}`}
            </button>
          }
          cancel={
            <a
              className="button-link button--secondary"
              href={`#/sowings/${sowing.id}`}
            >
              Cancel
            </a>
          }
        />
        {messages.length > 0 && (
          <div
            className="notice notice--error"
            role="alert"
            tabIndex={-1}
            ref={feedback}
          >
            <ul>
              {messages.map((message) => (
                <li key={message}>{message}</li>
              ))}
            </ul>
          </div>
        )}
      </form>
    </section>
  );
}
