# ABOUT-001 evidence

- Branch `feat/about-001` from `origin/main` `b632c5c` (writer `claude-about-001`), prepared for
  Batch 14. Frontend and documentation only: no backend, OpenAPI, migration, Compose or image change.
  Proposed release class: `best-effort` (registered in `docs/release/scope-v1.json`).
- Settings → About (`#/about`): reads the `/release.json` every production frontend image already
  publishes (`version`, `revision`, `source`, written by `frontend/Dockerfile`) through the
  exported `fetchReleaseInfo` that the update watcher now shares. The revision is shortened like the
  startup banner (`FLORABASE_REVISION`: 7 lower-case hex characters, otherwise the raw value). Without
  release metadata (development servers, the native app bundle) it shows the build version
  (`__FLORABASE_APP_VERSION__`) and "Development build (no release metadata)".
- Links: the project repository (an `https://` `source` from metadata, else
  `https://github.com/alessandrorossato/florabase`), `CHANGELOG.md` at tag `v<version>` and the
  GitHub release for that tag, the bundled `/LICENSE` (AGPL-3.0-or-later) and
  `/THIRD_PARTY_NOTICES.txt` that nginx already serves in the production frontend image. External links
  open in a new tab with `rel="noopener noreferrer"`. The changelog is linked, not bundled: the
  frontend build context is `frontend/`, which does not contain the root `CHANGELOG.md`.
- Settings → Data sources: new "Official site" column. URLs are the ones the repository already
  cites: WFO `https://www.worldfloraonline.org/` and its 2026-06 release
  `https://doi.org/10.5281/zenodo.20782718`; Kew WCVP `https://powo.science.kew.org/about-wcvp` and
  `https://sftp.kew.org/pub/data-repositories/WCVP/`; GBIF `https://www.gbif.org/`; Natural Earth
  `https://www.naturalearthdata.com/`; OpenStreetMap `https://www.openstreetmap.org/copyright`
  (attribution and ODbL page). The CSV row keeps only its in-app link.
- Navigation: `about` section, Settings destination after Help (icon `monitor`), lazy chunk in
  `App.tsx`; the shell destination test lists it.
- Checks: Vitest `src/settings src/shell src/pwa src/App.test.tsx src/App.lazy.test.tsx` (15 files,
  251 tests, including 4 new in `src/settings/AboutAndSourceLinks.test.tsx`), `pnpm typecheck`,
  `pnpm lint`, `prettier --check src`, `python3 scripts/check-features.py`.
- Not checked: the links against a production image in a browser (the `/LICENSE` and
  `/THIRD_PARTY_NOTICES.txt` paths exist only in the built image; dev servers answer with the app).
- Batch 14 overlap with `feat/ref-setup-001` (`1edf5fa`): `DataSourcesScreen.tsx` edits were placed
  away from its hunks and the new tests live in a new file instead of `HelpAndSources.test.tsx`;
  see the merge-tree result recorded in the thread handoff.
