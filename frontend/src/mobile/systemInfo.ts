/**
 * Fetches and validates the unauthenticated server compatibility contract
 * (`GET /api/v1/system/info`) before allowing mobile device sign-in.
 */

import {
  probeFlorabaseHealth,
  type HealthProbeErrorKind,
  type HttpGetFn,
} from "./healthProbe";
import { isVersionAtLeast, parseSemver } from "./semver";

export const SUPPORTED_API_VERSION = 1;
export const REQUIRED_CAPABILITY = "device-auth";

export interface SystemInfo {
  serverVersion: string;
  apiVersion: number;
  minClientVersion: string;
  capabilities: readonly string[];
}

export type ServerCompatibilityErrorKind =
  HealthProbeErrorKind | "incompatible-server" | "incompatible-client";

export interface OnboardingError {
  category: "invalid-url" | ServerCompatibilityErrorKind;
  heading: string;
  message: string;
}

export function onboardingErrorHeading(
  category: OnboardingError["category"],
): string {
  switch (category) {
    case "invalid-url":
      return "Invalid server URL";
    case "tls":
      return "Certificate not trusted";
    case "cleartext":
      return "HTTPS required";
    case "unreachable":
      return "Server unreachable";
    case "http-error":
      return "Server error";
    case "non-florabase":
      return "Not a Florabase server";
    case "incompatible-server":
      return "Server update required";
    case "incompatible-client":
      return "App update required";
  }
}

export type ServerCompatibilityResult =
  | {
      ok: true;
      serverUrl: string;
      info: SystemInfo;
    }
  | {
      ok: false;
      kind: ServerCompatibilityErrorKind;
      message: string;
    };

function parseJsonOrValue(raw: unknown): unknown {
  if (typeof raw !== "string") return raw;
  try {
    return JSON.parse(raw) as unknown;
  } catch {
    return raw;
  }
}

async function fetchSystemInfoJson(
  url: string,
  httpGet?: HttpGetFn,
): Promise<{ status: number; data: unknown }> {
  if (httpGet !== undefined) {
    return await httpGet(url);
  }
  const controller = new AbortController();
  const timer = window.setTimeout(() => {
    controller.abort();
  }, 10_000);
  try {
    const response = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
      credentials: "omit",
      signal: controller.signal,
    });
    const text = await response.text();
    return { status: response.status, data: parseJsonOrValue(text) };
  } finally {
    window.clearTimeout(timer);
  }
}

export function getAppVersion(): string {
  return typeof __FLORABASE_APP_VERSION__ === "string"
    ? __FLORABASE_APP_VERSION__
    : "0.0.0";
}

export async function checkServerCompatibility(
  normalizedServerUrl: string,
  {
    httpGet,
    allowDebugHttp = false,
    appVersion = getAppVersion(),
  }: {
    httpGet?: HttpGetFn;
    allowDebugHttp?: boolean;
    appVersion?: string;
  } = {},
): Promise<ServerCompatibilityResult> {
  const health = await probeFlorabaseHealth(normalizedServerUrl, {
    httpGet,
    allowDebugHttp,
  });
  if (!health.ok) {
    return health;
  }

  let response: { status: number; data: unknown };
  try {
    response = await fetchSystemInfoJson(
      `${normalizedServerUrl}/api/v1/system/info`,
      httpGet,
    );
  } catch {
    return {
      ok: false,
      kind: "unreachable",
      message:
        "Server responded to /api/v1/health, but the mobile app could not reach /api/v1/system/info. Check network and CORS configuration.",
    };
  }

  if (response.status === 404) {
    return {
      ok: false,
      kind: "incompatible-server",
      message:
        "This Florabase server does not support mobile device sign-in yet. Update your server to a version that provides /api/v1/system/info.",
    };
  }

  if (response.status < 200 || response.status >= 300) {
    return {
      ok: false,
      kind: "http-error",
      message: `Server responded with HTTP ${String(response.status)} at /api/v1/system/info.`,
    };
  }

  const body = parseJsonOrValue(response.data);
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return {
      ok: false,
      kind: "incompatible-server",
      message:
        "Server returned an unexpected response from /api/v1/system/info.",
    };
  }

  const record = body as Record<string, unknown>;
  const serverVersion =
    typeof record.server_version === "string" &&
    record.server_version.trim() !== ""
      ? record.server_version.trim()
      : null;
  const apiVersion =
    typeof record.api_version === "number" &&
    Number.isInteger(record.api_version)
      ? record.api_version
      : null;
  const minClientVersion =
    typeof record.min_client_version === "string" &&
    record.min_client_version.trim() !== ""
      ? record.min_client_version.trim()
      : null;
  const capabilities = Array.isArray(record.capabilities)
    ? record.capabilities.filter(
        (item): item is string => typeof item === "string",
      )
    : null;

  if (
    serverVersion === null ||
    apiVersion === null ||
    minClientVersion === null ||
    capabilities === null ||
    parseSemver(minClientVersion) === null
  ) {
    return {
      ok: false,
      kind: "incompatible-server",
      message:
        "Server returned an incomplete compatibility contract at /api/v1/system/info.",
    };
  }

  if (apiVersion !== SUPPORTED_API_VERSION) {
    return {
      ok: false,
      kind: "incompatible-server",
      message: `This server uses API version ${String(apiVersion)}, which is not supported by this Florabase app (supports API version ${String(SUPPORTED_API_VERSION)}).`,
    };
  }

  if (!capabilities.includes(REQUIRED_CAPABILITY)) {
    return {
      ok: false,
      kind: "incompatible-server",
      message:
        "This Florabase server does not advertise mobile device sign-in (device-auth). Update your server before signing in.",
    };
  }

  if (!isVersionAtLeast(appVersion, minClientVersion)) {
    return {
      ok: false,
      kind: "incompatible-client",
      message: `This Florabase app (${appVersion}) is older than the minimum version required by your server (${minClientVersion}). Update the app before signing in.`,
    };
  }

  return {
    ok: true,
    serverUrl: normalizedServerUrl,
    info: {
      serverVersion,
      apiVersion,
      minClientVersion,
      capabilities,
    },
  };
}
