import { expect, test } from "vitest";

import {
  descendantCounts,
  descendantSummaryLabel,
  type AncestryChildren,
} from "./useRecordedLineage";

function children(
  kinds: AncestryChildren["items"][number]["record"]["kind"][],
  total = kinds.length,
): AncestryChildren {
  return {
    total,
    offset: 0,
    limit: 25,
    items: kinds.map(
      (kind, index) =>
        ({
          record: { kind, id: String(index) },
        }) as AncestryChildren["items"][number],
    ),
  };
}

test("UI-POLISH-006: Overview and strip describe the same children with the same words", () => {
  const value = children(["seed_lot", "vegetative_lot", "vegetative_lot"]);
  expect(descendantCounts(value).map(({ label }) => label)).toEqual([
    "1 seed lot",
    "2 vegetative lots",
  ]);
  expect(descendantSummaryLabel(value)).toBe("1 seed lot, 2 vegetative lots");
  // A partial first page is summarised by its total, never by an undercount per kind.
  expect(descendantSummaryLabel(children(["sowing"], 30))).toBe(
    "30 recorded from this",
  );
  expect(descendantSummaryLabel(children([]))).toBeNull();
});
