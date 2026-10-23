/* global window, document */
// Blocking, same-origin bootstrap and the single browser-local preference store.
// Loaded before app styles/React; intentionally independent of authentication.
(function () {
  const key = "florabase.appearance.v1";
  const palettes = ["botanical", "herbarium", "mineral"];
  const appearances = ["system", "light", "dark"];
  const listeners = new Set();
  const media = window.matchMedia?.("(prefers-color-scheme: dark)");
  function parse(raw) {
    try {
      const value = JSON.parse(raw);
      if (!value || value.version !== 1) return defaults();
      return {
        palette: palettes.includes(value.palette) ? value.palette : "botanical",
        appearance: appearances.includes(value.appearance)
          ? value.appearance
          : "system",
      };
    } catch {
      return defaults();
    }
  }
  function defaults() {
    return { palette: "botanical", appearance: "system" };
  }
  let persistent = true;
  let preferences;
  try {
    preferences = parse(window.localStorage.getItem(key));
  } catch {
    preferences = defaults();
    persistent = false;
  }
  let snapshot;
  let watchingSystem = false;
  function update() {
    const effectiveAppearance =
      preferences.appearance === "system"
        ? media?.matches
          ? "dark"
          : "light"
        : preferences.appearance;
    const next = { ...preferences, effectiveAppearance, persistent };
    if (
      snapshot &&
      Object.keys(next).every((field) => next[field] === snapshot[field])
    )
      return;
    snapshot = next;
    const root = document.documentElement;
    root.dataset.palette = preferences.palette;
    root.dataset.appearance = effectiveAppearance;
    root.style.colorScheme = effectiveAppearance;
    const shouldWatch = preferences.appearance === "system";
    if (shouldWatch !== watchingSystem) {
      if (shouldWatch) media?.addEventListener("change", update);
      else media?.removeEventListener("change", update);
      watchingSystem = shouldWatch;
    }
    updateBrowserChrome();
    listeners.forEach((listener) => listener());
  }
  function updateBrowserChrome() {
    // At first paint CSS may not be loaded yet. DOMContentLoaded repeats this read.
    const color = window
      .getComputedStyle(document.documentElement)
      .getPropertyValue("--background")
      .trim();
    if (color)
      document
        .querySelector('meta[name="theme-color"]')
        ?.setAttribute("content", color);
  }
  function set(patch) {
    preferences = parse(
      JSON.stringify({ version: 1, ...preferences, ...patch }),
    );
    try {
      window.localStorage.setItem(
        key,
        JSON.stringify({ version: 1, ...preferences }),
      );
      persistent = true;
    } catch {
      persistent = false;
    }
    update();
  }
  function storage(event) {
    if (event.key !== key && event.key !== null) return;
    // Ignore a sessionStorage event with the same key; access itself can be denied.
    try {
      if (event.storageArea && event.storageArea !== window.localStorage)
        return;
    } catch {
      return;
    }
    preferences = parse(event.newValue);
    update();
  }
  window.addEventListener("storage", storage);
  document.addEventListener("DOMContentLoaded", updateBrowserChrome, {
    once: true,
  });
  update();
  window.florabaseAppearance = {
    getSnapshot: () => snapshot,
    subscribe: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    setPalette: (palette) => set({ palette }),
    setAppearance: (appearance) => set({ appearance }),
    cycleAppearance: () =>
      set({
        appearance:
          appearances[(appearances.indexOf(preferences.appearance) + 1) % 3],
      }),
    // Also permits isolated bootstrap tests without leaking global listeners.
    dispose: () => {
      window.removeEventListener("storage", storage);
      media?.removeEventListener("change", update);
      document.removeEventListener("DOMContentLoaded", updateBrowserChrome);
      listeners.clear();
    },
  };
})();
