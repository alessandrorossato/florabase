import { afterEach, expect, test, vi } from "vitest";
import type { Coords } from "leaflet";
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
