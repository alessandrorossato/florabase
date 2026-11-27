import { useEffect, useId, useState } from "react";

import { ApiError, isExpectedAuthCancellation } from "../auth/api";
import { useAuth } from "../auth/context";
import { getDashboard, type DashboardResponse } from "../collection/api";
import { Icon } from "../components/Icon";
import { PageHeader } from "../components/ReferenceUI";
import { Page } from "../components/WorkspaceUI";
import { localDay } from "../schedule/state";
import {
  workspaces,
  type Section,
  type WorkspaceHomeId,
} from "../shell/navigation";
import { sectionDescriptions } from "../shell/sectionDescriptions";
import { getNativeOverview } from "../native-ranges/api";
import { getCollectionProvenanceMap } from "../provenance-map/api";
import { listSuppliers } from "../suppliers/api";
import { listOrders } from "../orders/api";
import { glanceKpis, type GlanceExtras } from "./glance";
import "./workspace-home.css";

type Counts =
  | { status: "loading" }
  | { status: "ready"; value: DashboardResponse }
  | { status: "error" };

interface TileLink {
  label: string;
  href: string;
}

/** What a sub-section tile says. Counts come only from the Today summary; none is inferred. */
interface Tile {
  count?: (value: DashboardResponse) => { value: number; unit: string };
  detail?: (value: DashboardResponse) => string | null;
  links?: TileLink[];
  action?: TileLink;
}

const plural = (count: number, one: string, many: string) =>
  `${String(count)} ${count === 1 ? one : many}`;

const tiles: Partial<Record<Section, Tile>> = {
  seeds: {
    count: (value) => ({
      value: value.counts.active_seed_lots,
      unit: "active seed lots",
    }),
    detail: (value) =>
      value.overview.purchase_packets_without_order
        ? `${plural(value.overview.purchase_packets_without_order, "purchased lot", "purchased lots")} without an Order link`
        : null,
    action: { label: "New seed lot", href: "#/seeds?action=create" },
  },
  sowings: {
    count: (value) => ({
      value: value.counts.active_sowings,
      unit: "active sowings",
    }),
    detail: (value) =>
      value.overview.sowings_unknown_germination
        ? `${plural(value.overview.sowings_unknown_germination, "sowing", "sowings")} without a germination count`
        : null,
    action: { label: "New sowing", href: "#/sowings?action=create" },
  },
  cuttings: {},
  plants: {
    count: (value) => ({
      value: value.counts.active_plants,
      unit: "active Plants",
    }),
    detail: (value) =>
      plural(value.counts.active_plant_groups, "Plant group", "Plant groups"),
    links: [{ label: "Plant groups", href: "#/plants?type=group" }],
    action: { label: "New plant", href: "#/plants?action=create&kind=plant" },
  },
  harvests: {
    links: [
      { label: "Stored material", href: "#/harvests?tab=stored-material" },
    ],
    action: { label: "Record harvest", href: "#/harvests?action=create" },
  },
  locations: {
    action: { label: "New location", href: "#/locations?action=create" },
  },
  events: {
    count: (value) => ({ value: value.counts.events, unit: "recorded events" }),
  },
  history: {},
  schedule: {
    count: (value) => ({
      value: value.overview.due_today,
      unit: "due today",
    }),
    detail: (value) =>
      `${String(value.overview.overdue)} overdue · ${String(value.overview.next_seven_days)} in the next 7 days`,
    links: [{ label: "Calendar", href: "#/schedule?view=calendar" }],
    action: { label: "Plan work", href: "#/schedule?action=create" },
  },
  identities: {
    count: (value) => ({
      value: value.overview.current_identities,
      unit: "in current material",
    }),
    detail: (value) =>
      `${String(value.overview.identities_with_wfo)} with a confirmed WFO link`,
    action: {
      label: "New botanical identity",
      href: "#/identities?action=create",
    },
  },
  taxonomy: {},
  lineage: {},
  media: {},
  geography: {
    links: [
      { label: "Collection origins", href: "#/map" },
      { label: "Species distribution", href: "#/species-distribution" },
      { label: "Native ranges", href: "#/native-ranges" },
    ],
  },
  suppliers: {
    action: { label: "New supplier", href: "#/suppliers?action=create" },
  },
  orders: {
    action: { label: "New order", href: "#/orders?action=create" },
  },
};

