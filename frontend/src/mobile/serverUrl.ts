/**
 * Validation and normalization for the Florabase server URL entered in native onboarding.
 *
 * Release builds accept only `https://` origin URLs.
 * Debug builds additionally allow `http://` for the Android emulator host loopback (`10.0.2.2`),
 * local loopback, RFC1918 private LAN IPv4 addresses, and common local mDNS/LAN suffixes.
 */

export type ServerUrlValidationResult =
  { ok: true; normalizedUrl: string } | { ok: false; error: string };

const LOCAL_LAN_SUFFIXES = [".local", ".lan", ".home.arpa"];

function isIpv4PrivateOrLoopback(hostname: string): boolean {
  const parts = hostname.split(".");
  if (parts.length !== 4) return false;
  const octets = parts.map((part) => {
    if (!/^\d{1,3}$/.test(part)) return -1;
    return Number.parseInt(part, 10);
  });
  if (octets.some((octet) => octet < 0 || octet > 255)) return false;
  const [a, b] = octets;
  // RFC1918 class A private block (includes Android emulator host alias 10.0.2.2)
  if (a === 10) return true;
  // Loopback block
  if (a === 127) return true;
  // RFC1918 class B private block
  if (a === 172 && b >= 16 && b <= 31) return true;
  // RFC1918 class C private block
  if (a === 192 && b === 168) return true;
  return false;
}

export function isDebugAllowedHttpHost(hostname: string): boolean {
  const lower = hostname.toLowerCase();
  if (lower === "localhost" || lower === "[::1]" || lower === "::1") {
    return true;
  }
  if (isIpv4PrivateOrLoopback(lower)) {
    return true;
  }
  return LOCAL_LAN_SUFFIXES.some(
    (suffix) => lower.endsWith(suffix) && lower.length > suffix.length,
  );
}

export function validateServerUrl(
  rawInput: string,
  { allowDebugHttp }: { allowDebugHttp: boolean },
): ServerUrlValidationResult {
  const trimmed = rawInput.trim();
  if (trimmed === "") {
    return { ok: false, error: "Enter your Florabase server URL." };
  }

  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    return {
      ok: false,
      error: allowDebugHttp
        ? "Enter a full URL starting with https:// (or http://10.0.2.2:5173 in debug builds)."
        : "Enter a full URL starting with https:// (for example, https://florabase.example.com).",
    };
  }

  if (parsed.protocol !== "https:" && parsed.protocol !== "http:") {
    return {
      ok: false,
      error: allowDebugHttp
        ? "Only https:// URLs (or local http:// in debug builds) are supported."
        : "Only https:// server URLs are supported.",
    };
  }

  if (parsed.username !== "" || parsed.password !== "") {
    return {
      ok: false,
      error: "Do not include a username or password in the server URL.",
    };
  }

  if (parsed.hostname === "") {
    return { ok: false, error: "Enter a valid server hostname." };
  }

  if (parsed.search !== "" || parsed.hash !== "") {
    return {
      ok: false,
      error: "Server URL must not contain query parameters or fragments.",
    };
  }

  if (parsed.pathname !== "" && parsed.pathname !== "/") {
    return {
      ok: false,
      error:
        "Enter the server root URL without a path (for example, https://florabase.example.com).",
    };
  }

  if (parsed.protocol === "http:") {
    if (!allowDebugHttp) {
      return {
        ok: false,
        error: "HTTPS is required. Use an https:// server URL.",
      };
    }
    if (!isDebugAllowedHttpHost(parsed.hostname)) {
      return {
        ok: false,
        error:
          "Plain HTTP is only allowed for 10.0.2.2 or private LAN addresses in debug builds. Use https:// for other hosts.",
      };
    }
  }

  return {
    ok: true,
    normalizedUrl: `${parsed.protocol}//${parsed.host}`,
  };
}
