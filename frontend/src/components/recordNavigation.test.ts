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
  ["#/harvests?action=create", "#/harvests"],
  [
    "#/harvests?action=create&sourceType=plant&source=specimen",
    "#/plants/specimen",
  ],
  [
    "#/harvests?action=create&sourceType=plant_group&source=group",
    "#/plant-groups/group",
  ],
  ["#/seeds?action=create", "#/seeds"],
  ["#/sowings?action=create", "#/sowings"],
  ["#/plants?action=create&kind=plant", "#/plants"],
  ["#/plants?action=create&kind=group", "#/plants"],
  ["#/suppliers?action=create", "#/suppliers"],
  ["#/orders?action=create", "#/orders"],
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
    if (route.startsWith("#/harvests?action=create")) {
      expect(window.history.state as unknown).toMatchObject({
        collectionReturnFocus: parent === "#/harvests" ? "create" : "harvest",
      });
    }
    if (parent === "#/suppliers" || parent === "#/orders") {
      expect(window.history.state as unknown).toMatchObject({
        collectionReturnFocus: "create",
      });
    }
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
    "#/plants/specimen?tab=events",
    "#/harvests?action=create&sourceType=plant&source=specimen",
  ],
  [
    "#/plant-groups/group?tab=overview",
    "#/harvests?action=create&sourceType=plant_group&source=group",
  ],
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
