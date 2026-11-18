import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";

import { App } from "../App";
import { EvidenceTiles } from "../occurrence-map/EvidenceTiles";
import { openFormSection } from "../test/formSections";
import {
  AuthRequestLockedError,
  StaleAuthEpochError,
  attachAuthRequestGate,
  getProtectedAuthEpoch,
  isProtectedRequestAuthorized,
  requestJson,
  syncAuthRequestGate,
} from "./api";
import { AuthProvider } from "./AuthProvider";
import { useAuth } from "./context";

const identityId = "01900000-0000-7000-8000-000000000101";
const supplierId = "01900000-0000-7000-8000-000000000301";
const locationId = "01900000-0000-7000-8000-000000000401";
const placeId = "01900000-0000-7000-8000-000000000501";
const plantId = "01900000-0000-7000-8000-000000000701";

const identity = {
  id: identityId,
  scientific_name: "Persea americana",
  cultivar_name: null,
  common_name: "Avocado",
  display_label: "Persea americana",
  created_at: "2026-08-31T10:00:00Z",
  updated_at: "2026-08-31T10:00:00Z",
};

const supplier = {
  id: supplierId,
  name: "Rossi Nursery",
  kind: "nursery",
  website: null,
  email: null,
  phone: null,
  notes: null,
  retired_at: null,
  created_at: "2026-08-31T10:00:00Z",
  updated_at: "2026-08-31T10:00:00Z",
};

const location = {
  id: locationId,
  name: "Bench 4",
  parent_id: null,
  display_path: "Greenhouse → Bench 4",
  retired_at: null,
  created_at: "2026-08-31T10:00:00Z",
  updated_at: "2026-08-31T10:00:00Z",
};

const place = {
  id: placeId,
  name: "Sicily",
  parent_id: "world",
  display_path: "World → Europe → Italy → Sicily",
  place_kind: "custom",
  place_type: "other_named_area",
  provenance_site_count: 0,
  direct_usage_count: 0,
  source_name: null,
  source_version: null,
  source_code_type: null,
  source_code: null,
  retired_at: null,
  created_at: "2026-08-31T10:00:00Z",
  updated_at: "2026-08-31T10:00:00Z",
};

function makePlant(label = "Avocado #1", notes = "Grafted specimen.") {
  return {
    id: plantId,
    botanical_identity_id: identityId,
    botanical_identity: { id: identityId, display_label: "Persea americana" },
    label,
    originating_sowing_id: null,
    originating_sowing: null,
    originating_plant_group_id: null,
    originating_plant_group: null,
    direct_origin_kind: "purchased",
    direct_origin_detail: null,
    supplier_id: supplierId,
    supplier: { id: supplierId, name: supplier.name },
    material_provenance_place_id: placeId,
    material_provenance: { id: placeId, display_path: place.display_path },
    location_id: locationId,
    location: { id: locationId, display_path: location.display_path },
    collection_entry_date: { precision: "year", year: 2025 },
    lifecycle: "active",
    notes,
    created_at: "2026-08-31T10:00:00Z",
    updated_at: "2026-08-31T10:00:00Z",
  };
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function methodOf(init?: RequestInit): string {
  return (init?.method ?? "GET").toUpperCase();
}

function pathOf(input: RequestInfo | URL): string {
  return typeof input === "string"
    ? input
    : input instanceof URL
      ? input.toString()
      : input.url;
}

function parseBody(
  init?: RequestInit,
): Record<string, string | null | undefined> {
  return JSON.parse(
    typeof init?.body === "string" ? init.body : "{}",
  ) as Record<string, string | null | undefined>;
}

function mockSyncFetch(
  handler: (input: RequestInfo | URL, init?: RequestInit) => Response,
) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((input, init) => Promise.resolve(handler(input, init)));
}

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
  window.history.replaceState(null, "", "#/dashboard");
  window.localStorage.clear();
  window.sessionStorage.clear();
});

async function openPlantEditDialog(user: ReturnType<typeof userEvent.setup>) {
  await act(async () => {
    await vi.dynamicImportSettled();
  });
  await user.click(
    await screen.findByRole("button", { name: "More record actions" }),
  );
  await user.click(await screen.findByRole("button", { name: "Edit Plant" }));
}

