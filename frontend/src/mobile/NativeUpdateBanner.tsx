import { useState } from "react";

import { ActionButton } from "../components/Action";
import { compareSemver } from "./semver";

const GITHUB_RELEASES_URL =
  "https://github.com/alessandrorossato/florabase/releases";

export interface NativeUpdateBannerProps {
  serverVersion: string;
  appVersion: string;
}

/**
 * Native-only non-blocking banner shown when the connected Florabase server is
 * newer than the installed Android APK (`server_version > appVersion`).
 * Replaces the web-only `UpdateNotice` (`/release.json` poller).
 */
export function NativeUpdateBanner({
  serverVersion,
  appVersion,
}: NativeUpdateBannerProps) {
  const [dismissed, setDismissed] = useState(false);

  const serverIsNewer = compareSemver(serverVersion, appVersion) === 1;
  const visible = serverIsNewer && !dismissed;

  const message = `Your server is running Florabase ${serverVersion}, which is newer than this app (${appVersion}). Update the app from Obtainium or GitHub Releases.`;

  return (
    <>
      <p className="native-update-live" role="status">
        {visible ? message : ""}
      </p>
      {visible && (
        <aside
          className="native-update-notice"
          aria-label="Florabase app update"
        >
          <p>{message}</p>
          <div className="native-update-notice__actions">
            <a
              className="button button--primary"
              href={GITHUB_RELEASES_URL}
              target="_blank"
              rel="noopener noreferrer"
            >
              GitHub Releases
            </a>
            <ActionButton
              type="button"
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
