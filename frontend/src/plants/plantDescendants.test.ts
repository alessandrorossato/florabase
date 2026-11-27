import { expect, test } from "vitest";

import { harvestsHref } from "./plantDescendants";

test("UI-POLISH-006: a Plant without harvests does not link to the species' harvest list", () => {
  expect(harvestsHref({ harvests: 0, singleHarvestId: null }, "id")).toBe(
    undefined,
  );
  expect(harvestsHref({ harvests: 1, singleHarvestId: "h1" }, "id")).toBe(
    "#/harvests/h1",
  );
  expect(harvestsHref({ harvests: 3, singleHarvestId: null }, "id")).toBe(
    "#/identities/id?tab=harvests",
  );
});