test("reauthentication preserves EditWorkspace Plant draft, traps Escape/Tab, unlocks focus for same user, and leaves zero storage leakage", async () => {
  let currentPlant = makePlant();
  let currentSession = {
    user_id: "owner-1",
    login_name: "alice",
    display_name: "Alice Owner",
    owner: true,
  };
  let csrfToken = "csrf-epoch-1";
  let expireNextPatch = true;
  let blockProtectedReads = false;
  const protectedRequestsDuringLock: string[] = [];
  const patchCsrfHeaders: string[] = [];

  const fetchSpy = mockSyncFetch((input, init) => {
    const path = pathOf(input);
    const method = methodOf(init);
    if (path.endsWith("/auth/session")) return json(currentSession);
    if (path.endsWith("/auth/csrf")) return json({ csrf_token: csrfToken });
    if (path.endsWith("/health")) return json({ status: "ok" });
    if (path === "/api/v1/auth/login" && method === "POST") {
      const body = parseBody(init);
      if (body.password !== "valid-secret") {
        return json({ detail: "Invalid login name or password." }, 401);
      }
      csrfToken = "csrf-epoch-2";
      blockProtectedReads = false;
      currentSession = {
        user_id: "owner-1",
        login_name: body.login_name ?? "alice",
        display_name: "Alice Owner",
        owner: true,
      };
      return json({ ...currentSession, csrf_token: csrfToken });
    }
    if (blockProtectedReads) {
      protectedRequestsDuringLock.push(`${method} ${path}`);
      return json({ detail: "Should not have been called while locked" }, 500);
    }
    if (path === "/api/v1/plants" && method === "GET")
      return json([currentPlant]);
    if (path === "/api/v1/plant-groups" && method === "GET") return json([]);
    if (path === `/api/v1/plants/${plantId}` && method === "GET")
      return json(currentPlant);
    if (path === `/api/v1/plants/${plantId}` && method === "PUT") {
      const headers = new Headers(init?.headers);
      patchCsrfHeaders.push(headers.get("X-CSRF-Token") ?? "");
      if (expireNextPatch) {
        expireNextPatch = false;
        blockProtectedReads = true;
        return json({ detail: "Authentication required" }, 401);
      }
      const body = parseBody(init);
      currentPlant = makePlant(
        body.label ?? currentPlant.label,
        body.notes ?? "",
      );
      return json(currentPlant);
    }
    if (path.endsWith("/events")) return json([]);
    if (path === "/api/v1/botanical-identities") return json([identity]);
    if (path === "/api/v1/provenance-sites") return json([]);
    if (path === "/api/v1/sowings") return json([]);
    if (path === "/api/v1/suppliers") return json([supplier]);
    if (path === "/api/v1/geographic-places") return json([place]);
    if (path === "/api/v1/locations") return json([location]);
    throw new Error(`Unhandled fetch: ${method} ${path}`);
  });

  window.history.replaceState(null, "", `#/plants/${plantId}`);
  const user = userEvent.setup();
  const { container } = render(<App />);

  await openPlantEditDialog(user);

  const editDialog = await screen.findByRole("dialog", { name: "Edit Plant" });
  const labelInput = within(editDialog).getByLabelText("Label");
  await user.clear(labelInput);
  await user.type(labelInput, "Avocado #1 edited draft");

  await openFormSection(user, "Lifecycle & notes");
  const notesInput = within(editDialog).getByLabelText("Notes");
  await user.clear(notesInput);
  await user.type(notesInput, "Sensitive unsaved graft note.");

  const saveButton = within(editDialog).getByRole("button", {
    name: "Save changes",
  });
  saveButton.focus();
  await user.click(saveButton);

  const reauthHeading = await screen.findByRole("heading", {
    name: "Session expired — sign in again",
  });
  const reauthDialog = reauthHeading.closest("dialog");
  if (!reauthDialog) throw new Error("Expected reauth dialog element");
  expect(
    (document.getElementById("reauth-login-name") as HTMLInputElement).value,
  ).toBe("alice");
  expect(screen.getByRole("alert")).toHaveTextContent(/session expired/i);

  // Retained workspace remains direct child of <main> (CSS main > .application-shell) and is hidden/inert.
  const mainEl = container.querySelector("main");
  const appShell = mainEl?.querySelector(":scope > .application-shell");
  expect(appShell).not.toBeNull();
  expect(appShell).toHaveAttribute("hidden");
  expect(appShell).toHaveAttribute("inert");
  expect(appShell).toHaveAttribute("aria-hidden", "true");

  // No draft or auth tokens leaked to browser storage.
  for (const storage of [window.localStorage, window.sessionStorage]) {
    const dump = JSON.stringify(
      Object.fromEntries(
        Object.keys(storage)
          .filter((key) => key !== "florabase.appearance.v1")
          .map((key) => [key, storage.getItem(key)]),
      ),
    );
    expect(dump).not.toContain("Avocado #1 edited draft");
    expect(dump).not.toContain("Sensitive unsaved graft note");
    expect(dump).not.toContain("csrf-epoch");
    expect(dump).not.toContain("valid-secret");
  }

  // Protected request gate refuses requests synchronously while locked without touching fetch.
  const callsBeforeLockCheck = fetchSpy.mock.calls.length;
  await expect(requestJson("/api/v1/plants")).rejects.toBeInstanceOf(
    AuthRequestLockedError,
  );
  expect(fetchSpy.mock.calls.length).toBe(callsBeforeLockCheck);

  // Escape and Tab cannot close #reauth-dialog or underlying EditWorkspace.
  fireEvent.keyDown(reauthDialog, { key: "Escape" });
  const cancelEvent = new Event("cancel", { cancelable: true });
  reauthDialog.dispatchEvent(cancelEvent);
  expect(cancelEvent.defaultPrevented).toBe(true);
  await user.keyboard("{Tab}");
  expect(reauthHeading).toBeInTheDocument();

  // Failed reauthentication keeps draft locked, clears password input, and preserves EditWorkspace.
  const passwordInput = document.getElementById(
    "reauth-password",
  ) as HTMLInputElement;
  await user.type(passwordInput, "wrong-password");
  await user.click(screen.getByRole("button", { name: "Sign in" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /login name or password was not accepted/i,
  );
  expect(passwordInput.value).toBe("");
  expect(appShell).toHaveAttribute("hidden");

  // Same-user reauthentication unlocks without losing unsaved edits or auto-replaying PUT.
  await user.type(passwordInput, "valid-secret");
  await user.click(screen.getByRole("button", { name: "Sign in" }));

  await waitFor(() => {
    expect(
      screen.queryByRole("heading", {
        name: "Session expired — sign in again",
      }),
    ).not.toBeInTheDocument();
  });
  expect(protectedRequestsDuringLock).toEqual([]);
  expect(appShell).not.toHaveAttribute("hidden");
  expect(appShell).not.toHaveAttribute("inert");
  expect(appShell).not.toHaveAttribute("aria-hidden");
  // Did NOT auto-replay PUT on login: only the expired epoch-1 PUT happened so far.
  expect(patchCsrfHeaders).toEqual(["csrf-epoch-1"]);

  // Dirty form inputs and EditWorkspace modal survived completely intact!
  const restoredLabel =
    within(editDialog).getByLabelText<HTMLInputElement>("Label");
  const restoredNotes =
    within(editDialog).getByLabelText<HTMLTextAreaElement>("Notes");
  expect(restoredLabel.value).toBe("Avocado #1 edited draft");
  expect(restoredNotes.value).toBe("Sensitive unsaved graft note.");
  expect(document.activeElement).toBe(
    within(editDialog).getByRole("button", { name: "Save changes" }),
  );

  // Manual retry succeeds using the fresh Epoch-2 CSRF token!
  await user.click(
    within(editDialog).getByRole("button", { name: "Save changes" }),
  );
  await waitFor(() => {
    expect(patchCsrfHeaders).toEqual(["csrf-epoch-1", "csrf-epoch-2"]);
  });
  expect(
    await screen.findByRole("heading", { name: /Avocado #1 edited draft/i }),
  ).toBeInTheDocument();
});

test("cross-user login (Scenario H) synchronously destroys prior owner tree with zero transient exposure", async () => {
  const plantsAlice = [makePlant("Alice secret botanical specimen", "Private")];
  const plantsBob = [makePlant("Bob specimen", "Public")];
  let currentUser = "alice";
  let blockProtectedReads = false;

  mockSyncFetch((input, init) => {
    const path = pathOf(input);
    const method = methodOf(init);
    if (path.endsWith("/auth/session"))
      return json({
        user_id: currentUser === "alice" ? "user-alice" : "user-bob",
        login_name: currentUser,
        display_name: currentUser === "alice" ? "Alice" : "Bob",
        owner: currentUser === "alice",
      });
    if (path.endsWith("/auth/csrf"))
      return json({ csrf_token: `csrf-${currentUser}` });
    if (path.endsWith("/health")) return json({ status: "ok" });
    if (path === "/api/v1/auth/login" && method === "POST") {
      currentUser = "bob";
      blockProtectedReads = false;
      return json({
        user_id: "user-bob",
        login_name: "bob",
        display_name: "Bob",
        owner: false,
        csrf_token: "csrf-bob",
      });
    }
    if (blockProtectedReads) return json({ detail: "Locked" }, 500);
    if (path === "/api/v1/plants" && method === "GET")
      return json(currentUser === "alice" ? plantsAlice : plantsBob);
    if (path === "/api/v1/plant-groups" && method === "GET") return json([]);
    if (path === `/api/v1/plants/${plantId}` && method === "GET")
      return json(currentUser === "alice" ? plantsAlice[0] : plantsBob[0]);
    if (path === `/api/v1/plants/${plantId}` && method === "PUT") {
      blockProtectedReads = true;
      return json({ detail: "Expired" }, 401);
    }
    if (path.endsWith("/events")) return json([]);
    if (path === "/api/v1/botanical-identities") return json([identity]);
    if (path === "/api/v1/provenance-sites") return json([]);
    if (path === "/api/v1/sowings") return json([]);
    if (path === "/api/v1/suppliers") return json([supplier]);
    if (path === "/api/v1/geographic-places") return json([place]);
    if (path === "/api/v1/locations") return json([location]);
    throw new Error(`Unhandled fetch: ${method} ${path}`);
  });

  window.history.replaceState(null, "", `#/plants/${plantId}`);
  const user = userEvent.setup();
  const { container } = render(<App />);

  await openPlantEditDialog(user);
  const labelInput = await screen.findByLabelText("Label");
  await user.clear(labelInput);
  await user.type(labelInput, "Alice transient secret draft");
  await user.click(screen.getByRole("button", { name: "Save changes" }));

  await screen.findByRole("heading", {
    name: "Session expired — sign in again",
  });

  // Observe every DOM mutation once Bob submits credentials to prove zero transient frame of Alice's workspace.
  let observedAliceLeakAfterBobLogin = false;
  const observer = new MutationObserver(() => {
    const visibleShell = container.querySelector(
      ".application-shell:not([hidden])",
    );
    if (visibleShell?.textContent.includes("Alice transient secret draft")) {
      observedAliceLeakAfterBobLogin = true;
    }
  });
  observer.observe(container, {
    childList: true,
    subtree: true,
    attributes: true,
    characterData: true,
  });

  const loginInput = document.getElementById(
    "reauth-login-name",
  ) as HTMLInputElement;
  await user.clear(loginInput);
  await user.type(loginInput, "bob");
  await user.type(
    document.getElementById("reauth-password") as HTMLInputElement,
    "bob-secret",
  );
  await user.click(screen.getByRole("button", { name: "Sign in" }));

  await waitFor(() => {
    expect(
      screen.queryByRole("heading", {
        name: "Session expired — sign in again",
      }),
    ).not.toBeInTheDocument();
  });
  observer.disconnect();

  expect(observedAliceLeakAfterBobLogin).toBe(false);
  expect(
    screen.queryByDisplayValue("Alice transient secret draft"),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByText(/Alice secret botanical specimen/),
  ).not.toBeInTheDocument();
  expect(await screen.findByText(/Signed in as Bob/i)).toBeInTheDocument();
  expect(await screen.findAllByText(/Bob specimen/i)).not.toHaveLength(0);
});

test("explicit Discard unsaved changes and sign out destroys retained tree cleanly", async () => {
  let loggedOut = false;
  mockSyncFetch((input, init) => {
    const path = pathOf(input);
    const method = methodOf(init);
    if (path.endsWith("/auth/session"))
      return loggedOut
        ? json({ detail: "Not signed in" }, 401)
        : json({
            user_id: "owner-1",
            login_name: "alice",
            display_name: "Alice",
            owner: true,
          });
    if (path.endsWith("/auth/csrf")) return json({ csrf_token: "csrf-1" });
    if (path.endsWith("/auth/logout") && method === "POST") {
      loggedOut = true;
      return new Response(null, { status: 204 });
    }
    if (path.endsWith("/health")) return json({ status: "ok" });
    if (path === "/api/v1/plants" && method === "GET")
      return json([makePlant()]);
    if (path === "/api/v1/plant-groups" && method === "GET") return json([]);
    if (path === `/api/v1/plants/${plantId}` && method === "GET")
      return json(makePlant());
    if (path === `/api/v1/plants/${plantId}` && method === "PUT")
      return json({ detail: "Expired" }, 401);
    if (path.endsWith("/events")) return json([]);
    if (path === "/api/v1/botanical-identities") return json([identity]);
    if (path === "/api/v1/provenance-sites") return json([]);
    if (path === "/api/v1/sowings") return json([]);
    if (path === "/api/v1/suppliers") return json([supplier]);
    if (path === "/api/v1/geographic-places") return json([place]);
    if (path === "/api/v1/locations") return json([location]);
    throw new Error(`Unhandled fetch: ${method} ${path}`);
  });

  window.history.replaceState(null, "", `#/plants/${plantId}`);
  const user = userEvent.setup();
  render(<App />);

  await openPlantEditDialog(user);
  const labelInput = await screen.findByLabelText("Label");
  await user.clear(labelInput);
  await user.type(labelInput, "Draft to discard");
  await user.click(screen.getByRole("button", { name: "Save changes" }));

  await screen.findByRole("heading", {
    name: "Session expired — sign in again",
  });
  await user.click(
    screen.getByRole("button", {
      name: "Discard unsaved changes and sign out",
    }),
  );

  // Cold Sign-in form replaces the retained tree cleanly.
  expect(
    await screen.findByText(/Sign in with the local owner account/i),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
  expect(
    screen.queryByDisplayValue("Draft to discard"),
  ).not.toBeInTheDocument();
  expect(document.querySelector(".application-shell")).toBeNull();
});

test("backend outage (Scenario F: 503 then network recovery) keeps session authenticated, retains draft, and saves on manual retry", async () => {
  let failMode: "503" | "network" | "none" = "503";
  let putCount = 0;
  let currentPlant = makePlant();

  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const path = pathOf(input);
    const method = methodOf(init);
    if (path.endsWith("/auth/session"))
      return Promise.resolve(
        json({
          user_id: "owner-1",
          login_name: "alice",
          display_name: "Alice",
          owner: true,
        }),
      );
    if (path.endsWith("/auth/csrf"))
      return Promise.resolve(json({ csrf_token: "csrf-1" }));
    if (path.endsWith("/health"))
      return Promise.resolve(json({ status: "ok" }));
    if (path === "/api/v1/plants" && method === "GET")
      return Promise.resolve(json([currentPlant]));
    if (path === "/api/v1/plant-groups" && method === "GET")
      return Promise.resolve(json([]));
    if (path === `/api/v1/plants/${plantId}` && method === "GET")
      return Promise.resolve(json(currentPlant));
    if (path === `/api/v1/plants/${plantId}` && method === "PUT") {
      putCount++;
      if (failMode === "503")
        return Promise.resolve(json({ detail: "Unavailable" }, 503));
      if (failMode === "network")
        return Promise.reject(new TypeError("Failed to fetch"));
      const body = parseBody(init);
      currentPlant = makePlant(body.label ?? currentPlant.label);
      return Promise.resolve(json(currentPlant));
    }
    if (path.endsWith("/events")) return Promise.resolve(json([]));
    if (path === "/api/v1/botanical-identities")
      return Promise.resolve(json([identity]));
    if (path === "/api/v1/provenance-sites") return Promise.resolve(json([]));
    if (path === "/api/v1/sowings") return Promise.resolve(json([]));
    if (path === "/api/v1/suppliers") return Promise.resolve(json([supplier]));
    if (path === "/api/v1/geographic-places")
      return Promise.resolve(json([place]));
    if (path === "/api/v1/locations") return Promise.resolve(json([location]));
    throw new Error(`Unhandled fetch: ${method} ${path}`);
  });

  window.history.replaceState(null, "", `#/plants/${plantId}`);
  const user = userEvent.setup();
  render(<App />);
  await openPlantEditDialog(user);
  const labelInput = await screen.findByLabelText("Label");
  await user.clear(labelInput);
  await user.type(labelInput, "Avocado after outage");

  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /could not save|check the connection/i,
  );
  expect(
    screen.queryByRole("heading", { name: "Session expired — sign in again" }),
  ).not.toBeInTheDocument();

  failMode = "network";
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /could not save|check the connection/i,
  );

  failMode = "none";
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(
    await screen.findByRole("heading", { name: /Avocado after outage/i }),
  ).toBeInTheDocument();
  expect(putCount).toBe(3);
});

test("Scenarios A & B: requestJson fences stale Epoch-1 200 responses and delayed Epoch-1 401 errors after Epoch-2 login", async () => {
  const onUnauthorized = vi.fn();
  const epoch1Gate = syncAuthRequestGate({ locked: false, advanceEpoch: true });
  const epoch1Response = deferred<Response>();
  const epoch1Delayed401 = deferred<Response>();
  const epoch1BodyJson = deferred<unknown>();

  const detach = attachAuthRequestGate(onUnauthorized, false);
  const initialEpoch = getProtectedAuthEpoch();

  const fetchMock = vi.spyOn(globalThis, "fetch");
  fetchMock.mockImplementationOnce(() => epoch1Response.promise);
  fetchMock.mockImplementationOnce(() => epoch1Delayed401.promise);
  fetchMock.mockImplementationOnce(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      headers: new Headers({ "Content-Type": "application/json" }),
      json: () => epoch1BodyJson.promise,
    } as unknown as Response),
  );

  const p200 = requestJson("/api/v1/plants");
  const p401 = requestJson("/api/v1/sowings");
  const pBody = requestJson("/api/v1/orders");

  // Transition to locked and then new authenticated Epoch-2 (simulating session expiry + re-login).
  syncAuthRequestGate({ locked: true, advanceEpoch: true });
  expect(isProtectedRequestAuthorized()).toBe(false);
  const nextEpoch = syncAuthRequestGate({ locked: false, advanceEpoch: true });
  expect(nextEpoch).toBeGreaterThan(initialEpoch);
  expect(epoch1Gate).toBeLessThan(nextEpoch);

  epoch1Response.resolve(json([{ id: "stale" }]));
  epoch1Delayed401.resolve(json({ detail: "Expired" }, 401));
  epoch1BodyJson.resolve([{ id: "stale-body" }]);

  await expect(p200).rejects.toBeInstanceOf(StaleAuthEpochError);
  await expect(p401).rejects.toBeInstanceOf(StaleAuthEpochError);
  await expect(pBody).rejects.toBeInstanceOf(StaleAuthEpochError);
  expect(onUnauthorized).not.toHaveBeenCalled();

  detach();
});

