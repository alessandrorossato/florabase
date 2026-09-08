import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { App } from "./App";
import type { GeographicPlaceResponse } from "./geographic-places/api";
import type { LocationResponse } from "./locations/api";

const session = {
  user_id: "01900000-0000-7000-8000-000000000001",
  login_name: "owner",
  display_name: "Florabase Owner",
  owner: true,
};

function jsonResponse(
  body: unknown,
  status = 200,
  headers: Record<string, string> = {},
) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

function mockFetch(
  handler: (
    path: string,
    init: RequestInit | undefined,
  ) => Response | Promise<Response>,
) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const path =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    return Promise.resolve(handler(path, init));
  });
}

function noSessionThen(
  handler: (
    path: string,
    init: RequestInit | undefined,
  ) => Response | Promise<Response>,
) {
  let restoring = true;
  return mockFetch((path, init) => {
    if (restoring && path === "/api/v1/auth/session") {
      restoring = false;
      return jsonResponse({ detail: "Authentication required" }, 401);
    }
    if (path === "/api/v1/botanical-identities") return jsonResponse([]);
    return handler(path, init);
  });
}

function authenticatedThen(
  handler: (
    path: string,
    init: RequestInit | undefined,
  ) => Response | Promise<Response>,
) {
  return mockFetch((path, init) => {
    if (path.endsWith("/auth/session")) return jsonResponse(session);
    if (path.endsWith("/auth/csrf"))
      return jsonResponse({ csrf_token: "botanical-csrf" });
    if (path.endsWith("/health")) return jsonResponse({ status: "ok" });
    if (path === "/api/v1/provenance-sites") return jsonResponse([]);
    if (
      path === "/api/v1/botanical-identities" &&
      (init?.method === undefined || init.method === "GET")
    )
      return jsonResponse([]);
    return handler(path, init);
  });
}

function authenticatedDirectoryThen(
  handler: (
    path: string,
    init: RequestInit | undefined,
  ) => Response | Promise<Response>,
) {
  return mockFetch((path, init) => {
    if (path.endsWith("/auth/session")) return jsonResponse(session);
    if (path.endsWith("/auth/csrf"))
      return jsonResponse({ csrf_token: "botanical-csrf" });
    if (path.endsWith("/health")) return jsonResponse({ status: "ok" });
    return handler(path, init);
  });
}

const botanicalIdentity = {
  id: "01900000-0000-7000-8000-000000000099",
  scientific_name: "Acer palmatum",
  cultivar_name: "Bloodgood",
  common_name: "Japanese maple",
  created_at: "2026-08-29T10:00:00Z",
  updated_at: "2026-08-29T10:00:00Z",
  display_label: "Acer palmatum ‘Bloodgood’",
};

const botanicalProfile = {
  botanical_identity_id: botanicalIdentity.id,
  description: "A small deciduous tree.\n\nKnown for autumn colour.",
  origin_distribution: null,
  cultivation: "General guidance only.",
  uses: null,
  warnings: null,
};

function createIdentityThenProfile(
  profileHandler: (
    init: RequestInit | undefined,
  ) => Response | Promise<Response>,
) {
  return authenticatedThen((path, init) => {
    if (path === "/api/v1/botanical-identities")
      return jsonResponse(botanicalIdentity, 201);
    if (path === `/api/v1/botanical-identities/${botanicalIdentity.id}/profile`)
      return profileHandler(init);
    throw new Error(`unexpected request: ${path}`);
  });
}

async function createSelectedIdentity() {
  const user = userEvent.setup();
  render(<App />);
  await user.click(
    await screen.findByRole("button", { name: "+ New botanical identity" }),
  );
  await user.type(
    await screen.findByLabelText("Scientific name"),
    "Acer palmatum{Enter}",
  );
  await screen.findByRole("heading", {
    name: "Acer palmatum ‘Bloodgood’",
  });
  return user;
}

beforeEach(() => {
  window.history.replaceState(null, "", "#/identities");
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  localStorage.clear();
  sessionStorage.clear();
});

const supplier = {
  id: "01900000-0000-7000-8000-000000000200",
  name: "Rare Palm Seeds",
  kind: "seller" as const,
  website: "https://example.com/catalog",
  email: "sales@example.com",
  phone: "+39 123",
  notes: "International seller.\nShips seasonally.",
  retired_at: null as string | null,
  created_at: "2026-08-30T10:00:00Z",
  updated_at: "2026-08-30T10:00:00Z",
};

async function openSuppliers() {
  const user = userEvent.setup();
  render(<App />);
  await user.click(await screen.findByRole("button", { name: "Suppliers" }));
  return user;
}

const houseLocation: LocationResponse = {
  id: "01900000-0000-7000-8000-000000000300",
  name: "House",
  parent_id: null as string | null,
  display_path: "House",
  usage_scopes: ["plants", "sowings", "seed_lots"],
  usage: {
    plants: { active: 1, total: 2 },
    sowings: { active: 0, total: 1 },
    seed_lots: { active: 1, total: 1 },
  },
  retired_at: null as string | null,
  created_at: "2026-08-30T10:00:00Z",
  updated_at: "2026-08-30T10:00:00Z",
};

const cabinetLocation = {
  ...houseLocation,
  id: "01900000-0000-7000-8000-000000000301",
  name: "Seed cabinet",
  parent_id: houseLocation.id,
  display_path: "House → Seed cabinet",
};

const drawerLocation = {
  ...houseLocation,
  id: "01900000-0000-7000-8000-000000000302",
  name: "Drawer A",
  parent_id: cabinetLocation.id,
  display_path: "House → Seed cabinet → Drawer A",
};

async function openLocations() {
  const user = userEvent.setup();
  render(<App />);
  await user.click(await screen.findByRole("button", { name: "Locations" }));
  return user;
}

const worldPlace = {
  id: "019f3f06-3800-7149-bc3f-19b47997fade",
  name: "World",
  parent_id: null as string | null,
  display_path: "World",
  place_kind: "canonical" as const,
  place_type: null,
  provenance_site_count: 0,
  direct_usage_count: 0,
  source_name: "unicode_cldr" as string | null,
  source_version: "48.2.1" as string | null,
  source_code_type: "un_m49" as string | null,
  source_code: "001" as string | null,
  retired_at: null as string | null,
  created_at: "2026-07-08T00:00:00Z",
  updated_at: "2026-07-08T00:00:00Z",
};

const southAmericaPlace = {
  ...worldPlace,
  id: "019f3f06-3800-7fdd-a7a9-3d1562a38c53",
  name: "South America",
  parent_id: worldPlace.id,
  display_path:
    "World → Americas → Latin America and the Caribbean → South America",
  source_code: "005",
};

const brazilPlace = {
  ...worldPlace,
  id: "019f3f06-3800-7b32-a097-ed9760b28022",
  name: "Brazil",
  parent_id: southAmericaPlace.id,
  display_path: `${southAmericaPlace.display_path} → Brazil`,
  source_code_type: "iso_3166_1_alpha_2",
  source_code: "BR",
};

const thailandPlace = {
  ...worldPlace,
  id: "019f3f06-3800-7e69-9448-015e33fba60b",
  name: "Thailand",
  parent_id: worldPlace.id,
  display_path: "World → Asia → Southeast Asia → Thailand",
  source_code_type: "iso_3166_1_alpha_2",
  source_code: "TH",
};

async function openGeography() {
  const user = userEvent.setup();
  render(<App />);
  await user.click(await screen.findByRole("button", { name: "Geography" }));
  return user;
}

test("shows only the explicit restoration state while the session request is pending", () => {
  mockFetch(() => new Promise<Response>(() => undefined));
  render(<App />);

  expect(screen.getByText(/restoring your session/i)).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: /sign in/i }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText(/signed in as/i)).not.toBeInTheDocument();
});

test("a missing session shows an accessible login form", async () => {
  mockFetch(() => jsonResponse({ detail: "Authentication required" }, 401));
  render(<App />);

  expect(await screen.findByRole("button", { name: "Sign in" })).toBeEnabled();
  expect(screen.getByLabelText("Login name")).toHaveAttribute(
    "autocomplete",
    "username",
  );
  expect(screen.getByLabelText("Password")).toHaveAttribute("type", "password");
  expect(
    screen.queryByRole("heading", { name: "Botanical identities" }),
  ).not.toBeInTheDocument();
});

