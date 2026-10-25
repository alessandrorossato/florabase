import { useEffect, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import {
  getBotanicalProfile,
  listBotanicalNativeRanges,
} from "../botanical-profiles/api";
import { getExternalTaxonLink } from "./api";

/** Local reference reads only; visiting the identity never requests provider data. */
export function IdentityReferenceSummary({ id }: { id: string }) {
  const auth = useAuth();
  const [attempt, setAttempt] = useState(0);
  const [summary, setSummary] = useState<{
    description: string;
    range: string;
    source: string;
    failed: boolean;
  } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    void Promise.allSettled([
      getBotanicalProfile(id, controller.signal),
      listBotanicalNativeRanges(id, controller.signal),
      getExternalTaxonLink(id, controller.signal),
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
        )
          auth.sessionExpired();
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
  }, [id, attempt, auth]);
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
