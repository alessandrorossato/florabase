import { useEffect, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { getNativeSelection, type SelectedRanges } from "../native-ranges/api";
import { loadGeometry } from "../native-ranges/geometry";
import {
  NativeCoverageMap,
  type GeometryState,
} from "../native-ranges/NativeCoverageMap";
import { recordCategories } from "../saved-views/state";
import "../native-ranges/native-ranges.css";

export function IdentityNativeRange({ id }: { id: string }) {
  const auth = useAuth();
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    data?: SelectedRanges;
    missing?: boolean;
    failed?: boolean;
  } | null>(null);
  const [geometry, setGeometry] = useState<GeometryState>({
    status: "loading",
  });
  useEffect(() => {
    const controller = new AbortController();
    void getNativeSelection(
      id,
      { q: "", scope: "all", withRange: false, record: [...recordCategories] },
      0,
      controller.signal,
    )
      .then((data) => {
        if (!controller.signal.aborted) setResult({ data });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else
          setResult(
            error instanceof ApiError && error.status === 404
              ? { missing: true }
              : { failed: true },
          );
      });
    void loadGeometry()
      .then((data) => {
        if (!controller.signal.aborted) setGeometry({ status: "ready", data });
      })
      .catch(() => {
        if (!controller.signal.aborted) setGeometry({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [id, attempt, auth]);
  function retry() {
    setResult(null);
    setGeometry({ status: "loading" });
    setAttempt((n) => n + 1);
  }
  if (result?.missing)
    return (
      <p>
        The native-range map currently covers identities represented in the
        collection. Use Edit native range for this reference-only identity.
      </p>
    );
  if (result?.failed)
    return (
      <div role="alert">
        <p>Could not load structured native-range evidence.</p>
        <button type="button" onClick={retry}>
          Retry native-range evidence
        </button>
      </div>
    );
  if (!result?.data) return <p role="status">Loading native-range evidence…</p>;
  const data = result.data;
  return (
    <section
      className="native-ranges identity-native-preview"
      aria-label="Identity native-range evidence"
    >
      {data.total === 0 ? (
        <p>
          No structured native range is recorded. Distribution prose and
          occurrence records are not native-range assertions.
        </p>
      ) : (
        <>
          <NativeCoverageMap
            territories={data.territories.map((territory) => ({
              ...territory,
              identity_ids: [id],
            }))}
            identities={[data.identity]}
            comparisonIds={[id]}
            scopeLabel="Current botanical identity"
            geometry={geometry}
            selected
            retry={retry}
          />
          <h4>Recorded areas</h4>
          <ul>
            {data.ranges.map((range) => (
              <li key={range.id}>{range.display_path}</li>
            ))}
          </ul>
          {data.total > data.ranges.length && (
            <p>
              Showing {data.ranges.length} of {data.total} recorded areas. Open
              Native ranges for the complete evidence list.
            </p>
          )}
        </>
      )}
    </section>
  );
}
