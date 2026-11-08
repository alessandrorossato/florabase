import { useCallback, useEffect, useId, useRef, useState } from "react";

import type { components } from "../api/schema";
import { ApiError, requestJson } from "../auth/api";
import { InfoDisclosure } from "../components/ContextualHelp";
import { DetailEmptyState } from "../components/DetailEmptyState";
import { PageHeader } from "../components/ReferenceUI";
import { LifecycleStatus } from "../components/WorkspaceUI";
import { formatPartialDate } from "../events/eventData";
import {
  ancestryHref,
  lineageFallbackLabels,
  lineageKindLabels,
  lineageVerbs,
  recordHref,
} from "./useRecordedLineage";
import "./ancestry-explorer.css";

type AncestryResponse = components["schemas"]["AncestryResponse"];
type AncestryNode = components["schemas"]["AncestryNode"];
type AncestryChildren = components["schemas"]["AncestryChildren"];
export type AncestryKind = AncestryNode["record"]["kind"];

const PAGE = 25;

const originLabels: Record<NonNullable<AncestryNode["origin"]>, string> = {
  purchased: "Purchased",
  purchased_fruit: "From purchased fruit",
  self_collected: "Self-collected",
  collection_produced: "Produced from my collection",
  gift_exchange: "Gift / exchange",
  other: "Other origin",
  unknown: "Unknown origin",
};

function nameOf(node: AncestryNode) {
  return node.record.label ?? lineageFallbackLabels[node.record.kind];
}

function childrenPath(node: AncestryNode, offset: number) {
  return `/api/v1/lineage/${node.record.kind}/${node.record.id}/children?offset=${String(offset)}&limit=${String(PAGE)}`;
}

/**
 * How the oldest recorded record entered the collection. Nothing beyond it is recorded, so
 * the explorer states that instead of implying a parent.
 */
function OriginNote({ node }: { node: AncestryNode }) {
  const { origin } = node;
  let text: string;
  if (origin === "collection_produced")
    text =
      node.record.kind === "seed_lot"
        ? "Produced in the collection, but its producer was not recorded."
        : "Produced in the collection, but its source was not recorded.";
  else if (!origin || origin === "unknown")
    text = "Origin not recorded. No earlier record is known.";
  else
    text = `${originLabels[origin]}. Independently acquired; no earlier collection record.`;
  return <p className="ancestry-origin">{text}</p>;
}

/** The evidence that owns the edge from this record's recorded source to it. */
function Evidence({
  node,
  parentKind,
}: {
  node: AncestryNode;
  parentKind?: AncestryKind;
}) {
  const conversion = node.harvest_conversion;
  if (conversion)
    return (
      <p className="ancestry-evidence">
        {conversion.status === "reversed"
          ? "Reversed harvest conversion"
          : "Harvest conversion"}{" "}
        from{" "}
        <a href={`#/harvests/${conversion.harvest_id}`}>
          {conversion.harvest_label ?? "Unlabelled harvest"}
        </a>
        {" · "}
        {conversion.harvested_on
          ? formatPartialDate(conversion.harvested_on)
          : "Harvest date not recorded"}
      </p>
    );
  if (!parentKind) return null;
  const owner = lineageKindLabels[node.record.kind].toLowerCase();
  const what =
    node.record.kind === "seed_lot"
      ? "Producer"
      : parentKind === "plant_group" && node.record.kind === "plant"
        ? "Extraction"
        : "Source";
  return (
    <p className="ancestry-evidence">
      {what} recorded on this {owner}
    </p>
  );
}

function NodeCard({
  node,
  generation,
  parentKind,
  current = false,
  linkRef,
}: {
  node: AncestryNode;
  generation: number;
  parentKind?: AncestryKind;
  current?: boolean;
  linkRef?: (element: HTMLAnchorElement | null) => void;
}) {
  const { record } = node;
  return (
    <article
      className="ancestry-node"
      data-kind={record.kind}
      aria-current={current ? "true" : undefined}
    >
      <p className="ancestry-node__meta">
        <span>
          {current ? "This " : ""}
          {lineageKindLabels[record.kind]}
        </span>
        <span>Generation {generation}</span>
      </p>
      <a
        className="ancestry-node__name"
        href={recordHref(record.kind, record.id)}
        ref={linkRef}
      >
        {nameOf(node)}
      </a>
      <p className="ancestry-node__facts">
        <LifecycleStatus state={record.lifecycle} />
        {"botanical_identity" in record && (
          <span>{record.botanical_identity.display_label}</span>
        )}
      </p>
      <Evidence node={node} parentKind={parentKind} />
      {!current && (
        <a
          className="ancestry-node__focus"
          href={ancestryHref(record.kind, record.id)}
          aria-label={`Explore ancestry from ${nameOf(node)}`}
        >
          Explore from here
        </a>
      )}
    </article>
  );
}

