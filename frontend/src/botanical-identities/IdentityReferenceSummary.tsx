import { useEffect, useState } from "react";
import { ApiError, isExpectedAuthCancellation } from "../auth/api";
import { useAuth } from "../auth/context";
import {
  getBotanicalProfile,
  listBotanicalNativeRanges,
} from "../botanical-profiles/api";
import { getExternalTaxonLink } from "./api";

/** Local reference reads only; visiting the identity never requests provider data. */
export function IdentityReferenceSummary({ id }: { id: string }) {
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();
  const [attempt, setAttempt] = useState(0);
  const [summary, setSummary] = useState<{
    description: string;
    range: string;
    source: string;
    failed: boolean;
  } | null>(null);
  useEffect(() => {
    if (!authorized) return;
    const controller = new AbortController();
    void Promise.allSettled([
      getBotanicalProfile(id, capability, controller.signal),
      listBotanicalNativeRanges(id, capability, controller.signal),
      getExternalTaxonLink(id, capability, controller.signal),
    ]).then(([profile, ranges, source]) => {
      if (controller.signal.aborted) return;
      const unavailable = (result: PromiseSettledResult<unknown>) =>
        result.status === "rejected" &&
        !(result.reason instanceof ApiError && result.reason.status === 404);
      for (const result of [profile, ranges, source])
        if (
          result.status === "rejected" &&
          result.reason instanceof ApiError &&
          result.reason.status === 401
        ) {
          sessionExpired();
          return;
        }
      if (
        [profile, ranges, source].some(
          (result) =>
            result.status === "rejected" &&
            isExpectedAuthCancellation(result.reason),
        )
      ) {
        return;
      }
      setSummary({
        description:
          profile.status === "fulfilled"
            ? (profile.value.description ??
              "No botanical description recorded.")
            : unavailable(profile)
              ? "Botanical description unavailable."
              : "No botanical description recorded.",
        range:
          ranges.status === "fulfilled"
            ? `${String(ranges.value.length)} structured native-range entries recorded`
            : "Native-range status unavailable",
        source:
          source.status === "fulfilled" && source.value
            ? `${source.value.provider_display_name} reference: ${source.value.scientific_name}${source.value.stale ? " (stale)" : ""}`
            : unavailable(source)
              ? "Botanical source status unavailable"
              : "No confirmed GBIF reference",
        failed: [profile, ranges, source].some(unavailable),
      });
    });
    return () => {
      controller.abort();
    };
  }, [authorized, capability, id, attempt, sessionExpired]);
  return (
    <section className="identity-hub-section" aria-label="Botanical summary">
      <h3>Botanical summary</h3>
      {summary ? (
        <>
          <p>
            {summary.description.length > 240
              ? `${summary.description.slice(0, 240)}…`
              : summary.description}
          </p>
          <p className="field-help">
            {summary.source} · {summary.range}
          </p>
          {summary.failed && (
            <button
              type="button"
              className="button--secondary"
              onClick={() => {
                setAttempt((n) => n + 1);
              }}
            >
              Retry botanical summary
            </button>
          )}
          <a href={`#/identities/${id}?tab=reference`}>
            Read botanical reference
          </a>
          <a
            className="identity-snapshot-map-link"
            href={`#/identities/${id}?tab=maps`}
          >
            Explore geographic evidence
          </a>
        </>
      ) : (
        <p role="status">Loading botanical summary…</p>
      )}
    </section>
  );
}
