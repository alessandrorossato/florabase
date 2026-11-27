# WF-04 Batch 14b integration evidence

The Batch 14b integration branch is `ci/batch-14b`, based on pinned `origin/main` at
`08ff2f92d6f9b5496c04ed3b0ae5828451e35269` (PR #227). The integration writer is `claude-batch-14b`.
The [manifest](batches/batch-14b.json) records the exact source tips, merge commits, additive
`docs/progress.md` resolutions and post-merge reconciliations.

## Source provenance and exact-tip readiness

Each source was frozen in its own clean, claimed worktree with no pending handoff and reviewed
independently before integration:

| ID | Branch | Frozen tip | Writer | Source QA | Committed evidence |
| --- | --- | --- | --- | --- | --- |
| IMPORT-002 | `feat/import-002-sheet-wizard` | `c2a507faeac0d19d1c64a77cb25328b643188699` | `claude-import-002` | `claude-batch-14-source-qa` | [`import-002.md`](import-002.md) |
| REF-SETUP-001 | `feat/ref-setup-001` | `5b14359fd160ea36cb85bf9f90191c6a11a673ff` | `claude-ref-setup` | `claude-batch-14-source-qa` | [`ref-setup-001.md`](ref-setup-001.md), [`ref-setup-001-design.md`](ref-setup-001-design.md) |
| ABOUT-001 | `feat/about-001` | `02008ae1b7ec15b0114afaba30689fef46e7d51a` | `claude-about-001` | `claude-batch-14-source-qa` | [`about-001.md`](about-001.md) |
| UX-SORT-002 | `feat/ux-sort-002` | `af617fc0749bf39e6746df2f53196ce3aa1cfeac` | `claude-ux-sort-002` | `claude-batch-14-source-qa` | [`ux-sort-002.md`](ux-sort-002.md) |
| MEDIA-SETTINGS-001 | `feat/media-settings-001` | `77f96009a638660c9919ca72dcde2c240096fdae` | `claude-media-settings` | `claude-batch-14-source-qa` | [`media-settings-001.md`](media-settings-001.md) |
| MOBILE-003 | `feat/mobile-003-usable-app` | `b4fed54857219d251046e0d7593b7b64bbfbab04` | `neon-mobile-003` | `claude-batch-14-source-qa` | [`mobile.md`](../../mobile.md), [`progress.md`](../../progress.md) (no dedicated evidence file) |
| DOC-04 | `docs/doc-04-user-guide` | `7e19d2f6014c10887bd49b6ba7655586dafc65c2` | `claude-doc-04` | `claude-batch-14-source-qa` | [`doc-04.md`](doc-04.md), [`doc-04-trial-template.md`](doc-04-trial-template.md) |
| UI-POLISH-003 (with UI-POLISH-002, UI-POLISH-004 and UI-POLISH-005) | `fix/ui-polish-beta10` | `31ef52a9c94a60c22f7a8720b8178da8e35a60c5` | `claude-ui-polish` | `claude-batch-14-source-qa` | [`progress.md`](../../progress.md), [`native-ranges-explore.md`](../../native-ranges-explore.md) (no dedicated evidence file) |
| BETA-SECURITY-001 | `fix/postgres-libxml2-r5` | `b8122d15b70f8d4735845fbeda846d44feb10e8e` | `claude-pg-pin` | `claude-batch-14-source-qa` | [`postgres-libxml2-2.13.9-r5/README.md`](../../security/beta-security-001/postgres-libxml2-2.13.9-r5/README.md) |

IMPORT-002 is based on the older `main` `b632c5c`; the planner accepted it without a rebase and its
frozen tip remains an ancestor of the integration head. ABOUT-001 (`02008ae`) and REF-SETUP-001
(`5b14359`) have merged `main` `08ff2f9`. The eighth source, `fix/ui-polish-beta10`, carries
UI-POLISH-002, UI-POLISH-003, UI-POLISH-004 and UI-POLISH-005 (`1c07bd3`, `6614f80` and `945898b`
with review fixes `c7cdd1d` on top of `06d45ec`) and is recorded under the source ID
`UI-POLISH-003`. It also contains UX-SORT-002 `af617fc`, merged into the source at `254f39b` (both
Cuttings tests kept; `31ef52a` removes leftover progress merge markers), so the UI merge brings no
UX-SORT-002 change beyond the earlier UX-SORT-002 merge. The ninth source, `fix/postgres-libxml2-r5`
(BETA-SECURITY-001, based on `08ff2f9`), rebuilds the PostgreSQL image as `18.6-alpine-florabase.6`
with `libxml2=2.13.9-r5` in `postgres/Dockerfile` and pins the reproduced index and platform digests
in `release/inputs.json`, because Alpine withdrew `libxml2` `2.13.9-r3` and the hosted `rehearse`
check of PR #228 failed. This candidate supersedes the published eight-source `ci/batch-14`
`b59f659` (PR #228; its last source merge `6e2abb6` has the same tree, `8d5c3e1`, as this
branch's UI-POLISH-003 merge `4df61db`), which cannot be updated in place because the new source changes
files outside `scripts/` and `docs/`. It also supersedes the unpublished
eight-source `107ff11` (same sources with UI-POLISH at `06d45ec`), `7724825` (UI-POLISH at
`9d6705e`), the seven-source `9be1bba` and the earlier `c229d99`, whose integrated tree failed the
REF-SETUP-001 `system/info` key-set test against the MOBILE-003 `runtime_config` key; REF-SETUP-001
`5b14359` now checks the base keys as a subset.

## Integration conflict and cross-branch checks

- **Conflict resolution:** `feature-batch-prepare` reported conflicts only in `docs/progress.md`
  (all sources except REF-SETUP-001, BETA-SECURITY-001 included) and resolved them additively; the UI-POLISH milestones land in
  merge order after DOC-04, followed by the BETA-SECURITY-001 milestone. The UX-SORT-002 milestone that the UI source also carries is identical
  to the UX-SORT-002 source's, so the merge kept a single block and no duplicate needed removal. The reconciliation restores merge order there (the IMPORT-002
  milestones, based on older `b632c5c`, had landed below the Batch 13 milestone) and adds the
  missing blank line before the ABOUT-001 heading, without adding or removing any other line than
  the Batch 14b milestone.
- **Shared source files** (auto-merged, covered by checks on the integrated tree):
  `backend/openapi.json` and `frontend/src/api/schema.d.ts` (IMPORT-002, REF-SETUP-001, UX-SORT-002,
  MEDIA-SETTINGS-001, MOBILE-003); `backend/src/florabase/api/system.py`, `core/config.py` and
  `scripts/test-beta-runtime.py` (REF-SETUP-001, MOBILE-003); `backend/src/florabase/media/api.py`
  and `frontend/src/media/api.ts` (UX-SORT-002, MEDIA-SETTINGS-001); `frontend/src/App.tsx`,
  `shell/navigation.ts`, `shell/WorkbenchShell.test.tsx` (ABOUT-001, MEDIA-SETTINGS-001,
  UI-POLISH-003) and `components/navigationIcons.ts` (ABOUT-001, MEDIA-SETTINGS-001);
  `frontend/src/styles.css` (IMPORT-002, UI-POLISH-003); `frontend/src/taxonomy/TaxonomyScreen.tsx`
  (REF-SETUP-001, UI-POLISH-003/005); `frontend/src/settings/DataSourcesScreen.tsx` (REF-SETUP-001, ABOUT-001; the
  integrated text describes automatic background provisioning or manual mounting);
  `frontend/src/settings/settings.css` (REF-SETUP-001, MEDIA-SETTINGS-001, UI-POLISH-004);
  `frontend/src/settings/HelpAndSources.test.tsx` (REF-SETUP-001, UI-POLISH-004);
  `scripts/verification-impact.json` (IMPORT-002, REF-SETUP-001, UI-POLISH-003); `README.md`
  (ABOUT-001, DOC-04); `docs/installation.md` (REF-SETUP-001, BETA-SECURITY-001). BETA-SECURITY-001
  alone changes `postgres/Dockerfile`, `release/inputs.json` and the
  `docs/security/beta-security-001/` and `beta-distribution-001/postgresql-image.md` records.
- **Migration:** MEDIA-SETTINGS-001 adds `20261125_0050_media_settings` on `20261125_0049`; it is
  the single Alembic head of the integrated tree. Delivery therefore reports a migration and the
  operator runs `make dev-upgrade` after finish.
- **Generated API:** `make api-generate` on the integrated tree produced no drift.
- **Reconciliation:** prepended the Batch 14b integration milestone to
  [`docs/progress.md`](../../progress.md) and restored merge order there; listed Settings → Media
  in the [user guide](../../user-guide/README.md) (MEDIA-SETTINGS-001 left it to integration); and
  described automatic background WFO/WCVP provisioning (REF-SETUP-001) in
  [`reference-data.md`](../../user-guide/reference-data.md). The user guide's Workbench summary
  also names the workspace Overview pages and no longer lists Plant groups and Stored material as
  menu entries (UI-POLISH-002/003 changed the navigation after DOC-04 wrote it). UI-POLISH-004
  (full-width Settings, described Help links, home indicators, full screen, rail order) changes no
  label or path the user guide names. UI-POLISH-005 moves the Rooting attempt sections into
  Overview, Observations and Offspring tabs, puts **Log rooting observation** in the header and
  shows the rooting state as the header's **Rooting** row (formerly **Rooting outcome** under
  Rooting overview), so [`cuttings.md`](../../user-guide/cuttings.md) now names those tabs and the
  header; its other changes (record header, Harvest Overview/Photos tabs, Cuttings rows opening
  records, list headers, Native ranges cards, provenance map, species list) change no label or path
  the guide names. The Public / QR base URL example in
  [`finding-things-and-labels.md`](../../user-guide/finding-things-and-labels.md) (DOC-04) now uses
  `http://florabase.local:8080` instead of a private-network address, which the beta-runtime
  disclosure gate rejects.
- **Carried by the sources:** the `CHANGELOG.md` entry "End-user guide (`docs/user-guide/`)."
  under `Unreleased` → `Added` (REF-SETUP-001 `5b14359`) and Settings → Media in the root
  `README.md` feature list (ABOUT-001 `02008ae`) are present in the integrated tree.
- **Proposed release classes (for operator confirmation, already in `scope-v1.json`):**
  `IMPORT-002`, `REF-SETUP-001`, `ABOUT-001`, `UX-SORT-002`, `MEDIA-SETTINGS-001`, `UI-POLISH-002`,
  `UI-POLISH-003`, `UI-POLISH-004`, `UI-POLISH-005` (`best-effort`); `DOC-04` (`release-work`, still `in_progress`); `MOBILE-003`
  (`post-1.0`); `BETA-SECURITY-001` (`release-work`).
