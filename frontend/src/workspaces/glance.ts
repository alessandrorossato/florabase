import type { DashboardResponse } from "../collection/api";
import type { Overview as NativeOverview } from "../native-ranges/api";
import type { ProvenanceMapResponse } from "../provenance-map/api";
import type { WorkspaceHomeId } from "../shell/navigation";

/** Reads beyond the Today summary that a workspace home may add; each is optional. */
export interface GlanceExtras {
  native?: NativeOverview;
  origins?: ProvenanceMapResponse;
  suppliers?: number;
  orders?: number;
}

export interface GlanceKpi {
  label: string;
  value: string;
  hint?: string;
  href?: string;
}

const percent = (part: number, whole: number) =>
  `${String(Math.round((part / whole) * 100))}%`;

/**
 * Cross-section indicators for a workspace home: each combines what several sections hold
 * (UI-POLISH-004). Every value comes from an existing read; an indicator whose source is
 * missing or whose base is zero is left out rather than shown as 0%.
 */
export function glanceKpis(
  id: WorkspaceHomeId,
  value: DashboardResponse,
  extras: GlanceExtras,
): GlanceKpi[] {
  const { counts, overview } = value;
  const kpis: (GlanceKpi | null)[] = [];
  const germinationBase =
    overview.sowings_with_germination + overview.sowings_unknown_germination;
  const germination =
    germinationBase > 0
      ? {
          label: "Germination recorded",
          value: percent(overview.sowings_with_germination, germinationBase),
          hint: `of sowings · ${String(overview.sowings_unknown_germination)} without a count`,
          href: "#/sowings",
        }
      : null;
  if (id === "collection")
    kpis.push(
      {
        label: "Species in your material",
        value: String(overview.current_identities),
        hint: "Botanical identities with active records",
        href: "#/identities",
      },
      {
        label: "Active records",
        value: String(
          counts.active_seed_lots +
            counts.active_sowings +
            counts.active_plants +
            counts.active_plant_groups,
        ),
        hint: "seed lots, sowings, Plants and Plant groups",
      },
      germination,
      {
        label: "Work due this week",
        value: String(overview.next_seven_days),
        hint: `${String(overview.overdue)} overdue`,
        href: "#/schedule",
      },
    );
  if (id === "activity")
    kpis.push(
      {
        label: "Journal entries",
        value: String(counts.events),
        hint: "care and observations recorded",
        href: "#/events",
      },
      {
        label: "Overdue",
        value: String(overview.overdue),
        hint: `${String(overview.due_today)} due today`,
        href: "#/schedule",
      },
      {
        label: "Next 7 days",
        value: String(overview.next_seven_days),
        hint: "planned tasks",
        href: "#/schedule?view=calendar",
      },
      overview.sowings_unknown_germination > 0
        ? {
            label: "Germination to check",
            value: String(overview.sowings_unknown_germination),
            hint: "sowings without a germination count",
            href: "#/sowings",
          }
        : germination,
    );
  if (id === "explore") {
    const current = overview.current_identities;
    kpis.push(
      {
        label: "Botanical identities",
        value: String(counts.botanical_identities),
        hint: `${String(current)} in current material`,
        href: "#/identities",
      },
      current > 0
        ? {
            label: "WFO confirmed",
            value: percent(overview.identities_with_wfo, current),
            hint: `${String(overview.identities_with_wfo)} of ${String(current)} current identities`,
            href: "#/taxonomy",
          }
        : null,
      current > 0
        ? {
            label: "With a profile",
            value: percent(overview.identities_with_profile, current),
            hint: `${String(overview.identities_with_profile)} of ${String(current)} current identities`,
            href: "#/identities",
          }
        : null,
      extras.native && extras.native.represented > 0
        ? {
            label: "Native range recorded",
            value: percent(extras.native.with_range, extras.native.represented),
            hint: `${String(extras.native.with_range)} of ${String(extras.native.represented)} · ${String(extras.native.territories.length)} territories`,
            href: "#/native-ranges",
          }
        : null,
      extras.origins && extras.origins.total_provenance_sites > 0
        ? {
            label: "Origin sites mapped",
            value: String(
              extras.origins.total_provenance_sites -
                extras.origins.coordinate_less_sites,
            ),
            hint: `of ${String(extras.origins.total_provenance_sites)} recorded sites`,
            href: "#/map",
          }
        : null,
    );
  }
  if (id === "sourcing")
    kpis.push(
      extras.suppliers === undefined
        ? null
        : {
            label: "Suppliers",
            value: String(extras.suppliers),
            hint: "nurseries, seed banks and people",
            href: "#/suppliers",
          },
      extras.orders === undefined
        ? null
        : {
            label: "Orders",
            value: String(extras.orders),
            hint: "recorded purchases",
            href: "#/orders",
          },
      {
        label: "Lots without an order",
        value: String(overview.purchase_packets_without_order),
        hint: "purchased seed lots not linked to an Order",
        href: "#/seeds",
      },
      {
        label: "Species sourced and held",
        value: String(overview.current_identities),
        hint: "Botanical identities with active records",
        href: "#/identities",
      },
    );
  return kpis.filter((item): item is GlanceKpi => item !== null);
}
