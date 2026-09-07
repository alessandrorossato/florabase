import { useEffect, useId, useRef, useState } from "react";

import type { components } from "../api/schema";
import { ApiError, requestJson } from "../auth/api";
import { useAuth } from "../auth/context";

type Eligibility = components["schemas"]["PropagationReversalEligibility"];
export type CreationReversalResponse =
  | components["schemas"]["SowingCreationReversalResponse"]
  | components["schemas"]["PlantCreationReversalResponse"]
  | components["schemas"]["PlantGroupCreationReversalResponse"];
type Kind = "sowing" | "plant" | "plant_group";
const paths = {
  sowing: "sowings",
  plant: "plants",
  plant_group: "plant-groups",
};
const labels = { sowing: "sowing", plant: "plant", plant_group: "plant group" };
const entityPaths = { seed_lot: "seeds", ...paths };

export function CreationReversal({
  kind,
  id,
  lifecycle,
  revision,
  onReversed,
}: {
  kind: Kind;
  id: string;
  lifecycle: string;
  revision: string;
  onReversed: (result: CreationReversalResponse) => void;
}) {
  const auth = useAuth();
  const titleId = useId();
  const [eligibility, setEligibility] = useState<Eligibility | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [completed, setCompleted] = useState(false);
  const submitting = useRef(false);
  const feedback = useRef<HTMLParagraphElement>(null);
  const url = `/api/v1/${paths[kind]}/${encodeURIComponent(id)}`;
  useEffect(() => {
    if (lifecycle === "reversed") return;
    const controller = new AbortController();
    void requestJson<Eligibility>(`${url}/creation-reversal`, {
      signal: controller.signal,
    })
      .then((value) => {
        if (
          !["safe", "confirmation_required", "blocked"].includes(
            value.status,
          ) ||
          !Array.isArray(value.reasons) ||
          !Array.isArray(value.retained_observation_ids)
        ) {
          throw new Error("Invalid reversal eligibility response");
        }
        if (!controller.signal.aborted) setEligibility(value);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else
          setError(
            "Florabase could not check reversal eligibility. Retry before continuing.",
          );
      });
    return () => {
      controller.abort();
    };
  }, [url, lifecycle, revision, attempt, auth]);

  async function submit() {
    if (
      submitting.current ||
      !eligibility ||
      eligibility.status === "blocked" ||
      auth.state.status !== "authenticated"
    )
      return;
    if (eligibility.status === "confirmation_required" && !confirmed) return;
    submitting.current = true;
    setPending(true);
    setError("");
    try {
      const result = await requestJson<CreationReversalResponse>(
        `${url}/reverse-creation`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": auth.state.csrfToken,
          },
          body: JSON.stringify({ confirm_retained_observations: confirmed }),
        },
      );
      setCompleted(true);
      onReversed(result);
      window.setTimeout(() => feedback.current?.focus(), 0);
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else {
        setError(
          error instanceof ApiError && error.status === 409
            ? "The record changed or reversal now requires confirmation. Refresh eligibility to see the current reasons."
            : "Florabase could not reverse this creation. Refresh eligibility before retrying.",
        );
        setEligibility(null);
      }
    } finally {
      submitting.current = false;
      setPending(false);
    }
  }

  return (
    <section className="notice creation-reversal" aria-labelledby={titleId}>
      <h4 id={titleId}>Undo {labels[kind]} creation</h4>
      {lifecycle === "reversed" || completed ? (
        <p role="status" tabIndex={-1} ref={feedback}>
          Creation reversed. The source snapshot was restored. This record
          remains in history as Reversed, with its lineage and observations, and
          is no longer active. Repeating the forward action creates a new
          record.
        </p>
      ) : (
        <>
          <p>
            {kind === "sowing"
              ? "The SeedLot quantity and lifecycle"
              : "The Sowing lifecycle"}{" "}
            will return to the original recorded state. This {labels[kind]} will
            remain in history as Reversed and will no longer be active. Notes
            and lineage are retained.
          </p>
          {error && <p role="alert">{error}</p>}
          {!eligibility && !error && (
            <p role="status">Checking reversal eligibility…</p>
          )}
          {error && (
            <button
              type="button"
              disabled={pending}
              onClick={() => {
                setEligibility(null);
                setError("");
                setConfirmed(false);
                setAttempt((value) => value + 1);
              }}
            >
              Refresh eligibility
            </button>
          )}
          {eligibility && (
            <>
              {eligibility.reasons.length > 0 && (
                <ul>
                  {eligibility.reasons.map((reason, index) => (
                    <li key={`${reason.code}:${String(index)}`}>
                      {reason.message}
                      {reason.entity_id && reason.entity_type && (
                        <>
                          {" "}
                          <a
                            href={`#/${entityPaths[reason.entity_type]}/${reason.entity_id}`}
                          >
                            Open related record
                          </a>
                        </>
                      )}
                    </li>
                  ))}
                </ul>
              )}
              {eligibility.status === "confirmation_required" && (
                <label className="retained-history-confirmation">
                  <input
                    type="checkbox"
                    checked={confirmed}
                    disabled={pending}
                    onChange={(event) => {
                      setConfirmed(event.currentTarget.checked);
                    }}
                  />
                  I confirm that {eligibility.retained_observation_ids.length}{" "}
                  observation, flowering, or fruiting records will remain
                  attached to this historical result.
                </label>
              )}
              <button
                type="button"
                disabled={
                  pending ||
                  eligibility.status === "blocked" ||
                  (eligibility.status === "confirmation_required" && !confirmed)
                }
                onClick={() => {
                  void submit();
                }}
              >
                {pending ? "Reversing…" : `Undo ${labels[kind]} creation`}
              </button>
            </>
          )}
        </>
      )}
    </section>
  );
}
