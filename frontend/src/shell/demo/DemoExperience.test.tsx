import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, requestJson } from "../../auth/AuthProvider";
import { useAuth } from "../../auth/context";
import { WorkbenchShell } from "../WorkbenchShell";
import { DemoExperience } from "./DemoExperience";
import {
  extractDemoReadOnlyMessage,
  notifyDemoReadOnlyBlocked,
} from "./readonlyNotice";
import {
  DEMO_INSTALL_URL,
  DEMO_TOUR_DISMISSED_KEY,
  DEMO_TOUR_STEPS,
  hasExplicitTourParam,
} from "./tourSteps";

function DemoAuthProbe() {
  const { state, capability } = useAuth();
  if (state.status !== "authenticated") {
    return <p>{state.status}</p>;
  }
  return (
    <div>
      <p>{`demo:${String(state.session.demo_readonly)}`}</p>
      <p>{`csrf:${state.csrfToken}`}</p>
      <button
        type="button"
        onClick={() => {
          void requestJson("/api/v1/plants", {
            method: "POST",
            capability,
          }).catch(() => undefined);
        }}
      >
        Attempt write
      </button>
      {state.session.demo_readonly && <DemoExperience onNavigate={vi.fn()} />}
    </div>
  );
}

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.href;
  return input.url;
}

