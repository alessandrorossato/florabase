import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/source-sans-3";
import "@fontsource-variable/source-sans-3/wght-italic.css";
import "@fontsource-variable/source-serif-4";
import "../../styles.css";
import "../../styles/foundation.css";
import "../../styles/normalization.css";
import "../../styles/controls.css";
import { ScheduleUxPrototype } from "./ScheduleUxPrototype";
import { AuthContext } from "../../auth/context";
import { FixtureSchedule, fixtureAuth } from "./fixtures";
import "./prototype.css";

// This entry never mounts App, authenticates, proxies or forwards a request.
const fixture = new FixtureSchedule();
window.fetch = fixture.fetch;
const root = document.getElementById("root");
if (!root) throw new Error("Activity prototype root is missing");
createRoot(root).render(
  <StrictMode>
    <AuthContext.Provider value={fixtureAuth}>
      <ScheduleUxPrototype fixture={fixture} />
    </AuthContext.Provider>
  </StrictMode>,
);
