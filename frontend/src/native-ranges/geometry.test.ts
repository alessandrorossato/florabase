import { expect, test } from "vitest";
import geometry from "./data/world-110m.json";
import type { RangePlace, Territory } from "./api";
import { mapCoverage, rangeGeometry } from "./geometry";

const place = (code: string, type = "iso_3166_1_alpha_2"): RangePlace => ({
  id: code,
  name: "Never match by name",
  display_path: "Arbitrary label",
  place_kind: "canonical",
  source_code: code,
  source_code_type: type,
});

test("pinned public domain geometry uses ISO codes and canonical M49 descendants", () => {
  expect(geometry.source).toBe("Natural Earth");
  expect(geometry.version).toBe("5.1.1");
  expect(geometry.release).toBe("v5.1.2");
  expect(geometry.license).toBe("Public domain");
  expect(geometry.source_sha256).toBe(
    "718ac51d68ed2bf5de4f563fff2e2e045db706c1d3222805f3e317140a64213b",
  );
  expect(rangeGeometry(place("IT"), geometry).codes).toEqual(["IT"]);
  const southAmerica = rangeGeometry(place("005", "un_m49"), geometry);
  expect(southAmerica.codes).toContain("BR");
  expect(southAmerica.codes).toContain("AR");
  expect(southAmerica.codes).toContain("GF");
  expect(southAmerica.codes).not.toContain("FR");
  expect(rangeGeometry(place("001", "un_m49"), geometry).codes).toContain("AQ");
  expect(southAmerica.missing.length).toBeGreaterThan(0);
});

test("custom, CLDR-only and unknown codes never borrow ancestor or name geometry", () => {
  expect(
    rangeGeometry(
      { ...place("IT"), place_kind: "custom", name: "Italy" },
      geometry,
    ).codes,
  ).toEqual([]);
  expect(
    rangeGeometry({ ...place("unknown"), name: "Italy" }, geometry).codes,
  ).toEqual([]);
  expect(rangeGeometry(place("XK", "cldr_territory"), geometry).codes).toEqual(
    [],
  );
  expect(rangeGeometry(place("QO", "cldr_territory"), geometry).codes).toEqual(
    [],
  );
  expect(rangeGeometry(place("XX"), geometry).missing).toEqual(["XX"]);
  expect(rangeGeometry(place("999", "un_m49"), geometry).codes).toEqual([]);
});

test("disjoint exact countries remain disjoint and unavailable territories remain listed", () => {
  const units: Territory[] = ["IT", "TH", "XX"].map((code) => ({
    id: code,
    name: code,
    source_code: code,
    identity_count: 3,
  }));
  const mapped = mapCoverage(units, geometry);
  expect(mapped.available.map((v) => v.source_code)).toEqual(["IT", "TH"]);
  expect(mapped.unavailable.map((v) => v.source_code)).toEqual(["XX"]);
  expect(mapped.available[0].identity_count).toBe(3);
});
