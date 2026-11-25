# DOCS-004 evidence

- **Branch:** `docs/docs-004-batch12-followups`, originally from `origin/main`
  `1a7847612d3d77a292ab0dd841ee85371308f268`; `origin/main`
  `b632c5c734fdab55e62230cdee99938ae34ece7e` (beta.9 and MOBILE-002) merged in with merge commit
  `69b5547042bfd0a96c7dd49e2792466ff50e3c8f` (new base `b632c5c`).
- **Writer:** `antigravity-neon`, taken over by the operator for `claude-batch13` to integrate the
  new base.
- **Feature:** `DOCS-004` (`implemented`; proposed release class `best-effort` in
  [`docs/release/scope-v1.json`](../scope-v1.json), registered next to `DOCS-003`, not at the tail)
- **Tested commit:** `69b5547042bfd0a96c7dd49e2792466ff50e3c8f` (merge of the new base before
  updating this evidence; final frozen tip verified by canonical
  `make feature-verify AGENT_ID=claude-batch13`). The original doc fixes were tested at
  `ae69dc4e1a4fefad06d356d72fabdee31e1c0c04`.

## Merge with the new base

The merge conflicted in two documentation files only, resolved without other content changes:

- `docs/release/scope-v1.json`: every `origin/main` entry kept (including `"MOBILE-002": "post-1.0"`
  at the tail) plus `"DOCS-004": "best-effort"` directly above `"DOCS-003"`.
- `docs/progress.md`: every `origin/main` milestone kept, with the DOCS-004 milestone directly below
  the `# Engineering progress` heading.

## Changes

1. **Fix 1 — `WF-BATCH-PROGRESS-001` ordering wording ([`docs/features.json`](../../features.json)):**
   - Replaced `"…are both retained newest-merged first"` with
     `"…are both retained in merge order below the heading"` in the first acceptance criterion of
     `WF-BATCH-PROGRESS-001`, matching `scripts/feature_batch.py` `additive_progress()`
     (`prefix + other_prefix + common + suffix + other_suffix`).
   - Checked `docs/development-workflow.md` and [`docs/progress.md`](../../progress.md) for the same
     wording; neither contained it. Left historic batch manifests under
     `docs/release/evidence/batches/` untouched.
2. **Fix 2 — Reference-index YAML snippet ([`docs/installation.md`](../../installation.md)):**
   - Updated the sentence before the YAML snippet under *Optional botanical reference datasets* to:
     `add the two environment lines and the volumes line to the existing lists of the backend service (do not add a second environment: or volumes: key)`.
   - Rewrote the YAML snippet to show `backend:`, `# ...`, and `# ...existing entries stay...` under
     `environment:` and `volumes:` so operators append list items to the existing lists instead of
     creating duplicate YAML keys in `compose.yaml`.
   - Preserved the exact environment variable names and paths
     (`FLORABASE_WFO_SNAPSHOT_PATH=/var/lib/florabase/reference/wfo-2026-06.sqlite`,
     `FLORABASE_WCVP_V16_SNAPSHOT_PATH=/var/lib/florabase/reference/wcvp-v16/index.sqlite`,
     `/volume1/docker/florabase/reference:/var/lib/florabase/reference:ro`).
   - Verified in memory against `compose.yaml` with a duplicate-key-rejecting YAML loader that
     inserting the three list items yields valid Compose YAML with 5 `backend.environment` entries
     and 3 `backend.volumes` entries.

## Verification output

On tested commit `ae69dc4e1a4fefad06d356d72fabdee31e1c0c04`:

```text
$ make doc-links
Document links passed (369 documents)

$ python3 ./scripts/check-features.py
feature graph: 187 features valid
feature graph: not ready for a release candidate: RELEASE-001, BETA-IMAGE-001, beta-postgres-repro-001, BETA-SECURITY-001, BETA-DATA-001, BETA-ACCEPTANCE-001
```

`make verification-plan FORMAT=json` selected `"tier": "docs"` (`"docs_only": true`,
`"affected_scopes": ["documentation"]`). Adding this evidence file brings the checked document
count in `make doc-links` to 370 documents; the frozen branch tip is verified with `make doc-links`,
`python3 ./scripts/check-features.py`, and canonical `make feature-verify AGENT_ID=antigravity-neon`.

On merge commit `69b5547042bfd0a96c7dd49e2792466ff50e3c8f` (new base `b632c5c`):

```text
$ python3 ./scripts/check-features.py
feature graph: 188 features valid
feature graph: not ready for a release candidate: RELEASE-001, BETA-IMAGE-001, beta-postgres-repro-001, BETA-SECURITY-001, BETA-DATA-001, BETA-ACCEPTANCE-001

$ make doc-links
Document links passed (371 documents)
```
