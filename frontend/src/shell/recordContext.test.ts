import { expect, test } from "vitest";

import { recordContext } from "./recordContext";

const id = "0190d2a8-0000-7000-8000-000000000001";

test("plant details offer the Journal entry form, lineage and label", () => {
  const context = recordContext(`#/plants/${id}?tab=overview`);
  expect(context?.noun).toBe("Plant");
  expect(context?.actions.map(({ label, href }) => [label, href])).toEqual([
    ["Add Journal entry", `#/plants/${id}?tab=events&entry=new`],
    ["Open recorded lineage", `#/plants/${id}?tab=lineage`],
    ["Print label", `#/labels?kind=plant&record=${id}`],
  ]);
});

test("sowings offer the germination form; seed lots their lineage and label", () => {
  expect(recordContext(`#/sowings/${id}`)?.actions[0]).toMatchObject({
    label: "Add germination observation",
    href: `#/sowings/${id}?tab=germination&entry=new`,
  });
  expect(
    recordContext(`#/seeds/${id}`)?.actions.map(({ label }) => label),
  ).toEqual(["Open recorded lineage", "Print label"]);
  expect(recordContext(`#/plant-groups/${id}`)?.noun).toBe("Plant group");
});

test("directories, other records and malformed ids have no record context", () => {
  for (const hash of [
    "#/plants",
    "#/dashboard",
    `#/harvests/${id}`,
    "#/plants/x",
  ])
    expect(recordContext(hash)).toBeNull();
});
