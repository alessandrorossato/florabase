import { afterEach, expect, it, vi } from "vitest";
import { listHarvests } from "./api";

afterEach(() => vi.restoreAllMocks());
it("uses the existing exact identity query and leaves the All request unfiltered", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(() =>
      Promise.resolve(
        new Response("[]", { headers: { "Content-Type": "application/json" } }),
      ),
    );
  const signal = new AbortController().signal;
  await listHarvests(signal, "identity / exact");
  expect(fetch).toHaveBeenLastCalledWith(
    "/api/v1/harvests?botanical_identity_id=identity+%2F+exact",
    expect.objectContaining({ signal }),
  );
  await listHarvests(signal, "");
  expect(fetch).toHaveBeenLastCalledWith(
    "/api/v1/harvests",
    expect.objectContaining({ signal }),
  );
});