describe("DemoExperience", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.history.replaceState({}, "", "/#/dashboard");
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.useRealTimers();
    window.sessionStorage.clear();
  });

  it("auto-starts the guided tour on first visit and steps through real routes", () => {
    const onNavigate = vi.fn();
    render(<DemoExperience onNavigate={onNavigate} />);

    expect(
      screen.getByRole("region", { name: "Public demo notice" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Read-only demo")).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: "Interactive guided tour" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: DEMO_TOUR_STEPS[0].title }),
    ).toBeInTheDocument();
    expect(onNavigate).toHaveBeenCalledWith(DEMO_TOUR_STEPS[0].href);

    for (let index = 1; index < DEMO_TOUR_STEPS.length; index += 1) {
      fireEvent.click(screen.getByRole("button", { name: "Next" }));
      expect(
        screen.getByRole("heading", { name: DEMO_TOUR_STEPS[index].title }),
      ).toBeInTheDocument();
      expect(onNavigate).toHaveBeenLastCalledWith(DEMO_TOUR_STEPS[index].href);
    }

    const installLinks = screen.getAllByRole("link", {
      name: "Install Florabase",
    });
    expect(installLinks.length).toBeGreaterThanOrEqual(2);
    expect(installLinks[0]).toHaveAttribute("href", DEMO_INSTALL_URL);
    expect(DEMO_INSTALL_URL).toContain(
      "github.com/alessandrorossato/florabase",
    );

    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(
      screen.getByRole("heading", {
        name: DEMO_TOUR_STEPS[DEMO_TOUR_STEPS.length - 2].title,
      }),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: `Go to step 2: ${DEMO_TOUR_STEPS[1].title}`,
      }),
    );
    expect(
      screen.getByRole("heading", { name: DEMO_TOUR_STEPS[1].title }),
    ).toBeInTheDocument();
    expect(onNavigate).toHaveBeenLastCalledWith(DEMO_TOUR_STEPS[1].href);
  });

  it("persists dismissal on Escape and allows restarting from the banner", () => {
    const onNavigate = vi.fn();
    render(<DemoExperience onNavigate={onNavigate} />);

    fireEvent.keyDown(window, { key: "Escape" });
    expect(
      screen.queryByRole("region", { name: "Interactive guided tour" }),
    ).not.toBeInTheDocument();
    expect(window.sessionStorage.getItem(DEMO_TOUR_DISMISSED_KEY)).toBe("true");

    fireEvent.click(screen.getByRole("button", { name: "Start guided tour" }));
    expect(
      screen.getByRole("region", { name: "Interactive guided tour" }),
    ).toBeInTheDocument();
    expect(window.sessionStorage.getItem(DEMO_TOUR_DISMISSED_KEY)).toBeNull();
  });

  it("handles private-mode sessionStorage errors gracefully", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("Access denied", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("Access denied", "SecurityError");
    });

    const onNavigate = vi.fn();
    render(<DemoExperience onNavigate={onNavigate} />);

    expect(
      screen.getByRole("region", { name: "Interactive guided tour" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Skip tour" }));
    expect(
      screen.queryByRole("region", { name: "Interactive guided tour" }),
    ).not.toBeInTheDocument();
  });

  it("opens the tour when ?tour=1 is present even after prior dismissal", () => {
    window.sessionStorage.setItem(DEMO_TOUR_DISMISSED_KEY, "true");
    window.history.replaceState({}, "", "/?tour=1#/dashboard");

    const onNavigate = vi.fn();
    render(<DemoExperience onNavigate={onNavigate} />);

    expect(
      screen.getByRole("region", { name: "Interactive guided tour" }),
    ).toBeInTheDocument();
    expect(hasExplicitTourParam("?tour=1", "#/dashboard")).toBe(true);
    expect(hasExplicitTourParam("", "#/dashboard?tour=1")).toBe(true);
    expect(hasExplicitTourParam("", "#/dashboard")).toBe(false);
  });

  it("displays and dismisses read-only mutation notices", () => {
    const onNavigate = vi.fn();
    render(<DemoExperience onNavigate={onNavigate} />);

    expect(
      extractDemoReadOnlyMessage({
        detail: { code: "demo_read_only", message: "Demo is read-only." },
      }),
    ).toBe("Demo is read-only.");
    expect(extractDemoReadOnlyMessage({ detail: "Request forbidden" })).toBe(
      null,
    );

    act(() => {
      notifyDemoReadOnlyBlocked("This public demo is read-only.");
    });

    const notice = screen.getByRole("status");
    expect(notice).toHaveTextContent("This public demo is read-only.");

    fireEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("hides sign-out, create actions and owner-only settings in WorkbenchShell demo mode", () => {
    render(
      <WorkbenchShell
        section="settings"
        hash="#/settings"
        signedInAs="Demo visitor"
        signingOut={false}
        signOutDisabled
        demoReadOnly
        onSignOut={vi.fn()}
        onNavigate={vi.fn()}
      >
        <main>Demo body</main>
      </WorkbenchShell>,
    );

    expect(screen.getByText("Demo visitor (read-only)")).toBeInTheDocument();
    expect(screen.queryByText(/Signed in as/i)).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Sign out/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Record/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /New record/i }),
    ).not.toBeInTheDocument();

    // Owner-only settings links are hidden while safe links remain visible.
    expect(
      screen.queryByRole("link", { name: "Account" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Import / Export" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Theme" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Labels" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Help" })).toBeInTheDocument();
  });

  it("authenticates demo_readonly sessions without POST /api/v1/auth/csrf and surfaces 403 demo notices", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      if (url.endsWith("/api/v1/auth/session")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              user_id: "00000000-0000-0000-0000-000000000000",
              login_name: "",
              display_name: "Demo visitor",
              owner: false,
              canonical_origin: "https://demo.example.org",
              demo_readonly: true,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          ),
        );
      }
      if (url.endsWith("/api/v1/plants") && init?.method === "POST") {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              detail: {
                code: "demo_read_only",
                message: "This public demo is read-only.",
              },
            }),
            { status: 403, headers: { "Content-Type": "application/json" } },
          ),
        );
      }
      return Promise.reject(new Error(`Unexpected fetch: ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <AuthProvider>
        <DemoAuthProbe />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("demo:true")).toBeInTheDocument();
    });
    expect(screen.getByText("csrf:")).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(([input]) =>
        requestUrl(input).includes("/api/v1/auth/csrf"),
      ),
    ).toBe(false);

    fireEvent.click(screen.getByRole("button", { name: "Attempt write" }));

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(
        "This public demo is read-only.",
      );
    });
  });
});
