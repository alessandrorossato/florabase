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

export interface CapacitorFilesystemBridge {
  writeFile(options: {
    path: string;
    data: string;
    directory?: string;
    encoding?: string;
    recursive?: boolean;
  }): Promise<{ uri: string }>;
  getUri(options: {
    path: string;
    directory?: string;
  }): Promise<{ uri: string }>;
  deleteFile(options: { path: string; directory?: string }): Promise<void>;
  rmdir(options: {
    path: string;
    directory?: string;
    recursive?: boolean;
  }): Promise<void>;
}

export interface CapacitorShareBridge {
  canShare?: () => Promise<{ value: boolean }>;
  share(options: {
    title?: string;
    text?: string;
    url?: string;
    files?: string[];
    dialogTitle?: string;
  }): Promise<{ activityType?: string } | undefined>;
}

export interface CapacitorWebPrintBridge {
  print(options?: { jobName?: string }): Promise<void>;
}

export interface CapacitorPluginListenerHandle {
  remove(): Promise<void>;
}

export interface CapacitorAppState {
  isActive: boolean;
}

export interface CapacitorAppBridge {
  addListener(
    eventName: "appStateChange",
    listenerFunc: (state: CapacitorAppState) => void,
  ): Promise<CapacitorPluginListenerHandle> | CapacitorPluginListenerHandle;
}

export type LocalNotificationPermissionState =
  "prompt" | "prompt-with-rationale" | "granted" | "denied";

export interface CapacitorLocalNotificationPayload {
  id: number;
  title: string;
  body: string;
  inboxList?: string[];
  channelId?: string;
  group?: string;
  autoCancel?: boolean;
  smallIcon?: string;
  iconColor?: string;
  isExactNotification?: boolean;
  schedule?: {
    at?: string | Date;
    allowWhileIdle?: boolean;
  };
  extra?: Record<string, unknown>;
}

export interface CapacitorLocalNotificationActionPerformed {
  actionId: string;
  notification?: {
    id?: number;
    extra?: unknown;
  };
}

export interface CapacitorLocalNotificationsBridge {
  checkPermissions(): Promise<{ display: LocalNotificationPermissionState }>;
  requestPermissions(): Promise<{ display: LocalNotificationPermissionState }>;
  createChannel(channel: {
    id: string;
    name: string;
    description?: string;
    importance?: number;
    visibility?: number;
    vibration?: boolean;
  }): Promise<void>;
  getPending(): Promise<{ notifications?: { id: number }[] }>;
  schedule(options: {
    notifications: CapacitorLocalNotificationPayload[];
  }): Promise<{ notifications: { id: number }[] }>;
  cancel(options: { notifications: { id: number }[] }): Promise<void>;
  getDeliveredNotifications(): Promise<{
    notifications?: { id: number; tag?: string }[];
  }>;
  removeDeliveredNotificationsById?(options: { ids: number[] }): Promise<void>;
  removeDeliveredNotifications?(options: {
    notifications: { id: number; tag?: string }[];
  }): Promise<void>;
  addListener(
    eventName: "localNotificationActionPerformed",
    listenerFunc: (action: CapacitorLocalNotificationActionPerformed) => void,
  ): Promise<CapacitorPluginListenerHandle> | CapacitorPluginListenerHandle;
}

export interface CapacitorGlobal {
  isNativePlatform?: () => boolean;
  getPlatform?: () => string;
  Plugins?: {
    App?: CapacitorAppBridge;
    Preferences?: CapacitorPreferencesBridge;
    CapacitorHttp?: CapacitorHttpBridge;
    Filesystem?: CapacitorFilesystemBridge;
    LocalNotifications?: CapacitorLocalNotificationsBridge;
    Share?: CapacitorShareBridge;
    WebPrint?: CapacitorWebPrintBridge;
  };
  nativePromise?: <T = unknown>(
    pluginName: string,
    methodName: string,
    options?: Record<string, unknown>,
  ) => Promise<T>;
  addListener?: (
    pluginName: string,
    eventName: string,
    callback: (event: unknown) => void,
  ) => CapacitorPluginListenerHandle;
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
