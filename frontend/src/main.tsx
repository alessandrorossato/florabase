import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App.tsx";
import { trackInputModality } from "./focusModality";
import { isNativeShell } from "./mobile/runtime";
import { registerServiceWorker } from "./pwa/registerServiceWorker";
import { UpdateNotice } from "./pwa/UpdateNotice";
import "leaflet/dist/leaflet.css";
import "@fontsource-variable/source-sans-3";
import "@fontsource-variable/source-sans-3/wght-italic.css";
import "@fontsource-variable/source-serif-4";
import "@fontsource-variable/source-serif-4/wght-italic.css";
// Field Ledger (Florabase Next). Same-origin WOFF2; each face loads only when a palette uses it.
import "@fontsource-variable/instrument-sans/wght.css";
import "@fontsource-variable/instrument-sans/wght-italic.css";
import "@fontsource-variable/newsreader/opsz.css";
import "@fontsource-variable/newsreader/opsz-italic.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "./styles.css";
import "./styles/foundation.css";
import "./styles/normalization.css";
import "./styles/controls.css";
// Workbench shell after global sheets, before lazily loaded page CSS.
import "./shell/workbench.css";

const root = document.getElementById("root");

if (root === null) {
  throw new Error("Application root element is missing");
}

trackInputModality();
if (isNativeShell()) {
  const reactRoot = createRoot(root);
  void import("./mobile/NativeApp")
    .then(({ NativeApp }) => {
      reactRoot.render(
        <StrictMode>
          <NativeApp />
        </StrictMode>,
      );
    })
    .catch(() => {
      reactRoot.render(
        <main className="card" role="alert">
          <h1>Florabase failed to start</h1>
          <p>
            Close and reopen the app. If the problem persists, reinstall the
            latest Florabase APK.
          </p>
        </main>,
      );
    });
} else {
  void registerServiceWorker();
  createRoot(root).render(
    <StrictMode>
      <App />
      <UpdateNotice />
    </StrictMode>,
  );
}
