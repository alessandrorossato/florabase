#!/bin/sh
set -eu
# Compose initializes volume ownership before the non-root application starts.
# CI makes pnpm's lockfile-driven replacement safe without an interactive terminal.
mkdir -p "$HOME"
if [ "${FLORABASE_QUALITY_OFFLINE:-0}" = "1" ]; then
  # Only Quality's network-disabled compose overlay opts into offline startup.
  # Validate guaranteed pnpm artifacts without requiring optional .package-map.json
  # and without using JSON.parse on .modules.yaml (which is specified as YAML).
  if [ ! -s /app/node_modules/.pnpm/lock.yaml ] \
    || [ ! -s /app/node_modules/.modules.yaml ] \
    || ! cmp -s /app/pnpm-lock.yaml /app/node_modules/.pnpm/lock.yaml \
    || ! node - <<'EOF'
const fs = require("fs");
const path = require("path");

const fail = (reason) => {
  process.stderr.write(`florabase-dev-entrypoint: ${reason}\n`);
  process.exit(1);
};

const unquote = (raw, allowTrailingComma) => {
  let text = raw.trim();
  if (allowTrailingComma && text.endsWith(",")) {
    text = text.slice(0, -1).trim();
  }
  if (text.startsWith('"') && text.endsWith('"') && text.length >= 2) {
    return text.slice(1, -1).replace(/\\"/g, '"').replace(/\\\\/g, "\\");
  }
  if (text.startsWith("'") && text.endsWith("'") && text.length >= 2) {
    return text.slice(1, -1).replace(/''/g, "'");
  }
  return text;
};

const checkBalancedFlowTokens = (source) => {
  const stack = [];
  let quote = null;
  for (let i = 0; i < source.length; i += 1) {
    const ch = source[i];
    if (quote === '"') {
      if (ch === "\\") {
        i += 1;
      } else if (ch === '"') {
        quote = null;
      }
      continue;
    }
    if (quote === "'") {
      if (ch === "'" && source[i + 1] === "'") {
        i += 1;
      } else if (ch === "'") {
        quote = null;
      }
      continue;
    }
    if (ch === "#") {
      while (i < source.length && source[i] !== "\n") {
        i += 1;
      }
      continue;
    }
    if (ch === '"' || ch === "'") {
      quote = ch;
    } else if (ch === "{" || ch === "[") {
      stack.push(ch);
    } else if (ch === "}" || ch === "]") {
      const open = stack.pop();
      if ((ch === "}" && open !== "{") || (ch === "]" && open !== "[")) {
        fail("corrupt .modules.yaml delimiter balance");
      }
    }
  }
  if (quote !== null || stack.length !== 0) {
    fail("truncated or unbalanced .modules.yaml");
  }
};

const parseModulesYaml = (raw) => {
  if (!raw.trim() || raw.includes("\0")) {
    fail("empty or binary .modules.yaml");
  }
  const allLines = raw.split(/\r?\n/);
  let bodyLines = allLines;
  const nonEmptyIdx = [];
  for (let i = 0; i < allLines.length; i += 1) {
    const stripped = allLines[i].trim();
    if (stripped && !stripped.startsWith("#")) {
      nonEmptyIdx.push(i);
    }
  }
  if (nonEmptyIdx.length === 0) {
    fail("empty .modules.yaml");
  }
  const firstTrimmed = allLines[nonEmptyIdx[0]].trim();
  const lastTrimmed = allLines[nonEmptyIdx[nonEmptyIdx.length - 1]].trim();
  const wrappedInBraces = firstTrimmed === "{";
  if (wrappedInBraces) {
    if (lastTrimmed !== "}") {
      fail("truncated JSON-style .modules.yaml");
    }
    checkBalancedFlowTokens(raw);
    bodyLines = allLines.slice(nonEmptyIdx[0] + 1, nonEmptyIdx[nonEmptyIdx.length - 1]);
  }

  let baseIndent = null;
  let section = null;
  let container = null; // null | "flow-array" | "flow-object" | "yaml-block"
  let braceDepth = 0;
  const seenKeys = new Set();
  const scalars = {};
  const lists = {};
  const included = {};

  for (const rawLine of bodyLines) {
    const trimmed = rawLine.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }
    const indent = rawLine.length - rawLine.trimStart().length;
    if (baseIndent === null) {
      baseIndent = indent;
    }
    if (indent < baseIndent) {
      fail("unexpected indentation in .modules.yaml");
    }

    if (indent === baseIndent) {
      if (container === "flow-array" && (trimmed === "]" || trimmed === "],")) {
        container = null;
        section = null;
        continue;
      }
      if (container === "flow-object" && (trimmed === "}" || trimmed === "},")) {
        braceDepth -= 1;
        if (braceDepth !== 0) {
          fail("unbalanced object in .modules.yaml");
        }
        container = null;
        section = null;
        continue;
      }
      if (container === "flow-array" || container === "flow-object") {
        fail("unclosed container in .modules.yaml");
      }
      const match = trimmed.match(/^(?:"([^"]+)"|'([^']+)'|([A-Za-z0-9_.-]+))\s*:\s*(.*)$/);
      if (!match) {
        fail(`malformed .modules.yaml entry: ${trimmed}`);
      }
      const key = match[1] ?? match[2] ?? match[3];
      seenKeys.add(key);
      section = key;
      let rest = match[4].trim();
      const restNoComma = rest.endsWith(",") ? rest.slice(0, -1).trim() : rest;
      if (restNoComma === "{}" || restNoComma === "{},") {
        container = null;
      } else if (restNoComma === "{") {
        container = "flow-object";
        braceDepth = 1;
      } else if (restNoComma.startsWith("[") && restNoComma.endsWith("]")) {
        const inner = restNoComma.slice(1, -1).trim();
        lists[key] = inner
          ? inner.split(",").map((item) => unquote(item, false)).filter(Boolean)
          : [];
        container = null;
      } else if (restNoComma === "[") {
        lists[key] = [];
        container = "flow-array";
      } else if (rest === "") {
        container = "yaml-block";
      } else {
        scalars[key] = unquote(rest, true);
        container = null;
      }
      continue;
    }

    if (container === "flow-object") {
      if (trimmed === "}" || trimmed === "},") {
        braceDepth -= 1;
        if (braceDepth < 0) {
          fail("unbalanced nested object in .modules.yaml");
        }
        continue;
      }
      if (trimmed.endsWith("{")) {
        braceDepth += 1;
        continue;
      }
      if (section === "included" && braceDepth === 1) {
        const sub = trimmed.match(/^(?:"([^"]+)"|'([^']+)'|([A-Za-z0-9_.-]+))\s*:\s*(.+)$/);
        if (sub) {
          const subKey = sub[1] ?? sub[2] ?? sub[3];
          included[subKey] = unquote(sub[4], true);
        }
      }
    } else if (container === "flow-array") {
      if (trimmed === "]" || trimmed === "],") {
        container = null;
        continue;
      }
      lists[section].push(unquote(trimmed, true));
    } else if (container === "yaml-block") {
      if (trimmed.startsWith("-")) {
        if (!lists[section]) {
          lists[section] = [];
        }
        lists[section].push(unquote(trimmed.slice(1), false));
      } else {
        const sub = trimmed.match(/^(?:"([^"]+)"|'([^']+)'|([A-Za-z0-9_.-]+))\s*:\s*(.*)$/);
        if (!sub) {
          fail(`malformed nested YAML entry in .modules.yaml: ${trimmed}`);
        }
        if (section === "included") {
          const subKey = sub[1] ?? sub[2] ?? sub[3];
          included[subKey] = unquote(sub[4], false);
        }
      }
    } else {
      fail(`unexpected indented line under scalar key ${section}`);
    }
  }

  if (container === "flow-array" || container === "flow-object" || braceDepth !== 0) {
    fail("unclosed section in .modules.yaml");
  }
  return { seenKeys, scalars, lists, included };
};

