import { useEffect, useId, useRef, useState, type SyntheticEvent } from "react";
import {
  activeCsrfToken,
  ApiError,
  isExpectedAuthCancellation,
} from "../auth/api";
import { useAuth } from "../auth/context";
import {
  listBotanicalIdentities,
  type BotanicalIdentityResponse,
} from "../botanical-identities/api";
import { FieldLabel } from "../components/FieldLabel";
import { PageHeader } from "../components/ReferenceUI";
import { ErrorState, LoadingState, Page } from "../components/WorkspaceUI";
import {
  listLocations,
  locationsForScope,
  type LocationResponse,
} from "../locations/api";
import { localDay } from "../schedule/calendar";
import type { PartialDate } from "../seed-lots/api";
import { PartialDateField } from "../seed-lots/PartialDateField";
import { ReferencePicker } from "../seed-lots/ReferencePicker";
import { listSuppliers, type SupplierResponse } from "../suppliers/api";
import {
  quickAddPlant,
  recordHref,
  type QuickAddRequest,
  type QuickAddResponse,
} from "./api";
import { QuickAddNameField, type NameChoice } from "./NameField";
import "./quick-add.css";

type Origin = "unknown" | "purchased" | "gift_exchange";
type Material = "plant" | "plant_group";
type Quantity = "exact" | "approximate";

function today(): PartialDate {
  const [year, month, day] = localDay().split("-").map(Number);
  return { precision: "day", year, month, day };
}

function apiMessage(failure: unknown): string {
  if (failure instanceof ApiError) {
    const detail = (failure.body as { detail?: unknown } | undefined)?.detail;
    if (detail && typeof detail === "object" && "message" in detail) {
      const message = (detail as { message?: unknown }).message;
      if (typeof message === "string" && message) return message;
    }
    if (Array.isArray(detail))
      return "Check the highlighted details and try again.";
  }
  return "Florabase could not add the plant. Your details are still here.";
}

