import { useId, useState, type ReactNode } from "react";
import "./maps.css";

/** Presentation only: callers retain their own data, selection and evidence contracts. */
export function MapWorkspace({
  children,
  browser,
  browserLabel,
}: {
  children: ReactNode;
  browser?: ReactNode;
  browserLabel?: string;
}) {
  const id = useId();
  const [pane, setPane] = useState<"map" | "browser">("map");
  return (
    <div
      className={`maps-workspace${browser ? "" : " maps-workspace--canvas"}`}
      data-pane={pane}
    >
      {browser && (
        <div
          className="maps-pane-switch"
          role="group"
          aria-label="Map workspace view"
        >
          <button
            type="button"
            aria-pressed={pane === "map"}
            aria-controls={`${id}-map`}
            className="button--secondary"
            onClick={() => {
              setPane("map");
            }}
          >
            Map & evidence
          </button>
          <button
            type="button"
            aria-pressed={pane === "browser"}
            aria-controls={`${id}-browser`}
            className="button--secondary"
            onClick={() => {
              setPane("browser");
            }}
          >
            {browserLabel}
          </button>
        </div>
      )}
      <div id={`${id}-map`} className="maps-workspace__main">
        {children}
      </div>
      {browser && (
        <div id={`${id}-browser`} className="maps-workspace__browser">
          {browser}
        </div>
      )}
    </div>
  );
}