test("Scenario C: concurrent cookie-changing auth operations serialize without interleaving", async () => {
  const events: string[] = [];
  const loginGate = deferred<Response>();
  const logoutGate = deferred<Response>();

  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const path = pathOf(input);
    const method = methodOf(init);
    events.push(`start:${method}:${path}`);
    if (path.endsWith("/auth/session")) {
      events.push("end:GET:/auth/session");
      return json({
        user_id: "owner-1",
        login_name: "alice",
        display_name: "Alice",
        owner: true,
      });
    }
    if (path.endsWith("/auth/csrf")) {
      events.push("end:GET:/auth/csrf");
      return json({ csrf_token: "csrf-1" });
    }
    if (path.endsWith("/auth/logout")) {
      const resp = await logoutGate.promise;
      events.push("end:POST:/auth/logout");
      return resp;
    }
    if (path.endsWith("/auth/login")) {
      const resp = await loginGate.promise;
      events.push("end:POST:/auth/login");
      return resp;
    }
    throw new Error(`Unexpected fetch: ${method} ${path}`);
  });

  let api!: ReturnType<typeof useAuth>;
  function Harness() {
    api = useAuth();
    return <div>{api.state.status}</div>;
  }

  render(
    <AuthProvider>
      <Harness />
    </AuthProvider>,
  );

  await waitFor(() => {
    expect(api.state.status).toBe("authenticated");
  });

  events.length = 0;
  let logoutPromise!: Promise<void>;
  let loginPromise!: Promise<void>;
  act(() => {
    logoutPromise = api.logOut();
    loginPromise = api.logIn({ login_name: "alice", password: "secret" });
  });

  await waitFor(() => {
    expect(events).toContain("start:POST:/api/v1/auth/logout");
  });
  // Login must NOT start while logout cookie op is still in flight.
  expect(events).not.toContain("start:POST:/api/v1/auth/login");

  logoutGate.resolve(new Response(null, { status: 204 }));
  await waitFor(() => {
    expect(events).toContain("start:POST:/api/v1/auth/login");
  });
  expect(events.indexOf("end:POST:/auth/logout")).toBeLessThan(
    events.indexOf("start:POST:/api/v1/auth/login"),
  );

  loginGate.resolve(
    json({
      user_id: "owner-1",
      login_name: "alice",
      display_name: "Alice",
      owner: true,
      csrf_token: "csrf-2",
    }),
  );
  await Promise.all([logoutPromise, loginPromise]);
});