const root = "/app/node_modules";
const pkg = JSON.parse(fs.readFileSync("/app/package.json", "utf8"));
const manifest = parseModulesYaml(fs.readFileSync(path.join(root, ".modules.yaml"), "utf8"));

if (manifest.scalars.layoutVersion !== "5") {
  fail(`unsupported .modules.yaml layoutVersion: ${manifest.scalars.layoutVersion}`);
}
if (!pkg.packageManager || manifest.scalars.packageManager !== pkg.packageManager) {
  fail(`packageManager mismatch in .modules.yaml: ${manifest.scalars.packageManager}`);
}
if (manifest.scalars.virtualStoreDir !== ".pnpm") {
  fail(`unexpected virtualStoreDir in .modules.yaml: ${manifest.scalars.virtualStoreDir}`);
}
if (manifest.scalars.nodeLinker && manifest.scalars.nodeLinker !== "isolated") {
  fail(`unsupported nodeLinker in .modules.yaml: ${manifest.scalars.nodeLinker}`);
}
if (!manifest.seenKeys.has("pendingBuilds") || (manifest.lists.pendingBuilds || []).length > 0) {
  fail(".modules.yaml reports incomplete pendingBuilds");
}
if (
  !manifest.seenKeys.has("included")
  || manifest.included.dependencies !== "true"
  || manifest.included.devDependencies !== "true"
  || manifest.included.optionalDependencies === "false"
) {
  fail(".modules.yaml included dependency groups incomplete");
}

