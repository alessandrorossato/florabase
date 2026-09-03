import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
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
    fileParallelism: false,
    setupFiles: "./src/test/setup.ts",
    testTimeout: 15_000,
    coverage: {
      provider: "v8",
    },
  },
});