function useTodaySummary(): [Counts, () => void] {
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();
  const [state, setState] = useState<Counts>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!authorized) return;
    const controller = new AbortController();
    getDashboard(capability, controller.signal, localDay())
      .then((value) => {
        if (controller.signal.aborted) return;
        // Tiles read both blocks; a summary without them counts as unavailable, not a crash.
        const complete =
          typeof value === "object" &&
          (value as Partial<DashboardResponse>).counts != null &&
          (value as Partial<DashboardResponse>).overview != null;
        setState(complete ? { status: "ready", value } : { status: "error" });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isExpectedAuthCancellation(error))
          return;
        if (error instanceof ApiError && error.status === 401) sessionExpired();
        else setState({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [attempt, authorized, capability, sessionExpired]);
  return [
    state,
    () => {
      setState({ status: "loading" });
      setAttempt((value) => value + 1);
    },
  ];
}

/**
 * Optional reads behind Explore and Sourcing indicators. Each settles on its own; a failed
 * one only leaves its indicator out, and nothing is read for Collection or Activity.
 */
function useGlanceExtras(id: WorkspaceHomeId): GlanceExtras {
  const auth = useAuth();
  const { capability } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();
  const [extras, setExtras] = useState<{ id: WorkspaceHomeId } & GlanceExtras>({
    id,
  });
  useEffect(() => {
    if (!authorized || (id !== "explore" && id !== "sourcing")) return;
    const controller = new AbortController();
    const { signal } = controller;
    const settle = (patch: GlanceExtras) => {
      if (!signal.aborted)
        setExtras((value) => ({
          ...(value.id === id ? value : { id }),
          ...patch,
        }));
    };
    const ignore = () => undefined;
    if (id === "explore") {
      getNativeOverview(
        { q: "", scope: "all", withRange: false, record: [] },
        0,
        capability,
        signal,
      ).then((native) => {
        settle({ native });
      }, ignore);
      getCollectionProvenanceMap(capability, signal).then((origins) => {
        settle({ origins });
      }, ignore);
    } else {
      listSuppliers(capability, signal).then((items) => {
        settle({ suppliers: items.length });
      }, ignore);
      listOrders("", "", 0, capability, signal, 1).then((page) => {
        settle({ orders: page.total });
      }, ignore);
    }
    return () => {
      controller.abort();
    };
  }, [authorized, capability, id]);
  return extras.id === id ? extras : {};
}

/**
 * A workspace's home: one tile per sub-section with what it holds, a count where the Today
 * summary already has one, direct links to its views and its usual first action.
 */
export function WorkspaceHome({ id }: { id: WorkspaceHomeId }) {
  const titleId = useId();
  const workspace = workspaces.find((item) => item.id === id);
  const [counts, retry] = useTodaySummary();
  const extras = useGlanceExtras(id);
  const glanceId = useId();
  if (!workspace) return null;
  const kpis =
    counts.status === "ready" ? glanceKpis(id, counts.value, extras) : [];
  const sections = workspace.destinations.filter((item) => item.section !== id);
  return (
    <Page titleId={titleId} className="workspace-home">
      <PageHeader
        title={workspace.label}
        titleId={titleId}
        eyebrow="Overview"
        description={workspace.summary}
      />
      {counts.status === "error" && (
        <p className="notice workspace-home__notice" role="status">
          Counts could not be loaded; every section is still available.{" "}
          <button type="button" className="button--quiet" onClick={retry}>
            Retry counts
          </button>
        </p>
      )}
      {kpis.length > 0 && (
        <section className="workspace-home__glance" aria-labelledby={glanceId}>
          <h3 id={glanceId}>Across {workspace.label}</h3>
          <dl>
            {kpis.map((kpi) => (
              <div key={kpi.label}>
                <dt>
                  {kpi.href ? <a href={kpi.href}>{kpi.label}</a> : kpi.label}
                </dt>
                <dd>
                  <strong>{kpi.value}</strong>
                  {kpi.hint && <span>{kpi.hint}</span>}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      )}
      <ul
        className="workspace-home__tiles"
        aria-label={`${workspace.label} sections`}
      >
        {sections.map((item) => {
          const tile = tiles[item.section] ?? {};
          const ready = counts.status === "ready" ? counts.value : null;
          const count = ready && tile.count ? tile.count(ready) : null;
          const detail = ready && tile.detail ? tile.detail(ready) : null;
          return (
            <li key={item.section} className="workspace-home__tile">
              <h3>
                <a href={`#/${item.section}`}>
                  <Icon name={item.icon} />
                  <span>{item.label}</span>
                </a>
              </h3>
              {tile.count && (
                <p className="workspace-home__count">
                  {count ? (
                    <>
                      <strong>{count.value}</strong> {count.unit}
                    </>
                  ) : counts.status === "loading" ? (
                    <span className="workspace-home__placeholder">
                      Loading count…
                    </span>
                  ) : (
                    <span className="workspace-home__placeholder">
                      Count unavailable
                    </span>
                  )}
                </p>
              )}
              <p className="workspace-home__description">
                {sectionDescriptions[item.section]}
              </p>
              {detail && <p className="workspace-home__detail">{detail}</p>}
              {(tile.links ?? tile.action) && (
                <p className="workspace-home__links">
                  {tile.links?.map((link) => (
                    <a key={link.href} href={link.href}>
                      {link.label}
                    </a>
                  ))}
                  {tile.action && (
                    <a
                      className="workspace-home__action"
                      href={tile.action.href}
                    >
                      {tile.action.label}
                    </a>
                  )}
                </p>
              )}
            </li>
          );
        })}
      </ul>
    </Page>
  );
}