const declared = { ...(pkg.dependencies || {}), ...(pkg.devDependencies || {}) };
for (const name of Object.keys(declared)) {
  if (!fs.existsSync(path.join(root, name, "package.json"))) {
    fail(`missing declared dependency ${name}`);
  }
}

const lockText = fs.readFileSync(path.join(root, ".pnpm", "lock.yaml"), "utf8");
const snapMarker = "\nsnapshots:\n";
const snapIdx = lockText.indexOf(snapMarker);
if (snapIdx === -1) {
  fail("missing snapshots section in .pnpm/lock.yaml");
}
const skippedSet = new Set(manifest.lists.skipped || []);
const snapshotKeys = [];
for (const line of lockText.slice(snapIdx + snapMarker.length).split(/\r?\n/)) {
  if (line && !line.startsWith(" ") && !line.startsWith("#")) {
    break;
  }
  const match = line.match(/^  ([^ ].*?):\s*(\{\})?\s*$/);
  if (match) {
    snapshotKeys.push(unquote(match[1], false));
  }
}
if (snapshotKeys.length === 0) {
  fail("no snapshots found in .pnpm/lock.yaml");
}
const activeSnapshots = snapshotKeys.filter((key) => !skippedSet.has(key));

const pnpmRoot = path.join(root, ".pnpm");
const pnpmDirs = fs.readdirSync(pnpmRoot).filter(
  (entry) => entry !== "lock.yaml" && entry !== "node_modules"
    && fs.lstatSync(path.join(pnpmRoot, entry)).isDirectory(),
);
if (pnpmDirs.length !== activeSnapshots.length) {
  fail(`virtual store count ${pnpmDirs.length} != expected ${activeSnapshots.length}`);
}

for (const dir of pnpmDirs) {
  const nm = path.join(pnpmRoot, dir, "node_modules");
  if (!fs.existsSync(nm)) {
    fail(`missing virtual store node_modules for ${dir}`);
  }
  for (const item of fs.readdirSync(nm)) {
    if (item.startsWith(".")) {
      continue;
    }
    const itemPath = path.join(nm, item);
    if (item.startsWith("@")) {
      for (const scoped of fs.readdirSync(itemPath)) {
        if (!fs.existsSync(path.join(itemPath, scoped, "package.json"))) {
          fail(`dangling or incomplete virtual store dependency ${item}/${scoped} in ${dir}`);
        }
      }
    } else if (!fs.existsSync(path.join(itemPath, "package.json"))) {
      fail(`dangling or incomplete virtual store dependency ${item} in ${dir}`);
    }
  }
}

const binDir = path.join(root, ".bin");
const bins = fs.readdirSync(binDir);
if (bins.length === 0) {
  fail("empty .bin directory");
}
for (const bin of bins) {
  if (!fs.existsSync(path.join(binDir, bin))) {
    fail(`dangling binary link .bin/${bin}`);
  }
}
EOF
  then
    echo "florabase-dev-entrypoint: Quality frontend dependencies are incomplete or out of sync with pnpm-lock.yaml; rebuild or reinitialize Quality state" >&2
    exit 1
  fi
  exec "$@"
fi
export CI=true
pnpm install --frozen-lockfile --prefer-offline
exec "$@"
