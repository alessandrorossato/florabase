/**
 * Probes an existing Florabase instance via `GET /api/v1/health` (and best-effort `/release.json`
 * for production version metadata) using Capacitor's built-in native HTTP bridge when available.
 *
 * Using native `CapacitorHttp` for the unauthenticated health probe respects Android's
 * `network_security_config.xml` (system + user-installed CAs and cleartext policy) while keeping
 * backend CORS and auth configuration completely unchanged in MOBILE-001.
 */

import { getCapacitorGlobal } from "./runtime";

export interface HttpGetResponse {
  status: number;
  data: unknown;
}

export type HttpGetFn = (url: string) => Promise<HttpGetResponse>;

export type HealthProbeErrorKind =
  "tls" | "cleartext" | "unreachable" | "http-error" | "non-florabase";

export type HealthProbeResult =
  | {
      ok: true;
      serverUrl: string;
      status: "ok";
      httpStatus: number;
      serverVersion: string | null;
      serverRevision: string | null;
    }
  | {
      ok: false;
      kind: HealthProbeErrorKind;
      message: string;
    };

const REQUEST_TIMEOUT_MS = 10_000;

async function defaultHttpGet(url: string): Promise<HttpGetResponse> {
  const capacitor = getCapacitorGlobal();
  const headers = { Accept: "application/json" };

  const httpPlugin = capacitor?.Plugins?.CapacitorHttp;
  if (httpPlugin !== undefined) {
    const response = await httpPlugin.get({
      url,
      headers,
      connectTimeout: REQUEST_TIMEOUT_MS,
      readTimeout: REQUEST_TIMEOUT_MS,
    });
    return { status: response.status, data: response.data };
  }

  if (typeof capacitor?.nativePromise === "function") {
    const response = await capacitor.nativePromise<{
      status: number;
      data: unknown;
    }>("CapacitorHttp", "get", {
      url,
      headers,
      connectTimeout: REQUEST_TIMEOUT_MS,
      readTimeout: REQUEST_TIMEOUT_MS,
    });
    return { status: response.status, data: response.data };
  }

  const controller = new AbortController();
  const timer = window.setTimeout(() => {
    controller.abort();
  }, REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(url, {
      method: "GET",
      headers,
      cache: "no-store",
      credentials: "omit",
      signal: controller.signal,
    });
    const text = await response.text();
    return { status: response.status, data: parseJsonOrText(text) };
  } finally {
    window.clearTimeout(timer);
  }
}

function parseJsonOrText(raw: unknown): unknown {
  if (typeof raw !== "string") return raw;
  try {
    return JSON.parse(raw) as unknown;
  } catch {
    return raw;
  }
}

function classifyNetworkError(
  error: unknown,
  allowDebugHttp: boolean,
): { kind: HealthProbeErrorKind; message: string } {
  const detail =
    error instanceof Error
      ? error.message
      : typeof error === "string"
        ? error
        : "";
  const lower = detail.toLowerCase();

  if (
    lower.includes("cleartext") ||
    lower.includes("network security policy")
  ) {
    return {
      kind: "cleartext",
      message:
        "Cleartext HTTP traffic is blocked by Android network security policy. Use an https:// server URL.",
    };
  }

  if (
    lower.includes("certpathvalidatorexception") ||
    lower.includes("trust anchor") ||
    lower.includes("ssl") ||
    lower.includes("certificate") ||
    lower.includes("handshake") ||
    lower.includes("pkix")
  ) {
    return {
      kind: "tls",
      message:
        "TLS certificate was not trusted. If your NAS uses a self-signed or private CA, install the CA certificate in Android Settings (see docs/mobile.md).",
    };
  }

  return {
    kind: "unreachable",
    message: allowDebugHttp
      ? "Could not reach the server. Check the address, port, and network connection (use http://10.0.2.2:5173 to reach a local dev server from the Android emulator)."
      : "Could not reach the server. Check the address, port, and network connection.",
  };
}

async function fetchOptionalReleaseMetadata(
  serverUrl: string,
  httpGet: HttpGetFn,
): Promise<{ version: string | null; revision: string | null }> {
  try {
    const response = await httpGet(`${serverUrl}/release.json`);
    if (response.status < 200 || response.status >= 300) {
      return { version: null, revision: null };
    }
    const parsed = parseJsonOrText(response.data);
    if (typeof parsed !== "object" || parsed === null) {
      return { version: null, revision: null };
    }
    const record = parsed as Record<string, unknown>;
    const version =
      typeof record.version === "string" && record.version.trim() !== ""
        ? record.version.trim()
        : null;
    const revision =
      typeof record.revision === "string" &&
      record.revision.trim() !== "" &&
      record.revision !== "unknown"
        ? record.revision.trim()
        : null;
    return { version, revision };
  } catch {
    return { version: null, revision: null };
  }
}

export async function probeFlorabaseHealth(
  normalizedServerUrl: string,
  {
    httpGet = defaultHttpGet,
    allowDebugHttp = false,
  }: {
    httpGet?: HttpGetFn;
    allowDebugHttp?: boolean;
  } = {},
): Promise<HealthProbeResult> {
  const healthUrl = `${normalizedServerUrl}/api/v1/health`;
  let response: HttpGetResponse;
  try {
    response = await httpGet(healthUrl);
  } catch (error: unknown) {
    const classified = classifyNetworkError(error, allowDebugHttp);
    return { ok: false, kind: classified.kind, message: classified.message };
  }

  if (response.status === 404) {
    return {
      ok: false,
      kind: "non-florabase",
      message:
        "Server responded with HTTP 404 at /api/v1/health. This does not appear to be a Florabase server.",
    };
  }

  if (response.status < 200 || response.status >= 300) {
    return {
      ok: false,
      kind: "http-error",
      message: `Server responded with HTTP ${String(response.status)} at /api/v1/health.`,
    };
  }

  const body = parseJsonOrText(response.data);
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return {
      ok: false,
      kind: "non-florabase",
      message:
        'Server responded, but /api/v1/health did not return a Florabase JSON payload (expected {"status": "ok"}).',
    };
  }

  const record = body as Record<string, unknown>;
  if (record.status !== "ok") {
    return {
      ok: false,
      kind: "non-florabase",
      message:
        'Server responded, but /api/v1/health did not report status "ok". Check that this URL points to Florabase.',
    };
  }

  const healthVersion =
    typeof record.version === "string" && record.version.trim() !== ""
      ? record.version.trim()
      : null;

  let serverVersion = healthVersion;
  let serverRevision: string | null = null;
  if (serverVersion === null) {
    const release = await fetchOptionalReleaseMetadata(
      normalizedServerUrl,
      httpGet,
    );
    serverVersion = release.version;
    serverRevision = release.revision;
  }

  return {
    ok: true,
    serverUrl: normalizedServerUrl,
    status: "ok",
    httpStatus: response.status,
    serverVersion,
    serverRevision,
  };
}
