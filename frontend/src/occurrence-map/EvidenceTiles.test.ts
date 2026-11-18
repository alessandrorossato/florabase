import { afterEach, expect, test, vi } from "vitest";
import type { Coords } from "leaflet";
import {
  attachAuthRequestGate,
  getProtectedAuthEpoch,
  syncAuthRequestGate,
} from "../auth/api";
import { EvidenceTiles } from "./EvidenceTiles";
const coords = { x: 0, y: 0, z: 1 } as Coords;
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

test("empty HTTP 204 is successful and never reported as incomplete", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(new Response(null, { status: 204 }));
  const report = vi.fn(),
    done = vi.fn();
  const layer = new EvidenceTiles(() => "/local?local_only=true", report);
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
  vi.useFakeTimers();
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(() =>
      Promise.resolve(new Response(null, { status: 503 })),
    );
  const report = vi.fn(),
    done = vi.fn();
  const layer = new EvidenceTiles(() => "/tile", report);
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
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status }));
    const done = vi.fn(),
      report = vi.fn();
    const layer = new EvidenceTiles(() => "/tile?local_only=true", report);
    layer.createTile(coords, done);
    await vi.waitFor(() => {
      expect(done).toHaveBeenCalled();
    });
    expect(fetch).toHaveBeenCalledTimes(1);
    layer.cancel();
    fetch.mockRestore();
  }
});
test("unloading cancels pending work and removes obsolete failure state", async () => {
  vi.useFakeTimers();
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(new Response(null, { status: 503 }));
  const report = vi.fn();
  const layer = new EvidenceTiles(() => "/tile", report);
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
  const onUnauthorized = vi.fn(() => {
    syncAuthRequestGate({ locked: true, advanceEpoch: true });
  });
  const detach = attachAuthRequestGate(onUnauthorized, false);
  const epoch1 = getProtectedAuthEpoch();

  let releaseInFlight!: (response: Response) => void;
  const siblingSignals: AbortSignal[] = [];
  let callCount = 0;
  vi.spyOn(globalThis, "fetch").mockImplementation((_url, init) => {
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
  });

  const layer = new EvidenceTiles(
    (c) => `/tile/${String(c.z)}/${String(c.x)}/${String(c.y)}`,
    vi.fn(),
  );
  // Tile 1 schedules a 503 retry timer; Tile 2 stays in flight; Tile 3 hits 401.
  layer.createTile({ x: 0, y: 0, z: 1 } as Coords, vi.fn());
  await vi.advanceTimersByTimeAsync(0);
  layer.createTile({ x: 1, y: 0, z: 1 } as Coords, vi.fn());
  const done401 = vi.fn();
  layer.createTile({ x: 2, y: 0, z: 1 } as Coords, done401);
  await vi.advanceTimersByTimeAsync(0);

  expect(onUnauthorized).toHaveBeenCalledTimes(1);
  expect(onUnauthorized).toHaveBeenCalledWith(epoch1);
  expect(done401).toHaveBeenCalledTimes(1);
  expect(done401.mock.calls[0]?.[0]).toBeInstanceOf(Error);
  expect(siblingSignals[1]?.aborted).toBe(true);

  // Even if sibling resolves with 401, duplicate notification never fires.
  releaseInFlight(new Response(null, { status: 401 }));
  await vi.advanceTimersByTimeAsync(5000);
  expect(onUnauthorized).toHaveBeenCalledTimes(1);
  expect(callCount).toBe(3);

  // Explicit retry or new tile creation while locked emits zero network requests.
  layer.retryFailed();
  layer.createTile({ x: 3, y: 0, z: 1 } as Coords, vi.fn());
  expect(callCount).toBe(3);

  layer.cancel();
  detach();
});

test("stale-epoch tile 401 and aborted tile 401 never notify auth gate", async () => {
  const onUnauthorized = vi.fn();
  const detach = attachAuthRequestGate(onUnauthorized, false);

  let resolveEpoch1Tile!: (response: Response) => void;
  let resolveAbortedTile!: (response: Response) => void;
  vi.spyOn(globalThis, "fetch")
    .mockImplementationOnce(
      () =>
        new Promise<Response>((resolve) => {
          resolveEpoch1Tile = resolve;
        }),
    )
    .mockImplementationOnce(
      () =>
        new Promise<Response>((resolve) => {
          resolveAbortedTile = resolve;
        }),
    );

  const layer = new EvidenceTiles(() => "/tile", vi.fn());
  layer.createTile({ x: 0, y: 0, z: 1 } as Coords, vi.fn());
  const unloadedTile = layer.createTile(
    { x: 1, y: 0, z: 1 } as Coords,
    vi.fn(),
  );
  layer.fire("tileunload", { tile: unloadedTile });

  // Advance to epoch 2 (e.g., after reauthentication) while epoch 1 tile is still in flight.
  syncAuthRequestGate({ locked: false, advanceEpoch: true });

  resolveEpoch1Tile(new Response(null, { status: 401 }));
  resolveAbortedTile(new Response(null, { status: 401 }));
  await Promise.resolve();
  await Promise.resolve();

  expect(onUnauthorized).not.toHaveBeenCalled();

  layer.cancel();
  detach();
});
