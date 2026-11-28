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
  plugins: {
    LocalNotifications: {
      smallIcon: "ic_stat_florabase",
      iconColor: "#153A2C",
    },
  },
};

export default config;
