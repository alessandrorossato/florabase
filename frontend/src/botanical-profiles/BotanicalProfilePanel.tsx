import { useEffect, useRef, useState, type SyntheticEvent } from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { BotanicalNativeRangeManager } from "./BotanicalNativeRangeManager";
import {
  getBotanicalProfile,
  putBotanicalProfile,
  type BotanicalProfilePut,
  type BotanicalProfileResponse,
} from "./api";

const sections = [
  { field: "description", label: "Description" },
  { field: "origin_distribution", label: "Origin & distribution" },
  { field: "cultivation", label: "Cultivation" },
  { field: "uses", label: "Uses" },
  { field: "warnings", label: "Warnings" },
] as const;

type FieldName = (typeof sections)[number]["field"];
type ProfileValues = Record<FieldName, string>;
type LoadState =
  | { status: "loading" }
  | { status: "ready"; profile: BotanicalProfileResponse | null }
  | { status: "error"; message: string };
type SaveState =
  | { status: "idle" }
  | { status: "saving" }
  | { status: "saved"; message: string }
  | { status: "error"; message: string };

const emptyValues: ProfileValues = {
  description: "",
  origin_distribution: "",
  cultivation: "",
  uses: "",
  warnings: "",
};

function valuesFromProfile(
  profile: BotanicalProfileResponse | null,
): ProfileValues {
  return {
    description: profile?.description ?? "",
    origin_distribution: profile?.origin_distribution ?? "",
    cultivation: profile?.cultivation ?? "",
    uses: profile?.uses ?? "",
    warnings: profile?.warnings ?? "",
  };
}

function isProfileNotFound(error: ApiError): boolean {
  if (error.status !== 404 || typeof error.body !== "object" || !error.body)
    return false;
  const detail = (error.body as { detail?: unknown }).detail;
  return (
    typeof detail === "object" &&
    detail !== null &&
    (detail as { code?: unknown }).code === "botanical_profile_not_found"
  );
}