/** QUICK-ADD-001: add a purchased or gifted plant in one short form. */
export function QuickAddScreen() {
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();
  const token = activeCsrfToken(auth.state);
  const ids = {
    cultivar: useId(),
    common: useId(),
    label: useId(),
    count: useId(),
    notes: useId(),
    origin: useId(),
  };
  const nameRef = useRef<HTMLDivElement>(null);
  const [references, setReferences] = useState<
    | { status: "loading" }
    | { status: "error" }
    | {
        status: "ready";
        identities: BotanicalIdentityResponse[];
        locations: LocationResponse[];
        suppliers: SupplierResponse[];
      }
  >({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [name, setName] = useState("");
  const [choice, setChoice] = useState<NameChoice>({ kind: "text" });
  const [cultivar, setCultivar] = useState("");
  const [commonName, setCommonName] = useState("");
  const [material, setMaterial] = useState<Material>("plant");
  const [quantityKind, setQuantityKind] = useState<Quantity>("exact");
  const [count, setCount] = useState("");
  const [label, setLabel] = useState("");
  const [locationId, setLocationId] = useState("");
  const [supplierId, setSupplierId] = useState("");
  const [origin, setOrigin] = useState<Origin>("unknown");
  const [entryDate, setEntryDate] = useState<PartialDate | null>(today);
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [added, setAdded] = useState<QuickAddResponse | null>(null);

  useEffect(() => {
    if (!authorized) return;
    const controller = new AbortController();
    void Promise.all([
      listBotanicalIdentities(capability, controller.signal),
      listLocations(capability, controller.signal),
      listSuppliers(capability, controller.signal),
    ])
      .then(([identities, locations, suppliers]) => {
        setReferences({ status: "ready", identities, locations, suppliers });
      })
      .catch((failure: unknown) => {
        if (controller.signal.aborted || isExpectedAuthCancellation(failure))
          return;
        if (failure instanceof ApiError && failure.status === 401)
          sessionExpired();
        else setReferences({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [authorized, capability, sessionExpired, attempt]);

  function request(): QuickAddRequest | string {
    const trimmed = name.trim();
    if (!trimmed) return "Enter a scientific name.";
    let quantity: QuickAddRequest["quantity"] = null;
    if (material === "plant_group") {
      const value = Number(count);
      if (!/^\d+$/.test(count.trim()) || value < 1)
        return "Enter how many plants the group holds (1 or more).";
      quantity = { value, is_approximate: quantityKind === "approximate" };
    }
    return {
      identity:
        choice.kind === "existing"
          ? { existing_id: choice.identity.id }
          : {
              new: {
                scientific_name: trimmed,
                cultivar_name: cultivar.trim() || null,
                common_name: commonName.trim() || null,
                wfo:
                  choice.kind === "wfo"
                    ? {
                        source_taxon_id: choice.candidate.taxon.source_taxon_id,
                      }
                    : null,
              },
            },
      material,
      quantity,
      label: label.trim() || null,
      location_id: locationId || null,
      supplier_id: supplierId || null,
      direct_origin_kind: origin,
      collection_entry_date: entryDate,
      notes: notes.trim() || null,
    };
  }

  async function submit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (saving || !token) return;
    const payload = request();
    if (typeof payload === "string") {
      setError(payload);
      return;
    }
    const another =
      (event.nativeEvent.submitter as HTMLButtonElement | null)?.value ===
      "another";
    setSaving(true);
    setError(null);
    try {
      const result = await quickAddPlant(payload, token, capability);
      setAdded(result);
      if (result.identity_created && references.status === "ready") {
        // Later entries in this session can reuse the identity just created.
        const identities = await listBotanicalIdentities(capability).catch(
          () => references.identities,
        );
        setReferences({ ...references, identities });
      }
      if (another) {
        // Keep where and from whom; clear what differs between plants.
        setName("");
        setChoice({ kind: "text" });
        setCultivar("");
        setCommonName("");
        setLabel("");
        setCount("");
        setNotes("");
        // The field is disabled while saving; focus it once it is enabled again.
        window.setTimeout(() => {
          nameRef.current?.querySelector("input")?.focus();
        }, 0);
      } else {
        window.location.hash = recordHref(result);
      }
    } catch (failure: unknown) {
      if (isExpectedAuthCancellation(failure)) return;
      if (failure instanceof ApiError && failure.status === 401) {
        sessionExpired();
        return;
      }
      setError(apiMessage(failure));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Page titleId="quick-add-title" className="workspace--quick-add">
      <PageHeader
        title="Quick add plant"
        titleId="quick-add-title"
        eyebrow="Collection"
        description="Add a plant or group in one step. A WFO name creates its botanical identity, linked, at the same time."
      />
      {references.status === "loading" && (
        <LoadingState>Loading collection references…</LoadingState>
      )}
      {references.status === "error" && (
        <ErrorState
          onRetry={() => {
            setReferences({ status: "loading" });
            setAttempt((value) => value + 1);
          }}
        >
          Could not load your collection references.
        </ErrorState>
      )}
      {references.status === "ready" && (
        <form
          className="seed-form quick-add-form"
          onSubmit={(event) => void submit(event)}
        >
          {added && (
            <p role="status" className="notice quick-add-added">
              Added {added.record_kind === "plant" ? "plant" : "plant group"} of{" "}
              <a href={recordHref(added)}>{added.identity_display_label}</a>
              {added.identity_created
                ? added.wfo_linked
                  ? " · new identity linked to WFO"
                  : " · new identity, not linked to WFO"
                : ""}
              .
            </p>
          )}
          <div ref={nameRef}>
            <QuickAddNameField
              identities={references.identities}
              capability={capability}
              value={name}
              choice={choice}
              disabled={saving}
              onChange={(value, next) => {
                setName(value);
                setChoice(next);
              }}
            />
          </div>
          {choice.kind !== "existing" && (
            <div className="quick-add-row">
              <div className="field">
                <label htmlFor={ids.cultivar}>Cultivar</label>
                <input
                  id={ids.cultivar}
                  value={cultivar}
                  disabled={saving}
                  onChange={(event) => {
                    setCultivar(event.currentTarget.value);
                  }}
                />
              </div>
              <div className="field">
                <label htmlFor={ids.common}>Common name</label>
                <input
                  id={ids.common}
                  value={commonName}
                  disabled={saving}
                  onChange={(event) => {
                    setCommonName(event.currentTarget.value);
                  }}
                />
              </div>
            </div>
          )}
          <fieldset className="quick-add-material">
            <legend>What are you adding?</legend>
            <label className="checkbox-label">
              <input
                type="radio"
                name="quick-add-material"
                checked={material === "plant"}
                disabled={saving}
                onChange={() => {
                  setMaterial("plant");
                }}
              />
              One plant
            </label>
            <label className="checkbox-label">
              <input
                type="radio"
                name="quick-add-material"
                checked={material === "plant_group"}
                disabled={saving}
                onChange={() => {
                  setMaterial("plant_group");
                }}
              />
              A group of plants
            </label>
            {material === "plant_group" && (
              <div className="quick-add-row">
                <div className="field">
                  <FieldLabel required htmlFor={ids.count}>
                    How many
                  </FieldLabel>
                  <input
                    id={ids.count}
                    inputMode="numeric"
                    value={count}
                    disabled={saving}
                    onChange={(event) => {
                      setCount(event.currentTarget.value);
                    }}
                  />
                </div>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={quantityKind === "approximate"}
                    disabled={saving}
                    onChange={(event) => {
                      setQuantityKind(
                        event.currentTarget.checked ? "approximate" : "exact",
                      );
                    }}
                  />
                  Approximate count
                </label>
              </div>
            )}
          </fieldset>
          <div className="quick-add-row">
            <div className="field">
              <label htmlFor={ids.label}>Label</label>
              <input
                id={ids.label}
                value={label}
                disabled={saving}
                onChange={(event) => {
                  setLabel(event.currentTarget.value);
                }}
              />
            </div>
            <ReferencePicker
              label="Location"
              placeholder="Not recorded"
              disabled={saving}
              choices={locationsForScope(references.locations, "plants").map(
                (location) => ({
                  id: location.id,
                  label: location.display_path,
                  retired: Boolean(location.retired_at),
                }),
              )}
              value={locationId}
              onChange={setLocationId}
            />
          </div>
          <div className="quick-add-row">
            <ReferencePicker
              label="Supplier"
              placeholder="Not recorded"
              disabled={saving}
              choices={references.suppliers.map((supplier) => ({
                id: supplier.id,
                label: supplier.name,
              }))}
              value={supplierId}
              onChange={(value) => {
                setSupplierId(value);
                if (value && origin === "unknown") setOrigin("purchased");
              }}
            />
            <div className="field">
              <label htmlFor={ids.origin}>Origin</label>
              <select
                id={ids.origin}
                value={origin}
                disabled={saving}
                onChange={(event) => {
                  setOrigin(event.currentTarget.value as Origin);
                }}
              >
                <option value="unknown">Not recorded</option>
                <option value="purchased">Purchased</option>
                <option value="gift_exchange">Gift or exchange</option>
              </select>
            </div>
          </div>
          <PartialDateField
            id="quick-add-entry-date"
            label="In the collection since"
            hidePrecisionLabel
            value={entryDate}
            disabled={saving}
            onChange={setEntryDate}
          />
          <div className="field field--full">
            <label htmlFor={ids.notes}>Notes</label>
            <textarea
              id={ids.notes}
              rows={2}
              value={notes}
              disabled={saving}
              onChange={(event) => {
                setNotes(event.currentTarget.value);
              }}
            />
          </div>
          {error && <p role="alert">{error}</p>}
          <div className="form-actions">
            <button type="submit" value="open" disabled={saving || !token}>
              {saving ? "Adding…" : "Add and open"}
            </button>
            <button
              type="submit"
              value="another"
              className="button--secondary"
              disabled={saving || !token}
            >
              Add and add another
            </button>
          </div>
        </form>
      )}
    </Page>
  );
}
