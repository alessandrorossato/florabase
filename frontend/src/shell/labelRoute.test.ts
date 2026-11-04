import { expect, test } from "vitest";

import { labelRoute } from "./labelRoute";

const id = "0190d2a8-0000-7000-8000-000000000001";
const other = "0190d2a8-0000-7000-8000-000000000002";

test.each([
  [`https://florabase.example/#/seeds/${id}`, `#/seeds/${id}`],
  [`http://192.168.1.20:8080/#/plants/${id}`, `#/plants/${id}`],
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
  `https://user:pw@florabase.example/#/plants/${id}`,
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
