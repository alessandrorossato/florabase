/**
 * Runtime HTTP transport configuration shared by `AuthProvider` and `App`.
 *
 * Defaults to standard same-origin cookie + CSRF mode for the browser/PWA.
 * Only the lazily loaded Capacitor native shell calls `configureNativeBearerTransport`
 * to switch API calls to a remote server URL with `Authorization: Bearer <token>`
 * and `credentials: "omit"`, keeping `@capacitor/*` and native UI out of the web bundle.
 */

export interface NativeBearerTransportConfig {
  serverUrl: string;
  initialToken: string | null;
  saveToken: (token: string) => Promise<void>;
  clearToken: () => Promise<void>;
  getDefaultDeviceLabel: () => Promise<string>;
  onChangeServer?: () => void;
  onTrustLost?: () => Promise<void> | void;
}

interface TransportState {
  mode: "cookie" | "bearer";
  serverUrl: string;
  bearerToken: string | null;
  saveToken: ((token: string) => Promise<void>) | null;
  clearToken: (() => Promise<void>) | null;
  getDefaultDeviceLabel: (() => Promise<string>) | null;
  onChangeServer: (() => void) | null;
  onTrustLost: (() => Promise<void> | void) | null;
}

const state: TransportState = {
  mode: "cookie",
  serverUrl: "",
  bearerToken: null,
  saveToken: null,
  clearToken: null,
  getDefaultDeviceLabel: null,
  onChangeServer: null,
  onTrustLost: null,
};

export function configureNativeBearerTransport(
  config: NativeBearerTransportConfig,
): void {
  state.mode = "bearer";
  state.serverUrl = config.serverUrl.replace(/\/+$/, "");
  state.bearerToken = config.initialToken;
  state.saveToken = config.saveToken;
  state.clearToken = config.clearToken;
  state.getDefaultDeviceLabel = config.getDefaultDeviceLabel;
  state.onChangeServer = config.onChangeServer ?? null;
  state.onTrustLost = config.onTrustLost ?? null;
}

export function resetAuthTransport(): void {
  state.mode = "cookie";
  state.serverUrl = "";
  state.bearerToken = null;
  state.saveToken = null;
  state.clearToken = null;
  state.getDefaultDeviceLabel = null;
  state.onChangeServer = null;
  state.onTrustLost = null;
}

export function isNativeBearerTransport(): boolean {
  return state.mode === "bearer";
}

export function getConfiguredServerUrl(): string | null {
  return state.mode === "bearer" && state.serverUrl !== ""
    ? state.serverUrl
    : null;
}

export function hasNativeBearerToken(): boolean {
  return (
    state.mode === "bearer" &&
    state.bearerToken !== null &&
    state.bearerToken !== ""
  );
}

export async function persistNativeBearerToken(token: string): Promise<void> {
  if (state.mode !== "bearer" || state.saveToken === null) {
    return;
  }
  await state.saveToken(token);
  state.bearerToken = token;
}

export async function clearNativeBearerToken(): Promise<void> {
  state.bearerToken = null;
  if (state.mode === "bearer" && state.clearToken !== null) {
    try {
      await state.clearToken();
    } catch {
      // Best-effort clear; in-memory token is already wiped.
    }
  }
  if (state.mode === "bearer" && state.onTrustLost !== null) {
    try {
      await state.onTrustLost();
    } catch {
      // Best-effort local cleanup on loss of trust.
    }
  }
}

export async function loadDefaultDeviceLabel(): Promise<string> {
  if (state.mode !== "bearer" || state.getDefaultDeviceLabel === null) {
    return "";
  }
  try {
    return (await state.getDefaultDeviceLabel()).trim().slice(0, 120);
  } catch {
    return "Android device";
  }
}

export function canChangeServer(): boolean {
  return state.mode === "bearer" && state.onChangeServer !== null;
}

export function triggerChangeServer(): void {
  state.onChangeServer?.();
}

export function resolveApiUrl(path: string): string {
  if (state.mode !== "bearer" || state.serverUrl === "") {
    return path;
  }
  if (path.startsWith("/")) {
    return `${state.serverUrl}${path}`;
  }
  return path;
}

export function buildTransportFetchInit(
  init: RequestInit = {},
  { includeBearer = true }: { includeBearer?: boolean } = {},
): RequestInit {
  if (state.mode !== "bearer") {
    return {
      ...init,
      credentials: "same-origin",
    };
  }
  const headers = new Headers(init.headers);
  headers.delete("X-CSRF-Token");
  if (
    includeBearer &&
    state.bearerToken !== null &&
    state.bearerToken !== "" &&
    !headers.has("Authorization")
  ) {
    headers.set("Authorization", `Bearer ${state.bearerToken}`);
  }
  return {
    ...init,
    credentials: "omit",
    headers,
  };
}
