# WCVP-VERSION-001 — explicit v15/v16 support

Implementation is isolated on `feat/wcvp-version-001`, based on fetched `origin/main`
`c77a1c5330de949168bf5f7c90d0f533af1bc320`. Operator acceptance is pending;
files remain unstaged and uncommitted. No protected environment or approved source artifact changed.

## Approved releases and evidence

The authoritative assessment remains in the preserved research worktree:
`/home/alessandro/.codex/worktrees/88b2/florabase/docs/wcvp-v16-upgrade-assessment-2026-10-28.md`,
SHA-256 `1b8047ccc8409601691324cb6f47c1d271880e1b856c6a9786735aba637288ce`.
Its manifests, exact-ID comparisons and source records informed this bounded extension.
No download, licensing or archive-discovery investigation was repeated.

| Definition | v15 (default) | v16 (explicit) |
| --- | --- | --- |
| Official URL | `https://sftp.kew.org/pub/data-repositories/WCVP/Archive/wcvp_v15.zip` | `https://sftp.kew.org/pub/data-repositories/WCVP/wcvp.zip` |
| SHA-256 | `693e05b31ea6ce724c88ccf38bb964db2f22424b396f7ed1fd04fdb203af7e81` | `d32ea2b3a85e489b14e83bcc9eae7274532e1d113753f7be290d4b2dfde573fa` |
| Citation DOI | [10.34885/rvc3-4d77](https://doi.org/10.34885/rvc3-4d77), accessed 06 Jan 2026 | [10.34885/egs6-cp24](https://doi.org/10.34885/egs6-cp24), accessed 04 Jun 2026 |
| Taxa / distribution rows | 1,441,152 / 1,986,879 | 1,448,984 / 1,995,338 |
| README / names / distribution bytes | 17,827 / 298,218,467 / 141,066,449 | 18,112 / 300,826,661 / 141,657,561 |
| Settings path | `FLORABASE_WCVP_SNAPSHOT_PATH` | `FLORABASE_WCVP_V16_SNAPSHOT_PATH` |
| Crosswalk | `wcvp15-wgsrpd2-cldr48.2.1-v1` | `wcvp16-wgsrpd2-cldr48.2.1-v1` |

Both releases retain [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/), exact citation,
Kew provider identity, actual archive retrieval time and complete coverage. The frozen release
registry contains the complete approved Govaerts/Kew citation, URL and rights definitions.
The v16 upstream URL is mutable; its approved definition is immutable and any rotated bytes fail
checksum validation. There is no latest-release discovery or arbitrary-URL option.
See the [existing v15 source approval](native-range-enrichment-source-v15.md) and
[WGSRPD/CLDR mapping evidence](native-range-enrichment.md#geography-contract).

The assessment found 8,225 added IDs, 393 removed IDs, 87,460 changed shared records,
4,299 status transitions and 10,929 accepted-ID changes. An unchanged ID does not authorize a
cross-version identity relationship. The twelve equivalences remain exactly
BOL→BO, BUL→BG, CBD→KH, COS→CR, HUN→HU, LAO→LA, OMA→OM, PAR→PY, PER→PE,
THA→TH, URU→UY and VIE→VN. The literal mapping implementation is unchanged.

## Release selection and compatibility

| Configuration / durable evidence | Behavior |
| --- | --- |
| v15 only | Existing clients and UI start on v15; selecting v16 reports unavailable |
| v16 only | Default v15 reports unavailable; explicit v16 selection enables search/confirmation |
| Both | Independent bounded searches; selection does not mutate a confirmed link |
| Neither / corrupt / wrong-version index | Startup and operator data remain usable; source review fails closed |
| v15 link while browsing v16 | Retains v15 identity and version; new v16 proposal requires explicit reconfirmation |
| Frozen v15 or v16 proposal, original index absent | Inspect and Apply use original immutable release/crosswalk evidence |
| Deliberate v16 reconfirmation | Existing link UUID rotates; earlier unapplied proposals reject as stale |
| Applied historical proposal after reconfirmation | Immutable application and full original evidence remain inspectable |
| Removed ID / synonym / different accepted ID | No automatic migration or accepted-ID following; operator must choose an eligible exact record |
| Changed/absent distribution | Existing native ranges remain KEEP/CURRENT-ONLY; Apply never removes them |

`GET source`, `GET taxa`, `PUT link` and `POST proposals` accept `version=15|16`, default `15`.
History, proposal inspection and Apply do not accept a release selector: frozen proposal evidence
is authoritative. Unknown versions receive HTTP422. Checksums are checked against the selected
release; no fallback occurs between paths. The Native ranges panel exposes an explicit version
select before search and confirmation, names the confirmed and frozen release, and clears transient
candidate/proposal review on selection changes. Confirmation remains a separate explicit write.

Apply validates source URL/checksum/provider/licence/citation/coverage against that proposal's
original approved release, then its matching crosswalk. It retains identity/link/source/taxon,
destination revision/IDs and geography checks and immutable application constraints.
Locked geography rows are refreshed from PostgreSQL to observe another transaction's committed
metadata changes even when SQLAlchemy already holds those objects. Locks retain the established
places-before-identity ordering. Add/keep-only behavior and profile text are unchanged.

No Alembic migration is required: existing source JSON already stores release metadata,
proposals already freeze crosswalk/source and links already have a rotating UUID.
Format version 1, existing v15 metadata defaults, rows, evidence and triggers are retained.
There is no backfill, automatic reconciliation, taxonomy rename, BOTANY-003 or source redesign.

## Provisioning and resource measurement

Use separate filenames and explicit configuration mounts, readable by the runtime user.
Provision outside application startup with the existing bounded TLS CLI:

```sh
python -m florabase.native_range_enrichment.snapshot /wcvp/wcvp-v15.sqlite --version 15
python -m florabase.native_range_enrichment.snapshot /wcvp/wcvp-v16.sqlite --version 16
```

For an already securely retrieved approved archive:

```sh
python -m florabase.native_range_enrichment.snapshot /wcvp/wcvp-v16.sqlite \
  --version 16 --archive /audit/wcvp-v16.zip \
  --retrieved-at 2026-10-28T20:31:34.536724+00:00
```

Never invent the retrieval timestamp. The CLI validates exact hash, three ZIP members and sizes,
31/11 headers, bounded row values/flags, unique IDs and distribution references. It streams members
without extraction and publishes a temporary SQLite index atomically. Existing destinations must
already belong to the same approved release. A per-destination advisory lock rechecks ownership
before rename, including simultaneous cross-version provisioning. Unknown/corrupt/other-version
files are refused and preserved. The small `.lock` file remains intentionally. No schema change,
index conversion or link migration is needed. Mount indices read-only for the application.

The **production-format v16 index is 952,799,232 bytes (908.66 MiB)**, with 1,448,984 taxa and
1,995,338 distribution rows. [Recorded measurement](review/wcvp-version-001/provisioning-v16.json):
Python 3.14.7, wall 208.48s, user CPU 173.69s, system CPU 15.66s, peak process RSS 44,872 KiB
(43.82 MiB). These are one local run's observations, not a guaranteed host/cgroup memory ceiling.
The research comparison SQLite of 2,073,739,264 bytes is **not** the production index.

The index builder retains the 2,000,000,000-byte final-file limit; download remains limited to
100,000,000 bytes and 240 seconds. Provisioning needs the archive plus a temporary index in the
destination filesystem, SQLite journal/sort workspace and, for replacement, the existing index.
Reserve at least 3 GiB free per active build as operating headroom; temporary peak disk and cgroup
memory were not measured. Provision sequentially on small hosts. Keep approved archives for
reprovisioning if Kew rotates the v16 URL. Never use the v15 path for v16.

## Verification and Review

Focused checks cover archive/schema rejection, default/path configurations, metadata forgery,
cross-release destination protection (including simultaneous publishers), literal mappings,
version-aware HTTP confirmation/proposals, missing sources, frozen v15 Apply with v16 installed,
explicit reconfirmation/stale proposals, removed/status/accepted-ID transitions, immutable evidence,
range/identity/link conflicts, duplicate Apply, identity deletion serialization and changed geography.
Frontend checks cover the existing workflow, explicit v16 selection/checksum/confirmation/proposal
and inspectable applied v15 history while the selected v16 index is unavailable.

The impact planner selects **FULL** because configuration is a high-risk path. Use one final
`make feature-verify` after freezing all tracked changes; its per-worktree receipt and verification
logs are authoritative for canonical results, including API drift, coverage, PostgreSQL, migration
cycle and both builds. Focused tests do not substitute for that receipt.

This host exhausted Docker's default subnet pools. Existing networks were preserved. Review alone
uses checked-free `10.254.241.0/28`. Local disposable integration invocations use a temporary Docker
launcher at `/home/alessandro/.codex/worktrees/wcvp-version-001/florabase/.source-cache/wcvp-version-001/docker-bin/docker` adding only `10.254.240.0/28` to this exact worktree's
labelled disposable network configuration; all repository database/ownership/cleanup guards remain.
The launcher is outside the product and is unnecessary on hosts with available default pools.

See [isolated Review and operator checklist](review/wcvp-version-001/README.md).
The Review adapter reuses the existing environment/ownership checks with distinct project, database,
volumes and port; its small additive fixture refuses existing unrelated data and retains repeat seed IDs.
The standard Review, UI System v1, DEV, UAT, Preview and production are untouched.
