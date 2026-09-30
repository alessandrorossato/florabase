import { expect, test } from "vitest";
import { decimalToDms, dmsToDecimal } from "./coordinates";

test("DMS conversion handles hemispheres, fractions, zero and coordinate boundaries", () => {
  expect(
    dmsToDecimal(
      { degrees: "38", minutes: "10", seconds: "0", direction: "N" },
      "latitude",
    ).value,
  ).toBe(String(38 + 10 / 60));
  expect(
    dmsToDecimal(
      { degrees: "13", minutes: "21", seconds: "30.5", direction: "W" },
      "longitude",
    ).value,
  ).toBe(String(-(13 + 21 / 60 + 30.5 / 3600)));
  expect(
    dmsToDecimal(
      { degrees: "90", minutes: "0", seconds: "0", direction: "S" },
      "latitude",
    ).value,
  ).toBe("-90");
  expect(
    dmsToDecimal(
      { degrees: "180", minutes: "0", seconds: "0", direction: "E" },
      "longitude",
    ).value,
  ).toBe("180");
  expect(
    dmsToDecimal(
      { degrees: "", minutes: "", seconds: "", direction: "N" },
      "latitude",
    ).value,
  ).toBe("");
});

test.each([
  ["latitude", "91", "0", "0", "N"],
  ["longitude", "181", "0", "0", "E"],
  ["latitude", "90", "1", "0", "N"],
  ["longitude", "180", "0", "0.1", "W"],
  ["latitude", "1", "60", "0", "N"],
  ["latitude", "1", "-1", "0", "N"],
  ["latitude", "1", "1.5", "0", "N"],
  ["latitude", "1", "0", "60", "N"],
  ["latitude", "1", "0", "-0.1", "N"],
  ["latitude", "1.5", "0", "0", "N"],
  ["latitude", "", "1", "0", "N"],
  ["latitude", "1", "0", "NaN", "N"],
  ["latitude", "1", "0", "0", "E"],
] as const)(
  "rejects invalid %s DMS %s/%s/%s %s",
  (axis, degrees, minutes, seconds, direction) => {
    expect(
      dmsToDecimal({ degrees, minutes, seconds, direction }, axis).error,
    ).toBeTruthy();
  },
);

test("decimal-to-DMS round trips preserve ordinary decimal precision and carry at boundaries", () => {
  for (const axis of ["latitude", "longitude"] as const) {
    for (const value of [
      "38.166666666667",
      "-13.350123456789",
      "0",
      "-0.0000000001",
      "89.999999999999",
    ]) {
      const result = dmsToDecimal(decimalToDms(value, axis), axis);
      expect(result.error).toBeUndefined();
      expect(Number(result.value)).toBeCloseTo(Number(value), 11);
    }
  }
  expect(decimalToDms("180", "longitude")).toMatchObject({
    degrees: "180",
    minutes: "0",
    seconds: "0",
  });
});
