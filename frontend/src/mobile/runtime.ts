/**
 * Native-shell runtime detection without importing `@capacitor/core` into the web bundle.
 *
 * Capacitor Android injects `window.Capacitor` via `native-bridge.js` before module scripts run.
 * In web/PWA browsers `window.Capacitor` is absent, so `isNativeShell()` returns `false` and the
 * web entry path runs unchanged without downloading or evaluating native-only code.
 */

export interface CapacitorPreferencesBridge {
  get(options: { key: string }): Promise<{ value: string | null }>;
  set(options: { key: string; value: string }): Promise<void>;
  remove(options: { key: string }): Promise<void>;
}

export interface CapacitorHttpResponse {
  data: unknown;
  status: number;
  headers: Record<string, string>;
  url: string;
}

export interface CapacitorHttpBridge {
  get(options: {
    url: string;
    headers?: Record<string, string>;
    connectTimeout?: number;
    readTimeout?: number;
  }): Promise<CapacitorHttpResponse>;
}

export interface CapacitorGlobal {
  isNativePlatform?: () => boolean;
  getPlatform?: () => string;
  Plugins?: {
    Preferences?: CapacitorPreferencesBridge;
    CapacitorHttp?: CapacitorHttpBridge;
  };
  nativePromise?: <T = unknown>(
    pluginName: string,
    methodName: string,
    options?: Record<string, unknown>,
  ) => Promise<T>;
}

export function getCapacitorGlobal(
  target: typeof globalThis = globalThis,
): CapacitorGlobal | undefined {
  const candidate = (target as { Capacitor?: unknown }).Capacitor;
  if (typeof candidate !== "object" || candidate === null) {
    return undefined;
  }
  return candidate;
}

/**
 * Returns `true` only when running inside a Capacitor native container (Android/iOS).
 * Web and PWA contexts always return `false`.
 */
export function isNativeShell(target: typeof globalThis = globalThis): boolean {
  const capacitor = getCapacitorGlobal(target);
  try {
    return capacitor?.isNativePlatform?.() === true;
  } catch {
    return false;
  }
}

/**
 * Returns `true` only for debug mobile builds (`make mobile-android-debug`), which pass
 * `VITE_MOBILE_ALLOW_DEBUG_HTTP=true`. Standard web builds and release APKs always return `false`.
 */
export function isNativeDebugBuild(): boolean {
  return import.meta.env.VITE_MOBILE_ALLOW_DEBUG_HTTP === "true";
}
