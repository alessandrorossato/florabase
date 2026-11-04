import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { expect, test } from "vitest";

const tokens = readFileSync("src/styles/tokens.css", "utf8");
const css = readFileSync("src/styles.css", "utf8");
const index = readFileSync("index.html", "utf8");

test("every palette has two complete semantic sets without changing geometry or type", () => {
  const roles = [
    "background",
    "surface",
    "surface-subtle",
    "surface-hover",
    "text",
    "text-muted",
    "border",
    "border-strong",
    "primary",
    "primary-hover",
    "primary-subtle",
    "on-primary",
    "success",
    "warning",
    "warning-text",
    "danger",
    "danger-subtle",
    "warning-subtle",
    "info",
    "focus-ring",
    "overlay-backdrop",
    "elevation-overlay",
  ];
  for (const palette of ["botanical", "herbarium", "mineral", "field-ledger"]) {
    for (const appearance of ["light", "dark"]) {
      const selector = `:root[data-palette="${palette}"][data-appearance="${appearance}"]`;
      const start = tokens.indexOf(selector);
      expect(start).toBeGreaterThan(-1);
      const block = tokens.slice(start).split("}")[0];
      for (const role of roles) expect(block).toContain(`--${role}:`);
      expect(block).toContain(`color-scheme: ${appearance}`);
      expect(block).not.toMatch(/--(?:space|type|font|control-height|radius)-/);
    }
  }
  expect(tokens).toContain("--color-ink: var(--text)");
  expect(tokens).toContain("--accent-strong: var(--primary)");
});