test("Scenario G: EvidenceTiles aborts in-flight tile requests and cancels pending retry timers on auth lock", async () => {
  vi.useFakeTimers();
  const detach = attachAuthRequestGate(vi.fn(), false);

  const signals: AbortSignal[] = [];
  let fetchCount = 0;
  vi.spyOn(globalThis, "fetch").mockImplementation((_input, init) => {
    fetchCount++;
    if (init?.signal) signals.push(init.signal);
    if (fetchCount === 1) {
      return Promise.resolve(new Response(null, { status: 503 }));
    }
    return new Promise<Response>(() => {
      // Keep second tile request pending until aborted.
    });
  });

  const report = vi.fn();
  const tiles = new EvidenceTiles(
    (coords) =>
      `/api/v1/tiles/${String(coords.z)}/${String(coords.x)}/${String(coords.y)}.png`,
    report,
  );
  const done1 = vi.fn();
  const done2 = vi.fn();

  tiles.createTile({ x: 0, y: 0, z: 1 } as never, done1);
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
  // Tile 1 received 503 and scheduled a 500ms retry timer.
  expect(fetchCount).toBe(1);

  tiles.createTile({ x: 1, y: 0, z: 1 } as never, done2);
  await act(async () => {
    await Promise.resolve();
  });
  expect(fetchCount).toBe(2);
  expect(signals[1]?.aborted).toBe(false);

  // Locking auth gate aborts in-flight tile requests and clears retry timers.
  syncAuthRequestGate({ locked: true, advanceEpoch: true });
  expect(signals[1]?.aborted).toBe(true);

  act(() => {
    vi.advanceTimersByTime(5000);
  });
  // Retry timer must NOT fire after lock.
  expect(fetchCount).toBe(2);

  // Creating a tile while locked fails fast with zero network traffic.
  const done3 = vi.fn();
  tiles.createTile({ x: 2, y: 0, z: 1 } as never, done3);
  expect(fetchCount).toBe(2);
  expect(done3).toHaveBeenCalledTimes(1);

  detach();
});

