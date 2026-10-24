import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import "@testing-library/jest-dom/vitest";

import { beforeEach, vi } from "vitest";

const appearanceSource = readFileSync("public/appearance.js", "utf8");

const createMatchMedia = (query: string) => ({
  matches: false,
  media: query,
  onchange: null,
  addListener: vi.fn(),
  removeListener: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  dispatchEvent: vi.fn(),
});
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn(createMatchMedia),
});

Object.defineProperty(window, "scrollTo", { writable: true, value: vi.fn() });

// Execute the real blocking bootstrap for every component test, just as index.html does.
// Reset only this feature's storage key; existing sidebar and domain fixtures retain their contracts.
beforeEach(() => {
  const previous = (window as Partial<Window>).florabaseAppearance;
  previous?.dispose();
  // Tests may replace matchMedia with a partial mobile-query mock. Give each
  // bootstrap a fresh complete API before the test installs its own query behavior.
  window.matchMedia = vi.fn(createMatchMedia);
  window.localStorage.removeItem("florabase.appearance.v1");
  runInNewContext(appearanceSource, { window, document });
});

// jsdom has no layout scrolling; browsers use the native method for legacy section links.
Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
  configurable: true,
  writable: true,
  value: vi.fn(),
});