test("blocking bootstrap precedes application code; the public asset remains a classic same-origin script", () => {
  expect(index.indexOf('<script src="/appearance.js"></script>')).toBeLessThan(
    index.indexOf('type="module"'),
  );
  expect(readFileSync("public/appearance.js", "utf8")).not.toMatch(
    /fetch\(|XMLHttpRequest|document\.write|innerHTML/,
  );
});

test("screen palettes cannot change paper, QR geometry, original images or provider density colors", () => {
  const print = tokens.slice(
    tokens.indexOf("@media print"),
    tokens.indexOf("@media (forced-colors"),
  );
  expect(print).toContain("color-scheme: light !important");
  expect(print).toContain("--background: #ffffff");
  expect(print).toContain("--text: #000000");
  const labels = readFileSync("src/labels/labels.css", "utf8");
  const qr = readFileSync("src/labels/LabelQr.tsx", "utf8");
  expect(labels).toContain("background: white");
  expect(qr).toContain('fill="black"');
  expect(qr).toContain('fill="white"');
  expect(css).toMatch(/#5e0063,\s*#a42e61,\s*#d26b63,\s*#eeab79,\s*#ffebaa/);
  expect(css).not.toMatch(/filter:\s*(?:invert|hue-rotate)/);
});

function contrast(first: string, second: string) {
  function luminance(color: string) {
    return [0.2126, 0.7152, 0.0722].reduce((sum, weight, i) => {
      const v = Number.parseInt(color.slice(1 + i * 2, 3 + i * 2), 16) / 255;
      return (
        sum + weight * (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)
      );
    }, 0);
  }
  const values = [luminance(first), luminance(second)].sort((a, b) => a - b);
  return (values[1] + 0.05) / (values[0] + 0.05);
}

test("all six original and two Field Ledger sets meet the approved shared text, state and boundary contrast pairs", () => {
  for (const palette of ["botanical", "herbarium", "mineral", "field-ledger"]) {
    for (const mode of ["light", "dark"]) {
      const selector = `:root[data-palette="${palette}"][data-appearance="${mode}"]`;
      const block = tokens.slice(tokens.indexOf(selector)).split("}")[0];
      const colors = Object.fromEntries(
        [...block.matchAll(/--([a-z-]+): (#[0-9a-f]{6});/g)].map((m) => [
          m[1],
          m[2],
        ]),
      );
      const surfaces = [
        "background",
        "surface",
        "surface-subtle",
        "surface-hover",
        "primary-subtle",
      ];
      for (const surface of surfaces) {
        for (const text of [
          "text",
          "text-muted",
          "primary",
          "info",
          "success",
          "warning-text",
          "danger",
        ]) {
          expect(
            contrast(colors[text], colors[surface]),
            `${palette} ${mode} ${text}/${surface}`,
          ).toBeGreaterThanOrEqual(4.5);
        }
        for (const cue of ["border-strong", "focus-ring", "warning"]) {
          expect(
            contrast(colors[cue], colors[surface]),
            `${palette} ${mode} ${cue}/${surface}`,
          ).toBeGreaterThanOrEqual(3);
        }
      }
      for (const primary of ["primary", "primary-hover"])
        expect(
          contrast(colors["on-primary"], colors[primary]),
        ).toBeGreaterThanOrEqual(4.5);
      expect(
        contrast(colors.danger, colors["danger-subtle"]),
      ).toBeGreaterThanOrEqual(4.5);
      expect(
        contrast(colors["warning-text"], colors["warning-subtle"]),
      ).toBeGreaterThanOrEqual(4.5);
    }
  }
});

function block(selector: string) {
  const start = tokens.indexOf(selector);
  expect(start, selector).toBeGreaterThan(-1);
  return tokens.slice(start).split("}")[0];
}

test("the six UI Foundation themes stay byte-identical to main d94f275", () => {
  const pinned: Record<string, string> = {
    "botanical light":
      "aedad2d5144195729fc67a8e67c5f8c9d09ddc5d2cbb533c2f51de44606deca5",
    "botanical dark":
      "f5d53430ee9e1e6f8d986e4fcc4e6a406268d6ee7549ea000dabab84bc57648d",
    "herbarium light":
      "a10e710e859dbb8c8068a29290ea9aac1e6aed0194d85785bccae14f214e7326",
    "herbarium dark":
      "a82d9cbd13ff2d1f02278044241322f18afec834b8a38ae1b0f4333b0beaea97",
    "mineral light":
      "9a56dbe574dc231d8e14f91d5e220f556cf7d04acf800d52754c3dfc9709743e",
    "mineral dark":
      "458adfb372ed06401fc9810e2ec87fc78865eca485684b5f4143a2acd93ca93b",
  };
  for (const [name, digest] of Object.entries(pinned)) {
    const [palette, appearance] = name.split(" ");
    const text = block(
      `:root[data-palette="${palette}"][data-appearance="${appearance}"]`,
    );
    expect(createHash("sha256").update(text).digest("hex"), name).toBe(digest);
  }
});

test("new system tokens default to UI Foundation geometry, so only Field Ledger changes it", () => {
  const root = block(":root {");
  for (const declaration of [
    "--font-data: var(--font-ui);",
    "--control-height: 2.75rem;",
    "--control-height-touch: 2.75rem;",
    "--focus-ring-width: 3px;",
    "--focus-ring-offset: 3px;",
    "--tracking-heading: normal;",
    "--radius-small: 6px;",
    '--font-ui: "Source Sans 3 Variable", system-ui, sans-serif;',
  ])
    expect(root).toContain(declaration);
});

test("Field Ledger is a complete system: type, data font, radii, focus and pointer-aware controls", () => {
  const system = block(':root[data-palette="field-ledger"],');
  expect(system).toContain('--font-ui: "Instrument Sans Variable"');
  expect(system).toContain('--font-botanical: "Newsreader Variable"');
  expect(system).toContain('--font-data: "IBM Plex Mono"');
  expect(system).toContain(
    "--type-metric: 500 1.75rem/1.1429 var(--font-data);",
  );
  expect(system).toContain("--control-height: 2.5rem;");
  expect(system).toContain("--focus-ring-offset: 2px;");
  for (const role of [
    "display",
    "h1",
    "h2",
    "h3",
    "body",
    "strong",
    "small",
    "label",
    "eyebrow",
  ])
    expect(system).toContain(`--type-${role}:`);
  const touch = tokens.slice(
    tokens.indexOf("@media (max-width: 48rem), (any-pointer: coarse)"),
  );
  expect(touch.split("}")[0]).toContain(
    "--control-height: var(--control-height-touch);",
  );
  for (const mode of ["light", "dark"]) {
    const colors = block(
      `:root[data-palette="field-ledger"][data-appearance="${mode}"]`,
    );
    for (const role of [
      "rail-background",
      "rail-text",
      "rail-active",
      "lineage",
      "lineage-subtle",
    ])
      expect(colors).toContain(`--${role}:`);
    const pick = (role: string) =>
      new RegExp(`--${role}: (#[0-9a-f]{6});`).exec(colors)?.[1] ?? "";
    expect(
      contrast(pick("rail-text"), pick("rail-background")),
    ).toBeGreaterThanOrEqual(4.5);
    expect(
      contrast(pick("rail-text-muted"), pick("rail-background")),
    ).toBeGreaterThanOrEqual(4.5);
    expect(
      contrast(pick("rail-active"), pick("rail-background")),
    ).toBeGreaterThanOrEqual(4.5);
    expect(
      contrast(pick("lineage"), pick("lineage-subtle")),
    ).toBeGreaterThanOrEqual(4.5);
    expect(contrast(pick("lineage"), pick("surface"))).toBeGreaterThanOrEqual(
      4.5,
    );
  }
  // Print and forced colours are declared after Field Ledger, so they still win.
  expect(tokens.indexOf("@media print")).toBeGreaterThan(
    tokens.indexOf(
      ':root[data-palette="field-ledger"][data-appearance="dark"]',
    ),
  );
});

test("Field Ledger fonts are bundled same-origin with shipped OFL licences", () => {
  const main = readFileSync("src/main.tsx", "utf8");
  for (const entry of [
    "@fontsource-variable/instrument-sans/wght.css",
    "@fontsource-variable/newsreader/opsz-italic.css",
    "@fontsource/ibm-plex-mono/400.css",
  ])
    expect(main).toContain(`import "${entry}";`);
  for (const licence of ["instrument-sans", "newsreader", "ibm-plex-mono"]) {
    const path = `public/licenses/${licence}.txt`;
    expect(existsSync(path), path).toBe(true);
    expect(readFileSync(path, "utf8")).toContain(
      "SIL OPEN FONT LICENSE Version 1.1",
    );
  }
  expect(tokens + css + index).not.toMatch(
    /fonts\.(?:googleapis|gstatic)\.com|@import\s+url\(\s*["']?https?:/,
  );
});
