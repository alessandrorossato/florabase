import { lazy, Suspense, useEffect, useState } from "react";

import type { components } from "./api/schema";
import { AuthProvider } from "./auth/AuthProvider";
import { useAuth } from "./auth/context";
import { LoginForm } from "./auth/LoginForm";
import { BotanicalIdentityScreen } from "./botanical-identities/BotanicalIdentityScreen";
import { DashboardScreen } from "./collection/DashboardScreen";
import { GlobalEventsScreen } from "./events/GlobalEventsScreen";
import { GeographyScreen } from "./geographic-places/GeographyScreen";
import { ImportExportScreen } from "./import-export/ImportExportScreen";
import { LocationScreen } from "./locations/LocationScreen";
import { PlantScreen } from "./plants/PlantScreen";
import { SeedLotSowingWizard } from "./propagation/SeedLotSowingWizard";
import { SowingDescendantWizard } from "./propagation/SowingDescendantWizard";
import { SeedLotScreen } from "./seed-lots/SeedLotScreen";
import { SowingScreen } from "./sowings/SowingScreen";
import { SupplierScreen } from "./suppliers/SupplierScreen";

const ProvenanceMapScreen = lazy(async () => {
  const module = await import("./provenance-map/ProvenanceMapScreen");
  return { default: module.ProvenanceMapScreen };
});

type HealthResponse = components["schemas"]["HealthResponse"];
type HealthState =
  | { status: "loading" }
  | { status: "ready"; response: HealthResponse }
  | { status: "error" };

type Section =
  | "dashboard"
  | "seeds"
  | "sowings"
  | "plants"
  | "events"
  | "map"
  | "identities"
  | "suppliers"
  | "locations"
  | "geography"
  | "import-export";

interface Route {
  section: Section;
  recordId?: string;
  recordKind?: "plant" | "group";
  recordTypeFilter?: "plant" | "group";
  tab?: string;
  action?: string;
  identityId?: string;
  seedLotId?: string;
  sowingId?: string;
  creationKind?: "plant" | "group";
}

function currentRoute(): Route {
  const raw = window.location.hash.slice(1) || "/dashboard";
  const [pathname, query = ""] = raw.split("?", 2);
  const [first = "dashboard", id] = pathname.split("/").filter(Boolean);
  const tab = new URLSearchParams(query).get("tab") ?? undefined;
  const params = new URLSearchParams(query);
  const type = params.get("type");
  const action = params.get("action") ?? undefined;
  const identityId = params.get("identity") ?? undefined;
  const seedLotId = params.get("seedLot") ?? undefined;
  const sowingId = params.get("sowing") ?? undefined;
  const kind = params.get("kind");
  const context = {
    action,
    identityId,
    seedLotId,
    sowingId,
    creationKind: kind === "plant" || kind === "group" ? kind : undefined,
  } as const;
  if (first === "plant-groups")
    return { section: "plants", recordId: id, recordKind: "group", tab };
  if (first === "plants")
    return {
      section: "plants",
      recordId: id,
      recordKind: "plant",
      recordTypeFilter: type === "plant" || type === "group" ? type : undefined,
      tab,
      ...context,
    };
  const valid: Section[] = [
    "dashboard",
    "seeds",
    "sowings",
    "events",
    "map",
    "identities",
    "suppliers",
    "locations",
    "geography",
    "import-export",
  ];
  return {
    section: valid.includes(first as Section)
      ? (first as Section)
      : "dashboard",
    recordId: id,
    tab,
    ...context,
  };
}

const desktopGroups: {
  label: string;
  items: { id: Section; label: string }[];
}[] = [
  { label: "Overview", items: [{ id: "dashboard", label: "Dashboard" }] },
  {
    label: "Collection",
    items: [
      { id: "seeds", label: "Seeds" },
      { id: "sowings", label: "Sowings" },
      { id: "plants", label: "Plants" },
      { id: "events", label: "Events" },
      { id: "map", label: "Provenance map" },
    ],
  },
  {
    label: "Botany",
    items: [{ id: "identities", label: "Botanical identities" }],
  },
  {
    label: "Reference",
    items: [
      { id: "locations", label: "Locations" },
      { id: "suppliers", label: "Suppliers" },
      { id: "geography", label: "Geography" },
    ],
  },
  {
    label: "Tools",
    items: [{ id: "import-export", label: "Import / Export" }],
  },
];

