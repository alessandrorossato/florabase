import { expect, test } from "vitest";

import type { Conversion } from "./conversionApi";
import { countedConversions, uniqueConversions } from "./harvestConversions";

function conversion(id: string, lot: string, status: Conversion["status"]) {
  return { id, seed_lot_id: lot, status } as Conversion;
}

test("UI-POLISH-006: reversed Seed lot conversions are listed but not counted as descendants", () => {
  const rows = [
    conversion("a", "lot-1", "reversed"),
    conversion("b", "lot-1", "applied"),
    conversion("c", "lot-2", "reversed"),
    conversion("d", "lot-3", "applied"),
    conversion("e", "lot-3", "applied"),
  ];
  // A live conversion wins over a reversed one for the same lot, whatever the order.
  expect(uniqueConversions(rows).map(({ id }) => id)).toEqual(["b", "c", "d"]);
  expect(
    countedConversions(rows).map(({ seed_lot_id }) => seed_lot_id),
  ).toEqual(["lot-1", "lot-3"]);
});
