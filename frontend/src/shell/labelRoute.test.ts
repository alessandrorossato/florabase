import { expect, test } from "vitest";

import { labelRoute } from "./labelRoute";

const id = "0190d2a8-0000-7000-8000-000000000001";
const other = "0190d2a8-0000-7000-8000-000000000002";

// A full username-and-password URL, built rather than written as a literal.
const withCredentials = new URL(`https://florabase.example/#/plants/${id}`);
withCredentials.username = "user";
withCredentials.password = "pw";

test("the credential case carries both a username and a password", () => {
  expect(withCredentials.username).toBe("user");
  expect(withCredentials.password).toBe("pw");
  const parsed = new URL(withCredentials.href);
  expect(parsed.username).toBe("user");
  expect(parsed.password).toBe("pw");
  expect(parsed.hash).toBe(`#/plants/${id}`);
});

test.each([
  [`https://florabase.example/#/seeds/${id}`, `#/seeds/${id}`],
  [`http://florabase.test:8080/#/plants/${id}`, `#/plants/${id}`],
  [`https://florabase.example/#/plant-groups/${id}`, `#/plant-groups/${id}`],
  [
    `https://florabase.example/#/harvests/${id}?inventory=${other}`,
    `#/harvests/${id}?inventory=${other}`,
  ],
  [`  #/plants/${id}  `, `#/plants/${id}`],
])("accepts the label shape %s", (value, route) => {
  expect(labelRoute(value)).toBe(route);
});

test.each([
  "",
  "hello",
  `javascript:alert(1)//#/plants/${id}`,
  withCredentials.href,
  `https://florabase.example/app/#/plants/${id}`,
  `https://florabase.example/?next=x#/plants/${id}`,
  `https://florabase.example/#/plants/${id}?action=edit`,
  `https://florabase.example/#/plants?action=create`,
  `https://florabase.example/#/sowings/${id}`,
  `https://florabase.example/#/plants/not-a-uuid`,
  `ftp://florabase.example/#/plants/${id}`,
])("refuses anything a label does not encode: %s", (value) => {
  expect(labelRoute(value)).toBeNull();
});
