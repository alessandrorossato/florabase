import { geographyRoute, type GeographyView } from "./geography/routes";
import {
  collectionPageParent,
  openCollectionPage,
} from "./components/recordNavigation";
import { RecordPresentationProvider } from "./components/RecordPresentationProvider";
import {
  lazy,
  Suspense,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

import type { components } from "./api/schema";
import { AuthProvider } from "./auth/AuthProvider";
import { PasswordChangeContext, useAuth } from "./auth/context";
import { LoginForm } from "./auth/LoginForm";
import { WorkspaceBoundary } from "./components/WorkspaceBoundary";
import { loadWorkspaceChunk } from "./components/workspaceChunk";
import { isFreshDirectoryNavigation } from "./components/recordNavigation";
import { WorkbenchShell } from "./shell/WorkbenchShell";
import type { Section } from "./shell/navigation";

const HarvestScreen = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./harvests/HarvestScreen");
    return { default: module.HarvestScreen };
  }),
);

const AncestryExplorer = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./lineage/AncestryExplorer");
    return { default: module.AncestryExplorer };
  }),
);

const MediaScreen = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./media/MediaScreen");
    return { default: module.MediaScreen };
  }),
);

const TaxonomyScreen = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./taxonomy/TaxonomyScreen");
    return { default: module.TaxonomyScreen };
  }),
);

const GeographyWorkspace = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./geography/GeographyWorkspace");
    return { default: module.GeographyWorkspace };
  }),
);

const BotanicalIdentityScreen = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module =
      await import("./botanical-identities/BotanicalIdentityScreen");
    return { default: module.BotanicalIdentityScreen };
  }),
);

const DashboardScreen = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./collection/DashboardScreen");
    return { default: module.DashboardScreen };
  }),
);

const ScheduleScreen = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./schedule/ScheduleScreen");
    return { default: module.ScheduleScreen };
  }),
);

const HistoryScreen = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./history/HistoryScreen");
    return { default: module.HistoryScreen };
  }),
);
const GlobalEventsScreen = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./events/GlobalEventsScreen");
    return { default: module.GlobalEventsScreen };
  }),
);

const ImportExportScreen = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./import-export/ImportExportScreen");
    return { default: module.ImportExportScreen };
  }),
);

const LocationScreen = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./locations/LocationScreen");
    return { default: module.LocationScreen };
  }),
);

const AccountScreen = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./settings/AccountScreen");
    return { default: module.AccountScreen };
  }),
);

const SettingsScreen = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./settings/SettingsScreen");
    return { default: module.SettingsScreen };
  }),
);

const LabelsScreen = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./labels/LabelsScreen");
    return { default: module.LabelsScreen };
  }),
);

const PlantScreen = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./plants/PlantScreen");
    return { default: module.PlantScreen };
  }),
);

const SeedLotSowingWizard = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./propagation/SeedLotSowingWizard");
    return { default: module.SeedLotSowingWizard };
  }),
);

const SowingDescendantWizard = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./propagation/SowingDescendantWizard");
    return { default: module.SowingDescendantWizard };
  }),
);

const SeedLotScreen = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./seed-lots/SeedLotScreen");
    return { default: module.SeedLotScreen };
  }),
);

const SowingScreen = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./sowings/SowingScreen");
    return { default: module.SowingScreen };
  }),
);

const SupplierScreen = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./suppliers/SupplierScreen");
    return { default: module.SupplierScreen };
  }),
);

const OrderScreen = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./orders/OrderScreen");
    return { default: module.OrderScreen };
  }),
);

type HealthResponse = components["schemas"]["HealthResponse"];
const CuttingsScreen = lazy(() =>
  import("./ui-pages/Cuttings/Cuttings").then((module) => ({
    default: module.Cuttings,
  })),
);

type HealthState =
  | { status: "loading" }
  | { status: "ready"; response: HealthResponse }
  | { status: "error" };

