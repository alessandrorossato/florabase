# Frontend lint and format tooling maintenance

## Baseline and selected versions

- Starting `main`: `bc84fa403d09d2ac1f0012ecc43b8ddb0f32d7e7` (PR #86 is present).
- `eslint`: 10.9.1 → 10.12.0.
- `typescript-eslint`: 8.68.0 → 8.71.1.
- `eslint-plugin-react-refresh`: 0.5.5 → 0.5.7.
- `prettier`: 3.9.6 → 3.9.9. Prettier 3.9.10 was published less than the configured
  `minimum-release-age=1440` window ago when versions were refreshed, so this update preserves
  the repository's release-age safeguard rather than adding an allowlist exception.

All four selected packages are development tooling. Node 24.19.0, `>=24 <25`, pnpm 11.19.0,
TypeScript 5.9.3, and the existing React/Vite stack remain unchanged. ESLint 10.12 supports
Node `^20.19.0 || ^22.13.0 || >=24`; typescript-eslint 8.71.1 supports Node
`^18.18.0 || ^20.9.0 || >=21.1.0`, ESLint 8.57/9/10, and TypeScript `>=4.8.4 <6.1.0`.
The React Refresh plugin accepts ESLint 9/10. Prettier 3.9.9 supports this Node 24 runtime.

ESLint and typescript-eslint use minor releases; React Refresh and Prettier use patch releases.
ESLint 10.12 adds token/comment support to SourceCode type definitions and includes rule bug fixes;
lint on the unchanged source passed without new findings.
typescript-eslint's current compatibility matrix includes the repository's exact ESLint and
TypeScript versions; strict typecheck passed. The React Refresh plugin's ESLint peer range includes
ESLint 10, with no config migration required. Prettier's 3.9.9 release contains a Markdown `$`
math-detection fix; the new formatter check found no source formatting changes. Official notes:
[ESLint 10.12](https://eslint.org/blog/2026/10/eslint-v10.12.0-released/),
[typescript-eslint compatibility](https://typescript-eslint.io/users/dependency-versions/), and
[Prettier releases](https://github.com/prettier/prettier/releases).

## Lockfile and configuration

The only direct dependency declarations changed are the four packages above. The pnpm lockfile
updates their importer entries and the aligned typescript-eslint packages. ESLint's required
transitive graph changes include `@eslint/plugin-kit` 0.7.2 → 0.7.3 and the `file-entry-cache`
8.0.0 → 11.1.5 / `flat-cache` 4.0.1 → 6.1.23 chain, including its new cacheable/keyv support
packages. These are package-manager-resolved ESLint dependencies; no unrelated direct dependency
changed. `pnpm install --frozen-lockfile` passed. There is no workspace release-age exception,
lockfile hand-edit, ESLint/Prettier configuration change, application source change, or backend
dependency change.

Unchanged direct packages include `@eslint/js`, `eslint-plugin-react-hooks`, TypeScript, React and
React types, Vite and its React plugin, jsdom, `@types/node`, the previously delivered Leaflet and
user-event packages, and all backend dependencies.

## Verification evidence

- Prettier 3.9.9 `--check .`: all matched files formatted; no application source reformatting.
- ESLint `--max-warnings 0`: passed with no new diagnostics or warnings.
- TypeScript strict project check (`tsc -b --pretty false`): passed.
- Frozen install: passed.
- Frontend Vitest: 557 tests passed across 57 files.
- `make verify-build SERVICES=frontend`: production frontend image built; its owned disposable
  project removed its image and had zero residual containers, networks, or volumes.
- Synthetic UAT smoke used a unique worktree-owned project. Owner login succeeded; the authenticated
  Dashboard shell and Plants page rendered seeded synthetic records. The project removed its
  four containers, two images, network, and three volumes; no residual disposable resources remain.
  DEV, Feature Review, UAT Preview, Stable Preview, production, and other Docker projects were not
  targeted.
- `make verification-plan FORMAT=json`: **FULL**, escalated because `frontend/package.json` and
  `frontend/pnpm-lock.yaml` are high-risk paths. It selects all backend, frontend, and integration
  suites, both builds, a full migration cycle, and the FULL workflow/static checks.
- `git diff --check`: passed.

No application source or tooling configuration repair was needed. No package group outside lint and
format tooling was added. React/React DOM and matching types, Vite/plugin-react, jsdom, and the
remaining Dependabot #46 proposals are deferred; #46 and #24 were not modified. The next intended
batch is frontend React/Vite runtime/build tooling, after this batch's independent review and
delivery. This worktree remains unstaged and uncommitted for Luna's canonical verification.
