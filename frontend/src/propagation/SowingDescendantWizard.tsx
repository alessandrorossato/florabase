import { useEffect, useRef, useState, type SyntheticEvent } from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { Breadcrumbs } from "../components/CollectionUI";
import {
  listBotanicalIdentities,
  type BotanicalIdentityResponse,
} from "../botanical-identities/api";
import {
  listLocations,
  locationsForScope,
  type LocationResponse,
} from "../locations/api";
import { PartialDateField } from "../seed-lots/PartialDateField";
import {
  createPlantFromSowing,
  createPlantGroupFromSowing,
  getSowing,
  type PartialDate,
  type SowingLifecycle,
  type SowingResponse,
} from "../sowings/api";
import { PropagationPath } from "./PropagationPath";

type Kind = "plant" | "group";
type QuantityKind = "unknown" | "exact" | "approximate";

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
  const [label, setLabel] = useState("");
  const [entryDate, setEntryDate] = useState<PartialDate | null>(null);
  const [locationId, setLocationId] = useState("");
  const [notes, setNotes] = useState("");
  const [quantityKind, setQuantityKind] = useState<QuantityKind>("unknown");
  const [quantityValue, setQuantityValue] = useState("");
  const [resultingLifecycle, setResultingLifecycle] =
    useState<SowingLifecycle>("active");
  const [pending, setPending] = useState(false);
  const [messages, setMessages] = useState<string[]>([]);
  const feedback = useRef<HTMLDivElement>(null);

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
        setLocationId(sowing.location_id ?? "");
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
          { label: sowing.label ?? "Sowing", href: `#/sowings/${sowing.id}` },
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
            From <strong>{sowing.label ?? "Unlabelled Sowing"}</strong>. The
            originating Sowing is stored explicitly.
          </p>
        </div>
      </div>
      <PropagationPath
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
        ]}
      />
      <form
        className="propagation-form"
        onSubmit={(event) => void submit(event)}
        noValidate
      >
        <h3>New {kind === "plant" ? "Plant" : "Plant group"} details</h3>
        <div className="guided-form-grid">
          <div className="field">
            <label htmlFor="descendant-identity">Botanical identity</label>
            <select
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
            <small>
              The source identity is preselected, but a valid changed identity
              may be chosen.
            </small>
          </div>
          <div className="field">
            <label htmlFor="descendant-label">
              Label <span className="optional">(optional)</span>
            </label>
            <input
              id="descendant-label"
              value={label}
              onChange={(event) => {
                setLabel(event.currentTarget.value);
              }}
            />
          </div>
          <PartialDateField
            id="descendant-entry-date"
            label="Collection-entry date (optional)"
            value={entryDate}
            disabled={pending}
            onChange={setEntryDate}
          />
          <div className="field">
            <label htmlFor="descendant-location">
              Current location <span className="optional">(optional)</span>
            </label>
            <select
              id="descendant-location"
              value={locationId}
              onChange={(event) => {
                setLocationId(event.currentTarget.value);
              }}
            >
              <option value="">Not recorded</option>
              {locationsForScope(locations, "plants").map((location) => (
                <option
                  key={location.id}
                  value={location.id}
                  disabled={Boolean(location.retired_at)}
                >
                  {location.display_path}
                </option>
              ))}
            </select>
          </div>
          {kind === "group" && (
            <fieldset className="quantity-field">
              <legend>Plant group quantity</legend>
              <div className="field">
                <label htmlFor="descendant-quantity-kind">Precision</label>
                <select
                  id="descendant-quantity-kind"
                  value={quantityKind}
                  onChange={(event) => {
                    setQuantityKind(event.currentTarget.value as QuantityKind);
                  }}
                >
                  <option value="unknown">Unknown</option>
                  <option value="exact">Exact</option>
                  <option value="approximate">Approximate</option>
                </select>
              </div>
              {quantityKind !== "unknown" && (
                <div className="field">
                  <label htmlFor="descendant-quantity">Individuals</label>
                  <input
                    id="descendant-quantity"
                    inputMode="numeric"
                    value={quantityValue}
                    onChange={(event) => {
                      setQuantityValue(event.currentTarget.value);
                    }}
                  />
                </div>
              )}
              <small>
                Exact groups contribute their quantity to exact tracked
                descendants. Approximate and unknown groups remain explicitly
                uncertain.
              </small>
            </fieldset>
          )}
          <div className="field field--full">
            <label htmlFor="descendant-notes">
              Notes <span className="optional">(optional)</span>
            </label>
            <textarea
              id="descendant-notes"
              value={notes}
              onChange={(event) => {
                setNotes(event.currentTarget.value);
              }}
            />
          </div>
        </div>
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
                    : `The Sowing will become ${value} in the same atomic operation.`}
                </small>
              </span>
            </label>
          ))}
        </fieldset>
        {completionOutcome}
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
        <div className="actions">
          <button type="submit" disabled={pending}>
            {pending
              ? "Creating…"
              : `Create ${kind === "plant" ? "Plant" : "Plant group"}`}
          </button>
          <a
            className="button-link button--secondary"
            href={`#/sowings/${sowing.id}`}
          >
            Cancel
          </a>
        </div>
      </form>
    </section>
  );
}
