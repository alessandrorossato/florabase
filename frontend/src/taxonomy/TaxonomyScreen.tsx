import { useEffect, useMemo, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { PageHeader } from "../components/ReferenceUI";
import { recordCategories } from "../saved-views/state";
import { getTree, type Tree, type Node, type Identity } from "./api";
import { readState, taxonomyHash, type TaxonomyState } from "./state";
import "./taxonomy.css";

const scopes = [
  { value: "all", label: "All represented" },
  { value: "living", label: "Living" },
  { value: "current", label: "Current" },
  { value: "historical", label: "Historical" },
] as const;
const labels = {
  seed_lot: "Seeds",
  sowing: "Sowings",
  plant: "Plants",
  plant_group: "Plant groups",
  stored_material: "Stored material",
};
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

export function IdentityList({ identities }: { identities: Identity[] }) {
  return (
    <ul className="taxonomy-identities">
      {identities.map((identity) => (
        <li key={identity.id}>
          <a href={`#/identities/${identity.id}`}>{identity.display_label}</a>
          {identity.common_name && <span> · {identity.common_name}</span>}
          <span className="taxonomy-meta">{identity.representation}</span>
          {identity.synonym_of && (
            <p>
              WFO treats this linked name as a synonym of {identity.synonym_of}.
            </p>
          )}
          {identity.unresolved_reason && (
            <>
              <p>{identity.unresolved_reason}</p>
              <a href={`#/identities/${identity.id}?tab=taxonomy`}>
                Link taxonomy source
              </a>
            </>
          )}
        </li>
      ))}
    </ul>
  );
}

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
  const id = node.taxon.source_taxon_id;
  const descendants = children.get(id) ?? [];
  const open = expanded.has(id);
  return (
    <li>
      <div
        className={`taxonomy-row${selected === id ? " taxonomy-row--selected" : ""}`}
      >
        {descendants.length > 0 && (
          <button
            type="button"
            className="taxonomy-disclosure"
            aria-expanded={open}
            aria-label={`${open ? "Collapse" : "Expand"} ${node.taxon.scientific_name}`}
            onClick={() => {
              toggle(id);
            }}
          >
            {open ? "−" : "+"}
          </button>
        )}
        <button
          type="button"
          className="taxonomy-node"
          aria-pressed={selected === id}
          onClick={() => {
            select(id);
          }}
        >
          <span>{node.taxon.scientific_name}</span>{" "}
          <span className="taxonomy-meta">
            {node.taxon.rank} · {node.counts.represented}{" "}
            {node.counts.represented === 1 ? "identity" : "identities"}
            {selected === id && " · Selected"}
          </span>
        </button>
      </div>
      {open && descendants.length > 0 && (
        <ul
          className={
            depth > 2
              ? "taxonomy-branches taxonomy-branches--deep"
              : "taxonomy-branches"
          }
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

function CollectionTree({
  data,
  state,
  select,
}: {
  data: Tree;
  state: TaxonomyState;
  select: (id: string) => void;
}) {
  const [allRanks, setAllRanks] = useState(false);
  const [closed, setClosed] = useState<Set<string>>(new Set());
  const [opened, setOpened] = useState<Set<string>>(new Set());
  const byId = useMemo(
    () => new Map(data.nodes.map((node) => [node.taxon.source_taxon_id, node])),
    [data],
  );
  const visible = useMemo(() => {
    const branching = new Map<string, number>();
    for (const node of data.nodes)
      if (node.parent_id)
        branching.set(node.parent_id, (branching.get(node.parent_id) ?? 0) + 1);
    return new Set(
      data.nodes
        .filter(
          (node) =>
            allRanks ||
            major.has(node.taxon.rank) ||
            (branching.get(node.taxon.source_taxon_id) ?? 0) > 1 ||
            node.taxon.source_taxon_id === state.taxon,
        )
        .map((node) => node.taxon.source_taxon_id),
    );
  }, [data, allRanks, state]);
  const children = useMemo(() => {
    const result = new Map<string | null, Node[]>();
    for (const node of data.nodes) {
      if (!visible.has(node.taxon.source_taxon_id)) continue;
      let parent = node.parent_id;
      while (parent && !visible.has(parent))
        parent = byId.get(parent)?.parent_id ?? null;
      const group = result.get(parent) ?? [];
      group.push(node);
      result.set(parent, group);
    }
    return result;
  }, [data, byId, visible]);
  const expanded = new Set(
    data.nodes
      .filter(
        (node) =>
          !["genus", "species", "subspecies", "variety", "form"].includes(
            node.taxon.rank,
          ),
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
  const selected = byId.get(state.taxon);
  const detail = selected
    ? data.identities.filter((identity) =>
        selected.identity_ids.includes(identity.id),
      )
    : [];
  const genera = selected
    ? data.nodes.filter(
        (node) =>
          node.taxon.rank === "genus" &&
          node.identity_ids.some((id) => selected.identity_ids.includes(id)),
      )
    : [];
  return (
    <div className="taxonomy-workspace">
      <section aria-label="Taxonomic tree" className="taxonomy-panel">
        <h2>Taxonomic tree</h2>
        <label className="taxonomy-ranks">
          <input
            type="checkbox"
            checked={allRanks}
            onChange={(event) => {
              setAllRanks(event.target.checked);
            }}
          />
          Show every source rank
        </label>
        <p className="taxonomy-meta">
          Major and branching ranks are emphasized. Full source paths remain in
          node details.
        </p>
        <ul className="taxonomy-branches taxonomy-branches--root">
          {(children.get(null) ?? []).map((node) => (
            <Branch
              key={node.taxon.source_taxon_id}
              node={node}
              children={children}
              expanded={expanded}
              selected={state.taxon}
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
              select={select}
              depth={0}
            />
          ))}
        </ul>
      </section>
      <section aria-label="Selected taxon detail" className="taxonomy-panel">
        {!selected ? (
          <p>
            {state.taxon
              ? "Selected taxon is missing or no longer eligible under these filters."
              : "Select a taxon to inspect its represented identities."}
          </p>
        ) : (
          <>
            <h2>{selected.taxon.scientific_name}</h2>
            <p>
              {selected.taxon.rank} · {selected.taxon.source_taxon_id}
            </p>
            <p>
              {selected.counts.represented} represented identities ·{" "}
              {selected.counts.living} Living · {selected.counts.current}{" "}
              Current · {selected.counts.historical} Historical
            </p>
            <h3>Source classification</h3>
            <ol className="taxonomy-path">
              {(() => {
                const path: Node[] = [];
                let current: Node | undefined = selected;
                while (current) {
                  path.unshift(current);
                  current = current.parent_id
                    ? byId.get(current.parent_id)
                    : undefined;
                }
                return path.map((node) => (
                  <li key={node.taxon.source_taxon_id}>
                    <button
                      type="button"
                      className="button--secondary"
                      onClick={() => {
                        select(node.taxon.source_taxon_id);
                      }}
                    >
                      {node.taxon.scientific_name}{" "}
                      <span className="taxonomy-meta">{node.taxon.rank}</span>
                    </button>
                  </li>
                ));
              })()}
            </ol>
            {genera.length > 0 && (
              <>
                <h3>Represented genera</h3>
                <ul>
                  {genera.map((node) => (
                    <li key={node.taxon.source_taxon_id}>
                      <button
                        type="button"
                        className="button--secondary"
                        onClick={() => {
                          select(node.taxon.source_taxon_id);
                        }}
                      >
                        {node.taxon.scientific_name}
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            )}
            <h3>Represented identities</h3>
            <IdentityList identities={detail} />
          </>
        )}
        {state.taxon && (
          <button
            type="button"
            className="button--secondary"
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
  const [state, setState] = useState(readState);
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    key: string;
    data?: Tree;
    error?: string;
  } | null>(null);
  const filters = useMemo(
    () => ({ scope: state.scope, record: state.record, q: state.q, taxon: "" }),
    [state.scope, state.record, state.q],
  );
  const key = JSON.stringify({
    scope: state.scope,
    record: state.record,
    q: state.q,
    attempt,
  });
  useEffect(() => {
    const sync = () => {
      if (window.location.hash.split("?")[0] === "#/taxonomy")
        setState(readState());
    };
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    return () => {
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("popstate", sync);
    };
  }, []);
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
            setResult({
              key,
              error:
                error instanceof ApiError && error.status === 409
                  ? "Collection exceeds the taxonomy limit. Narrow the filters."
                  : "Could not load collection taxonomy.",
            });
        });
    }, 150);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [key, filters, auth]);
  const update = (next: TaxonomyState, typing = false) => {
    const hash = taxonomyHash(next);
    if (hash !== window.location.hash) {
      if (typing) window.history.replaceState(null, "", hash);
      else window.history.pushState(null, "", hash);
    }
    setState(next);
  };
  const current = result?.key === key ? result : null;
  const data = current?.data;
  return (
    <div className="taxonomy-screen">
      <PageHeader
        eyebrow="Explore"
        title="Collection taxonomy"
        titleId="taxonomy-title"
        actions={null}
        description="Explore the classification of botanical identities represented in your collection."
      />
      <p>
        Classification describes taxonomy. It does not measure genetic distance
        or recorded material Lineage.
      </p>
      <div className="actions" aria-label="Collection representation">
        {scopes.map((scope) => (
          <button
            key={scope.value}
            type="button"
            aria-pressed={state.scope === scope.value}
            onClick={() => {
              update({ ...state, scope: scope.value });
            }}
          >
            {scope.label}
          </button>
        ))}
      </div>
      <fieldset className="taxonomy-categories">
        <legend>Collection records</legend>
        {recordCategories.map((category) => (
          <label key={category}>
            <input
              type="checkbox"
              checked={state.record.includes(category)}
              onChange={(event) => {
                update({
                  ...state,
                  record: event.target.checked
                    ? [...state.record, category]
                    : state.record.filter((item) => item !== category),
                });
              }}
            />
            {labels[category]}
          </label>
        ))}
      </fieldset>
      <label className="taxonomy-search">
        Search collection taxonomy
        <input
          type="search"
          maxLength={200}
          value={state.q}
          onChange={(event) => {
            update({ ...state, q: event.target.value }, true);
          }}
        />
      </label>
      {!current && <p role="status">Loading collection taxonomy…</p>}
      {current?.error && (
        <div role="alert">
          <p>{current.error}</p>
          <button
            type="button"
            onClick={() => {
              setAttempt(attempt + 1);
            }}
          >
            Retry taxonomy
          </button>
        </div>
      )}
      {data && (
        <>
          {data.source && (
            <p className="taxonomy-meta">
              Taxonomy source:{" "}
              <a
                href="https://zenodo.org/records/20782718"
                target="_blank"
                rel="noreferrer"
              >
                World Flora Online — {data.source.version}
              </a>{" "}
              ·{" "}
              <a href={data.source.license} target="_blank" rel="noreferrer">
                CC0
              </a>
            </p>
          )}
          <p role="status">
            {data.counts.represented} represented identities · {data.unresolved}{" "}
            unresolved taxonomy
          </p>
          {!data.source_available && (
            <div className="notice">
              <p>Taxonomy source unavailable. {data.message}</p>
              <p>Collection records and botanical identities remain usable.</p>
              <button
                type="button"
                onClick={() => {
                  setAttempt(attempt + 1);
                }}
              >
                Retry source
              </button>
            </div>
          )}
          {data.counts.represented === 0 && (
            <p>No represented identities match these filters.</p>
          )}
          {data.source_available &&
            data.nodes.length === 0 &&
            data.counts.represented > 0 && (
              <p>
                No identities under these filters have confirmed taxonomy
                placement.
              </p>
            )}
          {data.source_available && (
            <CollectionTree
              data={data}
              state={state}
              select={(taxon) => {
                update({ ...state, taxon });
              }}
            />
          )}
          {data.unresolved > 0 && (
            <section
              className="taxonomy-panel"
              aria-label="Unresolved taxonomy"
            >
              <h2>Unresolved taxonomy ({data.unresolved})</h2>
              <IdentityList
                identities={data.identities.filter(
                  (identity) => !(identity.classification_ids ?? []).length,
                )}
              />
            </section>
          )}
        </>
      )}
    </div>
  );
}
