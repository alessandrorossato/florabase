import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

describe("Web App Manifest & PWA Metadata", () => {
  const publicDir = path.resolve(__dirname, "../../public");
  const manifestPath = path.join(publicDir, "manifest.webmanifest");
  const indexPath = path.resolve(__dirname, "../../index.html");

  function expectPngSize(src: string, size: number) {
    const png = fs.readFileSync(path.join(publicDir, src));
    expect(png.subarray(0, 8).toString("hex")).toBe("89504e470d0a1a0a");
    expect(png.readUInt32BE(16)).toBe(size);
    expect(png.readUInt32BE(20)).toBe(size);
  }

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

    expect(parsed.icons).toHaveLength(4);
    for (const purpose of ["any", "maskable"]) {
      for (const size of [192, 512]) {
        const dimensions = `${String(size)}x${String(size)}`;
        const icon = parsed.icons.find(
          (candidate) =>
            candidate.sizes === dimensions && candidate.purpose === purpose,
        );
        expect(icon).toBeDefined();
        if (!icon) throw new Error(`Missing ${dimensions} ${purpose} icon`);
        expect(icon.type).toBe("image/png");
        expectPngSize(icon.src, size);
      }
    }
  });

  it("all required mobile and favicon assets exist on disk", () => {
    expectPngSize("icons/florabase-apple-touch-icon.png", 180);
    expectPngSize("icons/favicon-16x16.png", 16);
    expectPngSize("icons/favicon-32x32.png", 32);
    expect(fs.existsSync(path.join(publicDir, "favicon.ico"))).toBe(true);
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

    expect(html).toMatch(
      /<link[^>]*rel="icon"[^>]*href="\/favicon\.ico\?v=brand-01"/,
    );
    for (const size of ["16x16", "32x32"]) {
      expect(html).toMatch(
        new RegExp(
          `<link[^>]*rel="icon"[^>]*sizes="${size}"[^>]*href="/icons/favicon-${size}\\.png"`,
        ),
      );
    }

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
      /<link[\s\S]*?rel="apple-touch-icon"[\s\S]*?sizes="180x180"[\s\S]*?href="\/icons\/florabase-apple-touch-icon\.png"/,
    );
  });
});
