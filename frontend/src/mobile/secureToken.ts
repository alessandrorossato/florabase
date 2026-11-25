/**
 * Typed bridge to the in-repo Android `SecureToken` Capacitor plugin.
 *
 * The Bearer device token is encrypted with a non-exportable AES-256-GCM key in
 * AndroidKeyStore and stored in app-private SharedPreferences. It is NEVER stored
 * in `localStorage`, `sessionStorage`, IndexedDB, or Capacitor `Preferences`.
 */

import { getCapacitorGlobal } from "./runtime";

export interface SecureTokenStore {
  get(): Promise<string | null>;
  set(token: string): Promise<void>;
  clear(): Promise<void>;
  getDeviceLabel(): Promise<string>;
}

const PLUGIN_NAME = "SecureToken";

async function invokeSecureToken<T>(
  method: string,
  options?: Record<string, unknown>,
): Promise<T> {
  const capacitor = getCapacitorGlobal();
  const plugin = (
    capacitor?.Plugins as
      | Record<
          string,
          Record<string, (opts?: Record<string, unknown>) => Promise<T>>
        >
      | undefined
  )?.[PLUGIN_NAME];
  if (typeof plugin?.[method] === "function") {
    return await plugin[method](options);
  }
  if (typeof capacitor?.nativePromise === "function") {
    return await capacitor.nativePromise<T>(PLUGIN_NAME, method, options);
  }
  throw new Error("SecureToken native plugin is unavailable.");
}

export function createSecureTokenStore(): SecureTokenStore {
  return {
    async get(): Promise<string | null> {
      try {
        const result = await invokeSecureToken<{ token?: string | null }>(
          "get",
        );
        return typeof result.token === "string" && result.token.trim() !== ""
          ? result.token
          : null;
      } catch {
        return null;
      }
    },
    async set(token: string): Promise<void> {
      await invokeSecureToken<unknown>("set", { token });
    },
    async clear(): Promise<void> {
      await invokeSecureToken<unknown>("clear");
    },
    async getDeviceLabel(): Promise<string> {
      try {
        const result = await invokeSecureToken<{ label?: string }>(
          "getDeviceLabel",
        );
        const label =
          typeof result.label === "string" ? result.label.trim() : "";
        return label.slice(0, 120) || "Android device";
      } catch {
        return "Android device";
      }
    },
  };
}