test("domain editors beyond PlantScreen (BotanicalIdentityScreen) retain unsaved draft across 401 recovery", async () => {
  let expireFirstPut = true;
  let savedCommon = "Avocado";
  mockSyncFetch((input, init) => {
    const path = pathOf(input);
    const method = methodOf(init);
    if (path.endsWith("/auth/session"))
      return json({
        user_id: "owner-1",
        login_name: "alice",
        display_name: "Alice",
        owner: true,
      });
    if (path.endsWith("/auth/csrf")) return json({ csrf_token: "csrf-bio" });
    if (path.endsWith("/health")) return json({ status: "ok" });
    if (path === "/api/v1/auth/login" && method === "POST")
      return json({
        user_id: "owner-1",
        login_name: "alice",
        display_name: "Alice",
        owner: true,
        csrf_token: "csrf-bio-2",
      });
    if (path === "/api/v1/botanical-identities" && method === "GET")
      return json([{ ...identity, common_name: savedCommon }]);
    if (path === `/api/v1/botanical-identities/${identityId}`) {
      if (method === "GET")
        return json({
          botanical_identity: { ...identity, common_name: savedCommon },
          ...identity,
          common_name: savedCommon,
          seed_lots: [],
          sowings: [],
          plants: [],
          plant_groups: [],
          harvests: [],
          vegetative_lots: [],
          propagation_attempts: [],
        });
      if (method === "PUT") {
        if (expireFirstPut) {
          expireFirstPut = false;
          return json({ detail: "Expired" }, 401);
        }
        const body = parseBody(init);
        savedCommon = body.common_name ?? "";
        return json({ ...identity, common_name: savedCommon });
      }
    }
    if (path.endsWith("/native-ranges") || path.endsWith("/events"))
      return json([]);
    if (path.endsWith("/cover-image") || path.endsWith("/external-taxon-link"))
      return json(null);
    if (path.includes("/profile"))
      return json({
        description: null,
        synonyms: [],
        native_ranges: [],
        native_range_status: "none",
      });
    if (path.endsWith("/occurrence-evidence")) return json({ summary: null });
    if (path.includes("/synonyms")) return json({ items: [], total: 0 });
    if (path.startsWith("/api/v1/botanical-identities/"))
      return json({
        botanical_identity: { ...identity, common_name: savedCommon },
        seed_lots: [],
        sowings: [],
        plants: [],
        plant_groups: [],
        harvests: [],
        events: [],
      });
    if (path === "/api/v1/plants") return json([]);
    if (path === "/api/v1/plant-groups") return json([]);
    if (path === "/api/v1/seed-lots") return json([]);
    if (path === "/api/v1/sowings") return json([]);
    if (path === "/api/v1/cuttings" || path.startsWith("/api/v1/vegetative"))
      return json([]);
    if (path.startsWith("/api/v1/propagation")) return json([]);
    if (path === "/api/v1/provenance-sites") return json([]);
    if (path === "/api/v1/botanical-profiles") return json(null);
    return json([]);
  });

  window.history.replaceState(null, "", `#/identities/${identityId}`);
  const user = userEvent.setup();
  render(<App />);
  await act(async () => {
    await vi.dynamicImportSettled();
  });
  await user.click(
    await screen.findByRole("button", { name: "Edit botanical identity" }),
  );
  const commonInput = await screen.findByLabelText("Common name");
  await user.clear(commonInput);
  await user.type(commonInput, "Hass avocado draft");
  await user.click(screen.getByRole("button", { name: /^Save/i }));

  await screen.findByRole("heading", {
    name: "Session expired — sign in again",
  });
  await user.type(
    document.getElementById("reauth-password") as HTMLInputElement,
    "secret",
  );
  await user.click(screen.getByRole("button", { name: "Sign in" }));

  await waitFor(() => {
    expect(
      screen.queryByRole("heading", {
        name: "Session expired — sign in again",
      }),
    ).not.toBeInTheDocument();
  });
  expect(screen.getByLabelText("Common name")).toHaveValue(
    "Hass avocado draft",
  );
});

