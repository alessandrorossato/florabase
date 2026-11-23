#!/usr/bin/env node
// Audit installed npm dependency licences for AGPL-3.0-or-later compatibility.

import fs from "node:fs";
import path from "node:path";

const FORBIDDEN = [
  ["GPL-2.0-only", /\bGPL[- ]?2(?:\.0)?-only\b/i],
  ["SSPL", /\bSSPL\b|Server Side Public License/i],
  ["BUSL", /\bBUSL\b|Business Source License/i],
  ["non-commercial", /\bCC[- ]?BY[- ]?NC\b|non[- ]?commercial/i],
];

function formatLicence(pkg) {
  if (typeof pkg.license === "string" && pkg.license.trim()) {
    return pkg.license.trim();
  }
  if (pkg.license && typeof pkg.license === "object" && typeof pkg.license.type === "string") {
    return pkg.license.type.trim();
  }
  if (Array.isArray(pkg.licenses)) {
    const parts = pkg.licenses
      .map((entry) => (typeof entry === "string" ? entry : entry?.type))
      .filter((value) => typeof value === "string" && value.trim())
      .map((value) => value.trim());
    if (parts.length > 0) return parts.join(" OR ");
  }
  return "UNKNOWN";
}

function collectPackages(rootDir) {
  const seen = new Map();
  function walk(dir) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(fullPath);
      } else if (entry.name === "package.json") {
        const parent = path.basename(dir);
        const grand = path.basename(path.dirname(dir));
        const greatGrand = path.basename(path.dirname(path.dirname(dir)));
        const isInstalledPkg =
          parent !== "node_modules" &&
          (grand === "node_modules" || (grand.startsWith("@") && greatGrand === "node_modules"));
        if (!isInstalledPkg) continue;
        try {
          const pkg = JSON.parse(fs.readFileSync(fullPath, "utf8"));
          if (typeof pkg.name === "string" && typeof pkg.version === "string") {
            seen.set(`${pkg.name}@${pkg.version}`, formatLicence(pkg));
          }
        } catch {
          // Ignore malformed or unreadable manifest files.
        }
      }
    }
  }
  walk(rootDir);
  return [...seen.entries()].sort((a, b) => a[0].localeCompare(b[0]));
}

const nodeModules = process.argv[2] || "node_modules";
const pnpmDir = path.join(nodeModules, ".pnpm");
const rootDir = fs.existsSync(pnpmDir) ? pnpmDir : nodeModules;
if (!fs.existsSync(rootDir)) {
  console.error(`npm dependencies directory not found: ${rootDir}`);
  process.exit(1);
}

const rows = collectPackages(rootDir);
const violations = [];
console.log(`== npm dependency licences (${rows.length} packages) ==`);
for (const [pkg, licence] of rows) {
  console.log(`  ${pkg}: ${licence}`);
  for (const [rule, pattern] of FORBIDDEN) {
    if (pattern.test(licence)) {
      violations.push({ pkg, licence, rule });
      break;
    }
  }
}

if (violations.length > 0) {
  console.error("\nForbidden npm licences detected:");
  for (const { pkg, licence, rule } of violations) {
    console.error(`  - ${pkg}: ${licence} (matched ${rule})`);
  }
  process.exit(1);
}

console.log(`npm licence check passed (${rows.length} packages, 0 forbidden).`);
