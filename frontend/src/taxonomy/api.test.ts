import { expect, test, vi } from "vitest";
import { requestJson } from "../auth/api";
import { getTree } from "./api";
vi.mock("../auth/api", () => ({ requestJson: vi.fn().mockResolvedValue({}) }));
test("both views request bounded protected thumbnail metadata through the existing endpoint", async () => {
  const signal = new AbortController().signal;
  for (const view of [undefined, "tree"] as const)
    await getTree(
      { scope: "current", record: ["seed_lot"], q: " Basil ", taxon: "", view },
      signal,
    );
  expect(requestJson).toHaveBeenCalledTimes(2);
  for (const call of vi.mocked(requestJson).mock.calls) {
    const url = call[0];
    expect(url).toContain("/api/v1/explore/taxonomy/tree?");
    expect(url).toContain("include_covers=true");
    expect(url).toContain("q=Basil");
    expect(url).toContain("record=seed_lot");
    expect(call[1]).toEqual({ signal });
  }
});
