import { expect, test } from "vitest";
import { sortDirectory } from "./directorySort";

const rows = [
  { name: "beta", date: { precision: "year" as const, year: 2024 } },
  { name: "Alpha 10", date: null },
  {
    name: "alpha 9",
    date: { precision: "day" as const, year: 2024, month: 5, day: 2 },
  },
  {
    name: "Gamma",
    date: { precision: "month" as const, year: 2023, month: 12 },
  },
];
const names = (sort: Parameters<typeof sortDirectory>[1]) =>
  sortDirectory(
    rows,
    sort,
    (row) => row.name,
    (row) => row.date,
  ).map((row) => row.name);

test("default keeps the API order and never mutates the input", () => {
  expect(names("")).toEqual(["beta", "Alpha 10", "alpha 9", "Gamma"]);
  names("name");
  expect(rows[0].name).toBe("beta");
});

test("names compare case-insensitively with numeric parts", () => {
  expect(names("name")).toEqual(["alpha 9", "Alpha 10", "beta", "Gamma"]);
  expect(names("name_desc")).toEqual(["Gamma", "beta", "Alpha 10", "alpha 9"]);
});

test("partial dates order by known parts and undated records stay last", () => {
  expect(names("newest")).toEqual(["alpha 9", "beta", "Gamma", "Alpha 10"]);
  expect(names("oldest")).toEqual(["Gamma", "beta", "alpha 9", "Alpha 10"]);
});
