import { act, cleanup, render } from "@testing-library/react";
import { createElement } from "react";
import { afterEach, expect, test, vi } from "vitest";
import type { Coords } from "leaflet";
import {
  getProtectedAuthEpoch,
  isProtectedRequestAuthorized,
  isReauthenticationState,
} from "../auth/api";
import { AuthProvider } from "../auth/AuthProvider";
import { useAuth, type AuthContextValue } from "../auth/context";
import { acquireTestAuth } from "../test/auth";
import { EvidenceTiles } from "./EvidenceTiles";
const coords = { x: 0, y: 0, z: 1 } as Coords;
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

async function mountRealProvider(
  initialOwner: { user_id: string; login_name: string; display_name: string },
  tileHandler: (
    url: string,
    init?: RequestInit,
  ) => Promise<Response> | Response,
) {
  let activeOwner = { ...initialOwner };
  const authRef: { current: AuthContextValue | null } = { current: null };
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    const method = (init?.method ?? "GET").toUpperCase();
    if (url.endsWith("/api/v1/auth/session")) {
      return Promise.resolve(
        new Response(JSON.stringify({ ...activeOwner, owner: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    }
    if (url.endsWith("/api/v1/auth/csrf") && method === "POST") {
      return Promise.resolve(
        new Response(
          JSON.stringify({ csrf_token: `csrf-${activeOwner.user_id}` }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    }
    if (url.endsWith("/api/v1/auth/login") && method === "POST") {
      const bodyText = typeof init?.body === "string" ? init.body : "{}";
      const body = JSON.parse(bodyText) as { login_name?: string };
      if (body.login_name === "bob") {
        activeOwner = {
          user_id: "owner-bob",
          login_name: "bob",
          display_name: "Bob",
        };
      } else {
        activeOwner = { ...initialOwner };
      }
      return Promise.resolve(
        new Response(
          JSON.stringify({ csrf_token: `csrf-${activeOwner.user_id}` }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    }
    return Promise.resolve(tileHandler(url, init));
  });

  function Probe() {
    authRef.current = useAuth();
    return null;
  }

  const view = render(
    createElement(AuthProvider, { children: createElement(Probe) }),
  );
  for (let i = 0; i < 8; i += 1) {
    if (authRef.current?.state.status === "authenticated") break;
    await act(async () => {
      await Promise.resolve();
    });
  }
  const initialAuth = authRef.current;
  if (initialAuth?.state.status !== "authenticated") {
    throw new Error("Expected AuthProvider to authenticate");
  }
  return {
    getAuth: () => {
      if (!authRef.current) throw new Error("Missing auth context");
      return authRef.current;
    },
    unmount: () => {
      view.unmount();
    },
  };
}

test("empty HTTP 204 is successful and never reported as incomplete", async () => {
  const { capability } = await acquireTestAuth();
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(new Response(null, { status: 204 }));
  const report = vi.fn(),
    done = vi.fn();
  const layer = new EvidenceTiles(
    () => "/local?local_only=true",
    report,
    capability,
  );
  layer.createTile(coords, done);
  await vi.waitFor(() => {
    expect(done).toHaveBeenCalled();
  });
  expect(done.mock.calls[0][0]).toBeUndefined();
  expect(report).toHaveBeenLastCalledWith({
    failed: 0,
    missing: 0,
    pending: 0,
  });
  expect(fetch).toHaveBeenCalledTimes(1);
  layer.cancel();
});
test("transient overlay failures retry twice, explicit retry preserves successful tiles", async () => {
  const { capability } = await acquireTestAuth();
  vi.useFakeTimers();
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(() =>
      Promise.resolve(new Response(null, { status: 503 })),
    );
  const report = vi.fn(),
    done = vi.fn();
  const layer = new EvidenceTiles(() => "/tile", report, capability);
  const image = layer.createTile(coords, done);
  await vi.runAllTimersAsync();
  expect(fetch).toHaveBeenCalledTimes(3);
  expect(report).toHaveBeenLastCalledWith({
    failed: 1,
    missing: 0,
    pending: 0,
  });
  fetch.mockResolvedValue(new Response(null, { status: 204 }));
  layer.retryFailed();
  await vi.runAllTimersAsync();
  expect(fetch).toHaveBeenCalledTimes(4);
  expect(done.mock.calls.at(-1)?.[1]).toBe(image);
  expect(report).toHaveBeenLastCalledWith({
    failed: 0,
    missing: 0,
    pending: 0,
  });
  layer.retryFailed();
  expect(fetch).toHaveBeenCalledTimes(4);
  layer.cancel();
});
test("cache miss and authorization failure do not create retry storms", async () => {
  for (const status of [404, 409, 401, 429]) {
    const { capability, unmount } = await acquireTestAuth();
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status }));
    const done = vi.fn(),
      report = vi.fn();
    const layer = new EvidenceTiles(
      () => "/tile?local_only=true",
      report,
      capability,
    );
    layer.createTile(coords, done);
    await vi.waitFor(() => {
      expect(done).toHaveBeenCalled();
    });
    expect(fetch).toHaveBeenCalledTimes(1);
    layer.cancel();
    fetch.mockRestore();
    unmount();
  }
});
test("unloading cancels pending work and removes obsolete failure state", async () => {
  const { capability } = await acquireTestAuth();
  vi.useFakeTimers();
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(new Response(null, { status: 503 }));
  const report = vi.fn();
  const layer = new EvidenceTiles(() => "/tile", report, capability);
  const tile = layer.createTile(coords, vi.fn());
  await vi.advanceTimersByTimeAsync(0);
  layer.fire("tileunload", { tile });
  await vi.runAllTimersAsync();
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(report).toHaveBeenLastCalledWith({
    failed: 0,
    missing: 0,
    pending: 0,
  });
  layer.cancel();
});

test("current-epoch tile HTTP 401 notifies auth gate once, cancels sibling retries, and blocks subsequent fetches while locked", async () => {
  vi.useFakeTimers();
  let releaseInFlight!: (response: Response) => void;
  const siblingSignals: AbortSignal[] = [];
  let callCount = 0;

  const harness = await mountRealProvider(
    { user_id: "owner-1", login_name: "owner-1", display_name: "Owner 1" },
    (_url, init) => {
      callCount++;
      if (init?.signal) siblingSignals.push(init.signal);
      if (callCount === 1) {
        return Promise.resolve(new Response(null, { status: 503 }));
      }
      if (callCount === 2) {
        return new Promise<Response>((resolve) => {
          releaseInFlight = resolve;
        });
      }
      return Promise.resolve(new Response(null, { status: 401 }));
    },
  );
  const { capability } = harness.getAuth();
  const epoch1 = getProtectedAuthEpoch();

  const layer = new EvidenceTiles(
    (c) => `/tile/${String(c.z)}/${String(c.x)}/${String(c.y)}`,
    vi.fn(),
    capability,
  );
  // Tile 1 schedules a 503 retry timer; Tile 2 stays in flight; Tile 3 hits 401.
  layer.createTile({ x: 0, y: 0, z: 1 } as Coords, vi.fn());
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
  layer.createTile({ x: 1, y: 0, z: 1 } as Coords, vi.fn());
  const done401 = vi.fn();
  layer.createTile({ x: 2, y: 0, z: 1 } as Coords, done401);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });

  const lockedEpoch = getProtectedAuthEpoch();
  expect(lockedEpoch).toBeGreaterThan(epoch1);
  expect(isProtectedRequestAuthorized()).toBe(false);
  expect(isReauthenticationState(harness.getAuth().state)).toBe(true);
  expect(done401).toHaveBeenCalledTimes(1);
  expect(done401.mock.calls[0]?.[0]).toBeInstanceOf(Error);
  expect(siblingSignals[1]?.aborted).toBe(true);

  // Even if sibling resolves with 401, duplicate notification never advances epoch again.
  releaseInFlight(new Response(null, { status: 401 }));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(5000);
  });
  expect(getProtectedAuthEpoch()).toBe(lockedEpoch);
  expect(callCount).toBe(3);

  // Explicit retry or new tile creation while locked emits zero network requests.
  layer.retryFailed();
  layer.createTile({ x: 3, y: 0, z: 1 } as Coords, vi.fn());
  expect(callCount).toBe(3);

  layer.cancel();
  harness.unmount();
});

test("stale-epoch tile 401 and aborted tile 401 never notify auth gate", async () => {
  let resolveEpoch1Tile!: (response: Response) => void;
  let resolveAbortedTile!: (response: Response) => void;
  let tileCalls = 0;

  const harness = await mountRealProvider(
    { user_id: "owner-1", login_name: "owner-1", display_name: "Owner 1" },
    () => {
      tileCalls += 1;
      if (tileCalls === 1) {
        return new Promise<Response>((resolve) => {
          resolveEpoch1Tile = resolve;
        });
      }
      return new Promise<Response>((resolve) => {
        resolveAbortedTile = resolve;
      });
    },
  );
  const { capability } = harness.getAuth();

  const layer = new EvidenceTiles(() => "/tile", vi.fn(), capability);
  layer.createTile({ x: 0, y: 0, z: 1 } as Coords, vi.fn());
  const unloadedTile = layer.createTile(
    { x: 1, y: 0, z: 1 } as Coords,
    vi.fn(),
  );
  layer.fire("tileunload", { tile: unloadedTile });

  // Advance to epoch 2 (lock + same-owner reauthenticate) while epoch 1 tile is in flight.
  act(() => {
    harness.getAuth().sessionExpired();
  });
  await act(async () => {
    await harness.getAuth().reauthenticate?.({
      login_name: "owner-1",
      password: "pw",
    });
  });
  const recoveredEpoch = getProtectedAuthEpoch();
  expect(harness.getAuth().state.status).toBe("authenticated");

  resolveEpoch1Tile(new Response(null, { status: 401 }));
  resolveAbortedTile(new Response(null, { status: 401 }));
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });

  expect(harness.getAuth().state.status).toBe("authenticated");
  expect(getProtectedAuthEpoch()).toBe(recoveredEpoch);

  layer.cancel();
  harness.unmount();
});