test("restores an existing session and recovers CSRF without a password", async () => {
  const calls: string[] = [];
  mockFetch((path, init) => {
    calls.push(`${init?.method ?? "GET"} ${path}`);
    if (path.endsWith("/session")) return jsonResponse(session);
    if (path.endsWith("/csrf"))
      return jsonResponse({ csrf_token: "fresh-csrf" });
    return jsonResponse({ status: "ok" });
  });
  render(<App />);

  expect(
    await screen.findByText("Signed in as Florabase Owner"),
  ).toBeInTheDocument();
  expect(screen.queryByLabelText("Password")).not.toBeInTheDocument();
  expect(calls.slice(0, 2)).toEqual([
    "GET /api/v1/auth/session",
    "POST /api/v1/auth/csrf",
  ]);
});

test("a restoration service failure is explicit and retryable", async () => {
  let attempts = 0;
  mockFetch((path) => {
    if (path.endsWith("/session")) {
      attempts += 1;
      if (attempts === 1) throw new TypeError("network unavailable");
      return jsonResponse({ detail: "Authentication required" }, 401);
    }
    throw new Error("unexpected request");
  });
  const user = userEvent.setup();
  render(<App />);

  expect(await screen.findByRole("alert")).toHaveTextContent(
    /could not reach the authentication service/i,
  );
  await user.click(
    screen.getByRole("button", { name: /retry session restoration/i }),
  );
  expect(
    await screen.findByRole("button", { name: "Sign in" }),
  ).toBeInTheDocument();
});

test("keyboard login succeeds, clears the password, and stores no token", async () => {
  const storageWrite = vi.spyOn(Storage.prototype, "setItem");
  const requests: { path: string; init?: RequestInit }[] = [];
  noSessionThen((path, init) => {
    requests.push({ path, init });
    if (path.endsWith("/login"))
      return jsonResponse({ csrf_token: "login-csrf" });
    if (path.endsWith("/session")) return jsonResponse(session);
    return jsonResponse({ status: "ok" });
  });
  const user = userEvent.setup();
  render(<App />);

  await user.type(await screen.findByLabelText("Login name"), "owner");
  const password = screen.getByLabelText("Password");
  await user.type(password, "correct horse battery staple{Enter}");

  expect(
    await screen.findByText("Signed in as Florabase Owner"),
  ).toBeInTheDocument();
  expect(localStorage.length).toBe(0);
  expect(sessionStorage.length).toBe(0);
  expect(storageWrite).not.toHaveBeenCalled();
  const loginRequest = requests.find(({ path }) => path.endsWith("/login"));
  expect(loginRequest?.init?.credentials).toBe("same-origin");
  expect(loginRequest?.init?.body).toBe(
    JSON.stringify({
      login_name: "owner",
      password: "correct horse battery staple",
    }),
  );
});

test("login exposes a busy state and prevents duplicate submission", async () => {
  let loginCalls = 0;
  noSessionThen((path) => {
    if (path.endsWith("/login")) {
      loginCalls += 1;
      return new Promise<Response>(() => undefined);
    }
    throw new Error("unexpected request");
  });
  const user = userEvent.setup();
  render(<App />);

  await user.type(await screen.findByLabelText("Login name"), "owner");
  await user.type(screen.getByLabelText("Password"), "a-password{Enter}");
  const button = screen.getByRole("button", { name: "Signing in…" });
  expect(button).toBeDisabled();
  expect(button.closest("form")).toHaveAttribute("aria-busy", "true");
  await user.click(button);
  expect(loginCalls).toBe(1);
});

test("invalid credentials stay generic, clear password, and focus feedback", async () => {
  noSessionThen((path) => {
    if (path.endsWith("/login"))
      return jsonResponse({ detail: "Invalid login credentials" }, 401);
    throw new Error("unexpected request");
  });
  const user = userEvent.setup();
  render(<App />);

  await user.type(await screen.findByLabelText("Login name"), "unknown-owner");
  await user.type(screen.getByLabelText("Password"), "wrong-password{Enter}");

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("login name or password was not accepted");
  expect(alert).toHaveFocus();
  expect(screen.getByLabelText("Password")).toHaveValue("");
  expect(alert).not.toHaveTextContent("unknown-owner");
});

test("throttled login shows useful generic retry information", async () => {
  noSessionThen((path) => {
    if (path.endsWith("/login"))
      return jsonResponse({ detail: "Too many login attempts" }, 429, {
        "Retry-After": "7",
      });
    throw new Error("unexpected request");
  });
  const user = userEvent.setup();
  render(<App />);

  await user.type(await screen.findByLabelText("Login name"), "owner");
  await user.type(screen.getByLabelText("Password"), "wrong-password{Enter}");
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Too many login attempts. Try again in 7 seconds.",
  );
});

test("login network failure is distinct from credential failure", async () => {
  noSessionThen((path) => {
    if (path.endsWith("/login")) throw new TypeError("network unavailable");
    throw new Error("unexpected request");
  });
  const user = userEvent.setup();
  render(<App />);

  await user.type(await screen.findByLabelText("Login name"), "owner");
  await user.type(screen.getByLabelText("Password"), "a-password{Enter}");
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /could not reach the authentication service/i,
  );
});

test("logout sends in-memory CSRF and clears authenticated UI", async () => {
  const requests: { path: string; init?: RequestInit }[] = [];
  mockFetch((path, init) => {
    requests.push({ path, init });
    if (path.endsWith("/session")) return jsonResponse(session);
    if (path.endsWith("/csrf"))
      return jsonResponse({ csrf_token: "fresh-csrf" });
    if (path.endsWith("/logout")) return jsonResponse({ status: "ok" });
    return jsonResponse({ status: "ok" });
  });
  const user = userEvent.setup();
  render(<App />);

  await user.click(await screen.findByRole("button", { name: "Sign out" }));
  expect(
    await screen.findByRole("button", { name: "Sign in" }),
  ).toBeInTheDocument();
  const logout = requests.find(({ path }) => path.endsWith("/logout"));
  expect(new Headers(logout?.init?.headers).get("X-CSRF-Token")).toBe(
    "fresh-csrf",
  );
});

test("an already-expired logout safely clears local authenticated state", async () => {
  mockFetch((path) => {
    if (path.endsWith("/session")) return jsonResponse(session);
    if (path.endsWith("/csrf"))
      return jsonResponse({ csrf_token: "fresh-csrf" });
    if (path.endsWith("/logout"))
      return jsonResponse({ detail: "Authentication required" }, 401);
    return jsonResponse({ status: "ok" });
  });
  const user = userEvent.setup();
  render(<App />);

  await user.click(await screen.findByRole("button", { name: "Sign out" }));
  expect(
    await screen.findByRole("button", { name: "Sign in" }),
  ).toBeInTheDocument();
});

