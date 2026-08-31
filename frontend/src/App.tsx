import { useEffect, useState } from "react";

import type { components } from "./api/schema";
import { AuthProvider } from "./auth/AuthProvider";
import { useAuth } from "./auth/context";
import { LoginForm } from "./auth/LoginForm";
import { BotanicalIdentityScreen } from "./botanical-identities/BotanicalIdentityScreen";
import { GeographyScreen } from "./geographic-places/GeographyScreen";
import { LocationScreen } from "./locations/LocationScreen";
import { SeedLotScreen } from "./seed-lots/SeedLotScreen";
import { SowingScreen } from "./sowings/SowingScreen";
import { SupplierScreen } from "./suppliers/SupplierScreen";

type HealthResponse = components["schemas"]["HealthResponse"];
type HealthState =
  | { status: "loading" }
  | { status: "ready"; response: HealthResponse }
  | { status: "error" };

function ApplicationShell() {
  const auth = useAuth();
  const state = auth.state;
  const [health, setHealth] = useState<HealthState>({ status: "loading" });
  const [section, setSection] = useState<
    "seeds" | "sowings" | "identities" | "suppliers" | "locations" | "geography"
  >("identities");

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
    <section aria-labelledby="page-title" className="card card--application">
      <div className="session-bar">
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
      <p className="eyebrow">Self-hosted botanical records</p>
      <h1 id="page-title">Florabase</h1>
      <nav aria-label="Primary navigation" className="primary-navigation">
        <button
          type="button"
          className="navigation-link"
          aria-current={section === "sowings" ? "page" : undefined}
          onClick={() => {
            setSection("sowings");
          }}
        >
          Sowings
        </button>
        <button
          type="button"
          className="navigation-link"
          aria-current={section === "seeds" ? "page" : undefined}
          onClick={() => {
            setSection("seeds");
          }}
        >
          Seeds
        </button>
        <button
          type="button"
          className="navigation-link"
          aria-current={section === "identities" ? "page" : undefined}
          onClick={() => {
            setSection("identities");
          }}
        >
          Botanical identities
        </button>
        <button
          type="button"
          className="navigation-link"
          aria-current={section === "suppliers" ? "page" : undefined}
          onClick={() => {
            setSection("suppliers");
          }}
        >
          Suppliers
        </button>
        <button
          type="button"
          className="navigation-link"
          aria-current={section === "locations" ? "page" : undefined}
          onClick={() => {
            setSection("locations");
          }}
        >
          Locations
        </button>
        <button
          type="button"
          className="navigation-link"
          aria-current={section === "geography" ? "page" : undefined}
          onClick={() => {
            setSection("geography");
          }}
        >
          Geography
        </button>
      </nav>
      {section === "seeds" ? (
        <SeedLotScreen />
      ) : section === "sowings" ? (
        <SowingScreen />
      ) : section === "identities" ? (
        <BotanicalIdentityScreen />
      ) : section === "suppliers" ? (
        <SupplierScreen />
      ) : section === "locations" ? (
        <LocationScreen />
      ) : (
        <GeographyScreen />
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
      <div
        aria-live="polite"
        className={`status status--compact status--${health.status}`}
      >
        {health.status === "loading" && <p>Checking backend connection…</p>}
        {health.status === "ready" && (
          <p>
            <span aria-hidden="true">●</span> Backend status:{" "}
            {health.response.status}
          </p>
        )}
        {health.status === "error" && (
          <p>Backend status is currently unavailable.</p>
        )}
      </div>
    </section>
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
