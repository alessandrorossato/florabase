import { useEffect, useState } from "react";

import { ActionButton } from "../components/Action";
import { watchForNewRelease } from "./releaseWatcher";
import "./update-notice.css";

const UPDATE_MESSAGE =
  "A new version of Florabase is available. Save any open changes, then reload to use it.";

/**
 * Polite, non-blocking notice shown when the server runs a newer Florabase release than the one
 * loaded in this window. Reloading is always the user's choice so unsaved edits are never lost.
 */
export function UpdateNotice({
  watch = watchForNewRelease,
  reload = () => {
    window.location.reload();
  },
}: {
  watch?: typeof watchForNewRelease;
  reload?: () => void;
}) {
  const [available, setAvailable] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(
    () =>
      watch({
        onUpdateAvailable: () => {
          setAvailable(true);
        },
      }),
    [watch],
  );

  const visible = available && !dismissed;

  return (
    <>
      <p className="pwa-update-live" role="status">
        {visible ? UPDATE_MESSAGE : ""}
      </p>
      {visible && (
        <aside className="pwa-update-notice" aria-label="Florabase update">
          <p>{UPDATE_MESSAGE}</p>
          <div className="pwa-update-notice__actions">
            <ActionButton onClick={reload}>Reload now</ActionButton>
            <ActionButton
              variant="quiet"
              onClick={() => {
                setDismissed(true);
              }}
            >
              Later
            </ActionButton>
          </div>
        </aside>
      )}
    </>
  );
}
