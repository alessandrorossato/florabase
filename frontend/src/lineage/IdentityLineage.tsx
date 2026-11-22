import { useCallback, useEffect, useId, useState } from "react";

import { ApiError, isExpectedAuthCancellation, requestJson } from "../auth/api";
import { useAuth } from "../auth/context";
import { InfoDisclosure } from "../components/ContextualHelp";
import { DetailEmptyState } from "../components/DetailEmptyState";
import { Breadcrumbs } from "../components/Breadcrumbs";
import { PageHeader } from "../components/ReferenceUI";
import { LifecycleStatus } from "../components/WorkspaceUI";
import { OriginNote } from "./AncestryExplorer";
import {
  buildForest,
  forestLines,
  nodeKey,
  type GraphNode,
  type IdentityLineageGraph,
  type LineItem,
} from "./identityForest";
import {
  ancestryHref,
  lineageFallbackLabels,
  lineageKindLabels,
  lineageVerbs,
  recordHref,
} from "./useRecordedLineage";
import "./ancestry-explorer.css";
import "./identity-lineage.css";

const nameOf = (node: GraphNode) =>
  node.record.label ?? lineageFallbackLabels[node.record.kind];

function NodeCard({ node }: { node: GraphNode }) {
  const { record } = node;
  return (
    <article
      className="ancestry-node identity-lineage__node"
      data-kind={record.kind}
      data-outside={node.in_identity ? undefined : "true"}
    >
      <p className="ancestry-node__meta">
        <span>{lineageKindLabels[record.kind]}</span>
        {!node.in_identity && <span>Outside this identity</span>}
      </p>
      <a
        className="ancestry-node__name"
        href={recordHref(record.kind, record.id)}
      >
        {nameOf(node)}
      </a>
      <p className="ancestry-node__facts">
        <LifecycleStatus state={record.lifecycle} />
        {!node.in_identity && "botanical_identity" in record && (
          <span>{record.botanical_identity.display_label}</span>
        )}
      </p>
      <a
        className="ancestry-node__focus"
        href={ancestryHref(record.kind, record.id)}
        aria-label={`Explore ancestry from ${nameOf(node)}`}
      >
        Explore ancestry
      </a>
    </article>
  );
}

function Branch({ item }: { item: LineItem }) {
  const { node, parentKind } = item;
  const verb = parentKind
    ? lineageVerbs[`${parentKind}>${node.record.kind}`]
    : undefined;
  if (item.reference)
    return (
      <li>
        {verb && <span className="ancestry-verb">{verb}</span>}
        <p className="identity-lineage__reference">
          <a href={recordHref(node.record.kind, node.record.id)}>
            {nameOf(node)}
          </a>{" "}
          (shown above)
        </p>
      </li>
    );
  return (
    <li>
      {verb && <span className="ancestry-verb">{verb}</span>}
      <NodeCard node={node} />
      {item.children.length > 0 && (
        <ul className="ancestry-tree">
          {item.children.map((child) => (
            <Branch key={nodeKey(child.node)} item={child} />
          ))}
        </ul>
      )}
    </li>
  );
}

type State =
  | { status: "loading" }
  | { status: "missing" }
  | { status: "error" }
  | { status: "ready"; value: IdentityLineageGraph };

/**
 * Recorded lineage across every record of one Botanical identity: each independent start
 * with its recorded descendants, plus records explicitly linked from other identities.
 */
