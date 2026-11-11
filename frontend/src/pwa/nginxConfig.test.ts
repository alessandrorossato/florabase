import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

describe("Nginx PWA Configuration", () => {
  const nginxConfPath = path.resolve(__dirname, "../../nginx.conf");
  const nginxContent = fs.readFileSync(nginxConfPath, "utf-8");

  it("serves service worker without caching", () => {
    expect(nginxContent).toContain("location = /sw.js {");
    expect(nginxContent).toContain(
      'add_header Cache-Control "no-cache, no-store, must-revalidate";',
    );
    expect(nginxContent).toContain("default_type application/javascript;");
  });

  it("serves manifest with application/manifest+json and no-cache", () => {
    expect(nginxContent).toContain("location = /manifest.webmanifest {");
    expect(nginxContent).toContain("default_type application/manifest+json;");
    expect(nginxContent).toContain('add_header Cache-Control "no-cache";');
  });

  it("serves offline fallback page, stylesheet and script with no-cache", () => {
    expect(nginxContent).toContain("location = /offline.html {");
    expect(nginxContent).toContain("location = /offline.css {");
    expect(nginxContent).toContain("location = /offline.js {");
    expect(nginxContent).toContain("default_type text/html;");
    expect(nginxContent).toContain("default_type text/css;");
    expect(nginxContent).toContain('add_header Cache-Control "no-cache";');
  });

  it("serves /icons/ and favicons with 1-day public caching", () => {
    expect(nginxContent).toContain("location /icons/ {");
    expect(nginxContent).toContain("location = /favicon.ico {");
    expect(nginxContent).toContain("location = /favicon.svg {");
    expect(nginxContent).toContain(
      'add_header Cache-Control "public, max-age=86400";',
    );
  });

  it("serves index.html with no-cache so bundle updates are discovered immediately", () => {
    expect(nginxContent).toContain("location = /index.html {");
    expect(nginxContent).toContain('add_header Cache-Control "no-cache";');
  });
});
