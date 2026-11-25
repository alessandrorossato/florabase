# MEDIA-SETTINGS-001 — Settings → Media defaults

- **Identifier:** `MEDIA-SETTINGS-001` (category `attachment`, P2, status `implemented`, proposed
  release class `best-effort`).
- **Branch:** `feat/media-settings-001` from `ci/batch-13` `756a3c86e4b2de549de3eca9c6d20c9ae26654d5`
  (Batch 13 is not yet on `main` and owns migration `20261125_0049`, which this change chains after).
- **Writer:** `claude-media-settings`.
- **Operator decision (2026-11-25):** approved the design note: (1) the local-copy setting only
  pre-selects the form choice, no automatic fetch; (2) default attribution/licence prefill only the
  owner's own uploads; (3) store in PostgreSQL with a migration rather than per-browser storage.

## Changes

- **Migration** `backend/alembic/versions/20261125_0050_media_settings.py` (`down_revision =
  "20261125_0049"`): adds to `application_settings` `media_save_local_copy_default BOOLEAN NOT NULL
  DEFAULT true`, `media_default_attribution VARCHAR(2000)`, `media_default_licence_label
  VARCHAR(2000)` and `media_default_licence_url VARCHAR(2048)`. Existing installations keep today's
  pre-checked choice and no prefill. No backfill, no data rewrite. Downgrade drops only these four
  preference columns; no media asset or collection record changes.
- **API** (`/api/v1/application-settings`, OpenAPI regenerated): the four fields are required members
  of the existing full-replace `ApplicationSettingsValue`, so a stale client cannot silently reset
  them. Text is normalized with the shared media `normalize_text` (blank → null, control characters
  refused); the licence URL uses the shared `validate_https_url`. Frontend writers (Labels, QR
  dialog, Settings → Media) already spread the latest settings before saving.
- **Uploads:** `POST /api/v1/media-assets/local` and
  `POST /api/v1/collection-records/{type}/{id}/photos/local` accept optional `licence_label` and
  `licence_url` form fields validated through `AssetMetadataWrite`; an invalid licence URL returns
  422 before any storage write.
- **UI:** new **Settings → Media** page (`#/media-settings`, Settings navigation, `gallery`
  pictogram) with loading, load-failure/retry, validation-failure (edits retained) and success
  states. `ExternalCopyChoice` (Media, Photos, identity cover) starts from the saved default, using the
  built-in pre-checked default while loading or when the read fails. The Media library upload form
  and record Photos upload form prefill attribution, licence label and licence URL from the defaults
  and now show licence fields for uploads; external references and edits are never prefilled.
- **Docs:** `docs/security.md`, `docs/media-library.md`, `docs/features.json`,
  `docs/release/scope-v1.json`, `docs/progress.md`; golden baselines in
  `scripts/fixtures/golden/scenarios.json` (see below).

## Privacy contract

Unchanged. The setting is a form default only: Florabase fetches an external image only on the
owner's explicit save with the choice selected (or explicit Save/Refresh local copy). Nothing fetches
in the background, on import or on migration.

## Golden baselines

Migration `20261125_0050` changes `schema_revision` (`20261125_0049` → `20261125_0050`) and the
`application_settings` table digest (new default columns on the single row) for `smoke` and
`comprehensive`, and therefore each profile's `canonical_sha256`. No other table digest or row count
changed.

## Checks run on the working tree

| Check | Result |
| --- | --- |
| `make test-backend` | 1428 passed, 3 skipped, coverage 90.19% |
| `./scripts/test-integration.sh` application settings, settings migration, attachment API | 21 passed |
| `git merge-tree` against `feat/about-001` `e517901`, `feat/import-002-sheet-wizard` `c2a507f`, `feat/ref-setup-001` `e17a318`, `feat/ux-sort-002` `e32b57f` | only additive `docs/progress.md` conflicts; `docs/installation.md` vs REF-SETUP-001 is pre-existing between `ci/batch-13` and that branch |
| `make golden-dataset-check` | 35 passed after the baseline update (before it, only `schema_revision`, `application_settings` and the canonical digest differed) |
| `make golden-dataset-comprehensive-check` | 29 passed after the baseline update (before it, every table digest matched; only the canonical digest differed) |
| `make test-frontend` | 141 files, 1482 tests passed |
| `make lint`, `make typecheck`, `make format` | clean |
| `make api-generate` | regenerated `backend/openapi.json` and `frontend/src/api/schema.d.ts` |
| `python3 scripts/check-features.py` | 194 features valid |

New tests: `backend/tests/test_application_settings.py` (normalization, required fields, invalid
values), `backend/tests/integration/test_application_settings.py` (persistence, other preferences
preserved, 422 without partial write), `backend/tests/integration/test_application_settings_migration.py`
(upgrade defaults), `backend/tests/integration/test_attachment_api.py`
(`test_local_uploads_accept_licence_metadata`), `frontend/src/settings/MediaSettingsScreen.test.tsx`,
and updated `PhotosSection`/`BotanicalIdentityCover`/`WorkbenchShell` tests.

The canonical FULL gate (`make feature-verify`) is run by the operator; this file records only the
checks above.

## Not done

- The identity cover local upload has no attribution field today, so no default applies there.
- README's Settings summary line and the Settings workspace `summary` string in
  `frontend/src/shell/navigation.ts` are left unchanged to avoid conflicts with `ABOUT-001`, which
  edits the same lines in Batch 14; add "Media" there during batch integration.
- No unsaved-changes departure guard on Settings → Media (single save button, edits retained on
  failure).
