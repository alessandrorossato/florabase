import { useEffect, useState } from "react";

import { isExpectedAuthCancellation } from "../auth/api";
import { useOptionalAuth } from "../auth/context";
import { PageHeader } from "../components/ReferenceUI";
import { Page } from "../components/WorkspaceUI";
import {
  getSystemReferences,
  type ReferenceSetupIndexStatus,
  type SystemReferences,
} from "./api";
import "./settings.css";

const sources = [
  {
    name: "World Flora Online (WFO)",
    use: "Taxonomy: accepted names and classification",
    access:
      "Local reviewed snapshot; provisioned automatically in the background when enabled, or mounted manually",
    licence: "CC0",
    where: "#/taxonomy",
  },
  {
    name: "Kew WCVP",
    use: "Reviewable native-range proposals",
    access:
      "Local sealed index; provisioned automatically in the background when enabled, or mounted manually",
    licence: "CC BY 3.0",
    where: "#/native-ranges",
  },
  {
    name: "GBIF",
    use: "Reference links on botanical identities and occurrence evidence for one identity at a time",
    access:
      "Online, only when you search, confirm or refresh a GBIF link, or press Load on a confirmed link",
    licence: "Per dataset",
    where: "#/species-distribution",
  },
  {
    name: "Natural Earth",
    use: "Map boundaries for overview maps",
    access: "Bundled with Florabase, works offline",
    licence: "Public domain",
    where: "#/map",
  },
  {
    name: "OpenStreetMap tiles",
    use: "Optional street-level basemap",
    access: "Off unless the operator enables it in runtime-config.js",
    licence: "ODbL, provider policy applies",
    where: "#/map",
  },
  {
    name: "Your own data (CSV)",
    use: "Bulk import and export of collection records",
    access: "Guided import with preview; nothing is written before you confirm",
    licence: "Yours",
    where: "#/import-export",
  },
] as const;

function statusTone(index: ReferenceSetupIndexStatus): string {
  if (index.state === "ready" || (index.state === "manual" && index.available))
    return "ready";
  if (index.state === "preparing") return "preparing";
  if (index.state === "failed") return "failed";
  return "muted";
}

/** Settings → Data sources: what external data Florabase uses and the rules for adding more. */
export function DataSourcesScreen() {
  const auth = useOptionalAuth();
  const isAuthenticated = auth?.state.status === "authenticated";
  const capability = auth?.capability;
  const [references, setReferences] = useState<SystemReferences | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const loadingStatus =
    isAuthenticated && references === null && statusError === null;

  useEffect(() => {
    if (!isAuthenticated || !capability?.isAuthorized()) return;
    const controller = new AbortController();
    void getSystemReferences(capability, controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return;
        setReferences(data);
        setStatusError(null);
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted || isExpectedAuthCancellation(caught))
          return;
        setStatusError("Could not load reference index status.");
      });
    return () => {
      controller.abort();
    };
  }, [isAuthenticated, capability]);

  return (
    <Page className="settings-workspace" titleId="data-sources-heading">
      <PageHeader
        title="Data sources"
        titleId="data-sources-heading"
        eyebrow="Settings"
        description="External references Florabase uses, how they are reached, and how new sources will be added."
      />
      <div className="settings-content">
        {isAuthenticated && (
          <section
            className="settings-panel"
            aria-labelledby="sources-reference-status"
          >
            <h3 id="sources-reference-status">Reference index status</h3>
            {loadingStatus && (
              <p role="status">Checking reference index status…</p>
            )}
            {statusError && <p role="alert">{statusError}</p>}
            {references && (
              <>
                <p className="reference-status-mode">
                  Automatic background setup:{" "}
                  <strong>
                    {references.mode === "auto" ? "enabled" : "off"}
                  </strong>
                </p>
                <dl className="reference-status-list">
                  <div className="reference-status-row">
                    <dt>World Flora Online (WFO 2026-06)</dt>
                    <dd>
                      <span
                        className={`reference-status-badge reference-status-badge--${statusTone(references.wfo)}`}
                      >
                        {references.wfo.status}
                      </span>
                    </dd>
                  </div>
                  <div className="reference-status-row">
                    <dt>Kew WCVP v16</dt>
                    <dd>
                      <span
                        className={`reference-status-badge reference-status-badge--${statusTone(references.wcvp_v16)}`}
                      >
                        {references.wcvp_v16.status}
                      </span>
                    </dd>
                  </div>
                </dl>
              </>
            )}
          </section>
        )}
        <section className="settings-panel" aria-labelledby="sources-current">
          <h3 id="sources-current">Sources in use</h3>
          <div className="data-sources-table">
            <table>
              <thead>
                <tr>
                  <th scope="col">Source</th>
                  <th scope="col">Used for</th>
                  <th scope="col">How it is reached</th>
                  <th scope="col">Licence</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((source) => (
                  <tr key={source.name}>
                    <th scope="row">
                      <a href={source.where}>{source.name}</a>
                    </th>
                    <td>{source.use}</td>
                    <td>{source.access}</td>
                    <td>{source.licence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <section className="settings-panel" aria-labelledby="sources-standard">
          <h3 id="sources-standard">Integration standard (planned)</h3>
          <p>
            New references and bulk input from private datasets will follow the
            same rules as the sources above. Managing integrations from this
            page is a future increment.
          </p>
          <ul>
            <li>
              Local first: a reviewed snapshot with version, retrieval date and
              checksum, so Florabase keeps working offline.
            </li>
            <li>
              Provenance on every value: which source, which release, and when
              it was confirmed.
            </li>
            <li>
              Explicit confirmation: a source proposes, you confirm; nothing
              overwrites your own records silently.
            </li>
            <li>
              Reversible bulk input: preview, validate and report before
              writing, as the CSV import already does.
            </li>
          </ul>
        </section>
      </div>
    </Page>
  );
}
