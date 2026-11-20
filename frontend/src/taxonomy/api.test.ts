import { afterEach, expect, test, vi } from "vitest";
import { acquireTestAuth } from "../test/auth";
import { getTree } from "./api";

afterEach(() => {
  vi.restoreAllMocks();
});

test("both views request bounded protected thumbnail metadata through the existing endpoint", async () => {
  const { capability } = await acquireTestAuth();
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(() =>
      Promise.resolve(
        new Response("{}", { headers: { "Content-Type": "application/json" } }),
      ),
    );
  const controller = new AbortController();
  const signal = controller.signal;
  for (const view of [undefined, "tree"] as const)
    await getTree(
      { scope: "current", record: ["seed_lot"], q: " Basil ", taxon: "", view },
      capability,
      signal,
    );
  expect(fetch).toHaveBeenCalledTimes(2);
  for (const call of fetch.mock.calls) {
    const url = call[0];
    expect(url).toContain("/api/v1/explore/taxonomy/tree?");
    expect(url).toContain("include_covers=true");
    expect(url).toContain("q=Basil");
    expect(url).toContain("record=seed_lot");
    expect(call[1]).toMatchObject({
      credentials: "same-origin",
      signal: expect.any(AbortSignal) as AbortSignal,
    });
  }
  let abortableSignal: AbortSignal | undefined;
  fetch.mockImplementationOnce(
    (_url, init) =>
      new Promise<Response>((_resolve, reject) => {
        abortableSignal = init?.signal ?? undefined;
        init?.signal?.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        });
      }),
  );
  const abortedCall = getTree(
    {
      scope: "current",
      record: ["seed_lot"],
      q: " Basil ",
      taxon: "",
      view: "tree",
    },
    capability,
    signal,
  ).catch(() => undefined);
  await Promise.resolve();
  expect(abortableSignal?.aborted).toBe(false);
  controller.abort();
  await abortedCall;
  expect(abortableSignal?.aborted).toBe(true);
});
