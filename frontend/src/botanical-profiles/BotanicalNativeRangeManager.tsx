import { useEffect, useMemo, useRef, useState } from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import {
  listGeographicPlaces,
  type GeographicPlaceResponse,
} from "../geographic-places/api";
import {
  addBotanicalNativeRange,
  listBotanicalNativeRanges,
  removeBotanicalNativeRange,
  type BotanicalNativeRangeResponse,
} from "./api";

type LoadState =
  | {
      status: "ready";
      ranges: BotanicalNativeRangeResponse[];
      places: GeographicPlaceResponse[];
    }
  | { status: "loading" | "error" };
type MutationState =
  | { status: "idle" | "saving" }
  | { status: "success" | "error"; message: string };

export function BotanicalNativeRangeManager({
  identityId,
}: {
  identityId: string;
}) {
  const auth = useAuth();
  const [load, setLoad] = useState<LoadState>({ status: "loading" });
  const [mutation, setMutation] = useState<MutationState>({ status: "idle" });
  const [selectedPlaceId, setSelectedPlaceId] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [focusPlaceId, setFocusPlaceId] = useState<string | null>(null);
  const selectorRef = useRef<HTMLSelectElement>(null);
  const feedbackRef = useRef<HTMLParagraphElement>(null);
  const addedButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      listBotanicalNativeRanges(identityId, controller.signal),
      listGeographicPlaces(controller.signal),
    ])
      .then(([ranges, places]) => {
        setLoad({ status: "ready", ranges, places });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else setLoad({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [auth, identityId, attempt]);

  useEffect(() => {
    if (mutation.status === "error") feedbackRef.current?.focus();
    if (mutation.status === "success" && focusPlaceId) {
      addedButtonRef.current?.focus();
    }
  }, [focusPlaceId, mutation]);

  const availablePlaces = useMemo(() => {
    if (load.status !== "ready") return [];
    const linked = new Set(load.ranges.map((item) => item.geographic_place_id));
    return load.places.filter(
      (place) => place.retired_at === null && !linked.has(place.id),
    );
  }, [load]);

  if (
    auth.state.status !== "authenticated" &&
    auth.state.status !== "logging-out" &&
    auth.state.status !== "logout-failed"
  )
    return null;
  const csrfToken = auth.state.csrfToken;
  const pending = mutation.status === "saving";

  async function addRange() {
    if (!selectedPlaceId || pending || load.status !== "ready") return;
    setMutation({ status: "saving" });
    try {
      const added = await addBotanicalNativeRange(
        identityId,
        selectedPlaceId,
        csrfToken,
      );
      setFocusPlaceId(added.geographic_place_id);
      setLoad({
        ...load,
        ranges: [...load.ranges, added].sort((first, second) =>
          first.geographic_place_path.localeCompare(
            second.geographic_place_path,
            undefined,
            { sensitivity: "base" },
          ),
        ),
      });
      setSelectedPlaceId("");
      setMutation({
        status: "success",
        message: `${added.geographic_place_path} was added to the native range.`,
      });
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else if (error instanceof ApiError && error.status === 409)
        setMutation({
          status: "error",
          message: "That geographic place is already in this native range.",
        });
      else if (error instanceof ApiError && error.status === 403)
        setMutation({
          status: "error",
          message:
            "Florabase could not authorize this native-range change. Refresh and try again.",
        });
      else
        setMutation({
          status: "error",
          message:
            "Florabase could not add this native range. Check the connection and try again.",
        });
    }
  }

  async function removeRange(range: BotanicalNativeRangeResponse) {
    if (pending || load.status !== "ready") return;
    setMutation({ status: "saving" });
    try {
      await removeBotanicalNativeRange(
        identityId,
        range.geographic_place_id,
        csrfToken,
      );
      setLoad({
        ...load,
        ranges: load.ranges.filter(
          (item) => item.geographic_place_id !== range.geographic_place_id,
        ),
      });
      setFocusPlaceId(null);
      setMutation({
        status: "success",
        message: `${range.geographic_place_path} was removed from the native range.`,
      });
      requestAnimationFrame(() => selectorRef.current?.focus());
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else
        setMutation({
          status: "error",
          message:
            "Florabase could not remove this native range. Check the connection and try again.",
        });
    }
  }

  return (
    <section className="native-range" aria-labelledby="native-range-title">
      <div>
        <h4 id="native-range-title">Native range</h4>
        <p>
          Named areas where this taxon is considered botanically native. These
          are reference knowledge, not collection origins or current locations.
        </p>
      </div>
      {load.status === "loading" && <p>Loading native range…</p>}
      {load.status === "error" && (
        <div className="notice notice--error" role="alert">
          <p>Florabase could not load this native range.</p>
          <button
            type="button"
            onClick={() => {
              setLoad({ status: "loading" });
              setAttempt((value) => value + 1);
            }}
          >
            Retry native range
          </button>
        </div>
      )}
      {load.status === "ready" && (
        <>
          {load.ranges.length === 0 ? (
            <p className="profile-empty">
              No structured native range recorded.
            </p>
          ) : (
            <ul className="native-range-list">
              {load.ranges.map((range) => (
                <li key={range.geographic_place_id}>
                  <div>
                    <strong>{range.geographic_place_name}</strong>
                    <small>{range.geographic_place_path}</small>
                  </div>
                  <button
                    type="button"
                    className="button--secondary"
                    disabled={pending}
                    ref={
                      focusPlaceId === range.geographic_place_id
                        ? addedButtonRef
                        : undefined
                    }
                    aria-label={`Remove ${range.geographic_place_name} from native range`}
                    onClick={() => {
                      void removeRange(range);
                    }}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className="native-range-add">
            <div className="field">
              <label htmlFor={`native-range-place-${identityId}`}>
                Geographic place
              </label>
              <select
                id={`native-range-place-${identityId}`}
                ref={selectorRef}
                disabled={pending || availablePlaces.length === 0}
                value={selectedPlaceId}
                onChange={(event) => {
                  setSelectedPlaceId(event.currentTarget.value);
                  setMutation({ status: "idle" });
                }}
              >
                <option value="">Choose an exact named area</option>
                {availablePlaces.map((place) => (
                  <option value={place.id} key={place.id}>
                    {place.name} — {place.display_path}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              disabled={pending || !selectedPlaceId}
              onClick={() => {
                void addRange();
              }}
            >
              {pending ? "Saving native range…" : "Add native range"}
            </button>
          </div>
          <p className="field-help">
            Each selection records only that exact area. Parents and children
            are not added automatically. Manage named areas in{" "}
            <a href="#/geography">Geography</a>.
          </p>
        </>
      )}
      {(mutation.status === "success" || mutation.status === "error") && (
        <p
          className={
            mutation.status === "error"
              ? "notice notice--error"
              : "notice notice--success"
          }
          role={mutation.status === "error" ? "alert" : "status"}
          ref={feedbackRef}
          tabIndex={mutation.status === "error" ? -1 : undefined}
        >
          {mutation.message}
        </p>
      )}
    </section>
  );
}