function Verb({ from, to }: { from: AncestryKind; to: AncestryKind }) {
  const verb = lineageVerbs[`${from}>${to}`];
  return verb ? <span className="ancestry-verb">{verb}</span> : null;
}

/** A recorded production step starts the next material generation. */
const nextGeneration = (generation: number, kind: AncestryKind) =>
  kind === "seed_lot" ? generation + 1 : generation;

type Load =
  | { status: "idle" | "loading" | "error" }
  | { status: "ready"; value: AncestryChildren };

/** One page-bounded level of recorded descendants; further levels load on request. */
function Descendants({
  parent,
  initial,
  generation,
}: {
  parent: AncestryNode;
  initial: AncestryChildren;
  generation: number;
}) {
  const [items, setItems] = useState(initial.items);
  const [total, setTotal] = useState(initial.total);
  const [more, setMore] = useState<"idle" | "loading" | "error">("idle");
  const firstNew = useRef<string | null>(null);
  const links = useRef(new Map<string, HTMLAnchorElement>());
  useEffect(() => {
    if (firstNew.current) links.current.get(firstNew.current)?.focus();
    firstNew.current = null;
  }, [items]);
  async function loadMore() {
    setMore("loading");
    try {
      const page = await requestJson<AncestryChildren>(
        childrenPath(parent, items.length),
      );
      // Offset pages can overlap if records were added meanwhile; keep each record once.
      const seen = new Set(
        items.map((item) => `${item.record.kind}:${item.record.id}`),
      );
      const added = page.items.filter(
        (item) => !seen.has(`${item.record.kind}:${item.record.id}`),
      );
      firstNew.current = added[0]?.record.id ?? null;
      setItems((current) => [...current, ...added]);
      setTotal(page.total);
      setMore("idle");
    } catch {
      setMore("error");
    }
  }
  const remaining = total - items.length;
  return (
    <>
      <ul className="ancestry-tree">
        {items.map((node) => (
          <DescendantItem
            key={`${node.record.kind}:${node.record.id}`}
            node={node}
            parentKind={parent.record.kind}
            generation={nextGeneration(generation, node.record.kind)}
            linkRef={(element) => {
              if (element) links.current.set(node.record.id, element);
              else links.current.delete(node.record.id);
            }}
          />
        ))}
      </ul>
      {remaining > 0 && (
        <div className="ancestry-more">
          <button
            type="button"
            className="button--secondary"
            disabled={more === "loading"}
            onClick={() => {
              void loadMore();
            }}
          >
            {more === "loading"
              ? "Loading…"
              : remaining <= PAGE
                ? `Show ${String(remaining)} more`
                : `Show ${String(PAGE)} more of ${String(remaining)} remaining`}
          </button>
          {more === "error" && (
            <span role="alert">Descendants could not be loaded.</span>
          )}
        </div>
      )}
    </>
  );
}

