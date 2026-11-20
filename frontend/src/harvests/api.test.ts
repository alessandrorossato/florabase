import { afterEach, expect, it, vi } from "vitest";
import { acquireTestAuth } from "../test/auth";
import { listHarvests } from "./api";

afterEach(() => vi.restoreAllMocks());
it("uses the existing exact identity query and leaves the All request unfiltered", async () => {
  const { capability } = await acquireTestAuth();
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(() =>
      Promise.resolve(
        new Response("[]", { headers: { "Content-Type": "application/json" } }),
      ),
    );
  const controller = new AbortController();
  const signal = controller.signal;
  await listHarvests(capability, signal, "identity / exact");
  expect(fetch).toHaveBeenLastCalledWith(
    "/api/v1/harvests?botanical_identity_id=identity+%2F+exact",
    expect.objectContaining({
      credentials: "same-origin",
      signal: expect.any(AbortSignal) as AbortSignal,
    }),
  );
  await listHarvests(capability, signal, "");
  expect(fetch).toHaveBeenLastCalledWith(
    "/api/v1/harvests",
    expect.objectContaining({
      credentials: "same-origin",
      signal: expect.any(AbortSignal) as AbortSignal,
    }),
  );
  let rejectInFlight!: (reason?: unknown) => void;
  fetch.mockImplementationOnce(
    (_url, init) =>
      new Promise<Response>((_resolve, reject) => {
        rejectInFlight = reject;
        init?.signal?.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        });
      }),
  );
  const abortedCall = listHarvests(capability, signal, "").catch(
    () => undefined,
  );
  await Promise.resolve();
  expect(
    (fetch.mock.calls.at(-1)?.[1]?.signal as AbortSignal | undefined)?.aborted,
  ).toBe(false);
  controller.abort();
  await abortedCall;
  rejectInFlight(new DOMException("Aborted", "AbortError"));
  expect(
    (fetch.mock.calls.at(-1)?.[1]?.signal as AbortSignal | undefined)?.aborted,
  ).toBe(true);
});