interface Route {
  section: Section;
  geographyView?: GeographyView;
  recordId?: string;
  cuttingRoute?: string;
  recordKind?: "plant" | "group";
  recordTypeFilter?: "plant" | "group";
  tab?: string;
  action?: string;
  identityId?: string;
  orderId?: string;
  sourceType?: "plant" | "plant_group";
  sourceId?: string;
  seedLotId?: string;
  sowingId?: string;
  creationKind?: "plant" | "group";
  placeId?: string;
  labelKind?: string;
  labelRecord?: string;
  /** The former Settings QR address (#/settings?tab=general) opens Labels' QR dialog. */
  labelQr?: boolean;
  /** #/lineage/<kind>/<id>: Material ancestry, within the focus record's own section. */
  ancestry?: {
    kind: keyof typeof ancestrySections;
    id: string;
  };
}

const ancestrySections = {
  seed_lot: "seeds",
  sowing: "sowings",
  plant: "plants",
  plant_group: "plants",
  vegetative_lot: "cuttings",
  propagation_attempt: "cuttings",
} as const;

function currentRoute(): Route {
  const raw = window.location.hash.slice(1) || "/dashboard";
  const [pathname, query = ""] = raw.split("?", 2);
  const [first = "dashboard", id, detailId] = pathname
    .split("/")
    .filter(Boolean);
  const tab = new URLSearchParams(query).get("tab") ?? undefined;
  const params = new URLSearchParams(query);
  const type = params.get("type");
  const action = params.get("action") ?? undefined;
  const identityId = params.get("identity") ?? undefined;
  const seedLotId = params.get("seedLot") ?? undefined;
  const sowingId = params.get("sowing") ?? undefined;
  const kind = params.get("kind");
  const placeId = params.get("place") ?? undefined;
  const context = {
    action,
    sourceType:
      params.get("sourceType") === "plant_group" ? "plant_group" : "plant",
    sourceId: params.get("source") ?? undefined,
    identityId,
    orderId: params.get("order") ?? undefined,
    seedLotId,
    sowingId,
    creationKind: kind === "plant" || kind === "group" ? kind : undefined,
  } as const;
  const ancestry =
    /^\/lineage\/(seed_lot|sowing|plant|plant_group|vegetative_lot|propagation_attempt)\/([^/]+)$/.exec(
      pathname,
    );
  if (ancestry) {
    const kind = ancestry[1] as keyof typeof ancestrySections;
    return {
      section: ancestrySections[kind],
      ancestry: { kind, id: ancestry[2] },
    };
  }
  if (first === "cuttings")
    return {
      section: "cuttings",
      cuttingRoute: id,
      recordId: detailId,
      ...context,
    };
  const geographic = geographyRoute(window.location.hash);
  if (geographic)
    return {
      section: "geography",
      geographyView: geographic.view,
      recordId: geographic.siteId,
      placeId,
      ...context,
    };
  if (first === "plant-groups")
    return {
      section: "plants",
      recordId: id,
      recordKind: "group",
      tab,
      action: action === "edit" ? action : undefined,
    };
  if (first === "plants")
    return {
      section: "plants",
      recordId: id,
      recordKind: "plant",
      recordTypeFilter: type === "plant" || type === "group" ? type : undefined,
      tab,
      ...context,
    };
  if (first === "settings" && tab === "general") {
    // Compatible redirect: the QR address moved to Labels (M8 final). The intent travels in
    // the address, so a repeated parse (React development double-invocation) agrees.
    window.history.replaceState(null, "", "#/labels?qr=edit");
    return { section: "labels", labelQr: true, ...context };
  }
  const valid: Section[] = [
    "dashboard",
    "seeds",
    "sowings",
    "harvests",
    "events",
    "history",
    "schedule",
    "taxonomy",
    "identities",
    "suppliers",
    "orders",
    "locations",
    "geography",
    "import-export",
    "labels",
    "settings",
    "account",
    "media",
  ];
  return {
    section: valid.includes(first as Section)
      ? (first as Section)
      : "dashboard",
    recordId: id,
    tab,
    placeId,
    labelKind: params.get("kind") ?? undefined,
    labelQr: first === "labels" && params.get("qr") === "edit",
    labelRecord: params.get("record") ?? undefined,
    ...context,
  };
}

