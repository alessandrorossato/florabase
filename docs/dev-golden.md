# Persistent Golden DEV

DEV at `http://localhost:5173` runs the primary `main` checkout. Its PostgreSQL and original media
volumes persist across app restarts and main updates. COMPREHENSIVE generation stays explicit.
Ordinary CI and canonical FULL use SMOKE. Normal UAT continues to use small fixtures unless an
operator explicitly selects COMPREHENSIVE for an isolated UAT instance.

## First operator-authorized initialization

1. After integration, bring the primary checkout to clean, current `origin/main`. Run
   `make dev-status`. If DEV is behind the code, run `make dev-upgrade`, then run `make dev-up`
   to refresh both application containers. Start an empty installation the same way and create
   its private owner with `make dev-bootstrap-owner LOGIN=<login>` before loading the collection.
2. Run `make dev-golden-status` from primary main. Check that the source, project `florabase`,
   database revision, durable attachment volume and loopback frontend are the expected DEV
   resources. Resolve a reported pending operation before proceeding.
3. Choose the authorized operation. An empty, migrated DEV collection with its owner and default
   settings can use `make dev-golden-init CONFIRM_DEV_GOLDEN=initialize-florabase-dev`.
   The existing small operator collection is occupied. Its first Golden load is a replacement
   and requires the operator's explicit `make dev-golden-reset CONFIRM_DEV_GOLDEN=replace-florabase-dev`.
   Schedule a brief DEV outage. The command creates the coordinated recovery pair, restores it
   in scratch, checks the originals against database metadata and verifies artifact checksums
   before replacing data.
4. Retain the reported backup ID and its directory. Run `make dev-golden-status` and
   `make dev-golden-verify`, then sign in with the existing DEV login and password. Promotion
   retains the enabled owner's login, display name and password hash. It uses the generated
   owner UUID for the fixture's references, so sign in again after replacement. UAT's public
   fixture passwords are rejected for the promoted owner.

The commands use the workstation Docker socket and exact primary DEV resources, including
`florabase_postgres_data`, `florabase_attachment_data` and `florabase_internal`. They refuse
foreign source mounts, network and volume consumers, nonstandard PostgreSQL database settings,
and incompatible code or database revisions. The maintenance transaction holds the regular DEV
lifecycle lock and the shared FULL capacity lock. It stops the identified DEV services and starts
the exact PostgreSQL image on the validated volume without a network or published port. Keep
direct Docker and PostgreSQL maintenance idle while using these cooperative commands.

## Backup and recovery

Verified pre-change snapshots are kept under
`$(git rev-parse --git-common-dir)/info/florabase-dev-golden/<backup-id>/`. Keep `before.json` and
the entire `before/` directory together. The manifest binds the dump, original media archive and
Golden ledger to the local cluster and storage identities. These private files include the owner
hash and session records. Use private storage if copying them for retention. The backup covers
the supported single-owner DEV database and local attachment originals. Thumbnail derivatives
regenerate from the originals.

An interrupted operation leaves `pending.json` in the same parent directory. Keep the primary
checkout and DEV containers at that operation's source and revision. Use:

```bash
make dev-golden-reset RECOVER=1 CONFIRM_DEV_GOLDEN=recover-florabase-dev
```

If replacement began, recovery restores the pre-change pair and verifies the resulting database,
originals and ledger by taking and loading another pair before starting DEV. If replacement had
already passed validation, recovery resumes startup. If replacement never began, recovery
restarts the preserved services. If identity or checksum validation refuses, retain the journal,
the backup directory and Docker diagnostics for investigation.

To return to a verified pair after a completed cutover, use the printed backup ID and the same
DEV cluster, volumes and schema. This takes another verified pair of the current DEV before
restoring the selected one. Archived restores retain the current private owner credentials and
invalidate sessions from the archive:

```bash
make dev-golden-reset RECOVER=1 BACKUP=<backup-id> CONFIRM_DEV_GOLDEN=recover-florabase-dev
```

## Verification and main updates

`make dev-golden-verify` compares a read-only capture of DEV against the reviewed pin in scratch.
Run it while the collection is idle, because an application edit between the database and media
reads can produce a transient inconsistency. Output distinguishes an exact baseline, modified
content, failed invariants, and an unavailable pin. Operator edits may invalidate fixture-specific
counts, relationships or projections even when the application accepts those edits. Verification
does not repair or reload DEV.

After synchronizing primary `main`, check `make dev-status` and use `make dev-upgrade` for pending
forward migrations, then `make dev-up`. A new schema needs a matching reviewed Comprehensive pin
for further initialization or reset. The existing DEV collection remains usable after its forward
migration. To update the pin, generate fresh isolated copies, review logical rows, domain
projections, original media and the canonical digest, then run
`make golden-dataset-comprehensive-check`. Pin updates never trigger a DEV replacement.

## Reviewed baseline at `20261110_0047`

| Measure | Value |
| --- | ---: |
| Plan nodes / managed ledger records | 3,200 / 3,181 |
| Domain records / counted rows | 3,995 / 4,004 |
| Botanical identities / seed lots / sowings | 115 / 429 / 538 |
| Plants / plant groups / events | 213 / 137 / 851 |
| Projected History entries / saved views | 1,927 / 20 |
| Media assets / stored originals | 37 / 32 |
| PostgreSQL database size in the dedicated suite | 15,455,935 bytes |
| Original media payload in the measured copy | 1,774,716 bytes |
| Dedicated suite generation / validation process | 11.28 seconds |
| Generation peak RSS in the dedicated suite | 223,164 KiB |
| Initial disposable DEV startup, including explicit migration and build | 45.3 seconds |
| Health wait after cutover or recovery | 16.5–16.7 seconds |

Startup timings come from a workstation smoke with cached image layers. The health wait excludes
snapshot preparation and restore. The canonical digest is `a6141fc43cf46012007f342b0ba71b005f31141ae34c85f4cdb79bb30a9da88b`.
The isolated digest covers 34 files, including two expected thumbnails. Verification rebuilds
those derivatives in scratch from the restored originals. The added scenarios traverse a cutting
back through a multi-generation seed lineage, retain failed and completed rooting attempts,
show mixed-unit height measurements and a correction, and record exact and estimated phenology
dates. An operator-attributed correction retains an Aloe name in the historical name ledger.
Existing media, geographic, sourcing and lifecycle scenarios are preserved. Media is synthetic
or uses the existing licensed or clearly synthetic fixture metadata. Synthetic WFO and WCVP
indexes are local to generation and verification. DEV does not present them as botanical
authority or provision them as live provider indexes.
