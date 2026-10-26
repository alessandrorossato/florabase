import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import {
  getBotanicalIdentity,
  type BotanicalIdentityResponse,
} from "../botanical-identities/api";
import { ActionButton } from "../components/Action";
import { Breadcrumbs } from "../components/CollectionUI";
import { DirectoryTools } from "../components/DirectoryTools";
import { Icon } from "../components/Icon";
import {
  BotanicalName,
  DirectorySearch,
  PageHeader,
} from "../components/ReferenceUI";
import { getTree, type Tree, type Node, type Identity } from "./api";
import { IdentityTaxonomyPanel } from "./IdentityTaxonomyPanel";
import { TreeExplorer } from "./TreeExplorer";

import { TaxonomyKpis } from "./TaxonomyKpis";
import { TaxonomyFilters } from "./TaxonomyFilters";
import { facetTree } from "./facets";
import { TaskDialog } from "../components/TaskDialog";
import { OverflowMenu } from "../components/ReferenceUI";
import "./refinement.css";
import {
  scopes,
  recordLabels as labels,
  representation,
  readState,
  taxonomyHash,
  taxonomyIdentityHash,
  type TaxonomyState,
} from "./state";
import "./taxonomy.css";
import "./explorer.css";

const major = new Set([
  "kingdom",
  "phylum",
  "class",
  "order",
  "family",
  "genus",
  "species",
  "subspecies",
  "variety",
  "form",
]);