function WorkspaceLoading() {
  return (
    <div className="workspace-route-loading" role="status">
      <span aria-hidden="true" className="workspace-route-loading__eyebrow" />
      <span aria-hidden="true" className="workspace-route-loading__title" />
      <p>Loading workspace…</p>
    </div>
  );
}

function ApplicationShell() {
  const auth = useAuth();
  const state = auth.state;
  const passwordChange = useContext(PasswordChangeContext);
  const [health, setHealth] = useState<HealthState>({ status: "loading" });
  const [route, setRoute] = useState<Route>(currentRoute);
  const [navigationReset, setNavigationReset] = useState(0);
  const formChanged = useRef(false);
  const formDeparture = useRef<(() => boolean) | null>(null);
  const clearFormChanged = useCallback(() => {
    formChanged.current = false;
  }, []);
  const registerFormDeparture = useCallback((guard: () => boolean) => {
    formDeparture.current = guard;
    return () => {
      if (formDeparture.current === guard) formDeparture.current = null;
    };
  }, []);

  useEffect(() => {
    const update = (event: Event) => {
      const next = currentRoute();
      setRoute(next);
      // Explicit directory opens start fresh; detail/history transitions retain
      // their existing focus and interaction behavior.
      if (isFreshDirectoryNavigation(event))
        setNavigationReset((value) => value + 1);
    };
    window.addEventListener("hashchange", update);
    window.addEventListener("popstate", update);
    return () => {
      window.removeEventListener("hashchange", update);
      window.removeEventListener("popstate", update);
    };
  }, []);

  useEffect(() => {
    formChanged.current = false;
  }, [
    route.section,
    route.recordId,
    route.action,
    route.creationKind,
    route.identityId,
  ]);

  function canNavigate(target: string) {
    if (target === window.location.hash) return true;
    return (
      formDeparture.current?.() ??
      (!formChanged.current ||
        !document.querySelector(".app-content form:not([role='search'])") ||
        window.confirm(
          "Discard unsaved form changes and return to the workspace?",
        ))
    );
  }

  /** Guarded in-app navigation to any existing hash route (shell, palette, menus). */
  function navigateTo(target: string) {
    if (target === window.location.hash && formDeparture.current) return;
    if (!canNavigate(target)) return;
    formChanged.current = false;
    // Creation and source tasks insert their parent page, exactly like content links,
    // so Back returns to the directory or source record wherever the task started.
    if (collectionPageParent(target)) {
      openCollectionPage(target);
      if (window.scrollY > 0) window.scrollTo(0, 0);
      return;
    }
    const previous = route.section;
    if (window.location.hash === target)
      window.history.replaceState(null, "", target);
    else window.history.pushState(null, "", target);
    const next = currentRoute();
    setRoute(next);
    // Same-section targets remount the workspace so initial props apply.
    if (next.section === previous) setNavigationReset((value) => value + 1);
    if (window.scrollY > 0) window.scrollTo(0, 0);
  }

  useEffect(() => {
    const controller = new AbortController();
    void fetch("/api/v1/health", { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Health request failed");
        const payload = (await response.json()) as HealthResponse;
        setHealth({ status: "ready", response: payload });
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError")
          return;
        setHealth({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, []);

  if (
    state.status !== "authenticated" &&
    state.status !== "logging-out" &&
    state.status !== "logout-failed"
  ) {
    return null;
  }
  const signedInAs = state.session.display_name ?? state.session.login_name;

  return (
    <WorkbenchShell
      section={route.section}
      hash={window.location.hash || "#/dashboard"}
      signedInAs={signedInAs}
      signingOut={state.status === "logging-out"}
      signOutDisabled={passwordChange?.pending}
      onSignOut={() => {
        if (route.section === "account" && formDeparture.current?.() === false)
          return;
        void auth.logOut();
      }}
      onNavigate={navigateTo}
    >
      <section
        aria-label="Workspace content"
        className="app-content"
        onClick={(event) => {
          if (
            event.defaultPrevented ||
            event.button !== 0 ||
            event.metaKey ||
            event.ctrlKey ||
            event.shiftKey ||
            event.altKey ||
            !(event.target instanceof Element)
          )
            return;
          const link = event.target.closest<HTMLAnchorElement>("a[href]");
          if (
            !link ||
            link.target === "_blank" ||
            link.origin !== window.location.origin ||
            (!collectionPageParent(link.hash) && route.section !== "account")
          )
            return;
          event.preventDefault();
          if (route.section === "account" && !collectionPageParent(link.hash)) {
            navigateTo(link.hash);
            return;
          }
          if (link.hash === window.location.hash && formDeparture.current)
            return;
          if (!canNavigate(link.hash)) return;
          formChanged.current = false;
          openCollectionPage(link.hash);
        }}
        onChangeCapture={(event) => {
          if (
            event.target instanceof Element &&
            event.target.closest("form:not([role='search'])")
          )
            formChanged.current = true;
        }}
        onClickCapture={(event) => {
          if (
            event.target instanceof Element &&
            event.target.closest("form [role='option']")
          )
            formChanged.current = true;
        }}
      >
        <RecordPresentationProvider
          key={route.section}
          fetchIdentities={
            route.section === "dashboard" ||
            route.section === "events" ||
            route.section === "sowings" ||
            route.section === "cuttings" ||
            route.section === "harvests"
          }
        >
          <WorkspaceBoundary
            key={`${route.section}:${String(navigationReset)}`}
          >
            <Suspense fallback={<WorkspaceLoading />}>
              {route.ancestry ? (
                <AncestryExplorer
                  key={`${route.ancestry.kind}:${route.ancestry.id}`}
                  kind={route.ancestry.kind}
                  id={route.ancestry.id}
                />
              ) : route.section === "sowings" &&
                route.action === "start" &&
                route.seedLotId ? (
                <SeedLotSowingWizard seedLotId={route.seedLotId} />
              ) : route.section === "plants" &&
                route.action === "from-sowing" &&
                route.sowingId &&
                route.creationKind ? (
                <SowingDescendantWizard
                  sowingId={route.sowingId}
                  kind={route.creationKind}
                />
              ) : route.section === "dashboard" ? (
                <DashboardScreen />
              ) : route.section === "harvests" ? (
                <HarvestScreen
                  initialId={route.recordId}
                  initialTab={route.action === "edit" ? "edit" : route.tab}
                  startCreating={route.action === "create"}
                  sourceType={route.sourceType}
                  sourceId={route.sourceId}
                />
              ) : route.section === "orders" ? (
                <OrderScreen
                  initialId={route.recordId}
                  initialTab={route.action === "edit" ? "edit" : route.tab}
                  startCreating={route.action === "create"}
                />
              ) : route.section === "media" ? (
                <MediaScreen
                  key={route.recordId ?? "directory"}
                  initialId={route.recordId}
                />
              ) : route.section === "seeds" ? (
                <SeedLotScreen
                  initialId={route.recordId}
                  initialTab={route.action === "edit" ? "edit" : route.tab}
                  initialIdentityId={route.identityId}
                  initialOrderId={route.orderId}
                  startCreating={route.action === "create"}
                />
              ) : route.section === "cuttings" ? (
                <CuttingsScreen
                  key={window.location.hash.split("?", 1)[0]}
                  route={route.cuttingRoute}
                  id={route.recordId}
                  identityId={route.identityId}
                  sourceId={route.sourceId}
                  sourceType={route.sourceType}
                />
              ) : route.section === "sowings" ? (
                <SowingScreen
                  initialId={route.recordId}
                  initialTab={route.action === "edit" ? "edit" : route.tab}
                  startCreating={route.action === "create"}
                />
              ) : route.section === "plants" ? (
                <PlantScreen
                  initialId={route.recordId}
                  initialKind={route.recordKind}
                  initialTypeFilter={route.recordTypeFilter}
                  initialTab={route.action === "edit" ? "edit" : route.tab}
                  initialIdentityId={route.identityId}
                  startCreating={route.action === "create"}
                  initialExtractionId={
                    route.action === "extract" ? route.sourceId : undefined
                  }
                  initialCreationKind={route.creationKind}
                  registerFormDeparture={registerFormDeparture}
                />
              ) : route.section === "schedule" ? (
                <ScheduleScreen />
              ) : route.section === "history" ? (
                <HistoryScreen />
              ) : route.section === "events" ? (
                <GlobalEventsScreen />
              ) : route.section === "taxonomy" ? (
                <TaxonomyScreen />
              ) : route.section === "identities" ? (
                <BotanicalIdentityScreen
                  initialId={route.recordId}
                  initialTab={route.tab}
                  startCreating={route.action === "create"}
                />
              ) : route.section === "suppliers" ? (
                <SupplierScreen
                  initialId={route.recordId}
                  initialTab={route.tab}
                  startCreating={route.action === "create"}
                />
              ) : route.section === "import-export" ? (
                <ImportExportScreen />
              ) : route.section === "account" ? (
                <AccountScreen
                  registerFormDeparture={registerFormDeparture}
                  clearFormChanged={clearFormChanged}
                />
              ) : route.section === "settings" ? (
                <SettingsScreen />
              ) : route.section === "labels" ? (
                <LabelsScreen
                  key={`${route.labelKind ?? ""}:${route.labelRecord ?? ""}`}
                  initialKind={route.labelKind}
                  initialId={route.labelRecord}
                  openQrDestination={route.labelQr}
                />
              ) : route.section === "locations" ? (
                <LocationScreen
                  key={route.recordId ?? "directory"}
                  initialId={route.recordId}
                  startCreating={route.action === "create"}
                />
              ) : (
                <GeographyWorkspace
                  view={route.geographyView ?? "overview"}
                  siteId={route.recordId}
                  placeId={route.placeId}
                  startCreating={route.action === "create"}
                />
              )}
            </Suspense>
          </WorkspaceBoundary>
        </RecordPresentationProvider>
        {state.status === "logout-failed" && (
          <div className="notice notice--error" role="alert">
            <p>{state.message}</p>
            <div className="actions">
              <button
                type="button"
                onClick={() => {
                  void auth.logOut();
                }}
              >
                Retry sign out
              </button>
              <button
                className="button--secondary"
                type="button"
                onClick={() => {
                  auth.cancelLogout();
                }}
              >
                Stay signed in
              </button>
            </div>
          </div>
        )}
        {health.status === "error" && (
          <div aria-live="polite" className="notice notice--warning">
            <p>Florabase cannot currently reach its application service.</p>
          </div>
        )}
      </section>
    </WorkbenchShell>
  );
}

function AuthenticatedApplication() {
  const auth = useAuth();
  const state = auth.state;

  if (state.status === "restoring") {
    return (
      <section aria-labelledby="page-title" className="card">
        <p className="eyebrow">Self-hosted botanical records</p>
        <h1 id="page-title">Florabase</h1>
        <p aria-live="polite" className="notice">
          Restoring your session…
        </p>
      </section>
    );
  }

  if (state.status === "recovery-failed") {
    return (
      <section aria-labelledby="page-title" className="card">
        <p className="eyebrow">Self-hosted botanical records</p>
        <h1 id="page-title">Florabase</h1>
        <div className="notice notice--error" role="alert">
          <p>{state.message}</p>
          <button
            type="button"
            onClick={() => {
              auth.retryRestoration();
            }}
          >
            Retry session restoration
          </button>
        </div>
      </section>
    );
  }

  if (
    state.status === "unauthenticated" ||
    state.status === "submitting-login"
  ) {
    return (
      <section aria-labelledby="page-title" className="card">
        <p className="eyebrow">Self-hosted botanical records</p>
        <h1 id="page-title">Florabase</h1>
        <p className="intro">Sign in with the local owner account.</p>
        <LoginForm />
      </section>
    );
  }

  return <ApplicationShell />;
}

export function App() {
  return (
    <main>
      <AuthProvider>
        <AuthenticatedApplication />
      </AuthProvider>
    </main>
  );
}
