import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import { afterEach, expect, test, vi } from "vitest";

const source = readFileSync("public/appearance.js", "utf8");
const key = "florabase.appearance.v1";
function bootstrap(raw: string | null, dark = false) {
  window.florabaseAppearance.dispose();
  if (raw === null) localStorage.removeItem(key);
  else localStorage.setItem(key, raw);
  const media = new EventTarget();
  const query = Object.assign(media, {
    matches: dark,
    media: "(prefers-color-scheme: dark)",
  });
  vi.spyOn(window, "matchMedia").mockReturnValue(query as MediaQueryList);
  runInNewContext(source, { window, document });
  return query;
}
afterEach(() => {
  vi.restoreAllMocks();
});

test("blocking bootstrap resolves saved dark before React and survives a fresh reload", () => {
  bootstrap(
    JSON.stringify({ version: 1, palette: "mineral", appearance: "dark" }),
  );
  expect(document.documentElement.dataset).toMatchObject({
    palette: "mineral",
    appearance: "dark",
  });
  expect(document.documentElement.style.colorScheme).toBe("dark");
  bootstrap(localStorage.getItem(key));
  expect(window.florabaseAppearance.getSnapshot()).toMatchObject({
    palette: "mineral",
    appearance: "dark",
    effectiveAppearance: "dark",
  });
});

test.each([
  null,
  "{broken",
  "null",
  "[]",
  '{"version":2,"palette":"mineral","appearance":"dark"}',
])("default for missing/corrupt/unknown version: %s", (raw) => {
  bootstrap(raw, true);
  expect(window.florabaseAppearance.getSnapshot()).toMatchObject({
    palette: "botanical",
    appearance: "system",
    effectiveAppearance: "dark",
  });
});

test("invalid fields fall back independently; unknown values never enter root attributes", () => {
  bootstrap(
    JSON.stringify({ version: 1, palette: "mineral", appearance: "invalid" }),
  );
  expect(window.florabaseAppearance.getSnapshot()).toMatchObject({
    palette: "mineral",
    appearance: "system",
  });
  bootstrap(
    JSON.stringify({ version: 1, palette: "invalid", appearance: "light" }),
  );
  expect(window.florabaseAppearance.getSnapshot()).toMatchObject({
    palette: "botanical",
    appearance: "light",
  });
});

test("System follows live OS changes; explicit appearance ignores them and re-entering System resolves current OS", () => {
  const media = bootstrap(null);
  media.matches = true;
  media.dispatchEvent(new Event("change"));
  expect(document.documentElement.dataset.appearance).toBe("dark");
  window.florabaseAppearance.setAppearance("light");
  media.dispatchEvent(new Event("change"));
  expect(document.documentElement.dataset.appearance).toBe("light");
  window.florabaseAppearance.setAppearance("system");
  expect(document.documentElement.dataset.appearance).toBe("dark");
});

test("cross-tab changes and clear synchronize without storage echo; unrelated/session storage is ignored", () => {
  bootstrap(null);
  const write = vi.spyOn(Storage.prototype, "setItem");
  const send = (
    keyValue: string | null,
    newValue: string | null,
    storageArea: Storage = localStorage,
  ) =>
    window.dispatchEvent(
      new StorageEvent("storage", { key: keyValue, newValue, storageArea }),
    );
  send(
    key,
    JSON.stringify({ version: 1, palette: "herbarium", appearance: "dark" }),
  );
  expect(window.florabaseAppearance.getSnapshot()).toMatchObject({
    palette: "herbarium",
    effectiveAppearance: "dark",
  });
  send("sidebar", "bad");
  send(key, JSON.stringify({ version: 1, palette: "mineral" }), sessionStorage);
  expect(window.florabaseAppearance.getSnapshot().palette).toBe("herbarium");
  send(key, "corrupt");
  expect(window.florabaseAppearance.getSnapshot().palette).toBe("botanical");
  send(null, null);
  expect(window.florabaseAppearance.getSnapshot().appearance).toBe("system");
  expect(write).not.toHaveBeenCalled();
});

test("storage denial and quota failure retain a working temporary theme", () => {
  window.florabaseAppearance.dispose();
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw new DOMException("Denied", "SecurityError");
  });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new DOMException("Full", "QuotaExceededError");
  });
  runInNewContext(source, { window, document });
  window.florabaseAppearance.setPalette("mineral");
  window.florabaseAppearance.setAppearance("dark");
  expect(window.florabaseAppearance.getSnapshot()).toMatchObject({
    palette: "mineral",
    effectiveAppearance: "dark",
    persistent: false,
  });
});

test("subscriber lifecycle is bounded and a no-op OS event preserves snapshot identity", () => {
  const media = bootstrap(null);
  const store = window.florabaseAppearance;
  const notify = vi.fn();
  const unsubscribe = store.subscribe(notify);
  const before = store.getSnapshot();
  media.dispatchEvent(new Event("change"));
  expect(store.getSnapshot()).toBe(before);
  expect(notify).not.toHaveBeenCalled();
  store.setAppearance("dark");
  expect(notify).toHaveBeenCalledTimes(1);
  unsubscribe();
  store.setAppearance("light");
  expect(notify).toHaveBeenCalledTimes(1);
});
