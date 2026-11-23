# UI-REVIEW-002 evidence

- Branch `fix/plants-list-reference-mount` from `origin/main` `ddf5a14` (writer `claude-batch13-impl`),
  prepared as the fourth Batch 12 source. No migration.
- Directory cards: `.app-content .ui-directory-records--gallery` used `repeat(auto-fit, …)`, which
  collapses empty tracks, so a single Plants record spanned the page (1022 × 1158 px at 1440 px).
  `auto-fill` keeps the tracks: one, three and twelve records now share the 244 px card width.
- WFO suggestions: read-only `GET /api/v1/explore/taxonomy/candidates?q=` (`searchWfoNames`) reuses
  `WfoSource.search` without an identity; the create form's scientific-name input offers the names
  through a native `datalist`, debounced, from two characters. OpenAPI and TypeScript declarations
  regenerated.
- Reference indexes: `compose.yaml` gains commented `FLORABASE_WFO_SNAPSHOT_PATH`,
  `FLORABASE_WCVP_V16_SNAPSHOT_PATH` and a `:ro` mount of the host `reference` folder at
  `/var/lib/florabase/reference` (47 lines, within the 50-line contract); `docs/installation.md`
  explains how to enable them. `docker compose config` passes both commented and uncommented.
- Media: the identity Media tab shows the cover with a compact caption and visible actions, and record
  photos as a thumbnail grid with owner chips; the empty state links to the records. External covers
  default to saving a local copy (the identity cover form was the path without that choice), and an
  unsaved external cover offers Save local copy in place. The media asset page names the asset by its
  title, filename or attribution, shows a status badge, and for unsaved references puts Save local
  copy first above a compact preview. Licence and local-copy settings in Settings stay out of scope.
- Checks: backend `pytest tests/test_taxonomy_api.py`, ruff, ruff format, mypy on `taxonomy`;
  frontend typecheck, ESLint, Prettier and Vitest on `botanical-identities`, `media`, `photos`,
  `taxonomy`, `UX001`, `UX004` (30 files, 190 tests). Before/after screenshots at 1440 and 390 px
  (and dark mode) were captured against mocked APIs and attached to the review thread, not committed.
- Follow-up after review and operator feedback: at 1440 × 900 both the identity Media tab and an
  unsaved external media asset page fit one screen (document height 900 px): smaller cover and
  thumbnails, Local copy above Details in the side column, Linked records and Covers side by side
  and a one-row delete section. Invalid image URLs no longer throw in the Local copy text, WFO
  suggestions follow a form reset, and thumbnails keep their Image source link.