export function BotanicalProfilePanel({ identityId }: { identityId: string }) {
  const auth = useAuth();
  const [loadState, setLoadState] = useState<LoadState>({ status: "loading" });
  const [saveState, setSaveState] = useState<SaveState>({ status: "idle" });
  const [values, setValues] = useState<ProfileValues>(emptyValues);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const feedbackRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    void getBotanicalProfile(identityId, controller.signal)
      .then((profile) => {
        setValues(valuesFromProfile(profile));
        setLoadState({ status: "ready", profile });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401) {
          auth.sessionExpired();
        } else if (error instanceof ApiError && isProfileNotFound(error)) {
          setValues(emptyValues);
          setLoadState({ status: "ready", profile: null });
        } else {
          setLoadState({
            status: "error",
            message:
              "Florabase could not load this botanical profile. Check the connection and try again.",
          });
        }
      });
    return () => {
      controller.abort();
    };
  }, [auth, identityId, loadAttempt]);

  useEffect(() => {
    if (saveState.status === "error") feedbackRef.current?.focus();
  }, [saveState]);

  if (
    auth.state.status !== "authenticated" &&
    auth.state.status !== "logging-out" &&
    auth.state.status !== "logout-failed"
  ) {
    return null;
  }
  const csrfToken = auth.state.csrfToken;

  async function save(event: SyntheticEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (saveState.status === "saving") return;
    setSaveState({ status: "saving" });
    const payload: BotanicalProfilePut = { ...values };
    try {
      const profile = await putBotanicalProfile(identityId, payload, csrfToken);
      if (profile === undefined) {
        setValues(emptyValues);
        setLoadState({ status: "ready", profile: null });
        setSaveState({
          status: "saved",
          message: "Botanical profile cleared.",
        });
      } else {
        setValues(valuesFromProfile(profile));
        setLoadState({ status: "ready", profile });
        setSaveState({ status: "saved", message: "Botanical profile saved." });
      }
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401) {
        auth.sessionExpired();
      } else if (error instanceof ApiError && error.status === 422) {
        setSaveState({
          status: "error",
          message:
            "Add profile text or a structured native range, or leave the profile absent.",
        });
      } else if (error instanceof ApiError && error.status === 403) {
        setSaveState({
          status: "error",
          message:
            "Florabase could not authorize this profile change. Refresh the page and try again.",
        });
      } else {
        setSaveState({
          status: "error",
          message:
            "Florabase could not save this botanical profile. Check the connection and try again.",
        });
      }
    }
  }

  return (
    <section
      aria-labelledby="botanical-profile-title"
      className="profile-panel"
    >
      <div className="profile-heading">
        <p className="eyebrow">Reference knowledge</p>
        <h3 id="botanical-profile-title">Botanical profile</h3>
        <p>General reference knowledge for this botanical identity.</p>
        <p>
          This is separate from observations about particular plants, seeds, or
          collection events.
        </p>
      </div>

      {loadState.status === "loading" && (
        <p aria-live="polite" className="notice">
          Loading botanical profile…
        </p>
      )}
      {loadState.status === "error" && (
        <div className="notice notice--error" role="alert">
          <p>{loadState.message}</p>
          <button
            type="button"
            onClick={() => {
              setLoadState({ status: "loading" });
              setSaveState({ status: "idle" });
              setLoadAttempt((attempt) => attempt + 1);
            }}
          >
            Retry profile
          </button>
        </div>
      )}
      {loadState.status === "ready" && (
        <>
          {loadState.profile === null ? (
            <div className="profile-empty">
              <h4>No profile yet</h4>
              <p>
                Add any useful section when reference knowledge is available.
              </p>
            </div>
          ) : (
            <div
              className="profile-content"
              aria-label="Saved botanical profile"
            >
              {sections.map(({ field, label }) => {
                const content = loadState.profile?.[field];
                return content ? (
                  <section key={field}>
                    <h4>{label}</h4>
                    <p>{content}</p>
                  </section>
                ) : null;
              })}
            </div>
          )}

          <form
            aria-busy={saveState.status === "saving"}
            className="profile-form"
            onSubmit={(event) => {
              void save(event);
            }}
          >
            <h4>{loadState.profile ? "Edit profile" : "Add profile"}</h4>
            <p>
              Text sections are optional. A profile is retained while it has
              text or structured native-range knowledge.
            </p>
            {sections.map(({ field, label }) => (
              <div className="field" key={field}>
                <label htmlFor={`profile-${field}`}>{label}</label>
                <textarea
                  id={`profile-${field}`}
                  name={field}
                  maxLength={20000}
                  rows={field === "description" ? 6 : 4}
                  value={values[field]}
                  disabled={saveState.status === "saving"}
                  aria-describedby={
                    field === "cultivation"
                      ? "profile-cultivation-hint"
                      : undefined
                  }
                  onChange={(event) => {
                    setValues((current) => ({
                      ...current,
                      [field]: event.target.value,
                    }));
                    if (saveState.status !== "idle")
                      setSaveState({ status: "idle" });
                  }}
                />
                {field === "cultivation" && (
                  <small id="profile-cultivation-hint">
                    General cultivation guidance, not measurements or outcomes
                    from your own plants.
                  </small>
                )}
              </div>
            ))}
            <button type="submit" disabled={saveState.status === "saving"}>
              {saveState.status === "saving"
                ? "Saving profile…"
                : "Save profile"}
            </button>
          </form>
          <BotanicalNativeRangeManager identityId={identityId} />
          {saveState.status === "saved" && (
            <p className="notice notice--success" role="status">
              {saveState.message}
            </p>
          )}
          {saveState.status === "error" && (
            <div
              className="notice notice--error"
              role="alert"
              ref={feedbackRef}
              tabIndex={-1}
            >
              <p>{saveState.message}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}