function DescendantItem({
  node,
  parentKind,
  generation,
  linkRef,
}: {
  node: AncestryNode;
  parentKind: AncestryKind;
  generation: number;
  linkRef: (element: HTMLAnchorElement | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const [load, setLoad] = useState<Load>({ status: "idle" });
  const panelId = useId();
  const count = node.descendant_count;
  useEffect(() => {
    if (!open || load.status !== "loading") return;
    const controller = new AbortController();
    requestJson<AncestryChildren>(childrenPath(node, 0), {
      signal: controller.signal,
    })
      .then((value) => {
        if (!controller.signal.aborted) setLoad({ status: "ready", value });
      })
      .catch(() => {
        if (!controller.signal.aborted) setLoad({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [open, load.status, node]);
  return (
    <li>
      <Verb from={parentKind} to={node.record.kind} />
      <NodeCard
        node={node}
        generation={generation}
        parentKind={parentKind}
        linkRef={linkRef}
      />
      {count > 0 && (
        <button
          type="button"
          className="button--quiet ancestry-toggle"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => {
            setOpen(!open);
            if (!open && load.status !== "ready")
              setLoad({ status: "loading" });
          }}
        >
          {`${open ? "Hide" : "Show"} ${String(count)} recorded ${count === 1 ? "descendant" : "descendants"}`}{" "}
          <span className="sr-only">of {nameOf(node)}</span>
        </button>
      )}
      {count > 0 && (
        // Hidden, not unmounted, so collapsing keeps loaded pages and nested expansions.
        <div id={panelId} hidden={!open}>
          {load.status === "loading" && (
            <p role="status">Loading descendants…</p>
          )}
          {load.status === "error" && (
            <p className="notice notice--error" role="alert">
              Descendants could not be loaded.{" "}
              <button
                type="button"
                className="button--quiet"
                onClick={() => {
                  setLoad({ status: "loading" });
                }}
              >
                Retry
              </button>
            </p>
          )}
          {load.status === "ready" && (
            <Descendants
              parent={node}
              initial={load.value}
              generation={generation}
            />
          )}
        </div>
      )}
    </li>
  );
}

type State =
  | { status: "loading" }
  | { status: "missing" }
  | { status: "error" }
  | { status: "ready"; value: AncestryResponse };

/**
 * Material ancestry centred on one record: its explicit recorded upstream chain, then its
 * recorded descendants, expanded progressively. Nothing is inferred from shared identity,
 * Location, taxonomy or photographs. This is not taxonomy or phylogeny.
 */
export function AncestryExplorer({
  kind,
  id,
}: {
  kind: AncestryKind;
  id: string;
}) {
  const titleId = useId();
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<State>({ status: "loading" });
  useEffect(() => {
    // App keys this page by record, so a new focus always mounts in its loading state.
    const controller = new AbortController();
    requestJson<AncestryResponse>(
      `/api/v1/lineage/${kind}/${id}?limit=${String(PAGE)}`,
      { signal: controller.signal },
    )
      .then((value) => {
        if (!controller.signal.aborted) setState({ status: "ready", value });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
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
  }, [kind, id, attempt]);
  const retry = useCallback(() => {
    setState({ status: "loading" });
    setAttempt((value) => value + 1);
  }, []);

  if (state.status !== "ready")
    return (
      <section className="ancestry-explorer" aria-labelledby={titleId}>
        <PageHeader
          eyebrow="Material ancestry"
          title={`${lineageKindLabels[kind]} ancestry`}
          titleId={titleId}
        />
        {state.status === "loading" && (
          <p role="status">Loading recorded ancestry…</p>
        )}
        {state.status === "missing" && (
          <DetailEmptyState>This record was not found.</DetailEmptyState>
        )}
        {state.status === "error" && (
          <div className="notice notice--error" role="alert">
            <p>Florabase could not load recorded ancestry.</p>
            <button type="button" onClick={retry}>
              Retry ancestry
            </button>
          </div>
        )}
      </section>
    );

  const { focus, ancestors, children } = state.value;
  // The API walks nearest-first; material flows oldest-first.
  const chain = [...ancestors].reverse();
  const oldest = chain[0] ?? focus;
  const generations: number[] = [];
  [...chain, focus].forEach((node, index) => {
    generations.push(
      index === 0
        ? 1
        : nextGeneration(generations[index - 1], node.record.kind),
    );
  });
  const focusGeneration = generations[chain.length];
  return (
    <section className="ancestry-explorer" aria-labelledby={titleId}>
      <PageHeader
        eyebrow="Material ancestry"
        title={nameOf(focus)}
        titleId={titleId}
        description={`${lineageKindLabels[focus.record.kind]} · recorded material relationships only`}
        actions={
          <a
            className="button-link button--secondary"
            href={recordHref(focus.record.kind, focus.record.id)}
          >
            Open {lineageKindLabels[focus.record.kind].toLowerCase()}
          </a>
        }
      />
      <InfoDisclosure label="How ancestry is recorded">
        <p>
          Only explicit collection records are shown: a Sowing’s source Seed
          lot, a Plant or Plant group’s source Sowing, an extraction from a
          Plant group and a Seed lot’s recorded producer. A shared Botanical
          identity, Location, taxonomy or photograph never implies ancestry.
          Reversed and inactive records stay visible with their status.
          Generations count recorded seed production steps; they are not genetic
          generations.
        </p>
      </InfoDisclosure>

      <section
        className="ancestry-section"
        aria-labelledby={`${titleId}-origin`}
      >
        <h3 id={`${titleId}-origin`}>Recorded origin</h3>
        <OriginNote node={oldest} />
        <ol className="ancestry-chain" aria-label="Recorded upstream path">
          {chain.map((node, index) => (
            <li key={`${node.record.kind}:${node.record.id}`}>
              {index > 0 && (
                <Verb
                  from={chain[index - 1].record.kind}
                  to={node.record.kind}
                />
              )}
              <NodeCard
                node={node}
                generation={generations[index]}
                parentKind={chain[index - 1]?.record.kind}
              />
            </li>
          ))}
          <li>
            {chain.length > 0 && (
              <Verb
                from={chain[chain.length - 1].record.kind}
                to={focus.record.kind}
              />
            )}
            <NodeCard
              node={focus}
              generation={focusGeneration}
              parentKind={chain[chain.length - 1]?.record.kind}
              current
            />
          </li>
        </ol>
      </section>

      <section
        className="ancestry-section"
        aria-labelledby={`${titleId}-descendants`}
      >
        <h3 id={`${titleId}-descendants`}>Recorded descendants</h3>
        {children.total === 0 ? (
          <DetailEmptyState>No recorded descendants.</DetailEmptyState>
        ) : (
          <Descendants
            parent={focus}
            initial={children}
            generation={focusGeneration}
          />
        )}
      </section>
    </section>
  );
}
