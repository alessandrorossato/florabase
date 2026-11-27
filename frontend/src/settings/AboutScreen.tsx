import { useEffect, useState } from "react";

import { PageHeader } from "../components/ReferenceUI";
import { Page } from "../components/WorkspaceUI";
import { fetchReleaseInfo, type ReleaseInfo } from "../pwa/releaseWatcher";
import "./settings.css";

export const PROJECT_URL = "https://github.com/alessandrorossato/florabase";

/** Same short form as the container startup banner. */
function shortRevision(revision: string): string {
  return /^[0-9a-f]{8,64}$/i.test(revision)
    ? revision.slice(0, 7).toLowerCase()
    : revision || "not recorded";
}

/** Settings → About: running release, changelog, licence and project link. */
export function AboutScreen() {
  // undefined while loading; null when the server publishes no /release.json (development).
  const [release, setRelease] = useState<ReleaseInfo | null | undefined>();

  useEffect(() => {
    let active = true;
    void fetchReleaseInfo().then((info) => {
      if (active) setRelease(info);
    });
    return () => {
      active = false;
    };
  }, []);

  const version = release?.version ?? __FLORABASE_APP_VERSION__;
  // Only an https source from the image metadata replaces the canonical project URL.
  const project = release?.source.startsWith("https://")
    ? release.source.replace(/\/+$/, "")
    : PROJECT_URL;
  const tag = `v${version}`;

  return (
    <Page className="settings-workspace" titleId="about-heading">
      <PageHeader
        title="About"
        titleId="about-heading"
        eyebrow="Settings"
        description="Which Florabase release is running, what changed, and under which licence."
      />
      <div className="settings-content">
        <section className="settings-panel" aria-labelledby="about-release">
          <h3 id="about-release">Release</h3>
          <dl className="help-concepts">
            <dt>Version</dt>
            <dd>Florabase {version}</dd>
            <dt>Image revision</dt>
            <dd>
              {release === undefined ? (
                <span role="status">Checking…</span>
              ) : release === null ? (
                "Development build (no release metadata)"
              ) : (
                <code>{shortRevision(release.revision)}</code>
              )}
            </dd>
            <dt>Project</dt>
            <dd>
              <a href={project} target="_blank" rel="noopener noreferrer">
                {project}
              </a>
            </dd>
          </dl>
        </section>
        <section className="settings-panel" aria-labelledby="about-changes">
          <h3 id="about-changes">What changed</h3>
          <ul>
            <li>
              <a
                href={`${project}/blob/${tag}/CHANGELOG.md`}
                target="_blank"
                rel="noopener noreferrer"
              >
                Changelog for {tag}
              </a>
            </li>
            <li>
              <a
                href={`${project}/releases/tag/${tag}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                Release notes for {tag}
              </a>
            </li>
          </ul>
        </section>
        <section className="settings-panel" aria-labelledby="about-licence">
          <h3 id="about-licence">Licence</h3>
          <p>
            Florabase is free software under the GNU Affero General Public
            License, version 3 or later (AGPL-3.0-or-later).
          </p>
          <ul>
            <li>
              <a href="/LICENSE" target="_blank" rel="noopener noreferrer">
                Licence text
              </a>
            </li>
            <li>
              <a
                href="/THIRD_PARTY_NOTICES.txt"
                target="_blank"
                rel="noopener noreferrer"
              >
                Third-party notices
              </a>
            </li>
          </ul>
        </section>
      </div>
    </Page>
  );
}
