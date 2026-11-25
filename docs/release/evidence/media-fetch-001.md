# MEDIA-FETCH-001 — Save local copy for Wikipedia/Wikimedia images

- **Identifier:** `MEDIA-FETCH-001` (category `attachment`, P2, status `implemented`, release class
  `best-effort`).
- **Branch:** `fix/media-fetch-001` from `origin/main` `b632c5c734fdab55e62230cdee99938ae34ece7e`.
- **Writer:** `claude-media-fetch`.
- **Migration / OpenAPI:** none. The rewrite is a Pydantic validator and the response schema is
  unchanged.

## Operator evidence (v0.1.0-beta.9 on the NAS, 2026-11-25)

- `POST /api/v1/media-assets/{id}/save-local-copy` returned 422
  `{"code":"external_fetch_failed","message":"The external image is unavailable. Try again."}`.
- The asset's external URL was a Wikipedia file description page,
  `https://it.wikipedia.org/wiki/File:Unk_desert_flower_2.jpg`.
- From inside the backend container: without a `User-Agent` the request got `403 Forbidden
  text/plain`; with `User-Agent: Florabase/0.1 media-copy` it got `200 OK text/html`.

Two causes: no `User-Agent`, and a file description page (HTML) instead of the image.

## Changes

- `backend/src/florabase/media/fetch.py`
  - `USER_AGENT = "Florabase/<florabase.__version__> media-copy (+https://github.com/alessandrorossato/florabase)"`
    sent with the existing `Accept` on every request, redirects included. No other new headers, no
    cookies or credentials. Pinned public-address sockets, no proxy environment, the redirect limit,
    size, type and encoding checks and the single deadline are unchanged.
  - `wikimedia_file_url(url)`: pure function. An `http(s)` URL on `*.wikipedia.org` or
    `*.wikimedia.org` (no explicit port, no userinfo) whose path is `/wiki/<ns>:<name>` with `ns`
    in `File`, `Image`, `Immagine`, `Datei`, `Fichier`, `Archivo`, `Ficheiro`, `Arquivo`, `Bestand`
    (case-insensitive) becomes `https://<host>/wiki/Special:FilePath/<name>`: the name is decoded,
    spaces become underscores, it is re-encoded with `quote(..., safe="()")`, and query and fragment
    are dropped. Everything else, including `Special:FilePath` and `upload.wikimedia.org`, passes
    through unchanged.
  - `fetch_image` applies the rewrite first, so already-saved references with a `/wiki/File:` URL
    can be copied without editing.
  - A final `200` `text/html` response raises `external_fetch_failed` with "This address is a web
    page, not an image. Use the image's own address." (no destination details).
- `backend/src/florabase/media/schemas.py`: `ExternalAssetCreate.image_url` runs the rewrite after
  HTTPS validation. That covers `POST /media-assets/external` and both collection-photo creation
  paths. `source_url` is a separate, required field that keeps the operator's page URL. The metadata
  edit path (`AssetMetadataWrite`) cannot change `image_url`, so there is no edit path to cover.
- Docs: `docs/media-library.md` (one paragraph), `docs/progress.md`, `docs/features.json`,
  `docs/release/scope-v1.json`.

## Tests (`backend/tests/test_media_fetch.py`)

- `test_user_agent_is_sent_on_first_request_and_after_redirect`
- `test_html_page_has_direct_address_message`
- `test_wikimedia_file_page_is_fetched_through_file_path`
- `test_wikimedia_file_pages_rewrite_to_file_path` (it/en/de/fr/nl/es/pt Wikipedia, mobile host,
  Commons, localized namespaces, encoded and reserved characters, spaces, query and fragment)
- `test_non_wikimedia_file_pages_pass_through` (`Special:FilePath`, `upload.wikimedia.org`, article
  pages, empty name, look-alike hosts, explicit port, `index.php?title=`, non-URLs)
- `test_external_reference_stores_file_path_and_keeps_source_page`
- The existing safety tests are unchanged and still pass: private and reserved addresses, a
  redirect to a private address, too many redirects, wrong types, size, encoding, timeout.

No network access: the tests reuse the module's existing `getaddrinfo` and `_PinnedConnection`
stubs.

## Verification

- Focused (dev quality container): `pytest tests/test_media_fetch.py tests/test_media.py
  tests/test_media_copies.py tests/test_collection_photos.py` gave 99 passed. `ruff check`,
  `ruff format --check` and `mypy` were clean.
- Canonical gate: `make feature-verify` on the frozen tree, run by the operator (the agent's
  Remote Control mode blocks it). The receipt is recorded in the delivery report.

## Batch 13 merge check

`git merge-tree --write-tree` of this tip against `feat/propagation-batch-001`,
`feat/care-bulk-001`, `docs/docs-004-batch12-followups` and `feat/fn-05-directory-sort` (local
refs) is recorded in the delivery report.
