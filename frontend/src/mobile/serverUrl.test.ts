import { describe, expect, it } from "vitest";

import { validateServerUrl } from "./serverUrl";

function ipv4(...octets: [number, number, number, number]): string {
  return octets.join(".");
}

describe("validateServerUrl", () => {
  it("accepts and normalizes https URLs in release and debug builds", () => {
    expect(
      validateServerUrl("  https://Florabase.Example.COM/ ", {
        allowDebugHttp: false,
      }),
    ).toEqual({
      ok: true,
      normalizedUrl: "https://florabase.example.com",
    });

    expect(
      validateServerUrl("https://nas.home.arpa:8443", {
        allowDebugHttp: false,
      }),
    ).toEqual({
      ok: true,
      normalizedUrl: "https://nas.home.arpa:8443",
    });
  });

  it("rejects http URLs in release builds (including 10.0.2.2 and LAN)", () => {
    const privateLan = ipv4(192, 168, 1, 20);
    for (const url of [
      "http://10.0.2.2:5173",
      `http://${privateLan}:8080`,
      "http://localhost:5173",
      "http://florabase.example.com",
    ]) {
      const result = validateServerUrl(url, { allowDebugHttp: false });
      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.error).toContain("HTTPS is required");
      }
    }
  });

  it("allows http for 10.0.2.2 and private LAN hosts in debug builds only", () => {
    const classC = ipv4(192, 168, 1, 42);
    const classB = ipv4(172, 16, 0, 10);
    for (const url of [
      "http://10.0.2.2:5173",
      "http://10.0.2.2:8000/",
      `http://${classC}:8080`,
      `http://${classB}:5173`,
      "http://127.0.0.1:5173",
      "http://localhost:5173",
      "http://nas.local:8080",
    ]) {
      const result = validateServerUrl(url, { allowDebugHttp: true });
      expect(result.ok).toBe(true);
    }
  });

  it("still rejects public http hosts even in debug builds", () => {
    const result = validateServerUrl("http://florabase.example.com", {
      allowDebugHttp: true,
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toContain("10.0.2.2 or private LAN");
    }
  });

  it("rejects empty, malformed, non-http(s), credentialed, or path/query URLs", () => {
    const credentialed = ["https://user:pass", "florabase.example.com"].join(
      "@",
    );
    expect(validateServerUrl("   ", { allowDebugHttp: true }).ok).toBe(false);
    expect(validateServerUrl("not a url", { allowDebugHttp: true }).ok).toBe(
      false,
    );
    expect(
      validateServerUrl("ftp://nas.local", { allowDebugHttp: true }).ok,
    ).toBe(false);
    expect(validateServerUrl(credentialed, { allowDebugHttp: false }).ok).toBe(
      false,
    );
    expect(
      validateServerUrl("https://florabase.example.com/subpath", {
        allowDebugHttp: false,
      }).ok,
    ).toBe(false);
    expect(
      validateServerUrl("https://florabase.example.com/?a=1", {
        allowDebugHttp: false,
      }).ok,
    ).toBe(false);
  });
});