test("owner-bound capability resumes same-owner attached layers on unlock but permanently blocks former-owner fetches on owner switch", async () => {
  vi.useFakeTimers();
  const requestedUrls: string[] = [];
  const harness = await mountRealProvider(
    {
      user_id: "owner-alice",
      login_name: "alice",
      display_name: "Alice",
    },
    (url) => {
      requestedUrls.push(url);
      if (url.includes("/alice-503")) {
        return Promise.resolve(new Response(null, { status: 503 }));
      }
      if (url.includes("/alice-401")) {
        return Promise.resolve(new Response(null, { status: 401 }));
      }
      return Promise.resolve(new Response(null, { status: 204 }));
    },
  );
  const aliceCapability = harness.getAuth().capability;

  const aliceLayer = new EvidenceTiles(
    (c) =>
      `/alice-${c.x === 0 ? "503" : c.x === 1 ? "401" : "ok"}/${String(c.z)}`,
    vi.fn(),
    aliceCapability,
  );
  // Simulate attached Leaflet layer whose onRemove() has NOT run yet across owner switch.
  (aliceLayer as unknown as { attached: boolean }).attached = true;
  const aliceRedraw = vi.spyOn(aliceLayer, "redraw").mockImplementation(() => {
    aliceLayer.createTile({ x: 2, y: 0, z: 2 } as Coords, vi.fn());
    return aliceLayer;
  });

  // Queue a 503 retry timer then trigger a tile 401.
  aliceLayer.createTile({ x: 0, y: 0, z: 1 } as Coords, vi.fn());
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
  aliceLayer.createTile({ x: 1, y: 0, z: 1 } as Coords, vi.fn());
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
  expect(isReauthenticationState(harness.getAuth().state)).toBe(true);

  // Same-owner recovery unlocks Alice's workspace generation -> automatically redraws.
  await act(async () => {
    await harness.getAuth().reauthenticate?.({
      login_name: "alice",
      password: "pw",
    });
  });
  expect(aliceRedraw).toHaveBeenCalledTimes(1);
  expect(requestedUrls).toEqual([
    "/alice-503/1",
    "/alice-401/1",
    "/alice-ok/2",
  ]);

  // Expire Alice again cleanly while a 503 timer is pending.
  aliceLayer.createTile({ x: 0, y: 0, z: 3 } as Coords, vi.fn());
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
  aliceLayer.createTile({ x: 1, y: 0, z: 3 } as Coords, vi.fn());
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
  const callsBeforeOwnerSwitch = requestedUrls.length;
  aliceRedraw.mockClear();

  // Different-owner authentication barrier fires BEFORE Alice's layer is unmounted, then unlocks Bob.
  await act(async () => {
    await harness.getAuth().reauthenticate?.({
      login_name: "bob",
      password: "pw",
    });
  });
  const bobCapability = harness.getAuth().capability;

  // Even before React commits unmount or if timers/retryFailed/createTile fire on Alice's layer:
  await act(async () => {
    await vi.advanceTimersByTimeAsync(10000);
  });
  aliceLayer.retryFailed();
  aliceLayer.createTile({ x: 2, y: 0, z: 4 } as Coords, vi.fn());
  expect(aliceRedraw).not.toHaveBeenCalled();
  expect(requestedUrls).toHaveLength(callsBeforeOwnerSwitch);

  // Bob's newly mounted layer succeeds normally.
  const bobLayer = new EvidenceTiles(
    (c) => `/bob-ok/${String(c.z)}/${String(c.x)}/${String(c.y)}`,
    vi.fn(),
    bobCapability,
  );
  bobLayer.createTile({ x: 0, y: 0, z: 1 } as Coords, vi.fn());
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
  expect(requestedUrls.slice(callsBeforeOwnerSwitch)).toEqual([
    "/bob-ok/1/0/0",
  ]);

  aliceLayer.cancel();
  bobLayer.cancel();
  harness.unmount();
});
