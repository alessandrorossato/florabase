import { afterEach, expect, test } from "vitest";

import { trackInputModality } from "./focusModality";

let stop: (() => void) | undefined;
afterEach(() => {
  stop?.();
  delete document.documentElement.dataset.input;
});

test("records keyboard use, ignores bare modifiers, and resets on pointer use", () => {
  stop = trackInputModality();
  expect(document.documentElement.dataset.input).toBeUndefined();
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Shift" }));
  expect(document.documentElement.dataset.input).toBeUndefined();
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab" }));
  expect(document.documentElement.dataset.input).toBe("keyboard");
  document.dispatchEvent(new Event("pointerdown"));
  expect(document.documentElement.dataset.input).toBe("pointer");
});
