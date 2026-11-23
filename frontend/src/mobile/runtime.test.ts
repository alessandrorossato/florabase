import { afterEach, describe, expect, it, vi } from "vitest";

import { getCapacitorGlobal, isNativeShell } from "./runtime";

describe("native shell runtime detection", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns false in web contexts where window.Capacitor is absent", () => {
    const webGlobal = {} as typeof globalThis;
    expect(getCapacitorGlobal(webGlobal)).toBeUndefined();
    expect(isNativeShell(webGlobal)).toBe(false);
  });

  it("returns false when Capacitor reports a non-native web platform", () => {
    const webCapGlobal = {
      Capacitor: {
        isNativePlatform: () => false,
        getPlatform: () => "web",
      },
    } as unknown as typeof globalThis;

    expect(isNativeShell(webCapGlobal)).toBe(false);
  });

  it("returns true when Capacitor reports a native platform", () => {
    const androidGlobal = {
      Capacitor: {
        isNativePlatform: () => true,
        getPlatform: () => "android",
      },
    } as unknown as typeof globalThis;

    expect(isNativeShell(androidGlobal)).toBe(true);
  });

  it("fails closed to false if Capacitor.isNativePlatform throws", () => {
    const brokenGlobal = {
      Capacitor: {
        isNativePlatform: () => {
          throw new Error("bridge error");
        },
      },
    } as unknown as typeof globalThis;

    expect(isNativeShell(brokenGlobal)).toBe(false);
  });
});