function Branch({
  node,
  children,
  expanded,
  selected,
  toggle,
  select,
  depth,
}: {
  node: Node;
  children: Map<string | null, Node[]>;
  expanded: Set<string>;
  selected: string;
  toggle: (id: string) => void;
  select: (id: string) => void;
  depth: number;
}) {
  const id = node.taxon.source_taxon_id,
    descendants = children.get(id) ?? [],
    open = expanded.has(id);
  return (
    <li>
      <div
        className={`taxonomy-row${selected === id ? " taxonomy-row--selected" : ""}`}
      >
        {descendants.length ? (
          <button
            type="button"
            className="taxonomy-disclosure"
            aria-expanded={open}
            aria-label={`${open ? "Collapse" : "Expand"} ${node.taxon.scientific_name}`}
            onClick={() => {
              toggle(id);
            }}
          >
            <Icon name={open ? "chevron-down" : "chevron-up"} />
          </button>
        ) : (
          <span className="taxonomy-disclosure-space" />
        )}
        <button
          type="button"
          className="taxonomy-node"
          aria-label={`${node.taxon.scientific_name} ${node.taxon.rank} ${String(node.counts.represented)} ${node.counts.represented === 1 ? "identity" : "identities"}${selected === id ? " Selected" : ""}`}
          aria-pressed={selected === id}
          onClick={() => {
            select(id);
          }}
        >
          <span
            className={
              ["genus", "species", "subspecies", "variety", "form"].includes(
                node.taxon.rank,
              )
                ? "taxonomy-scientific"
                : undefined
            }
          >
            {node.taxon.scientific_name}
          </span>
          <span className="taxonomy-rank">{node.taxon.rank}</span>
          <span className="taxonomy-count">
            {node.counts.represented}
            <span className="sr-only">
              {" "}
              {node.counts.represented === 1 ? "identity" : "identities"}
            </span>
          </span>
          {selected === id && <span className="sr-only">Selected</span>}
        </button>
      </div>
      {open && descendants.length > 0 && (
        <ul
          className={`taxonomy-branches${depth > 2 ? " taxonomy-branches--deep" : ""}`}
        >
          {descendants.map((child) => (
            <Branch
              key={child.taxon.source_taxon_id}
              node={child}
              children={children}
              expanded={expanded}
              selected={selected}
              toggle={toggle}
              select={select}
              depth={depth + 1}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

function IdentityReview({
  identity,
  state,
  refresh,
}: {
  identity: Identity;
  state: TaxonomyState;
  refresh: () => void;
}) {
  const auth = useAuth();
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    data?: BotanicalIdentityResponse;
    failed?: boolean;
  } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    void getBotanicalIdentity(identity.id, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setResult({ data });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else setResult({ failed: true });
      });
    return () => {
      controller.abort();
    };
  }, [identity.id, attempt, auth]);
  const commonName = result?.data
    ? result.data.common_name
    : identity.common_name;
  return (
    <div className="taxonomy-review">
      <header className="taxonomy-inspector-heading">
        <p className="eyebrow">Botanical identity</p>
        <h3>
          <BotanicalName
            label={result?.data?.display_label ?? identity.display_label}
            scientificName={
              result?.data?.scientific_name ?? identity.scientific_name
            }
          />
        </h3>
        <p className="taxonomy-meta">
          {commonName ? `${commonName} · ` : ""}
          {representation[identity.representation]} ·{" "}
          {identity.retained_records} retained{" "}
          {identity.retained_records === 1 ? "record" : "records"}
        </p>
      </header>
      <a
        className="taxonomy-identity-link"
        href={taxonomyIdentityHash(identity.id, state, true)}
      >
        Open botanical identity →
      </a>
      {!result && <p role="status">Loading botanical identity…</p>}
      {result?.failed && (
        <div role="alert">
          <p>Could not load this botanical identity.</p>
          <ActionButton
            variant="secondary"
            onClick={() => {
              setResult(null);
              setAttempt(attempt + 1);
            }}
          >
            Retry identity
          </ActionButton>
        </div>
      )}
      {result?.data && (
        <IdentityTaxonomyPanel
          identityId={identity.id}
          updatedAt={result.data.updated_at}
          onLinkChanged={refresh}
          onIdentityRefreshed={(fresh) => {
            setResult({ data: fresh });
          }}
        />
      )}
    </div>
  );
}

function CollectionTree({
  data,
  state,
  update,
  refresh,
  fullscreen,
  toggleFullscreen,
}: {
  data: Tree;
  state: TaxonomyState;
  update: (next: TaxonomyState, typing?: boolean) => void;
  refresh: () => void;
  fullscreen: boolean;
  toggleFullscreen: () => void;
}) {
  const allRanks = state.ranks === "all";
  const [detailsOpen, setDetailsOpen] = useState(true);
  const [closed, setClosed] = useState<Set<string>>(new Set()),
    [opened, setOpened] = useState<Set<string>>(new Set());
  const inspector = useRef<HTMLElement>(null),
    browser = useRef<HTMLElement>(null);
  const byId = useMemo(
    () => new Map(data.nodes.map((node) => [node.taxon.source_taxon_id, node])),
    [data],
  );
  const visible = useMemo(() => {
    const branching = new Map<string, number>();
    for (const node of data.nodes)
      if (node.parent_id)
        branching.set(node.parent_id, (branching.get(node.parent_id) ?? 0) + 1);
    const focusIds = new Set<string>();
    if (state.branch && byId.has(state.branch)) {
      for (const node of data.nodes) {
        let current: Node | undefined = node;
        while (current) {
          if (current.taxon.source_taxon_id === state.branch) {
            focusIds.add(node.taxon.source_taxon_id);
            break;
          }
          current = current.parent_id ? byId.get(current.parent_id) : undefined;
        }
      }
      let parent: Node | undefined = byId.get(state.branch);
      while (parent) {
        focusIds.add(parent.taxon.source_taxon_id);
        parent = parent.parent_id ? byId.get(parent.parent_id) : undefined;
      }
    }
    return new Set(
      data.nodes
        .filter(
          (node) =>
            (!focusIds.size || focusIds.has(node.taxon.source_taxon_id)) &&
            (allRanks ||
              major.has(node.taxon.rank) ||
              (branching.get(node.taxon.source_taxon_id) ?? 0) > 1 ||
              node.taxon.source_taxon_id === state.taxon),
        )
        .map((node) => node.taxon.source_taxon_id),
    );
  }, [data, byId, allRanks, state]);
  const children = useMemo(() => {
    const result = new Map<string | null, Node[]>();
    for (const node of data.nodes) {
      if (!visible.has(node.taxon.source_taxon_id)) continue;
      let parent = node.parent_id;
      while (parent && !visible.has(parent))
        parent = byId.get(parent)?.parent_id ?? null;
      result.set(parent, [...(result.get(parent) ?? []), node]);
    }
    return result;
  }, [data, byId, visible]);
  const expanded = new Set(
    data.nodes
      .filter(
        (node) =>
          ![
            "order",
            "genus",
            "species",
            "subspecies",
            "variety",
            "form",
          ].includes(node.taxon.rank),
      )
      .map((node) => node.taxon.source_taxon_id),
  );
  for (const id of opened) expanded.add(id);
  for (const id of closed) expanded.delete(id);
  let ancestor = byId.get(state.taxon)?.parent_id;
  while (ancestor) {
    if (!closed.has(ancestor)) expanded.add(ancestor);
    ancestor = byId.get(ancestor)?.parent_id;
  }
  const selected = byId.get(state.taxon),
    path: Node[] = [];
  let current = selected;
  while (current) {
    path.unshift(current);
    current = current.parent_id ? byId.get(current.parent_id) : undefined;
  }
  const unresolved = data.identities.filter(
    (identity) => !identity.classification_ids?.length,
  );
  const reviewing = state.panel === "unresolved" || !data.source_available;
  const selectedIdentity = state.identity
    ? data.identities.find((identity) => identity.id === state.identity)
    : unresolved[0];
  const select = (taxon: string) => {
    setDetailsOpen(true);
    update({ ...state, taxon, panel: undefined, identity: undefined });
  };
  const genera = selected
    ? data.nodes.filter(
        (node) =>
          node.taxon.rank === "genus" &&
          node.identity_ids.some((id) => selected.identity_ids.includes(id)),
      )
    : [];
  const jump = (target: HTMLElement | null) => {
    target?.focus();
    target?.scrollIntoView({ block: "start" });
  };
  return (
    <div
      className={`taxonomy-workspace${state.view === "tree" && !reviewing ? " taxonomy-workspace--graph" : ""}${!detailsOpen ? " taxonomy-workspace--wide" : ""}`}
    >
      <section
        aria-label="Taxonomic tree"
        className="taxonomy-browser"
        ref={browser}
        tabIndex={-1}
      >
        <div
          className="taxonomy-browser-tabs"
          role="group"
          aria-label="Taxonomy presentation"
        >
          <button
            type="button"
            aria-pressed={!reviewing}
            disabled={!data.source_available}
            onClick={() => {
              update({ ...state, panel: undefined, identity: undefined });
            }}
          >
            {state.view === "tree" ? "Represented" : "Classification"}{" "}
            <span>
              {data.source_available
                ? data.counts.represented - data.unresolved
                : "—"}
            </span>
          </button>
          <button
            type="button"
            aria-pressed={reviewing}
            onClick={() => {
              update({ ...state, panel: "unresolved" });
            }}
          >
            {data.source_available ? "Needs review" : "Local identities"}{" "}
            <span>{unresolved.length}</span>
          </button>
        </div>
        {!reviewing && state.view === "tree" ? (
          <TreeExplorer
            data={data}
            state={state}
            update={update}
            select={select}
            fullscreen={fullscreen}
            toggleFullscreen={toggleFullscreen}
            detailsOpen={detailsOpen}
            toggleDetails={() => {
              setDetailsOpen((value) => !value);
            }}
          />
        ) : !reviewing ? (
          <>
            <div className="taxonomy-list-meta">
              <span>
                {data.counts.represented} represented ·{" "}
                {
                  data.nodes.filter((node) => node.taxon.rank === "family")
                    .length
                }{" "}
                placed families
              </span>
            </div>
            <div className="taxonomy-tree-tools">
              <span>Counts are distinct identities</span>
              <button
                type="button"
                onClick={() => {
                  setOpened(
                    new Set(
                      data.nodes.map((node) => node.taxon.source_taxon_id),
                    ),
                  );
                  setClosed(new Set());
                }}
              >
                Expand all
              </button>
              <button
                type="button"
                onClick={() => {
                  setOpened(new Set());
                  setClosed(
                    new Set(
                      data.nodes.map((node) => node.taxon.source_taxon_id),
                    ),
                  );
                }}
              >
                Collapse all
              </button>
            </div>
            <div className="taxonomy-tree-scroll">
              <ul
                className="taxonomy-branches taxonomy-branches--root"
                aria-label="Taxonomic classification"
              >
                {(children.get(null) ?? []).map((node) => (
                  <Branch
                    key={node.taxon.source_taxon_id}
                    node={node}
                    children={children}
                    expanded={expanded}
                    selected={state.taxon}
                    depth={0}
                    select={select}
                    toggle={(id) => {
                      if (expanded.has(id)) {
                        setClosed(new Set(closed).add(id));
                        const next = new Set(opened);
                        next.delete(id);
                        setOpened(next);
                      } else {
                        setOpened(new Set(opened).add(id));
                        const next = new Set(closed);
                        next.delete(id);
                        setClosed(next);
                      }
                    }}
                  />
                ))}
              </ul>
              {!data.nodes.length && (
                <p className="taxonomy-empty">
                  {data.counts.represented
                    ? "No identities under these filters have confirmed taxonomy placement."
                    : "No represented identities match these filters."}
                </p>
              )}
            </div>
            <div className="taxonomy-browser-footer">
              <span>{data.unresolved} unresolved</span>
              <button
                type="button"
                onClick={() => {
                  update({ ...state, panel: "unresolved" });
                }}
              >
                Review links →
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="taxonomy-list-meta">
              <span>
                {unresolved.length}{" "}
                {data.source_available
                  ? "unresolved identities"
                  : "local identities"}
              </span>
            </div>
            {data.source_available && (
              <p className="taxonomy-list-help">
                Unlinked, stale or unavailable placement. Local names stay
                unchanged.
              </p>
            )}
            <ul
              className="taxonomy-review-list"
              aria-label="Unresolved taxonomy"
            >
              {unresolved.map((identity) => (
                <li key={identity.id}>
                  <button
                    type="button"
                    aria-pressed={selectedIdentity?.id === identity.id}
                    onClick={() => {
                      update({
                        ...state,
                        panel: "unresolved",
                        identity: identity.id,
                      });
                    }}
                  >
                    <span>
                      <BotanicalName
                        label={identity.display_label}
                        scientificName={identity.scientific_name}
                      />
                      <span className="taxonomy-meta">
                        {identity.common_name
                          ? `${identity.common_name} · `
                          : ""}
                        {representation[identity.representation]}
                      </span>
                      <span className="taxonomy-meta">
                        {identity.unresolved_reason}
                      </span>
                    </span>
                    <span className="taxonomy-count">
                      {identity.retained_records}
                      <span className="sr-only"> retained records</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            {!unresolved.length && (
              <p className="taxonomy-empty">
                No unresolved identities match these filters.
              </p>
            )}
          </>
        )}
        <ActionButton
          variant="quiet"
          className="taxonomy-mobile-jump"
          onClick={() => {
            jump(inspector.current);
          }}
        >
          Inspect selection ↓
        </ActionButton>
      </section>
      <section
        aria-label="Selected taxon detail"
        className="taxonomy-inspector"
        hidden={state.view === "tree" && !reviewing && !detailsOpen}
        ref={inspector}
        tabIndex={-1}
      >
        <ActionButton
          variant="quiet"
          className="taxonomy-mobile-jump"
          onClick={() => {
            jump(browser.current);
          }}
        >
          ↑ Back to hierarchy
        </ActionButton>
        {reviewing ? (
          selectedIdentity ? (
            <IdentityReview
              key={`${selectedIdentity.id}:${String(data.source_available)}:${data.source?.version ?? ""}:${data.source?.checksum ?? ""}`}
              identity={selectedIdentity}
              state={state}
              refresh={() => {
                update({
                  ...state,
                  panel: "unresolved",
                  identity: selectedIdentity.id,
                });
                refresh();
              }}
            />
          ) : (
            <p className="taxonomy-empty">
              {state.identity
                ? "Selected identity is no longer eligible under these filters."
                : "Select an identity to review its source link."}
            </p>
          )
        ) : !selected ? (
          <div className="taxonomy-empty">
            <h3>
              {state.taxon
                ? "Selected taxon is missing or no longer eligible under these filters."
                : "Select a taxon"}
            </h3>
            <p>Inspect its source classification and represented identities.</p>
          </div>
        ) : (
          <>
            <header className="taxonomy-inspector-heading">
              <p className="eyebrow">{selected.taxon.rank}</p>
              <h3 className="taxonomy-scientific">
                {selected.taxon.scientific_name}
              </h3>
              <p className="taxonomy-meta">
                {selected.taxon.authorship || "Authorship not supplied"}
              </p>
              <span className="taxonomy-source-status">
                Accepted source concept
              </span>
            </header>
            <dl className="taxonomy-source-facts">
              <div>
                <dt>Rank</dt>
                <dd>{selected.taxon.rank}</dd>
              </div>
              <div>
                <dt>WFO identifier</dt>
                <dd>
                  <code>{selected.taxon.source_taxon_id}</code>
                </dd>
              </div>
              <div>
                <dt>Source version</dt>
                <dd>{data.source?.version}</dd>
              </div>
            </dl>
            <TaxonomyKpis
              key={
                state.taxon +
                JSON.stringify([
                  state.scope,
                  state.record,
                  state.status,
                  state.media,
                  state.q,
                ])
              }
              identities={data.identities.filter((identity) =>
                selected.identity_ids.includes(identity.id),
              )}
              state={state}
            />
            <nav
              aria-label="Source classification"
              className="taxonomy-classification"
            >
              <h4>Full classification path</h4>
              <ol>
                {path.map((node) => (
                  <li key={node.taxon.source_taxon_id}>
                    <button
                      type="button"
                      aria-current={
                        node.taxon.source_taxon_id === state.taxon
                          ? "location"
                          : undefined
                      }
                      onClick={() => {
                        select(node.taxon.source_taxon_id);
                      }}
                    >
                      {node.taxon.scientific_name}{" "}
                      <span>{node.taxon.rank}</span>
                    </button>
                  </li>
                ))}
              </ol>
            </nav>
            {genera.length > 0 && (
              <details className="taxonomy-genera">
                <summary>Represented genera ({genera.length})</summary>
                <ul>
                  {genera.map((node) => (
                    <li key={node.taxon.source_taxon_id}>
                      <button
                        type="button"
                        className="button--quiet"
                        onClick={() => {
                          select(node.taxon.source_taxon_id);
                        }}
                      >
                        {node.taxon.scientific_name}
                      </button>
                    </li>
                  ))}
                </ul>
              </details>
            )}
            <p className="taxonomy-meta taxonomy-boundary">
              Classification does not measure genetic distance or recorded
              material Lineage.
            </p>
          </>
        )}
        {state.taxon && !reviewing && (
          <button
            type="button"
            className="button--quiet taxonomy-clear"
            onClick={() => {
              select("");
            }}
          >
            Clear selected taxon
          </button>
        )}
      </section>
    </div>
  );
}

export function TaxonomyScreen() {
  const auth = useAuth();
  const fullscreenHost = useRef<HTMLDivElement>(null);
  const nativeFullscreen = useRef(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [fullscreenNotice, setFullscreenNotice] = useState("");
  const leaveFullscreen = useCallback(() => {
    setFullscreen(false);
    setFullscreenNotice("");
    if (
      document.fullscreenElement === fullscreenHost.current &&
      typeof document.exitFullscreen === "function"
    )
      void document.exitFullscreen().catch(() => {
        if (document.fullscreenElement === fullscreenHost.current)
          setFullscreenNotice("Use your browser's fullscreen control to exit.");
      });
    nativeFullscreen.current = false;
  }, []);
  const toggleFullscreen = () => {
    if (fullscreen) {
      leaveFullscreen();
      return;
    }
    const host = fullscreenHost.current;
    const fallback = () => {
      if (!host?.isConnected) return;
      setFullscreen(true);
      setFullscreenNotice(
        "Browser fullscreen unavailable; using a full viewport workspace.",
      );
    };
    if (host && typeof host.requestFullscreen === "function") {
      // Open the dialog after native fullscreen so its top layer remains above the fullscreen host.
      void host
        .requestFullscreen()
        .then(() => {
          if (host.isConnected && document.fullscreenElement === host)
            setFullscreen(true);
        })
        .catch(fallback);
    } else fallback();
  };
  useEffect(() => {
    const host = fullscreenHost.current;
    const sync = () => {
      if (document.fullscreenElement === host) nativeFullscreen.current = true;
      else if (nativeFullscreen.current) {
        nativeFullscreen.current = false;
        setFullscreen(false);
        setFullscreenNotice("");
      }
    };
    document.addEventListener("fullscreenchange", sync);
    return () => {
      document.removeEventListener("fullscreenchange", sync);
      if (
        document.fullscreenElement === host &&
        typeof document.exitFullscreen === "function"
      )
        void document.exitFullscreen().catch(() => {
          /* Navigation has removed the modal; native exit may already be complete. */
        });
    };
  }, []);
  const [state, setState] = useState(readState),
    [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    key: string;
    data?: Tree;
    error?: string;
  } | null>(null);
  const filters = useMemo(
    () => ({
      scope: state.scope,
      record: state.record,
      q: state.q,
      taxon: "",
    }),
    [state.scope, state.record, state.q],
  );
  const key = JSON.stringify(filters);
  useEffect(() => {
    const sync = () => {
      if (window.location.hash.split("?")[0] === "#/taxonomy") {
        const next = readState();
        if (next.view !== "tree") leaveFullscreen();
        setState(next);
      }
    };
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    return () => {
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("popstate", sync);
    };
  }, [leaveFullscreen]);
  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      void getTree(filters, controller.signal)
        .then((data) => {
          if (!controller.signal.aborted) setResult({ key, data });
        })
        .catch((error: unknown) => {
          if (controller.signal.aborted) return;
          if (error instanceof ApiError && error.status === 401)
            auth.sessionExpired();
          else
            setResult((previous) => ({
              key,
              data: previous?.key === key ? previous.data : undefined,
              error:
                error instanceof ApiError && error.status === 409
                  ? "Collection exceeds the taxonomy limit. Narrow the representation or record filters."
                  : "Could not load collection taxonomy.",
            }));
        });
    }, 150);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [key, filters, attempt, auth]);
  const update = (next: TaxonomyState, typing = false) => {
    const hash = taxonomyHash(next);
    if (hash !== window.location.hash)
      window.history[typing ? "replaceState" : "pushState"](null, "", hash);
    setState(next);
  };
  const current = result?.key === key ? result : null,
    rawData = current?.data;
  const data = useMemo(
    () =>
      rawData
        ? facetTree(rawData, { status: state.status, media: state.media })
        : undefined,
    [rawData, state.status, state.media],
  );
  const activeFilters = [
    ...(state.scope !== "all"
      ? [
          {
            label: "Representation",
            value:
              scopes.find((scope) => scope.value === state.scope)?.label ??
              "All represented",
            onRemove: () => {
              update({ ...state, scope: "all" });
            },
          },
        ]
      : []),
    ...state.record.map((category) => ({
      label: labels[category],
      value: "included",
      onRemove: () => {
        update({
          ...state,
          record: state.record.filter((item) => item !== category),
        });
      },
    })),
  ];
  for (const [key, label] of [
    ["branch", "Hierarchy focus"],
    ["status", "Source placement"],
    ["media", "Stored thumbnail"],
    ["through", "Tree depth"],
    ["ranks", "List ranks"],
    ["photos", "Node thumbnails"],
  ] as const) {
    const value = state[key];
    if (value)
      activeFilters.push({
        label,
        value:
          key === "branch"
            ? (rawData?.nodes.find((n) => n.taxon.source_taxon_id === value)
                ?.taxon.scientific_name ?? value)
            : value,
        onRemove: () => {
          update({ ...state, [key]: undefined });
        },
      });
  }
  const clearFilters = () => {
    update({
      ...state,
      scope: "all",
      record: [],
      branch: undefined,
      status: undefined,
      media: undefined,
      through: undefined,
      ranks: undefined,
      photos: undefined,
      panel: undefined,
      identity: undefined,
    });
  };
  const missingSource =
    !data?.source_available && data?.message?.includes("not installed");
  return (
    <div
      ref={fullscreenHost}
      className={`taxonomy-screen taxonomy-refined${state.view === "tree" ? " taxonomy-screen--tree" : ""}`}
    >
      <TaskDialog
        title="Collection taxonomy workspace"
        modal={fullscreen}
        onClose={leaveFullscreen}
        className={`taxonomy-stage${fullscreen ? " taxonomy-stage--fullscreen" : ""}`}
      >
        <Breadcrumbs items={[{ label: "Explore" }, { label: "Taxonomy" }]} />
        <PageHeader
          eyebrow=""
          title="Collection taxonomy"
          titleId="taxonomy-title"
          description="Classification of the botanical identities in your collection."
          actions={
            <DirectoryTools
              name="Taxonomy"
              search={
                <>
                  <DirectorySearch
                    id="taxonomy-query"
                    label="Search collection taxonomy"
                    placeholder="Search identities, genera, families…"
                    value={state.q}
                    hideLabel
                    maxLength={200}
                    onChange={(q) => {
                      update({ ...state, q }, true);
                    }}
                  />
                  <div
                    className="taxonomy-view-switch"
                    role="group"
                    aria-label="Taxonomy view"
                  >
                    <ActionButton
                      variant="secondary"
                      aria-pressed={state.view !== "tree"}
                      onClick={() => {
                        leaveFullscreen();
                        update({ ...state, view: undefined });
                      }}
                    >
                      List
                    </ActionButton>
                    <ActionButton
                      variant="secondary"
                      aria-pressed={state.view === "tree"}
                      onClick={() => {
                        update({ ...state, view: "tree" });
                      }}
                    >
                      Tree explorer
                    </ActionButton>
                  </div>
                </>
              }
              activeFilters={activeFilters}
              onReset={clearFilters}
              filters={
                <TaxonomyFilters data={rawData} state={state} update={update} />
              }
            />
          }
        />
        <div className="taxonomy-source-line">
          {" "}
          <div className="taxonomy-source-summary">
            <span
              className={
                data?.source_available
                  ? "taxonomy-source-status"
                  : "taxonomy-meta"
              }
            >
              {!data
                ? "Checking WFO source…"
                : data.source_available
                  ? "WFO source available"
                  : missingSource
                    ? "WFO source not installed"
                    : "WFO source unavailable"}
            </span>
            {data?.source && (
              <details>
                <summary>{data.source.version}</summary>
                <p>{data.source.citation}</p>
                <p>
                  Snapshot checksum: <code>{data.source.checksum}</code>
                </p>
                <a
                  href="https://zenodo.org/records/20782718"
                  target="_blank"
                  rel="noreferrer"
                >
                  Source release
                </a>{" "}
                ·{" "}
                <a href={data.source.license} target="_blank" rel="noreferrer">
                  CC0
                </a>
              </details>
            )}
          </div>
          <OverflowMenu
            label="About taxonomy search"
            ariaLabel="About taxonomy search"
          >
            <p>
              Collection search is separate from explicit WFO candidate
              matching. Filters retain distinct identity counts and
              source-backed classification.
            </p>
          </OverflowMenu>
        </div>
        {fullscreenNotice && (
          <p role="status" className="taxonomy-fullscreen-notice">
            {fullscreenNotice}
          </p>
        )}
        {fullscreen &&
          (!data?.source_available || state.panel === "unresolved") && (
            <ActionButton
              variant="secondary"
              className="taxonomy-fullscreen-exit"
              icon="maximize"
              onClick={leaveFullscreen}
            >
              Exit fullscreen
            </ActionButton>
          )}
        {state.view === "tree" && data && !data.source_available && (
          <p className="taxonomy-meta">
            The diagram needs the configured WFO source. Local identities and
            saved link evidence remain below; Classification remains available.
          </p>
        )}
        {!current && <p role="status">Loading collection taxonomy…</p>}
        {current?.error && (
          <div role="alert" className="taxonomy-source-notice">
            <p>{current.error}</p>
            <ActionButton
              icon="refresh"
              variant="secondary"
              onClick={() => {
                setAttempt(attempt + 1);
              }}
            >
              Retry taxonomy
            </ActionButton>
          </div>
        )}
        {data && (
          <>
            <p className="sr-only" role="status">
              {data.counts.represented} represented identities ·{" "}
              {data.unresolved} unresolved taxonomy
            </p>
            {!data.source_available && (
              <div className="taxonomy-source-notice">
                <p>
                  <strong>
                    {missingSource
                      ? "The optional WFO source is not installed."
                      : "Taxonomy source error."}
                  </strong>{" "}
                  {data.message} Local identities and retained confirmation
                  evidence remain accessible. Matching needs the local source.
                </p>
                <ActionButton
                  icon="refresh"
                  variant="quiet"
                  onClick={() => {
                    setAttempt(attempt + 1);
                  }}
                >
                  Retry source
                </ActionButton>
                <span className="taxonomy-meta">
                  Retry rechecks the configured source; it does not install WFO.
                </span>
              </div>
            )}
            <CollectionTree
              data={data}
              state={state}
              update={update}
              fullscreen={fullscreen}
              toggleFullscreen={toggleFullscreen}
              refresh={() => {
                setAttempt((value) => value + 1);
              }}
            />
          </>
        )}
      </TaskDialog>
    </div>
  );
}
