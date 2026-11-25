import { readFileSync } from "node:fs";

import react from "@vitejs/plugin-react";
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

export default defineConfig({
  plugins: [react()],
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
