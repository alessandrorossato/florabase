/**
 * Persists the non-secret Florabase server URL in Capacitor Preferences on native builds.
 * No credentials or tokens are stored here.
 */

import { getCapacitorGlobal, type CapacitorGlobal } from "./runtime";

export const SERVER_URL_PREFERENCE_KEY = "florabase.server_url";

export interface ServerUrlStore {
  load(): Promise<string | null>;
  save(url: string): Promise<void>;
  clear(): Promise<void>;
}

function createCapacitorPreferencesStore(
  capacitor: CapacitorGlobal,
): ServerUrlStore | null {
  const plugin = capacitor.Plugins?.Preferences;
  if (plugin !== undefined) {
    return {
      async load() {
        const result = await plugin.get({ key: SERVER_URL_PREFERENCE_KEY });
        return typeof result.value === "string" && result.value !== ""
          ? result.value
          : null;
      },
      async save(url: string) {
        await plugin.set({ key: SERVER_URL_PREFERENCE_KEY, value: url });
      },
      async clear() {
        await plugin.remove({ key: SERVER_URL_PREFERENCE_KEY });
      },
    };
  }

  const nativePromise = capacitor.nativePromise;
  if (typeof nativePromise === "function") {
    return {
      async load() {
        const result = await nativePromise<{ value?: string | null }>(
          "Preferences",
          "get",
          { key: SERVER_URL_PREFERENCE_KEY },
        );
        return typeof result.value === "string" && result.value !== ""
          ? result.value
          : null;
      },
      async save(url: string) {
        await nativePromise("Preferences", "set", {
          key: SERVER_URL_PREFERENCE_KEY,
          value: url,
        });
      },
      async clear() {
        await nativePromise("Preferences", "remove", {
          key: SERVER_URL_PREFERENCE_KEY,
        });
      },
    };
  }

  return null;
}

function createLocalStorageFallbackStore(): ServerUrlStore {
  return {
    load() {
      try {
        const value = window.localStorage.getItem(SERVER_URL_PREFERENCE_KEY);
        return Promise.resolve(value !== null && value !== "" ? value : null);
      } catch {
        return Promise.resolve(null);
      }
    },
    save(url: string) {
      try {
        window.localStorage.setItem(SERVER_URL_PREFERENCE_KEY, url);
      } catch {
        // Ignore storage quota or private-mode failures in fallback mode.
      }
      return Promise.resolve();
    },
    clear() {
      try {
        window.localStorage.removeItem(SERVER_URL_PREFERENCE_KEY);
      } catch {
        // Ignore storage failures in fallback mode.
      }
      return Promise.resolve();
    },
  };
}

export function createServerUrlStore(
  target: typeof globalThis = globalThis,
): ServerUrlStore {
  const capacitor = getCapacitorGlobal(target);
  if (capacitor !== undefined) {
    const nativeStore = createCapacitorPreferencesStore(capacitor);
    if (nativeStore !== null) {
      return nativeStore;
    }
  }
  return createLocalStorageFallbackStore();
}
