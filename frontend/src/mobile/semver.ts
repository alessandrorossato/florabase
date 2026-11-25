/**
 * Strict SemVer 2.0.0 parser and comparator including pre-release ordering.
 *
 * Examples:
 * - `0.1.0-beta.8 < 0.1.0-beta.10 < 0.1.0`
 * - `0.1.0-alpha.1 < 0.1.0-beta.1 < 0.1.0-rc.1 < 0.1.0`
 * - Build metadata (`+sha`) is ignored for precedence per SemVer 2.0.0 §10.
 */

export interface ParsedSemver {
  major: number;
  minor: number;
  patch: number;
  prerelease: readonly (number | string)[];
}

const SEMVER_RE =
  /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$/;

const NUMERIC_IDENT_RE = /^(0|[1-9]\d*)$/;

export function parseSemver(input: string): ParsedSemver | null {
  const trimmed = input.trim();
  const match = SEMVER_RE.exec(trimmed);
  if (match === null) return null;

  const major = Number.parseInt(match[1], 10);
  const minor = Number.parseInt(match[2], 10);
  const patch = Number.parseInt(match[3], 10);
  if (
    !Number.isSafeInteger(major) ||
    !Number.isSafeInteger(minor) ||
    !Number.isSafeInteger(patch)
  ) {
    return null;
  }

  const rawPre: string | undefined = match[4];
  if (!rawPre) {
    return { major, minor, patch, prerelease: [] };
  }

  const prerelease: (number | string)[] = [];
  for (const part of rawPre.split(".")) {
    if (/^\d+$/.test(part)) {
      if (!NUMERIC_IDENT_RE.test(part)) {
        // SemVer 2.0.0 §9: numeric identifiers MUST NOT include leading zeroes.
        return null;
      }
      const num = Number.parseInt(part, 10);
      if (!Number.isSafeInteger(num)) return null;
      prerelease.push(num);
    } else {
      prerelease.push(part);
    }
  }

  return { major, minor, patch, prerelease };
}

/**
 * Compares two SemVer 2.0.0 strings.
 * Returns `-1` if `a < b`, `0` if `a == b`, `1` if `a > b`, or `null` if either is invalid.
 */
export function compareSemver(a: string, b: string): -1 | 0 | 1 | null {
  const pa = parseSemver(a);
  const pb = parseSemver(b);
  if (pa === null || pb === null) return null;

  if (pa.major !== pb.major) return pa.major < pb.major ? -1 : 1;
  if (pa.minor !== pb.minor) return pa.minor < pb.minor ? -1 : 1;
  if (pa.patch !== pb.patch) return pa.patch < pb.patch ? -1 : 1;

  const aPre = pa.prerelease;
  const bPre = pb.prerelease;
  if (aPre.length === 0 && bPre.length === 0) return 0;
  // A version without a pre-release has higher precedence than a pre-release (SemVer §11.3).
  if (aPre.length === 0) return 1;
  if (bPre.length === 0) return -1;

  const len = Math.min(aPre.length, bPre.length);
  for (let i = 0; i < len; i += 1) {
    const ai = aPre[i];
    const bi = bPre[i];
    if (ai === bi) continue;
    const aNum = typeof ai === "number";
    const bNum = typeof bi === "number";
    if (aNum && bNum) return ai < bi ? -1 : 1;
    // Numeric identifiers always have lower precedence than non-numeric identifiers (SemVer §11.4.3).
    if (aNum) return -1;
    if (bNum) return 1;
    return ai < bi ? -1 : 1;
  }

  if (aPre.length === bPre.length) return 0;
  return aPre.length < bPre.length ? -1 : 1;
}

export function isVersionAtLeast(
  currentVersion: string,
  minVersion: string,
): boolean {
  const cmp = compareSemver(currentVersion, minVersion);
  return cmp !== null && cmp >= 0;
}
