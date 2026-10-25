import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { listBotanicalNativeRanges } from "../botanical-profiles/api";
import { ExternalBotanicalDataPanel } from "./ExternalBotanicalDataPanel";
import { getExternalTaxonLink, type BotanicalIdentityResponse } from "./api";

const NativeRange = lazy(() =>
  import("./IdentityNativeRange").then((m) => ({
    default: m.IdentityNativeRange,
  })),
);
const Origins = lazy(() =>
  import("./IdentityOrigins").then((m) => ({ default: m.IdentityOrigins })),
);
import {
  getCollectionProvenanceMap,
  type ProvenanceMapSite,
} from "../provenance-map/api";
import { identityOriginSites } from "./identityGeography";
import { getCachedOccurrenceEvidence } from "../occurrence-map/api";

type Evidence = "native-range" | "occurrences" | "origins";

export function IdentityMaps({
  identity,
  csrfToken,
  onEditRange,
}: {
  identity: BotanicalIdentityResponse;
  csrfToken: string;
  onEditRange: () => void;
}) {
  const auth = useAuth();
  const [open, setOpen] = useState<Evidence | null>(null);
  const inspectionHeading = useRef<HTMLHeadingElement>(null);
  const triggers = useRef<Partial<Record<Evidence, HTMLButtonElement>>>({});
  useEffect(() => {
    if (!open) return;
    const frame = requestAnimationFrame(() => {
      inspectionHeading.current?.focus({ preventScroll: true });
      inspectionHeading.current?.scrollIntoView({ block: "start" });
    });
    return () => {
      cancelAnimationFrame(frame);
    };
  }, [open]);
  const [attempt, setAttempt] = useState(0);
  const [status, setStatus] = useState<{
    range: string;
    occurrences: string;
    failed: boolean;
    origins: string;
    sites?: ProvenanceMapSite[];
    cache: string;
  } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    void Promise.allSettled([
      listBotanicalNativeRanges(identity.id, controller.signal),
      getExternalTaxonLink(identity.id, controller.signal).then(
        async (link) => ({
          link,
          cache: link
            ? await getCachedOccurrenceEvidence(identity.id, controller.signal)
            : null,
        }),
      ),
      getCollectionProvenanceMap(controller.signal),
    ]).then(([range, source, origins]) => {
      if (controller.signal.aborted) return;
      for (const result of [range, source, origins])
        if (
          result.status === "rejected" &&
          result.reason instanceof ApiError &&
          result.reason.status === 401
        )
          auth.sessionExpired();
      setStatus({
        range:
          range.status === "fulfilled"
            ? `${String(range.value.length)} structured ${range.value.length === 1 ? "entry" : "entries"} recorded`
            : "Native-range availability could not load",
        occurrences:
          source.status === "fulfilled"
            ? source.value.link
              ? `${source.value.link.provider_display_name}: ${source.value.link.scientific_name}${source.value.link.stale ? " · link needs review" : " · confirmed reference"}`
              : "No confirmed GBIF reference"
            : "Occurrence reference could not load",
        origins:
          origins.status === "fulfilled"
            ? (() => {
                const sites = identityOriginSites(
                  origins.value.sites,
                  identity.id,
                );
                return `${String(sites.length)} mapped ${sites.length === 1 ? "site" : "sites"} · ${String(sites.reduce((n, site) => n + site.records.length, 0))} direct record links`;
              })()
            : "Recorded origins could not load",
        sites:
          origins.status === "fulfilled"
            ? identityOriginSites(origins.value.sites, identity.id)
            : undefined,
        cache:
          source.status === "fulfilled" && source.value.link
            ? source.value.cache?.summary
              ? `${source.value.cache.summary.eligible_mapped_records.toLocaleString()} eligible mapped observations · ${source.value.cache.stale ? "cache needs review" : "saved evidence"}`
              : "No saved occurrence evidence"
            : "A confirmed reference is required",
        failed:
          range.status === "rejected" ||
          source.status === "rejected" ||
          origins.status === "rejected",
      });
    });
    return () => {
      controller.abort();
    };
  }, [identity.id, attempt, auth]);
  const evidence = [
    {
      key: "native-range" as const,
      title: "Native range",
      status: status?.range,
      description:
        "Recorded native-area assertions, separate from distribution prose and observations.",
      href: `#/native-ranges?mode=species&identity=${identity.id}`,
      link: "Open native ranges for this identity",
    },
    {
      key: "occurrences" as const,
      title: "Occurrence evidence",
      status: status?.occurrences,
      description:
        "Observed occurrences are not native distribution. Provider loading remains opt-in.",
      href: `#/species-distribution?identity=${identity.id}`,
      link: "Open occurrence evidence for this identity",
    },
    {
      key: "origins" as const,
      title: "Collection origins",
      status: status?.origins,
      description:
        "Direct material provenance. Storage Locations and Suppliers do not establish botanical origin.",
      href: "#/map",
      link: "Open collection origins · all identities",
    },
  ];
  return (
    <div className="identity-geography">
      <header className="identity-section-heading">
        <div>
          <h3>Geographic evidence</h3>
          <p>
            Compare three distinct evidence types. Select one to inspect its
            map.
          </p>
        </div>
      </header>
      {status?.failed && (
        <div role="alert">
          <p>Some geographic availability information is unavailable.</p>
          <button
            className="button--secondary"
            type="button"
            onClick={() => {
              setAttempt((n) => n + 1);
            }}
          >
            Retry geographic summary
          </button>
        </div>
      )}
      <div className="identity-evidence-index">
        {evidence.map((item) => (
          <section
            key={item.key}
            id={`identity-${item.key}`}
            className="identity-evidence-section"
            aria-label={item.title}
          >
            <header>
              <h4>{item.title}</h4>
              <p className="identity-evidence-status">
                {item.status ?? "Loading availability…"}
              </p>
            </header>
            <p>{item.description}</p>
            {item.key === "occurrences" && (
              <p className="field-help">{status?.cache}</p>
            )}
            {item.key === "origins" && (
              <p className="field-help">
                Mapped sites retain recorded accuracy; unlocated origins are
                omitted.
              </p>
            )}
            <div className="actions">
              <button
                className="button--secondary"
                type="button"
                aria-expanded={open === item.key}
                aria-controls="identity-geographic-inspection"
                ref={(element) => {
                  if (element) triggers.current[item.key] = element;
                }}
                onClick={() => {
                  setOpen(open === item.key ? null : item.key);
                }}
              >
                {open === item.key ? "Close" : "Inspect"}{" "}
                {item.title.toLowerCase()}
              </button>
              <a href={item.href}>{item.link}</a>
              {item.key === "native-range" && (
                <button
                  type="button"
                  className="button--secondary"
                  onClick={onEditRange}
                >
                  Edit native range
                </button>
              )}
            </div>
            {item.key === "origins" && (
              <p className="field-help">
                Preview: exact identity. Dedicated workspace: all identities; no
                exact filter is supported.
              </p>
            )}
          </section>
        ))}
      </div>
      {open && (
        <section
          id="identity-geographic-inspection"
          className="identity-map-preview"
          aria-label={`${evidence.find((item) => item.key === open)?.title ?? "Geographic"} inspection`}
        >
          <div className="identity-inspection-heading">
            <h3 ref={inspectionHeading} tabIndex={-1}>
              {evidence.find((item) => item.key === open)?.title}
            </h3>
            <button
              className="button--secondary"
              type="button"
              onClick={() => {
                setOpen(null);
                triggers.current[open]?.focus();
              }}
            >
              Close inspection
            </button>
          </div>
          <Suspense fallback={<p role="status">Loading geographic view…</p>}>
            {open === "native-range" ? (
              <NativeRange id={identity.id} />
            ) : open === "occurrences" ? (
              <ExternalBotanicalDataPanel
                identityId={identity.id}
                scientificName={identity.scientific_name}
                csrfToken={csrfToken}
                view="occurrences"
              />
            ) : (
              <Origins id={identity.id} initialSites={status?.sites} />
            )}
          </Suspense>
        </section>
      )}
    </div>
  );
}