test("tile-only HTTP 401 without JSON 401 triggers reauth dialog, preserves active dirty editor, and supports same-user save and cross-user reset", async () => {
  let currentPlant = makePlant();
  let currentUser: "alice" | "bob" = "alice";
  let csrfToken = "csrf-tile-1";
  let tileUnauthorized = false;
  const putCsrfHeaders: string[] = [];

  mockSyncFetch((input, init) => {
    const path = pathOf(input);
    const method = methodOf(init);
    if (path.endsWith("/auth/session"))
      return json({
        user_id: currentUser === "alice" ? "user-alice" : "user-bob",
        login_name: currentUser,
        display_name: currentUser === "alice" ? "Alice" : "Bob",
        owner: true,
      });
    if (path.endsWith("/auth/csrf")) return json({ csrf_token: csrfToken });
    if (path.endsWith("/health")) return json({ status: "ok" });
    if (path === "/api/v1/auth/login" && method === "POST") {
      const body = parseBody(init);
      currentUser = body.login_name === "bob" ? "bob" : "alice";
      csrfToken = currentUser === "bob" ? "csrf-bob" : "csrf-tile-2";
      tileUnauthorized = false;
      return json({
        user_id: currentUser === "alice" ? "user-alice" : "user-bob",
        login_name: currentUser,
        display_name: currentUser === "alice" ? "Alice" : "Bob",
        owner: true,
        csrf_token: csrfToken,
      });
    }
    if (path.includes("/occurrence-evidence/tiles/")) {
      if (tileUnauthorized) {
        return new Response(null, { status: 401 });
      }
      return new Response(null, { status: 204 });
    }
    if (path === "/api/v1/plants" && method === "GET")
      return json([currentPlant]);
    if (path === "/api/v1/plant-groups" && method === "GET") return json([]);
    if (path === `/api/v1/plants/${plantId}` && method === "GET")
      return json(currentPlant);
    if (path === `/api/v1/plants/${plantId}` && method === "PUT") {
      const headers = new Headers(init?.headers);
      putCsrfHeaders.push(headers.get("X-CSRF-Token") ?? "");
      const body = parseBody(init);
      currentPlant = makePlant(body.label ?? currentPlant.label);
      return json(currentPlant);
    }
    if (path.endsWith("/events")) return json([]);
    if (path === "/api/v1/botanical-identities") return json([identity]);
    if (path === "/api/v1/provenance-sites") return json([]);
    if (path === "/api/v1/sowings") return json([]);
    if (path === "/api/v1/suppliers") return json([supplier]);
    if (path === "/api/v1/geographic-places") return json([place]);
    if (path === "/api/v1/locations") return json([location]);
    throw new Error(`Unhandled fetch: ${method} ${path}`);
  });

  window.history.replaceState(null, "", `#/plants/${plantId}`);
  const user = userEvent.setup();
  const { container } = render(<App />);

  await openPlantEditDialog(user);
  const editDialog = await screen.findByRole("dialog", { name: "Edit Plant" });
  const labelInput = within(editDialog).getByLabelText("Label");
  await user.clear(labelInput);
  await user.type(labelInput, "Avocado tile recovery draft");

  // Trigger a tile-only HTTP 401 via EvidenceTiles with zero JSON 401s.
  tileUnauthorized = true;
  const tiles = new EvidenceTiles(
    (coords) =>
      `/api/v1/botanical-identities/${identityId}/occurrence-evidence/tiles/${String(coords.z)}/${String(coords.x)}/${String(coords.y)}.png`,
    vi.fn(),
  );
  tiles.createTile({ x: 0, y: 0, z: 2 } as never, vi.fn());

  const reauthHeading = await screen.findByRole("heading", {
    name: "Session expired — sign in again",
  });
  expect(reauthHeading).toBeInTheDocument();
  const appShell = container.querySelector("main > .application-shell");
  expect(appShell).toHaveAttribute("hidden");
  expect(appShell).toHaveAttribute("inert");

  // Same-user reauthentication keeps dirty editor intact and enables manual Save with new CSRF.
  await user.type(
    document.getElementById("reauth-password") as HTMLInputElement,
    "alice-secret",
  );
  await user.click(screen.getByRole("button", { name: "Sign in" }));

  await waitFor(() => {
    expect(
      screen.queryByRole("heading", {
        name: "Session expired — sign in again",
      }),
    ).not.toBeInTheDocument();
  });
  expect(within(editDialog).getByLabelText("Label")).toHaveValue(
    "Avocado tile recovery draft",
  );
  await user.click(
    within(editDialog).getByRole("button", { name: "Save changes" }),
  );
  await waitFor(() => {
    expect(putCsrfHeaders).toEqual(["csrf-tile-2"]);
  });

  // Trigger another tile-only 401 while editing and recover as Bob (Scenario H).
  await openPlantEditDialog(user);
  const editDialog2 = await screen.findByRole("dialog", { name: "Edit Plant" });
  const labelInput2 = within(editDialog2).getByLabelText("Label");
  await user.clear(labelInput2);
  await user.type(labelInput2, "Alice secret after tile 401");

  tileUnauthorized = true;
  tiles.createTile({ x: 1, y: 0, z: 2 } as never, vi.fn());
  await screen.findByRole("heading", {
    name: "Session expired — sign in again",
  });

  const loginInput = document.getElementById(
    "reauth-login-name",
  ) as HTMLInputElement;
  await user.clear(loginInput);
  await user.type(loginInput, "bob");
  await user.type(
    document.getElementById("reauth-password") as HTMLInputElement,
    "bob-secret",
  );
  await user.click(screen.getByRole("button", { name: "Sign in" }));

  await waitFor(() => {
    expect(
      screen.queryByRole("heading", {
        name: "Session expired — sign in again",
      }),
    ).not.toBeInTheDocument();
  });
  expect(
    screen.queryByDisplayValue("Alice secret after tile 401"),
  ).not.toBeInTheDocument();
  expect(await screen.findByText(/Signed in as Bob/i)).toBeInTheDocument();

  tiles.cancel();
});
