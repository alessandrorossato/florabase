import { afterEach, beforeEach, expect, test } from "vitest";
import { browserBack } from "../test/history";
import {
  closeCollectionPage,
  collectionPageParent,
  openCollectionPage,
} from "./recordNavigation";

beforeEach(() => {
  window.history.replaceState(null, "", "#/dashboard");
});
afterEach(() => {
  window.history.replaceState(null, "", "#/dashboard");
});

test.each([
  ["#/seeds?action=create", "#/seeds"],
  ["#/sowings?action=create", "#/sowings"],
  ["#/plants?action=create&kind=plant", "#/plants"],
  ["#/plants?action=create&kind=group", "#/plants"],
  ["#/plants?action=extract&source=group", "#/plant-groups/group"],
  ["#/sowings?action=start&seedLot=lot", "#/seeds/lot"],
  ["#/plants?action=from-sowing&sowing=tray&kind=plant", "#/sowings/tray"],
])(
  "%s establishes its canonical parent and preserves earlier history",
  async (route, parent) => {
    expect(collectionPageParent(route)).toBe(parent);
    openCollectionPage(route);
    expect(window.location.hash).toBe(route);
    await browserBack();
    expect(window.location.hash).toBe(parent);
    await browserBack();
    expect(window.location.hash).toBe("#/dashboard");
  },
);

test("direct create Cancel has a category fallback without consuming external history", () => {
  window.history.replaceState(null, "", "#/plants?action=create&kind=group");
  closeCollectionPage("#/plants");
  expect(window.location.hash).toBe("#/plants");
});

test("Details, Edit and unrelated routes do not acquire a create parent", () => {
  for (const route of [
    "#/plants/specimen",
    "#/sowings/tray?tab=edit",
    "#/seeds/lot?action=edit",
    "#/events",
    "#/settings",
  ])
    expect(collectionPageParent(route)).toBeNull();
});

test.each([
  [
    "#/sowings/tray?tab=lineage",
    "#/plants?action=from-sowing&sowing=tray&kind=plant",
  ],
  [
    "#/sowings/tray?tab=events",
    "#/plants?action=from-sowing&sowing=tray&kind=group",
  ],
])(
  "source operation preserves the exact Details parent %s for Back and Cancel",
  async (parent, route) => {
    window.history.replaceState(null, "", parent);
    openCollectionPage(route);
    await browserBack();
    expect(window.location.hash).toBe(parent);
    openCollectionPage(route);
    const traversal = new Promise<void>((resolve) => {
      window.addEventListener(
        "popstate",
        () => {
          resolve();
        },
        { once: true },
      );
    });
    closeCollectionPage("#/sowings/tray");
    await traversal;
    expect(window.location.hash).toBe(parent);
  },
);
