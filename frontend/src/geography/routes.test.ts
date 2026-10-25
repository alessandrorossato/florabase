import { expect, test } from "vitest";
import { geographyRoute } from "./routes";
import { readDirectoryState, savedViewHash } from "../saved-views/state";

test.each([
  ["native-ranges", "native_ranges", "native-ranges"],
  ["species-distribution", "species_distribution", "species-distribution"],
  ["map", "provenance_map", "origins"],
] as const)(
  "legacy %s and Geography-local routes retain the same directory state",
  (legacy, surface, view) => {
    const query =
      "q=Ocimum&scope=current&mode=species&identity=01900000-0000-7000-8000-000000000001&identity=01900000-0000-7000-8000-000000000002&record=plant&withRange=true&plants=false&future=keep";
    expect(geographyRoute(`#/${legacy}?${query}`)).toEqual({ view });
    expect(geographyRoute(`#/geography/${view}?${query}`)).toEqual({ view });
    expect(readDirectoryState(surface, `#/geography/${view}?${query}`)).toEqual(
      readDirectoryState(surface, `#/${legacy}?${query}`),
    );
  },
);

test("Geography defaults to Overview while legacy record and management links remain exact", () => {
  expect(geographyRoute("#/geography")).toEqual({ view: "overview" });
  expect(geographyRoute("#/geography?q=Italy")).toEqual({ view: "places" });
  expect(geographyRoute("#/geography?place=exact-id")).toEqual({
    view: "places",
  });
  expect(geographyRoute("#/geography?mode=map&q=Italy")).toEqual({
    view: "sites",
  });
  expect(geographyRoute("#/geography/exact-site-id")).toEqual({
    view: "sites",
    siteId: "exact-site-id",
  });
  expect(geographyRoute("#/locations")).toBeNull();
  expect(geographyRoute("#/toString")).toBeNull();
});

test("canonical Places and sites derive their mode without changing Geography v1 Saved Views", () => {
  expect(readDirectoryState("geography", "#/geography/sites?q=Italy")).toEqual({
    q: "Italy",
    mode: "sites",
  });
  expect(readDirectoryState("geography", "#/geography/sites?mode=map")).toEqual(
    { q: "", mode: "map" },
  );
  expect(readDirectoryState("geography", "#/geography/places?q=Italy")).toEqual(
    { q: "Italy", mode: "places" },
  );
  expect(savedViewHash("geography", 1, { q: "Italy", mode: "map" })).toBe(
    "#/geography?q=Italy&mode=map",
  );
});
