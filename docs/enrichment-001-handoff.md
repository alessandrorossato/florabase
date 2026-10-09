# ENRICHMENT-001 implementation handoff

Implementation, operator UAT and independent final review are complete. The tree is intentionally
**unstaged and uncommitted** until the reviewed local commit and protected delivery.

## Worktree and feature boundary

- Worktree: `/home/alessandro/.codex/worktrees/16cc/florabase`.
- Branch: `feat/enrichment-001-native-range-proposals`, attached by `make feature-init`.
- Base and unchanged HEAD: `477ba4b6a287cf326aabb2b389902bc8df12b03a` (verified/delivered
  EXPLORE-002, PR #78). All implementation is in the working tree.
- Existing ENRICHMENT-001 is **verified**. ENRICHMENT-002 automatic refresh,
  SCHEDULE-001 and the broad cross-application visual/product review remain future work.
- BOTANY-003's separately approved blocked text-enrichment contract remains unchanged.
  No collection-origin semantics, occurrence-derived native assertions, profile prose, Saved Views,
  operational History or new generic provider/batch infrastructure is introduced.

## Exact source approval and provisioning

Provider: Royal Botanic Gardens, Kew. Dataset: **World Checklist of Vascular Plants, version 15**,
extracted/published 6 January 2026. Official plain archive:
<https://sftp.kew.org/pub/data-repositories/WCVP/Archive/wcvp_v15.zip>.

- SHA-256: `693e05b31ea6ce724c88ccf38bb964db2f22424b396f7ed1fd04fdb203af7e81`.
- Retrieval: `2026-10-09T06:16:20.117071+00:00`; compressed bytes: 89,508,082.
- Licence: [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/), confirmed by the exact
  DOI release record and official companion v15 DwCA metadata, not inferred from README/footer.
- README citation: Govaerts R (ed.). 2026. WCVP: World Checklist of Vascular Plants. Facilitated
  by the Royal Botanic Gardens, Kew. [WWW document] URL https://doi.org/10.34885/rvc3-4d77
  [accessed 06 Jan 2026]. Actual retrieval, transformations, no endorsement and accuracy limitations
  are additionally shown in the UI/evidence.
- Complete index: **1,441,152 taxa; 1,986,879 distribution assertions; 948,400,128 bytes**.
  No duplicate identifiers or malformed widths occurred during full audited inspection.

The explicit CLI `python -m florabase.native_range_enrichment.snapshot` installs this one pinned
archive into a replaceable SQLite index. The complete UAT index is ignored at
`backend/src/.source-cache/wcvp-v15.sqlite`, selected only by `compose.uat.yaml`. It was built from
`/tmp/enrichment-001-wcvp-v15.zip` with the actual retrieval metadata recorded above.
The plain archive, companion archive and extracted audit README remain outside Git. No provider
fetch runs at startup, migration, page navigation, Apply or ordinary API request time. Production
starts without the optional index; provisioning, read-only mount/environment configuration, disk
bounds and recovery are documented in [the contract](native-range-enrichment.md).

[Exact source audit](native-range-enrichment-source-v15.md) records source GO before implementation,
version/licence evidence, all source fields and qualifiers. Backend Docker exclusions prevent the
index entering images. Failed download/parse keeps an existing index intact; missing or corrupt
indexes preserve ordinary profile/range editing and retained evidence.

## Taxon, TDWG, proposals and durable evidence

The operator searches a literal prefix (up to 25 candidates), reviews authorship/rank/status and
accepted-taxon context, then confirms the exact WCVP `plant_name_id`. Accepted, self-accepted
Species/Subspecies/Variety/Form are eligible. Similar names, synonyms, a GBIF link or scientific-name
equality never establish a source match automatically. WCVP links are separate from the existing
GBIF-specific advisory links/cache. Reconfirmation invalidates older proposals.

The versioned crosswalk is **`wcvp15-wgsrpd2-cldr48.2.1-v1`**. Twelve reviewed exact level-3 units
map to canonical `unicode_cldr / 48.2.1 / iso_3166_1_alpha_2` places. The contract contains the
complete mapping table and official WGSRPD evidence. Splits (CZE/BLT/LBS), partial territories,
unknown/blank/lowercase codes and missing/retired canonical places are visible but excluded.
No fuzzy joins, inferred country detail, descendant expansion or geometry-derived knowledge occurs.

Native additions require all three source flags `introduced/extinct/location_doubtful` to be zero.
All original eleven distribution fields, assertion IDs and decisions are frozen; Introduced and
qualified assertions remain context only. Proposals show ADD, KEEP and CURRENT-ONLY. Apply adds
only explicitly selected mapped Native ranges, keeps **every** current range, and removes none.
Removal/replacement is deliberately unsupported. Existing manually curated range justification
is never replaced by imported provenance. Empty source evidence does not mean absence.

Migration **`20261009_0039`** adds WCVP links, monotonic range revisions, immutable frozen proposals
and immutable applications. Applied evidence copies the complete proposal plus selection, added/
kept IDs and destination revision/time. It survives source-index removal, link replacement and
manual range edits. Latest-ten history and exact-ID reads expose prior evidence and application
outcomes. PostgreSQL update/delete guards, unique application keys and restrictive FKs preserve
applied evidence. Identity deletion is serialized with Apply and rejected when applications exist;
the deletion UI mentions retained source evidence. Unapplied evidence can cascade with an explicitly
deleted unused identity. Empty downgrade preserves existing ranges/text; populated downgrade refuses
any WCVP link/proposal/application instead of destroying evidence.

## Apply, stale state and security

Apply locks selected geography in UUID order, then the identity, following existing canonical range
writers. It revalidates exact geography source codes, identity snapshot, link version/taxon/source,
current canonical IDs and monotonic revision, pinned source version/checksum and crosswalk version.
A stale or repeated Apply returns 409 with no partial writes. Editing/restoring a range is still
stale. Concurrent Apply produces one application. Apply versus identity deletion either retains
applied evidence and rejects deletion, or deletes the unused identity and rejects Apply.

**Frozen-source policy:** retained v15 proposals can still be applied when the optional source index
is missing, against their clearly displayed exact frozen version, provided durable/current checks
pass. Reprovisioning a snapshot flags the link stale for *new* retrieval and requires confirmation;
it does not rewrite old evidence. Future approved source/crosswalk versions require new proposals.

Seven authenticated endpoints under `/api/v1/botanical-identities/{identity_id}/native-range-enrichment`
cover source status, literal taxon search, link confirmation, proposal create/list/exact read and
Apply. Writes require owner, Origin and CSRF. Input extras/duplicate or empty selections are rejected.
The CLI alone accesses a fixed official HTTPS archive: no arbitrary URLs/forwarded cookies, no
redirects, bounded 10/60-second timeouts/240-second download, 100 MB compressed/2 GB index bounds,
exact ZIP contents/sizes/checksum, streamed UTF-8/pipe parsing, no archive extraction, atomic install.
OpenAPI and generated frontend declarations are checked in as intentional working-tree artifacts.

## Focused validation

Focused implementation validation passed: **75 backend unit tests**, **81 real PostgreSQL integration tests**,
**38 distinct frontend tests** (23 enrichment/provider/Explore, 14 profile/navigation and one
additional guarded identity-deletion case), **19 UAT host guard tests**, 95-feature graph,
Ruff/format, strict mypy **315 files**, Prettier/ESLint/strict TypeScript, API generation/drift,
Vite production bundle and both production Docker images. Repeated focused UI/source runs are
not counted as additional tests. PostgreSQL had six existing Alembic deprecation warnings.
The production backend's startup/health passed with the source index absent, network disabled,
read-only root and ephemeral attachment tmpfs. Reproducible focused commands:

```sh
python3 scripts/workflow_environment.py quality compose -- run --rm --no-deps backend \
  pytest --no-cov tests/test_native_range_enrichment.py tests/test_botanical_identity_service.py \
  tests/test_botanical_native_range.py tests/test_botanical_profile_service.py \
  tests/test_external_botany_provider.py tests/test_native_ranges_explore.py
python3 scripts/workflow_environment.py quality compose -- run --rm --no-deps backend \
  sh -ec 'ruff check src tests alembic; ruff format --check src tests alembic; mypy'
make api-check
make test-uat-preview
python3 scripts/check-features.py
```

PostgreSQL focused validation used `compose.integration.yaml` with a unique disposable project and tmpfs
PostgreSQL, plus a temporary override running Alembic head and the enrichment service/API/migration,
profile API, external botany API, native-range Explore and identity service/API modules. A free
`10.240.39.0/28` subnet avoids the host's occupied default range. Cleanup affects that exact
project only and never uses volume deletion. Committed concurrency-test records are explicitly
scoped/removed inside that disposable fixture so later downgrade tests see no persistent evidence.

Frontend validation includes the new enrichment panel, existing advisory provider panel,
NativeRangesScreen, targeted App/UX004 profile/native-range navigation and UX001 guarded identity
delete, strict TypeScript, ESLint/Prettier and Vite production bundle. Both Docker `runtime` targets
are built locally. No full canonical gate, coverage claim or verification receipt is asserted.
Existing Alembic path-separator deprecation warnings remain; none were suppressed.

## Operator UAT

- URL: **http://localhost:15174**; owner **preview / preview** (synthetic UAT only).
- Owner/source: this worktree, Compose project `florabase-uat-preview`; schema **0039**.
- Explicit guarded retirement from old owner `258f`, then new worktree up/seed/status. Fixture
  **v4 / 42 baseline records**. No personal collection data or DEV/Stable Preview/production change.
- Frontend/backend/database are healthy. Initial frontend dependency installation exceeded the
  first startup health window; it subsequently became healthy. Seed is explicit and idempotent.
- Entry: Botanical identities → open a synthetic identity → Reference → Native range →
  **Check trusted source**. Source UI uses named radio/checkbox choices, textual diff/limitations,
  two-step Apply confirmation, error/success focus and explicit retry. No provider request on mount.

Implementation smoke confirmed exact Aloe accepted/nonaccepted/synonym choices, explicit confirmation,
76 raw assertions (one mapped Native Oman and 75 Introduced contexts), Apply adding Oman while keeping
manual Thailand/Italy, canonical refresh and fresh KEEP proposal. Aloe's source link and one immutable
application are deliberately retained for review; no operator acceptance is claimed. DOM checks at
390×844, 1024×844 and 1440×844 found no horizontal overflow and observed focused success feedback.

Suggested scenarios (these are synthetic identities; source evidence remains actual pinned WCVP):

| Identity / exact WCVP ID | Review scenario |
| --- | --- |
| Aloe vera / `298116` | Already linked/applied Oman. Retrieve now: KEEP Oman, CURRENT-ONLY Thailand/Italy; select KEEP for a no-change application. Expand evidence: introduced regions cannot be selected. `298117` and synonyms are disabled. |
| Ocimum basilicum / `136820` | Mixed mapped Cambodia/Laos/Thailand/Vietnam and unresolved Native units; 102 Introduced assertions remain context. Select only one addition; keep every existing manual range. |
| Viola tricolor / `2461201` | Native Bulgaria/Hungary eligible; CZE/BLT splits and ITA/FRA/SPA partial units visible and excluded. |
| Lavandula angustifolia / `108971` | Native France/Spain/Italy all partial: no rounded country additions. Duplicate illegitimate name remains disabled. Existing ranges remain current-only. |
| Solanum quitoense / `3032457` | Native Costa Rica/Peru eligible, other units unresolved; selective multi-candidate review. |

For stale Apply: retrieve a proposal; in another tab edit the identity or add/remove a manual range;
then attempt the first proposal's Apply. Expect focused 409 feedback and no selected addition.
Retry source status/reconfirm as needed and retrieve/review fresh evidence. Reopen prior applied
proposals through Recent retained proposals; their source/assertions and actual Add/Keep outcome
stay frozen. Explore → Native ranges reads the resulting canonical relationships for represented
identities; pending/failed/unapplied proposals never enter coverage.

Independent final canonical verification passed on the corrected tree: `make feature-verify` ran the
full **856 backend unit / 534 frontend / 693 PostgreSQL integration** suites, strict mypy (**317
files**), formatting/lint/type checks, API drift, production build, migration verification,
whitespace checks and receipt recording. One pre-existing integration expectation was corrected to
assert that a failed transactional downgrade leaves Alembic at the actual `20261009_0039` head.
Operator UAT was accepted. The broad cross-application visual review remains a later release
checkpoint. Delivery and `make feature-finish` remain pending; after merge, run `make dev-upgrade`
for migration `20261009_0039`.