function ApplicationShell() {
  const auth = useAuth();
  const state = auth.state;
  const [health, setHealth] = useState<HealthState>({ status: "loading" });
  const [route, setRoute] = useState<Route>(currentRoute);
  const [moreOpen, setMoreOpen] = useState(false);

  useEffect(() => {
    const update = () => {
      setRoute(currentRoute());
    };
    window.addEventListener("hashchange", update);
    window.addEventListener("popstate", update);
    return () => {
      window.removeEventListener("hashchange", update);
      window.removeEventListener("popstate", update);
    };
  }, []);

  function navigate(section: Section) {
    window.history.pushState(null, "", `#/${section}`);
    setRoute({ section });
    setMoreOpen(false);
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
    <div className="application-shell">
      <aside className="desktop-sidebar">
        <div className="desktop-sidebar__content">
          <a className="brand" href="#/dashboard">
            Florabase
          </a>
          <nav aria-label="Primary navigation">
            {desktopGroups.map((group) => (
              <section key={group.label} aria-label={group.label}>
                <p>{group.label}</p>
                {group.items.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className="navigation-link"
                    aria-current={
                      route.section === item.id ? "page" : undefined
                    }
                    onClick={() => {
                      navigate(item.id);
                    }}
                  >
                    {item.label}
                  </button>
                ))}
              </section>
            ))}
          </nav>
        </div>
      </aside>
      <section aria-labelledby="page-title" className="app-content">
        <div className="session-bar app-header">
          <div>
            <p className="eyebrow">Self-hosted botanical records</p>
            <h1 id="page-title">Florabase</h1>
          </div>
          <div>
            <p>Signed in as {signedInAs}</p>
            <button
              className="button--secondary"
              type="button"
              disabled={state.status === "logging-out"}
              onClick={() => {
                void auth.logOut();
              }}
            >
              {state.status === "logging-out" ? "Signing out…" : "Sign out"}
            </button>
          </div>
        </div>
        {route.section === "sowings" &&
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
        ) : route.section === "seeds" ? (
          <SeedLotScreen
            initialId={route.recordId}
            initialTab={route.tab}
            initialIdentityId={route.identityId}
            startCreating={route.action === "create"}
          />
        ) : route.section === "sowings" ? (
          <SowingScreen initialId={route.recordId} initialTab={route.tab} />
        ) : route.section === "plants" ? (
          <PlantScreen
            initialId={route.recordId}
            initialKind={route.recordKind}
            initialTypeFilter={route.recordTypeFilter}
            initialTab={route.tab}
            initialIdentityId={route.identityId}
            startCreating={route.action === "create"}
            initialCreationKind={route.creationKind}
          />
        ) : route.section === "events" ? (
          <GlobalEventsScreen />
        ) : route.section === "map" ? (
          <Suspense
            fallback={<p aria-live="polite">Loading provenance map…</p>}
          >
            <ProvenanceMapScreen />
          </Suspense>
        ) : route.section === "identities" ? (
          <BotanicalIdentityScreen
            initialId={route.recordId}
            initialTab={route.tab}
          />
        ) : route.section === "suppliers" ? (
          <SupplierScreen
            key={route.recordId ?? "directory"}
            initialId={route.recordId}
            initialTab={route.tab}
          />
        ) : route.section === "import-export" ? (
          <ImportExportScreen />
        ) : route.section === "locations" ? (
          <LocationScreen
            key={route.recordId ?? "directory"}
            initialId={route.recordId}
          />
        ) : (
          <GeographyScreen
            key={route.recordId ?? "directory"}
            initialSiteId={route.recordId}
          />
        )}
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
      <nav aria-label="Mobile primary navigation" className="mobile-navigation">
        {[
          { id: "dashboard", label: "Home" },
          { id: "seeds", label: "Seeds" },
          { id: "sowings", label: "Sowings" },
          { id: "plants", label: "Plants" },
        ].map((item) => (
          <a
            key={item.id}
            href={`#/${item.id}`}
            aria-current={route.section === item.id ? "page" : undefined}
            onClick={() => {
              setMoreOpen(false);
            }}
          >
            {item.label}
          </a>
        ))}
        <button
          type="button"
          aria-expanded={moreOpen}
          aria-controls="mobile-more-menu"
          aria-current={
            !["dashboard", "seeds", "sowings", "plants"].includes(route.section)
              ? "page"
              : undefined
          }
          onClick={() => {
            setMoreOpen((value) => !value);
          }}
        >
          More
        </button>
      </nav>
      {moreOpen && (
        <nav
          aria-label="More navigation"
          className="mobile-more"
          id="mobile-more-menu"
        >
          {desktopGroups
            .slice(1)
            .flatMap(({ items }) => items)
            .filter(({ id }) => !["plants", "seeds", "sowings"].includes(id))
            .map((item) => (
              <button
                key={item.id}
                type="button"
                aria-current={route.section === item.id ? "page" : undefined}
                onClick={() => {
                  navigate(item.id);
                }}
              >
                {item.label}
              </button>
            ))}
        </nav>
      )}
    </div>
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
