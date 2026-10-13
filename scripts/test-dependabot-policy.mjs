#!/usr/bin/env node
// Use the already pinned OpenAPI toolchain's YAML parser; no new dependency or bot emulator.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

const root = process.argv[2] ?? path.resolve(import.meta.dirname, "..");
const frontend = createRequire(path.join(process.cwd(), "package.json"));
const openapi = createRequire(frontend.resolve("openapi-typescript"));
const redocly = createRequire(openapi.resolve("@redocly/openapi-core"));
const { load } = redocly("js-yaml");
const eslint = createRequire(frontend.resolve("typescript-eslint"));
const estree = createRequire(
  eslint.resolve("@typescript-eslint/typescript-estree"),
);
const semver = estree("semver");
const config = load(
  readFileSync(path.join(root, ".github/dependabot.yml"), "utf8"),
);
const pkg = JSON.parse(
  readFileSync(path.join(root, "frontend/package.json"), "utf8"),
);
const pins = { ...pkg.dependencies, ...pkg.devDependencies };
assert.equal(config.version, 2);
assert.equal(config.updates.length, 3);
const rules = Object.fromEntries(
  config.updates.map((rule) => [rule["package-ecosystem"], rule]),
);
assert.deepEqual(Object.keys(rules).sort(), ["docker", "npm", "pip"]);
for (const rule of config.updates) {
  assert.deepEqual(rule.schedule, { interval: "weekly" });
  assert.equal(rule["open-pull-requests-limit"], undefined);
  assert.equal(rule.allow, undefined);
}
assert.equal(rules.pip.directory, "/backend");
assert.equal(rules.npm.directory, "/frontend");
assert.equal(rules.docker.directory, "/");
assert.deepEqual(rules.pip.groups, {
  "backend-minor-patches": { "update-types": ["minor", "patch"] },
});
assert.deepEqual(rules.npm.groups, {
  "frontend-minor-patches": { "update-types": ["minor", "patch"] },
});
assert.deepEqual(rules.pip.ignore, [
  { "dependency-name": "sqlalchemy", versions: [">=2.1,<2.2"] },
]);
const expected = {
  react: ">=19.3.0 <20.0.0",
  "react-dom": ">=19.3.0 <20.0.0",
  "@types/react": ">=19.3.0 <20.0.0",
  "@types/react-dom": ">=19.3.0 <20.0.0",
  jsdom: ">=30.1.0",
  "@types/node": ">=25.0.0",
};
assert.equal(rules.npm.ignore.length, Object.keys(expected).length);
for (const rule of rules.npm.ignore) {
  assert.ok(
    Object.hasOwn(pins, rule["dependency-name"]),
    "ignore name must exist in manifest",
  );
  assert.deepEqual(rule, {
    "dependency-name": rule["dependency-name"],
    versions: [expected[rule["dependency-name"]]],
  });
}
// Exercise native npm range semantics at the maintained/deferred boundaries.
for (const name of ["react", "react-dom", "@types/react", "@types/react-dom"]) {
  assert.equal(semver.satisfies("19.2.99", expected[name]), false);
  assert.equal(semver.satisfies("19.3.0", expected[name]), true);
  assert.equal(semver.satisfies("19.3.99", expected[name]), true);
  assert.equal(semver.satisfies("19.4.0", expected[name]), true);
}
assert.equal(semver.satisfies("30.0.99", expected.jsdom), false);
assert.equal(semver.satisfies("30.1.0", expected.jsdom), true);
assert.equal(semver.satisfies("31.0.0", expected.jsdom), true);
assert.equal(semver.satisfies("24.99.0", expected["@types/node"]), false);
assert.equal(semver.satisfies("25.0.0", expected["@types/node"]), true);
assert.equal(semver.satisfies("26.6.4", expected["@types/node"]), true);
assert.equal(semver.satisfies("27.0.0", expected["@types/node"]), true);
assert.equal(rules.docker.ignore, undefined);
assert.equal(pkg.engines.node, ">=24 <25");
assert.match(pins.react, /^19\.2\./);
assert.match(pins["react-dom"], /^19\.2\./);
assert.match(pins["@types/react"], /^19\.2\./);
assert.match(pins["@types/react-dom"], /^19\.2\./);
assert.match(pins.jsdom, /^30\.0\./);
assert.match(pins["@types/node"], /^24\./);
for (const filename of [
  "backend/pyproject.toml",
  "backend/requirements.lock",
  "backend/requirements-dev.lock",
]) {
  assert.match(
    readFileSync(path.join(root, filename), "utf8"),
    /sqlalchemy==2\.0\./,
  );
}
const lock = readFileSync(path.join(root, "frontend/pnpm-lock.yaml"), "utf8");
for (const name of Object.keys(expected))
  assert.ok(lock.includes(`${name}@${pins[name]}`));
console.log(
  "DEPENDABOT POLICY PASSED: valid YAML; exact names/ranges; weekly groups intact; delivered contracts unchanged",
);
