import { readFileSync } from "node:fs";
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
  for (const palette of ["botanical", "herbarium", "mineral"]) {
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

test("all six implemented sets meet the approved shared text, state and boundary contrast pairs", () => {
  for (const palette of ["botanical", "herbarium", "mineral"]) {
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