export function IdentityLineage({ identityId }: { identityId: string }) {
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();
  const titleId = useId();
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<State>({ status: "loading" });
  useEffect(() => {
    if (!authorized) return;
    const controller = new AbortController();
    requestJson<IdentityLineageGraph>(
      `/api/v1/lineage/identities/${identityId}/graph`,
      { capability, signal: controller.signal },
    )
      .then((value) => {
        if (!controller.signal.aborted) setState({ status: "ready", value });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isExpectedAuthCancellation(error))
          return;
        if (error instanceof ApiError && error.status === 401) {
          sessionExpired();
          return;
        }
        setState({
          status:
            error instanceof ApiError && [404, 422].includes(error.status)
              ? "missing"
              : "error",
        });
      });
    return () => {
      controller.abort();
    };
  }, [attempt, authorized, capability, identityId, sessionExpired]);
  const retry = useCallback(() => {
    setState({ status: "loading" });
    setAttempt((value) => value + 1);
  }, []);

  if (state.status !== "ready")
    return (
      <section className="ancestry-explorer" aria-labelledby={titleId}>
        <PageHeader
          eyebrow="Explore"
          title="Identity lineage"
          titleId={titleId}
        />
        {state.status === "loading" && (
          <p role="status">Loading recorded lineage…</p>
        )}
        {state.status === "missing" && (
          <DetailEmptyState>
            This botanical identity was not found.
          </DetailEmptyState>
        )}
        {state.status === "error" && (
          <div className="notice notice--error" role="alert">
            <p>Florabase could not load recorded lineage.</p>
            <button type="button" onClick={retry}>
              Retry lineage
            </button>
          </div>
        )}
      </section>
    );

  const graph = state.value;
  const forest = buildForest(graph);
  const lineItems = forestLines(forest);
  const identity = graph.botanical_identity;
  const relationships = graph.edges.length;
  return (
    <section className="ancestry-explorer" aria-labelledby={titleId}>
      <Breadcrumbs
        items={[
          { label: "Explore" },
          { label: "Lineage", href: "#/lineage" },
          { label: identity.display_label },
        ]}
      />
      <PageHeader
        eyebrow=""
        title={identity.display_label}
        titleId={titleId}
        description={`${String(graph.total)} ${graph.total === 1 ? "record" : "records"} · ${String(relationships)} recorded ${relationships === 1 ? "relationship" : "relationships"} · ${String(forest.independent.length)} without recorded relationships`}
        actions={
          <a
            className="button-link button--secondary"
            href={`#/identities/${identity.id}`}
          >
            Open identity
          </a>
        }
      />
      <InfoDisclosure label="How identity lineage is built">
        <p>
          Every Seed lot, Sowing, Plant group, Plant, vegetative lot and rooting
          attempt of this identity is listed, but they are connected only where
          a relationship was explicitly recorded. Sharing a Botanical identity
          never implies shared ancestry. Records of other identities appear only
          when they are explicitly linked, marked “Outside this identity”.
          Inactive and reversed records keep their status.
        </p>
      </InfoDisclosure>
      {graph.truncated && (
        <p className="notice" role="note">
          Showing the first {String(graph.limit)} of {String(graph.total)}{" "}
          records. Open a record’s ancestry to follow the rest.
        </p>
      )}
      {graph.total === 0 && (
        <DetailEmptyState>No records use this identity yet.</DetailEmptyState>
      )}

      {lineItems.length > 0 && (
        <section
          className="ancestry-section"
          aria-labelledby={`${titleId}-lines`}
        >
          <h3 id={`${titleId}-lines`}>Recorded lines</h3>
          <ul className="identity-lineage__roots">
            {lineItems.map((line) => (
              <li key={nodeKey(line.node)} className="identity-lineage__line">
                {line.node.in_identity && <OriginNote node={line.node} />}
                <ul className="ancestry-tree">
                  <Branch item={line} />
                </ul>
              </li>
            ))}
          </ul>
        </section>
      )}

      {forest.independent.length > 0 && (
        <section
          className="ancestry-section"
          aria-labelledby={`${titleId}-independent`}
        >
          <h3 id={`${titleId}-independent`}>Without recorded relationships</h3>
          <ul className="identity-lineage__independent">
            {forest.independent.map((node) => (
              <li key={nodeKey(node)}>
                <NodeCard node={node} />
                <OriginNote node={node} />
              </li>
            ))}
          </ul>
        </section>
      )}
    </section>
  );
}