test("logout network failure retains explicit session state and actions", async () => {
  mockFetch((path) => {
    if (path.endsWith("/session")) return jsonResponse(session);
    if (path.endsWith("/csrf"))
      return jsonResponse({ csrf_token: "fresh-csrf" });
    if (path.endsWith("/logout")) throw new TypeError("network unavailable");
    if (path === "/api/v1/botanical-identities") return jsonResponse([]);
    return jsonResponse({ status: "ok" });
  });
  const user = userEvent.setup();
  render(<App />);

  await user.click(await screen.findByRole("button", { name: "Sign out" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /server session may still be active/i,
  );
  expect(screen.getByRole("button", { name: "Retry sign out" })).toBeEnabled();
  await user.click(screen.getByRole("button", { name: "Stay signed in" }));
  await waitFor(() => {
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
  expect(screen.getByText("Signed in as Florabase Owner")).toBeInTheDocument();
});

test("authenticated owners see the labelled create form and truthful empty state", async () => {
  authenticatedThen(() => {
    throw new Error("unexpected request");
  });
  render(<App />);

  expect(
    await screen.findByRole("heading", { name: "Botanical identities" }),
  ).toBeInTheDocument();
  const user = userEvent.setup();
  const newIdentity = await screen.findByRole("button", {
    name: "+ New botanical identity",
  });
  expect(newIdentity).toHaveAttribute("aria-expanded", "false");
  expect(screen.queryByLabelText("Scientific name")).not.toBeInTheDocument();
  await user.click(newIdentity);
  expect(newIdentity).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByLabelText("Scientific name")).toHaveFocus();
  expect(
    screen.getByLabelText("Scientific name").closest(".creation-panel"),
  ).not.toBeNull();
  expect(screen.getByLabelText("Scientific name")).toBeRequired();
  expect(screen.getByLabelText("Scientific name")).toHaveAttribute(
    "maxlength",
    "255",
  );
  expect(screen.getByLabelText("Cultivar")).toHaveAccessibleDescription(
    /without quotation marks/i,
  );
  expect(screen.getByLabelText("Common name")).toBeInTheDocument();
  expect(newIdentity.closest(".directory-heading")).not.toBeNull();
  await user.click(screen.getByRole("button", { name: "Cancel" }));
  expect(newIdentity).toHaveAttribute("aria-expanded", "false");
  expect(newIdentity).toHaveFocus();
  expect(
    screen.getByRole("heading", {
      name: "Select a botanical identity",
    }),
  ).toBeInTheDocument();
  expect(
    await screen.findByText("No botanical identities yet."),
  ).toBeInTheDocument();
});

test("directory loading is explicit before the collection request resolves", async () => {
  authenticatedDirectoryThen((path) => {
    if (path === "/api/v1/botanical-identities")
      return new Promise<Response>(() => undefined);
    throw new Error(`unexpected request: ${path}`);
  });
  render(<App />);

  expect(
    await screen.findByText("Loading botanical identities…"),
  ).toBeInTheDocument();
  expect(screen.getByLabelText("Filter botanical identities")).toBeDisabled();
});

test("directory records are keyboard-selectable and reuse the existing profile panel", async () => {
  const annona = {
    ...botanicalIdentity,
    id: "01900000-0000-7000-8000-000000000100",
    scientific_name: "Annona cherimola",
    cultivar_name: null,
    common_name: "Cherimoya",
    display_label: "Annona cherimola",
  };
  authenticatedDirectoryThen((path) => {
    if (path === "/api/v1/botanical-identities")
      return jsonResponse([annona, botanicalIdentity]);
    if (path === `/api/v1/botanical-identities/${annona.id}/profile`)
      return jsonResponse(
        { detail: { code: "botanical_profile_not_found" } },
        404,
      );
    throw new Error(`unexpected request: ${path}`);
  });
  const user = userEvent.setup();
  render(<App />);

  const annonaButton = await screen.findByRole("button", {
    name: /Annona cherimola.*Cherimoya/i,
  });
  expect(annonaButton).toHaveAttribute("aria-pressed", "false");
  annonaButton.focus();
  await user.keyboard("{Enter}");
  expect(annonaButton).toHaveAttribute("aria-pressed", "true");
  expect(
    screen.getByRole("heading", { name: "Annona cherimola" }),
  ).toBeInTheDocument();
  expect(
    await screen.findByRole("heading", { name: "No profile yet" }),
  ).toBeInTheDocument();
});

test("client-side filter matches loaded common names and distinguishes zero matches", async () => {
  const annona = {
    ...botanicalIdentity,
    id: "01900000-0000-7000-8000-000000000100",
    scientific_name: "Annona cherimola",
    cultivar_name: null,
    common_name: "Cherimoya",
    display_label: "Annona cherimola",
  };
  authenticatedDirectoryThen((path) => {
    if (path === "/api/v1/botanical-identities")
      return jsonResponse([annona, botanicalIdentity]);
    throw new Error(`unexpected request: ${path}`);
  });
  const user = userEvent.setup();
  render(<App />);
  const filter = await screen.findByLabelText("Filter botanical identities");
  await waitFor(() => {
    expect(filter).toBeEnabled();
  });

  await user.type(filter, "cherimoya");
  expect(
    screen.getByRole("button", { name: /Annona cherimola/i }),
  ).toBeInTheDocument();
  await waitFor(() => {
    expect(
      screen.queryByRole("button", { name: /Acer palmatum/i }),
    ).not.toBeInTheDocument();
  });
  await user.clear(filter);
  await user.type(filter, "no such identity");
  expect(screen.getByRole("status")).toHaveTextContent(
    "No botanical identities match this filter.",
  );
  expect(
    screen.queryByText("No botanical identities yet."),
  ).not.toBeInTheDocument();
});

test("directory failure is distinct and retryable", async () => {
  authenticatedDirectoryThen((path) => {
    if (path === "/api/v1/botanical-identities")
      return jsonResponse({ detail: "Internal Server Error" }, 500);
    throw new Error(`unexpected request: ${path}`);
  });
  render(<App />);

  expect(await screen.findByRole("alert")).toHaveTextContent(
    /could not load.*directory/i,
  );
  expect(
    screen.getByRole("button", { name: "Retry directory" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByText("No botanical identities yet."),
  ).not.toBeInTheDocument();
});

test("directory session expiry returns to the shared login boundary", async () => {
  authenticatedDirectoryThen((path) => {
    if (path === "/api/v1/botanical-identities")
      return jsonResponse({ detail: "Authentication required" }, 401);
    throw new Error(`unexpected request: ${path}`);
  });
  render(<App />);

  expect(await screen.findByRole("alert")).toHaveTextContent(
    /session expired.*sign in again/i,
  );
  expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
});

test("keyboard creation sends generated-contract fields with CSRF and renders the response", async () => {
  let createRequest: RequestInit | undefined;
  let directoryCalls = 0;
  authenticatedDirectoryThen((path, init) => {
    if (path === "/api/v1/botanical-identities") {
      if (init?.method === undefined) {
        directoryCalls += 1;
        return jsonResponse(directoryCalls === 1 ? [] : [botanicalIdentity]);
      }
      createRequest = init;
      return jsonResponse(botanicalIdentity, 201);
    }
    if (path === `/api/v1/botanical-identities/${botanicalIdentity.id}/profile`)
      return jsonResponse(
        { detail: { code: "botanical_profile_not_found" } },
        404,
      );
    throw new Error("unexpected request");
  });
  const user = userEvent.setup();
  render(<App />);
  const newIdentity = await screen.findByRole("button", {
    name: "+ New botanical identity",
  });
  await user.click(newIdentity);

  await user.type(
    await screen.findByLabelText("Scientific name"),
    "Acer palmatum",
  );
  await user.type(screen.getByLabelText("Cultivar"), "Bloodgood");
  await user.type(
    screen.getByLabelText("Common name"),
    "Japanese maple{Enter}",
  );

  expect(
    await screen.findByRole("heading", {
      name: "Acer palmatum ‘Bloodgood’",
    }),
  ).toBeInTheDocument();
  expect(screen.getAllByText("Japanese maple")).toHaveLength(3);
  expect(screen.queryByText(botanicalIdentity.id)).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: /Acer palmatum.*Japanese maple/i }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(directoryCalls).toBe(2);
  expect(createRequest?.method).toBe("POST");
  expect(new Headers(createRequest?.headers).get("X-CSRF-Token")).toBe(
    "botanical-csrf",
  );
  expect(createRequest?.body).toBe(
    JSON.stringify({
      scientific_name: "Acer palmatum",
      cultivar_name: "Bloodgood",
      common_name: "Japanese maple",
    }),
  );
  expect(screen.queryByLabelText("Scientific name")).not.toBeInTheDocument();
  expect(newIdentity).toHaveAttribute("aria-expanded", "false");
  expect(newIdentity).toHaveFocus();
});

test("creation exposes a busy state and prevents duplicate submissions", async () => {
  let createCalls = 0;
  authenticatedThen((path) => {
    if (path === "/api/v1/botanical-identities") {
      createCalls += 1;
      return new Promise<Response>(() => undefined);
    }
    throw new Error("unexpected request");
  });
  const user = userEvent.setup();
  render(<App />);
  await user.click(
    await screen.findByRole("button", { name: "+ New botanical identity" }),
  );

  await user.type(
    await screen.findByLabelText("Scientific name"),
    "Acer palmatum{Enter}",
  );
  const button = screen.getByRole("button", {
    name: "Creating botanical identity…",
  });
  expect(button).toBeDisabled();
  expect(button.closest("form")).toHaveAttribute("aria-busy", "true");
  expect(
    screen.getByText("Saving the botanical identity…"),
  ).toBeInTheDocument();
  await user.click(button);
  expect(createCalls).toBe(1);
});

test("backend validation is announced in useful language and receives focus", async () => {
  authenticatedThen((path) => {
    if (path === "/api/v1/botanical-identities") {
      return jsonResponse(
        {
          detail: [
            {
              type: "value_error",
              loc: ["body", "scientific_name"],
              msg: "Value error, Value must not be blank",
              input: " ",
            },
          ],
        },
        422,
      );
    }
    throw new Error("unexpected request");
  });
  const user = userEvent.setup();
  render(<App />);
  await user.click(
    await screen.findByRole("button", { name: "+ New botanical identity" }),
  );

  await user.type(await screen.findByLabelText("Scientific name"), " {Enter}");
  expect(screen.getByLabelText("Scientific name")).toHaveValue(" ");
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("Scientific name cannot be blank.");
  expect(alert).toHaveFocus();
  expect(alert).not.toHaveTextContent("value_error");
});

test("a duplicate offers an accessible action that loads the existing record without CSRF", async () => {
  const existingId = botanicalIdentity.id;
  let getRequest: RequestInit | undefined;
  let resolveGet: ((response: Response) => void) | undefined;
  authenticatedThen((path, init) => {
    if (path === "/api/v1/botanical-identities") {
      return jsonResponse(
        {
          detail: {
            code: "botanical_identity_conflict",
            message: "Botanical identity already exists",
            existing_id: existingId,
          },
        },
        409,
      );
    }
    if (path === `/api/v1/botanical-identities/${existingId}`) {
      getRequest = init;
      return new Promise<Response>((resolve) => {
        resolveGet = resolve;
      });
    }
    throw new Error("unexpected request");
  });
  const user = userEvent.setup();
  render(<App />);
  await user.click(
    await screen.findByRole("button", { name: "+ New botanical identity" }),
  );

  await user.type(
    await screen.findByLabelText("Scientific name"),
    "Acer palmatum{Enter}",
  );
  expect(await screen.findByRole("status")).toHaveTextContent(
    "This botanical identity already exists",
  );
  await user.click(
    screen.getByRole("button", { name: "Select existing botanical identity" }),
  );
  expect(
    screen.getByText("Loading the existing botanical identity…"),
  ).toBeInTheDocument();
  resolveGet?.(jsonResponse(botanicalIdentity));
  expect(
    await screen.findByRole("heading", {
      name: "Acer palmatum ‘Bloodgood’",
    }),
  ).toBeInTheDocument();
  expect(getRequest?.method).toBeUndefined();
  expect(new Headers(getRequest?.headers).has("X-CSRF-Token")).toBe(false);
});

test("server failure is explicit and distinct from duplicate or validation feedback", async () => {
  authenticatedThen((path) => {
    if (path === "/api/v1/botanical-identities") {
      return jsonResponse({ detail: "Internal Server Error" }, 500);
    }
    throw new Error("unexpected request");
  });
  const user = userEvent.setup();
  render(<App />);
  await user.click(
    await screen.findByRole("button", { name: "+ New botanical identity" }),
  );

  await user.type(
    await screen.findByLabelText("Scientific name"),
    "Acer palmatum{Enter}",
  );
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent(/could not save.*check the connection/i);
  expect(alert).not.toHaveTextContent(/already exists|cannot be blank/i);
});

test("forbidden creation is explicit and does not retry with a stale CSRF token", async () => {
  let createCalls = 0;
  authenticatedThen((path) => {
    if (path === "/api/v1/botanical-identities") {
      createCalls += 1;
      return jsonResponse({ detail: "Request forbidden" }, 403);
    }
    throw new Error("unexpected request");
  });
  const user = userEvent.setup();
  render(<App />);
  await user.click(
    await screen.findByRole("button", { name: "+ New botanical identity" }),
  );

  await user.type(
    await screen.findByLabelText("Scientific name"),
    "Acer palmatum{Enter}",
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /could not authorize this change.*refresh/i,
  );
  expect(createCalls).toBe(1);
});

test("botanical authentication expiry returns to the existing login boundary", async () => {
  authenticatedThen((path) => {
    if (path === "/api/v1/botanical-identities") {
      return jsonResponse({ detail: "Authentication required" }, 401);
    }
    throw new Error("unexpected request");
  });
  const user = userEvent.setup();
  render(<App />);
  await user.click(
    await screen.findByRole("button", { name: "+ New botanical identity" }),
  );

  await user.type(
    await screen.findByLabelText("Scientific name"),
    "Acer palmatum{Enter}",
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /session expired.*sign in again/i,
  );
  expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: "Botanical identities" }),
  ).not.toBeInTheDocument();
});

test("profile loading is explicit and GET sends neither CSRF nor a mutation method", async () => {
  let profileRequest: RequestInit | undefined;
  createIdentityThenProfile((init) => {
    profileRequest = init;
    return new Promise<Response>(() => undefined);
  });

  await createSelectedIdentity();

  expect(screen.getByText("Loading botanical profile…")).toBeInTheDocument();
  expect(profileRequest?.method).toBeUndefined();
  expect(new Headers(profileRequest?.headers).has("X-CSRF-Token")).toBe(false);
});

test("no-profile state explains reference knowledge and exposes accessible optional fields", async () => {
  createIdentityThenProfile(() =>
    jsonResponse(
      {
        detail: {
          code: "botanical_profile_not_found",
          message: "Botanical profile not found",
        },
      },
      404,
    ),
  );

  await createSelectedIdentity();

  expect(
    await screen.findByRole("heading", { name: "No profile yet" }),
  ).toBeInTheDocument();
  expect(
    screen.getByText(
      /general reference knowledge for this botanical identity/i,
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/separate from observations about particular plants/i),
  ).toBeInTheDocument();
  for (const label of [
    "Description",
    "Origin & distribution",
    "Cultivation",
    "Uses",
    "Warnings",
  ]) {
    expect(screen.getByLabelText(label)).not.toBeRequired();
    expect(screen.getByLabelText(label).tagName).toBe("TEXTAREA");
  }
  expect(screen.getByLabelText("Cultivation")).toHaveAccessibleDescription(
    /general cultivation guidance, not measurements or outcomes/i,
  );
});

test("partial profile display and editor preserve multiline plain text", async () => {
  createIdentityThenProfile(() => jsonResponse(botanicalProfile));

  await createSelectedIdentity();

  expect(
    await screen.findByLabelText("Saved botanical profile"),
  ).toHaveTextContent(/small deciduous tree.*known for autumn colour/i);
  expect(screen.getByLabelText("Description")).toHaveValue(
    botanicalProfile.description,
  );
  expect(screen.getByLabelText("Origin & distribution")).toHaveValue("");
  expect(
    screen.queryByText("Origin & distribution", { selector: "h4" }),
  ).not.toBeInTheDocument();
});

test("profile creation uses PUT with CSRF and announces a multiline save", async () => {
  let profileCalls = 0;
  let putRequest: RequestInit | undefined;
  createIdentityThenProfile((init) => {
    profileCalls += 1;
    if (profileCalls === 1)
      return jsonResponse(
        { detail: { code: "botanical_profile_not_found" } },
        404,
      );
    putRequest = init;
    return jsonResponse(
      {
        ...botanicalProfile,
        description: "First paragraph.\n\nSecond paragraph.",
      },
      201,
    );
  });
  const user = await createSelectedIdentity();
  const description = await screen.findByLabelText("Description");

  await user.type(
    description,
    "First paragraph.{Enter}{Enter}Second paragraph.",
  );
  await user.click(screen.getByRole("button", { name: "Save profile" }));

  expect(await screen.findByRole("status")).toHaveTextContent(
    "Botanical profile saved.",
  );
  expect(putRequest?.method).toBe("PUT");
  expect(new Headers(putRequest?.headers).get("X-CSRF-Token")).toBe(
    "botanical-csrf",
  );
  if (typeof putRequest?.body !== "string")
    throw new Error("Expected a JSON request body");
  expect(JSON.parse(putRequest.body)).toMatchObject({
    description: "First paragraph.\n\nSecond paragraph.",
    origin_distribution: "",
  });
});

test("clearing one section updates the profile and clearing the final section returns to no profile", async () => {
  let profileCalls = 0;
  createIdentityThenProfile(() => {
    profileCalls += 1;
    if (profileCalls === 1)
      return jsonResponse({
        ...botanicalProfile,
        description: "Description",
        cultivation: null,
        uses: "Ornamental",
      });
    if (profileCalls === 2)
      return jsonResponse({
        ...botanicalProfile,
        description: null,
        cultivation: null,
        uses: "Ornamental",
      });
    return new Response(undefined, { status: 204 });
  });
  const user = await createSelectedIdentity();

  const description = await screen.findByLabelText("Description");
  await user.clear(description);
  await user.click(screen.getByRole("button", { name: "Save profile" }));
  expect(await screen.findByRole("status")).toHaveTextContent(/profile saved/i);
  expect(screen.getByLabelText("Uses")).toHaveValue("Ornamental");

  await user.clear(screen.getByLabelText("Uses"));
  await user.click(screen.getByRole("button", { name: "Save profile" }));
  expect(await screen.findByRole("status")).toHaveTextContent(
    /profile cleared/i,
  );
  expect(
    screen.getByRole("heading", { name: "No profile yet" }),
  ).toBeInTheDocument();
});

test("profile validation and network failures are announced without duplicate saves", async () => {
  let profileCalls = 0;
  createIdentityThenProfile(() => {
    profileCalls += 1;
    if (profileCalls === 1)
      return jsonResponse(
        { detail: { code: "botanical_profile_not_found" } },
        404,
      );
    if (profileCalls === 2)
      return jsonResponse({ detail: { code: "botanical_profile_empty" } }, 422);
    throw new TypeError("network unavailable");
  });
  const user = await createSelectedIdentity();

  await user.click(await screen.findByRole("button", { name: "Save profile" }));
  const validation = await screen.findByRole("alert");
  expect(validation).toHaveTextContent(
    /add content to at least one profile section/i,
  );
  expect(validation).toHaveFocus();

  await user.type(screen.getByLabelText("Warnings"), "Handle carefully.");
  await user.click(screen.getByRole("button", { name: "Save profile" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /could not save this botanical profile.*check the connection/i,
  );
  expect(profileCalls).toBe(3);
});

test("profile session expiry returns to the shared login boundary", async () => {
  let profileCalls = 0;
  createIdentityThenProfile(() => {
    profileCalls += 1;
    if (profileCalls === 1)
      return jsonResponse(
        { detail: { code: "botanical_profile_not_found" } },
        404,
      );
    return jsonResponse({ detail: "Authentication required" }, 401);
  });
  const user = await createSelectedIdentity();

  await user.type(
    await screen.findByLabelText("Description"),
    "Reference text",
  );
  await user.click(screen.getByRole("button", { name: "Save profile" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    /session expired.*sign in again/i,
  );
  expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
});

test("primary navigation switches accessibly to the empty supplier directory", async () => {
  authenticatedThen((path) => {
    if (path === "/api/v1/suppliers") return jsonResponse([]);
    throw new Error(`unexpected request: ${path}`);
  });
  const user = await openSuppliers();
  expect(screen.getByRole("button", { name: "Suppliers" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  expect(
    await screen.findByRole("heading", { name: "Suppliers" }),
  ).toBeInTheDocument();
  expect(screen.getByText("No suppliers yet.")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "+ New supplier" }));
  expect(
    screen.getByLabelText("Name", { selector: "#new-supplier-name" }),
  ).toHaveFocus();
  expect(
    screen
      .getByLabelText("Name", { selector: "#new-supplier-name" })
      .closest(".creation-panel"),
  ).not.toBeNull();
  expect(screen.getByLabelText("Name")).toBeRequired();
  expect(screen.getByLabelText("Kind").tagName).toBe("SELECT");
  for (const kind of [
    "Seller",
    "Nursery",
    "Supermarket",
    "Person",
    "Exchange",
    "Other",
  ])
    expect(screen.getByRole("option", { name: kind })).toBeInTheDocument();
  const newSupplier = screen.getByRole("button", { name: "+ New supplier" });
  await user.click(screen.getByRole("button", { name: "Cancel" }));
  expect(newSupplier).toHaveAttribute("aria-expanded", "false");
  expect(newSupplier).toHaveFocus();
  await user.click(
    screen.getByRole("button", { name: "Botanical identities" }),
  );
  expect(
    screen.getByRole("heading", { name: "Botanical identities" }),
  ).toBeInTheDocument();
});

test("supplier directory loading, failure, and retry controls are explicit", async () => {
  authenticatedThen((path) => {
    if (path === "/api/v1/suppliers")
      return new Promise<Response>(() => undefined);
    throw new Error(`unexpected request: ${path}`);
  });
  await openSuppliers();
  expect(await screen.findByText("Loading suppliers…")).toBeInTheDocument();
  expect(screen.getByLabelText("Filter suppliers")).toBeDisabled();
  cleanup();
  vi.restoreAllMocks();
  authenticatedThen((path) => {
    if (path === "/api/v1/suppliers")
      return jsonResponse({ detail: "error" }, 500);
    throw new Error(`unexpected request: ${path}`);
  });
  await openSuppliers();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /could not load the supplier directory/i,
  );
  expect(screen.getByRole("button", { name: "Retry directory" })).toBeEnabled();
});

test("keyboard supplier creation needs only name and kind and sends CSRF", async () => {
  const requests: { path: string; init?: RequestInit }[] = [];
  let suppliers: (typeof supplier)[] = [];
  authenticatedThen((path, init) => {
    requests.push({ path, init });
    if (path === "/api/v1/suppliers" && init?.method === "POST") {
      suppliers = [supplier];
      return jsonResponse(supplier, 201);
    }
    if (path === "/api/v1/suppliers") return jsonResponse(suppliers);
    throw new Error(`unexpected request: ${path}`);
  });
  const user = await openSuppliers();
  const newSupplier = await screen.findByRole("button", {
    name: "+ New supplier",
  });
  expect(newSupplier).toHaveAttribute("aria-expanded", "false");
  expect(
    screen.queryByLabelText("Name", { selector: "#new-supplier-name" }),
  ).not.toBeInTheDocument();
  await user.click(newSupplier);
  await user.type(await screen.findByLabelText("Name"), "Rare Palm Seeds");
  await user.keyboard("{Enter}");
  expect(
    await screen.findByRole("heading", { name: "Rare Palm Seeds" }),
  ).toBeInTheDocument();
  const create = requests.find(
    ({ path, init }) => path === "/api/v1/suppliers" && init?.method === "POST",
  );
  expect(create?.init?.body).toBe(
    JSON.stringify({ name: "Rare Palm Seeds", kind: "seller" }),
  );
  expect(new Headers(create?.init?.headers).get("X-CSRF-Token")).toBe(
    "botanical-csrf",
  );
  expect(newSupplier).toHaveAttribute("aria-expanded", "false");
  expect(newSupplier).toHaveFocus();
});

test("supplier filtering, keyboard selection, optional details, editing, and lifecycle work", async () => {
  const nursery = {
    ...supplier,
    id: "01900000-0000-7000-8000-000000000201",
    name: "Local nursery",
    kind: "nursery" as const,
    website: null,
    email: "local@example.com",
    phone: null,
    notes: null,
  };
  let suppliers = [nursery, supplier];
  authenticatedThen((path, init) => {
    if (path === "/api/v1/suppliers" && !init?.method)
      return jsonResponse(suppliers);
    if (path === `/api/v1/suppliers/${supplier.id}` && init?.method === "PUT") {
      if (typeof init.body !== "string") throw new Error("expected JSON body");
      const body = JSON.parse(init.body) as Record<string, string>;
      suppliers = [
        { ...supplier, ...body, updated_at: "2026-08-30T11:00:00Z" },
        nursery,
      ];
      return jsonResponse(suppliers[0]);
    }
    if (path === `/api/v1/suppliers/${supplier.id}/retire`) {
      suppliers = [
        { ...suppliers[0], retired_at: "2026-08-30T12:00:00Z" },
        nursery,
      ];
      return jsonResponse(suppliers[0]);
    }
    if (path === `/api/v1/suppliers/${supplier.id}/reactivate`) {
      suppliers = [{ ...suppliers[0], retired_at: null }, nursery];
      return jsonResponse(suppliers[0]);
    }
    throw new Error(`unexpected request: ${path}`);
  });
  const user = await openSuppliers();
  const filter = await screen.findByLabelText("Filter suppliers");
  await user.type(filter, "sales@example.com");
  expect(screen.queryByText("Local nursery")).not.toBeInTheDocument();
  const record = screen.getByRole("button", { name: /Rare Palm Seeds/i });
  record.focus();
  await user.keyboard("{Enter}");
  expect(record).toHaveAttribute("aria-pressed", "true");
  expect(
    screen.getByRole("link", { name: "Visit supplier website" }),
  ).toHaveAttribute("href", supplier.website);
  expect(screen.getByRole("link", { name: supplier.email })).toHaveAttribute(
    "href",
    `mailto:${supplier.email}`,
  );
  expect(
    screen.getAllByText(/International seller\.\s+Ships seasonally\./),
  ).toHaveLength(1);
  await user.click(screen.getByRole("button", { name: "Edit supplier" }));
  const editName = screen.getByLabelText("Name", {
    selector: "#edit-supplier-name",
  });
  await user.clear(editName);
  await user.type(editName, "Rare Palm Seeds Europe");
  await user.click(screen.getByRole("button", { name: "Save supplier" }));
  expect(await screen.findByText(/was updated/i)).toBeInTheDocument();
  await user.click(screen.getByLabelText("More supplier actions"));
  await user.click(screen.getByRole("button", { name: "Retire supplier" }));
  expect(
    await screen.findByText("This supplier is retired."),
  ).toBeInTheDocument();
  await user.click(screen.getByLabelText("More supplier actions"));
  await user.click(screen.getByRole("button", { name: "Reactivate supplier" }));
  await waitFor(() => {
    expect(
      screen.queryByText("This supplier is retired."),
    ).not.toBeInTheDocument();
  });
});

test("supplier validation, forbidden saves, and session expiry are explicit", async () => {
  let status = 422;
  authenticatedThen((path, init) => {
    if (path === "/api/v1/suppliers" && init?.method === "POST") {
      if (status === 422)
        return jsonResponse(
          {
            detail: [
              {
                loc: ["body", "website"],
                msg: "Value error",
                type: "value_error",
                input: "bad",
              },
            ],
          },
          422,
        );
      if (status === 403)
        return jsonResponse({ detail: "Request forbidden" }, 403);
      return jsonResponse({ detail: "Authentication required" }, 401);
    }
    if (path === "/api/v1/suppliers") return jsonResponse([]);
    throw new Error(`unexpected request: ${path}`);
  });
  const user = await openSuppliers();
  await user.click(
    await screen.findByRole("button", { name: "+ New supplier" }),
  );
  await user.type(await screen.findByLabelText("Name"), "Source");
  await user.click(screen.getByRole("button", { name: "Create supplier" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/check website/i);
  expect(screen.getByLabelText("Name")).toHaveValue("Source");
  expect(
    screen.getByRole("button", { name: "+ New supplier" }),
  ).toHaveAttribute("aria-expanded", "true");
  status = 403;
  await user.click(screen.getByRole("button", { name: "Create supplier" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /could not authorize/i,
  );
  status = 401;
  await user.click(screen.getByRole("button", { name: "Create supplier" }));
  expect(
    await screen.findByRole("button", { name: "Sign in" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("alert")).toHaveTextContent(/session expired/i);
});

test("primary navigation opens an empty accessible location directory", async () => {
  authenticatedThen((path) => {
    if (path === "/api/v1/locations") return jsonResponse([]);
    throw new Error(`unexpected request: ${path}`);
  });
  const user = await openLocations();
  expect(screen.getByRole("button", { name: "Locations" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  expect(
    await screen.findByRole("heading", { name: "Locations" }),
  ).toBeInTheDocument();
  expect(screen.getByText("No locations yet.")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "+ New location" }));
  expect(
    screen.getByLabelText("Name", { selector: "#new-location-name" }),
  ).toHaveFocus();
  expect(screen.getByLabelText("Name")).toBeRequired();
  expect(screen.getByLabelText("Parent location").tagName).toBe("SELECT");
  expect(
    screen.getByRole("option", { name: "No parent (root location)" }),
  ).toBeInTheDocument();
  const newLocation = screen.getByRole("button", { name: "+ New location" });
  await user.click(screen.getByRole("button", { name: "Cancel" }));
  expect(newLocation).toHaveAttribute("aria-expanded", "false");
  expect(newLocation).toHaveFocus();
});

test("location hierarchy renders paths and supports keyboard selection", async () => {
  authenticatedThen((path) => {
    if (path === "/api/v1/locations")
      return jsonResponse([houseLocation, cabinetLocation, drawerLocation]);
    throw new Error(`unexpected request: ${path}`);
  });
  const user = await openLocations();
  expect(
    screen.queryByRole("button", { name: /Seed cabinet/ }),
  ).not.toBeInTheDocument();
  await user.click(await screen.findByRole("button", { name: "Expand House" }));
  await user.click(screen.getByRole("button", { name: "Expand Seed cabinet" }));
  const drawer = await screen.findByRole("button", {
    name: /Drawer A.*House → Seed cabinet → Drawer A/i,
  });
  drawer.focus();
  await user.keyboard("{Enter}");
  expect(drawer).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("heading", { name: "Drawer A" })).toBeInTheDocument();
  expect(screen.getAllByText("House → Seed cabinet → Drawer A")).toHaveLength(
    2,
  );
  expect(
    screen
      .getAllByRole("link", { name: "Plants" })
      .some((link) => link.getAttribute("href") === "#/plants"),
  ).toBe(true);
  expect(screen.getByText(/1 active, 2 total/)).toBeInTheDocument();
  expect(
    screen
      .getAllByLabelText("Usage scopes")
      .some((item) => item.textContent.includes("Seed lots")),
  ).toBe(true);
  await user.click(screen.getByRole("button", { name: "Edit location" }));
  const parent = screen.getByLabelText("Parent location", {
    selector: "#edit-location-parent",
  });
  expect(parent).not.toContainElement(
    screen.queryByRole("option", { name: /Drawer A/ }),
  );
  await user.click(screen.getByRole("button", { name: /^House.*House$/i }));
  await user.click(screen.getByRole("button", { name: "Edit location" }));
  const rootParent = screen.getByLabelText("Parent location", {
    selector: "#edit-location-parent",
  });
  expect(
    Array.from(rootParent.querySelectorAll("option"), (option) => option.value),
  ).toEqual([""]);
});

test("location creation supports roots and the selected create-child shortcut", async () => {
  const requests: { path: string; init?: RequestInit }[] = [];
  let locations: (typeof houseLocation)[] = [];
  authenticatedThen((path, init) => {
    requests.push({ path, init });
    if (path === "/api/v1/locations" && init?.method === "POST") {
      if (typeof init.body !== "string") throw new Error("expected JSON body");
      const body = JSON.parse(init.body) as {
        name: string;
        parent_id?: string;
      };
      const created = body.parent_id
        ? {
            ...cabinetLocation,
            name: body.name,
            parent_id: body.parent_id,
            display_path: `House → ${body.name}`,
          }
        : { ...houseLocation, name: body.name, display_path: body.name };
      locations = [...locations, created];
      return jsonResponse(created, 201);
    }
    if (path === "/api/v1/locations") return jsonResponse(locations);
    throw new Error(`unexpected request: ${path}`);
  });
  const user = await openLocations();
  await user.click(
    await screen.findByRole("button", { name: "+ New location" }),
  );
  await user.type(await screen.findByLabelText("Name"), "House{Enter}");
  expect(
    await screen.findByRole("heading", { name: "House" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "+ New location" }),
  ).toHaveAttribute("aria-expanded", "false");
  await user.click(screen.getByRole("button", { name: "Create child here" }));
  expect(
    screen.getByLabelText("Parent location", {
      selector: "#new-location-parent",
    }),
  ).toHaveValue(houseLocation.id);
  await user.type(
    screen.getByLabelText("Name", { selector: "#new-location-name" }),
    "Seed cabinet{Enter}",
  );
  expect(
    await screen.findByRole("heading", { name: "Seed cabinet" }),
  ).toBeInTheDocument();
  const posts = requests.filter(({ init }) => init?.method === "POST");
  expect(posts).toHaveLength(2);
  const scopes = ["plants", "sowings", "seed_lots"];
  expect(posts[0]?.init?.body).toBe(
    JSON.stringify({ name: "House", usage_scopes: scopes }),
  );
  expect(posts[1]?.init?.body).toBe(
    JSON.stringify({
      name: "Seed cabinet",
      parent_id: houseLocation.id,
      usage_scopes: scopes,
    }),
  );
  expect(new Headers(posts[1]?.init?.headers).get("X-CSRF-Token")).toBe(
    "botanical-csrf",
  );
});

test("location rename reparent retire and reactivate use hierarchy-aware controls", async () => {
  const garden = {
    ...houseLocation,
    id: "01900000-0000-7000-8000-000000000303",
    name: "Garden",
    display_path: "Garden",
  };
  const cabinetForEdit = {
    ...cabinetLocation,
    usage: {
      ...cabinetLocation.usage,
      sowings: { active: 0, total: 0 },
    },
  };
  let updateBody: Record<string, unknown> | undefined;
  let locations: LocationResponse[] = [
    garden,
    houseLocation,
    cabinetForEdit,
    drawerLocation,
  ];
  authenticatedThen((path, init) => {
    if (path === "/api/v1/locations" && !init?.method)
      return jsonResponse(locations);
    if (
      path === `/api/v1/locations/${cabinetLocation.id}` &&
      init?.method === "PUT"
    ) {
      if (typeof init.body !== "string") throw new Error("expected JSON body");
      updateBody = JSON.parse(init.body) as Record<string, unknown>;
      locations = locations.map((item) =>
        item.id === cabinetLocation.id
          ? {
              ...item,
              name: "Seed cupboard",
              parent_id: garden.id,
              display_path: "Garden → Seed cupboard",
              usage_scopes: [
                "plants",
                "seed_lots",
              ] as LocationResponse["usage_scopes"],
              updated_at: "2026-08-30T11:00:00Z",
            }
          : item,
      );
      return jsonResponse(
        locations.find(({ id }) => id === cabinetLocation.id),
      );
    }
    if (path === `/api/v1/locations/${cabinetLocation.id}/retire`) {
      locations = locations.map((item) =>
        item.id === cabinetLocation.id
          ? { ...item, retired_at: "2026-08-30T12:00:00Z" }
          : item,
      );
      return jsonResponse(
        locations.find(({ id }) => id === cabinetLocation.id),
      );
    }
    if (path === `/api/v1/locations/${cabinetLocation.id}/reactivate`) {
      locations = locations.map((item) =>
        item.id === cabinetLocation.id ? { ...item, retired_at: null } : item,
      );
      return jsonResponse(
        locations.find(({ id }) => id === cabinetLocation.id),
      );
    }
    throw new Error(`unexpected request: ${path}`);
  });
  const user = await openLocations();
  await user.click(await screen.findByRole("button", { name: "Expand House" }));
  await user.click(
    await screen.findByRole("button", { name: /Seed cabinet.*House/i }),
  );
  await user.click(screen.getByRole("button", { name: "Edit location" }));
  const name = screen.getByLabelText("Name", {
    selector: "#edit-location-name",
  });
  await user.clear(name);
  await user.type(name, "Seed cupboard");
  await user.selectOptions(
    screen.getByLabelText("Parent location", {
      selector: "#edit-location-parent",
    }),
    garden.id,
  );
  await user.click(screen.getByRole("checkbox", { name: "Sowings" }));
  await user.click(screen.getByRole("button", { name: "Save location" }));
  expect(
    await screen.findByText(/Garden → Seed cupboard was updated/),
  ).toBeInTheDocument();
  expect(updateBody).toMatchObject({
    name: "Seed cupboard",
    parent_id: garden.id,
    usage_scopes: ["plants", "seed_lots"],
  });
  await user.click(screen.getByLabelText("More location actions"));
  await user.click(screen.getByRole("button", { name: "Retire location" }));
  expect(
    await screen.findByText(/remains available for historical records/i),
  ).toBeInTheDocument();
  await user.click(screen.getByLabelText("More location actions"));
  await user.click(screen.getByRole("button", { name: "Reactivate location" }));
  await waitFor(() => {
    expect(
      screen.queryByText(/remains available for historical records/i),
    ).not.toBeInTheDocument();
  });
});

test("location deletion confirms safe leaves and explains blocked parents", async () => {
  const garden = {
    ...houseLocation,
    id: "01900000-0000-7000-8000-000000000303",
    name: "Garden",
    display_path: "Garden",
    usage: {
      plants: { active: 0, total: 0 },
      sowings: { active: 0, total: 0 },
      seed_lots: { active: 0, total: 0 },
    },
  };
  let locations = [garden, houseLocation, cabinetLocation];
  authenticatedThen((path, init) => {
    if (path === "/api/v1/locations" && !init?.method)
      return jsonResponse(locations);
    if (
      path === `/api/v1/locations/${houseLocation.id}` &&
      init?.method === "DELETE"
    )
      return jsonResponse(
        {
          detail: {
            code: "location_has_children",
            message: "Move or delete child Locations first",
          },
        },
        409,
      );
    if (
      path === `/api/v1/locations/${garden.id}` &&
      init?.method === "DELETE"
    ) {
      locations = locations.filter(({ id }) => id !== garden.id);
      return new Response(null, { status: 204 });
    }
    throw new Error(`unexpected request: ${path}`);
  });
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const user = await openLocations();
  await user.click(
    await screen.findByRole("button", { name: /^House.*House$/i }),
  );
  await user.click(screen.getByLabelText("More location actions"));
  await user.click(screen.getByRole("button", { name: "Delete location" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /move or delete child locations/i,
  );

  await user.click(screen.getByRole("button", { name: /^Garden.*Garden$/i }));
  await user.click(screen.getByLabelText("More location actions"));
  await user.click(screen.getByRole("button", { name: "Delete location" }));
  expect(await screen.findByText(/Garden was deleted/)).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: /^Garden.*Garden$/i }),
  ).not.toBeInTheDocument();
});

test("location loading failures hierarchy conflicts authorization and expiry are explicit", async () => {
  authenticatedThen((path) => {
    if (path === "/api/v1/locations")
      return new Promise<Response>(() => undefined);
    throw new Error(`unexpected request: ${path}`);
  });
  await openLocations();
  expect(await screen.findByText("Loading locations…")).toBeInTheDocument();
  cleanup();
  vi.restoreAllMocks();

  let status = 500;
  authenticatedThen((path, init) => {
    if (path === "/api/v1/locations" && init?.method === "POST") {
      if (status === 409)
        return jsonResponse(
          { detail: { code: "location_cycle", message: "Cycle" } },
          409,
        );
      if (status === 403)
        return jsonResponse({ detail: "Request forbidden" }, 403);
      return jsonResponse({ detail: "Authentication required" }, 401);
    }
    if (path === "/api/v1/locations") {
      if (status === 500) return jsonResponse({ detail: "error" }, 500);
      return jsonResponse([]);
    }
    throw new Error(`unexpected request: ${path}`);
  });
  const user = await openLocations();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /could not load the location directory/i,
  );
  status = 409;
  await user.click(screen.getByRole("button", { name: "Retry directory" }));
  await user.click(
    await screen.findByRole("button", { name: "+ New location" }),
  );
  await user.type(await screen.findByLabelText("Name"), "Shelf");
  await user.click(screen.getByRole("button", { name: "Create location" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /hierarchy cycle/i,
  );
  expect(screen.getByLabelText("Name")).toHaveValue("Shelf");
  expect(
    screen.getByRole("button", { name: "+ New location" }),
  ).toHaveAttribute("aria-expanded", "true");
  status = 403;
  await user.click(screen.getByRole("button", { name: "Create location" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /could not authorize/i,
  );
  status = 401;
  await user.click(screen.getByRole("button", { name: "Create location" }));
  expect(
    await screen.findByRole("button", { name: "Sign in" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("alert")).toHaveTextContent(/session expired/i);
});

test("Geography navigation loads, filters, and selects broad and country canonical nodes", async () => {
  authenticatedThen((path) => {
    if (path === "/api/v1/geographic-places")
      return jsonResponse([
        worldPlace,
        southAmericaPlace,
        brazilPlace,
        thailandPlace,
      ]);
    throw new Error(`unexpected request: ${path}`);
  });
  const user = await openGeography();
  expect(screen.getByRole("button", { name: "Geography" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  expect(
    await screen.findByRole("heading", { name: "Geography" }),
  ).toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: "+ New geographic place" }),
  );
  expect(
    screen.getByLabelText("Name", {
      selector: "#new-geographic-place-name",
    }),
  ).toHaveFocus();
  const newPlace = screen.getByRole("button", {
    name: "+ New geographic place",
  });
  await user.click(screen.getByRole("button", { name: "Cancel" }));
  expect(newPlace).toHaveAttribute("aria-expanded", "false");
  expect(newPlace).toHaveFocus();
  const filter = screen.getByLabelText("Filter geography");
  await user.type(filter, "Brazil");
  const brazil = screen.getByRole("button", {
    name: /Brazil.*World.*South America.*Brazil/i,
  });
  brazil.focus();
  await user.keyboard("{Enter}");
  expect(brazil).toHaveAttribute("aria-pressed", "true");
  expect(screen.getAllByText(brazilPlace.display_path).length).toBeGreaterThan(
    1,
  );
  expect(screen.getByText(/Canonical CLDR place/)).toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: "Edit local place" }),
  ).not.toBeInTheDocument();
  await user.clear(filter);
  await user.type(filter, "South America");
  await user.click(
    screen.getByRole("button", { name: /South America.*World/i }),
  );
  expect(
    screen.getByRole("heading", { name: "South America" }),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/A region is as valid as a country/i),
  ).toBeInTheDocument();
});

test("local geography creation supports Thailand to Chiang Mai to Doi Suthep and custom editing", async () => {
  const requests: { path: string; init?: RequestInit }[] = [];
  let places: GeographicPlaceResponse[] = [worldPlace, thailandPlace];
  authenticatedThen((path, init) => {
    requests.push({ path, init });
    if (path === "/api/v1/geographic-places" && init?.method === "POST") {
      if (typeof init.body !== "string") throw new Error("expected JSON body");
      const body = JSON.parse(init.body) as { name: string; parent_id: string };
      const parent = places.find(({ id }) => id === body.parent_id);
      if (!parent) throw new Error("parent missing");
      const created = {
        ...worldPlace,
        id:
          body.name === "Chiang Mai" ? "local-chiang-mai" : "local-doi-suthep",
        name: body.name,
        parent_id: body.parent_id,
        display_path: `${parent.display_path} → ${body.name}`,
        place_kind: "custom" as const,
        source_name: null,
        source_version: null,
        source_code_type: null,
        source_code: null,
      };
      places = [...places, created];
      return jsonResponse(created, 201);
    }
    if (
      path === "/api/v1/geographic-places/local-chiang-mai" &&
      init?.method === "PUT"
    ) {
      places = places.map((place) =>
        place.id === "local-chiang-mai"
          ? {
              ...place,
              name: "Chiang Mai Province",
              parent_id: worldPlace.id,
              display_path: "World → Chiang Mai Province",
              updated_at: "2026-08-30T12:00:00Z",
            }
          : place,
      );
      return jsonResponse(places.find(({ id }) => id === "local-chiang-mai"));
    }
    if (
      path === "/api/v1/geographic-places/local-chiang-mai/retire" &&
      init?.method === "POST"
    ) {
      places = places.map((place) =>
        place.id === "local-chiang-mai"
          ? { ...place, retired_at: "2026-08-30T12:05:00Z" }
          : place,
      );
      return jsonResponse(places.find(({ id }) => id === "local-chiang-mai"));
    }
    if (
      path === "/api/v1/geographic-places/local-chiang-mai/reactivate" &&
      init?.method === "POST"
    ) {
      places = places.map((place) =>
        place.id === "local-chiang-mai"
          ? { ...place, retired_at: null }
          : place,
      );
      return jsonResponse(places.find(({ id }) => id === "local-chiang-mai"));
    }
    if (path === "/api/v1/geographic-places") return jsonResponse(places);
    throw new Error(`unexpected request: ${path}`);
  });
  const user = await openGeography();
  await user.type(await screen.findByLabelText("Filter geography"), "Thailand");
  await user.click(screen.getByRole("button", { name: /Thailand.*World/i }));
  await user.click(
    screen.getByRole("button", { name: "Create local child here" }),
  );
  await user.type(
    screen.getByLabelText("Name", {
      selector: "#new-geographic-place-name",
    }),
    "Chiang Mai{Enter}",
  );
  expect(
    await screen.findByRole("heading", { name: "Chiang Mai" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "+ New geographic place" }),
  ).toHaveAttribute("aria-expanded", "false");
  await user.click(
    screen.getByRole("button", { name: "Create local child here" }),
  );
  await user.type(
    screen.getByLabelText("Name", {
      selector: "#new-geographic-place-name",
    }),
    "Doi Suthep{Enter}",
  );
  expect(
    await screen.findByText(/Thailand → Chiang Mai → Doi Suthep was created/i),
  ).toBeInTheDocument();

  await user.clear(screen.getByLabelText("Filter geography"));
  await user.click(screen.getByRole("button", { name: /Chiang Mai.*Local/i }));
  await user.click(
    screen.getByRole("button", { name: "Edit geographic place" }),
  );
  const editName = screen.getByLabelText("Name", {
    selector: "#edit-geographic-place-name",
  });
  await user.clear(editName);
  await user.type(editName, "Chiang Mai Province");
  await user.selectOptions(
    screen.getByLabelText("Parent geographic place", {
      selector: "#edit-geographic-place-parent",
    }),
    worldPlace.id,
  );
  await user.click(screen.getByRole("button", { name: "Save local place" }));
  expect(
    await screen.findByText(/World → Chiang Mai Province was updated/i),
  ).toBeInTheDocument();
  await user.click(screen.getByLabelText("More geographic place actions"));
  await user.click(screen.getByRole("button", { name: "Retire local place" }));
  expect(
    await screen.findByText(/retained for historical provenance/i),
  ).toBeInTheDocument();
  await user.click(screen.getByLabelText("More geographic place actions"));
  await user.click(
    screen.getByRole("button", { name: "Reactivate local place" }),
  );
  await waitFor(() => {
    expect(
      screen.queryByText(/retained for historical provenance/i),
    ).not.toBeInTheDocument();
  });
  const post = requests.find(({ init }) => init?.method === "POST");
  expect(new Headers(post?.init?.headers).get("X-CSRF-Token")).toBe(
    "botanical-csrf",
  );
});

test("geography loading, failure, validation, authorization, and session expiry are explicit", async () => {
  authenticatedThen((path) => {
    if (path === "/api/v1/geographic-places")
      return new Promise<Response>(() => undefined);
    throw new Error(`unexpected request: ${path}`);
  });
  await openGeography();
  expect(await screen.findByText("Loading geography…")).toBeInTheDocument();
  cleanup();
  vi.restoreAllMocks();

  let status = 500;
  authenticatedThen((path, init) => {
    if (path === "/api/v1/geographic-places" && init?.method === "POST") {
      if (status === 422)
        return jsonResponse(
          {
            detail: [
              {
                loc: ["body", "name"],
                msg: "Value error, Name must not be blank",
                type: "value_error",
                input: " ",
              },
            ],
          },
          422,
        );
      if (status === 403)
        return jsonResponse({ detail: "Request forbidden" }, 403);
      return jsonResponse({ detail: "Authentication required" }, 401);
    }
    if (path === "/api/v1/geographic-places") {
      if (status === 500) return jsonResponse({ detail: "error" }, 500);
      return jsonResponse([worldPlace]);
    }
    throw new Error(`unexpected request: ${path}`);
  });
  const user = await openGeography();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /could not load the geography directory/i,
  );
  status = 422;
  await user.click(screen.getByRole("button", { name: "Retry directory" }));
  await user.click(
    await screen.findByRole("button", { name: "+ New geographic place" }),
  );
  await user.selectOptions(
    await screen.findByLabelText("Parent geographic place"),
    worldPlace.id,
  );
  await user.type(screen.getByLabelText("Name"), " {Enter}");
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /cannot be blank/i,
  );
  expect(
    screen.getByRole("button", { name: "+ New geographic place" }),
  ).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByLabelText("Name")).toHaveValue(" ");
  status = 403;
  await user.type(screen.getByLabelText("Name"), "Local{Enter}");
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /could not authorize/i,
  );
  status = 401;
  await user.type(screen.getByLabelText("Name"), "{Enter}");
  expect(
    await screen.findByRole("button", { name: "Sign in" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("alert")).toHaveTextContent(/session expired/i);
});
