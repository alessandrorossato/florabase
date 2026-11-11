import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

describe("Web App Manifest & PWA Metadata", () => {
  const publicDir = path.resolve(__dirname, "../../public");
  const manifestPath = path.join(publicDir, "manifest.webmanifest");
  const indexPath = path.resolve(__dirname, "../../index.html");

  it("manifest.webmanifest exists and contains valid JSON", () => {
    expect(fs.existsSync(manifestPath)).toBe(true);
    const content = fs.readFileSync(manifestPath, "utf-8");
    const parsed = JSON.parse(content) as Record<string, unknown>;

    expect(parsed.name).toBe("Florabase");
    expect(parsed.short_name).toBe("Florabase");
    expect(parsed.start_url).toBe("/");
    expect(parsed.scope).toBe("/");
    expect(parsed.display).toBe("standalone");
    expect(parsed.theme_color).toBe("#153a2c");
    expect(parsed.background_color).toBe("#153a2c");
    expect(Array.isArray(parsed.icons)).toBe(true);
  });

  it("manifest includes required icons with standard and maskable purposes", () => {
    const content = fs.readFileSync(manifestPath, "utf-8");
    const parsed = JSON.parse(content) as {
      icons: { src: string; sizes: string; type: string; purpose?: string }[];
    };

    const icon192 = parsed.icons.find(
      (icon) => icon.sizes === "192x192" && icon.purpose === "any",
    );
    expect(icon192).toBeDefined();
    if (icon192 === undefined) throw new Error("192x192 icon missing");
    expect(fs.existsSync(path.join(publicDir, icon192.src))).toBe(true);

    const icon512 = parsed.icons.find(
      (icon) => icon.sizes === "512x512" && icon.purpose === "any",
    );
    expect(icon512).toBeDefined();
    if (icon512 === undefined) throw new Error("512x512 icon missing");
    expect(fs.existsSync(path.join(publicDir, icon512.src))).toBe(true);

    const maskable192 = parsed.icons.find(
      (icon) => icon.sizes === "192x192" && icon.purpose === "maskable",
    );
    expect(maskable192).toBeDefined();
    if (maskable192 === undefined)
      throw new Error("192x192 maskable icon missing");
    expect(fs.existsSync(path.join(publicDir, maskable192.src))).toBe(true);

    const maskable512 = parsed.icons.find(
      (icon) => icon.sizes === "512x512" && icon.purpose === "maskable",
    );
    expect(maskable512).toBeDefined();
    if (maskable512 === undefined)
      throw new Error("512x512 maskable icon missing");
    expect(fs.existsSync(path.join(publicDir, maskable512.src))).toBe(true);
  });

  it("all required mobile and favicon assets exist on disk", () => {
    expect(
      fs.existsSync(path.join(publicDir, "icons/apple-touch-icon.png")),
    ).toBe(true);
    expect(fs.existsSync(path.join(publicDir, "icons/icon.svg"))).toBe(true);
    expect(fs.existsSync(path.join(publicDir, "favicon.ico"))).toBe(true);
    expect(fs.existsSync(path.join(publicDir, "favicon.svg"))).toBe(true);
    expect(fs.existsSync(path.join(publicDir, "offline.html"))).toBe(true);
    expect(fs.existsSync(path.join(publicDir, "offline.css"))).toBe(true);
    expect(fs.existsSync(path.join(publicDir, "offline.js"))).toBe(true);
    expect(fs.existsSync(path.join(publicDir, "sw.js"))).toBe(true);
  });

  it("index.html references manifest, icons and iOS mobile meta tags", () => {
    const html = fs.readFileSync(indexPath, "utf-8");

    // Manifest link
    expect(html).toContain('rel="manifest"');
    expect(html).toContain('href="/manifest.webmanifest"');

    // Theme color
    expect(html).toMatch(/<meta[^>]*name="theme-color"[^>]*content="#153a2c"/);

    // Favicon and vector icon links
    expect(html).toMatch(/<link[^>]*rel="icon"[^>]*href="\/favicon\.svg"/);
    expect(html).toMatch(
      /<link[\s\S]*?rel="icon"[\s\S]*?sizes="192x192"[\s\S]*?href="\/icons\/icon-192\.png"/,
    );
    expect(html).toMatch(
      /<link[\s\S]*?rel="alternate icon"[\s\S]*?href="\/favicon\.ico"/,
    );

    // iOS Add to Home Screen support
    expect(html).toMatch(
      /<meta[^>]*name="mobile-web-app-capable"[^>]*content="yes"/,
    );
    expect(html).toMatch(
      /<meta[^>]*name="apple-mobile-web-app-capable"[^>]*content="yes"/,
    );
    expect(html).toMatch(
      /<meta[^>]*name="apple-mobile-web-app-title"[^>]*content="Florabase"/,
    );
    expect(html).toMatch(
      /<link[\s\S]*?rel="apple-touch-icon"[\s\S]*?sizes="180x180"[\s\S]*?href="\/icons\/apple-touch-icon\.png"/,
    );
  });
});
