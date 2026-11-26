import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";

import react from "@vitejs/plugin-react";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";

const packageJson = JSON.parse(
  readFileSync(new URL("./package.json", import.meta.url), "utf8"),
) as { version?: string };
const appVersion =
  typeof packageJson.version === "string" && packageJson.version.trim() !== ""
    ? packageJson.version.trim()
    : "0.0.0";

const parsedMaxWorkers = Number.parseInt(
  process.env.VITEST_MAX_WORKERS ?? "",
  10,
);
const maxWorkers =
  Number.isInteger(parsedMaxWorkers) && parsedMaxWorkers > 0
    ? parsedMaxWorkers
    : 3;

/**
 * The production image serves /LICENSE and /THIRD_PARTY_NOTICES.txt as static files (see the
 * Dockerfile). The development server would otherwise answer them with the app, so the About
 * page's licence links serve the same texts in DEV and UAT. Notices are generated once, lazily.
 */
function licenceFiles(): Plugin {
  let notices: string | undefined;
  return {
    name: "florabase-licence-files",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use((request, response, next) => {
        const path = (request.url ?? "").split("?", 1)[0];
        let body: string;
        try {
          if (path === "/LICENSE")
            body = readFileSync(new URL("./LICENSE", import.meta.url), "utf8");
          else if (path === "/THIRD_PARTY_NOTICES.txt")
            body = notices ??= execFileSync(
              process.execPath,
              ["build-notices.mjs"],
              {
                cwd: new URL(".", import.meta.url),
                encoding: "utf8",
                maxBuffer: 64 * 1024 * 1024,
              },
            );
          else {
            next();
            return;
          }
        } catch (error) {
          next(error);
          return;
        }
        response.setHeader("Content-Type", "text/plain; charset=utf-8");
        response.end(body);
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), licenceFiles()],
  define: {
    __FLORABASE_APP_VERSION__: JSON.stringify(appVersion),
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.BACKEND_PROXY_URL ?? "http://backend:8000",
        changeOrigin: false,
      },
    },
  },
  test: {
    environment: "jsdom",
    fileParallelism: true,
    pool: "forks",
    maxWorkers,
    setupFiles: "./src/test/setup.ts",
    testTimeout: 15_000,
    coverage: {
      provider: "v8",
    },
  },
});
