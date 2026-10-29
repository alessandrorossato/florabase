import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/source-sans-3";
import "@fontsource-variable/source-sans-3/wght-italic.css";
import "@fontsource-variable/source-serif-4";
import "@fontsource-variable/source-serif-4/wght-italic.css";
import "../styles.css";
import "../styles/foundation.css";
import "../styles/normalization.css";
import "../styles/controls.css";
import { Lab } from "./Lab";
import "./lab.css";

const root = document.getElementById("root");
if (!root) throw new Error("UI lab root is missing");
createRoot(root).render(
  <StrictMode>
    <Lab />
  </StrictMode>,
);
