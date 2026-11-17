# CERT-04 · UI scaffold gate evidence

Base `836bf80305a19fdd7f49845b8bc00ae423553a93`. Source
`ci/cert-04-ui-scaffold-gate`, writer `sol-batch03-c121`.

## UI-SYSTEM-001 criterion 5

- `make test-ui-page` runs `scripts/test_ui_page.py` in local FULL, required remote FULL
  quality and `make ci`. The existing workflow stage order includes this check ahead of
  container stages.
- `make verify-build` checks the actual production artifact whenever the selected services
  include frontend. Local affected, product and FULL use that target, as do the required remote
  build job and `make ci`. The backend-only build skips the frontend check.
- The build uses the locally built, positively labelled frontend image. A stopped container on
  the disabled network exposes its Nginx document root to `docker cp`. The existing owned
  disposable lifecycle retires the container and image, and the configuration temporary
  directory also holds the copied artifact.

## Focused verification

- `make test-ui-page` passed all 3 existing scaffold tests.
- `GITHUB_ACTIONS=true make test-verification-impact` passed impact, stage evidence and
  feature-graph regressions. New coverage pins local and remote selection, exercises the Make
  target against a deliberately failing scaffold test, and verifies frontend-only build-check
  invocation, successful validation, failure propagation and temporary directory cleanup.
- `GITHUB_ACTIONS=true make test-feature-workflow` passed 54 tests.
- Scoped Ruff lint and formatting, strict mypy for the changed workflow implementations,
  and `git diff --check` passed. `make verification-plan` selected FULL.
- `make verify-build SERVICES=frontend` accepted the original production artifact and retired
  one owned container and one owned image with zero residual containers, networks, volumes or
  retained owned images.
- A scratch copy added `import "./ui-lab/lab.css";` to `frontend/src/main.tsx`. The same
  isolated build command built the image, then failed with `UI lab content in production build`.
  Cleanup again verified the removal of one owned container and one owned image with zero
  residual containers, networks, volumes or retained owned images.

The independent QA record in the Batch 03 coordination package identifies the exact frozen Git
commit. The combined batch requires a fresh canonical FULL.
