import { describe, expect, it } from "vitest";

import { compareSemver, isVersionAtLeast, parseSemver } from "./semver";

describe("SemVer comparator with pre-release ordering", () => {
  it("orders pre-release identifiers numerically and before final release", () => {
    expect(compareSemver("0.1.0-beta.8", "0.1.0-beta.10")).toBe(-1);
    expect(compareSemver("0.1.0-beta.10", "0.1.0")).toBe(-1);
    expect(compareSemver("0.1.0-beta.8", "0.1.0")).toBe(-1);
    expect(compareSemver("0.1.0-beta.10", "0.1.0-beta.8")).toBe(1);
    expect(compareSemver("0.1.0", "0.1.0-beta.10")).toBe(1);
    expect(compareSemver("0.1.0-beta.8", "0.1.0-beta.8")).toBe(0);
  });

  it("handles alpha/beta/rc precedence, numeric vs alphanumeric, and build metadata", () => {
    expect(compareSemver("0.1.0-alpha.1", "0.1.0-beta.1")).toBe(-1);
    expect(compareSemver("0.1.0-beta.1", "0.1.0-rc.1")).toBe(-1);
    expect(compareSemver("0.1.0-1", "0.1.0-alpha")).toBe(-1);
    expect(compareSemver("0.1.0-beta.8", "0.1.0-beta.8.1")).toBe(-1);
    expect(compareSemver("0.1.0-beta.8+abc123", "0.1.0-beta.8+def456")).toBe(0);
    expect(compareSemver("1.0.0", "0.9.9")).toBe(1);
  });

  it("checks minimum version thresholds cleanly", () => {
    expect(isVersionAtLeast("0.1.0-beta.8", "0.1.0-beta.8")).toBe(true);
    expect(isVersionAtLeast("0.1.0-beta.10", "0.1.0-beta.8")).toBe(true);
    expect(isVersionAtLeast("0.1.0", "0.1.0-beta.8")).toBe(true);
    expect(isVersionAtLeast("0.1.0-beta.7", "0.1.0-beta.8")).toBe(false);
    expect(isVersionAtLeast("0.1.0-beta.8", "0.1.0-beta.10")).toBe(false);
    expect(isVersionAtLeast("0.1.0-beta.8", "0.1.0")).toBe(false);
  });

  it("rejects malformed SemVer strings", () => {
    expect(parseSemver("")).toBeNull();
    expect(parseSemver("v0.1.0")).toBeNull();
    expect(parseSemver("0.1")).toBeNull();
    expect(parseSemver("01.0.0")).toBeNull();
    expect(parseSemver("0.1.0-beta.08")).toBeNull();
    expect(compareSemver("not-a-version", "0.1.0")).toBeNull();
    expect(isVersionAtLeast("0.1.0-beta.8", "bad")).toBe(false);
  });
});
