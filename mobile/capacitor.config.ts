import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "io.github.alessandrorossato.florabase",
  appName: "Florabase",
  webDir: "../frontend/dist",
  // Disable Capacitor bridge argument logging so plugin calls like SecureToken.set
  // never print Bearer tokens to Android logcat (even in debug builds).
  loggingBehavior: "none",
  server: {
    androidScheme: "https",
  },
  android: {
    allowMixedContent: false,
  },
};

export default config;
